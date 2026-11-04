# -*- coding: utf-8 -*-
"""콜툰(Call-Toon) 및 통화·음성 밈 쇼츠 레퍼런스/원본/키워드 발굴 수집기

    python calltoon_watch.py          수집 → web/calltoon.js, calltoon_store.json
    python calltoon_watch.py --dry    저장 없이 요약만 출력

3가지 카테고리로 콜툰 소재를 자동 수집한다:
  1. ref      : 검증된 콜툰 레퍼런스 채널 7곳 (여보숏, 마이콜, 받을까 말까, 전화왔숑, 받아볼까, 아무튼망고, 스피커폰)
                최신 쇼츠 + 역대 인기 쇼츠 + 채널 내 아웃라이어 배수 + 설명란 출처(원본 채널/인스타) 자동 추출
  2. orig     : 역추적된 원본 가족·육아·일상 채널 (봄타고가을타고, 리안이쑥쑥, 컴온 유머스트컴백홈, 장꾸발랄 등) 쇼츠
  3. discover : 미개척 한국/해외 통화·육성·홈캠 키워드 발굴 쇼츠

외부 패키지 없이 파이썬 표준 라이브러리만 사용한다.
"""
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "calltoon.js")
STORE = os.path.join(BASE, "calltoon_store.json")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 1. 검증된 콜툰 레퍼런스 채널 (기존 4개 + 신규 발굴 3개 = 총 7개)
REF_CHANNELS = [
    ("여보숏", "UChQ0N_DsTLCiokzF6hiFClA", "통화 UI 파형 + 대각선 종이툰"),
    ("마이콜", "UCivcwygiS5z833iABbxsV8Q", "3등신 2D 캐릭터 + 표정 리액션"),
    ("받을까 말까", "UC-GEyRPFjdd_O0lyGksiMZQ", "Dark 파형 & 크림 종이툰 병행"),
    ("전화왔숑", "UCJ9_3hjZ2gog5WCrApay7qQ", "가족·부부·아이 통화 일러스트"),
    ("받아볼까", "UCEcawrJIoVFILyyifqze9ow", "누적 7,160만뷰 · 파스텔 2D 캐릭터 대화툰"),
    ("아무튼망고", "UC8D6w-5-Twl5SDq7fwqRACA", "급성장 신흥 강자 · 상하 분할 라인아트 종이툰"),
    ("스피커폰", "UCScuSuYLlzYMtkruY1VN2JA", "신생 통화·대화 일러스트 쇼츠"),
    ("통신보안", "UCYj6uIuPGUQ6jip6UtqXjmQ", "구독 24.5만 · 누적 10.8억뷰 통화·대화 쇼츠 대형 채널"),
    ("오늘의 통화", "UCfCH4R67ynUTE55W-r_hgSA", "구독 15.2만 · 누적 7.8억뷰 #통화녹음 대표 채널"),
    ("인생 녹음 중", "UC1OU9eIk4JGnh9DN1yxwW9A", "구독 139만 · 누적 4.3억뷰 부부·가족 일상 녹음툰"),
    ("목소리 극장", "UCBTMGeLEcGkEaymgAGyjVOw", "구독 3.6만 · 누적 2.6억뷰 #통화녹음 일러스트"),
    ("통화툰", "UCfqYYRdo7vddSuN0Yw_Bw8A", "구독 7.4만 · 누적 1.6억뷰 #통화툰 전문 채널"),
    ("여보세요?", "UCkU2qrzka8NtFvvyEKt0r1Q", "구독 2.1만 · 누적 9,167만뷰 #웃긴통화 전문"),
    ("레코드포유 RECORD FOR U", "UCeTKRANKQYeeQWl8z8pqSsQ", "구독 2.5천 · 누적 1,002만뷰 가족 통화 레코드툰"),
    ("당장들어", "UCoqJO9tSTMUFbDfMFy3Ovjg", "구독 3.0천 · 누적 997만뷰 가족·아이 통화 유머"),
]

