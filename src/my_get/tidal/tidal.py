#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import json
import random
import re
import time
import aigpy
import base64
import requests
from xml.etree import ElementTree

from .model import *
from .enums import *
from .settings import *

# SSL Warnings | retry number
requests.packages.urllib3.disable_warnings()
requests.adapters.DEFAULT_RETRIES = 5


class TidalAPI(object):
    def __init__(self):
        self.key = LoginKey()
        self.apiKey = {'clientId': '7m7Ap0JC9j1cOM3n',
                       'clientSecret': 'vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY='}

    def __get__(self, path, params={}, urlpre='https://api.tidalhifi.com/v1/'):
        header = {}
        header = {'authorization': f'Bearer {self.key.accessToken}'}
        params['countryCode'] = self.key.countryCode
        errmsg = "Get operation err!"
        for index in range(0, 3):
            try:
                respond = requests.get(urlpre + path, headers=header, params=params)
                if respond.url.find("playbackinfopostpaywall") != -1 and SETTINGS.downloadDelay is not False:
                    # random sleep between 0.5 and 5 seconds and print it
                    sleep_time = random.randint(500, 5000) / 1000
                    print(f"Sleeping for {sleep_time} seconds, to mimic human behaviour and prevent too many requests error")
                    time.sleep(sleep_time)

                if respond.status_code == 429:
                    print('Too many requests, waiting for 20 seconds...')
                    # Loop countdown 20 seconds and print the remaining time
                    for i in range(20, 0, -1):
                        time.sleep(1)
                        print(i, end=' ')
                    print('')
                    continue

                result = json.loads(respond.text)
                if 'status' not in result:
                    return result

                if 'userMessage' in result and result['userMessage'] is not None:
                    errmsg += result['userMessage']
                break
            except Exception as e:
                if index >= 3:
                    errmsg += respond.text

        raise Exception(errmsg)

    def __getItems__(self, path, params={}):
        params['limit'] = 50
        params['offset'] = 0
        total = 0
        ret = []
        while True:
            data = self.__get__(path, params)
            if 'totalNumberOfItems' in data:
                total = data['totalNumberOfItems']
            if total > 0 and total <= len(ret):
                return ret

            ret += data["items"]
            num = len(data["items"])
            if num < 50:
                break
            params['offset'] += num
        return ret

    def __getResolutionList__(self, url):
        ret = []
        txt = requests.get(url).content.decode('utf-8')
        # array = txt.split("#EXT-X-STREAM-INF")
        array = txt.split("#")
        for item in array:
            if "RESOLUTION=" not in item:
                continue
            if "EXT-X-STREAM-INF:" not in item:
                continue
            stream = VideoStreamUrl()
            stream.codec = aigpy.string.getSub(item, "CODECS=\"", "\"")
            stream.m3u8Url = "http" + aigpy.string.getSubOnlyStart(item, "http").strip()
            stream.resolution = aigpy.string.getSub(item, "RESOLUTION=", "http").strip()
            stream.resolution = stream.resolution.split(',')[0]
            stream.resolutions = stream.resolution.split("x")
            ret.append(stream)
        return ret


    def getAlbum(self, id) -> Album:
        return aigpy.model.dictToModel(self.__get__('albums/' + str(id)), Album())

    def getPlaylist(self, id) -> Playlist:
        return aigpy.model.dictToModel(self.__get__('playlists/' + str(id)), Playlist())

    def getArtist(self, id) -> Artist:
        return aigpy.model.dictToModel(self.__get__('artists/' + str(id)), Artist())

    def getTrack(self, id) -> Track:
        return aigpy.model.dictToModel(self.__get__('tracks/' + str(id)), Track())

    def getVideo(self, id) -> Video:
        return aigpy.model.dictToModel(self.__get__('videos/' + str(id)), Video())

    def getMix(self, id) -> Mix:
        mix = Mix()
        mix.id = id
        mix.tracks, mix.videos = self.getItems(id, Type.Mix)
        return mix

    def getTypeData(self, id, type: Type):
        if type == Type.Album:
            return self.getAlbum(id)
        if type == Type.Artist:
            return self.getArtist(id)
        if type == Type.Track:
            return self.getTrack(id)
        if type == Type.Video:
            return self.getVideo(id)
        if type == Type.Playlist:
            return self.getPlaylist(id)
        if type == Type.Mix:
            return self.getMix(id)
        return None

    def getLyrics(self, id) -> Lyrics:
        data = self.__get__(f'tracks/{str(id)}/lyrics', urlpre='https://listen.tidal.com/v1/')
        return aigpy.model.dictToModel(data, Lyrics())

    def getItems(self, id, type: Type):
        if type == Type.Playlist:
            data = self.__getItems__('playlists/' + str(id) + "/items")
        elif type == Type.Album:
            data = self.__getItems__('albums/' + str(id) + "/items")
        elif type == Type.Mix:
            data = self.__getItems__('mixes/' + str(id) + '/items')
        else:
            raise Exception("invalid Type!")

        tracks = []
        videos = []
        for item in data:
            if item['type'] == 'track' and item['item']['streamReady']:
                tracks.append(aigpy.model.dictToModel(item['item'], Track()))
            else:
                videos.append(aigpy.model.dictToModel(item['item'], Video()))
        return tracks, videos

    def getArtistAlbums(self, id, includeEP=False):
        data = self.__getItems__(f'artists/{str(id)}/albums')
        albums = list(aigpy.model.dictToModel(item, Album()) for item in data)
        if not includeEP:
            return albums

        data = self.__getItems__(f'artists/{str(id)}/albums', {"filter": "EPSANDSINGLES"})
        albums += list(aigpy.model.dictToModel(item, Album()) for item in data)
        return albums

    # from https://github.com/Dniel97/orpheusdl-tidal/blob/master/interface.py#L582
    def parse_mpd(self, xml: bytes) -> list:
        # Removes default namespace definition, don't do that!
        xml = re.sub(r'xmlns="[^"]+"', '', xml, count=1)
        root = ElementTree.fromstring(xml)

        # List of AudioTracks
        tracks = []

        for period in root.findall('Period'):
            for adaptation_set in period.findall('AdaptationSet'):
                for rep in adaptation_set.findall('Representation'):
                    # Check if representation is audio
                    content_type = adaptation_set.get('contentType')
                    if content_type != 'audio':
                        raise ValueError('Only supports audio MPDs!')

                    # Codec checks
                    codec = rep.get('codecs').upper()
                    if codec.startswith('MP4A'):
                        codec = 'AAC'

                    # Segment template
                    seg_template = rep.find('SegmentTemplate')
                    # Add init file to track_urls
                    track_urls = [seg_template.get('initialization')]
                    start_number = int(seg_template.get('startNumber') or 1)

                    # https://dashif-documents.azurewebsites.net/Guidelines-TimingModel/master/Guidelines-TimingModel.html#addressing-explicit
                    # Also see example 9
                    seg_timeline = seg_template.find('SegmentTimeline')
                    if seg_timeline is not None:
                        seg_time_list = []
                        cur_time = 0

                        for s in seg_timeline.findall('S'):
                            # Media segments start time
                            if s.get('t'):
                                cur_time = int(s.get('t'))

                            # Segment reference
                            for i in range((int(s.get('r') or 0) + 1)):
                                seg_time_list.append(cur_time)
                                # Add duration to current time
                                cur_time += int(s.get('d'))

                        # Create list with $Number$ indices
                        seg_num_list = list(range(start_number, len(seg_time_list) + start_number))
                        # Replace $Number$ with all the seg_num_list indices
                        track_urls += [seg_template.get('media').replace('$Number$', str(n)) for n in seg_num_list]

                    tracks.append(track_urls)
        return tracks
    
    def getStreamUrl(self, id, quality: AudioQuality):
        squality = "LOSSLESS"
        if quality == AudioQuality.Normal:
            squality = "LOW"
        elif quality == AudioQuality.High:
            squality = "HIGH"
        elif quality == AudioQuality.HiFi:
            squality = "LOSSLESS"
        elif quality == AudioQuality.Max:
            squality = "HI_RES_LOSSLESS"

        paras = {"audioquality": squality, "playbackmode": "STREAM", "assetpresentation": "FULL"}
        data = self.__get__(f'tracks/{str(id)}/playbackinfopostpaywall', paras)
        resp = aigpy.model.dictToModel(data, StreamRespond())

        if "vnd.tidal.bt" in resp.manifestMimeType:
            manifest = json.loads(base64.b64decode(resp.manifest).decode('utf-8'))
            ret = StreamUrl()
            ret.trackid = resp.trackid
            ret.soundQuality = resp.audioQuality
            ret.codec = manifest['codecs']
            ret.encryptionKey = manifest['keyId'] if 'keyId' in manifest else ""
            ret.url = manifest['urls'][0]
            ret.urls = [ret.url]
            return ret
        elif "dash+xml" in resp.manifestMimeType:
            xmldata = base64.b64decode(resp.manifest).decode('utf-8')
            ret = StreamUrl()
            ret.trackid = resp.trackid
            ret.soundQuality = resp.audioQuality
            ret.codec = aigpy.string.getSub(xmldata, 'codecs="', '"')
            ret.encryptionKey = ""#manifest['keyId'] if 'keyId' in manifest else ""
            ret.urls = self.parse_mpd(xmldata)[0]
            if len(ret.urls) > 0:
                ret.url = ret.urls[0]
            return ret
            
        raise Exception("Can't get the streamUrl, type is " + resp.manifestMimeType)

    def getVideoStreamUrl(self, id, quality: VideoQuality):
        paras = {"videoquality": "HIGH", "playbackmode": "STREAM", "assetpresentation": "FULL"}
        data = self.__get__(f'videos/{str(id)}/playbackinfopostpaywall', paras)
        resp = aigpy.model.dictToModel(data, StreamRespond())

        if "vnd.tidal.emu" in resp.manifestMimeType:
            manifest = json.loads(base64.b64decode(resp.manifest).decode('utf-8'))
            array = self.__getResolutionList__(manifest['urls'][0])
            icmp = int(quality.value)
            index = 0
            for item in array:
                if icmp <= int(item.resolutions[1]):
                    break
                index += 1
            if index >= len(array):
                index = len(array) - 1
            return array[index]
        raise Exception("Can't get the streamUrl, type is " + resp.manifestMimeType)

    def getTrackContributors(self, id):
        return self.__get__(f'tracks/{str(id)}/contributors')

    def getCoverUrl(self, sid, width="320", height="320"):
        if sid is None:
            return ""
        return f"https://resources.tidal.com/images/{sid.replace('-', '/')}/{width}x{height}.jpg"

    def getCoverData(self, sid, width="320", height="320"):
        url = self.getCoverUrl(sid, width, height)
        try:
            return requests.get(url).content
        except:
            return ''

    def parseUrl(self, url):
        if "tidal.com" not in url:
            return Type.Null, url

        url = url.lower()
        for index, item in enumerate(Type):
            if item.name.lower() in url:
                etype = item
                return etype, aigpy.string.getSub(url, etype.name.lower() + '/', '/')
        return Type.Null, url

    def getByString(self, string):
        if aigpy.string.isNull(string):
            raise Exception("Please enter something.")

        obj = None
        etype, sid = self.parseUrl(string)
        for index, item in enumerate(Type):
            if etype != Type.Null and etype != item:
                continue
            if item == Type.Null:
                continue
            try:
                obj = self.getTypeData(sid, item)
                return item, obj
            except:
                continue

        raise Exception("No result.")


# Singleton
TIDAL_API = TidalAPI()
