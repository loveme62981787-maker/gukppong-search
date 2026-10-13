# -*- coding: utf-8 -*-
"""외국인이 한국·일본에서 '체험'하는 영상(야구장, 한복, 찜질방, 템플스테이 ...)을 찾아 web/experience.js 로 저장

    python experience_watch.py            검색 → web/experience.js
    python experience_watch.py --dry      저장 없이 요약만 출력

TOPICS 가 체험 종류와 판별 단어의 기준입니다. 사이트(web/index.html)도 이 목록(experience.js 안의 EXP_TOPICS)을
그대로 써서 기존 영상까지 같은 기준으로 분류하므로, 종류를 추가하려면 여기만 고치면 됩니다.
discover.py / build_site.py 와 독립적으로 동작합니다. (API 키 불필요, 표준 라이브러리만 사용)
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
OUT = os.path.join(BASE, "web", "experience.js")
STORE = os.path.join(BASE, "experience_store.json")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UNIT_H = {"s": 0, "m": 0, "h": 1, "d": 24, "w": 168, "mo": 720, "y": 8760}
MIN_SEC = 181      # 이 길이 미만(쇼츠)은 제외. 길이를 모르면 유지
MAX_ITEMS = 500

# 체험 종류: 이름 -> 제목에 들어 있으면 해당 체험으로 보는 단어(소문자)
TOPICS = {
    "⚾ 야구장": ["baseball", "kbo", "야구", "야구장", "야구장", "npb", "プロ野球", "野球"],
    "👘 한복·한옥": ["hanbok", "한복", "hanok", "한옥", "kimono", "着物", "기모노", "yukata", "유카타"],
    "♨️ 찜질방·온천": ["jjimjilbang", "jimjilbang", "찜질방", "sauna", "spa", "onsen", "온천", "温泉", "ryokan", "료칸", "public bath"],
    "🏯 사찰·템플스테이": ["temple stay", "templestay", "템플스테이", "buddhist temple", "사찰"],
    "🍳 요리·만들기 체험": ["cooking class", "kimchi making", "making kimchi", "김장", "쿠킹클래스", "요리 체험", "만들기 체험", "cooking lesson", "tteokbokki making", "pottery", "도자기", "ceramic"],
    "🎎 전통문화 체험": ["tea ceremony", "다도", "calligraphy", "서예", "traditional culture", "전통문화", "cultural experience", "문화 체험", "문화체험", "traditional performance", "gugak", "국악", "samulnori", "사물놀이"],
    "🎤 노래방·PC방": ["noraebang", "노래방", "karaoke", "pc bang", "pc방", "피시방", "internet cafe", "arcade", "게임센터"],
    "🥋 무예·스포츠": ["taekwondo", "태권도", "sumo", "스모", "相撲", "ssireum", "씨름", "hapkido", "martial art", "k-pop dance class", "dance class", "댄스 클래스"],
    "🎆 축제·콘서트": ["festival", "축제", "concert", "콘서트", "fan meeting", "팬미팅", "fireworks", "불꽃", "祭り", "firefly"],
    "🛒 시장·로컬": ["traditional market", "전통시장", "local market", "시장 체험", "street market", "수산시장", "fish market", "night market", "야시장"],
}
COUNTRY_WORDS = {"한국": ["korea", "korean", "seoul", "busan", "jeju", "한국", "서울", "부산", "제주", "k-pop", "kpop", "k-culture", "한류", "daegu", "incheon"],
                 "일본": ["japan", "japanese", "tokyo", "osaka", "kyoto", "일본", "도쿄", "오사카", "교토", "日本", "東京"]}
QUERIES = {
    "한국": ["foreigners baseball game Korea", "foreigner first time Korean baseball stadium", "foreigners hanbok experience Korea",
             "foreigners jjimjilbang first time", "foreigner temple stay Korea", "foreigners kimchi making Korea", "foreigners Korean cooking class",
             "foreigners noraebang Korea", "foreigner PC bang Korea", "foreigners taekwondo Korea", "foreigners traditional market Korea experience",
             "Korean cultural experience foreigners", "foreigners Korean festival experience", "foreigners tea ceremony Korea",
             "외국인 한국 문화 체험", "외국인 야구장 반응", "외국인 찜질방 체험", "외국인 템플스테이", "외국인 한복 체험", "외국인 김장 체험",
             "외국인 노래방 반응", "외국인 한국 전통시장"],
    "일본": ["foreigners sumo tournament Japan", "foreigner onsen first time Japan", "foreigners kimono experience Japan",
             "foreigner Japanese baseball game", "foreigners ryokan stay Japan", "foreigners Japanese festival experience", "외국인 일본 문화 체험"],
}
SORTS = ["EgIQAQ%3D%3D", "CAISBAgEEAE%3D"]  # 관련도순 / 이번 달 최신순


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


def to_sec(text):
    m = re.fullmatch(r"(\d+):([0-5]\d)(?::([0-5]\d))?", (text or "").strip())
    if not m:
        return None
    return int(m[1]) * 60 + int(m[2]) if m[3] is None else int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])


def topics_of(text):
    t = text.lower()
    return [name for name, words in TOPICS.items() if any(w in t for w in words)]


def search(query, sp):
    for i in range(3):
        try:
            page = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=" + sp)
            data = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S).group(1))
            break
        except (AttributeError, ValueError):
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
            length = (v.get("lengthText") or {}).get("simpleText", "")
            out.append({"id": v["videoId"], "title": "".join(r["text"] for r in v["title"]["runs"]), "channel": run["text"],
                        "channel_id": run["navigationEndpoint"]["browseEndpoint"]["browseId"],
                        "age_h": age_hours(v.get("publishedTimeText", {}).get("simpleText", "")),
                        "age_text": v.get("publishedTimeText", {}).get("simpleText", ""),
                        "length": length.strip() if to_sec(length) is not None else None, "duration_sec": to_sec(length),
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
    for country, queries in QUERIES.items():
        n0 = len(found)
        for q in queries:
            for sp in SORTS:
                for v in search(q, sp):
                    text = v["title"] + " " + v["channel"]
                    topics = topics_of(text)
                    if not topics or v["age_h"] is None or not any(w in text.lower() for w in COUNTRY_WORDS[country]):
                        continue
                    if v["duration_sec"] is not None and v["duration_sec"] < MIN_SEC:
                        continue  # 쇼츠 제외 (길이를 모르면 유지)
                    if re.search(r"north korea|pyongyang|hotel review|top hotels|official (music )?video|lyrics", text.lower()):
                        continue
                    v.update(country=country, topics=topics)
                    found.setdefault(v["id"], v)
                time.sleep(0.4)
        print(f"[{country}] 체험 영상 {len(found) - n0}개")
    ids = sorted({v["channel_id"] for v in found.values()})
    with ThreadPoolExecutor(6) as ex:
        subs = dict(zip(ids, ex.map(channel_subs, ids)))
    items = [{"id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"], "subs": subs.get(v["channel_id"]),
              "views": v["views"], "country": v["country"], "section": "experience", "exp": True, "topics": v["topics"],
              "age_text": v["age_text"], "length": v["length"], "duration_sec": v["duration_sec"],
              "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"), "first_seen": store.get(v["id"], today)}
             for v in found.values()]
    items.sort(key=lambda x: (x["first_seen"], x["published"]), reverse=True)
    items = items[:MAX_ITEMS]
    by_topic = {t: sum(t in i["topics"] for i in items) for t in TOPICS}
    print(f"체험 영상 {len(items)}개 (한국 {sum(i['country'] == '한국' for i in items)} / 일본 {sum(i['country'] == '일본' for i in items)}) {by_topic}")
    if dry:
        for i in items[:20]:
            print(f"  {','.join(i['topics']):20} {i['length'] or '-':>8} {i['channel']} | {i['title'][:50]}")
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i["first_seen"] for i in items}, f, ensure_ascii=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.EXP_TOPICS=%s;\nwindow.EXPERIENCE=%s;\n" % (json.dumps(TOPICS, ensure_ascii=False), json.dumps(items, ensure_ascii=False)))
    print("저장: web/experience.js")


if __name__ == "__main__":
    main()
