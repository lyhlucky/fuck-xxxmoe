
import requests
import json
from base64 import b64decode
import xml.etree.ElementTree as ET
from yt_dlp import YoutubeDL
from urllib.parse import urlparse, unquote
import os
import time
import subprocess
import hashlib
from common import MsgType, flush_print, sanitize_filename, wrap_cookie_dict, sanitize_title
from pywidevine import PSSH, Cdm
import re
from cdmhelper import create_cmd_device
import logging
import traceback

logger = logging.getLogger('onlyfans')

"""
https://raw.githubusercontent.com/deviint/onlyfans-dynamic-rules/main/dynamicRules.json
https://raw.githubusercontent.com/Growik/onlyfans-dynamic-rules/main/rules.json
https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/main/onlyfans.json

onlyfans-dynamic-rules
{
	"static_param": "RPnq8UadKceN7JNbeh2ApmUxM0A2nU9y",
	"start": "24650",
	"end": "666078a0",
	"checksum_constant": 13,
	"checksum_indexes": [4,5,7,9,9,11,13,17,18,19,23,23,23,24,25,26,27,27,28,28,28,28,28,29,30,32,32,33,33,34,34,38],
	"app_token": "33d57ade8c02dbc5a333db99ff9ae26a",
	"remove_headers": ["user_id"],
    "revision": "202404181902-08205f45c3",
    "is_current": null,
	"format": "24650:{}:{:x}:666078a0",
	"prefix": "24650",
	"suffix": "666078a0"
}     
"""

