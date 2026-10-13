# -*- coding: utf-8 -*-
"""매일 '외국인이 한국/일본을 방문한 후기·여행·브이로그' 영상을 찾아 텔레그램으로 알려줍니다.

    python discover.py          찾아서 텔레그램으로 발송 (이미 보낸 영상은 제외)
    python discover.py --dry    발송/기록 없이 화면에만 출력 (테스트)

그룹 (구독자 / 조회수), 각 그룹은 최신 영상이 맨 위:
  1) 구독자 1천 미만 + 조회수 높음   2) 구독자 1천 미만 + 조회수 낮음
  3) 1천~1만 + 조회수 낮음           4) 1천~1만 + 조회수 높음
  5) 구독자 1만 이상
  + 별도 목록: 구독자 대비 조회수 비율이 높은 영상
기준 숫자는 discover.ini 에서 바꿉니다.
"""
import configparser
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import notifier

BASE = os.path.dirname(os.path.abspath(__file__))
INI = os.path.join(BASE, "discover.ini")
SEEN = os.path.join(BASE, "discover_seen.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 검색어와, 영상 제목에 반드시 들어가야 하는 나라 키워드
COUNTRIES = {
    "한국": {
        "flag": "🇰🇷",
        "queries": ["first time in Korea vlog", "Seoul travel vlog", "Korea trip vlog", "visiting Korea first time",
                    "Busan travel vlog", "Jeju travel vlog", "Korea travel diary", "Korea solo travel vlog",
                    "Corée du Sud vlog voyage", "Corea del Sur vlog viaje", "living in Korea foreigner vlog",
                    "South Korea trip honest review", "외국인 한국 여행 브이로그", "외국인 한국 방문 후기"],
        "keywords": ["korea", "korean", "seoul", "busan", "jeju", "corée", "coree", "séoul", "corea", "coréen",
                     "incheon", "hongdae", "myeongdong", "gangnam", "seongsu", "한국", "서울", "부산", "제주"],
        "exclude_chars": r"[가-힣぀-ヿ]",
    },
    "일본": {
        "flag": "🇯🇵",
        "queries": ["first time in Japan vlog", "Tokyo travel vlog", "Japan trip vlog", "Japan travel diary",
                    "Kyoto Osaka travel vlog", "Japan solo travel vlog", "visiting Japan first time honest review",
                    "Japon voyage vlog", "Japón viaje vlog", "living in Japan foreigner vlog",
                    "Japan trip honest review tourist", "外国人 日本旅行 vlog", "外国人 日本 初めて 旅行"],
        "keywords": ["japan", "tokyo", "kyoto", "osaka", "japon", "japón", "hokkaido", "fukuoka", "nara",
                     "okinawa", "nippon", "日本", "東京"],
        "exclude_chars": r"[぀-ヿ가-힣]",
    },
}
UNIT_H = {"s": 0, "m": 0, "h": 1, "d": 24, "w": 168, "mo": 720, "y": 8760}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                                               "Cookie": "CONSENT=YES+1; SOCS=CAI"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")


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


def age_hours(text):
    # '5h ago', '1d ago', '3w ago', '2mo ago', '1y ago' (줄임말) 또는 '5 hours ago' (풀네임) 모두 처리
    m = re.search(r"(\d+)\s*(mo|y|w|d|h|m|s)", (text or "").replace("month", "mo"))
    return int(m.group(1)) * UNIT_H[m.group(2)] if m else None


def parse_count(text, word):
    m = re.search(r"([\d.,]+)\s*([KMB]?)\s*" + word, text or "")
    if not m:
        return None
    return int(float(m.group(1).replace(",", "")) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2)])


def fmt_num(n):
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def fmt_age(h):
    if h < 24:
        return f"{h}시간 전"
    if h < 24 * 60:
        return f"{h // 24}일 전"
    if h < 24 * 365:
        return f"{h // (24 * 30)}개월 전"
    return f"{h // (24 * 365)}년 전"


