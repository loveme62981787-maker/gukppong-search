import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cc_discover as cc
import license_watch as lw
from test_license_watch import page, CC, STD, A, B, C

NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
D = "ddddddddddd"


def cand(vid, title="My first time in Korea travel vlog", sec=600):
    return {"id": vid, "title": title, "channel": "ch", "channel_id": "UC1", "views": 5, "length": "10:00", "duration_sec": sec}


def read_js(path):
    return json.loads(open(path, encoding="utf-8").read()[len("window.CC_VIDEOS="):-2])


class GateTest(unittest.TestCase):
    def test_topic_filter(self):
        self.assertTrue(cc.topic_ok(cand(A), "한국"))
        self.assertFalse(cc.topic_ok(cand(A, sec=120), "한국"))   # 숏폼
        self.assertFalse(cc.topic_ok(cand(A, "No copyright music Korea travel"), "한국"))
        self.assertFalse(cc.topic_ok(cand(A, "Korea travel vlog"), "일본"))   # 다른 나라
        self.assertFalse(cc.topic_ok(cand(A, "Seoul election news"), "한국"))
        self.assertFalse(cc.topic_ok(cand("bad"), "한국"))   # 잘못된 ID

    def test_search_result_alone_never_published(self):
        store, lic = cc.empty_store(), {"items": {}}
        cc.add_candidates(store, [cand(A)], "한국", "q", lic["items"], NOW, 5)
        self.assertEqual(store["items"][A]["status"], "pending")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.js")
            self.assertEqual(cc.export_js(store, lic, p), 0)
            self.assertEqual(read_js(p), [])

    def test_verdicts(self):
        store, lic = cc.empty_store(), {"items": {}}
        cc.add_candidates(store, [cand(A), cand(B), cand(C)], "한국", "q", lic["items"], NOW, 5)
        cc.apply_verdict(store, lic, A, lw.parse_watch(page(A, [CC]), A), NOW)
        cc.apply_verdict(store, lic, B, lw.parse_watch(page(B, [STD]), B), NOW)
        cc.apply_verdict(store, lic, C, ("err", "blocked"), NOW)
        self.assertEqual([store["items"][i]["status"] for i in (A, B, C)], ["verified", "rejected", "pending"])
        self.assertEqual(store["items"][C]["fail_count"], 1)
        self.assertFalse(cc.is_due(store["items"][C], NOW))   # 백오프 중
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.js")
            self.assertEqual(cc.export_js(store, lic, p), 1)
            data = read_js(p)
            self.assertEqual([x["id"] for x in data], [A])
            self.assertEqual(data[0]["foreign"], "unknown")
            self.assertNotIn("description", data[0])

    def test_failure_preserves_verified(self):
        store, lic = cc.empty_store(), {"items": {}}
        cc.add_candidates(store, [cand(A)], "한국", "q", lic["items"], NOW, 5)
        cc.apply_verdict(store, lic, A, lw.parse_watch(page(A, [CC]), A), NOW)
        cc.apply_verdict(store, lic, A, ("err", "blocked"), NOW)   # 재확인 실패
        self.assertEqual(store["items"][A]["status"], "verified")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cc.export_js(store, lic, os.path.join(d, "o.js")), 1)
        self.assertEqual(lw.export_item(lic["items"][A]).get("s"), 1)   # 화면에는 '지난 확인 기준' 표시


