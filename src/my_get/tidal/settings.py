#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import aigpy
import base64

from .enums import *


class Settings(aigpy.model.ModelBase):
    checkExist = False
    includeEP = True
    language = 0
    lyricFile = False
    apiKeyIndex = 0
    showProgress = False
    showTrackInfo = False
    saveAlbumInfo = False
    downloadVideos = True
    multiThread = False
    downloadDelay = True
    addPlaylistIndex = False
    playlistIndex = None
    downloadPath = "./download/"
    audioQuality = AudioQuality.HiFi
    videoQuality = VideoQuality.P1080
    usePlaylistFolder = True
    albumFolderFormat = R"{ArtistName}/{Flag} {AlbumTitle} [{AlbumID}] [{AlbumYear}]"
    playlistFolderFormat = R"Playlist/{PlaylistName} [{PlaylistUUID}]"
    trackFileFormat = R"{ArtistName} - {TrackTitle}{ExplicitFlag}"
    videoFileFormat = R"{ArtistName} - {VideoTitle}{ExplicitFlag}"



class TokenSettings(aigpy.model.ModelBase):
    userid = None
    countryCode = None
    accessToken = None
    refreshToken = None
    expiresAfter = 0

    # def __encode__(self, string):
    #     sw = bytes(string, 'utf-8')
    #     st = base64.b64encode(sw)
    #     return st

    def __decode__(self, string):
        try:
            sr = base64.b64decode(string)
            st = sr.decode()
            return st
        except:
            return string

    def read(self, path):
        self._path_ = path
        txt = aigpy.file.getContent(self._path_)
        if len(txt) > 0:
            data = json.loads(self.__decode__(txt))
            aigpy.model.dictToModel(data, self)

    # def save(self):
    #     data = aigpy.model.modelToDict(self)
    #     txt = json.dumps(data)
    #     aigpy.file.write(self._path_, self.__encode__(txt), 'wb')


# Singleton
SETTINGS = Settings()
TOKEN = TokenSettings()
