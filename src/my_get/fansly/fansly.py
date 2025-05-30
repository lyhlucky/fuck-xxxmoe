from .api import Api
from yt_dlp import YoutubeDL
import json
from base64 import b64decode
from common import MsgType, flush_print, sanitize_title
import os
import subprocess
from urllib.parse import unquote


class FanslyAdaptor:
    def __init__(self, params, proxies, progress_hook):
        self.params = params
        self.proxies = proxies
        self.progress_hook = progress_hook
        self.metadata = json.loads(b64decode(self.params['metadata']).decode('utf-8'))
        self.cookies = self.metadata['http_headers']['cookie']
        self.ffmpeg_location = params['ffmpeg_location']

    def extract(self):
        api = Api(auth=self.metadata["http_headers"]["authorization"],
                  media_info=self.metadata["media_info"],
                  proxies=self.proxies,
                  )
        
        title = unquote(api.title)
        if len(title) == 0:
            title = f"{'Fansly'}_{self.params['uuid']}"

        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': '',
                'local_thumbnail': '',
                'duration': 0,
                'is_live': False
            }
        }))
        
        title = sanitize_title(title)
        file_path = os.path.join(self.params["save_path"], title)
        max_path = 180
        if len(file_path) > max_path:
            file_path = file_path[0:max_path]
            title = os.path.basename(file_path)

        self.final_location = f'{self.params["save_path"]}/{title}.mp4'
        self.video_location = f'{self.params["save_path"]}/{title}_video.mp4'
        self.audio_location = f'{self.params["save_path"]}/{title}_audio.m4a'

        original_video_url, original_audio_url, metadata = api.parse_url(self.params["url"])
        if (len(original_audio_url) != 0) :
            self._download(original_video_url, metadata, self.video_location)
            self._download(original_audio_url, metadata, self.audio_location)
            self._merger_files(self.video_location, self.audio_location, self.final_location)
        else:
            self._download(original_video_url, metadata, self.final_location)
        
        
    def _download(self, url, metadata, output):
        http_headers = {
            "Cookie": f'CloudFront-Key-Pair-Id={metadata["Key-Pair-Id"]}; CloudFront-Signature={metadata["Signature"]}; CloudFront-Policy={metadata["Policy"]}; {self.cookies}'
        }

        ydl_opts = {
            'cachedir': False,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'playliststart': 1,
            'playlistend': 1,
            'retries': 3,
            'ffmpeg_location': self.params["ffmpeg_location"],
            "http_headers": http_headers,
            'outtmpl': output,
        }
        if self.params['proxy']:
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

    def _merger_files(self, video_src, audio_src, video_output):
        print(f'Start merger {video_src} and {audio_src} to {video_output}...')
        command = [
            os.path.join(self.ffmpeg_location, 'ffmpeg'),
            '-i', video_src, '-i', audio_src, '-vcodec', 'copy', '-acodec', 'copy', '-strict' ,'-2' ,video_output
        ]
        subprocess.run(command)
        print('Merger finished.')