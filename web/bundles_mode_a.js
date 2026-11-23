// -*- coding: utf-8 -*-
/**
 * web/bundles_mode_a.js
 * =====================
 * 모드 A: @daoyingtan (島映談) & @旅人眼中的台灣 벤치마크 기반
 * 1) 나라별 100% 독립 분리 (🇹🇼 대만 / 🇰🇷 한국 / 🇯🇵 일본)
 * 2) 한 묶음(1편의 롱폼 = 14~17분) 안에 서로 다른 외국인 채널 3팀 + 서로 다른 3대 코스 주제 배치:
 *    - [1부 · 파생 쇼츠 #1]: 🚇 교통·편의점·치안·디지털 인프라 충격
 *    - [2부 · 파생 쇼츠 #2]: 🍜 야시장·로컬 맛집·아침식사·길거리 미식 감탄
 *    - [3부 · 파생 쇼츠 #3]: 🤝 현지인 인심(人情味/情/おもてなし)·지방 자연 풍경·체류 연장 감동
 * 3) 원클릭 [이 묶음(롱폼 1편 + 쇼츠 1·2·3) 제작 프롬프트 & 출처 복사] 및 [묶음 전체 사용 완료] 지원
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
        label: "🍜 대만 야시장(夜市)·우육면·루로우판·아침식사(豆漿/刈包)·버블티",
        re: /food|eat|night market|market|breakfast|beef noodle|boba|bubble tea|dumpling|xiao long bao|stinky tofu|mango|street food|restaurant|cafe|tea|夜市|美食|小吃|牛肉麵|滷肉飯|豆漿|珍珠奶茶/i,
      },
      {
        slot: 3,
        badge: "3부 · 📱 파생 쇼츠 #3 (로컬 인심·자연·환도)",
        color: "#10b981",
        label: "🤝 대만 인정미(人情味)·지우펀/아리산/타이난/가오슝/화롄 환도 감동",
        re: /people|kind|friendly|help|love|Emotional|cry|tears|jiufen|alishan|tainan|kaohsiung|hualien|taitung|kenting|sun moon lake|taroko|island|nature|mountain|人情味|熱情|感動|九份|阿里山|台南|高雄|花蓮|台東|環島/i,
      },
    ],
    kr: [
      {
        slot: 1,
        badge: "1부 · 📱 파생 쇼츠 #1 (치안·교통·편의)",
        color: "#0ea5e9",
        label: "🚨 한국 새벽 치안·노트북 자리 비우기·지하철/KTX·편의점·배달 속도",
        re: /safe|alone at night|laptop|cafe|lost|wallet|subway|metro|train|ktx|bus|airport|incheon|convenience|7-?eleven|cu\b|gs25|fast|delivery|wifi|clean|restroom|치안|안전|노트북|분실물|지하철|교통|편의점|배달|화장실/i,
      },
      {
        slot: 2,
        badge: "2부 · 📱 파생 쇼츠 #2 (한식·시장 먹방)",
        color: "#f59e0b",
        label: "🍖 한국 고깃집(K-BBQ)·밑반찬 리필·전통시장·치킨·한강 라면·길거리 음식",
        re: /food|eat|bbq|meat|kimchi|ramen|market|street food|chicken|fried|side dish|banchan|restaurant|bakery|coffee|dessert|음식|한식|고깃집|삼겹살|반찬|시장|치킨|라면|먹방|빵집/i,
      },
      {
        slot: 3,
        badge: "3부 · 📱 파생 쇼츠 #3 (한국인의 정·지방·문화)",
        color: "#10b981",
        label: "❤️ 한국인의 정(情)·부산/제주/경주/시골 인심·한복/야구장 응원 감동",
        re: /people|kind|friendly|help|free|grandma|ajumma|hanbok|palace|baseball|busan|jeju|gyeongju|countryside|village|hiking|mountain|temple|cry|tears|love|한국인|인심|친절|할머니|사장님|부산|제주|경주|시골|한복|경복궁|야구장|감동/i,
      },
    ],
    jp: [
      {
        slot: 1,
        badge: "1부 · 📱 파생 쇼츠 #1 (편의점·신칸센·치안)",
        color: "#0ea5e9",
        label: "🚅 일본 편의점(콘비니)·자판기·신칸센 정시 운행·코반/분실물·치안",
        re: /konbini|convenience|7-?eleven|family.?mart|lawson|vending|shinkansen|bullet train|train|subway|station|taxi|safe|clean|lost|wallet|police|koban|airport|편의점|자판기|신칸센|전철|택시|치안|안전|분실물|コンビニ|新幹線/i,
      },
      {
        slot: 2,
        badge: "2부 · 📱 파생 쇼츠 #2 (일식·이자카야 미식)",
        color: "#f59e0b",
        label: "🍣 일본 라멘·스시/회전초밥·이자카야·와규·규동·타마고산도·말차 디저트",
        re: /food|eat|ramen|sushi|izakaya|wagyu|beef|gyudon|udon|soba|tonkatsu|curry|onigiri|egg sandwich|matcha|bakery|market|street food|라멘|스시|초밥|이자카야|와규|규동|우동|돈카츠|편의점 음식|ラーメン|寿司|居酒屋/i,
      },
      {
        slot: 3,
        badge: "3부 · 📱 파생 쇼츠 #3 (오모테나시·지방·전통)",
        color: "#10b981",
        label: "♨️ 일본의 배려(오모테나시)·교토/이즈/홋카이도/료칸 온천·체류 연장 감동",
        re: /people|kind|polite|service|omotenashi|help|kyoto|osaka|hokkaido|okinawa|fukuoka|nara|fuji|onsen|ryokan|shrine|temple|tradition|countryside|love|cry|배려|친절|서비스|교토|오사카|홋카이도|온천|료칸|감동|京都|温泉/i,
      },
    ],
  };

  const COUNTRY_META = {
    tw: {
      flag: "🇹🇼",
      name: "대만 (Taiwan)",
      subj: "대만",
      listKey: "twexp",
      channels: "@世界讚台灣 / @台灣讓世界驚喜",
      thumbTop: "完全兩個世界！ / 台灣真的太被低估了！",
      thumbBot: "歐美旅人見證台灣日常直呼全世界最貼心",
      shortsGuide: "쇼츠 #1(교통·편의점) + 쇼츠 #2(야시장·미식) + 쇼츠 #3(대만 인정미·환도) ➔ 모두 본편 롱폼으로 『相關影片』 연결",
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
      thumbTop: "絶対あと2泊延ばす！ / 日本の日常が凄すぎる！",
      thumbBot: "海外の旅人が日本のコンビニ・グルメ・おもてなしに感動した理由",
      shortsGuide: "쇼츠 #1(콘비니·신칸센) + 쇼츠 #2(이자카야·라멘) + 쇼츠 #3(오모테나시·교토/온천) ➔ 모두 본편 롱폼으로 『関連動画』 연결",
    },
  };

  let curCountry = "tw";
  let curSort = "score";
  let curSize = 3; // 3팀 or 4팀
  let curQuery = "";
  let hideDoneInBundles = true;

  function classifySlot(v, cKey) {
    const rules = COURSE_RULES[cKey];
    const text = ((v.title || "") + " " + (v._gi || []).join(" ") + " " + (v._jgi || []).join(" ") + " " + (v._topics || []).join(" ")).toLowerCase();
    for (const r of rules) {
      if (r.re.test(text)) return r.slot;
    }
    return 0; // 범용 여행 브이로그 (비어 있는 슬롯에 자동 배정)
  }

  function getCountryVideos(cKey) {
    const meta = COUNTRY_META[cKey];
    return V.filter(v => {
      if (hidden.has(v.id)) return false;
      if (hideDoneInBundles && done.has(v.id)) return false;
      if (v._form === "short") return false; // 롱폼 원본 위주
      // 외국인 원본(foreign) 또는 체험 목록 우선
      const inExpList = Array.isArray(v._lists) && v._lists.includes(meta.listKey);
      const isSubjMatch = v._subj === meta.subj || (cKey === "tw" && (v.country === "대만" || (v.sources || []).includes("taiwan_exp")));
      if (!inExpList && !(isSubjMatch && v._kind === "foreign")) return false;
      if (curQuery) {
        const hay = ((v.title || "") + " " + (v.channel || "") + " " + (memos[v.id] || "")).toLowerCase();
        if (!hay.includes(curQuery)) return false;
      }
      return true;
    });
  }

  function sortPool(arr) {
    return arr.slice().sort((a, b) => {
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
      // 기본: Argon 채점(있으면 가점) + 등급(S>A>B) + 점수 + 조회수 종합
      const arA = a._sc && !a._sc.held && typeof scTot === "function" ? scTot(a._sc) * 2 : 0;
      const arB = b._sc && !b._sc.held && typeof scTot === "function" ? scTot(b._sc) * 2 : 0;
      const ga = a._grade === "S" ? 300 : a._grade === "A" ? 200 : a._grade === "B" ? 100 : 0;
      const gb = b._grade === "S" ? 300 : b._grade === "A" ? 200 : b._grade === "B" ? 100 : 0;
      const sa = arA + ga + (a._score || 0) + Math.min(50, Math.log10(Math.max(a.views || 1, 1)) * 8);
      const sb = arB + gb + (b._score || 0) + Math.min(50, Math.log10(Math.max(b.views || 1, 1)) * 8);
      return sb - sa;
    });
  }

  /**
   * 모드 A 핵심 알고리즘:
   * - 선택된 나라(TW / KR / JP)의 외국인 원본 영상들을 슬롯 1(교통·편의·치안), 슬롯 2(음식·야시장), 슬롯 3(인심·자연·지방)으로 분류
   * - 한 묶음(Bundle)을 만들 때 반드시 서로 다른 외국인 유튜버(channel_id 중복 금지) + 서로 다른 주제(1부 + 2부 + 3부 [+ 4부])로 짝지어 배치!
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
      for (const v of arr) {
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
    const allPools = [bucket1, bucket2, bucket3, bucket0];

    while (true) {
      const usedChannels = new Set();
      const items = [];

      // 1부(교통/편의/치안), 2부(미식/야시장), 3부(인심/자연/지방)에서 각각 1개씩 뽑되, 부족하면 bucket0이나 다른 버킷에서 보충
      const p1 = pickFrom(bucket1, usedChannels) || pickFrom(bucket0, usedChannels) || pickFrom(bucket2, usedChannels) || pickFrom(bucket3, usedChannels);
      if (p1) items.push({ slot: 1, video: p1 });

      const p2 = pickFrom(bucket2, usedChannels) || pickFrom(bucket0, usedChannels) || pickFrom(bucket3, usedChannels) || pickFrom(bucket1, usedChannels);
      if (p2) items.push({ slot: 2, video: p2 });

      const p3 = pickFrom(bucket3, usedChannels) || pickFrom(bucket0, usedChannels) || pickFrom(bucket1, usedChannels) || pickFrom(bucket2, usedChannels);
      if (p3) items.push({ slot: 3, video: p3 });

      if (curSize === 4) {
        const p4 = pickFrom(bucket0, usedChannels) || pickFrom(bucket2, usedChannels) || pickFrom(bucket3, usedChannels) || pickFrom(bucket1, usedChannels);
        if (p4) items.push({ slot: 4, video: p4 });
      }

      if (items.length < 3) break;
      bundles.push({
        index: bundles.length + 1,
        country: cKey,
        items,
      });
      if (bundles.length >= 60) break; // 화면 쾌적성을 위해 상위 60개 묶음(180~240개 영상) 우선 표시
    }
    return { bundles, totalVideos: raw.length, counts: { b1: bucket1.length, b2: bucket2.length, b3: bucket3.length, b0: bucket0.length } };
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
    `;
    document.head.appendChild(st);
  }

  function buildBundleCopyPrompt(b) {
    const meta = COUNTRY_META[b.country];
    const rules = COURSE_RULES[b.country];
    const lines = [];
    lines.push(`[🍱 모드 A (@daoyingtan 식 3~4팀 종합 코스 합본 롱폼 1편 + 주제별 파생 쇼츠 1·2·3 동시 제작 지시)]`);
    lines.push(`• 대상 국가 및 채널: ${meta.flag} ${meta.name} (${meta.channels})`);
    lines.push(`• 묶음 번호: 세트 #${b.index} (서로 다른 외국인 유튜버 ${b.items.length}팀 종합 옴니버스 · 권장 길이 14~17분)\n`);
    lines.push(`[🎬 본편 1~${b.items.length}부 구성 및 파생 쇼츠 #1~#${b.items.length} 매칭 원본 소스]`);
    b.items.forEach((it, idx) => {
      const v = it.video;
      const r = rules[idx] || rules[rules.length - 1];
      lines.push(`${idx + 1}부 (파생 쇼츠 #${idx + 1} — ${r.label}):`);
      lines.push(`  - 원본 채널명: ${v.channel}`);
      lines.push(`  - 원본 제목: ${v.title}`);
      lines.push(`  - 원본 링크: https://www.youtube.com/watch?v=${v.id} (조회수: ${fmt(v.views)} / 길이: ${v.length || "미확인"})`);
    });
    lines.push(`\n[📌 설명란 출처 표기 블록 (복붙용)]`);
    b.items.forEach(it => {
      const prefix = b.country === "tw" ? "影片來源：" : b.country === "jp" ? "映像出典：" : "영상 출처: ";
      lines.push(`${prefix}${it.video.channel} (https://www.youtube.com/watch?v=${it.video.id})`);
    });
    lines.push(`\n[🎨 @daoyingtan 스타일 5단 썸네일 & 파생 쇼츠 1·2·3 설계]`);
    lines.push(`• 썸네일 상단 빅타이포: ${meta.thumbTop}`);
    lines.push(`• 썸네일 중앙 ${b.items.length}분할: 1부(${b.items[0].video.channel}) ➡ 2부(${b.items[1].video.channel}) ➡ 3부(${b.items[2].video.channel}) 감정 대비 + 하단 알약 배지`);
    lines.push(`• 썸네일 하단 요약 바: ${meta.thumbBot}`);
    lines.push(`• 파생 쇼츠 분리 발행: ${meta.shortsGuide}`);
    return lines.join("\n");
  }

  function renderBundlesView() {
    injectBundleStyles();
    const infoEl = document.getElementById("bdinfo");
    const listEl = document.getElementById("bdlist");
    if (!infoEl || !listEl) return;

    // Update country button active states
    document.querySelectorAll("#bdcty .chip").forEach(btn => {
      btn.classList.toggle("on", btn.dataset.c === curCountry);
    });
    document.querySelectorAll("#bdsize .chip").forEach(btn => {
      btn.classList.toggle("on", +btn.dataset.n === curSize);
    });

    const { bundles, totalVideos, counts } = buildModeABundles(curCountry);
    const meta = COUNTRY_META[curCountry];
    const rules = COURSE_RULES[curCountry];

    infoEl.innerHTML =
      `<b>${meta.flag} ${meta.name}</b> 외국인 원본 롱폼 총 <b>${totalVideos.toLocaleString()}개</b> ` +
      `(1부 교통·편의·치안 <b>${counts.b1}개</b> / 2부 야시장·미식 <b>${counts.b2}개</b> / 3부 인심·자연·지방 <b>${counts.b3}개</b> / 기타 종합 <b>${counts.b0}개</b>) ` +
      `➔ <b>서로 다른 유튜버 ${curSize}팀씩 총 ${bundles.length}개 합본 세트</b> 자동 편성 완료!`;

    listEl.innerHTML = "";
    if (!bundles.length) {
      listEl.innerHTML = `<div class="empty">조건에 맞는 ${meta.name} 묶음 영상이 부족합니다. 검색어를 지우거나 '사용 완료 숨기기'를 해제해 보세요.</div>`;
      return;
    }

    bundles.forEach(b => {
      const box = document.createElement("div");
      box.className = "bd-box";

      const totalViews = b.items.reduce((acc, it) => acc + (it.video.views || 0), 0);
      const head = document.createElement("div");
      head.className = "bd-head";
      head.innerHTML = `
        <div class="bd-title">
          <span class="bd-badge">${meta.flag} 세트 #${b.index}</span>
          <span>${meta.name} ${b.items.length}팀 종합 코스 (1부 교통·편의 ➡ 2부 미식·야시장 ➡ 3부 인심·풍경)</span>
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
        renderBundlesView();
      };

      box.appendChild(head);

      const grid = document.createElement("div");
      grid.className = "bd-grid";

      b.items.forEach((it, idx) => {
        const v = it.video;
        const r = rules[idx] || rules[rules.length - 1];
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
              ${v._sc && !v._sc.held && typeof scTot === "function" ? `<span class="tag sc-${scGrade(v._sc)}">🎯 Argon ${scTot(v._sc)}점 (${scGrade(v._sc)})</span>` : ""}
              ${v._grade ? `<span class="tag grade-${v._grade}">🏆 ${v._grade}</span>` : ""}
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
          renderBundlesView();
        };
        card.querySelector(".dn").onclick = () => {
          done.has(v.id) ? done.delete(v.id) : done.add(v.id);
          saveAll();
          renderBundlesView();
        };
        card.querySelector(".hd").onclick = () => {
          hidden.has(v.id) ? hidden.delete(v.id) : hidden.add(v.id);
          saveAll();
          renderBundlesView();
        };
        grid.appendChild(card);
      });

      box.appendChild(grid);

      // Shorts 1, 2, 3 plan bar at the bottom of each bundle
      const plan = document.createElement("div");
      plan.className = "bd-shorts-plan";
      plan.innerHTML =
        `<div><b>🎬 롱폼 본편 (${b.items.length}팀 옴니버스 14~17분)</b>: ` +
        b.items.map((it, i) => `[${i + 1}부] ${it.video.channel}`).join(" ➡ ") +
        ` (설명란 출처 ${b.items.length}곳 동시 표기)</div>` +
        `<div><b>📱 주제별 파생 쇼츠 1·2·3 자동 분리</b>: ` +
        b.items.map((it, i) => `<b>쇼츠 #${i + 1}</b>(${it.video.channel} 하이라이트 50초)`).join(" + ") +
        ` ➔ 3개 쇼츠 모두 이 본편으로 <b>『관련 동영상』</b> 직결!</div>`;
      box.appendChild(plan);

      listEl.appendChild(box);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const mvBtn = document.getElementById("mv");
    if (!mvBtn) return;

    // 1. Add top nav button: "🍱 나라별 3~4팀 합본 묶음 (모드 A)" right after "🎬 영상"
    const mbdBtn = document.createElement("button");
    mbdBtn.className = "chip";
    mbdBtn.id = "mbd";
    mbdBtn.textContent = "🍱 나라별 3~4팀 합본 묶음 (모드 A)";
    mbdBtn.title = "@daoyingtan(島映談) 방식: 나라별(대만/한국/일본)로 서로 다른 주제의 외국인 원본 3~4팀을 1편(롱폼+쇼츠 1·2·3)으로 자동 묶어 배치합니다";
    mvBtn.after(mbdBtn);

    // 2. Create #bdview container
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
        <div class="qg" id="bdsize">
          <b>🍱 2단계: 1편당 합칠 외국인 팀 수</b>
          <button class="chip on" data-n="3">3팀 합본 (1부 교통·편의 + 2부 미식 + 3부 인심·풍경 ➔ 파생 쇼츠 #1·#2·#3)</button>
          <button class="chip" data-n="4">4팀 합본 (1~4부 종합 코스 ➔ 파생 쇼츠 #1~#4)</button>
        </div>
      </div>
      <div class="bar">
        <input id="bdq" placeholder="이 나라 묶음 안에서 키워드·지역(타이베이/가오슝/부산/교토 등)·유튜버 검색">
        <select id="bdsort">
          <option value="score">🏆 추천 합본 우선순위순 (Argon 채점 + S/A등급 + 조회수)</option>
          <option value="argon">🎯 Argon 스크립트 채점 점수 높은순 (점수판정기준_Argon용)</option>
          <option value="views">👁 원본 조회수 높은순</option>
          <option value="ratio">🔥 구독자 대비 조회수(아웃라이어)순</option>
          <option value="pub">📅 최신 업로드순</option>
        </select>
        <label class="chip" style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">
          <input type="checkbox" id="bdhidedone" checked style="width:15px;height:15px;margin:0;flex:none;min-width:0">
          사용 완료 영상 빼고 새 묶음만 짜기
        </label>
      </div>
      <div class="sub" style="max-width:1200px;margin:4px auto 8px;padding:0 16px" id="bdinfo"></div>
      <div class="bd-wrap" id="bdlist"></div>
    `;
    document.getElementById("thview").before(bdView);

    // Bind events inside #bdview
    bdView.querySelectorAll("#bdcty .chip").forEach(b => {
      b.onclick = () => {
        curCountry = b.dataset.c;
        renderBundlesView();
      };
    });
    bdView.querySelectorAll("#bdsize .chip").forEach(b => {
      b.onclick = () => {
        curSize = +b.dataset.n;
        renderBundlesView();
      };
    });
    document.getElementById("bdq").oninput = e => {
      curQuery = e.target.value.trim().toLowerCase();
      renderBundlesView();
    };
    document.getElementById("bdsort").onchange = e => {
      curSort = e.target.value;
      renderBundlesView();
    };
    document.getElementById("bdhidedone").onchange = e => {
      hideDoneInBundles = e.target.checked;
      renderBundlesView();
    };

    // Hook into setModeAll & setMode
    const origSetModeAll = window.setModeAll;
    window.setModeAll = function (m) {
      if (m === "bd") {
        ["mv", "mc", "ms", "mct", "mnw", "mth"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.classList.remove("on");
        });
        mbdBtn.classList.add("on");
        document.querySelectorAll(".vmode").forEach(e => (e.hidden = true));
        ["chview", "scview", "ctview", "nwview", "thview", "my-score-view", "hidden-videos-view"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.hidden = true;
        });
        bdView.hidden = false;
        renderBundlesView();
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
