# coding: utf8

from enum import Enum
import subprocess
import json
import os
import sys
import collections
import math
from slugify import slugify
import webvtt
import html
from pysrt.srtitem import SubRipItem
from pysrt.srttime import SubRipTime
from vtt_to_srt.vtt_to_srt import vtt_to_srt
import re
from urllib.parse import urlparse, urlunparse, quote
import tempfile
import secrets
import time


def flush_print(data):
    print('\n' + data + '\n')
    #sys.stderr.write('\r\n'+data+'\r\n')
    sys.stdout.flush()


class MsgType(Enum):
    param = 'param'
    sniff = 'sniff'
    playlist = 'playlist'
    downloading = 'downloading'
    fixing = 'fixing'
    converting = 'converting'
    converted = 'converted'
    finished = 'finished'
    sleep = 'sleep'


def get_encoder_codec_names(encoder):
    try:
        codec_names = {
            'libx264': ['h264', 'avc1'],
            'libx265': ['h265', 'hevc'],
            'libmp3lame': ['mp3'],
            'aac': ['aac'],
        }

        return codec_names[encoder]
    except Exception as e:
        return None


class MediaInfo():
    def __init__(self, ffmpeg_location, filepath):
        self.ffmpeg_location = ffmpeg_location
        self.filepath = filepath
        self.mediainfo = self._get_mediainfo()

    def get_codec(self, type):
        try:
            streams = self.mediainfo['streams']

            for stream in streams:
                if stream['codec_type'] == type:
                    return stream['codec_name']
        except Exception as e:
            return None

    def get_resolution(self):
        try:
            streams = self.mediainfo['streams']

            for stream in streams:
                if stream['codec_type'] == 'video':
                    return f"{stream['width']}x{stream['height']}"
            return '0x0'
        except Exception as e:
            return '0x0'

    def get_quality(self):
        try:
            streams = self.mediainfo['streams']

            for stream in streams:
                if stream['codec_type'] == 'audio':
                    if not 'bit_rate' in stream:
                        return f"{int(int(self.mediainfo['format']['bit_rate'])/1000)}Kb/s"
                    else:
                        bit_rate = int(int(stream['bit_rate'])/1000)
                        if bit_rate < 20:
                            return f"{int(int(self.mediainfo['format']['bit_rate'])/1000)}Kb/s"
                        else:
                            return f"{bit_rate}Kb/s"
        except Exception as e:
            return None

    def get_duration(self):
        try:
            return int(float(self.mediainfo['format']['duration']))
        except Exception as e:
            return 0

    def get_format_names(self):
        try:
            return self.mediainfo['format']['format_name'].split(',')
        except Exception as e:
            return None

    def get_width(self):
        if 'streams' in self.mediainfo:
            streams = self.mediainfo['streams']
            for stream in streams:
                if stream['codec_type'] == 'video':
                    return int(stream['width'])
        return 0

    def get_height(self):
        if 'streams' in self.mediainfo:
            streams = self.mediainfo['streams']
            for stream in streams:
                if stream['codec_type'] == 'video':
                    return int(stream['height'])
        return 0

    def get_audio_bitrate(self):
        if 'streams' in self.mediainfo:
            streams = self.mediainfo['streams']
            for stream in streams:
                if stream['codec_type'] == 'audio':
                    return int(int(stream['bit_rate'])/1000)
        return 0

    def _get_mediainfo(self):
        command = [
            os.path.join(self.ffmpeg_location, 'ffprobe'),
            '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', self.filepath
        ]

        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.stdout.read().decode('utf-8')
        return json.loads(output)


# copy from: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s%s" % (s, size_name[i])


formats = {
    0: "track_name",
    1: "artist",
    2: "album",
    3: "album_artist",
    4: "genre",
    5: "disc_number",
    6: "duration",
    7: "year",
    8: "original_date",
    9: "track_number",
    10: "total_tracks",
    11: "isrc",
    12: "track_id",
}


