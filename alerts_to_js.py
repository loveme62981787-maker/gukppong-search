# -*- coding: utf-8 -*-
"""텔레그램 알림으로 보낸 영상 목록(alerts/*.csv)을 사이트용 web/alerts.js 로 옮긴다 (네트워크 불필요).

    python alerts_to_js.py                 alerts/*.csv → web/alerts.js
    python alerts_to_js.py --dir 경로      다른 폴더의 csv 를 읽는다 (시험용)

CSV 열(첫 줄 제목, 한글·영문 모두 허용): 날짜(date) / 나라(country: 한국·일본) / 영상ID(id) / 링크(link) / 제목(title) / 채널(channel) / 채널ID(channel_id) /
구독자(subs) / 조회수(views) / 길이(length, 12:34 형식) / 게시일(published, YYYY-MM-DD).  영상ID 가 없으면 링크에서 뽑는다. 같은 영상은 한 번만(가장 먼저 알림이 온 날짜 기준).
기존 제목 기반 등급과 스크립트 채점은 별개다. 이 변환기는 점수를 만들지 않는다.
"""
import csv
import glob
import json
import os
import re
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "alerts.js")
ALIASES = {
    "date": ["날짜", "date", "알림일", "alert_date"], "country": ["나라", "country", "국가"], "id": ["영상id", "id", "video_id", "videoid"],
    "link": ["링크", "link", "url"], "title": ["제목", "title", "영상제목"], "channel": ["채널", "channel", "채널명"], "channel_id": ["채널id", "channel_id"],
    "subs": ["구독자", "구독자수", "subs", "subscribers"], "views": ["조회수", "views"], "length": ["길이", "length", "영상길이"], "published": ["게시일", "published", "업로드일", "날짜(게시)"],
}
ID_RE = re.compile(r"(?:youtu\.be/|v=|/shorts/|/embed/)([\w-]{11})")


def num(s):
    s = str(s or "").strip().replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KkMm만천]?)", s)
    if not match:
        return None
    return int(float(match[1]) * {"k": 1000, "m": 1000000, "만": 10000, "천": 1000, "": 1}[match[2].lower()])


def main():
    d = os.path.join(BASE, "alerts")
    if "--dir" in sys.argv:
        d = sys.argv[sys.argv.index("--dir") + 1]
    files = sorted(glob.glob(os.path.join(d, "*.csv")))
    if not files:
        print("알림 CSV 없음: 기존 사이트 데이터를 유지합니다.")
        return
    items, seen = [], set()
    for p in files:
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        if not rows:
            continue
        head = [h.strip().lower() for h in rows[0]]
        col = {k: next((head.index(a.lower()) for a in al if a.lower() in head), None) for k, al in ALIASES.items()}
        if col["id"] is None and col["link"] is None:
            raise ValueError("알림 CSV에 영상 ID 또는 링크 열이 없습니다. 기존 출력은 유지됩니다.")
        fallback_date = os.path.splitext(os.path.basename(p))[0][:10]
        for r in rows[1:]:
            g = lambda k: (r[col[k]].strip() if col[k] is not None and col[k] < len(r) else "")
            vid = g("id") or (ID_RE.search(g("link")) or [None, ""])[1]
            if not re.fullmatch(r"[\w-]{11}", vid or "") or vid in seen:
                continue
            seen.add(vid)
            country = g("country")
            items.append({"id": vid, "title": g("title") or "(제목 없음)", "channel": g("channel"), "channel_id": g("channel_id") if re.fullmatch(r"UC[\w-]{22}", g("channel_id")) else "",
                          "subs": num(g("subs")), "views": num(g("views")), "length": g("length"), "published": g("published"),
                          "country": "일본" if "일본" in country or country.lower() in ("jp", "japan") else "한국", "section": "alert", "alert": True,
                          "alert_date": g("date") or fallback_date, "first_seen": g("date") or fallback_date})
    if not items:
        print("유효한 알림 영상 없음: 기존 사이트 데이터를 유지합니다.")
        return
    # 공개 필드만 내보낸다. 원본 CSV와 스크립트·메일·채점 원문은 복사하지 않는다.
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(OUT), delete=False) as f:
        temp = f.name
        f.write("window.ALERTS=%s;\n" % json.dumps(items, ensure_ascii=False))
    os.replace(temp, OUT)
    print("저장:", os.path.relpath(OUT, BASE), len(items), "개")


if __name__ == "__main__":
    main()
