# -*- coding: utf-8 -*-
"""12분 이상 롱폼 여행·체험·외국인 반응 영상 수집 (한국·일본·대만) → longform_exp_store.json, web/longform_exp.js

    python longform_watch.py                   공식 API 검색(실행당 쿼리 최대 12개) → 저장 + 화면 파일
    python longform_watch.py --dry             저장 없이 결과만 출력
    python longform_watch.py --export-only     저장분으로 화면 파일만 다시 만든다 (네트워크 없음)
    python longform_watch.py --report-dir DIR  국가별 이전/새 ID 개수 보고서(JSON)를 DIR 에 쓴다 (비공개 폴더용)

기존 전체 수집(수 시간)과 따로 도는 작은 경로다. 기준: 길이 720초 이상, 조회수 하한 없음, Shorts 제외.
- 나라·주제는 제목으로만 판정한다. 제목에서 보이는 근거(외국인 단어, 한국어 지역명)는 '추정'으로만 저장한다 (lf_basis).
  채널 정보나 검색 결과만으로 외국인·제작자 국적을 확정하지 않는다. 설명글 원문은 저장·공개하지 않는다.
- 이미 사이트(web/*.js 목록 파일)에 있는 영상 ID 는 새 영상으로 세지 않고 저장하지 않는다 (index.html 이 같은 ID 는 합친다).
- 6시간마다가 아니라 하루 2회 정도 돌리는 것을 전제로, 검색 쿼리는 국가별 풀에서 돌아가며 4개씩 고른다 (search.list 100유닛 × 12).
- API 쿼터가 없으면 공개 검색 페이지 파서(experience_watch.search)로 대신한다 (이 경우 게시일은 추정하지 않고 비운다).
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

import hot_shorts_watch as hs
from hot_shorts_watch import ApiError, api_get, api_key, chunks, iso_sec, js_safe, load_store_strict, StoreCorrupt, write_atomic  # noqa: F401

BASE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE, "longform_exp_store.json")
OUT = os.path.join(BASE, "web", "longform_exp.js")
KST = timezone(timedelta(hours=9))
SCHEMA = 1
MIN_SEC = 720            # 12분
MAX_QUERIES = 12         # 실행당 search.list 호출 상한
PER_COUNTRY = 4          # 국가별 하루 쿼리 수 (3국 × 4 = 12)
COUNTRY_KO = {"KR": "한국", "JP": "일본", "TW": "대만"}
LANG = {"KR": "ko", "JP": "ja", "TW": "zh-Hant"}
# 사이트가 영상 목록으로 읽는 파일 (이미 있는 ID 판정용). 점수·알림 기록처럼 목록이 아닌 파일은 제외
SITE_LISTS = ["videos", "experience", "viral", "japan_topics", "global_topics", "global_topics_jp", "topic_candidates", "reference", "benchmark", "alerts",
              "taiwan_exp", "kr_regional", "cc_videos", "calltoon", "kr_news"]

# 검색 풀 (q, 길이 구간). medium=4~20분, long=20분 초과 — 12분 이상을 모두 덮으려고 섞는다
POOL = {
    "KR": [("foreigner first time Korea travel vlog", "medium"), ("foreigners Korea trip experience", "long"), ("외국인 한국 여행 체험", "medium"), ("외국인 한국 시골 체험", "long"),
           ("tourist Korea local food experience", "medium"), ("foreigners react Korea kindness", "medium"), ("외국인 한국 반응 친절", "long"), ("American visits Korea first time", "long"),
           ("foreigner Korean convenience store subway first time", "medium"), ("外国人 韓国 旅行 初めて", "medium"), ("外國人 韓國 旅行 體驗", "medium"), ("foreigner Jeju Busan travel vlog", "long")],
    "JP": [("foreigner first time Japan travel vlog", "medium"), ("tourist Japan local experience", "long"), ("外国人 日本 旅行 体験", "medium"), ("外国人 日本 初めて 感動", "long"),
           ("외국인 일본 여행 체험", "medium"), ("후쿠오카 도쿄 여행 브이로그", "long"), ("오사카 교토 여행 브이로그", "medium"), ("foreigners react Japan hospitality", "medium"),
           ("海外の反応 日本 旅行", "medium"), ("日本 旅行 外國人 體驗", "long"), ("Japan countryside ryokan onsen foreigner vlog", "long"), ("일본 소도시 현지 체험 일상", "medium")],
    "TW": [("foreigner first time Taiwan travel vlog", "medium"), ("tourist Taiwan night market experience", "long"), ("外國人 台灣 體驗 第一次", "medium"), ("老外 台灣 旅遊 感動", "long"),
           ("외국인 대만 여행 체험", "medium"), ("타이베이 대만 여행 브이로그", "long"), ("단수이 지우펀 대만 여행 브이로그", "medium"), ("foreigners love Taiwan reaction", "medium"),
           ("外国人 台湾 旅行 体験", "medium"), ("台灣 外國人 人情味 小吃", "long"), ("Taiwan Taipei Kaohsiung Tainan travel foreigner vlog", "long"), ("대만 현지 체험 일상 한달살기", "medium")],
}

COUNTRY_RE = {
    "KR": re.compile(r"korea|korean|seoul|busan|jeju|한국|서울|부산|제주|韓國|韓国|한옥|hanok", re.I),
    "JP": re.compile(r"japan|japanese|tokyo|osaka|kyoto|fukuoka|hokkaido|okinawa|일본|도쿄|오사카|교토|후쿠오카|삿포로|오키나와|日本|東京|大阪|京都|福岡|北海道|沖縄", re.I),
    "TW": re.compile(r"taiwan|taipei|kaohsiung|tainan|taichung|대만|타이완|타이베이|가오슝|단수이|지우펀|台灣|台湾|臺灣|台北|臺北|高雄|台南|台中|夜市", re.I),
}
TRAVEL_RE = re.compile(r"travel|trip|vlog|tour|visit|experience|food|eating|street food|night market|hotel|ryokan|onsen|local|first time|stay|living|여행|브이로그|체험|맛집|먹방|투어|일상|한달살기|한 달 살기|"
                       r"旅行|旅遊|旅游|體驗|体験|体験|夜市|小吃|初めて|感動|感动|人情味|vlog", re.I)
FOREIGN_RE = re.compile(r"foreigner|tourist|first time|american|british|canadian|australian|european|indian|filipino|brazilian|외국인|외국 |미국인|유럽인|外國人|外国人|老外|外籍|外國遊客|外国人観光客|海外の反応|海外反応|"
                        r"海外の人|外國夫妻|reacts?\b|reaction|react to", re.I)
# 정치·뉴스·잡학·음악·대중문화 리뷰는 배제 (주제 무관)
NOISE_RE = re.compile(r"\bnews\b|breaking|election|president|politic|trump|biden|\bwar\b|attack|crime|murder|earthquake|lyrics|\bmv\b|official video|playlist|\bost\b|album|"
                      r"north korea|북한|podcast|dating|documentary|facts? about|did you know|unknown facts|explained|history of|k-?drama|\bdrama\b|anime|movie|netflix|뉴스|속보|정치|대통령|선거|사건|사고|잡학|상식|가사|드라마|영화|예능|"
                      r"ニュース|政治|選挙|雑学|歌詞|ドラマ|映画|新聞|政治|選舉|冷知識|歌詞|電影|戲劇", re.I)
HANGUL_RE = re.compile(r"[가-힣]{2,}")
KANA_RE = re.compile(r"[぀-ヿ]")


def classify(title):
    """제목 하나로 (나라 코드, 근거) 를 정한다. 근거는 모두 '추정'이다. 맞지 않으면 None.
    - 나라 신호가 정확히 한 나라여야 한다 (섞이면 제외)
    - 여행·체험 단어 필수, 뉴스·정치·잡학·음악·드라마 제목은 제외
    - 외국인 신호('foreign_title') 또는 한국어 제목+일본·대만 지역명('ko_region': 한국인 제작자의 현지 체험 추정). 한국 소재는 외국인 신호가 있어야 한다"""
    t = title or ""
    hit = [c for c, r in COUNTRY_RE.items() if r.search(t)]
    if len(hit) != 1 or NOISE_RE.search(t) or not TRAVEL_RE.search(t):
        return None
    c = hit[0]
    if FOREIGN_RE.search(t):
        return c, "foreign_title"
    if c in ("JP", "TW") and HANGUL_RE.search(t) and not KANA_RE.search(t):
        return c, "ko_region"
    return None


def site_ids(base=BASE):
    """사이트 목록 파일에 이미 있는 영상 ID 집합 (이 수집기의 파일은 제외)"""
    ids = set()
    for name in SITE_LISTS:
        p = os.path.join(base, "web", name + ".js")
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                ids.update(re.findall(r'"id":\s*"([A-Za-z0-9_-]{11})"', f.read()))
    return ids


def fetch_details(ids):
    out = {}
    for part in chunks(list(ids), 50):
        r = api_get("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(part)})
        for it in r.get("items", []):
            st = it.get("statistics", {})
            sn = it.get("snippet", {})
            out[it["id"]] = {"id": it["id"], "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""), "channel_id": sn.get("channelId", ""),
                             "published": (sn.get("publishedAt") or "")[:10], "views": int(st["viewCount"]) if "viewCount" in st else None,
                             "duration_sec": iso_sec(it.get("contentDetails", {}).get("duration")), "live": sn.get("liveBroadcastContent", "none")}
    return out


def pick_queries(cursor, n_per=PER_COUNTRY, pool=POOL):
    """국가별로 cursor 위치부터 n_per 개를 돌아가며 고른다. (job 목록, 새 cursor)"""
    jobs, new = [], dict(cursor or {})
    for cc in ("KR", "JP", "TW"):
        qs, start = pool[cc], int((cursor or {}).get(cc, 0)) % len(pool[cc])
        for k in range(min(n_per, len(qs))):
            q, dur = qs[(start + k) % len(qs)]
            jobs.append((cc, q, dur))
        new[cc] = (start + n_per) % len(qs)
    return jobs[:MAX_QUERIES], new


def search_api(job):
    cc, q, dur = job
    r = api_get("search", {"part": "id", "q": q, "type": "video", "videoDuration": dur, "maxResults": 50, "regionCode": cc, "relevanceLanguage": LANG[cc]})
    return [it["id"]["videoId"] for it in r.get("items", []) if hs.ID_RE.match(it.get("id", {}).get("videoId", ""))]


def search_public(job):
    """쿼터 소진 시 대체: 공개 검색 페이지 파서. 길이·조회수는 페이지 표기, 게시일은 추정하지 않는다"""
    import experience_watch as ew
    out = []
    for v in ew.search(job[1], ew.SORTS[0]):
        out.append(dict(v, published="", live="none"))
    return out


def run(store, site, today, api_fn=search_api, detail_fn=fetch_details, public_fn=search_public, cursor=None):
    """검색 → 판정 → (새 저장분, 보고). site 는 사이트에 이미 있는 ID 집합"""
    jobs, new_cursor = pick_queries(store.get("cursor") if cursor is None else cursor)
    items = dict(store.get("items", {}))
    rep = {cc: {"prev_store": sum(1 for v in items.values() if v.get("lf_country") == cc), "on_site_already": 0, "added": [], "queries": 0, "errors": 0} for cc in COUNTRY_KO}
    quota_out = False
    found = {}   # id -> (cc, query, 공개 파서 항목 or None)
    for job in jobs:
        cc = job[0]
        rep[cc]["queries"] += 1
        got = None
        if not quota_out:
            try:
                got = [(i, None) for i in api_fn(job)]
            except ApiError as e:
                rep[cc]["errors"] += 1
                print(f"  경고: 검색 실패({job[1]}): {e}", file=sys.stderr)
                if "403" in str(e):
                    quota_out = True   # 키·쿼터 문제: 남은 쿼리는 공개 파서로 넘긴다
        if got is None and (quota_out or not api_key()):
            try:
                got = [(v["id"], v) for v in public_fn(job) if hs.ID_RE.match(v.get("id", ""))]
            except Exception as e:  # noqa: BLE001
                rep[cc]["errors"] += 1
                print(f"  경고: 공개 검색도 실패({job[1]}): {type(e).__name__}", file=sys.stderr)
        for i, pub in got or []:
            found.setdefault(i, (cc, job[1], pub))
    fresh = [i for i in found if i not in items]
    todo = []
    for i in fresh:
        if i in site:
            rep[found[i][0]]["on_site_already"] += 1   # 이미 사이트에 있음: 새 영상으로 세지 않는다
        else:
            todo.append(i)
    det = {}
    if todo and not quota_out:
        try:
            det = detail_fn(todo)
        except ApiError as e:
            print("  경고: 영상 상세 조회 실패 (이번에는 새로 저장하지 않음):", e, file=sys.stderr)
    for i in todo:
        cc_q, q, pub = found[i]
        v = det.get(i) or (pub if pub and not det else None)
        if not v or v.get("live") not in ("none", None) or not isinstance(v.get("duration_sec"), int) or v["duration_sec"] < MIN_SEC:
            continue
        cls = classify(v.get("title"))
        if not cls:
            continue
        cc, basis = cls
        items[i] = {"id": i, "title": v["title"], "channel": v.get("channel", ""), "channel_id": v.get("channel_id", ""), "subs": None, "views": v.get("views"),
                    "country": COUNTRY_KO[cc], "section": "longform_exp", "length": None, "duration_sec": v["duration_sec"], "published": v.get("published", ""),
                    "first_seen": today, "lf_country": cc, "lf_basis": basis, "lf_query": q}
        rep[cc]["added"].append(i)
    out = {"schema": SCHEMA, "updated": today, "collected_at": hs.now_utc(), "cursor": new_cursor, "items": items}
    return out, rep


def merge_stores(remote, ours, base=hs._NO_BASE):
    """원격 저장분(remote)에 이번 수집분(ours)을 합친다: 영상 ID 합집합(조회수·정보는 더 늦게 관측한 쪽), 검색 커서는 3-way.
    base = 이번 수집을 시작한 시점의 저장분. 원격 커서가 base 와 같으면(그 사이 아무도 전진 안 함) 우리 커서를 채택하고, 원격이 따로 전진했으면 원격을 보존한다"""
    def stamp(d):
        return str((d or {}).get("collected_at") or (d or {}).get("updated") or "")
    items = dict((remote or {}).get("items", {}))
    ours_newer = hs._later(stamp(ours), stamp(remote))
    for i, v in (ours or {}).get("items", {}).items():
        cur = items.get(i)
        if cur is None:
            items[i] = v
        elif str(v.get("first_seen", "9999")) < str(cur.get("first_seen", "9999")):
            items[i] = dict(v, first_seen=v["first_seen"])   # 첫 발견일은 더 이른 쪽
        elif v.get("views") is not None and ours_newer:
            items[i] = dict(cur, views=v["views"])
    upd = max((x for x in ((remote or {}).get("updated"), (ours or {}).get("updated")) if x), default="")
    base_cursor = hs._NO_BASE if base is hs._NO_BASE else ((base or {}).get("cursor") or None)
    cursor = hs.merge_cursor((remote or {}).get("cursor") or None, (ours or {}).get("cursor") or None, base_cursor) or {}
    out = {"schema": SCHEMA, "updated": upd, "cursor": cursor, "items": items}
    ca = max((x.get("collected_at") for x in (remote, ours) if x and x.get("collected_at")), default=None)
    if ca:
        out["collected_at"] = ca
    return out


def export(store, path=OUT):
    rows = sorted(store.get("items", {}).values(), key=lambda v: (v.get("first_seen", ""), v.get("views") or 0), reverse=True)
    write_atomic(path, "window.LONGFORM_EXP=" + js_safe(rows) + ";\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--export-only", action="store_true")
    ap.add_argument("--report-dir", default="")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        store = load_store_strict(STORE)
    except StoreCorrupt as e:
        print("오류:", e, file=sys.stderr)
        return 1
    if a.export_only:
        print("롱폼 %d개 내보냄" % export(store))
        return 0
    if not api_key():
        print("API 키가 없어 공식 API 는 쓰지 않습니다 (공개 검색 파서만 시도)")
    today = datetime.now(KST).strftime("%Y-%m-%d")
    new, rep = run(store, site_ids(), today)
    for cc, r in rep.items():
        print(f"{COUNTRY_KO[cc]}: 쿼리 {r['queries']} 오류 {r['errors']} · 이전 저장 {r['prev_store']} · 사이트에 이미 있음 {r['on_site_already']} · 새로 반영 {len(r['added'])}")
    if a.report_dir:
        os.makedirs(a.report_dir, exist_ok=True)
        rp = os.path.join(a.report_dir, f"longform_report_{today}.json")
        write_atomic(rp, json.dumps({"date": today, "min_sec": MIN_SEC, "countries": {COUNTRY_KO[c]: {"prev_store_count": r["prev_store"], "on_site_already": r["on_site_already"], "new_count": len(r["added"]),
                                                                                                    "new_ids": r["added"]} for c, r in rep.items()}}, ensure_ascii=False, indent=1))
    if a.dry:
        return 0
    if all(r["errors"] >= r["queries"] > 0 for r in rep.values()):
        print("::warning::모든 검색이 실패했습니다 — 기존 저장분을 그대로 둡니다", file=sys.stderr)
        return 0
    write_atomic(STORE, json.dumps(new, ensure_ascii=False, indent=1))
    print("롱폼 %d개 저장" % export(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
