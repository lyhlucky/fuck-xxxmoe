import requests
import json
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET


class Api:
    def __init__(self, auth, media_info, proxies):
        self.proxies = proxies
        self.media_info = media_info
        self.title = unquote(media_info["title"]).replace("\n", " ")

        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "authorization": auth,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

    def parse_url(self, url):
        result = urlparse(url)
        path_arr = result.path.split('/')
        path_ending = path_arr[-1]
        if path_ending == "home":
            account_id = self._fetch_account_id(self.media_info["user_name"])
            post_id = self._fetch_post_id(account_id, self.title)
            return self._fetch_post(post_id)
        elif path_ending == "posts" or "/posts/" in result.path:
            user_name = path_arr[1]
            account_id = self._fetch_account_id(user_name)
            post_id = self._fetch_post_id(account_id, self.title)
            return self._fetch_post(post_id)
        elif "/post/" in result.path:
            post_id = path_ending
            return self._fetch_post(post_id)
        elif "/messages/" in result.path:
            messge_id = path_ending
            message_index = self.media_info["message_index"]
            limit = self.media_info["limit"]
            return self._fetch_message(messge_id, message_index, limit)
        else:
            raise Exception("Unsupport url!")

    def _fetch_account_id(self, username):
        try:
            url = f"https://apiv3.fansly.com/api/v1/account?usernames={username}&ngsw-bypass=true"
            response = self.session.get(url, proxies=self.proxies)
            webplayback = json.loads(response.text)
            return webplayback["response"][0]["id"]
        except Exception as e:
            raise(e)

    def _fetch_post_id(self, account_id, content):
        try:
            url = f"https://apiv3.fansly.com/api/v1/timelinenew/{account_id}?before=0&after=0&wallId=&contentSearch={content}&ngsw-bypass=true"
            response = self.session.get(url, proxies=self.proxies)
            webplayback = json.loads(response.text)
            return webplayback["response"]["posts"][0]["id"]
        except Exception as e:
            raise(e)
        
    def _fetch_post(self, post_id):
        try:
            url = f"https://apiv3.fansly.com/api/v1/post?ids={post_id}&ngsw-bypass=true"
            response = self.session.get(url, proxies=self.proxies)
            webplayback = json.loads(response.text)
            posts = webplayback["response"]["posts"]
            attachments = next(i for i in posts if i["id"] == post_id)["attachments"]
            video_index = self.media_info["video_index"]
            if video_index < len(attachments):
                content_id = attachments[video_index]["contentId"]
            else:
                content_id = attachments[0]["contentId"]

            aggregatedPosts = webplayback["response"]["aggregatedPosts"] #用户转发的视频改用aggregatedPosts的内容
            if len(aggregatedPosts) != 0:
                for item in aggregatedPosts:
                    if item["id"] == content_id:
                        attachments = item["attachments"]
                        video_index = self.media_info["video_index"]
                        if video_index < len(attachments):
                            content_id = attachments[video_index]["contentId"]
                        else:
                            content_id = attachments[0]["contentId"]
            
            accountMediaBundles = webplayback["response"]["accountMediaBundles"]
            if len(accountMediaBundles) != 0: 
                for item in accountMediaBundles:
                    if item["id"] == content_id:
                        accountMediaIds = item["accountMediaIds"]
                        video_index = self.media_info["video_index"]
                        content_id = accountMediaIds[video_index]

            account_medias = webplayback["response"]["accountMedia"]
            # account_media = next(i for i in account_medias if i["id"] == content_id)
            account_media = None
            for i in account_medias:
                if i["id"] == content_id:
                    account_media = i
                    break
            
            if account_media is None:
                url = f"https://apiv3.fansly.com/api/v1/account/media?ids={content_id}&ngsw-bypass=true"
                response = self.session.get(url, proxies=self.proxies)
                media_data = response.json()
                account_media = media_data['response'][0]

            medias = account_media["media"]["variants"]

            mpd_media = None
            is_m3u8 = False
            for i in medias:
                if i["mimetype"] == "application/dash+xml":
                    mpd_media = i
                    break

            if mpd_media is None or (mpd_media is not None and len(mpd_media["locations"]) == 0):
                if "preview" in account_media:
                    previews = account_media["preview"]["variants"]
                    for i in previews :
                        if i["mimetype"] == "application/dash+xml":
                            mpd_media = i
                            break
 
            if mpd_media is None:
                is_m3u8 = True
                for i in medias:
                    if i["mimetype"] == "application/vnd.apple.mpegurl":
                        mpd_media = i
                        break

            if mpd_media is None or (mpd_media is not None and len(mpd_media["locations"]) == 0):
                is_m3u8 =True
                if "preview" in account_media:
                    previews = account_media["preview"]["variants"]
                    for i in previews :
                        if i["mimetype"] == "application/vnd.apple.mpegurl":
                            mpd_media = i
                            break
                
            mpd_location = mpd_media["locations"][0]
            metadata = mpd_location["metadata"]

            resolution =  json.loads(mpd_media["metadata"])["variants"][0]
            if resolution["h"] < resolution["w"]:
                quality = resolution["h"]
            else:
                quality = resolution["w"]
                
            headers = {
                "Cookie": f'CloudFront-Key-Pair-Id={metadata["Key-Pair-Id"]}; CloudFront-Signature={metadata["Signature"]}; CloudFront-Policy={metadata["Policy"]}'
            }

            if (is_m3u8 != True):
                response = requests.get(mpd_location["location"], headers=headers, proxies=self.proxies)
                root = ET.fromstring(response.text)
                adaptationsets = root.findall('.//{urn:mpeg:dash:schema:mpd:2011}BaseURL')
                origial_video_name = adaptationsets[0].text
                
                origial_audio_name = ""
                for audio_name in adaptationsets:
                    if "media-audio" in audio_name.text:
                        origial_audio_name = audio_name.text
                        break
                    
                parts = f'{mpd_location["location"]}'.split("/")
                parts[-1] = f'{origial_video_name}'
                original_video_url = "/".join(parts)

                if len(origial_audio_name) != 0: #有些视频没有声音，需要判断是否取到名字再走合并
                    parts[-1] = f'{origial_audio_name}'
                    original_audio_url = "/".join(parts)
                else:
                    original_audio_url = ""

                return original_video_url, original_audio_url ,metadata
            else:
                original_video_url = f'{mpd_location["location"][:-5]}_{quality}.m3u8'
                # original_video_url = mpd_location["location"]
                original_audio_url = ""
                return original_video_url,original_audio_url,metadata
        except Exception as e:
            raise(e)
        
    def _fetch_message(self, message_id, message_index, limit):
        try:
            url = f"https://apiv3.fansly.com/api/v1/message?groupId={message_id}&limit={limit}&ngsw-bypass=true"
            response = self.session.get(url, proxies=self.proxies)
            webplayback = json.loads(response.text)
            messages = webplayback["response"]["messages"]
            message = messages[limit - message_index - 1]
            attachments = message["attachments"]
            content_id = next(i for i in attachments if i["messageId"] == message["id"])["contentId"]
            account_medias = webplayback["response"]["accountMedia"]
            

            is_bundle = True
            for i in account_medias:
                if i["id"] == content_id:
                    is_bundle = False
                    break

            if is_bundle:   
                accountMediaBundles = webplayback["response"]["accountMediaBundles"]
                if len(accountMediaBundles) != 0: 
                    accountMediaIds = next(i for i in accountMediaBundles if i["id"] == content_id)["accountMediaIds"]
                    video_index = self.media_info["video_index"]
                    content_id = accountMediaIds[video_index]

            account_media = next(i for i in account_medias if i["id"] == content_id)
            medias = account_media["media"]["variants"]

            mpd_media = None
            is_m3u8 = False
            for i in medias:
                if i["mimetype"] == "application/dash+xml":
                    mpd_media = i
                    break

            if mpd_media is None or (mpd_media is not None and len(mpd_media["locations"]) == 0):
                if "preview" in account_media:
                    previews = account_media["preview"]["variants"]
                    for i in previews :
                        if i["mimetype"] == "application/dash+xml":
                            mpd_media = i
                            break
 
            if mpd_media is None:
                is_m3u8 = True
                for i in medias:
                    if i["mimetype"] == "application/vnd.apple.mpegurl":
                        mpd_media = i
                        break

            if mpd_media is None or (mpd_media is not None and len(mpd_media["locations"]) == 0):
                is_m3u8 =True
                if "preview" in account_media:
                    previews = account_media["preview"]["variants"]
                    for i in previews :
                        if i["mimetype"] == "application/vnd.apple.mpegurl":
                            mpd_media = i
                            break
                
            mpd_location = mpd_media["locations"][0]
            metadata = mpd_location["metadata"]
            
            resolution =  json.loads(mpd_media["metadata"])["variants"][0]
            if resolution["h"] < resolution["w"]:
                quality = resolution["h"]
            else:
                quality = resolution["w"]

            headers = {
                "Cookie": f'CloudFront-Key-Pair-Id={metadata["Key-Pair-Id"]}; CloudFront-Signature={metadata["Signature"]}; CloudFront-Policy={metadata["Policy"]}'
            }

            if (is_m3u8 != True):
                response = requests.get(mpd_location["location"], headers=headers, proxies=self.proxies)
                root = ET.fromstring(response.text)
                adaptationsets = root.findall('.//{urn:mpeg:dash:schema:mpd:2011}BaseURL')
                origial_video_name = adaptationsets[0].text
                
                origial_audio_name = ""
                for audio_name in adaptationsets:
                    if "media-audio" in audio_name.text:
                        origial_audio_name = audio_name.text
                        break
                    
                parts = f'{mpd_location["location"]}'.split("/")
                parts[-1] = f'{origial_video_name}'
                original_video_url = "/".join(parts)

                if len(origial_audio_name) != 0:
                    parts[-1] = f'{origial_audio_name}'
                    original_audio_url = "/".join(parts)
                else:
                    original_audio_url = ""

                return original_video_url, original_audio_url ,metadata
            else:
                original_video_url = f'{mpd_location["location"][:-5]}_{quality}.m3u8'
                original_audio_url = ""
                return original_video_url,original_audio_url,metadata
        
        except Exception as e:
            raise(e)
