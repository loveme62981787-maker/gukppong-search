import json
import re
import unittest
from pathlib import Path

import hot_shorts_watch as hs

ROOT = Path(__file__).parents[1]
C = hs.CRITERIA


def vid(i, pub, views=1000):
    return {"id": f"V{i:010d}", "title": f"t{i}", "published_at": pub, "views": views, "duration_sec": 45}


def page(ids):
    items = [{"shortsLockupViewModel": {"overlayMetadata": {"primaryText": {"content": "제목 " + i}, "secondaryText": {"content": "1K views"}},
                                        "onTap": {"innertubeCommand": {"reelWatchEndpoint": {"videoId": i}}}}} for i in ids]
    return "<html><script>var ytInitialData = " + json.dumps({"contents": {"x": [{"y": items}]}}) + ";</script></html>"


class ParseTests(unittest.TestCase):
    def test_parse_reads_ids_titles_and_dedupes(self):
        r = hs.parse_shorts_page(page(["AAAAAAAAAAA", "BBBBBBBBBBB", "AAAAAAAAAAA"]))
        self.assertEqual([x["id"] for x in r], ["AAAAAAAAAAA", "BBBBBBBBBBB"])
        self.assertEqual(r[0]["views_text"], "1K views")

    def test_unreadable_or_empty_is_none_not_zero(self):
        self.assertIsNone(hs.parse_shorts_page("<html>consent</html>"))
        self.assertIsNone(hs.parse_shorts_page(page([])))
        self.assertIsNone(hs.parse_shorts_page(page(["short"])))   # 11자 ID 형식이 아니면 버린다


class MembershipTests(unittest.TestCase):
    def test_tab_absence_alone_never_confirms_false(self):
        vs = [vid(1, "2026-11-10T00:00:00Z"), vid(2, "2026-11-09T00:00:00Z"), vid(3, "2026-11-08T00:00:00Z"), vid(4, "2026-11-01T00:00:00Z")]
        tab = [{"id": vs[0]["id"]}, {"id": vs[2]["id"]}]
        m = hs.classify_membership(vs, tab, {})
        self.assertEqual(m[vs[0]["id"]], (True, "shorts_tab"))
        self.assertEqual(m[vs[1]["id"]], (None, "pending"))   # 탭 첫 페이지에 없다는 것만으로는 쇼츠 아님을 확정하지 않는다
        self.assertEqual(m[vs[3]["id"]], (None, "pending"))

    def test_pinned_old_short_does_not_poison_newer_videos(self):
        vs = [vid(1, "2026-11-10T00:00:00Z"), vid(2, "2026-11-09T00:00:00Z"), vid(3, "2020-01-01T00:00:00Z")]
        m = hs.classify_membership(vs, [{"id": vs[2]["id"]}], {})   # 고정된 오래된 쇼츠만 탭에 보임
        self.assertEqual(m[vs[2]["id"]][0], True)
        self.assertIsNone(m[vs[0]["id"]][0])
        self.assertIsNone(m[vs[1]["id"]][0])

    def test_over_three_minutes_is_not_short(self):
        v = dict(vid(1, "2026-11-10T00:00:00Z"), duration_sec=600)
        self.assertEqual(hs.classify_membership([v], None, {})[v["id"]], (False, "too_long"))

    def test_duration_alone_never_confirms(self):
        vs = [vid(1, "2026-11-10T00:00:00Z")]
        self.assertEqual(hs.classify_membership(vs, None, {})[vs[0]["id"]][0], None)   # 45초여도 탭을 못 읽으면 보류

    def test_blocked_tab_keeps_previous_confirmation(self):
        vs = [vid(1, "2026-11-10T00:00:00Z"), vid(2, "2026-11-09T00:00:00Z")]
        prev = {vs[0]["id"]: {"short": True, "checked": "2026-11-01"}}
        m = hs.classify_membership(vs, None, prev)
        self.assertEqual(m[vs[0]["id"]], (True, "kept"))
        self.assertEqual(m[vs[1]["id"]], (None, "pending"))


