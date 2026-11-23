// -*- coding: utf-8 -*-
/**
 * web/bundles_mode_a.js (v2.0 — 무제한 대량 묶음 + 3~10분 알짜 클립 복원 + 6대 테마 묶음 + 무한 스크롤 & 리믹스)
 * ============================================================================================================
 * 모드 A: @daoyingtan (島映談) & @旅人眼中的台灣 벤치마크 기반
 * 1) 나라별 100% 독립 분리 (🇹🇼 대만 / 🇰🇷 한국 / 🇯🇵 일본)
 * 2) 기존 60묶음 제한 완전 해제 + 3~10분(181~600초) 외국인 원본 클립까지 전량 복원하여 나라별 1,000~1,800+ 묶음 생성
 * 3) 6가지 묶음 테마 지원:
 *    - 🍱 종합 3코스 합본 (1부 교통·편의·치안 + 2부 야시장·미식 + 3부 인심·지방·풍경)
 *    - 🚇 교통·편의점·치안 집중 합본 (3~4팀 모두 인프라·치안)
 *    - 🍜 야시장·로컬 미식 집중 합본 (3~4팀 모두 미식·먹방)
 *    - 🤝 현지인 인심(人情味/情/おもてなし)·감동 집중 합본
 *    - 🗺️ 비수도권 지방 소도시·자연·환도 집중 합본
 *    - ⚡ 첫방문 충격·반전·체류 연장 집중 합본
 * 4) 🔄 새로운 3~4팀 조합으로 계속 섞기(리믹스 시드) & 스크롤 시 자동 추가 로딩(무한 스크롤)
 */
