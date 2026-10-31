import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import license_watch as lw

A, B, C = "aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"
NOW = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)


def row(title, text, url=None):
    run = {"text": text}
    if url:
        run["navigationEndpoint"] = {"urlEndpoint": {"url": url}}
    return {"metadataRowRenderer": {"title": {"simpleText": title}, "contents": [{"runs": [run]}]}}


def page(vid, rows=(), desc="", status="OK", ep=None, related_rows=()):
    pr = {"playabilityStatus": {"status": status}, "videoDetails": {"videoId": vid}, "microformat": {"playerMicroformatRenderer": {"description": {"simpleText": desc}}}}
    data = {"currentVideoEndpoint": {"watchEndpoint": {"videoId": ep or vid}},
            "contents": {"twoColumnWatchNextResults": {"results": {"results": {"contents": [{"videoSecondaryInfoRenderer": {"metadataRowContainer": {"metadataRowContainerRenderer": {"rows": list(rows)}}}}]}},
                         "secondaryResults": {"items": list(related_rows)}}}}
    return f"<script>var ytInitialPlayerResponse = {json.dumps(pr)};var x=1;</script><script>var ytInitialData = {json.dumps(data)};</script>"


CC = row("License", "Creative Commons Attribution license (reuse allowed)", "https://www.youtube.com/t/creative_commons")
STD = row("License", "Standard YouTube License")


class ParseTest(unittest.TestCase):
    def test_structured_cc_standard_unknown(self):
        self.assertEqual(lw.parse_watch(page(A, [CC]), A)[1]["license"], "cc_by")
        self.assertEqual(lw.parse_watch(page(A, [STD]), A)[1]["license"], "standard")
        self.assertIsNone(lw.parse_watch(page(A, []), A)[1]["license"])   # 표기 없음 = 표준이 아니라 '표기 없음'
        self.assertEqual(lw.parse_watch(page(A, [row("License", "Something else")]), A)[1]["license"], "unrecognized")

    def test_only_exact_cc_by_evidence(self):
        def lic(text, url=None):
            return lw.parse_watch(page(A, [row("License", text, url)]), A)[1]["license"]
        self.assertEqual(lic("Creative Commons Attribution license (reuse allowed)"), "cc_by")
        self.assertEqual(lic("reuse allowed", "https://www.youtube.com/t/creative_commons"), "cc_by")
        self.assertEqual(lic("see license", "https://creativecommons.org/licenses/by/4.0/"), "cc_by")
        for text, url in [("see license", "https://creativecommons.org/"), ("see license", "https://creativecommons.org/about"), ("see license", "https://creativecommons.org/licenses/by-nc/4.0/"),
                          ("see license", "https://creativecommons.org/licenses/by-sa/4.0/"), ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
                          ("Creative Commons Attribution-NonCommercial", None), ("Creative Commons Attribution-ShareAlike", None), ("x", "https://example.com/t/creative_commons"),
                          ("x", "https://creativecommons.org/licenses/by/4.0/evil")]:
            self.assertEqual(lic(text, url), "unrecognized", (text, url))

    def test_no_inference_from_text_or_other_rows_or_related(self):
        # 설명에 CC 문구가 있어도, 라이선스가 아닌 행(음악 라이선스 등)이어도, 추천 영상 영역이어도 CC BY 가 아니다
        self.assertIsNone(lw.parse_watch(page(A, [], desc="Creative Commons Attribution license (reuse allowed)"), A)[1]["license"])
        self.assertIsNone(lw.parse_watch(page(A, [row("Licensed to YouTube by", "Creative Commons Attribution")]), A)[1]["license"])
        self.assertIsNone(lw.parse_watch(page(A, [], related_rows=[CC]), A)[1]["license"])

    def test_identity_and_errors(self):
        self.assertEqual(lw.parse_watch(page(B, [CC]), A), ("err", "identity_mismatch"))
        self.assertEqual(lw.parse_watch(page(A, [CC], ep=B), A), ("err", "identity_mismatch"))
        self.assertEqual(lw.parse_watch("<html>consent</html>", A), ("err", "blocked"))
        self.assertEqual(lw.parse_watch(page(A, [CC], status="UNPLAYABLE"), A), ("err", "unavailable"))


