#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import aigpy
import logging
from aigpy.fileHelper import createEmptyFile
from .paths import *
from .printf import *
from .decryption import *
from .tidal import *

from concurrent.futures import ThreadPoolExecutor
from common import MsgType, flush_print 


def __encrypted__(stream, srcPath, descPath):
    if aigpy.string.isNull(stream.encryptionKey):
        os.replace(srcPath, descPath)
    else:
        key, nonce = decrypt_security_token(stream.encryptionKey)
        decrypt_file(srcPath, descPath, key, nonce)
        os.remove(srcPath)


def __parseContributors__(roleType, Contributors):
    if Contributors is None:
        return None
    try:
        ret = []
        for item in Contributors['items']:
            if item['role'] == roleType:
                ret.append(item['name'])
        return ret
    except:
        return None


def __setMetaData__(track: Track, album: Album, filepath, contributors, lyrics):
    obj = aigpy.tag.TagTool(filepath)
    obj.album = track.album.title
    obj.title = track.title
    if not aigpy.string.isNull(track.version):
        obj.title += ' (' + track.version + ')'

    obj.artist = list(map(lambda artist: artist.name, track.artists))
    obj.copyright = track.copyRight
    obj.tracknumber = track.trackNumber
    obj.discnumber = track.volumeNumber
    obj.composer = __parseContributors__('Composer', contributors)
    obj.isrc = track.isrc

    obj.albumartist = list(map(lambda artist: artist.name, album.artists))
    obj.date = album.releaseDate
    obj.totaldisc = album.numberOfVolumes
    obj.lyrics = lyrics
    if obj.totaldisc <= 1:
        obj.totaltrack = album.numberOfTracks
    coverpath = TIDAL_API.getCoverUrl(album.cover, "1280", "1280")
    obj.save(coverpath)



