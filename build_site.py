# -*- coding: utf-8 -*-
"""유튜브 검색 결과를 모아 사이트용 데이터(web/videos.js)로 저장합니다.

    python build_site.py            검색 → web/videos.js 갱신 (누적, 새 영상은 NEW 표시)
    python build_site.py --notify   위에 더해 새 영상을 텔레그램으로도 알림 (config.ini 필요)

검색 로직은 discover.py 를 그대로 씁니다. API 키는 필요 없습니다.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import discover
import notifier

BASE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(BASE, "web")
STORE = os.path.join(BASE, "site_store.json")
KST = timezone(timedelta(hours=9))
KEEP_DAYS = 60  # 이 기간이 지난 영상은 목록에서 뺌


def to_item(v, country, section, now):
    return {
        "id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"],
        "subs": v.get("subs"), "views": v["views"], "country": country, "section": section,
        "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    notify = "--notify" in sys.argv
    st = discover.load_settings()
    st["exclude_ids"] = discover.resolve_channels(st["exclude_links"])
    store = notifier.read_json(STORE, {"videos": {}, "subs": {}})
    cache = store["subs"]
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    skip = set(st["exclude_videos"])
    found = []

    others = discover.find_other_cities(st, skip, set(), cache)
    found += [to_item(v, "한국", "other", now) for v in others]
    other_ids = {v["id"] for v in others}
    for name, spec in discover.COUNTRIES.items():
        for v in discover.find_country(name, spec, st, skip, cache):
            if v["id"] not in other_ids:
                found.append(to_item(v, name, "recent", now))

    vids = store["videos"]
    new_items = []
    for it in found:
        old = vids.get(it["id"])
        if old:
            old.update(views=it["views"], subs=it["subs"])  # 조회수·구독자만 갱신
        else:
            it["first_seen"] = today
            vids[it["id"]] = it
            new_items.append(it)
    cutoff = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    store["videos"] = {k: v for k, v in vids.items() if v["first_seen"] >= cutoff}
    store["subs"] = cache
    notifier.write_json(STORE, store)

    os.makedirs(WEB, exist_ok=True)
    items = sorted(store["videos"].values(), key=lambda v: (v["first_seen"], v["published"]), reverse=True)
    with open(os.path.join(WEB, "videos.js"), "w", encoding="utf-8") as f:
        f.write("window.UPDATED=%s;\nwindow.VIDEOS=%s;\n" % (
            json.dumps(now.strftime("%Y-%m-%d %H:%M"), ensure_ascii=False), json.dumps(items, ensure_ascii=False)))
    print(f"영상 {len(items)}개 저장 (새 영상 {len(new_items)}개) → web/videos.js")

    if notify and new_items:
        cfg = notifier.load_config()
        if not (cfg["tg_token"] and cfg["tg_chat"]):
            print("[알림 건너뜀] config.ini 에 텔레그램 토큰/채팅ID 가 없어요.")
            return
        for i in range(0, len(new_items), 8):
            chunk = new_items[i:i + 8]
            text = "🆕 <b>새 영상 %d개</b>\n\n" % len(new_items) if i == 0 else ""
            text += "\n\n".join(
                f"{'🇰🇷' if v['country'] == '한국' else '🇯🇵'} <b>{discover.html.escape(v['title'][:70])}</b>\n"
                f"📺 {discover.html.escape(v['channel'])} · 👥 {discover.fmt_num(v['subs'])} · 👁 {discover.fmt_num(v['views'])}\n"
                f"🔗 https://youtu.be/{v['id']}" for v in chunk)
            notifier.notify(cfg, "새 영상", text, text)
            time.sleep(1.5)


if __name__ == "__main__":
    main()
