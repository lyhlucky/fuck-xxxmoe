
import requests
import json
from base64 import b64decode
from yt_dlp import YoutubeDL
from urllib.parse import urlparse
from common import MsgType, flush_print, sanitize_filename, ensure_playlistname
import os
from bs4 import BeautifulSoup
import re


class ThinkificAdaptor:
    def __init__(
        self,
        params,
        proxies,
        progress_hook=None
    ):
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.cookie_dict = json.loads(b64decode(self.params['sessdata']).decode('utf-8'))
        self.ffmpeg_location = params['ffmpeg_location']
        self.final_location = None

        self.session = requests.Session()
        self.session.headers.update({
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        })
        self.session.cookies.update(
            requests.utils.cookiejar_from_dict(self.cookie_dict, cookiejar=None, overwrite=True)
        )

    def extract(self):
        original_url = self.params['url']
        result_parse = urlparse(original_url)
        api_prefix = 'https://' + result_parse.netloc + '/api/course_player/v2'
        path_seq = result_parse.path.split('/')
        video_api_url = api_prefix + '/' + path_seq[1] + '/' + path_seq[3]
        media_slug = path_seq[5]
        response = self.session.get(video_api_url, proxies=self.proxies)
        data = response.json()
        contents = data['contents']
        thumbnail_url = ''

        for content in contents:
            if media_slug == content['slug']:
                lesson_url = f'{api_prefix}/lessons/{content["contentable_id"]}'
                lesson_response = self.session.get(lesson_url, proxies=self.proxies)
                if lesson_response.status_code == 200:
                    lesson_data = lesson_response.json()
                    current_video_info = lesson_data['videos'][0]
                    thumbnail_url = current_video_info['primary_thumbnail_url']
                    title = sanitize_filename(content['name'])
                    if self.params['add_playlist_index'] == "true":
                        title = f"{self.params['playlist_index']}.{title}"

                    flush_print(json.dumps({
                        'type': MsgType.sniff.value,
                        'msg': {
                            'ret_code': '0',
                            'title': title,
                            'thumbnail': thumbnail_url,
                            'local_thumbnail': '',
                            'duration': 0,
                            'is_live': False
                        }
                    }))

                    video_url = ''
                    if 'l-team' in original_url: # https://l-team.thinkific.com/
                        video_url = self.parse_1team()
                    else: # https://training.thinkific.com/
                        media_url = f'https://fast.wistia.com/embed/medias/{current_video_info["identifier"]}.json'
                        media_response = self.session.get(media_url, proxies=self.proxies)
                        if media_response.status_code == 200:
                            media_data = media_response.json()
                            video_url = media_data['media']['assets'][0]['url']

                    file_path = os.path.join(self.params["save_path"], title)
                    max_path = 180
                    if len(file_path) > max_path:
                        file_path = file_path[0:max_path]
                        title = os.path.basename(file_path)

                    if self.params['add_playlist_index'] == "true":
                        self.final_location = f'{self.params["save_path"]}/{self.params["playlist_index"]}.{title}.mp4'
                    else:
                        self.final_location = f'{self.params["save_path"]}/{title}.mp4'

                    self._download(video_url, self.final_location)
                break

    def extract_playlist(self):
        videos = []
        original_url = self.params['url']
        result_parse = urlparse(original_url)
        api_prefix = 'https://' + result_parse.netloc + '/api/course_player/v2'
        path_seq = result_parse.path.split('/')
        video_api_url = api_prefix + '/' + path_seq[1] + '/' + path_seq[3]
        response = self.session.get(video_api_url, proxies=self.proxies)
        data = response.json()
        contents = data['contents']
        playlist_name = ensure_playlistname(data['course']['name'])

        for content in contents:
            if content['contentable_type'] == 'Lesson' and content['default_lesson_type_icon'] == 'video':
                url = f'https://training.thinkific.com/courses/take/{data["course"]["slug"]}/lessons/{content["slug"]}?itdl_pname={playlist_name}'
                videos.append({
                    'title': content['name'],
                    'url': url
                })

        resp = {
            'type': MsgType.playlist.value,
            'msg': {
                'videos': videos
            }
        }
        flush_print(json.dumps(resp))

    def _download(self, url, output):
        ydl_opts = {
            'cachedir': False,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'playliststart': 1,
            'playlistend': 1,
            'retries': 3,
            'ffmpeg_location': self.ffmpeg_location,
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

    def parse_1team(self):
        video_url = ''
        metadata = json.loads(b64decode(self.params['metadata']).decode('utf-8'))
        response = self.session.get(metadata['videoSrc'], proxies=self.proxies)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script', type='text/javascript')

        for script in scripts:
            text = script.get_text()
            match = re.search(r"_wq\.push\(\{\s*id:\s*'([\w\d]+)'", text)

            if match:
                id = match.group(1)
                print("匹配到的 ID:", id)
                m3u8_url = f'https://fast.wistia.com/embed/medias/{id}.m3u8'
                video_url = self._get_best_from_m3u8(m3u8_url)
                break

        return video_url

    def _get_best_from_m3u8(self, m3u8_url):
        best_m3u8_url = None
        response = self.session.get(m3u8_url, proxies=self.proxies)
        if response.status_code == 200:
            m3u8_content = response.text
            m3u8_lines = m3u8_content.splitlines()
            urls = [line for line in m3u8_lines if line and not line.startswith("#")]
            best_m3u8_url = urls[0]

        return best_m3u8_url