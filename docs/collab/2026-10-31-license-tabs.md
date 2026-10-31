# 2026-10-31 라이선스 탭 3개 (CC BY 확인 / 무료 사용 표기 / 라이선스 미확인)

사용자 요청으로 영상별 라이선스 **상태 정보**를 보여주는 상위 탭 3개를 추가했다. 이 정보는 참고용이며 **재사용 허가를 보증하지 않는다.**
담당: 수집기 `license_watch.py`·워크플로·화면(`web/index.html`)은 Claude가 구현했다. `discover.py`의 `get`만 가져다 쓰고 고치지 않았다. 구현 후 Codex가 diff와 테스트 결과를 검토한다 (AGENTS.md 담당 표에 `license_watch.py`·`data/video_licenses.json`·`web/video_licenses.js`·`web/license_view` 로직을 추가할지는 공유 파일이라 Codex 합의 후 반영).

## 판정 규칙
| 탭 | 들어가는 조건 | 근거(고정 문구로만 표시) |
|---|---|---|
| 🪪 CC BY 확인 | watch 페이지의 **영상 자체 메타데이터 행**(제목이 `License`/`라이선스` 등)이 Creative Commons Attribution | 확인일 + 확인한 watch URL |
| 📝 무료 사용 표기 | 설명란에 **이 영상 자체**를 써도 된다는 명시적 허용 문구 | "설명란에 이 영상 자체의 무료 사용 허용 문구가 있음" (원문 비공개) |
| ❔ 라이선스 미확인 | 확인 전 / 확인 실패 / CC 표기 없음 / 알 수 없는 표기 | 사유 4가지를 카드·상단 요약에서 구분해 표시 |

- 표준 라이선스로 확인됐고 허용 문구도 없는 영상은 세 탭 모두에서 빠진다.
- CC BY 는 채널·이름·검색 스니펫·설명란의 "Creative Commons" 글자로 **추정하지 않는다.** 추천 영상 영역과 `Licensed to YouTube by` 같은 음악 행도 읽지 않는다.
- 무료 사용: 배경음악·스톡·이미지·폰트 소스 표기 문장은 건너뛰고, 부정·면책 문구(`not free to use`, `without permission`, `all rights reserved`, `무단`, `사용 금지` 등)가 설명란에 하나라도 있으면 허용으로 보지 않는다(보수적). 단순 `free to use`·`feel free to use the timestamps`·`you can use this video to plan` 같은 문장은 허용으로 보지 않는다.
- **표기가 없다고 표준으로 간주하지 않는다.** 확인했지만 CC 표기가 없는 영상은 `unknown / no_marker`(화면: "CC 표기 없음(표준으로 단정하지 않음)").

## 스키마
`data/video_licenses.json` (수집기가 쓰는 저장소, 영상 ID 키, 원문 없음)
```json
{"schema":1,"updated":"2026-10-31T14:43:02Z","items":{"<ID>":{
  "license":"cc_by|standard|unknown","unknown_reason":"never_verified|no_marker|unrecognized",
  "free_use":0,"free_rule":"en_video|ko_video|ja_video",
  "checked_at":"YYYY-MM-DD","attempted_at":"ISO","fail_count":0,"miss_count":0,"error":null}}}
```
`web/video_licenses.js` (화면용, 저장소에서 결정적으로 생성 · 손으로 고치지 않음): `window.VIDEO_LICENSES={schema,updated,scope,items:{ID:{l,u?,f?,c?,e?,s?}}}`
- `l` 상태, `u` 미확인 사유, `f` 무료 사용 규칙 코드, `c` 확인일, `e` 오류 코드, `s=1` 확인된 기록이 있는데 이번 재확인이 실패(= "지난 확인 기준").
- 내보내기는 허용 값 목록으로 걸러서 설명 원문·이메일·노션·FM이 새어 나갈 수 없다. 기록이 없는 영상 = 확인 전.
- 근거 표시는 영상 ID로 만든 watch URL(`https://www.youtube.com/watch?v=ID`)과 확인일뿐이다.

