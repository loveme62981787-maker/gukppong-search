import unittest
from pathlib import Path

import hot_shorts_watch as hs
import longform_watch as lw

ROOT = Path(__file__).parents[1]


def vid(i, title, sec, live="none"):
    return {"id": i, "title": title, "channel": "c", "channel_id": "UC" + "x" * 22, "published": "2026-11-01", "views": 12, "duration_sec": sec, "live": live}


class ClassifyTests(unittest.TestCase):
    def test_country_and_basis_from_title(self):
        self.assertEqual(lw.classify("Foreigners first time Korea travel vlog"), ("KR", "foreign_title"))
        self.assertEqual(lw.classify("外國人 台灣 夜市 小吃 體驗"), ("TW", "foreign_title"))
        self.assertEqual(lw.classify("외국인 일본 소도시 여행 체험"), ("JP", "foreign_title"))
        self.assertEqual(lw.classify("후쿠오카 도쿄 여행 브이로그"), ("JP", "ko_region"))   # 한국어 제목 + 일본 지역명: 제작자 국적은 확정하지 않는 추정

    def test_rejections(self):
        self.assertIsNone(lw.classify("서울 부산 여행 브이로그"))                       # 한국 소재는 외국인 신호 필수
        self.assertIsNone(lw.classify("Foreigner Japan Korea trip vlog"))              # 두 나라 섞임
        self.assertIsNone(lw.classify("Japan election news foreigner"))                # 뉴스·정치
        self.assertIsNone(lw.classify("Taiwan travel official MV lyrics"))             # 음악
        self.assertIsNone(lw.classify("Did you know facts about Japan travel foreigner"))   # 잡학
        self.assertIsNone(lw.classify("Foreigner in North Korea travel"))
        self.assertIsNone(lw.classify("Taiwan foreigner"))                              # 여행·체험 단어 없음


class QueryTests(unittest.TestCase):
    def test_at_most_twelve_and_rotates(self):
        jobs, cur = lw.pick_queries({})
        self.assertLessEqual(len(jobs), lw.MAX_QUERIES)
        self.assertEqual({j[0] for j in jobs}, {"KR", "JP", "TW"})
        jobs2, _ = lw.pick_queries(cur)
        self.assertNotEqual([j[1] for j in jobs], [j[1] for j in jobs2])
        self.assertTrue(all(j[2] in ("medium", "long") for j in jobs))

    def test_pool_has_korean_region_queries_for_jp_tw(self):
        for cc in ("JP", "TW"):
            self.assertTrue(any(hs.re.search(r"[가-힣]{2,}", q) for q, _ in lw.POOL[cc]))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.n = 0

    def api(self, job):
        return ["AAAAAAAAAA" + job[0][0], "BBBBBBBBBB" + job[0][0], "CCCCCCCCCC" + job[0][0], "DDDDDDDDDD" + job[0][0]]

    def detail(self, ids):
        out = {}
        for i in ids:
            cc = {"K": "Korea", "J": "Japan", "T": "Taiwan"}[i[-1]]
            kind = i[0]
            out[i] = {"A": vid(i, f"Foreigner first time {cc} travel vlog", 1500), "B": vid(i, f"Foreigner first time {cc} travel vlog", 700),   # 700초: 12분 미만
                      "C": vid(i, f"Foreigner first time {cc} travel vlog", 50), "D": vid(i, f"Foreigner {cc} trip live", 1500, live="live")}[kind]
        return out

    def test_filters_length_shorts_live_and_site_duplicates(self):
        site = {"AAAAAAAAAAK"}   # 이미 사이트에 있는 한국 영상
        store, rep = lw.run({}, site, "2026-11-16", api_fn=self.api, detail_fn=self.detail)
        self.assertEqual(set(store["items"]), {"AAAAAAAAAAJ", "AAAAAAAAAAT"})   # 12분 미만·쇼츠·라이브·사이트 중복 제외
        self.assertEqual(rep["KR"]["on_site_already"], 1)
        self.assertEqual(rep["KR"]["added"], [])
        self.assertEqual(len(rep["JP"]["added"]), 1)
        it = store["items"]["AAAAAAAAAAJ"]
        self.assertEqual((it["country"], it["lf_basis"], it["section"]), ("일본", "foreign_title", "longform_exp"))
        self.assertNotIn("description", it)
        self.assertGreaterEqual(it["duration_sec"], 720)

    def test_known_store_ids_are_not_new(self):
        first, _ = lw.run({}, set(), "d1", api_fn=self.api, detail_fn=self.detail)
        again, rep = lw.run(first, set(), "d2", api_fn=self.api, detail_fn=self.detail, cursor={})
        self.assertEqual(sum(len(r["added"]) for r in rep.values()), 0)
        self.assertEqual(set(again["items"]), set(first["items"]))

    def test_api_failure_keeps_store_and_falls_back_to_public(self):
        def boom(job):
            raise hs.ApiError("search 실패: HTTP 403")
        pub = lambda job: [dict(vid("PPPPPPPPPP" + job[0][0], f"Foreigner first time {({'K': 'Korea', 'J': 'Japan', 'T': 'Taiwan'})[job[0][0]]} travel vlog", 1500), published="")]  # noqa: E731
        prev = {"items": {"OLDOLDOLDOK": {"id": "OLDOLDOLDOK", "lf_country": "KR"}}}
        store, rep = lw.run(prev, set(), "d", api_fn=boom, detail_fn=lambda ids: {}, public_fn=pub)
        self.assertIn("OLDOLDOLDOK", store["items"])
        self.assertEqual(rep["KR"]["prev_store"], 1)
        self.assertTrue(all(v["published"] == "" for k, v in store["items"].items() if k.startswith("PPPP")))   # 공개 파서 결과의 게시일은 추정하지 않는다


class WiringTests(unittest.TestCase):
    def test_index_and_workflow(self):
        h = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('src="longform_exp.js', h)
        self.assertIn('"longform_exp"', h)
        self.assertIn('absorb(x, null, "longform_exp")', h)   # 같은 ID 는 기존 영상에 출처만 덧붙인다
        y = (ROOT / ".github" / "workflows" / "longform.yml").read_text(encoding="utf-8")
        self.assertRegex(y, r"concurrency:\s*\n\s*group: update")
        self.assertIn("python safe_publish.py longform", y)
        self.assertIn("ref: main", y)
        self.assertNotIn("git pull --rebase", y)


if __name__ == "__main__":
    unittest.main()
