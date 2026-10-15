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
    observed_at = v.get("observed_at", now.astimezone(KST).isoformat())
    if valid_timestamp(observed_at) is None:
        observed_at = None
    views = v.get("views")
    return {
        "id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"],
        "subs": v.get("subs"), "views": views,
        "observed_at": observed_at, "subs_checked_at": v.get("subs_checked_at"),
        "views_history": [[observed_at, views]] if observed_at and valid_views(views) else [], "country": country, "section": section,
        "length": v.get("length"), "duration_sec": v.get("duration_sec"), "is_short": v.get("is_short"),
        "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"),
    }


def valid_views(value):
    """조회수 이력에는 확인된 0 이상의 정수만 기록한다."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def valid_timestamp(value):
    """잘못된 시각이나 시간대 없는 값은 증가 속도 계산에 사용하지 않는다."""
    try:
        stamp = datetime.fromisoformat(value)
        return stamp if stamp.utcoffset() is not None else None
    except (TypeError, ValueError):
        return None


def merge_history(history, observed_at, views):
    """기존 관측을 우선 보존하고 시간순으로 최신 12개를 남긴다."""
    merged = {}
    for row in history if isinstance(history, list) else []:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            continue
        stamp, count = row
        parsed = valid_timestamp(stamp)
        if parsed is not None and valid_views(count):
            merged.setdefault(parsed, [stamp, count])
    parsed = valid_timestamp(observed_at)
    if parsed is not None and valid_views(views):
        merged.setdefault(parsed, [observed_at, views])
    return [merged[key] for key in sorted(merged)[-12:]]


def merge_items(vids, found, today):
    """재발견된 영상의 통계를 갱신하고 비어 있지 않은 길이 정보를 보충한다."""
    new_items = []
    for it in found:
        old = vids.get(it["id"])
        if old is not None:
            if valid_views(it.get("views")):
                old["views"] = it["views"]
            if it.get("subs") is not None:
                old["subs"] = it["subs"]
            old["views_history"] = merge_history(
                old.get("views_history"), it.get("observed_at"), it.get("views"))
            for key in ("observed_at", "subs_checked_at"):
                if valid_timestamp(it.get(key)) is not None and (key != "observed_at" or valid_views(it.get("views"))):
                    old[key] = it[key]
                else:
                    old.setdefault(key, None)
            for key in ("length", "duration_sec", "is_short"):
                value = it.get(key)
                if value is not None and not (isinstance(value, str) and not value.strip()):
                    old[key] = value
        else:
            it = dict(it, first_seen=today)
            it.setdefault("observed_at", None)
            it.setdefault("subs_checked_at", None)
            it["views_history"] = merge_history([], it["observed_at"], it.get("views"))
            vids[it["id"]] = it
            new_items.append(it)
    return new_items


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    notify = "--notify" in sys.argv
    st = discover.load_settings()
    st["exclude_ids"] = discover.resolve_channels(st["exclude_links"])
    store = notifier.read_json(STORE, {"videos": {}, "subs": {}})
    cache = store["subs"]
    checked_at = store.setdefault("subs_checked_at", {})
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    skip = set(st["exclude_videos"])
    found = []

    others = discover.find_other_cities(st, skip, set(), cache, checked_at)
    found += [to_item(v, "한국", "other", now) for v in others]
    other_ids = {v["id"] for v in others}
    for name, spec in discover.COUNTRIES.items():
        for v in discover.find_country(name, spec, st, skip, cache, checked_at):
            if v["id"] not in other_ids:
                found.append(to_item(v, name, "recent", now))

    vids = store["videos"]
    new_items = merge_items(vids, found, today)
    cutoff = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    store["videos"] = {k: v for k, v in vids.items() if v["first_seen"] >= cutoff}
    store["subs"] = cache
    notifier.write_json(STORE, store)

    os.makedirs(WEB, exist_ok=True)
    items = sorted(store["videos"].values(), key=lambda v: (v["first_seen"], v["published"]), reverse=True)
    with open(os.path.join(WEB, "videos.js"), "w", encoding="utf-8") as f:
        public_settings = {key: st[key] for key in ("subs_low", "subs_high", "high_views", "ratio_min", "ratio_min_views")}
        f.write("window.SETTINGS=%s;\n" % json.dumps(public_settings, ensure_ascii=False))
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
