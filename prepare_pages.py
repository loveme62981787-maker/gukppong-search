"""Pages 배포용 디렉터리 만들기: web 을 복사하고, 일반 목록의 10분 이하 롱폼(181~600초) 영상을 ID 단위로 뺀다.

- 저장소의 web/ 원본은 건드리지 않는다. 배포 artifact 만 가볍게 만든다 (표준 라이브러리만 사용).
- 제외 기준: index.html 의 absorb 순서로 합친 뒤 최종 유효 길이가 180초 초과 ~ 600초 이하(600초 포함)인 영상. 숏폼(180초 이하)·길이 미확인·10분 초과는 그대로 둔다.
- ID 전역 제거: 제외가 확정된 ID 는 모든 일반 배열에서 사본(길이 누락·미확인 포함)까지 지워 사이트에서 되살아나지 않게 한다.
  같은 ID 의 최종 항목 중 범위 밖/미확인이 하나라도 있으면(UI 에 남는 경우) 아무 사본도 건드리지 않아 UI 와 같게 보존한다.
- 대상: `window.NAME=[...];` 형태의 순수 JSON 배열 할당 안의 영상 레코드(id + 길이). hot_shorts.js(쇼츠 전용)는 건너뛴다.
- 점수·라이선스·메타데이터 파일(AUTO_SCORES.items, video_licenses.js 등)은 길이 필드가 없어 그대로 남는다.
- JSON 으로 읽히지 않는 구간은 건드리지 않고(fail-safe) 보고서에 남긴다. 남기는 레코드는 원문 글자 그대로 보존한다.
- 길이 해석은 web/index.html 의 normLen 과 같다: 유효한 duration_sec 우선, 없으면 length 문자열(m:ss / h:mm:ss).

사용: python prepare_pages.py [--src web] [--out _site] [--dry-run] [--report 파일.json]
"""
import argparse
import channel_exclusions as channel_block
import json
import math
import re
import shutil
import sys
from pathlib import Path

MID_MIN_EXCL = 180   # 180초 초과부터
MID_MAX_INCL = 600   # 600초 이하까지 제외 (정확히 600 포함)
# index.html 의 absorb 호출 순서(앞이 먼저 합쳐짐). VIDEOS 는 V 의 시작 목록
ABSORB_ORDER = ["VIDEOS", "VIRAL", "EXPERIENCE", "JP_TOPIC_ITEMS", "GLOBAL_ITEMS", "GLOBAL_ITEMS_JP", "TOPIC_CANDIDATES", "REFERENCE",
                "BENCHMARK", "ALERTS", "TAIWAN_EXP", "KR_REGIONAL", "LONGFORM_EXP", "CC_VIDEOS"]
SKIP_FILES = {"hot_shorts.js", "hot_shorts_view.js"}   # 쇼츠 전용 데이터·화면은 보존
MARKER = ".prepare_pages"
_ASSIGN = re.compile(r"(?:^|;)[ \t]*window\.(\w+)[ \t]*=[ \t]*(?=\[)", re.M)
_LEN = re.compile(r"^(\d+):([0-5]\d)(?::([0-5]\d))?$")
_DEC = json.JSONDecoder()


def record_seconds(rec):
    """index.html normLen 과 같은 길이(초) 해석. 모르면 None"""
    d = rec.get("duration_sec")
    if isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d) and d >= 0:
        return math.floor(d)
    s = rec.get("length")
    m = _LEN.match(s.strip()) if isinstance(s, str) else None
    if not m:
        return None
    return int(m[1]) * 60 + int(m[2]) if m[3] is None else int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])


def in_mid(sec):
    return sec is not None and MID_MIN_EXCL < sec <= MID_MAX_INCL


def _split_array(text, start):
    """text[start]=='[' 인 JSON 배열을 원문 구간으로 나눈다 → (요소 구간 목록, 배열 끝 위치). 깨져 있으면 ValueError"""
    i = start + 1
    spans = []
    n = len(text)
    while True:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i < n and text[i] == "]" and not spans:
            return spans, i + 1
        val, end = _DEC.raw_decode(text, i)
        spans.append((i, end, val))
        j = end
        while j < n and text[j] in " \t\r\n":
            j += 1
        if j < n and text[j] == ",":
            i = j + 1
        elif j < n and text[j] == "]":
            return spans, j + 1
        else:
            raise ValueError("배열 구조 오류")


