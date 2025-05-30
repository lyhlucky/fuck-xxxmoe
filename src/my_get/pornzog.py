
import requests
import json
from common import MsgType, flush_print, sanitize_filename
import os
from yt_dlp import YoutubeDL
import re
from base64 import b64decode
from urllib.parse import urlparse, parse_qs, unquote


class PornzogAdaptor:
    def __init__(
        self,
        url,
        params,
        proxies,
        progress_hook=None
    ):
        self.original_url = url
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.final_location = None

        parsed_url = urlparse(url)
        self.host = parsed_url.netloc

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Referer': 'https://{0}/'.format(self.host),
            'Accept': 'application/json, text/plain, */*'
        })

    def extract(self):
        video_id = self.get_video_id(self.original_url)
        api_url = f'https://{self.host}/api/videofile.php?video_id={video_id}&lifetime=8640000'
        response = self.session.get(url=api_url, proxies=self.proxies)
        content = response.json()
        video_url = content[-1]['video_url']
        video_url = self.decode_url(video_url)
        if video_url.startswith('/'):
            video_url = 'https://{0}{1}'.format(self.host, video_url)
        parsed = urlparse(video_url)
        qs = parse_qs(parsed.query)
        if 'f' not in qs:
            video_url = video_url + '&f=video.m3u8'

        metadata = json.loads(b64decode(self.params['metadata']).decode('utf-8'))
        title = unquote(metadata['title'])
        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': metadata['thumbnail'],
                'local_thumbnail': '',
                'duration': 0,
                'is_live': False
            }
        }))

        title = sanitize_filename(title)
        file_path = os.path.join(self.params["save_path"], title)
        max_path = 180
        if len(file_path) > max_path:
            file_path = file_path[0:max_path]
            title = os.path.basename(file_path)

        self.final_location = os.path.join(self.params["save_path"], f"{title}.mp4")
        self._download(video_url, self.final_location)

    def get_video_id(self, url):
        pattern = r'/(?:videos?|embed)/(\d+)/'
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return video_id
        return None

    def decode_url(self, url):
        url = url.replace('А', 'A').replace('В', 'B').replace('С', 'C').replace('Е', 'E').replace('М', 'M').replace('~', '=').replace(',','/')
        url = b64decode(url)
        url = url.decode("utf8")
        return url

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