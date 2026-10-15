import json
import unittest
from datetime import datetime
from unittest.mock import patch

import build_site
import discover


class ObservationValidationTests(unittest.TestCase):
    def test_malformed_history_keeps_valid_points(self):
        stamp = '2026-10-15T00:00:00Z'
        rows = [None, [], ['bad', 1], ['2026-10-15', 1], [stamp, -1], [stamp, True],
                [stamp, '100'], [stamp, 100]]
        self.assertEqual(build_site.merge_history(rows, None, 0), [[stamp, 100]])
        self.assertEqual(build_site.merge_history({}, 'bad', 100), [])

    def test_missing_views_are_not_an_observed_zero(self):
        renderer = {'videoId': 'video', 'title': {'runs': [{'text': 'title'}]},
                    'publishedTimeText': {'simpleText': '1 hour ago'},
                    'ownerText': {'runs': [{'text': 'channel', 'navigationEndpoint': {
                        'browseEndpoint': {'browseId': 'channel'}}}]}}
        for value, known in [('100 views', True), ('0 views', True), ('unknown', False)]:
            renderer['viewCountText'] = {'simpleText': value}
            page = 'var ytInitialData = ' + json.dumps({'videoRenderer': renderer}) + ';</script>'
            with patch.object(discover, 'get', return_value=page):
                row = discover.search('test', 7)[0]
            item = build_site.to_item(row, '한국', 'recent', datetime.now(build_site.KST))
            self.assertEqual(item['observed_at'] is not None, known)
            self.assertEqual(len(item['views_history']), 1 if known else 0)
            previous = '2026-10-14T00:00:00Z'
            saved = dict(row, views=5000, observed_at=previous, views_history=[[previous, 5000]])
            build_site.merge_items({'video': saved}, [item], '2026-10-15')
            self.assertEqual(saved['views'], row['views'] if known else 5000)
            self.assertEqual(len(saved['views_history']), 2 if known else 1)

    def test_duplicate_timestamp_preserves_first_value(self):
        stamp = '2026-10-15T00:00:00Z'
        self.assertEqual(build_site.merge_history([[stamp, 5000]], stamp, 0), [[stamp, 5000]])

    def test_bad_incoming_timestamp_does_not_replace_valid(self):
        stamp = '2026-10-15T00:00:00Z'
        old = dict(id='video', views=10, subs=10, observed_at=stamp, subs_checked_at=stamp)
        build_site.merge_items({'video': old}, [dict(id='video', views=None, subs=None,
                              observed_at='bad', subs_checked_at='bad')], '2026-10-15')
        self.assertEqual(old['observed_at'], stamp)
        self.assertEqual(old['subs_checked_at'], stamp)
