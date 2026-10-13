# 협업 기록: 영상 길이 데이터 계약 + 담당 파일 (2026-10-14)

참여: Claude Code(사이트·배포 담당), Codex(수집·데이터 담당). 토론 2라운드, 읽기 전용 호출로 진행. 결론은 양측 합의.

## 쟁점과 결론
| 쟁점 | Claude 초안 | Codex 반박/수정 | 합의 |
|---|---|---|---|
| 길이 누락 처리 | 없으면 빈 값 | 길이 누락을 쇼츠로 판정 금지, 미확인은 `null` | `length`: 문자열\|null, `duration_sec`: 정수\|null, `is_short`: bool\|null. 누락/파싱 오류는 `null` |
| 누적 데이터 | 필드만 추가 | 기존 영상 길이가 계속 빌 수 있음 | 재발견 시 갱신하되 빈 값이 기존 값을 지우지 않음. 기존 영상은 소급 삭제 안 함 |
| 필터 위치 | discover.py | 구독자 조회 전에 공통 적용 | `find_country`/`find_other_cities` 모두 구독자 조회 전에 적용. 파싱·판별은 discover.py, 최소 길이·누락 정책은 discover.ini |
| 구독자 캐시 | 범위 밖 | None 값도 계속 재사용되는 문제 | None이면 다음 실행에 재시도, 성공값은 유지 (한 줄 수준) |
| 사이트 설정 | `window.SETTINGS` 내보내기 | 공개 다섯 값만 | `subs_low, subs_high, high_views, ratio_min, ratio_min_views` 만 노출 |

## 담당 파일
- **Codex**: `discover.py`, `discover.ini`, `build_site.py`, `tests/`
- **Claude**: `web/index.html`, `channels_watch.py`, `viral_watch.py`, `seed_channels.txt`, `.github/workflows/update.yml`, README의 '현재 구현 상태'
- **공유(변경 전 상대에게 알림)**: `AGENTS.md`, 데이터 스키마(`videos.js` 항목 필드)
- 그 외(`notifier.py`, `collect.py`)는 필요성이 확인될 때만 변경

## 격리 방식
- Codex는 별도 git worktree의 `codex/length-contract` 브랜치에서만 작업한다.
- 생성 파일(`web/videos.js`, `site_store.json`)은 커밋하지 않는다.
- Claude가 diff와 테스트 결과를 검토한 뒤 main에 병합한다.

## 합격 기준
1. `py -3.12 -m unittest discover -s tests`: `12:34→754`, `1:02:03→3723`, 누락·오류→`null`, 기존 값 보존, 분류 경계
2. `py -3.12 build_site.py`: "영상 N개 저장" 출력, 신규 영상에 길이 반영
3. 브라우저: 카드의 길이 표시, 길이순 정렬, 분류 칩, 구형 데이터와 화제 영상 병합 정상 (Claude가 확인)
4. `window.SETTINGS`에는 합의한 다섯 값만 존재
