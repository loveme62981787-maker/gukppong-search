"""영상별 라이선스 상태 수집기 (표준 라이브러리만 사용, API 키 없음).

사이트가 쓰는 모든 입력 데이터(web/*.js 의 영상 목록)의 영상 ID 를 모아 중복 없이 하나씩 watch 페이지를 읽고,
  1) 영상 자체의 구조화된 라이선스 행(CC BY / 표준 YouTube 라이선스)
  2) 설명란의 '이 영상 자체'에 대한 명시적 무료 사용 허용 문구
만 기록한다. 채널·이름·검색 스니펫으로는 추정하지 않고, 표기가 없다고 표준으로 간주하지도 않는다.

저장: data/video_licenses.json (영상 ID 별 상태·확인일)  →  내보내기: web/video_licenses.js
실행: python license_watch.py [--limit N] [--workers N] [--max-seconds N] [--export-only]
설계 근거: docs/collab/2026-10-31-license-tabs.md
"""
import argparse
import json
import os
import random
import re
import sys
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import discover

BASE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE, "data", "video_licenses.json")
OUT = os.path.join(BASE, "web", "video_licenses.js")
WEB = os.path.join(BASE, "web")
SCHEMA = 1

# 사이트가 읽는 영상 목록 (파일, 변수). 모든 수집 경로를 합쳐 영상 ID 로 중복을 없앤다
INPUTS = [("videos.js", "VIDEOS"), ("viral.js", "VIRAL"), ("experience.js", "EXPERIENCE"), ("japan_topics.js", "JP_TOPIC_ITEMS"),
          ("global_topics.js", "GLOBAL_ITEMS"), ("global_topics_jp.js", "GLOBAL_ITEMS_JP"), ("topic_candidates.js", "TOPIC_CANDIDATES"),
          ("reference.js", "REFERENCE"), ("benchmark.js", "BENCHMARK"), ("alerts.js", "ALERTS"), ("taiwan_exp.js", "TAIWAN_EXP"),
          ("cc_videos.js", "CC_VIDEOS")]   # cc_discover.py 가 CC BY 로 확인한 영상도 재확인 대상에 포함
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# 다시 확인하는 주기 (확인에 성공한 기록 / 실패 기록의 재시도 간격)
RECHECK_DAYS = {"cc_by": 14, "standard": 30, "unknown": 30}
RETRY_BASE_H, RETRY_MAX_H = 6, 24 * 7
MARKER_MISS_LIMIT = 2   # CC BY 로 확인된 영상에서 표기가 연속 2번 사라져야 '미확인'으로 내린다 (화면 구성이 달라 한 번 빠지는 경우 대비)
CIRCUIT_FAILS = 10      # 연속 실패가 이만큼이면 차단으로 보고 이번 실행을 멈춘다 (기존 기록은 그대로)
SAVE_EVERY = 25


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 입력 영상 ID 목록
def load_inventory(web_dir=WEB):
    """사이트 입력 데이터의 영상 ID → first_seen(있으면). 읽을 수 없는 파일은 건너뛰고 나머지를 쓴다"""
    inv, dec = {}, json.JSONDecoder()
    for fname, var in INPUTS:
        try:
            with open(os.path.join(web_dir, fname), encoding="utf-8") as f:
                text = f.read()
            m = re.search(r"window\." + var + r"\s*=\s*", text)
            data, _ = dec.raw_decode(text, m.end())
        except (OSError, AttributeError, ValueError):
            print(f"  입력 건너뜀: {fname} ({var})")
            continue
        for x in data if isinstance(data, list) else []:
            vid = x.get("id") if isinstance(x, dict) else None
            if isinstance(vid, str) and ID_RE.match(vid):
                fs = x.get("first_seen") if isinstance(x.get("first_seen"), str) else ""
                if vid not in inv or fs > inv[vid]:
                    inv[vid] = fs
    return inv


# ---------------------------------------------------------------- watch 페이지 해석
def _json_after(page, name):
    m = re.search(r"(?:var\s+|window\.|window\[[\"'])" + name + r"[\"']?\]?\s*=\s*", page)
    if not m:
        return None
    try:
        return json.JSONDecoder().raw_decode(page, m.end())[0]
    except ValueError:
        return None


def _text(o):
    if not isinstance(o, dict):
        return ""
    return o.get("simpleText") or "".join(r.get("text", "") for r in o.get("runs", []) if isinstance(r, dict))


