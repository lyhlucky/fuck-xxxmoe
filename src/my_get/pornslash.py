#********************************************************************************************
# https://www.pornslash.com/
#********************************************************************************************

import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os
import subprocess
from common import MsgType, flush_print, sanitize_filename
import logging


logger = logging.getLogger('pornslash')

class PornSlashAdaptor:
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

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'accept': '*/*'
        })

    def extract(self):
        original_url = self.params['url']
        response = self.session.get(original_url, proxies=self.proxies)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        if '/shorts/' in original_url:
            title, thumbnail_url, video_url = self._parse_shorts(soup)
        else:
            title, thumbnail_url, video_url = self._parse_videos(soup)
        
        if video_url is None:
            raise Exception('Not find url')
        
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

        best_m3u8_url = self._get_best_from_m3u8(video_url)

        file_path = f'{self.params["save_path"]}/{title}'
        max_path = 180
        if len(file_path) > max_path:
            file_path = file_path[0:max_path]
            title = os.path.basename(file_path)

        self.final_location = f'{self.params["save_path"]}/{title}.mp4'
        self._download(best_m3u8_url, self.final_location)
            
    def _parse_videos(self, soup):
        title = None
        thumbnail_url = None
        video_url = None

        tag_title = soup.find('title')
        if tag_title:
            title = tag_title.get_text()
        else:
            title = f"PornSlash-{int(time.time())}"

        ld_json_script = soup.find('script', type='application/ld+json')
        if ld_json_script:
            ld_json = json.loads(ld_json_script.get_text())
            thumbnail_url = ld_json['thumbnailUrl']

        tag_scripts = soup.find_all('script')
        for script in tag_scripts:
            script_text = script.get_text()
            match = re.search(r'loadSource\("([^"]+)"\)', script_text, re.DOTALL)
            if match:
                video_url = match.group(1)
                break

        return title, thumbnail_url, video_url

    def _parse_shorts(self, soup):
        title = None
        thumbnail_url = None
        video_url = None

        tag_scripts = soup.find_all('script')
        for script in tag_scripts:
            script_text = script.get_text()
            match = re.search(r'i=!1,l=({.*?}),p=!1,', script_text, re.DOTALL)
            if match:
                video_info = match.group(1)
                video_dict = json.loads(video_info)
                title = sanitize_filename(video_dict['title'])
                thumbnail_url = video_dict['image']

                shorts_url = 'https://www.pornslash.com/get/shorts'
                response = self.session.get(shorts_url, proxies=self.proxies)
                response.raise_for_status()
                shorts_dict = response.json()
                video_url = f'{shorts_dict["url"]}/master/{video_dict["encid"]}'
                break

        return title, thumbnail_url, video_url

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

        command = [
            os.path.join(self.params['ffmpeg_location'], 'ffmpeg'),
            '-f',
            'concat',
            '-safe',
            "0",
            '-i',
            input_file,
            '-c',
            'copy',
            output_file
        ]
        subprocess.run(command)

    def _format_size(self, size):
        """格式化文件大小，返回合适的单位（字节、KB 或 MB）"""
        if size < 1024:
            return f"{size:.2f} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"