# coding: utf8

import json
import logging
import os
from common import flush_print
from common import MsgType, MediaInfo
from downloader import Downloader
from converter import Converter
from urllib.parse import urlparse, parse_qs, unquote
import copy
import re

logger = logging.getLogger('manager')


class Manager:
    def __init__(self, params):
        self.params = params
        self.convert_only = False

    def process(self):
        if 'downloader' not in self.params and 'converter' in self.params:
            logger.info('convert only')
            self.convert_only = True
            self.params['converter']['ffmpeg_location'] = self.params['ffmpeg_location']
            self.params['converter']['params_filepath'] = self.params['params_filepath']
        else:
            self._adjust_params()
            self.downloader = Downloader(self.params['downloader'])
            self.downloader.process()

            if 'playlist' in self.params['downloader'] and self.params['downloader']['playlist'] == 'true':
                return
            
            if 'sniff_only' in self.params['downloader'] and self.params['downloader']['sniff_only'] == 'true':
                return
            
            if self.params['converter']['input'] == 'downloader':
                self.params['converter']['input'] = self.downloader.get_downloaded_filepath()
                self.params['converter']['input_from_downloader'] = True

            # update save_path here for path contain unicode issue
            if self.params['converter']['save_path'] == 'downloader':
                self.params['converter']['save_path'] = os.path.dirname(self.downloader.get_downloaded_filepath())

            if self.params['downloader']['save_id3'] == 'true' and \
                    self.params['downloader']['media_type'] == 'audio':
                if 'audio' not in self.params['converter']:
                    self.params['converter']['audio'] = {}
                self.params['converter']['audio']['id3_info'] = self.downloader.get_id3_info()

            parsed = urlparse(self.params['downloader']['url'])
            qs = parse_qs(parsed.query)
            if 'segment_start' in qs:
                self.params['converter']['segment_start'] = qs['segment_start'][0]
            if 'segment_end' in qs:
                self.params['converter']['segment_end'] = qs['segment_end'][0]

        self.converter = Converter(self.params['converter'])
        if 'downloader' in self.params:
            self.converter.audio_bit_rate = self.downloader.audio_bit_rate
        self.converter.process()

        # run no command only, like mediainfo command
        if 'command' not in self.params['converter']:
            self._print_finish_info()

    def exitSubloop(self):
        if 'downloader' in self.params:
            self.downloader.stopLiveProgressTimer()

    def _adjust_params(self):
        if 'downloader' not in self.params:
            self.params['downloader'] = copy.deepcopy(self.params)
            self.params['downloader']['params_filepath'] = self.params['params_filepath']
            self.params['downloader']['log_path'] = self.params['log_path']

            if 'playlist' in self.params and self.params['playlist'] == 'true':
                return

            self.params['converter'] = {
                'ffmpeg_location': self.params['ffmpeg_location'],
                'input': 'downloader',
                'preset': 'downloader',
                'params_filepath': self.params['params_filepath'],
                'save_path': self.params['save_path']
            }
            self.params['downloader']['params_filepath'] = self.params['params_filepath']

            if self.params['media_type'] == 'audio':
                self.params['converter'] = {
                    'format': 'mp3',
                    'audio': {
                        'encoder': 'libmp3lame',
                        'channel': 'origin',
                        'sample_rate': 'origin',
                        'bit_rate': 'origin' if self.params['audio_quality'].upper == 'BEST' else self.params['audio_quality'][0:-3],
                    },
                }

            if self.params['media_type'] == 'video':
                self.params['converter'] = {
                    'format': 'mp4',
                    'video': {
                        'encoder': 'libx264',
                        'resolution': 'origin',
                        'frame_rate': 'origin',
                        'bit_rate': 'origin'
                    },
                    'audio': {
                        'encoder': 'aac',
                        'channel': 'origin',
                        'sample_rate': 'origin',
                        'bit_rate': 'origin'
                    }
                }

        elif 'downloader' in self.params:
            self.params['downloader']['log_path'] = self.params['log_path']
            self.params['downloader']['params_filepath'] = self.params['params_filepath']

            if 'sniff_only' in self.params['downloader'] and self.params['downloader']['sniff_only'] == 'true':
                return

            if 'playlist' in self.params['downloader'] and self.params['downloader']['playlist'] == 'true':
                return

            self.params['downloader']['ffmpeg_location'] = self.params['ffmpeg_location']

            self.params['converter']['ffmpeg_location'] = self.params['ffmpeg_location']
            self.params['converter']['params_filepath'] = self.params['params_filepath']

            if self.params['downloader']['media_type'] == 'audio':
                bit_rate = self.params['downloader']['audio_quality']
                if 'audio' not in self.params['converter']:
                    self.params['converter']['audio'] = {}
                self.params['converter']['audio']['bit_rate'] = 'origin' if bit_rate.upper() == 'BEST' else bit_rate[0:-3]

    # 有些视频文件下载后文件名不一致，则在已下载的文件目录下查找视频文件
    def _find_video_file(self, filepath):
        destpath = ''
        format_container = ['.m4a', '.mkv', '.mp4', '.ogg', '.webm', '.flv', '.unknown_video']
        dirname = os.path.dirname(filepath)
        for item in os.scandir(dirname):
            if item.is_file():
                for ft in format_container:
                    if item.path.endswith(ft):
                        destpath = item.path
        return destpath

    def _print_finish_info(self):
        self.exitSubloop()
        filepath = self.converter.get_converted_filepath()
        if not os.path.exists(filepath):
            video_name = self._find_video_file(filepath)
            if (len(video_name) > 0):
                filepath = video_name
            else:
                raise Exception("Video file does not exist!")

        mediainfo = MediaInfo(self.params['ffmpeg_location'], filepath)
        resolution = mediainfo.get_resolution()
        quality = mediainfo.get_quality()
        duration = mediainfo.get_duration()
        filetype = filepath[filepath.rfind('.')+1:].upper()

        if not self.convert_only:
            filepath = self.downloader.adjust_playlist_filepath(filepath)

        resp = {
            'type': MsgType.finished.value,
            'msg': {
                'duration': str(duration),
                'filetype': filetype,
                'quality': quality,
                'filesize': str(os.path.getsize(filepath)),
                'filepath': filepath,
                'resolution': resolution,
                'ret_code': '0',
            },
        }

        if not self.convert_only:
            if 'lyric' in self.params['downloader']:
                resp['msg']['lyric'] = self.downloader.get_subtitle_filepath()
            else:
                resp['msg']['subtitle'] = self.downloader.get_subtitle_filepath()

        flush_print(json.dumps(resp))

        resp = {
            'type': MsgType.sleep.value,
            'msg': {
                'ret_code': '0'
            },
        }
        flush_print(json.dumps(resp))