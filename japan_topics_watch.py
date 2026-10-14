# -*- coding: utf-8 -*-
"""일본 영상 중 '아직 비어 있는데 터지는 주제' 4가지를 먼저 찾아 web/japan_topics.js 로 저장

    python japan_topics_watch.py            검색 → web/japan_topics.js
    python japan_topics_watch.py --dry      저장 없이 요약만 출력

주제 4가지 (기획 분석 기준, 중위 조회수와 평균 대비 배수):
  가족 첫 방일·서프라이즈 / 일식·첫입 리액션 / 이자카야·밤 술자리 / 접객·친절·배려
이미 포화된 주제(치안·심야, 철도·교통, 육아·아이, 제조업·자동차, 풍경·계절·온천, 편의점·가격)는 일부러 찾지 않는다.

TOPICS 가 주제 이름과 판별 규칙(정규식)의 기준이며, 사이트(web/index.html)도 japan_topics.js 안의 JP_TOPICS 를
그대로 써서 기존 영상까지 같은 기준으로 분류한다. 주제를 고치려면 여기만 고치면 된다.
experience_watch.py 의 검색·파싱 함수를 재사용한다. (API 키 불필요, 표준 라이브러리만 사용)
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import experience_watch as ew

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "japan_topics.js")
STORE = os.path.join(BASE, "japan_topics_store.json")
KST = timezone(timedelta(hours=9))
MIN_SEC = 181
MAX_ITEMS = 500

# 주제 이름 -> (판별 정규식(JS·파이썬 공통 문법만 사용, 대소문자 무시), 설명)
TOPICS = {
    "👨‍👩‍👧 가족 첫 방일·서프라이즈": (
        r"\bfamily\b(?!\s?mart)|\bparents?\b|\bmom\b|\bdad\b|\bmother\b|\bfather\b|grandparents?|grandma|grandpa|\bsurprise|first visit|"
        r"가족|부모님|엄마|아빠|어머니|아버지|서프라이즈|첫 방일|家族|サプライズ",
        "중위 9.5만 · 평균의 2.35배"),
    "🍣 일식·첫입 리액션": (
        r"sushi|ramen|wagyu|tempura|takoyaki|okonomiyaki|yakitori|udon|\bsoba\b|katsu|omakase|onigiri|japanese food|first bite|"
        r"first time (trying|eating|tasting)|try(ing)? japanese|taste test|일식|스시|초밥|라멘|와규|첫입|첫 입|먹방|寿司|ラーメン",
        "중위 7.4만 · 평균의 1.83배"),
    "🏮 이자카야·밤 술자리": (
        r"izakaya|이자카야|\bsake\b|사케|nomihodai|bar hopping|yokocho|golden gai|nightlife|night out|highball|하이볼|술집|술자리|居酒屋|飲み会|"
        r"drinking in (japan|tokyo|osaka)",
        "중위 4.7만 · 평균의 1.16배"),
    "🙇 접객·친절·배려": (
        r"omotenashi|hospitality|customer service|politeness|\bpolite\b|kindness|so kind|\bmanners\b|considerate|courtesy|lost (wallet|phone)|"
        r"lost and found|접객|친절|배려|오모테나시|서비스 정신|おもてなし",
        "중위 4만 · 평균의 1.00배"),
}
QUERIES = {
    "👨‍👩‍👧 가족 첫 방일·서프라이즈": [
        "family first time in Japan", "parents first time Japan reaction", "surprising my family with a Japan trip", "family trip Japan vlog",
        "bringing my parents to Japan", "grandparents first time Japan", "외국인 가족 첫 일본 방문", "일본 가족 여행 외국인 반응"],
    "🍣 일식·첫입 리액션": [
        "first time trying Japanese food reaction", "foreigners try Japanese food first time", "sushi first time reaction Japan",
        "ramen in Japan first time reaction", "wagyu first time Japan", "외국인 일본 음식 첫 입 반응", "외국인 스시 처음 먹어봄 일본"],
    "🏮 이자카야·밤 술자리": [
        "izakaya first time foreigner", "izakaya Japan night out foreigners", "Japanese bar hopping first time", "Golden Gai foreigners",
        "Omoide Yokocho foreigners", "Tokyo izakaya night drinking vlog", "nomihodai Japan foreigners", "외국인 일본 이자카야 체험"],
    "🙇 접객·친절·배려": [
        "Japanese hospitality foreigners shocked", "omotenashi foreigners reaction", "Japan customer service shocked tourist",
        "politeness in Japan foreigners reaction", "kindness of Japanese people tourist", "lost wallet Japan returned tourist",
        "외국인이 감동한 일본 친절", "일본 접객 서비스 외국인 반응"],
}
SORTS = ["EgIQAQ%3D%3D", "CAISBAgEEAE%3D", "CAMSAhAB"]  # 관련도순 / 이번 달 최신순 / 조회수순(전체 기간)
JP_WORDS = ["japan", "japanese", "tokyo", "osaka", "kyoto", "hokkaido", "fukuoka", "okinawa", "일본", "도쿄", "오사카", "교토", "日本", "東京", "大阪", "京都"]
KR_WORDS = ["korea", "seoul", "busan", "jeju", "k-pop", "kpop", "한국", "대한민국", "서울", "부산", "제주", "한류", "韓国"]
PATTERNS = {name: re.compile(rule, re.I) for name, (rule, _) in TOPICS.items()}


def topics_of(text):
    return [n for n, p in PATTERNS.items() if p.search(text)]


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
    for topic, queries in QUERIES.items():  # 주제 순서대로 먼저 찾는다
        n0 = len(found)
        for q in queries:
            for sp in SORTS:
                for v in ew.search(q, sp):
                    title = v["title"]
                    text = title + " " + v["channel"]
                    topics = topics_of(title)  # 주제는 제목만 보고 판별 (채널 이름의 Family/Dad 같은 단어로 오분류 방지)
                    if v["age_h"] is None or not topics or not any(w in text.lower() for w in JP_WORDS):
                        continue
                    if any(w in title.lower() for w in KR_WORDS):
                        continue  # 한국이 함께 나오는 영상은 일본 주제가 아니므로 제외
                    if v["duration_sec"] is not None and v["duration_sec"] < MIN_SEC:
                        continue  # 쇼츠 제외 (길이를 모르면 유지)
                    if re.search(r"official (music )?video|lyrics", text.lower()):
                        continue
                    v.update(country="일본", topics=topics)
                    found.setdefault(v["id"], v)
                time.sleep(0.4)
        print(f"[{topic}] 누적 {len(found)}개 (+{len(found) - n0})")
    ids = sorted({v["channel_id"] for v in found.values()})
    with ThreadPoolExecutor(6) as ex:
        subs = dict(zip(ids, ex.map(ew.channel_subs, ids)))
    items = [{"id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"], "subs": subs.get(v["channel_id"]),
              "views": v["views"], "country": "일본", "section": "jp_topic", "jp_topics": v["topics"],
              "age_text": v["age_text"], "length": v["length"], "duration_sec": v["duration_sec"],
              "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"), "first_seen": store.get(v["id"], today)}
             for v in found.values()]
    items.sort(key=lambda x: (x["first_seen"], x["views"]), reverse=True)
    items = items[:MAX_ITEMS]
    by_topic = {t: sum(t in i["jp_topics"] for i in items) for t in TOPICS}
    print(f"일본 주제 영상 {len(items)}개 {by_topic}")
    if dry:
        for i in items[:20]:
            print(f"  {','.join(i['jp_topics'])[:18]:18} {i['length'] or '-':>8} 조회 {i['views']:>9,} {i['channel']} | {i['title'][:45]}")
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i["first_seen"] for i in items}, f, ensure_ascii=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    topics_js = {n: {"rule": rule, "info": info} for n, (rule, info) in TOPICS.items()}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.JP_TOPICS=%s;\nwindow.JP_TOPIC_ITEMS=%s;\n" % (json.dumps(topics_js, ensure_ascii=False), json.dumps(items, ensure_ascii=False)))
    print("저장: web/japan_topics.js")


if __name__ == "__main__":
    main()
