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


if __name__ == "__main__":
    unittest.main()