def _walk(o, fn):
    stack = [o]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            fn(x)
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)


CC_DENY_RE = re.compile(r"non-?commercial|no-?deriv|share-?alike|\bcc0\b|\bby-(?:nc|sa|nd)\b|public domain dedication|\bzero\b|\b(?:nc|sa|nd)\b")
CC_BY_URL_RE = re.compile(r"^https?://(?:www\.)?creativecommons\.org/licenses/by/\d+(?:\.\d+)?/?$", re.I)


def _classify_license(text, urls):
    """라이선스 행 하나 → 'cc_by' | 'standard' | 'unrecognized'. CC BY 는 명시적 Attribution 표기, 정확한 /licenses/by/<버전> 링크, YouTube 공식 creative_commons 링크만 인정한다.
    by-nc/by-sa/by-nd/cc0 같은 다른 조건과 임의의 creativecommons.org 주소는 인정하지 않는다"""
    s = text.casefold()
    if CC_DENY_RE.search(s) or any(re.search(r"/licenses/(?!by/)|/publicdomain/|/by-(?:nc|sa|nd)", u, re.I) for u in urls):
        return "unrecognized"
    yt = any(urlparse(u).netloc.lower().endswith("youtube.com") and urlparse(u).path.rstrip("/") == "/t/creative_commons" for u in urls)
    if "creative commons attribution" in s or yt or any(CC_BY_URL_RE.match(u.strip()) for u in urls):
        return "cc_by"
    if "standard youtube license" in s or "표준 youtube 라이선스" in s or "표준 유튜브 라이선스" in s:
        return "standard"
    return "unrecognized"


LICENSE_TITLES = {"license", "licence", "라이선스", "라이센스", "ライセンス", "licencia", "lizenz", "licença"}


def license_from_data(data):
    """영상 자체의 라이선스 행만 읽는다 (추천 영상 영역은 제외). 반환: 'cc_by' | 'standard' | 'unrecognized' | None(표기 없음)"""
    res = data.get("contents", {}).get("twoColumnWatchNextResults", {}).get("results", {}).get("results", {})
    roots = [res.get("contents", []), data.get("engagementPanels", [])]
    kinds = set()

    def visit(d):
        row = d.get("metadataRowRenderer")
        if not isinstance(row, dict) or _text(row.get("title")).strip().casefold() not in LICENSE_TITLES:
            return
        texts, urls = [], []
        for c in row.get("contents", []):
            texts.append(_text(c))
            for r in c.get("runs", []) if isinstance(c, dict) else []:
                u = (r.get("navigationEndpoint") or {}).get("urlEndpoint", {}).get("url", "") if isinstance(r, dict) else ""
                if u:
                    urls.append(u)
        kinds.add(_classify_license(" ".join(texts), urls))

    _walk(roots, visit)
    if not kinds:
        return None
    return kinds.pop() if len(kinds) == 1 else "unrecognized"


# 설명란 무료 사용 허용 문구: '이 영상 자체'에 대한 명시적 허용만. 배경음악·스톡 소스 표기, 부정·면책 문구는 제외한다
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_SPLIT_RE = re.compile(r"[\n\r.!?。！？;；]+")
NOT_VIDEO_RE = re.compile(
    r"\b(music|songs?|tracks?|bgm|soundtrack|sound ?effects?|sfx|audio|beats?|instrumental|stock|footage from|pixabay|pexels|unsplash|"
    r"shutterstock|storyblocks|artlist|epidemic ?sound|incompetech|kevin ?mac ?leod|freepik|envato|canva|fonts?|images?|photos?|pictures?|"
    r"icons?|templates?|lyrics?|thumbnails?)\b|음악|배경음|브금|효과음|음원|폰트|이미지|사진|썸네일|音楽|効果音|音源|フォント|画像|写真|サムネ",
    re.I)
