# -*- coding: utf-8 -*-
"""오늘의 인기 정책·경제·이슈 쇼츠 소재 수집기 (토큰 0소모 · 저작권 클린 검증)

    python kr_news_watch.py          수집 → web/kr_news.js, kr_news_store.json
    python kr_news_watch.py --dry    저장 없이 요약만 출력

3가지 카테고리로 당일 쇼츠용 뉴스 소재를 자동 수집·채점한다:
  1. kogl1   : 대한민국 정책브리핑(korea.kr) 중 '공공누리 제1유형(출처표시, 상업적 이용·변경 가능)'이 확인된 기사·포토·그래픽만 수집
  2. economy : 당일 화제 경제·민생·연금·지원금·IT(삼성/애플 등) 인기 이슈 뉴스 (팩트·숫자 추출 및 자체 인용 카드 제작용)
  3. celeb   : 당일 연예·문화·스포츠 화제 뉴스 + 위키미디어 커먼즈(CC-BY / CC0) 합법 사진 자동 매칭

외부 패키지·AI 토큰 없이 파이썬 표준 라이브러리만 사용한다.
"""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "kr_news.js")
STORE = os.path.join(BASE, "kr_news_store.json")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

ALLOWED_WIKI_LIC = ("CC0", "PUBLIC DOMAIN", "CC BY 4.0", "CC BY 3.0", "CC BY 2.5", "CC BY 2.0", "CC BY-SA 4.0", "CC BY-SA 3.0")

# @ve.rris 스타일 빨간 테두리 배지로 뽑기 좋은 숫자·금액·비율 패턴
BADGE_RE = re.compile(
    r"(?:월\s*)?\d[\d,]*(?:\.\d+)?\s*(?:조\s*원|억\s*원|만\s*원|천\s*원|원|달러|%|퍼센트|배|만\s*명|만\s*대|세|년|개월|시간|위|건)"
)

# 쇼츠 대박 트리거 키워드 (민생·돈·연금·세금·비교·대기업·반전)
HOT_KEYWORDS = [
    ("연금", 18), ("국민연금", 22), ("기초연금", 22), ("지원금", 20), ("환급", 20),
    ("세금", 16), ("건보료", 18), ("전기요금", 16), ("과태료", 18), ("벌금", 16),
    ("삼성", 16), ("애플", 16), ("아이폰", 16), ("갤럭시", 16), ("현대차", 14),
    ("부동산", 14), ("청약", 14), ("대출", 14), ("금리", 14), ("물가", 14),
    ("역전", 20), ("논란", 15), ("충격", 14), ("반전", 16), ("최초", 12), ("무료", 14),
    ("할인", 12), ("인상", 14), ("인하", 14), ("개편", 14), ("시행", 12),
]


def http_get(url, timeout=12, headers=None):
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def extract_badges(text):
    found = []
    for m in BADGE_RE.finditer(text or ""):
        val = re.sub(r"\s+", " ", m.group(0)).strip()
        if val not in found:
            found.append(val)
        if len(found) >= 4:
            break
    return found


def calc_shorts_score(title, summary, badges, category):
    t = f"{title} {summary}"
    score = 45 if category == "kogl1" else 40
    score += min(24, len(badges) * 9)
    for kw, pts in HOT_KEYWORDS:
        if kw in t:
            score += pts
    if "?" in title or "왜" in title or "이유" in title or "vs" in title.lower():
        score += 10
    return min(99, score)


def make_hook_preview(title, badges):
    clean = re.sub(r"\s*[-|]\s*.*$", "", title or "").strip()
    clean = re.sub(r"\[.*?\]|\(.*?\)", "", clean).strip()
    b_str = f" [{badges[0]}]" if badges else ""
    return f"{clean[:26]}{b_str}"