class FreeUseTest(unittest.TestCase):
    def test_explicit_video_permission(self):
        for d in ["This video is free to use. Please credit the channel.", "Feel free to reupload this video.", "You can reuse my footage in your own videos.",
                  "Feel free to use my clips in your own videos!", "이 영상은 누구나 자유롭게 사용해도 됩니다", "この動画は自由に使用してOKです"]:
            self.assertTrue(lw.free_use_rule(d), d)

    def test_music_stock_and_unrelated_are_not_permission(self):
        for d in ["Music: Kevin MacLeod - free to use", "Background music is royalty free", "Stock footage from Pexels is free to use", "배경음악은 누구나 자유롭게 사용 가능합니다",
                  "Feel free to use the timestamps below", "You can use this video to plan your trip", "Free to use thumbnails: Canva", "効果音は自由に使用OK", "Subscribe! Business: a@b.com"]:
            self.assertIsNone(lw.free_use_rule(d), d)

    def test_ambiguous_or_conditional_phrases_are_not_permission(self):
        for d in ["Feel free to download this video", "You can share this video with friends", "Feel free to download and share my videos", "This video is royalty free",
                  "This video is free to use if you purchase the pack", "Feel free to reupload this video when you subscribe to my channel", "Reuse this video with a paid membership",
                  "この動画はダウンロードできます", "영상은 누구나 자유롭게 사용 가능합니다 (유료 멤버십 시)"]:
            self.assertIsNone(lw.free_use_rule(d), d)

    def test_negation_and_disclaimers(self):
        for d in ["This video is not free to use.", "Do not reupload this video without permission. Feel free to reupload this video", "All rights reserved. This video is free to use",
                  "이 영상은 무단 사용 금지입니다", "Feel free to download my footage. Permission is required for commercial use."]:
            self.assertIsNone(lw.free_use_rule(d), d)

    def test_no_raw_text_in_result(self):
        rec = lw.observe(None, lw.parse_watch(page(A, [CC], desc="This video is free to use. contact: me@x.com https://x.com/secret"), A), NOW)
        self.assertNotIn("secret", json.dumps(rec)); self.assertNotIn("me@x.com", json.dumps(rec)); self.assertEqual(rec["free_rule"], "en_video")


