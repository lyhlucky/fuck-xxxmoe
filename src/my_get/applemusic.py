import base64
import re
import subprocess
import os
import json
import logging
import m3u8
import requests
import datetime
from io import TextIOWrapper
from mutagen.mp4 import MP4, MP4Cover
from xml.etree import ElementTree
from pywidevine import PSSH, Cdm, WidevinePsshData
from yt_dlp import YoutubeDL
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse, parse_qs

from common import MsgType, flush_print, join_query_item, ensure_playlistname, ensure_limit_title
from cdmhelper import create_cmd_device

logger = logging.getLogger('applemusic')

STORE_FRONT = {
    "AE": "143481-2,32", "AG": "143540-2,32", "AI": "143538-2,32", "AL": "143575-2,32", "AM": "143524-2,32",
    "AO": "143564-2,32", "AR": "143505-28,32", "AT": "143445-4,32", "AU": "143460-27,32", "AZ": "143568-2,32",
    "BB": "143541-2,32", "BE": "143446-2,32", "BF": "143578-2,32", "BG": "143526-2,32", "BH": "143559-2,32",
    "BJ": "143576-2,32", "BM": "143542-2,32", "BN": "143560-2,32", "BO": "143556-28,32", "BR": "143503-15,32",
    "BS": "143539-2,32", "BT": "143577-2,32", "BW": "143525-2,32", "BY": "143565-2,32", "BZ": "143555-2,32",
    "CA": "143455-6,32", "CG": "143582-2,32", "CH": "143459-57,32", "CL": "143483-28,32", "CN": "143465-19,32",
    "CO": "143501-28,32", "CR": "143495-28,32", "CV": "143580-2,32", "CY": "143557-2,32", "CZ": "143489-2,32",
    "DE": "143443-4,32", "DK": "143458-2,32", "DM": "143545-2,32", "DO": "143508-28,32", "DZ": "143563-2,32",
    "EC": "143509-28,32", "EE": "143518-2,32", "EG": "143516-2,32", "ES": "143454-8,32", "FI": "143447-2,32",
    "FJ": "143583-2,32", "FM": "143591-2,32", "FR": "143442-3,32", "GB": "143444-2,32", "GD": "143546-2,32",
    "GH": "143573-2,32", "GM": "143584-2,32", "GR": "143448-2,32", "GT": "143504-28,32", "GW": "143585-2,32",
    "GY": "143553-2,32", "HK": "143463-45,32", "HN": "143510-28,32", "HR": "143494-2,32", "HU": "143482-2,32",
    "ID": "143476-2,32", "IE": "143449-2,32", "IL": "143491-2,32", "IN": "143467-2,32", "IS": "143558-2,32",
    "IT": "143450-7,32", "JM": "143511-2,32", "JO": "143528-2,32", "JP": "143462-9,32", "KE": "143529-2,32",
    "KG": "143586-2,32", "KH": "143579-2,32", "KN": "143548-2,32", "KR": "143466-13,32", "KW": "143493-2,32",
    "KY": "143544-2,32", "KZ": "143517-2,32", "LA": "143587-2,32", "LB": "143497-2,32", "LC": "143549-2,32",
    "LK": "143486-2,32", "LR": "143588-2,32", "LT": "143520-2,32", "LU": "143451-2,32", "LV": "143519-2,32",
    "MD": "143523-2,32", "MG": "143531-2,32", "MK": "143530-2,32", "ML": "143532-2,32", "MN": "143592-2,32",
    "MO": "143515-45,32", "MR": "143590-2,32", "MS": "143547-2,32", "MT": "143521-2,32", "MU": "143533-2,32",
    "MW": "143589-2,32", "MX": "143468-28,32", "MY": "143473-2,32", "MZ": "143593-2,32", "NA": "143594-2,32",
    "NE": "143534-2,32", "NG": "143561-2,32", "NI": "143512-28,32", "NL": "143452-10,32", "NO": "143457-2,32",
    "NP": "143484-2,32", "NZ": "143461-27,32", "OM": "143562-2,32", "PA": "143485-28,32", "PE": "143507-28,32",
    "PG": "143597-2,32", "PH": "143474-2,32", "PK": "143477-2,32", "PL": "143478-2,32", "PT": "143453-24,32",
    "PW": "143595-2,32", "PY": "143513-28,32", "QA": "143498-2,32", "RO": "143487-2,32", "RU": "143469-16,32",
    "SA": "143479-2,32", "SB": "143601-2,32", "SC": "143599-2,32", "SE": "143456-17,32", "SG": "143464-19,32",
    "SI": "143499-2,32", "SK": "143496-2,32", "SL": "143600-2,32", "SN": "143535-2,32", "SR": "143554-2,32",
    "ST": "143598-2,32", "SV": "143506-28,32", "SZ": "143602-2,32", "TC": "143552-2,32", "TD": "143581-2,32",
    "TH": "143475-2,32", "TJ": "143603-2,32", "TM": "143604-2,32", "TN": "143536-2,32", "TR": "143480-2,32",
    "TT": "143551-2,32", "TW": "143470-18,32", "TZ": "143572-2,32", "UA": "143492-2,32", "UG": "143537-2,32",
    "US": "143441-1,32", "UY": "143514-2,32", "UZ": "143566-2,32", "VC": "143550-2,32", "VE": "143502-28,32",
    "VG": "143543-2,32", "VN": "143471-2,32", "YE": "143571-2,32", "ZA": "143472-2,32", "ZW": "143605-2,32"
}

