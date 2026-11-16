import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import hot_shorts_watch as hs
import longform_watch as lw
import safe_publish as sp

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
PATHS = ["store.json", "web/out.js"]


def run(cwd, *a):
    r = subprocess.run(["git", *a], cwd=cwd, env=ENV, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def merge_write_for(cwd):
    """원격 최신 파일에 ours(id→값)를 합치고 화면 파일을 다시 만드는 테스트용 합치기 (같은 키는 더 큰 값)"""
    def mw(ours, base_text=None):
        sj = Path(cwd, "store.json")
        cur = json.loads(sj.read_text("utf-8")) if sj.exists() else {}
        cur.update({k: v for k, v in ours.items() if k not in cur or v >= cur[k]})
        sj.write_text(json.dumps(cur, sort_keys=True), "utf-8")
        Path(cwd, "web").mkdir(exist_ok=True)
        Path(cwd, "web/out.js").write_text("window.X=" + json.dumps(cur, sort_keys=True) + ";\n", "utf-8")
    return mw


class Repo:
    def __init__(self, root):
        self.root = root
        self.bare = os.path.join(root, "origin.git")
        run(root, "init", "--bare", "-b", "main", self.bare)
        seed = os.path.join(root, "seed")
        run(root, "init", "-b", "main", seed)
        Path(seed, "store.json").write_text("{}", "utf-8")
        Path(seed, "web").mkdir()
        Path(seed, "web/out.js").write_text("window.X={};\n", "utf-8")
        Path(seed, "code.py").write_text("print(1)\n", "utf-8")
        run(seed, "add", "."); run(seed, "commit", "-m", "init"); run(seed, "push", self.bare, "HEAD:main")

    def clone(self, name):
        d = os.path.join(self.root, name)
        run(self.root, "clone", "-b", "main", self.bare, d)
        return d


class PublishRace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.repo = Repo(self.root)
        self.cwd0 = os.getcwd()
        self.env0 = dict(os.environ)
        os.environ.update({k: v for k, v in ENV.items() if k.startswith("GIT_")})   # sp.git 이 커밋할 때 쓸 신원

    def tearDown(self):
        os.chdir(self.cwd0)
        os.environ.clear()
        os.environ.update(self.env0)
        self.tmp.cleanup()

    def publish(self, d, ours, **kw):
        os.chdir(d)
        return sp.publish(PATHS, "데이터", lambda: ours, merge_write_for(d), log=lambda *_: None, **kw)

    def remote_file(self, name):
        return run(self.root, "--git-dir", self.repo.bare, "show", "main:" + name)

    def remote_store(self):
        return json.loads(self.remote_file("store.json"))

    def test_stale_checkout_merges_without_conflict(self):
        stale = self.repo.clone("stale")   # 옛 커밋 (run43841193201 처럼)
        fresh = self.repo.clone("fresh")
        self.assertEqual(self.publish(fresh, {"A": "2026-11-16"}), "pushed")
        self.assertEqual(self.publish(stale, {"B": "2026-11-16"}), "pushed")   # 같은 파일을 다르게 바꿨지만 충돌 없이 합쳐진다
        self.assertEqual(self.remote_store(), {"A": "2026-11-16", "B": "2026-11-16"})
        js = self.remote_file("web/out.js")
        self.assertIn('"A"', js)
        self.assertIn('"B"', js)

    def test_push_race_retries_and_keeps_both(self):
        a, b = self.repo.clone("a"), self.repo.clone("b")
        raced = {"done": False}

        def git_fn(*args, check=True):
            if args[0] == "push" and not raced["done"]:
                raced["done"] = True   # 내 push 직전에 다른 실행이 먼저 push
                self.publish(a, {"A": "2026-11-16"})
            os.chdir(b)
            return sp.git(*args, check=check)
        os.chdir(b)
        r = sp.publish(PATHS, "데이터", lambda: {"B": "2026-11-16"}, merge_write_for(b), git_fn=git_fn, log=lambda *_: None)
        self.assertEqual(r, "pushed")
        self.assertTrue(raced["done"])
        self.assertEqual(self.remote_store(), {"A": "2026-11-16", "B": "2026-11-16"})

    def test_unrelated_remote_changes_preserved(self):
        stale = self.repo.clone("stale")
        other = self.repo.clone("other")
        Path(other, "code.py").write_text("print(2)\n", "utf-8")
        run(other, "commit", "-am", "수동 코드 변경"); run(other, "push", "origin", "HEAD:main")
        self.publish(stale, {"B": "x"})
        self.assertEqual(self.remote_file("code.py"), "print(2)")

    def test_older_stats_do_not_overwrite_newer_remote(self):
        a, b = self.repo.clone("a"), self.repo.clone("b")
        self.publish(a, {"K": "2026-11-16"})
        self.publish(b, {"K": "2026-11-10"})   # 오래된 값은 원격 값을 덮지 못한다
        self.assertEqual(self.remote_store(), {"K": "2026-11-16"})

    def test_nochange(self):
        a = self.repo.clone("a")
        self.publish(a, {"K": "1"})
        b = self.repo.clone("b")
        self.assertEqual(self.publish(b, {"K": "1"}), "nochange")

    def test_diverged_local_history_fails_loudly_and_pushes_nothing(self):
        a, b = self.repo.clone("a"), self.repo.clone("b")
        Path(b, "code.py").write_text("print(9)\n", "utf-8")
        run(b, "commit", "-am", "로컬 커밋")
        self.publish(a, {"A": "1"})
        with self.assertRaises(sp.PublishError):
            self.publish(b, {"B": "1"})
        self.assertEqual(self.remote_store(), {"A": "1"})

    def assert_untouched(self, d, head, remote_store):
        self.assertEqual(run(d, "rev-parse", "HEAD"), head)
        self.assertEqual(self.remote_store(), remote_store)

    def test_staged_unrelated_file_aborts_before_any_change(self):
        b = self.repo.clone("b")
        Path(b, "code.py").write_text("print(7)\n", "utf-8")
        run(b, "add", "code.py")   # 사용자가 staging 해 둔 무관 파일
        head = run(b, "rev-parse", "HEAD")
        with self.assertRaises(sp.PublishError) as cm:
            self.publish(b, {"B": "1"})
        self.assertIn("code.py", str(cm.exception))
        self.assert_untouched(b, head, {})
        self.assertEqual(run(b, "diff", "--cached", "--name-only"), "code.py")   # staging 그대로
        self.assertEqual(Path(b, "code.py").read_text("utf-8"), "print(7)\n")

    def test_unstaged_unrelated_edit_aborts_and_is_preserved(self):
        b = self.repo.clone("b")
        Path(b, "code.py").write_text("print(8)\n", "utf-8")
        head = run(b, "rev-parse", "HEAD")
        with self.assertRaises(sp.PublishError):
            self.publish(b, {"B": "1"})
        self.assert_untouched(b, head, {})
        self.assertEqual(Path(b, "code.py").read_text("utf-8"), "print(8)\n")
        self.assertEqual(run(b, "diff", "--cached", "--name-only"), "")

    def test_dirty_target_files_are_allowed(self):
        b = self.repo.clone("b")
        Path(b, "store.json").write_text('{"B": "1"}', "utf-8")   # 수집이 써 둔 결과 (대상 파일)
        Path(b, "scratch.txt").write_text("untracked", "utf-8")   # untracked 는 커밋에 섞이지 않으므로 막지 않는다
        self.assertEqual(self.publish(b, {"B": "1"}), "pushed")
        self.assertEqual(self.remote_store(), {"B": "1"})

    def test_push_retry_does_not_touch_unrelated_files(self):
        a, b = self.repo.clone("a"), self.repo.clone("b")
        raced = {"done": False}

        def git_fn(*args, check=True):
            if args[0] == "push" and not raced["done"]:
                raced["done"] = True
                self.publish(a, {"A": "1"})
            os.chdir(b)
            return sp.git(*args, check=check)
        os.chdir(b)
        sp.publish(PATHS, "데이터", lambda: {"B": "1"}, merge_write_for(b), git_fn=git_fn, log=lambda *_: None)
        self.assertEqual(run(b, "status", "--porcelain", "--untracked-files=no"), "")

    def test_commit_contains_only_target_paths(self):
        b = self.repo.clone("b")
        self.publish(b, {"B": "1"})
        files = run(self.root, "--git-dir", self.repo.bare, "show", "--name-only", "--format=", "main").split()
        self.assertEqual(sorted(files), sorted(PATHS))

    def test_failure_leaves_checkpoint_and_success_removes_it(self):
        b = self.repo.clone("b")
        cp = os.path.join(b, "collection", "cp.json")
        Path(b, "code.py").write_text("print(3)\n", "utf-8")   # 가드로 실패
        os.chdir(b)
        with self.assertRaises(sp.PublishError):
            sp.publish(PATHS, "데이터", lambda: {"B": "1"}, merge_write_for(b), log=lambda *_: None, checkpoint_path=cp)
        self.assertEqual(json.loads(Path(cp).read_text("utf-8")), {"B": "1"})
        run(b, "checkout", "--", "code.py")
        sp.publish(PATHS, "데이터", lambda: {"B": "1"}, merge_write_for(b), log=lambda *_: None, checkpoint_path=cp)
        self.assertFalse(os.path.exists(cp))

    def test_base_text_is_head_store_at_start(self):
        a, b = self.repo.clone("a"), self.repo.clone("b")
        self.publish(a, {"A": "1"})   # 원격만 전진 — b 의 HEAD 는 아직 {}
        seen = []

        def mw(ours, base_text):
            seen.append(base_text)
            merge_write_for(b)(ours)
        os.chdir(b)
        sp.publish(PATHS, "데이터", lambda: {"B": "1"}, mw, log=lambda *_: None)
        self.assertEqual(seen, ["{}"])   # 수집 시작 HEAD 의 저장분

    def test_persistent_rejection_raises_after_retries(self):
        b = self.repo.clone("b")

        class Rejected:
            returncode, stderr, stdout = 1, "rejected", ""

        def git_fn(*args, check=True):
            os.chdir(b)
            return Rejected() if args[0] == "push" else sp.git(*args, check=check)
        os.chdir(b)
        with self.assertRaises(sp.PublishError):
            sp.publish(PATHS, "데이터", lambda: {"B": "1"}, merge_write_for(b), retries=2, git_fn=git_fn, log=lambda *_: None)
        self.assertEqual(self.remote_store(), {})


def ch(cid, checked, med, videos=(), cache=None, bf=None):
    rec = {"id": cid, "checked": checked, "subs": 1000, "median_views": med, "videos": [dict(v) for v in videos], "membership_cache": cache or {}}
    if bf:
        rec["backfill"] = bf
    return rec


def vd(i, views, checked, at=None):
    v = {"id": i, "views": views, "checked": checked, "title": i}
    if at:
        v["collected_at"] = at
    return v


def chat(cid, at, med, videos=(), bf=None):
    """collected_at(UTC 시각)이 있는 채널 기록"""
    rec = ch(cid, at[:10], med, videos, bf=bf)
    rec["collected_at"] = at
    return rec


def store(*chs, upd="2026-11-16"):
    return {"updated": upd, "channels": {c["id"]: c for c in chs}}


A, B = "UC" + "a" * 22, "UC" + "b" * 22


class HotMerge(unittest.TestCase):
    def test_union_keeps_both_sides_and_newer_stats(self):
        remote = {"updated": "2026-11-16", "channels": {A: ch(A, "2026-11-16", 500, [vd("v1", 100, "2026-11-16")], bf={"token": "R", "pages": 5})}}
        ours = {"updated": "2026-11-15", "channels": {A: ch(A, "2026-11-15", 100, [vd("v1", 90, "2026-11-15"), vd("v2", 300, "2026-11-15")], bf={"token": "O", "pages": 9}),
                                                      B: ch(B, "2026-11-15", 7)}}
        m = hs.merge_stores(remote, ours)
        a = m["channels"][A]
        self.assertEqual(m["updated"], "2026-11-16")
        self.assertEqual(a["median_views"], 500)   # 더 늦게 확인한 원격 통계 유지
        self.assertEqual({v["id"]: v["views"] for v in a["videos"]}, {"v1": 100, "v2": 300})   # 합집합, 같은 ID 는 더 늦은 값
        self.assertEqual(a["backfill"], {"token": "R", "pages": 5})   # 커서 충돌은 원격 보존
        self.assertIn(B, m["channels"])

    def test_newer_ours_wins_stats_but_keeps_remote_only_videos(self):
        remote = {"updated": "2026-11-10", "channels": {A: ch(A, "2026-11-10", 5, [vd("old", 1, "2026-11-10")])}}
        ours = {"updated": "2026-11-16", "channels": {A: ch(A, "2026-11-16", 50, [vd("new", 2, "2026-11-16")])}}
        a = hs.merge_stores(remote, ours)["channels"][A]
        self.assertEqual(a["median_views"], 50)
        self.assertEqual({v["id"] for v in a["videos"]}, {"old", "new"})

    def test_empty_sides(self):
        self.assertEqual(hs.merge_stores({}, {"updated": "x", "channels": {A: ch(A, "x", 1)}})["channels"].keys(), {A})
        self.assertEqual(hs.merge_stores({"updated": "x", "channels": {A: ch(A, "x", 1)}}, {})["channels"].keys(), {A})


T0, T1, T2 = "2026-11-16T00:20:00Z", "2026-11-16T06:20:00Z", "2026-11-16T12:20:00Z"


class HotThreeWay(unittest.TestCase):
    def test_normal_consecutive_run_advances_cursor(self):
        base = store(chat(A, T0, 5, bf={"token": "T1", "pages": 1}))
        remote = base   # 수집하는 동안 원격은 그대로
        ours = store(chat(A, T1, 5, bf={"token": "T5", "pages": 5}))
        m = hs.merge_stores(remote, ours, base)
        self.assertEqual(m["channels"][A]["backfill"], {"token": "T5", "pages": 5})

    def test_new_channel_and_first_cursor_are_taken(self):
        base, remote = store(), store()
        ours = store(chat(B, T1, 5, bf={"token": "T1", "pages": 1}))
        self.assertEqual(hs.merge_stores(remote, ours, base)["channels"][B]["backfill"], {"token": "T1", "pages": 1})

    def test_concurrent_remote_cursor_is_preserved(self):
        base = store(chat(A, T0, 5, bf={"token": "T1", "pages": 1}))
        remote = store(chat(A, T1, 5, bf={"token": "R", "pages": 9}))   # 그 사이 다른 실행이 push
        ours = store(chat(A, T1, 5, bf={"token": "T5", "pages": 5}))
        self.assertEqual(hs.merge_stores(remote, ours, base)["channels"][A]["backfill"], {"token": "R", "pages": 9})

    def test_cursor_reset_by_ours_is_taken_when_remote_unmoved(self):
        base = store(chat(A, T0, 5, bf={"done": True, "done_at": "2026-11-01", "pages": 3}))
        ours = store(chat(A, T1, 5))   # 완주 후 14일 지나 커서를 비움
        self.assertNotIn("backfill", hs.merge_stores(base, ours, base)["channels"][A])

    def test_no_base_keeps_remote_cursor_conservatively(self):
        remote = store(chat(A, T0, 5, bf={"token": "R"}))
        ours = store(chat(A, T1, 5, bf={"token": "O"}))
        self.assertEqual(hs.merge_stores(remote, ours)["channels"][A]["backfill"], {"token": "R"})

    def test_same_day_newer_stats_are_taken(self):
        remote = store(chat(A, T0, 100, [vd("v1", 1000, "2026-11-16", T0)]))
        ours = store(chat(A, T1, 150, [vd("v1", 1500, "2026-11-16", T1)]))   # 같은 날 6시간 뒤 실행
        a = hs.merge_stores(remote, ours, remote)["channels"][A]
        self.assertEqual(a["median_views"], 150)
        self.assertEqual(a["videos"][0]["views"], 1500)

    def test_stale_observation_does_not_overwrite_newer_remote(self):
        remote = store(chat(A, T2, 150, [vd("v1", 1500, "2026-11-16", T2)]))
        ours = store(chat(A, T0, 100, [vd("v1", 1000, "2026-11-16", T0), vd("v2", 7, "2026-11-16", T0)]))   # 같은 날 더 오래된 관측
        a = hs.merge_stores(remote, ours, remote)["channels"][A]
        self.assertEqual(a["median_views"], 150)
        self.assertEqual({v["id"]: v["views"] for v in a["videos"]}, {"v1": 1500, "v2": 7})

    def test_legacy_date_only_remote_is_older_than_same_day_timestamp(self):
        remote = store(ch(A, "2026-11-16", 100, [vd("v1", 1000, "2026-11-16")]))   # 옛 기록: 날짜만
        ours = store(chat(A, T1, 150, [vd("v1", 1500, "2026-11-16", T1)]))
        self.assertEqual(hs.merge_stores(remote, ours, remote)["channels"][A]["median_views"], 150)

    def test_build_channel_stamps_collected_at(self):
        info = {"title": "t", "subs": 1000, "country": "KR"}
        seed = {"id": A, "kind": "travel_original"}
        vids = [{"id": "%011d" % i, "title": "외국인 한국 여행", "views": 20000, "duration_sec": 30, "published_at": "2026-11-01T00:00:00Z"} for i in range(20)]
        rec = hs.build_channel(seed, info, vids, [{"id": v["id"]} for v in vids], None, "2026-11-16", collected_at=T1)
        self.assertEqual(rec["collected_at"], T1)
        self.assertTrue(all(v["collected_at"] == T1 for v in rec["videos"]))
        self.assertTrue(all(m["collected_at"] == T1 for m in rec["membership_cache"].values()))
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.js")
            hs.export({"updated": "x", "channels": {A: rec}}, out, exclusions={}, seeds=[])
            js = Path(out).read_text("utf-8")
        self.assertIn('"id":"%s"' % A, js.replace(" ", ""))
        self.assertEqual(js.count("collected_at"), len(rec["videos"]))   # 채널 항목에는 내부 시각을 싣지 않는다 (영상 항목에만)


class LongformThreeWay(unittest.TestCase):
    def lf(self, at, cursor, items=None, upd="2026-11-16"):
        return {"updated": upd, "collected_at": at, "cursor": cursor, "items": items or {}}

    def test_normal_run_advances_cursor(self):
        base = self.lf(T0, {"KR": 0, "JP": 0, "TW": 0})
        ours = self.lf(T1, {"KR": 4, "JP": 4, "TW": 4})
        self.assertEqual(lw.merge_stores(base, ours, base)["cursor"], {"KR": 4, "JP": 4, "TW": 4})

    def test_concurrent_remote_cursor_preserved(self):
        base = self.lf(T0, {"KR": 0})
        remote = self.lf(T1, {"KR": 8})
        ours = self.lf(T1, {"KR": 4})
        self.assertEqual(lw.merge_stores(remote, ours, base)["cursor"], {"KR": 8})

    def test_empty_base_takes_ours(self):
        self.assertEqual(lw.merge_stores({}, self.lf(T1, {"KR": 4}), {})["cursor"], {"KR": 4})

    def test_same_day_views_update_only_when_newer(self):
        it = lambda v: {"a": {"id": "a", "first_seen": "2026-11-16", "views": v}}
        newer = lw.merge_stores(self.lf(T0, {}, it(1)), self.lf(T1, {}, it(9)))
        self.assertEqual(newer["items"]["a"]["views"], 9)
        older = lw.merge_stores(self.lf(T2, {}, it(5)), self.lf(T1, {}, it(9)))
        self.assertEqual(older["items"]["a"]["views"], 5)
        self.assertEqual(older["collected_at"], T2)


class LongformMerge(unittest.TestCase):
    def test_union_and_remote_cursor(self):
        remote = {"updated": "2026-11-16", "cursor": {"KR": 4}, "items": {"a": {"id": "a", "first_seen": "2026-11-16", "views": 5}}}
        ours = {"updated": "2026-11-15", "cursor": {"KR": 8}, "items": {"a": {"id": "a", "first_seen": "2026-11-14", "views": 3}, "b": {"id": "b", "first_seen": "2026-11-15", "views": 1}}}
        m = lw.merge_stores(remote, ours)
        self.assertEqual(set(m["items"]), {"a", "b"})
        self.assertEqual(m["items"]["a"]["views"], 3)   # 같은 ID: 첫 발견일이 더 이른 쪽 기록
        self.assertEqual(m["items"]["a"]["first_seen"], "2026-11-14")
        self.assertEqual(m["cursor"], {"KR": 4})
        self.assertEqual(m["updated"], "2026-11-16")


class WorkflowGates(unittest.TestCase):
    def test_collect_export_outcomes_reach_verdict_and_deploy_needs_publish(self):
        root = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        for name in ("hot_shorts.yml", "longform.yml"):
            y = (root / name).read_text("utf-8")
            for k in ("collect_failed", "export_failed", "publish_failed"):
                self.assertIn(k + ": ${{ steps.", y, name)
                self.assertIn("needs.build.outputs." + k, y, name)
            self.assertIn("steps.collect.outcome == 'failure'", y, name)
            self.assertIn("steps.export.outcome == 'failure'", y, name)
            self.assertIn("if: needs.build.outputs.published == 'true'", y, name)   # 게시 실패한 working tree 는 배포하지 않는다
            self.assertEqual(y.count("if: steps.publish.outcome == 'success'"), 2, name)   # configure-pages, upload-pages-artifact
            self.assertIn("checkpoint", y, name)


if __name__ == "__main__":
    unittest.main()