class OnlyFansAdaptor:
    def __init__(
        self,
        params,
        progress_hook,
        proxies
    ):
        self.params = params
        self.progress_hook = progress_hook
        self.proxies = proxies
        self.ffmpeg_location = params['ffmpeg_location']
        self.final_location = None
        self.video_title = None
        self.cookie_dict = json.loads(b64decode(self.params['sessdata']).decode('utf-8'))
        self.cookie = wrap_cookie_dict(self.cookie_dict)
        self.metadata = json.loads(b64decode(params['metadata']).decode('utf-8'))
        self.is_direct_download = False

        if 'playlist' in self.params:
            self.mediaList = list()
            self.user_agent = self.params['user-agent']
            self.author = None
            self.filter_type = 'All'
            if(self.metadata['mediaType'] == 'Video'):
                self.filter_type = 'video'
            elif(self.metadata['mediaType'] == 'Image'):
                self.filter_type = 'photo'
            
            self.filter_starttime =  int(self.metadata['startTime'])
            self.filter_endtime = int(self.metadata['endTime'])
        elif ('is_drm' in self.metadata and not self.metadata['is_drm']) or ('type' in self.metadata and self.metadata['type'] == 'photo'):
            self.is_direct_download = True
        else:
            self.mpd_cookie = None
            self.post_id = self.metadata['post_id']
            self.video_id = self.metadata['video_id']
            self.is_chat = self.metadata['is_chat']
            self.is_paid = self.metadata['is_paid']
            self.user_agent = self.metadata['user-agent']

    def extract(self):
        if self.is_direct_download:
            self.video_title = sanitize_filename(unquote(self.metadata['title']))
            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': self.video_title,
                    'thumbnail': self.metadata['thumbnail'],
                    'local_thumbnail': '',
                    'duration': 0,
                    'is_live': False
                }
            }))
            file_path = f"{self.params['save_path']}/{self.video_title}"
            max_path = 180
            if (len(file_path) > max_path):
                file_path = file_path[0:max_path]
                self.video_title = os.path.basename(file_path).strip()
            
            if self.metadata['type'] == 'photo':
                self.final_location = f"{self.params['save_path']}/{self.video_title}.jpg"
            else:
                self.final_location = f"{self.params['save_path']}/{self.video_title}.mp4"
            
            videoUrl = None
            if 'url' in self.metadata:
                videoUrl = self.metadata['url']
            else:
                videoUrl = self.params['url']

            attemps1 = 0
            maxretry1=2
            while attemps1 < maxretry1:

                try:
                    attemps1 += 1
                    self._download(videoUrl, self.cookie, self.final_location)
                    break
                except Exception as e:
                    self.video_title = sanitize_title(unquote(self.video_title))
                    if self.metadata['type'] == 'photo':
                        self.final_location = f"{self.params['save_path']}/{self.video_title}.jpg"
                    else:
                        self.final_location = f"{self.params['save_path']}/{self.video_title}.mp4"
                    if attemps1 == 2:
                        logger.error(traceback.format_exc())
            return
        
        # 获取密钥
        pssh, video_url, audio_url = self._get_video_info()
        decryption_key = self._get_decryption_keys(pssh)
        cookie = f'{self.mpd_cookie}; {self.cookie}'
        save_path = self.params['save_path']
        current_directory = os.getcwd()
        os.chdir(save_path)

        # 下载视频
        video_save_path = 'video_encrypt.mp4'
        if os.path.exists(video_save_path):
            os.remove(video_save_path)
        self._download(video_url, cookie, video_save_path)

        # 下载音频
        audio_save_path = 'audio_encrypt.m4a'
        if os.path.exists(audio_save_path):
            os.remove(audio_save_path)
        self._download(audio_url, cookie, audio_save_path)

        # 解密视频
        video_decrypt_path = 'video_decrypt.mp4'
        self._decrypt_file(decryption_key, video_save_path, video_decrypt_path)

        # 解密音频
        audio_decrypt_path = 'audio_decrypt.m4a'
        self._decrypt_file(decryption_key, audio_save_path, audio_decrypt_path)

        # 合并视频和音频
        video_output = "video_fixed.mp4"
        self._merger_files(video_decrypt_path, audio_decrypt_path, video_output)

        # 移动视频到下载路径
        valid_filename = sanitize_filename(self.video_title)
        file_path = f"{save_path}/{valid_filename}"
        max_path = 180
        if (len(file_path) > max_path):
            file_path = file_path[0:max_path]
            valid_filename = os.path.basename(file_path).strip()

        attemps = 0
        while attemps < 4:
            attemps += 1
            try:
                os.rename(video_output, f"{valid_filename}.mp4")
                self.final_location = f"{save_path}/{valid_filename}.mp4"
                break
            except OSError as e:
                logger.info(f"rename error: {e}")
                if attemps == 1:
                    valid_filename = sanitize_title(valid_filename)
                elif attemps == 2:
                    valid_filename = valid_filename[0:20]
                else:
                    valid_filename = f"Onlyfans-{int(time.time() * 1000)}"

        os.chdir(current_directory)

    def _get_video_info(self):
        def parse_drm(media: dict):
            thumb_url = ''
            if 'thumb' in media:
                thumb_url = media['thumb']
            elif 'files' in media and 'thumb' in media['files']:
                thumb_url = media['files']['thumb']['url']
            
            if self.video_title is None:
                self.video_title = 'OnlyFans'

            flush_print(json.dumps({
                'type': MsgType.sniff.value,
                'msg': {
                    'ret_code': '0',
                    'title': sanitize_filename(self.video_title),
                    'thumbnail': thumb_url,
                    'local_thumbnail': '',
                    'duration': 0,
                    'is_live': False
                }
            }))

            drm = media['files']['drm']
            mpd_url = drm['manifest']['dash']
            signature_dash = drm['signature']['dash']
            cf_kpi = signature_dash['CloudFront-Key-Pair-Id']
            cf_policy = signature_dash['CloudFront-Policy']
            cf_signature = signature_dash['CloudFront-Signature']
            self.mpd_cookie = f'CloudFront-Key-Pair-Id={cf_kpi};CloudFront-Policy={cf_policy};CloudFront-Signature={cf_signature}'
            return self._request_mpd(mpd_url)

        if self.is_chat:
            def get_message(chat_id: str, next_id=None):
                url = f'https://onlyfans.com/api2/v2/chats/{chat_id}/messages?limit=100&order=desc&skip_users=all'
                if next_id is not None:
                    url = url + f'&id={next_id}'

                headers = self._make_headers_with_sign(url)
                response = requests.get(url, headers=headers, proxies=self.proxies)
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
                
            # https://onlyfans.com/my/chats/chat/1689310
            # https://onlyfans.com/my/chats/chat/1689310/
            # https://onlyfans.com/my/chats/chat/1689310/pinned
            chat_id = None
            next_id = None
            original_url = self.params['url']
            
            if original_url.endswith('/'):
                original_url = original_url[0:-1]

            match = re.search(r'/chat/(\d+)', original_url)
            if match:
                chat_id = match.group(1)

            if not chat_id:
                chat_id = self.metadata['chat_id']
            while True:
                content = get_message(chat_id, next_id)
                message_list = content['list']
                for item in message_list:
                    if str(item['id']) == self.post_id:
                        media_list = item['media']
                        for media in media_list:
                            if str(media['id']) == self.video_id:
                                if 'text' in item:
                                    self.video_title = item['text']
                                return parse_drm(media)
                        break
                
                if content['hasMore']:
                    next_id = message_list[-1]['id']
                else:
                    break

            return None
        else:
            if self.is_paid:
                def get_paid(offset: int):
                    url = f'https://onlyfans.com/api2/v2/posts/paid?limit=100&skip_users=all&format=infinite&offset={offset}'
                    headers = self._make_headers_with_sign(url)
                    response = requests.get(url, headers=headers, proxies=self.proxies)     
                    content = response.json()
                    return content
                
                offset = 0
                
                while True:
                    content = get_paid(offset)
                    message_list = content['list']
                    for item in message_list:
                        if str(item['id']) == self.post_id:
                            if(item['responseType'] == 'message'):
                                self.is_chat = True
                            media_list = item['media']
                            for media in media_list:
                                if str(media['id']) == self.video_id:
                                    if 'text' in item:
                                        self.video_title = item['text']
                                    return parse_drm(media)
                            break
                
                    if content['hasMore']:
                        offset += 100
                    else:
                        break
            else:
                url = f'https://onlyfans.com/api2/v2/posts/{self.post_id}?skip_users=all'
                headers = self._make_headers_with_sign(url)
                response = requests.get(url, headers=headers, proxies=self.proxies)     
                content = response.json()
                media_list = content['media']

                for media in media_list:
                    if self.video_id == str(media['id']):
                        if 'text' in content:
                            self.video_title = content['text']
                        return parse_drm(media)
        return None

    def _make_headers_with_sign(self, link: str):
        content = None
        try:
            # rules_url = 'https://download.itubego.com/itubego/tools/onlyfans_dynamic_rules.json'
            rules_url = 'https://download.onvideoeditor.com/itubego/tools/onlyfans_dynamic_rules.json'
            response = requests.get(rules_url, proxies=self.proxies)
            if response.status_code == 200:
                config = response.json()
                rules_link = config['link']
                if len(rules_link) == 0:
                    content = config["rules"]
                else:
                    link_response = requests.get(rules_link, proxies=self.proxies)
                    if link_response.status_code == 200:
                        content = link_response.json()
        except Exception as e:
            logger.info(f'Request dynamic rules failed: {e}')

        if content is None:
            content = {
	            "static_param": "LeVvhQ1CyK0S2GRIQe7EUGSmuYDlHU1d",
	            "start": "36673",
	            "end": "67a331d2",
	            "checksum_constant": -993,
	            "checksum_indexes": [1, 1, 3, 4, 5, 7, 8, 10, 11, 13, 14, 14, 14, 15, 15, 17, 18, 18, 19, 20, 22, 22, 24, 24, 27, 29, 30, 33, 33, 35, 37, 39],
	            "app_token": "33d57ade8c02dbc5a333db99ff9ae26a",
	            "remove_headers": ["user_id"],
	            "revision": "202502050939-12f98d453f",
	            "format": "36673:{}:{:x}:67a331d2",
	            "prefix": "36673",
	            "suffix": "67a331d2"
            }     

        timestamp = str(round(time.time() * 1000))

        if "app_token" in content:
            app_token = content["app_token"]
        else:
            app_token = content["app-token"]

        path = urlparse(link).path
        query = urlparse(link).query
        path = path if not query else f"{path}?{query}"

        static_param = content["static_param"]

        a = [static_param, timestamp, path, self.cookie_dict['auth_id']]
        msg = "\n".join(a)

        message = msg.encode("utf-8")
        hash_object = hashlib.sha1(message)
        sha_1_sign = hash_object.hexdigest()
        sha_1_b = sha_1_sign.encode("ascii")

        checksum_indexes = content["checksum_indexes"]
        checksum_constant = content["checksum_constant"]
        checksum = sum(sha_1_b[i] for i in checksum_indexes) + checksum_constant

        if 'format' in content:
            final_sign = content['format'].format(sha_1_sign, abs(checksum))
        else:
            final_sign = f'{content["prefix"]}:{sha_1_sign}:{hex(abs(checksum))[2:]}:{content["suffix"]}'

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': self.user_agent,
            'X-Bc': self.cookie_dict['fp'],
            'User-Id': self.cookie_dict['auth_id'],
            'Cookie': self.cookie,
            'App-Token': app_token,
            'Sign': final_sign,
            'Time': timestamp
        }
        return headers
    
    def _request_mpd(self, url):
        headers = {
            'Accept': '*/*', 
            'User-Agent': self.user_agent,
            'Cookie': self.mpd_cookie
        }

        response = requests.get(url, headers=headers, proxies=self.proxies)
        root = ET.fromstring(response.text)
        adaptationsets = root.findall('.//{urn:mpeg:dash:schema:mpd:2011}AdaptationSet')
        final_pssh = ''
        video_url = ''
        audio_url = ''
        host = url[0 : url.rfind("/") + 1]

        for adaptation in adaptationsets:
            contentProtections = adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}ContentProtection')
            final_pssh = contentProtections[2].find('{urn:mpeg:cenc:2013}pssh').text
            representations = adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}Representation')

            for representation in representations:
                baseurl = representation.find('{urn:mpeg:dash:schema:mpd:2011}BaseURL').text

                if baseurl.find('_source.') != -1:
                    video_url = host + baseurl
                elif baseurl.find('_audio.') != -1:
                    audio_url = host + baseurl

        return final_pssh, video_url, audio_url
    
    def _get_license(self, url, headers, payload):
        response = requests.post(url, data=payload, headers=headers, proxies=self.proxies)
        return response.content

    def _get_decryption_keys(self, pssh):
        # or self.is_paid
        if self.is_chat :
            license_url = f'https://onlyfans.com/api2/v2/users/media/{self.video_id}/drm/message/{self.post_id}?type=widevine'
        else:
            license_url = f'https://onlyfans.com/api2/v2/users/media/{self.video_id}/drm/post/{self.post_id}?type=widevine'
        headers = self._make_headers_with_sign(license_url)
        cdm = Cdm.from_device(create_cmd_device())
        cdm_session_id = cdm.open()
        resp1 = self._get_license(license_url, headers, bytes.fromhex('08 04'))
        cdm.set_service_certificate(cdm_session_id, resp1)
        challenge = cdm.get_license_challenge(cdm_session_id, PSSH(pssh))
        resp2 = self._get_license(license_url, headers, challenge)
        cdm.parse_license(cdm_session_id, resp2)
        content_key = next(i for i in cdm.get_keys(cdm_session_id) if i.type == "CONTENT")
        return f'{content_key.kid.hex}:{content_key.key.hex()}'
        
    def _download(self, url, cookie, output):
        http_headers = {
            "Cookie": cookie
        }

        ydl_opts = {
            'cachedir': False,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'playliststart': 1,
            'playlistend': 1,
            'retries': 3,
            'ffmpeg_location': self.ffmpeg_location,
            "http_headers": http_headers,
            'outtmpl': output,
        }

        if 'proxy' in self.params and self.params['proxy'] is not None:
            proxy = self.params['proxy']
            if 'host' in proxy and proxy['host']:
                if proxy['password'] != '':
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    ydl_opts['proxy'] = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"    
        
        with YoutubeDL(ydl_opts) as ydl:
            if self.progress_hook is not None:
                ydl.add_progress_hook(self.progress_hook)
            ydl.download(url)

    def _decrypt_file(self, drm_key, src_file, dest_file):
        command = [
            os.path.join(self.ffmpeg_location, 'itg-key'),
            '--key', drm_key, src_file, dest_file
        ]
        subprocess.run(command)

    def _merger_files(self, video_src, audio_src, video_output):
        command = [
            os.path.join(self.ffmpeg_location, 'ffmpeg'),
            '-i', video_src,
            '-i', audio_src,
            '-vcodec', 'copy',
            '-acodec', 'copy',
            '-strict', '-2',
            '-y',
            video_output
        ]
        subprocess.run(command)

    def extract_playlist(self):
        urlSplit = self.params['url'].split('/')
        # urlSplit = 'https://onlyfans.com/my/chats/chat/16149273/'.split('/')
        if 'chat' in urlSplit:
            self.requestChatMedias(urlSplit[-2],'')
        else:
            self.getRequestId()
        
    def getRequestId(self):
        urlList = self.params['url'].split('/')
        mediaType = None
        if(urlList[-2]=='onlyfans.com'):
            self.author = urlList[-1]
            mediaType = 'media'
        elif(urlList[-1]=='media' or urlList[-1]=='videos' or urlList[-1]=='photos'):
            self.author = urlList[-2]
            mediaType = urlList[-1]
        else:
            logger.error('url not support batch download')

        if mediaType == 'media':
            mediaType += 's'  
        
        link = f'https://onlyfans.com/api2/v2/users/{self.author}'
        headers = self._make_headers_with_sign(link)
        response = requests.get(link, headers=headers, proxies=self.proxies)     
        content = response.json()
        if 'id' in content:
            userid = content['id']

            link = None
            if self.filter_endtime > 0:
                link = f'https://onlyfans.com/api2/v2/users/{userid}/posts/{mediaType}?limit=100&order=publish_date_desc&skip_users=all&format=infinite&counters=0&&beforePublishTime={self.filter_endtime}.999999'
            else:
                link = f'https://onlyfans.com/api2/v2/users/{userid}/posts/{mediaType}?limit=100&order=publish_date_desc&skip_users=all&format=infinite&counters=1'
            self.requestMedias(userid,link,mediaType)
        else:
            logger.error('onlyfans request id error!')
            
    
    def requestMedias(self,id:str,link:str,type:str):
        
        headers = self._make_headers_with_sign(link)

        content = ''
        try:
            response = requests.get(link, headers=headers, proxies=self.proxies)     
            content = response.json()
        except:
            logger.error(traceback.format_exc())

        publishTime = 0

        if content:            
            self.mediaList.extend(self.parseMediasContent(content))                
            publishTime = content['tailMarker']

        if 'hasMore' in content and content['hasMore'] and ((self.filter_starttime >0 and self.filter_starttime < float(publishTime)) or self.filter_starttime == 0) :
            
            tlink = f'https://onlyfans.com/api2/v2/users/{id}/posts/{type}?limit=100&order=publish_date_desc&skip_users=all&format=infinite&counters=0&&beforePublishTime={publishTime}'
            self.requestMedias(id,tlink,type)
        else:
            flush_print(json.dumps({
                'type': MsgType.playlist.value,
                'msg': {
                    'videos': self.mediaList,
                    'userId': self.author
                }
            }))


    def requestChatMedias(self,chatId:str,meassageId:str):

        # https://onlyfans.com/api2/v2/users/list?m[]=361947617

        # link = f'https://onlyfans.com/api2/v2/users/list?m[]={chatId}'
        # headers = self._make_headers_with_sign(link)
        # response = requests.get(link, headers=headers, proxies=self.proxies)     
        # content = response.json()

        # if content and chatId in content:
        #     self.author = content[chatId]['name']

        self.author = f'chatid_{chatId}'

        link = f'https://onlyfans.com/api2/v2/chats/{chatId}/messages?limit=100&order=desc&skip_users=all{meassageId}'
        headers = self._make_headers_with_sign(link)

        content = ''
        try:
            response = requests.get(link, headers=headers, proxies=self.proxies)     
            content = response.json()
        except:
            logger.error(traceback.format_exc())
        
        if content:
            self.mediaList.extend(self.parseMediasContent(content)) 
                     
            if 'hasMore' in content and content['hasMore'] :
                change_time = content['list'][-1]['changedAt']
                change_time = change_time.split('+')[0]
                change_time = change_time.split('T')
                change_time = f'{change_time[0]} {change_time[1]}'
                change_time = time.strptime(change_time,"%Y-%m-%d %H:%M:%S")
                change_time = int(time.mktime(change_time))   
                if self.filter_starttime < change_time:
                    meassageId = content['list'][-1]['id']
                    self.requestChatMedias(chatId,f'&id={meassageId}')
        
        if len(self.mediaList) >0: 
            flush_print(json.dumps({
                'type': MsgType.playlist.value,
                'msg': {
                    'videos': self.mediaList,
                    'userId': self.author
                }
            }))
    
    def parseMediasContent(self,data:dict):
        mediaList = list()
        for tdata in data['list']:
            madia_key = 'media'
            
            if  madia_key not in tdata:
                continue

            # 日期筛选
            post_time = None
            is_chat = False
            if 'postedAt' in tdata:
                post_time = tdata['postedAt']
            elif 'createdAt' in tdata:
                post_time = tdata['createdAt']
                is_chat = True
            
            timeformat = False
            time_str = None
            dtime = post_time.split('+')
            if  len(dtime) >1:
                dtime = dtime[0].split('T')
                if len(dtime) > 1:
                    time_str = f'{dtime[0]} {dtime[1]}'
                    time_str = time.strptime(time_str,"%Y-%m-%d %H:%M:%S")
                    post_time = int(time.mktime(time_str))                       
                    timeformat = True                
            if not timeformat:
                    logger.error('post time format error!')

            if self.filter_starttime >0 :
                if  post_time > self.filter_endtime:
                    continue
                elif post_time < self.filter_starttime:
                    break

            text = None
            if 'text'  in tdata:           
                text = tdata['text']
                text = sanitize_filename(text)
            
            if not text:
                if not time_str:
                    time_str = time.localtime(time.time())
                                
                time_str = time.strftime('%Y-%m-%d %H:%M:%S',time_str)
                text = f'{self.author}_{time_str}' 

            postId = tdata['id']
            index = 0
            for tmedia in tdata[madia_key]:
                media1 = dict()
                if index > 0:
                    media1['title'] = f'{text}_{index}'
                else:
                    media1['title'] = text
                index += 1
                media1['post_id'] = str(postId)
                media1['video_id'] = str(tmedia['id'])
                media1['post_time'] = post_time
                media1['duration'] = tmedia['duration']

                media_type = tmedia['type']
                if media_type == 'gif':
                    media_type = 'video'
                #类型筛选
                if self.filter_type != 'All' and self.filter_type != media_type: 
                    continue

                if media_type != 'photo' and media_type != 'video' :
                    continue

                media1['type'] = media_type
                media1['url'] = tmedia['files']['full']['url']
                
                if 'thumb' in tmedia['files'] and tmedia['files']['thumb']:
                    media1['thumbnail'] = tmedia['files']['thumb']['url']                                  
                else:
                    if not media1['url'] and 'drm' not in tmedia['files']:    #未付费文件              
                        continue
                
                if 'drm' in tmedia['files']:
                    media1['is_drm'] = True
                else:
                    media1['is_drm'] = False

                media1['is_paid'] = False
                if media1['is_drm'] and media1['url']:
                    media1['is_paid'] = True

                if not media1['url'] :
                        media1['url'] = 'onlyfans.com'
                
                media1['is_chat'] = is_chat

                if is_chat:
                    media1['chat_id'] = self.author.split('_')[-1]
                        
                mediaList.append(media1)
                         
        return mediaList