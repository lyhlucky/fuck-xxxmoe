import json
from mutagen.mp4 import MP4Cover
import requests
from urllib.parse import urlparse, quote
from common import MsgType, flush_print, ensure_playlistname
import re
import secrets
import logging
from pywidevine import PSSH, Cdm
import subprocess
from pathlib import Path
from cdmhelper import create_cmd_device
from base64 import b64encode, b64decode
import tempfile
import os
import time
import sys
import urllib.request
from curlx import CurlX


logger = logging.getLogger('spotifyApi')

class Api:
    def __init__(self, url, cookies, proxies, params):
        self._source_url = url
        self._proxies = proxies
        self.params= params

        self.external_url = None
        self.playlist_name = ''
        self.access_token_data = None
        self.access_token = None
        self.client_id = None
        self.client_tokent = None

        self.metadata = json.loads(b64decode(self.params['metadata']).decode('utf-8'))

        if 'clientId' in self.metadata:
            self.client_id = self.metadata['clientId']
            
        self.authorization = b64decode(self.params['authorization']).decode('utf-8')
        if not self.authorization.startswith('Bearer'):
            self.authorization = f"Bearer {self.authorization}"
            
        if sys.platform == 'darwin':
            self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
        else:
            self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.3"

        self._session = CurlX(proxies=proxies, headers={
            'Accept': 'application/json',
            'App-Platform': 'WebPlayer',
            'Referer': 'https://open.spotify.com/',
            "authorization": self.authorization,
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'Application/json;charset=UTF-8',
            'Origin': 'https://open.spotify.com',
            "User-Agent": self.user_agent
        })

        if cookies is not None:
            self._session.update_cookies(cookies)

        # self._get_access_token()
        # self._session.update_headers({"Authorization": f"Bearer {self.access_token}"})

        if 'spotify-app-version' in self.metadata:
            self._session.update_headers({"spotify-app-version": self.metadata["spotify-app-version"]})

        if 'client-token' in self.metadata:
            self._session.update_headers({"client-token": self.metadata["client-token"]})
        else:
            self._get_client_token()
            if self.client_tokent is not None:
                self._session.update_headers({"client-token": self.client_tokent})

        if 'accept-language' in self.metadata:
            self._session.update_headers({"Accept-Language": self.metadata["accept-language"]})
        else:
            ip = self._get_public_ip()
            if ip:
                country_code = self._get_country_by_ip(ip)
                if country_code:
                    accept_language = self._set_accept_language(country_code)
                    # print(f"IP 地址: {ip}")
                    # print(f"国家代码: {country_code}")
                    # print(f"Accept-Language: {accept_language}")
                    self._session.update_headers({'Accept-Language': accept_language})

        self.pssh = None
        self.cdm = Cdm.from_device(create_cmd_device())
        self.cdm_session = self.cdm.open()

    def extract_track(self):
        logger.info('extract_track begin')
        result = urlparse(self._source_url)
        if '/track/' in result.path:
            pattern = r'/track/(\w+)'
            track_id = re.search(pattern, result.path).group(1)
            type = "track"
        elif '/episode/' in result.path:
            pattern = r'/episode/(\w+)'
            track_id = re.search(pattern, result.path).group(1)
            type = "episode"
        else:
            raise Exception("URL Unsupported")
        
        is_premium = self._check_premium()
        logger.info(f'is_premium: {is_premium}')
        metadata = self._request_track_metadata(type, track_id)
        logger.info(f'metadata: {metadata}')
        unsynced_lyrics, synced_lyrics = self._get_lyrics(type, track_id)
        tags = self._get_tags(type, metadata, unsynced_lyrics)
        logger.info('get tags end')
        file_id = self._request_file_id(type, track_id, is_premium)

        if self.params['add_playlist_index'] == "true":
            title = f"{self.params['playlist_index']}.{metadata['name']}"
        else:
            title = f"{metadata['name']}"

        if file_id is not None:
            logger.info(f'file_id: {file_id}')
            self.pssh = self._request_pssh(file_id)
            logger.info(f'pssh: {self.pssh}')
            cdn_url = self._request_cdn_url(file_id)
            logger.info(f'cdn_url: {cdn_url}')
            info = {
                'access_token': self.access_token,
                'is_premium': is_premium,
                'title': title,
                'tags': tags,
                'pssh': self.pssh,
                'cdn_url': cdn_url,
                'synced_lyrics': synced_lyrics
            }
        else:
            info = {
                'access_token': self.access_token,
                'is_premium': is_premium,
                'title': title,
                'tags': tags,
                'pssh': None,
                'cdn_url': self.external_url,
                'synced_lyrics': synced_lyrics
            }

        thumbnail_url = ''
        if type == "track" and metadata['album']['images']:
            thumbnail_url = metadata['album']['images'][0]['url']
        elif type == "episode" and metadata['images']:
            thumbnail_url = metadata['images'][0]['url']

        artist_name = ''
        if "\xa9ART" in tags and len(tags["\xa9ART"]) > 0:
            artist_name = tags["\xa9ART"][0]
        album_name = ''
        if "\xa9alb" in tags and len(tags["\xa9alb"]) > 0:
            album_name = tags["\xa9alb"][0]

        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': thumbnail_url,
                'local_thumbnail': '',
                'duration': int(metadata['duration_ms']/1000),
                'artist': artist_name,
                'album': album_name,
                'kind': 'song'
            }
        }))
        return info
    
    def _check_premium(self):
        try:
            url = 'https://api.spotify.com/v1/me'
            response = self._session.get(url)
            webplayback = json.loads(response.text)
            if 'product' in webplayback and webplayback['product'] == 'premium':
                return True
        except Exception as e:
            logger.info(f"check premium failed: {e}")
        
        return False
            
    def _get_gid(self, track_id):
        def __real_encode_array(src_arr, charset_length, base):
            offset = 0
            for i, val in enumerate(src_arr, start=0):
                tmp = val * charset_length + offset
                src_arr[i] = tmp % base
                offset = int(tmp / base)
        
            while offset:
                src_arr.append(offset % base)
                offset = int(offset / base)
        
        def __real_encode_arrays(arr1, arr2, src_val, base):
            offset = 0
            index = 0
            for i, val in enumerate(arr2, start=0):
                index = i
                if index < len(arr1):
                    tmp = int(arr1[index]) + val * src_val + offset
                    arr1[index] = tmp % base
                else:
                    tmp = val * src_val + offset
                    arr1.append(tmp % base)
                offset = int(tmp / base)

            while offset:
                index = index + 1
                if index < len(arr1):
                    tmp = int(arr1[index]) + offset
                    arr1[index] = tmp % base
                else:
                    tmp = offset         
                    arr1.append(tmp % base)
                offset = int(tmp / base)
            
        def __encode_array(src_arr, charset_length, base):
            arr1 = [0]
            arr2 = [1]
            for val in src_arr:
                __real_encode_arrays(arr1, arr2, val, base)
                __real_encode_array(arr2, charset_length, base)
            return arr1

        def __convert_array(arr, charset):
            result = []
            for val in arr:
                result.append(charset[val])
            result.reverse()
            return result

        base62_charset = list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        charset = {}
        for i, val in enumerate(base62_charset, start=0):
            charset[val] = i
        
        conv_arr = __convert_array(list(track_id), charset)
        enc_arr = __encode_array(conv_arr, 62, 16)

        while len(enc_arr) < 22:
            enc_arr.append(0)

        gid = "".join(__convert_array(enc_arr, base62_charset))
        return gid

    """
    type ['track', 'episode']
    id ['track id', 'episode id']
    """ 
    def _request_file_id(self, type, id, is_premium):
        logger.info(f'request track_id: {id}')
        file_id = None
        
        try:
            if type == "track":
                gid = self._get_gid(id)
                logger.info(f'gid={gid}')
                url = f'https://spclient.wg.spotify.com/metadata/4/track/{gid}?market=from_token'
                response = self._session.get(url)
                webplayback = response.json()
                if is_premium:
                    format_tag = "MP4_256"
                else:
                    format_tag = "MP4_128"

                if "file" in webplayback:
                    items = webplayback['file']
                    file_id = next(i for i in items if i['format'] == format_tag)['file_id']
                elif "alternative" in webplayback:
                    file_list = webplayback["alternative"][0]['file']
                    file_id = next(i['file_id'] for i in file_list if i['format'] == format_tag)      
            elif type == "episode":
                variables = quote(json.dumps({
                    "uri": "spotify:episode:%s" % id
                }, separators=(',', ':')))

                extensions = quote(json.dumps({
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": '9697538fe993af785c10725a40bb9265a20b998ccd2383bd6f586e01303824e9'
                    }
                }, separators=(',', ':')))
                url = f'https://api-partner.spotify.com/pathfinder/v1/query?operationName=getEpisodeOrChapter&variables={variables}&extensions={extensions}'
                response = self._session.get(url)
                webplayback = json.loads(response.text)
                items = webplayback["data"]["episodeUnionV2"]["audio"]["items"]
                if len(items) > 0:
                    format_tag = "MP4_128"
                    file_id = next(i for i in items if i['format'] == format_tag)['fileId']

                if file_id is None:
                    #https://spclient.wg.spotify.com/metadata/4/episode/2a44b96af72354379956a184305d283b?market=from_token
                    gid = self._get_gid(id)
                    logger.info(f'gid={gid}')
                    url = f'https://spclient.wg.spotify.com/metadata/4/episode/{gid}?market=from_token'
                    response = self._session.get(url)
                    data = response.json()
                    self.external_url = data['external_url']
        except Exception as e:
            logger.info(f"get file id failed: {e}")
        
        return file_id
        
    def _request_track_metadata(self, type, track_id):
        metadata = None
        try:
            if type == "track":
                url = f'https://api.spotify.com/v1/tracks?ids={track_id}&market=from_token'
                response = self._session.get(url)
                webplayback = json.loads(response.text)
                metadata = webplayback['tracks'][0]
            elif type == "episode":
                url = f'https://api.spotify.com/v1/episodes?ids={track_id}&market=from_token'
                response = self._session.get(url)
                webplayback = json.loads(response.text)
                metadata = webplayback['episodes'][0]
        except Exception as e:
            logger.info(f"get metadata failed: {e}")
            
        return metadata

    def _request_pssh(self, file_id):
        session = CurlX(proxies=self._proxies, headers={
            'Accept': '*/*',
            "User-Agent": self.user_agent
        })

        try:
            url = f'https://seektables.scdn.co/seektable/{file_id}.json'
            response = session.get(url)
            webplayback = response.json()
            pssh = webplayback.get('pssh')
            if pssh:
                return pssh
        except Exception as e:
            logger.info(f"get pssh failed: {e}")
        finally:
            session.close()

        return None
        
    def _request_cdn_url(self, file_id):
        cdn_url = None
        try:
            url = f'https://gae2-spclient.spotify.com/storage-resolve/v2/files/audio/interactive/10/{file_id}?version=10000000&product=9&platform=39&alt=json'
            response = self._session.get(url)
            webplayback = json.loads(response.text)
            cdn_url = webplayback['cdnurl'][0]
        except Exception as e:
            logger.info(f"get cdn url failed: {e}")
        return cdn_url

    def _get_tags(self, type, metadata, unsynced_lyrics):
        logger.info(f'get tags type: {type}')       
        if type == "track":
            album_info = metadata['album']
            tags = {
                "\xa9nam": [metadata['name']],
                "\xa9ART": [self._join_artist(metadata['artists'])],
                "aART": [self._join_artist(album_info['artists'])],
                "\xa9alb": [album_info['name']],
                'trkn': [(int(metadata['track_number']), int(album_info['total_tracks']))]
            }
            if album_info['images']:
                tags["covr"] = MP4Cover(self._get_cover(album_info['images'][0]['url'])),
            if "release_date" in album_info:
                tags["\xa9day"] = [album_info['release_date'].split('-')[0]]
            if unsynced_lyrics:
                tags["\xa9lyr"] = [unsynced_lyrics]
        elif type == "episode":
            show_info = metadata['show']
            tags = {
                "\xa9nam": [metadata["name"]],
                "\xa9ART": [show_info['publisher']],
                "aART": [show_info['publisher']],
                "desc": [metadata['description']],
                "catg": [show_info['media_type']]
            }
            if 'images' in metadata and metadata['images']:
                tags["covr"] = MP4Cover(self._get_cover(metadata['images'][0]['url'])),
            if "release_date" in metadata:
                tags["\xa9day"] = [metadata["release_date"].split('-')[0]]

        return tags
    
    def _get_lyrics(self, type, track_id):
        try:
            if type == "track":
                url = f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}?format=json&market=from_token'
                response = self._session.get(url)
                unsynced_lyrics = ''
                synced_lyrics = ''
                unsynced_line_list = []
                synced_line_list = []
                lines = response.json()['lyrics']['lines']
                for i in lines:
                    words = i["words"]
                    if len(words) > 0:
                        unsynced_line_list.append(words)
                        start_time = self._ms_to_lrc_time(i["startTimeMs"])
                        synced_line_list.append(f"[{start_time}]{words}")

                unsynced_lyrics = '\n'.join(unsynced_line_list)
                synced_lyrics = '\n'.join(synced_line_list)
                return unsynced_lyrics, synced_lyrics
        except Exception as e:
            logger.info(f"get lyrics failed: {e}")
                    
        return None, None
    
    # 转换毫秒到分钟:秒.毫秒格式
    def _ms_to_lrc_time(self, ms):
        ms = int(ms)
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = (ms % 1000) // 10
        return f"{minutes:02}:{seconds:02}.{milliseconds:02}"
                
    def _get_cover(self, url):
        return requests.get(url, proxies=self._proxies, verify=False).content
    
    #playlist
    def extract_playlist(self):
        medias = []
        operation = ""
        variabDic = {}
        sha256 = ""
        
        if self._source_url.find('/album/') != -1:
            # https://open.spotify.com/album/1WMVvswNzB9i2UMh9svso5
            operation = "getAlbum"
            variabDic["locale"] = ""
            variabDic["offset"] = 0
            variabDic["limit"] = 50
            sha256 = "469874edcad37b7a379d4f22f0083a49ea3d6ae097916120d9bbe3e36ca79e9d"
            result_parse = urlparse(self._source_url)
            pathList = result_parse.path.split('/')
            variabDic["uri"] = "spotify:" + pathList[-2] + ":" + pathList[-1]
        elif self._source_url.find('/playlist/') != -1:
            # https://open.spotify.com/playlist/37i9dQZF1DXaImRpG7HXqp
            # https://open.spotify.com/playlist/2EFPm1JYiRmRacYn9P5ceA?si=e621773b6bb94136&nd=1&dlsi=1c14e7451e194c37
            operation = "fetchPlaylist"
            variabDic["offset"] = 0
            variabDic["limit"] = 25
            sha256 = "76849d094f1ac9870ac9dbd5731bde5dc228264574b5f5d8cbc8f5a8f2f26116"
            result_parse = urlparse(self._source_url)
            pathList = result_parse.path.split('/')
            variabDic["uri"] = "spotify:" + pathList[-2] + ":" + pathList[-1]
        elif self._source_url.find('/artist/') != -1:
            # https://open.spotify.com/artist/2elBjNSdBE2Y3f0j1mjrql?si=972ce28780944bc3&nd=1&dlsi=274fb6195eab4738
            operation = "queryArtistOverview"
            variabDic["locale"] = ""
            variabDic["includePrerelease"] = True
            sha256 = "da986392124383827dc03cbb3d66c1de81225244b6e20f8d78f9f802cc43df6e"
            result_parse = urlparse(self._source_url)
            pathList = result_parse.path.split('/')
            variabDic["uri"] = "spotify:" + pathList[-2] + ":" + pathList[-1]
        elif self._source_url.find('/show/') != -1:
            # [Podcast=播客， Audiobook=有声书]
            typename = self._query_show_metadata()
            if typename == 'Podcast':
                # https://open.spotify.com/show/3IM0lmZxpFAY7CwMuv9H4g
                operation = "queryPodcastEpisodes"
                variabDic["offset"] = 0
                variabDic["limit"] = 100
                sha256 = '108deda91e2701403d95dc39bdade6741c2331be85737b804a00de22cc0acabf'
            elif typename == 'Audiobook':
                # https://open.spotify.com/show/6QPS5yUc9VlzoTT36w0nzq
                operation = "queryBookChapters"
                variabDic["offset"] = 0
                variabDic["limit"] = 50
                sha256 = '9879e364e7cee8e656be5f003ac7956b45c5cc7dea1fd3c8039e6b5b2e1f40b4'

            result_parse = urlparse(self._source_url)
            pathList = result_parse.path.split('/')
            variabDic["uri"] = "spotify:" + pathList[-2] + ":" + pathList[-1]
        else:
            if self._source_url.find('/collection/tracks') != -1:
                # 喜欢列表
                # https://open.spotify.com/collection/tracks
                operation = "fetchLibraryTracks"
                variabDic["offset"] = 0
                variabDic["limit"] = 100
                sha256 = 'fb836a1734971837ca61db9488daf8c69d123e9cb7cf31323d9e64e9c59d4be8'
            elif self._source_url.find('/collection/your-episodes') != -1:
                # 你的单集列表
                # https://open.spotify.com/collection/your-episodes
                operation = "fetchLibraryEpisodes"
                variabDic["offset"] = 0
                variabDic["limit"] = 5
                sha256 = '823a8101fb475f622a1f050a482d11114d8d677941382cc98a146801cf3e8511'
                variabDic["uri"] = "spotify:playlist:37i9dQZF1FgnTBfUlzkeKt"

        variables = quote(json.dumps(variabDic, separators=(',', ':')))

        extensions = quote(json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": sha256
            }
        }, separators=(',', ':')))
        
        try:
            apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName={operation}&variables={variables}&extensions={extensions}"
            response = self._session.get(apiUrl)
            jsonData = response.json()

            if operation == "getAlbum" :
                medias = self._get_albumlist(jsonData=jsonData, uri=variabDic["uri"], extensions=extensions)
            elif operation == "fetchPlaylist" :
                medias = self._get_playlist(jsonData=jsonData, uri=variabDic["uri"], extensions=extensions)
            elif operation == "queryArtistOverview":
                medias = self._get_artist_toplist(jsonData)
            elif operation == "queryPodcastEpisodes":
                medias = self._get_podcast_episodes(jsonData=jsonData, uri=variabDic["uri"], extensions=extensions)
            elif operation == "queryBookChapters":
                medias = self._get_book_chapters(jsonData=jsonData, uri=variabDic["uri"], extensions=extensions)
            elif operation == "fetchLibraryTracks":
                medias = self._get_like_tracks(jsonData=jsonData, extensions=extensions)
            elif operation == "fetchLibraryEpisodes":
                medias = self._get_your_episodes(jsonData=jsonData, uri=variabDic["uri"], extensions=extensions)

            resp = {
                'type': MsgType.playlist.value,
                'msg': {
                    'videos': medias
                }
            }
            flush_print(json.dumps(resp))
        except Exception as e:
            logger.info(f"get all playlist failed: {e}")

    def _get_albumlist(self, jsonData, uri, extensions):
        mediaList = []
        album_union = jsonData['data']['albumUnion']
        self.playlist_name = ensure_playlistname(album_union['name'])

        original_albumlist = self._parse_albumlist(jsonData)
        mediaList.extend(original_albumlist)
        totalCount = album_union['tracks']['totalCount']
        requestedCount = 50

        while requestedCount < totalCount:
            try:
                variables = quote(json.dumps({
                    "uri": uri,
                    "offset": requestedCount,
                    "limit": 300
                }, separators=(',', ':')))

                apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=queryAlbumTracks&variables={variables}&extensions={extensions}"
                response = self._session.get(apiUrl)
                albumlist_json = response.json()
                more_albumlist = self._parse_albumlist(albumlist_json)
                mediaList.extend(more_albumlist)
                requestedCount += 300
            except Exception as e:
                logger.info(f"get albumlist failed: {e}")
                break

        return mediaList
        
    def _get_playlist(self, jsonData, uri, extensions):
        mediaList = []
        playlistV2 = jsonData['data']['playlistV2']
        self.playlist_name = ensure_playlistname(playlistV2['name'])
        original_playlist = self._parse_playlist(jsonData)
        mediaList.extend(original_playlist)

        content = playlistV2['content']
        totalCount = content['totalCount']
        pagingInfo = content['pagingInfo']
        offset = pagingInfo['offset']
        limit = pagingInfo['limit']
        requestedCount = offset + limit

        while requestedCount < totalCount:
            try:
                variables = quote(json.dumps({
                    "uri": uri,
                    "offset": requestedCount,
                    "limit": 100
                }, separators=(',', ':')))

                apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=fetchPlaylistContents&variables={variables}&extensions={extensions}"
                response = self._session.get(apiUrl)
                playlist_json = response.json()
                more_playlist = self._parse_playlist(playlist_json)
                mediaList.extend(more_playlist)
                content = playlist_json['data']['playlistV2']['content']
                pagingInfo = content['pagingInfo']
                offset = pagingInfo['offset']
                limit = pagingInfo['limit']
                requestedCount = offset + limit
            except Exception as e:
                logger.info(f"get playlist failed: {e}")
                break

        return mediaList
    
    def _get_artist_toplist(self, jsonData):
        mediaList = []
        artist_union = jsonData['data']['artistUnion']
        itemList = artist_union['discography']['topTracks']['items']
        self.playlist_name = ensure_playlistname(f"Top-{artist_union['profile']['name']}")

        for item in itemList:
            media = {}
            track = item['track']
            if ('name' in track) and ('uri' in track) and ('playability' in track):
                playable = track['playability']['playable']
                if playable:
                    media['title'] = track['name']
                    track_id = track['uri'].split(':')[-1]
                    # si_val = self._generate_hex_string()
                    # media['url'] = f"https://open.spotify.com/track/{track_id}?si={si_val}"
                    media['url'] = f"https://open.spotify.com/track/{track_id}?itdl_pname={self.playlist_name}"
                    mediaList.append(media)

        return mediaList
    
    def _get_podcast_episodes(self, jsonData, uri, extensions):
        mediaList = []
        podcast_union = jsonData['data']['podcastUnionV2']
        episodesV2 = podcast_union['episodesV2']
        self.playlist_name = ensure_playlistname(podcast_union['name'])

        original_episodelist = self._parse_episodelist(episodesV2['items'])
        mediaList.extend(original_episodelist)

        totalCount = episodesV2['totalCount']
        requestedCount = 100

        while requestedCount < totalCount:
            try:
                variables = quote(json.dumps({
                    "uri": uri,
                    "offset": requestedCount,
                    "limit": 100
                }, separators=(',', ':')))

                apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=queryPodcastEpisodes&variables={variables}&extensions={extensions}"
                response = self._session.get(apiUrl)
                episodelist_json = response.json()
                items = episodelist_json['data']['podcastUnionV2']['episodesV2']['items']
                more_episodelist = self._parse_episodelist(items)
                mediaList.extend(more_episodelist)
                requestedCount += 100
            except Exception as e:
                logger.info(f"get podcast episodes failed: {e}")
                break

        return mediaList

    def _get_book_chapters(self, jsonData, uri, extensions):
        mediaList = []
        podcast_union = jsonData['data']['podcastUnionV2']
        chapters = podcast_union['chaptersV2']
        self.playlist_name = ensure_playlistname(podcast_union['name'])

        original_chapterlist = self._parse_chapterlist(chapters['items'])
        mediaList.extend(original_chapterlist)

        totalCount = chapters['totalCount']
        requestedCount = 50

        while requestedCount < totalCount:
            try:
                variables = quote(json.dumps({
                    "uri": uri,
                    "offset": requestedCount,
                    "limit": 100
                }, separators=(',', ':')))

                apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=queryBookChapters&variables={variables}&extensions={extensions}"
                response = self._session.get(apiUrl)
                chapterlist_json = response.json()
                items = chapterlist_json['data']['podcastUnionV2']['chaptersV2']['items']
                more_chapterlist = self._parse_chapterlist(items)
                mediaList.extend(more_chapterlist)
                requestedCount += 100
            except Exception as e:
                logger.info(f"get book chapters failed: {e}")
                break

        return mediaList

    def _get_like_tracks(self, jsonData, extensions):
        mediaList = []
        tracks = jsonData['data']['me']['library']['tracks']
        self.playlist_name = 'Like-Spotify'

        original_tracklist = self._parse_like_tracks(tracks['items'])
        mediaList.extend(original_tracklist)

        totalCount = tracks['totalCount']
        requestedCount = 100

        while requestedCount < totalCount:
            try:
                variables = quote(json.dumps({
                    "offset": requestedCount,
                    "limit": 100
                }, separators=(',', ':')))

                apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=fetchLibraryTracks&variables={variables}&extensions={extensions}"
                response = self._session.get(apiUrl)
                tracklist_json = response.json()
                items = tracklist_json['data']['me']['library']['tracks']['items']
                more_tracklist = self._parse_like_tracks(items)
                mediaList.extend(more_tracklist)
                requestedCount += 100
            except Exception as e:
                logger.info(f"get like tracks failed: {e}")
                break

        return mediaList

    def _get_your_episodes(self, jsonData, uri, extensions):
        mediaList = []
        content = jsonData['data']['playlistV2']['content']
        tracks = content['items']
        self.playlist_name = 'Your-Episodes-Spotify'

        original_tracklist = self._parse_your_episodes(tracks)
        mediaList.extend(original_tracklist)

        totalCount = content['totalCount']
        requestedCount = 5

        while requestedCount < totalCount:
            try:
                variables = quote(json.dumps({
                    "uri": uri,
                    "offset": requestedCount,
                    "limit": 5
                }, separators=(',', ':')))

                apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=fetchLibraryEpisodes&variables={variables}&extensions={extensions}"
                response = self._session.get(apiUrl)
                tracklist_json = response.json()
                items = tracklist_json['data']['playlistV2']['content']['items']
                more_tracklist = self._parse_your_episodes(items)
                mediaList.extend(more_tracklist)
                requestedCount += 100
            except Exception as e:
                logger.info(f"get your episodes failed: {e}")
                break

        return mediaList

    def _parse_playlist(self, json_data):
        result = []
        itemlist = json_data['data']['playlistV2']['content']['items']
    
        for item in itemlist:
            media = {}
            itemV2Data = item['itemV2']['data']
            if ('name' in itemV2Data) and ('uri' in itemV2Data) and ('playability' in itemV2Data):
                playable = itemV2Data['playability']['playable']
                if playable:
                    media['title'] = itemV2Data['name']
                    uri_sq = itemV2Data['uri'].split(':')
                    media['url'] = f"https://open.spotify.com/{uri_sq[1]}/{uri_sq[2]}?itdl_pname={self.playlist_name}"
                    result.append(media)

        return result
    
    def _parse_albumlist(self, json_data):
        result = []
        itemList = json_data['data']['albumUnion']['tracks']['items']

        for item in itemList:
            media = {}
            track = item['track']
            if ('name' in track) and ('uri' in track) and ('playability' in track):
                playable = track['playability']['playable']
                if playable:
                    media['title'] = track['name']
                    track_id = track['uri'].split(':')[-1]
                    # si_val = self._generate_hex_string()
                    # media['url'] = f"https://open.spotify.com/track/{track_id}?si={si_val}"
                    media['url'] = f"https://open.spotify.com/track/{track_id}?itdl_pname={self.playlist_name}"
                    result.append(media)

        return result

    def _parse_episodelist(self, items):
        result = []

        for item in items:
            media = {}
            episode = item['entity']['data']
            if ('name' in episode) and ('uri' in episode) and ('playability' in episode):
                playable = episode['playability']['playable']
                if playable:
                    media['title'] = episode['name']
                    episode_id = episode['uri'].split(':')[-1]
                    # si_val = self._generate_hex_string()
                    # media['url'] = f"https://open.spotify.com/episode/{episode_id}?si={si_val}"
                    media['url'] = f"https://open.spotify.com/episode/{episode_id}?itdl_pname={self.playlist_name}"
                    result.append(media)

        return result
    
    def _parse_chapterlist(self, items):
        result = []

        for item in items:
            media = {}
            chapter = item['entity']['data']
            if ('name' in chapter) and ('uri' in chapter) and ('playability' in chapter):
                playable = chapter['playability']['playable']
                if playable:
                    media['title'] = chapter['name']
                    chapter_id = chapter['uri'].split(':')[-1]
                    # si_val = self._generate_hex_string()
                    # media['url'] = f"https://open.spotify.com/episode/{episode_id}?si={si_val}"
                    media['url'] = f"https://open.spotify.com/episode/{chapter_id}?itdl_pname={self.playlist_name}"
                    result.append(media)

        return result

    def _parse_like_tracks(self, items):
        result = []

        for item in items:
            media = {}
            track = item['track']
            track_data = track['data']
            if ('name' in track_data) and ('_uri' in track) and ('playability' in track_data):
                playable = track_data['playability']['playable']
                if playable:
                    media['title'] = track_data['name']
                    track_id = item['track']['_uri'].split(':')[-1]
                    media['url'] = f"https://open.spotify.com/track/{track_id}?itdl_pname={self.playlist_name}"
                    result.append(media)

        return result
    
    def _parse_your_episodes(self, items):
        result = []

        for item in items:
            media = {}
            track = item['itemV2']
            track_data = track['data']
            if ('name' in track_data) and ('_uri' in track) and ('playability' in track_data):
                playable = track_data['playability']['playable']
                if playable:
                    media['title'] = track_data['name']
                    track_id = track['_uri'].split(':')[-1]
                    media['url'] = f"https://open.spotify.com/episode/{track_id}?itdl_pname={self.playlist_name}"
                    result.append(media)

        return result

    # return [Podcast=播客， Audiobook=有声书]
    def _query_show_metadata(self):
        typename = None
        try:
            result_parse = urlparse(self._source_url)
            pathList = result_parse.path.split('/')
            id = pathList[-1]
            variables = quote(json.dumps({
                "uri":"spotify:show:%s" % id
            }, separators=(',', ':')))
            extensions = quote(json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": '5fb034a236a3e8301e9eca0e23def3341ed66c891ea2d4fea374c091dc4b4a6a'
                }
            }, separators=(',', ':')))
            apiUrl = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=queryShowMetadataV2&variables={variables}&extensions={extensions}"
            response = self._session.get(apiUrl)
            jsonData = response.json()
            return jsonData['data']['podcastUnionV2']['__typename']
        except Exception as e:
            logger.info(f"get show metadata failed: {e}")

        return typename

    def _generate_hex_string(self, length=16):
        return ''.join(secrets.choice('0123456789abcdef') for _ in range(length))
    
    def _join_artist(self, artists):
        artist_name = ''
        artist_names = []
        for artist in artists:
            artist_names.append(artist['name'])
        if len(artist_names) > 0:
            artist_name = ','.join(artist_names)
        return artist_name
    
    def _get_access_token(self):
        file_path = self._local_access_token_location()
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = json.load(file)
                expiration_timestamp_ms = data.get("accessTokenExpirationTimestampMs")
                current_timestamp_ms = int(time.time() * 1000)
                # 判断token是否过期, 如果离过期时间超过60s则继续使用这个token
                diff = expiration_timestamp_ms - current_timestamp_ms
                if diff > 60000:
                    self.access_token_data = data
                    self.access_token = data['accessToken']
                    self.client_id = data['clientId']
                    self.client_tokent = data['clientTokent']
                    return

        try:
            url = 'https://open.spotify.com/get_access_token?reason=init&productType=web-player'
            response = self._session.get(url)
            response.raise_for_status()
            content = response.json()
            self.access_token_data = content
            self.access_token = content['accessToken']
            self.client_id = content['clientId']
            # 将数据写入文件
            file_path = self._local_access_token_location()
            with open(file_path, 'w') as file:
                json.dump(content, file)
        except Exception as e:
            raise Exception('Get access token failed.')
        
    def _get_client_token(self):
        if self.client_tokent is not None or self.client_id is None:
            return
        
        try:
            url = 'https://clienttoken.spotify.com/v1/clienttoken'
            response = self._session.post(url, json={
                "client_data":{
                    "client_version": self.client_version,
                    "client_id": self.client_id,
                    "js_sdk_data":{
                        "device_brand":"unknown",
                        "device_model":"unknown",
                        "os":"windows",
                        "os_version":"NT 10.0",
                        "device_id": self._generate_hex_string(32),
                        "device_type":"computer"
                        }
                    }
                })
            response.raise_for_status()
            self.client_tokent = response.json()['granted_token']['token']
            # 将数据写入文件
            self.access_token_data['clientTokent'] = self.client_tokent
            file_path = self._local_access_token_location()
            with open(file_path, 'w') as file:
                json.dump(self.access_token_data, file)
        except Exception as e:
            logger.info('get client token failed.')

    def _local_access_token_location(self):
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "llm_spotify_access_token_7f6d6a.json")
        return file_path
    
    def _get_public_ip(self):
    # 获取公网 IP 地址
        try:
            response = requests.get('https://api64.ipify.org?format=json', proxies=self._proxies)
            ip = response.json()['ip']
            return ip
        except Exception as e:
            # print(f"无法获取IP地址: {e}")
            return None

    def _get_country_by_ip(self, ip):
        # 使用免费 IP 地理位置服务获取国家信息
        try:
            response = requests.get(f'https://ipapi.co/{ip}/json/', proxies=self._proxies)
            data = response.json()
            return data.get('country_code')
        except Exception as e:
            # print(f"无法获取国家信息: {e}")
            return None

    def _set_accept_language(self, country_code):
        # 国家代码和对应的 Accept-Language 映射表
        accept_language_map = {
            'CN': "zh-CN,zh;q=0.9",
            'HK': "zh-HK,zh;q=0.9",
            'MO': "zh-MO,zh;q=0.9",
            'TW': "zh-TW,zh;q=0.9",
            'JP': "ja-JP,ja;q=0.9",
            'KR': "ko-KR,ko;q=0.9",
            'US': "en-US,en;q=0.9",
            'GB': "en-GB,en;q=0.9",
            'FR': "fr-FR,fr;q=0.9",
            'DE': "de-DE,de;q=0.9",
            'ES': "es-ES,es;q=0.9",
            'IT': "it-IT,it;q=0.9",
            'BR': "pt-BR,pt;q=0.9",
            'PT': "pt-PT,pt;q=0.9",
            'RU': "ru-RU,ru;q=0.9",
            'IN': "hi-IN,hi;q=0.9",
            'AR': "es-AR,es;q=0.9",
            'MX': "es-MX,es;q=0.9",
            'CA': "en-CA,en;q=0.9",  # 或者 fr-CA,fr;q=0.9
            'AU': "en-AU,en;q=0.9",
            'NZ': "en-NZ,en;q=0.9",
            'SA': "ar-SA,ar;q=0.9",
            'EG': "ar-EG,ar;q=0.9",
            'IL': "he-IL,he;q=0.9",
            'TR': "tr-TR,tr;q=0.9",
            'TH': "th-TH,th;q=0.9",
            'VN': "vi-VN,vi;q=0.9",
            'ID': "id-ID,id;q=0.9",
            'MY': "ms-MY,ms;q=0.9",
            'SG': "en-SG,en;q=0.9",  # 或者 zh-SG,zh;q=0.9
            'ZA': "en-ZA,en;q=0.9",
            'NG': "en-NG,en;q=0.9",
            'KE': "en-KE,en;q=0.9",
            'PK': "ur-PK,ur;q=0.9",
            'BD': "bn-BD,bn;q=0.9",
            'LK': "si-LK,si;q=0.9",  # 或者 ta-LK,ta;q=0.9
            'GR': "el-GR,el;q=0.9",
            'NL': "nl-NL,nl;q=0.9",
            'BE': "nl-BE,nl;q=0.9",  # 或者 fr-BE,fr;q=0.9
            'SE': "sv-SE,sv;q=0.9",
            'NO': "no-NO,no;q=0.9",  # 或者 nb-NO,nb;q=0.9
            'DK': "da-DK,da;q=0.9",
            'FI': "fi-FI,fi;q=0.9",
            'PL': "pl-PL,pl;q=0.9",
            'CZ': "cs-CZ,cs;q=0.9",
            'HU': "hu-HU,hu;q=0.9",
            'SK': "sk-SK,sk;q=0.9",
            'RO': "ro-RO,ro;q=0.9",
            'BG': "bg-BG,bg;q=0.9",
            'UA': "uk-UA,uk;q=0.9",
            'BY': "be-BY,be;q=0.9",
            'IR': "fa-IR,fa;q=0.9",
            'IQ': "ar-IQ,ar;q=0.9",
            'AE': "ar-AE,ar;q=0.9",
        }

        # 返回对应的 Accept-Language 或者默认值
        return accept_language_map.get(country_code, "en-US,en;q=0.9")
    
    def get_decryption_keys(self):
        challenge = self.cdm.get_license_challenge(self.cdm_session, PSSH(self.pssh))
        license_b64 = self._get_license_b64(challenge)
        self.cdm.parse_license(self.cdm_session, license_b64)
        return f'1:{next(i for i in self.cdm.get_keys(self.cdm_session) if i.type == "CONTENT").key.hex()}'
    
    def decrypt(self, decryption_key, encrypted_location, decrypted_location):
        subprocess.run(
            [
                str(Path(self.params['ffmpeg_location']) / 'itg-key'),
                encrypted_location,
                "--key",
                decryption_key,
                decrypted_location,
            ],
            check=True,
        )

    def _get_license_b64(self, challenge):
        license_b64 = None
        url = "https://gae2-spclient.spotify.com/widevine-license/v1/audio/license"
        headers = {
            'Accept': '*/*',
            "Authorization": self.authorization,
            'origin': 'https://open.spotify.com',
            'referer': 'https://open.spotify.com/',
            'User-Agent': self.user_agent
        }

        if 'client-token' in self.metadata:
            headers['client-token'] = self.metadata["client-token"]

        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=challenge,
                proxies=self._proxies
            )
            response.raise_for_status()
            license_b64 = b64encode(response.content).decode('utf8')
        except Exception as e:
            logger.info(f'get license failed. {e}')

        return license_b64