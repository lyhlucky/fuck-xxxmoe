# coding: utf8

import yt_dlp as youtube_dl
from yt_dlp.downloader import get_suitable_downloader
import json
import logging
import os
import requests
import re
from urllib.parse import urlparse, parse_qs, quote, unquote
from time import time
import ntpath
from hashlib import md5
import common
from common import MsgType, flush_print, sanitize_title, sanitize_filename
import youtube_tools
import spotify_tools
from you_get.common import any_download as you_get_any_download
import traceback
import sys
from metadata_extractor import MetadataExtractor
import base64
from threading import Timer
import urllib
from myget import MyGetProxy
from my_get.spotify.spotify import SpotifyAdaptor


logger = logging.getLogger('downloader')

gLiveProgress = 0

class RepeatingTimer(Timer):
    def run(self):
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


class Downloader():
    def __init__(self, params):
        self._check_params(params)

        flush_print(json.dumps({
            'type': MsgType.param.value,
            'msg': {
                'ret_code': '0',
            }
        }))

        self.params = params
        self._adjust_params()

        self.proxies = None
        self._update_proxies()

        self.ie_result = {}
        self.total_filesize = 52428800
        self.downloaded_filesize = 0
        self.total_filecount = 1
        self.downloaded_filecount = 0
        self.pre_filesize = 0
        self.playlist_name = None
        self.playlist_index = None
        self.playlist_ext = None
        self.filetype = ''
        self.info = {}
        self.prepare_filepath = ''
        self.hook_filepath = ''
        self.final_formats = {'format': '', 'vcodec': '', 'acodec': ''}
        self.downloaded_filepath = None
        self.converted_filepath = None
        self.sub_exist = False
        self.sub_path = ''
        self.audio_bit_rate = ''
        self.is_writeautomaticsub = True

        self.cookies = ['']

        # real meta for spotify
        self.real_title = None
        self.real_thumbnail = None
        self.real_artist = None
        self.real_album = None
        self.real_date = None

        self.you_get_data = None

        self.is_live = False
        self.live_progress_timer = None

        self.is_youtube = False
        self.is_vimeo = False
        self.is_spotify = False
        self.is_bilibili = False
        self.is_tiktok = False

        custom_params = ['itdl_pname', 'itdl_pindex', 'itdl_ptotal', 'itdl_title',
                         'itdl_ext', 'itdl_thumbnail', 'media_title', 'itdl_from']
        self.original_url = unquote(common.remove_query_param(params['url'], custom_params))

        if re.search('www.youtube.com|m.youtube.com|youtu.be|youtube.com|gaanavideo', self.original_url):
            self.is_youtube = True
        elif re.search('www.vimeo.com|vimeo.com', self.original_url):
            self.is_vimeo = True
        elif re.search('spotify.com', self.original_url):
            self.is_spotify = True
        elif re.search('bilibili.com', self.original_url):
            self.is_bilibili = True
        elif re.search('tiktok.com', self.original_url):
            self.is_tiktok = True

        if re.search('soundcloud.com|freesound.org|bandcamp.com|mixcloud.com|spotify.com', self.original_url):
            self.params['media_type'] = 'audio'

        # resolve youtube music url
        if re.search('music.youtube.com', self.original_url):
            params['url'] = params['url'].replace('music.', '')

        self.analysis_cache = os.path.join(
            params['save_path'], 'analysis_cache.json')

        self.ytdl_extract_succeed = False

        self.cookiefile = ''
        if 'cookiefile' in self.params:
            self.cookiefile = self.params['cookiefile']
            
        self.media_title = None 
        self.playlist_name = None
        self.playlist_index = None
        self.playlist_total = None
        self.playlist_title = None
        self.playlist_ext = None
        self.playlist_thumbnail = None
        parsed = urlparse(params['url'])
        qs = parse_qs(parsed.query)
        if 'itdl_pname' in qs:
            self.playlist_name = qs['itdl_pname'][0]
        if 'itdl_pindex' in qs:
            self.playlist_index = qs['itdl_pindex'][0]
        if 'itdl_ptotal' in qs:
            self.playlist_total = qs['itdl_ptotal'][0]
        if 'itdl_title' in qs:
            self.playlist_title = qs['itdl_title'][0]
        if 'itdl_ext' in qs:
            self.playlist_ext = qs['itdl_ext'][0]
        if 'itdl_thumbnail' in qs:
            self.playlist_thumbnail = qs['itdl_thumbnail'][0]

            # remove itdl params
            if params['url'].find('&itdl_pname') != -1:
                params['url'] = params['url'][:params['url'].find('&itdl_pname')]
            if params['url'].find('?itdl_pname') != -1:
                params['url'] = params['url'][:params['url'].find('?itdl_pname')]

        if 'media_title' in qs:
            self.media_title = qs['media_title'][0]
            if params['url'].find('&media_title') != -1:
                params['url'] = params['url'][:params['url'].find('&media_title')]
            if params['url'].find('?media_title') != -1:
                params['url'] = params['url'][:params['url'].find('?media_title')]

        if 'playlist_total' in self.params:
            self.playlist_total = self.params['playlist_total']
        
        if 'playlist_index' in self.params:
            self.playlist_index = self.params['playlist_index']

        # reverse index
        if self.params['playlist_reverse_index'] == 'true' and self.playlist_total and self.playlist_index:
            # padding_len = len(self.playlist_total)
            # reverse_index = int(self.playlist_total) - int(self.playlist_index) + 1
            # self.playlist_index = str(reverse_index).zfill(padding_len)
            reverse_index = int(self.playlist_total) - int(self.playlist_index) + 1
            self.playlist_index = str(reverse_index).zfill(2)
            self.params['playlist_index'] = self.playlist_index

        # for bilibili
        self.p = None
        if self.is_bilibili:
            if 'p' in qs:
                self.p = qs['p'][0]
            self.params['add_playlist_index'] = 'false'

        logger.info('init succeed by params: ' + json.dumps(self.params))

    def process(self):
        logger.info('start processing')
        if self.playlist_title and self.playlist_ext:
            logger.info('direct download file')
            return self._direct_download()

        if self.media_title:
            logger.info('download media file')
            return self._direct_downloadMedia()

        if self.params['device'] != 'android' and self.params['read_cookie'] == 'true':
            self._load_cookie()

        if 'playlist' in self.params and self.params['playlist'] == 'true':
            return self._extract_playlist()
        
        if self.is_spotify:
            # From Spotify
            # if 'authorization' in self.params:
            if 'sessdata' in self.params:
                spotify_ap = SpotifyAdaptor(self.params, proxies=self.proxies, progress_hook=self._hook)
                spotify_ap.extract()
                self.downloaded_filepath = spotify_ap.final_location
                self.audio_bit_rate = spotify_ap.audio_bit_rate
                self.sub_path = spotify_ap.lrc_path
                return
            else:
                # From Youtube
                logger.info('start get youtube url from spotify')
                ret = youtube_tools.match_video_and_metadata(self.params['url'], proxies=self.proxies)
                self.params['url'] = ret['url']
                if ret['title']:
                    self.real_title = ret['title']
                    if self.params['add_playlist_index'] == 'true':
                        self.real_title = f'{self.playlist_index}.{self.real_title}'
                if ret['thumbnail']:
                    self.real_thumbnail = ret['thumbnail']
                if ret['artist']:
                    self.real_artist = ret['artist']
                if ret['album']:
                    self.real_album = ret['album']
                if ret['date']:
                    self.real_date = ret['date']
                self.is_youtube = True
                logger.info('get youtube url from spotify succeed, youtube url: ' + self.params['url'])
        
        mgp = MyGetProxy(url=self.original_url, params=self.params, proxies=self.proxies, progress_hook=self._hook)
        if mgp.extract():
            self.downloaded_filepath = mgp.downloaded_filepath
            self.audio_bit_rate = mgp.audio_bit_rate
            self.sub_path = mgp.sub_path
            return
        
        # extract info
        metadata_extract_succeed = False
        if 'metadata' in self.params and len(self.params['metadata']) > 48:
            try:
                extractor = MetadataExtractor(self.params['url'], self.params['metadata'])
                self.ie_result = extractor.process()
                # prepare filename
                # ydl_opts = self._setup_ydl_opts(True) 
                # self.prepare_filepath = youtube_dl.YoutubeDL(ydl_opts).prepare_filename(self.ie_result)
                metadata_extract_succeed = True
                self.ytdl_extract_succeed = True
                logger.info('browser metadata extract succeed')
            except Exception as e:
                metadata_extract_succeed = False

        if not metadata_extract_succeed:
            self.ytdl_extract_succeed = False
            try:
                self._ytdl_extract_info()
                self.ytdl_extract_succeed = True
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.info('ytdl extract failed, try youget extract info')
                if self.is_vimeo:
                    url = self.params['url']
                    self.params['url'] = url.replace('https', 'http')
                    self._ytdl_extract_info()
                    self.ytdl_extract_succeed = True
                else:
                    # self._youget_ectract_info()
                    raise Exception("extract info error")

        if 'is_live' in self.ie_result and self.ie_result['is_live']:
            self.is_live = True
        
        # 限制文件名长度
        title = self.ie_result['title']
        self.ie_result['title'] = self._ensure_title_length(title, self.params["save_path"])

        # prepare filename
        ydl_opts = self._setup_ydl_opts(True)
        self.prepare_filepath = youtube_dl.YoutubeDL(ydl_opts).prepare_filename(self.ie_result)

        # download thumbnail
        self.ie_result['local_thumbnail'] = os.path.join(
            self.params['save_path'], f"{md5(self.params['url'].encode('utf-8')).hexdigest()}.jpg")
        if not os.path.exists(self.ie_result['local_thumbnail']):
            try:
                if self.real_thumbnail:
                    self.ie_result['thumbnail'] = self.real_thumbnail

                self._download_file(self.ie_result['thumbnail'], self.ie_result['local_thumbnail'])
            except Exception as e:
                self.ie_result['local_thumbnail'] = ''

        # print extract info
        self._print_basic_info()

        if 'sniff_only' in self.params and self.params['sniff_only'] == 'true':
            return

        # process download
        logger.info('start downloading video')
        resp = {
            'type': MsgType.downloading.value,
            'msg': {
                'progress': '0',
                'speed': '0KB/s',
                'filesize': '0',
                'eta': '0',
            },
        }
        flush_print(json.dumps(resp))

        # send live progress
        if self.is_live:
            def updateProgress():
                global gLiveProgress
                gLiveProgress += 1

                flush_print(json.dumps({
                    'type': MsgType.downloading.value,
                    'msg': {
                        'progress': str(gLiveProgress)
                    },
                }))

            self.live_progress_timer = RepeatingTimer(1.0, updateProgress)
            self.live_progress_timer.start()

        # try youtube-dl download
        youtube_dl_failed = True
        attempts = 0
        max_retries = 2
        
        while attempts < max_retries:
            if self.ytdl_extract_succeed:
                for index, cookie in enumerate(self.cookies, start=1):
                    if cookie != '':
                        self._write_cookiefile(cookie)
                    try:
                        attempts += 1
                        ydl_opts = self._setup_ydl_opts(False)
                        youtube_dl.YoutubeDL(ydl_opts).process_ie_result(self.ie_result)
                        youtube_dl_failed = False

                        # set downloaded filepath
                        logger.info('start set download filepath')
                        self._set_downloaded_filepath()
                        logger.info('set download filepath succeed')
                        attempts = max_retries
                        break
                    except Exception as e:
                        self.is_writeautomaticsub = False

                        # bilibili 4k merge
                        if self.is_bilibili and len(e.args) == 1 and str(e.args[0]).find('Stream #1:0 -> #0:1 (copy)') != -1:
                            self._merge_Bilibili_4k_video()
                            youtube_dl_failed = False
                            break
                        else:
                            # 可能是标题存在非法字符
                            title = self.ie_result['title']
                            self.ie_result['title'] = self._ensure_title_length(title, self.params["save_path"], True)

                            if cookie != '':
                                logger.info('download by ' + cookie['browser'] + ' cookie failed')
                            if index != len(self.cookies):
                                continue
                            else:
                                logger.error(traceback.format_exc())

        #try you-get while youtube-dl failed
        # if youtube_dl_failed:
        #     self._try_you_get()
        #     if self.params['add_playlist_index'] == 'true' and self.playlist_index:
        #         basename = os.path.basename(self.downloaded_filepath)
        #         adjust_path = os.path.join(os.path.dirname(self.downloaded_filepath), f"{self.playlist_index}.{basename}")
        #         os.replace(self.downloaded_filepath, adjust_path)
        #         self.downloaded_filepath = adjust_path

        # set subtitle filepath
        logger.info('start set subtitle filepath')
        self._set_subtitle_filepath()
        logger.info('set download subtitle succeed')

        logger.info('download video succeed')

    def stopLiveProgressTimer(self):
        if self.live_progress_timer is not None:
            self.live_progress_timer.cancel()

    def _update_proxies(self):
        if 'proxy' in self.params:
            proxy = self.params['proxy']
            if proxy is not None and 'host' in proxy and proxy['host']:
                if proxy['password'] != '':
                    usr_proxies = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    usr_proxies = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
                if 'http' in usr_proxies:
                    self.proxies = {'http': usr_proxies, 'https': usr_proxies}

        if self.proxies is None:
            # Get system proxy
            sys_proxies = urllib.request.getproxies()
            if 'http' in sys_proxies:
                sys_proxies['https'] = sys_proxies['http']
                self.proxies = sys_proxies

    def _direct_download(self):
        title = self.playlist_title
        if self.params['add_playlist_index'] == 'true' and self.playlist_index:
            title = f"{self.playlist_index}.{title}"
        thumbnail = ''
        if self.playlist_thumbnail:
            thumbnail = self.playlist_thumbnail

        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': thumbnail,
                'local_thumbnail': '',
                'duration': '0',
            }
        }))

        info = {
            'url': self.original_url,
        }
        if 'metadata' in self.params:
            metadata = self.params['metadata']
            if len(metadata) > 48:
                metadata = json.loads(base64.b64decode(metadata))
                if 'http_headers' in metadata:
                    http_headers = metadata['http_headers']
                    for key in list(http_headers):
                        if http_headers[key] == None:
                            del http_headers[key]

                    info['http_headers'] = http_headers    

        save_path = self.params["save_path"]
        self.prepare_filepath = f'{save_path}/{self._ensure_title_length(title, save_path)}.{self.playlist_ext}'

        attempts = 0
        max_retries = 2
        while attempts <max_retries:
            try:
                attempts += 1
                downloader = get_suitable_downloader(info)
                ydl_opts = self._setup_ydl_opts(False)
                ydl = youtube_dl.YoutubeDL(ydl_opts)
                fd = downloader(ydl, ydl_opts)
                fd.add_progress_hook(self._hook)
                fd.download(self.prepare_filepath, info)
                logger.info('download video succeed')
                self._set_downloaded_filepath()
                break
            except Exception as e:
                self.prepare_filepath = f'{save_path}/{self._ensure_title_length(title, save_path,True)}.{self.playlist_ext}'
                if attempts == 2:
                    logger.error(traceback.format_exc())

    def _direct_downloadMedia(self):
        # 下载m3u8
        thumbnail = ''
        if self.playlist_thumbnail:
            thumbnail = self.playlist_thumbnail

        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': self.media_title,
                'thumbnail': thumbnail,
                'local_thumbnail': '',
                'duration': '0',
            }
        }))

        save_path = self.params["save_path"]
        self.prepare_filepath = f'{save_path}/{self._ensure_title_length(self.media_title, save_path)}.mp4'
        ydl_opts = self._setup_ydl_opts(False)
        ydl_opts.update({
            'outtmpl': self.prepare_filepath
        })

        if 'metadata' in self.params:
            metadata = self.params['metadata']
            if len(metadata) > 48:
                metadata = json.loads(base64.b64decode(metadata))
                if 'http_headers' in metadata:
                    http_headers = metadata['http_headers']
                    for key in list(http_headers):
                        if http_headers[key] == None:
                            del http_headers[key]

                    ydl_opts.update({'http_headers': http_headers})

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(self.original_url)

        self._set_downloaded_filepath()
    
    def _ytdl_extract_info(self):
        def extract():
            for index, cookie in enumerate(self.cookies, start=1):
                if cookie != '':
                    self._write_cookiefile(cookie)

                try:
                    ydl_opts = self._setup_ydl_opts(True)
                    self.ie_result = youtube_dl.YoutubeDL(ydl_opts).extract_info(self.params['url'])
                    break
                except Exception as e:
                    if cookie != '':
                        logger.info('extract by ' + cookie['browser'] + ' cookie failed')

                    if index != len(self.cookies):
                        continue
                    else:
                        raise e

        logger.info('start extracting video')
        extract()
        logger.info('extract video succeed')

    def _youget_ectract_info(self):
        you_get_any_download(
            self.params['url'],
            output_dir=self.params['save_path'],
            merge=True,
            json_output=True,
            info_only=True,
            ffmpeg_location=self.params['ffmpeg_location'],
            progress_hook=self._you_get_hook
        )

        self.ie_result['title'] = self.you_get_data['title']

    def _try_you_get(self):
        logger.info('try you-get to download video')
        stream_id = -1
        if not self.is_tiktok:
            you_get_any_download(
                self.params['url'],
                output_dir=self.params['save_path'],
                merge=True,
                json_output=True,
                info_only=True,
                ffmpeg_location=self.params['ffmpeg_location'],
                progress_hook=self._you_get_hook
            )

            if self.you_get_data and 'streams' in self.you_get_data:
                stream_id = self._find_you_get_stream()

        if stream_id != -1:
            you_get_any_download(
                self.params['url'],
                output_dir=self.params['save_path'],
                merge=True,
                stream_id=stream_id,
                ffmpeg_location=self.params['ffmpeg_location'],
                progress_hook=self._you_get_hook
            )
        else:
            you_get_any_download(
                self.params['url'],
                output_dir=self.params['save_path'],
                merge=True,
                ffmpeg_location=self.params['ffmpeg_location'],
                progress_hook=self._you_get_hook
            )

    def _find_you_get_stream(self):
        other_stream_id = -1
        mp4_stream_id = -1

        stream_id = -1
        streams = self.you_get_data['streams']
        other_max = 0
        mp4_max = 0
        min = sys.maxsize

        for id, value in streams.items():
            if not 'size' in value:
                continue

            if self.params['media_type'] == 'video':
                # discards 60fps
                if value['quality'].find('p60') != -1:
                    continue

                if value['container'] != 'mp4':
                    if self.params['video_quality'].upper() != 'BEST' and \
                            value['quality'].find(self.params['video_quality'].lower()) != -1:
                        other_stream_id = id

                    if self.params['video_quality'].upper() == 'BEST':
                        if value['size'] > other_max:
                            other_max = value['size']
                            other_stream_id = id

                if value['container'] == 'mp4':
                    if self.params['video_quality'].upper() != 'BEST' and \
                            value['quality'].find(self.params['video_quality'].lower()) != -1:
                        mp4_stream_id = id
                        break

                    if self.params['video_quality'].upper() == 'BEST':
                        if value['size'] > mp4_max:
                            mp4_max = value['size']
                            mp4_stream_id = id

            if self.params['media_type'] == 'audio':
                if value['size'] < min:
                    min = value['size']
                    stream_id = id

        if other_stream_id != -1:
            stream_id = other_stream_id
        if mp4_stream_id != -1:
            stream_id = mp4_stream_id

        if other_stream_id != -1 and mp4_stream_id != -1:
            stream_id = other_stream_id if other_max > mp4_max else mp4_stream_id

        return stream_id

    def adjust_playlist_filepath(self, filepath):
        if self.playlist_name and self.playlist_index:
            playlist_dir = os.path.join(
                ntpath.dirname(filepath), self.playlist_name)
            if not os.path.exists(playlist_dir):
                try:
                    os.mkdir(playlist_dir)
                except:
                    os.mkdir(sanitize_title(playlist_dir))

            dst = os.path.join(playlist_dir, ntpath.basename(filepath))
            if len(dst) >= 200:
                dst = dst[0:190]
                file_suffix = os.path.splitext(filepath)[-1]
                dst = dst + file_suffix
            os.rename(filepath, dst)
            filepath = dst

            if self.sub_exist:
                dst_sub = os.path.join(playlist_dir, ntpath.basename(self.sub_path))
                if len(dst_sub) >= 200:
                    dst_sub = dst_sub[0:190]
                    file_suffix = os.path.splitext(self.sub_path)[-1]
                    dst_sub = dst_sub + file_suffix
                
                os.rename(self.sub_path, dst_sub)
                self.sub_path = dst_sub

        return filepath

    def get_id3_info(self):
        id3_info = {}

        # return empty object while ytdl extract failed
        if not self.ytdl_extract_succeed:
            return id3_info

        if os.path.exists(self.ie_result['local_thumbnail']):
            id3_info['cover'] = self.ie_result['local_thumbnail']
        if 'album' in self.ie_result and self.ie_result['album']:
            id3_info['album'] = self.ie_result['album']
        if self.real_album:
            id3_info['album'] = self.real_album
        if 'artist' in self.ie_result and self.ie_result['artist']:
            id3_info['artist'] = self.ie_result['artist']
        if self.real_artist:
            id3_info['artist'] = self.real_artist
        if 'title' in self.ie_result and self.ie_result['title']:
            id3_info['title'] = self.ie_result['title']
        if self.real_title:
            id3_info['title'] = self.real_title
        if 'upload_date' in self.ie_result and self.ie_result['upload_date']:
            id3_info['date'] = self.ie_result['upload_date']
        if self.real_date:
            id3_info['date'] = self.real_date

        return id3_info

    def get_downloaded_filepath(self):
        if self.real_title:
            dst_name = common.sanitize_filename(self.real_title)
            self.downloaded_filepath = self._rename_filepath(self.downloaded_filepath, dst_name)
        return self.downloaded_filepath

    def get_subtitle_filepath(self):
        if self.real_title and os.path.exists(self.sub_path):
            dst_name = common.sanitize_filename(self.real_title)
            self.sub_path = self._rename_filepath(self.sub_path, dst_name)
        return self.sub_path

    def _load_cookie(self):
        logger.info('start load cookies')
        # from browsercookie import load_cookies
        # parsed_uri = urlparse(self.params['url'])
        # domain = parsed_uri.netloc
        # if domain.startswith('www.'):
        #     domain = domain[4:]
        # if domain.find('youtu.be') != -1:
        #     domain += ';youtube.com'
        # if domain.find('spotify.com') != -1:
        #     domain += ';youtube.com'
        # self.cookies += load_cookies(domain)
        # logger.info('load cookies finished')

    def _rename_filepath(self, filepath, dst_name):
        dst_filename = dst_name + filepath[filepath.rfind('.'):]
        dst_filepath = os.path.join(os.path.dirname(filepath), dst_filename)
        os.replace(filepath, dst_filepath)
        return dst_filepath

    def _write_cookiefile(self, data):
        # try to write cookie to log_path
        cookiedirs = [self.params['save_path'], self.params['log_path']]
        for index, cookiedir in enumerate(cookiedirs, start=1):
            try:
                if index == 1:
                    self.cookiefile = os.path.join(cookiedir, data['browser'] + '.txt')
                else:
                    self.cookiefile = os.path.join(cookiedir, f'dl.{int(time()*1000)}.log')

                logger.info('write ' + data['browser'] + ' cookie to file: ' + self.cookiefile)
                f = open(self.cookiefile, 'w')
                f.write(data['cookie'])
                f.close()
                logger.info(data['browser'] + ' cookie wirte to file succeed')
                break
            except Exception as e:
                continue

    def _adjust_params(self):
        if not 'ffmpeg_location' in self.params:
            self.params['ffmpeg_location'] = ''
        if not 'save_path' in self.params:
            self.params['save_path'] = os.path.dirname(self.params['params_filepath'])
        if not 'media_type' in self.params:
            self.params['media_type'] = 'video'
        if not 'video_quality' in self.params:
            self.params['video_quality'] = '480P'
        if not 'audio_quality' in self.params:
            self.params['audio_quality'] = '128Kb/s'
        if not 'device' in self.params:
            self.params['device'] = 'pc'
        if not 'save_id3' in self.params:
            self.params['save_id3'] = 'false'
        if not 'proxy' in self.params:
            self.params['proxy'] = None
        if not 'ratelimit' in self.params:
            self.params['ratelimit'] = ''
        if not 'subtitle' in self.params:
            self.params['subtitle'] = ''
        if not 'nocheckcertificate' in self.params:
            self.params['nocheckcertificate'] = 'false'
        if not 'read_cookie' in self.params:
            self.params['read_cookie'] = 'true'
        if not 'add_playlist_index' in self.params:
            self.params['add_playlist_index'] = 'false'
        if not 'playlist_reverse_index' in self.params:
            self.params['playlist_reverse_index'] = 'false'
        if 'lyric' in self.params:
            self.params['subtitle'] = self.params['lyric']
        if not 'print_formats' in self.params:
            self.params['print_formats'] = 'false'

    def _check_params(self, params):
        if not 'url' in params:
            raise Exception('url not in params')

    def _print_basic_info(self):
        duration = 0
        if 'duration' in self.ie_result:
            duration = self.ie_result['duration']

        title = self.ie_result['title']

        thumbnail = ''
        if self.playlist_thumbnail:
            thumbnail = self.playlist_thumbnail

        info = {
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': thumbnail,
                'local_thumbnail': '',
                'duration': duration,
                'is_live': self.is_live
            }
        }

        if self.is_bilibili and self.p:
            info['msg']['title'] = info['msg']['title'] + ' - ' + self.p

        if 'thumbnail' in self.ie_result:
            info['msg']['thumbnail'] = self.ie_result['thumbnail']

        if 'local_thumbnail' in self.ie_result:
            info['msg']['local_thumbnail'] = self.ie_result['local_thumbnail']

        if self.params['add_playlist_index'] == 'true' and self.playlist_index:
            info['msg']['title'] = f"{self.playlist_index}.{info['msg']['title']}"

        if self.real_title:
            info['msg']['title'] = self.real_title

        prepare_filepath = self.prepare_filepath
        if self.is_youtube:
            if self.params['media_type'] == 'audio':
                prepare_filepath = prepare_filepath[0:prepare_filepath.rfind('.')] + '.mp3'
            else:
                prepare_filepath = prepare_filepath[0:prepare_filepath.rfind('.')] + '.mp4'
        info['msg']['filepath'] = prepare_filepath

        if self.params['print_formats'] == 'true':
            info['msg']['formats'] = self.ie_result['formats']

        flush_print(json.dumps(info))

    def _setup_ydl_opts(self, sniff_only):
        if sniff_only:
            ydl_opts = {
                'cachedir': False,
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'playliststart': 1,
                'playlistend': 1,
                'retries': 3,
                'writethumbnail': False,
                'outtmpl': os.path.join(self.params['save_path'], '%(title)s.%(ext)s'),
            }
        else:
            ydl_opts = {
                'cachedir': False,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'playliststart': 1,
                'playlistend': 1,
                'retries': 3,
                'ffmpeg_location': self.params['ffmpeg_location'],
                'progress_hooks': [self._hook],
                'outtmpl': os.path.join(self.params['save_path'], '%(title)s.%(ext)s'),
            }

            if self.is_youtube:
                self._find_youtube_formats()
                ydl_opts['format'] = self.final_formats['format']
                self.ie_result['format_id'] = self.final_formats['format']
                self.ie_result['requested_formats'] = None

            if self.is_vimeo:
                self._find_vimeo_formats()
                if self.final_formats['format'] != None:
                    ydl_opts['format'] = self.final_formats['format']
                    self.ie_result['format_id'] = self.final_formats['format']
                    self.ie_result['requested_formats'] = None

            # 2024-4-23 尝试添加-f 0下载tiktok无水印视频，https://github.com/yt-dlp/yt-dlp/issues/9506
            # if self.is_tiktok:
            #     ydl_opts['format'] = '0'

            if self.params['ratelimit'] != '':
                ydl_opts['ratelimit'] = float(self.params['ratelimit'])

            if self.is_live:
                ydl_opts['external_downloader'] = 'ffmpeg'
                ydl_opts['hls_use_mpegts'] = True

        if self.params['subtitle'] != '':
            # if self.is_writeautomaticsub:
            #     ydl_opts['writeautomaticsub'] = True
            # else:
            #     ydl_opts['writesubtitles'] = True
            ydl_opts['writesubtitles'] = True
            # YouTube 自动字幕
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitlesformat'] = 'srt'
            # 加上.*会下载所有自动字幕
            # self.params['subtitle'] += ".*"
            ydl_opts['subtitleslangs'] = self.params['subtitle'].split(',')

        if self.params['device'] == 'android':
            ydl_opts['outtmpl'] = os.path.join(
                self.params['save_path'], '%(title).90s.%(ext)s')

        if self.params['nocheckcertificate'] == 'true':
            # ydl_opts['nocheckcertificate'] = 'true'
            ydl_opts['nocheckcertificate'] = True

        if os.path.exists(self.cookiefile):
            ydl_opts['cookiefile'] = self.cookiefile

        if self.params['proxy']:
            proxy = self.params['proxy']
            if 'host' in proxy and proxy['host']:
                if proxy['password'] != '':
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"

        return ydl_opts

    def _find_youtube_formats(self):

        def find_best_audio(acodec=None):
            # sorted_formats = sorted(
            #     self.ie_result['formats'], key=lambda format: int(format['abr']) if 'abr' in format and format['abr'] != None else 0, reverse=True)

            # 先按 abr 降序排序，再按 language_preference 降序排序
            sorted_formats = sorted(
                self.ie_result['formats'],
                key=lambda format: (
                    int(format['abr']) if 'abr' in format and format['abr'] is not None else 0,
                    format['language_preference'] if 'language_preference' in format and format['language_preference'] is not None else -1
                ),
                reverse=True
            )
            best_format = None
            # 先找到原始音频
            for format in sorted_formats:
                if 'vcodec' in format and format['vcodec'] != 'none':
                    continue

                best_format = format
                break

            # 匹配用户选择的音频
            if 'audio_language' in self.params and self.params['audio_language'] != 'original':
                for format in sorted_formats:
                    if 'vcodec' in format and format['vcodec'] != 'none':
                        continue

                    if 'language' in format and format['language'] and self.params['audio_language'].lower() in format['language'].lower():
                        best_format = format
                        if acodec != None:
                            if 'acodec' in format and acodec == format['acodec'].split('.')[0]:
                                best_format = format
                                break
                            else:
                                continue
                        else:
                            break
            else:
                for format in sorted_formats:
                    if 'vcodec' in format and format['vcodec'] != 'none':
                        continue

                    if acodec != None:
                        if 'acodec' in format and acodec == format['acodec'].split('.')[0]:
                            best_format = format
                            break
                        else:
                            continue
                    else:
                        break

            return best_format

        if self.params['media_type'] == 'audio':
            audio_format = find_best_audio()

            self.final_formats['format'] = audio_format['format_id']
            self.final_formats['acodec'] = audio_format['acodec']

        elif self.params['media_type'] == 'video':
            if self.params['video_quality'].upper() == 'BEST':
                sorted_formats = sorted(
                    self.ie_result['formats'], key=lambda format: int(format['height']) if 'height' in format and format['height'] != None else 0, reverse=True)
                video_format = sorted_formats[0]
            else:
                sorted_formats = sorted(
                    self.ie_result['formats'], key=lambda format: int(format['height']) if 'height' in format and format['height'] != None else 10000)
                min_gap = 9999
                wanted_height = int(self.params['video_quality'][0:-1])
                for format in sorted_formats:
                    if 'height' in format and format['height'] != None and abs(wanted_height - int(format['height'])) < min_gap:
                        video_format = format
                        min_gap = abs(wanted_height - int(format['height']))

            for format in sorted_formats:
                if 'height' in format and format['height'] == video_format['height'] and format['vcodec'].split('.')[0] == 'avc1':
                    video_format = format

            video_filesize = video_format['filesize'] if 'filesize' in video_format and video_format[
                'filesize'] != None and video_format['filesize'] > 0 else self.total_filesize
            if video_format['acodec'] != 'none':
                self.final_formats['format'] = video_format['format_id']
                audio_format = video_format
                self.total_filesize = video_filesize
            else:
                audio_format = find_best_audio('mp4a')
                audio_filesize = audio_format['filesize'] if 'filesize' in audio_format and audio_format[
                    'filesize'] != None and audio_format['filesize'] > 0 else self.total_filesize
                self.total_filesize = video_filesize + audio_filesize
                self.final_formats['format'] = video_format['format_id'] + \
                    '+' + audio_format['format_id']
                self.total_filecount = 2

            self.final_formats['vcodec'] = video_format['vcodec'].split('.')[0]
            self.final_formats['acodec'] = audio_format['acodec'].split('.')[0]

    def _find_vimeo_formats(self):
        self.final_formats = {'format': None, 'vcodec': None, 'acodec': None}

        max_height = 0
        for format in self.ie_result['formats']:
            result = re.compile(r'http-(\d{1,5})p').search(format['format_id'])
            if hasattr(result, 'group') and int(result.group(1)) > max_height:
                self.final_formats['format'] = format['format_id']
                max_height = int(result.group(1))

    def _download_file(self, url, file_name):
        with open(file_name, "wb") as file:
            response = requests.get(url, proxies=self.proxies)
            file.write(response.content)
            file.close()

    def _set_downloaded_filepath(self):
        file_exists = False
        self.downloaded_filepath = self.prepare_filepath
        if not os.path.exists(self.downloaded_filepath):
            # unknown_video is for tiktok video
            merge_container = ['m4a', 'mkv', 'mp4', 'ogg', 'webm', 'flv', 'unknown_video']
            for item in merge_container:
                tmp_filepath = self.prepare_filepath[0:self.prepare_filepath.rfind('.')] + '.' + item
                if os.path.exists(tmp_filepath):
                    file_exists = True
                    self.downloaded_filepath = tmp_filepath
                    break
            
            # Bilibili下载番剧，文件名前面多了集数，导致查找不到文件
            if not file_exists and self.is_bilibili:
                downloaded_dir = os.path.dirname(self.downloaded_filepath)
                basename = os.path.splitext(os.path.basename(self.downloaded_filepath))[0]
                for item in os.scandir(downloaded_dir):
                    if item.is_file:
                        sufix = os.path.splitext(item.path)[-1][1:]
                        if sufix in merge_container:
                            file_exists = True
                            self.downloaded_filepath = item.path
                            break

        else:
            file_exists = True

        if not file_exists:
            raise Exception('file not exists')

        # adjust for playlist index
        if self.params['add_playlist_index'] == 'true' and self.playlist_index:
            basename = os.path.basename(self.downloaded_filepath)
            adjust_path = os.path.join(os.path.dirname(self.downloaded_filepath), f"{self.playlist_index}.{basename}")
            os.replace(self.downloaded_filepath, adjust_path)
            self.downloaded_filepath = adjust_path

    def _set_subtitle_filepath(self):
        self.sub_path = ''
        if self.params['subtitle'] != '' and self.downloaded_filepath != None:

            video_dir = os.path.dirname(self.downloaded_filepath)
            video_filename = os.path.basename(self.downloaded_filepath)

            files = os.listdir(video_dir)
            for file in files:
                if file.find('vtt') != -1 or file.find('srt') != -1:
                    self.sub_exist = True

                    sub_format = file[file.rfind('.')+1:]
                    self.sub_path = os.path.join(video_dir, file)
                    adjust_path = os.path.join(video_dir, video_filename[0:video_filename.rfind('.') + 1] + sub_format)
                    os.replace(self.sub_path, adjust_path)
                    self.sub_path = adjust_path
                    try:
                        if 'lyric' in self.params:
                            self.sub_path = common.vtt2lrc(adjust_path)
                            os.remove(adjust_path)
                        elif sub_format == 'vtt':
                            # self.sub_path = common.vtt2srt2(adjust_path) #使用这个转换的字幕文件缺少数字编号
                            self.sub_path = common.vtt2srt(adjust_path)
                            os.remove(adjust_path)
                    except Exception as e:
                        logger.error(traceback.format_exc())

                    break

            if not self.sub_exist:
                self.sub_path = ''

    def _you_get_hook(self, d):
        if d['status'] == 'downloading':
            resp = {
                'type': MsgType.downloading.value,
                'msg': {
                    'progress': str('{0:.3f}'.format(d['progress'])),
                    'speed': d['speed'],
                    'filesize': d['filesize'],
                    'eta': d['eta'],
                },
            }
            flush_print(json.dumps(resp))
        if d['status'] == 'finished':
            self.downloaded_filepath = d['filepath']
        if d['status'] == 'info':
            self.you_get_data = d['data']
        if d['status'] == 'playlist':
            self.you_get_videos = d['data']

    def _hook(self, d):
        if 'status' in d and d['status'] == 'downloading':
            if 'filename' in d:
                self.hook_filepath = d['filename']
            if 'total_bytes_estimate' in d:
                self.pre_filesize = d['total_bytes_estimate']
            elif 'total_bytes' in d:
                self.pre_filesize = d['total_bytes']

            if self.total_filecount == 1:
                if 'total_bytes_estimate' in d:
                    self.total_filesize = d['total_bytes_estimate']
                elif 'total_bytes' in d:
                    self.total_filesize = d['total_bytes']

            # Exception: float division by zero
            if self.total_filesize is None or self.total_filesize == 0:
                return

            progress = (d['downloaded_bytes'] +
                        self.downloaded_filesize) / float(self.total_filesize)
            if progress > 1.0:
                self.total_filesize += 10485760
                progress = (d['downloaded_bytes'] + self.downloaded_filesize) / float(self.total_filesize)

            resp = {
                'type': MsgType.downloading.value,
                'msg': {
                    'progress': str('{0:.3f}'.format(progress)),
                    'speed': d['_speed_str'].replace('KiB', 'KB').replace('MiB', 'MB'),
                    'filesize': str(self.total_filesize),
                    'eta': str(d['eta']),
                },
            }
            flush_print(json.dumps(resp))
        elif 'status' in d and d['status'] == 'finished':
            self.downloaded_filecount += 1
            if self.downloaded_filecount != self.total_filecount and self.pre_filesize is not None:
                self.downloaded_filesize += self.pre_filesize
        else:
            resp = {
                'type': MsgType.finished.value,
                'msg': {
                    'ret_code': '1',
                },
            }
            flush_print(json.dumps(resp))

    def _ensure_title_length(self, title, save_path, retry=False):
        if not retry:
            suitable_title = sanitize_filename(unquote(title))
        else:
            suitable_title = sanitize_title(unquote(title))

        file_path = os.path.join(save_path, suitable_title)
        max_path = 180
        if len(file_path) > max_path:
            file_path = file_path[0:max_path]
            suitable_title = os.path.basename(file_path)
        return suitable_title

    def _ytdl_extract_playlist(self):
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }
        
        if self.params['nocheckcertificate'] == 'true':
            ydl_opts['nocheckcertificate'] = 'true'

        if os.path.exists(self.cookiefile):
            ydl_opts['cookiefile'] = self.cookiefile

        if self.params['proxy']:
            proxy = self.params['proxy']
            if 'host' in proxy and proxy['host']:
                if proxy['password'] != '':
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"

        result = youtube_dl.YoutubeDL(ydl_opts).extract_info(self.params['url'])

        playlist_name = result['extractor'] + ':video'
        if 'title' in result:
            # from https://github.com/django/django/blob/master/django/utils/text.py get_valid_filename
            s = result['title']
            s = str(s).strip().replace(' ', '_')
            s = re.sub(r'(?u)[^-\w.]', '', s)
            playlist_name = s
        
        playlist_name = common.sanitize_title(playlist_name)

        padding_len = len(str(len(result['entries'])))
        videos = []
        total = len(result['entries'])
        for index, item in enumerate(result['entries'], start=1):
            if item is None:
                continue

            video = {}
            if self.is_youtube:
                video['url'] = f"https://www.youtube.com/watch?v={item['id']}&itdl_pname={quote(playlist_name)}&itdl_pindex={str(index).zfill(padding_len)}&itdl_ptotal={total}"
            elif 'ext' in item:
                itdl_params = f"itdl_pname={quote(playlist_name)}&itdl_pindex={str(index).zfill(padding_len)}&itdl_ptotal={total}&itdl_title={quote(item['title'])}&itdl_ext={item['ext']}"
                if item['url'].find('?') != -1:
                    video['url'] = f"{item['url']}&{itdl_params}"
                else:
                    video['url'] = f"{item['url']}?{itdl_params}"
            else:
                sep = '?'
                if item['url'].find('?') != -1:
                    sep = '&'
                video['url'] = f"{item['url']}{sep}itdl_pname={quote(playlist_name)}&itdl_pindex={str(index).zfill(padding_len)}&itdl_ptotal={total}"

            if 'title' not in item:
                video['title'] = f"{str(index).zfill(padding_len)}.{playlist_name}"
            else:
                video['title'] = item['title']

            videos.append(video)

        resp = {
            'type': MsgType.playlist.value,
            'msg': {
                'videos': videos
            }
        }
        flush_print(json.dumps(resp))

    def _spotify_extract_playlist(self):
        use_new = True
        # if use_new and 'authorization' in self.params:
        if use_new and 'sessdata' in self.params:
            spotify_ap = SpotifyAdaptor(self.params, proxies=self.proxies)
            spotify_ap.extract_playlist()
        else:
            access_token = None
            if 'authorization' in self.params:
                access_token = f"{base64.b64decode(self.params['authorization']).decode('utf-8')}"

            spotify_tools.init(self.proxies, access_token=access_token)

            videos = []
            if re.search('playlist', self.params['url']):
                videos = spotify_tools.fetch_playlist(self.params['url'])
            if re.search('album', self.params['url']):
                videos = spotify_tools.fetch_album(self.params['url'])
            if re.search('artist', self.params['url']):
                videos = spotify_tools.fetch_artist(self.params['url'])
            if re.search('show', self.params['url']):
                videos = spotify_tools.fetch_show(self.params['url'])

            resp = {
                'type': MsgType.playlist.value,
                'msg': {
                    'videos': videos
                }
            }
            flush_print(json.dumps(resp))

    def _youget_extract_playlist(self):
        you_get_any_download(
            self.params['url'],
            output_dir=self.params['save_path'],
            merge=True,
            json_output=True,
            info_only=True,
            playlist=True,
            ffmpeg_location=self.params['ffmpeg_location'],
            progress_hook=self._you_get_hook
        )

        resp = {
            'type': MsgType.playlist.value,
            'msg': {
                'videos': self.you_get_videos
            }
        }
        flush_print(json.dumps(resp))

    def _extract_playlist(self):
        logger.info('start extracting playlist')
        for index, cookie in enumerate(self.cookies, start=1):
            if cookie != '':
                self._write_cookiefile(cookie)

            try:
                mgp = MyGetProxy(self.original_url, self.params, proxies=self.proxies)
                if mgp.extract_playlist():
                    pass
                else:
                    if self.is_spotify:
                        self._spotify_extract_playlist()
                    else:
                        self._ytdl_extract_playlist()
                break
            except Exception as e:
                logger.error(traceback.format_exc())

                if cookie != '':
                    logger.info('extract by ' + cookie['browser'] + ' cookie failed')

                if index != len(cookie):
                    continue
                else:
                    raise e
        logger.info('extract playlist succeed')

    def _merge_Bilibili_4k_video(self):
        ffmpeg_path = self.params['ffmpeg_location']
        save_path = self.params['save_path']

        video = ''
        audio = ''
        for root,dirs,names in os.walk(save_path):
            for name in names:
                ext = os.path.splitext(name)[1]
                if ext.lower() == '.mp4' and os.path.getsize(os.path.join(root,name)) >0:
                    video = os.path.join(root,name)
                elif ext.lower() == '.m4a':
                    audio = os.path.join(root,name)
                else:
                    continue

        common.merge_audio_video(ffmpeg_path,audio,video,self.prepare_filepath)


        # set downloaded filepath
        logger.info('start set download filepath')
        self._set_downloaded_filepath()
        logger.info('set download filepath succeed')