def scan_js_text(text):
    """`window.NAME=[...]` 배열을 모두 찾는다 → ([(NAME, start, spans, end)], skipped_vars)"""
    found, skipped, scan = [], [], 0
    while True:
        m = _ASSIGN.search(text, scan)
        if not m:
            return found, skipped
        start = m.end()
        try:
            spans, end = _split_array(text, start)
        except (ValueError, json.JSONDecodeError):
            skipped.append(m.group(1))
            scan = start + 1
            continue
        found.append((m.group(1), start, spans, end))
        scan = end


def filter_js_text(text, drop_ids):
    """JS 텍스트에서 drop_ids 에 속한 레코드를 뺀 새 텍스트와 통계. 반환 (text, removed_ids[중복 포함], kept_count, skipped_vars)"""
    out, pos, removed, kept = [], 0, [], 0
    found, skipped = scan_js_text(text)
    for _, start, spans, end in found:
        drop = [isinstance(v, dict) and v.get("id") in drop_ids for _, _, v in spans]
        if not any(drop):
            kept += len(spans)
            continue
        # 남는 요소는 원문 그대로, 요소 사이 구분 글자(쉼표·공백)는 원래 첫 구분을 재사용한다
        sep = text[spans[0][1]:spans[1][0]] if len(spans) > 1 else ","
        keep_src = [text[a:b] for (a, b, _), d in zip(spans, drop) if not d]
        removed += [v["id"] for (_, _, v), d in zip(spans, drop) if d]
        kept += len(keep_src)
        out.append(text[pos:start])
        out.append("[" + text[start + 1:spans[0][0]] + sep.join(keep_src) + "]")
        pos = end
    out.append(text[pos:])
    return "".join(out), removed, kept, skipped


def script_order(src):
    """index.html 의 <script src> 순서(파일명 → 순번). 목록에 없는 파일은 뒤로"""
    idx = src / "index.html"
    names = re.findall(r'<script[^>]+src="([^"?#]+)', idx.read_text("utf-8")) if idx.exists() else []
    return {n: i for i, n in enumerate(names)}


def compute_excluded(arrays):
    """index.html 의 absorb 를 그대로 흉내 내 ID 별 최종 유효 길이를 구하고, 제외할 ID 집합과 충돌 보존 ID 집합을 돌려준다.
    arrays: {NAME: [레코드, ...]} (스크립트 순서로 이어붙인 것). 반환 (excluded, conflict)"""
    entries = []    # V: 항목별 [id, sec]. VIDEOS 안의 같은 ID 는 별도 항목(UI 의 V.slice() 와 같다)
    first = {}      # V.find(v => v.id === x.id): 항목이 처음 생긴 위치
    for name in ABSORB_ORDER:
        for rec in arrays.get(name, []):
            if not isinstance(rec, dict) or not isinstance(rec.get("id"), str):
                continue
            sec = record_seconds(rec)
            i = first.get(rec["id"])
            if i is not None and name != "VIDEOS":
                if sec is not None:
                    entries[i][1] = sec
                continue
            first.setdefault(rec["id"], len(entries))
            entries.append([rec["id"], sec])
    by_id = {}
    for i, sec in entries:
        by_id.setdefault(i, []).append(sec)
    excluded = {i for i, s in by_id.items() if all(in_mid(x) for x in s)}
    conflict = {i for i, s in by_id.items() if any(in_mid(x) for x in s)} - excluded
    return excluded, conflict