def search(query, window_days, any_time=False):
    # 기본: 업로드 날짜순 + 이번 주 + 동영상. (이번 주 필터는 최대 7일)
    # any_time=True: 기간 제한 없이 동영상 검색 (관련도순)
    if any_time:
        sp = "EgIQAQ%3D%3D"
    else:
        sp = "CAISBAgDEAE%3D" if window_days <= 7 else "CAISBAgEEAE%3D"
    d = initial_data(get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=" + sp))
    out = []

    def f(o):
        v = o.get("videoRenderer")
        if not v:
            return
        try:
            run = v["ownerText"]["runs"][0]
            out.append({
                "id": v["videoId"],
                "title": "".join(r["text"] for r in v["title"]["runs"]),
                "channel": run["text"],
                "channel_id": run["navigationEndpoint"]["browseEndpoint"]["browseId"],
                "age_h": age_hours(v.get("publishedTimeText", {}).get("simpleText", "")),
                "views": parse_count(v.get("viewCountText", {}).get("simpleText", ""), "views") or 0,
            })
        except (KeyError, IndexError):
            pass
    walk(d, f)
    return out


def channel_subs(cid, cache):
    if cid in cache:
        return cache[cid]
    try:
        subs = parse_count(get("https://www.youtube.com/channel/" + cid), "subscribers")
    except Exception:  # noqa: BLE001
        subs = None
    cache[cid] = subs
    time.sleep(0.6)
    return subs


def load_settings():
    cp = configparser.ConfigParser()
    cp.read(INI, encoding="utf-8-sig")
    s = cp["settings"]
    return {"subs_low": s.getint("subs_low", 1000), "subs_high": s.getint("subs_high", 10000),
            "high_views": s.getint("high_views", 3000), "ratio_min": s.getfloat("ratio_min", 3),
            "ratio_min_views": s.getint("ratio_min_views", 500), "per_group": s.getint("per_group", 5),
            "latest_top": s.getint("latest_top", 10),
            "per_group_small_low": s.getint("per_group_small_low", 15),
            "other_cities_count": s.getint("other_cities_count", 15),
            "skip_sent": s.getboolean("skip_already_sent", False),
            "exclude_videos": [(VIDEO_RE.findall(x) or ([x] if re.fullmatch(r"[\w-]{11}", x) else []))[0]
                               for x in re.split(r"[,\s]+", s.get("exclude_videos", "")) if x and (VIDEO_RE.findall(x) or re.fullmatch(r"[\w-]{11}", x))],
            "exclude_names": [re.sub(r"\s+", "", x).casefold() for x in s.get("exclude_channel_names", "").split(",") if x.strip()],
            "exclude_links": [x.strip() for x in s.get("exclude_channels", "").split(",") if x.strip()],
            "window_days": s.getint("window_days", 7)}


VIDEO_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:[^\s]*&)?v=|shorts/|live/|embed/))([\w-]{11})")


def parse_exclusions(text):
    """텔레그램 메시지에서 제외할 영상 ID를 뽑는다. (영상 링크만 제외, 채널은 그대로)"""
    return list(dict.fromkeys(VIDEO_RE.findall(text or "")))


def read_telegram_exclusions(cfg, data, dry):
    """봇에게 내가 보낸 유튜브 영상 링크를 읽어서 '제외 목록'에 추가한다. 처리하면 답장(확인)을 보낸다."""
    if not (cfg["tg_token"] and cfg["tg_chat"]):
        return
    url = f"https://api.telegram.org/bot{cfg['tg_token']}/getUpdates?timeout=0&offset={data.get('tg_offset', 0)}"
    try:
        updates = json.loads(get(url)).get("result", [])
    except Exception as e:  # noqa: BLE001
        print(f"[제외 링크 확인 실패] {e}")
        return
    added_v = []
    last = None
    for u in updates:
        last = u["update_id"]
        msg = u.get("message") or u.get("edited_message") or {}
        if str(msg.get("chat", {}).get("id")) != str(cfg["tg_chat"]):
            continue  # 내 채팅에서 온 메시지만 처리
        for v in parse_exclusions(msg.get("text", "") + " " + msg.get("caption", "")):
            if v not in data["excluded_videos"]:
                data["excluded_videos"].append(v)
                added_v.append(v)
    if added_v:
        lines = [f"🚫 영상 {len(added_v)}개를 제외 목록에 추가했어요. (같은 채널의 다른 영상은 계속 알려드려요)"]
        lines += [f"• https://youtu.be/{v}" for v in added_v[:10]]
        text = "\n".join(lines)
        print(text)
        if not dry:
            notifier.notify(cfg, "제외 목록 추가", html.escape(text), text)
    if last is not None and not dry:
        data["tg_offset"] = last + 1


