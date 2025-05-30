import re
import sys
from urllib.parse import urlparse, parse_qs

from my_get.applemusic import AppleMusicAdaptor
from my_get.thinkific import ThinkificAdaptor
from my_get.linemusic import LineMusicAdaptor
from my_get.udemy import UdemyAdaptor
from my_get.pornhat import PornhatAdaptor
from my_get.tube8 import Tube8Adaptor
from my_get.fansone import FansoneAdaptor
from my_get.deezermusic.deezermusic import DeerzerAdaptor
from my_get.amazonmusic.amazonmusic import AmazonMusicAdaptor
from my_get.tidal.tidalmusic import TidalAdaptor
from my_get.fansly.fansly import FanslyAdaptor
from my_get.onlyfans import OnlyFansAdaptor
from my_get.tktube import TktubeAdaptor
from my_get.boundhub import BoundhubAdaptor
from my_get.pornslash import PornSlashAdaptor
from my_get.caribbeancom import CaribbeancomAdaptor
from my_get.tnaflix import TnaflixAdaptor
from my_get.missav import MissavAdaptor
from my_get.netflix import NetFlixAdaptor
from my_get.myfansjp import MyFansJpAdaptor
from my_get.pornzog import PornzogAdaptor
from my_get.unext import UnextAdaptor


