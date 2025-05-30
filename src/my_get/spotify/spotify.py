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
from common import MsgType, flush_print, ensure_limit_title


logger = logging.getLogger('spotify')

class SpotifyAdaptor:
    def __init__(self, params, proxies, progress_hook=None):
        self.params = params
        self.progress_hook = progress_hook
        self.save_path = params['save_path']
        self.ffmpeg_location = params['ffmpeg_location']
        self.proxies = proxies
        self.cookies = json.loads(b64decode(self.params['sessdata']).decode('utf-8'))
        self.final_location = None
        self.audio_bit_rate = '128k'
        self.has_lrc = True
        self.lrc_path = ''

        if 'has_lyric' in params:
            self.has_lrc = params['has_lyric'] == 'true'

    def extract(self):
        # 获取下载信息
        api = Api(url=self.params['url'], cookies=self.cookies, proxies=self.proxies, params=self.params)
        track = api.extract_track()

        is_drm = True
        if track['pssh'] is None:
            is_drm = False

        final_title = ensure_limit_title(self.save_path, track["title"])

        # 开始下载
        logger.info('start download.')
        # t = int(time.time())
        if is_drm:
            save_location = f'{self.save_path}/audio_encrypted.mp4'
        else:
            save_location = f'{self.save_path}/{final_title}.mp3'

        self._download(track['cdn_url'], save_location)

        if is_drm:
            # 开始解密
            logger.info('start decrypt.')
            # crypto = Crypto(
            #     pssh=track['pssh'],
            #     ffmpeg_location=self.ffmpeg_location,
            #     headers=track['access_token'],
            #     proxies=self.proxies
            # )
            decryption_key = api.get_decryption_keys()
            decrypted_location = f'{self.save_path}/audio_decrypted.mp4'
            api.decrypt(decryption_key, save_location, decrypted_location)
            save_location = decrypted_location

        # 修复文件，更改比特率
        logger.info('start fix.')
        audio_sufix = "mp3"
        if is_drm:
            audio_sufix = "m4a"
            fixed_location = f'{self.save_path}/audio_fixed.{audio_sufix}'
            if track['is_premium']:
                self.audio_bit_rate = '256k'
            else:
                self.audio_bit_rate = '128k'
            self._fixup_song(save_location, fixed_location, self.audio_bit_rate)

            # 添加标签
            logger.info('add tags.')
            self._add_tags(fixed_location, track['tags'], is_drm)
            save_location = fixed_location

        # final_title = ensure_limit_title(self.save_path, track["title"])

        synced_lyrics = track['synced_lyrics']
        if self.has_lrc and synced_lyrics:
            self.lrc_path = f'{self.save_path}/{final_title}.lrc'
            with open(self.lrc_path, "w", encoding="utf-8") as f:
                f.write(synced_lyrics)

        self.final_location = f'{self.save_path}/{final_title}.{audio_sufix}'
        shutil.move(save_location, self.final_location)
        logger.info('download finish.')

    def extract_playlist(self):
        api = Api(url=self.params['url'], cookies=self.cookies, proxies=self.proxies ,params=self.params)
        api.extract_playlist()

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
        
        attemps = 0

        while attemps < 3:
            attemps += 1
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    if self.progress_hook is not None:
                        ydl.add_progress_hook(self.progress_hook)
            
                    ydl.download(url)
                    break
            except:
                pass

    def _fixup_song(self, decrypted_location, fixed_location, audio_bit_rate):
        # command = [
        #     str(Path(self.ffmpeg_location) / 'ffmpeg'),
        #     '-i', decrypted_location, "-metadata", "artist=unknown",
        #     '-b:a', audio_bit_rate, fixed_location
        # ]
        command = [
            str(Path(self.ffmpeg_location) / 'ffmpeg'),
            '-i',
            decrypted_location,
            '-c:a',
            'copy',
            fixed_location
        ]
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

    def _add_tags(self, file_path, tags, is_mp4):
        if is_mp4:
            try:
                file = MP4(file_path)
                file.update(tags)
                file.save()
            except:
                pass