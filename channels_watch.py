# -*- coding: utf-8 -*-
"""벤치마킹용 '비슷한 컨셉 채널' 찾기 → web/channels.js

    python channels_watch.py            채널 검색·분석 → web/channels.js 저장
    python channels_watch.py --dry      저장 없이 요약만 출력

동작
 1) seed_channels.txt 의 채널 이름을 유튜브에서 찾아 확정 (시작점)
 2) discover_queries 로 영상/채널을 검색해 비슷한 컨셉 채널을 더 발견
 3) 채널마다 최근 영상 15개(RSS)와 쇼츠 탭을 읽어 롱폼/숏폼 비율, 평균 조회수, 컨셉 일치도 계산
 4) 롱폼 위주 / 숏폼 위주 / 둘 다 로 분류

discover.py / build_site.py 와는 독립적으로 동작합니다. (API 키 불필요, 표준 라이브러리만 사용)
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(BASE, "seed_channels.txt")
OUT = os.path.join(BASE, "web", "channels.js")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}

# 내 채널 (결과에서 제외)
MY_CHANNELS = ["코리아탐방록", "코리아관찰기"]
# 컨셉 일치도 판단용 단어: 최근 영상 제목에 이 단어가 들어 있는 비율이 높을수록 비슷한 채널
CONCEPT_WORDS = ["해외반응", "해외 반응", "외국인", "국뽕", "한류", "외신", "극찬", "k-culture", "k-pop", "kpop", "한국 문화", "한국인", "대한민국", "korea",
                 "한국에", "한국이", "한국을", "한국의", "한국 "]
DISCOVER_QUERIES = ["해외반응 한국", "외국인 반응 한국", "국뽕 해외반응", "한국 칭찬 외신 반응", "외국인이 놀란 한국",
                    "한류 해외반응", "외국인 한국 여행 반응", "한국 문화 외국인 충격", "외신 한국 극찬", "한국 해외 반응 쇼츠",
                    "일본 반응 한국", "한국 vs 일본 외국인 반응", "foreigners react to Korea", "reaction to Korean culture",
                    "해외 네티즌 반응 한국", "국뽕 쇼츠"]
MAX_CHANNELS = 160
MIN_SCORE = 0.45  # 컨셉 일치도 최소값 (시드 채널은 무관하게 포함)


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


def search(query, sp):
    for i in range(3):  # 가끔 검색 결과 형식이 달라서 실패하므로 다시 시도
        try:
            return initial_data(get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=" + sp))
        except AttributeError:
            time.sleep(2 * (i + 1))
    raise RuntimeError("검색 결과를 읽지 못함")


def channel_search(name):
    """채널 이름으로 검색해 가장 위 채널 1개를 (id, 이름) 으로"""
    out = []

    def f(o):
        c = o.get("channelRenderer")
        if c:
            out.append((c["channelId"], c.get("title", {}).get("simpleText", "")))
    walk(search(name, "EgIQAg%3D%3D"), f)
    return out[0] if out else None


def resolve_handle(handle):
    """@핸들 로 채널 페이지를 열어 (id, 이름) 을 확정 (이름 검색보다 정확)"""
    page = get("https://www.youtube.com/" + urllib.parse.quote(handle))
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page) or re.search(r'"externalId":"(UC[\w-]{22})"', page)
    if not m:
        return None
    n = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    return m.group(1), (n.group(1) if n else handle)


def video_search_channels(query):
    """영상 검색 결과(관련도순 + 이번 달)에서 채널을 모은다"""
    found = {}
    for sp in ("EgIQAQ%3D%3D", "EgQIBBAB"):
        def f(o):
            v = o.get("videoRenderer")
            if v:
                try:
                    r = v["ownerText"]["runs"][0]
                    found[r["navigationEndpoint"]["browseEndpoint"]["browseId"]] = r["text"]
                except (KeyError, IndexError):
                    pass
        try:
            walk(search(query, sp), f)
        except Exception as e:  # noqa: BLE001
            print(f"  [검색 실패] {query}: {e}")
        time.sleep(0.4)
    return found


def analyze(cid, name, seed):
    """채널 1개 분석. 실패하면 None"""
    try:
        root = ET.fromstring(get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
    except Exception:  # noqa: BLE001
        return None
    vids = []
    for e in root.findall("a:entry", NS):
        st = e.find("m:group/m:community/m:statistics", NS)
        vids.append({"id": e.findtext("yt:videoId", "", NS), "title": e.findtext("a:title", "", NS),
                     "published": e.findtext("a:published", "", NS)[:10],
                     "views": int(st.get("views")) if st is not None and st.get("views") else 0})
    if not vids:
        return None
    try:
        shorts = set(re.findall(r'"reelWatchEndpoint":\{"videoId":"([\w-]{11})"', get(f"https://www.youtube.com/channel/{cid}/shorts")))
    except Exception:  # noqa: BLE001
        shorts = set()
    try:
        subs = parse_count(get(f"https://www.youtube.com/channel/{cid}"), "subscribers")
    except Exception:  # noqa: BLE001
        subs = None
    for v in vids:
        v["short"] = v["id"] in shorts
    n_short = sum(v["short"] for v in vids)
    ratio = n_short / len(vids)
    kind = "short" if ratio >= 0.7 else "long" if ratio <= 0.3 else "both"
    score = sum(any(w in v["title"].lower() for w in CONCEPT_WORDS) for v in vids) / len(vids)
    if score < MIN_SCORE and not seed:
        return None
    return {"id": cid, "name": name, "subs": subs, "type": kind, "short_n": n_short, "long_n": len(vids) - n_short,
            "score": round(score, 2), "avg_views": int(sum(v["views"] for v in vids) / len(vids)),
            "last_upload": max(v["published"] for v in vids), "seed": seed, "latest": vids[:4]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry" in sys.argv
    mine = {re.sub(r"\s+", "", n).casefold() for n in MY_CHANNELS}
    cands = {}  # id -> (name, seed)

    seeds = []
    if os.path.exists(SEEDS):
        with open(SEEDS, encoding="utf-8-sig") as f:
            seeds = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    for name in seeds:
        try:
            r = resolve_handle(name) if name.startswith("@") else channel_search(name)
        except Exception as e:  # noqa: BLE001
            print(f"[시드 실패] {name}: {e}")
            continue
        if r:
            cands[r[0]] = (r[1], True)
            print(f"[시드] {name} -> {r[1]} ({r[0]})")
        else:
            print(f"[시드 못 찾음] {name}")
        time.sleep(0.4)

    for q in DISCOVER_QUERIES:
        for cid, name in video_search_channels(q).items():
            cands.setdefault(cid, (name, False))
    cands = {k: v for k, v in cands.items() if re.sub(r"\s+", "", v[0]).casefold() not in mine}
    print(f"후보 채널 {len(cands)}개 (시드 {sum(1 for v in cands.values() if v[1])}개)")
    items = sorted(cands.items(), key=lambda kv: not kv[1][1])[:MAX_CHANNELS]  # 시드 우선
    with ThreadPoolExecutor(6) as ex:
        res = [r for r in ex.map(lambda kv: analyze(kv[0], kv[1][0], kv[1][1]), items) if r]
    res.sort(key=lambda c: (c["subs"] or 0), reverse=True)
    print(f"분석 완료: {len(res)}개 (롱폼 {sum(c['type'] == 'long' for c in res)} / 숏폼 {sum(c['type'] == 'short' for c in res)} / 둘 다 {sum(c['type'] == 'both' for c in res)})")
    if dry:
        for c in res[:40]:
            print(f"  {c['type']:5} 구독 {c['subs']} 일치 {c['score']} 평균조회 {c['avg_views']} {c['name']}")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.CH_UPDATED=%s;\nwindow.CHANNELS=%s;\n" % (
            json.dumps(datetime.now(KST).strftime("%Y-%m-%d %H:%M")), json.dumps(res, ensure_ascii=False)))
    print("저장: web/channels.js")


if __name__ == "__main__":
    main()