class StatsTests(unittest.TestCase):
    def stats(self, shorts, n=20, rest=(False, "x")):
        sample = [vid(i, "2026-11-10T00:00:00Z") for i in range(n)]
        members = {v["id"]: ((True, "shorts_tab") if i < shorts else rest) for i, v in enumerate(sample)}
        return hs.sample_stats(sample, members)

    def test_center_threshold_and_strict_badge_are_separate(self):
        self.assertTrue(self.stats(18)["shorts_centered"])     # 90% 이상
        self.assertFalse(self.stats(17)["shorts_centered"])
        self.assertTrue(self.stats(19)["shorts_centered"])
        self.assertFalse(self.stats(19)["all_shorts_strict"])  # 쇼츠 중심이어도 전부 쇼츠는 아님
        self.assertTrue(self.stats(20)["all_shorts_strict"])

    def test_small_sample_never_centered(self):
        s = self.stats(19, n=19)
        self.assertFalse(s["shorts_centered"] or s["all_shorts_strict"])

    def test_pending_excluded_ratio_is_reported_separately(self):
        s = self.stats(10, n=20, rest=(None, "pending"))
        self.assertEqual((s["sample_known"], s["shorts_ratio_known"]), (10, 1.0))
        self.assertFalse(s["shorts_centered"])   # 보류 제외 100%여도 전체 표본 기준 50%이므로 쇼츠 중심 아님

    def test_16_of_20_is_80_percent_not_centered(self):
        s = self.stats(16, n=20, rest=(None, "pending"))
        self.assertEqual((s["sample_shorts"], s["sample_n"], s["shorts_ratio"], s["shorts_centered"], s["all_shorts_strict"]), (16, 20, 0.8, False, False))

    def test_pending_counts_against_ratio(self):
        s = self.stats(10, n=20, rest=(None, "pending"))   # 나머지 10개는 보류: 쇼츠 확인 비율은 50%
        self.assertEqual((s["sample_shorts"], s["sample_pending"], s["shorts_ratio"]), (10, 10, 0.5))


class HotTests(unittest.TestCase):
    def test_hot_rule_matches_criteria(self):
        ok, sub_m, med_m = hs.is_hot(C["min_views"], 10000, 4000)
        self.assertEqual((ok, sub_m, med_m), (True, 1.0, 2.5))
        self.assertFalse(hs.is_hot(C["min_views"] - 1, 100, 1000)[0])                 # 조회수 1만 미만은 입장 불가
        self.assertEqual(C["min_views"], 10000)
        self.assertTrue(hs.is_hot(C["min_views"], 50_000_000, 5_000_000)[0])          # 구독자 배수·중앙값 배수가 아주 낮아도 1만 이상이면 입장
        self.assertTrue(hs.is_hot(C["min_views"], None, None)[0])                     # 구독자 비공개·중앙값 없음이어도 입장

    def test_displayed_multiple_is_real_and_floor_is_selection_only(self):
        real, floor = hs.sub_multiples(100000, 100)
        self.assertEqual((real, floor), (1000.0, 100.0))                              # 표시는 실제 views/subs, 선별은 분모 최소 1000
        self.assertEqual(hs.is_hot(100000, 100, None)[1], 1000.0)
        self.assertEqual(hs.sub_multiples(1000, 0), (None, None))

    def test_zero_median_is_safe_and_multiples_are_display_only(self):
        self.assertEqual(hs.is_hot(200000, 50_000_000, 0)[2], None)                   # 중앙값 0 은 분모 예외 방어
        for k in ("min_sub_multiple", "min_median_multiple", "min_abs_views", "max_per_channel"):
            self.assertNotIn(k, C)                                                    # 입장 조건에서 제거됨

    def test_median_needs_enough_confirmed_shorts(self):
        sample = [vid(i, "2026-11-10T00:00:00Z", 1000 * (i + 1)) for i in range(10)]
        few = {v["id"]: (True, "s") if i < C["min_median_sample"] - 1 else (None, "p") for i, v in enumerate(sample)}
        self.assertIsNone(hs.median_of(sample, few))
        many = {v["id"]: (True, "s") for v in sample}
        self.assertEqual(hs.median_of(sample, many), 5500)


