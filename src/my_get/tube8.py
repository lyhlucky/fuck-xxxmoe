
import requests
import json
from common import MsgType, flush_print, sanitize_filename
import os
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import time


class Tube8Adaptor:
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
        script = soup.find('script', id='tm_pc_player_setup')

        if script:
            script_lines = script.text.split('\n')
            playervars = None

            for line in script_lines:
                if line.find('playervars') != -1:
                    playervars = line[line.find('{'):]
                    break
            
            if playervars is not None:
                json_data = json.loads(playervars)

                title = ''
                if "video_title" in json_data:
                    title = sanitize_filename(json_data['video_title'])
                else:
                    title = f'Tube8-{int(time.time())}'

                thumb_url = ''
                if "image_url" in json_data:
                    thumb_url = json_data['image_url']

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

                # 优先hls/m3u8链接
                medias = json_data['mediaDefinitions']
                video_url = medias[0]['videoUrl']
                for media in medias:
                    if media['format'] == 'hls':
                        video_url = media['videoUrl']
                        break
                
                response = self.session.get(url=video_url, proxies=self.proxies)
                videos = response.json()
                tmp_quality = 0
                for video in videos:
                    quality = video['quality']
                    if quality.isdigit():
                        quality = int(quality)
                        if quality > tmp_quality:
                            tmp_quality = quality
                            video_url = video['videoUrl']
 
                file_path = os.path.join(self.params["save_path"], title)
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)

                self.final_location = os.path.join(self.params["save_path"], f"{title}.mp4")
                self._download(video_url, self.final_location)
            else:
                raise Exception('playervars not found!')
        else:
            raise Exception('script tm_pc_player_setup not found!')

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