COND_RE = re.compile(r"\b(?:if|when|unless|once) you\s+(?:purchase|buy|pay|subscribe|join|donate|become)|\b(?:purchase|paid|premium|membership|patreon|for a fee|license fee)\b|구매|결제|유료|구독 ?(?:시|하면|해야)|購入|有料", re.I)   # 구매·결제·구독 조건부 문구는 무료 허용이 아니다
DENY_RE = re.compile(
    r"\b(not|never|no)\s+(be\s+)?(free|allowed|permitted|reused?|re-?upload\w*|used?|copied|copy|for (reuse|commercial|redistribution))|"
    r"\b(do(es)? not|don'?t|cannot|can'?t|must not)\s+(use|reuse|re-?upload|repost|copy|download|steal|edit)|"
    r"\bwithout (my |our |prior |written |the )?(permission|consent|authori[sz]ation)|\bpermission (is )?(required|needed)|\bask (me |us )?(for )?permission|"
    r"\bcontact (me|us) (for|to|before)\b[^.]{0,20}(use|reuse|permission|licens)|\ball rights reserved|\bno (reuse|re-?upload\w*|reposting|redistribution)|"
    r"\b(prohibited|forbidden)\b|무단|허락 ?없이|허가 ?없이|[사이]용 ?금지|재업로드 ?금지|사전 ?(허락|동의|협의)|허락을? ?받|저작권 ?(침해|보호)|"
    r"転載禁止|無断|禁止|許可なく|許可を",
    re.I)
_EN_SUBJ = r"(?:video|videos|vlog|footage|clips?|film|content)"
POSITIVE = [
    ("en_video", re.compile(
        r"\b(?:this|the|my|our)\s+(?:entire\s+|whole\s+)?" + _EN_SUBJ + r"\b[^,;]{0,30}?\b(?:is|are|may be|can be)\s+(?:completely\s+|totally\s+|100%\s+)?"
        r"(?:free to (?:use|reuse|re-use|edit)|free for (?:anyone|everyone|all|public)(?: to use)?|in the public domain|public domain)", re.I)),
    ("en_video", re.compile(
        r"\b(?:feel free|you(?:'re| are) (?:free|welcome)|you (?:can|may)|anyone can|everyone can)\s+(?:to\s+)?(?:freely\s+)?(?:reuse|re-?use|re-?upload|edit|repost|remix)\s+"
        r"(?:this|the|my|our|these|any of (?:my|our|the))\s+" + _EN_SUBJ + r"\b", re.I)),
    ("en_video", re.compile(
        r"\bfeel free to use\s+(?:this|the|my|our|these|any of (?:my|our|the))\s+" + _EN_SUBJ + r"\b[^,;]{0,25}?"
        r"(?:in your|for your|for any|in any|commercially|for (?:free|personal|commercial)|without (?:asking|permission|credit)|with credit|as long as|if you credit)", re.I)),
]
_KO_SUBJ = re.compile(r"영상|동영상|콘텐츠|클립|브이로그")
_KO_PERM = re.compile(r"(?:자유롭게|마음껏|무료로|누구나).{0,12}?(?:사용|이용|편집|재사용|재업로드)(?:해도|하셔도|하실 수|할 수|가능|됩니다|돼요|좋습니다|좋아요)")
_JA_SUBJ = re.compile(r"動画|映像|ビデオ|クリップ")
_JA_PERM = re.compile(r"(?:自由に|ご自由に|無料で|誰でも).{0,10}?(?:使用|利用|使って|使え|転載|編集)")
_JA_OK = re.compile(r"OK|ＯＫ|可能|できます|大丈夫|ください|いただいて|構いません")


def free_use_rule(description):
    """설명란에서 이 영상 자체의 무료 사용 허용 문구를 찾는다. 반환: 규칙 코드('en_video'|'ko_video'|'ja_video') 또는 None. 원문은 어디에도 남기지 않는다"""
    if not description:
        return None
    text = _MAIL_RE.sub(" ", _URL_RE.sub(" ", description[:6000]))
    segs = [s.strip() for s in _SPLIT_RE.split(text) if s.strip()]
    if any(DENY_RE.search(s) for s in segs):
        return None   # 부정·면책 문구가 하나라도 있으면 허용으로 보지 않는다 (보수적)
    for s in segs:
        if NOT_VIDEO_RE.search(s) or COND_RE.search(s):
            continue   # 배경음악·스톡·이미지 등 영상 자체가 아닌 자료의 표기
        for code, rx in POSITIVE:
            if rx.search(s):
                return code
        if _KO_SUBJ.search(s) and _KO_PERM.search(s):
            return "ko_video"
        if _JA_SUBJ.search(s) and _JA_PERM.search(s) and _JA_OK.search(s):
            return "ja_video"
    return None


