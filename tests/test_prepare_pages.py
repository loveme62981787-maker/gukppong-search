import json
import tempfile
import unittest
from pathlib import Path

import prepare_pages as pp


def js(name, items, sep=", "):
    return f"window.{name}=[" + sep.join(json.dumps(i, ensure_ascii=False) for i in items) + "];\n"


def rec(i, sec=None, length=None):
    r = {"id": i, "title": "제목 " + i, "score": 7}
    if sec is not None:
        r["duration_sec"] = sec
    if length is not None:
        r["length"] = length
    return r


class PreparePagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.src, self.out = self.tmp / "web", self.tmp / "_site"
        (self.src / "channels" / "x").mkdir(parents=True)
        (self.src / "channels" / "x" / "index.html").write_text("<p>채널</p>", "utf-8")

    def run_prepare(self, dry=False):
        return pp.prepare(self.src, self.out, dry)

    def out_ids(self, name, var):
        t = (self.out / name).read_text("utf-8")
        return [r["id"] for r in json.loads(t[t.index("=") + 1:t.rindex(";")])]

    def test_exact_boundary_sets(self):
        items = [rec("s180", 180), rec("m181", 181), rec("m600", 600), rec("l601", 601), rec("unk"),
                 rec("str_mid", length="5:30"), rec("str_edge", length="10:00"), rec("str_long", length="10:01"),
                 rec("bad", length="쓰레기"), rec("float", 180.9)]
        (self.src / "videos.js").write_text(js("VIDEOS", items), "utf-8")
        r = self.run_prepare()
        self.assertEqual(self.out_ids("videos.js", "VIDEOS"), ["s180", "l601", "unk", "str_long", "bad", "float"])
        self.assertEqual(sorted(r["removed_ids"]), ["m181", "m600", "str_edge", "str_mid"])
        self.assertLess(r["bytes_after"], r["bytes_before"])

    def test_shorts_file_and_originals_preserved(self):
        hot = "window.HOT_SHORTS=" + json.dumps({"videos": [rec("h1", 300), rec("h2", 59)]}) + ";\n"
        hot_list = js("HOT_SHORTS_LIST", [rec("h3", 300)])
        (self.src / "hot_shorts.js").write_text(hot + hot_list, "utf-8")
        orig = js("VIDEOS", [rec("m1", 300), rec("k", 700)])
        (self.src / "videos.js").write_text(orig, "utf-8")
        self.run_prepare()
        self.assertEqual((self.out / "hot_shorts.js").read_text("utf-8"), hot + hot_list)
        self.assertEqual((self.src / "videos.js").read_text("utf-8"), orig)   # 원본 web 은 그대로
        self.assertEqual((self.out / "channels" / "x" / "index.html").read_text("utf-8"), "<p>채널</p>")

    def test_duplicate_ids_counted_once_and_all_records_removed(self):
        (self.src / "a.js").write_text(js("VIDEOS", [rec("dup", 300), rec("keep", 900)]), "utf-8")
        (self.src / "b.js").write_text(js("VIRAL", [rec("dup", 300), rec("dup", 400)]), "utf-8")
        r = self.run_prepare()
        self.assertEqual(r["removed_ids"], ["dup"])
        self.assertEqual(r["removed_unique_ids"], 1)
        self.assertEqual(sum(s["removed_records"] for s in r["files"].values()), 3)
        self.assertEqual(self.out_ids("b.js", "VIRAL"), [])

    def ids_after(self, files):
        """files: {파일명: (변수, 레코드들)} → 제거 후 {파일명: id 목록}, 보고서"""
        for name, (var, items) in files.items():
            (self.src / name).write_text(js(var, items), "utf-8")
        r = self.run_prepare()
        return {n: self.out_ids(n, v) for n, (v, _) in files.items()}, r

    def test_unknown_copy_does_not_revive_excluded_id(self):
        got, r = self.ids_after({"a.js": ("VIDEOS", [rec("x", 300), rec("ok", 700)]), "b.js": ("VIRAL", [rec("x")]),
                                 "c.js": ("EXPERIENCE", [rec("x", length="쓰레기")])})
        self.assertEqual(got, {"a.js": ["ok"], "b.js": [], "c.js": []})
        self.assertEqual(r["removed_ids"], ["x"])
        got, _ = self.ids_after({"a.js": ("VIDEOS", [rec("y")]), "b.js": ("VIRAL", [rec("y", 300)])})   # 미확인이 먼저여도 같다
        self.assertEqual(got, {"a.js": [], "b.js": []})

    def test_conflict_follows_ui_absorb_order(self):
        # 나중에 합쳐지는 길이가 이긴다: VIDEOS 300 → VIRAL 900 이면 최종 900 → 전부 보존
        got, r = self.ids_after({"a.js": ("VIDEOS", [rec("c", 300)]), "b.js": ("VIRAL", [rec("c", 900)])})
        self.assertEqual(got, {"a.js": ["c"], "b.js": ["c"]})
        self.assertEqual(r["conflict_preserved_ids"], [])   # 최종 유효 길이 하나(900)라 충돌 아님, 그냥 범위 밖
        # 반대 순서: VIDEOS 900 → VIRAL 300 이면 최종 300 → 전부 제거
        got, _ = self.ids_after({"a.js": ("VIDEOS", [rec("c", 900)]), "b.js": ("VIRAL", [rec("c", 300)])})
        self.assertEqual(got, {"a.js": [], "b.js": []})
        # source 순서가 파일명 순서와 달라도 absorb 순서(ALERTS 가 VIRAL 보다 뒤)를 따른다
        got, _ = self.ids_after({"a.js": ("ALERTS", [rec("d", 300)]), "b.js": ("VIRAL", [rec("d", 900)])})
        self.assertEqual(got, {"a.js": [], "b.js": []})

    def test_same_videos_list_duplicates_with_conflict_are_preserved(self):
        got, r = self.ids_after({"v.js": ("VIDEOS", [rec("e", 300), rec("e", 900)])})   # UI 는 별도 항목 둘 → 900 쪽이 보임
        self.assertEqual(got, {"v.js": ["e", "e"]})
        self.assertEqual(r["conflict_preserved_ids"], ["e"])
        self.assertEqual(r["removed_ids"], [])

    def test_script_order_in_index_html_decides_same_var_order(self):
        (self.src / "index.html").write_text('<script src="z.js"></script><script src="a.js?v=1"></script>', "utf-8")
        got, _ = self.ids_after({"a.js": ("VIRAL", [rec("f", 300)]), "z.js": ("VIRAL", [rec("f", 900)])})   # z 먼저, a 나중 → 300 최종
        self.assertEqual(got, {"a.js": [], "z.js": []})

    def test_dry_run_writes_nothing(self):
        (self.src / "videos.js").write_text(js("VIDEOS", [rec("m1", 300)]), "utf-8")
        r = self.run_prepare(dry=True)
        self.assertEqual(r["removed_unique_ids"], 1)
        self.assertFalse(self.out.exists())

    def test_unparsable_is_left_alone_and_reported(self):
        bad = 'window.VIDEOS=[{"id":"m1","duration_sec":300},{broken}];\n'
        (self.src / "videos.js").write_text(bad, "utf-8")
        good = js("VIRAL", [rec("m2", 300)])
        (self.src / "ok.js").write_text(good, "utf-8")
        r = self.run_prepare()
        self.assertEqual((self.out / "videos.js").read_text("utf-8"), bad)
        self.assertEqual(r["skipped_vars"], {"videos.js": ["VIDEOS"]})
        self.assertEqual(r["removed_ids"], ["m2"])

    def test_kept_records_and_other_statements_byte_identical(self):
        keep = rec("k", 999)
        text = ('window.CH_UPDATED="x";\n' + js("VIDEOS", [rec("m", 300), keep], sep=",") +
                'window.VIDEOS=window.VIDEOS||[];\nwindow.SCORES={"items":[{"id":"m","duration_sec":300}]};\n')
        (self.src / "videos.js").write_text(text, "utf-8")
        self.run_prepare()
        out = (self.out / "videos.js").read_text("utf-8")
        self.assertEqual(out, text.replace(json.dumps(rec("m", 300), ensure_ascii=False) + ",", ""))   # 점수 객체(비배열)는 그대로

    def test_no_change_file_identical_and_non_list_values_untouched(self):
        t = 'window.GLOBAL_TOPICS={"a":{"duration_sec":300,"id":"zz"}};\n'
        (self.src / "t.js").write_text(t, "utf-8")
        r = self.run_prepare()
        self.assertEqual((self.out / "t.js").read_text("utf-8"), t)
        self.assertEqual(r["files"], {})

    def test_refuse_overlapping_or_unmarked_out(self):
        with self.assertRaises(SystemExit):
            pp.prepare(self.src, self.src / "sub")
        self.out.mkdir()
        (self.out / "keep.txt").write_text("x")
        with self.assertRaises(SystemExit):
            self.run_prepare()


if __name__ == "__main__":
    unittest.main()
