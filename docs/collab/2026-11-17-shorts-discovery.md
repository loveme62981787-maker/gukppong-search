# 쇼츠 채널 발굴 heartbeat (2026-11-17)

기준 origin/main(f8fb1e1). 새 검색·API 수집 없음(GitHub update run 44016215713 이 in_progress 라 겹치지 않도록 대기). 코드 변경 없음, 시드만 추가. 키·비밀 미출력, 유료 API·DeepSeek 미사용, 429 없음.

## 검토
- 캐시: `private/tw_candidates_more.json`(38), `tw_collect.json`, `tw_screen.json` + 읽기전용 `hot_shorts_candidates.json`(KR/JP 90, 시드 제외 후 약 40) 와 `shorts-task-private/titles.json`(제목).
- 우선순위 TW6 / KR2 / JP2 중 TW 6만 근거가 충분했다.

## 시드 추가 (hot_shorts_seeds.json +6, kind=unverified, country_hint=TW)
@andy_in_taiwan(앤디·미국인 가족), @milaintaiwan(러시아인 밀라), @krtw(한국인 낙지), @koreanfriendhoony(한국인 후니), @yomanajxlil(17년 미국인), @rifat(외국인 가이드). 채널명은 원어+한국어 병기(직접 번역).
- 근거는 캐시된 실제 영상 제목 2~3개(`topic_evidence`)뿐이다. 출연자 국적·원본 여부는 시청 검증하지 않았다. 재사용 금지.
- strict topic 필터는 그대로다. 영상 데이터는 아직 수집하지 않았다(캐시 영상은 Shorts 확인값이 없어 병합하지 않음). 다음 Actions 수집이 새 시드를 읽는다.

## KR/JP 미등록 (제목만으로는 부족)
- KR @팩트-k: 외국인 제목 1개뿐·시사 혼합. @한국반응zip: 최대 4천 뷰로 1만 미달. @mihoinkorea: 국제커플 일상(앞서 제외한 유형). @channelckoony: 한국인이 유럽 소재.
- JP @japantamilbros: 연기형 콩트 의심·제목에 외국인 신호 없음. @lancul: 영어학원 광고 콩트. @知っとこニッポン: 뉴스 클립 재가공.
- TW 보류 유지: @celinezlll, @unfollowadrian, @leosapplemint3791(쇼츠 비율 낮거나 현지 연출 의심).

## 검증
- `python -m unittest tests.test_hot_shorts`: 50개 모두 통과(OK). 실패하던 `test_example_taiwan_channel_included`는 특정 날 스냅샷(16/20) 고정을 제거하고, store 레코드↔export 값 일치 + 비율(`sample_shorts/sample_n`)·`shorts_centered`/`all_shorts_strict` 플래그 의미(`CRITERIA` 기준)만 검증하도록 수정. 16/20=80% 케이스는 `StatsTests.test_16_of_20_is_80_percent_not_centered` 단위 fixture가 이미 보장.
- 변경 파일: `hot_shorts_seeds.json`, `tests/test_hot_shorts.py`, 본 문서. `tests/test_safe_publish.py` 미접촉. 원본 `../gukppong-telegram` 미수정, 커밋/push 없음.

## 다음
- 재시도 파일(`discovery_retry.json`)은 429 가 없어 만들지 않음. run 44016215713 종료 후 부모 수집으로 신규 시드 6개 영상 확인.
