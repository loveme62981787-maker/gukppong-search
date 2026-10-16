# -*- coding: utf-8 -*-
"""Codex 세션이 만든 전체 영상 재분류(EXPERIENCE_ASSIGNMENTS, 제목 기준)를 사이트용 web/experience_assignments.js 로 옮긴다.

    python assignments_to_js.py <Codex 가 만든 videos.js 경로>

체험 후보(candidate)와 관련 자료(related)만 옮기고, 미분류·제외는 옮기지 않는다. 형식: {영상ID: [상태, [갈래 id...], [[꼭지 이름, 근거, 갈래 id]...]]}
영상 내용·외국인 여부는 검증된 것이 아니다(content_verified=false).
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "experience_assignments.js")


def main():
    src = sys.argv[1]
    with open(src, encoding="utf-8") as f:
        txt = f.read()
    i = txt.index("EXPERIENCE_ASSIGNMENTS=") + len("EXPERIENCE_ASSIGNMENTS=")
    data, _ = json.JSONDecoder().raw_decode(txt[i:])
    out, n = {}, {}
    for vid, a in data.items():
        st = a.get("experience_status")
        n[st] = n.get(st, 0) + 1
        if st not in ("candidate", "related"):
            continue
        out[vid] = [st, a.get("experience_categories", []),
                    [[t.get("label"), t.get("evidence"), t.get("category_id")] for t in a.get("experience_topics", [])]]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.EXPERIENCE_ASSIGNMENTS=%s;\n" % json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("전체", len(data), n, "→ 옮긴 것", len(out), os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