class TidalDownlowd:

    def __init__(self):
        self.finalPath = ""


    def downloadVideo(self, video: Video, album: Album = None, playlist: Playlist = None):
        try:
            flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': video.title,
                'thumbnail': TIDAL_API.getCoverUrl(video.imageID, "320", "180"),
                'local_thumbnail': '',
                'duration': video.duration,
                'is_live': False
            }
            }))
            stream = TIDAL_API.getVideoStreamUrl(video.id, SETTINGS.videoQuality)
            path = getVideoPath(video, album, playlist)
            self.finalPath = path

            m3u8content = requests.get(stream.m3u8Url).content
            if m3u8content is None:
                Printf.err()
                return False, f"GetM3u8 failed.{str(e)}"

            urls = aigpy.m3u8.parseTsUrls(m3u8content)
            if len(urls) <= 0:
                Printf.err()
                return False, "GetTsUrls failed.{str(e)}"


            tool = aigpy.download.DownloadTool(path, urls)
            global isDownloading 
            isDownloading = True
            def downloadVideoProgress():
                resp = {
                'type': MsgType.downloading.value,
                'msg': {
                        'progress': '0',
                        'speed': '0KB/s',
                        'filesize': '0',
                        },
                }
                oldSize = 0
                while isDownloading :
                    if tool.curSize != tool.maxSize or tool.curSize == 0:
                        if tool.maxSize !=0:
                            resp['msg']['progress'] = str('{0:.3f}'.format(tool.curSize / tool.maxSize)) 
                            resp['msg']['filesize'] = str(tool.maxSize)
                            resp['msg']['speed'] = str('{0:.2f}'.format((tool.curSize - oldSize)/ 1048576)) + "MB/s"
                            oldSize = tool.curSize
                            flush_print(json.dumps(resp))
                            time.sleep(1)
                    else:
                        resp['msg']['progress'] = str('{0:.3f}'.format(tool.curSize / tool.maxSize))
                        resp['msg']['filesize'] = str(tool.maxSize)
                        flush_print(json.dumps(resp))
                        return
                    
            t = threading.Thread(target=downloadVideoProgress)
            t.start()

            check, msg = tool.start(False,15)
            isDownloading = False
            if check:
                Printf.success()
                return True
            else:
                Printf.err()
                raise Exception("执行失败")
        except Exception as e:
            Printf.err()
            raise Exception("执行失败")


    def downloadTrack(self, track: Track, album=None, playlist=None, userProgress=None, partSize=1048576):
        try:
            if SETTINGS.addPlaylistIndex:
                title = f"{SETTINGS.playlistIndex}.{track.title}"
            else:
                title = track.title
            flush_print(json.dumps({
            'type': MsgType.sniff.value,
            'msg': {
                'ret_code': '0',
                'title': title,
                'thumbnail': TIDAL_API.getCoverUrl(album.cover, "320", "320"),
                'local_thumbnail': '',
                'duration': track.duration,
                'is_live': False
            }
            }))
            stream = TIDAL_API.getStreamUrl(track.id, SETTINGS.audioQuality)
            path = getTrackPath(track, stream, album, playlist)
            self.finalPath = path
            if userProgress is not None:
                userProgress.updateStream(stream)

            # print(stream.url)
            # download
            logging.info("[DL Track] name=" + aigpy.path.getFileName(path) + "\nurl=" + stream.url)

            tool = aigpy.download.DownloadTool(path + '.part', stream.urls)
            tool.setUserProgress(userProgress)
            tool.setPartSize(partSize)

            global isDownloading 
            isDownloading = True

            def downloadProgress():
                resp = {
                'type': MsgType.downloading.value,
                'msg': {
                        'progress': '0',
                        'speed': '0KB/s',
                        'filesize': '0',
                        },
                }
                oldSize = 0
                while isDownloading :
                    if tool.curSize != tool.maxSize or tool.curSize == 0:
                        if tool.maxSize !=0:
                            resp['msg']['progress'] = str('{0:.3f}'.format(tool.curSize / tool.maxSize)) 
                            resp['msg']['filesize'] = str(tool.maxSize)
                            resp['msg']['speed'] = str('{0:.2f}'.format((tool.curSize - oldSize)/ 1048576)) + "MB/s"
                            oldSize = tool.curSize
                            flush_print(json.dumps(resp))
                            time.sleep(1)
                    
                    else:
                        resp['msg']['progress'] = str('{0:.3f}'.format(tool.curSize / tool.maxSize))
                        resp['msg']['filesize'] = str(tool.maxSize)
                        flush_print(json.dumps(resp))
                        return
                    
            t = threading.Thread(target=downloadProgress)
            t.start()
            check, err = tool.start(SETTINGS.showProgress)
            isDownloading = False

            if not check:
                Printf.err()
                return False, str(err)

            # encrypted -> decrypt and remove encrypted file
            __encrypted__(stream, path + '.part', path)

            # contributors
            try:
                contributors = TIDAL_API.getTrackContributors(track.id)
            except:
                contributors = None

            # lyrics
            try:
                lyrics = TIDAL_API.getLyrics(track.id).subtitles
                if SETTINGS.lyricFile:
                    lrcPath = path.rsplit(".", 1)[0] + '.lrc'
                    aigpy.file.write(lrcPath, lyrics, 'w')
            except:
                lyrics = ''

            __setMetaData__(track, album, path, contributors, lyrics)

            isDownloading = False
            Printf.success()
   

            # t.join()
            return True, ''
        except Exception as e:
            Printf.err()
            raise Exception("执行失败")


    def downloadTracks(self, tracks, album: Album = None, playlist : Playlist=None):
        
        def __getAlbum__(item: Track):
            album = TIDAL_API.getAlbum(item.album.id)
            return album
        
        if not SETTINGS.multiThread:
            for index, item in enumerate(tracks):
                itemAlbum = album
                if itemAlbum is None:
                    itemAlbum = __getAlbum__(item)
                    item.trackNumberOnPlaylist = index + 1
                self.downloadTrack(item, itemAlbum, playlist)
        else:
            thread_pool = ThreadPoolExecutor(max_workers=5)
            for index, item in enumerate(tracks):
                itemAlbum = album
                if itemAlbum is None:
                    itemAlbum = __getAlbum__(item)
                    item.trackNumberOnPlaylist = index + 1
                thread_pool.submit(self.downloadTrack, item, itemAlbum, playlist)
            thread_pool.shutdown(wait=True)


    def downloadVideos(self,videos, album: Album, playlist=None):
        for item in videos:
            self.downloadVideo(item, album, playlist)


# Singleton
TIDAL_Download = TidalDownlowd()

