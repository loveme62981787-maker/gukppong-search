# 2026-11-01 CC 영상 카드 업로드 날짜

문제: `CC_VIDEOS`의 `published`가 빈 문자열이라 카드에 날짜가 없었다. 담당: Claude. 구현 후 Codex가 diff와 테스트를 검토한다.

## 변경
- `license_watch.parse_watch`: **영상 ID가 일치한 watch 페이지**의 `playerMicroformatRenderer.publishDate`(없으면 `uploadDate`)를 **한국시간(UTC+9) 기준** `YYYY-MM-DD`로 바꿔 결과 `published`로 전달한다(시간대가 있는 ISO 시각은 KST로 변환, 날짜만 있으면 그대로, 형식이 틀리면 거부). 앞 10자만 자르면 `2025-01-30T18:00:06-08:00`(한국 화면 2025-01-31)처럼 하루가 어긋난다. 실제 달력 날짜가 아니거나 2005년 이전·내일 이후면 `""`. 라이선스 판정에는 영향이 없고 `observe`/`video_licenses.json`에도 저장하지 않는다.
- `cc_discover.apply_verdict`가 `published`를 후보 저장소에 보존(빈 결과·실패로 기존 날짜를 지우지 않음), `export_js`가 내보낸다. 앞으로 발견·재확인되는 영상은 자동으로 채워진다.
- `python cc_discover.py --backfill-dates`: 검색·라이선스 재평가 없이, 확인된 후보 중 날짜가 빈 것만 순차(최대 2동시)로 읽는다. 실패하면 값을 그대로 두고, 차단성 오류가 2번 연속이면 중단(종료 코드 2).
- `python cc_discover.py --refresh-dates`: 확인된 영상 **전부**의 날짜를 같은 함수로 다시 읽어 갱신한다(예전 앞 10자 값 교정). 실패하면 기존 값 보존.
- `web/index.html`: 확인된 CC 날짜(`pub_actual`)는 화제 영상의 상대 날짜(`age_text`)·추정 `published`보다 먼저 표시하고(툴팁: 한국시간 기준), 없을 때만 상대 날짜로 대체한다. `absorb`가 기존 ID의 빈 `published`도 채운다(있는 값은 덮어쓰지 않음). 카드 채널 옆은 `업로드 YYYY-MM-DD`, 없으면 `업로드 날짜 미확인`(수집일 `first_seen`은 업로드로 표시하지 않음, 화제 영상은 기존 `age_text`). `cc_videos.js` 캐시 버전 갱신.
- 설명 원문·이메일은 저장하지 않는다(날짜 문자열만 읽는다).

## 확인
테스트: 시간대 하루 경계(서부 전날 저녁·KST 자정·UTC)·날짜만·잘못된 형식, 재수집 갱신/실패 보존, 실제 날짜가 viral보다 우선, 날짜 추출(타임존 포함 문자열, uploadDate, 잘못된/미래/빈 날짜, 다른 영상 ID 페이지), 판정 후 날짜 보존, 보충(빈 것만·실패 유지·라이선스 기록 불변), 차단 중단, 중복 ID 빈 날짜 병합, 카드 표기. `tests/test_license_tabs.mjs`의 `video_licenses.js` 배선 검사는 캐시 버전 쿼리(`?v=...`)를 허용하도록 고쳤다(이전부터 실패 중이던 항목).
실행: 기존 CC BY 15개 모두 날짜 수집(실패 0, 차단 없음). 브라우저 화면 확인은 하지 못했다.
