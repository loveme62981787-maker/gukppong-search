# -*- coding: utf-8 -*-
"""외국인(대만 사람이 아닌 사람)이 대만을 여행·체험·경험하는 영상을 넓게 찾아 web/taiwan_exp.js 로 저장

    python taiwan_watch.py            검색 → web/taiwan_exp.js
    python taiwan_watch.py --dry      저장 없이 요약만 출력

방식: 영어·한국어·일본어·스페인어·프랑스어·태국어·베트남어·인도네시아어 검색어로 대만 지명이 제목에 있는 영상을 모은다 (관련도순·이번 달·조회수순).
제목에 대만 지명이 있고, 181초 이상이며, 지정학·뉴스·칩 산업 영상이 아닌 것만 남긴다. 외국인인지는 사이트(web/index.html)가 제목·채널 위치로 추정한다.
experience_watch.py 의 검색·파싱 함수를 재사용한다. (API 키 불필요, 표준 라이브러리만 사용)
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import experience_watch as ew

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "taiwan_exp.js")
STORE = os.path.join(BASE, "taiwan_exp_store.json")
KST = timezone(timedelta(hours=9))
MIN_SEC = 181
MAX_ITEMS = 4000
SORTS = ["EgIQAQ%3D%3D", "CAISBAgEEAE%3D", "CAMSAhAB"]   # 관련도순 / 이번 달 최신순 / 조회수순
# 사이트(index.html)의 TW_RE·NONTW_RE 와 같은 기준
TW_RE = re.compile(r"\btaiwan\b|taipei|kaohsiung|tainan|taichung|hualien|taitung|jiufen|shifen|alishan|sun moon lake|kenting|tamsui|danshui|ximending|shilin|raohe|台灣|臺灣|台湾|台北|高雄|台南|台中|花蓮|花莲|九份|대만|타이완|타이베이|가오슝|타이난|타이중|지우펀|đài loan|ไต้หวัน|taiw[aá]n|tai[wo]an|ta[iï]wan|taïwan", re.I)
NONTW_RE = re.compile(r"strait|invasion|\bpla\b|military|\btsmc\b|\bchips?\b|semiconductor|election|president|geopolit|\bwar\b|missile|tariff|trump|biden|\bnews\b|breaking|해협|침공|군사|반도체|선거|대통령|지정학|台海|兩岸|两岸|解放軍|選舉|總統|\bguerre\b|\bchine\b|conflit|\bkrieg\b|\bguerra\b|\bchina\b.{0,12}\b(vs|versus|conflict|threat)|politique|elecciones|presidente|militar|\bchiny\b|ukraine|война", re.I)
EXCLUDE_RE = re.compile(r"official (music )?video|lyrics|\bmv\b|full album|\bost\b|asmr|gameplay|walkthrough|trailer|react(s|ion)? to .*(song|mv|trailer)", re.I)

TOPICS_EN = ["night market", "street food", "MRT subway", "bubble tea", "Jiufen", "Shifen sky lantern", "Taipei 101", "Alishan", "Sun Moon Lake", "Kenting", "Tainan food", "Taichung",
             "Kaohsiung", "Hualien Taroko Gorge", "Taitung", "Beitou hot spring", "convenience store 7-Eleven", "scooter", "safe solo female", "cost of living", "moving to",
             "expat life", "teaching English", "breakfast", "temple", "lantern festival", "Din Tai Fung", "beef noodle soup", "high speed rail", "Yilan", "Penghu", "Taroko",
             "National Palace Museum", "Shilin night market", "Ximending", "Tamsui", "Elephant Mountain", "Cijin island", "Pingxi", "Lukang", "Taiwan vs", "hiking", "cycling around",
             "road trip", "motorcycle", "cafes", "hotel stay", "weekend", "day trip from Taipei", "foreigners react", "first impressions", "honest thoughts", "culture shock", "kindness of locals"]
LEAD_EN = ["Taiwan {t}", "Taiwan {t} vlog", "I visited Taiwan {t}", "first time in Taiwan {t}"]
QUERIES_OTHER = [
    "대만 여행 브이로그", "타이베이 여행", "대만 야시장", "지우펀 여행", "대만 3박4일", "대만 맛집 투어", "대만 편의점", "타이중 여행", "가오슝 여행", "대만 외국인 반응", "대만 한달살기", "대만 혼자 여행",
    "台湾旅行 vlog", "台北 食べ歩き", "台湾 夜市", "九份 旅行", "台湾 一人旅", "台湾 2泊3日", "台湾 コンビニ", "台中 旅行", "高雄 旅行", "台湾 初めて", "台湾 移住",
    "viaje a Taiwán vlog", "Taiwán qué ver", "mudarse a Taiwán", "voyage Taïwan vlog", "Taïwan que faire", "vivre à Taïwan", "เที่ยวไต้หวัน", "ไต้หวัน vlog", "du lịch Đài Loan", "Đài Loan vlog",
    "liburan ke Taiwan", "Taiwan vlog Indonesia", "Taiwan travel Filipino", "Taiwan trip Malaysia", "Taiwan Reise", "Tayvan gezisi", "Taiwan Indian vlog", "Taiwan travel Hindi", "Taiwan Telugu vlog",
]


def queries():
    qs = []
    for t in TOPICS_EN:
        for lead in LEAD_EN[:2] if t not in ("moving to",) else LEAD_EN[:1]:
            qs.append((lead.format(t=t), SORTS[:2]))
        qs.append(("Taiwan " + t + " foreigner", SORTS[:1]))
    for q in QUERIES_OTHER:
        qs.append((q, SORTS))
    qs += [("Taiwan travel vlog", SORTS), ("Taiwan trip first time", SORTS), ("Taipei travel vlog 2026", SORTS), ("Taiwan living abroad vlog", SORTS)]
    return qs


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
    qs = queries()

    def run(job):
        q, sorts = job
        out = []
        for sp in sorts:
            out += ew.search(q, sp)
        return out

    found = {}
    with ThreadPoolExecutor(4) as ex:
        for job, results in zip(qs, ex.map(run, qs)):
            for v in results:
                t = v["title"]
                if v["age_h"] is None or not TW_RE.search(t) or NONTW_RE.search(t) or EXCLUDE_RE.search(t):
                    continue
                if v["duration_sec"] is not None and v["duration_sec"] < MIN_SEC:
                    continue   # 쇼츠 제외 (길이를 모르면 유지)
                found.setdefault(v["id"], v)
    print(f"검색어 {len(qs)}개 → 후보 {len(found)}개")
    ids = sorted({v["channel_id"] for v in found.values()})
    with ThreadPoolExecutor(6) as ex:
        subs = dict(zip(ids, ex.map(ew.channel_subs, ids)))
    items = [{"id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"], "subs": subs.get(v["channel_id"]), "views": v["views"],
              "country": "대만", "section": "taiwan_exp", "age_text": v["age_text"], "length": v["length"], "duration_sec": v["duration_sec"],
              "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"), "first_seen": store.get(v["id"], today)} for v in found.values()]
    items.sort(key=lambda x: (x["first_seen"], x["views"]), reverse=True)
    items = items[:MAX_ITEMS]
    print(f"저장 대상 {len(items)}개")
    if dry:
        for i in items[:15]:
            print(f"  {i['length'] or '-':>8} 조회 {i['views']:>9,} {i['channel'][:18]} | {i['title'][:50]}")
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i["first_seen"] for i in items}, f, ensure_ascii=False)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.TAIWAN_EXP=%s;\n" % json.dumps(items, ensure_ascii=False))
    print("저장: web/taiwan_exp.js")


if __name__ == "__main__":
    main()
