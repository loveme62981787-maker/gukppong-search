import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import score_alerts as scorer


class TaiwanAndPreservationTests(unittest.TestCase):
    def test_taiwan_public_rows_are_unique_longform_and_whitelisted(self):
        rows = json.loads((Path(__file__).parents[1] / 'data/taiwan_videos.json').read_text(encoding='utf-8'))['items']
        self.assertGreater(len(rows), 0)
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        allowed = {'id','title','channel','channel_id','views','subs','length','duration_sec','published','age_text','country','section','sources','first_seen','observed_at'}
        for row in rows:
            self.assertLessEqual(set(row), allowed)
            self.assertEqual(row['country'], '대만')
            self.assertGreater(row['duration_sec'], 180)
            self.assertRegex(row['published'], r'^\d{4}-\d{2}-\d{2}$')

    def test_claude_baseline_is_never_called_again(self):
        with patch.object(scorer, 'manual_ids', return_value=set()), patch.object(scorer, 'alerts', side_effect=AssertionError('must not load candidates')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                scorer.score_unlocked('3l-QftM5c94', Path('not-needed.txt'))
            self.assertEqual(json.loads(output.getvalue())['status'], 'already_scored')
