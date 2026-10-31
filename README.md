# 국뽕 영상 서칭

외국인이 한국·일본을 방문한 후기/브이로그 영상을 유튜브에서 자동으로 찾아 **카드형 사이트**로 보여주고, 새 영상은 **텔레그램**으로 알려주는 프로젝트입니다.
유튜브 검색 페이지를 직접 읽기 때문에 **YouTube API 키가 필요 없습니다.** 파이썬 기본 기능만 사용합니다(외부 패키지 없음).

## 구조

| 파일 | 역할 |
|---|---|
| `discover.py` | 유튜브 검색·필터링·구독자 수 확인 (핵심 검색 로직) |
| `discover.ini` | 구독자/조회수 기준, 제외할 채널·영상, 검색 기간 설정 |
| `build_site.py` | `discover.py`를 호출해 결과를 누적 저장 → `web/videos.js` 생성, `--notify` 시 텔레그램 발송 |
| `notifier.py` | 텔레그램/이메일 알림, 채널 RSS 읽기 |
| `collect.py` | 텔레그램 봇으로 보낸 링크·사진을 CSV로 저장 (사이트와 별개, 미연결) |
| `channels_watch.py` | 비슷한 컨셉 채널 자동 발견·분석(롱폼/숏폼/둘 다 분류) → `web/channels.js` |
| `viral_watch.py` | 오래된 영상 포함, 조회수·구독자 대비 조회수가 폭발한 화제 영상 수집 → `web/viral.js` (영상 길이 포함) |
| `reference_watch.py` | `reference_channels.txt` 에 적은 별도 레퍼런스 채널의 동영상 탭 전체 수집 → `web/reference.js` (사이트의 '📌 별도 레퍼런스' 목록, 다른 목록에는 섞이지 않음) |
| `experience_watch.py` | 외국인 체험 영상(야구장·한복·찜질방·템플스테이 등) 수집 → `web/experience.js`. 체험 종류 기준(`TOPICS`)은 여기서만 관리 |
| `japan_topics_watch.py` | 일본 영상 중 "아직 비어 있는데 터지는 주제" 4가지(가족 첫 방일·서프라이즈 / 일식·첫입 리액션 / 이자카야·밤 술자리 / 접객·친절·배려)를 먼저 수집 → `web/japan_topics.js`. 주제 기준(`TOPICS`)은 여기서만 관리 |
| `global_topics_watch.py` | "글로벌 콘텐츠" 12개 갈래·140꼭지(안전·치안, 대중교통, 편의·속도, 음식, 카페, 밤·놀거리, 뷰티·쇼핑, 도시·풍경, 전통, 사회 시스템, 예의·정서, K팝) 중 외국인이 한국에서 사용·경험·말하는 영상을 수집 → `web/global_topics.js`. 꼭지 기준(`GROUPS`)은 여기서만 관리. 수집이 오래 걸려 아침 실행과 수동 실행에서만 돈다 |
| `web/curation.js` | 소재 등급(S/A/B) 수동 검수 결과 — 승격·강등·제외 영상ID. 등급은 클릭률 예측이 아니라 "소재 검토 우선순위"이며, 적합성 관문(대상국·외국인 체험/사건·역방향 제외)을 통과한 영상에만 붙는다. 기준과 근거는 `docs/collab/2026-10-15-grade-criteria.md` |
| `seed_channels.txt` | 벤치마킹 시작점 채널 이름 목록 (여기에 한 줄씩 추가) |
| `web/index.html` | 사이트 화면 (정적 페이지, `videos.js`만 읽음) |
| `web/scorer.js` | 🎯 국뽕 점수 기준(6항목 100점·등급·한국/일본 12갈래)과 브라우저 '간이 채점기' (참고용 규칙 기반). 사이트의 '점수 기준' 화면이 이 파일을 그대로 읽는다 |
| `web/scores.js` | 🎯 스크립트 채점 기록 (Claude 스킬 결과를 손으로 옮긴 파일, 생성 파일 아님). 영상 ID가 같으면 카드에 점수 배지가 붙는다 |
| `license_watch.py` | 사이트의 모든 영상 ID(중복 제거)의 watch 페이지를 읽어 영상 자체의 CC BY 표기·설명란 무료 사용 문구를 기록 → `data/video_licenses.json`, `web/video_licenses.js` (🪪 라이선스 탭 3개). 참고용이며 재사용 허가를 보증하지 않음. 근거: `docs/collab/2026-10-31-license-tabs.md` |
| `web/videos.js` | 자동 생성되는 데이터 파일 (직접 수정하지 않음) |
| `site_store.json` | 누적 영상·구독자 캐시 (다음 실행의 "새 영상" 구분용) |
| `.github/workflows/update.yml` | 매일 자동 갱신 + GitHub Pages 배포 |

## 실행 방법

### 내 PC에서
요구사항: Python 3.12 (Windows는 `py -3.12`).

