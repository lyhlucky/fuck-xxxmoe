import json
import subprocess
from pathlib import Path
import time
from yt_dlp import YoutubeDL
from mutagen.mp4 import MP4
import shutil
from base64 import b64decode
import logging
from io import TextIOWrapper
import json
import os

from .api import Api
from .crypto import Crypto
from common import MsgType, flush_print, sanitize_title


logger = logging.getLogger('amazonmusic')

class AmazonMusicAdaptor:
    def __init__(self, params, proxies, progress_hook=None):
        self.params = params
        self.progress_hook = progress_hook
        self.save_path = params['save_path']
        self.ffmpeg_location = params['ffmpeg_location']
        self.proxies = proxies
        self.cookies = json.loads(b64decode(self.params['sessdata']).decode('utf-8'))
        self.final_location = None
        self.audio_bit_rate = '320k'

    def extract(self):
        # 获取下载信息
        api = Api(cookies=self.cookies, proxies=self.proxies ,params=self.params)
        api.process()

        # 获取解密信息
        crypto = Crypto(
            pssh=api.pssh,
            dmls_url=api.dmls_url,
            ffmpeg_location=self.ffmpeg_location,
            header={
                'token': f'Bearer {api.app_config["accessToken"]}',
                'customerId': f'{api.app_config["customerId"]}',
                'deviceType': f'{api.app_config["deviceType"]}',
                'deviceId': f'{api.app_config["deviceId"]}',
                'csrfrnd': f'{api.app_config["csrf"]["rnd"]}', 
                'csrftoken': f'{api.app_config["csrf"]["token"]}', 
                'csrfts': f'{api.app_config["csrf"]["ts"]}', 
            },
            proxies=self.proxies
        )
        decryption_key = crypto.get_decryption_keys()
        # print(f"@decryption_key: {decryption_key}")

        # 开始下载
        t = int(time.time())
        suffix = api.codecs
        index = suffix.find('.')
        if index != -1:
            suffix = api.codecs[0:index]

        save_location = f'{self.save_path}/{t}_encrypted.{suffix}'
        self._download(api.audio_url, save_location)

        decrypted_location = f'{self.save_path}/{t}_decrypted.{suffix}'
        crypto.decrypt(decryption_key, save_location, decrypted_location)

        # fixed_location = f'{self.save_path}/{t}_fixed.m4a'
        # self._fixup_song(decrypted_location, fixed_location)

        # 添加标签
        tags = api.get_tags()
        self._add_tags(decrypted_location, tags)

        title = sanitize_title(api.title)
        if self.params['add_playlist_index'] == "true":
            title = f"{self.params['playlist_index']}.{title}"

        file_path = os.path.join(self.params["save_path"], title)
        max_path = 180
        if len(file_path) > max_path:
            file_path = file_path[0:max_path]
            title = os.path.basename(file_path)

        self.final_location = f'{self.save_path}/{title}.{suffix}'
        shutil.move(decrypted_location, self.final_location)

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

    def _fixup_song(self, decrypted_location, fixed_location):
        command = [
            str(Path(self.ffmpeg_location) / 'ffmpeg'),
            '-i', decrypted_location, "-metadata", "artist=placeholder",
            '-b:a', self.audio_bit_rate, fixed_location
        ]
        # subprocess.run(command, check=True)
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

    def _add_tags(self, file_path, tags):
        file = MP4(file_path)
        file.update(tags)
        file.save()