class MyGetProxy:
    def __init__(self, url, params, proxies, progress_hook=None):
        self.original_url = url
        self.params = params
        self.proxies = proxies
        self.progress_hook = progress_hook
        self.audio_bit_rate = ''
        self.sub_path = ''
        self.downloaded_filepath = None

        self.is_applemusic = False
        self.is_deezer = False
        self.is_amazon = False
        self.is_tidal = False
        self.is_fansly = False
        self.is_onlyfans = False
        self.is_thinkific = False
        self.is_linemusic = False
        self.is_udemy = False
        self.is_pornhat = False
        self.is_tube8 = False
        self.is_fansone = False
        self.is_cctv = False
        self.is_tktube = False
        self.is_boundhub = False
        self.is_pornslash = False
        self.is_caribbeancom = False
        self.is_tnaflix = False
        self.is_missav = False
        self.is_netflix = False
        self.is_myfansjp = False
        self.is_pornzog = False
        self.is_unext = False

        self._identify_website()

    def _identify_website(self):
        if re.search('music.apple.com', self.original_url):
            self.is_applemusic = True
        elif re.search('www.deezer.com|dzr.page.link|deezer.page.link', self.original_url):
            self.is_deezer = True
        elif re.search('music.amazon.', self.original_url):
            self.is_amazon = True
        elif re.search('tidal.com', self.original_url):
            self.is_tidal = True
        elif re.search('fansly.com', self.original_url):
            self.is_fansly = True
        elif re.search('onlyfans.com', self.original_url):
            self.is_onlyfans = True
        elif re.search('thinkific.com', self.original_url):
            self.is_thinkific = True
        elif re.search('music.line.me/webapp|https://lin.ee/', self.original_url):
            self.is_linemusic = True
        elif re.search('udemy.com', self.original_url):
            self.is_udemy = True
        elif re.search('www.pornhat.com', self.original_url):
            self.is_pornhat = True
        elif re.search('www.tube8.com', self.original_url):
            self.is_tube8 = True
        elif re.search('fansone.co/', self.original_url):
            self.is_fansone = True
        elif re.search('tv.cctv.com', self.original_url):
            self.is_cctv = True
        elif re.search('tktube.com', self.original_url):
            self.is_tktube = True
        elif re.search('boundhub.com', self.original_url):
            self.is_boundhub = True
        elif re.search('pornslash.com', self.original_url):
            self.is_pornslash = True
        elif re.search('caribbeancom.com', self.original_url):
            self.is_caribbeancom = True
        elif re.search('tnaflix.com', self.original_url):
            self.is_tnaflix = True
        elif re.search('missav.com|missav123.com', self.original_url):
            self.is_missav = True
        elif re.search('netflix.com', self.original_url):
            self.is_netflix = True
        elif re.search('myfans.jp', self.original_url):
            self.is_myfansjp = True
        elif re.search('video.unext.jp', self.original_url):
            self.is_unext = True
        else:
            parsed = urlparse(self.params['url'])
            qs = parse_qs(parsed.query)
            if 'itdl_from' in qs:
                current_site = qs['itdl_from'][0]
                if current_site == 'pornzog':
                    self.is_pornzog = True

        # if sys.platform.startswith("win32"):
        #     pass
        # else:
        #     # 由于curl_cffi最低要求macos12.0以上系统，暂不支持粘贴下载
        #     self.is_boundhub = False
        #     self.is_missav = False
        #     self.is_tktube = False

    def extract(self) -> bool:
        if self.is_applemusic:
            apple_music_ap = AppleMusicAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            apple_music_ap.extract()
            self.downloaded_filepath = apple_music_ap.final_location
            self.audio_bit_rate = apple_music_ap.audio_bit_rate
            self.sub_path = apple_music_ap.lrc_path
            return True
        elif self.is_deezer:
            if 'sessdata' in self.params:
                deezer_ap = DeerzerAdaptor(self.params)
                deezer_ap.download()
                self.downloaded_filepath = deezer_ap.final_location
                self.audio_bit_rate = "320k"
                return True
            else:
                return False
        elif self.is_amazon:
            amazon_ap = AmazonMusicAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            amazon_ap.extract()
            self.downloaded_filepath = amazon_ap.final_location
            self.audio_bit_rate = amazon_ap.audio_bit_rate
            return True
        elif self.is_tidal:
            tidal_ap = TidalAdaptor(self.params)
            tidal_ap.download()
            self.downloaded_filepath = tidal_ap.final_location
            self.audio_bit_rate = "320k"
            return True
        elif self.is_fansly:
            fansly_ap = FanslyAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            fansly_ap.extract()
            self.downloaded_filepath = fansly_ap.final_location
            return True
        elif self.is_onlyfans:
            onlyfans_ap = OnlyFansAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            onlyfans_ap.extract()
            self.downloaded_filepath = onlyfans_ap.final_location
            return True
        elif self.is_thinkific:
            thinkific_ap = ThinkificAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            thinkific_ap.extract()
            self.downloaded_filepath = thinkific_ap.final_location
            return True
        elif self.is_linemusic:
            linemusic_ap = LineMusicAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            linemusic_ap.extract()
            self.downloaded_filepath = linemusic_ap.final_location
            return True
        elif self.is_udemy:
            udemy_ap = UdemyAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            udemy_ap.extract()
            self.downloaded_filepath = udemy_ap.final_location
            return True
        elif self.is_pornhat:
            pornhat_ap = PornhatAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            pornhat_ap.extract()
            self.downloaded_filepath = pornhat_ap.final_location
            return True
        elif self.is_tube8:
            tube8_ap = Tube8Adaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            tube8_ap.extract()
            self.downloaded_filepath = tube8_ap.final_location
            return True
        elif self.is_fansone:
            fansone_ap = FansoneAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            fansone_ap.extract()
            self.downloaded_filepath = fansone_ap.final_location
            return True
        elif self.is_tktube:
            tktube_ap = TktubeAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            tktube_ap.extract()
            self.downloaded_filepath = tktube_ap.final_location
            return True
        elif self.is_boundhub:
            boundhub_ap = BoundhubAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            boundhub_ap.extract()
            self.downloaded_filepath = boundhub_ap.final_location
            return True
        elif self.is_pornslash:
            pornslash_ap = PornSlashAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            pornslash_ap.extract()
            self.downloaded_filepath = pornslash_ap.final_location
            return True
        elif self.is_caribbeancom:
            caribbeancom_ap = CaribbeancomAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            caribbeancom_ap.extract()
            self.downloaded_filepath = caribbeancom_ap.final_location
            return True
        elif self.is_tnaflix:
            tnaflix_ap = TnaflixAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            tnaflix_ap.extract()
            self.downloaded_filepath = tnaflix_ap.final_location
            return True
        elif self.is_missav:
            missav_ap = MissavAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            missav_ap.extract()
            self.downloaded_filepath = missav_ap.final_location
            return True
        elif self.is_netflix:
            netflix_ap = NetFlixAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            netflix_ap.extract()
            self.downloaded_filepath = netflix_ap.final_location
            return True
        elif self.is_myfansjp:
            myfans_ap = MyFansJpAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            myfans_ap.extract()
            self.downloaded_filepath = myfans_ap.final_location
            return True
        elif self.is_pornzog:
            pornzog_ap = PornzogAdaptor(self.original_url, params=self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            pornzog_ap.extract()
            self.downloaded_filepath = pornzog_ap.final_location
            return True
        elif self.is_unext:
            unext_ap = UnextAdaptor(self.original_url, params=self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            unext_ap.extract()
            self.downloaded_filepath = unext_ap.final_location
            return True

        return False
    
    def extract_playlist(self) -> bool:
        if self.is_applemusic:
            apple_music_ap = AppleMusicAdaptor(self.params, proxies=self.proxies)
            apple_music_ap.extract_playlist()
            return True
        elif self.is_deezer:
            deezer_ap = DeerzerAdaptor(self.params)
            deezer_ap.download()
            return True
        elif self.is_amazon:
            amazon_ap = AmazonMusicAdaptor(self.params, proxies=self.proxies)
            amazon_ap.extract()
            return True
        elif self.is_tidal:
            tidal_ap = TidalAdaptor(self.params)
            tidal_ap.download()
            return True
        elif self.is_linemusic:
            linemusic_ap = LineMusicAdaptor(self.params, proxies=self.proxies)
            linemusic_ap.extract_playlist()
            return True
        elif self.is_thinkific:
            thinkific_ap = ThinkificAdaptor(self.params, proxies=self.proxies)
            thinkific_ap.extract_playlist()
            return True
        elif self.is_onlyfans:
            onlyfans_ap = OnlyFansAdaptor(self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            onlyfans_ap.extract_playlist()
            return True
        elif self.is_unext:
            unext_ap = UnextAdaptor(self.original_url, params=self.params, proxies=self.proxies, progress_hook=self.progress_hook)
            unext_ap.extract_playlist()
            return True
        
        return False
