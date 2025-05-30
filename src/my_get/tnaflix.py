#********************************************************************************************
# https://m.tnaflix.com/
# https://www.tnaflix.com/
#********************************************************************************************

import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os
from common import MsgType, flush_print, sanitize_filename
from yt_dlp import YoutubeDL
import logging


logger = logging.getLogger('tnaflix')

class TnaflixAdaptor:
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
        self.stop_event = False

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'accept': '*/*'
        })

    def extract(self):
        original_url = self.params['url']
        title = None
        thumbnail_url = ''
        response = self.session.get(original_url, proxies=self.proxies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        ld_json_script = soup.find('script', type='application/ld+json')
        if ld_json_script:
            ld_json = json.loads(ld_json_script.get_text())
            title = sanitize_filename(ld_json['name'])
            thumbnail_url = ld_json['thumbnailUrl']

        if title is None:
            title = f"Tnaflix-{int(time.time())}"

        video_id = self._get_video_id(original_url)
        if video_id is None:
            raise Exception("invalid video id")
        
        logger.info(f"video id: {video_id}")
        api_url = f"https://m.tnaflix.com/ajax/video-player/{video_id}"
        response = self.session.get(api_url, proxies=self.proxies)
        response.raise_for_status()
        html_content = response.json()['html']
        soup = BeautifulSoup(html_content, 'html.parser')
        source_tags = soup.find_all('source')
        if source_tags:
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

            video_url = source_tags[0].get('src')
            file_path = f'{self.params["save_path"]}/{title}'
            max_path = 180
            if len(file_path) > max_path:
                file_path = file_path[0:max_path]
                title = os.path.basename(file_path)
            self.final_location = f'{self.params["save_path"]}/{title}.mp4'
            self._download(video_url, self.final_location)
        else:
            raise Exception("No source")

    def _get_video_id(self, url):
        match = re.search(r'video(\d+)', url)
        if match:
            return match.group(1)
        return None
    
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
