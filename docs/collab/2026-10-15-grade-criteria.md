# 협업 기록: 소재 등급(S/A/B) 기준과 데이터 계약 (2026-10-15)

참여: Claude Code(점수·등급·화면), Codex(수집·병합·테스트). 토론 2라운드, 읽기 전용 호출. 사용자의 정의: "국뽕 채널 소재로 가장 좋은 영상 = 사건·조회수·이슈가 될 만한 소재".
※ 제목·조회수 기준의 잠정 판단이며 영상 내용과 출처를 직접 검증한 결과가 아니다.

## 합의
1. **적합성 관문이 먼저, 점수는 그다음.** 대상국(한국/일본) → 반응 주체(외국인이 체험·반응) → 구체적 체험 또는 사건. 관문을 통과하지 못하면 점수가 높아도 등급 없음. 수동 승격도 관문과 공식 기관 상한을 우회하지 않는다.
2. **유형 2가지**: 체험형(외국인의 상시 체험·반응, 외국인 체험·반응이 근거) / 사건형(한국·일본 관련 구체적 사건·성과, 확인 가능한 근거가 근거).
3. **점수 보정**: 조회수 점수는 1천만까지 확대, 조회수·비율 이중 보상 완화, 구독자 1천 미만은 비율 점수 제외, 이슈 단어에서 그룹명(BTS 등) 제거, '세계 최초'/'최초' 중복 계산 제거, 정부·공식 기관 채널은 최대 A.
4. **S의 개수는 결과**: '상위 몇 %'가 아니라 관문 + 점수 기준선 + 수동 검수로 정한다.
5. **역방향·단순 팬 반응 제외**: 한국인이 외국 것을 보고 놀라는 영상, 중국이 소재인 일본 반응 영상, 아이돌끼리의 BTS 리액션 등.

## 이견과 결론
| 영상 | Claude | Codex | 결론 |
|---|---|---|---|
| 0H2ipX9FKSo 폴란드 대통령 열병식 K-방산 | S(사건형) | 조건부 S | **S(사건형)**. 공식 기관 채널이 아닐 때 |
| IbkYgEA5hGk 강대국도 놀란 군사력 | S(사건형) | A, 사건·성과 확인 시 재심사 | **A** (검증 대기) |
| dw73VBUuKsY 전 세계가 한국을 두려워하는 이유 / x4k-f4J0rPY 최후의 승자는 한국 | S 유지 | A (후킹은 가점일 뿐 사건 확인을 대체 못 함) | **A** (검증 대기) |
| 7vOkn4m-XCs Pooh in Korea 첫 BTS 콘서트 | A | 제외 → A 동의 | **A** |

## 수동 검수 결과 (영상ID)
- **S 승격(5+1)**: lN58VScauho, WeK6MYYkjIo, 7mCYhMQaIl8, Gg2jgCmsKj8, A52vP_u0dqU, 0H2ipX9FKSo
- **A 강등**: x4k-f4J0rPY, dw73VBUuKsY, TuA67Mwqh94, -2PBULqHSRs, Ho8m7E3v96o, pg3JEEOMsoc, gcX4mY9f-10, fhMW-iiWmOU, CFou0Hx-KSY, IbkYgEA5hGk, qXS5BbrjU5E, B8LmPenTa3c, fLQpKQaI0Sc, JdxGtmECVZg, Ir3Y0UBB3UI, 0KocmLSvd8Q, 62Ngc7djedI, 7vOkn4m-XCs
- **등급에서 제외**: kA2uKQqptIY, FHoDHTKFzdc, 7bfyyYcPl9A, OVQ4lkWHBzs, ASCpSQDhFvg, nz-afcB9EsI, 6qKxKpHzHAQ, ZPC66cpiv-s

## 담당과 데이터 계약
- **Claude**: `web/index.html`(관문·유형·점수·등급·UI·근거 표시), `web/curation.js`(수동 검수 ID 목록)
- **Codex**: `discover.py`, `discover.ini`, `build_site.py`, `tests/` — 영상 항목에 `observed_at`(시간대 포함 ISO), `subs_checked_at`, `views_history`([[관측시각, 조회수], ...] 최대 12개) 추가
  - 실제 관측·확인할 때만 기록, 캐시 재사용으로 갱신하지 않음. 결측은 `null`, 과거 시각은 추정하지 않음.
  - 병합 시 기존 유효 값·이력 보존, 같은 시각 중복 관측 제거, 최신 12개 유지. 구형 데이터는 오류 없이 동작, 소급 변경 없음.
  - 사이트는 유효 관측이 2개 이상일 때만 조회수 증가 속도를 점수에 쓰고, 그 외에는 기존 방식(하위 호환).
- **격리**: Codex는 별도 worktree(`codex/views-history`)에서만 작업하고 생성 파일(`web/videos.js`, `site_store.json`)은 커밋하지 않는다. Claude가 diff와 테스트를 검토한 뒤 main에 병합.

## 합격 기준
1. Codex: `py -3.12 -m unittest discover -s tests` — views_history 보존·상한(12)·중복 제거, 결측 null, 구형 데이터 호환
2. Claude(브라우저): 관문 통과 영상만 등급이 붙음, 제외 ID가 S/A/B 어디에도 없음, 승격 ID가 관문·공식 기관 상한을 우회하지 않음, 구형 데이터(이력 없음) 정상, 콘솔 오류 없음
3. 구현 후 서로 검토