class BudgetTest(unittest.TestCase):
    def test_rotation_and_budget(self):
        store = cc.empty_store()
        first = cc.pick_queries(store, 1, NOW)
        self.assertEqual([c for c, _ in first], ["한국", "일본", "대만"])
        for c, q in first:
            store["searches"][c + "|" + q] = {"at": lw.iso(NOW)}
        second = cc.pick_queries(store, 1, NOW)   # 쓴 검색어는 간격 안에서 건너뛰고 다른 검색어로 돈다
        self.assertEqual(len(second), 3)
        self.assertTrue(all(q not in [f[1] for f in first] for _, q in second))
        for c, q in second:
            store["searches"][c + "|" + q] = {"at": lw.iso(NOW)}
        for c, qs in cc.QUERIES.items():
            for q in qs:
                store["searches"][c + "|" + q] = {"at": lw.iso(NOW)}
        self.assertEqual(cc.pick_queries(store, 1, NOW), [])   # 전부 최근에 썼으면 쉰다
        self.assertEqual(len(cc.pick_queries(store, 1, datetime(2026, 11, 2, 12, 0, 0, tzinfo=timezone.utc))), 3)

    def test_candidate_cap_and_known_untouched(self):
        store, lic = cc.empty_store(), {"items": {}}
        store["items"][A] = {"id": A, "status": "verified"}
        found = [cand(x * 11) for x in "abcdefgh"]
        new = cc.add_candidates(store, found, "한국", "q", lic["items"], NOW, 5)
        self.assertEqual(len(new), 5)
        self.assertEqual(store["items"][A], {"id": A, "status": "verified"})


class RunTest(unittest.TestCase):
    def _env(self, d):
        web = os.path.join(d, "web")
        os.makedirs(web)
        with open(os.path.join(web, "videos.js"), "w", encoding="utf-8") as f:
            f.write('window.VIDEOS=[{"id":"%s","first_seen":"2026-10-01"}];' % A)
        return web, dict(store_path=os.path.join(d, "c.json"), lic_path=os.path.join(d, "l.json"), out_path=os.path.join(web, "cc_videos.js"), web_dir=web)

    def test_block_stops_quickly(self):
        calls = []

        def get(url):
            calls.append(url)
            raise OSError("blocked")
        with tempfile.TemporaryDirectory() as d:
            _, kw = self._env(d)
            r = cc.run(1, 5, 2, get=get, fetch=get, sleep=lambda s: None, now_fn=lambda: NOW, **kw)
        self.assertTrue(r["stopped"])
        self.assertEqual(len(calls), 1)   # 첫 검색 실패에서 즉시 중단

    def test_same_id_merge_and_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            web, kw = self._env(d)
            with open(kw["lic_path"], "w") as f:
                json.dump({"schema": 1, "updated": "", "items": {C: {"license": "standard", "checked_at": "2026-10-30"}}}, f)
            vids = [cand(A), cand(D)]

            def get(url):
                if "results" in url:
                    self.assertIn("sp=" + cc.CC_SP, url)
                    rows = [{"videoRenderer": {"videoId": v["id"], "title": {"runs": [{"text": v["title"]}]},
                                               "ownerText": {"runs": [{"text": "ch", "navigationEndpoint": {"browseEndpoint": {"browseId": "UC1"}}}]},
                                               "lengthText": {"simpleText": "10:00"}, "viewCountText": {"simpleText": "5 views"}}} for v in vids]
                    return "var ytInitialData = " + json.dumps({"a": rows}) + ";</script>"
                return page(url.split("=")[-1], [CC])
            r = cc.run(1, 5, 2, get=get, fetch=get, sleep=lambda s: None, now_fn=lambda: NOW, **kw)
            self.assertEqual(sorted(r["new"]), sorted([A, D]))
            self.assertEqual(r["exported"], 2)
            lic = lw.load_store(kw["lic_path"])
            self.assertEqual(lic["items"][C]["license"], "standard")   # 기존 라이선스 기록 보존
            self.assertEqual(lic["items"][A]["license"], "cc_by")
            self.assertIn(D, lw.load_inventory(web))   # 확인된 CC 가 라이선스 입력 재고에 포함


def dated(vid, pub, key="publishDate", rows=(CC,)):
    return page(vid, list(rows)).replace('"playerMicroformatRenderer": {', '"playerMicroformatRenderer": {"%s": "%s", ' % (key, pub))


