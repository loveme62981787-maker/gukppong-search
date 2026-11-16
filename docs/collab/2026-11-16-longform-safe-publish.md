# 롱폼 체험 수집 + 데이터 안전 게시 (2026-11-16)

## 1. 저장 충돌 원인과 해결
- 증거: run 43841193201 이 옛 커밋(e647a97)을 checkout 해 수집 → 최신(0b09525)에 `git pull --rebase` → `hot_shorts_store.json`·`web/hot_shorts.js` 충돌. concurrency 그룹 `update` 만으로는 대기 실행이 옛 checkout 을 쓰는 것을 막지 못한다.
- `hot_shorts.yml`/`longform.yml`: `checkout ref: main, fetch-depth: 0` + 작업 시작 시 `git merge --ff-only origin/main`.
- `safe_publish.py`: 수집분(ours)을 메모리에 잡고 → 대상 파일만 HEAD 로 되돌림 → `fetch` + `merge --ff-only` → 원격 저장분에 ID 기준 합치기(`hot_shorts_watch.merge_stores` / `longform_watch.merge_stores`) → 화면 JS 재생성 → 커밋 → `push origin HEAD:main`. 거절되면 우리 커밋만 취소하고 처음부터 재시도(기본 5회). 생성 JS 는 rebase 로 합치지 않는다. 대상 파일 외 원격 코드·수동 변경은 건드리지 않는다. 로컬에 갈라진 커밋이 있으면 덮어쓰지 않고 실패한다.
- 합치기 규칙: 채널은 더 늦게 확인한 쪽 통계 기준 + 영상·쇼츠 확인 캐시 합집합(같은 ID 는 더 늦은 확인), 백필 커서는 충돌 시 원격 보존(건너뛴 구간 없이 재수집으로 따라잡음), `updated` 는 최댓값.
- 실패하면 `::error::` 로 남고 `verdict` 작업이 실행을 실패로 표시한다(사이트 배포는 계속). `update` concurrency 그룹과 Pages 배포 구조는 그대로.
- 테스트: `tests/test_safe_publish.py` — 로컬 bare 저장소에서 옛 checkout·서로 다른 ID 동시 갱신, push 경합(재시도), 원격 코드 보존, 오래된 값 비덮어쓰기, 갈라진 이력 실패, 계속 거절 시 실패.

## 2. 롱폼 수집 (`longform_watch.py`)
- 길이 720초 이상, 조회수 하한 없음, Shorts·라이브 제외. 실행당 search.list 최대 12개(국가별 4개 × 100유닛), 하루 2회 ≈ 2,400유닛.
- 판정은 제목만: 대상국 정확히 1개 + 여행·체험 단어 + (외국인 신호 `foreign_title` | 한국어 제목+일본·대만 지역명 `ko_region`). 한국 소재는 외국인 신호 필수. 뉴스·정치·잡학·음악·드라마·북한 등 배제. 모두 추정이며 제작자 국적·외국인 여부를 확정하지 않는다.
- 사이트에 이미 있는 ID 는 저장·집계하지 않는다(`on_site_already` 로만 센다). `index.html` 은 `absorb(x, null, "longform_exp")` 로 같은 ID 를 기존 영상에 출처만 덧붙인다.
- 비공개 보고: `--report-dir` 로 국가별 이전 저장 수·사이트에 이미 있던 수·새 반영 ID 를 JSON 으로 남긴다.

## 남은 일
- 실제 GitHub Actions 동시 실행에서의 push 경합은 로컬 bare 저장소로만 검증했다.
- 제목 기반 추정이라 일부 오탐(예: 사연 편집 채널)이 있을 수 있다 — 채널 시청 검증은 하지 않았다.