def resolve_channels(entries):
    """discover.ini 의 exclude_channels (채널 링크 / @핸들 / UC... ID)를 채널 ID 집합으로 바꾼다."""
    ids = set()
    for e in entries:
        m = re.search(r"(UC[\w-]{22})", e)
        if m:
            ids.add(m.group(1))
            continue
        link = notifier.normalize_link(e)
        if not link:
            print(f"[제외 채널 형식 오류] {e}")
            continue
        try:
            ids.add(notifier.lookup_channel(link)[0])
        except Exception as ex:  # noqa: BLE001
            print(f"[제외 채널 확인 실패] {e}: {ex}")
    return ids


def find_country(name, spec, st, seen, cache):
    videos = {}
    failed = 0
    for q in spec["queries"]:
        for attempt in range(3):  # 일시적 실패에 대비해 최대 3번 시도
            try:
                for v in search(q, st["window_days"]):
                    videos.setdefault(v["id"], v)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  [검색 실패 {attempt + 1}/3] {q}: {e}")
                time.sleep(3 * (attempt + 1))
        else:
            failed += 1
        time.sleep(0.5)
    print(f"[{name}] 검색어 {len(spec['queries'])}개 중 {failed}개 실패, 영상 {len(videos)}개 수집")
    keep = []
    for v in videos.values():
        text = v["title"].lower()
        if v["id"] in seen or v["age_h"] is None or v["age_h"] > st["window_days"] * 24:
            continue
        if re.sub(r"\s+", "", v["channel"]).casefold() in st["exclude_names"] or v["channel_id"] in st["exclude_ids"]:
            continue  # 내 채널(코리아탐방록, 코리아관찰기 등)은 통째로 제외
        if re.search(r"north korea|pyongyang|hotel review|hotel guide|top hotels", text + " " + v["channel"].lower()):
            continue  # 북한 / 호텔 리뷰 자동업로드 영상은 제외 (한국어·일본어 제목, 워킹투어는 포함)
        if not any(k in text for k in spec["keywords"]):
            continue
        keep.append(v)
    print(f"[{name}] 후보 {len(keep)}개 (구독자 수 확인 중)")
    # 구독자 수는 채널마다 한 번만 확인 (이미 확인한 채널은 저장해 둔 값 사용), 6개씩 동시에 확인
    todo = sorted({v["channel_id"] for v in keep if v["channel_id"] not in cache})
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda c: channel_subs(c, cache), todo))
    for v in keep:
        v["subs"] = cache.get(v["channel_id"])
    keep = [v for v in keep if v["subs"] is not None]
    keep.sort(key=lambda v: v["age_h"])  # 최신순
    return keep


# 서울·부산이 아닌 다른 도시를 여행하는 영상 (기간 제한 없음, 매일 새로운 영상으로 바뀜)
OTHER_CITIES = {
    "queries": ["Jeju travel vlog", "Jeju island trip vlog", "Gyeongju travel vlog", "Jeonju hanok travel vlog",
                "Gangneung travel vlog", "Sokcho Seoraksan travel vlog", "Daegu travel vlog", "Incheon travel vlog",
                "Suwon travel vlog", "Yeosu travel vlog", "Andong travel vlog", "Tongyeong travel vlog",
                "Daejeon travel vlog", "Gwangju Korea travel vlog", "Ulleungdo travel vlog", "Namhae Korea trip vlog",
                "Korea countryside travel vlog", "Korea road trip vlog small town", "Korea beyond Seoul travel vlog",
                "Pohang Chuncheon Gapyeong travel vlog"],
    "keywords": ["jeju", "gyeongju", "jeonju", "gangneung", "sokcho", "seorak", "daegu", "incheon", "suwon", "yeosu",
                 "andong", "tongyeong", "daejeon", "gwangju", "ulleung", "namhae", "pohang", "chuncheon", "gapyeong",
                 "nami island", "damyang", "boseong", "mokpo", "gunsan", "taean", "jinju", "ulsan", "changwon",
                 "gangwon", "jeolla", "gyeongsang", "chungcheong", "제주", "경주", "전주", "강릉", "속초", "대구",
                 "인천", "수원", "여수", "안동", "통영", "대전", "광주", "울릉", "남해", "포항", "춘천", "가평"],
    # 서울·부산 영상은 빼기 (서울의 유명 지역 이름도 포함)
    "exclude": ["seoul", "séoul", "busan", "hongdae", "myeongdong", "gangnam", "seongsu", "itaewon", "서울", "부산",
                "north korea", "pyongyang", "hotel review", "hotel guide", "top hotels"],
}