def parse_watch(page, vid):
    """반환: ('ok', {license, free_rule, has_desc}) 또는 ('err', 코드). 대상 영상 ID 가 정확히 같을 때만 ok"""
    pr = _json_after(page, "ytInitialPlayerResponse")
    if not isinstance(pr, dict):
        return "err", "blocked"   # 동의/차단/봇 확인 화면 등 정상 watch 페이지가 아님
    st = (pr.get("playabilityStatus") or {}).get("status")
    got = (pr.get("videoDetails") or {}).get("videoId")
    if st == "LOGIN_REQUIRED" and not got:
        return "err", "blocked"
    if got != vid:
        return "err", "unavailable" if st in ("ERROR", "UNPLAYABLE") and not got else "identity_mismatch"
    if st not in ("OK", "LIVE_STREAM_OFFLINE", "CONTENT_CHECK_REQUIRED"):
        return "err", "unavailable"
    data = _json_after(page, "ytInitialData")
    if not isinstance(data, dict):
        return "err", "no_initial_data"
    ep = data.get("currentVideoEndpoint", {}).get("watchEndpoint", {}).get("videoId")
    if ep is not None and ep != vid:
        return "err", "identity_mismatch"
    mf = (pr.get("microformat") or {}).get("playerMicroformatRenderer") or {}
    desc = _text(mf.get("description")) or (pr.get("videoDetails") or {}).get("shortDescription")
    return "ok", {"license": license_from_data(data), "free_rule": free_use_rule(desc), "has_desc": bool(desc) or "description" in mf or "shortDescription" in (pr.get("videoDetails") or {})}


# ---------------------------------------------------------------- 상태 갱신 (실패해도 확인된 기록을 지우지 않는다)
def observe(prev, result, now):
    """이전 기록 + 이번 결과 → 새 기록. 확인 실패는 과거에 확인된 값을 유지하고 오류 표시만 붙인다"""
    rec = dict(prev) if prev else {"license": "unknown", "unknown_reason": "never_verified", "free_use": 0, "fail_count": 0, "miss_count": 0}
    rec["attempted_at"] = iso(now)
    kind, val = result
    if kind == "err":
        rec["fail_count"] = int(rec.get("fail_count", 0)) + 1
        rec["error"] = val
        return rec
    rec["error"] = None
    rec["fail_count"] = 0
    today = iso(now)[:10]   # checked_at = 라이선스 증거를 마지막으로 '새로 확인한' 날, attempted_at = 마지막 시도 시각. 과거 증거를 유지할 때는 checked_at 을 올리지 않는다
    lic = val["license"]
    if lic in ("cc_by", "standard"):
        rec.update(license=lic, miss_count=0, checked_at=today)
        rec.pop("unknown_reason", None)
    elif lic == "unrecognized":
        rec.update(license="unknown", unknown_reason="unrecognized", miss_count=0, checked_at=today)
    elif prev and prev.get("license") in ("cc_by", "standard"):   # 확인됐던 표기가 이번에 안 보임
        rec["miss_count"] = int(prev.get("miss_count", 0)) + 1
        if rec["miss_count"] >= MARKER_MISS_LIMIT:
            rec.update(license="unknown", unknown_reason="no_marker", checked_at=today)
        else:
            rec["error"] = "marker_missing"   # 지난 확인 기준으로 유지(checked_at 은 과거 그대로)하고 오래된 값 표시
    else:
        rec.update(license="unknown", unknown_reason="no_marker", miss_count=0, checked_at=today)   # 표기가 없다고 표준으로 보지 않는다
    if val["has_desc"]:
        rec["free_use"] = 1 if val["free_rule"] else 0
        rec["free_rule"] = val["free_rule"]
        rec["free_checked_at"] = today
        if not val["free_rule"]:
            rec.pop("free_rule", None)
    elif rec.get("free_use"):
        rec["error"] = rec.get("error") or "description_missing"   # 설명을 못 읽었으면 이전 판정과 그 증거 날짜(free_checked_at)를 유지
        rec.setdefault("free_checked_at", (prev or {}).get("checked_at"))
    return rec


