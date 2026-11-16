# 대만 외국인 체험·반응 쇼츠 채널 추가 발굴 (2026-11-16)

기준 커밋 56c0d4c. 공식 YouTube Data API(기존 환경 키, 값은 출력·저장하지 않음)만 사용, 추가 결제·GUI·git commit/push 없음. 코드(`.py`/`.js`) 변경 없음. 바뀐 것은 시드·저장·화면 데이터뿐이다.

## 진단: 왜 TW 신규가 2개뿐이었나
- 직전 실행(HEAD~1 → HEAD)에서 TW 공개 영상은 797 → 799, 신규 2개. 채널은 35개 그대로.
- 기존 수집(`hot_shorts_watch.py` 기본 실행, 6시간 cron)은 **시드에 등록된 채널만** 새 영상·조회수 갱신·과거 이어받기를 한다. 새 채널을 찾는 일은 별도 `--discover`(검색 100유닛/쿼리)이고 Actions 에서는 돌리지 않는다 → 발굴과 갱신은 완전히 별개이며, 등록 채널이 늘지 않는 한 신규는 거의 늘지 않는다.
- 등록 TW 35채널 중 22개는 공개 영상 0~2개다(소규모·제목 필터 보류). 보류는 TW 835개로 공개(799)보다 많다. 제목에 외국인+대만 신호가 둘 다 없으면 공개하지 않는 엄격 필터 때문이며 이 필터는 그대로 두었다.
- 기존 `hot_shorts_candidates.json`(사용자 기존 파일)은 읽지도 덮어쓰지도 않았다.

## 실제 발굴·수집
- 새 TW 검색: 쿼리 24개 × 정렬 2(viewCount/relevance) 시도 → 앞쪽 일부만 성공, 이후 **HTTP 429**(쿼터/속도 제한). 성공분에서 채널 167개. (쿼터를 더 쓰지 않으려고 재시도하지 않음; 다음 쿼터 갱신 후 나머지 쿼리를 돌리면 더 나올 수 있음)
- 선별 깔때기: 167 → 시드·제외목록 이미 있음 16 → 신규 151 → 제목에 외국인+대만 신호 없음 87 제외 → 64 → 뉴스·정치 공식계정·언어교육·본인 채널(@世界讚台灣)·이전 판단 제외(@肌肉山山 등) 16 제외 → 48을 기존 코드(`collect_channel`)로 검증(쇼츠 확인·1만뷰·제목 신호) → **10채널 시드 등록**.
- 후보 저장: `private/tw_candidates_more.json`(비공개·미등록, `auto_public:false`; `private/` 는 `.git/info/exclude` 로 로컬 제외). 나머지 38개는 아래 사유로 미등록.

## 등록한 신규 10채널 (hot_shorts_seeds.json, kind=unverified)
채널명 번체(원어) + 한국어 병기(`name_ko`, 직접 번역이라 공식 표기가 아닐 수 있음), `topic_evidence` 에 공개 제목 2~3개 저장. 공개는 기존 엄격 필터를 통과한 영상만.

| 채널 | 구독자 | 공개 쇼츠(1만+·필터 통과) | 제목 필터 보류 |
|---|---|---|---|
| @justinintaiwan Justin in Taiwan 我不是歪國人 | 25.2만 | 305 | 148 |
| @broccolivlog Broccoli Vlog / 花椰菜 Vlog | 8.9만 | 208 | 83 |
| @manahello 我是Mana | 54.6만 | 118 | 373 |
| @xiaming513 夏明 Daniel | 1.2만 | 44 | 11 |
| @有璟嘿喲 요찡 | 45.2만 | 24 | 288 |
| @tw-universe 臺灣尋奇 | 80.7만 | 20 | 238 |
| @mamalucy Mama Lucy 英國媽媽在台灣 | 4.1만 | 15 | 4 |
| @clairesenglish 克雷兒 Claire | 42만 | 11 | 267 |
| @loganbeck 小貝米漿 Logan Beck | 59.7만 | 9 | 36 |
| @livsig 恩希 & 席格 | 2,200 | 8 | 4 |
- 합계 TW 공개: 채널 35 → 45, 영상 799 → 1,561(신규 762). `last_error` 없음.
- 모두 제목 근거 선별이다. **출연자 국적·원본 여부는 확인하지 않았다**(시청 검증 아님). `reaction_edit`/`unverified` 는 재사용 가능 표시가 아니며 원본으로 쓰지 말 것.

## 미등록 38개 (제외·보류 사유별)
| 사유 | 개수 | 예 |
|---|---|---|
| 실제 체험형이나 이번 10개 상한 밖(보류, 다음 확장 후보) | 10 | @andy_in_taiwan, @koreanfriendhoony, @milaintaiwan, @krtw, @rifat, @celinezlll, @leosapplemint3791, @yomanajxlil, @langgedaddy, @unfollowadrian |
| AI 내레이션형 의심(@lianxinfanyin 유사, 개별 확인 필요) | 7 | @斯琴途説, @台味記事, @清茶評局, @暮色观察, @第n空间, @城市筆記簿, @世界萬花筒 |
| 외국인 거리 인터뷰형(보류) | 2 | @jaychentaiwan, @peggyfoshow |
| 제목 근거 2개 미만 / 공개 쇼츠 거의 없음 | 11 | @sergthedreamer, @eddylive, @happyjoyday, @kellymosa, @kaobeicold 등 |
| 타 채널 인용 재업로드·집계 | 1 | @taiwannumberone888 |
| 중국/정치 소재(외국인 체험 아님) | 3 | @英國莉莉-e1n, @台灣小師妹, @hellotaiwanese |
| 현지인·연출 일상 | 3 | @loloh, @gafamily4, @happyhazel2930 |
| 스탠드업 코미디(체험·반응 아님) | 1 | @evandanger5443 |
- 사전 제외 16(뉴스·정치 공식계정·언어교육 등): @setn, @chinatimes, @ftv_news, @udn-video, @dwchinese, @thestormmedia, @chingte_taiwan, @amazingtalker, @thaiwithbow, @世界讚台灣(본인), @肌肉山山 등.
- 위 표 합 38 = 검증 48 − 채택 10. 그룹별 목록은 `private/tw_candidates_more.json`.

## 보존·검증
- 기존 저장 채널 75개는 신규 병합 전후 완전 동일(KR/JP 포함). 공개 영상 JP 4,272 / KR 1,654 변화 없음, 기존 공개 영상 유실 0. 백업은 `private/` 에만 둠.
- `python -m unittest tests.test_hot_shorts` 50개 통과.
- 변경 파일: `hot_shorts_seeds.json`(+10, 추가만), `hot_shorts_store.json`, `web/hot_shorts.js`(재생성), 본 문서. `tests/test_safe_publish.py`(사용자 기존 수정)와 `hot_shorts_candidates.json`(사용자 기존 파일)은 건드리지 않았고 커밋 대상에도 넣지 말 것.

## 한계
- 검색이 429 로 중단돼 발굴 범위가 쿼리 일부에 한정된다. 쿼터 회복 후 나머지 쿼리·한국어/일본어 쿼리로 추가 발굴 가능.
- `shorts_centered=false` 채널(@tw-universe, @loganbeck, @manahello, @clairesenglish, @livsig)은 최근 표본에 롱폼이 섞여 있다. 공개된 영상은 쇼츠 확인 규칙을 통과한 것만이다.
- 부모가 검토 후 게시한다(커밋·push 미실행).
