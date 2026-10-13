# -*- coding: utf-8 -*-
"""한국 봇 / 일본 봇으로 보낸 링크·글·사진을 표(CSV)로 계속 쌓아서 저장합니다.

보내는 법 (텔레그램 봇 대화창에서):
    레퍼런스 https://youtu.be/xxxx        -> '레퍼런스' 로 저장
    여행 https://youtu.be/xxxx            -> '여행하는 외국인' 으로 저장
    (사진은 설명(캡션) 맨 앞에 '레퍼런스' 또는 '여행' 을 쓰고 보내세요)
앞에 단어가 없으면 '미분류' 로 저장되고, 봇이 다시 알려줍니다.

    python collect.py          새 메시지를 읽어서 저장하고, 봇이 답장
    python collect.py --dry    저장/답장 없이 화면에만 출력 (테스트)

저장 위치: collection/korea.csv, collection/japan.csv, collection/photos/
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import notifier

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "collection")
PHOTOS = os.path.join(OUT, "photos")
STATE = os.path.join(BASE, "collection_state.json")
KST = timezone(timedelta(hours=9))
COLUMNS = ["번호", "저장일시", "종류", "링크", "영상/채널 제목", "메모", "사진파일"]

# (표시 이름, 파일 이름, 환경변수 이름, config.ini 구역)
BOTS = [
    ("한국", "korea", "KOREA_BOT_TOKEN", "korea_bot"),
    ("일본", "japan", "JAPAN_BOT_TOKEN", "japan_bot"),
]
URL_RE = re.compile(r"https?://[^\s<>\"']+")
YT_RE = re.compile(r"(?:youtu\.be/|youtube\.com/)", re.I)


def get_token(env, section):
    tok = os.environ.get(env, "").strip()
    if tok:
        return tok
    import configparser
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(notifier.CONFIG_INI, encoding="utf-8-sig")
    return cp.get(section, "bot_token", fallback="").strip()


def api(token, method, params=None):
    data = urllib.parse.urlencode(params or {}).encode()
    with urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data), timeout=30) as r:
        return json.loads(r.read().decode())


def classify(text):
    """맨 앞 단어로 종류를 정하고, 단어를 뗀 나머지 내용을 돌려준다."""
    t = (text or "").strip()
    m = re.match(r"^[#\[\(]?\s*(레퍼런스|reference|ref|여행하는\s*외국인|여행|travel)\s*[#\]\)]?[:：\-]?\s*", t, re.I)
    if not m:
        return "미분류", t
    word = m.group(1).replace(" ", "").lower()
    kind = "레퍼런스" if word in ("레퍼런스", "reference", "ref") else "여행하는 외국인"
    return kind, t[m.end():].strip()


CHANNEL_RE = re.compile(r"youtube\.com/(@[^/?#\s]+|channel/UC[\w-]{22}|c/[^/?#\s]+|user/[^/?#\s]+)", re.I)


def channel_info(url):
    """유튜브 채널 링크에서 '채널명 (구독자 N)' 과 채널 ID 를 가져온다. 채널 링크가 아니면 None."""
    m = CHANNEL_RE.search(url)
    if not m:
        return None
    try:
        page = notifier.http_get("https://www.youtube.com/" + m.group(1))
        cid = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page) \
            or re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', page)
        name = re.search(r'<meta property="og:title" content="([^"]*)"', page)
        subs = re.search(r"([\d.,]+)\s*([KMB万千]?)\s*(?:subscribers|명)", page)
        import html as _html
        plain = _html.unescape(name.group(1)).strip() if name else m.group(1)
        label = plain + (f" (구독자 {subs.group(1)}{subs.group(2)})" if subs else "")
        if not cid:
            print(f"  [채널 정보] 채널 ID를 찾지 못함 ({m.group(1)[:30]}), 페이지 길이 {len(page)}")
        return label, (cid.group(1) if cid else ""), plain
    except Exception as e:  # noqa: BLE001
        print(f"  [채널 정보 실패] {m.group(1)[:30]}: {type(e).__name__}: {e}")
        return "", "", ""


def link_title(url):
    """유튜브 링크의 영상 제목과 채널명을 가져온다 (실패하면 빈 값)."""
    if not YT_RE.search(url):
        return ""
    ch = channel_info(url)
    if ch is not None:  # 채널 링크
        return ch[0]
    try:
        o = urllib.parse.quote(url, safe="")
        with urllib.request.urlopen(f"https://www.youtube.com/oembed?url={o}&format=json", timeout=15) as r:
            d = json.loads(r.read().decode())
        return f"{d.get('title', '')} / {d.get('author_name', '')}"
    except Exception:  # noqa: BLE001
        return ""


def read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: 엑셀에서 한글 안 깨짐
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def make_entries(msg, token):
    """메시지 하나를 저장할 항목(들)로 바꾼다. (kind, link, title, memo, photo_bytes)"""
    text = msg.get("text") or msg.get("caption") or ""
    kind, rest = classify(text)
    links = URL_RE.findall(rest)
    memo = URL_RE.sub("", rest).strip()
    photo = None
    if msg.get("photo"):
        fid = msg["photo"][-1]["file_id"]  # 가장 큰 크기
        path = api(token, "getFile", {"file_id": fid})["result"]["file_path"]
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{token}/{path}", timeout=60) as r:
            photo = (r.read(), os.path.splitext(path)[1] or ".jpg")
    entries = []
    for i, link in enumerate(links or [""]):
        ch = channel_info(link) if link and YT_RE.search(link) else None
        title = ch[0] if ch is not None else (link_title(link) if link else "")
        meta = (ch[1], ch[2]) if ch and ch[1] else None  # (채널ID, 채널명): 새 영상 알림 대상
        entries.append((kind, link, title, memo if i == 0 else "", photo if i == 0 else None, meta))
    if not links and not memo and not photo:
        return []
    return entries


def add_to_watchlist(label, kind, meta, link):
    """채널 링크로 저장한 채널을 새 영상 알림 목록(channels.csv)에 추가한다. 새로 추가했으면 True."""
    cid, name = meta
    rows = notifier.load_channels()
    if any(r["채널ID"].strip() == cid for r in rows):
        return False
    rows.append({"채널명": name, "채널링크": link, "채널ID": cid, "메모": f"{label} · {kind}"})
    notifier.save_channels(rows)
    return True


def process_bot(label, fname, token, chat_id, state, dry):
    key = f"{fname}_offset"
    try:
        who = api(token, "getMe")["result"]["username"]
        updates = api(token, "getUpdates", {"offset": state.get(key, 0), "timeout": 0})["result"]
    except Exception as e:  # noqa: BLE001
        print(f"[{label} 봇] 메시지 읽기 실패: {e}")
        return False
    print(f"[{label} 봇] @{who} 새 메시지 {len(updates)}개 (내 채팅 ID: {chat_id})")
    for u in updates:
        m = u.get("message") or u.get("edited_message") or {}
        print(f"   - 채팅 {m.get('chat', {}).get('id')} / 글자수 {len(m.get('text') or m.get('caption') or '')} / 사진 {bool(m.get('photo'))}")
    if not updates:
        return False
    csv_path = os.path.join(OUT, f"{fname}.csv")
    rows = read_rows(csv_path)
    changed = False
    for u in updates:
        state[key] = u["update_id"] + 1
        msg = u.get("message") or u.get("edited_message") or {}
        if str(msg.get("chat", {}).get("id")) != str(chat_id):
            continue  # 내 채팅에서 온 메시지만 저장
        try:
            entries = make_entries(msg, token)
        except Exception as e:  # noqa: BLE001
            print(f"  [처리 실패] {e}")
            continue
        if not entries:
            continue
        replies = []
        for kind, link, title, memo, photo, meta in entries:
            now = datetime.now(KST)
            pfile = ""
            if photo:
                pfile = f"photos/{fname}_{now:%Y%m%d_%H%M%S}_{len(rows) + 1}{photo[1]}"
            dup = next((r for r in rows if link and r["링크"] == link and r["종류"] == kind), None)
            if dup:
                # 같은 링크가 이미 있어도, 사진이 새로 왔으면 사진은 그 항목에 추가로 저장한다
                if photo and not dup.get("사진파일"):
                    if not dry:
                        os.makedirs(PHOTOS, exist_ok=True)
                        with open(os.path.join(OUT, pfile), "wb") as f:
                            f.write(photo[0])
                    dup["사진파일"] = pfile
                    changed = True
                    replies.append(f"📷 이미 있던 항목 (#{dup['번호']})에 사진을 추가로 저장했어요")
                else:
                    replies.append(f"↩️ 이미 저장돼 있어요 ({kind})")
                continue
            if photo and not dry:
                os.makedirs(PHOTOS, exist_ok=True)
                with open(os.path.join(OUT, pfile), "wb") as f:
                    f.write(photo[0])
            rows.append({"번호": len(rows) + 1, "저장일시": now.strftime("%Y-%m-%d %H:%M"), "종류": kind, "링크": link,
                         "영상/채널 제목": title, "메모": memo, "사진파일": pfile})
            changed = True
            tail = " (앞에 '레퍼런스' 또는 '여행'을 붙여 보내면 구분돼요)" if kind == "미분류" else ""
            watch = ""
            if meta and not dry and add_to_watchlist(label, kind, meta, link):
                watch = "\n🔔 이 채널의 새 영상이 올라오면 알려드릴게요"
            replies.append(f"✅ {label} · {kind} 저장 (#{len(rows)}){tail}" + (f"\n{title}" if title else "") + watch)
        text = "\n".join(replies)
        print(f"[{label}] {text}")
        if not dry:
            try:
                api(token, "sendMessage", {"chat_id": chat_id, "text": text})
            except Exception as e:  # noqa: BLE001
                print(f"  [답장 실패] {e}")
    if changed and not dry:
        write_rows(csv_path, rows)
    return changed


def main():
    dry = "--dry" in sys.argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = notifier.load_config()
    chat_id = cfg["tg_chat"]
    state = notifier.read_json(STATE, {})
    for label, fname, env, section in BOTS:
        token = get_token(env, section)
        if not token:
            print(f"[{label} 봇] 토큰이 없어서 건너뜀 ({env})")
            continue
        process_bot(label, fname, token, chat_id, state, dry)
    if not dry:
        notifier.write_json(STATE, state)


if __name__ == "__main__":
    main()