# ---------------------------------------------------------------- 저장·내보내기
def load_store(path=STORE):
    """없으면 빈 저장소. 손상된 파일은 덮어쓰지 않도록 예외를 낸다"""
    if not os.path.exists(path):
        return {"schema": SCHEMA, "updated": "", "items": {}}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or not isinstance(d.get("items"), dict):
        raise ValueError("data/video_licenses.json 형식이 올바르지 않아요")
    return d


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def save_store(store, path=STORE):
    _atomic_write(path, json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True))


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ERR_CODES = {"blocked", "identity_mismatch", "unavailable", "no_initial_data", "network", "http_error", "marker_missing", "description_missing"}
UNK_REASONS = {"never_verified", "no_marker", "unrecognized"}


def export_item(rec):
    """화면용 최소 필드만 (허용 값 목록으로 걸러서 원문·이메일 등이 새어 나가지 않게 한다)"""
    lic = rec.get("license") if rec.get("license") in ("cc_by", "standard", "unknown") else "unknown"
    out = {"l": lic}
    if lic == "unknown":
        out["u"] = rec.get("unknown_reason") if rec.get("unknown_reason") in UNK_REASONS else "never_verified"
    if rec.get("free_use") and rec.get("free_rule") in ("en_video", "ko_video", "ja_video"):
        out["f"] = rec["free_rule"]
    if isinstance(rec.get("checked_at"), str) and DATE_RE.match(rec["checked_at"]):
        out["c"] = rec["checked_at"]
    fc = rec.get("free_checked_at") or rec.get("checked_at")
    if "f" in out and isinstance(fc, str) and DATE_RE.match(fc):
        out["fc"] = fc   # 무료 사용 문구를 마지막으로 확인한 날 (라이선스 확인일과 다를 수 있다)
    err = rec.get("error")
    if err in ERR_CODES:
        out["e"] = err
        if out.get("c"):
            out["s"] = 1   # 확인된 기록이 있는데 이번 확인은 실패 → 지난 확인 기준
    return out