def find_other_cities(st, skip_ids, sent_ids, cache):
    """서울·부산 외 다른 도시 여행 영상을 찾는다. 이미 보냈던 영상은 빼서 매일 새로운 영상이 오게 한다."""
    spec = OTHER_CITIES
    found = {}
    for q in spec["queries"]:
        for attempt in range(3):
            try:
                for v in search(q, st["window_days"], any_time=True):
                    found.setdefault(v["id"], v)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  [검색 실패 {attempt + 1}/3] {q}: {e}")
                time.sleep(3 * (attempt + 1))
        time.sleep(0.5)
    cands = []
    for v in found.values():
        text = (v["title"] + " " + v["channel"]).lower()
        if v["id"] in skip_ids or v["id"] in sent_ids or v["age_h"] is None:
            continue
        if re.sub(r"\s+", "", v["channel"]).casefold() in st["exclude_names"] or v["channel_id"] in st["exclude_ids"]:
            continue
        if any(x in text for x in spec["exclude"]):
            continue
        if not any(k in text for k in spec["keywords"]):
            continue
        cands.append(v)
    cands.sort(key=lambda v: v["age_h"])  # 가능하면 최신 영상부터
    want = st["other_cities_count"]
    pool = cands[: want * 3]  # 구독자 수를 확인할 후보 (필요한 만큼만)
    todo = sorted({v["channel_id"] for v in pool if v["channel_id"] not in cache})
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda c: channel_subs(c, cache), todo))
    out = []
    for v in pool:
        v["subs"] = cache.get(v["channel_id"])
        if v["subs"] is not None:
            out.append(v)
    print(f"[다른 도시] 검색 {len(found)}개 → 후보 {len(cands)}개 → 선택 {min(len(out), want)}개")
    return out[:want]


def group_videos(keep, st):
    hv = st["high_views"]
    g = [[], [], [], [], []]
    for v in keep:
        s, high = v["subs"], v["views"] >= hv
        if s < st["subs_low"]:
            g[0 if high else 1].append(v)
        elif s < st["subs_high"]:
            g[3 if high else 2].append(v)
        else:
            g[4].append(v)
    ratio = [v for v in keep if v["views"] >= st["ratio_min_views"] and v["views"] / max(v["subs"], 1) >= st["ratio_min"]]
    return g, ratio


def line(i, v, with_ratio=False):
    e = html.escape
    extra = f" · 📈 {v['views'] / max(v['subs'], 1):.1f}배" if with_ratio else ""
    return (f"{i}. <b>{e(v['title'][:70])}</b>\n   📺 {e(v['channel'])} · 👥 {fmt_num(v['subs'])} · "
            f"👁 {fmt_num(v['views'])} · 🕒 {fmt_age(v['age_h'])}{extra}\n   🔗 https://youtu.be/{v['id']}")


def build_blocks(name, flag, g, ratio, st):
    n, hv = st["per_group"], fmt_num(st["high_views"])
    # g = [소규모+높음, 소규모+낮음, 중간+낮음, 중간+높음, 1만 이상] 를 아래 순서로 보여준다
    order = [  # (제목, g의 번호, 보여줄 개수)
        (f"👥 구독자 {fmt_num(st['subs_low'])} 미만 · 조회수 낮음", 1, st["per_group_small_low"]),
        (f"👥 구독자 {fmt_num(st['subs_low'])} 미만 · 조회수 높음 ({hv}+)", 0, n),
        (f"👥 {fmt_num(st['subs_low'])}~{fmt_num(st['subs_high'])} · 조회수 낮음", 2, n),
        (f"👥 {fmt_num(st['subs_low'])}~{fmt_num(st['subs_high'])} · 조회수 높음 ({hv}+)", 3, n),
        (f"👥 구독자 {fmt_num(st['subs_high'])} 이상", 4, n),
    ]
    blocks = []
    for t, idx, cnt in order:
        vids = g[idx][:cnt]
        body = "\n".join(line(i, v) for i, v in enumerate(vids, 1)) or "(해당 영상 없음)"
        blocks.append((f"<b>{t}</b>\n{body}", vids))
    body = "\n".join(line(i, v, True) for i, v in enumerate(ratio[:n], 1)) or "(해당 영상 없음)"
    blocks.append((f"<b>📈 구독자 대비 조회수 높은 영상 ({st['ratio_min']:g}배 이상)</b>\n{body}", ratio[:n]))
    return blocks


