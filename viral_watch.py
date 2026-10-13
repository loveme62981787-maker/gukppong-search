# -*- coding: utf-8 -*-
"""오래전에 올라왔어도 바이럴/화제가 된 한국·일본 방문·반응 영상을 찾아 web/viral.js 로 저장

    python viral_watch.py            검색 → web/viral.js
    python viral_watch.py --dry      저장 없이 요약만 출력

방식: 유튜브 검색을 '조회수순'으로 (전체 기간 / 올해) 정렬해서 읽고,
      조회수가 크거나(VIRAL_VIEWS 이상) 구독자 대비 조회수가 폭발한 영상만 남긴다.
      '사건/이슈'를 직접 알 수는 없어서, 조회수·구독자 대비 비율·화제성 단어로 추정한다.
discover.py / build_site.py 와 독립적으로 동작한다. (API 키 불필요, 표준 라이브러리만 사용)
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "viral.js")
STORE = os.path.join(BASE, "viral_store.json")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UNIT_H = {"s": 0, "m": 0, "h": 1, "d": 24, "w": 168, "mo": 720, "y": 8760}

VIRAL_VIEWS = 300_000      # 이 조회수 이상이면 화제 영상
RATIO_VIEWS = 50_000       # 이 조회수 이상이면서
RATIO_MIN = 8              # 조회수 / 구독자 가 이 값 이상이면 (작은 채널의 대박) 화제 영상
MAX_ITEMS = 400
BUZZ_WORDS = ["논란", "화제", "난리", "충격", "viral", "controversy", "shocked", "went viral", "goes viral", "trending", "반응", "reaction"]

# (나라, 아이콘, 검색어, 제목에 반드시 들어가야 하는 단어)
COUNTRIES = {
    "한국": (["foreigners visiting Korea first time", "first time in Korea vlog", "foreigner reacts to Korea", "Korea travel vlog",
              "tourist in Seoul reaction", "foreigner living in Korea", "외국인 한국 방문 반응", "외국인이 놀란 한국", "외국인 한국 여행 후기",
              "해외반응 한국", "국뽕 해외반응", "foreigners shocked by Korea"],
             ["korea", "korean", "seoul", "busan", "jeju", "한국", "서울", "부산", "제주", "k-pop", "kpop", "k-culture", "한류"]),
    "일본": (["foreigners visiting Japan first time", "first time in Japan vlog", "foreigner reacts to Japan", "Japan travel vlog",
              "tourist in Tokyo reaction", "foreigner living in Japan", "외국인 일본 방문 반응", "일본 여행 외국인 반응", "해외반응 일본",
              "foreigners shocked by Japan"],
             ["japan", "japanese", "tokyo", "osaka", "kyoto", "일본", "도쿄", "오사카", "교토", "日本", "東京"]),
}
SORTS = ["CAMSAhAB", "CAMSBAgFEAE"]  # 조회수순(전체 기간) / 조회수순(올해)


def get(url, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"})
            return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def initial_data(page):
    return json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S).group(1))


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def parse_count(text, word):
    m = re.search(r"([\d.,]+)\s*([KMB]?)\s*" + word, text or "")
    return int(float(m.group(1).replace(",", "")) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2)]) if m else None


def age_hours(text):
    m = re.search(r"(\d+)\s*(mo|y|w|d|h|m|s)", (text or "").replace("month", "mo"))
    return int(m.group(1)) * UNIT_H[m.group(2)] if m else None


def search(query, sp):
    for i in range(3):
        try:
            data = initial_data(get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=" + sp))
            break
        except AttributeError:
            time.sleep(2 * (i + 1))
    else:
        return []
    out = []

    def f(o):
        v = o.get("videoRenderer")
        if not v:
            return
        try:
            run = v["ownerText"]["runs"][0]
            out.append({"id": v["videoId"], "title": "".join(r["text"] for r in v["title"]["runs"]), "channel": run["text"],
                        "channel_id": run["navigationEndpoint"]["browseEndpoint"]["browseId"],
                        "age_h": age_hours(v.get("publishedTimeText", {}).get("simpleText", "")),
                        "age_text": v.get("publishedTimeText", {}).get("simpleText", ""),
                        "length": v.get("lengthText", {}).get("simpleText", ""),  # 영상 길이 (예: 12:34), 라이브/쇼츠는 비어 있을 수 있음
                        "views": parse_count(v.get("viewCountText", {}).get("simpleText", ""), "views") or 0})
        except (KeyError, IndexError):
            pass
    walk(data, f)
    return out


def channel_subs(cid):
    try:
        return parse_count(get("https://www.youtube.com/channel/" + cid), "subscribers")
    except Exception:  # noqa: BLE001
        return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry" in sys.argv
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    store = {}
    if os.path.exists(STORE):
        try:
            with open(STORE, encoding="utf-8") as f:
                store = json.load(f)
        except (OSError, json.JSONDecodeError):
            store = {}
    found = {}
    for country, (queries, words) in COUNTRIES.items():
        n0 = len(found)
        for q in queries:
            for sp in SORTS:
                for v in search(q, sp):
                    t = v["title"].lower()
                    if v["age_h"] is None or v["views"] < RATIO_VIEWS or not any(w in t for w in words):
                        continue
                    if re.search(r"north korea|pyongyang|hotel review|top hotels|official (music )?video|lyrics|\bm/?v\b|full album|\bost\b|extended .*version", t):
                        continue
                    v["country"] = country
                    found.setdefault(v["id"], v)
                time.sleep(0.4)
        print(f"[{country}] 후보 {len(found) - n0}개 (조회수 {RATIO_VIEWS:,}+)")
    ids = sorted({v["channel_id"] for v in found.values()})
    with ThreadPoolExecutor(6) as ex:
        subs = dict(zip(ids, ex.map(channel_subs, ids)))
    items = []
    for v in found.values():
        s = subs.get(v["channel_id"])
        ratio = v["views"] / max(s or 1, 1)
        if v["views"] >= VIRAL_VIEWS or (s and ratio >= RATIO_MIN):
            buzz = any(w in v["title"].lower() for w in BUZZ_WORDS)
            items.append({"id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"], "subs": s,
                          "views": v["views"], "country": v["country"], "section": "viral", "viral": True, "buzz": buzz,
                          "age_text": v["age_text"], "length": v["length"], "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"),
                          "first_seen": store.get(v["id"], today)})
    items.sort(key=lambda x: x["views"], reverse=True)
    items = items[:MAX_ITEMS]
    print(f"화제 영상 {len(items)}개 (한국 {sum(i['country'] == '한국' for i in items)} / 일본 {sum(i['country'] == '일본' for i in items)})")
    if dry:
        for i in items[:25]:
            print(f"  {i['views']:>10,} 구독 {i['subs']} {i['age_text']:>14} {i['channel']} | {i['title'][:50]}")
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i["first_seen"] for i in items}, f, ensure_ascii=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.VIRAL=%s;\n" % json.dumps(items, ensure_ascii=False))
    print("저장: web/viral.js")


if __name__ == "__main__":
    main()
