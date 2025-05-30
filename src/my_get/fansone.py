
import requests
import json
from common import MsgType, flush_print, sanitize_filename
import os
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
from base64 import b64decode
import sys


class FansoneAdaptor:
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

        # UserAgent需要和上层登录的浏览器一致，暂时先写死
        # if sys.platform == 'darwin':
        #     user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15'
        # else:
        #     user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'

        if 'user_agent' in params:
            user_agent = params['user_agent']
        else:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Cookie': b64decode(self.params['sessdata']).decode('utf-8')
        })

    def extract(self):
        original_url = self.params['url']
        response = self.session.get(original_url, proxies=self.proxies)
        soup = BeautifulSoup(response.text, 'html.parser') 
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            json_data = json.loads(script.text)
            current_post = json_data['props']['initialState']['post']['currentPost']
            if current_post:
                title = sanitize_filename(current_post['title'])
                if len(title) == 0:
                    title = sanitize_filename(current_post['content'])
                    if len(title) == 0:
                        title = f'FansOne-{current_post["displayname"]}-{current_post["id"]}' 

                domain = current_post['domain']
                video_code = current_post['video']
                thumb_url = current_post['thumb']

                if len(domain) > 0:
                    if 'video7' in domain:
                        # domain: video7.fansone.co
                        video_url = f'https://{domain}/{domain}/{video_code}/master.m3u8'
                        if not thumb_url or len(thumb_url) == 0:
                            thumb_url = f'https://{domain}/{domain}/{video_code}/large-0000000000.jpeg'
                    else:
                        # domain: video5.fansone.co
                        video_url = f'https://{domain}/{video_code}/master.m3u8'
                        if not thumb_url or len(thumb_url) == 0:
                            thumb_url = f'https://{domain}/{video_code}/large-0000000000.jpeg'
                else:
                    if not thumb_url or len(thumb_url) == 0:
                        thumb_url = f'https://static.fansone.co/videos/{video_code}/large-0000000000.jpeg'

                    video_url = f'https://video1.fansone.co/static.fansone.co/videos/{video_code}/master'

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

                file_path = os.path.join(self.params["save_path"], title)
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)
                self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                self._download(video_url, self.final_location)
            else:
                raise Exception('json currentPost not found!')
        else:
            raise Exception('script __NEXT_DATA__ not found!')

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