def fetch_korea_kr_item(nid):
    url = f"https://www.korea.kr/news/policyNewsView.do?newsId={nid}"
    try:
        raw = http_get(url, timeout=10)
        is_kogl1 = ("공공누리" in raw) and ("제1유형" in raw or "opentype01" in raw or "출처표시" in raw)
        if not is_kogl1:
            return None
        t_m = re.search(r'<meta property="og:title" content="([^"]+)"', raw)
        d_m = re.search(r'<meta property="og:description" content="([^"]+)"', raw)
        i_m = re.search(r'<meta property="og:image" content="([^"]+)"', raw)
        date_m = re.search(r"(\d{4}\.\d{2}\.\d{2})", raw)

        title = html.unescape(t_m.group(1)).strip() if t_m else ""
        title = re.sub(r"\s*-\s*정책뉴스.*$", "", title).strip()
        if not title:
            return None
        summary = html.unescape(d_m.group(1)).strip() if d_m else ""
        summary = re.sub(r"\s*-\s*정책브리핑.*$", "", summary).strip()
        img = html.unescape(i_m.group(1)).strip() if i_m else ""
        pub_date = date_m.group(1).replace(".", "-") if date_m else datetime.now(KST).strftime("%Y-%m-%d")

        # 본문 텍스트에서 추가 숫자 배지 추출
        body_m = re.search(r'<div class="view_cont[^"]*">(.*?)</div>', raw, re.S)
        body_txt = re.sub(r"<[^>]+>", " ", html.unescape(body_m.group(1))) if body_m else ""
        badges = extract_badges(f"{title} {summary} {body_txt[:600]}")
        score = calc_shorts_score(title, summary, badges, "kogl1")

        return {
            "id": f"kogl_{nid}",
            "category": "kogl1",
            "title": title,
            "summary": summary[:160],
            "url": url,
            "thumb": img,
            "source": "대한민국 정책브리핑",
            "license": "✅ 공공누리 제1유형 (사진·본문 상업적 무료)",
            "published": pub_date,
            "badges": badges,
            "score": score,
            "hook": make_hook_preview(title, badges),
        }
    except Exception:
        return None


def collect_kogl1_news(max_items=24):
    urls = [
        "https://www.korea.kr/news/policyNewsList.do",
        "https://www.korea.kr/news/policyNewsList.do?pageIndex=2",
    ]
    nids = []
    for u in urls:
        try:
            raw = http_get(u)
            for m in re.findall(r"newsId=(\d+)", raw):
                if m not in nids:
                    nids.append(m)
        except Exception:
            pass
    nids = nids[:max_items]
    items = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(fetch_korea_kr_item, nids):
            if res:
                items.append(res)
    return items


def search_wiki_cc_thumb(person_or_kw):
    if not person_or_kw:
        return None
    u = (
        "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrnamespace=6&gsrsearch={urllib.parse.quote('filetype:bitmap ' + person_or_kw)}"
        "&gsrlimit=4&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=640&format=json"
    )
    try:
        raw = http_get(u, timeout=8, headers={"User-Agent": "GukppongSearchBot/1.0"})
        d = json.loads(raw)
        pages = d.get("query", {}).get("pages", {})
        for _, p in pages.items():
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "").strip()
            if any(lic.upper().startswith(ok) for ok in ALLOWED_WIKI_LIC):
                artist_raw = meta.get("Artist", {}).get("value", "Wikimedia")
                artist = re.sub(r"<[^>]+>", "", artist_raw).strip()[:20]
                return {
                    "thumb": ii.get("thumburl") or ii.get("url", ""),
                    "license": f"✅ Wikimedia {lic} (사진 출처: {artist})",
                }
    except Exception:
        pass
    return None