```bash
py -3.12 build_site.py            # 새 영상 검색 → web/videos.js 갱신
py -3.12 build_site.py --notify   # 위 + 새 영상 텔레그램 알림
```

그 뒤 `web/index.html`을 브라우저에서 열면 됩니다. Windows에서는 `업데이트하고_열기.bat`을 더블클릭해도 같습니다.
처음 실행은 구독자 수를 확인하느라 몇 분 걸립니다.

### 텔레그램 알림 설정 (선택)
토큰은 코드/저장소에 넣지 않습니다. 아래 중 하나로만 설정하세요.

- 환경변수: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- 로컬 파일 `config.ini` (`.gitignore`로 제외됨):
  ```ini
  [telegram]
  bot_token = 여기에_봇_토큰
  chat_id = 여기에_내_chat_id
  ```
- GitHub Actions: 저장소 Settings → Secrets and variables → Actions 에 같은 이름으로 등록

봇 토큰은 텔레그램 @BotFather(`/mybots`), chat ID는 봇에 메시지를 보낸 뒤 `getUpdates`에서 확인합니다.

### 자동 업데이트 + 공개 (GitHub Pages)
1. 저장소 Settings → Pages → Source 를 **GitHub Actions** 로 선택
2. Actions 탭 → "영상 업데이트 + 사이트 배포" → Run workflow
3. 이후 매일 한국시간 07:00, 18:00에 자동 실행
4. 주소: `https://loveme62981787-maker.github.io/gukppong-search/`

## 🎯 국뽕 점수 (스크립트 채점)
기존 🏆 등급(제목·조회수 기준 검토 우선순위)과 별개로, 스크립트 전문을 읽고 매기는 100점 만점 점수입니다. 항목: 포인트 밀도 25 · 반응 강도 20 · 반전 20 · 희소성 15 · 썸네일화 10 · 호의 일관성 10. 등급: S 85+ · A 70~84 · B 55~69 · C 54 이하. 한국판·일본판은 같은 기준에 갈래만 다릅니다.
- 사이트 위쪽 **🎯 국뽕 점수** 버튼: 📏 점수 기준 / 🏆 채점 기록 / 🧮 간이 채점기(참고용, 오차 ±12점 가정)
- 점수를 추가하려면 `web/scores.js` 의 `items` 에 한 줄을 넣습니다 (필드 설명은 파일 맨 위 주석). `web/scorer.js`·`web/scores.js` 를 고치면 push 만으로 바로 배포됩니다.
- 간이 채점기 테스트: `node --test tests/test_scorer.mjs`
- 협업 기록: `docs/collab/2026-10-20-score-layer.md`

## 현재 구현 상태

완료
- [x] 한국/일본 방문 영상 검색 및 필터 (`discover.py`, 백업에서 복구)
- [x] 서울·부산 외 지방 도시 영상 별도 수집
- [x] 결과 누적 저장, 60일 지난 영상 정리, NEW 표시
- [x] 카드형 사이트: 국가/지방/저장 필터, 검색, 구독자 구간 필터, 정렬 4종, 카드 내 재생, 즐겨찾기(브라우저 저장), 다크모드
- [x] 텔레그램 새 영상 알림 코드 (`--notify`)
- [x] GitHub Actions 자동 갱신/배포 설정 파일
- [x] 🪪 라이선스 탭 3개(CC BY 확인 / 무료 사용 표기 / 라이선스 미확인) + `license_watch.py` 수집기·Actions 단계 (코드 완료, Codex 검토 대기)

미확인 / 남은 일
- [ ] 라이선스 확인 backfill: 사이트 영상 약 14,000개 중 일부만 확인됨. 수동 실행의 `license_limit` 또는 매일 자동 실행(400개씩)으로 채워진다. 내 PC: `python license_watch.py --limit 300`, 화면 파일만 다시 만들기: `python license_watch.py --export-only`, 테스트: `node --test tests/test_license_tabs.mjs`
- [ ] **GitHub Actions에서 유튜브 검색이 막히지 않는지 아직 검증 안 됨.** 막히면 영상 0개가 나올 수 있음 → 내 PC에서 `build_site.py` 실행 후 `web/videos.js`, `site_store.json`을 커밋하는 방식으로 대체
- [ ] Pages 첫 배포 실행 확인
- [ ] 텔레그램 토큰/chat ID 새로 설정 (이전 값은 복구되지 않음)
- [ ] 영상 재생(임베드) 실제 클릭 테스트
- [ ] `collect.py`(텔레그램 봇으로 링크 수집)를 사이트에 연결할지 결정
- [ ] 모바일 화면 점검, 일본 영상 비율/품질 조정

## 주의
- 저장소가 Public이므로 사이트와 코드가 모두 공개됩니다. **API 키, 토큰, `.env`, `config.ini`는 커밋하지 마세요.**
- 영상은 유튜브 공식 임베드/링크로만 보여주며 내려받지 않습니다.

협업 규칙은 [`AGENTS.md`](AGENTS.md)를 참고하세요.
