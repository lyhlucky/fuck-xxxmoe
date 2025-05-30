from deezer import Deezer
from deezer import TrackFormats
from .settings import load as loadSettings
from .utils import getBitrateNumberFromText, formatListener
from .downloader import Downloader
from .itemgen import GenerationError
import re
from urllib.request import urlopen
from base64 import b64decode
from common import flush_print, MsgType
import json
import ssl


from .itemgen import generateTrackItem, \
    generateAlbumItem, \
    generatePlaylistItem, \
    generateArtistItem, \
    generateArtistDiscographyItem, \
    generateArtistTopItem
from .errors import LinkNotRecognized, LinkNotSupported


class LogListener:
    @classmethod
    def send(cls, key, value=None):
        # logString = formatListener(key, value)
        # if len(logString) > 0: print(logString)
        if key == "updateQueue":
            if value.get('progress'):
                flush_print(json.dumps({
                    'type': MsgType.downloading.value,
                    'msg': value
                }))           
        elif key == "downloadInfo":
            if value["state"] == "downloadStart":
                flush_print(json.dumps({
                    'type': MsgType.sniff.value,
                    'msg': value["data"]
                }))
            elif value["state"] == "playlist":
                flush_print(json.dumps({
                    'type': MsgType.playlist.value,
                    'msg': value["data"]
                }))

class DeerzerAdaptor:
    def __init__(self, params):
        self.params = params
        self.bitrate = TrackFormats.MP3_320
        self.final_location = ''

        cookies = json.loads(b64decode(self.params['sessdata']).decode('utf-8'))
        self.cookie_arl = cookies['arl']

    def download(self):
        dz = Deezer()
        # 验证登录
        if not dz.login_via_arl(self.cookie_arl):
            raise Exception("Deerzer not login")

        settings = loadSettings()
        listener = LogListener()
        plugins = {}

        def downloadLink(url, bitrate=None):
            downloadObjects = []

            try:
                downloadObject = self.generateDownloadObject(dz, url, bitrate, plugins, listener)
            except GenerationError as e:
                print(f"{e.link}: {e.message}")
                raise e

            if isinstance(downloadObject, list):
                downloadObjects += downloadObject
            else:
                downloadObjects.append(downloadObject)

            for obj in downloadObjects:
                if obj.__type__ == "Convertable":
                    obj = plugins[obj.plugin].convert(dz, obj, settings, listener)

                dl = Downloader(dz, obj, settings, listener ,self.params)
                dl.start()
                self.final_location = dl.writepath

        settings['downloadLocation'] = self.params['save_path']

        downloadLink(self.params['url'], self.bitrate)

    def parseLink(self, link):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if 'dzr.page.link' in link or 'deezer.page.link' in link: 
            link = urlopen(link, context=ctx).url # Resolve URL shortner
        # Remove extra stuff
        if '?' in link: 
            link = link[:link.find('?')]
        if '&' in link: 
            link = link[:link.find('&')]
        if link.endswith('/'): link = link[:-1] #  Remove last slash if present

        link_type = None
        link_id = None

        if not 'deezer' in link: return (link, link_type, link_id) # return if not a deezer link

        if '/track' in link:
            link_type = 'track'
            link_id = re.search(r"/track/(.+)", link).group(1)
        elif '/playlist' in link:
            link_type = 'playlist'
            link_id = re.search(r"/playlist/(\d+)", link).group(1)
        elif '/album' in link:
            link_type = 'album'
            link_id = re.search(r"/album/(.+)", link).group(1)
        elif re.search(r"/artist/(\d+)/top_track", link):
            link_type = 'artist_top'
            link_id = re.search(r"/artist/(\d+)/top_track", link).group(1)
        elif re.search(r"/artist/(\d+)/discography", link):
            link_type = 'artist_discography'
            link_id = re.search(r"/artist/(\d+)/discography", link).group(1)
        elif '/artist' in link:
            link_type = 'artist'
            link_id = re.search(r"/artist/(\d+)", link).group(1)

        return (link, link_type, link_id)

    def generateDownloadObject(self, dz, link, bitrate, plugins=None, listener=None):
        (link, link_type, link_id) = self.parseLink(link)

        if link_type is None or link_id is None:
            if plugins is None: plugins = {}
            plugin_names = plugins.keys()
            current_plugin = None
            item = None
            for plugin in plugin_names:
                current_plugin = plugins[plugin]
                item = current_plugin.generateDownloadObject(dz, link, bitrate, listener)
                if item: return item
            raise LinkNotRecognized(link)

        if link_type == "track":
            return generateTrackItem(dz, link_id, bitrate)
        if link_type == "album":
            return generateAlbumItem(dz, link_id, bitrate)
        if link_type == "playlist":
            return generatePlaylistItem(dz, link_id, bitrate)
        if link_type == "artist":
            return generateArtistItem(dz, link_id, bitrate, listener)
        if link_type == "artist_discography":
            return generateArtistDiscographyItem(dz, link_id, bitrate, listener)
        if link_type == "artist_top":
            return generateArtistTopItem(dz, link_id, bitrate)

        raise LinkNotSupported(link)

