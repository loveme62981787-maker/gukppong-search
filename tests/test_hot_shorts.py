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
        ok, sub_m, med_m = hs.is_hot(C["min_views"], 10000, 40000)
        self.assertEqual((ok, sub_m, med_m), (True, 10.0, 2.5))
        self.assertFalse(hs.is_hot(C["min_views"] - 1, 100, 1000)[0])                 # 조회수 최소 미달
        self.assertFalse(hs.is_hot(150000, 1000000, 100000)[0])                       # 배수 둘 다 미달
        self.assertTrue(hs.is_hot(150000, 1000000, 70000)[0])                         # 중앙값 대비만 충족(2.14배)
        self.assertTrue(hs.is_hot(300000, 100000, None)[0])                           # 중앙값 없음 + 구독자 3배
        self.assertEqual(hs.is_hot(150000, None, None)[0], False)                     # 구독자 비공개 + 중앙값 없음 → 근거 부족

    def test_displayed_multiple_is_real_and_floor_is_selection_only(self):
        real, floor = hs.sub_multiples(100000, 100)
        self.assertEqual((real, floor), (1000.0, 100.0))                              # 표시는 실제 views/subs, 선별은 분모 최소 1000
        self.assertEqual(hs.is_hot(100000, 100, None)[1], 1000.0)
        self.assertEqual(hs.sub_multiples(1000, 0), (None, None))

    def test_absolute_views_pass_for_big_channels_and_zero_median_is_safe(self):
        self.assertTrue(hs.is_hot(C["min_abs_views"], 50_000_000, 5_000_000)[0])      # 대형 채널·전부 대박 채널도 100만 이상이면 통과
        self.assertFalse(hs.is_hot(C["min_abs_views"] - 1, 50_000_000, 5_000_000)[0])
        self.assertEqual(hs.is_hot(200000, 50_000_000, 0)[2], None)                   # 중앙값 0 은 분모 예외 방어

    def test_median_needs_enough_confirmed_shorts(self):
        sample = [vid(i, "2026-11-10T00:00:00Z", 1000 * (i + 1)) for i in range(10)]
        few = {v["id"]: (True, "s") if i < C["min_median_sample"] - 1 else (None, "p") for i, v in enumerate(sample)}
        self.assertIsNone(hs.median_of(sample, few))
        many = {v["id"]: (True, "s") for v in sample}
        self.assertEqual(hs.median_of(sample, many), 5500)


def seed(**kw):
    return dict({"id": "UC" + "a" * 22, "kind": "reaction_edit", "note": "n"}, **kw)


def info(**kw):
    return dict({"title": "채널", "handle": "@ch", "country": "TW", "subs": 10000, "uploads": "UUx"}, **kw)


def twenty(base_views=200000):
    return [vid(i, f"2026-11-{20 - i:02d}T00:00:00Z", base_views) for i in range(20)]


class BuildTests(unittest.TestCase):
    def test_only_tab_confirmed_hot_videos_are_listed(self):
        vs = twenty()
        tab = [{"id": v["id"]} for v in vs[:19]]   # 마지막 하나는 탭에 없음
        rec = hs.build_channel(seed(), info(), vs, tab, None, "2026-11-16")
        self.assertEqual(len(rec["videos"]), C["max_per_channel"])   # 19개가 터졌어도 채널당 상한
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
        self.assertEqual(len(again["videos"]), C["max_per_channel"])
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
        self.assertEqual(len(again["videos"]), C["max_per_channel"])   # 새 영상은 조회수 미달, 밀려난 기존 터진 쇼츠가 보존됨
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
            self.assertTrue((v["sub_multiple"] or 0) >= C["min_sub_multiple"] or (v["median_multiple"] or 0) >= C["min_median_multiple"] or v["views"] >= C["min_abs_views"])
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
        chs = [c for c in self.store["channels"].values() if c["id"] not in ex["channels"]]
        expected = {v["id"] for c in chs for v in c["videos"] if v["id"] not in ex["videos"]}
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


if __name__ == "__main__":
    unittest.main()
