# -*- coding: utf-8 -*-
"""코리아탐방록 - 유튜브 채널 새 영상 알림 프로그램

사용법 (자세한 설명은 README.md 참고):
    python notifier.py add https://www.youtube.com/@핸들     채널 추가
    python notifier.py check                                  새 영상 확인 + 알림
    python notifier.py list                                   등록된 채널 보기
    python notifier.py test                                   알림이 오는지 테스트
    python notifier.py demo                                   각 채널의 최신 영상 1개를 '새 영상'처럼 알림 (기록은 안 함)

외부 패키지 없이 파이썬 기본 기능만 사용합니다. API 키도 필요 없습니다.
"""
import argparse
import configparser
import csv
import html
import json
import os
import re
import smtplib
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_CSV = os.path.join(BASE_DIR, "channels.csv")
SEEN_JSON = os.path.join(BASE_DIR, "seen.json")
KEYWORDS_TXT = os.path.join(BASE_DIR, "keywords.txt")
CONFIG_INI = os.path.join(BASE_DIR, "config.ini")

CSV_COLUMNS = ["채널명", "채널링크", "채널ID", "메모"]
FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
KST = timezone(timedelta(hours=9))
MAX_SEEN_PER_CHANNEL = 300

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


# ---------------------------------------------------------------- 공통 도우미
def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        # 유럽 등에서 뜨는 쿠키 동의 화면을 건너뛰기 위한 값
        "Cookie": "CONSENT=YES+1; SOCS=CAI",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 채널 목록 (CSV)
def load_channels():
    if not os.path.exists(CHANNELS_CSV):
        return []
    with open(CHANNELS_CSV, encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if (row.get("채널ID") or "").strip()]


def save_channels(rows):
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않게 함
    with open(CHANNELS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in CSV_COLUMNS})


def normalize_link(text):
    """'@handle', 'youtube.com/@handle', 전체 URL 등을 표준 채널 링크로 바꿈."""
    text = text.strip()
    m = re.search(r"(UC[\w-]{22})", text)
    if m and "/channel/" in text:
        return "https://www.youtube.com/channel/" + m.group(1)
    m = re.search(r"@([\w.\-]+)", text)
    if m:
        return "https://www.youtube.com/@" + m.group(1)
    return None


def lookup_channel(link):
    """채널 페이지에서 (채널ID, 채널명)을 찾는다."""
    page = http_get(link)
    patterns = [
        r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"',
        r'"externalId":"(UC[\w-]{22})"',
        r'"channelId":"(UC[\w-]{22})"',
        r'"browseId":"(UC[\w-]{22})"',
        r'channel_id=(UC[\w-]{22})',
    ]
    channel_id = None
    for p in patterns:
        m = re.search(p, page)
        if m:
            channel_id = m.group(1)
            break
    if not channel_id:
        raise RuntimeError("채널 페이지에서 채널 ID를 찾지 못했습니다. 링크를 확인해 주세요.")
    m = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    name = html.unescape(m.group(1)).strip() if m else link
    return channel_id, name


def cmd_add(args):
    rows = load_channels()
    known = {r["채널ID"] for r in rows}
    seen = read_json(SEEN_JSON, {})
    memo = args.memo or ""
    for raw in args.links:
        link = normalize_link(raw)
        if not link:
            print(f"[건너뜀] 채널 링크 형식이 아닙니다: {raw}")
            continue
        try:
            channel_id, name = lookup_channel(link)
        except Exception as e:  # noqa: BLE001
            print(f"[실패] {raw} -> {e}")
            continue
        if channel_id in known:
            print(f"[이미 있음] {name} ({channel_id})")
            continue
        rows.append({"채널명": name, "채널링크": link, "채널ID": channel_id, "메모": memo})
        known.add(channel_id)
        print(f"[추가] {name}  ->  {channel_id}")
        # 처음 추가하는 채널: 기존 영상은 알리지 않고 '본 것'으로만 기록
        try:
            videos = fetch_feed(channel_id)
            seen[channel_id] = [v["id"] for v in videos]
            print(f"       기존 영상 {len(videos)}개는 알림 없이 기록만 했어요.")
        except Exception as e:  # noqa: BLE001
            print(f"       (RSS 확인 실패: {e}) 다음 실행 때 기록만 하고 넘어갑니다.")
    save_channels(rows)
    write_json(SEEN_JSON, seen)


def cmd_list(_args):
    rows = load_channels()
    if not rows:
        print("등록된 채널이 없습니다.")
    for i, r in enumerate(rows, 1):
        print(f"{i}. {r['채널명']}  {r['채널링크']}  {r['채널ID']}  {r.get('메모', '')}")