## 수집기 `license_watch.py` (표준 라이브러리만, 키 없음)
- 대상: 사이트 입력 데이터 11개(`videos/viral/experience/japan_topics/global_topics/global_topics_jp/topic_candidates/reference/benchmark/alerts/taiwan_exp`)의 모든 영상 ID를 합쳐 **중복 제거**. 읽을 수 없는 입력은 건너뛰고 나머지를 쓴다.
- 해석: `discover.get`으로 watch 페이지를 읽고 `ytInitialPlayerResponse.videoDetails.videoId`와 `currentVideoEndpoint`가 **대상 ID와 정확히 같을 때만** 인정(불일치·차단·비정상 화면은 오류 코드). 라이선스는 `ytInitialData`의 본문/참여 패널에서 `metadataRowRenderer`만 읽는다.
- 순서(공정성): ① 기록 없는 **새 영상**(first_seen 최신순) → ② **마지막 시도가 가장 오래된** 기록. `--limit`의 20%는 재확인 몫으로 남겨 오래된 영상도 계속 돈다. 별도 커서 파일 없이 `attempted_at`이 커서 역할을 하므로 전체 재고가 언젠가 한 바퀴 돈다. 재확인 주기: CC BY 14일, 그 외 30일, 실패는 6시간부터 2배씩(최대 7일), 표기가 사라져 보이면 1일.
- 안전: 동시 4(최대 8), 요청당 25초 제한(`discover.get`), 네트워크 오류는 지수 백오프로 3회, 404/410은 재시도 안 함, 전체 `--max-seconds`(기본 1500), **연속 10회 차단성 실패면 이번 실행 중단**, 25건마다 원자적 저장 + 종료 시 항상 저장·내보내기.
- 실패 처리: 확인에 실패하면 **과거에 확인된 값을 그대로 두고** `error`와 `s=1`만 붙인다. 한 번도 확인된 적 없으면 `never_verified`(미확인)로 남고 절대 승격되지 않는다. 확인된 CC BY의 표기가 한 번 안 보이는 것은 화면 구성 차이일 수 있어 **연속 2번**이어야 `unknown/no_marker`로 내린다. 설명을 못 읽었으면 이전 무료 사용 판정을 유지한다.
- 저장소 파일이 손상되면 덮어쓰지 않고 종료 코드 1로 알린다. 입력 목록을 못 읽은 경우 내보내기에서 기록을 잘라내지 않는다.
- 모드: 기본 / `--limit N` / `--export-only`(네트워크 없이 `data/` → `web/` 재생성).

## Actions
- `update.yml`: 모든 수집·알림 가져오기 **뒤**, 데이터 저장 **앞**에 `license_watch.py --limit 400` (`continue-on-error`, 30분 제한), 그 뒤 네트워크 없는 `--export-only`(실패해도 계속). 데이터 저장 단계는 파일이 없어도 실패하지 않게 파일별로 `git add`. 수동 실행에 `license_limit` 입력(처음 채우기용). 기존 단계는 그대로이고 어떤 실패도 배포를 막지 않는다.
- push 트리거 경로에 `web/video_licenses.js`, `data/video_licenses.json` 추가. 워크플로의 자동 커밋은 `GITHUB_TOKEN`으로 push하므로 다시 워크플로를 깨우지 않아 루프가 없다(기존 `web/videos.js`와 같은 방식). 원격 충돌은 AGENTS.md대로 자동 커밋(원격) 우선.
- 별도 예약 배치는 만들지 않았다. 하루 2회 × 400 = 800건/일이면 재고 약 14,400개가 약 18일에 한 바퀴 돈다(초기 backfill은 수동 실행의 `license_limit`로 앞당길 수 있다). 부족하면 이후에 전용 cron을 추가한다.

