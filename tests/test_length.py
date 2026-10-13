import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import mock_open, patch

import build_site
import discover


class LengthTests(unittest.TestCase):
    def setUp(self):
        # 외부 통신은 모든 테스트에서 금지한다.
        network = patch("urllib.request.urlopen", side_effect=AssertionError("네트워크 접근 금지"))
        network.start()
        self.addCleanup(network.stop)

    def video(self, ident="영상", duration=754):
        return {"id": ident, "title": "Jeju Korea vlog", "channel": "여행자",
                "channel_id": ident, "age_h": 1, "views": 100, "subs": 10,
                "length": "12:34" if duration == 754 else None,
                "duration_sec": duration, "is_short": discover.is_short(duration, {})}

    def test_parse_duration(self):
        for value, expected in [("12:34", 754), ("1:02:03", 3723), (None, None),
                                ("", None), ("쓰레기값", None), (" ", None),
                                ("1:60", None), ("1:99:03", None), ("-1:02", None),
                                ("1:2", None), (123, None), ("0:00", 0)]:
            with self.subTest(value=value):
                self.assertEqual(discover.parse_duration(value), expected)

    def test_search_length(self):
        for length in ["12:34", "1:02:03", None, "", "쓰레기값"]:
            renderer = {"videoId": "영상", "title": {"runs": [{"text": "제목"}]},
                        "ownerText": {"runs": [{"text": "채널", "navigationEndpoint": {
                            "browseEndpoint": {"browseId": "채널"}}}]}}
            if length is not None:
                renderer["lengthText"] = {"simpleText": length}
            page = "var ytInitialData = " + json.dumps({"videoRenderer": renderer}) + ";</script>"
            with self.subTest(length=length), patch.object(discover, "get", return_value=page):
                video = discover.search("검색", 7)[0]
                duration = discover.parse_duration(length)
                self.assertEqual(video["duration_sec"], duration)
                self.assertEqual(video["length"], length if duration is not None else None)

    def test_boundaries(self):
        for duration, short, keep in [(0, True, False), (179, True, False),
                                      (180, True, False), (181, False, True)]:
            with self.subTest(duration=duration):
                video = self.video(duration=duration)
                self.assertEqual(discover.keep_longform(video, {}), keep)
                self.assertIs(video["is_short"], short)
        st = {"short_max_sec": 60, "longform_min_sec": 300}
        for duration, short, keep in [(60, True, False), (61, False, False),
                                      (299, False, False), (300, False, True)]:
            video = self.video(duration=duration)
            self.assertEqual(discover.keep_longform(video, st), keep)
            self.assertIs(video["is_short"], short)

    def test_unknown_policy(self):
        for st, expected in [({}, True), ({"unknown_length": "keep"}, True),
                             ({"unknown_length": "drop"}, False)]:
            video = self.video(duration=None)
            self.assertEqual(discover.keep_longform(video, st), expected)
            self.assertIsNone(video["is_short"])

    def test_settings_defaults_and_policy(self):
        with patch("builtins.open", mock_open(read_data="[settings]\n")):
            st = discover.load_settings()
        self.assertEqual((st["short_max_sec"], st["longform_min_sec"], st["unknown_length"]),
                         (180, 181, "keep"))
        with patch("builtins.open", mock_open(read_data="[settings]\nunknown_length = drop\n")):
            self.assertEqual(discover.load_settings()["unknown_length"], "drop")
        with patch("builtins.open", mock_open(read_data="[settings]\nunknown_length = 오타\n")):
            with self.assertRaises(ValueError):
                discover.load_settings()

    def test_filter_before_subscriber_lookup(self):
        spec = {"queries": ["검색"], "keywords": ["jeju"], "exclude": []}
        for route in ("country", "cities"):
            for policy in ("keep", "drop"):
                with self.subTest(route=route, policy=policy):
                    st = {"window_days": 7, "exclude_names": [], "exclude_ids": set(),
                          "other_cities_count": 5, "unknown_length": policy}
                    videos = [self.video("쇼츠", 180), self.video("롱폼"),
                              self.video("미확인", None), self.video("캐시")]
                    cache = {"롱폼": None, "캐시": 0}

                    def lookup(cid, cache):
                        cache[cid] = 10
                        return 10

                    with patch.object(discover, "search", return_value=videos), \
                            patch.object(discover, "channel_subs", side_effect=lookup) as subs, \
                            patch.object(discover.time, "sleep"), \
                            patch.object(discover, "OTHER_CITIES", spec), redirect_stdout(io.StringIO()):
                        if route == "country":
                            result = discover.find_country("한국", spec, st, set(), cache)
                        else:
                            result = discover.find_other_cities(st, set(), set(), cache)
                    expected = {"롱폼", "미확인"} if policy == "keep" else {"롱폼"}
                    self.assertEqual({c.args[0] for c in subs.call_args_list}, expected)
                    self.assertEqual({v["id"] for v in result}, expected | {"캐시"})
                    self.assertEqual(cache["캐시"], 0)

    def test_subscriber_cache_retry(self):
        cache = {"채널": None, "성공": 0}
        with patch.object(discover, "get", side_effect=[OSError(), "123 subscribers"]) as get, \
                patch.object(discover.time, "sleep"):
            self.assertIsNone(discover.channel_subs("채널", cache))
            self.assertEqual(discover.channel_subs("채널", cache), 123)
            self.assertEqual(discover.channel_subs("채널", cache), 123)
            self.assertEqual(discover.channel_subs("성공", cache), 0)
            self.assertEqual(get.call_count, 2)

    def test_merge_preserves_nonempty_values(self):
        old = dict(self.video(), first_seen="2026-10-01")
        for empty in (None, "", "   "):
            vids = {old["id"]: copy.deepcopy(old)}
            new = dict(self.video(), length=empty, duration_sec=None, is_short=None, views=200)
            self.assertEqual(build_site.merge_items(vids, [new], "2026-10-14"), [])
            for key in ("length", "duration_sec", "is_short", "first_seen"):
                self.assertEqual(vids[old["id"]][key], old[key])
            self.assertEqual(vids[old["id"]]["views"], 200)

    def test_merge_updates_and_legacy(self):
        now = datetime(2026, 10, 14, tzinfo=build_site.KST)
        item = build_site.to_item(self.video(), "한국", "recent", now)
        for key in ("length", "duration_sec", "is_short"):
            self.assertEqual(item[key], self.video()[key])
        legacy = {k: v for k, v in item.items() if k not in ("length", "duration_sec", "is_short")}
        legacy_video = {k: v for k, v in self.video().items() if k not in ("length", "duration_sec", "is_short")}
        legacy_item = build_site.to_item(legacy_video, "한국", "recent", now)
        for key in ("length", "duration_sec", "is_short"):
            self.assertIsNone(legacy_item[key])
        vids = {"영상": dict(legacy, first_seen="2026-10-01"), "유지": {"id": "유지"}}
        build_site.merge_items(vids, [item], "2026-10-14")
        self.assertIs(vids["영상"]["is_short"], False)
        self.assertEqual(vids["영상"]["duration_sec"], 754)
        self.assertIn("유지", vids)
        build_site.merge_items(vids, [dict(item, duration_sec=0, length="0:00", is_short=True)], "2026-10-14")
        self.assertEqual(vids["영상"]["duration_sec"], 0)
        self.assertIs(vids["영상"]["is_short"], True)
        new = build_site.merge_items(vids, [dict(item, id="신규")], "2026-10-14")
        self.assertEqual(new[0]["first_seen"], "2026-10-14")

    def test_build_offline(self):
        st = discover.load_settings()
        legacy = {"id": "기존", "first_seen": "9999-01-01", "published": "2026-10-01"}
        store = {"videos": {"기존": legacy}, "subs": {}}
        output = io.StringIO()
        opened = mock_open()
        with patch.object(discover, "load_settings", return_value=st), \
                patch.object(discover, "resolve_channels", return_value=set()), \
                patch.object(discover, "find_other_cities", return_value=[]), \
                patch.object(discover, "find_country", return_value=[self.video()]), \
                patch.object(build_site.notifier, "read_json", return_value=store), \
                patch.object(build_site.notifier, "write_json") as write, \
                patch.object(build_site.os, "makedirs"), patch("builtins.open", opened), \
                patch.object(build_site.sys, "argv", ["build_site.py"]), redirect_stdout(output):
            build_site.main()
        exported = "".join(c.args[0] for c in opened().write.call_args_list)
        settings = json.loads(exported.split("window.SETTINGS=", 1)[1].split(";", 1)[0])
        self.assertEqual(set(settings), {"subs_low", "subs_high", "high_views", "ratio_min", "ratio_min_views"})
        self.assertEqual(settings, {k: st[k] for k in settings})
        self.assertIn("영상 2개 저장 (새 영상 1개)", output.getvalue())
        saved = write.call_args.args[1]["videos"]
        self.assertEqual(saved["기존"], legacy)
        self.assertEqual(saved["영상"]["duration_sec"], 754)


if __name__ == "__main__":
    unittest.main()
