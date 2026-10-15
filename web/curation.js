// 소재 등급 수동 검수 결과 (근거: docs/collab/2026-10-15-grade-criteria.md, Claude + Codex 교차 검토)
// 제목·조회수 기준의 잠정 판단이며 영상 내용과 출처를 직접 검증한 것이 아니다.
//  promote : S 로 올리되, 적합성 관문과 공식 기관 채널 상한(최대 A)을 우회하지 않는다
//  demote  : 최대 A 까지만 (사건·성과가 확인되면 S 재심사). status 'pending' = 사건 확인 대기
//  exclude : 등급을 주지 않는다 (역방향·단순 팬 반응·한국과 무관 등)
window.CURATION = {
  promote: ["lN58VScauho", "WeK6MYYkjIo", "7mCYhMQaIl8", "Gg2jgCmsKj8", "A52vP_u0dqU", "0H2ipX9FKSo"],
  demote: {
    "x4k-f4J0rPY": "pending", "dw73VBUuKsY": "pending", "IbkYgEA5hGk": "pending",   // 국뽕 후킹은 강하지만 구체적 사건·성과 확인 필요
    "TuA67Mwqh94": "", "-2PBULqHSRs": "", "Ho8m7E3v96o": "", "pg3JEEOMsoc": "", "gcX4mY9f-10": "", "fhMW-iiWmOU": "", "CFou0Hx-KSY": "",
    "qXS5BbrjU5E": "", "B8LmPenTa3c": "", "fLQpKQaI0Sc": "", "JdxGtmECVZg": "", "Ir3Y0UBB3UI": "", "0KocmLSvd8Q": "", "62Ngc7djedI": "", "7vOkn4m-XCs": ""
  },
  exclude: ["kA2uKQqptIY", "FHoDHTKFzdc", "7bfyyYcPl9A", "OVQ4lkWHBzs", "ASCpSQDhFvg", "nz-afcB9EsI", "6qKxKpHzHAQ", "ZPC66cpiv-s"],
  // 영상 유형(외국인 원본 / 현지 편집·소개 / 기관·방송 / 미확인)의 공통 수동 분류. 근거: docs/collab/2026-10-15-uploader-kind.md
  //  - 채널 ID 기준(이름은 바뀔 수 있고 부분 일치는 오분류가 많아 쓰지 않는다). 영상 단위 예외는 videos 에 적는다.
  //  - note 는 확인한 근거(채널 공식 소개), reviewed 는 확인일. 개인 보정(브라우저 저장)이 이 값보다 우선한다.
  //  - kind: "foreign"=외국인 원본, "local"=현지 편집·소개(한국인·일본인 등 현지 운영 채널이 편집·번역한 소개 영상), "inst"=기관·방송, "unk"=미확인
  kind: {
    channels: {
      "UCzznO4xSV8BKnUBPyswtCUw": {kind: "inst", note: "Arirang News — 방송사 뉴스 채널(공식 소개)", reviewed: "2026-10-15"},
      "UCR-L8oZkHzgDh1ahJhH2WDQ": {kind: "inst", note: "KOREA NOW — 연합뉴스의 공식 영어 채널(공식 소개)", reviewed: "2026-10-15"},
      "UC6oRqb8L9Cv8yOu8hm4E__g": {kind: "inst", note: "Koreanet — Korea.net 공식 채널(공식 소개)", reviewed: "2026-10-15"},
      "UCtlz8pU3IiHf77V8s740-pQ": {kind: "inst", note: "VisitSeoul TV — 서울 공식 관광 채널(공식 소개)", reviewed: "2026-10-15"},
      "UCev47mZSefA6nM--tDxcxVA": {kind: "inst", note: "대한민국정부 — 정부 공식 채널(공식 소개)", reviewed: "2026-10-15"},
      "UC-VbFgagk6GJGDJgRQIMpZw": {kind: "inst", note: "MBC every1 — 방송 채널 공식 계정(공식 소개)", reviewed: "2026-10-15"},
      "UCcQTRi69dsVYHN3exePtZ1A": {kind: "inst", note: "KBS News — 방송사 뉴스 채널(공식 소개)", reviewed: "2026-10-15"},
      "UCsU-I-vHLiaMfV_ceaYz5rQ": {kind: "inst", note: "JTBC News — 방송사 뉴스 채널(공식 소개)", reviewed: "2026-10-15"},
      "UChlgI3UHCOnwUGzWzbJ3H5w": {kind: "inst", note: "YTN — 방송사 공식 채널(공식 소개)", reviewed: "2026-10-15"},
      "UCkinYTS9IHqOEwR1Sze2JTw": {kind: "inst", note: "SBS 뉴스 — 방송사 뉴스 채널(공식 소개)", reviewed: "2026-10-15"},
      "UC_Lnb8ZHqqgLbp-7hltuT9w": {kind: "inst", note: "CNA Insider — 싱가포르 방송사 CNA 산하 매체(채널 소개)", reviewed: "2026-10-15"},
      "UCJl_l4tC08dfI3oTGG9C5aA": {kind: "foreign", note: "김치귀신 마이 Kimchi Ghost Mai — 소개에 '최초 외국인 미스 춘향 김치귀신 마이'라고 적혀 있어 외국인 운영(채널명이 한글이어도 외국인 원본)", reviewed: "2026-10-15"},
      "UCg-p3lQIqmhh7gHpyaOmOiQ": {kind: "foreign", note: "영국남자 Korean Englishman — 소개에 '저는 영국남자 조쉬이고 한국어와 영어로 영상을 만든다'고 적혀 있어 외국인 운영(한국어 제목이 많아도 외국인 원본으로 분류)", reviewed: "2026-10-15"}
    },
    videos: {}
  }
};
