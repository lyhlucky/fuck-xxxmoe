from ..utils import removeDuplicateArtists, removeFeatures
from ..types.Artist import Artist
from ..types.Date import Date
from ..types.Picture import Picture
from ..types import VARIOUS_ARTISTS

class Album:
    def __init__(self, alb_id="0", title="", pic_md5=""):
        self.id = alb_id
        self.title = title
        self.pic = Picture(pic_md5, "cover")
        self.artist = {"Main": []}
        self.artists = []
        self.mainArtist = None
        self.date = Date()
        self.dateString = ""
        self.trackTotal = "0"
        self.discTotal = "0"
        self.embeddedCoverPath = ""
        self.embeddedCoverURL = ""
        self.explicit = False
        self.genre = []
        self.barcode = "Unknown"
        self.label = "Unknown"
        self.copyright = ""
        self.recordType = "album"
        self.bitrate = 0
        self.rootArtist = None
        self.variousArtists = None

        self.playlistId = None
        self.owner = None
        self.isPlaylist = False

    def parseAlbum(self, albumAPI):
        self.title = albumAPI['title']

        # Getting artist image ID
        # ex: https://e-cdns-images.dzcdn.net/images/artist/f2bc007e9133c946ac3c3907ddc5d2ea/56x56-000000-80-0-0.jpg
        art_pic = albumAPI['artist']['picture_small']
        art_pic = art_pic[art_pic.find('artist/') + 7:-24]
        self.mainArtist = Artist(
            albumAPI['artist']['id'],
            albumAPI['artist']['name'],
            "Main",
            art_pic
        )
        if albumAPI.get('root_artist'):
            art_pic = albumAPI['root_artist']['picture_small']
            art_pic = art_pic[art_pic.find('artist/') + 7:-24]
            self.rootArtist = Artist(
                albumAPI['root_artist']['id'],
                albumAPI['root_artist']['name'],
                "Root",
                art_pic
            )

        for artist in albumAPI['contributors']:
            isVariousArtists = str(artist['id']) == VARIOUS_ARTISTS
            isMainArtist = artist['role'] == "Main"

            if isVariousArtists:
                self.variousArtists = Artist(
                    art_id = artist['id'],
                    name = artist['name'],
                    role = artist['role']
                )
                continue

            if artist['name'] not in self.artists:
                self.artists.append(artist['name'])

            if isMainArtist or artist['name'] not in self.artist['Main'] and not isMainArtist:
                if not artist['role'] in self.artist:
                    self.artist[artist['role']] = []
                self.artist[artist['role']].append(artist['name'])

        self.trackTotal = albumAPI['nb_tracks']
        self.recordType = albumAPI['record_type']

        self.barcode = albumAPI.get('upc', self.barcode)
        self.label = albumAPI.get('label', self.label)
        self.explicit = bool(albumAPI.get('explicit_lyrics', False))
        if 'release_date' in albumAPI:
            self.date.day = albumAPI["release_date"][8:10]
            self.date.month = albumAPI["release_date"][5:7]
            self.date.year = albumAPI["release_date"][0:4]
            self.date.fixDayMonth()

        self.discTotal = albumAPI.get('nb_disk')
        self.copyright = albumAPI.get('copyright')

        if self.pic.md5 == "" and albumAPI.get('cover_small'):
            # Getting album cover MD5
            # ex: https://e-cdns-images.dzcdn.net/images/cover/2e018122cb56986277102d2041a592c8/56x56-000000-80-0-0.jpg
            alb_pic = albumAPI['cover_small']
            self.pic.md5 = alb_pic[alb_pic.find('cover/') + 6:-24]

        if albumAPI.get('genres') and len(albumAPI['genres'].get('data', [])) > 0:
            for genre in albumAPI['genres']['data']:
                self.genre.append(genre['name'])

    def parseAlbumGW(self, albumAPI_gw):
        self.title = albumAPI_gw['ALB_TITLE']
        self.mainArtist = Artist(
            art_id = albumAPI_gw['ART_ID'],
            name = albumAPI_gw['ART_NAME'],
            role = "Main"
        )

        self.artists = [albumAPI_gw['ART_NAME']]
        self.trackTotal = albumAPI_gw['NUMBER_TRACK']
        self.discTotal = albumAPI_gw['NUMBER_DISK']
        self.label = albumAPI_gw.get('LABEL_NAME', self.label)

        explicitLyricsStatus = albumAPI_gw.get('EXPLICIT_ALBUM_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN)
        self.explicit = explicitLyricsStatus in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]

        self.addExtraAlbumGWData(albumAPI_gw)

    def addExtraAlbumGWData(self, albumAPI_gw):
        if self.pic.md5 == "" and albumAPI_gw.get('ALB_PICTURE'):
            self.pic.md5 = albumAPI_gw['ALB_PICTURE']
        if 'PHYSICAL_RELEASE_DATE' in albumAPI_gw:
            self.date.day = albumAPI_gw["PHYSICAL_RELEASE_DATE"][8:10]
            self.date.month = albumAPI_gw["PHYSICAL_RELEASE_DATE"][5:7]
            self.date.year = albumAPI_gw["PHYSICAL_RELEASE_DATE"][0:4]
            self.date.fixDayMonth()

    def makePlaylistCompilation(self, playlist):
        self.variousArtists = playlist.variousArtists
        self.mainArtist = playlist.mainArtist
        self.title = playlist.title
        self.rootArtist = playlist.rootArtist
        self.artist = playlist.artist
        self.artists = playlist.artists
        self.trackTotal = playlist.trackTotal
        self.recordType = playlist.recordType
        self.barcode = playlist.barcode
        self.label = playlist.label
        self.explicit = playlist.explicit
        self.date = playlist.date
        self.discTotal = playlist.discTotal
        self.playlistId = playlist.playlistId
        self.owner = playlist.owner
        self.pic = playlist.pic
        self.isPlaylist = True

    def removeDuplicateArtists(self):
        """Removes duplicate artists for both artist array and artists dict"""
        (self.artist, self.artists) = removeDuplicateArtists(self.artist, self.artists)

    def getCleanTitle(self):
        """Removes featuring from the album name"""
        return removeFeatures(self.title)
