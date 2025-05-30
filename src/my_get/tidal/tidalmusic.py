#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import sys

from .events import *
from .settings import *



class TidalAdaptor:
    def __init__(self, params):
        self.params = params
        self.final_location = ''


    def download(self):       
        TOKEN.read(getTokenPath())
        TIDAL_API.apiKey = apiKey.getItem()
        SETTINGS.downloadPath = self.params['save_path']
        if self.params['add_playlist_index'] == "true":
            SETTINGS.addPlaylistIndex = True
            SETTINGS.playlistIndex = self.params["playlist_index"]

        initToken()
        
        start(self.params['url'])
        self.final_location = TIDAL_Download.finalPath 




# if __name__ == '__main__':
#     path = "C:\\Users\\lucky\\Desktop"
#     url = "https://tidal.com/browse/track/282500346"
#     dl = TidalAdaptor
#     dl.download(path,url)