(function () {
  const COURSE_RULES = {
    tw: [
      {
        slot: 1,
        badge: "1부 · 📱 파생 쇼츠 #1 (교통·편의·치안)",
        color: "#0ea5e9",
        label: "🚇 타이베이 지하철(捷運)·고속철도·만능 편의점(超商)·새벽 치안",
        re: /mrt|metro|subway|train|high speed rail|hsr|airport|7-?eleven|seven.?eleven|family.?mart|convenience|safe|night|clean|easycard|bus|bike|youbike|wifi|hospital|捷运|捷運|高鐵|超商|便利|治安|安全|乾淨/i,
      },
      {
        slot: 2,
        badge: "2부 · 📱 파생 쇼츠 #2 (야시장·미식)",
        color: "#f59e0b",
        label: "🍜 대만 야시장(夜市)·우육면·루로우판·아침식사(豆漿/蛋餅)·버블티·열대과일",
        re: /food|eat|night market|market|breakfast|beef noodle|boba|bubble tea|dumpling|xiao long bao|stinky tofu|mango|street food|restaurant|cafe|tea|fruit|hot ?pot|夜市|美食|小吃|牛肉麵|滷肉飯|豆漿|珍珠奶茶/i,
      },
      {
        slot: 3,
        badge: "3부 · 📱 파생 쇼츠 #3 (로컬 인심·자연·환도)",
        color: "#10b981",
        label: "🤝 대만 인정미(人情味)·지우펀/아리산/타이난/가오슝/화롄·타이둥 환도 감동",
        re: /people|kind|friendly|help|love|emotional|cry|tears|jiufen|alishan|tainan|kaohsiung|hualien|taitung|kenting|sun moon lake|taroko|yilan|taichung|island|nature|mountain|cycling|人情味|熱情|感動|九份|阿里山|台南|高雄|花蓮|台東|環島/i,
      },
    ],
    kr: [
      {
        slot: 1,
        badge: "1부 · 📱 파생 쇼츠 #1 (치안·교통·편의)",
        color: "#0ea5e9",
        label: "🚨 한국 새벽 치안·노트북 자리 비우기·지하철/KTX·편의점·20분 속도",
        re: /safe|alone at night|laptop|cafe|lost|wallet|subway|metro|train|ktx|arex|bus|airport|incheon|convenience|7-?eleven|cu\b|gs25|fast|delivery|wifi|clean|restroom|glasses|치안|안전|노트북|분실물|지하철|교통|편의점|배달|화장실/i,
      },
      {
        slot: 2,
        badge: "2부 · 📱 파생 쇼츠 #2 (한식·시장 먹방)",
        color: "#f59e0b",
        label: "🍖 한국 고깃집(K-BBQ)·무료 반찬·광장시장·치킨·한강 라면·베이커리 카페",
        re: /food|eat|bbq|meat|pork|beef|kimchi|ramen|market|street food|chicken|fried|side dish|banchan|restaurant|bakery|coffee|dessert|bingsu|tteokbokki|음식|한식|고깃집|삼겹살|반찬|시장|치킨|라면|먹방|빵집|카페/i,
      },
      {
        slot: 3,
        badge: "3부 · 📱 파생 쇼츠 #3 (한국인의 정·지방·문화)",
        color: "#10b981",
        label: "❤️ 한국인의 정(情)·부산/제주/경주/안동/울릉도·한복/KBO 야구장 응원 감동",
        re: /people|kind|friendly|help|free|grandma|ajumma|hanbok|palace|baseball|busan|jeju|gyeongju|jeonju|andong|ulleung|dokdo|suwon|countryside|village|hiking|mountain|temple|cry|tears|love|한국인|인심|친절|할머니|사장님|부산|제주|경주|전주|안동|시골|한복|경복궁|야구장|감동/i,
      },
    ],
    jp: [
      {
        slot: 1,
        badge: "1부 · 📱 파생 쇼츠 #1 (편의점·신칸센·치안)",
        color: "#0ea5e9",
        label: "🚅 일본 편의점(콘비니)·자판기·신칸센 정시 운행·코반/분실물·청결",
        re: /konbini|convenience|7-?eleven|family.?mart|lawson|vending|shinkansen|bullet train|train|subway|suica|station|taxi|safe|clean|spotless|lost|wallet|police|koban|airport|편의점|자판기|신칸센|전철|택시|치안|안전|청결|분실물|コンビニ|新幹線/i,
      },
      {
        slot: 2,
        badge: "2부 · 📱 파생 쇼츠 #2 (일식·이자카야 미식)",
        color: "#f59e0b",
        label: "🍣 일본 라멘·스시·서서 마시는 이자카야·와규·돈카츠·규카츠·말차 디저트",
        re: /food|eat|ramen|sushi|izakaya|tachinomi|wagyu|beef|gyudon|udon|soba|tonkatsu|gyukatsu|curry|onigiri|egg sandwich|matcha|bakery|market|street food|cheap|라멘|스시|초밥|이자카야|와규|규동|우동|돈카츠|편의점 음식|ラーメン|寿司|居酒屋/i,
      },
      {
        slot: 3,
        badge: "3부 · 📱 파생 쇼츠 #3 (오모테나시·지방·전통)",
        color: "#10b981",
        label: "♨️ 일본의 배려(오모테나시)·교토/규슈/시코쿠/오키나와/료칸 온천·가족 서프라이즈",
        re: /people|kind|polite|service|omotenashi|hospitality|help|kyoto|osaka|hokkaido|okinawa|fukuoka|kyushu|shikoku|nara|hiroshima|fuji|hakuba|shirakawa|onsen|ryokan|shrine|temple|tradition|family|surprise|kids|countryside|love|cry|배려|친절|서비스|교토|오사카|홋카이도|규슈|시코쿠|온천|료칸|감동|京都|温泉/i,
      },
    ],
  };

  const REGIONAL_RE = {
    tw: /tainan|kaohsiung|taitung|hualien|yilan|taichung|jiufen|shifen|alishan|sun moon lake|kenting|taroko|penghu|kinmen|yehliu|keelung|chiayi|nantou|pingtung|cycling|round island|台南|高雄|台東|花蓮|宜蘭|台中|九份|十分|阿里山|日月潭|墾丁|太魯閣|環島|타이난|가오슝|타이둥|화롄|이란|타이중|지우펀|스펀|아리산|컨딩|환도/i,
    kr: /busan|jeju|gyeongju|jeonju|andong|ulleung|dokdo|suwon|gangneung|sokcho|yeosu|tongyeong|geoje|daegu|daejeon|chuncheon|damyang|mokpo|suncheon|namhae|부산|제주|경주|전주|안동|울릉|독도|수원|강릉|속초|여수|통영|거제|대구|춘천|담양|목포|순천/i,
    jp: /kyoto|osaka|hokkaido|okinawa|fukuoka|kyushu|shikoku|nara|hiroshima|miyajima|nagoya|sapporo|kobe|kanazawa|nagasaki|kumamoto|kagoshima|beppu|yokohama|kamakura|hakone|otaru|sendai|hakuba|shirakawa|takamatsu|matsushima|tokashiki|izu|fuji|교토|오사카|홋카이도|오키나와|후쿠오카|규슈|시코쿠|히로시마|삿포로|가나자와|가고시마|벳푸|하코네|하쿠바|시라카와고/i,
  };

  const SHOCK_RE = /first time|shock|surpris|amaz|unbeliev|insane|incredible|blown away|speechless|never expected|didn'?t expect|changed my mind|underrated|best|love|cry|tears|extend|stay longer|don'?t want to leave|衝撃|感動|驚|처음|충격|감동|반전|눈물/i;

  const COUNTRY_META = {
    tw: {
      flag: "🇹🇼",
      name: "대만 (Taiwan)",
      subj: "대만",
      listKey: "twexp",
      channels: "@世界讚台灣 / @台灣讓世界驚喜",
      thumbTop: "完全兩個世界！ / 台灣真的太被低估了！ (완전히 다른 세상! / 대만은 너무 저평가됐어요!)",
      thumbBot: "歐美旅人見證台灣日常直呼全世界最貼心 (구미 여행자들이 대만 일상을 겪고 전 세계에서 가장 따뜻하다고 감탄)",
      shortsGuide: "쇼츠 #1(교통·편의점) + 쇼츠 #2(야시장·미식) + 쇼츠 #3(대만 인정미·환도) ➔ 모두 본편 롱폼으로 『相關影片(관련 동영상)』 연결",
    },
    kr: {
      flag: "🇰🇷",
      name: "한국 (Korea)",
      subj: "한국",
      listKey: "krexp",
      channels: "@코리아탐방록",
      thumbTop: "내가 알던 한국이 맞아?! / 한국은 대체 어떤 나라길래!",
      thumbBot: "외국인 여행자들이 한국 일상에서 직접 겪고 말을 잃은 이유",
      shortsGuide: "쇼츠 #1(새벽 치안·교통) + 쇼츠 #2(고깃집·시장 먹방) + 쇼츠 #3(한국인의 정·지방 인심) ➔ 모두 본편 롱폼으로 『관련 동영상』 연결",
    },
    jp: {
      flag: "🇯🇵",
      name: "일본 (Japan)",
      subj: "일본",
      listKey: "jpexp",
      channels: "@ニッポン反応ラボ-c9x / @外から見たニッポン",
      thumbTop: "絶対あと2泊延ばす！ / 日本の日常が凄すぎる！ (무조건 2박 더 연장할래! / 일본의 일상이 대단해!)",
      thumbBot: "海外の旅人が日本のコンビニ・グルメ・おもてなしに感動した理由 (해외 여행자가 일본 편의점·미식·오모테나시에 감동한 이유)",
      shortsGuide: "쇼츠 #1(콘비니·신칸센) + 쇼츠 #2(이자카야·라멘) + 쇼츠 #3(오모테나시·교토/온천) ➔ 모두 본편 롱폼으로 『関連動画(관련 동영상)』 연결",
    },
  };

  let curCountry = "tw";
  let curSort = "score";
  let curSize = 3; // 3팀 or 4팀
  let curTheme = "all_course"; // all_course, slot1_only, slot2_only, slot3_only, regional_only, shock_only
  let curPoolMode = "all_foreign"; // all_foreign (3분+ 전체), long_10m (10분+), clip_3_10m (3~10분 알짜), strict_1p (1인칭 확정만)
  let curQuery = "";
  let hideDoneInBundles = true;
  let remixSeed = 0; // 🔄 다른 조합으로 재셔플 시드
  let visibleCount = 40; // 한 번에 그리는 묶음 수 (스크롤/더보기로 무제한 확장)
  let cachedBundles = [];

  // 전체 데이터셋(3~10분 알짜 클립 포함) 통합 풀 복원 (캐시)
  let FULL_POOL = null;
  const TW_MATCH_RE = /\btaiwan\b|taipei|kaohsiung|tainan|taichung|hualien|taitung|jiufen|shifen|alishan|sun moon lake|kenting|tamsui|danshui|ximending|shilin|raohe|yilan|taroko|台灣|臺灣|台湾|台北|高雄|台南|台中|花蓮|花莲|九份|대만|타이완|타이베이|가오슝|타이난|타이중|지우펀/i;
  const KR_MATCH_RE = /\bkorea\b|seoul|busan|jeju|incheon|gyeongju|jeonju|andong|ulleung|dokdo|suwon|gangneung|sokcho|hongdae|myeongdong|gangnam|k-?pop|k-?drama|k-?food|kimchi|hanbok|한국|대한민국|서울|부산|제주|경주|전주|안동|韓国|韓國/i;
  const JP_MATCH_RE = /\bjapan\b|tokyo|osaka|kyoto|hokkaido|okinawa|fukuoka|nara|hiroshima|nagoya|sapporo|kobe|kanazawa|kyushu|shikoku|shinjuku|shibuya|shinkansen|ramen|sushi|konbini|ryokan|onsen|일본|도쿄|오사카|교토|홋카이도|오키나와|후쿠오카|日本|東京|大阪|京都|北海道|沖縄|福岡/i;
  const BAD_NEWS_RE = /strait|invasion|\bpla\b|military|\btsmc\b|\bchips?\b|semiconductor|election|president|geopolit|\bwar\b|missile|tariff|trump|biden|\bnews\b|breaking|protest|murder|crime|lawsuit|해협|침공|군사|반도체|선거|대통령|지정학|뉴스|속보|재판|시위|台海|兩岸|两岸|解放軍|選舉|總統/i;
  const TRAD_LOCAL_RE = /[臺灣體國學與來為說這們會開關門時間點長買賣愛謝頭電話語樣麼車線號領處區義裡讓還進過邊總師歲歷觀動場廣麵雞鍋馬鳥魚貓龍東聽書從當實對將應該嗎]/;

  function ensureFullPool() {
    if (FULL_POOL) return FULL_POOL;
    const byId = new Map();
    // 1. 먼저 index.html 의 V 에 있는 영상들 등록 (채점 _sc, 등급 _grade 등 메타데이터 보존)
    (window.V || []).forEach(v => {
      if (v && v.id) byId.set(v.id, v);
    });
    // 2. index.html 에서 10분 미만(181~600초)이라 잘려나간 알짜 클립들과 전체 소스 복원
    const rawArrays = [
      [window.VIDEOS, "discovery"],
      [window.TAIWAN_EXP, "taiwan_exp"],
      [window.GLOBAL_ITEMS, "global"],
      [window.GLOBAL_ITEMS_JP, "global_jp"],
      [window.EXPERIENCE, "experience"],
      [window.VIRAL, "viral"],
      [window.LONGFORM_EXP, "longform_exp"],
      [window.TOPIC_CANDIDATES, "topic_search"],
      [window.KR_REGIONAL, "kr_regional"],
      [window.CC_VIDEOS, "cc_discovery"],
      [window.JP_TOPIC_ITEMS, "japan"],
      [window.ALERTS, "alert"],
    ];
    const scMap = typeof SC_BY_ID !== "undefined" ? SC_BY_ID : new Map();
    rawArrays.forEach(([arr, src]) => {
      (arr || []).forEach(x => {
        if (!x || !x.id) return;
        if (byId.has(x.id)) {
          const ex = byId.get(x.id);
          if (Array.isArray(ex.sources) && !ex.sources.includes(src)) ex.sources.push(src);
          return;
        }
        const copy = Object.assign({}, x);
        if (typeof normLen === "function") {
          const n = normLen(copy);
          copy.duration_sec = n.sec;
          copy.length = n.text;
          copy._form = n.sec == null ? "unk" : n.sec >= 181 ? "long" : "short";
        }
        copy.sources = Array.isArray(copy.sources) ? copy.sources.slice() : [src];
        if (!copy.sources.includes(src)) copy.sources.push(src);
        const t = (copy.title || "") + " " + (copy.channel || "");
        if (TW_MATCH_RE.test(copy.title || "") || copy.country === "대만" || src === "taiwan_exp") copy._subj = "대만";
        else if (KR_MATCH_RE.test(copy.title || "") || copy.country === "한국") copy._subj = "한국";
        else if (JP_MATCH_RE.test(copy.title || "") || copy.country === "일본") copy._subj = "일본";
        else copy._subj = copy.country || "";

        if (typeof kindOf === "function") {
          const kr = kindOf(copy);
          copy._kind = kr[0];
        } else {
          copy._kind = "foreign";
        }
        copy._sc = scMap.get(copy.id) || null;
        if (copy._score == null) {
          const vw = copy.views || 0;
          let sc = Math.max(0, Math.min(35, Math.round((Math.log10(Math.max(vw, 10)) - 2) / 4 * 35)));
          if (copy.subs && vw >= 5000) {
            const rt = vw / Math.max(copy.subs, 1000);
            sc += Math.min(15, Math.round(Math.min(rt / 10, 1) * 15));
          }
          if (SHOCK_RE.test(copy.title || "")) sc += 15;
          if (REGIONAL_RE[copy._subj === "대만" ? "tw" : copy._subj === "일본" ? "jp" : "kr"]?.test(copy.title || "")) sc += 10;
          if (copy._kind === "foreign") sc += 15;
          copy._score = Math.max(35, Math.min(96, sc));
          copy._grade = copy._score >= 75 ? "S" : copy._score >= 60 ? "A" : copy._score >= 48 ? "B" : "C";
        }
        byId.set(copy.id, copy);
      });
    });
    FULL_POOL = [...byId.values()];
    return FULL_POOL;
  }

  function isEligibleForeignVideo(v, cKey) {
    if (!v || !v.id || !v.title) return false;
    if (v.bm || v.ref) return false;
    if (v._kind === "inst" || v._kind === "local") return false;
    const t = v.title || "";
    const ch = v.channel || "";
    if (BAD_NEWS_RE.test(t)) return false;

    // 쇼츠(180초 이하) 제외
    if (v.duration_sec != null && v.duration_sec < 181) return false;
    if (v._form === "short") return false;

    // 길이 필터 모드
    if (curPoolMode === "long_10m" && v.duration_sec != null && v.duration_sec < 600) return false;
    if (curPoolMode === "clip_3_10m" && (v.duration_sec == null || v.duration_sec > 720)) return false;

    // 국가 일치 판정
    const meta = COUNTRY_META[cKey];
    const inExpList = Array.isArray(v._lists) && v._lists.includes(meta.listKey);
    let countryMatch = inExpList || v._subj === meta.subj;
    if (!countryMatch) {
      if (cKey === "tw" && (v.country === "대만" || (v.sources || []).includes("taiwan_exp") || TW_MATCH_RE.test(t))) countryMatch = true;
      else if (cKey === "kr" && (v.country === "한국" || KR_MATCH_RE.test(t))) countryMatch = true;
      else if (cKey === "jp" && (v.country === "일본" || JP_MATCH_RE.test(t))) countryMatch = true;
    }
    if (!countryMatch) return false;

    // 자국 국뽕 편집 채널 제외 (한국: 한글 제목/채널, 일본: 가나 제목/채널, 대만: 번체 한자 제목/채널)
    if (cKey === "kr" && (/[가-힣]{2,}/.test(t) || /[가-힣]{2,}/.test(ch))) return false;
    if (cKey === "jp" && (/[぀-ヿ]/.test(t) || /[぀-ヿ]/.test(ch))) return false;
    if (cKey === "tw" && /[一-鿿]/.test(t + ch) && !/[぀-ヿ가-힣]/.test(t + ch) && TRAD_LOCAL_RE.test(t + ch)) return false;

    // 엄격 모드일 때는 1인칭 외국인 확정(v._kind === "foreign" 또는 inExpList)만 허용
    if (curPoolMode === "strict_1p" && !inExpList && v._kind !== "foreign") return false;

    // 테마 집중 모드일 때 필터
    if (curTheme === "regional_only" && !REGIONAL_RE[cKey].test(t)) return false;
    if (curTheme === "shock_only" && !SHOCK_RE.test(t) && !(v._sc && !v._sc.held)) return false;

    if (curQuery) {
      const hay = (t + " " + ch + " " + (memos[v.id] || "") + " " + (v._gi || []).join(" ") + " " + (v._jgi || []).join(" ")).toLowerCase();
      if (!hay.includes(curQuery)) return false;
    }
    return true;
  }

  function classifySlot(v, cKey) {
    const rules = COURSE_RULES[cKey];
    const text = ((v.title || "") + " " + (v._gi || []).join(" ") + " " + (v._jgi || []).join(" ") + " " + (v._topics || []).join(" ")).toLowerCase();
    // 우선순위: 여러 키워드가 겹칠 때 더 구체적인 슬롯으로 배정
    const m1 = rules[0].re.test(text);
    const m2 = rules[1].re.test(text);
    const m3 = rules[2].re.test(text);
    if (m1 && !m2 && !m3) return 1;
    if (m2 && !m1 && !m3) return 2;
    if (m3 && !m1 && !m2) return 3;
    if (m2) return 2;
    if (m1) return 1;
    if (m3) return 3;
    return 0;
  }

  function getCountryVideos(cKey) {
    const pool = ensureFullPool();
    return pool.filter(v => {
      if (hidden.has(v.id)) return false;
      if (hideDoneInBundles && done.has(v.id)) return false;
      return isEligibleForeignVideo(v, cKey);
    });
  }

  // 시드 기반 결정론적 셔플 오프셋 (리믹스 버튼을 누를 때마다 새로운 팀 조합 생성)
  function hashShift(id, seed) {
    if (!seed) return 0;
    let h = seed * 2654435761;
    for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 1597334677);
    return ((h >>> 0) % 1000) / 1000;
  }

  function sortPool(arr) {
    return arr.slice().sort((a, b) => {
      if ( remixSeed > 0 ) {
        // 리믹스 시드가 켜져 있으면 상위권 그룹 내에서 새로운 조합으로 섞는다
        const sa = hashShift(a.id, remixSeed);
        const sb = hashShift(b.id, remixSeed);
        if (Math.abs(sa - sb) > 0.08) return sb - sa;
      }
      if (curSort === "views") return (b.views || 0) - (a.views || 0);
      if (curSort === "ratio") {
        const ra = a.subs ? (a.views || 0) / Math.max(a.subs, 1000) : 0;
        const rb = b.subs ? (b.views || 0) / Math.max(b.subs, 1000) : 0;
        return rb - ra;
      }
      if (curSort === "pub") return String(b.published || "").localeCompare(String(a.published || ""));
      if (curSort === "argon") {
        const as = a._sc && !a._sc.held && typeof scTot === "function" ? scTot(a._sc) : -1;
        const bs = b._sc && !b._sc.held && typeof scTot === "function" ? scTot(b._sc) : -1;
        if (bs !== as) return bs - as;
      }
      const arA = a._sc && !a._sc.held && typeof scTot === "function" ? scTot(a._sc) * 2.5 : 0;
      const arB = b._sc && !b._sc.held && typeof scTot === "function" ? scTot(b._sc) * 2.5 : 0;
      const ga = a._grade === "S" ? 300 : a._grade === "A" ? 200 : a._grade === "B" ? 100 : 0;
      const gb = b._grade === "S" ? 300 : b._grade === "A" ? 200 : b._grade === "B" ? 100 : 0;
      const fa = a._kind === "foreign" ? 60 : 0;
      const fb = b._kind === "foreign" ? 60 : 0;
      const sa = arA + ga + fa + (a._score || 0) + Math.min(50, Math.log10(Math.max(a.views || 1, 1)) * 8);
      const sb = arB + gb + fb + (b._score || 0) + Math.min(50, Math.log10(Math.max(b.views || 1, 1)) * 8);
      return sb - sa;
    });
  }

  /**
   * 무제한 모드 A 묶음 빌더:
   * - 60개 제한 없이 데이터셋 끝까지 모든 가능한 3~4팀 합본 세트를 생성!
   * - 한 묶음 안에서 동일한 유튜버(channel_id) 중복 절대 금지
   */
  function buildModeABundles(cKey) {
    const raw = sortPool(getCountryVideos(cKey));
    const bucket1 = [], bucket2 = [], bucket3 = [], bucket0 = [];
    raw.forEach(v => {
      const s = classifySlot(v, cKey);
      if (s === 1) bucket1.push(v);
      else if (s === 2) bucket2.push(v);
      else if (s === 3) bucket3.push(v);
      else bucket0.push(v);
    });

    const usedIds = new Set();
    const pickFrom = (arr, usedChannels) => {
      for (let i = 0; i < arr.length; i++) {
        const v = arr[i];
        if (usedIds.has(v.id)) continue;
        const chKey = v.channel_id || v.channel || v.id;
        if (usedChannels.has(chKey)) continue;
        usedIds.add(v.id);
        usedChannels.add(chKey);
        return v;
      }
      return null;
    };

    const bundles = [];

    // 테마 집중 모드(단일 테마로만 3~4팀 묶기) vs 종합 3코스 모드
    if (curTheme === "slot1_only" || curTheme === "slot2_only" || curTheme === "slot3_only") {
      const targetSlot = curTheme === "slot1_only" ? 1 : curTheme === "slot2_only" ? 2 : 3;
      const primaryPool = targetSlot === 1 ? bucket1 : targetSlot === 2 ? bucket2 : bucket3;
      while (true) {
        const usedChannels = new Set();
        const items = [];
        for (let k = 0; k < curSize; k++) {
          const p = pickFrom(primaryPool, usedChannels);
          if (p) items.push({ slot: targetSlot, video: p });
        }
        if (items.length < curSize) break;
        bundles.push({ index: bundles.length + 1, country: cKey, items });
      }
    } else {
      // 기본 종합 코스 (1부 교통·편의 + 2부 야시장·미식 + 3부 인심·지방 [+ 4부]) — 끝까지 계속 묶는다!
      while (true) {
        const usedChannels = new Set();
        const items = [];

        const p1 = pickFrom(bucket1, usedChannels) || pickFrom(bucket0, usedChannels) || pickFrom(bucket3, usedChannels) || pickFrom(bucket2, usedChannels);
        if (p1) items.push({ slot: 1, video: p1 });

        const p2 = pickFrom(bucket2, usedChannels) || pickFrom(bucket0, usedChannels) || pickFrom(bucket3, usedChannels) || pickFrom(bucket1, usedChannels);
        if (p2) items.push({ slot: 2, video: p2 });

        const p3 = pickFrom(bucket3, usedChannels) || pickFrom(bucket0, usedChannels) || pickFrom(bucket1, usedChannels) || pickFrom(bucket2, usedChannels);
        if (p3) items.push({ slot: 3, video: p3 });

        if (curSize === 4) {
          const p4 = pickFrom(bucket0, usedChannels) || pickFrom(bucket2, usedChannels) || pickFrom(bucket3, usedChannels) || pickFrom(bucket1, usedChannels);
          if (p4) items.push({ slot: 4, video: p4 });
        }

        if (items.length < curSize) break;
        bundles.push({
          index: bundles.length + 1,
          country: cKey,
          items,
        });
      }
    }

    return {
      bundles,
      totalVideos: raw.length,
      counts: { b1: bucket1.length, b2: bucket2.length, b3: bucket3.length, b0: bucket0.length },
    };
  }

  function injectBundleStyles() {
    if (document.getElementById("bd-style")) return;
    const st = document.createElement("style");
    st.id = "bd-style";
    st.textContent = `
      .bd-wrap { max-width: 1200px; margin: 12px auto 60px; padding: 0 16px; }
      .bd-box { background: var(--card); border: 2px solid var(--line); border-radius: 16px; padding: 16px; margin-bottom: 22px; box-shadow: 0 4px 14px rgba(0,0,0,0.04); }
      .bd-head { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; padding-bottom: 12px; border-bottom: 1px solid var(--line); margin-bottom: 14px; }
      .bd-title { font-size: 17px; font-weight: 800; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
      .bd-badge { font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 99px; background: var(--acc); color: #fff; }
      .bd-actions { display: flex; gap: 8px; flex-wrap: wrap; }
      .bd-copy { background: var(--acc); color: #fff; border: 0; border-radius: 10px; padding: 8px 14px; font-weight: 700; font-size: 13px; cursor: pointer; }
      .bd-copy:hover { opacity: 0.92; }
      .bd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
      .bd-slot-badge { display: inline-block; font-size: 12px; font-weight: 800; color: #fff; padding: 4px 10px; border-radius: 8px; margin-bottom: 6px; }
      .bd-shorts-plan { margin-top: 12px; padding: 10px 14px; border-radius: 10px; background: var(--bg); font-size: 12.5px; color: var(--ink); display: flex; flex-direction: column; gap: 4px; }
      .bd-shorts-plan b { color: var(--acc); }
      .bd-more-bar { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; align-items: center; margin: 24px 0 40px; padding: 18px; background: var(--card); border: 2px dashed var(--acc); border-radius: 14px; }
    `;
    document.head.appendChild(st);
  }

  function buildBundleCopyPrompt(b) {
    const meta = COUNTRY_META[b.country];
    const rules = COURSE_RULES[b.country];
    const lines = [];
    lines.push(`[🍱 모드 A (@daoyingtan 식 3~4팀 종합 코스 합본 롱폼 1편 + 주제별 파생 쇼츠 1·2·3 동시 제작 지시)]`);
    lines.push(`• 대상 국가 및 채널: ${meta.flag} ${meta.name} (${meta.channels})`);
    lines.push(`• 묶음 번호: 세트 #${b.index}${remixSeed ? " (리믹스 조합 #" + remixSeed + ")" : ""} (서로 다른 외국인 유튜버 ${b.items.length}팀 합본 · 권장 길이 14~17분)\n`);
    lines.push(`[🎬 본편 1~${b.items.length}부 구성 및 파생 쇼츠 #1~#${b.items.length} 매칭 원본 소스]`);
    b.items.forEach((it, idx) => {
      const v = it.video;
      const r = rules[(it.slot ? it.slot - 1 : idx)] || rules[idx] || rules[rules.length - 1];
      const scTxt = v._sc && !v._sc.held && typeof scTot === "function" ? ` / Argon 채점: ${scTot(v._sc)}점(${scGrade(v._sc)})` : "";
      lines.push(`${idx + 1}부 (파생 쇼츠 #${idx + 1} — ${r.label}):`);
      lines.push(`  - 원본 채널명: ${v.channel}`);
      lines.push(`  - 원본 제목: ${v.title}`);
      lines.push(`  - 원본 링크: https://www.youtube.com/watch?v=${v.id} (조회수: ${fmt(v.views)} / 길이: ${v.length || "미확인"}${scTxt})`);
    });
    lines.push(`\n[📌 설명란 출처 표기 블록 (복붙용)]`);
    b.items.forEach(it => {
      const prefix = b.country === "tw" ? "影片來源：" : b.country === "jp" ? "映像出典：" : "영상 출처: ";
      lines.push(`${prefix}${it.video.channel} (https://www.youtube.com/watch?v=${it.video.id})`);
    });
    lines.push(`\n[🎨 @daoyingtan 스타일 5단 썸네일 & 파생 쇼츠 1·2·3 설계]`);
    lines.push(`• 썸네일 상단 빅타이포: ${meta.thumbTop}`);
    lines.push(`• 썸네일 중앙 ${b.items.length}분할: ` + b.items.map((it, i) => `${i + 1}부(${it.video.channel})`).join(" ➡ ") + ` 감정 대비 + 하단 알약 배지`);
    lines.push(`• 썸네일 하단 요약 바: ${meta.thumbBot}`);
    lines.push(`• 파생 쇼츠 분리 발행: ${meta.shortsGuide}`);
    return lines.join("\n");
  }

  function createBundleCardEl(b, meta, rules) {
    const box = document.createElement("div");
    box.className = "bd-box";

    const totalViews = b.items.reduce((acc, it) => acc + (it.video.views || 0), 0);
    const avgScore = Math.round(b.items.reduce((acc, it) => {
      const v = it.video;
      const sc = v._sc && !v._sc.held && typeof scTot === "function" ? scTot(v._sc) : (v._score || 60);
      return acc + sc;
    }, 0) / b.items.length);
    const avgGrade = avgScore >= 75 ? "S" : avgScore >= 60 ? "A" : avgScore >= 48 ? "B" : "C";
    const themeTitle =
      curTheme === "slot1_only" ? "🚇 교통·편의점·치안 집중 합본" :
      curTheme === "slot2_only" ? "🍜 야시장·로컬 미식 집중 합본" :
      curTheme === "slot3_only" ? "🤝 현지인 친절·인심·감동 집중 합본" :
      curTheme === "regional_only" ? "🗺️ 비수도권 지방·자연·환도 합본" :
      curTheme === "shock_only" ? "⚡ 첫방문 충격·반전·체류연장 합본" :
      "🍱 1부 교통·편의 ➡ 2부 미식·야시장 ➡ 3부 인심·풍경 종합 코스";

    const head = document.createElement("div");
    head.className = "bd-head";
    head.innerHTML = `
      <div class="bd-title">
        <span class="bd-badge">${meta.flag} 세트 #${b.index}${remixSeed ? " (리믹스 #" + remixSeed + ")" : ""}</span>
        <span>${meta.name} ${b.items.length}팀 (${themeTitle})</span>
        <span class="tag grade-${avgGrade}">🏆 묶음 평균 ${avgScore}점 (${avgGrade}등급)</span>
        <span class="tag hot">👁 원본 합산 조회수 ${fmt(totalViews)}</span>
      </div>
      <div class="bd-actions">
        <button class="bd-copy">📋 이 묶음(롱폼 1편 + 쇼츠 1·2·3) 제작 프롬프트 & 출처 복사</button>
        <button class="chip bd-done-all">✅ 이 묶음(${b.items.length}개) 모두 사용 완료 처리</button>
      </div>
    `;

    head.querySelector(".bd-copy").onclick = e => {
      const txt = buildBundleCopyPrompt(b);
      navigator.clipboard.writeText(txt).then(() => {
        const btn = e.currentTarget;
        const old = btn.textContent;
        btn.textContent = "✅ 세트 #" + b.index + " (롱폼+쇼츠 1·2·3) 복사 완료!";
        setTimeout(() => (btn.textContent = old), 2200);
      });
    };

    head.querySelector(".bd-done-all").onclick = () => {
      b.items.forEach(it => done.add(it.video.id));
      saveAll();
      rebuildAndRender(true);
    };

    box.appendChild(head);

    const grid = document.createElement("div");
    grid.className = "bd-grid";

    b.items.forEach((it, idx) => {
      const v = it.video;
      const r = rules[(it.slot ? it.slot - 1 : idx)] || rules[idx] || rules[rules.length - 1];
      const card = document.createElement("div");
      card.className = "card kd-" + (v._kind || "foreign") + (done.has(v.id) ? " done" : "");
      card.innerHTML = `
        <button class="fav ${favs.has(v.id) ? "on" : ""}" title="저장">${favs.has(v.id) ? "★" : "☆"}</button>
        <div class="th"><img loading="lazy" src="https://i.ytimg.com/vi/${v.id}/mqdefault.jpg"><div class="play">▶</div></div>
        <div class="body">
          <div><span class="bd-slot-badge" style="background:${r.color}">${idx + 1}부 · 📱 파생 쇼츠 #${idx + 1}</span></div>
          <div style="font-size:11.5px;color:var(--mute);font-weight:600;margin-top:-4px">${r.label}</div>
          <a class="t" target="_blank" rel="noopener" href="https://youtu.be/${v.id}"></a>
          <div class="m"></div>
          <div class="tags">
            ${v._sc && !v._sc.held && typeof scTot === "function" ? `<span class="tag sc-${scGrade(v._sc)}">🎯 자막채점 ${scTot(v._sc)}점 (${scGrade(v._sc)}등급)</span>` : ""}
            ${v._score != null ? `<span class="tag grade-${v._grade || "B"}">🏆 ${v._score}점 (${v._grade || "B"}등급)</span>` : ""}
            <span class="tag">👥 ${fmt(v.subs)}</span>
            <span class="tag">👁 ${fmt(v.views)}</span>
            ${v.length ? `<span class="tag">⏱ ${v.length}</span>` : ""}
            ${(v._gi || []).slice(0, 2).map(t => `<span class="tag">${t}</span>`).join("")}
            ${(v._jgi || []).slice(0, 2).map(t => `<span class="tag">${t}</span>`).join("")}
          </div>
          <div class="act">
            <button class="btn dn ${done.has(v.id) ? "on" : ""}">${done.has(v.id) ? "✅ 사용 완료" : "☐ 사용 완료 (다른 영상으로 교체)"}</button>
            <button class="btn hd">${hidden.has(v.id) ? "↩ 복구" : "🗑 제외"}</button>
          </div>
        </div>
      `;
      card.querySelector(".t").textContent = v.title;
      card.querySelector(".m").textContent = `${v.channel} · ${v.published ? v.published.slice(0, 10) : "날짜 미확인"}`;
      card.querySelector(".th").onclick = e => {
        e.currentTarget.innerHTML = `<iframe src="https://www.youtube.com/embed/${v.id}?autoplay=1" allow="autoplay;encrypted-media" allowfullscreen></iframe>`;
        e.currentTarget.onclick = null;
      };
      card.querySelector(".fav").onclick = () => {
        favs.has(v.id) ? favs.delete(v.id) : favs.add(v.id);
        saveAll();
        renderVisibleBundles();
      };
      card.querySelector(".dn").onclick = () => {
        done.has(v.id) ? done.delete(v.id) : done.add(v.id);
        saveAll();
        rebuildAndRender(true);
      };
      card.querySelector(".hd").onclick = () => {
        hidden.has(v.id) ? hidden.delete(v.id) : hidden.add(v.id);
        saveAll();
        rebuildAndRender(true);
      };
      grid.appendChild(card);
    });

    box.appendChild(grid);

    const plan = document.createElement("div");
    plan.className = "bd-shorts-plan";
    plan.innerHTML =
      `<div><b>🎬 롱폼 본편 (${b.items.length}팀 옴니버스 14~17분)</b>: ` +
      b.items.map((it, i) => `[${i + 1}부] ${it.video.channel}`).join(" ➡ ") +
      ` (설명란 출처 ${b.items.length}곳 동시 표기)</div>` +
      `<div><b>📱 주제별 파생 쇼츠 1·2·3 자동 분리</b>: ` +
      b.items.map((it, i) => `<b>쇼츠 #${i + 1}</b>(${it.video.channel} 하이라이트 50초)`).join(" + ") +
      ` ➔ ${b.items.length}개 쇼츠 모두 이 본편으로 <b>『관련 동영상』</b> 직결!</div>`;
    box.appendChild(plan);

    return box;
  }

  let lastBuildResult = null;

  function rebuildAndRender(keepVisibleCount) {
    if (!keepVisibleCount) visibleCount = 40;
    lastBuildResult = buildModeABundles(curCountry);
    cachedBundles = lastBuildResult.bundles;
    renderVisibleBundles();
  }

  function renderVisibleBundles() {
    injectBundleStyles();
    const infoEl = document.getElementById("bdinfo");
    const listEl = document.getElementById("bdlist");
    if (!infoEl || !listEl) return;

    document.querySelectorAll("#bdcty .chip").forEach(btn => {
      btn.classList.toggle("on", btn.dataset.c === curCountry);
    });
    document.querySelectorAll("#bdsize .chip").forEach(btn => {
      btn.classList.toggle("on", +btn.dataset.n === curSize);
    });
    document.querySelectorAll("#bdtheme .chip").forEach(btn => {
      btn.classList.toggle("on", btn.dataset.th === curTheme);
    });
    document.querySelectorAll("#bdpool .chip").forEach(btn => {
      btn.classList.toggle("on", btn.dataset.pm === curPoolMode);
    });

    if (!lastBuildResult) lastBuildResult = buildModeABundles(curCountry);
    const { bundles, totalVideos, counts } = lastBuildResult;
    const meta = COUNTRY_META[curCountry];
    const rules = COURSE_RULES[curCountry];
    const shownN = Math.min(visibleCount, bundles.length);

    infoEl.innerHTML =
      `<b>${meta.flag} ${meta.name}</b> 외국인 원본 후보 총 <b>${totalVideos.toLocaleString()}개</b> ` +
      `(1부 교통·편의·치안 <b>${counts.b1.toLocaleString()}개</b> / 2부 야시장·미식 <b>${counts.b2.toLocaleString()}개</b> / 3부 인심·자연·지방 <b>${counts.b3.toLocaleString()}개</b> / 범용 여행 <b>${counts.b0.toLocaleString()}개</b>) ` +
      `➔ <b>서로 다른 유튜버 ${curSize}팀씩 총 <span style="color:var(--acc);font-size:15px">${bundles.length.toLocaleString()}개 합본 세트</span></b> 자동 편성 완료! ` +
      `(현재 <b>1~${shownN.toLocaleString()}번째 묶음</b> 표시 중 · 스크롤 시 자동 계속 로딩)`;

    listEl.innerHTML = "";
    if (!bundles.length) {
      listEl.innerHTML = `<div class="empty">조건에 맞는 ${meta.name} 묶음 영상이 부족합니다. 검색어를 지우거나 필터를 '전체 외국인 여행·체험'으로 변경해 보세요.</div>`;
      return;
    }

    const frag = document.createDocumentFragment();
    bundles.slice(0, shownN).forEach(b => {
      frag.appendChild(createBundleCardEl(b, meta, rules));
    });

    if (shownN < bundles.length) {
      const moreBar = document.createElement("div");
      moreBar.className = "bd-more-bar";
      const rem = bundles.length - shownN;
      moreBar.innerHTML = `
        <span style="font-weight:800;font-size:14px">📦 아직 <span style="color:var(--acc)">${rem.toLocaleString()}개 묶음(${(rem * curSize).toLocaleString()}개 영상)</span>이 더 준비되어 있습니다!</span>
        <button class="bd-copy" id="bd-more-50">➕ 다음 50묶음 더 보기 (${shownN + 1}~${Math.min(bundles.length, shownN + 50)}번)</button>
        <button class="chip on" id="bd-more-200" style="font-weight:800;padding:8px 14px">➕ 다음 200묶음 한꺼번에 펼치기</button>
        <button class="chip" id="bd-more-all" style="font-weight:700;padding:8px 14px">🚀 전체 ${bundles.length.toLocaleString()}개 묶음 끝까지 다 펼치기</button>
      `;
      moreBar.querySelector("#bd-more-50").onclick = () => {
        visibleCount += 50;
        renderVisibleBundles();
      };
      moreBar.querySelector("#bd-more-200").onclick = () => {
        visibleCount += 200;
        renderVisibleBundles();
      };
      moreBar.querySelector("#bd-more-all").onclick = () => {
        visibleCount = bundles.length;
        renderVisibleBundles();
      };
      frag.appendChild(moreBar);
    }

    listEl.appendChild(frag);
  }

  // 스크롤이 아래로 내려가면 자동으로 +30묶음씩 계속 이어서 펼쳐준다!
  window.addEventListener("scroll", () => {
    const bdView = document.getElementById("bdview");
    if (!bdView || bdView.hidden || !cachedBundles.length) return;
    if (visibleCount >= cachedBundles.length) return;
    const moreBtn = document.getElementById("bd-more-50");
    if (moreBtn && moreBtn.getBoundingClientRect().top < window.innerHeight + 900) {
      visibleCount += 30;
      renderVisibleBundles();
    }
  }, { passive: true });

  document.addEventListener("DOMContentLoaded", () => {
    const mvBtn = document.getElementById("mv");
    if (!mvBtn) return;

    const mbdBtn = document.createElement("button");
    mbdBtn.className = "chip";
    mbdBtn.id = "mbd";
    mbdBtn.textContent = "🍱 나라별 3~4팀 합본 묶음 (모드 A)";
    mbdBtn.title = "@daoyingtan(島映談) 방식: 나라별(대만/한국/일본)로 서로 다른 외국인 유튜버 3~4팀을 1편(롱폼+쇼츠 1·2·3)으로 무제한 대량 묶어 배치합니다";
    mvBtn.after(mbdBtn);

    const bdView = document.createElement("div");
    bdView.id = "bdview";
    bdView.hidden = true;
    bdView.innerHTML = `
      <div class="quick">
        <div class="qg" id="bdcty">
          <b>🌏 1단계: 나라 선택 (100% 나라별 분리)</b>
          <button class="chip on" data-c="tw">🇹🇼 대만 합본 묶음 (@世界讚台灣 · @台灣讓世界驚喜)</button>
          <button class="chip" data-c="kr">🇰🇷 한국 합본 묶음 (@코리아탐방록)</button>
          <button class="chip" data-c="jp">🇯🇵 일본 합본 묶음 (@ニッポン反応ラボ · @外から見たニッポン)</button>
        </div>
      </div>
      <div class="quick" style="margin-top:8px">
        <div class="qg" id="bdtheme">
          <b>🎯 2단계: 묶음 테마 방식 (6종)</b>
          <button class="chip on" data-th="all_course">🍱 @daoyingtan 정석 종합 3코스 (1부 교통·편의 + 2부 미식 + 3부 인심·풍경)</button>
          <button class="chip" data-th="slot1_only">🚇 교통·편의점·치안 집중 묶음</button>
          <button class="chip" data-th="slot2_only">🍜 야시장·로컬 미식 집중 묶음</button>
          <button class="chip" data-th="slot3_only">🤝 현지인 인심(人情味/情/おもてなし) 집중 묶음</button>
          <button class="chip" data-th="regional_only">🗺️ 비수도권 지방 소도시·환도 집중 묶음</button>
          <button class="chip" data-th="shock_only">⚡ 첫방문 충격·반전 집중 묶음</button>
        </div>
      </div>
      <div class="quick" style="margin-top:8px">
        <div class="qg" id="bdsize">
          <b>👥 3단계: 합칠 팀 수 & 리믹스</b>
          <button class="chip on" data-n="3">3팀 합본 (쇼츠 #1·#2·#3)</button>
          <button class="chip" data-n="4">4팀 합본 (쇼츠 #1~#4)</button>
        </div>
        <div class="qg" id="bdpool">
          <b>🎞️ 원본 길이·범위</b>
          <button class="chip on" data-pm="all_foreign">🌏 전체 외국인 영상 (3분+ 알짜 클립 & 롱폼 총망라 — 1,500+묶음)</button>
          <button class="chip" data-pm="clip_3_10m">⚡ 3~12분 핵심 클립만 (합본 편집 최고 효율)</button>
          <button class="chip" data-pm="long_10m">🎬 10분+ 장편 브이로그만</button>
          <button class="chip" data-pm="strict_1p">🏅 1인칭 확정(My/We/Vlog)만</button>
        </div>
      </div>
      <div class="bar">
        <input id="bdq" placeholder="이 나라 묶음 안에서 키워드·지역(타이난/가오슝/부산/경주/교토/규슈 등)·유튜버 검색">
        <select id="bdsort">
          <option value="score">🏆 추천 합본 우선순위순 (Argon 채점 + S/A등급 + 조회수)</option>
          <option value="argon">🎯 Argon 스크립트 채점 점수 높은순 (점수판정기준_Argon용)</option>
          <option value="views">👁 원본 조회수 높은순</option>
          <option value="ratio">🔥 구독자 대비 조회수(아웃라이어)순</option>
          <option value="pub">📅 최신 업로드순</option>
        </select>
        <button class="chip on" id="bdremix" style="font-weight:800;background:#0ea5e9;border-color:#0ea5e9;color:#fff" title="누를 때마다 서로 다른 외국인 유튜버들을 새로운 3~4팀 짝으로 다시 묶어줍니다">🔄 다른 3~4팀 조합으로 새로 묶기 (계속 리믹스)</button>
        <label class="chip" style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">
          <input type="checkbox" id="bdhidedone" checked style="width:15px;height:15px;margin:0;flex:none;min-width:0">
          사용 완료 빼기
        </label>
      </div>
      <div class="sub" style="max-width:1200px;margin:4px auto 8px;padding:0 16px" id="bdinfo"></div>
      <div class="bd-wrap" id="bdlist"></div>
    `;
    document.getElementById("thview").before(bdView);

    bdView.querySelectorAll("#bdcty .chip").forEach(b => {
      b.onclick = () => {
        curCountry = b.dataset.c;
        rebuildAndRender(false);
      };
    });
    bdView.querySelectorAll("#bdtheme .chip").forEach(b => {
      b.onclick = () => {
        curTheme = b.dataset.th;
        rebuildAndRender(false);
      };
    });
    bdView.querySelectorAll("#bdsize .chip").forEach(b => {
      b.onclick = () => {
        curSize = +b.dataset.n;
        rebuildAndRender(false);
      };
    });
    bdView.querySelectorAll("#bdpool .chip").forEach(b => {
      b.onclick = () => {
        curPoolMode = b.dataset.pm;
        rebuildAndRender(false);
      };
    });
    document.getElementById("bdq").oninput = e => {
      curQuery = e.target.value.trim().toLowerCase();
      rebuildAndRender(false);
    };
    document.getElementById("bdsort").onchange = e => {
      curSort = e.target.value;
      rebuildAndRender(false);
    };
    document.getElementById("bdremix").onclick = e => {
      remixSeed += 1;
      e.currentTarget.textContent = `🔄 다른 3~4팀 조합으로 새로 묶기 (리믹스 #${remixSeed} 적용중 · 클릭 시 또 섞기)`;
      rebuildAndRender(false);
    };
    document.getElementById("bdhidedone").onchange = e => {
      hideDoneInBundles = e.target.checked;
      rebuildAndRender(false);
    };

    const origSetModeAll = window.setModeAll;
    window.setModeAll = function (m) {
      if (m === "bd") {
        ["mv", "mc", "ms", "mct", "mnw", "mth", "mmy", "hidden-videos-tab"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.classList.remove("on");
        });
        mbdBtn.classList.add("on");
        document.querySelectorAll(".vmode").forEach(e => (e.hidden = true));
        ["chview", "scview", "ctview", "nwview", "thview", "hsview", "listrow", "my-score-view", "hidden-videos-view"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.hidden = true;
        });
        bdView.hidden = false;
        rebuildAndRender(true);
      } else {
        mbdBtn.classList.remove("on");
        bdView.hidden = true;
        if (typeof origSetModeAll === "function") origSetModeAll(m);
      }
    };

    const origSetMode = window.setMode;
    window.setMode = function (m) {
      if (m === "bd") {
        window.setModeAll("bd");
      } else {
        mbdBtn.classList.remove("on");
        bdView.hidden = true;
        if (typeof origSetMode === "function") origSetMode(m);
      }
    };

    mbdBtn.onclick = () => window.setModeAll("bd");
  });
})();