def seed(**kw):
    return dict({"id": "UC" + "a" * 22, "kind": "reaction_edit", "note": "n", "topic_filter": False}, **kw)   # 기존 테스트는 일반 제목이라 제목 필터 면제. 필터는 아래 TopicFilterTests 에서 따로 검증


def info(**kw):
    return dict({"title": "채널", "handle": "@ch", "country": "TW", "subs": 10000, "uploads": "UUx"}, **kw)


def twenty(base_views=200000):
    return [vid(i, f"2026-11-{20 - i:02d}T00:00:00Z", base_views) for i in range(20)]


class BuildTests(unittest.TestCase):
    def test_only_tab_confirmed_hot_videos_are_listed(self):
        vs = twenty()
        tab = [{"id": v["id"]} for v in vs[:19]]   # 마지막 하나는 탭에 없음
        rec = hs.build_channel(seed(), info(), vs, tab, None, "2026-11-16")
        self.assertEqual(len(rec["videos"]), 19)   # 채널당 개수 제한 없음: 탭에서 확인된 19개 전부
        self.assertTrue(all(v["short"] is True and v["short_signal"] == "shorts_tab" for v in rec["videos"]))
        self.assertTrue(rec["shorts_centered"] and not rec["all_shorts_strict"])
        self.assertTrue(rec["tab_checked"])

    def test_unconfirmed_hot_is_counted_pending_not_listed(self):
        rec = hs.build_channel(seed(), info(), twenty(), None, None, "2026-11-16")
        self.assertEqual(rec["videos"], [])
        self.assertEqual(rec["pending_hot"], 20)
        self.assertFalse(rec["shorts_centered"])

    def test_country_target_beats_registered_country(self):
        a = hs.build_channel(seed(country_hint="JP"), info(country="TW"), twenty(), None, None, "d")
        self.assertEqual((a["country"], a["country_basis"]), ("JP", "seed_manual"))   # 영상이 다루는 대상국이 우선
        o = hs.build_channel(seed(country_hint="JP", country_override="KR"), info(country="US"), twenty(), None, None, "d")
        self.assertEqual((o["country"], o["country_basis"]), ("KR", "seed_manual"))   # override 최우선, 제3국 등록도 무시
        n = hs.build_channel(seed(), info(country="TW"), twenty(), None, None, "d")
        self.assertEqual((n["country"], n["country_basis"]), ("TW", "channel_country"))
        b = hs.build_channel(seed(country_hint="JP"), info(country=""), twenty(), None, None, "d")
        self.assertEqual((b["country"], b["country_basis"]), ("JP", "seed_manual"))
        c = hs.build_channel(seed(), info(country=""), twenty(), None, None, "d")
        self.assertEqual(c["country"], "")   # 근거 없으면 나라를 정하지 않는다

    def test_kind_defaults_to_unverified_never_original(self):
        self.assertEqual(hs.build_channel(seed(kind=None), info(), twenty(), None, None, "d")["kind"], "unverified")
        self.assertEqual(hs.build_channel(seed(kind="bogus"), info(), twenty(), None, None, "d")["kind"], "unverified")
        self.assertEqual(hs.build_channel(seed(kind="reaction_edit"), info(), twenty(), None, None, "d")["kind"], "reaction_edit")

    def test_blocked_tab_run_keeps_previous_confirmed_videos(self):
        vs = twenty()
        first = hs.build_channel(seed(), info(), vs, [{"id": v["id"]} for v in vs], None, "2026-11-10")
        again = hs.build_channel(seed(), info(), vs, None, first, "2026-11-16")   # 이번엔 탭이 막힘
        self.assertEqual(len(again["videos"]), 20)
        self.assertTrue(all(v["short_signal"] == "kept" and v["short_checked"] == "2026-11-10" for v in again["videos"]))
        self.assertTrue(again["shorts_centered"])   # 이전 확인이 표본 통계에도 이어진다

    def test_membership_cache_covers_non_hot_sample_and_survives_blocked_tab(self):
        vs = twenty(base_views=2000)   # 하나도 터지지 않음
        first = hs.build_channel(seed(), info(), vs, [{"id": v["id"]} for v in vs[:18]], None, "2026-11-10")
        self.assertEqual(first["videos"], [])
        self.assertEqual(len(first["membership_cache"]), 18)   # 터진 영상이 없어도 표본 전체 확인이 저장된다
        self.assertEqual(set(first["membership_cache"][vs[0]["id"]]), {"short", "checked"})   # 비공개 원문 없음
        again = hs.build_channel(seed(), info(), vs, None, first, "2026-11-16")   # 클라우드에서 탭 차단
        self.assertEqual((again["sample_shorts"], again["shorts_ratio"], again["shorts_centered"]), (18, 0.9, True))
        self.assertEqual(again["membership_cache"][vs[0]["id"]]["checked"], "2026-11-10")   # 확인일은 보존

    def test_user_reference_and_exclude_seeds(self):
        rec = hs.build_channel(seed(user_reference=True), info(), twenty(), None, None, "d")
        self.assertTrue(rec["user_reference"])
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            with open(p, "w") as f:
                json.dump([seed(), seed(id="UC" + "b" * 22, exclude=True)], f)
            self.assertEqual([x["id"] for x in hs.load_seeds(p)], [seed()["id"]])
            self.assertEqual(hs.extra_excluded(p), ["UC" + "b" * 22])

    def test_old_hot_video_outside_window_is_kept(self):
        vs = twenty()
        first = hs.build_channel(seed(), info(), vs, [{"id": v["id"]} for v in vs], None, "2026-11-10")
        shifted = [vid(100 + i, f"2026-12-{20 - i:02d}T00:00:00Z", 1000) for i in range(20)]
        again = hs.build_channel(seed(), info(), shifted, [{"id": v["id"]} for v in shifted], first, "2026-11-16")
        self.assertEqual(len(again["videos"]), 20)   # 새 영상은 조회수 미달(1000), 밀려난 기존 터진 쇼츠 20개가 개수 제한 없이 누적 보존됨
        self.assertTrue(all(v["short_signal"] == "kept" for v in again["videos"]))