def format_string(
    string_format, tags, slugification=False, force_spaces=False, total_songs=0
):
    """ Generate a string of the format '[artist] - [song]' for the given spotify song. """
    format_tags = dict(formats)
    format_tags[0] = tags["name"]
    format_tags[1] = tags["artists"][0]["name"]
    format_tags[2] = tags["album"]["name"]
    format_tags[3] = tags["artists"][0]["name"]
    format_tags[4] = tags["genre"]
    format_tags[5] = tags["disc_number"]
    format_tags[6] = tags["duration"]
    format_tags[7] = tags["year"]
    format_tags[8] = tags["release_date"]
    format_tags[9] = tags["track_number"]
    format_tags[10] = tags["total_tracks"]
    format_tags[11] = tags["external_ids"]["isrc"]
    try:
        format_tags[12] = tags["id"]
    except KeyError:
        pass

    format_tags_sanitized = {
        k: sanitize_title(str(v), ok="'-_()[]{}") if slugification else str(v)
        for k, v in format_tags.items()
    }
    # calculating total digits presnet in total_songs to prepare a zfill.
    total_digits = 0 if total_songs == 0 else int(math.log10(total_songs)) + 1

    for x in formats:
        format_tag = "{" + formats[x] + "}"
        # Making consistent track number by prepending zero
        # on it according to number of digits in total songs
        if format_tag == "{track_number}":
            format_tags_sanitized[x] = format_tags_sanitized[x].zfill(total_digits)

        string_format = string_format.replace(format_tag, format_tags_sanitized[x])

    return string_format


def get_sec(time_str):
    if ":" in time_str:
        splitter = ":"
    elif "." in time_str:
        splitter = "."
    else:
        raise ValueError(
            "No expected character found in {} to split" "time values.".format(time_str)
        )
    v = time_str.split(splitter, 3)
    v.reverse()
    sec = 0
    if len(v) > 0:  # seconds
        sec += int(v[0])
    if len(v) > 1:  # minutes
        sec += int(v[1]) * 60
    if len(v) > 2:  # hours
        sec += int(v[2]) * 3600
    return sec


def extract_spotify_id(raw_string):
    """
    Returns a Spotify ID of a playlist, album, etc. after extracting
    it from a given HTTP URL or Spotify URI.
    """

    if "/" in raw_string:
        # Input string is an HTTP URL
        if raw_string.endswith("/"):
            raw_string = raw_string[:-1]
        # We need to manually trim additional text from HTTP URLs
        # We could skip this if https://github.com/plamere/spotipy/pull/324
        # gets merged,
        to_trim = raw_string.find("?")
        if not to_trim == -1:
            raw_string = raw_string[:to_trim]
        splits = raw_string.split("/")
    else:
        # Input string is a Spotify URI
        splits = raw_string.split(":")

    spotify_id = splits[-1]

    return spotify_id


def sanitize_title(title, ok=".-_()[]{}"):
    """ Generate filename to be downloaded. """
    if sys.version_info >= (3, 8):
        title = slugify(title, lowercase=False, allow_unicode=True)
    else:
        title = title.replace(" ", "_")
        title = title.replace(":", "_")
        # replace slashes with "-" to avoid folder creation errors
        title = title.replace("/", "-").replace("\\", "-")
        # slugify removes any special characters
        title = slugify(title, ok=ok, lower=False, spaces=True)
    return title

def sanitize_filename(title):
    valid_filename = re.sub(r'<[^>]+>', '', title)
    valid_filename = re.sub(r'[\/:*?"<>|\\\r\n]', '', valid_filename)
    valid_filename = valid_filename.strip()
    return valid_filename

def vtt2lrc(vtt_file):
    lrc = ''
    for caption in webvtt.read(vtt_file):
        lrc += f'[{caption.start}]{caption.text}\n'
    vtt_filename = os.path.basename(vtt_file)
    vtt_dirname = os.path.dirname(vtt_file)
    lrc_file = os.path.join(vtt_dirname, vtt_filename[0:vtt_filename.rfind('.')+1] + 'lrc')
    f = open(lrc_file, 'w', encoding='utf-8')
    f.write(lrc)
    f.close()
    return lrc_file


