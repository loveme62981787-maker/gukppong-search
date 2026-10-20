// 국뽕 점수 기준과 '간이 채점기' (브라우저·node 공용)
// 정밀한 점수는 사람(또는 Claude 스킬)이 스크립트를 읽고 매기고, 이 파일의 estimate() 는 키워드 규칙으로 계산한 '참고용 예비 점수'다.
// 기준 설명(RUBRIC·GRADES)은 사이트의 '점수 기준' 화면이 그대로 읽어 쓴다. 기준을 바꾸면 사이트 설명도 같이 바뀐다.
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GukScore = api;
})(typeof self !== "undefined" ? self : this, function () {
  // ---- 1) 점수 기준 (100점) ----
  const RUBRIC = [
    {key: "density", label: "포인트 밀도", max: 25, desc: "국뽕 포인트가 몇 개이고 10분당 몇 개 나오는가. 5개 이상이면 만점권",
      hi: "10분에 6개 이상 (예: 울릉도·독도 영상 약 8개/10분)", lo: "한국 이야기가 20%뿐이고 나머지는 준비·잡담"},
    {key: "reaction", label: "반응 강도", max: 20, desc: "실제 감탄사·충격 발언·표정 변화가 있는가. '예쁘다' 수준이면 중간, '평생 최고' 같은 말이 있으면 높음",
      hi: "'내가 먹어 본 최고의 새우예요', '인생에서 이렇게 달라 보인 적이 없어요'", lo: "'예뻐요, 좋아요'만 반복"},
    {key: "twist", label: "반전·낙차", max: 20, desc: "기대와 다르게 흘러간 순간(의심→감탄, 불만→인정). 한 문장으로 요약되는 반전이 있는가",
      hi: "'벌금 낼 줄 알았는데 경찰이 응원해 줬다'", lo: "코스를 순서대로 소개만 함"},
    {key: "rarity", label: "소재 희소성", max: 15, desc: "흔한 '서울 1일 코스'가 아니라 아직 덜 쓰인 갈래·지방·장면인가",
      hi: "울릉도·독도, 시코쿠, 한옥 2박, 백화점 키즈 층", lo: "경복궁→명동→남산, 도쿄 쇼핑 하울"},
    {key: "thumb", label: "썸네일화", max: 10, desc: "한 장면·한 마디로 압축되는가 (표정, 대비되는 사물, 짧은 대사)",
      hi: "유리 바닥 케이블카, 파란 대문, 레몬이 튀어나오는 캔", lo: "설명 위주 가이드"},
    {key: "favor", label: "호의 일관성", max: 10, desc: "영상 전체 흐름이 호의적인가. 불평·논란·광고 구간은 감점",
      hi: "불평이 거의 없고 '고마워요, 한국'으로 끝남", lo: "숙소 혹평·바가지·비하 발언·스폰서 구간"}
  ];
  const GRADES = [
    {g: "S", min: 85, label: "바로 쓸 만한 소재"},
    {g: "A", min: 70, label: "좋은 소재 (구간 편집으로 더 좋아짐)"},
    {g: "B", min: 55, label: "참고할 만한 소재 (손질 필요)"},
    {g: "C", min: 0, label: "단독으로는 약함 (장면만 컷으로)"}
  ];
  const gradeOf = n => (GRADES.find(x => n >= x.min) || GRADES[GRADES.length - 1]).g;
  // 포인트 1개 = 외국인이 (a) 한국·일본의 구체적 장면을 직접 겪고 (b) 놀람·감탄·비교 같은 반응을 보인 것. 반응이 약하면 0.5개
  const POINT_RULE = "외국인이 한국·일본의 구체적 장면을 직접 겪고, 놀람·감탄·비교·충격 같은 반응을 보인 것이 1개예요. 장면만 있고 반응이 약하면 0.5개, 같은 장면의 반복은 1개로 합쳐요.";

  // ---- 2) 국뽕 포인트 갈래 (한국 12갈래 / 일본 12갈래) ----
  const CATS = {
    kr: [
      {id: "safety", name: "안전·치안", words: ["safe", "safety", "cctv", "walk alone", "walking alone", "at night", "nothing will happen", "안전", "치안"]},
      {id: "transport", name: "대중교통·이동", words: ["subway", "metro", "ktx", "express train", "airport railroad", "arex", "t-money", "tmoney", "climate card", "bus ", "taxi", "지하철", "버스", "택시", "교통"]},
      {id: "convenience", name: "편의·속도", words: ["convenience store", " cu ", "gs25", "7-eleven", "seven eleven", "delivery", "kiosk", "24 hours", "24-hour", "wifi", "wi-fi", "internet speed", "same day", "self-service", "편의점", "배달", "키오스크"]},
      {id: "food", name: "음식·식문화", words: ["bbq", "barbecue", "kimchi", "tteokbokki", "chicken", "bibimbap", "samgyeopsal", "pork belly", "side dish", "stew", "soup", "noodle", "market food", "street food", "restaurant", "삼겹살", "치킨", "떡볶이", "비빔밥", "반찬", "맛집"]},
      {id: "cafe", name: "카페·디저트", words: ["cafe", "café", "coffee", "dessert", "bakery", "salt bread", "latte", "matcha", "bingsu", "cake", "카페", "디저트", "빙수"]},
      {id: "night", name: "밤·놀거리", words: ["night market", "nightlife", "karaoke", "noraebang", "arcade", "pc bang", "photo booth", "claw machine", "night view", "han river", "야경", "노래방", "포토부스", "한강"]},
      {id: "beauty", name: "뷰티·쇼핑", words: ["olive young", "skincare", "skin care", "sheet mask", "cosmetic", "daiso", "k-beauty", "makeup", "hair salon", "shopping", "fashion", "올리브영", "다이소", "화장품", "쇼핑"]},
      {id: "nature", name: "도시·자연·풍경", words: ["view", "scenery", "mountain", "river", "sunset", "sunrise", "island", "beach", "nature", "hike", "hiking", "lake", "landscape", "cable car", "풍경", "산", "바다", "섬"]},
      {id: "tradition", name: "전통·문화유산", words: ["palace", "hanok", "hanbok", "temple", "tradition", "heritage", "unesco", "museum", "folk village", "궁", "한옥", "한복", "사찰", "문화유산"]},
      {id: "society", name: "사회 시스템·교육", words: ["immigration", "tax refund", "tax free", "tax-free", "public toilet", "recycling", "healthcare", "hospital", "system", "free entry", "입국", "택스리펀", "면세"]},
      {id: "people", name: "사람·예의·정서", words: ["kind", "friendly", "helpful", "polite", "locals", "staff", "welcoming", "warm", "generous", "gave me", "친절", "배려", "정"]},
      {id: "pop", name: "K팝·팬덤·콘텐츠", words: ["k-pop", "kpop", "idol", "k-drama", "kdrama", "filming location", "bts", "blackpink", "concert", "fan ", "드라마", "아이돌", "팬"]}
    ],
    jp: [
      {id: "hospitality", name: "접객·친절·배려", words: ["omotenashi", "hospitality", "staff", "friendly", "kind", "helpful", "polite", "접객", "친절", "배려"]},
      {id: "clean", name: "치안·청결", words: ["clean", "safe", "safety", "spotless", "trash", "no litter", "청결", "치안", "깨끗"]},
      {id: "transport", name: "대중교통·정확성", words: ["shinkansen", "bullet train", "on time", "punctual", "suica", "pasmo", "subway", "train", "신칸센", "지하철", "교통"]},
      {id: "konbini", name: "편의점·자판기", words: ["konbini", "convenience store", "7-eleven", "seven eleven", "family mart", "familymart", "lawson", "vending machine", "편의점", "자판기"]},
      {id: "food", name: "일식·첫입", words: ["sushi", "ramen", "tempura", "udon", "soba", "wagyu", "yakitori", "tonkatsu", "onigiri", "matcha", "omelette", "curry", "초밥", "라멘", "우동"]},
      {id: "izakaya", name: "이자카야·밤 술자리", words: ["izakaya", "standing bar", "sake", "yokocho", "highball", "이자카야", "야키니쿠"]},
      {id: "family", name: "가족·서프라이즈", words: ["my family", "kids", "my daughter", "my son", "parents", "surprise", "가족", "아이"]},
      {id: "tradition", name: "전통·문화유산", words: ["shrine", "temple", "ryokan", "onsen", "kimono", "festival", "castle", "tea ceremony", "신사", "료칸", "온천", "축제"]},
      {id: "nature", name: "도시·자연·계절 풍경", words: ["fuji", "cherry blossom", "autumn leaves", "view", "island", "mountain", "beach", "deer", "sunset", "scenery", "후지", "벚꽃", "단풍", "풍경"]},
      {id: "otaku", name: "쇼핑·애니·게임", words: ["akihabara", "anime", "manga", "pokemon", "pokémon", "uniqlo", "don quijote", "donki", "figure", "gachapon", "arcade", "daiso", "애니", "포켓몬", "다이소"]},
      {id: "manners", name: "사람·예의·질서", words: ["queue", "line up", "orderly", "respectful", "manners", "no one crosses", "bow", "예의", "질서"]},
      {id: "price", name: "물가·가성비", words: ["cheap", "affordable", "reasonable", "so cheap", "yen", "price", "가성비", "저렴"]}
    ]
  };

  // ---- 3) 반응·반전·부정·주의 어휘 ----
  const STRONG = ["amazing", "incredible", "insane", "unbelievable", "best", "so good", "delicious", "stunning", "breathtaking", "wow", "love it", "loved it", "obsessed", "perfect", "can't believe", "cannot believe", "never seen", "never had", "10 out of 10", "unreal", "magical", "heaven", "crazy cheap", "so cheap", "blown away", "speechless", "life-changing", "fantastic", "awesome", "gorgeous", "mind-blowing", "dinguerie", "incroyable", "increíble", "espectacular", "buenísimo", "대박", "최고", "감동", "미쳤", "놀라"];
  const MEDIUM = ["beautiful", "nice", "cute", "pretty", "impressive", "impressed", "cool", "lovely", "great", "so clean", "really good", "tasty", "yummy", "i like", "i love", "comfortable", "peaceful", "relaxing", "fresh", "surprised", "sweet", "맛있", "예쁘", "멋지", "깨끗", "친절", "chulo", "guay", "génial", "masarap", "ang ganda"];
  const NEG = ["tired", "exhausted", "hate", "annoying", "annoyed", "disgusting", "terrible", "awful", "horrible", "expensive", "overpriced", "rude", "crowded", "packed", "scam", "dirty", "disappointed", "disappointing", "not good", "bad", "worst", "chaotic", "too hot", "too cold", "pissed", "stressful", "wasted", "refund", "불평", "별로", "실망", "비싸"];
  const TWIST = [/(didn'?t|did not|never|wasn'?t|was not) (really )?(expect|think)/, /not expecting/, /to my surprise/, /surprisingly/, /turned out/, /i thought .{0,60}\bbut\b/, /expected .{0,60}\b(but|and)\b/, /plot twist/, /actually .{0,30}\b(better|good|amazing|great)\b/, /unexpected/, /(shocked|stunned)/, /better than (i|we) (expected|thought)/, /changed my (mind|mind about)/, /i was wrong/];
  const SPONSOR_RE = /sponsor|promo code|use my code|discount code|link in (the )?description|#ad\b|paid partnership|affiliate|klook|hotels\.com|\bdji\b|osmo|booking\.com|thanks to .{0,30} for (sponsoring|making)/i;
  const SENSITIVE_RE = /dokdo|takeshima|liancourt|comfort women|prostitut|north korea|racis[tm]|homeless|terrorist/i;
  const PROFANITY_RE = /\b(fuck\w*|shit\w*|bitch\w*|bastard\w*|asshole\w*|cunt\w*)\b/gi;
  // 흔한 코스(희소성 감점)와 덜 쓰인 지역(가점)
  const CLICHE = ["myeongdong", "gyeongbokgung", "namsan", "n seoul tower", "hongdae", "gangnam", "itaewon", "dongdaemun", "shibuya", "shinjuku", "akihabara", "asakusa", "harajuku", "tokyo tower", "starfield"];
  const RARE_PLACES = ["jeonju", "gyeongju", "ulleung", "dokdo", "andong", "hahoe", "sokcho", "gangneung", "tongyeong", "yeosu", "jeju", "muju", "suwon", "daegu", "shikoku", "kyushu", "okinawa", "hokkaido", "kagoshima", "kumamoto", "hakuba", "shirakawa", "matsushima", "awaji", "takamatsu", "tokashiki", "nara", "miyajima", "hiroshima", "fuji"];
  // 영어 판별: 흔한 영어 단어 비율. 낮으면 다른 언어 스크립트로 보고 정확도가 낮다고 알린다
  const EN_STOP = ["the", "and", "is", "it", "to", "we", "of", "in", "that", "this", "you", "so", "was", "for", "on", "are", "with", "have", "but", "my"];

  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const norm = s => ` ${s.toLowerCase()} `;
  const has = (t, words) => words.some(w => t.includes(w));
  const count = (t, words) => words.filter(w => t.includes(w)).length;

  // 스크립트 정리: 음악·박수 표시, 시간 표시(00:12, (1분 7초))를 지우고 문장 단위로 나눈다. 마지막 시간표시가 있으면 분량(분)을 추정한다
  function prepare(text) {
    const raw = String(text == null ? "" : text);
    let maxSec = 0;
    raw.replace(/\((\d{1,2}):(\d{2})(?::(\d{2}))?\)|\b(\d{1,2}):([0-5]\d)(?::([0-5]\d))?\b/g, (m, a, b, c, d, e, f) => {
      const h = a !== undefined ? [a, b, c] : [d, e, f];
      const sec = h[2] !== undefined ? +h[0] * 3600 + +h[1] * 60 + +h[2] : +h[0] * 60 + +h[1];
      if (sec < 6 * 3600 && sec > maxSec) maxSec = sec;
      return m;
    });
    const musicTags = (raw.match(/\[(music|musica|musique|musika|applause|laughter|singing|sighs|snorts)[^\]]*\]/gi) || []).length;
    const clean = raw
      .replace(/\[[^\]]{0,40}\]/g, " ")
      .replace(/\((\d{1,2}):(\d{2})(?::(\d{2}))?\)/g, " ")
      .replace(/\b\d{1,2}:[0-5]\d(?::[0-5]\d)?\b/g, " ")
      .replace(/https?:\/\/\S+/g, " ")
      .replace(/\s+/g, " ").trim();
    const sentences = clean.split(/(?<=[.!?。！？])\s+|\n+/).map(s => s.trim()).filter(s => s.length > 2);
    const words = clean ? clean.split(/\s+/).length : 0;
    return {clean, sentences, words, musicTags, maxSec};
  }

  function languageHint(clean, words) {
    if (words < 30) return "unknown";
    if (/[가-힣]/.test(clean) && (clean.match(/[가-힣]/g) || []).length > clean.length * 0.2) return "ko";
    const tokens = clean.toLowerCase().split(/\s+/);
    const hit = tokens.filter(w => EN_STOP.includes(w.replace(/[^a-z]/g, ""))).length;
    return hit / tokens.length > 0.18 ? "en" : "other";
  }

  // 포인트 찾기: 문장마다 갈래 단어가 있고 반응어가 같은 문장(강한 반응은 앞뒤 한 문장까지)에 있으면 센다. 같은 갈래는 4문장 안에서 하나로 합친다
  function findPoints(sentences, cats) {
    const found = []; // {cat, idx, value, text}
    sentences.forEach((s, i) => {
      const t = norm(s);
      cats.forEach(c => {
        if (!has(t, c.words)) return;
        const near = [sentences[i - 1], s, sentences[i + 1]].filter(Boolean).map(norm).join(" ");
        const strong = has(t, STRONG) || has(near, STRONG);
        const mid = has(t, MEDIUM);
        const value = strong ? 1 : mid ? 0.5 : 0;
        if (value) found.push({cat: c, idx: i, value, text: s});
      });
    });
    const merged = [];
    cats.forEach(c => {
      let last = null;
      found.filter(f => f.cat === c).forEach(f => {
        if (last && f.idx - last.idx <= 4) { if (f.value > last.value) { last.value = f.value; last.text = f.text; } last.idx = f.idx; }
        else { last = {cat: c, idx: f.idx, value: f.value, text: f.text}; merged.push(last); }
      });
    });
    return merged;
  }

  // 간이 채점: 반환값의 모든 항목은 키워드 규칙으로 센 값이라 사람이 읽고 매긴 점수와 다를 수 있다 (참고용)
  function estimate(text, opts) {
    const o = Object.assign({ver: "kr", minutes: null}, opts || {});
    const cats = CATS[o.ver === "jp" ? "jp" : "kr"];
    const p = prepare(text);
    const flags = [];
    const lang = languageHint(p.clean, p.words);
    if (p.words < 250) flags.push("스크립트가 짧아요(250단어 미만). 점수가 불안정해요.");
    if (p.musicTags / Math.max(1, p.sentences.length) > 0.3 || p.words < 120 && p.musicTags > 5) flags.push("음악·효과음 표시가 많고 대사가 적어요. 점수를 내기 어려운 영상일 수 있어요.");
    if (lang === "other") flags.push("영어·한국어가 아닌 스크립트로 보여요. 이 채점기는 영어·한국어 위주라 정확도가 많이 낮아요.");
    if (lang === "ko") flags.push("한국어 스크립트는 감탄어·갈래 어휘가 적어서 정확도가 낮아요.");

    const lower = norm(p.clean);
    if (SPONSOR_RE.test(p.clean)) flags.push("광고·협찬 문구가 있어요. 해당 구간은 편집에서 빼거나 표기를 확인하세요.");
    const sens = p.clean.match(SENSITIVE_RE);
    if (sens) flags.push("민감 주제 단어가 있어요(" + [...new Set(sens.map(x => x.toLowerCase()))].join(", ") + "). 인용·썸네일에 쓰기 전에 맥락을 확인하세요.");
    const prof = (p.clean.match(PROFANITY_RE) || []).length;
    if (prof >= 5) flags.push("욕설이 " + prof + "번 이상 있어요. 그대로 쓰기 어려워요.");

    const found = findPoints(p.sentences, cats);
    const points = found.reduce((a, f) => a + f.value, 0);
    const perCat = cats.map(c => ({id: c.id, name: c.name, points: found.filter(f => f.cat === c).reduce((a, f) => a + f.value, 0)})).filter(c => c.points > 0).sort((a, b) => b.points - a.points);

    // 분량: 직접 입력한 분 > 스크립트의 마지막 시간 표시 > 단어 수(분당 140단어)로 추정
    const minutes = o.minutes > 0 ? o.minutes : p.maxSec > 120 ? p.maxSec / 60 : Math.max(1, p.words / 140);
    const per10 = points / minutes * 10;

    const n = Math.max(1, p.sentences.length);
    const strongN = p.sentences.filter(s => has(norm(s), STRONG)).length, midN = p.sentences.filter(s => has(norm(s), MEDIUM)).length;
    const r = (2 * strongN + midN) / n * 100;
    const twistN = p.sentences.filter(s => TWIST.some(re => re.test(s.toLowerCase()))).length;
    const negN = p.sentences.filter(s => has(norm(s), NEG)).length;
    const negRate = negN / n * 100;
    const catN = perCat.length;
    const lowerAll = lower;
    const cliche = count(lowerAll, CLICHE), rare = count(lowerAll, RARE_PLACES);
    const shortStrong = p.sentences.filter(s => has(norm(s), STRONG) && s.split(/\s+/).length <= 10).length;

    const parts = {
      density: points < 3 ? clamp(Math.round(4 + points * 2), 0, 10) : clamp(Math.round(5 + 3.2 * per10), 0, 25),
      reaction: Math.round(20 * Math.min(1, r / 40)),
      twist: clamp(twistN * 4, 0, 20),
      rarity: clamp(Math.round(4 + catN * 1 + Math.min(rare, 3) * 2 - Math.min(cliche, 4) * 1.2), 0, 15),
      thumb: shortStrong ? clamp(Math.round(2 + shortStrong * 1.2), 0, 10) : 2,
      favor: clamp(Math.round(10 - negRate * 0.8 - (SPONSOR_RE.test(p.clean) ? 1 : 0)), 1, 10)
    };
    const total = Object.values(parts).reduce((a, b) => a + b, 0);
    const seen = new Set(), quotes = found.filter(f => f.value >= 1 && !seen.has(f.text) && seen.add(f.text)).sort((a, b) => b.text.length - a.text.length).slice(0, 6).map(f => ({cat: f.cat.name, text: f.text.length > 160 ? f.text.slice(0, 157) + "…" : f.text}));
    return {
      total, grade: gradeOf(total), points: Math.round(points * 2) / 2, parts, perCat, quotes, flags,
      minutes: Math.round(minutes * 10) / 10, per10: Math.round(per10 * 10) / 10, words: p.words, sentences: p.sentences.length, lang,
      detail: {strongN, midN, twistN, negN, cliche, rare}
    };
  }

  return {RUBRIC, GRADES, CATS, POINT_RULE, gradeOf, estimate, _prepare: prepare};
});
