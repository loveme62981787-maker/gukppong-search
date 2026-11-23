import unittest
import channel_exclusions as c


class ChannelExclusionsTests(unittest.TestCase):
    def test_all_sources_and_future_ids(self):
        config = {'channels': [{'id': 'channel1', 'handle': '@blocked', 'names': ['Blocked Name']}], 'video_ids': ['known']}
        sources = ['window.VIDEOS=[{"id":"new","channel_id":"channel1"},{"id":"keep","channel":"Other","title":"Blocked Name"}];',
                   'window.ALERTS=[{"id":"new"},{"id":"known"}];',
                   'window.HOT_SHORTS={"channels":[{"id":"channel1"}],"videos":[{"id":"future","channel_id":"channel1"}]};',
                   'window.VIDEO_LICENSES={"items":{"known":{"license":"cc"},"keep":{"license":"cc"}}};']
        ids = c.blocked_ids(sources, config)
        self.assertEqual(ids, {'known', 'new', 'future', 'channel1'})
        values = [list(c.assignments(c.filter_text(s, config, ids)))[0][2] for s in sources]
        self.assertEqual([r['id'] for r in values[0]], ['keep'])
        self.assertEqual(values[1], [])
        self.assertEqual(values[2], {'channels': [], 'videos': []})
        self.assertEqual(set(values[3]['items']), {'keep'})

    def test_exact_alias_and_nondata_unchanged(self):
        config = {'channels': [{'id': 'c', 'handle': '@blocked', 'names': ['Blocked Name']}]}
        self.assertTrue(c.matched({'channel': 'BLOCKED NAME'}, config))
        self.assertTrue(c.matched({'channel_url': 'https://www.youtube.com/@blocked'}, config))
        self.assertFalse(c.matched({'channel': 'Blocked Name Fan'}, config))
        text = 'window.fn=()=>42;\nwindow.OTHER=[{"id":"safe"}];'
        self.assertEqual(c.filter_text(text, config, set()), text)