def export_js(store, inventory_ids, out=OUT):
    """저장소 → web/video_licenses.js. 입력 목록을 못 읽은 경우에는 기록을 잘라내지 않고 모두 내보낸다"""
    items = {i: export_item(r) for i, r in sorted(store["items"].items()) if not inventory_ids or i in inventory_ids}
    scope = {"inventory": len(inventory_ids) if inventory_ids else len(items), "checked": sum(1 for v in items.values() if "c" in v),
             "cc_by": sum(1 for v in items.values() if v["l"] == "cc_by"), "standard": sum(1 for v in items.values() if v["l"] == "standard"),
             "free_use": sum(1 for v in items.values() if "f" in v), "stale": sum(1 for v in items.values() if v.get("s"))}
    payload = {"schema": SCHEMA, "updated": store.get("updated", ""), "scope": scope, "items": items}
    _atomic_write(out, "window.VIDEO_LICENSES=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    return scope


# ---------------------------------------------------------------- 대상 고르기 (새 영상 먼저, 그 다음 오래된 확인 순)
def retry_delay(fail_count):
    return timedelta(hours=min(RETRY_BASE_H * 2 ** max(fail_count - 1, 0), RETRY_MAX_H))


def is_due(rec, now):
    at = parse_iso(rec.get("attempted_at"))
    if at is None:
        return True
    if int(rec.get("fail_count", 0)) > 0:
        return now >= at + retry_delay(int(rec["fail_count"]))
    if rec.get("error") == "marker_missing":
        return now >= at + timedelta(days=1)   # 표기가 한 번 안 보인 영상은 빨리 다시 확인한다
    return now >= at + timedelta(days=RECHECK_DAYS.get(rec.get("license"), 30))


def pick_targets(inventory, items, limit, now):
    """새 영상(기록 없음) → 그 다음 시도한 지 가장 오래된 기록 순. 재확인 몫을 일부 남겨 오래된 영상도 계속 돈다"""
    oldest = sorted((i for i in inventory if i not in items), key=lambda i: inventory[i] or "")   # first_seen 오름차순 (모르면 가장 오래된 쪽)
    fresh = oldest
    due = sorted((i for i in inventory if i in items and is_due(items[i], now)), key=lambda i: items[i].get("attempted_at") or "")
    reserve = min(len(due), max(limit // 5, 1) if limit >= 5 else 0)
    budget = max(limit - reserve, 0)
    newest_n = (budget + 1) // 2   # 새 영상 몫의 절반은 최신부터, 절반은 가장 오래된 것부터 → 오래된 재고가 새 영상에 밀려 굶지 않는다
    take_fresh = oldest[::-1][:newest_n]
    for i in oldest:
        if len(take_fresh) >= budget:
            break
        if i not in take_fresh:
            take_fresh.append(i)
    rest = limit - len(take_fresh)
    return take_fresh + due[:rest], len(fresh), len(due)


# ---------------------------------------------------------------- 수집
def fetch_one(vid, fetch=discover.get, sleep=time.sleep, tries=3):
    """네트워크 오류는 지수 백오프로 재시도. 반환은 parse_watch 와 같은 ('ok'|'err', ...)"""
    code = "network"
    for k in range(tries):
        try:
            return parse_watch(fetch("https://www.youtube.com/watch?v=" + vid), vid)
        except Exception as e:   # urllib 의 HTTPError/URLError/timeout 등 모든 네트워크 실패
            status = getattr(e, "code", None)
            if status in (404, 410):
                return "err", "unavailable"
            code = "blocked" if status in (403, 429) else "http_error" if status else "network"
            if k < tries - 1:
                sleep((8 if status == 429 else 1.5) * 2 ** k + random.random())
    return "err", code


def run(limit, workers, max_seconds, fetch=discover.get, sleep=time.sleep, now_fn=now_utc, web_dir=WEB, store_path=STORE, out_path=OUT):
    store = load_store(store_path)   # 손상 시 예외 → 아무것도 덮어쓰지 않는다
    inv = load_inventory(web_dir)
    now = now_fn()
    targets, n_fresh, n_due = pick_targets(inv, store["items"], limit, now)
    print(f"입력 영상 {len(inv)}개 · 기록 {len(store['items'])}개 · 새 영상 {n_fresh}개 · 재확인 대상 {n_due}개 → 이번에 {len(targets)}개 확인")
    deadline, done, fails_in_row, aborted = time.monotonic() + max_seconds, 0, 0, ""
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for s in range(0, len(targets), workers * 2):
                if time.monotonic() > deadline:
                    aborted = "시간 제한"
                    break
                chunk = targets[s:s + workers * 2]
                for vid, res in zip(chunk, ex.map(lambda v: fetch_one(v, fetch, sleep), chunk)):
                    store["items"][vid] = observe(store["items"].get(vid), res, now_fn())
                    done += 1
                    fails_in_row = fails_in_row + 1 if res[0] == "err" and res[1] in ("blocked", "network", "http_error") else 0
                    if done % SAVE_EVERY == 0:
                        store["updated"] = iso(now_fn()); save_store(store, store_path)
                if fails_in_row >= CIRCUIT_FAILS:
                    aborted = "연속 실패(차단 의심)"
                    break
                sleep(0.3)
    finally:   # 중간에 멈춰도 확인한 만큼은 저장·내보낸다
        if done:
            store["updated"] = iso(now_fn())
        save_store(store, store_path)
        scope = export_js(store, set(inv), out_path)
    print(f"확인 {done}개" + (f" (중단: {aborted})" if aborted else "") + f" · 확인된 영상 {scope['checked']}개 / CC BY {scope['cc_by']} · 무료 사용 문구 {scope['free_use']} · 지난 확인 기준 {scope['stale']}")
    return scope


def main():
    ap = argparse.ArgumentParser(description="영상별 라이선스 상태 수집")
    ap.add_argument("--limit", type=int, default=300, help="이번 실행에서 확인할 영상 수 (기본 300)")
    ap.add_argument("--workers", type=int, default=4, help="동시 요청 수 (기본 4, 최대 8)")
    ap.add_argument("--max-seconds", type=int, default=1500, help="이 시간이 지나면 새 요청을 멈추고 저장 (기본 1500초)")
    ap.add_argument("--export-only", action="store_true", help="네트워크 없이 data/video_licenses.json 에서 web/video_licenses.js 만 다시 만든다")
    a = ap.parse_args()
    try:
        if a.export_only:
            store = load_store()
            scope = export_js(store, set(load_inventory()))
            print(f"내보내기만: 확인된 영상 {scope['checked']}개 / CC BY {scope['cc_by']} · 무료 사용 문구 {scope['free_use']}")
        else:
            run(max(a.limit, 0), min(max(a.workers, 1), 8), max(a.max_seconds, 1))
    except (OSError, ValueError) as e:   # 손상된 저장소 등: 데이터를 건드리지 않고 알린다
        print("라이선스 수집 중단:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
