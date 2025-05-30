
import requests
import json
from base64 import b64decode
from urllib.parse import urlparse, unquote
from common import MsgType, flush_print, sanitize_filename
import random
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import subprocess


class UdemyAdaptor:
    def __init__(
        self,
        params,
        proxies,
        progress_hook=None
    ):
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.metadata = json.loads(b64decode(self.params['metadata']).decode('utf-8'))
        self.final_location = None

        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        })
        self.session.cookies.update(
            requests.utils.cookiejar_from_dict(json.loads(b64decode(self.params['sessdata']).decode('utf-8')), cookiejar=None, overwrite=True)
        )

        retry_strategy = Retry(
            total=3,
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def extract(self):
        title = unquote(self.metadata["title"])
        title = sanitize_filename(title)
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
        original_url = self.params['url']
        course_type = self.metadata['type']

        if course_type == 'lecture':
            qval = format(random.random(),'.16f')
            lecture_fileds = 'fields[lecture]=asset,description,download_url,is_free,last_watched_second'
            assert_fileds = 'fields[asset]=asset_type,length,media_license_token,course_is_drmed,media_sources,captions,thumbnail_sprite,slides,slide_urls,download_urls,external_url'
            hostname = urlparse(original_url).netloc
            api_url = f'https://{hostname}/api-2.0/users/me/subscribed-courses/{self.metadata["courseId"]}/{course_type}s/{self.metadata["itemId"]}/?{lecture_fileds}&{assert_fileds}&q={qval}'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                data = response.json()
                media_sources = data['asset']['media_sources']
                m3u8_url = None

                for media in media_sources:
                    if media['type'] == 'application/x-mpegURL':
                        m3u8_url = media['src']
                        break

                if m3u8_url is None:
                    m3u8_url = media_sources[0]['src']

                best_m3u8_url = self._get_best_from_m3u8(m3u8_url)

                file_path = os.path.join(self.params["save_path"], title)
                max_path = 180
                if len(file_path) > max_path:
                    file_path = file_path[0:max_path]
                    title = os.path.basename(file_path)

                if self.params['add_playlist_index'] == "true":
                    self.final_location = f'{self.params["save_path"]}/{self.params["playlist_index"]}.{title}.mp4'
                else:
                    self.final_location = f'{self.params["save_path"]}/{title}.mp4'

                self._download(best_m3u8_url, self.final_location)

    def _get_best_from_m3u8(self, m3u8_url):
        best_m3u8_url = None
        response = self.session.get(m3u8_url, proxies=self.proxies)
        if response.status_code == 200:
            m3u8_content = response.text
            m3u8_lines = m3u8_content.splitlines()
            urls = [line for line in m3u8_lines if line and not line.startswith("#")]
            best_m3u8_url = urls[-1]

        return best_m3u8_url
    
    def _download(self, m3u8_url, output):
        # 下载 M3U8 文件
        response = self.session.get(m3u8_url, proxies=self.proxies)
        if response.status_code == 200:
            m3u8_content = response.text
            m3u8_lines = m3u8_content.splitlines()
            
            # 找到所有的切片 URL
            ts_urls = [line for line in m3u8_lines if line and not line.startswith("#")]
            
            ts_files = []
            total_segments = len(ts_urls)
            total_size = 0
            total_time = 0
            
            for i, ts_url in enumerate(ts_urls):
                ts_file_path = f"{self.params['save_path']}/segment_{i}.ts"
           
                start_time = time.time()
                ts_content = self.session.get(ts_url, proxies=self.proxies).content
                end_time = time.time()
                
                with open(ts_file_path, 'wb') as f:
                    f.write(ts_content)
                
                ts_files.append(ts_file_path)

                elapsed_time = end_time - start_time
                total_time += elapsed_time
                size = len(ts_content)
                total_size += size
                speed = size / elapsed_time  # B/s
                progress = (i + 1) / total_segments # 百分比进度
                remaining_time = (total_segments - (i + 1)) * (total_time / (i + 1))
                
                flush_print(json.dumps({
                    'type': MsgType.downloading.value,
                    'msg': {
                        'progress': str('{0:.3f}'.format(progress)),
                        'speed': self._format_size(speed),
                        'filesize': str(total_size),
                        'eta': str(remaining_time),
                    }
                }))
            
            self._merge_ts_files(ts_files, output)
 
    def _merge_ts_files(self, ts_files, output_file):
        os.chdir(self.params['save_path'])

        input_file = 'input'
        with open(input_file, 'w') as f:
            for ts_file in ts_files:
                f.write(f"file '{ts_file}'\n")

        subprocess.run([
            os.path.join(self.params['ffmpeg_location'], 'ffmpeg'),
            '-f', 'concat', '-safe', "0", '-i', input_file, '-c', 'copy',
            output_file
        ])

    def _format_size(self, size):
        """格式化文件大小，返回合适的单位（字节、KB 或 MB）"""
        if size < 1024:
            return f"{size:.2f} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"