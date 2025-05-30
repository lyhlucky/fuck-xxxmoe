#********************************************************************************************
# https://myfans.jp/
#********************************************************************************************

import json
import os
from common import MsgType, flush_print, sanitize_filename, sanitize_title
from yt_dlp import YoutubeDL
import logging
from urllib.parse import urlparse
import requests
import traceback
from base64 import b64decode


logger = logging.getLogger('myfans')

class MyFansJpAdaptor:
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
        self.cookie_dict = None

        if 'sessdata' in self.params:
            self.cookie_dict = json.loads(b64decode(self.params['sessdata']).decode('utf-8'))

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'accept': 'application/json, text/plain, */*',
            'Google-Ga-Data': 'event328'
        })

        if self.cookie_dict is not None and '_mfans_token' in self.cookie_dict:
            self.session.headers.update({'Authorization': f'Token {self.cookie_dict["_mfans_token"]}'})

    def extract(self):
        original_url = self.params['url']
        if '/posts/' not in original_url:
            raise Exception('Unsupported url')
        
        result_parse = urlparse(original_url)
        path_seq = result_parse.path.split('/')
        post_id = path_seq[-1]
        logger.info(f"post_id: {post_id}")
        self._parse_post(post_id)

    def _parse_post(self, post_id):
        try:
            url = f'https://api.myfans.jp/api/v2/posts/{post_id}'
            response = self.session.get(url, proxies=self.proxies)
            content = response.json()
            title = content['body']
            if len(title) == 0:
                title = f"MyFans-{post_id}"

            videos = content.get("videos", {})
            trial = videos.get("trial")
            main = videos.get("main")
            current_video_data = None

            if main:
                current_video_data = main[-1] if isinstance(main, list) and main else None
            elif trial:
                current_video_data = trial[-1] if isinstance(trial, list) and trial else None
            else:
                raise Exception('Not find video url')
            
            thumbnail_url = current_video_data.get('image_url', '')
            if len(thumbnail_url) == 0:
                thumbnail_url = current_video_data['post_image']['square_thumbnail_url']
            
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

            clean_title = sanitize_title(title)
            file_path = f'{self.params["save_path"]}/{clean_title}'
            max_path = 180
            if len(file_path) > max_path:
                file_path = file_path[0:max_path]
                clean_title = os.path.basename(file_path)
            self.final_location = f'{self.params["save_path"]}/{clean_title}.mp4'
            video_url = current_video_data['url']
            self._download(video_url, self.final_location)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise e

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