# -*- coding: utf-8 -*-
"""사이트에 있는 영상의 채널 위치(국가)를 채널 '정보' 페이지에서 읽어 web/channel_country.js 로 저장

    python channel_country_watch.py            새 채널만 조회해 저장 (기존 조회 결과는 channel_country_store.json 에 보관)
    python channel_country_watch.py --max 200  이번에 조회할 채널 수 제한

채널 위치는 채널 운영자가 정보 페이지에 적은 국가다. 국적이 아니므로(한국에 사는 외국인 채널도 'South Korea'), '해외 위치'만 외국인 근거로 쓴다.
API 키 불필요, 표준 라이브러리만 사용.
"""
import glob
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch_country(cid):
    """채널 정보 페이지를 조금씩 읽다가 국가가 나오면 바로 멈춘다 (페이지 전체는 1~3MB 라서)"""
    req = urllib.request.Request("https://www.youtube.com/channel/" + cid + "/about", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"})
    buf = b""
    with urllib.request.urlopen(req, timeout=25) as r:
        while len(buf) < 4_000_000:
            chunk = r.read(65536)
            if not chunk:
                break
            buf += chunk
            m = re.search(rb"\"country\":\"([^\"]+)\"", buf)
            if m:
                return m.group(1).decode("utf-8", "replace")
            if b"\"aboutChannelViewModel\"" in buf and b"\"description\"" in buf and len(buf) > 2_500_000:
                break
    return ""

BASE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE, "channel_country_store.json")
OUT = os.path.join(BASE, "web", "channel_country.js")


def channel_ids():
    ids = set()
    for p in glob.glob(os.path.join(BASE, "web", "*.js")):
        if os.path.basename(p) in ("channel_country.js", "curation.js"):
            continue
        with open(p, encoding="utf-8") as f:
            ids.update(re.findall(r'"channel_id": ?"(UC[\w-]{22})"', f.read()))
    return ids


def country(cid):
    for i in range(2):
        try:
            return cid, fetch_country(cid)
        except Exception:  # noqa: BLE001
            time.sleep(1.5)
    return cid, None   # 조회 실패: 다음 실행에서 다시 시도


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    store = {}
    if os.path.exists(STORE):
        with open(STORE, encoding="utf-8") as f:
            store = json.load(f)
    todo = sorted(i for i in channel_ids() if i not in store)
    if "--max" in sys.argv:
        todo = todo[:int(sys.argv[sys.argv.index("--max") + 1])]
    print(f"채널 {len(store) + len(todo)}개 중 새로 조회할 것 {len(todo)}개")
    with ThreadPoolExecutor(6) as ex:
        for n, (cid, c) in enumerate(ex.map(country, todo), 1):
            if c is not None:
                store[cid] = c
            if n % 200 == 0:
                print(" ", n, "/", len(todo))
                with open(STORE, "w", encoding="utf-8") as f:
                    json.dump(store, f, ensure_ascii=False)
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False)
    out = {k: v for k, v in store.items() if v}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.CHANNEL_COUNTRY=%s;\n" % json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    from collections import Counter
    print("저장:", os.path.relpath(OUT, BASE), len(out), "개", Counter(out.values()).most_common(8))


if __name__ == "__main__":
    main()
