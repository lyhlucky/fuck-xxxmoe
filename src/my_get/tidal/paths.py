#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import os
import aigpy
import datetime
import appdirs

from .tidal import *
from .settings import *



def __fixPath__(name: str):
    return aigpy.path.replaceLimitChar(name, '-').strip()



def __getExtension__(stream: StreamUrl):
    if '.flac' in stream.url:
        return '.flac'
    if '.mp4' in stream.url:
        if 'ac4' in stream.codec or 'mha1' in stream.codec:
            return '.mp4'
        elif 'flac' in stream.codec:
            return '.flac'
        return '.m4a'
    return '.m4a'




def getTrackPath(track, stream, album=None, playlist=None):
    base = SETTINGS.downloadPath 
    number = str(track.trackNumber).rjust(2, '0')

    # artist
    # artists = __fixPath__(TIDAL_API.getArtistsName(track.artists))
    artist = __fixPath__(track.artist.name) if track.artist is not None else ""

    # title
    title = __fixPath__(track.title)
    if not aigpy.string.isNull(track.version):
        title += f' ({__fixPath__(track.version)})'

    # explicit
    explicit = "(Explicit)" if track.explicit else ''

    # album and addyear
    # albumName = __fixPath__(album.title) if album is not None else ''
    # year = __getYear__(album.releaseDate) if album is not None else ''

    # extension
    extension = __getExtension__(stream)

    retpath = SETTINGS.trackFileFormat
    # retpath = retpath.replace(R"{TrackNumber}", number) 
    retpath = retpath.replace(R"{ArtistName}", artist)
    retpath = retpath.replace(R"{TrackTitle}", title)
    retpath = retpath.replace(R"{ExplicitFlag}", explicit)
    retpath = retpath.strip()

    if SETTINGS.addPlaylistIndex:
        return f"{base}/{SETTINGS.playlistIndex}.{retpath}{extension}"

    return f"{base}/{retpath}{extension}"


def getVideoPath(video, album=None, playlist=None):
    base = SETTINGS.downloadPath 

    # get number
    number = str(video.trackNumber).rjust(2, '0')

    # get artist
    # artists = __fixPath__(TIDAL_API.getArtistsName(video.artists))
    artist = __fixPath__(video.artist.name) if video.artist is not None else ""

    # explicit
    explicit = "(Explicit)" if video.explicit else ''

    # title and year and extension
    title = __fixPath__(video.title)
    # year = __getYear__(video.releaseDate)
    extension = ".mp4"

    retpath = SETTINGS.videoFileFormat
    # retpath = retpath.replace(R"{VideoNumber}", number)
    retpath = retpath.replace(R"{ArtistName}", artist)
    retpath = retpath.replace(R"{VideoTitle}", title)
    retpath = retpath.replace(R"{ExplicitFlag}", explicit)
    retpath = retpath.strip()

    if SETTINGS.addPlaylistIndex:
        return f"{base}/{SETTINGS.playlistIndex}.{retpath}{extension}"
    
    return f"{base}/{retpath}{extension}"



def getTokenPath():

    data_dir = appdirs.user_data_dir()
    # path = "C:\\Users\\lucky\\AppData\\Local\\.tidal-dl.token.json"
    if os.name == "nt" :
        return data_dir + str('\\tidal-dl.token.json')
    else:
        return data_dir + "tidal-dl.token.json"

# def getProfilePath():
#     return  os.path.dirname(os.path.abspath(__file__))  + '/.tidal-dl.json'
