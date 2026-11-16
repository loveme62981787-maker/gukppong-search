# -*- coding: utf-8 -*-
"""수집 결과를 원격 main 최신 위에 안전하게 게시한다 (동시 실행·수동 push 와 충돌하지 않게)

    python safe_publish.py hot_shorts     터진 쇼츠 저장분(hot_shorts_store.json, web/hot_shorts.js)
    python safe_publish.py longform       롱폼 체험 저장분(longform_exp_store.json, web/longform_exp.js)

문제: 옛 커밋을 checkout 한 실행이 수집한 뒤 'git pull --rebase' 하면 생성 JS 한 줄이 충돌한다.
방식: 수집 결과(ours)를 메모리에 잡고, 이 대상 파일만 HEAD 로 되돌린 뒤 원격 최신으로 fast-forward 하고,
      원격 저장분에 ours 를 영상 ID 기준으로 합쳐(merge) 화면 파일을 다시 만든 뒤 커밋·push 한다.
      push 가 거절되면(그 사이 다른 push) 같은 일을 처음부터 다시 한다 (최대 retries 번).
      생성된 JS 텍스트를 rebase 로 합치지 않는다. 원격의 다른 파일·코드는 건드리지 않는다.
실패하면 0 이 아닌 코드로 끝나고, 수집 결과는 collection/checkpoint_<대상>.json (gitignored)에 남는다.
"""
import argparse
import json
import os
import subprocess
import sys

REMOTE, BRANCH = "origin", "main"


class PublishError(Exception):
    pass


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise PublishError(f"git {' '.join(args[:2])} 실패: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def foreign_dirty(paths, git_fn=git):
    """대상 paths 이외의 tracked 변경(unstaged·staged·충돌) 목록. untracked 는 git commit 에 섞이지 않으므로 보지 않는다"""
    out = git_fn("status", "--porcelain", "-z", "--untracked-files=no").stdout
    ok = {p.replace("\\", "/") for p in paths}
    ents, bad, k = out.split("\0"), [], 0
    while k < len(ents):
        e = ents[k]
        k += 1
        if len(e) < 4:
            continue
        names = [e[3:]]
        if e[0] in "RC" or e[1] in "RC":   # 이름 변경·복사는 원래 경로가 다음 항목에 따로 온다
            names.append(ents[k] if k < len(ents) else "")
            k += 1
        if any(n and n not in ok for n in names):
            bad.append(" -> ".join(names))
    return bad


def publish(paths, message, snapshot, merge_write, retries=5, remote=REMOTE, branch=BRANCH, git_fn=git, log=print, checkpoint_path=None):
    """snapshot() -> ours (메모리). merge_write(ours, base_text) 는 디스크에 있는 원격 최신 파일에 ours 를 합쳐 paths 를 다시 쓴다.
    base_text = 수집을 시작한 HEAD 에 커밋돼 있던 paths[0](저장분) 원문 (없으면 None) — 원격이 그 사이 따로 진전했는지 3-way 로 가리는 기준.
    시작 전에 paths 이외의 tracked 변경(staged 포함)이 있으면 아무것도 건드리지 않고 중단한다 (git commit·reset 이 사용자 작업을 휩쓸지 않게).
    실패하면 checkpoint_path(gitignored·비공개 경로)에 ours 를 JSON 으로 남긴다. 반환: 'pushed' | 'nochange'. 실패는 PublishError"""
    ours = snapshot()
    last = ""
    try:
        bad = foreign_dirty(paths, git_fn)
        if bad:
            raise PublishError("대상 파일 이외에 커밋되지 않은 tracked 변경이 있어 중단합니다 (아무것도 바꾸지 않음): " + ", ".join(bad[:8]))
        shown = git_fn("show", f"HEAD:{paths[0]}", check=False)
        base_text = shown.stdout if shown.returncode == 0 else None   # 수집 시작 시점의 저장분 (retries 동안 HEAD 가 움직이므로 처음에 한 번만 잡는다)
        for attempt in range(1, retries + 1):
            git_fn("fetch", remote, branch)
            tracked = [p for p in paths if git_fn("ls-files", "--error-unmatch", p, check=False).returncode == 0]
            if tracked:
                git_fn("checkout", "HEAD", "--", *tracked)   # 대상 파일만 되돌린다 (수집 결과는 ours 에 있다)
            for p in paths:
                if p not in tracked and os.path.exists(p):
                    os.remove(p)   # 아직 커밋된 적 없는 생성 파일: 원격이 같은 파일을 새로 추가했어도 ff 가 막히지 않게 치운다 (ours 는 메모리에 있다)
            git_fn("merge", "--ff-only", f"{remote}/{branch}")   # 로컬에 갈라진 커밋이 있으면 여기서 실패 → 덮어쓰지 않고 중단
            merge_write(ours, base_text)
            git_fn("add", "--", *paths)
            if git_fn("diff", "--cached", "--quiet", check=False).returncode == 0:
                return _done("nochange", checkpoint_path)
            base = git_fn("rev-parse", "HEAD").stdout.strip()
            git_fn("commit", "-m", message, "--", *paths)   # 경로를 지정해 대상 파일만 커밋한다
            r = git_fn("push", remote, f"HEAD:{branch}", check=False)
            if r.returncode == 0:
                return _done("pushed", checkpoint_path)
            last = (r.stderr or r.stdout).strip()[:300]
            log(f"push 거절(시도 {attempt}/{retries}), 원격 최신 위에서 다시 합칩니다: {last}")
            git_fn("reset", "--mixed", base)   # 우리 커밋만 취소. 시작 시 paths 이외 staged 가 없음을 확인했으므로 index 에는 대상 파일만 있다
        raise PublishError(f"push 를 {retries}번 시도했으나 계속 거절됨: {last}")
    except PublishError:
        _checkpoint(ours, checkpoint_path, log)
        raise


def _done(result, checkpoint_path):
    if checkpoint_path and os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)   # 게시됐으니 이전 실패분 체크포인트는 필요 없다
    return result


