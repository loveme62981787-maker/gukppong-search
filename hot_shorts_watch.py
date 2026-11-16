# -*- coding: utf-8 -*-
"""여행·체험·해외반응 쇼츠 채널과 '터진 쇼츠'를 한국·일본·대만(채널 소재 국가)별로 모아 web/hot_shorts.js 로 저장

    python hot_shorts_watch.py                 시드 채널(hot_shorts_seeds.json) 수집 → hot_shorts_store.json + web/hot_shorts.js
    python hot_shorts_watch.py --dry           저장 없이 요약만 출력
    python hot_shorts_watch.py --export-only   네트워크 없이 저장분으로 web/hot_shorts.js 만 다시 만든다
    python hot_shorts_watch.py --discover      검색(공식 API search.list, 호출당 100 유닛)으로 후보 채널을 찾아 같은 검증을 돌리고 hot_shorts_candidates.json 에 요약만 저장

근거 (모두 코드 상수 CRITERIA 에서 나오고, 화면 문구도 이 값을 그대로 읽는다):
- 채널 정보·구독자·국가·최근 업로드 20개 이상·조회수: 공식 YouTube Data API v3 (channels / playlistItems / videos). 환경변수 YOUTUBE_API_KEY 또는 GOOGLE_API_KEY (값은 출력·저장하지 않는다)
- Shorts 실제 확인 신호: 채널 /shorts 탭 페이지의 shortsLockupViewModel 에 그 영상 ID 가 들어 있는지(onTap.innertubeCommand.reelWatchEndpoint.videoId).
  길이(3분 이하)만으로는 확정하지 않는다. 탭 첫 페이지에 없다는 것만으로 '쇼츠 아님'을 확정하지 않는다(고정·오래된 영상은 첫 페이지에 안 나올 수 있다) → unknown(보류).
  '쇼츠 아님'은 길이가 3분을 넘는 경우에만 확정한다(Shorts 는 3분 이하).
- 최근 표본(fetch_n) 전체의 확인 결과는 membership_cache(영상ID → 쇼츠 여부·확인일, 비공개 원문 없음)로 채널별 저장한다. 터진 영상만 저장하면 클라우드에서 탭이 막힐 때 표본 비율이 무너진다.
- 클라우드에서 탭이 막히면 이전 확인 결과(membership_cache)를 보존하고 새 영상은 보류로 둔다. 어떤 실패도 기존 저장분을 지우지 않는다.
- 채널 소개문(예: 명상음악)이 아니라 실제 업로드가 기준이다. '쇼츠만 올리는 채널'이라고 영구 단정하지 않고 '최근 표본 기준'으로만 표시한다.
- 국가는 '영상이 다루는 대상국' 우선: 시드의 country_override > country_hint(country_basis=seed_manual) > 채널 snippet.country(등록 국가). 등록 국가가 미국 등 제3국이어도 시드 지정이 이긴다.
- 구독자 대비 배수는 실제 views/subs 를 표시한다. 선별에만 분모 최소 1000 을 쓰는 별도 필드(sub_multiple_floor)를 쓴다. 조회수 min_abs_views 이상이면 배수와 무관하게 터진 쇼츠로 본다.
- 시드의 exclude=true(주제 무관 잡학·유머 채널)는 수집·표시에서 뺀다. 영상 제목의 주제 키워드 적중은 topic_hits 로 보조 신호만 남긴다(자동 배제하지 않는다).
- 편집·해외반응 채널(kind=reaction_edit)의 영상은 벤치마킹 참고용일 뿐 재사용 가능한 원본이 아니다. CC BY 같은 라이선스 판정과는 독립이다(이 파일은 라이선스를 판단하지 않는다).
표준 라이브러리만 사용한다.
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(BASE, "hot_shorts_seeds.json")
STORE = os.path.join(BASE, "hot_shorts_store.json")
CANDIDATES = os.path.join(BASE, "hot_shorts_candidates.json")
OUT = os.path.join(BASE, "web", "hot_shorts.js")
KST = timezone(timedelta(hours=9))
SCHEMA = 1
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 기준 상수: 화면 문구(web/hot_shorts_view.js)는 내보낸 이 값을 그대로 읽는다
CRITERIA = {
    "sample_n": 20,             # 최근 업로드 표본 개수(uploads playlist 의 최신순). 20개 미만이면 쇼츠중심 판정을 하지 않는다
    "fetch_n": 50,              # 터진 쇼츠 후보로 읽는 최근 업로드 최대 개수
    "center_ratio": 0.9,        # 표본 중 Shorts 확인 비율이 이 이상이면 '쇼츠 중심'
    "min_views": 100000,        # 터진 쇼츠 최소 조회수
    "min_sub_multiple": 3.0,    # 구독자 대비 배수 (조회수 / 구독자) 이 이상이거나
    "min_abs_views": 1000000,   # 이 조회수 이상이면 배수와 무관하게 터진 쇼츠 (대형 채널·전부 대박 채널 보정)
    "sub_floor": 1000,          # 선별용 구독자 분모 최소값 (표시하는 구독자 대비 배수는 실제 views/subs)
    "min_median_multiple": 2.0,  # 표본 중앙값 대비 배수가 이 이상 (표본 중 Shorts 확인 영상이 min_median_sample 개 이상일 때만 계산)
    "min_median_sample": 5,
    "max_per_channel": 12,      # 채널당 표시하는 터진 쇼츠 상한
}
COUNTRIES = {"KR": "한국", "JP": "일본", "TW": "대만"}
KINDS = ("travel_original", "reaction_edit", "unverified")   # unverified: 원본 여부를 확인하지 못함 (원본으로 쓰지 않는다)
SHORTS_MAX_SEC = 180   # Shorts 길이 상한(3분)
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CH_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


def today():
    return datetime.now(KST).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- 공식 API
def api_key():
    return os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""


class ApiError(Exception):
    pass


def api_get(path, params, tries=3):
    """공식 API 호출. 실패 메시지에 키가 새지 않게 항상 가린다"""
    key = api_key()
    if not key:
        raise ApiError("API 키 없음 (YOUTUBE_API_KEY 또는 GOOGLE_API_KEY)")
    url = "https://www.googleapis.com/youtube/v3/" + path + "?" + urllib.parse.urlencode(dict(params, key=key))
    last = ""
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (400, 401, 403, 404):
                break   # 재시도해도 같은 결과 (키·권한·쿼터)
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
        time.sleep(1.5 * (i + 1))
    raise ApiError(f"{path} 실패: {last}")


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fetch_channels(ids):
    out = {}
    for part in chunks(list(ids), 50):
        r = api_get("channels", {"part": "snippet,statistics,contentDetails", "id": ",".join(part)})
        for it in r.get("items", []):
            st = it.get("statistics", {})
            out[it["id"]] = {
                "title": it["snippet"].get("title", ""),
                "handle": it["snippet"].get("customUrl", ""),
                "country": it["snippet"].get("country", ""),
                "subs": None if st.get("hiddenSubscriberCount") or "subscriberCount" not in st else int(st["subscriberCount"]),
                "video_count": int(st["videoCount"]) if "videoCount" in st else None,
                "uploads": it.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""),
            }
    return out


def fetch_upload_ids(playlist_id, n):
    ids, token = [], ""
    while len(ids) < n:
        p = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": min(50, n - len(ids))}
        if token:
            p["pageToken"] = token
        r = api_get("playlistItems", p)
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", []) if ID_RE.match(i.get("contentDetails", {}).get("videoId", ""))]
        token = r.get("nextPageToken", "")
        if not token:
            break
    return ids[:n]


def iso_sec(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return None
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def fetch_videos(ids):
    out = {}
    for part in chunks(list(ids), 50):
        r = api_get("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(part)})
        for it in r.get("items", []):
            st = it.get("statistics", {})
            out[it["id"]] = {
                "id": it["id"],
                "title": it["snippet"].get("title", ""),
                "published_at": it["snippet"].get("publishedAt", ""),
                "views": int(st["viewCount"]) if "viewCount" in st else None,
                "duration_sec": iso_sec(it.get("contentDetails", {}).get("duration")),
            }
    return out


# ---------------------------------------------------------------- 공개 /shorts 탭
def http_text(url, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise ApiError(f"페이지 읽기 실패: {type(last).__name__}")


def parse_shorts_page(html):
    """/shorts 탭 HTML 에서 shortsLockupViewModel 을 읽어 [{id, title, views_text}] (화면 순서). 구조를 못 읽으면 None (본문은 출력·저장하지 않는다)"""
    m = re.search(r"ytInitialData\s*=\s*", html or "")
    if not m:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html, m.end())
    except ValueError:
        return None
    found, seen = [], set()

    def walk(o):
        if isinstance(o, dict):
            s = o.get("shortsLockupViewModel")
            if isinstance(s, dict):
                vid = (((s.get("onTap") or {}).get("innertubeCommand") or {}).get("reelWatchEndpoint") or {}).get("videoId")
                if isinstance(vid, str) and ID_RE.match(vid) and vid not in seen:
                    seen.add(vid)
                    om = s.get("overlayMetadata") or {}
                    found.append({"id": vid, "title": ((om.get("primaryText") or {}).get("content") or ""), "views_text": ((om.get("secondaryText") or {}).get("content") or "")})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    return found or None   # 0개는 '쇼츠 없음'의 증거가 아니라 읽기 실패와 구분되지 않는다 → 증거 부족


def fetch_shorts_tab(channel_id):
    try:
        return parse_shorts_page(http_text(f"https://www.youtube.com/channel/{channel_id}/shorts"))
    except ApiError:
        return None


# ---------------------------------------------------------------- 판정 (네트워크 없음: 회귀 테스트 대상)
def classify_membership(videos, tab, prev):
    """videos: 최신순 영상 dict 목록(id, duration_sec). tab: /shorts 탭 항목 목록 또는 None. prev: 이전 확인 {id: {short, checked}}.
    반환 {id: (short, signal)}: True(탭에 있음) / False(길이 3분 초과) / None(증거 부족).
    탭 첫 페이지에 없다는 것만으로는 False 를 확정하지 않는다 (고정·오래된 영상은 안 나올 수 있다)"""
    in_tab = {t["id"] for t in tab} if tab else set()
    out = {}
    for v in videos:
        d = v.get("duration_sec")
        if v["id"] in in_tab:
            out[v["id"]] = (True, "shorts_tab")
        elif d is not None and d > SHORTS_MAX_SEC:
            out[v["id"]] = (False, "too_long")
        else:
            p = (prev or {}).get(v["id"])
            out[v["id"]] = (p["short"], "kept") if p and p.get("short") in (True, False) else (None, "pending")
    return out


def sample_stats(sample, members):
    """최근 표본(최신순 앞 sample_n 개)의 Shorts 확인 통계. 표본이 부족하면 쇼츠중심 판정을 하지 않는다 (False)"""
    n = len(sample)
    confirmed = sum(1 for v in sample if members.get(v["id"], (None,))[0] is True)
    not_short = sum(1 for v in sample if members.get(v["id"], (None,))[0] is False)
    pending = n - confirmed - not_short
    known = confirmed + not_short
    ratio = confirmed / n if n else 0.0
    enough = n >= CRITERIA["sample_n"]
    return {
        "sample_n": n, "sample_shorts": confirmed, "sample_not_short": not_short, "sample_pending": pending,
        "shorts_ratio": round(ratio, 3), "sample_known": known,
        "shorts_ratio_known": round(confirmed / known, 3) if known else None,   # 보류 제외 비율 (참고용, 쇼츠 중심 판정에는 쓰지 않는다)
        "shorts_centered": bool(enough and ratio >= CRITERIA["center_ratio"]),
        "all_shorts_strict": bool(enough and confirmed == n),   # 표본 전부 확인됨 (최근 기준일 뿐, 영구 단정 아님)
    }


def median_of(sample, members):
    vals = [v["views"] for v in sample if members.get(v["id"], (None,))[0] is True and v.get("views") is not None]
    if len(vals) < CRITERIA["min_median_sample"]:
        return None
    return statistics.median(vals)


def sub_multiples(views, subs):
    """(실제 views/subs, 선별용 views/max(subs, sub_floor)). 구독자 비공개·0 이면 둘 다 None"""
    if views is None or not subs:
        return None, None
    return round(views / subs, 2), round(views / max(subs, CRITERIA["sub_floor"]), 2)


def is_hot(views, subs, median):
    """(터짐 여부, 실제 구독자 대비 배수, 중앙값 대비 배수). 선별은 CRITERIA 그대로 (분모 최소값·절대 조회수 포함)"""
    sub_m, floor_m = sub_multiples(views, subs)
    med_m = round(views / median, 2) if views is not None and median else None   # median 0/None 은 분모 예외 방어
    ok = views is not None and views >= CRITERIA["min_views"] and (
        views >= CRITERIA["min_abs_views"]
        or (floor_m is not None and floor_m >= CRITERIA["min_sub_multiple"])
        or (med_m is not None and med_m >= CRITERIA["min_median_multiple"]))
    return ok, sub_m, med_m


TOPIC_WORDS = ("외국인", "한국", "일본", "대만", "台灣", "台湾", "外國人", "外国人", "日本", "韓國", "韓国", "korea", "japan", "taiwan", "foreigner", "reaction", "反應", "反応", "體驗", "体験", "旅行", "travel", "visit")


def topic_hit(title):
    t = (title or "").lower()
    return any(w.lower() in t for w in TOPIC_WORDS)


def build_channel(seed, info, videos, tab, prev_channel, checked):
    """채널 한 개의 기록. videos 는 최신순 전체(fetch_n). 반환 dict(channel + hot videos)"""
    prev_members = {v["id"]: v for v in (prev_channel or {}).get("videos", [])}
    prev_flags = {i: {"short": v.get("short"), "checked": v.get("short_checked")} for i, v in prev_members.items() if v.get("short") in (True, False)}
    for i, f in ((prev_channel or {}).get("membership_cache") or {}).items():   # 표본 전체의 이전 확인 결과 (터진 영상만이 아니라) → 탭이 막혀도 표본 통계가 이어진다
        if isinstance(f, dict) and f.get("short") in (True, False):
            prev_flags[i] = {"short": f["short"], "checked": f.get("checked")}
    for i, f in ((prev_channel or {}).get("flags") or {}).items():   # 예전 형식(flags): 확정된 쇼츠(True)만 이어받는다
        if f is True:
            prev_flags.setdefault(i, {"short": True, "checked": (prev_channel or {}).get("checked")})
    members = classify_membership(videos, tab, prev_flags)
    sample = videos[:CRITERIA["sample_n"]]
    st = sample_stats(sample, members)
    median = median_of(sample, members)
    country, basis = (info.get("country") or "").upper(), "channel_country"
    for k in ("country_override", "country_hint"):   # 영상이 다루는 대상국(시드 지정)이 등록 국가보다 우선
        if seed.get(k) in COUNTRIES:
            country, basis = seed[k], "seed_manual"
            break
    topic_hits = sum(1 for v in sample if topic_hit(v.get("title")))
    hot, pending_hot = [], 0
    for v in videos:
        short, signal = members[v["id"]]
        ok, sub_m, med_m = is_hot(v.get("views"), info.get("subs"), median)
        if not ok:
            continue
        if short is not True:
            pending_hot += 1 if short is None else 0   # 터질 만한 조회수지만 쇼츠 증거 부족 → 목록에 넣지 않고 개수만 센다
            continue
        old = prev_members.get(v["id"], {})
        when = ((prev_flags.get(v["id"]) or {}).get("checked") or old.get("short_checked") or (prev_channel or {}).get("checked") or checked) if signal == "kept" else checked   # 보존한 값은 이번 확인일이 아니라 이전 확인일
        hot.append({
            "id": v["id"], "title": v.get("title", ""), "published": (v.get("published_at") or "")[:10], "views": v["views"],
            "duration_sec": v.get("duration_sec"), "sub_multiple": sub_m, "sub_multiple_floor": sub_multiples(v["views"], info.get("subs"))[1], "median_multiple": med_m,
            "topic_hit": topic_hit(v.get("title")),
            "short": True, "short_signal": signal, "short_checked": when,
            "checked": when,
        })
    hot.sort(key=lambda x: -x["views"])
    hot = hot[:CRITERIA["max_per_channel"]]
    fetched = {v["id"] for v in videos}
    for old in (prev_channel or {}).get("videos", []):   # 최근 업로드 창에서 밀려난 기존 터진 쇼츠는 그대로 보존 (조회수 갱신만 멈춤)
        if old["id"] not in fetched and len(hot) < CRITERIA["max_per_channel"] and old.get("short") is True:
            hot.append(dict(old, short_signal="kept"))
    rec = {
        "id": seed["id"], "title": info.get("title", ""), "handle": info.get("handle", ""), "country": country, "country_basis": basis,
        "kind": seed.get("kind") if seed.get("kind") in KINDS else "unverified", "note": seed.get("note", ""),
        "subs": info.get("subs"), "median_views": int(median) if median else None, "checked": checked, "tab_checked": bool(tab),
        "pending_hot": pending_hot, "topic_hits": topic_hits, "user_reference": bool(seed.get("user_reference")), **st, "videos": hot,
        "membership_cache": {i: {"short": m[0], "checked": (prev_flags.get(i) or {}).get("checked") or checked if m[1] == "kept" else checked}
                             for i, m in members.items() if m[0] in (True, False)},
    }
    return rec


def merge_failed(prev_channel, seed, reason, checked):
    """수집이 실패한 채널: 이전 기록을 그대로 두고 실패 사유만 덧붙인다. 이전 기록이 없으면 보류 기록"""
    if prev_channel:
        return dict(prev_channel, last_error=reason, last_error_at=checked)
    return {"id": seed["id"], "title": "", "handle": "", "country": seed.get("country_hint", ""), "country_basis": "seed_manual", "kind": seed.get("kind") if seed.get("kind") in KINDS else "unverified",
            "note": seed.get("note", ""), "subs": None, "median_views": None, "checked": None, "tab_checked": False, "pending_hot": 0, "sample_n": 0, "sample_shorts": 0,
            "sample_not_short": 0, "sample_pending": 0, "shorts_ratio": 0.0, "shorts_centered": False, "all_shorts_strict": False, "user_reference": bool(seed.get("user_reference")), "videos": [], "last_error": reason, "last_error_at": checked}


def collect_channel(seed, prev_channel, checked, infos, tab_fetch=fetch_shorts_tab):
    cid = seed["id"]
    info = infos.get(cid)
    if not info or not info.get("uploads"):
        return merge_failed(prev_channel, seed, "채널 정보를 읽지 못함", checked)
    try:
        ids = fetch_upload_ids(info["uploads"], CRITERIA["fetch_n"])
        vm = fetch_videos(ids)
    except ApiError as e:
        return merge_failed(prev_channel, seed, str(e), checked)
    videos = [vm[i] for i in ids if i in vm]   # playlist 순서 = 최신순
    tab = tab_fetch(cid)
    return build_channel(seed, info, videos, tab, prev_channel, checked)


# ---------------------------------------------------------------- 저장·내보내기
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except (OSError, json.JSONDecodeError):
        return default


def js_safe(obj):
    """<script> 안에서도 안전한 JSON: 닫는 태그·HTML 주석을 만들 수 있는 문자를 이스케이프한다"""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def export(store, path=OUT, exclusions=None):
    # Argon 검토 후 확인한 주제 무관 채널·영상은 재수집되어도 공개 목록에서 제외한다.
    if exclusions is None:
        exclusions = load_json(os.path.join(BASE, "hot_shorts_exclusions.json"), {})
    channels = sorted(store.get("channels", {}).values(), key=lambda c: (c.get("country", ""), -(c.get("subs") or 0)))
    out_ch, out_v = [], []
    for c in channels:
        if c["id"] in exclusions.get("channels", {}):
            continue
        ch = {k: v for k, v in c.items() if k not in ("videos", "flags", "membership_cache")}
        visible = [v for v in c.get("videos", []) if v["id"] not in exclusions.get("videos", {})]
        ch["hot_n"] = len(visible)
        out_ch.append(ch)
        for v in visible:
            out_v.append(dict(v, channel_id=c["id"], country=c.get("country", "")))
    payload = {"schema": SCHEMA, "updated": store.get("updated", ""), "criteria": CRITERIA, "countries": COUNTRIES, "channels": out_ch, "videos": out_v}
    with open(path, "w", encoding="utf-8") as f:
        f.write("window.HOT_SHORTS=" + js_safe(payload) + ";\n")
    return len(out_ch), len(out_v)


def load_seeds(path=SEEDS):
    seeds = load_json(path, [])
    ok, seen = [], set()
    for s in seeds:
        if isinstance(s, dict) and CH_RE.match(s.get("id", "")) and s["id"] not in seen and not s.get("exclude"):   # exclude: 주제 무관 잡학·유머 채널
            seen.add(s["id"])
            ok.append(s)
    return ok


def extra_excluded(path=SEEDS):
    return [s["id"] for s in load_json(path, []) if isinstance(s, dict) and s.get("exclude") and CH_RE.match(s.get("id", ""))]


def run(seeds, store, checked, infos=None, tab_fetch=fetch_shorts_tab):
    """시드 전체를 수집해 store 를 갱신해 돌려준다 (네트워크 접근은 infos/tab_fetch 로 주입 가능)"""
    channels = dict(store.get("channels", {}))
    for cid in [c for c in extra_excluded()]:
        channels.pop(cid, None)
    if infos is None:
        try:
            infos = fetch_channels([s["id"] for s in seeds])
        except ApiError as e:
            print("채널 정보 조회 실패, 기존 저장분 유지:", e)
            infos = {}
    for s in seeds:
        channels[s["id"]] = collect_channel(s, channels.get(s["id"]), checked, infos, tab_fetch)
    return {"schema": SCHEMA, "updated": checked, "channels": channels}


def summary(store):
    rows = []
    for c in store["channels"].values():
        rows.append(f"  {c.get('country') or '?'} {c.get('handle') or c['id']} 구독 {c.get('subs')} 표본 {c.get('sample_shorts')}/{c.get('sample_n')} 쇼츠중심={c.get('shorts_centered')} 전부={c.get('all_shorts_strict')} 터진 {len(c.get('videos', []))}" + (f" [오류: {c['last_error']}]" if c.get("last_error") else ""))
    return "\n".join(rows)


# ---------------------------------------------------------------- 후보 발굴 (선택 실행)
DISCOVER_QUERIES = {
    "KR": ["외국인 한국 여행 체험 쇼츠", "외국인 한국 친절 반응 shorts", "foreigner Korea experience shorts", "외국인 한국 시골 체험 shorts", "foreigners reaction Korea kindness shorts"],
    "JP": ["외국인 일본 여행 체험 쇼츠", "外国人 日本 体験 反応 ショート", "外国人 日本 親切 感動 shorts", "foreigner Japan experience shorts", "海外の反応 日本 旅行 ショート"],
    "TW": ["外國人 台灣 體驗 反應 shorts", "外國人 台灣 人情味 感動 shorts", "foreigner Taiwan experience shorts", "外國人 來台灣 旅遊 驚訝 shorts", "外國人 台灣 夜市 反應"],
}
SEARCH_LANG = {"KR": "ko", "JP": "ja", "TW": "zh-Hant"}


def discover(checked, max_per_query=25):
    """search.list 로 후보 채널 ID 를 모아(쿼리당 100 유닛) 같은 검증을 돌리고 요약만 저장한다. 시드는 자동으로 바꾸지 않는다"""
    seen = {}
    for cc, qs in DISCOVER_QUERIES.items():
        for q in qs:
            try:
                r = api_get("search", {"part": "snippet", "q": q, "type": "video", "videoDuration": "short", "order": "viewCount", "maxResults": max_per_query,
                                       "regionCode": cc, "relevanceLanguage": SEARCH_LANG[cc]})
            except ApiError as e:
                print("검색 실패:", e)
                continue
            for it in r.get("items", []):
                cid = it["snippet"].get("channelId", "")
                if CH_RE.match(cid):
                    e = seen.setdefault(cid, {"queries": [], "cc": cc})
                    e["queries"].append(q)
    known = {s["id"] for s in load_seeds()}
    cand = [{"id": c} for c in seen if c not in known]
    infos = fetch_channels([c["id"] for c in cand]) if cand else {}
    out = []
    for c in cand:
        info = infos.get(c["id"])
        if not info:
            continue
        # 등록 국가가 비었거나 제3국이어도 검색 지역(대상국)이 근거이므로 country_hint 로 쓴다 (수동 확인 전 후보일 뿐)
        seed = {"id": c["id"], "kind": "unverified", "country_hint": seen[c["id"]]["cc"]}
        rec = collect_channel(seed, None, checked, infos)
        out.append({k: rec[k] for k in ("id", "title", "handle", "country", "subs", "sample_n", "sample_shorts", "shorts_ratio", "shorts_centered", "all_shorts_strict", "pending_hot")}
                   | {"hot_n": len(rec["videos"]), "queries": seen[c["id"]]["queries"][:3]})
    out.sort(key=lambda r: (-r["hot_n"], -(r["subs"] or 0)))
    with open(CANDIDATES, "w", encoding="utf-8") as f:
        json.dump({"checked": checked, "criteria": CRITERIA, "candidates": out}, f, ensure_ascii=False, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--export-only", action="store_true")
    ap.add_argument("--discover", action="store_true")
    a = ap.parse_args()
    store = load_json(STORE, {})
    if a.export_only:
        print("채널 %d개 · 터진 쇼츠 %d개 내보냄" % export(store))
        return 0
    if not api_key():
        print("API 키가 없어 이번 수집은 건너뜁니다 (기존 데이터 유지)")
        return 0
    checked = today()
    if a.discover:
        found = discover(checked)
        print(f"후보 {len(found)}개 검증 → hot_shorts_candidates.json")
        for r in found[:30]:
            print(f"  {r['country']} {r['handle'] or r['id']} 구독 {r['subs']} 표본쇼츠 {r['sample_shorts']}/{r['sample_n']} 터진 {r['hot_n']}")
        return 0
    seeds = load_seeds()
    if not seeds:
        print("시드 채널이 없습니다:", SEEDS)
        return 0
    new = run(seeds, store, checked)
    print(summary(new))
    if a.dry:
        return 0
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    print("채널 %d개 · 터진 쇼츠 %d개 저장" % export(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
