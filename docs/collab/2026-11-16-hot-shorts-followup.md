# 터진 쇼츠 후속 수정 (2026-11-16)

Argon 검토 + 사용자 추가 지시 반영. 브라우저·네트워크 호출 없이 파일 수정과 단위 테스트만 했다.

## UI
- 상단 탭(`#mhs`) 삭제. 기존 `📂 목록` 줄의 `🗂 분류 보류` 바로 오른쪽에 `🔥 터진 쇼츠 (한국/일본/대만)` 버튼 3개.
- 누르면 길이 필터와 무관한 독립 화면(`#hsview`)으로 전환. 다른 목록 칩을 누르면 영상 화면으로 복귀. 저장·사용 완료·숨김·메모는 기존 `favs/done/hidden/memos` 공유.

## 판정 (hot_shorts_watch.py)
- 탭 첫 페이지 부재만으로 False 확정 금지 → unknown. False 는 길이 3분 초과(`too_long`)만.
- `membership_cache`: 표본 전체의 쇼츠 확인 결과(영상ID→여부·확인일)를 채널별 저장. 탭이 막혀도 표본 비율 유지. 예전 `flags` 는 True 만 이어받는다(저장분은 이번에 변환; 통계는 다음 정기 수집에서 새 규칙으로 재계산).
- 쇼츠 중심은 보류 포함 전체 표본 기준 유지, 보류 제외 비율(`shorts_ratio_known`, `sample_known`)은 병기.
- 국가 우선순위: `country_override` > `country_hint` > 등록 국가.
- 구독자 대비 배수는 실제 views/subs 표시, 선별용 `sub_multiple_floor`(분모 최소 1000) 분리. `min_abs_views` 100만 이상은 무조건 통과. 중앙값 0 방어.
- 시드 `exclude`(주제 무관 채널 제외), 제목 주제 키워드 `topic_hit/topic_hits`(보조 신호, 자동 배제 아님).
- `DISCOVER_QUERIES` 에 TW 추가(`zh-Hant`), 검색 지역을 country_hint 로 사용.

## @lianxinfanyin
- 대만 목록에 사용자 지정 참고 채널(`user_reference`)로 포함. 최근 20개 중 16개 확인(80%), `쇼츠 중심 기준 미충족`·`전부 쇼츠 아님`으로 표시.

## 미해결
- 기존 시드 중 주제 무관 채널은 네트워크 없이 확인 못 해 `exclude` 지정 안 함.
- 저장분 통계는 다음 수집 때 새 규칙으로 갱신.
