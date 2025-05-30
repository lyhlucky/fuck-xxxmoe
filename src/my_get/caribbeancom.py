
#********************************************************************************************
# https://en.caribbeancom.com/eng/index2.htm  https://www.caribbeancom.com/index2.htm
#********************************************************************************************

import requests
import json
from common import MsgType, flush_print, sanitize_filename
import os
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import time
import re
from base64 import b64decode
from urllib.parse import urlparse
import hashlib
import random
import string


class CaribbeancomAdaptor:
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
        self.domain = 'en'

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'accept': '*/*'
        })

        if 'sessdata' in self.params:
            self.session.cookies.update(
                requests.utils.cookiejar_from_dict(json.loads(b64decode(self.params['sessdata']).decode('utf-8')), cookiejar=None, overwrite=True)
            )

    def extract(self):
        original_url = self.params['url']
        if 'shorts.caribbeancom.com' in original_url:
            self._parse_shorts(original_url)
            return
        
        result = urlparse(original_url)
        if result.hostname.split('.')[0] != 'en':
            self.domain = 'www'

        auth_key = self._get_auth_key()
        if auth_key is None:
            raise Exception('Error: no auth_key')

        response = self.session.get(original_url, proxies=self.proxies)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        tag_title = soup.find('title')
        if tag_title:
            title = sanitize_filename(tag_title.get_text())
        else:
            title = f"Caribbeancom-{int(time.time())}"

        tag_scripts = soup.find_all('script')
        movie_id = self._find_movie_id(tag_scripts)
        if movie_id is None:
            raise Exception('Error: no movie_id')

        for script in tag_scripts:
            script_text = script.get_text()
            match = re.search(r'var movieFile = "(.*?)";', script_text, re.DOTALL)
            if match:
                movie_file = match.group(1)
                video_url = movie_file.replace('\" + movie_id + \"', movie_id) + auth_key
                thumbnail_url = f'https://{self.domain}.caribbeancom.com/member/moviepages/{movie_id}/images/l/001.jpg'
                local_thumbnail = self._download_thumbnail(thumbnail_url)

                flush_print(json.dumps({
                    'type': MsgType.sniff.value,
                    'msg': {
                        'ret_code': '0',
                        'title': title,
                        'thumbnail': '',
                        'local_thumbnail': local_thumbnail,
                        'duration': 0,
                        'is_live': False
                    }
                }))

                file_path = f'{self.params["save_path"]}/{title}'
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)

                self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                self._download(video_url, self.final_location)
                break

    def _get_auth_key(self):
        key = None
        timestamp = int(time.time())
        auth_url = f'https://{self.domain}.caribbeancom.com/member/app/getauthjw7key?_={timestamp}'
        response = self.session.get(auth_url, proxies=self.proxies)
        response.raise_for_status()
        match = re.search(r'window.authjw7Key = ({.*?});', response.text, re.DOTALL)
        if match:
            auth_dict = json.loads(match.group(1))
            key = auth_dict['u']
        return key
    
    def _find_movie_id(self, tag_scripts):
        movie_id = None
        for script in tag_scripts:
            script_text = script.get_text()
            match = re.search(r'ar Movie = ({.*?});', script_text, re.DOTALL)
            if match:
                movie_dict = json.loads(match.group(1))
                movie_id = movie_dict['movie_id']
                break
        return movie_id

    def _parse_shorts(self, url):
        result = urlparse(url)
        path_parts = result.path.split('/')
        movie_id = path_parts[-1]
        if len(movie_id) == 0:
            movie_id = path_parts[-2]

        api_url = f'https://shorts.caribbeancom.com/api/v1/pt/shorts/random?page=1&limit=5&start_movie_id={movie_id}&site_id=2468&list_site_id=2468'
        response = self.session.get(api_url, proxies=self.proxies)
        response.raise_for_status()
        shorts_dict = response.json()
        rows = shorts_dict['Rows']
        for row in rows:
            if row['MovieID'] == movie_id:
                video_url = row['VideoSrc']
                title = row['Title']

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

                title = sanitize_filename(title)
                file_path = f'{self.params["save_path"]}/{title}'
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)

                self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                self._download(video_url, self.final_location)
                break

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

    def _download_thumbnail(self, url):
        save_path = ''
        response = self.session.get(url, proxies=self.proxies)
        if response.status_code == 200:
            try:
                random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                hash_value = hashlib.sha256(random_string.encode()).hexdigest()[0:12]
                timestamp = int(time.time() * 1000)
                download_path = self.params["save_path"]
                # download_path = os.path.abspath(os.path.join(self.params["save_path"], "../../.thumb"))
                # if not os.path.exists(download_path):
                #     os.makedirs(download_path)
                    
                save_path = f'{download_path}/{hash_value}_{timestamp}.jpg'
                with open(save_path, 'wb') as file:
                    file.write(response.content)
            except:
                pass
        return save_path