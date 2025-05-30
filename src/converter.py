# coding: utf8

import logging
import os
from io import TextIOWrapper
import subprocess
from common import MsgType, MediaInfo, convert_size
from common import flush_print, get_encoder_codec_names, dict_merge
import json
from time import strftime, gmtime, time
import base64

logger = logging.getLogger('converter')


class Converter():
    def __init__(self, params):
        self.params = params

        if 'preset' in params and params['preset'] != 'downloader':
            with open(params['preset']) as json_file:
                encode_params = json.load(json_file)

            # for customer encode params
            dict_merge(encode_params, self.params)
            dict_merge(self.params, encode_params)

        self._adjust_params()

        self.input_file = self.params['input']
        self.input_format_names = self.input_file[self.input_file.rfind('.')+1:]

        self.v_need_encode = False
        self.a_need_encode = False
        self.ffmpeg_inputs = []
        self.ffmpeg_vfilter = []
        self.ffmpeg_afilter = []
        self.ffmpeg_encoder = []
        self.ffmpeg_maps = []
        self.ffmpeg_output = []
        self.exist_id3_cover = False
        self.adjust_output_filename = False
        self.audio_bit_rate = ''

    def process(self):
        if 'command' in self.params and self.params['command'] == 'mediainfo':
            files = self.params['input'].split(';')
            for file in files:
                self.input_file = file
                self._set_input_mediainfo()
                self._print_mediainfo()
            return

        # set input file mediainfo
        logger.info('start set input file mediainfo')
        self._set_input_mediainfo()
        logger.info('set input file mediainfo succeed')

        # convert video
        logger.info('start converting video')
        self._convert()
        logger.info('convert video succeed')

    def get_converted_filepath(self):
        return self.converted_filepath

    def _adjust_params(self):
        if 'video' in self.params:
            if self.params['video']['bit_rate'].find('Kb/s') != -1:
                self.params['video']['bit_rate'] = self.params['video']['bit_rate'][0:-3]

        if 'audio' in self.params:
            if self.params['audio']['bit_rate'].find('Kb/s') != -1:
                self.params['audio']['bit_rate'] = self.params['audio']['bit_rate'][0:-3]

    def _set_input_mediainfo(self):
        self.input_file_mediainfo = MediaInfo(self.params['ffmpeg_location'], self.input_file)

    def _print_mediainfo(self):
        if self.input_file_mediainfo.get_duration() == 0:
            resp = {
                'type': 'mediainfo',
                'msg': {
                    'ret_code': '-1',
                },
            }
            return flush_print(json.dumps(resp))

        mediainfo = {
            'format': self.input_format_names.upper(),
            'duration': strftime("%M:%S", gmtime(self.input_file_mediainfo.get_duration())),
            'size': convert_size(os.path.getsize(self.input_file)),
            'quality': self.input_file_mediainfo.get_resolution(),
            'thumbnail': self._get_thumbnail(),
            'ret_code': '0',
        }
        if self.input_file_mediainfo.get_duration() > 3600:
            mediainfo['duration'] = strftime("%H:%M:%S", gmtime(self.input_file_mediainfo.get_duration()))

        if mediainfo['quality'] == '0x0':
            mediainfo['quality'] = self.input_file_mediainfo.get_quality()

        resp = {
            'type': 'mediainfo',
            'msg': mediainfo,
        }
        flush_print(json.dumps(resp))

    def _get_thumbnail(self):
        try:
            thumbnail = os.path.join(os.path.dirname(self.params['params_filepath']), f'{int(time()*1000)}.jpg')
            command = [os.path.join(self.params['ffmpeg_location'], 'ffmpeg'), '-i', self.input_file, '-vf', 'scale=100:-1', '-y', thumbnail]
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            for line in TextIOWrapper(p.stderr, encoding="utf-8"):
                continue

            if os.path.exists(thumbnail):
                with open(thumbnail, 'rb') as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                os.remove(thumbnail)
                return encoded_string
            return ''
        except Exception as e:
            return ''

    def _need_convert(self):
        if self.params['isNeedConvert'] == 'false':
            return False

        if 'video' in self.params:
            input_vcodec = self.input_file_mediainfo.get_codec('video')
            v_codec_names = get_encoder_codec_names(self.params['video']['encoder'])
            if not v_codec_names:
                return True
            if input_vcodec not in v_codec_names:
                return True

            if self.params['video']['resolution'] != 'origin':
                return True

        if 'audio' in self.params:
            input_acodec = self.input_file_mediainfo.get_codec('audio')
            a_codec_names = get_encoder_codec_names(self.params['audio']['encoder'])
            if not a_codec_names:
                return True
            if input_acodec not in a_codec_names:
                return True
            if self.params['audio']['bit_rate'] != 'origin':
                if len(self.audio_bit_rate) == 0 or self.params['audio']['bit_rate'] != self.audio_bit_rate:
                    return True

        if self.params['format'] != self.input_format_names:
            return True

        if os.path.dirname(self.input_file) != self.params['save_path']:
            return True

        if 'segment_start' in self.params:
            return True 

        return False

    def _resize_image(self, filepath, width=300, height=-1):
        command = [os.path.join(self.params['ffmpeg_location'], 'ffmpeg')]
        output = os.path.join(os.path.dirname(filepath), f'{int(time()*1000)}.{filepath[filepath.rfind(".")+1:]}')
        command += ['-i', filepath, '-vf', f'scale={width}:{height}', '-y', output]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in TextIOWrapper(p.stderr, encoding="utf-8"):
            continue
        return output

    def _set_ffmpeg_inputs(self):
        self.ffmpeg_inputs = ['-i', self.input_file]
        if 'convert_percent_limit' in self.params:
            self.convert_duration = float(self.params['convert_percent_limit']) * self.input_file_mediainfo.get_duration()
            format = os.path.splitext(self.input_file)[-1].lower()
            if (format != ".avi"):
                self.ffmpeg_inputs = ['-ss', '0', '-t', str(self.convert_duration), '-i', self.input_file]
            else:
                self.ffmpeg_inputs = ['-ss', '1', '-t', str(self.convert_duration), '-i', self.input_file]
            self.v_need_encode = True 
            self.a_need_encode = True 
        
        if 'segment_start' in self.params:
            self.convert_duration = int(self.params['segment_end']) - int(self.params['segment_start'])
            self.ffmpeg_inputs = ['-ss', str(self.params['segment_start']), '-t', str(self.convert_duration), '-i', self.input_file]
            self.v_need_encode = True
            self.a_need_encode = True

        self.ffmpeg_maps = ['-map', '0:a']

        if self.params['format'] == 'mp3' and 'id3_info' in self.params['audio'] and 'cover' in self.params['audio']['id3_info']:
            cover = self._resize_image(self.params['audio']['id3_info']['cover'])
            if os.path.exists(cover):
                self.ffmpeg_inputs += ['-i', cover]
                self.ffmpeg_maps += ['-map', '1:v']
                self.exist_id3_cover = True

    def _set_ffmpeg_filters(self):
        self.ffmpeg_vfilter = ['-vf']
        if 'video' in self.params:
            video = self.params['video']
            if video['resolution'] != 'origin':
                self.v_need_encode = True
                if self.params['format'] != '3gp':
                    file_width = self.input_file_mediainfo.get_width()
                    file_height = self.input_file_mediainfo.get_height()
                    width = int(video['resolution'].split('x')[0])
                    height = int(video['resolution'].split('x')[1])
                    if file_width > file_height:
                        self.ffmpeg_vfilter += [f'scale=-2:{height}']
                    else:
                        self.ffmpeg_vfilter += [f'scale={height}:-2']
                else:
                    self.ffmpeg_vfilter += [f'scale={video["resolution"]}']

        if len(self.ffmpeg_vfilter) == 1:
            self.ffmpeg_vfilter = []

    def _set_ffmpeg_encoder(self):
        self.ffmpeg_encoder = []
        if 'video' in self.params:
            video = self.params['video']
            input_vcodec = self.input_file_mediainfo.get_codec('video')
            v_codec_names = get_encoder_codec_names(video['encoder'])

            encode_params = []

            if self.params['format'] != self.input_format_names:
                self.v_need_encode = True

            if (self.input_format_names == 'flv' or self.input_format_names == 'mkv') and self.params['format'] == 'mp4':
                self.v_need_encode = False

            if video['frame_rate'] != 'origin':
                encode_params += ['-r', video['frame_rate']]
                self.v_need_encode = True

            if video['bit_rate'] != 'origin':
                encode_params += ['-b:v', video['bit_rate']]
                self.v_need_encode = True

            if v_codec_names and input_vcodec not in v_codec_names:
                self.v_need_encode = True
            
            if len(self.ffmpeg_vfilter) > 0:
                self.v_need_encode = True

            # skip 4k+ encode while input file from downloader, 4k video height is 2160
            if self.params.get('input_from_downloader') and self.input_file_mediainfo.get_height() > 2160:
                self.v_need_encode = False

            if not self.v_need_encode:
                video['encoder'] = 'copy'
            
            self.ffmpeg_encoder += ['-c:v', video['encoder']]
            if self.v_need_encode:
                self.ffmpeg_encoder += encode_params

            if video['encoder'] == 'libx264':
                self.ffmpeg_encoder += ['-preset', 'veryfast', '-profile:v', 'main', '-level', '3.1', '-pix_fmt', 'yuv420p']

            if video['encoder'] == 'wmv2':
                self.ffmpeg_encoder += ['-qscale', '3']

        if 'audio' in self.params:
            audio = self.params['audio']

            if audio['encoder'] == 'none':
                self.ffmpeg_encoder += ['-an']
            else:
                input_acodec = self.input_file_mediainfo.get_codec('audio')
                a_codec_names = get_encoder_codec_names(audio['encoder'])

                encode_params = []

                if self.params['format'] != self.input_format_names:
                    self.a_need_encode = True

                if (self.input_format_names == 'flv' or self.input_format_names == 'mkv') and self.params['format'] == 'mp4':
                    self.a_need_encode = False

                if audio['channel'] != 'origin':
                    encode_params += ['-ac', audio['channel']]
                    self.a_need_encode = True

                if audio['sample_rate'] != 'origin':
                    encode_params += ['-ar', audio['sample_rate']]
                    self.a_need_encode = True

                if audio['bit_rate'] != 'origin':
                    encode_params += ['-b:a', audio['bit_rate']]
                    self.a_need_encode = True
                else:
                    if len(self.audio_bit_rate) > 0 and int(self.audio_bit_rate[0:-1]) > 128:
                        if self.params['format'] == 'mp3':
                            encode_params += ['-b:a', '320k']
                        else:
                            encode_params += ['-b:a', self.audio_bit_rate]
                    self.v_need_encode = True

                if a_codec_names and input_acodec not in a_codec_names:
                    self.a_need_encode = True

                if not self.a_need_encode:
                    audio['encoder'] = 'copy'

                if audio['encoder'] == 'aac':
                    audio['encoder'] = 'libfdk_aac'

                self.ffmpeg_encoder += ['-c:a', audio['encoder']]
                if self.a_need_encode:
                    self.ffmpeg_encoder += encode_params

                # if self.params['format'] == 'mp3' and 'id3_info' in audio:
                if self.params['format'] == 'mp3':
                    if 'id3_info' in audio and len(audio['id3_info']) > 0:
                        id3_info = audio['id3_info']
                        if 'album' in id3_info:
                            self.ffmpeg_encoder += ['-metadata', f'album={id3_info["album"]}']
                        if 'artist' in id3_info:
                            self.ffmpeg_encoder += ['-metadata', f'artist={id3_info["artist"]}']
                        if 'title' in id3_info:
                            self.ffmpeg_encoder += ['-metadata', f'title={id3_info["title"]}']
                        if 'date' in id3_info:
                            self.ffmpeg_encoder += ['-metadata', f'date={id3_info["date"]}']
                    else:
                        self.ffmpeg_encoder += ['-map_metadata', '0', '-id3v2_version', '3', '-write_id3v1', '1']
                        self.exist_id3_cover = True

        if ('video' not in self.params and not self.exist_id3_cover) or ('video' in self.params and self.input_format_names == "mp3"):
            self.ffmpeg_encoder += ['-vn']

    def _set_ffmpeg_output(self):
        filename = os.path.basename(self.input_file)
        converted_filename = filename[0:filename.rfind('.')] + '.' + self.params['format']
        if os.path.normpath(self.input_file) == os.path.normpath(os.path.join(self.params['save_path'], converted_filename)) and self._need_convert():
            converted_filename = '_' + converted_filename
            self.adjust_output_filename = True
        self.converted_filepath = os.path.normpath(os.path.join(self.params['save_path'], converted_filename))
        self.ffmpeg_output = ['-y', self.converted_filepath]

    def _convert(self):
        resp = {
            'type': MsgType.converting.value,
            'msg': {
                'progress': '0'
            },
        }
        flush_print(json.dumps(resp))

        if not self._need_convert():
            self.converted_filepath = self.input_file
        else:
            self.convert_duration = self.input_file_mediainfo.get_duration()
            self._set_ffmpeg_inputs()
            self._set_ffmpeg_filters()
            self._set_ffmpeg_encoder()
            self._set_ffmpeg_output()

            command = [os.path.join(self.params['ffmpeg_location'], 'ffmpeg')]

            command += self.ffmpeg_inputs + self.ffmpeg_vfilter + self.ffmpeg_afilter + self.ffmpeg_encoder

            # more than one file
            if len(self.ffmpeg_maps) / 2 > 1:
                command += self.ffmpeg_maps

            command += self.ffmpeg_output

            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                for line in TextIOWrapper(p.stderr, encoding="utf-8"):
                    if line.startswith('frame') or line.startswith('size'):
                        arr = line.split(' ')
                        for item in arr:
                            if item.startswith('time'):
                                timestr = item.split('=')[1]
                                ftr = [3600, 60, 1]
                                second = sum([a*b for a, b in zip(ftr, map(float, timestr.split(':')))])
                                progress = second / self.convert_duration
                                if progress > 1:
                                    progress = 1
                                resp = {
                                    'type': MsgType.converting.value,
                                    'msg': {
                                        'pid': str(p.pid),
                                        'progress': str('{0:.3f}'.format(progress))
                                    },
                                }
                                flush_print(json.dumps(resp))
                    else:
                        logger.info('ffmpeg output: ' + line)
            except Exception as e:
                logger.info('ffmpeg progress output exception')

            p.wait()

        if self.adjust_output_filename:
            os.replace(self.converted_filepath, self.input_file)
            self.converted_filepath = self.input_file

        resp = {
            'type': MsgType.converted.value,
            'msg': {
                'ret_code': '0'
            },
        }
        flush_print(json.dumps(resp))
