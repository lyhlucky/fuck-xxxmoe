
import requests
import json
from common import MsgType, flush_print, sanitize_filename
import os
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import time


class PornhatAdaptor:
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
        player_div = soup.find('div', id='player_wrap')

        if player_div:
            title = ''
            if 'data-title' in player_div:
                title = sanitize_filename(player_div['data-title'])
            else:
                title = f'Pornhat-{int(time.time())}'

            video_div = player_div.find('video')
            if video_div:
                thumb_url = video_div['poster']
                if not thumb_url.startswith('http'):
                    thumb_url = 'https:' + thumb_url

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

                source_arry = video_div.find_all('source')
                video_url = source_arry[-1]['src']

                file_path = os.path.join(self.params["save_path"], title)
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)
                self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                self._download(video_url, self.final_location)
            else:
                raise Exception('video div not found.')
        else:
            raise Exception('player_wrap div not found.')

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