# 2. 역추적된 원본 가족·육아·일상 채널 (콜툰 채널들의 실제 음성 출처)
ORIG_CHANNELS = [
    ("봄타고가을타고", "UCStWbcX00IAmaxOV7zIy-zg", "가족·부부·아이 일상 원본"),
    ("리안이쑥쑥", "UC4Xg0LGE3IUiJQwbyStcbaQ", "육아·아이 말투 원본"),
    ("컴온 유머스트컴백홈", "UCi9MZe9of7XqwgThwMnXNpA", "가족 유머·통화 원본"),
    ("장꾸발랄", "UC-8hH-Q3LmGm6_WOICkEM4Q", "장난꾸러기 아이 일상 원본"),
    ("감자네: 일기", "UC9wK7odTgYce5teR30awbkw", "누적 4,160만뷰 · 육아·형제·가족 일상 원본"),
]

# 3. 미개척 통화·육성 키워드 발굴 (한국어 + 글로벌 영어)
DISCOVER_QUERIES = [
    ("엄마 딸 전화 레전드 쇼츠", "🇰🇷 한국 통화"),
    ("아빠 아들 통화 쇼츠", "🇰🇷 한국 통화"),
    ("아기 통화 레전드 쇼츠", "🇰🇷 한국 육아"),
    ("남편 전화 레전드 쇼츠", "🇰🇷 한국 부부"),
    ("할머니 손자 전화 쇼츠", "🇰🇷 한국 가족"),
    ("동생 언니 대화 쇼츠", "🇰🇷 한국 남매/자매"),
    ("홈캠 가족 레전드 쇼츠", "🇰🇷 한국 홈캠"),
    ("toddler phone call funny shorts", "🌎 글로벌 육아"),
    ("kid calls dad funny shorts", "🌎 글로벌 통화"),
    ("funny kid conversation shorts", "🌎 글로벌 육아"),
]

# 언어유희/발음 의존도가 높아 해외 번역 시 주의해야 할 키워드
WORDPLAY_WORDS = [
    "삼행시", "이행시", "사행시", "n행시", "끝말잇기", "발음", "사투리",
    "말장난", "아재개그", "언어유희", "동음이의어", "받아쓰기", "맞춤법",
]

# 감정·상황 반전이 뚜렷해 대만/일본 수출에 특히 유리한 키워드
EMOTION_WORDS = [
    "엄마", "아빠", "딸", "아들", "아기", "남편", "아내", "할머니", "할아버지", "동생", "언니", "오빠", "누나",
    "울음", "식겁", "감동", "반전", "전화", "통화", "거짓말", "비밀", "뽀뽀", "트라우마", "부탁", "혼내",
    "사랑", "미안", "화난", "삐진", "장난", "toddler", "mom", "dad", "baby", "call",
]


def get(url, lang="ko-KR,ko;q=0.9,en-US;q=0.8", tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept-Language": lang,
                    "Cookie": "CONSENT=YES+1; SOCS=CAI",
                },
            )
            return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.2 * (i + 1))
    raise last


def initial_data(page):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S)
    return json.loads(m.group(1)) if m else {}


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def parse_kr_views(text):
    """'조회수 540만회', '조회수 5.3천회', '1.2M views', '5,403,910 views' 등을 정수로 변환"""
    if not text:
        return 0
    t = text.replace(",", "").strip()
    m_kr = re.search(r"([\d.]+)\s*(억|만|천)?\s*회", t)
    if m_kr:
        num = float(m_kr.group(1))
        unit = m_kr.group(2) or ""
        mult = {"": 1, "천": 1_000, "만": 10_000, "억": 100_000_000}[unit]
        return int(num * mult)
    m_en = re.search(r"([\d.]+)\s*([KMB]?)\s*views", t, re.I)
    if m_en:
        num = float(m_en.group(1))
        unit = (m_en.group(2) or "").upper()
        mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[unit]
        return int(num * mult)
    return 0


