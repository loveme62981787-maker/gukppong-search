# -*- coding: utf-8 -*-
"""별도 레퍼런스 채널의 영상을 전부 모아 web/reference.js 로 저장

    python reference_watch.py            reference_channels.txt 의 채널 → web/reference.js
    python reference_watch.py --dry      저장 없이 요약만 출력
    python reference_watch.py --max 300  채널당 최대 영상 수 (기본 3000)

reference_channels.txt: 한 줄에 채널 하나. @핸들 / 채널 URL / UC로 시작하는 채널 ID / 채널 이름 모두 가능 (@핸들·ID 가 가장 정확).
검색으로 모은 영상과 달리 채널의 '동영상' 탭을 끝까지 읽는다 (쇼츠 탭은 포함하지 않는다).
API 키 불필요, 표준 라이브러리만 사용. channels_watch.py 의 채널 확인 함수를 재사용한다.
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import channels_watch as cw
from viral_watch import age_hours, get, initial_data, parse_count, walk

BASE = os.path.dirname(os.path.abspath(__file__))
LIST = os.path.join(BASE, "reference_channels.txt")
OUT = os.path.join(BASE, "web", "reference.js")
STORE = os.path.join(BASE, "reference_store.json")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_PER_CHANNEL = 3000


def read_list():
    names = []
    if os.path.exists(LIST):
        with open(LIST, encoding="utf-8-sig") as f:
            for line in f:
                s = line.split("#")[0].strip()
                if s:
                    names.append(s)
    return names


def resolve(entry):
    """줄 하나 → (채널 ID, 이름). 못 찾으면 None"""
    m = re.search(r"(UC[\w-]{22})", entry)
    if m:
        cid = m.group(1)
        page = get("https://www.youtube.com/channel/" + cid)
        n = re.search(r'<meta property="og:title" content="([^"]*)"', page)
        return cid, (n.group(1) if n else cid)
    m = re.search(r"(@[\w.\-%]+)", entry)
    if m:
        return cw.resolve_handle(m.group(1))
    return cw.channel_search(entry)


def parse_video(v, cid, cname, now, today, first_seen):
    try:
        age_text = v.get("publishedTimeText", {}).get("simpleText", "")
        h = age_hours(age_text)
        title = "".join(r["text"] for r in v["title"]["runs"])
        return {"id": v["videoId"], "title": title, "channel": cname, "channel_id": cid,
                "views": parse_count(v.get("viewCountText", {}).get("simpleText", ""), "views") or 0,
                "age_text": age_text, "length": v.get("lengthText", {}).get("simpleText", ""),
                "published": (now - timedelta(hours=h)).strftime("%Y-%m-%d") if h is not None else today,
                "first_seen": first_seen.get(v["videoId"], today)}
    except (KeyError, IndexError):
        return None


def short_count(text):
    m = re.match(r"\s*([\d.,]+)\s*([KMB]?)", text or "")
    return int(float(m.group(1).replace(",", "")) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2)]) if m else 0


def parse_lockup(x, cid, cname, now, today, first_seen):
    """새 채널 화면의 lockupViewModel 형식 (영상만; 재생목록·쇼츠 등은 건너뜀)"""
    try:
        if x.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
            return None
        vid = x["contentId"]
        meta = x["metadata"]["lockupMetadataViewModel"]
        parts = [p["text"]["content"] for r in meta["metadata"]["contentMetadataViewModel"]["metadataRows"] for p in r.get("metadataParts", []) if "text" in p]
        views = short_count(parts[0]) if parts and "view" in json.dumps(meta, ensure_ascii=False)[:4000].lower() else 0
        age_text = next((p for p in parts if re.search(r"\d\s*(?:y|mo|w|d|h|m|s)\w*\s*ago|ago", p)), "")
        length = ""

        def f(o):
            nonlocal length
            b = o.get("thumbnailBadgeViewModel")
            if b and not length and re.match(r"^\d+(:\d\d){1,2}$", b.get("text", "")):
                length = b["text"]
        walk(x.get("contentImage", {}), f)
        h = age_hours(age_text)
        return {"id": vid, "title": meta["title"]["content"], "channel": cname, "channel_id": cid, "views": views,
                "age_text": age_text, "length": length,
                "published": (now - timedelta(hours=h)).strftime("%Y-%m-%d") if h is not None else today,
                "first_seen": first_seen.get(vid, today)}
    except (KeyError, IndexError, TypeError):
        return None


def channel_videos(cid, cname, now, today, first_seen, limit):
    page = get("https://www.youtube.com/channel/" + cid + "/videos")
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
    ver = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', page)
    data = initial_data(page)
    out, seen = [], set()
    while True:
        raw, tokens = [], []

        def f(o):
            if "videoRenderer" in o:
                raw.append(parse_video(o["videoRenderer"], cid, cname, now, today, first_seen))
            if "lockupViewModel" in o:
                raw.append(parse_lockup(o["lockupViewModel"], cid, cname, now, today, first_seen))
            ci = o.get("continuationItemRenderer")   # 목록 맨 끝의 '더 보기' 토큰만 쓴다 (정렬 칩의 토큰과 구분)
            if ci:
                c = ci.get("continuationEndpoint", {}).get("continuationCommand", {})
                if c.get("token"):
                    tokens.append(c["token"])
        walk(data, f)
        for p in raw:
            if p and p["id"] not in seen:
                seen.add(p["id"])
                out.append(p)
        if len(out) >= limit or not tokens or not key:
            break
        body = json.dumps({"context": {"client": {"clientName": "WEB", "clientVersion": ver.group(1) if ver else "2.20240101.00.00", "hl": "en", "gl": "US"}},
                           "continuation": tokens[0]}).encode()
        req = urllib.request.Request("https://www.youtube.com/youtubei/v1/browse?key=" + key.group(1), data=body,
                                     headers={"User-Agent": UA, "Content-Type": "application/json", "Accept-Language": "en-US,en;q=0.9"})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            print("  이어 읽기 실패:", e)
            break
        time.sleep(0.5)
    return out[:limit]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry" in sys.argv
    limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else MAX_PER_CHANNEL
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    first_seen = {}
    if os.path.exists(STORE):
        try:
            with open(STORE, encoding="utf-8") as f:
                first_seen = json.load(f)
        except (OSError, json.JSONDecodeError):
            first_seen = {}
    items, channels = [], []
    for entry in read_list():
        try:
            r = resolve(entry)
        except Exception as e:  # noqa: BLE001
            r = None
            print(f"[{entry}] 확인 실패: {e}")
        if not r:
            print(f"[{entry}] 채널을 찾지 못했어요 (@핸들이나 채널 URL 로 알려 주세요)")
            continue
        cid, cname = r
        subs = parse_count(get("https://www.youtube.com/channel/" + cid), "subscribers")
        vids = channel_videos(cid, cname, now, today, first_seen, limit)
        for v in vids:
            v.update({"subs": subs, "country": "", "section": "reference", "ref": True})
        items += vids
        channels.append({"channel_id": cid, "channel": cname, "videos": len(vids)})
        print(f"[{cname}] 영상 {len(vids)}개 (구독자 {subs})")
    print(f"레퍼런스 영상 {len(items)}개 / 채널 {len(channels)}개")
    if dry:
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i["first_seen"] for i in items}, f, ensure_ascii=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.REFERENCE=%s;\n" % json.dumps(items, ensure_ascii=False))
    print("저장: web/reference.js")


if __name__ == "__main__":
    main()