def _checkpoint(ours, path, log):
    """게시에 실패하면 메모리에만 있던 수집 결과가 사라지므로 gitignored 경로(collection/)에 남긴다. 저장분과 같은 공개 데이터라 비밀은 없다"""
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ours, f, ensure_ascii=False)
        log(f"수집 결과 체크포인트를 남겼습니다: {path}")
    except (OSError, TypeError, ValueError) as e:
        log(f"체크포인트 저장 실패: {type(e).__name__}")


def _base(text):
    """수집 시작 HEAD 의 저장분 원문 → dict. 없으면 빈 저장분({}), 읽을 수 없으면 NO_BASE(커서는 원격 우선으로 보수적 처리)"""
    import hot_shorts_watch as hs
    if text is None:
        return {}
    try:
        v = json.loads(text)
    except ValueError:
        return hs._NO_BASE
    return v if isinstance(v, dict) else hs._NO_BASE


def _hot():
    import hot_shorts_watch as hs
    paths = ["hot_shorts_store.json", "web/hot_shorts.js"]

    def snapshot():
        return hs.load_store_strict(hs.STORE)

    def merge_write(ours, base_text):
        merged = hs.merge_stores(hs.load_store_strict(hs.STORE), ours, _base(base_text))
        hs.write_atomic(hs.STORE, hs.json.dumps(merged, ensure_ascii=False, indent=1))
        hs.export(merged)
    return paths, "터진 쇼츠 데이터 업데이트", snapshot, merge_write


def _longform():
    import longform_watch as lw
    paths = ["longform_exp_store.json", "web/longform_exp.js"]

    def snapshot():
        return lw.load_store_strict(lw.STORE)

    def merge_write(ours, base_text):
        merged = lw.merge_stores(lw.load_store_strict(lw.STORE), ours, _base(base_text))
        lw.write_atomic(lw.STORE, lw.json.dumps(merged, ensure_ascii=False, indent=1))
        lw.export(merged)
    return paths, "롱폼 체험 영상 데이터 업데이트", snapshot, merge_write


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["hot_shorts", "longform"])
    ap.add_argument("--retries", type=int, default=5)
    a = ap.parse_args()
    paths, msg, snap, mw = _hot() if a.target == "hot_shorts" else _longform()
    try:
        cp = os.path.join("collection", f"checkpoint_{a.target}.json")   # collection/ 은 .gitignore 대상
        print("게시 결과:", publish(paths, msg, snap, mw, retries=a.retries, checkpoint_path=cp))
    except PublishError as e:
        print("::error::안전 게시 실패 — 수집분은 원격에 올라가지 않았습니다:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