def parse_iso_duration(iso_str):
    """PT27S, PT1M5S 등을 초(int)로 변환"""
    if not iso_str:
        return 0
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso_str)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s


def fmt_length(sec):
    if not sec or sec <= 0:
        return "쇼츠"
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def extract_source_credit(desc):
    """영상 설명란에서 '출처: ...' 또는 원본 크레딧 표기를 추출"""
    if not desc:
        return ""
    lines = [ln.strip() for ln in desc.splitlines() if ln.strip()]
    for i, line_s in enumerate(lines):
        m = re.search(r"(?:출처|원본|원작|음성\s*출처|source|credit)\s*[:：\-]\s*(.+)", line_s, re.I)
        if m:
            val = m.group(1).strip()
            if val and not re.search(r"gmail\.com|naver\.com|비즈니스|문의", val, re.I):
                # 다음 줄에 계정 핸들이나 채널명이 이어지는 경우 함께 결합
                if i + 1 < len(lines) and len(lines[i + 1]) <= 30 and not re.search(r"http|문의|비즈니스|구독|좋아요", lines[i + 1]):
                    val = f"{val} ({lines[i + 1]})"
                return val[:70]
    return ""


KNOWN_OCR_CREDITS = {
    "zasCdbKUkqg": "유튜브 @봄타고가을타고 (원본: ekI83vMceDY)",
    "llB_rvP7xsI": "인스타그램 @ryu_999",
    "XvexXfIwE84": "인스타그램 @hayooni23",
    "-iNory-Y-Mw": "인스타그램 @hayooni23",
    "XAvT4I75ETI": "인스타 haneun1126 (하누니)",
}


def build_source_url(source_credit, category="", channel_id="", vid=""):
    """원작자 출처 문자열에서 인스타·틱톡·유튜브 직행 URL을 생성"""
    if category == "orig" and vid:
        return f"https://www.youtube.com/shorts/{vid}"
    if not source_credit:
        return ""
    s = source_credit.strip()
    m_vid = re.search(r"원본\s*:\s*([A-Za-z0-9_-]{11})", s)
    if m_vid:
        return f"https://www.youtube.com/shorts/{m_vid.group(1)}"
    m_ig = re.search(r"(?:인스타(?:그램)?|instagram|ig)\s*[:：@]?\s*@?([A-Za-z0-9._]{2,35})", s, re.I)
    if m_ig and m_ig.group(1).lower() not in ("그램", "릴스", "출처"):
        return f"https://www.instagram.com/{m_ig.group(1)}/"
    m_tt = re.search(r"(?:틱톡|tiktok)\s*[:：@]?\s*@?([A-Za-z0-9._]{2,35})", s, re.I)
    if m_tt:
        return f"https://www.tiktok.com/@{m_tt.group(1)}"
    m_yt = re.search(r"(?:유튜브|youtube)\s*[:：]?\s*@([^\s/()]+)", s, re.I)
    if m_yt:
        return "https://www.youtube.com/@" + urllib.parse.quote(m_yt.group(1))
    m_at = re.search(r"@([A-Za-z0-9._]{3,35})", s)
    if m_at:
        return f"https://www.instagram.com/{m_at.group(1)}/"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote(s)