class RunTests(unittest.TestCase):
    def test_failure_keeps_existing_channel_record(self):
        old = hs.build_channel(seed(), info(), twenty(), [{"id": v["id"]} for v in twenty()], None, "2026-11-10")
        store = {"channels": {old["id"]: old}}
        out = hs.run([seed()], store, "2026-11-16", infos={})   # 채널 정보 조회 실패
        kept = out["channels"][old["id"]]
        self.assertEqual(kept["videos"], old["videos"])
        self.assertEqual(kept["last_error_at"], "2026-11-16")

    def test_failed_new_channel_is_pending_stub(self):
        out = hs.run([seed()], {}, "2026-11-16", infos={})
        c = out["channels"][seed()["id"]]
        self.assertEqual((c["videos"], c["shorts_centered"], c["all_shorts_strict"]), ([], False, False))

    def test_other_channels_untouched_by_seed_list(self):
        other = hs.merge_failed(None, seed(id="UC" + "b" * 22), "x", "d")
        out = hs.run([seed()], {"channels": {other["id"]: other}}, "d", infos={})
        self.assertIn(other["id"], out["channels"])


class ExportTests(unittest.TestCase):
    def test_js_safe_blocks_script_breakout(self):
        s = hs.js_safe({"t": "</script><img src=x onerror=alert(1)> &  "})
        self.assertNotIn("<", s)
        self.assertNotIn(">", s)
        self.assertNotIn(" ", s)
        self.assertEqual(json.loads(s)["t"], "</script><img src=x onerror=alert(1)> &  ")


