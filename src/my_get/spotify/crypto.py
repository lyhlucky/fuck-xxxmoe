import requests
import base64
import requests
from pywidevine import PSSH, Cdm
import subprocess
from pathlib import Path
import logging
from cdmhelper import create_cmd_device


logger = logging.getLogger('spotifyCrypto')

class Crypto:
    def __init__(self, pssh, ffmpeg_location, headers, proxies=None):
        self.pssh = PSSH(pssh)
        self.ffmpeg_location = ffmpeg_location
        self.headers = headers
        self.proxies = proxies

        self.session = requests.Session()
        self.session.verify = False
        # self.session.headers.update({
        #     "Authorization": f"{self.headers['authorization']}",
        #     'origin': 'https://open.spotify.com',
        #     'referer': 'https://open.spotify.com/',
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        # })

        self.session.headers.update({
            'Accept': '*/*',
            "Authorization": f"{self.headers['authorization']}",
            'origin': 'https://open.spotify.com',
            'referer': 'https://open.spotify.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15'
        })
        
        self.cdm = Cdm.from_device(create_cmd_device())
        self.cdm_session = self.cdm.open()

    def get_decryption_keys(self):
        challenge = self.cdm.get_license_challenge(self.cdm_session, self.pssh)
        license_b64 = self._get_license_b64(challenge)
        self.cdm.parse_license(self.cdm_session, license_b64)
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
        license_b64 = None

        urls = [
            "https://gae2-spclient.spotify.com/widevine-license/v1/audio/license",
            "https://gue1-spclient.spotify.com/widevine-license/v1/audio/license"
        ]

        for url in urls:
            response = self.session.post(
                url=url,
                data=challenge,
                proxies=self.proxies
            )
            if response.status_code == 200:
                license_b64 = base64.b64encode(response.content).decode('utf8')
                break
            else:
                logger.info(f"Get license failed! [{response.status_code}] {response.reason}: {response.content}")

        # attemps = 0

        # while attemps < 3:
        #     attemps += 1

        #     try:
        #         response = self.session.post(
        #             url='https://gue1-spclient.spotify.com/widevine-license/v1/audio/license',
        #             data=challenge,
        #             proxies=self.proxies
        #         )
        #         if response.status_code == 200:
        #             license_b64 = base64.b64encode(response.content).decode('utf8')
        #             break
        #         else:
        #             logger.info(f"Get license failed! [{response.status_code}] {response.reason}: {response.content}")
        #     except:
        #             logger.info("Get license Exception")

        return license_b64