def vtt2srt(vtt_file):
    vtt_filename = os.path.basename(vtt_file)
    vtt_dirname = os.path.dirname(vtt_file)
    srt_file = os.path.join(vtt_dirname, vtt_filename[0:vtt_filename.rfind('.')+1] + 'srt')
    srt = open(srt_file, 'w', encoding='utf-8')

    index = 0
    for caption in webvtt.read(vtt_file):
        index += 1
        start = SubRipTime(0, 0, caption.start_in_seconds)
        end = SubRipTime(0, 0, caption.end_in_seconds)
        srt.write(SubRipItem(index, start, end, html.unescape(caption.text)).__str__()+'\n')

    return srt_file


def vtt2srt2(vtt_file):
    vtt_to_srt(vtt_file) # 没有数字编号
    vtt_filename = os.path.basename(vtt_file)
    vtt_dirname = os.path.dirname(vtt_file)
    srt_file = os.path.join(vtt_dirname, vtt_filename[0:vtt_filename.rfind('.')+1] + 'srt')
    return srt_file

def lrc2srt(lrc_content):
    srt_content = ""
    index = 1

    # 正则表达式匹配 LRC 的时间戳部分
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')

    for line in lrc_content.splitlines():
        match = pattern.match(line)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3)

            start_time = f"{minutes:02}:{int(seconds):02},{int((seconds - int(seconds)) * 1000):03}"
            end_minutes = (minutes + (seconds + 5) // 60) % 60
            end_seconds = (seconds + 5) % 60
            end_time = f"{int(end_minutes):02}:{int(end_seconds):02},{int((end_seconds - int(end_seconds)) * 1000):03}"

            srt_content += f"{index}\n"
            srt_content += f"00:{start_time} --> 00:{end_time}\n"
            srt_content += f"{text.strip()}\n\n"
            index += 1

    return srt_content

def filter_emoji(desstr, restr=''):
    # 过滤表情
    try:
        co = re.compile(u'[\U00010000-\U0010ffff]')
    except re.error:
        co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
    return co.sub(restr, desstr)

def wrap_cookie_dict(cookie_dict):
    cookies = ""

    for key, value in cookie_dict.items():
        cookies = cookies + f"{key}={value}; "

    if (len(cookies) > 0):
        cookies = cookies[0:-2]

    return cookies

def remove_query_param(url, params: list):
    url_parts = urlparse(url)
    query_params = url_parts.query.split('&')
    is_change = False
    new_query_params = []

    for query_param in query_params:
        is_exist = False
        for param_to_remove in params:
            if query_param.startswith(f"{param_to_remove}="):
                is_exist = True
                is_change = True
                break

        if not is_exist:
            new_query_params.append(query_param)

    if is_change:
        new_query = '&'.join(new_query_params)
        new_url = urlunparse((
            url_parts.scheme,
            url_parts.netloc,
            url_parts.path,
            url_parts.params,
            new_query,
            url_parts.fragment
        ))
        return new_url
    else:
        return url
    
def join_query_item(url, key, value):
    if url.find('?') == -1:
        return f"{url}?{key}={value}"
    else:
        return f"{url}&{key}={value}"
    
def is_valid_filename(name):
    try:
        with open(name, 'w'):
            pass
        os.remove(name)
        return True
    except OSError:
        return False

def ensure_playlistname(name, tag=None):
    valid_name = sanitize_title(name)
    if len(valid_name) == 0:
        temp_name = os.path.join(tempfile.gettempdir(), name)
        if is_valid_filename(temp_name):
            return quote(name)
        else:
            timestamp = int(time.time())
            if tag is not None:
                return f"{tag}-{timestamp}"
            else:
                return f"Unknown-{timestamp}"

    return valid_name

def ensure_limit_title(dir, title, limit=180):
    title = sanitize_filename(title)
    file_path = f"{dir}/{title}"
    max_path = limit
    if len(file_path) > max_path:
        file_path = file_path[0:max_path]
        title = os.path.basename(file_path)
    return title

def generate_random_hex(length:int, upperCase: bool):
    hex = ''.join(secrets.choice('0123456789abcdef') for _ in range(length))
    if upperCase:
        hex = hex.upper()
    return hex

def merge_audio_video(ffmpeg_path,audio,video,output):
    subprocess.run([
            os.path.join(ffmpeg_path, 'ffmpeg'),
            '-i', audio,
            '-i', video,
            '-acodec', 'copy',
            '-vcodec', 'copy',
            '-strict', '-2',
            '-y',
            output
        ])