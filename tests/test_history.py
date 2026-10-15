import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from unittest.mock import patch

import build_site
import discover


class HistoryTests(unittest.TestCase):
    def setUp(self):
        network = patch("urllib.request.urlopen", side_effect=AssertionError("네트워크 연결 금지"))
        network.start()
        self.addCleanup(network.stop)
        self.now = datetime(2026, 10, 15, 9, 30, tzinfo=build_site.KST)

    def video(self, views=100):
        return dict(id="영상", title="Jeju Korea vlog", channel="여행자",
                    channel_id="채널", age_h=1, views=views, subs=10)

    def item(self, views=100, day=0):
        return build_site.to_item(self.video(views), "한국", "recent",
                                  self.now + timedelta(days=day))

    def test_new_and_null(self):
        item = self.item()
        self.assertEqual(item["observed_at"], "2026-10-15T09:30:00+09:00")
        self.assertEqual(item["views_history"], [[item["observed_at"], 100]])
        self.assertIsNone(json.loads(json.dumps(item))["subs_checked_at"])
        self.assertIsNone(self.item(None)["views"])
        vids = {}
        build_site.merge_items(vids, [item], "2026-10-15")
        self.assertEqual(vids["영상"]["views_history"], item["views_history"])

    def test_history_preserved_and_capped(self):
        vids = {}
        for day in range(15):
            build_site.merge_items(vids, [self.item(day, day)], "2026-10-15")
        expected = [[self.item(day, day)["observed_at"], day] for day in range(3, 15)]
        self.assertEqual(vids["영상"]["views_history"], expected)
        self.assertEqual(vids["영상"]["first_seen"], "2026-10-15")

    def test_duplicates_preserve_original_observation(self):
        item = self.item()
        vids = {"영상": copy.deepcopy(item)}
        for stamp in (item["observed_at"], "2026-10-15T00:30:00+00:00"):
            build_site.merge_items(vids, [dict(item, views=200, observed_at=stamp)], "2026-10-15")
        self.assertEqual(vids["영상"]["views_history"], item["views_history"])

    def test_latest_means_chronological_order(self):
        history = [[self.item(day, day)["observed_at"], day] for day in reversed(range(13))]
        result = build_site.merge_history(history, self.item(0)["observed_at"], 999)
        self.assertEqual([row[1] for row in result], list(range(1, 13)))

    def test_legacy_starts_now_without_backfill(self):
        legacy = dict(self.video(), first_seen="2026-10-01")
        untouched = dict(legacy, id="미발견")
        vids = {"영상": legacy, "미발견": copy.deepcopy(untouched)}
        build_site.merge_items(vids, [self.item()], "2026-10-15")
        self.assertEqual(legacy["views_history"], self.item()["views_history"])
        self.assertIsNone(legacy["subs_checked_at"])
        self.assertEqual(vids["미발견"], untouched)
        build_site.merge_items(vids, [self.video()], "2026-10-15")
        self.assertEqual(legacy["views_history"], self.item()["views_history"])

    def test_invalid_views_do_not_erase_values_or_history(self):
        for invalid in (None, -1):
            with self.subTest(views=invalid):
                old = self.item()
                old["subs_checked_at"] = self.now.isoformat()
                vids = {"영상": copy.deepcopy(old)}
                incoming = self.item(invalid, 1)
                incoming["subs"] = None
                self.assertEqual(incoming["views_history"], [])
                build_site.merge_items(vids, [incoming], "2026-10-16")
                for key in ("views_history", "views", "subs", "subs_checked_at"):
                    self.assertEqual(vids["영상"][key], old[key])

    def test_subscriber_timestamp_only_on_success(self):
        cache, checked = {"구형": 0}, {}
        with patch.object(discover, "get", side_effect=[OSError(), "0 subscribers"]) as get, \
                patch.object(discover.time, "sleep"):
            self.assertEqual(discover.channel_subs("구형", cache, checked), 0)
            self.assertNotIn("구형", checked)
            self.assertIsNone(discover.channel_subs("채널", cache, checked))
            self.assertNotIn("채널", checked)
            self.assertEqual(discover.channel_subs("채널", cache, checked), 0)
            stamp = checked["채널"]
            self.assertIsNotNone(datetime.fromisoformat(stamp).utcoffset())
            self.assertEqual(discover.channel_subs("채널", cache, checked), 0)
            self.assertEqual(checked["채널"], stamp)
            self.assertEqual(get.call_count, 2)

    def test_both_search_routes_propagate_cached_timestamp(self):
        spec = {"queries": ["검색"], "keywords": ["jeju"], "exclude": []}
        st = dict(window_days=7, exclude_names=[], exclude_ids=set(), other_cities_count=5)
        for route in ("country", "cities"):
            for cached in (False, True):
                with self.subTest(route=route, cached=cached):
                    cache = {"채널": 10} if cached else {}
                    checked = {"채널": self.now.isoformat()} if cached else {}
                    with patch.object(discover, "search", return_value=[self.video()]), \
                            patch.object(discover, "get", return_value="10 subscribers") as get, \
                            patch.object(discover.time, "sleep"), \
                            patch.object(discover, "OTHER_CITIES", spec), redirect_stdout(io.StringIO()):
                        if route == "country":
                            result = discover.find_country("한국", spec, st, set(), cache, checked)
                        else:
                            result = discover.find_other_cities(st, set(), set(), cache, checked)
                    self.assertEqual(result[0]["subs_checked_at"], checked["채널"])
                    self.assertEqual(get.call_count, 0 if cached else 1)
                    item = build_site.to_item(result[0], "한국", "recent", self.now)
                    self.assertEqual(item["subs_checked_at"], checked["채널"])
                    if cached:
                        self.assertEqual(checked["채널"], self.now.isoformat())


if __name__ == "__main__":
    unittest.main()
