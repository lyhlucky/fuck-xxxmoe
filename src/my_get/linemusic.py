import requests
from urllib.parse import urlparse, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import json
from common import MsgType, flush_print, ensure_playlistname, sanitize_filename
from yt_dlp import YoutubeDL
from mutagen.mp4 import MP4, MP4Cover
from base64 import b64decode
import os


class LineMusicAdaptor:
    def __init__(self, params, proxies, progress_hook=None):
        self.params = params
        self.proxies = proxies
        self.progress_hook = progress_hook

        self.device_id = b64decode(params['authorization']).decode('utf-8')
        self.media_metadata = None
        self.final_location = None

        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        })
        self.session.cookies.update(
            requests.utils.cookiejar_from_dict(json.loads(b64decode(params['sessdata']).decode('utf-8')), cookiejar=None, overwrite=True)
        )

        retry_strategy = Retry(
            total=3,
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def extract(self):
        # https://music.line.me/webapp/track/mt000000000bf88096
        original_url = self.params['url']
        if original_url.startswith('https://lin.ee/'):
            response = self.session.get(original_url, proxies=self.proxies)
            if response.status_code == 200:
                original_url = response.url

        result_parse = urlparse(original_url)
        path_seq = result_parse.path.split('/')
        media_type = path_seq[2]
        media_id = path_seq[3]

        self.media_metadata = self._get_media_metadata(media_type, media_id)

        if media_type == 'track':
            track_info = self.media_metadata['response']['result']['tracks'][0]
            album_info = track_info['album']
            title = track_info['trackTitle']
            if self.params['add_playlist_index'] == "true":
                title = f"{self.params['playlist_index']}.{title}"

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': title,
                    'thumbnail': album_info['imageUrl'],
                    'local_thumbnail': '',
                    'duration': 0,
                    'is_live': False
                }
            }))
            timestamp = int(time.time())
            api_url = f'https://music.line.me/api2/track/{media_id}/source/forWebPlay.v1?deviceId={self.device_id}&forceAnonymous=false&t={timestamp}'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                webplayback = response.json()
                m3u8_url = webplayback['response']['result']['trackSource']['m3u8Url']
                title = self._adjust_title(track_info['trackTitle'])
                self.final_location = f'{self.params["save_path"]}/{title}.mp3'
                self._download(m3u8_url)
                self._update_track_tags()

        elif media_type == 'video':
            # https://music.line.me/webapp/video/mv00000000000136d5?refererId=mi000000000f472a8a&refererType=artist
            video_info = self.media_metadata['response']['result']['videos'][0]
            title = video_info['videoTitle']
            if self.params['add_playlist_index'] == "true":
                title = f"{self.params['playlist_index']}.{title}"

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': title,
                    'thumbnail': video_info['imageUrl'],
                    'local_thumbnail': '',
                    'duration': 0,
                    'is_live': False
                }
            }))
            result = urlparse(original_url)
            qs = parse_qs(result.query)
            refererId = qs['refererId'][0]
            api_url = f'https://music.line.me/api2/video/{media_id}/source/forWebPlay.v1?deviceId={self.device_id}&quality=1&listId={refererId}&listName=ARTIST'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                webplayback = response.json()
                m3u8_url = webplayback['response']['result']['videoSource']['m3u8Url']
                title = self._adjust_title(video_info["videoTitle"])
                self.final_location = f'{self.params["save_path"]}/{title}.mp4'
                self._download(m3u8_url)
                self._update_video_tags()

    def extract_playlist(self):
        medias = []
        original_url = self.params['url']
        result_parse = urlparse(original_url)
        path_seq = result_parse.path.split('/')
        playlist_type = path_seq[2]
        playlist_id = path_seq[3]

        if playlist_type == 'playlist':
            # https://music.line.me/webapp/playlist/s-NM_20240717_1721202331286_u212b5a21a
            api_url = f'https://music.line.me/api2/playlist/{playlist_id}.v2'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                webplayback = response.json()
                playlist = webplayback['response']['result']['playlist']
                tracks = playlist['tracks']
                playlist_name = ensure_playlistname(playlist['title'], 'LineMusic')

                for track in tracks:
                    media = {}
                    media['title'] = track['trackTitle']
                    media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                    medias.append(media)
        
        elif playlist_type == 'album':
            # https://music.line.me/webapp/album/mb00000000016c5685
            api_url = f'https://music.line.me/api2/album/{playlist_id}/tracks.v1?start=1&display=1000'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                webplayback = response.json()
                tracks = webplayback['response']['result']['tracks']
                playlist_name = None

                for track in tracks:
                    media = {}
                    if playlist_name is None:
                        playlist_name = ensure_playlistname(track['album']['albumTitle'])

                    media['title'] = track['trackTitle']
                    media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                    medias.append(media)

                display_count = len(medias)
                total_count = webplayback['response']['result']['trackTotalCount']
                while display_count < total_count:
                    api_url = f'https://music.line.me/api2/artist/{playlist_id}/tracks.v1?start={display_count+1}&display=100'
                    response = self.session.get(api_url, proxies=self.proxies)
                    if response.status_code == 200:
                        webplayback = response.json()
                        tracks = webplayback['response']['result']['tracks']
                        for track in tracks:
                            media = {}
                            media['title'] = track['trackTitle']
                            media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                            medias.append(media)
                            display_count = len(medias)
                    else:
                        break

        elif playlist_type == 'artist':
            if len(path_seq) > 4:
                medias.extend(self._get_artist(path_seq[4], playlist_id))
        
        elif playlist_type == 'library':
            # https://music.line.me/webapp/library/tracks
            medias.extend(self._get_like_tracks())

        resp = {
            'type': MsgType.playlist.value,
            'msg': {
                'videos': medias
            }
        }
        flush_print(json.dumps(resp))
    
    def _get_artist(self, artist_type, playlist_id):
        medias = []

        if artist_type == 'tracks':
            # https://music.line.me/webapp/artist/mi000000000f472a8a/tracks
            api_url = f'https://music.line.me/api2/artist/{playlist_id}/tracks.v1?start=1&display=100'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                webplayback = response.json()
                tracks = webplayback['response']['result']['tracks']
                playlist_name = None

                for track in tracks:
                    media = {}
                    if playlist_name is None:
                        playlist_name = ensure_playlistname(f"{track['artists'][0]['artistName']}-Top")

                    media['title'] = track['trackTitle']
                    media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                    medias.append(media)

                display_count = len(medias)
                total_count = webplayback['response']['result']['trackTotalCount']
                while display_count < total_count:
                    api_url = f'https://music.line.me/api2/artist/{playlist_id}/tracks.v1?start={display_count+1}&display=100'
                    response = self.session.get(api_url, proxies=self.proxies)
                    if response.status_code == 200:
                        webplayback = response.json()
                        tracks = webplayback['response']['result']['tracks']
                        for track in tracks:
                            media = {}
                            media['title'] = track['trackTitle']
                            media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                            medias.append(media)
                            display_count = len(medias)
                    else:
                        break
        elif artist_type == 'videos':
            # https://music.line.me/webapp/artist/mi000000000f472a8a/videos
            api_url = f'https://music.line.me/api2/artist/{playlist_id}/videos.v1?start=1&display=30&type=MUSICVIDEO'
            response = self.session.get(api_url, proxies=self.proxies)
            if response.status_code == 200:
                webplayback = response.json()
                videos = webplayback['response']['result']['videos']
                playlist_name = None

                for video in videos:
                    media = {}
                    if playlist_name is None:
                        playlist_name = ensure_playlistname(f"{video['artistName']}-MV")

                    media['title'] = video['videoTitle']
                    media['url'] = f'https://music.line.me/webapp/video/{video["videoId"]}?refererId={playlist_id}&refererType=artist&itdl_pname={playlist_name}'
                    medias.append(media)

                display_count = len(medias)
                total_count = webplayback['response']['result']['videoTotalCount']
                while display_count < total_count:
                    api_url = f'https://music.line.me/api2/artist/{playlist_id}/videos.v1?start={display_count+1}&display=30&type=MUSICVIDEO'
                    response = self.session.get(api_url, proxies=self.proxies)
                    if response.status_code == 200:
                        webplayback = response.json()
                        videos = webplayback['response']['result']['videos']
                        for video in videos:
                            media = {}
                            media['title'] = video['videoTitle']
                            media['url'] = f'https://music.line.me/webapp/video/{video["videoId"]}?refererId={playlist_id}&refererType=artist&itdl_pname={playlist_name}'
                            medias.append(media)
                            display_count = len(medias)
                    else:
                        break

        return medias
    
    def _get_like_tracks(self):
        medias = []
        api_url = f'https://music.line.me/api2/user/me/like/tracks.v1?start=1&display=100'
        response = self.session.get(api_url, proxies=self.proxies)
        if response.status_code == 200:
            webplayback = response.json()
            tracks = webplayback['response']['result']['tracks']
            playlist_name = 'Like-Line-Music'

            for track in tracks:
                media = {}
                media['title'] = track['trackTitle']
                media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                medias.append(media)

            display_count = len(medias)
            total_count = webplayback['response']['result']['trackTotalCount']
            while display_count < total_count:
                api_url = f'https://music.line.me/api2/user/me/like/tracks.v1?start={display_count+1}&display=100'
                response = self.session.get(api_url, proxies=self.proxies)
                if response.status_code == 200:
                    webplayback = response.json()
                    tracks = webplayback['response']['result']['tracks']
                    for track in tracks:
                        media = {}
                        media['title'] = track['trackTitle']
                        media['url'] = f'https://music.line.me/webapp/track/{track["trackId"]}?itdl_pname={playlist_name}'
                        medias.append(media)
                        display_count = len(medias)
                else:
                    break

        return medias
    
    def _download(self, url):
        ydl_opts = {
            'cachedir': False,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'playliststart': 1,
            'playlistend': 1,
            'retries': 3,
            'ffmpeg_location': self.params['ffmpeg_location'],
            'outtmpl': self.final_location,
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

    def _get_media_metadata(self, media_type, media_id):
        metadata = None
        api_url = ''
        if media_type == 'video':
            api_url = f'https://music.line.me/api2/videos/{media_id}.v1'
        else:
            api_url = f'https://music.line.me/api2/tracks/{media_id}.v1'    
        
        response = self.session.get(api_url, proxies=self.proxies)
        if response.status_code == 200:
            metadata = response.json()
        return metadata

    def _update_track_tags(self):
        track_info = self.media_metadata['response']['result']['tracks'][0]
        album_info = track_info['album']
        tags = {
            "\xa9nam": [track_info["trackTitle"]],
            "\xa9alb": [album_info['albumTitle']],
            "\xa9ART": [track_info["artists"][0]['artistName']],
            "aART": [album_info['artists'][0]['artistName']],
            "covr": [MP4Cover(self._get_cover(album_info['imageUrl']))],
            "\xa9day": [album_info["releaseDate"].split('.')[0]],
            'trkn': [(int(track_info['trackNumber']), int(album_info['trackTotalCount']))]
        }

        file = MP4(self.final_location)
        file.update(tags)
        file.save()

    def _update_video_tags(self):
        video_info = self.media_metadata['response']['result']['videos'][0]
        tags = {
            "\xa9nam": [video_info["videoTitle"]],
            "\xa9ART": [video_info["artistName"]],
            "covr": [MP4Cover(self._get_cover(video_info['imageUrl']))],
            "\xa9day": [video_info["releaseDate"]]
        }

        file = MP4(self.final_location)
        file.update(tags)
        file.save()

    def _adjust_title(self, title):
        title = sanitize_filename(title)
        if self.params['add_playlist_index'] == "true":
            title = f'{self.params["playlist_index"]}.{title}'

        file_path = os.path.join(self.params["save_path"], title)
        max_path = 180
        if len(file_path) > max_path:
            file_path = file_path[0:max_path]
            title = os.path.basename(file_path)
        return title

    def _get_cover(self, url):
        return requests.get(url, proxies=self.proxies, verify=False).content