def pack(head, blocks, limit=3800):
    msgs, cur = [], head
    for text, _ in blocks:
        if len(cur) + len(text) + 2 > limit and cur != head:
            msgs.append(cur)
            cur = head + "(이어서)\n\n"
        cur += "\n\n" + text if cur.strip() else text
    msgs.append(cur)
    return msgs


def main():
    dry = "--dry" in sys.argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    st = load_settings()
    st["exclude_ids"] = resolve_channels(st["exclude_links"])
    cfg = notifier.load_config()
    seen_data = notifier.read_json(SEEN, {})
    for k, default in (("videos", []), ("subs", {}), ("excluded_videos", [])):
        seen_data.setdefault(k, default)
    read_telegram_exclusions(cfg, seen_data, dry)  # 텔레그램으로 보낸 제외 링크 반영
    # 제외 목록(내가 봇에 보낸 링크)은 항상 뺀다. 이미 보낸 영상은 skip_already_sent = yes 일 때만 뺀다.
    seen = set(seen_data["excluded_videos"]) | set(st["exclude_videos"]) | (set(seen_data["videos"]) if st["skip_sent"] else set())
    cache = seen_data["subs"]
    new_ids = []
    seen_data.setdefault("sent_other", [])
    other_ids = []
    for name, spec in COUNTRIES.items():
        extra = []
        if name == "한국":  # 맨 앞: 서울·부산 말고 다른 도시 여행 영상
            others = find_other_cities(st, set(seen_data["excluded_videos"]) | set(st["exclude_videos"]),
                                       set(seen_data["sent_other"]), cache)
            body = "\n".join(line(i, v) for i, v in enumerate(others, 1)) or "(해당 영상 없음)"
            extra = [(f"<b>🏝 서울·부산 말고 다른 도시 여행 ({len(others)}개)</b>\n{body}", others)]
            other_ids = [v["id"] for v in others]
        keep = find_country(name, spec, st, seen, cache)
        if not keep and not extra:  # 아무것도 못 찾았을 때 조용히 넘어가지 않고 알림
            notice = f"⚠️ {spec['flag']} 오늘 {name} 방문 영상을 찾지 못했어요. (검색 실패 또는 새 영상 없음)"
            print(notice)
            if not dry:
                notifier.notify(cfg, f"[{name}] 결과 없음", notice, notice)
            continue
        blocks = list(extra)
        if keep:
            # 가장 최근에 올라온 영상 N개는 따로 보내고, 나머지로 그룹을 나눈다
            top = keep[:st["latest_top"]]
            g, ratio = group_videos(keep[st["latest_top"]:], st)
            top_body = "\n".join(line(i, v) for i, v in enumerate(top, 1))
            blocks.append((f"<b>🕒 가장 최근에 올라온 영상 TOP {len(top)}</b>\n{top_body}", top))
            blocks += build_blocks(name, spec["flag"], g, ratio, st)
        head = f"{spec['flag']} <b>오늘의 {name} 방문 영상</b>\n"
        for m in pack(head, blocks):
            print("\n" + re.sub(r"<[^>]+>", "", html.unescape(m)))
            if not dry:
                ok = notifier.notify(cfg, f"[{name}] 오늘의 영상", m, re.sub(r"<[^>]+>", "", html.unescape(m)))
                print("  -> 발송 성공" if ok else "  -> 발송 실패")
                time.sleep(1.5)  # 텔레그램 연속 발송 제한 방지
        for _, vids in blocks:
            new_ids += [v["id"] for v in vids]
    if not dry:
        if st["skip_sent"]:
            seen_data["videos"] = (seen_data["videos"] + new_ids)[-3000:]
        seen_data["sent_other"] = (seen_data["sent_other"] + other_ids)[-3000:]  # 다른 도시 영상은 한 번 보내면 다시 안 보냄
        notifier.write_json(SEEN, seen_data)


if __name__ == "__main__":
    main()