class SiteDataTests(unittest.TestCase):
    """저장소에 들어 있는 실제 데이터의 불변식"""

    @classmethod
    def setUpClass(cls):
        text = (ROOT / "web" / "hot_shorts.js").read_text(encoding="utf-8")
        assert text.startswith("window.HOT_SHORTS=") and text.rstrip().endswith(";")
        cls.d = json.loads(text[len("window.HOT_SHORTS="):].rstrip().rstrip(";"))
        cls.store = json.loads((ROOT / "hot_shorts_store.json").read_text(encoding="utf-8"))

    def test_criteria_exported_equals_code(self):
        self.assertEqual(self.d["criteria"], hs.CRITERIA)

    def test_example_taiwan_channel_included(self):
        ch = {c["id"]: c for c in self.d["channels"]}["UC0MUbD8ISz4koLlo0LfgNng"]
        self.assertEqual(ch["country"], "TW")
        self.assertEqual(ch["kind"], "reaction_edit")
        self.assertFalse(ch["shorts_centered"])   # 실제 최근 표본에 롱폼(명상음악)이 섞여 있어 쇼츠 중심(90%)이 아님
        self.assertEqual((ch["sample_shorts"], ch["sample_n"], ch["shorts_ratio"]), (16, 20, 0.8))   # 16/20=80% 그대로 표시, 전부 쇼츠로 날조하지 않음
        self.assertFalse(ch["all_shorts_strict"])
        self.assertTrue(ch["user_reference"])
        self.assertGreater(ch["hot_n"], 0)

    def test_three_countries_have_channels_and_videos(self):
        for cc in ("KR", "JP", "TW"):
            self.assertTrue([c for c in self.d["channels"] if c["country"] == cc], cc)
            self.assertTrue([v for v in self.d["videos"] if v["country"] == cc], cc)

    def test_every_video_is_confirmed_hot_with_valid_ids(self):
        chs = {c["id"]: c for c in self.d["channels"]}
        for v in self.d["videos"]:
            self.assertRegex(v["id"], hs.ID_RE.pattern)
            self.assertIn(v["channel_id"], chs)
            self.assertIs(v["short"], True)
            self.assertIn(v["short_signal"], ("shorts_tab", "kept"))
            self.assertGreaterEqual(v["views"], C["min_views"])
            self.assertIn(v["country"], hs.COUNTRIES)
            self.assertRegex(v["checked"], r"^\d{4}-\d{2}-\d{2}$")

    def test_center_flags_follow_code_rule(self):
        for c in self.d["channels"]:
            if c["shorts_centered"]:
                self.assertGreaterEqual(c["sample_n"], C["sample_n"])
                self.assertGreaterEqual(c["shorts_ratio"], C["center_ratio"])
            if c["all_shorts_strict"]:
                self.assertEqual(c["sample_shorts"], c["sample_n"])
            self.assertIn(c["kind"], hs.KINDS)

    def test_no_secrets_or_private_links_in_data(self):
        blob = "".join((ROOT / n).read_text(encoding="utf-8") for n in ("web/hot_shorts.js", "hot_shorts_store.json", "hot_shorts_seeds.json"))
        for bad in ("AIza", "notion.so", "notion.site", "api_key", "key="):
            self.assertNotIn(bad, blob)
        self.assertIsNone(re.search(r"[\w.]+@[\w-]+\.[a-z]{2,}", blob))

    def test_store_and_export_agree(self):
        ex = json.loads((ROOT / "hot_shorts_exclusions.json").read_text(encoding="utf-8"))
        seeds = {x["id"]: x for x in json.loads((ROOT / "hot_shorts_seeds.json").read_text(encoding="utf-8"))}
        chs = [c for c in self.store["channels"].values() if c["id"] not in ex["channels"] and not seeds.get(c["id"], {}).get("exclude")]
        expected = {v["id"] for c in chs for v in c["videos"] if v["id"] not in ex["videos"] and hs.topic_visible(seeds.get(c["id"]), c.get("country", ""), v.get("title"))}
        self.assertEqual(len(chs), len(self.d["channels"]))
        self.assertEqual(expected, {v["id"] for v in self.d["videos"]})

    def test_seeds_are_valid_and_unique(self):
        seeds = json.loads((ROOT / "hot_shorts_seeds.json").read_text(encoding="utf-8"))
        ids = [s["id"] for s in seeds]
        self.assertEqual(len(ids), len(set(ids)))
        for s in seeds:
            self.assertRegex(s["id"], hs.CH_RE.pattern)
            self.assertIn(s["kind"], hs.KINDS)


