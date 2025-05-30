import requests
import base64
import json
import requests
from pywidevine import PSSH, Cdm
import subprocess
from pathlib import Path
from cdmhelper import create_cmd_device


class Crypto:
    def __init__(self, pssh, dmls_url, ffmpeg_location, header, proxies=None):
        self.pssh = PSSH(pssh)
        self.dmls_url = dmls_url
        self.ffmpeg_location = ffmpeg_location
        self.header = header
        self.proxies = proxies

        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'accept':'application/json', 
            'content-encoding':'amz-1.0', 
            'content-type':'application/json', 
            'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36', 
            'csrf-rnd':self.header['csrfrnd'], 
            'csrf-token':self.header['csrftoken'], 
            'csrf-ts':self.header['csrfts'], 
            'authorization':self.header['token'], 
            'x-amz-target':'com.amazon.digitalmusiclocator.DigitalMusicLocatorServiceExternal.getLicenseForPlaybackV2'})
        
        self.cdm = Cdm.from_device(create_cmd_device())
        self.cdm_session = self.cdm.open()

    def get_decryption_keys(self):
        challenge = self.cdm.get_license_challenge(self.cdm_session, self.pssh)
        license_b64 = self._get_license_b64(challenge)
        self.cdm.parse_license(self.cdm_session, license_b64)
        # for i in self.cdm.get_keys(self.cdm_session):
        #     if i.type == "CONTENT":
        #         return f"{i.kid.hex}:{i.key.hex()}"
        return f'1:{next(i for i in self.cdm.get_keys(self.cdm_session) if i.type == "CONTENT").key.hex()}'
    
    def decrypt(self, decryption_key, encrypted_location, decrypted_location):
        subprocess.run(
            [
                str(Path(self.ffmpeg_location) / 'itg-key'),
                encrypted_location,
                "--key",
                decryption_key,
                decrypted_location,
            ],
            check=True,
        )

    def _get_license_b64(self, challenge):
        b64challenge = base64.b64encode(challenge).decode()
        license_response = self.session.post(
            url=self.dmls_url,
            proxies=self.proxies,
            data=(json.dumps({'licenseChallenge': b64challenge,
            'Authorization':self.header['token'], 
            'DrmType':'WIDEVINE', 
            'appInfo':{'musicAgent': 'Maestro/1.0 WebCP/1.0.12443.0 (ab9e-ebb8-WebC-55b3-232d3)'}, 
            'customerId':self.header['customerId'], 
            'deviceToken':{'deviceTypeId':self.header['deviceType'], 
            'deviceId':self.header['deviceId']}})))
        
        if license_response.status_code != 200:
            raise Exception(f"Get license failed")
        
        license_response_json = license_response.json()
        if 'license' not in license_response_json:
            raise Exception("Invalid license response")

        license_b64 = license_response_json['license']
        return license_b64