def evaluate_export_fit(title, desc="", length_sec=30):
    """대만(Dark 파형)·일본(Warm 종이툰) 현지화 적합도 및 추천 스킨 판정"""
    combined = f"{title} {desc}".lower()
    for w in WORDPLAY_WORDS:
        if w in combined:
            return (
                "wordplay",
                f"⚠️ 언어유희·발음 주의 ('{w}' 포함)",
                "번역 난이도 높음 (한국 내수용 권장)",
            )
    tw_strong = any(w in combined for w in ["식겁", "울음", "거짓말", "반전", "난리", "폭소", "남편", "아내", "비밀", "전화", "통화", "트라우마", "혼내"])
    jp_warm = any(w in combined for w in ["아기", "안정형", "귀여운", "귀여워서", "무해한", "부탁", "뽀뽀", "사랑", "동심", "힐링", "순수", "딸", "아들", "동생", "언니", "toddler", "baby"])
    if tw_strong and jp_warm:
        skin = "🇹🇼 대만 Dark 파형 · 🇯🇵 일본 종이툰 모두 적합"
    elif tw_strong:
        skin = "🇹🇼 대만 Dark 파형 스킨 추천 (통화·반전 몰입)"
    elif jp_warm:
        skin = "🇯🇵 일본 Warm 종이툰 추천 (힐링·공감 에세이)"
    else:
        skin = "🇹🇼 대만 · 🇯🇵 일본 공용 변환 가능"

    if any(w in combined for w in EMOTION_WORDS) or (0 < length_sec <= 60):
        return ("good", "🌏 대만·일본 수출 추천 (감정·상황 중심)", skin)
    return ("good", "🌏 해외 번역 가능", skin)


def fetch_channel_shorts(ch_name, ch_id, category, note="", limit=45):
    """채널의 /shorts 탭에서 최신 쇼츠 목록 수집"""
    url = f"https://www.youtube.com/channel/{ch_id}/shorts"
    try:
        data = initial_data(get(url))
    except Exception as e:  # noqa: BLE001
        print(f"  [경고] {ch_name} ({ch_id}) 쇼츠 탭 로드 실패: {e}")
        return []

    out = []
    seen = set()

    def f(o):
        sl = o.get("shortsLockupViewModel")
        if not sl:
            return
        try:
            vid = sl["onTap"]["innertubeCommand"]["reelWatchEndpoint"]["videoId"]
            if vid in seen:
                return
            seen.add(vid)
            meta = sl.get("overlayMetadata", {})
            title = meta.get("primaryText", {}).get("content", "")
            sec_text = meta.get("secondaryText", {}).get("content", "")
            acc_text = sl.get("accessibilityText", "")
            views = parse_kr_views(sec_text) or parse_kr_views(acc_text)
            if not title and acc_text:
                title = re.sub(r",\s*조회수.*|,\s*[\d.,]+\s*[KMB]?\s*views.*", "", acc_text).strip()
            if vid and title:
                out.append({
                    "id": vid,
                    "title": title,
                    "channel": ch_name,
                    "channel_id": ch_id,
                    "category": category,
                    "channel_note": note,
                    "views": views,
                })
        except (KeyError, IndexError, TypeError):
            pass

    walk(data, f)
    return out[:limit]


def fetch_channel_popular_search(ch_name, ch_id, category, note="", limit=25):
    """채널명으로 조회수순 검색하여 최신 탭에서 밀려난 과거 대박 쇼츠(예: 3개월 전 547만뷰)까지 보강"""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(ch_name) + "&sp=CAMSAhAB"
    try:
        data = initial_data(get(url))
    except Exception:  # noqa: BLE001
        return []

    out = []
    seen = set()

    def f(o):
        v = o.get("videoRenderer")
        if v and "videoId" in v:
            vid = v["videoId"]
            if vid in seen:
                return
            try:
                run = v["ownerText"]["runs"][0]
                found_cid = run["navigationEndpoint"]["browseEndpoint"]["browseId"]
                if found_cid != ch_id:
                    return
                title = "".join(r["text"] for r in v["title"]["runs"])
                v_txt = v.get("viewCountText", {}).get("simpleText", "")
                views = parse_kr_views(v_txt)
                seen.add(vid)
                out.append({
                    "id": vid,
                    "title": title,
                    "channel": ch_name,
                    "channel_id": ch_id,
                    "category": category,
                    "channel_note": note,
                    "views": views,
                })
            except (KeyError, IndexError, TypeError):
                pass

    walk(data, f)
    return out[:limit]