def prepare(src, out, dry_run=False):
    """src 를 out 으로 복사하면서 필터링한다. dry_run 이면 파일을 쓰지 않고 보고서만 만든다"""
    src, out = Path(src).resolve(), Path(out).resolve()
    if not src.is_dir():
        raise SystemExit(f"원본 폴더가 없어요: {src}")
    if out == src or src in out.parents or out in src.parents:
        raise SystemExit("출력 폴더는 원본 폴더와 겹치면 안 돼요")
    if not dry_run:
        if out.exists():
            if not (out / MARKER).exists():
                raise SystemExit(f"기존 폴더를 덮어쓰지 않아요(표식 없음): {out}")
            shutil.rmtree(out)
        shutil.copytree(src, out)
        (out / MARKER).write_text("prepare_pages.py 가 만든 배포용 사본\n", "utf-8")
    # 1차: 모든 일반 배열을 읽어 absorb 순서로 ID 별 최종 길이 → 제외 ID 집합 (쇼츠 전용 파일은 읽지 않는다)
    order = script_order(src)
    files = sorted((f for f in src.rglob("*.js") if f.name not in SKIP_FILES),
                   key=lambda f: (order.get(f.relative_to(src).as_posix(), len(order)), f.relative_to(src).as_posix()))
    arrays, texts = {}, {}
    for f in files:
        try:
            texts[f] = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        for name, _, spans, _ in scan_js_text(texts[f])[0]:
            arrays.setdefault(name, []).extend(v for _, _, v in spans)
    excluded, conflict = compute_excluded(arrays)
    block_path = src.parent / "channel_exclusions.json"
    block_config = json.loads(block_path.read_text("utf-8")) if block_path.exists() else {}
    block_ids = channel_block.blocked_ids((f.read_text("utf-8") for f in src.rglob("*.js")), block_config) if block_config else set()
    report = {"min_sec_excl": MID_MIN_EXCL, "max_sec_incl": MID_MAX_INCL, "files": {}, "skipped_vars": {}, "parse_errors": [],
              "conflict_preserved_ids": sorted(conflict)}
    all_ids, total_before, total_after = set(), 0, 0
    for f in sorted(src.rglob("*.js")):
        rel = f.relative_to(src).as_posix()
        raw = f.read_bytes()
        total_before += len(raw)
        new_raw = raw
        if f.name not in SKIP_FILES:
            text = texts.get(f)
            if text is None:
                report["parse_errors"].append(rel)
            else:
                new_text, removed, kept, skipped = filter_js_text(text, excluded)
                if skipped:
                    report["skipped_vars"][rel] = skipped
                if removed:
                    new_raw = new_text.encode("utf-8")
                    all_ids.update(removed)
                    report["files"][rel] = {"removed_records": len(removed), "removed_unique_ids": len(set(removed)),
                                            "kept_records": kept, "bytes_before": len(raw), "bytes_after": len(new_raw)}
                    if not dry_run:
                        (out / rel).write_bytes(new_raw)
        if block_config:
            new_raw = channel_block.filter_text(new_raw.decode("utf-8"), block_config, block_ids).encode("utf-8")
            if not dry_run and new_raw != raw:
                (out / rel).write_bytes(new_raw)
        total_after += len(new_raw)
    report["channel_blocked_ids"] = sorted(block_ids)
    report["removed_unique_ids"] = len(all_ids)
    report["removed_ids"] = sorted(all_ids)
    report["bytes_before"] = total_before
    report["bytes_after"] = total_after
    report["dry_run"] = dry_run
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default="web")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 제거 예정 보고서만 만든다")
    ap.add_argument("--report", help="전체 보고서(제거 ID 목록 포함)를 저장할 JSON 경로")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    r = prepare(a.src, a.out, a.dry_run)
    if a.report:
        Path(a.report).write_text(json.dumps(r, ensure_ascii=False, indent=1), "utf-8")
    print(f"{'[dry-run] ' if a.dry_run else ''}제거 고유 ID {r['removed_unique_ids']}개 · 용량 {r['bytes_before']:,} → {r['bytes_after']:,} bytes "
          f"(-{r['bytes_before'] - r['bytes_after']:,})")
    for rel, s in r["files"].items():
        print(f"  {rel}: -{s['removed_records']}건 (남음 {s['kept_records']}) {s['bytes_before']:,}→{s['bytes_after']:,}")
    if r["conflict_preserved_ids"]:
        print(f"  충돌(범위 안·밖 길이 혼재)로 보존한 ID {len(r['conflict_preserved_ids'])}개")
    if r["skipped_vars"] or r["parse_errors"]:
        print(f"  ! 파싱 못해 그대로 둔 곳: {r['skipped_vars']} {r['parse_errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
