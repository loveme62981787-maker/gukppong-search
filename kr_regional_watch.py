# -*- coding: utf-8 -*-
"""한국어 지역 해시태그·지역명(#후쿠오카 #도쿄 / #단수이 #타이베이 ...)으로 한국어 제작자의 일본·대만 현지 여행·체험 원본을 찾아 web/kr_regional.js 로 저장

    python kr_regional_watch.py            검색 → kr_regional_store.json + web/kr_regional.js
    python kr_regional_watch.py --dry      저장 없이 요약만 출력

근거(제목에서만 확인 가능한 것): 한국어 지역명(해시태그 포함) + 한국어 체험 단어 + 롱폼. 뉴스·재편집·쇼츠·국내 지명 혼합은 제외한다.
제목이 한글이라는 사실만으로 제작자 국적을 확정하지 않는다: 저장값은 '한국어 제목 근거'(ko_title)일 뿐이고, 화면은 추정으로만 표시한다.
experience_watch.py 의 검색·파싱 함수를 재사용한다. 검색이 실패한 실행은 이전 저장분을 그대로 두고 새 결과만 합친다. (API 키 불필요, 표준 라이브러리만 사용)
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import experience_watch as ew

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "kr_regional.js")
STORE = os.path.join(BASE, "kr_regional_store.json")
KST = timezone(timedelta(hours=9))
MIN_SEC = 181
MAX_ITEMS = 1500
MIN_OK_RATIO = 0.5   # 검색 작업 중 이 비율 이상 성공해야 '이번 실행이 정상'으로 보고 정리한다 (아니면 이전 저장분만 유지하며 합친다)
SORTS = ["EgIQAQ%3D%3D", "CAISBAgEEAE%3D"]   # 관련도순 / 이번 달 최신순

# 나라 -> {표시 지역: 제목에서 지역으로 인정하는 한국어 표기}. 나라마다 대표 지역을 여러 개 둔다
REGIONS = {
    "일본": {
        "후쿠오카": ["후쿠오카"], "도쿄": ["도쿄", "동경"], "오사카": ["오사카"], "교토": ["교토"], "삿포로·홋카이도": ["삿포로", "홋카이도"],
        "오키나와": ["오키나와"], "나고야": ["나고야"], "벳푸·유후인": ["벳푸", "유후인"], "구마모토": ["구마모토"], "히로시마": ["히로시마"],
        "나라·고베": ["나라 여행", "고베"],
    },
    "대만": {
        "타이베이": ["타이베이", "타이페이"], "단수이": ["단수이", "딴수이"], "지우펀": ["지우펀"], "타이중": ["타이중"], "가오슝": ["가오슝"],
        "타이난": ["타이난"], "화롄": ["화롄", "화련"], "컨딩·아리산": ["컨딩", "아리산"],
    },
}
QUERY_SUFFIX = ["", "여행 브이로그", "맛집 먹방", "체험 일상"]   # 지역명 단독(해시태그 검색 포함) + 체험 단어 조합

# 제목에 하나라도 있어야 하는 한국어 체험·여행 단어
EXP_RE = re.compile(r"여행|브이로그|vlog|맛집|먹방|투어|체험|일상|한달살기|한 달 살기|살이|워홀|유학|출장|호캉스|온천|료칸|야시장|코스|박\s?\d일|\d박|혼자|가족|부모님|당일치기|기차|카페|숙소|호텔|쇼핑|산책|드라이브|라멘|노포|기행|걷기|일주일|주말|휴가|힐링|노을|선셋", re.I)
# 뉴스·재편집·정보 가공물·비체험 (제목에 있으면 제외)
NEWS_RE = re.compile(r"뉴스|속보|단독|특파원|사건|사고|참사|지진|쓰나미|태풍\s?(상륙|접근|경보)|선거|대통령|총리|정치|외교|관세|환율|경제 전망|논란|폭로|논평|시사|[가-힣]*뉴스", re.I)
REEDIT_RE = re.compile(r"반응|리액션|해외\s?반응|요약|몰아보기|모아보기|모음|하이라이트|다시보기|클립|풀버전|짤|리뷰만|편집본|재업|영화\s?리뷰|드라마\s?리뷰|예고편|결말|줄거리|해설|나\s?혼자\s?산다|MBC|KBS|SBS|tvN|JTBC|예능|방송|ASMR|asmr|공식\s?(뮤직비디오|영상)|MV\b|가사", re.I)
SHORTS_RE = re.compile(r"#shorts?\b|쇼츠|숏츠|shorts", re.I)
# 한국 국내 지명·귀국 표현: 일본·대만 여행이 아닐 가능성이 커서 제외한다
DOMESTIC_RE = re.compile(r"서울|부산|제주|인천|대구|대전|광주|강릉|속초|경주|전주|여수|수원|한국에서|국내\s?(여행|맛집)")
# 단수이는 한국어 '단수(물 공급 중단)' 오탐이 많다: 아래 단어가 있으면 제외하고, 대만 근거 단어가 있거나 여행 단어가 있을 때만 인정한다
WATER_OUT_RE = re.compile(r"단수\s?이\s?(다|예요|에요|입니다|발생|사태|공지|예정|안내|때문)|물이?\s?(안|끊|나오지)|급수|수도|아파트|정전|복구|공사|배관|누수|수압")
TW_CONTEXT_RE = re.compile(r"대만|타이완|타이베이|타이페이|MRT|홍마오청|훙마오청|라오제|위런마터우|어인|지우펀|타이중|가오슝|타이난|화롄|淡水|taiwan|tamsui|danshui", re.I)


def region_of(title, country):
    """제목에서 나라의 한국어 지역 표기를 찾는다. 해시태그(#지역)도 일반 표기와 같이 보고, 어떤 방식으로 맞았는지 함께 돌려준다"""
    hits = []
    for region, names in REGIONS[country].items():
        for n in names:
            if n in title:
                hits.append((region, "#" + n in title))
                break
    return hits


def judge(v):
    """검색 결과 한 건을 판정한다. 통과하면 근거 dict, 아니면 None. 네트워크를 쓰지 않는다 (회귀 테스트용)"""
    t = v.get("title") or ""
    if not re.search(r"[가-힣]{2,}", t) or v.get("age_h") is None:
        return None
    if v.get("duration_sec") is None or v["duration_sec"] < MIN_SEC or SHORTS_RE.search(t):
        return None   # 쇼츠 제외, 길이를 모르면 확정 데이터에 넣지 않는다
    if NEWS_RE.search(t) or REEDIT_RE.search(t) or DOMESTIC_RE.search(t):
        return None
    found = {c: region_of(t, c) for c in REGIONS}
    countries = [c for c, h in found.items() if h]
    if len(countries) != 1:
        return None   # 지역 근거가 없거나 일본·대만이 한 제목에 섞여 있으면 나라를 확정하지 않는다
    country = countries[0]
    hits = found[country]
    words = sorted({m.group(0).strip() for m in EXP_RE.finditer(t)})
    if not words:
        return None
    if any(r == "단수이" for r, _ in hits):
        if WATER_OUT_RE.search(t):
            return None
        if not TW_CONTEXT_RE.search(t) and not re.search(r"여행|브이로그|vlog|맛집|야시장|투어|노을|선셋|카페|먹방|산책", t, re.I):
            return None
    return {"country": country, "region": hits[0][0], "regions": [r for r, _ in hits], "hashtag": any(h for _, h in hits), "words": words}


def queries():
    qs = []
    for country, regions in REGIONS.items():
        for region, names in regions.items():
            base = names[0]
            qs.append(("#" + base, SORTS))
            for suf in QUERY_SUFFIX:
                qs.append(((base + " " + suf).strip(), SORTS))
    return qs


def load_store():
    try:
        with open(STORE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def run_job(job):
    """검색 한 건 실행. 실패하면 None (빈 결과와 구분해서 성공 비율을 센다)"""
    q, sorts = job
    out = []
    try:
        for sp in sorts:
            out += ew.search(q, sp)
    except Exception:  # noqa: BLE001
        return None
    return out


def collect(jobs, runner=run_job, workers=3):
    found, ok = {}, 0
    with ThreadPoolExecutor(workers) as ex:
        for job, results in zip(jobs, ex.map(runner, jobs)):
            if results is None:
                continue
            ok += 1
            for v in results:
                ev = judge(v)
                if ev:
                    if v["id"] in found:
                        found[v["id"]]["_q"].append(job[0])
                    else:
                        found[v["id"]] = dict(v, ev=ev, _q=[job[0]])
    return found, ok


def merge(prev, found, now):
    """이전 저장분을 보존하고 새 결과를 합친다. 같은 ID 는 첫 발견일·기존 근거를 유지하고 검색어·단어만 합집합으로 늘린다"""
    today = now.strftime("%Y-%m-%d")
    out = dict(prev)
    for vid, v in found.items():
        ev = v["ev"]
        old = out.get(vid) or {}
        subs = old.get("subs")
        out[vid] = {"id": vid, "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"], "subs": v.get("subs", subs), "views": v["views"],
                    "country": ev["country"], "section": "kr_regional", "age_text": v["age_text"], "length": v["length"], "duration_sec": v["duration_sec"],
                    "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"), "first_seen": old.get("first_seen", today),
                    "kr_regional": True, "kr_country": ev["country"], "kr_region": ev["region"], "kr_regions": ev["regions"], "kr_hashtag": ev["hashtag"],
                    "kr_words": sorted(set(ev["words"]) | set(old.get("kr_words", []))), "kr_queries": sorted(set(v["_q"]) | set(old.get("kr_queries", [])))[:6],
                    "ko_title": True}
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry" in sys.argv
    now = datetime.now(KST)
    prev = load_store()
    jobs = queries()
    found, ok = collect(jobs)
    enough = ok >= len(jobs) * MIN_OK_RATIO
    print(f"검색어 {len(jobs)}개 중 성공 {ok}개 → 후보 {len(found)}개" + ("" if enough else " (실패가 많아 이전 저장분을 유지하고 새 결과만 합침)"))
    # 영상 검색 결과만 사용한다. 중복 영상의 구독자 수는 기존 사이트 자료를 활용한다.
    merged = {k: v for k, v in merge(prev, found, now).items() if not (NEWS_RE.search(v.get("title", "")) or REEDIT_RE.search(v.get("title", "")) or DOMESTIC_RE.search(v.get("title", "")))}   # 제외 기준이 강화되면 이전 저장분에도 적용
    items = sorted(merged.values(), key=lambda x: (x["first_seen"], x["views"]), reverse=True)[:MAX_ITEMS]
    by = {}
    for i in items:
        by.setdefault(i["country"], []).append(i)
    for c, rows in by.items():
        print(f"[{c}] {len(rows)}개 (이번에 새로 발견 {sum(1 for r in rows if r['id'] in found and r['id'] not in prev)}개)")
    if dry:
        for i in items[:15]:
            print(f"  {i['country']} {i['kr_region']} {i['length'] or '-':>8} 조회 {i['views']:>9,} {i['id']} | {i['title'][:50]}")
        return
    if not found and not prev:
        print("결과가 없어 저장하지 않음")
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i for i in items}, f, ensure_ascii=False)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.KR_REGIONAL=%s;\n" % json.dumps(items, ensure_ascii=False))
    print("저장: web/kr_regional.js")


if __name__ == "__main__":
    main()