# ---------------------------------------------------------------- RSS 읽기
def fetch_feed(channel_id):
    last_err = None
    for _ in range(2):  # 가끔 일시적으로 실패하므로 한 번 더 시도
        try:
            text = http_get(FEED_URL.format(channel_id))
            break
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
    else:
        raise RuntimeError(f"RSS를 읽지 못했습니다: {last_err}")
    root = ET.fromstring(text)
    videos = []
    for entry in root.findall("a:entry", NS):
        vid = entry.findtext("yt:videoId", default="", namespaces=NS)
        title = entry.findtext("a:title", default="", namespaces=NS)
        published = entry.findtext("a:published", default="", namespaces=NS)
        link_el = entry.find("a:link", NS)
        link = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={vid}"
        desc = entry.findtext("media:group/media:description", default="", namespaces=NS)
        videos.append({"id": vid, "title": title, "published": published, "link": link, "description": desc})
    return videos


def format_date(iso_text):
    try:
        dt = datetime.fromisoformat(iso_text.replace("Z", "+00:00")).astimezone(KST)
        return dt.strftime("%Y-%m-%d %H:%M (한국시간)")
    except ValueError:
        return iso_text


# ---------------------------------------------------------------- 한국 관련 키워드
def load_keywords():
    if not os.path.exists(KEYWORDS_TXT):
        return []
    words = []
    with open(KEYWORDS_TXT, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line)
    return words


def find_keywords(video, keywords):
    text = (video["title"] + "\n" + video["description"]).lower()
    return [k for k in keywords if k.lower() in text]


# ---------------------------------------------------------------- 알림 (텔레그램 / 이메일)
def load_config():
    cfg = configparser.ConfigParser(interpolation=None)
    if os.path.exists(CONFIG_INI):
        cfg.read(CONFIG_INI, encoding="utf-8-sig")

    def get(section, key, env):
        value = os.environ.get(env) or (cfg.get(section, key, fallback="") if cfg.has_section(section) else "")
        return value.strip()

    return {
        "tg_token": get("telegram", "bot_token", "TELEGRAM_BOT_TOKEN"),
        "tg_chat": get("telegram", "chat_id", "TELEGRAM_CHAT_ID"),
        "smtp_host": get("email", "smtp_host", "SMTP_HOST") or "smtp.gmail.com",
        "smtp_port": get("email", "smtp_port", "SMTP_PORT") or "587",
        "smtp_user": get("email", "username", "SMTP_USER"),
        "smtp_pass": get("email", "password", "SMTP_PASS"),
        "mail_to": get("email", "to", "MAIL_TO"),
    }


def send_telegram(cfg, text):
    url = f"https://api.telegram.org/bot{cfg['tg_token']}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": cfg["tg_chat"],
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8")).get("ok", False)