def search_discover_shorts(query, tag, limit=12):
    """유튜브 검색(조회수순)에서 짧은 쇼츠/통화 영상을 발굴"""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=CAMSAhAB"
    try:
        data = initial_data(get(url))
    except Exception:  # noqa: BLE001
        return []

    out = []
    seen = set()

    def f(o):
        v = o.get("videoRenderer")
        if v and "videoId" in v:
            vid = v["videoId"]
            if vid in seen:
                return
            try:
                title = "".join(r["text"] for r in v["title"]["runs"])
                run = v["ownerText"]["runs"][0]
                ch_name = run["text"]
                ch_id = run["navigationEndpoint"]["browseEndpoint"]["browseId"]
                len_txt = v.get("lengthText", {}).get("simpleText", "")
                sec = 0
                if len_txt:
                    parts = [int(x) for x in len_txt.split(":") if x.isdigit()]
                    if len(parts) == 2:
                        sec = parts[0] * 60 + parts[1]
                    elif len(parts) == 3:
                        sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
                if sec > 95:
                    return
                v_txt = v.get("viewCountText", {}).get("simpleText", "")
                views = parse_kr_views(v_txt)
                if views < 30_000:
                    return
                seen.add(vid)
                out.append({
                    "id": vid,
                    "title": title,
                    "channel": ch_name,
                    "channel_id": ch_id,
                    "category": "discover",
                    "channel_note": tag,
                    "views": views,
                    "length_sec": sec,
                })
            except (KeyError, IndexError, TypeError):
                pass

        sl = o.get("shortsLockupViewModel")
        if sl:
            try:
                vid = sl["onTap"]["innertubeCommand"]["reelWatchEndpoint"]["videoId"]
                if vid in seen:
                    return
                meta = sl.get("overlayMetadata", {})
                title = meta.get("primaryText", {}).get("content", "")
                sec_text = meta.get("secondaryText", {}).get("content", "")
                views = parse_kr_views(sec_text)
                if views < 30_000 or not title:
                    return
                seen.add(vid)
                out.append({
                    "id": vid,
                    "title": title,
                    "channel": "",
                    "channel_id": "",
                    "category": "discover",
                    "channel_note": tag,
                    "views": views,
                })
            except (KeyError, IndexError, TypeError):
                pass

    walk(data, f)
    return out[:limit]


def get_local_yt_api_key():
    """로컬 환경변수 또는 사용자 홈의 ~/.claude/youtube/api_key.txt 가 있으면 읽는다 (저장소 내부에는 절대 저장하지 않음)"""
    k = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if k:
        return k
    p = os.path.expanduser("~/.claude/youtube/api_key.txt")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return ""
    return ""


