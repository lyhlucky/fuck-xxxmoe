import logging
from deezer.utils import LyricsStatus
from deezer.errors import GWAPIError, APIError
from deezer.utils import map_user_playlist

from .types.DownloadObjects import Single, Collection
from .errors import GenerationError, ISRCnotOnDeezer, InvalidID, NotYourPrivatePlaylist

logger = logging.getLogger('deemix')

def generateTrackItem(dz, link_id, bitrate, trackAPI=None, albumAPI=None):
    # Check if is an isrc: url
    if str(link_id).startswith("isrc"):
        try:
            trackAPI = dz.api.get_track(link_id)
        except APIError as e:
            raise GenerationError(f"https://deezer.com/track/{link_id}", str(e)) from e

        if 'id' in trackAPI and 'title' in trackAPI:
            link_id = trackAPI['id']
        else:
            raise ISRCnotOnDeezer(f"https://deezer.com/track/{link_id}")
    if not str(link_id).strip('-').isdecimal(): raise InvalidID(f"https://deezer.com/track/{link_id}")

    # Get essential track info
    try:
        trackAPI_gw = dz.gw.get_track_with_fallback(link_id)
    except GWAPIError as e:
        raise GenerationError(f"https://deezer.com/track/{link_id}", str(e)) from e

    title = trackAPI_gw['SNG_TITLE'].strip()
    if trackAPI_gw.get('VERSION') and trackAPI_gw['VERSION'] not in trackAPI_gw['SNG_TITLE']:
        title += f" {trackAPI_gw['VERSION']}".strip()
    explicit = bool(int(trackAPI_gw.get('EXPLICIT_LYRICS', 0)))

    return Single({
        'type': 'track',
        'id': link_id,
        'bitrate': bitrate,
        'title': title,
        'artist': trackAPI_gw['ART_NAME'],
        'cover': f"https://e-cdns-images.dzcdn.net/images/cover/{trackAPI_gw['ALB_PICTURE']}/75x75-000000-80-0-0.jpg",
        'explicit': explicit,
        'single': {
            'trackAPI_gw': trackAPI_gw,
            'trackAPI': trackAPI,
            'albumAPI': albumAPI
        }
    })

def generateAlbumItem(dz, link_id, bitrate, rootArtist=None):
    # Get essential album info
    if str(link_id).startswith('upc'):
        upcs = [link_id[4:],]
        upcs.append(int(upcs[0]))
        lastError = None
        for upc in upcs:
            try:
                albumAPI = dz.api.get_album(f"upc:{upc}")
            except APIError as e:
                lastError = e
                albumAPI = None
        if not albumAPI:
            raise GenerationError(f"https://deezer.com/album/{link_id}", str(lastError)) from lastError
        link_id = albumAPI['id']
    else:
        try:
            albumAPI = dz.api.get_album(link_id)
        except APIError as e:
            raise GenerationError(f"https://deezer.com/album/{link_id}", str(e)) from e

    if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/album/{link_id}")

    # Get extra info about album
    # This saves extra api calls when downloading
    albumAPI_gw = dz.gw.get_album(link_id)
    albumAPI['nb_disk'] = albumAPI_gw['NUMBER_DISK']
    albumAPI['copyright'] = albumAPI_gw['COPYRIGHT']
    albumAPI['release_date'] = albumAPI_gw['PHYSICAL_RELEASE_DATE']
    albumAPI['root_artist'] = rootArtist

    # If the album is a single download as a track
    if albumAPI['nb_tracks'] == 1:
        if len(albumAPI['tracks']['data']):
            return generateTrackItem(dz, albumAPI['tracks']['data'][0]['id'], bitrate, albumAPI=albumAPI)
        raise GenerationError(f"https://deezer.com/album/{link_id}", "Single has no tracks.")

    tracksArray = dz.gw.get_album_tracks(link_id)

    if albumAPI['cover_small'] is not None:
        cover = albumAPI['cover_small'][:-24] + '/75x75-000000-80-0-0.jpg'
    else:
        cover = f"https://e-cdns-images.dzcdn.net/images/cover/{albumAPI_gw['ALB_PICTURE']}/75x75-000000-80-0-0.jpg"

    totalSize = len(tracksArray)
    albumAPI['nb_tracks'] = totalSize
    collection = []
    for pos, trackAPI in enumerate(tracksArray, start=1):
        trackAPI['POSITION'] = pos
        trackAPI['SIZE'] = totalSize
        collection.append(trackAPI)

    explicit = albumAPI_gw.get('EXPLICIT_ALBUM_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS') in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]

    return Collection({
        'type': 'album',
        'id': link_id,
        'bitrate': bitrate,
        'title': albumAPI['title'],
        'artist': albumAPI['artist']['name'],
        'cover': cover,
        'explicit': explicit,
        'size': totalSize,
        'collection': {
            'tracks_gw': collection,
            'albumAPI': albumAPI
        }
    })

