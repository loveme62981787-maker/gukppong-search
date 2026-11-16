// 🔥 터진 쇼츠 독립 화면 (한국·일본·대만 채널 소재 국가별). 데이터: hot_shorts.js (hot_shorts_watch.py 가 만든다)
// - 롱폼 기본 필터(180초 이하 숨김)와 무관한 별도 화면이다: 이 화면은 V(영상 목록)와 lenmode 를 쓰지 않는다.
// - 같은 영상 ID 의 저장·사용 완료·숨김·메모는 index.html 의 favs/done/hidden/memos 를 그대로 공유한다 (saveAll 로 같은 저장소에 쓴다).
// - 모든 화면 문구는 textContent 로만 넣고 링크는 검증된 ID 로만 만든다 (innerHTML 에 데이터를 넣지 않는다 → XSS 방지).
// - 기준 문구는 데이터가 내보낸 criteria 값에서 만든다 (코드 상수와 화면 문구가 어긋나지 않게).
(function (root) {
  "use strict";
  const ID_RE = /^[A-Za-z0-9_-]{11}$/, CH_RE = /^UC[A-Za-z0-9_-]{22}$/;
  const COUNTRY_ORDER = ["KR", "JP", "TW"];
  const KIND_BADGE = {
    reaction_edit: ["🎞 해외반응·편집 채널 — 벤치마킹 참고용 (재사용 가능한 원본 아님)", "kind-local", "다른 사람이 편집·재구성한 영상이에요. 이 목록에 있다는 사실이 재사용 허가를 뜻하지 않아요."],
    unverified: ["❔ 성격 미확인 채널 — 원본 여부를 확인하기 전 (재사용 가능한 원본으로 보지 않아요)", "kind-unk", "원본 촬영자인지 편집 채널인지 확인하지 못했어요. 확인 전까지 벤치마킹 참고용으로만 보세요."],
    travel_original: ["🧳 원본 여행자 채널 — 재사용 권리는 영상별로 따로 확인", "kind-foreign", "촬영한 사람 본인의 채널이에요. 라이선스(CC BY 등)는 이 목록과 별개로 영상마다 확인해야 해요."],
  };
  const safeVideoId = s => typeof s === "string" && ID_RE.test(s) ? s : null;
  const safeChannelId = s => typeof s === "string" && CH_RE.test(s) ? s : null;
  const num = n => typeof n === "number" && isFinite(n) ? n : null;
  const fmtN = n => n == null ? "?" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(n);
  const fmtX = n => n == null ? "-" : (Math.round(n * 10) / 10) + "배";
  // JP·TW 채널은 한국어 병기명(name_ko)이 있으면 "원어명 (한국어명)" 으로 보여준다
  const chName = ch => !ch ? "채널" : (ch.title || ch.handle || "채널") + (ch.name_ko && ch.name_ko !== ch.title ? " (" + ch.name_ko + ")" : "");
  const pct = r => Math.round((num(r) || 0) * 100) + "%";

  // 기준 문구: criteria(내보낸 코드 상수)에서 만든다
  function criteriaText(c) {
    return `터진 쇼츠 = Shorts 탭·Shorts 재생목록에서 실제 확인된 영상 중 조회수 ${c.min_views.toLocaleString("ko-KR")}회 이상 (한국·일본·대만 공통, 구독자 수와 무관). ` +
      `화면의 '구독자 대비'와 '표본 중앙값 대비' 배수는 입장 조건이 아니라 표시·정렬 보조예요 (구독자 대비는 실제 조회수÷구독자). ` +
      `채널 하나에서 보여주는 개수는 제한하지 않고, 최근 업로드 ${c.fetch_n || "?"}개와 Shorts 재생목록 ${c.shorts_n || "?"}개까지 읽어요 (그보다 오래된 Shorts는 실행마다 ${c.backfill_pages || "?"}페이지(페이지당 50개)씩 이어받고, 이미 확인한 영상은 누적 보존). ` +
      `표본 = 채널의 최근 업로드 ${c.sample_n}개 (중앙값은 그중 Shorts 확인 영상이 ${c.min_median_sample}개 이상일 때만 계산). ` +
      `쇼츠 중심 = 표본이 ${c.sample_n}개 이상이고 Shorts 확인 비율(보류 포함 전체 표본 기준) ${Math.round(c.center_ratio * 100)}% 이상. 전부 쇼츠 = 같은 표본 전부가 Shorts로 확인됨. ` +
      `둘 다 '최근 표본 기준'일 뿐 앞으로도 쇼츠만 올린다는 뜻이 아니에요. 길이(3분 이하)만으로는 쇼츠로 확정하지 않고, 증거가 부족하면 보류해요. Shorts 탭 첫 페이지에 없다는 것만으로는 '쇼츠 아님'으로 확정하지 않아요 (고정·오래된 영상 때문). 3분 초과 영상만 쇼츠 아님으로 확정해요. ` +
      `채널 주제(외국인이 나오는 한국·일본·대만 여행 체험·반응)는 채널 소개가 아니라 실제 영상 제목 근거로 사람이 확인해 시드에 올린 것이고, 자동 발굴 후보는 근거 확인 전에는 공개하지 않아요. 여러 주제를 섞는 채널은 영상 제목에 외국인 신호와 대상국 이름이 함께 있는 쇼츠만 보여주고, 나머지는 보류해요 (제목만 본 것이라 영상을 직접 시청해 확인했다는 뜻이 아니에요).`;
  }

  // 채널 배지: [문구, 클래스, 설명]
  function channelBadges(ch, center) {
    const out = [], n = num(ch.sample_n) || 0, k = num(ch.sample_shorts) || 0;
    const sample = `최근 ${n}개 중 Shorts 확인 ${k}개 (${pct(ch.shorts_ratio)})`;
    if (ch.shorts_centered) out.push(["🎯 쇼츠 중심 (최근 표본 기준)", "kind-ref", sample + " · 영구 단정 아님"]);
    else out.push([`🔀 쇼츠·롱폼 혼합 또는 표본 부족 — 쇼츠 중심 기준 미충족 (${n}개 중 ${k}개 확인, ${pct(ch.shorts_ratio)})`, "kind-unk", sample + " · 쇼츠 중심 기준(" + Math.round((center || 0.9) * 100) + "%)에 못 미쳐요. 보류·롱폼을 쇼츠로 세지 않았어요"]);
    if (ch.user_reference) out.push(["📌 사용자 지정 참고 채널", "kind-ref", "쇼츠 중심 기준과 상관없이 직접 지정해 목록에 넣은 채널이에요"]);
    if (ch.all_shorts_strict) out.push(["✅ 표본 전부 쇼츠 (엄격)", "kind-inst", `최근 ${n}개 전부 Shorts 탭에서 확인 · 앞으로도 그렇다는 뜻은 아니에요`]);
    if (ch.country_basis === "seed_manual") out.push(["국가: 수동 지정", "kind-unk", "채널 정보에 국가가 비어 있어 직접 지정했어요"]);
    const kb = KIND_BADGE[ch.kind] || KIND_BADGE.unverified;
    out.push([kb[0], kb[1], kb[2]]);
    if (num(ch.sample_pending) > 0) out.push([`⏳ 보류 ${ch.sample_pending}개`, "kind-unk", "Shorts 탭으로 확인할 증거가 부족한 영상 (길이로 추정하지 않아요)"]);
    return out;
  }

  const hay = (v, ch, memos) => ((v.title || "") + " " + (ch ? ch.title + " " + ch.handle + " " + (ch.name_ko || "") : "") + " " + ((memos && memos[v.id]) || "")).toLowerCase();

  // 보기 필터: 같은 영상 ID 의 숨김·사용 완료 상태는 영상 화면과 같은 집합을 쓴다 (기본은 둘 다 제외)
  function filterVideos(videos, chById, o) {
    const st = o.state, q = (o.q || "").trim().toLowerCase();
    return videos.filter(v => {
      if (!safeVideoId(v.id)) return false;
      if (o.country && v.country !== o.country) return false;
      const ch = chById[v.channel_id];
      if (o.kind && (!ch || ch.kind !== o.kind)) return false;
      if (o.mine === "hidden") { if (!st.hidden.has(v.id)) return false; } else if (st.hidden.has(v.id)) return false;
      if (o.mine === "done") { if (!st.done.has(v.id)) return false; } else if (!o.mine && st.done.has(v.id)) return false;
      if (o.mine === "fav" && !st.favs.has(v.id)) return false;
      if (o.mine === "memo" && !st.memos[v.id]) return false;
      if (q && !hay(v, ch, st.memos).includes(q)) return false;
      return true;
    });
  }
  function sortVideos(list, key) {
    const by = {
      views: (a, b) => (b.views || 0) - (a.views || 0),
      sub: (a, b) => (b.sub_multiple || 0) - (a.sub_multiple || 0) || (b.views || 0) - (a.views || 0),
      median: (a, b) => (b.median_multiple || 0) - (a.median_multiple || 0) || (b.views || 0) - (a.views || 0),
      pub: (a, b) => (b.published || "").localeCompare(a.published || ""),
    };
    return list.slice().sort(by[key] || by.views);
  }

  // ---- DOM (textContent 전용) ----
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const link = (text, href, cls) => { const a = el("a", cls, text); if (href) { a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer"; } return a; };
  const tag = (text, cls, title) => { const s = el("span", "tag" + (cls ? " " + cls : ""), text); if (title) s.title = title; return s; };
  const chUrl = id => safeChannelId(id) ? "https://www.youtube.com/channel/" + id : null;

  function channelCard(ch) {
    const c = el("div", "card " + (ch.kind === "travel_original" ? "kd-foreign" : "kd-local"));
    const b = el("div", "body");
    const t = link(chName(ch), chUrl(ch.id), "t"); b.append(t);
    const m = el("div", "m");
    m.append(ch.handle ? ch.handle + " · " : "", "구독자 " + fmtN(num(ch.subs)), " · 확인 " + (ch.checked || "-"));
    b.append(m);
    const tags = el("div", "tags");
    channelBadges(ch, (data().criteria || {}).center_ratio).forEach(x => tags.append(tag(x[0], x[1], x[2])));
    tags.append(tag("🔥 터진 쇼츠 " + (num(ch.hot_n) || 0) + "개", "hot"));
    if (num(ch.pending_hot) > 0) tags.append(tag("⏳ 터질 조회수지만 쇼츠 증거 부족 " + ch.pending_hot + "개 (보류)", "kind-unk"));
    b.append(tags);
    const act = el("div", "act");
    act.append(link("채널", chUrl(ch.id), "btn"), link("쇼츠 탭", chUrl(ch.id) && chUrl(ch.id) + "/shorts", "btn"));
    b.append(act);
    if (ch.note) b.append(el("div", "sub", ch.note));
    if (ch.last_error) b.append(el("div", "sub", "⚠ 마지막 수집 실패(" + (ch.last_error_at || "-") + "): 이전 확인 결과를 유지하고 있어요"));
    c.append(b);
    return c;
  }

  function videoCard(v, ch, st, onChange) {
    const id = v.id;
    const card = el("div", "card " + (ch && ch.kind === "travel_original" ? "kd-foreign" : "kd-local") + (st.done.has(id) ? " done" : ""));
    const th = el("div", "th");
    const fav = el("button", "fav" + (st.favs.has(id) ? " on" : ""), st.favs.has(id) ? "★" : "☆");
    const a = link("", "https://www.youtube.com/shorts/" + id);
    const img = el("img"); img.loading = "lazy"; img.alt = ""; img.src = "https://i.ytimg.com/vi/" + id + "/mqdefault.jpg";
    a.append(img, el("div", "play", "▶"));
    th.append(fav, a);
    const b = el("div", "body");
    b.append(link(v.title || "(제목 없음)", "https://www.youtube.com/shorts/" + id, "t"));
    const m = el("div", "m");
    m.append(link(chName(ch), chUrl(v.channel_id), "chl"), " · 업로드 " + (v.published || "-"));
    b.append(m);
    const tags = el("div", "tags");
    tags.append(tag("👁 " + fmtN(num(v.views)), "", (num(v.views) || 0).toLocaleString("ko-KR") + "회"));
    tags.append(tag("구독자 대비 " + fmtX(num(v.sub_multiple)), "hot", "실제 조회수 ÷ 구독자 (선별에는 별도로 분모 최소 1천을 썼어요)"));
    tags.append(tag("표본 중앙값 대비 " + fmtX(num(v.median_multiple)), "hot", "채널 최근 표본의 Shorts 확인 영상 조회수 중앙값 대비"));
    tags.append(tag("확인 " + (v.checked || "-"), "", v.short_signal === "kept" ? "이전 확인 결과를 보존한 값이에요 (이번에는 탭을 다시 확인하지 못함)" : "Shorts 탭에서 확인한 날"));
    if (ch) {
      tags.append(tag("쇼츠 표본 " + (num(ch.sample_shorts) || 0) + "/" + (num(ch.sample_n) || 0) + " (" + pct(ch.shorts_ratio) + ")", "", "채널 최근 업로드 표본 중 Shorts 확인 비율"));
      if (ch.shorts_centered) tags.append(tag("🎯 쇼츠 중심(최근)", "kind-ref"));
      if (ch.all_shorts_strict) tags.append(tag("✅ 전부 쇼츠(표본)", "kind-inst"));
      const kb = KIND_BADGE[ch.kind] || KIND_BADGE.unverified;
      tags.append(tag(kb[0], kb[1], kb[2]));
    }
    tags.append(tag("Shorts 탭 확인", "kind-ref", "길이가 아니라 채널 /shorts 탭에 실제로 나온 영상"));
    b.append(tags);
    const act = el("div", "act");
    const ok = el("button", "btn ok" + (st.done.has(id) ? " on" : ""), st.done.has(id) ? "✓ 사용 완료" : "사용 완료");
    const memo = el("button", "btn memo" + (st.memos[id] ? " on" : ""), "📝 메모");
    const hd = el("button", "btn hd", st.hidden.has(id) ? "↩ 복구" : "🗑 숨김");
    act.append(ok, memo, hd);
    const ta = el("textarea"); ta.hidden = true; ta.placeholder = "메모 (이 브라우저에만 저장돼요)"; ta.value = st.memos[id] || "";
    b.append(act, ta);
    card.append(th, b);
    const toggle = (set) => { set.has(id) ? set.delete(id) : set.add(id); onChange(); };
    fav.onclick = () => toggle(st.favs); ok.onclick = () => toggle(st.done); hd.onclick = () => toggle(st.hidden);
    memo.onclick = () => { ta.hidden = !ta.hidden; if (!ta.hidden) ta.focus(); };
    ta.oninput = () => { ta.value.trim() ? st.memos[id] = ta.value : delete st.memos[id]; memo.classList.toggle("on", !!st.memos[id]); onChange(true); };
    return card;
  }

  const data = () => root.HOT_SHORTS || {channels: [], videos: [], criteria: null, countries: {}};
  let countrySel = "all";
  // 채널당 개수 제한은 없지만 화면에는 나라별로 PAGE 개씩 보여주고 '더 보기'로 늘린다 (카드 수천 개를 한 번에 그리지 않으려는 표시 한도이지 수집 한도가 아니다)
  const PAGE = 60, shown = {KR: PAGE, JP: PAGE, TW: PAGE};
  function setCountry(cc) { countrySel = cc === "KR" || cc === "JP" || cc === "TW" ? cc : "all"; }

  function render() {
    const D = data(), body = document.getElementById("hsbody");
    if (!body) return;
    // index.html 의 상태 집합을 이름으로 읽는다: 가져오기 등으로 새 Set 으로 바뀌어도 항상 최신 값
    const st = {favs, done, hidden, memos};
    const onChange = quiet => { saveAll(); if (!quiet) render(); };
    const chById = {}; D.channels.forEach(c => { chById[c.id] = c; });
    const q = document.getElementById("hsq").value, sortKey = document.getElementById("hssort").value, kind = document.getElementById("hskind").value, mine = document.getElementById("hsmine").value;
    const crit = document.getElementById("hscrit"); if (crit && D.criteria) crit.textContent = criteriaText(D.criteria);
    const chips = document.getElementById("hscty"); chips.textContent = "";
    const mkChip = (k, label) => { const b = el("button", "chip" + (countrySel === k ? " on" : ""), label); b.onclick = () => { countrySel = k; render(); }; chips.append(b); };
    mkChip("all", "전체 " + D.videos.length);
    COUNTRY_ORDER.forEach(cc => mkChip(cc, `터진 쇼츠 (${D.countries[cc] || cc}) ${D.videos.filter(v => v.country === cc).length}`));
    body.textContent = "";
    document.getElementById("hsinfo").textContent = `채널 ${D.channels.length}개 · 터진 쇼츠 ${D.videos.length}개 · 갱신 ${D.updated || "-"} · 이 화면은 길이 필터와 무관하게 Shorts 탭에서 확인된 쇼츠만 보여줘요`;
    if (root.syncHotButtons) root.syncHotButtons(countrySel);
    COUNTRY_ORDER.filter(cc => countrySel === "all" || countrySel === cc).forEach(cc => {
      const name = D.countries[cc] || cc;
      const chs = D.channels.filter(c => c.country === cc && (!kind || c.kind === kind) && ((num(c.sample_n) || 0) > 0 || c.user_reference));
      const vids = sortVideos(filterVideos(D.videos, chById, {country: cc, q, kind, mine, state: st}), sortKey);
      const sec = el("section", "sc-sec");
      sec.append(el("h2", "", `🔥 터진 쇼츠 (${name})`));
      sec.append(el("p", "sc-mute", `영상 주제 국가 기준 · 쇼츠 채널 ${chs.length}개 · 보이는 터진 쇼츠 ${vids.length}개`));
      const det = el("details"); det.open = true;
      det.append(el("summary", "", `📺 ${name} 쇼츠 채널 목록 (${chs.length})`));
      const cg = el("div", "grid");
      if (!chs.length) cg.append(el("div", "empty", "아직 이 나라에서 검증된 채널이 없어요"));
      chs.slice().sort((a, b) => (b.shorts_centered - a.shorts_centered) || ((b.subs || 0) - (a.subs || 0))).forEach(c => cg.append(channelCard(c)));
      det.append(cg); sec.append(det);
      sec.append(el("h3", "", `🔥 터진 쇼츠 (${name}) 영상`));
      const vg = el("div", "grid");
      if (!vids.length) vg.append(el("div", "empty", "조건에 맞는 터진 쇼츠가 없어요"));
      vids.slice(0, shown[cc]).forEach(v => vg.append(videoCard(v, chById[v.channel_id], st, onChange)));
      sec.append(vg);
      if (vids.length > shown[cc]) {
        const more = el("button", "btn", `더 보기 (${shown[cc]}/${vids.length})`);
        more.onclick = () => { shown[cc] += PAGE; render(); };
        sec.append(more);
      }
      body.append(sec);
    });
  }
  root.renderHotShorts = render;
  root.setHotCountry = cc => { setCountry(cc); };
  root.HotShortsView = {chName, safeVideoId, safeChannelId, criteriaText, channelBadges, setCountry, filterVideos, sortVideos, channelCard, videoCard, KIND_BADGE, render};
  if (typeof document !== "undefined" && document.getElementById) {
    ["hsq", "hssort", "hskind", "hsmine"].forEach(i => { const e = document.getElementById(i); if (e) e.addEventListener("input", render); });
  }
})(typeof window !== "undefined" ? window : globalThis);
