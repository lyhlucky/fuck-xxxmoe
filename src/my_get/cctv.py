
import requests
import json
from common import MsgType, flush_print, sanitize_filename, generate_random_hex
import os
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import time
import re


class CctvAdaptor:
    def __init__(
        self,
        params,
        proxies,
        progress_hook=None
    ):
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.final_location = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        })

    def extract(self):
        original_url = self.params['url']
        response = self.session.get(original_url, proxies=self.proxies)
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script', type='text/javascript')
        guid = None

        for script in scripts:
            pattern = r'guid = "([a-f0-9]{32})"'
            match = re.search(pattern, script.text)
            if match:
                guid = match.group(1)
                print(guid)
                break

        if guid is None:
            raise Exception('Error: not find guid!')

        timestamp = int(time.time())
        vc_num = generate_random_hex(32, upperCase=True)
        uid = generate_random_hex(32, upperCase=True)
        video_info_url = f'https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}&client=flash&im=0&tsp={timestamp}&vn=2049&vc={vc_num}&uid={uid}&wlan='
        response = self.session.get(url=video_info_url, proxies=self.proxies)
        video_info = response.json()

        title = video_info['title']
        if len(title) == 0:
            title = video_info['tag']
            if len(title) == 0:
                title = F"CCTV-{timestamp}"
        
        thumb_url = video_info['image']

        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': thumb_url,
                'local_thumbnail': '',
                'duration': 0,
                'is_live': False
            }
        }))

        # 低分辨率链接
        video_url = video_info['hls_url']
        manifest = video_info['manifest']
        if 'hls_h5e_url' in manifest:
            # 高分辨率链接
            video_url = manifest['hls_h5e_url']
        
        title = sanitize_filename(title)
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