def fetch_details_batch_api(vids, api_key):
    """YouTube Data API v3로 50개씩 초고속 배치 조회 (로컬 API 키가 있을 때만 사용)"""
    out = {}
    for i in range(0, len(vids), 50):
        chunk = vids[i:i + 50]
        params = urllib.parse.urlencode({
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(chunk),
            "key": api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("items", []):
                vid = item["id"]
                sn = item.get("snippet", {})
                st = item.get("statistics", {})
                cd = item.get("contentDetails", {})
                desc = sn.get("description", "") or ""
                out[vid] = {
                    "title": sn.get("title") or "",
                    "channel": sn.get("channelTitle") or "",
                    "channel_id": sn.get("channelId") or "",
                    "views": int(st.get("viewCount") or 0),
                    "length_sec": parse_iso_duration(cd.get("duration", "")),
                    "published": (sn.get("publishedAt") or "")[:10],
                    "desc": desc[:500],
                    "source_credit": extract_source_credit(desc),
                }
        except Exception:  # noqa: BLE001
            pass
    return out


def fetch_watch_detail(vid):
    """개별 watch 페이지에서 정확한 조회수, 길이(초), 업로드일, 설명란(출처) 추출 (API 키 없을 때 폴백)"""
    url = f"https://www.youtube.com/watch?v={vid}"
    try:
        page = get(url)
        m = re.search(r"var ytInitialPlayerResponse = (\{.*?\});", page, re.S)
        if not m:
            return {}
        p = json.loads(m.group(1))
        vd = p.get("videoDetails", {})
        mf = p.get("microformat", {}).get("playerMicroformatRenderer", {})
        desc = vd.get("shortDescription", "") or ""
        pub = (mf.get("publishDate") or mf.get("uploadDate") or "")[:10]
        return {
            "title": vd.get("title") or "",
            "channel": vd.get("author") or "",
            "channel_id": vd.get("channelId") or "",
            "views": int(vd.get("viewCount") or 0),
            "length_sec": int(vd.get("lengthSeconds") or 0),
            "published": pub,
            "desc": desc[:500],
            "source_credit": extract_source_credit(desc),
        }
    except Exception:  # noqa: BLE001
        return {}


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

    raw_items = {}
    ref_ids = {cid for _, cid, _ in REF_CHANNELS}
    orig_ids = {cid for _, cid, _ in ORIG_CHANNELS}

    print("1) 검증된 콜툰 레퍼런스 채널 7곳 (최신순 + 역대 인기순) 수집 중...")
    for ch_name, ch_id, note in REF_CHANNELS:
        recent_items = fetch_channel_shorts(ch_name, ch_id, "ref", note, limit=45)
        pop_items = fetch_channel_popular_search(ch_name, ch_id, "ref", note, limit=25)
        combined_ch = 0
        for it in recent_items + pop_items:
            if it["id"] not in raw_items:
                raw_items[it["id"]] = it
                combined_ch += 1
            elif it.get("views", 0) > raw_items[it["id"]].get("views", 0):
                raw_items[it["id"]]["views"] = it["views"]
        print(f"   - {ch_name}: {combined_ch}개 (최신 {len(recent_items)} / 인기검색 {len(pop_items)})")
        time.sleep(0.25)

    print("2) 역추적된 원본 가족·육아 채널 쇼츠 수집 중...")
    for ch_name, ch_id, note in ORIG_CHANNELS:
        items = fetch_channel_shorts(ch_name, ch_id, "orig", note, limit=30)
        for it in items:
            raw_items.setdefault(it["id"], it)
        print(f"   - {ch_name}: {len(items)}개")
        time.sleep(0.25)

    print("3) 미개척 통화·육성 키워드 발굴 중...")
    disc_count = 0
    for q, tag in DISCOVER_QUERIES:
        items = search_discover_shorts(q, tag, limit=10)
        for it in items:
            if it["id"] not in raw_items:
                raw_items[it["id"]] = it
                disc_count += 1
        time.sleep(0.25)
    print(f"   - 키워드 발굴 후보: {disc_count}개")

    need_detail = [
        vid
        for vid, it in raw_items.items()
        if vid not in store
        or not store[vid].get("published")
        or not store[vid].get("length_sec")
        or not it.get("channel")
        or (it["category"] == "ref" and "source_credit" not in store[vid])
    ]

    details = {}
    if need_detail:
        api_key = get_local_yt_api_key()
        if api_key:
            print(f"4) 상세 정보(업로드일·길이·출처 표기) 고속 배치 조회 중 ({len(need_detail)}개)...")
            details = fetch_details_batch_api(need_detail, api_key)
        else:
            batch = need_detail[:150]
            print(f"4) 상세 정보(업로드일·길이·출처 표기) 웹 병렬 조회 중 ({len(batch)}개)...")
            with ThreadPoolExecutor(8) as ex:
                details = dict(zip(batch, ex.map(fetch_watch_detail, batch)))

    ch_views = {}
    merged_list = []

    for vid, it in raw_items.items():
        cached = store.get(vid, {})
        det = details.get(vid, {})

        title = det.get("title") or it.get("title") or cached.get("title") or ""
        channel = it.get("channel") or det.get("channel") or cached.get("channel") or ""
        channel_id = it.get("channel_id") or det.get("channel_id") or cached.get("channel_id") or ""
        views = max(it.get("views") or 0, det.get("views") or 0, cached.get("views") or 0)
        length_sec = det.get("length_sec") or it.get("length_sec") or cached.get("length_sec") or 0
        published = det.get("published") or cached.get("published") or today
        first_seen = cached.get("first_seen") or today
        source_credit = det.get("source_credit") if "source_credit" in det else cached.get("source_credit", "")
        desc = det.get("desc") or cached.get("desc") or ""

        category = it["category"]
        if channel_id in ref_ids:
            category = "ref"
        elif channel_id in orig_ids:
            category = "orig"

        max_sec = 180 if category == "orig" else 120
        if length_sec > max_sec:
            continue

        export_fit, export_reason, skin_rec = evaluate_export_fit(title, desc, length_sec)

        item = {
            "id": vid,
            "title": title,
            "channel": channel,
            "channel_id": channel_id,
            "category": category,
            "channel_note": it.get("channel_note", ""),
            "views": views,
            "length_sec": length_sec,
            "length": fmt_length(length_sec),
            "published": published,
            "first_seen": first_seen,
            "source_credit": KNOWN_OCR_CREDITS.get(vid) or source_credit or (f"유튜브 원본 @{channel}" if category == "orig" and channel else ""),
            "source_url": build_source_url(KNOWN_OCR_CREDITS.get(vid) or source_credit or (f"유튜브 원본 @{channel}" if category == "orig" and channel else ""), category, channel_id, vid),
            "export_fit": export_fit,
            "export_reason": export_reason,
            "skin_rec": skin_rec,
        }
        merged_list.append(item)
        if channel_id and views > 0:
            ch_views.setdefault(channel_id, []).append(views)

    ch_medians = {cid: max(int(statistics.median(vlist)), 1000) for cid, vlist in ch_views.items() if vlist}

    for item in merged_list:
        cid = item["channel_id"]
        med = ch_medians.get(cid, 0)
        item["median_views"] = med
        if med > 0 and len(ch_views.get(cid, [])) >= 3:
            item["multiple"] = round(item["views"] / med, 1)
        else:
            item["multiple"] = round(item["views"] / 100_000, 1)

    merged_list.sort(key=lambda x: (x["multiple"], x["views"]), reverse=True)

    print(
        f"완료: 총 {len(merged_list)}개 "
        f"(레퍼런스 {sum(x['category']=='ref' for x in merged_list)} / "
        f"원본채널 {sum(x['category']=='orig' for x in merged_list)} / "
        f"키워드발굴 {sum(x['category']=='discover' for x in merged_list)})"
    )

    if dry:
        for x in merged_list[:20]:
            print(
                f"  [{x['category']}] {x['views']:>10,}회 ({x['multiple']}x) | {x['channel']} | "
                f"{x['title'][:38]} | 출처:{x['source_credit'] or '-'}"
            )
        return

    new_store = dict(store)
    for x in merged_list:
        new_store[x["id"]] = {
            "title": x["title"],
            "channel": x["channel"],
            "channel_id": x["channel_id"],
            "views": x["views"],
            "length_sec": x["length_sec"],
            "published": x["published"],
            "first_seen": x["first_seen"],
            "source_credit": x["source_credit"],
        }
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(new_store, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    updated_str = now.strftime("%Y-%m-%d %H:%M KST")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"window.CALLTOON_UPDATED={json.dumps(updated_str)};\n")
        f.write(f"window.CALLTOON={json.dumps(merged_list, ensure_ascii=False)};\n")
    print(f"저장 완료: {OUT}")


if __name__ == "__main__":
    main()
