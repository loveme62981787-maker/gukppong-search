"""CC BY 영상 새로 찾기 (표준 라이브러리만 사용, API 키 없음).

한국·일본·대만 여행/문화/음식 체험 주제를 YouTube 공개 검색의 'Creative Commons' 필터(sp=EgQQATAB)로 돌려 후보 영상을 모으고,
검색 결과는 CC 라고 믿지 않은 채 영상마다 watch 페이지를 license_watch.fetch_one/parse_watch 로 다시 확인한다. 확인된 CC BY 만 web/cc_videos.js 로 내보낸다.

저장: data/cc_candidates.json (후보 큐 + 검색 기록. 설명 원문·연락처 없음, 제목·채널 같은 공개 메타데이터만)
      data/video_licenses.json (license_watch 와 공유: 확인 결과 기록)  →  web/cc_videos.js (현재 CC BY 로 확인된 영상만)
실행: python cc_discover.py [--per-country N] [--max-candidates N] [--workers N] [--export-only]
설계 근거: docs/collab/2026-11-01-cc-discovery.md
차단(429/403/비정상 화면)이 보이면 즉시 멈춘다. 프록시·우회 없음.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import discover
import license_watch as lw

BASE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE, "data", "cc_candidates.json")
OUT = os.path.join(BASE, "web", "cc_videos.js")
SCHEMA = 1
CC_SP = "EgQQATAB"   # 검색 필터: 유형=동영상 + 기능=Creative Commons
MIN_SEC = 181
RETRY_H, RETRY_MAX_H = 6, 24 * 7
SEARCH_GAP_H = 20     # 같은 검색어를 다시 돌리기까지 최소 간격 (돌아가며 쓰므로 사실상 한 바퀴 후)

# 나라별 검색어 (외국인이 겪는 한국·일본·대만 여행/문화/음식 체험이 주제. 영어 위주)
QUERIES = {
    "한국": ["Korea travel vlog", "first time in Korea", "Seoul street food", "Busan trip", "Korean culture experience", "living in Korea foreigner", "Jeju island travel", "Korea convenience store food"],
    "일본": ["Japan travel vlog", "first time in Japan", "Tokyo street food", "Osaka food tour", "Kyoto trip", "Japanese culture experience", "living in Japan foreigner", "Japan convenience store food"],
    "대만": ["Taiwan travel vlog", "first time in Taiwan", "Taipei night market", "Taiwan street food", "Taiwan trip", "Taiwanese culture experience", "living in Taiwan foreigner", "Taiwan convenience store food"],
}
PLACE = {
    "한국": re.compile(r"korea|seoul|busan|jeju|incheon|gyeongju|hanok|k-?food|한국|서울|부산|제주|韓国|韓國|韩国", re.I),
    "일본": re.compile(r"japan|tokyo|osaka|kyoto|hokkaido|okinawa|fukuoka|nara\b|hiroshima|nagoya|shinjuku|shibuya|일본|도쿄|오사카|교토|日本|東京|大阪|京都", re.I),
    "대만": re.compile(r"taiwan|taipei|kaohsiung|tainan|taichung|hualien|jiufen|shifen|alishan|kenting|台灣|臺灣|台湾|台北|高雄|대만|타이베이", re.I),
}
# 여행·음식·문화 체험 신호 / 무관한 영상(음악·스톡·광고·뉴스·게임)
TOPIC_OK_RE = re.compile(r"travel|trip|vlog|visit|food|eat|eating|street|market|tour|first time|living|live in|moved|culture|experience|hotel|stay|hike|hiking|festival|temple|shrine|cafe|ramen|sushi|"
                         r"day in|days in|explor|walking|train|subway|여행|맛집|체험|旅行|食べ|体験|旅", re.I)
TOPIC_BAD_RE = re.compile(r"official (music )?video|lyrics?|\bmv\b|full album|\bost\b|no ?copyright|copyright[- ]free|royalty[- ]free|stock footage|background music|\bbgm\b|asmr|gameplay|walkthrough|"
                          r"trailer|slideshow|lofi|lo-fi|playlist|sponsored|\bad\b|news|breaking|election|military|\bwar\b|stocks?\b|crypto|tutorial|lesson", re.I)

BLOCK_ERRS = {"blocked", "network", "http_error"}


def now_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- 검색
def search_cc(query, get=discover.get):
    """CC 필터 검색 1페이지 → 후보 목록(공개 메타데이터만). 예외는 호출자가 차단으로 처리한다"""
    page = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=" + CC_SP)
    d = discover.initial_data(page)
    out = []

    def f(o):
        v = o.get("videoRenderer")
        if not v:
            return
        try:
            run = v["ownerText"]["runs"][0]
            length = (v.get("lengthText") or {}).get("simpleText")
            sec = discover.parse_duration(length)
            views = discover.parse_count(v.get("viewCountText", {}).get("simpleText", ""), "views")
            out.append({"id": v["videoId"], "title": "".join(r["text"] for r in v["title"]["runs"]), "channel": run["text"],
                        "channel_id": run["navigationEndpoint"]["browseEndpoint"]["browseId"], "views": views if views is not None else 0,
                        "length": length.strip() if sec is not None else None, "duration_sec": sec})
        except (KeyError, IndexError):
            pass
    discover.walk(d, f)
    return out


def topic_ok(c, country):
    """기본 주제 거름망: 길이 181초 이상 + 해당 나라 지명이 제목에 있고 + 여행/체험 신호가 있고 + 음악·스톡·광고 신호가 없을 것.
    외국인 여부는 판단하지 않는다 (알 수 없음으로 둔다)"""
    t = c.get("title") or ""
    sec = c.get("duration_sec")
    return (isinstance(sec, int) and sec >= MIN_SEC and bool(lw.ID_RE.match(c.get("id") or "")) and bool(PLACE[country].search(t))
            and bool(TOPIC_OK_RE.search(t)) and not TOPIC_BAD_RE.search(t))


# ---------------------------------------------------------------- 저장소
def empty_store():
    return {"schema": SCHEMA, "updated": "", "searches": {}, "items": {}}


def load_store(path=STORE):
    if not os.path.exists(path):
        return empty_store()
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or not isinstance(d.get("items"), dict) or not isinstance(d.get("searches"), dict):
        raise ValueError("data/cc_candidates.json 형식이 올바르지 않아요")
    return d


def save_store(store, path=STORE):
    lw._atomic_write(path, json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True))


# ---------------------------------------------------------------- 검색어 돌리기 (나라별 예산 + 가장 오래 안 쓴 검색어부터)
def pick_queries(store, per_country, now):
    picked = []
    for country, qs in QUERIES.items():
        def key(q):
            s = store["searches"].get(country + "|" + q) or {}
            return s.get("at") or ""
        due = [q for q in qs if (lw.parse_iso((store["searches"].get(country + "|" + q) or {}).get("at")) or datetime.min.replace(tzinfo=timezone.utc)) + timedelta(hours=SEARCH_GAP_H) <= now]
        picked += [(country, q) for q in sorted(due, key=key)[:max(per_country, 0)]]
    return picked


def is_due(item, now):
    """후보 재시도 시각: 실패 횟수만큼 6시간부터 2배씩 늦춘다"""
    at = lw.parse_iso(item.get("attempted_at"))
    if at is None or not item.get("fail_count"):
        return True
    return now >= at + timedelta(hours=min(RETRY_H * 2 ** (item["fail_count"] - 1), RETRY_MAX_H))


def add_candidates(store, found, country, query, lic_items, now, cap):
    """검색 결과를 주제 거름망에 통과시켜 최대 cap 개를 큐에 넣는다. 이미 아는 후보는 건드리지 않고(확인 상태 보존) 새 것만 센다"""
    new = []
    for c in found:
        if len(new) >= cap:
            break
        if c["id"] in store["items"] or not topic_ok(c, country):
            continue
        store["items"][c["id"]] = {"id": c["id"], "title": c["title"], "channel": c["channel"], "channel_id": c["channel_id"], "views": c["views"], "length": c["length"],
                                   "duration_sec": c["duration_sec"], "country": country, "first_seen": now.strftime("%Y-%m-%d"), "query": query,
                                   "status": "pending", "fail_count": 0}
        new.append(c["id"])
    return new


def apply_verdict(store, lic_store, vid, res, now):
    """확인 결과 반영. 실패는 pending 으로 두고 백오프, CC BY 가 아니면 rejected(공개 안 함). 라이선스 기록은 license_watch 와 같은 규칙(observe)으로 갱신한다"""
    it = store["items"][vid]
    it["attempted_at"] = lw.iso(now)
    lic_store["items"][vid] = lw.observe(lic_store["items"].get(vid), res, now)
    if res[0] == "err":
        it["fail_count"] = int(it.get("fail_count", 0)) + 1
        it["error"] = res[1]
        return
    it["fail_count"], it["error"] = 0, None
    it["status"] = "verified" if res[1]["license"] == "cc_by" else "rejected"


# ---------------------------------------------------------------- 내보내기 (현재 CC BY 로 기록된 영상만)
def export_js(store, lic_store, out=OUT):
    """검증 통과(status=verified)이고 라이선스 기록이 지금도 cc_by 인 영상만. 재확인에 실패해도 기록이 cc_by 로 남아 있으면 그대로 두고(화면이 '지난 확인 기준' 표시) 조용히 사라지지 않게 한다"""
    items = []
    for vid, it in sorted(store["items"].items(), key=lambda kv: kv[1].get("first_seen", ""), reverse=True):
        if it.get("status") != "verified" or (lic_store["items"].get(vid) or {}).get("license") != "cc_by":
            continue
        items.append({"id": vid, "title": it["title"], "channel": it["channel"], "channel_id": it["channel_id"], "views": it.get("views", 0), "length": it.get("length"),
                      "duration_sec": it.get("duration_sec"), "country": it["country"], "first_seen": it["first_seen"], "published": "", "sources": ["cc_discovery"],
                      "foreign": "unknown"})   # 외국인 여부는 확인하지 않았다
    lw._atomic_write(out, "window.CC_VIDEOS=" + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + ";\n")
    return len(items)


# ---------------------------------------------------------------- 실행
def run(per_country, max_candidates, workers, get=discover.get, fetch=discover.get, sleep=time.sleep, now_fn=now_utc,
        store_path=STORE, lic_path=lw.STORE, out_path=OUT, web_dir=lw.WEB):
    store, lic = load_store(store_path), lw.load_store(lic_path)
    now = now_fn()
    stopped, new_ids = "", []
    try:
        for country, q in pick_queries(store, per_country, now):
            try:
                found = search_cc(q, get)
            except Exception as e:   # 검색이 막히면 바로 멈춘다 (더 두드리지 않는다)
                stopped = f"검색 실패({getattr(e, 'code', None) or type(e).__name__}): 차단 의심"
                break
            store["searches"][country + "|" + q] = {"at": lw.iso(now_fn()), "found": len(found)}
            new_ids += add_candidates(store, found, country, q, lic["items"], now, max_candidates)
            sleep(2)
        if not stopped:
            todo = new_ids + [i for i, it in store["items"].items() if it["status"] == "pending" and i not in new_ids and is_due(it, now)]
            cap = max_candidates * len(QUERIES)
            todo = todo[:cap]
            blocks = 0
            with ThreadPoolExecutor(max_workers=min(max(workers, 1), 2)) as ex:
                for s in range(0, len(todo), 2):
                    chunk = todo[s:s + 2]
                    for vid, res in zip(chunk, ex.map(lambda v: lw.fetch_one(v, fetch, sleep), chunk)):
                        apply_verdict(store, lic, vid, res, now_fn())
                        blocks = blocks + 1 if res[0] == "err" and res[1] in BLOCK_ERRS else 0
                    if blocks >= 2:
                        stopped = "확인 중 차단 의심"
                        break
                    sleep(1)
    finally:   # 중간에 멈춰도 한 만큼 저장·내보낸다
        store["updated"] = lic["updated"] = lw.iso(now_fn())
        save_store(store, store_path)
        lw.save_store(lic, lic_path)
        n = export_js(store, lic, out_path)
        lw.export_js(lic, set(lw.load_inventory(web_dir)), lw.OUT if lic_path == lw.STORE else out_path + ".lic.js")
    st = {k: sum(1 for i in store["items"].values() if i["status"] == k) for k in ("pending", "verified", "rejected")}
    print(f"새 후보 {len(new_ids)}개: {new_ids} · 큐 {st} · 공개 CC BY {n}개" + (f" · 중단: {stopped}" if stopped else ""))
    return {"new": new_ids, "stopped": stopped, "exported": n, **st}


def main():
    ap = argparse.ArgumentParser(description="CC BY 영상 새로 찾기")
    ap.add_argument("--per-country", type=int, default=1, help="나라마다 이번에 돌릴 검색어 수 (기본 1)")
    ap.add_argument("--max-candidates", type=int, default=5, help="나라마다 새 후보 상한 (기본 5)")
    ap.add_argument("--workers", type=int, default=2, help="동시 확인 수 (기본 2, 최대 2)")
    ap.add_argument("--export-only", action="store_true", help="네트워크 없이 data → web/cc_videos.js 만 다시 만든다")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        if a.export_only:
            print(f"내보내기만: 공개 CC BY {export_js(load_store(), lw.load_store())}개")
        else:
            r = run(a.per_country, a.max_candidates, a.workers)
            return 2 if r["stopped"] else 0
    except (OSError, ValueError) as e:
        print("CC 탐색 중단:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
