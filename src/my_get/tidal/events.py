#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import aigpy
import os
from .download import *



def start_album(obj: Album):
    tracks, videos = TIDAL_API.getItems(obj.id, Type.Album)
    _extract_playlist(tracks,videos)
    os._exit(0)
    # TIDAL_Download.downloadTracks(tracks, obj)
    # if SETTINGS.downloadVideos:
    #     TIDAL_Download.downloadVideos(videos, obj)


def start_track(obj: Track):
    album = TIDAL_API.getAlbum(obj.album.id)
    TIDAL_Download.downloadTrack(obj, album)


def start_video(obj: Video):
    TIDAL_Download.downloadVideo(obj, obj.album)


def start_artist(obj: Artist):
    albums = TIDAL_API.getArtistAlbums(obj.id, SETTINGS.includeEP)
    lists = []
    for item in albums:
        tracks, videos = TIDAL_API.getItems(item.id, Type.Album)
        if tracks is not None and tracks != []:
            for track in tracks:
                url = "https://tidal.com/browse/track/" + f'{track.id}'
                list = {}
                list['title'] = track.title
                list['url'] = url
                lists.append(list)
        if videos is not None and videos != [] :    
            for video in videos:
                url = "https://tidal.com/browse/video/" + f'{video.id}'
                list = {}
                list['title'] = video.title
                list['url'] = url
                lists.append(list)

    flush_print(json.dumps({
        'type': MsgType.playlist.value,
        'msg': {
            'videos': lists
        }
    }))
    os._exit(0)


def start_playlist(obj: Playlist):
    tracks, videos = TIDAL_API.getItems(obj.uuid, Type.Playlist)
    _extract_playlist(tracks,videos)
    os._exit(0)
    # TIDAL_Download.downloadTracks(tracks, None, obj)
    # if SETTINGS.downloadVideos:
    #     TIDAL_Download.downloadVideos(videos, None, obj)


def start_mix(obj: Mix):
    _extract_playlist(obj.tracks,obj.videos)
    os._exit(0)




def start_type(etype: Type, obj):
    if etype == Type.Album:
        start_album(obj)
    elif etype == Type.Track:
        start_track(obj)
    elif etype == Type.Video:
        start_video(obj)
    elif etype == Type.Artist:
        start_artist(obj)
    elif etype == Type.Playlist:
        start_playlist(obj)
    elif etype == Type.Mix:
        start_mix(obj)


def start(string):
    if aigpy.string.isNull(string):
        Printf.err()
        raise Exception("执行失败")

    strings = string.split(" ")
    for item in strings:
        if aigpy.string.isNull(item):
            continue
        try:
            etype, obj = TIDAL_API.getByString(item)

        except Exception as e:
            raise Exception("执行失败")

        try:
            start_type(etype, obj)
        except Exception as e:
            Printf.err()
            raise Exception("执行失败")



def initToken():
    if aigpy.string.isNull(TOKEN.accessToken):
        return False

    TIDAL_API.key.countryCode = TOKEN.countryCode
    TIDAL_API.key.userId = TOKEN.userid
    TIDAL_API.key.accessToken = TOKEN.accessToken
    return True
    

def _extract_playlist(tracks,videos):
    lists = []
    if tracks is not None and tracks != []:
        for track in tracks:
            url = "https://tidal.com/browse/track/" + f'{track.id}'
            list = {}
            list['title'] = track.title
            list['url'] = url
            lists.append(list)
    if videos is not None and videos != [] :    
        for video in videos:
            url = "https://tidal.com/browse/video/" + f'{video.id}'
            list = {}
            list['title'] = video.title
            list['url'] = url
            lists.append(list)

    flush_print(json.dumps({
        'type': MsgType.playlist.value,
        'msg': {
            'videos': lists
        }
    }))




