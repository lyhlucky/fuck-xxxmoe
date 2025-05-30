from ssl import SSLError
from time import sleep, time
import logging

from requests import get
from requests.exceptions import ConnectionError as RequestsConnectionError, ReadTimeout, ChunkedEncodingError
from urllib3.exceptions import SSLError as u3SSLError

from .utils.crypto import _md5, _ecbCrypt, _ecbDecrypt, generateBlowfishKey, decryptChunk

from .utils import USER_AGENT_HEADER
from .types.DownloadObjects import Single
from .errors import DownloadCanceled, DownloadEmpty

logger = logging.getLogger('deemix')

def generateStreamPath(sng_id, md5, media_version, media_format): # 生成流路径--生成加密流链接要用
    urlPart = b'\xa4'.join(
        [md5.encode(), str(media_format).encode(), str(sng_id).encode(), str(media_version).encode()])
    md5val = _md5(urlPart)
    step2 = md5val.encode() + b'\xa4' + urlPart + b'\xa4'
    step2 = step2 + (b'.' * (16 - (len(step2) % 16)))
    urlPart = _ecbCrypt('jo6aey6haid2Teih', step2)
    return urlPart.decode("utf-8")

def reverseStreamPath(urlPart):
    step2 = _ecbDecrypt('jo6aey6haid2Teih', urlPart)
    (_, md5, media_format, sng_id, media_version, _) = step2.split(b'\xa4')
    return (sng_id.decode('utf-8'), md5.decode('utf-8'), media_version.decode('utf-8'), media_format.decode('utf-8'))

def generateCryptedStreamURL(sng_id, md5, media_version, media_format): # 生成加密的流媒体链接
    urlPart = generateStreamPath(sng_id, md5, media_version, media_format)
    return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/mobile/1/" + urlPart

def generateStreamURL(sng_id, md5, media_version, media_format): # 生成流媒体链接
    urlPart = generateStreamPath(sng_id, md5, media_version, media_format)
    return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/api/1/" + urlPart

def reverseStreamURL(url): # 流媒体链接反转或还原为原始资源
    urlPart = url[url.find("/1/")+3:]
    return reverseStreamPath(urlPart)

def streamTrack(outputStream, track, start=0, downloadObject=None, listener=None):
    if downloadObject and downloadObject.isCanceled: raise DownloadCanceled
    headers= {'User-Agent': USER_AGENT_HEADER}
    chunkLength = start
    isCryptedStream = "/mobile/" in track.downloadURL or "/media/" in track.downloadURL # 根据链接是否带关键字判断是否需要解密

    itemData = {
        'id': track.id,
        'title': track.title,
        'artist': track.mainArtist.name
    }

    try:
        with get(track.downloadURL, headers=headers, stream=True, timeout=10) as request:
            request.raise_for_status()
            if isCryptedStream:
                blowfish_key = generateBlowfishKey(str(track.id))

            # 请求文件的大小
            complete = int(request.headers["Content-Length"])
            if complete == 0: raise DownloadEmpty

            # 请求开始的时间
            startTime = time()
            # 上一秒的下载大小
            tempSize = 0

            if start != 0:
                responseRange = request.headers["Content-Range"]
                if listener:
                    listener.send('downloadInfo', {
                        'uuid': downloadObject.uuid,
                        'data': itemData,
                        'state': "downloading",
                        'alreadyStarted': True,
                        'value': responseRange
                    })
            else:
                if listener:
                    listener.send('downloadInfo', {
                        'uuid': downloadObject.uuid,
                        'data': itemData,
                        'state': "downloading",
                        'alreadyStarted': False,
                        'value': complete
                    })

            isStart = True
            for chunk in request.iter_content(2048 * 3):
                if isCryptedStream:
                    if len(chunk) >= 2048:
                        chunk = decryptChunk(blowfish_key, chunk[0:2048]) + chunk[2048:]

                if isStart and chunk[0] == 0:
                    for i, byte in enumerate(chunk):
                        if byte != 0: break
                    chunk = chunk[i:]
                isStart = False

                outputStream.write(chunk)
                chunkSingleLength = len(chunk)
                chunkLength += chunkSingleLength

                if downloadObject:
                    if isinstance(downloadObject, Single):
                        # chunkProgres = (chunkLength / (complete + start)) * 100
                        chunkProgres = chunkLength / (complete + start)
                        downloadObject.progressNext = chunkProgres
                        downloadObject.fileSize = complete

                        # 每一秒统计一次下载量
                        interval = time() - startTime
                        offset = chunkLength - tempSize
                        if interval > 1 and offset > 0:                          
                            # 重置开始时间
                            startTime = time()
                            # 每秒的下载量
                            speed = offset * (1 / interval)
                            # KB级下载速度处理
                            if 0 <= speed < (1024 ** 2):
                                downloadObject.progressSpeed = f"{(speed / 1024):.2f} KB/s"
                            # MB级下载速度处理
                            else:
                                downloadObject.progressSpeed = f"{(speed / (1024 ** 2)):.2f} MB/s"
                            # 重置上一秒的下载大小
                            tempSize = chunkLength
                            # 计算剩余时间
                            downloadObject.progressRemainingTime = (complete - chunkLength) / speed
                            downloadObject.updateProgress(listener)
                    else:
                        chunkProgres = (chunkSingleLength / (complete + start)) / downloadObject.size * 100
                        downloadObject.progressNext += chunkProgres
                        downloadObject.updateProgress(listener)

                    # downloadObject.updateProgress(listener)

    except (SSLError, u3SSLError):
        streamTrack(outputStream, track, chunkLength, downloadObject, listener)
    except (RequestsConnectionError, ReadTimeout, ChunkedEncodingError):
        sleep(2)
        streamTrack(outputStream, track, start, downloadObject, listener)
