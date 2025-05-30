import requests
import json
from base64 import b64decode
import xml.etree.ElementTree as ET
import os
from common import MsgType, flush_print, sanitize_filename
import logging
import signal
import time


logger = logging.getLogger('netflix')

class NetFlixAdaptor:
    def __init__(
        self,
        params,
        progress_hook,
        proxies
    ):
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies

        self.metadata = json.loads(b64decode(self.params['metadata']).decode('utf-8'))
        self.ffmpeg_location = params['ffmpeg_location']
        self.final_location = None
        self.stop_event = False
        self.over_write = True

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'accept': '*/*'
        })

    def extract(self):   
        video_title = sanitize_filename(self.metadata['title'])
        video_url = self.metadata['videoUrl']
        audio_url = self.metadata['audioUrl']
        subtitle_url = self.metadata['subtitleUrl']
        save_path = self.params['save_path']

        complete_save_path = os.path.join(save_path, video_title)
        max_path = 180
        if (len(complete_save_path) > max_path):
            complete_save_path = complete_save_path[0:max_path]
            video_title = os.path.basename(complete_save_path)

        # 下载字幕
        try:
            if len(subtitle_url) > 0:
                subtile_xml = os.path.join(save_path, f'{video_title}.xml')
                self._download(subtitle_url, subtile_xml, False)
                subtile_srt = os.path.join(save_path, f'{video_title}.srt')
                self._xml_to_srt(subtile_xml, subtile_srt)
        except:
            pass

        # 下载音频
        self._download(audio_url, os.path.join(save_path, f'{video_title}.m4a'), False)

        # 下载视频
        video_save_path = os.path.join(save_path, f'{video_title}_encrypt.mp4')
        self._download(video_url, video_save_path)

        self.final_location = video_save_path

    def _download(self, url, output, log_progress: bool = True):
        # Register signal handlers for graceful termination
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # 检查是否有部分下载的文件
            downloaded_size = 0
            if os.path.exists(output):
                downloaded_size = os.path.getsize(output)

            # 获取文件大小
            response = self.session.get(url, stream=True, proxies=self.proxies)
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
            response = self.session.get(url, stream=True, headers=headers, proxies=self.proxies)
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
                        elapsed_time = time.time() - start_time
                        speed = downloaded_size / elapsed_time
                        percent_complete = downloaded_size / file_size
                        remaining_size = file_size - downloaded_size
                        remaining_time = remaining_size / speed if speed > 0 else 0  # 秒

                        if log_progress:
                            flush_print(json.dumps({
                                    'type': MsgType.downloading.value,
                                    'msg': {
                                        'progress': str('{0:.3f}'.format(percent_complete)),
                                        'speed': self._format_size(speed),
                                        'filesize': str(file_size),
                                        'eta': str(remaining_time),
                                    }
                            }))

        except requests.exceptions.RequestException as e:
            raise Exception(f"Download Error: {e}")
        
    def _signal_handler(self, signum, frame):
        logger.info(f"signal_handler {signum}")
        self.stop_event = True
    
    def _xml_to_srt(self, xml_path, srt_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.info(f"Failed to parse XML file: {e}")
            return

        # Extract the namespace
        namespace = "{" + root.tag.split('}')[0].strip('{') + "}"

        try:
            with open(srt_path, "w", encoding="utf-8") as srt_file:
                subtitle_index = 1
                for p in root.findall(f".//{namespace}p"):
                    begin_time = p.attrib.get("begin")
                    end_time = p.attrib.get("end")

                    if begin_time and end_time:
                        srt_file.write(f"{subtitle_index}\n")
                        srt_file.write(f"{self._ticks_to_srt_time(begin_time)} --> {self._ticks_to_srt_time(end_time)}\n")

                        subtitle_text = ""
                        for elem in p.iter():
                            if elem.tag.endswith("br"):
                                subtitle_text += "\n"
                            elif elem.text:
                                subtitle_text += elem.text

                        srt_file.write(f"{subtitle_text.strip()}\n\n")
                        subtitle_index += 1

        except IOError as e:
            logger.info(f"Failed to write to SRT file: {e}")

    def _format_size(self, size):
        """格式化文件大小，返回合适的单位（字节、KB 或 MB）"""
        if size < 1024:
            return f"{size:.2f} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"

    def _ticks_to_srt_time(self, ticks_str):
        """将时间从 XML 格式 (秒) 转换为 SRT 格式 (00:00:00,000)"""
        ticks = int(ticks_str[:-1])  # Remove the last character and convert to integer
        total_milliseconds = ticks // 10000
        hours = total_milliseconds // (1000 * 60 * 60)
        minutes = (total_milliseconds % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (total_milliseconds % (1000 * 60)) // 1000
        milliseconds = total_milliseconds % 1000

        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

