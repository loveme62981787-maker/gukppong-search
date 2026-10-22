import json
import unittest
from unittest.mock import patch
import caption_fetch as c


class CaptionTests(unittest.TestCase):
    def test_segment_timing_and_entities(self):
        self.assertEqual(c.parse_xml('<timedtext><body><p t="1234"><s>Hello</s><s> &amp; world</s></p><p t="2000">\n</p></body></timedtext>'), '[0:01] Hello & world')
        self.assertEqual(c.parse_xml('<transcript><text start="600.9">end</text></transcript>'), '[10:00] end')

    def test_invalid_xml(self):
        for raw in ('', '<html>blocked</html>', '<!DOCTYPE x><transcript/>', '<timedtext><body><p>missing time</p></body></timedtext>'):
            with self.subTest(raw=raw), self.assertRaises(c.CaptionFailure):
                c.parse_xml(raw)

    def test_public_client_flow_and_identity(self):
        vid = 'abcdefghijk'
        player = {'playabilityStatus': {'status': 'OK'}, 'videoDetails': {'videoId': vid}, 'captions': {'playerCaptionsTracklistRenderer': {'captionTracks': [{'baseUrl': 'https://www.youtube.com/api/timedtext', 'languageCode': 'en'}]}}}
        page = 'var ytInitialPlayerResponse = ' + json.dumps(player) + '; "INNERTUBE_API_KEY":"public_config"'
        with patch.object(c, 'request', side_effect=[page, json.dumps(player), '<transcript><text start="0">hello</text></transcript>']) as call:
            text = c.download({'id': vid})
            self.assertIn('Video ID: '+vid, text)
            self.assertIn('[0:00] hello', text)
            self.assertEqual(call.call_args_list[1].args[1]['videoId'], vid)
        player['videoDetails']['videoId'] = 'other000000'
        with patch.object(c, 'request', side_effect=[page, json.dumps(player)]), self.assertRaisesRegex(c.CaptionFailure, 'mismatch'):
            c.download({'id': vid})

    def test_restricted_video_does_not_call_other_client(self):
        page = 'var ytInitialPlayerResponse = ' + json.dumps({'playabilityStatus': {'status': 'LOGIN_REQUIRED'}})
        with patch.object(c, 'request', return_value=page) as call, self.assertRaises(c.CaptionFailure):
            c.download({'id': 'abcdefghijk'})
        self.assertEqual(call.call_count, 1)

    def test_external_caption_host_rejected(self):
        with self.assertRaisesRegex(c.CaptionFailure, 'host_invalid'):
            c.request('https://example.com/caption')
