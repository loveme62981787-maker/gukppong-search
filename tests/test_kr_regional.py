import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

import kr_regional_watch as kr

ROOT = Path(__file__).parents[1]


def video(title, sec=900, **kw):
    v = {"id": "AAAAAAAAAAA", "title": title, "channel": "채널", "channel_id": "UCx", "age_h": 100, "age_text": "4d ago", "length": "15:00", "duration_sec": sec, "views": 1000}
    v.update(kw)
    return v


class JudgeTests(unittest.TestCase):
    def test_accepts_regional_experience_titles(self):
        a = kr.judge(video("후쿠오카 3박4일 여행 브이로그 #후쿠오카"))
        self.assertEqual((a["country"], a["region"], a["hashtag"]), ("일본", "후쿠오카", True))
        b = kr.judge(video("타이베이 야시장 먹방 일상"))
        self.assertEqual((b["country"], b["region"], b["hashtag"]), ("대만", "타이베이", False))
        self.assertEqual(kr.judge(video("도쿄 한달살기 일상 vlog"))["country"], "일본")

    def test_rejects_shorts_news_reedits_domestic_and_mixed(self):
        for t, sec in [("후쿠오카 여행 브이로그", 60), ("후쿠오카 여행 브이로그", None), ("후쿠오카 여행 #shorts", 900), ("도쿄 지진 속보 여행객", 900),
                       ("도쿄 여행 해외반응 모음", 900), ("서울에서 먹는 도쿄 맛집", 900), ("도쿄 타이베이 여행 브이로그", 900), ("후쿠오카 정치 이야기", 900),
                       ("후쿠오카", 900), ("Fukuoka travel vlog", 900)]:
            self.assertIsNone(kr.judge(video(t, sec)), t)

    def test_danshui_false_positives(self):
        for t in ["우리 아파트 단수이 사태 여행 갈래", "오늘 단수이 발생 복구 공사", "단수이 예정 안내 브이로그"]:
            self.assertIsNone(kr.judge(video(t)), t)
        self.assertEqual(kr.judge(video("단수이 노을 맛집 여행"))["region"], "단수이")
        self.assertEqual(kr.judge(video("대만 단수이 브이로그"))["country"], "대만")
        self.assertIsNone(kr.judge(video("단수이 정보")))   # 대만·여행 근거 없음

    def test_no_nationality_claim_in_evidence(self):
        ev = kr.judge(video("오사카 여행 브이로그"))
        self.assertFalse({"nationality", "creator_country", "korean"} & set(ev))


class MergeAndFailureTests(unittest.TestCase):
    now = datetime(2026, 11, 5, tzinfo=timezone(timedelta(hours=9)))

    def test_failed_searches_keep_previous_data(self):
        prev = {"OLD00000001": {"id": "OLD00000001", "first_seen": "2026-11-01", "title": "x"}}
        found, ok = kr.collect([("q", kr.SORTS)], runner=lambda job: None)
        self.assertEqual((found, ok), ({}, 0))
        self.assertEqual(kr.merge(prev, found, self.now), prev)

    def test_merge_keeps_first_seen_and_unions_evidence(self):
        v = video("후쿠오카 여행 브이로그")
        found, ok = kr.collect([("후쿠오카", kr.SORTS)], runner=lambda job: [v])
        prev = {"AAAAAAAAAAA": {"first_seen": "2026-10-01", "kr_words": ["맛집"], "kr_queries": ["old"]}}
        out = kr.merge(prev, found, self.now)["AAAAAAAAAAA"]
        self.assertEqual(out["first_seen"], "2026-10-01")
        self.assertIn("맛집", out["kr_words"])
        self.assertIn("브이로그", out["kr_words"])
        self.assertIn("old", out["kr_queries"])
        self.assertTrue(out["ko_title"] and out["kr_regional"])

    def test_queries_cover_multiple_regions_per_country(self):
        qs = [q for q, _ in kr.queries()]
        for tag in ["#후쿠오카", "#도쿄", "#오사카", "#단수이", "#타이베이", "#지우펀"]:
            self.assertIn(tag, qs)


class WiringTests(unittest.TestCase):
    def test_workflow_runs_and_commits_collector_output(self):
        y = (ROOT / ".github/workflows/update.yml").read_text(encoding="utf-8")
        self.assertIn("python taiwan_watch.py", y)
        entry = (ROOT / "taiwan_watch.py").read_text(encoding="utf-8")
        self.assertIn("kr_regional_watch.main()", entry)
        self.assertIn('"kr_regional_store.json", "web/kr_regional.js"', entry)

    def test_published_data_is_unique_and_longform(self):
        p = ROOT / "web/kr_regional.js"
        if not p.exists():
            self.skipTest("아직 수집 전")
        rows = json.loads(p.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
        self.assertEqual(len(rows), len({r["id"] for r in rows}))
        for r in rows:
            self.assertIn(r["country"], ("일본", "대만"))
            self.assertGreaterEqual(r["duration_sec"], 181)
            self.assertTrue(r["kr_regional"] and r["ko_title"])


if __name__ == "__main__":
    unittest.main()
