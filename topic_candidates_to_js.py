# -*- coding: utf-8 -*-
"""Codex 가 주제 검색(280개 영어 검색어)으로 모은 후보 영상(data/topic_candidates.json)을 사이트용 web/topic_candidates.js 로 바꾼다.

    python topic_candidates_to_js.py

필요한 필드만 옮긴다: 영상 정보 + 체험 후보 상태 + 갈래 id + 근거(제목 키워드). 영상 내용·국적은 검증된 것이 아니다(content_verified=false).
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "data", "topic_candidates.json")
OUT = os.path.join(BASE, "web", "topic_candidates.js")
KEEP = ["id", "title", "channel", "channel_id", "length", "duration_sec", "views", "subs", "country", "age_text", "published"]


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for v in data.get("videos", []):
        it = {k: v.get(k) for k in KEEP}
        it["section"] = "topic_candidate"
        it["x_status"] = v.get("experience_status")            # candidate(체험 후보) / related(관련 자료)
        it["x_cats"] = v.get("experience_categories", [])      # safety, transport, ... (12갈래 id)
        it["x_topics"] = [{"label": t.get("label"), "evidence": t.get("evidence"), "cat": t.get("category_id")} for t in v.get("experience_topics", [])]
        it["x_foreign"] = v.get("foreign_evidence", "unverified")
        it["first_seen"] = (v.get("retrieved_at") or "")[:10]
        items.append(it)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.TOPIC_CANDIDATES=%s;\n" % json.dumps(items, ensure_ascii=False))
    print("저장:", os.path.relpath(OUT, BASE), len(items), "개")


if __name__ == "__main__":
    main()