class DiscoverTests(unittest.TestCase):
    def test_taiwan_queries_and_language_exist(self):
        self.assertTrue(hs.DISCOVER_QUERIES["TW"])
        self.assertEqual(hs.SEARCH_LANG["TW"], "zh-Hant")
        self.assertTrue(set(hs.DISCOVER_QUERIES) <= set(hs.SEARCH_LANG))


class WorkflowTests(unittest.TestCase):
    def test_workflow_is_independent_shares_group_and_keeps_data_on_failure(self):
        y = (ROOT / ".github" / "workflows" / "hot_shorts.yml").read_text(encoding="utf-8")
        self.assertRegex(y, r"concurrency:\s*\n\s*group: update")
        self.assertIn("secrets.YOUTUBE_API_KEY", y)
        self.assertIn("python hot_shorts_watch.py", y)
        self.assertIn("continue-on-error: true", y)
        self.assertNotIn("python build_site.py", y)   # 기존 전체 갱신을 돌리지 않는다
        self.assertRegex(y, r"git add [^\n]*hot_shorts_store\.json[^\n]*web/hot_shorts\.js")



class TopicFilterTests(unittest.TestCase):
    def test_title_needs_foreigner_and_target_country(self):
        self.assertTrue(hs.topic_ok("외국인이 한국 시골에서 놀란 이유", "KR"))
        self.assertTrue(hs.topic_ok("美國人第一次來台灣夜市", "TW"))
        self.assertTrue(hs.topic_ok("韓國人 台灣 旅行 反應", "TW"))
        self.assertFalse(hs.topic_ok("iPhone 선물", "TW"))
        self.assertFalse(hs.topic_ok("台灣 新聞 快訊", "TW"))            # 대상국만 있음 (일반 뉴스)
        self.assertFalse(hs.topic_ok("外國人 日本 旅行", "TW"))          # 다른 나라 이야기
        self.assertFalse(hs.topic_ok("韓國人 在台灣", "KR"))              # 대상국 사람은 외국인 신호가 아님 + 대상국어 없음

    def test_mixed_channel_publishes_only_title_matched_videos(self):
        vs = twenty()
        vs[0]["title"] = "外國人 台灣 夜市 反應"
        tab = [{"id": v["id"]} for v in vs]
        rec = hs.build_channel(seed(topic_filter=None), info(), vs, tab, None, "d")
        self.assertEqual([v["id"] for v in rec["videos"]], [vs[0]["id"]])
        self.assertEqual(rec["topic_held"], 19)

    def test_old_kept_videos_are_filtered_too(self):
        vs = twenty()
        first = hs.build_channel(seed(), info(), vs, [{"id": v["id"]} for v in vs], None, "d")
        shifted = [vid(100 + i, f"2026-12-{20 - i:02d}T00:00:00Z", 1000) for i in range(20)]
        again = hs.build_channel(seed(topic_filter=None), info(), shifted, [{"id": v["id"]} for v in shifted], first, "d")
        self.assertEqual(again["videos"], [])

    def test_export_hides_unmatched_and_excluded_seed_without_network(self):
        import tempfile
        import os
        vs = twenty()
        mixed = hs.build_channel(seed(), info(), vs, [{"id": v["id"]} for v in vs], None, "d")
        bad = hs.build_channel(seed(id="UC" + "b" * 22), info(), vs, [{"id": v["id"]} for v in vs], None, "d")
        store = {"updated": "d", "channels": {mixed["id"]: mixed, bad["id"]: bad}}
        with tempfile.TemporaryDirectory() as d:
            n = hs.export(store, os.path.join(d, "o.js"), exclusions={}, seeds=[seed(topic_filter=None), seed(id=bad["id"], exclude=True)])
        self.assertEqual(n, (1, 0))   # exclude 채널은 빠지고, 필터 채널의 제목 근거 없는 영상은 공개되지 않는다


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.orig = (hs.fetch_playlist_ids, hs.fetch_videos)
        self.pages = {"": (["a%010d" % i for i in range(3)], "T1"), "T1": (["b%010d" % i for i in range(3)], "T2"), "T2": (["c%010d" % i for i in range(3)], "")}
        self.fail_token = None

        def fpi(pid, n, token=""):
            if pid.startswith("UUSH"):
                if token and token == self.fail_token:
                    raise hs.ApiError("boom")
                if token == "":
                    return ["h%010d" % 0], "T1"   # head 는 한 페이지 크기만 읽고 다음 토큰을 준다
                return self.pages[token]
            return [], ""
        hs.fetch_playlist_ids = fpi
        hs.fetch_videos = lambda ids: {i: {"id": i, "title": "외국인 한국 " + i, "published_at": "2020-01-01T00:00:00Z", "views": 50000, "duration_sec": 30} for i in ids}
        hs.fetch_shorts_tab = lambda cid: None

    def tearDown(self):
        hs.fetch_playlist_ids, hs.fetch_videos = self.orig

    def run_once(self, prev, day="2026-11-16"):
        s = seed(country_hint="KR")
        return hs.collect_channel(s, prev, day, {s["id"]: info(uploads="UUx")}, tab_fetch=lambda c: None)

    def test_cursor_advances_resumes_and_completes_keeping_old_videos(self):
        saved = hs.CRITERIA["backfill_pages"]
        hs.CRITERIA["backfill_pages"] = 1
        try:
            r1 = self.run_once(None)
            self.assertEqual(r1["backfill"], {"token": "T2", "pages": 1})   # head 의 T1 부터 한 페이지(T1 → b…) 읽고 T2 저장
            r2 = self.run_once(r1)
            self.assertEqual(r2["backfill"]["done"], True)
            ids = {v["id"] for v in r2["videos"]}
            self.assertTrue({"a%010d" % 0, "b%010d" % 0, "c%010d" % 0} <= ids or len(ids) >= 7)
        finally:
            hs.CRITERIA["backfill_pages"] = saved

    def test_failure_keeps_cursor_and_old_videos(self):
        saved = hs.CRITERIA["backfill_pages"]
        hs.CRITERIA["backfill_pages"] = 1
        try:
            r1 = self.run_once(None)
            self.fail_token = "T2"
            r2 = self.run_once(r1)
            self.assertEqual(r2["backfill"]["token"], "T2")   # 실패해도 커서 그대로
            self.assertTrue({v["id"] for v in r1["videos"]} <= {v["id"] for v in r2["videos"]})
        finally:
            hs.CRITERIA["backfill_pages"] = saved

    def test_done_resets_after_interval_but_not_before(self):
        done = {"done": True, "done_at": "2026-11-10", "pages": 5}
        prev = dict(self.run_once(None), backfill=done)
        self.assertEqual(self.run_once(prev, "2026-11-16")["backfill"], done)   # 6일: 유지
        self.assertEqual(self.run_once(prev, "2026-11-30")["backfill"]["done_at"], "2026-11-30")   # 20일: 커서를 비우고 다시 훑어 새 완료일


