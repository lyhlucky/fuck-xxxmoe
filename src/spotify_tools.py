# coding: utf8

# inspired by: https://github.com/ritiek/spotify-downloader/blob/master/spotdl/spotify_tools.py

import logging
import spotipy
import spotipy.oauth2 as oauth2
from titlecase import titlecase
import common
import sys
import requests


logger = logging.getLogger('spotiy_tools')
spotify = None
g_proxies = None
g_access_token = None


def init(proxies, access_token=None):
    global g_proxies
    global g_access_token

    g_proxies = proxies
    g_access_token = access_token


def generate_token():
    """ Generate the token. """
    credentials = oauth2.SpotifyClientCredentials(
        client_id="4fe3fecfe5334023a1472516cc99d805",
        client_secret="0f02b7c483c04257984695007a4a8d5c",
        proxies=g_proxies
    )
    token = credentials.get_access_token()
    return token


def must_be_authorized(func, spotify=spotify):
    def wrapper(*args, **kwargs):
        global spotify
        try:
            assert spotify
            return func(*args, **kwargs)
        except (AssertionError, spotipy.client.SpotifyException):
            if g_access_token is None:
                token = generate_token()
            else:
                token = g_access_token
            spotify = spotipy.Spotify(auth=token, proxies=g_proxies)
            return func(*args, **kwargs)

    return wrapper


@must_be_authorized
def generate_metadata(raw_song):
    """ Fetch a song's metadata from Spotify. """
    # fetch track information directly if it is spotify link
    logger.debug("Fetching metadata for given track URL")
    meta_tags = spotify.track(raw_song)

    artist = spotify.artist(meta_tags["artists"][0]["id"])
    album = spotify.album(meta_tags["album"]["id"])

    try:
        meta_tags[u"genre"] = titlecase(artist["genres"][0])
    except IndexError:
        meta_tags[u"genre"] = None
    try:
        meta_tags[u"copyright"] = album["copyrights"][0]["text"]
    except IndexError:
        meta_tags[u"copyright"] = None
    try:
        meta_tags[u"external_ids"][u"isrc"]
    except KeyError:
        meta_tags[u"external_ids"][u"isrc"] = None

    meta_tags[u"release_date"] = album["release_date"]
    meta_tags[u"publisher"] = album["label"]
    meta_tags[u"total_tracks"] = album["tracks"]["total"]

    # Some sugar
    meta_tags["year"], *_ = meta_tags["release_date"].split("-")
    meta_tags["duration"] = meta_tags["duration_ms"] / 1000.0
    meta_tags["spotify_metadata"] = True
    # Remove unwanted parameters
    del meta_tags["duration_ms"]
    del meta_tags["available_markets"]
    del meta_tags["album"]["available_markets"]

    return meta_tags


@must_be_authorized
def fetch_playlist(playlist):
    try:
        playlist_id = common.extract_spotify_id(playlist)
    except IndexError:
        # Wrong format, in either case
        logger.error("The provided playlist URL is not in a recognized format!")
        sys.exit(10)
    try:
        # results = spotify.user_playlist(
        #     user=None, playlist_id=playlist_id, fields="tracks,next,name"
        # )
        results = spotify.playlist(
            playlist_id=playlist_id
        )
    except spotipy.client.SpotifyException:
        logger.error("Unable to find playlist")
        logger.info("Make sure the playlist is set to publicly visible and then try again")
        sys.exit(11)

    return get_track_urls(results['tracks'], results['name'])


@must_be_authorized
def fetch_album(album):
    album_id = common.extract_spotify_id(album)
    album = spotify.album(album_id)
    return get_track_urls(album['tracks'], common.sanitize_title(album['name']))


@must_be_authorized
def fetch_artist(artist_url, album_type=None):
    # fetching artist's albums limitting the results to the US to avoid duplicate
    # albums from multiple markets
    artist_id = common.extract_spotify_id(artist_url)
    results = spotify.artist_albums(artist_id, album_type=album_type, country="US")

    albums = results["items"]
    autoken = generate_token
    # indexing all pages of results
    while results["next"]:
        results = spotify.next(results)
        albums.extend(results["items"])

    tracks = []
    for album in albums:
        tracks.extend(fetch_album(album["external_urls"]["spotify"]))

    return tracks


@must_be_authorized
def fetch_show(show):
    show_id = common.extract_spotify_id(show)
    url = f"https://api.spotify.com/v1/shows/{show_id}"
    
    headers = {
        "Authorization": f'Bearer {g_access_token}' 
    }

    response = requests.get(url,headers = headers,proxies=g_proxies)

    if response.status_code == 200:
        data = response.json()
    else:
        logger.error("Unable to find shows")
        sys.exit(11)
    return get_track_urls(data['episodes'], data['name'])


@must_be_authorized
def get_track_urls(tracks, list_name):
    track_urls = []
    count = 1
    while True:
        for item in tracks["items"]:
            if "track" in item:
                track = item["track"]
            else:
                track = item
            try:
                music = {}
                music['url'] = track["external_urls"]["spotify"] + f"?itdl_pname={common.sanitize_title(list_name)}&itdl_pindex={count}"
                music['title'] = track['name']
                track_urls.append(music)
                count += 1
            except KeyError:
                logger.warning(
                    u"Skipping track {0} by {1} (local only?)".format(
                        track["name"], track["artists"][0]["name"]
                    )
                )
        # 1 page = 50 results
        # check if there are more pages
        if tracks["next"]:
            tracks = spotify.next(tracks)
        else:
            break

    total = len(track_urls)
    for music in track_urls:
        music['url'] += f"&itdl_ptotal={total}"
    return track_urls