def collect_google_rss(query, category, max_items=15):
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    out = []
    try:
        xml_str = http_get(rss_url, timeout=12)
        root = ET.fromstring(xml_str)
        for item in root.findall(".//item")[:max_items]:
            raw_title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            press = source_el.text.strip() if source_el is not None and source_el.text else "뉴스"
            title = re.sub(r"\s*-\s*[^-]+$", "", raw_title).strip()
            if not title:
                continue
            badges = extract_badges(title)
            score = calc_shorts_score(title, "", badges, category)
            nid = "gn_" + str(abs(hash(title)))[:10]
            pub_date = datetime.now(KST).strftime("%Y-%m-%d")
            try:
                dt = datetime.strptime(pub[:16].strip(), "%a, %d %b %Y")
                pub_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

            thumb = ""
            lic_label = "🛡 팩트·숫자만 추출 (자체 인용카드 + Pixabay 스톡 사용)"
            if category == "celeb":
                # 제목 첫 어절(인물/그룹명 후보)로 위키미디어 CC-BY 사진 매칭 시도
                first_word = re.sub(r"[^가-힣A-Za-z]", "", title.split()[0]) if title.split() else ""
                if len(first_word) >= 2:
                    w = search_wiki_cc_thumb(first_word)
                    if w:
                        thumb = w["thumb"]
                        lic_label = w["license"]

            out.append({
                "id": nid,
                "category": category,
                "title": title,
                "summary": f"{press} 보도 · 핵심 숫자/팩트를 추출해 음슴체 비교 대본 및 자체 뉴스 브리핑 카드로 안전 제작",
                "url": link,
                "thumb": thumb,
                "source": press,
                "license": lic_label,
                "published": pub_date,
                "badges": badges,
                "score": score,
                "hook": make_hook_preview(title, badges),
            })
    except Exception:
        pass
    return out


def main():
    dry = "--dry" in sys.argv
    existing = {}
    if os.path.exists(STORE):
        try:
            with open(STORE, encoding="utf-8") as f:
                data = json.load(f)
                for it in data.get("items", []):
                    existing[it["id"]] = it
        except Exception:
            pass

    print("1) 대한민국 정책브리핑(korea.kr) 공공누리 제1유형 기사 수집 중...")
    kogl_items = collect_kogl1_news(20)
    print(f"   -> 공공누리 1유형 확인 기사 {len(kogl_items)}건")

    print("2) 당일 인기 경제·민생·연금·IT 이슈 뉴스 수집 중...")
    eco_items = []
    for q in [
        "국민연금 OR 기초연금 OR 지원금 OR 환급금 when:2d",
        "삼성전자 OR 갤럭시 OR 애플 OR 아이폰 가격 판매량 when:2d",
        "과태료 OR 벌금 OR 전기요금 OR 건보료 개편 when:2d",
    ]:
        eco_items.extend(collect_google_rss(q, "economy", 8))

    print("3) 연예·문화 화제 뉴스 + 위키미디어 CC-BY 사진 매칭 중...")
    celeb_items = collect_google_rss("손흥민 OR 이정재 OR 아이유 OR 방탄소년단 OR 블랙핑크 기록 1위 when:3d", "celeb", 10)

    # 병합 및 중복 제목 제거
    seen_titles = set()
    merged = []
    for it in kogl_items + eco_items + celeb_items:
        norm_t = re.sub(r"\s+", "", it["title"])[:18]
        if norm_t in seen_titles:
            continue
        seen_titles.add(norm_t)
        merged.append(it)

    merged.sort(key=lambda x: (x.get("score", 0), x.get("published", "")), reverse=True)
    updated_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

    print(f"총 {len(merged)}건 수집 완료 (갱신: {updated_str})")
    if dry:
        for it in merged[:5]:
            print(f"  [{it['category']}] ({it['score']}점) {it['title']} | 배지:{it['badges']}")
        return

    store_obj = {"updated": updated_str, "items": merged}
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(store_obj, f, ensure_ascii=False, indent=2)

    js_content = (
        f"window.KR_NEWS_UPDATED = {json.dumps(updated_str, ensure_ascii=False)};\n"
        f"window.KR_NEWS = {json.dumps(merged, ensure_ascii=False)};\n"
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"저장 완료: {STORE}, {OUT}")


if __name__ == "__main__":
    main()
