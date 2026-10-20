# AGENTS.md — Claude / Codex 협업 가이드

이 저장소는 사람과 AI 코딩 에이전트(Claude Code, Codex)가 함께 작업합니다. 개요와 실행 방법은 [README.md](README.md)를 먼저 읽으세요.

## 절대 규칙
- `.env`, `config.ini`, API 키, 봇 토큰, 비밀번호를 **읽어서 출력하거나 커밋하지 않는다.** 비밀 값은 환경변수/GitHub Secrets로만 쓴다. 저장소는 Public이다.
- `web/videos.js`, `site_store.json`은 `build_site.py`가 만드는 **생성 파일**이다. 손으로 고치지 말고 스크립트를 다시 실행한다.
- 파이썬은 **표준 라이브러리만** 쓴다(외부 패키지 추가 시 먼저 사용자에게 확인).
- 사용자 대화와 주석, 사용자에게 보이는 문구는 **한국어**로 쓴다.

## 코드 규칙
- 검색/필터 로직은 `discover.py`, 저장/내보내기는 `build_site.py`, 알림은 `notifier.py`에 둔다. 역할을 섞지 않는다.
- 사이트(`web/index.html`)는 빌드 도구 없는 단일 정적 파일을 유지한다. `videos.js`만 읽고 서버를 필요로 하지 않는다.
- 기존 코드의 주석 밀도와 이름 규칙(한국어 주석, snake_case)을 따른다.

## 확인 방법
```bash
py -3.12 build_site.py     # 에러 없이 끝나고 "영상 N개 저장" 출력되는지
```
그 뒤 `web/index.html`을 브라우저로 열어 카드/필터/정렬이 동작하는지 본다.

## 담당 파일 (2026-10-14 합의, 근거: docs/collab/2026-10-14-length-contract.md)
- **Codex**: `discover.py`, `discover.ini`, `build_site.py`, `tests/`
- **Claude**: `web/index.html`, `channels_watch.py`, `viral_watch.py`, `seed_channels.txt`, `.github/workflows/update.yml`, README '현재 구현 상태', `web/scorer.js`·`web/scores.js`(🎯 국뽕 점수 기준·채점 기록)·`tests/test_scorer.mjs`(Codex 검토 요청)
- **공유**: `AGENTS.md`, 데이터 스키마 — 바꾸기 전에 상대에게 알린다.
- 중요한 변경은 서로 해결책을 제안하고 반박·수정하는 토론(2~3라운드)을 거치고, 합의 내용과 역할은 `docs/collab/`에 기록한다. 구현 후에는 상대가 diff와 테스트 결과를 검토한다.

## 협업 방식
- 작업 전에 `git pull`로 최신 상태를 받는다. 한 번에 한 에이전트가 같은 파일을 고치지 않도록, 작업 범위를 커밋 메시지에 적는다.
- 커밋은 작게, 메시지는 한국어로 "무엇을 왜" 적는다.
- `.github/workflows/update.yml`이 매일 `site_store.json`, `web/videos.js`를 자동 커밋한다. 충돌이 나면 **자동 커밋 쪽(원격)을 우선**하고 코드 변경만 다시 적용한다.
- 미완료 항목의 목록은 README의 "현재 구현 상태"에서 관리한다. 작업을 끝내면 체크 상태를 갱신한다.