def send_email(cfg, subject, plain_text):
    msg = MIMEText(plain_text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["smtp_user"]
    msg["To"] = cfg["mail_to"]
    with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"]), timeout=30) as s:
        s.starttls()
        s.login(cfg["smtp_user"], cfg["smtp_pass"])
        s.send_message(msg)
    return True


def notify(cfg, subject, html_text, plain_text):
    """텔레그램 → (실패/미설정 시) 이메일 순서로 시도. 하나라도 성공하면 True."""
    if cfg["tg_token"] and cfg["tg_chat"]:
        try:
            if send_telegram(cfg, html_text):
                return True
        except Exception as e:  # noqa: BLE001
            print(f"  [텔레그램 실패] {e}")
    if cfg["smtp_user"] and cfg["smtp_pass"] and cfg["mail_to"]:
        try:
            if send_email(cfg, subject, plain_text):
                return True
        except Exception as e:  # noqa: BLE001
            print(f"  [이메일 실패] {e}")
    return False


def build_message(channel_name, video, matched, memo=""):
    e = html.escape
    when = format_date(video["published"])
    tag_html = f"\n🏷 {e(memo)}" if memo else ""
    tag_plain = f"\n구분: {memo}" if memo else ""
    if matched:
        head = "🇰🇷🔥🔥 <b>[한국 관련 영상!]</b> 🔥🔥🇰🇷"
        flag = "✅ <b>한국 관련: 예</b> (" + e(", ".join(matched)) + ")"
        plain_head = "★★★ [한국 관련 영상!] ★★★"
        plain_flag = "한국 관련: 예 (" + ", ".join(matched) + ")"
    else:
        head = "🆕 새 영상"
        flag = "한국 관련: 아니오"
        plain_head = "[새 영상]"
        plain_flag = flag
    html_text = (
        f"{head}\n\n"
        f"📺 채널: <b>{e(channel_name)}</b>{tag_html}\n"
        f"🎬 제목: {e(video['title'])}\n"
        f"📅 업로드: {e(when)}\n"
        f"{flag}\n"
        f"🔗 {e(video['link'])}"
    )
    plain = (
        f"{plain_head}\n채널: {channel_name}{tag_plain}\n제목: {video['title']}\n"
        f"업로드: {when}\n{plain_flag}\n링크: {video['link']}"
    )
    subject = ("[한국 관련] " if matched else "[새 영상] ") + f"{channel_name} - {video['title']}"
    return subject, html_text, plain


# ---------------------------------------------------------------- 명령: check / demo / test
def cmd_check(_args):
    channels = load_channels()
    if not channels:
        print("channels.csv 에 채널이 없습니다. 먼저 'add' 로 채널을 추가하세요.")
        return
    cfg = load_config()
    keywords = load_keywords()
    seen = read_json(SEEN_JSON, {})
    total_new = 0
    for ch in channels:
        cid, name = ch["채널ID"].strip(), ch["채널명"].strip()
        try:
            videos = fetch_feed(cid)
        except Exception as e:  # noqa: BLE001
            print(f"[오류] {name}: {e}")
            continue
        if cid not in seen:
            seen[cid] = [v["id"] for v in videos]
            print(f"[처음 등록] {name}: 기존 영상 {len(videos)}개는 알리지 않고 기록만 했어요.")
            continue
        known = set(seen[cid])
        new_videos = [v for v in videos if v["id"] not in known]
        new_videos.sort(key=lambda v: v["published"])  # 오래된 것부터
        if not new_videos:
            print(f"[새 영상 없음] {name}")
        for v in new_videos:
            matched = find_keywords(v, keywords)
            subject, html_text, plain = build_message(name, v, matched, (ch.get("메모") or "").strip())
            print("\n" + plain + "\n")
            if notify(cfg, subject, html_text, plain):
                seen[cid].append(v["id"])
                total_new += 1
            else:
                print("  ※ 알림을 보내지 못해서 '본 영상'으로 기록하지 않았습니다. (다음 실행 때 다시 시도)")
                print("     config.ini 설정을 확인해 주세요.")
        seen[cid] = seen[cid][-MAX_SEEN_PER_CHANNEL:]
        write_json(SEEN_JSON, seen)  # 채널마다 저장 (중간에 멈춰도 안전)
    write_json(SEEN_JSON, seen)
    print(f"\n완료: 알림 {total_new}건 발송")


def cmd_demo(_args):
    cfg = load_config()
    keywords = load_keywords()
    for ch in load_channels():
        try:
            videos = fetch_feed(ch["채널ID"].strip())
        except Exception as e:  # noqa: BLE001
            print(f"[오류] {ch['채널명']}: {e}")
            continue
        if not videos:
            continue
        v = videos[0]
        matched = find_keywords(v, keywords)
        subject, html_text, plain = build_message(ch["채널명"], v, matched, (ch.get("메모") or "").strip())
        print("\n" + plain + "\n")
        ok = notify(cfg, "[데모] " + subject, "🧪 <i>(데모 알림 - 실제 새 영상 아님)</i>\n" + html_text,
                    "(데모 알림)\n" + plain)
        print("  -> 발송 성공" if ok else "  -> 발송 실패 또는 미설정 (config.ini 확인)")


def cmd_test(_args):
    cfg = load_config()
    ok = notify(cfg, "코리아탐방록 알림 테스트", "✅ <b>코리아탐방록 알림 테스트</b>\n설정이 잘 되었어요!",
                "코리아탐방록 알림 테스트: 설정이 잘 되었어요!")
    print("테스트 알림을 보냈습니다. 폰을 확인하세요!" if ok else
          "알림을 보내지 못했습니다. config.ini (토큰/채팅ID) 를 확인해 주세요.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="코리아탐방록 새 영상 알림")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add", help="채널 링크(@핸들)로 채널 추가")
    p.add_argument("links", nargs="+")
    p.add_argument("--memo", default="", help="메모 (선택)")
    p.set_defaults(func=cmd_add)
    sub.add_parser("check", help="새 영상 확인 후 알림").set_defaults(func=cmd_check)
    sub.add_parser("list", help="등록된 채널 목록").set_defaults(func=cmd_list)
    sub.add_parser("test", help="알림 테스트 메시지 발송").set_defaults(func=cmd_test)
    sub.add_parser("demo", help="최신 영상을 새 영상처럼 알림 (기록 안 함)").set_defaults(func=cmd_demo)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
