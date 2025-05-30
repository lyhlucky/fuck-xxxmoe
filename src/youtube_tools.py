# coding: utf8

# inspired by: https://github.com/ritiek/spotify-downloader/blob/master/spotdl/youtube_tools.py

import logging
import spotify_tools
from bs4 import BeautifulSoup
import urllib
import common
import re
import json
import ssl


logger = logging.getLogger('youtube_tools')

BASE_SEARCH_URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q={}"

def match_video_and_metadata(track, proxies=None):
    """ Get and match track data from Spotify. """
    meta_tags = None

    logger.debug("Input song is a Spotify URL")

    if proxies is not None:
        spotify_tools.init(proxies)

    # Let it generate metadata, YouTube doesn't know Spotify slang
    meta_tags = spotify_tools.generate_metadata(track)
    search_query = []
    search_query_retry = 2
    for i in range(search_query_retry):
        search_query.append(common.format_string(
            "{artist} - {track_name}", meta_tags, force_spaces=True
        ))
    for i in range(search_query_retry):
        search_query.append(common.format_string(
            "{track_name}", meta_tags, force_spaces=True
        ))
    youtube_url = YouTubeSearch().search(search_query)

    ret = {
        'url': youtube_url,
        'title': None,
        'thumbnail': None
    }

    if 'name' in meta_tags:
        ret['title'] = meta_tags['name']
    if 'album' in meta_tags:
        if 'images' in meta_tags['album'] and len(meta_tags['album']['images']) > 0:
            ret['thumbnail'] = meta_tags['album']['images'][0]['url']
        if 'name' in meta_tags['album']:
            ret['album'] = meta_tags['album']['name']
    if 'artists' in meta_tags and len(meta_tags['artists']) > 0:
        ret['artist'] = meta_tags['artists'][0]['name']
    if 'release_date' in meta_tags:
        ret['date'] = meta_tags['release_date']

    return ret


class YouTubeSearch:
    def __init__(self):
        self.base_search_url = BASE_SEARCH_URL

    def generate_search_url(self, query):
        quoted_query = urllib.request.quote(query)
        return self.base_search_url.format(quoted_query)

    def _fetch_response_html(self, url):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(url, context=ctx)
        soup = BeautifulSoup(response.read(), "html.parser")
        return soup

    def _extract_video_details_from_result(self, html):
        video_time = html.find("span", class_="video-time").get_text()
        inner_html = html.find("div", class_="yt-lockup-content")
        video_id = inner_html.find("a")["href"][-11:]
        video_title = inner_html.find("a")["title"]
        video_details = {
            "url": "https://www.youtube.com/watch?v=" + video_id,
            "title": video_title,
            "duration": video_time,
        }
        return video_details

    def _fetch_search_results(self, html, limit=10):
        scripts = html.find_all('script')
        for script in scripts:
            try:
                if script and script.string.find('ytInitialData') != -1:
                    m = re.search(r'({.*?});', script.string)
                    if m:
                        data = m.group(1)
                        ytInitialData = json.loads(data)
                        videos = []
                        contents = ytInitialData['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']

                        for content in contents:
                            if 'videoRenderer' in content:
                                video = {
                                    'url': 'https://www.youtube.com/watch?v=' + content['videoRenderer']['videoId'],
                                    'title': '',
                                    'duration': '',
                                }
                                videos.append(video)

                                if len(videos) >= limit:
                                    break
                        if len(videos) > 0:
                            return videos
            except Exception as e:
                continue

        result_source = html.find_all(
            "div", {"class": "yt-lockup-dismissable yt-uix-tile"}
        )
        videos = []

        for result in result_source:
            if not self._is_video(result):
                continue

            video = self._extract_video_details_from_result(result)
            videos.append(video)

            if len(videos) >= limit:
                break

        return videos

    def _is_video(self, result):
        # ensure result is not a channel
        not_video = (
            result.find("channel") is not None
            or "yt-lockup-channel" in result.parent.attrs["class"]
            or "yt-lockup-channel" in result.attrs["class"]
        )

        # ensure result is not a mix/playlist
        not_video = not_video or "yt-lockup-playlist" in result.parent.attrs["class"]

        # ensure video result is not an advertisement
        not_video = not_video or result.find("googleads") is not None
        # ensure video result is not a live stream
        not_video = not_video or result.find("span", class_="video-time") is None

        video = not not_video
        return video

    def _is_server_side_invalid_response(self, videos, html):
        if videos:
            return False
        search_message = html.find("div", {"class": "search-message"})
        return search_message is None

    def search(self, query, retries=0):
        """ Search and scrape YouTube to return a list of matching videos. """
        search_url = self.generate_search_url(query[retries])
        logger.debug('Fetching YouTube results for "{}" at "{}".'.format(query[retries], search_url))
        html = self._fetch_response_html(search_url)
        videos = self._fetch_search_results(html)
        to_retry = retries < len(query) - 1
        if to_retry and len(videos) < 1:
            logger.debug(
                "Retrying since YouTube returned invalid response for search "
                "results. Retries left: {retries}.".format(retries=retries)
            )
            return self.search(query, retries=retries+1)
        return videos[0]["url"]
