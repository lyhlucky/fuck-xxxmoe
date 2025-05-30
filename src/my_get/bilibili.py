import requests
import json
import re
from yt_dlp import YoutubeDL
from base64 import b64decode
import os
import subprocess
from bs4 import BeautifulSoup
from common import MsgType, flush_print, sanitize_filename


class BilibiliAdaptor():
    def __init__(self, params, proxies, progress_hook=None):
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.final_location = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Cookie': b64decode(self.params['sessdata']).decode('utf-8')
        })

    # 检测是否登录
    # 0 未登录（游客）
    # 1 已登录（普通会员）
    # 2 已登录（大会员
    def checkLogin(self):
        response = self.session.get(
            url='https://api.bilibili.com/x/web-interface/nav',
            proxies=self.proxies)

        body = json.loads(response.text)
        data = body['data']
        if data['isLogin']:
            if data['vipStatus']:
                return 2
            else:
                return 1
        else:
            return 0

    def extract(self):
        original_url = self.params['url']
        video_url = None
        audio_url = None

        if '/video/BV' in original_url or '/video/av' in original_url:
            title = ''
            thumb_url = ''
            response = self.session.get(original_url, proxies=self.proxies)
            soup = BeautifulSoup(response.text, 'html.parser')
            thumbnail_meta = soup.find('meta', attrs={'itemprop': 'thumbnailUrl'})
            if thumbnail_meta:
                thumb_url = thumbnail_meta['content']
                if not thumb_url.startswith('http'):
                    thumb_url = 'https:' + thumb_url

            video_title_tag = soup.find(None, attrs={'class': 'video-title'})
            if video_title_tag:
                title = video_title_tag.string

            if len(title) == 0:
                title = soup.title.string

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

            # 获取音视频下载链接
            play_info = json.loads(
                re.search(
                    pattern=r'<script>window.__playinfo__=([\s\S]*?)</script>',
                    string=response.text).group(1)
            )

            if 'data' in play_info:
                dash = play_info['data']['dash']
                video_list = dash['video']
                audio_list = dash['audio']
                order_video_list = sorted(video_list, key=lambda i: i['id'], reverse=True)

                for video in order_video_list:
                    # 下载h264/avc编码的视频，另外支持hevc, av1
                    if 'avc' in video['codecs']:
                        video_url = video['baseUrl']
                        break

                if video_url is None:
                    video_url = order_video_list[0]['baseUrl']
                
                audio_url = audio_list[len(audio_list)-1]['baseUrl']
                print(f"video_url: {video_url}, audio_url: {audio_url}")

                save_path = self.params["save_path"]
                # 下载视频
                video_path = os.path.join(save_path, 'video.mp4')
                self._download(video_url, video_path)
                # 下载音频
                audio_path = os.path.join(save_path, 'audio.m4a')
                self._download(audio_url, audio_path)
                # 合并音频和视频
                title = sanitize_filename(title)
                file_path = os.path.join(save_path, title)
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)
                self.final_location = f'{save_path}/{title}.mp4'
                self._merger_video_and_audio(video_path, audio_path, self.final_location)

        return video_url, audio_url
    
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
            # 下载需要headers
            'http_headers': {
                'Referer': self.params['url']
            }
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

    def _merger_video_and_audio(self, video_src, audio_src, video_output):
        print(f'Start merger {video_src} and {audio_src} to {video_output}...')
        command = [
            os.path.join(self.params['ffmpeg_location'], 'ffmpeg'),
            '-i', video_src, '-i', audio_src, '-vcodec', 'copy', '-acodec', 'copy','-strict' ,'-2' , video_output
        ]
        subprocess.run(command)
        print('Merger finished.')