def generatePlaylistItem(dz, link_id, bitrate, playlistAPI=None, playlistTracksAPI=None):
    if not playlistAPI:
        if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/playlist/{link_id}")
        # Get essential playlist info
        try:
            playlistAPI = dz.api.get_playlist(link_id)
        except APIError:
            playlistAPI = None
        # Fallback to gw api if the playlist is private
        if not playlistAPI:
            try:
                userPlaylist = dz.gw.get_playlist_page(link_id)
                playlistAPI = map_user_playlist(userPlaylist['DATA'])
            except GWAPIError as e:
                raise GenerationError(f"https://deezer.com/playlist/{link_id}", str(e)) from e

        # Check if private playlist and owner
        if not playlistAPI.get('public', False) and playlistAPI['creator']['id'] != str(dz.current_user['id']):
            logger.warning("You can't download others private playlists.")
            raise NotYourPrivatePlaylist(f"https://deezer.com/playlist/{link_id}")

    if not playlistTracksAPI:
        playlistTracksAPI = dz.gw.get_playlist_tracks(link_id)
    playlistAPI['various_artist'] = dz.api.get_artist(5080) # Useful for save as compilation

    totalSize = len(playlistTracksAPI)
    playlistAPI['nb_tracks'] = totalSize
    collection = []
    for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
        if trackAPI.get('EXPLICIT_TRACK_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]:
            playlistAPI['explicit'] = True
        trackAPI['POSITION'] = pos
        trackAPI['SIZE'] = totalSize
        collection.append(trackAPI)

    if 'explicit' not in playlistAPI: playlistAPI['explicit'] = False

    return Collection({
        'type': 'playlist',
        'id': link_id,
        'bitrate': bitrate,
        'title': playlistAPI['title'],
        'artist': playlistAPI['creator']['name'],
        'cover': playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
        'explicit': playlistAPI['explicit'],
        'size': totalSize,
        'collection': {
            'tracks_gw': collection,
            'playlistAPI': playlistAPI
        }
    })

def generateArtistItem(dz, link_id, bitrate, listener=None):
    if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/artist/{link_id}")
    # Get essential artist info
    try:
        artistAPI = dz.api.get_artist(link_id)
    except APIError as e:
        raise GenerationError(f"https://deezer.com/artist/{link_id}", str(e)) from e

    rootArtist = {
        'id': artistAPI['id'],
        'name': artistAPI['name'],
        'picture_small': artistAPI['picture_small']
    }
    if listener: listener.send("startAddingArtist", rootArtist)

    artistDiscographyAPI = dz.gw.get_artist_discography(link_id, 100)
    allReleases = artistDiscographyAPI.pop('all', [])
    albumList = []
    for album in allReleases:
        try:
            albumList.append(generateAlbumItem(dz, album['id'], bitrate, rootArtist=rootArtist))
        except GenerationError as e:
            logger.warning("Album %s has no data: %s", str(album['id']), str(e))

    if listener: listener.send("finishAddingArtist", rootArtist)
    return albumList

def generateArtistDiscographyItem(dz, link_id, bitrate, listener=None):
    if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/artist/{link_id}/discography")
    # Get essential artist info
    try:
        artistAPI = dz.api.get_artist(link_id)
    except APIError as e:
        raise GenerationError(f"https://deezer.com/artist/{link_id}/discography", str(e)) from e

    rootArtist = {
        'id': artistAPI['id'],
        'name': artistAPI['name'],
        'picture_small': artistAPI['picture_small']
    }
    if listener: listener.send("startAddingArtist", rootArtist)

    artistDiscographyAPI = dz.gw.get_artist_discography_tabs(link_id, 100)
    artistDiscographyAPI.pop('all', None) # all contains albums and singles, so its all duplicates. This removes them
    albumList = []
    for releaseType in artistDiscographyAPI:
        for album in artistDiscographyAPI[releaseType]:
            try:
                albumList.append(generateAlbumItem(dz, album['id'], bitrate, rootArtist=rootArtist))
            except GenerationError as e:
                logger.warning("Album %s has no data: %s", str(album['id']), str(e))

    if listener: listener.send("finishAddingArtist", rootArtist)
    return albumList

def generateArtistTopItem(dz, link_id, bitrate):
    if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/artist/{link_id}/top_track")
    # Get essential artist info
    try:
        artistAPI = dz.api.get_artist(link_id)
    except APIError as e:
        raise GenerationError(f"https://deezer.com/artist/{link_id}/top_track", str(e)) from e

    # Emulate the creation of a playlist
    # Can't use generatePlaylistItem directly as this is not a real playlist
    playlistAPI = {
        'id':f"{artistAPI['id']}_top_track",
        'title': f"{artistAPI['name']} - Top Tracks",
        'description': f"Top Tracks for {artistAPI['name']}",
        'duration': 0,
        'public': True,
        'is_loved_track': False,
        'collaborative': False,
        'nb_tracks': 0,
        'fans': artistAPI['nb_fan'],
        'link': f"https://www.deezer.com/artist/{artistAPI['id']}/top_track",
        'share': None,
        'picture': artistAPI['picture'],
        'picture_small': artistAPI['picture_small'],
        'picture_medium': artistAPI['picture_medium'],
        'picture_big': artistAPI['picture_big'],
        'picture_xl': artistAPI['picture_xl'],
        'checksum': None,
        'tracklist': f"https://api.deezer.com/artist/{artistAPI['id']}/top",
        'creation_date': "XXXX-00-00",
        'creator': {
            'id': f"art_{artistAPI['id']}",
            'name': artistAPI['name'],
            'type': "user"
        },
        'type': "playlist"
    }

    artistTopTracksAPI_gw = dz.gw.get_artist_top_tracks(link_id)
    return generatePlaylistItem(dz, playlistAPI['id'], bitrate, playlistAPI=playlistAPI, playlistTracksAPI=artistTopTracksAPI_gw)
