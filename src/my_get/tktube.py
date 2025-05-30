#********************************************************************************************
# https://tktube.com/ja
#********************************************************************************************

from bs4 import BeautifulSoup
import time
import re
import json
import os
import signal
from common import MsgType, flush_print, sanitize_filename
import logging
import sys
import threading
from curlx import CurlX


logger = logging.getLogger('tktube')

class TktubeAdaptor:
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
        self.over_write = True
        self.max_threads = 4
        self.is_multi_download = True

        if self.is_multi_download:
            self.stop_event = threading.Event()
            self.lock = threading.Lock()  # 用于线程安全的变量更新
        else:
            self.stop_event = False

        self.session = CurlX(proxies=proxies, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'accept': '*/*',
            'Connection': 'keep-alive'
        })

    def extract(self):
        try:
            original_url = self.params['url']
            response = self.session.get(original_url)

            soup = BeautifulSoup(response.text, 'html.parser')
            tag_scripts = soup.find_all('script')

            for script in tag_scripts:
                script_text = script.get_text()
                match = re.search(r"var flashvars = ({.*?});", script_text, re.DOTALL)
                if match:
                    flashvars_text = match.group(1)
                    flashvars_text = flashvars_text.replace('\t', '').replace('\n', '')
                    flashvars_text = re.sub(r"(\b\w+\b):", r'"\1":', flashvars_text)
                    try:
                        flashvars_dict = eval(flashvars_text)
                    except Exception as e:
                        raise("decode flashvars_text error")
                    
                    title = sanitize_filename(flashvars_dict['video_title'])
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
                    video_url = flashvars_dict['video_alt_url'].replace('\"', '')
                    # 多线程下载
                    if self.is_multi_download:
                        self._multi_download(video_url, self.final_location)
                    else:
                        self._single_download(video_url, self.final_location)
                    break
        except Exception as e:
            logger.info(f"parse html failed: {e}")

    def _download_chunk(self, url, start, end, output, chunk_index, progress):
        try:
            headers = {'Range': f"bytes={start}-{end}"}
            response = self.session.get(url, headers=headers, stream=True)
            chunk_file = f"{output}.part{chunk_index}"

            with open(chunk_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.stop_event.is_set():
                        return
                    if chunk:
                        file.write(chunk)
                        with self.lock:  # 确保线程安全地更新下载进度
                            progress['downloaded'] += len(chunk)
        except Exception as e:
            logger.info(f"download chunk failed: {e}")

    def _merge_chunks(self, output, total_chunks):
        with open(output, "wb") as final_file:
            for i in range(total_chunks):
                chunk_file = f"{output}.part{i}"
                with open(chunk_file, "rb") as file:
                    final_file.write(file.read())
                os.remove(chunk_file)  # 删除临时分片文件

    def _print_progress(self, progress, file_size, start_time):
        while not self.stop_event.is_set():
            with self.lock:
                downloaded = progress['downloaded']
                percent_complete = downloaded / file_size
                elapsed_time = time.time() - start_time
                if elapsed_time == 0:
                    elapsed_time = 0.1
                speed = downloaded / elapsed_time if elapsed_time > 0 else 0  # 每秒字节数
                remaining_size = file_size - downloaded
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

            if downloaded >= file_size:  # 下载完成
                break
            time.sleep(1)

    def _multi_download(self, url, output):
        try:
            # 获取文件总大小
            response = self.session.get(url, stream=True)
            file_size = int(response.headers.get("content-length", 0))
            if file_size == 0:
                raise Exception("Download Error: File size is 0")

            if os.path.exists(output):
                downloaded_size = os.path.getsize(output)
                if downloaded_size == file_size:
                    if self.over_write:
                        os.remove(output)
                    else:
                        logger.info("File already exists, skipping download")
                        return

            # 分片大小和数量
            chunk_size = file_size // self.max_threads
            progress = {'downloaded': 0}
            threads = []
            start_time = time.time()

            # 启动进度显示线程
            progress_thread = threading.Thread(target=self._print_progress, args=(progress, file_size, start_time))
            progress_thread.start()

            # 启动分片下载线程
            for i in range(self.max_threads):
                start = i * chunk_size
                end = start + chunk_size - 1 if i < self.max_threads - 1 else file_size - 1
                thread = threading.Thread(target=self._download_chunk, args=(url, start, end, output, i, progress))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            self.stop_event.set()  # 停止进度显示线程
            progress_thread.join()

            # 合并分片
            self._merge_chunks(output, self.max_threads)
            logger.info("Download completed")

        except Exception as e:
            raise Exception(f"Download Error: {e}")

    def _single_download(self, url, output):        
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
            response.raise_for_status()

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
                        cur_time = time.time()
                        elapsed_time = cur_time - start_time
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
        if self.is_multi_download:
            self.stop_event.set()
        else:
            self.stop_event = True
    
    def _format_size(self, size):
        """格式化文件大小，返回合适的单位（字节、KB 或 MB）"""
        if size < 1024:
            return f"{size:.2f} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"
        