## 화면 (`web/index.html`)
- 맨 위 탭 줄에서 `auto_scores.js`(→ `taiwan_hidden.js`)가 `DOMContentLoaded`에 넣는 **🙈 숨긴 영상 탭(`#hidden-videos-tab`) 바로 뒤**에 3개를 넣는다(없으면 `#mmy`·`#ms` 뒤). `index.html`의 DOMContentLoaded 처리기는 그보다 늦게 등록돼 순서가 보장된다. 생성 파일(`auto_scores.js`)은 건드리지 않았다.
- 탭은 화면 전환이 아니라 영상 화면의 보기 필터다(`viewSel` 공유). 채점·숨긴 영상 화면에서 누르면 영상 화면으로 돌아와 적용된다.
- **브라우저에서 눈으로 확인하지 못했다**(브라우저 도구 없음). 인라인 스크립트 문법 검사와 node 테스트만 했으므로, 아래 '검증 명령'의 수동 확인이 필요하다.
- 세 탭은 목록·나라·소재·길이 필터와 AND, 탭끼리는 OR. 기존 목록에서도 영상은 그대로 보인다. 같은 영상은 `V`에 한 번이라 저장·메모·사용 완료·숨김을 그대로 공유하고, 숨김·사용 완료 영상은 기본 목록처럼 탭에서도 빠진다. "전체 초기화"는 탭 선택도 풀지만 저장 데이터는 지우지 않는다.
- 개수 = 사이트 영상(중복 제거) 기준. 미확인 = 확인 전 + 확인 실패 + CC 표기 없음(+ 알 수 없는 표기). 상단 요약 줄에 확인 범위·사유별 개수를 보여준다.
- 카드에는 고정 문구 한 줄 + 확인일 + 확인한 watch 페이지 링크 + "참고용(사용 보증 아님)". 지난 확인 기준이면 "⚠ 재확인에 실패해 지난 확인 기준" 표시. 문구는 DOM 텍스트로만 넣는다.

## 트레이드오프·한계
- 이번 환경에서 확인한 watch 페이지(표준 라이선스 영상 1개)에는 라이선스 행이 **아예 없었다.** 즉 현재 YouTube 화면에서 표준 라이선스는 "표기 없음"으로만 나타나므로 `standard`는 사실상 확정되지 않고, 대부분의 영상이 "CC 표기 없음"으로 미확인 탭에 모인다(요구사항인 '부재로 표준 추정 금지'의 직접 결과). 사유를 나눠 보이는 것으로 완화했다.
- `ytInitialData`가 없는 일부 페이지는 `no_initial_data` 오류로 남아 재시도된다(원인 조사는 아직 안 함).
- 무료 사용 판정은 정규식 규칙이라 놓치거나(영어·한국어·일본어 외, 특이한 표현) 보수적으로 제외하는 경우가 많다. 오탐을 줄이는 쪽을 택했다. 설명란이 길어도 앞 6,000자만 본다.
- CC BY 행 구조는 실제 수집에서 1건이 파싱됐지만 표본이 매우 작다. YouTube 화면 구성이 바뀌면 표기가 안 보일 수 있고, 그때는 연속 2회 규칙으로 서서히 미확인이 된다.
- 사용자가 아닌 쪽의 수집(영상 페이지 읽기)이 차단되면 새 정보는 못 얻지만 기존 기록·배포는 그대로다.

## 확인 범위 (작성 시점)
- 입력 영상 ID 14,362개 중 302개 확인(작성 중 다른 곳에서 실행된 첫 수집 기준, 약 2%): CC BY 1, 표준 0, 무료 사용 문구 0, CC 표기 없음 301, 확인 실패 3(별도 집계, 확인 수에는 불포함). 나머지는 모두 "확인 전".
- 테스트: `python -m unittest discover -s tests` (94개 통과, 신규 `tests/test_license_watch.py` 19개), `node --test tests/test_license_tabs.mjs` (5개), 기존 `tests/*.mjs` 22개 통과.

## 검증 명령 (배치/수동)
```bash
python -m unittest discover -s tests                 # 94개 (license_watch 19개 포함)
node --test tests/test_license_tabs.mjs              # 라이선스 탭 로직·배선 5개
python license_watch.py --limit 50 --workers 2       # 소량 실제 확인 (네트워크)
python license_watch.py --export-only                # data → web 재생성 (네트워크 없음)
```
브라우저로 `web/index.html`을 열어 확인: ① 맨 위 줄 🙈 숨긴 영상 뒤에 🪪/📝/❔ 3개와 개수 ② CC BY 클릭 → 카드에 안내 한 줄·확인 링크 ③ 나라·길이·목록과 함께 개수 변화 ④ 숨김 후 탭에서 빠지고 🙈 숨긴 영상에 나타남, 전체 초기화 후에도 숨김 유지 ⑤ 상단 요약의 확인 전+확인 실패+CC 표기 없음 합 = ❔ 개수.
칩 개수는 페이지를 열 때 한 번 계산하며 숨김·사용 완료 영상도 포함한다(📂 목록 개수와 같은 방식).