class AppleMusicAdaptor:
    def __init__(self, params, proxies, progress_hook=None):
        self.params = params
        self.proxies = proxies
        self.progress_hook = progress_hook
        self.final_location = None
        self.prefer_hevc = False
        self.has_lrc = True
        self.audio_bit_rate = '256k'
        self.lrc_path = ''

        if 'has_lyric' in params:
            self.has_lrc = params['has_lyric'] == 'true'

        cookie_dict = json.loads(base64.b64decode(self.params['sessdata']).decode())

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "origin": "https://music.apple.com",
            "Media-User-Token": cookie_dict["media-user-token"],
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
        })
        self.session.cookies.update(
            requests.utils.cookiejar_from_dict(cookie_dict, cookiejar=None, overwrite=True)
        )
        retry_strategy = Retry(
            total=3,
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        web_page = self.session.get("https://beta.music.apple.com", proxies=self.proxies).text
        index_js_uri = re.search(r"/assets/index-legacy-[^/]+\.js", web_page).group(0)
        index_js_page = self.session.get(
            f"https://beta.music.apple.com{index_js_uri}",
            proxies=self.proxies
        ).text
        token = re.search('(?=eyJh)(.*?)(?=")', index_js_page).group(1)
        self.session.headers.update({"authorization": f"Bearer {token}"})
        self.country = cookie_dict["itua"].lower()
        self.storefront = STORE_FRONT[self.country.upper()]

        self.cdm = Cdm.from_device(create_cmd_device())
        self.cdm_session = self.cdm.open()
        
    def extract(self):
        original_url = self.params['url']
        result_parse = urlparse(original_url)
        path_seq = result_parse.path.split('/')
        track_id = None
        save_path = self.params["save_path"]

        if original_url.find('/album/') != -1 and original_url.find('?i=') != -1:
            qs = parse_qs(result_parse.query)
            if 'i' in qs:
                track_id = qs['i'][0]
        else:
            track_id = path_seq[-1]
            
        if track_id is None:
            raise Exception('Error: Invaild track id')
            
        logger.info(f'track_id: {track_id}')

        if original_url.find('/music-video/') != -1:
            metadata = self.session.get(
                f"https://amp-api.music.apple.com/v1/catalog/{self.country}/music-videos/{track_id}",
                proxies=self.proxies
            ).json()["data"][0]['attributes']

            track_title = metadata['name']
            if self.params['add_playlist_index'] == "true":
                track_title = f'{self.params["playlist_index"]}.{track_title}'

            artwork = metadata['artwork']
            artwork_url = artwork['url']
            artwork_url = artwork_url.replace('{w}', '{}'.format(artwork["width"]))
            thumbnail_url = artwork_url.replace('{h}', '{}'.format(artwork["height"]))

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': track_title,
                    'thumbnail': thumbnail_url,
                    'local_thumbnail': '',
                    'duration': int(metadata['durationInMillis']/1000),
                    'artist': metadata['artistName'],
                    'album': '',
                    'kind': 'musicVideo'
                }
            }))

            audio_encrypted_location = f'{save_path}/{track_id}_encrypted.m4a'
            audio_decrypted_location = f'{save_path}/{track_id}_decrypted.m4a'
            video_encrypted_location = f'{save_path}/{track_id}_encrypted.m4v'
            video_decrypted_location = f'{save_path}/{track_id}_decrypted.m4v'

            webplayback = self._get_webplayback(track_id)
            audio_url, video_url = self._get_music_video_stream_url(webplayback)

            audio_descryption_key = self._get_music_video_decryption_key(audio_url, track_id)
            self._download(audio_url, audio_encrypted_location)
            self._decrypt(audio_encrypted_location, audio_decrypted_location, audio_descryption_key)

            video_descryption_key = self._get_music_video_decryption_key(video_url, track_id)
            self._download(video_url, video_encrypted_location)
            self._decrypt(video_encrypted_location, video_decrypted_location, video_descryption_key)

            fixed_location = f'{save_path}/{track_id}_fixed.m4v'
            self._fixup_music_video(video_decrypted_location, audio_decrypted_location, fixed_location)
            tags = self._get_music_video_tags(metadata, thumbnail_url)
            self._add_tags(fixed_location, tags)

            final_title = ensure_limit_title(save_path, track_title)
            self.final_location = f'{save_path}/{final_title}.m4v'
            os.rename(fixed_location, self.final_location)
        elif original_url.find('/post/') != -1:
            # https://music.apple.com/cn/post/1761286900
            api_url = f'https://amp-api.music.apple.com/v1/catalog/{self.country}/contents?ids={track_id}&platform=web'
            response = self.session.get(api_url, proxies=self.proxies)
            metadata = response.json()["data"][0]['attributes']
            track_title = metadata['name']
            if self.params['add_playlist_index'] == "true":
                track_title = f'{self.params["playlist_index"]}.{track_title}'

            artwork = metadata['artwork']
            artwork_url = artwork['url']
            artwork_url = artwork_url.replace('{w}', '{}'.format(artwork["width"]))
            thumbnail_url = artwork_url.replace('{h}', '{}'.format(artwork["height"]))

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': track_title,
                    'thumbnail': thumbnail_url,
                    'local_thumbnail': '',
                    'duration': int(metadata['durationInMilliseconds']/1000),
                    'artist': metadata['uploadingBrandName'],
                    'album': '',
                    'kind': 'uploadedVideo'
                }
            }))

            video_url = None
            asset_tokens = metadata['assetTokens']
            if '1080pHdVideo' in asset_tokens:
                video_url = asset_tokens['1080pHdVideo']
            else:
                video_url = list(asset_tokens.items())[-1]

            final_title = ensure_limit_title(save_path, track_title)
            self.final_location = f'{save_path}/{final_title}.m4v'
            self._download(video_url, self.final_location)
        else:
            webplayback = self._get_webplayback(track_id)
            asset = next(i for i in webplayback["assets"] if i["flavor"] == "28:ctrp256")           
            thumbnail_url = asset['artworkURL']
            metadata = asset['metadata']
            track_title = metadata['itemName']
            if self.params['add_playlist_index'] == "true":
                track_title = f'{self.params["playlist_index"]}.{track_title}'

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': track_title,
                    'thumbnail': thumbnail_url,
                    'local_thumbnail': '',
                    'duration': int(metadata['duration']/1000),
                    'artist': metadata['artistName'],
                    'album': metadata['playlistName'],
                    'kind': 'song'
                }
            }))

            audio_encrypted_location = f'{save_path}/{track_id}_encrypted.m4a'
            audio_decrypted_location = f'{save_path}/{track_id}_decrypted.m4a'

            unsynced_lyrics, synced_lyrics = self._get_lyrics(track_id)
            stream_url = asset['URL']
            key = self._get_song_decryption_key(stream_url, track_id)
            self._download(stream_url, audio_encrypted_location)
            self._decrypt(audio_encrypted_location, audio_decrypted_location, key)
            fixed_location = f'{save_path}/{track_id}_fixed.m4a'
            self._fixup_song(audio_decrypted_location, fixed_location)
            tags = self._get_song_tags(metadata, thumbnail_url, unsynced_lyrics)
            self._add_tags(fixed_location, tags)
            final_title = ensure_limit_title(save_path, track_title)

            if self.has_lrc and synced_lyrics:
                self.lrc_path = f'{save_path}/{final_title}.lrc'
                with open(self.lrc_path, "w", encoding="utf-8") as f:
                    f.write(synced_lyrics)

            self.final_location = f'{save_path}/{final_title}.m4a'
            os.rename(fixed_location, self.final_location)
    
    def extract_playlist(self):
        original_url = self.params['url']
        result_parse = urlparse(original_url)
        path_list = result_parse.path.split('/')
        playlist_id = path_list[-1]
        if playlist_id == "see-all":
            playlist_id = path_list[-2]
        api_url = None
        medias = []

        if original_url.find('/artist/') != -1:
            qs = parse_qs(result_parse.query)
            if 'section' in qs:
                section_name = qs['section'][0]
                if section_name == 'top-songs' or section_name == 'music-videos' or section_name == 'top-music-videos':
                    api_url = f'https://amp-api.music.apple.com/v1/catalog/{self.country}/artists/{playlist_id}/view/{section_name}?limit=100'
                    response = self.session.get(api_url, proxies=self.proxies)
                    playlist_data = response.json()
                    playlist_name = ensure_playlistname(f"{playlist_data['data'][0]['attributes']['artistName']}-{section_name}", 'AppleMusic-Unknown-Playlist')
                    tracks = playlist_data['data']
                    medias.extend(self._get_medias(tracks, playlist_name))
                    while 'next' in playlist_data:
                        api_url = f"https://amp-api.music.apple.com{playlist_data['next']}&limit=100"
                        response = self.session.get(api_url, proxies=self.proxies)
                        playlist_data = response.json()
                        tracks = playlist_data['data']
                        medias.extend(self._get_medias(tracks, playlist_name))
        elif original_url.find('/library/') != -1:
            if original_url.find('/songs') != -1:
                #https://music.apple.com/cn/library/songs
                api_url = f'https://amp-api.music.apple.com/v1/me/library/songs?limit=100&meta=sorts&offset=0&platform=web&sort=name'
                response = self.session.get(api_url, proxies=self.proxies)
                playlist_data = response.json()
                playlist_name = 'AppleMusic-Library-Songs'
                tracks = playlist_data['data']
                medias.extend(self._get_medias(tracks, playlist_name))
                while 'next' in playlist_data:
                    api_url = f"https://amp-api.music.apple.com{playlist_data['next']}&limit=100&meta=sorts&platform=web&sort=name"
                    response = self.session.get(api_url, proxies=self.proxies)
                    playlist_data = response.json()
                    tracks = playlist_data['data']
                    medias.extend(self._get_medias(tracks, playlist_name))
            elif original_url.find('/albums/') != -1:
                #https://amp-api.music.apple.com/v1/me/library/albums/l.G8Pic2q
                api_url = f'https://amp-api.music.apple.com/v1/me/library/albums/{playlist_id}?platform=web'
                response = self.session.get(api_url, proxies=self.proxies)
                playlist_data = response.json()['data'][0]
                playlist_name = ensure_playlistname(playlist_data['attributes']['name'], 'AppleMusic-Unknown-Playlist')
                tracks = playlist_data['relationships']['tracks']['data']
                medias.extend(self._get_medias(tracks, playlist_name))
            elif original_url.find('/playlist/') != -1:
                #https://music.apple.com/cn/library/playlist/p.7gU0eK0Md3?l=zh-Hans-CN
                params = "?fields%5Bmusic-videos%5D=artistUrl,artwork,durationInMillis,url&fields%5Bsongs%5D=artistUrl,artwork,durationInMillis,url&include=tracks&platform=web"
                api_url = f"https://amp-api.music.apple.com/v1/me/library/playlists/{playlist_id}{params}"
                response = self.session.get(api_url, proxies=self.proxies)
                playlist_data = response.json()['data'][0]
                playlist_name = ensure_playlistname(f"AppleMusic-{playlist_data['attributes']['name']}", 'AppleMusic-Unknown-Playlist')
                tracks = playlist_data['relationships']['tracks']
                medias.extend(self._get_medias(tracks['data'], playlist_name))
                if 'next' in tracks:
                    path = tracks['next']
                    while True:
                        api_url = f"https://amp-api.music.apple.com{path}"
                        response = self.session.get(api_url, proxies=self.proxies)
                        playlist_data = response.json()
                        tracks = playlist_data['data']
                        medias.extend(self._get_medias(tracks, playlist_name))
                        if 'next' in playlist_data:
                            path = playlist_data['next']
                        else:
                            break
        else:
            if original_url.find('/album/') != -1:
                api_url = f"https://amp-api.music.apple.com/v1/catalog/{self.country}/albums/{playlist_id}?platform=web"
                response = self.session.get(api_url, proxies=self.proxies)
                playlist_data = response.json()['data'][0]
                playlist_name = ensure_playlistname(playlist_data['attributes']['name'], 'AppleMusic-Unknown-Playlist')
                tracks = playlist_data['relationships']['tracks']['data']
                medias.extend(self._get_medias(tracks, playlist_name))
            elif original_url.find('/playlist/') != -1:
                api_url = f"https://amp-api.music.apple.com/v1/catalog/{self.country}/playlists/{playlist_id}?extend=trackCount&platform=web&limit%5Btracks%5D=300"
                response = self.session.get(api_url, proxies=self.proxies)
                playlist_data = response.json()['data'][0]
                attributes = playlist_data['attributes']
                trackCount = attributes['trackCount']
                playlist_name = ensure_playlistname(attributes['name'], 'AppleMusic-Unknown-Playlist')
                tracks = playlist_data['relationships']['tracks']['data']
                medias.extend(self._get_medias(tracks, playlist_name))
                if trackCount > 300:
                    api_url = f"https://amp-api.music.apple.com/v1/catalog/{self.country}/playlists/{playlist_id}/tracks?platform=web&offset=300"
                    response = self.session.get(api_url, proxies=self.proxies)
                    playlist_data = response.json()
                    tracks = playlist_data['data']
                    medias.extend(self._get_medias(tracks, playlist_name))

        flush_print(json.dumps({
            'type': MsgType.playlist.value,
            'msg': {
                'videos': medias
            }
        }))

    def _get_medias(self, tracks, playlist_name):
        medias = []
        for track in tracks:
            media = {}
            attributes = track['attributes']
            media['title'] = attributes['name']
            if 'url' in attributes:
                media['url'] = join_query_item(attributes['url'], 'itdl_pname', playlist_name)
            else:
                if 'playParams' in attributes:
                    play_params = attributes['playParams']
                    if play_params['kind'] == 'song':
                        url = f'https://music.apple.com/{self.country}/song/{attributes["name"]}/{play_params["catalogId"]}'
                        media['url'] = join_query_item(url, 'itdl_pname', playlist_name)
                    elif play_params['kind'] == 'musicVideo':
                        url = f'https://music.apple.com/{self.country}/music-video/{attributes["name"]}/{play_params["catalogId"]}'
                        media['url'] = join_query_item(url, 'itdl_pname', playlist_name)

            if len(media) > 0:
                medias.append(media)
        return medias

    def _get_webplayback(self, track_id):
        response = self.session.post(
            "https://play.music.apple.com/WebObjects/MZPlay.woa/wa/webPlayback",
            json={
                "salableAdamId": track_id,
            },
            proxies=self.proxies
        )
        return response.json()["songList"][0]
    
    def _get_music_video_stream_url(self, webplayback):
        with YoutubeDL(
            {
                "allow_unplayable_formats": True,
                "quiet": True,
                "no_warnings": True,
            }
        ) as ydl:
            playlist = ydl.extract_info(webplayback["hls-playlist-url"], download=False)
        if self.prefer_hevc:
            video_stream_url = playlist["formats"][-1]["url"]
        else:
            video_stream_url = [
                i["url"]
                for i in playlist["formats"]
                if i["vcodec"] is not None and "avc1" in i["vcodec"]
            ][-1]
        audio_stream_url = next(
            i["url"]
            for i in playlist["formats"]
            if "audio-stereo-256" in i["format_id"]
        )
        return audio_stream_url, video_stream_url
    
    def _download(self, url, save_location):
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": save_location,
            "allow_unplayable_formats": True,
            "fixup": "never",
            'ffmpeg_location': self.params['ffmpeg_location'],
            'retries': 3,
        }
        if self.params['proxy']:
            proxy = self.params['proxy']
            if 'host' in proxy and proxy['host']:
                if proxy['password'] != '':
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
        with YoutubeDL(ydl_opts) as ydl:
            if (self.progress_hook is not None):
                ydl.add_progress_hook(self.progress_hook)

            ydl.download(url)

    def get_license_b64(self, challenge, track_uri, track_id):
        return self.session.post(
            "https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/acquireWebPlaybackLicense",
            json={
                "challenge": challenge,
                "key-system": "com.widevine.alpha",
                "uri": track_uri,
                "adamId": track_id,
                "isLibrary": False,
                "user-initiated": True,
            },
            proxies=self.proxies
        ).json()["license"]

    def _get_music_video_decryption_key(self, stream_url, track_id):
        playlist = m3u8.load(stream_url, verify_ssl=False)
        track_uri = next(
            i
            for i in playlist.keys
            if i.keyformat == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
        ).uri
        pssh = PSSH(track_uri.split(",")[1])
        challenge = base64.b64encode(
            self.cdm.get_license_challenge(self.cdm_session, pssh)
        ).decode()
        license_b64 = self.get_license_b64(challenge, track_uri, track_id)
        self.cdm.parse_license(self.cdm_session, license_b64)
        return f'1:{next(i for i in self.cdm.get_keys(self.cdm_session) if i.type == "CONTENT").key.hex()}'

    def _get_song_decryption_key(self, stream_url, track_id):
        track_uri = m3u8.load(stream_url, verify_ssl=False).keys[0].uri
        widevine_pssh_data = WidevinePsshData()
        widevine_pssh_data.algorithm = 1
        widevine_pssh_data.key_ids.append(base64.b64decode(track_uri.split(",")[1]))
        pssh = PSSH(base64.b64encode(widevine_pssh_data.SerializeToString()).decode())
        challenge = base64.b64encode(
            self.cdm.get_license_challenge(self.cdm_session, pssh)
        ).decode()
        license_b64 = self.get_license_b64(challenge, track_uri, track_id)
        self.cdm.parse_license(self.cdm_session, license_b64)
        return f'1:{next(i for i in self.cdm.get_keys(self.cdm_session) if i.type == "CONTENT").key.hex()}'

    def _decrypt(self, encrypted_location, decrypted_location, decryption_keys):
        subprocess.run(
            [
                os.path.join(self.params['ffmpeg_location'], 'itg-key'),
                encrypted_location,
                "--key",
                decryption_keys,
                decrypted_location,
            ],
            check=True,
        )

    def _get_cover(self, url):
        return requests.get(url, proxies=self.proxies, verify=False).content

    def _get_song_tags(self, metadata, cover_url, unsynced_lyrics):
        cover_url = cover_url.replace("600x600bb", "1200x1200bb")
        tags = {
            "\xa9nam": [metadata["itemName"]],
            "\xa9gen": [metadata["genre"]],
            "aART": [metadata["playlistArtistName"]],
            "\xa9alb": [metadata["playlistName"]],
            "soar": [metadata["sort-artist"]],
            "soal": [metadata["sort-album"]],
            "sonm": [metadata["sort-name"]],
            "\xa9ART": [metadata["artistName"]],
            "geID": [metadata["genreId"]],
            "atID": [int(metadata["artistId"])],
            "plID": [int(metadata["playlistId"])],
            "cnID": [int(metadata["itemId"])],
            "sfID": [metadata["s"]],
            "rtng": [metadata["explicit"]],
            "pgap": metadata["gapless"],
            "cpil": metadata["compilation"],
            "disk": [(metadata["discNumber"], metadata["discCount"])],
            "trkn": [(metadata["trackNumber"], metadata["trackCount"])],
            "covr": [MP4Cover(self._get_cover(cover_url))],
            "stik": [1],
        }
        if "copyright" in metadata:
            tags["cprt"] = [metadata["copyright"]]
        if "releaseDate" in metadata:
            tags["\xa9day"] = [metadata["releaseDate"]]
        if "comments" in metadata:
            tags["\xa9cmt"] = [metadata["comments"]]
        if "xid" in metadata:
            tags["xid "] = [metadata["xid"]]
        if "composerId" in metadata:
            tags["cmID"] = [int(metadata["composerId"])]
            tags["\xa9wrt"] = [metadata["composerName"]]
            tags["soco"] = [metadata["sort-composer"]]
        if unsynced_lyrics:
            tags["\xa9lyr"] = [unsynced_lyrics]
        return tags

    def _get_music_video_tags(self, metadata, cover_url):
        tags = {
            "\xa9ART": [metadata["artistName"]],
            "\xa9nam": [metadata["name"]],
            "covr": [MP4Cover(self._get_cover(cover_url))]
        }
        if "releaseDate" in metadata:
            tags["\xa9day"] = [metadata["releaseDate"]]
        if 'genreNames' in metadata:
            genre_names = metadata['genreNames']
            if len(genre_names) > 0:                
                tags["\xa9gen"] = genre_names
        return tags
    
    def _add_tags(self, filename, tags):
        file = MP4(filename)
        file.update(tags)
        file.save()

    def _fixup_song(self, decrypted_location, fixed_location):
        command = [
            os.path.join(self.params['ffmpeg_location'], 'ffmpeg'),
            '-i', decrypted_location, "-metadata", "artist=placeholder",
            '-b:a', self.audio_bit_rate, fixed_location
        ]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            duration_ms = None
            ftr = [3600, 60, 1]
            for line in TextIOWrapper(p.stderr, encoding="utf-8"):
                if line.find('Duration:') != -1:
                    timestr = line.strip().split(',')[0][10:]
                    duration_ms = sum([a*b for a, b in zip(ftr, map(float, timestr.split(':')))])
                if line.startswith('frame') or line.startswith('size'):
                    arr = line.split(' ')
                    for item in arr:
                        if item.startswith('time'):
                            timestr = item.split('=')[1]
                            second = sum([a*b for a, b in zip(ftr, map(float, timestr.split(':')))])
                            progress = second / duration_ms
                            flush_print(json.dumps({
                                'type': MsgType.fixing.value,
                                'msg': {
                                    'pid': str(p.pid),
                                    'progress': str('{0:.3f}'.format(progress))
                                },
                            }))
                else:
                    logger.info('ffmpeg output: ' + line)
        except Exception as e:
            logger.info('ffmpeg progress output exception')

        p.wait()

    def _fixup_music_video(self, video_decrypted_location, audio_decrypted_location, fixed_location):
        command = [
            os.path.join(self.params['ffmpeg_location'], 'ffmpeg'),
            '-i', video_decrypted_location,
            '-i', audio_decrypted_location,
            '-b:a', self.audio_bit_rate,
            '-vcodec', 'copy', '-acodec', 'copy','-strict', '-2' , fixed_location
        ]
        subprocess.run(command, check=True)

    def _get_synced_lyrics_formated_time(self, unformatted_time):
        unformatted_time = (
            unformatted_time.replace("m", "").replace("s", "").replace(":", ".")
        )
        unformatted_time = unformatted_time.split(".")
        m, s, ms = 0, 0, 0
        ms = int(unformatted_time[-1])
        if len(unformatted_time) >= 2:
            s = int(unformatted_time[-2]) * 1000
        if len(unformatted_time) >= 3:
            m = int(unformatted_time[-3]) * 60000
        unformatted_time = datetime.datetime.fromtimestamp((ms + s + m) / 1000.0)
        ms_new = f"{int(str(unformatted_time.microsecond)[:3]):03d}"
        if int(ms_new[2]) >= 5:
            ms = int(f"{int(ms_new[:2]) + 1}") * 10
            unformatted_time += datetime.timedelta(
                milliseconds=ms
            ) - datetime.timedelta(microseconds=unformatted_time.microsecond)
        return unformatted_time.strftime("%M:%S.%f")[:-4]

    def _get_lyrics(self, track_id):
        try:
            lyrics_ttml = ElementTree.fromstring(
                self.session.get(
                    f"https://amp-api.music.apple.com/v1/catalog/{self.country}/songs/{track_id}/lyrics",
                    proxies=self.proxies
                ).json()["data"][0]["attributes"]["ttml"]
            )
        except:
            return None, None
        unsynced_lyrics = ""
        synced_lyrics = ""
        for div in lyrics_ttml.iter("{http://www.w3.org/ns/ttml}div"):
            for p in div.iter("{http://www.w3.org/ns/ttml}p"):
                if p.attrib.get("begin"):
                    synced_lyrics += f'[{self._get_synced_lyrics_formated_time(p.attrib.get("begin"))}]{p.text}\n'
                if p.text is not None:
                    unsynced_lyrics += p.text + "\n"
            unsynced_lyrics += "\n"
        return unsynced_lyrics[:-2], synced_lyrics