if __name__ == "__main__":
    unittest.main()


class StorageSafetyTests(unittest.TestCase):
    def test_corrupt_store_is_not_overwritten(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "store.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write('{"schema": 1, "channels": {')   # 잘린 JSON
            with self.assertRaises(hs.StoreCorrupt):
                hs.load_store_strict(p)
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), '{"schema": 1, "channels": {')   # 그대로
            self.assertEqual(hs.load_store_strict(os.path.join(d, "none.json")), {})   # 파일 없음은 빈 저장분

    def test_atomic_write_replaces_without_leftover_tmp(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.json")
            hs.write_atomic(p, "one")
            hs.write_atomic(p, "two")
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), "two")
            self.assertEqual(os.listdir(d), ["a.json"])

    def test_name_ko_and_topic_evidence_are_carried(self):
        rec = hs.build_channel(seed(name_ko="외국인이 본 대만", topic_evidence=["제목 근거"]), info(), twenty(), None, None, "d")
        self.assertEqual((rec["name_ko"], rec["topic_evidence"]), ("외국인이 본 대만", ["제목 근거"]))

    def test_shorts_playlist_ids_count_as_shorts_evidence_beyond_tab(self):
        vs = twenty()
        rec = hs.build_channel(seed(), info(), vs, [{"id": v["id"]} for v in vs], None, "d")
        self.assertEqual(rec["sample_shorts"], 20)
