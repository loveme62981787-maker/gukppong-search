# 2026-11-01 CC BY 영상 새로 찾기 (cc_discover.py)

기존 영상 라이선스 backfill(`license_watch.py`)과 별개로, 한국·일본·대만 여행/문화/음식 체험 주제에서 **새 CC BY 영상**을 찾아 사이트에 넣는다. 참고용 상태 정보이며 재사용 허가를 보증하지 않는다.
담당: `cc_discover.py`·`web/index.html` 연결·워크플로는 Claude. 구현 후 Codex가 diff와 테스트를 검토한다. `discover.py`는 `get/initial_data/walk/parse_*`만 가져다 쓰고 고치지 않았다.

## 제안 (검토 요청)
1. YouTube 공개 검색의 **Creative Commons 필터**(`sp=EgQQATAB` = 동영상 + CC)로 나라별 검색어를 돌려 후보를 모은다. 검색 결과는 CC 라고 믿지 않는다.
2. 후보는 영상마다 `license_watch.fetch_one/parse_watch`로 watch 페이지의 **영상 자체 라이선스 행**을 다시 읽어 `cc_by`일 때만 `verified`. 아니면 `rejected`(공개 안 함), 실패는 `pending`(6시간부터 2배 백오프, 최대 7일).
3. 저장은 분리: 후보 큐·검색 기록 `data/cc_candidates.json`(제목·채널·길이 같은 공개 메타데이터만, 설명 원문·연락처 없음) / 확인 결과는 기존 `data/video_licenses.json`에 같은 `observe` 규칙으로 합친다 / 공개는 `web/cc_videos.js`(검증 통과 + 라이선스 기록이 지금도 `cc_by`인 것만).
4. 화면: `index.html`이 `CC_VIDEOS`를 `absorb(x, null, "cc_discovery")`로 **같은 ID에 합친다** → 기존 목록 소속·저장·숨김·사용 완료·점수는 ID 기준이라 그대로. 새 영상은 `sources:["cc_discovery"]`, `country`, `first_seen`, `duration_sec`, `foreign:"unknown"`.
5. 재고 연결: `license_watch.INPUTS`에 `cc_videos.js` 추가 → CC 영상도 14일 주기 재확인 대상. 재확인이 실패해도 기록은 `cc_by`로 남고 `s=1`("지난 확인 기준") 표시가 보이며 **조용히 사라지지 않는다**. 표기가 연속 2번 안 보이면 그때 내려가고 공개에서도 빠진다.
6. 주제 거름망(기본): 181초 이상 + 해당 나라 지명이 제목에 있음 + 여행/체험 신호 + 음악·무저작권·스톡·광고·뉴스 신호 없음. **외국인 여부는 영어 제목만으로 단정하지 않고 `unknown`으로 둔다.**
7. 예산·안전: 나라마다 검색어 1개(가장 오래 안 쓴 검색어부터 돌아가며, 20시간 안에 쓴 검색어는 건너뜀), 새 후보 5개 상한, 동시 확인 2개, 검색이 한 번이라도 실패하거나 확인 중 차단성 오류가 2회 연속이면 즉시 중단(종료 코드 2). 프록시·우회 없음.
8. 워크플로: `license.yml`(4시간마다)에서 **최신 받기(`git pull --rebase`) 뒤, 라이선스 backfill 앞**에 `cc_discover.py` 실행(`continue-on-error`, 5분). 차단되면 즉시 끝나 backfill은 그대로 돈다. 새 파일(`data/cc_candidates.json`, `web/cc_videos.js`)도 같은 커밋에 포함. `update.yml`은 push 경로·저장 단계에 두 파일 추가(배포 artifact는 `web` 전체라 `cc_videos.js` 포함).

## Codex 검토 권고 (확인 부탁)
- 나라 판정이 검색어 기준 + 제목 지명 정규식이라 한일 혼합 제목은 검색한 나라로 들어간다. `discover.py` 쪽 국가 판정과 맞출지.
- CC 필터 검색은 결과 수가 적고 순위가 불안정할 수 있다. 검색어 목록(영어 8개×3국)을 넓힐지, `--per-country`를 2로 올릴지는 차단 여부를 보며 결정.
- `foreign:"unknown"`은 `_kind` 추정(제목·채널 규칙)에 맡긴다. 새 영상이 목록에 못 들어가면 '분류 보류'에 있다.
- 제외한 것: 모델/API 호출 없음, 점수 호출 없음, 설명 원문 저장 없음, 기존 `video_licenses.json` 덮어쓰기 없음(합쳐서 저장).

## 첫 실행 결과 (2026-11-01, 나라마다 검색 1·후보 5·동시 2)
- 차단 없음. 후보 15개(한국 5·일본 5·대만 5) 전부 watch 페이지에서 CC BY 로 확인(`verified` 15, `rejected` 0, `pending` 0). 공개 `cc_videos.js` 15개.
- 후보 ID: 한국 `GU0rDtNS9rY` `Ir3Y0UBB3UI` `Lv3PhYQu_xI` `RKq47l8JjE4` `W0hAkzO0dRs` / 일본 `9-A5WRZAp14` `MeqtR3l0yys` `QHMS6ScJLrQ` `eHrBTMfVdSw` `hG2oi4IHhGA` / 대만 `4Z2fSN57GJ0` `BJX5aolc2o8` `KjQdimh-pPI` `Phj4hUFJfEA` `h667SqrdEdE`
- `data/video_licenses.json`: 기존 기록 보존(CC BY 1 → 16, 전체 385). backfill은 동시에 돌리지 않았다.
- 외국인 여부·영상 내용은 확인하지 않았다(제목 기준 후보). **브라우저에서 눈으로 확인하지 못했다** (카드/탭 표시는 수동 확인 필요).

## 테스트
`python -m unittest discover -s tests` 106개 통과(신규 `tests/test_cc_discover.py` 8개: 후보 거름망, 검색 결과만으로는 공개 안 됨, 판정/백오프, 실패 시 확인된 CC 유지·`s=1`, 검색어 회전·예산, 후보 상한, 차단 즉시 중단, 같은 ID 합치기·재고 포함). 기존 node 테스트 26개 통과.

## 최종 검토
- Claude 구현 후 Codex 검토: 기존 ID 합치기 경로를 그대로 사용하고 점수·숨김·사용 완료 저장 방식은 바꾸지 않음.
- 15개 중 기존 입력 영상과 겹치는 4개는 기존 카드에 라이선스만 연결되고, 11개는 신규 영상으로 추가됨.
- 브라우저에서 RKq47l8JjE4(한국), MeqtR3l0yys(일본), 4Z2fSN57GJ0(대만)의 실제 라이선스 행을 직접 확인: 모두 크리에이티브 커먼즈 저작자 표시 라이선스(재사용 허용).
- 로컬 CC BY 탭 16개 및 16개 카드 표시 확인. 외국인 국적은 별도로 검증하지 않았으므로 확정하지 않음.
- 나라 혼합 제목은 기존 사이트 주제 판정 규칙을 유지. 검색어는 후보 검색 국가이며 국적 정보가 아님.
- Python 106개, Node 26개 통과. 공개 파일에는 영상 공개 메타데이터와 라이선스 상태만 저장.