## 배포 전 검토 피드백과 반영 (2026-10-31, 사용자)
| # | 지적 | 반영 |
|---|---|---|
| 1 | 탭이 아래 패널 쪽 줄에 있고 스크린샷의 맨 위 '숨긴 영상' 옆이 아니다. 모드 전환·초기화·목록별 개수·실제 연결 테스트 필요 | 아래 별도 줄(`#licrow`)을 완전히 제거. `index.html`의 `<license-tabs>` 블록이 `DOMContentLoaded`(auto_scores.js→`taiwan_hidden.js`의 처리기보다 늦게 등록)에서 `#hidden-videos-tab` 바로 뒤에 3개를 삽입(`my_scores.js`의 `#mmy`·`#ms`는 대체 기준). `setMode`를 최외곽에서 감싸 영상·채널·채점·내 채점·숨긴 영상 어느 쪽으로 옮겨도 라이선스 선택을 풀고, 탭을 누르면 어느 화면에서든 영상 화면으로 돌아와 같은 목록·나라·주제·길이 필터와 함께 적용. 탭은 한 번에 하나, 선택 중에는 '🎬 영상' 강조가 꺼지고 해제·초기화하면 다시 켜짐. 개수와 상단 요약은 `render`마다 현재 선택한 📂 목록 기준으로 재계산. 테스트는 실제 블록을 가짜 DOM에서 그대로 실행(`tests/test_license_tabs.mjs`) |
| 2 | 부모 실행 결과(344회 시도·324페이지, CC BY 1·무료 0, 차단으로 서킷 브레이커 중단), 재고 14,362, 자동 800/일이면 새 영상 최신순 때문에 오래된 재고가 굶는다 | **네트워크 수집은 다시 실행하지 않았고 `data/video_licenses.json`은 그대로 보존**. 처음 확인하는 영상의 선택을 절반 최신순 + 절반 가장 오래된 순으로 변경(`pick_targets`, 중복 없이 전체 소진). 라이선스 전용 `license.yml` 추가: 4시간마다(`17 */4 * * *`) 200개, 수집 단계 최대 10분(`--max-seconds 480`), `concurrency: update`, 시작 시 `git pull --rebase`, 바뀐 것이 있을 때만 커밋·푸시 후 Pages 배포. push 트리거 없음 + `GITHUB_TOKEN` 푸시라 루프 없음. 알림 동기화로 들어온 새 영상도 매 실행이 현재 `web/*.js`에서 ID를 다시 모으므로 별도 연동 없이 새 영상 몫으로 처리됨. 모델/API 호출 없음 |
| 3 | 파서가 임의의 creativecommons.org 주소를 CC BY로 본다. 무료 사용 규칙이 너무 느슨하다 | CC BY는 ① 명시적 `Creative Commons Attribution` 표기 ② 정확한 `creativecommons.org/licenses/by/<버전>` 링크 ③ 공식 `youtube.com/t/creative_commons` 링크만. by-nc/by-sa/by-nd/cc0/publicdomain, 도메인만 있는 주소, 다른 사이트의 creative_commons 경로는 `unrecognized`. 무료 사용: `download/share`만 있는 문장, `royalty-free`만 있는 문장 패턴 삭제(허용 동사는 use/reuse/reupload/edit/repost/remix), `if you purchase/pay/subscribe`·유료/구매/구독 조건부 문장은 건너뜀(한·일 포함). 음성·부정 고정 픽스처 추가 |
| 4 | 표기가 안 보여 과거 CC BY를 유지하거나 설명을 못 읽어 과거 무료 허용을 유지할 때 `checked_at`이 오늘로 덮인다 | `checked_at` = 라이선스 증거를 마지막으로 새로 확인한 날, `attempted_at` = 마지막 시도, 새 필드 `free_checked_at` = 무료 사용 증거 날짜(내보내기 `fc`). 유지(`marker_missing`/`description_missing`)할 때는 해당 날짜를 올리지 않음. 기존 저장 기록과 호환(없으면 `checked_at`으로 대체) |
| 5 | 문서·테스트·커밋 금지·네트워크 금지 | 이 절 추가, 전체 테스트 재실행, 커밋/푸시/네트워크 수집 없음 |

주의: 이전 규칙으로 `cc_by`가 된 기존 기록 1건(`G8w5NCTlg2I`)은 새 규칙으로 다시 검증하지 않았다(네트워크 금지). 14일 재확인 주기에 새 규칙으로 다시 판정된다. 그 전까지는 확인일과 링크를 보고 직접 확인할 것.
