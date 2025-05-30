#********************************************************************************************
# https://missav.com/
#********************************************************************************************

from bs4 import BeautifulSoup
import time
import re
import json
import os
from common import MsgType, flush_print, sanitize_filename
from yt_dlp import YoutubeDL
import logging
from curlx import CurlX


logger = logging.getLogger('missav')

class MissavAdaptor:
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

        self.session = CurlX(proxies=proxies, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'accept': '*/*'
        })

    def extract(self):
        try:
            original_url = self.params['url']
            response = self.session.get(original_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 获取标题
            title = None
            meta_title_tag = soup.find('meta', property='og:title')
            if meta_title_tag and meta_title_tag.get('content'):
                title = sanitize_filename(meta_title_tag['content'])
            else:
                title = f"MissAV-{int(time.time())}"
            
            # 获取缩略图
            thumbnail_url = ''
            meta_image_tag = soup.find('meta', property='og:image')
            if meta_image_tag and meta_image_tag.get('content'):
                thumbnail_url = meta_image_tag['content']

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

            scripts = soup.find_all('script', type='text/javascript')
            for script in scripts:
                match = re.search(r"'(m3u8\|.*?\|source)'", script.text)
                if match:
                    content = match.group(1)
                    logger.info(f"[EVAL] {content}")
                    parts = content.split('|')
                    protocol = parts[8]       # "https"
                    domain = f"{parts[7]}.{parts[6]}"  # "surrit.com"
                    file_id = f"{parts[5]}-{parts[4]}-{parts[3]}-{parts[2]}-{parts[1]}"
                    # 视频质量
                    quality = parts[10]       # "720p"
                    # 视频类型
                    file_type = parts[9]      # "video"
                    # 拼接成最终的 URL
                    video_url = f"{protocol}://{domain}/{file_id}/{quality}/{file_type}.m3u8"
                    file_path = f'{self.params["save_path"]}/{title}'
                    max_path = 180
                    if len(file_path) > max_path:
                        file_path = file_path[0:max_path]
                        title = os.path.basename(file_path)
                    self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                    self._download(video_url, self.final_location)
                    break
        except Exception as e:
            logger.info(f"parse html failed: {e}")

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
