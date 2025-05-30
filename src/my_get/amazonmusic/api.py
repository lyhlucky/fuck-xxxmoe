import json
from mutagen.mp4 import MP4Cover
import requests
import re
from datetime import datetime
from random import getrandbits
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import os
from common import MsgType, flush_print, join_query_item, ensure_playlistname


class Api:
    def __init__(self, cookies, proxies, params):
        self.params = params
        self._source_url = params['url']
        self._user_gent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        self._proxies = proxies
        self._is_album = False
        self._is_playlist = False
        self._is_track = False
        self._albumId = ''
        self._playlistId = ''
        self._mediaId = ''
        self._deeplink = ''
        self._metadata = {}
        self._ref_marker = ''
        self._referer = ''

        self.app_config = None
        self.pssh = None
        self.codecs = None
        self.audio_url = None
        self.title = None
        self.dmls_url = None

        self._session = requests.Session()
        self._session.cookies.update(
            requests.utils.cookiejar_from_dict(cookies, cookiejar=None, overwrite=True)
        )       

    def process(self):
        result = urlparse(self._source_url)
        self._hostname = result.hostname
        self._homepage= f"{result.scheme}://{result.hostname}"
        if '/albums/' in self._source_url:
            self._albumId = result.path[8:]
        elif '/playlists/' in self._source_url:
            self._playlistId = result.path[11:]
        elif '/user-playlists/' in self._source_url:
            self._playlistId = result.path[16:]

        self._deeplink = result.path
        for x in result.query.split('&'):
            if x.find('trackAsin') > -1:
                self._is_track = True
                self._mediaId = x[10:]
                self._deeplink = f'{result.path}?{x}'
                break

        if not self._is_track:
            if len(self._albumId) > 0:
                self._is_album = True
            elif len(self._playlistId) > 0:
                self._is_playlist = True

        self._session.headers.update(
            {
                'Content-Type': 'text/plain;charset=UTF-8',
                'User-Agent': self._user_gent
            }
        )

        self.app_config = self._get_app_config()
        home_data = self._request_home()

        if self._is_album or self._is_playlist:
            self._extract_playlist(home_data)
            os._exit(0)

        for method in home_data['methods']:
            if 'template' in method and 'multiSelectBar' in method['template']:
                template = method['template']
                self._metadata['cover'] = template['headerImage']
                self._metadata["artistName"] = template['headerPrimaryText']
                self._metadata["albumName"] = template['headerImageAltText']
                if 'footer' in template and len(template['footer']) > 0:
                    self._metadata["copyright"] = template['footer']

                try:
                    text_list = template['headerTertiaryText'].split('•')
                    if len(text_list) > 1:
                        tertiary_text = text_list[-1].strip()
                        time_format = datetime.strptime(tertiary_text, '%b %d %Y')
                        self._metadata["year"] = str(time_format.year)
                except Exception:
                    pass

                totaltracks = template['multiSelectBar']['actionButton1']['observer']['defaultValue']['onItemSelected'][0]['keys']
                for tracknum, t in enumerate(totaltracks, start=1):
                    if t.find(self._mediaId) > -1:
                        self._metadata['tracknum'] = (tracknum, len(totaltracks))
                        item = template['widgets'][0]['items'][tracknum - 1]
                        self._metadata["title"] = item['primaryText']
                        self._metadata["durationSeconds"] = item['secondaryText3']
                        break
                break

        if self.params['add_playlist_index'] == "true":
            title = f"{self.params['playlist_index']}.{self._metadata['title']}"
        else:
            title = f"{self._metadata['title']}"

        flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': self._metadata['cover'],
                'local_thumbnail': '',
                'duration': self._metadata['durationSeconds'],
                'is_live': False
            }
        }))
        
        self.title = self._metadata['title']
        self.dmls_url = f"{self._homepage}/{self.app_config['siteRegion']}/api/dmls/"
        self._get_download_info()

    def get_tags(self):
        tags = {
            "\xa9nam": [self._metadata["title"]],
            "aART": [self._metadata["artistName"]],
            "\xa9alb": [self._metadata["albumName"]],
            "\xa9ART": [self._metadata["artistName"]],
            "covr": [MP4Cover(self._get_cover(self._metadata['cover']))],
        }
        if 'tracknum' in self._metadata:
            tags['trkn'] = [self._metadata['tracknum']]
        if "year" in self._metadata:
            tags['\xa9day'] = [self._metadata['year']]
        if "copyright" in self._metadata:
            tags['cprt'] = [self._metadata['copyright']]
        return tags
    
    def _extract_playlist(self, webplayback):
        current_template = None
        for method in webplayback['methods']:
            if 'template' in method and 'widgets' in method['template']:
                current_template = method['template']
                break

        tracks = current_template['widgets'][0]['items']
        playlist_name = ensure_playlistname(f"{current_template['headerImageAltText']}-{current_template['headerPrimaryText']}")

        videos = []
        for track in tracks:
            url = f"{self._homepage}{track['primaryLink']['deeplink']}"
            url = join_query_item(url, 'itdl_pname', playlist_name)
            video = {}
            video['title'] = track['primaryText']
            video['url'] = url
            videos.append(video)

        flush_print(json.dumps({
            'type': MsgType.playlist.value,
            'msg': {
                'videos': videos
            }
        }))

    def _get_app_config(self):
        try:
            result = urlparse(self._source_url)
            url = f"https://{result.hostname}/config.json"
            response = self._session.get(url, proxies=self._proxies)
            app_config = response.json()

            # response = self._session.get(self._source_url, proxies=self._proxies)
            # match = re.search(r"window\.amznMusic\s*=\s*(\{[^;]*?\});", response.text)
            # if match:
            #     json_data = match.group(1)
            #     json_data = json_data.replace("appConfig","\"appConfig\"")
            #     json_data = json_data.replace("ssr", "\"ssr\"")
            #     json_data = json_data.replace("isInContainerApp: true,", "\"isInContainerApp\": true")
            #     app_config = json.loads(json_data)['appConfig']
            # else:
            #     raise Exception("Invalid appconfig")

        except requests.exceptions.RequestException as e:
            raise e
    
        return app_config

    def _request_home(self):
        url = f"https://{self.app_config['siteRegion'].lower()}.mesk.skill.music.a2z.com/api/showHome"

        if self._is_track:
            self._ref_marker = self.app_config['metricsContext']['refMarker']
            self._referer = ''
        else:
            self._ref_marker = ''
            self._referer = 'www.google.com'

        payload = {
            "deeplink": "{"
                "\"interface\":\"DeeplinkInterface.v1_0.DeeplinkClientInformation\","
                "\"deeplink\":\"%(deeplink)s\""
            "}" % {"deeplink": self._deeplink},
            "headers": "{"
                "\"x-amzn-authentication\":\"{"
                    "\\\"interface\\\":\\\"ClientAuthenticationInterface.v1_0.ClientTokenElement\\\","
                    "\\\"accessToken\\\":\\\"%(accessToken)s\\\""
                "}\","
                "\"x-amzn-device-model\":\"WEBPLAYER\","
                "\"x-amzn-device-width\":\"1920\","
                "\"x-amzn-device-family\":\"WebPlayer\","
                "\"x-amzn-device-id\":\"%(deviceId)s\","
                "\"x-amzn-user-agent\":\"%(userAgent)s\","
                "\"x-amzn-session-id\":\"%(sessionId)s\","
                "\"x-amzn-device-height\":\"1080\","
                "\"x-amzn-request-id\":\"%(requestId)s\","
                "\"x-amzn-device-language\":\"%(deveceLanguage)s\","
                "\"x-amzn-currency-of-preference\":\"%(preference)sD\","
                "\"x-amzn-os-version\":\"1.0\","
                "\"x-amzn-application-version\":\"1.0.13425.0\","
                "\"x-amzn-device-time-zone\":\"Asia/Shanghai\","
                "\"x-amzn-timestamp\":\"%(timestamp)s\","
                "\"x-amzn-csrf\":\"{"
                    "\\\"interface\\\":\\\"CSRFInterface.v1_0.CSRFHeaderElement\\\","
                    "\\\"token\\\":\\\"%(csrfToken)s\\\","
                    "\\\"timestamp\\\":\\\"%(csrfTs)s\\\","
                    "\\\"rndNonce\\\":\\\"%(csrfRnd)s\\\""
                "}\","
                "\"x-amzn-music-domain\":\"%(domain)s\","
                "\"x-amzn-referer\":\"%(referer)s\","
                "\"x-amzn-affiliate-tags\":\"\","
                "\"x-amzn-ref-marker\":\"%(refMarker)s\","
                "\"x-amzn-page-url\":\"%(pageUrl)s\","
                "\"x-amzn-weblab-id-overrides\":\"\","
                "\"x-amzn-video-player-token\":\"\","
                "\"x-amzn-feature-flags\":\"hd-supported,uhd-supported\","
                "\"x-amzn-has-profile-id\":\"true\"}\""
            "}" % {
                'accessToken': self.app_config['accessToken'],
                'deviceId': self.app_config['deviceId'],
                'userAgent': self._user_gent,
                'sessionId': self.app_config['sessionId'],
                'requestId': self._generate_request_id(),
                'deveceLanguage': self.app_config['displayLanguage'],
                'preference': self.app_config['musicTerritory'],
                'timestamp': self._get_timestamp(),
                'csrfToken': self.app_config['csrf']['token'],
                'csrfTs': self.app_config['csrf']['ts'],
                'csrfRnd': self.app_config['csrf']['rnd'],
                'domain': self._hostname,
                'referer': self._referer,
                'refMarker': self._ref_marker,
                'pageUrl': self._source_url
            }
        }

        try:
            response = self._session.post(url, json=payload, proxies=self._proxies)
            webplayback = json.loads(response.text)
            return webplayback

        except requests.exceptions.RequestException as e:
            raise e
              
    # 获取下载链接,PSSH,编码格式
    def _get_download_info(self):
        self._session.headers['Content-Type'] = 'application/json'
        self._session.headers['X-Amz-Target'] = 'com.amazon.digitalmusiclocator.DigitalMusicLocatorServiceExternal.getDashManifestsV2'
        self._session.headers['Content-Encoding'] = 'amz-1.0'
        self._session.headers['Authorization'] = f'Bearer {self.app_config["accessToken"]}'
        payload = {
            "customerId": f"{self.app_config['customerId']}",
            "deviceToken": {
                "deviceTypeId": f"{self.app_config['deviceType']}",
                "deviceId": f"{self.app_config['deviceId']}"
            },
            "appMetadata": {"https":"true"},
            "clientMetadata": {
                "clientId": "WebCP",
                "clientRequestId": f"{self._generate_request_id()}"
            },
            "contentIdList": [{"identifier": f"{self._mediaId}", "identifierType": "ASIN"}],
            "musicDashVersionList": ["SIREN_KATANA"],
            "contentProtectionList": ["TRACK_PSSH"],
            "tryAsinSubstitution": True,
            "customerInfo": {"marketplaceId": f"{self.app_config['marketplaceId']}", "territoryId": f"{self.app_config['musicTerritory']}"},
            "appInfo": {"musicAgent": "Maestro/1.0 WebCP/1.0.13425.0 (0055-6403-WebC-542a-8130c)"}
        }

        try:
            pssh = None
            codecs = None
            audio_url = None
            response = self._session.post(self.dmls_url, json=payload, proxies=self._proxies)
            webplayback = json.loads(response.text)
            manifest = webplayback['contentResponseList'][0]['manifest']
            root = ET.fromstring(manifest)
            adaptationsets = root.findall('.//{urn:mpeg:dash:schema:mpd:2011}AdaptationSet')
            has_flac = False

            # 优先下载flac无损格式
            for i in range(0, len(adaptationsets)):
                adaptation = adaptationsets[i]
                contentProtections = adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}ContentProtection')
                content_pssh = contentProtections[1].find('{urn:mpeg:cenc:2013}pssh').text
                representations = adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}Representation')
                temp_bandwidth = 0

                for representation in representations:
                    if representation.attrib['codecs'] == 'flac':
                        has_flac = True

                        if pssh is None:
                            pssh = content_pssh

                        codecs = 'flac'
                        bandwidth = int(representation.attrib['bandwidth'])
                        if bandwidth > temp_bandwidth:
                            temp_bandwidth = bandwidth
                            audio_url = representation.find('{urn:mpeg:dash:schema:mpd:2011}BaseURL').text

            if not has_flac:
                tempPriority = None
                for adaptation in adaptationsets:
                    selectionPriority = int(adaptation.attrib['selectionPriority'])
                    if (tempPriority is None) or (selectionPriority < tempPriority):
                        tempPriority = selectionPriority
                        contentProtections = adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}ContentProtection')
                        pssh = contentProtections[1].find('{urn:mpeg:cenc:2013}pssh').text
                        representations = adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}Representation')
                        temp_bandwidth = 0

                        for representation in representations:
                                codecs = representation.attrib['codecs']
                                bandwidth = int(representation.attrib['bandwidth'])
                                if bandwidth > temp_bandwidth:
                                    temp_bandwidth = bandwidth
                                    audio_url = representation.find('{urn:mpeg:dash:schema:mpd:2011}BaseURL').text

            self.pssh = pssh
            self.codecs = codecs
            self.audio_url = audio_url

        except requests.exceptions.RequestException as e:
            raise e
        
    def _generate_request_id(self):
        hash = hex(getrandbits(128))[2:]
        return f"{hash[0:8]}-{hash[8:12]}-{hash[12:16]}-{hash[16:20]}-{hash[20:32]}"

    def _get_timestamp(self):
        now = datetime.now()
        timestamp = now.timestamp()
        return int(timestamp * 100)

    def _get_cover(self, url):
        return requests.get(url, proxies=self._proxies, verify=False).content