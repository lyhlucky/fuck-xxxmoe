import base64
import json


class MetadataExtractor():
    def __init__(self, url, metadata):
        self.url = url
        self.metadata = json.loads(base64.b64decode(metadata))

    def process(self):
        extractor_type = self._get_extractor_type()
        if extractor_type == 'youtube':
            return self._youtube_extractor()
        if extractor_type == 'common':
            return self._youtube_extractor()

    def _get_extractor_type(self):
        if 'youtube.com' in self.url:
            return 'youtube'
        else:
            return 'common'

    def _youtube_extractor(self):
        result = {
            'id': self.url,
            'title': self.metadata['title'],
            'thumbnails': [{
                'url': self.metadata['thumbnail']['url'],
                'width': self.metadata['thumbnail']['width'],
                'height': self.metadata['thumbnail']['height'],
                'id': 0,
            }],
            'extractor': 'youtube',
            'extractor_key': 'Youtube',
            'thumbnail': self.metadata['thumbnail']['url'],
            'display_id': self.url,
            'requested_formats': {},
            'format': '',
            'format_id': '',
            'local_thumbnail': '',
        }

        result['formats'] = []

        def _parse_streams(streams):
            for stream in streams:
                mime = self._parse_yt_mimetype(stream['mimeType'])
                format = {
                    'format_id': str(stream['itag']),
                    'url': stream['url'],
                    'protocol': stream['url'].split(':')[0],
                    'ext': mime.get('ext'),
                    'acodec': mime.get('acodec'),
                    'vcodec': mime.get('vcodec'),
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'fps': stream.get('fps'),
                    'format': f"{stream.get('itag')} - {stream.get('width')}x{stream.get('height')} ({stream.get('qualityLabel')})",
                    'filesize': int(stream['contentLength']) if 'contentLength' in stream else 0,
                    'asr': None,
                    'abr': stream.get('averageBitrate'),
                }
                result['formats'].append(format)

        _parse_streams(self.metadata['stream'])
        _parse_streams(self.metadata['adaptive'])

        return result

    def _parse_yt_mimetype(self, mime):
        type = mime.split(';')[0].split('/')[0]
        ext = mime.split(';')[0].split('/')[1]
        codecs = mime.split(';')[1].split('=')[1].split(',')
        vcodec = 'none'
        acodec = 'none'
        if type == 'video':
            if len(codecs) == 1:
                vcodec = codecs[0][1:-1]
            if len(codecs) == 2:
                vcodec = codecs[0][1:]
                acodec = codecs[1][:-1]
        if type == 'audio':
            if len(codecs) == 1:
                acodec = codecs[0][1:-1]

        return {
            'ext': ext,
            'vcodec': vcodec,
            'acodec': acodec,
        }