class StateTest(unittest.TestCase):
    def ok(self, lic, free=None):
        return "ok", {"license": lic, "free_rule": free, "has_desc": True}

    def test_failure_retains_verified_evidence_and_flags_stale(self):
        r1 = lw.observe(None, self.ok("cc_by", "en_video"), NOW)
        r2 = lw.observe(r1, ("err", "blocked"), NOW + timedelta(days=15))
        self.assertEqual((r2["license"], r2["free_use"], r2["checked_at"], r2["error"], r2["fail_count"]), ("cc_by", 1, "2026-10-31", "blocked", 1))
        e = lw.export_item(r2)
        self.assertEqual((e["l"], e["f"], e["s"], e["e"], e["c"]), ("cc_by", "en_video", 1, "blocked", "2026-10-31"))

    def test_failure_never_promotes_unknown(self):
        r = lw.observe(None, ("err", "network"), NOW)
        self.assertEqual((r["license"], r["unknown_reason"]), ("unknown", "never_verified"))
        e = lw.export_item(r)
        self.assertEqual(e["l"], "unknown"); self.assertNotIn("c", e); self.assertNotIn("s", e)

    def test_retained_evidence_keeps_its_own_date(self):
        d1, d2 = NOW, NOW + timedelta(days=3)
        r = lw.observe(None, self.ok("cc_by", "en_video"), d1)
        r2 = lw.observe(r, self.ok(None, "en_video"), d2)   # CC 표기만 안 보임: 지난 증거 유지
        self.assertEqual((r2["license"], r2["checked_at"], r2["error"], r2["attempted_at"][:10]), ("cc_by", "2026-10-31", "marker_missing", "2026-11-03"))
        self.assertEqual(lw.export_item(r2)["c"], "2026-10-31")
        r3 = lw.observe(r, ("ok", {"license": "cc_by", "free_rule": None, "has_desc": False}), d2)   # 설명 못 읽음: 무료 사용 증거 날짜 유지
        self.assertEqual((r3["free_use"], r3["free_checked_at"], r3["error"], r3["checked_at"]), (1, "2026-10-31", "description_missing", "2026-11-03"))
        self.assertEqual(lw.export_item(r3)["fc"], "2026-10-31")
        r4 = lw.observe(r, self.ok("cc_by", "en_video"), d2)   # 정상 재확인은 날짜가 갱신된다
        self.assertEqual((r4["checked_at"], r4["free_checked_at"], r4["error"]), ("2026-11-03", "2026-11-03", None))

    def test_pick_targets_half_newest_half_oldest(self):
        inv = {f"{n:011d}": f"2026-10-{n:02d}" for n in range(1, 21)}
        pick, nf, nd = lw.pick_targets(inv, {}, 10, NOW)
        ids = [int(i) for i in pick]
        self.assertEqual((sorted(ids[:5]), sorted(ids[5:])), ([16, 17, 18, 19, 20], [1, 2, 3, 4, 5]))
        pick, _, _ = lw.pick_targets(inv, {}, 25, NOW)
        self.assertEqual(len(set(pick)), 20)   # 중복 없이 전체

    def test_missing_marker_needs_two_misses_and_is_not_standard(self):
        r = lw.observe(None, self.ok("cc_by"), NOW)
        r = lw.observe(r, self.ok(None), NOW); self.assertEqual((r["license"], r["error"]), ("cc_by", "marker_missing"))
        r = lw.observe(r, self.ok(None), NOW); self.assertEqual((r["license"], r["unknown_reason"]), ("unknown", "no_marker"))
        self.assertEqual(lw.observe(None, self.ok(None), NOW)["unknown_reason"], "no_marker")

    def test_description_edit_updates_free_use_and_missing_desc_keeps_it(self):
        r = lw.observe(None, self.ok("standard", "ko_video"), NOW)
        r = lw.observe(r, ("ok", {"license": "standard", "free_rule": None, "has_desc": False}), NOW)
        self.assertEqual(r["free_use"], 1)
        r = lw.observe(r, self.ok("standard", None), NOW)
        self.assertEqual(r["free_use"], 0); self.assertNotIn("free_rule", r)

    def test_export_item_whitelists_fields(self):
        e = lw.export_item({"license": "cc_by", "free_use": 1, "free_rule": "RAW DESCRIPTION", "checked_at": "not a date", "error": "<script>", "description": "x"})
        self.assertEqual(e, {"l": "cc_by"})


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        d = self.tmp.name
        self.web = os.path.join(d, "web"); os.makedirs(self.web)
        self.store = os.path.join(d, "data", "video_licenses.json"); self.out = os.path.join(self.web, "video_licenses.js")
        def w(name, var, items):
            with open(os.path.join(self.web, name), "w", encoding="utf-8") as f:
                f.write(f"window.{var}=" + json.dumps(items) + ";\n")
        w("videos.js", "VIDEOS", [{"id": A, "first_seen": "2026-10-01"}, {"id": B, "first_seen": "2026-10-30"}])
        w("viral.js", "VIRAL", [{"id": A}, {"id": C}, {"id": "bad"}])   # A 는 중복, 'bad' 는 ID 형식이 아님
        self.pages = {A: page(A, [CC], desc="This video is free to use"), B: page(B, [STD]), C: page(C, [])}
        self.calls = []

    def fetch(self, url):
        vid = url.split("v=")[1]; self.calls.append(vid)
        p = self.pages[vid]
        if isinstance(p, Exception):
            raise p
        return p

    def go(self, limit=10, **kw):
        return lw.run(limit, 2, 60, fetch=self.fetch, sleep=lambda s: None, now_fn=lambda: NOW, web_dir=self.web, store_path=self.store, out_path=self.out, **kw)

    def exported(self):
        return json.loads(open(self.out, encoding="utf-8").read().split("=", 1)[1].rstrip(";\n"))

    def test_dedup_all_sources_and_export(self):
        self.assertEqual(set(lw.load_inventory(self.web)), {A, B, C})
        scope = self.go()
        self.assertEqual(sorted(self.calls), sorted([A, B, C]))   # 중복 없이 한 번씩
        items = self.exported()["items"]
        self.assertEqual((items[A]["l"], items[A]["f"]), ("cc_by", "en_video"))
        self.assertEqual(items[B]["l"], "standard")
        self.assertEqual((items[C]["l"], items[C]["u"]), ("unknown", "no_marker"))
        self.assertEqual((scope["cc_by"], scope["standard"], scope["free_use"], scope["checked"]), (1, 1, 1, 3))

    def test_limit_new_first_then_oldest_attempt(self):
        self.go(limit=1)
        self.assertEqual(self.calls, [B])   # first_seen 이 가장 최근인 새 영상부터
        self.go(limit=5)
        self.assertEqual(sorted(self.calls), sorted([B, A, C]))   # 이미 확인한 B 는 아직 재확인 주기 전이라 다시 안 읽는다

    def test_failures_keep_data_and_circuit_breaker(self):
        self.go()
        later = NOW + timedelta(days=40)
        self.pages = {k: OSError("boom") for k in (A, B, C)}
        lw.run(10, 1, 60, fetch=self.fetch, sleep=lambda s: None, now_fn=lambda: later, web_dir=self.web, store_path=self.store, out_path=self.out)
        items = self.exported()["items"]
        self.assertEqual((items[A]["l"], items[A]["s"], items[A]["e"]), ("cc_by", 1, "network"))   # 이전 확인값 유지 + 오래된 값 표시
        self.assertEqual(items[B]["l"], "standard")

    def test_circuit_breaker_stops_run(self):
        ids = [f"{i:011d}" for i in range(30)]
        with open(os.path.join(self.web, "viral.js"), "w", encoding="utf-8") as f:
            f.write("window.VIRAL=" + json.dumps([{"id": i} for i in ids]) + ";")
        self.pages = {i: OSError("blocked") for i in ids + [A, B, C]}
        self.go(limit=100)
        self.assertLess(len(self.calls), 30 * 3 + 3)   # 재시도 포함해도 전부 돌지 않고 중간에 멈춘다

    def test_corrupt_store_is_not_overwritten(self):
        os.makedirs(os.path.dirname(self.store)); open(self.store, "w").write("{broken")
        with self.assertRaises(ValueError):
            self.go()
        self.assertEqual(open(self.store).read(), "{broken")

    def test_export_only_and_missing_inventory_does_not_prune(self):
        self.go()
        os.remove(os.path.join(self.web, "videos.js")); os.remove(os.path.join(self.web, "viral.js"))   # 입력을 못 읽어도 기록을 잘라내지 않는다
        lw.export_js(lw.load_store(self.store), set(lw.load_inventory(self.web)), self.out)
        self.assertEqual(set(self.exported()["items"]), {A, B, C})

    def test_retry_and_http_status(self):
        n = []
        class E(Exception):
            code = 404
        def f(url):
            n.append(1); raise E()
        self.assertEqual(lw.fetch_one(A, f, lambda s: None), ("err", "unavailable")); self.assertEqual(len(n), 1)   # 404 는 재시도하지 않는다
        n.clear()
        def g(url):
            n.append(1); raise OSError("x")
        self.assertEqual(lw.fetch_one(A, g, lambda s: None), ("err", "network")); self.assertEqual(len(n), 3)


if __name__ == "__main__":
    unittest.main()
