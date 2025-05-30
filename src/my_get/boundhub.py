#********************************************************************************************
# https://www.boundhub.com/
#********************************************************************************************

from bs4 import BeautifulSoup
import time
import re
import json
import os
import signal
from common import MsgType, flush_print, sanitize_filename
import logging
from curlx import CurlX


logger = logging.getLogger('boundhub')

class BoundhubAdaptor:
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
        self.over_write = True

        self.session = CurlX(proxies=proxies, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'accept': '*/*'
        })

    def extract(self):
        try:
            original_url = self.params['url']
            response = self.session.get(original_url)            
            soup = BeautifulSoup(response.text, 'html.parser')    
                   
            tag_title = soup.find('title')
            if tag_title:
                title = sanitize_filename(tag_title.get_text())
            else:
                title = f"Boundhub-{int(time.time())}"

            tag_scripts = soup.find_all('script')
            for script in tag_scripts:
                script_text = script.get_text()
                match = re.search(r"var flashvars = ({.*?});", script_text, re.DOTALL)
                if match:
                    flashvars_text = match.group(1)
                    flashvars_text = flashvars_text.replace('\t', '').replace('\n', '')
                    flashvars_text = re.sub(r"(\b\w+\b):", r'"\1":', flashvars_text)
                    flashvars_dict = eval(flashvars_text)                
                    thumbnail_url = flashvars_dict['preview_url'].replace('\"', '')

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

                    file_path = f'{self.params["save_path"]}/{title}'
                    max_path = 180
                    if len(file_path) > max_path:
                        file_path = file_path[0:max_path]
                        title = os.path.basename(file_path)

                    self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                    video_url = flashvars_dict['video_url'].replace('\"', '')
                    self._download(video_url, self.final_location)
                    break
        except Exception as e:
            logger.info(f"parse html failed: {e}")

    def _download(self, url, output):        
        # Register signal handlers for graceful termination
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # 检查是否有部分下载的文件
            downloaded_size = 0
            if os.path.exists(output):
                downloaded_size = os.path.getsize(output)

            # 获取文件大小
            response = self.session.get(url, stream=True)
            file_size = int(response.headers.get("content-length", 0))
            if file_size == 0:
                raise Exception('Download Error: file size is 0')

            if file_size == downloaded_size:
                if self.over_write:
                    os.remove(output)
                    downloaded_size = 0
                else:
                    logger.info("Skip the download, the file is already exist")
                    return

            # 设置请求头的Range字段以支持断点续传
            headers = self.session.headers.copy()
            if downloaded_size > 0:
                headers['Range'] = f"bytes={downloaded_size}-"

            # 发起请求
            response = self.session.get(url, stream=True, headers=headers)
            
            # 记录开始时间
            start_time = time.time()

            # 写入文件并显示进度
            with open(output, "ab") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.stop_event:  # 检查是否有停止信号
                        logger.info("abort download")
                        break
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)

                        # 计算下载速度
                        elapsed_time = time.time() - start_time
                        speed = downloaded_size / elapsed_time
                        percent_complete = downloaded_size / file_size
                        remaining_size = file_size - downloaded_size
                        remaining_time = remaining_size / speed if speed > 0 else 0  # 秒

                        flush_print(json.dumps({
                                'type': MsgType.downloading.value,
                                'msg': {
                                    'progress': str('{0:.3f}'.format(percent_complete)),
                                    'speed': self._format_size(speed),
                                    'filesize': str(file_size),
                                    'eta': str(remaining_time),
                                }
                        }))

        except Exception as e:
            raise Exception(f"Download Error: {e}")
        
    def _signal_handler(self, signum, frame):
        logger.info(f"signal_handler {signum}")
        self.stop_event = True
    
    def _format_size(self, size):
        """格式化文件大小，返回合适的单位（字节、KB 或 MB）"""
        if size < 1024:
            return f"{size:.2f} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"