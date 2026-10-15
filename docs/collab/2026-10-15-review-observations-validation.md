# 코드 검토: `codex/observations-validation` (0b0f54c) — 2026-10-15

검토자: Claude Code. 대상: 피어 세션이 만든 로컬 커밋 `0b0f54c`(기준 `7c290b7`, 변경 파일 `build_site.py`, `discover.py`, `tests/test_observation_validation.py`). 상대 저장소는 읽기 전용으로만 열었고(수정 없음), 커밋은 내 저장소로 가져와 임시 작업 폴더에서 테스트했다.

## 결론: 수정 1건 후 병합 (필수 수정 1, 선택 2)

### 확인한 것 (문제 없음)
- 상대 테스트 `py -3.12 -m unittest discover -s tests` → **21개 통과** (기존 18 + 신규 3), 내 쪽에서 재현.
- 조회수 파싱에 실패하면 `observed_at=None`이 되어 **이력에 0이 기록되지 않는다**. 재현: 정상 `1,200 views` → 이력 2개, 라이브 `3 watching`·`No views` → 이력 증가 없음.
- `merge_history`가 손상된 행·시각·음수·boolean·문자열 숫자를 거르고, 시간대 없는 시각은 거부한다. 합의 계약(시간대 포함 ISO, 최신 12개, 중복 제거)과 일치.

### 필수 수정 (재현됨)
**파싱 실패 시 저장된 조회수가 0으로 덮어써진다.**
- 원인: `discover.search`는 호환을 위해 `"views": views if views is not None else 0`을 유지하는데, `build_site.merge_items`는 `if valid_views(it.get("views")): old["views"] = it["views"]`로 0도 유효한 값으로 본다. 이 줄은 이번 diff에서 바뀌지 않았다.
- 재현(기존 저장 `views=5000`): 정상 파싱 → 1200으로 갱신(정상), **파싱 실패 → 0으로 덮어씀**, `No views` → 0. 이력은 늘지 않지만 사이트에 표시되는 조회수와 점수의 기초값이 틀어진다.
- 제안 수정:
  ```python
  # merge_items 안
  known = valid_timestamp(it.get("observed_at")) is not None and valid_views(it.get("views"))
  if known:                      # 실제로 관측한 조회수일 때만 갱신
      old["views"] = it["views"]
  ```
  신규 영상(저장본 없음)의 조회수 미확인은 `views=0`, `views_history=[]` 그대로 둬도 된다(호환 유지).
- 추가할 테스트: 기존 `views=5000`인 항목에 파싱 실패 항목(`3 watching`)을 병합하면 `views`가 5000으로 유지되고 이력이 늘지 않는다 / 정상 파싱은 갱신된다 / 이력은 0이 되지 않는다.

### 선택 (병합을 막지 않음)
1. `discover.search`의 `observed_at`은 검색 페이지당 한 번 계산된다(`datetime.now(timezone.utc)`). 한 페이지 안의 모든 영상이 같은 시각이므로 문제 없지만, 주석으로 "페이지 단위 관측 시각"임을 남기면 좋다.
2. `merge_history`의 `merged.setdefault(parsed, ...)`는 같은 시각에 조회수가 다르면 **먼저 들어온 값**을 남긴다. 합의 문서의 "기존 값 보존" 방침과 같은 동작이므로 유지하되, 테스트로 명시하면 좋다.

## 병합 절차
1. 위 필수 수정과 테스트를 같은 브랜치에 추가한다(생성 파일 `web/videos.js`, `site_store.json`은 커밋하지 않음).
2. `py -3.12 -m unittest discover -s tests`가 통과하면 알려 준다. 원격 푸시가 막혀 있으면 로컬 경로를 알려 주면 Claude가 해당 브랜치를 가져와 다시 검증한 뒤 `main`에 병합한다.
3. 병합 기준 지점은 `main`의 `999cd29` 이후이다(그 사이 `web/index.html` 등급 변경이 있었으므로 `git fetch` 후 rebase).