class DateTest(unittest.TestCase):
    def test_extract_validates_date_and_identity(self):
        self.assertEqual(lw.parse_watch(dated(A, "2024-05-01T10:00:00-07:00"), A)[1]["published"], "2024-05-02")   # 한국시간 변환
        self.assertEqual(lw.parse_watch(dated(A, "2023-02-03", "uploadDate"), A)[1]["published"], "2023-02-03")
        for bad in ("2024-13-40", "not a date", "2099-01-01", "1999-01-01", ""):
            self.assertEqual(lw.parse_watch(dated(A, bad), A)[1]["published"], "", bad)   # 날짜를 지어내지 않는다
        self.assertEqual(lw.parse_watch(page(A, [CC]), A)[1]["published"], "")
        self.assertEqual(lw.parse_watch(dated(B, "2024-05-01"), A), ("err", "identity_mismatch"))   # 다른 영상 페이지의 날짜는 쓰지 않는다
        self.assertEqual(lw.parse_watch(dated(A, "2024-05-01", rows=(STD,)), A)[1]["license"], "standard")   # 날짜가 라이선스 판정에 영향 없음

    def test_verdict_keeps_date_and_exports(self):
        store, lic = cc.empty_store(), {"items": {}}
        cc.add_candidates(store, [cand(A)], "한국", "q", lic["items"], NOW, 5)
        cc.apply_verdict(store, lic, A, lw.parse_watch(dated(A, "2024-05-01"), A), NOW)
        cc.apply_verdict(store, lic, A, lw.parse_watch(page(A, [CC]), A), NOW)   # 이후 날짜가 빈 결과로 덮지 않는다
        cc.apply_verdict(store, lic, A, ("err", "blocked"), NOW)
        self.assertEqual(store["items"][A]["published"], "2024-05-01")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.js")
            cc.export_js(store, lic, p)
            self.assertEqual(read_js(p)[0]["published"], "2024-05-01")
            self.assertNotIn("description", json.dumps(store))

    def test_backfill_fills_only_missing_and_keeps_on_failure(self):
        store, lic = cc.empty_store(), {"items": {}}
        cc.add_candidates(store, [cand(A), cand(B), cand(C), cand(D)], "한국", "q", lic["items"], NOW, 5)
        for v in (A, B, C, D):
            cc.apply_verdict(store, lic, v, lw.parse_watch(page(v, [CC]), v), NOW)
        store["items"][D]["published"] = "2020-01-01"
        calls = []

        def fetch(url):
            vid = url.split("=")[-1]
            calls.append(vid)
            if vid == B:
                return "<html>nothing</html>"   # 정상 페이지 아님 → 실패, 날짜는 그대로 빈 값
            return dated(vid, "2024-06-07")
        with tempfile.TemporaryDirectory() as d:
            sp, lp, op = (os.path.join(d, n) for n in ("c.json", "l.json", "o.js"))
            cc.save_store(store, sp)
            lw.save_store(lic, lp)
            before = json.dumps(lw.load_store(lp), sort_keys=True)
            filled, failed, stopped = cc.backfill_dates(2, fetch, lambda s: None, lambda: NOW, sp, lp, op)
            self.assertEqual((filled, stopped), (2, ""))
            self.assertEqual(failed, [B + ":blocked"])
            self.assertNotIn(D, calls)   # 이미 날짜가 있으면 다시 요청하지 않는다
            self.assertEqual(json.dumps(lw.load_store(lp), sort_keys=True), before)   # 라이선스 기록은 재평가하지 않는다
            pubs = {x["id"]: x["published"] for x in read_js(op)}
            self.assertEqual(pubs, {A: "2024-06-07", B: "", C: "2024-06-07", D: "2020-01-01"})

    def test_backfill_stops_on_block(self):
        store, lic = cc.empty_store(), {"items": {}}
        ids = ["a" * 10 + x for x in "12345678"]
        cc.add_candidates(store, [cand(i) for i in ids], "한국", "q", lic["items"], NOW, 9)
        for i in ids:
            store["items"][i]["status"] = "verified"
        calls = []

        def fetch(url):
            calls.append(url)
            raise OSError("blocked")
        with tempfile.TemporaryDirectory() as d:
            sp, lp, op = (os.path.join(d, n) for n in ("c.json", "l.json", "o.js"))
            cc.save_store(store, sp)
            lw.save_store(lic, lp)
            r = cc.backfill_dates(2, fetch, lambda s: None, lambda: NOW, sp, lp, op)
        self.assertTrue(r[2])
        self.assertLessEqual(len(calls), 6)   # 첫 묶음(2개, 재시도 포함)에서 멈춘다


if __name__ == "__main__":
    unittest.main()
