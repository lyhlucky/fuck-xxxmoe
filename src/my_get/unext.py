#********************************************************************************************
# https://video.unext.jp/
#********************************************************************************************

import requests
import re
import json
import os
from pywidevine import PSSH, Cdm
import subprocess
from yt_dlp import YoutubeDL
import logging
from urllib.parse import urlparse, urlencode, parse_qs
import xml.etree.ElementTree as ET
from base64 import b64decode
from io import TextIOWrapper

from common import MsgType, flush_print, sanitize_filename, ensure_playlistname, join_query_item
from cdmhelper import create_cmd_device


logger = logging.getLogger('Unext')

class UnextAdaptor:
    def __init__(
        self,
        original_url,
        params,
        proxies,
        progress_hook=None
    ):
        self.original_url = original_url
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.final_location = None
        self.play_token = None
        self.video_pssh = None
        self.audio_pssh = None
        self.video_url = None
        self.audio_url = None
        self.metadata = None
        self.resolution_list = []

        if 'metadata' in params:
            self.metadata = json.loads(b64decode(params['metadata']).decode('utf-8'))

        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'accept': '*/*',
            'content-type': 'application/json'
        })
        
        if 'sessdata' in params:
            self.session.cookies.update(
                requests.utils.cookiejar_from_dict(json.loads(b64decode(self.params['sessdata']).decode('utf-8')), cookiejar=None, overwrite=True)
            )
        self.session.proxies = proxies

    def extract(self):
        parsed = urlparse(self.original_url)
        if '/play/' in self.original_url:
            path_array = parsed.path.split("/")
            season_id = path_array[-2]
            episode_id = path_array[-1]
            episode_metadata = self._get_episode_metadata(season_id, episode_id)

            video_title = episode_metadata["season_title"]
            if len(episode_metadata["display_no"]) > 0:
                video_title = video_title + f" [{episode_metadata['display_no']}]"
            if len(episode_metadata["episode_title"]) > 0 and video_title != episode_metadata["episode_title"]:
                video_title = video_title + " - " + episode_metadata["episode_title"]

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': video_title,
                    'thumbnail': episode_metadata['thumbnail'],
                    'local_thumbnail': '',
                    'duration': 0,
                    'is_live': False
                }
            }))

            play_mode = 'caption'
            if self.metadata is not None and 'audioLanguage' in self.metadata and self.metadata['audioLanguage'] == 'Dub':
                play_mode = 'dub'

            mpd_url = self._get_mpd_url(episode_id, play_mode)
            self._parse_mpd(mpd_url)

            save_path = self.params['save_path']
            current_directory = os.getcwd()
            os.chdir(save_path)

            audio_key = self._get_decryption_key(self.audio_pssh, 0)

            vindex = 1
            if self.metadata is not None and 'resolution' in self.metadata:
                height = int(self.metadata['resolution'].split('x')[-1])
                if height < 1080:
                    vindex = 2
            video_key = self._get_decryption_key(self.video_pssh, vindex)

            audio_encrypted_path = 'audio_encrypted.mp4'
            self._download(self.audio_url, audio_encrypted_path)

            video_encrypted_path = 'vidio_encrypted.mp4'
            self._download(self.video_url, video_encrypted_path)

            audio_decrypted_path = 'audio_decrypted.mp4'
            self._decrypt(audio_key, audio_encrypted_path, audio_decrypted_path)

            video_decrypted_path = 'vidio_decrypted.mp4'
            self._decrypt(video_key, video_encrypted_path, video_decrypted_path)

            video_mux_path = "video_mux.mp4"
            self._merge_audio_video(audio_decrypted_path, video_decrypted_path, video_mux_path)

            valid_filename = sanitize_filename(video_title)
            file_path = f"{save_path}/{valid_filename}"
            max_path = 180
            if (len(file_path) > max_path):
                file_path = file_path[0:max_path]
                valid_filename = os.path.basename(file_path).strip()

            os.rename(video_mux_path, f"{valid_filename}.mp4")
            self.final_location = f"{save_path}/{valid_filename}.mp4"
            os.chdir(current_directory)
        else:
            logger.info(f"extract url failed: {self.original_url}")
            raise(Exception('unsupported error'))
        
    def extract_playlist(self):
        parsed = urlparse(self.original_url)
        qs = parse_qs(parsed.query)
        season_id = None

        if 'td' in qs:
            season_id = qs['td'][0]
        else:
            if '/episode/' in self.original_url:
                pattern = r'/episode/(SID\d+)/'
                match = re.search(pattern, self.original_url)
                if match:
                    season_id = match.group(1)
            elif '/title/' in self.original_url:
                path_array = parsed.path.split("/")
                season_id = path_array[-1]
            elif '/play/' in self.original_url:
                path_array = parsed.path.split("/")
                season_id = path_array[-2]
            else:
                logger.info(f"extract url failed: {self.original_url}")
                raise(Exception('unsupported error'))
        
        if season_id is not None:
            self._parse_episode_list(season_id)
        else:
            logger.info(f"invalid season_id")
            raise(Exception('unsupported error'))

    def _parse_episode_list(self, season_id):

        def get_one_page(season_id, page_index):
            base_url = "https://cc.unext.jp/"
            has_more = False

            params = {
                "operationName": "cosmo_getVideoTitleEpisodes",
                "variables": json.dumps({
                    "code": season_id,
                    "page": page_index,
                    "pageSize": 20
                }, separators=(',', ':')),
                "extensions": json.dumps({
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "a2ee1b5c371aa0385a45bd8066671e50b8e618312246356a4d6b3feaf50d6a93"
                    }
                }, separators=(',', ':'))
            }
            try:
                videos = []
                encoded_url = base_url + "?" + urlencode(params)
                response = self.session.get(encoded_url)
                response.raise_for_status()
                episodes_wrapper = response.json()['data']['webfront_title_titleEpisodes']
                if episodes_wrapper['pageInfo']['pages'] > page_index:
                    has_more = True

                episodes = episodes_wrapper['episodes']
                for episode in episodes:
                    video = {}
                    if len(episode['episodeName']) > 0:
                        video['title'] = episode['episodeName']
                    else:
                        display_no = episode['displayNo']
                        if display_no.startswith('#'):
                            display_no = display_no.replace('#', 'E')
                        video['title'] = display_no
                    episode_id = episode['id']
                    video_url = f'https://video.unext.jp/play/{season_id}/{episode_id}'
                    playlist_name = ensure_playlistname(f'{metadata["season_title"]}', 'u-next')

                    video['url'] = join_query_item(video_url, 'itdl_pname', playlist_name)
                    video['duration'] = episode['duration']
                    video['episode_id'] = episode_id
                    videos.append(video)

                return has_more, videos
            except Exception as e:
                logger.info(f"get episodes failed: {e}")
                raise(Exception('get episodes error'))
            
        metadata = self._get_season_metadata(season_id)
            
        episodes_list = []
        page_index = 1
        has_more = True

        while has_more:
            has_more, videos = get_one_page(season_id, page_index)
            episodes_list.extend(videos)
            page_index = page_index + 1

        # 获取列表第一个视频的分辨率支持列表
        parsed = urlparse(episodes_list[0]['url'])
        episode_id = parsed.path.split("/")[-1]
        mpd_url = self._get_mpd_url(episode_id)
        self._parse_mpd(mpd_url)
        
        resp = {
            'type': MsgType.playlist.value,
            'msg': {
                'videos': episodes_list,
                'title': metadata['season_title'],
                'thumbnail': metadata['thumbnail'],
                'description': metadata['description'],
                'has_dub': metadata['has_dub'],
                'resolutions': self.resolution_list
            }
        }
        flush_print(json.dumps(resp))

    def _get_season_metadata(self, season_id):
        metadata = {}
        base_url = "https://cc.unext.jp/"
        params = {
            "operationName": 'cosmo_getVideoTitle',
            "variables": json.dumps({
                "code": season_id
            }, separators=(',', ':')),
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9c27258639966cfe47ebf308f155c3107d7489ed421b4d6e5ea61c3dd3c06c57"
                }
            }, separators=(',', ':'))
        }

        encoded_url = base_url + "?" + urlencode(params)
        try:
            response = self.session.get(encoded_url)
            response.raise_for_status()
            data = response.json()['data']
            stage = data['webfront_title_stage']
            metadata['season_title'] = stage['titleName']
            thumbnail_url = stage['thumbnail']['standard']
            if not thumbnail_url.startswith('http'):
                thumbnail_url = 'https://' + thumbnail_url
            metadata['thumbnail'] = thumbnail_url
            if len(stage['catchphrase']) > 0:
                metadata['description'] = stage['catchphrase']
            elif len(stage['attractions']) > 0:
                metadata['description'] = stage['attractions']
            elif len(stage['story']) > 0:
                metadata['description'] = stage['story']

            metadata['has_dub'] = stage.get('hasDub', False)

        except Exception as e:
            logger.info(f"get season metadata failed: {e}")
            raise(Exception("get season metadata error"))
        
        return metadata
    
    def _get_episode_metadata(self, season_id, episode_id):
        metadata = {}
        base_url = "https://cc.unext.jp/"
        params = {
            "operationName": 'cosmo_getTitle',
            "variables": json.dumps({
                "id": season_id,
                "episodeCode": episode_id,
                "episodePageSize": 1000,
                "episodePage": 1
            }, separators=(',', ':')),
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "34793f6c4562e912ea232e6552abc5ea638c7254119188c68fa3b5789851c0a4"
                }
            }, separators=(',', ':'))
        }

        encoded_url = base_url + "?" + urlencode(params)
        try:
            response = self.session.get(encoded_url)
            response.raise_for_status()
            data = response.json()['data']
            stage = data['webfront_title_stage']
            metadata['season_title'] = stage['titleName']
            episodes = data['webfront_title_titleEpisodes']['episodes']
            metadata['has_dub'] = stage['episode']['hasDub']
            for episode in episodes:
                if episode['id'] == episode_id:
                    metadata['episode_title'] = episode['episodeName']
                    display_no = episode['displayNo']
                    if display_no.startswith('#'):
                        display_no = display_no.replace('#', 'E')
                    metadata['display_no'] = display_no
                    thumbnail_url = episode['thumbnail']['standard']
                    if not thumbnail_url.startswith('http'):
                        thumbnail_url = 'https://' + thumbnail_url
                    metadata['thumbnail'] = thumbnail_url
                    break
        except Exception as e:
            logger.info(f"get episode metadata failed: {e}")
            raise(Exception("get episode metadata error"))
        
        return metadata

    def _get_mpd_url(self, episode_id, play_mode='caption'):
        base_url = "https://cc.unext.jp/"
        params = {
            "operationName": "cosmo_getPlaylistUrl",
            "variables": json.dumps({
                "code": episode_id,
                "playMode": play_mode,
                "bitrateLow": 1500,
                "bitrateHigh": None,
                "validationOnly": False
            }, separators=(',', ':')),
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "a2309e22a6819ff747cf9a389dd78db35fa3c386fac1d53461061ba20fa44e34"
                }
            }, separators=(',', ':'))
        }

        encoded_url = base_url + "?" + urlencode(params)
        try:
            response = self.session.get(encoded_url)
            response.raise_for_status()
            content = response.json()
            data = content['data']['webfront_playlistUrl']
            self.play_token = data['playToken']
            profiles = data['urlInfo'][0]['movieProfile']
            for profile in profiles:
                if profile['type'] == 'DASH':
                    mpd_url = profile['playlistUrl'] + f"&play_token={self.play_token}"
                    return mpd_url
        except Exception as e:
            logger.info(f"get mpd url failed: {e}")
            raise(Exception("get mpd url error"))
        
        return None
    
    def _parse_mpd(self, url): 
        try:
            response = self.session.get(url)
            response.raise_for_status()
            root = ET.fromstring(response.text)

            ns = {
                'ns': 'urn:mpeg:dash:schema:mpd:2011',
                'cenc': 'urn:mpeg:cenc:2013'
            }

            # === 1. 获取最高分辨率的视频 BaseURL 和 pssh ===
            max_height = -1
            resoliton_map = {}
            cur_res_height = None
            if self.metadata is not None and 'resolution' in self.metadata:
                cur_res_height = int(self.metadata['resolution'].split('x')[-1])

            for adaptation_set in root.findall('.//ns:AdaptationSet[@contentType="video"]', ns):
                pssh_elements = adaptation_set.findall('.//cenc:pssh', ns)
                self.video_pssh = pssh_elements[-1].text if pssh_elements else None

                if cur_res_height is not None:
                    for rep in adaptation_set.findall('ns:Representation', ns):
                        height = int(rep.attrib.get('height', 0))
                        
                        if cur_res_height == height:
                            self.video_url = rep.find('ns:BaseURL', ns).text #获取最后一个相同分辨率的url
                    
                        width = int(rep.attrib.get('width', 0))
                        if width > 0 and height > 0:
                            resoliton = f"{width}x{height}"
                            resoliton_map[resoliton] = True #去除重复

                if self.video_url is None:
                    # 如果没有设置分辨率则读取最高分辨率
                    for rep in adaptation_set.findall('ns:Representation', ns):
                        height = int(rep.attrib.get('height', 0))
                        
                        if height > max_height:
                            max_height = height
                            self.video_url = rep.find('ns:BaseURL', ns).text
                    
                        width = int(rep.attrib.get('width', 0))
                        if width > 0 and height > 0:
                            resoliton = f"{width}x{height}"
                            resoliton_map[resoliton] = True #去除重复
                
            self.resolution_list = list(resoliton_map.keys())
            if len(self.resolution_list) > 0:
                # 排序分辨率，按高度从大到小
                self.resolution_list.sort(key=lambda res: int(res.split('x')[1]), reverse=True)
            
            # === 2. 获取音频的 pssh 和 BaseURL（优先 mp4a，次选第一个）===
            audio_sets = root.findall('.//ns:AdaptationSet[@contentType="audio"]', ns)

            found = False
            for adaptation_set in audio_sets:
                for rep in adaptation_set.findall('ns:Representation', ns):
                    if "mp4a" in rep.attrib.get('codecs', ''):
                        base_url_element = rep.find('ns:BaseURL', ns)
                        if base_url_element is not None:
                            self.audio_url = base_url_element.text
                            # 遍历 ContentProtection，取最后一个 cenc:pssh
                            pssh_text = None
                            for cp in adaptation_set.findall('ns:ContentProtection', ns):
                                pssh = cp.find('cenc:pssh', ns)
                                if pssh is not None:
                                    pssh_text = pssh.text
                            self.audio_pssh = pssh_text
                            found = True
                            break
                if found:
                    break

            # 如果没有 mp4a，就取第一个 AdaptationSet 的 pssh 和 BaseURL
            if not found and audio_sets:
                first_audio = audio_sets[0]
                rep = first_audio.find('ns:Representation', ns)
                base_url_element = rep.find('ns:BaseURL', ns) if rep is not None else None
                self.audio_url = base_url_element.text if base_url_element is not None else None

                pssh_text = None
                for cp in first_audio.findall('ns:ContentProtection', ns):
                    pssh = cp.find('cenc:pssh', ns)
                    if pssh is not None:
                        pssh_text = pssh.text
                self.audio_pssh = pssh_text

        except Exception as e:
            logger.info(f"parse mpd failed: {e}")
            raise Exception("parse mpd error")

    
    def _get_license(self, data):
        response = self.session.post(
            url=f'https://wvproxy.unext.jp/proxy?play_token={self.play_token}',
            data=data,
            proxies=self.proxies
        )
        return response.content
    
    def _get_decryption_key(self, pssh, index):
        # print(f'[get_decryption_key] pssh: {pssh}')
        cdm = Cdm.from_device(create_cmd_device())
        cdm_session = cdm.open()
        cert = self._get_license(bytes.fromhex('08 04'))
        cdm.set_service_certificate(cdm_session, cert)
        challenge = cdm.get_license_challenge(cdm_session, PSSH(pssh))
        license = self._get_license(challenge)
        cdm.parse_license(cdm_session, license)
        keys = cdm.get_keys(cdm_session)
        content_keys = []
        # print(f"keys: {keys}")
        for i in keys:
            if i.type == "CONTENT":
                key = f'{i.kid.hex}:{i.key.hex()}'
                content_keys.append(key)
                # print(f'key={key}')
        
        if index < len(content_keys):
            return content_keys[index]

        return None
    
    def _decrypt(self, decryption_key, encrypted_location, decrypted_location):
        subprocess.run([
            os.path.join(self.params['ffmpeg_location'], 'itg-key'),
            encrypted_location,
            "--key",
            decryption_key,
            decrypted_location
        ])

    def _merge_audio_video(self, audio, video, output):
        command = [
            os.path.join(self.params['ffmpeg_location'], 'ffmpeg'),
            '-i', audio,
            '-i', video,
            '-acodec', 'copy',
            '-vcodec', 'copy',
            '-strict', '-2',
            '-y',
            output
        ]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            duration_ms = None
            ftr = [3600, 60, 1]
            for line in TextIOWrapper(p.stderr, encoding="utf-8"):
                if line.find('Duration:') != -1:
                    timestr = line.strip().split(',')[0][10:]
                    duration_ms = sum([a*b for a, b in zip(ftr, map(float, timestr.split(':')))])
                if line.startswith('frame') or line.startswith('size'):
                    arr = line.split(' ')
                    for item in arr:
                        if item.startswith('time'):
                            timestr = item.split('=')[1]
                            second = sum([a*b for a, b in zip(ftr, map(float, timestr.split(':')))])
                            progress = second / duration_ms
                            resp = {
                                'type': MsgType.fixing.value,
                                'msg': {
                                    'pid': str(p.pid),
                                    'progress': str('{0:.3f}'.format(progress))
                                },
                            }
                            flush_print(json.dumps(resp))
                else:
                    logger.info('ffmpeg output: ' + line)
        except Exception as e:
            logger.info('ffmpeg progress output exception')

        p.wait()
    
    def _download(self, url, output):
        ydl_opts = {
            'cachedir': False,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'playliststart': 1,
            'playlistend': 1,
            'retries': 3,
            'ffmpeg_location': self.params['ffmpeg_location'],
            'outtmpl': output,
        }

        if 'proxy' in self.params and self.params['proxy'] is not None:
            proxy = self.params['proxy']
            if 'host' in proxy and proxy['host']:
                if proxy['password'] != '':
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"    
        
        with YoutubeDL(ydl_opts) as ydl:
            if self.progress_hook is not None:
                ydl.add_progress_hook(self.progress_hook)
            ydl.download(url)