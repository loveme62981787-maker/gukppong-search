# 텔레그램 알림 목록 연결

사용자 확정: koreatambang-alert의 alerts CSV를 기존 사이트에 자동 반영한다. 같은 영상 ID는 하나로 합치고 기존 목록 소속과 사용 완료 기록을 유지한다. 별도 텔레그램 목록과 출처 표시를 제공한다.

추가 확정: 최소 점수 제한은 없다. 스크립트 채점 C등급은 정렬 방향과 관계없이 마지막에 보이며, 미채점과 보류는 C로 취급하지 않는다. 제목·조회수로 추정한 기존 등급과 구분한다.

## 역할 및 확인

- Codex: 비공개 CSV를 복사·커밋하지 않고 허용된 영상 필드만 내보내는 자동화, 변환 실패 시 기존 데이터 보존, 변환 테스트.
- Claude CLI: 사이트 담당 화면의 목록·배지·정렬 수정 요청. 기존 FM 스킬은 이 CLI 세션에서 접근할 수 없다고 확인했다.
- 원본 영상 스크립트 수집과 사용자의 기존 Claude 세션 FM 연결은 아직 완료되지 않았다. 새 영상에 추정 점수를 공식 채점 결과로 붙이지 않는다.
- Claude의 첫 정렬 구현은 내 채점 정렬에서만 C를 내리는 문제가 있어 Codex가 반박·수정을 요청했다. Claude가 모든 정렬에서 C를 미채점·보류보다 뒤로 배치하도록 수정했고, Codex가 8개 정렬 × 양방향 회귀 테스트와 브라우저 목록 표시를 검증했다.
- 사용자 요청으로 만료 없는 Contents 읽기 전용 토큰을 알림 저장소 하나에 한정해 생성하고 ALERTS_TOKEN Secret 등록을 확인했다. 토큰 값은 파일에 저장하지 않았다.

## 운영

GitHub Actions의 ALERTS_TOKEN은 비공개 알림 저장소의 Contents 읽기 권한이 필요하다. Secrets 등록 여부와 실제 실행 성공은 별도로 확인해야 한다. 토큰이 없거나 checkout이 실패하면 기존 web/alerts.js를 유지한다. CSV는 alerts_src/alerts에서 직접 읽으며 원본은 공개 저장소나 Pages 산출물에 넣지 않는다.

로컬 재생성: `python alerts_to_js.py --dir <비공개 alerts 폴더>`.
검증: Python 테스트 25개, Node 테스트 11개 통과. 알림 영상 251개 변환. `node --test tests/test_alert_sort.mjs tests/test_scorer.mjs`.
