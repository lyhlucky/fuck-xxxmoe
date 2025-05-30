#!/usr/bin/env python

__all__ = ['tiktok_download']

from ..common import *

from bs4 import BeautifulSoup
import requests
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'}

def get_video_url(tiktok_url):
    '''Extract video source url from usual TikTok url

    Parameters:
    tiktok_url (str): TikTok url

    Returns:
    str: video source url
    '''

    r = requests.get(tiktok_url, headers=headers, allow_redirects=True)

    if r.status_code != 200:
        print('Bad request to TikTok server. Status code: {}'.format(r.status_code))
        raise Exception('Bad request to TikTok server. Status code: {}'.format(r.status_code))

    soup = BeautifulSoup(r.text, 'html.parser')
    data = soup.find('script', attrs={'id': '__NEXT_DATA__'})

    if not data:
        print('Can\'t get data from url. Check error.txt')
        raise Exception('Can\'t get data from url. Check error.txt')

    data = json.loads(data.text)

    try:
        video_url = data['props']['pageProps']['videoData']['itemInfos']['video']['urls'][0]

    except Exception as e:
        raise e

    return video_url


def get_video_id(soruce_video_url):
    '''Extract video id from source video url

    Parameters:
    soruce_video_url (str): Source video url

    Returns:
    str: video id
    '''

    r = requests.get(soruce_video_url, headers=headers)

    if r.status_code != 200:
        raise Exception('Bad request to source video server. Status code: {}'.format(r.status_code))

    content = r.content
    position = content.find('vid:'.encode())

    if position == -1:
        print('Can\'t find video id')
        raise Exception('Can\'t find video id')

    video_id = content[position+4:position+36].decode('utf-8')

    return video_id

def tiktok_download(url, output_dir='.', merge=True, info_only=False, **kwargs):
    referUrl = url.split('?')[0]
    headers = fake_headers

    # trick or treat
    html = get_content(url, headers=headers)
    data = r1(r'<script id="__NEXT_DATA__".*?>(.*?)</script>', html)
    info = json.loads(data)
    wid = info['props']['initialProps']['$wid']
    cookie = 'tt_webid=%s; tt_webid_v2=%s' % (wid, wid)

    # here's the cookie
    headers['Cookie'] = cookie

    # try again
    html = get_content(url, headers=headers)
    data = r1(r'<script id="__NEXT_DATA__".*?>(.*?)</script>', html)
    info = json.loads(data)
    wid = info['props']['initialProps']['$wid']
    cookie = 'tt_webid=%s; tt_webid_v2=%s' % (wid, wid)

    videoData = info['props']['pageProps']['itemInfo']['itemStruct']
    videoId = videoData['id']
    videoUrl = videoData['video']['downloadAddr']
    uniqueId = videoData['author'].get('uniqueId')
    nickName = videoData['author'].get('nickname')

    title = '%s [%s]' % (nickName or uniqueId, videoId)

    # we also need the referer
    headers['Referer'] = referUrl

    source = videoUrl
    mime, ext, size = url_info(source, headers=headers)

    print_info(site_info, title, mime, size)
    kwargs['progress_hook']({
        'status': 'info',
        'data': {
            'title': title,
        },
    })

    if not info_only:
        download_urls([source], title, ext, size, output_dir, headers=headers, merge=merge, **kwargs)

site_info = "TikTok.com"
download = tiktok_download
download_playlist = playlist_not_supported('tiktok')
