// 터진 영상 목록(한국·일본·대만): 체험 목록 영상 중 구독자 대비 조회수가 높은 영상을 따로 모은다.
// 체험 목록은 기존 원본 분류와 대만 수동 검토 결과를 재사용한다.
function breakoutKeys(v, isHot) {
  if (!Number.isFinite(v.subs) || v.subs <= 0 || !Number.isFinite(v.views) ||
      !isHot(v) || v.ref || v.bm || ['local', 'inst'].includes(v._kind)) return [];
  const pairs = [['krexp', 'hot_kr'], ['jpexp', 'hot_jp'], ['twexp', 'hot_tw']];
  return pairs.filter(([key]) => v._lists.includes(key)).map(([, key]) => key);
}

// 같은 채널(channel_id)에서 사이트가 수집한 같은 형식(숏폼/롱폼) 영상의 조회수 중앙값 대비 배수.
// 자기 자신은 빼고, 같은 영상 ID는 한 번만 세며, 유효한 조회수만 쓴다. 표본이 minN개 미만이면 null(표시 생략).
// 채널 전체의 실제 중앙값이 아니라 '수집된 표본' 기준이다.
function channelMedianRatio(v, pool, minN = 4) {
  if (!v.channel_id || !v._form || v._form === 'unk' || !Number.isFinite(v.views)) return null;
  const seen = new Set();
  const views = [];
  for (const x of pool) {
    if (x.id === v.id || seen.has(x.id) || x.channel_id !== v.channel_id || x._form !== v._form) continue;
    seen.add(x.id);
    if (Number.isFinite(x.views) && x.views >= 0) views.push(x.views);
  }
  if (views.length < minN) return null;
  views.sort((a, b) => a - b);
  const mid = views.length >> 1;
  const median = views.length % 2 ? views[mid] : (views[mid - 1] + views[mid]) / 2;
  return median > 0 ? {n: views.length, median, x: v.views / median} : null;
}

// 카드에 붙일 설명: 구독자 대비 배수(터짐 기준과 같은 계산) + 수집 표본 중앙값 대비(표본이 충분할 때만)
const BREAKOUT_KEYS = ['hot_kr', 'hot_jp', 'hot_tw'];
function breakoutInfo(v, pool, ratio) {
  if (!(v._lists || []).some(k => BREAKOUT_KEYS.includes(k))) return null;
  return {sub: ratio(v), med: channelMedianRatio(v, pool)};
}

document.addEventListener('DOMContentLoaded', () => {
  const defs = [['hot_kr', '🔥 터진 영상 (한국)', '한국'], ['hot_jp', '🔥 터진 영상 (일본)', '일본'], ['hot_tw', '🔥 터진 영상 (대만)', '대만']];
  const hold = document.querySelector('#lists [data-k="hold"]');
  if (typeof LISTS === 'undefined' || !hold) return;
  const sep = document.createElement('span'); sep.className = 'lsep'; sep.textContent = '|'; sep.setAttribute('aria-hidden', 'true');
  hold.before(sep);
  const saved = ls.get('lists', []);
  for (const [key, label, country] of defs) {
    LISTS.splice(LISTS.findIndex(x => x[0] === 'hold'), 0, [key, label]);
    LISTKEYS.add(key); LISTTAG[key] = label;
    LIST_NOTE[key] = `${country} 체험 목록 영상 중 구독자 대비 조회수가 높은(📈) 영상이에요. 레퍼런스·벤치마킹·현지 채널·기관 영상은 빼요. 체험 목록과 같은 추정이라 영상 내용을 보고 확인한 것은 아니에요.`;
    const b = document.createElement('button'); b.className = 'chip'; b.dataset.k = key; b.append(label);
    b.append(Object.assign(document.createElement('small'), {textContent: '0'}));
    b.onclick = () => { listSel.has(key) ? listSel.delete(key) : listSel.add(key); ls.set('lists', [...listSel]); render(); };
    hold.before(b);
    if (Array.isArray(saved) && saved.includes(key)) listSel.add(key);
  }
  // 목록 계산(대만 후처리 포함)이 끝난 다음 덧붙인다. 출처 유형을 바꿔 다시 계산할 때도 같은 순서로 적용된다
  const prev = computeLists;
  computeLists = function () {
    prev();
    V.forEach(v => { v._lists = v._lists.filter(k => !BREAKOUT_KEYS.includes(k)); v._lists.push(...breakoutKeys(v, isHot)); });
  };
  computeLists();
  refreshListCounts();
  render();
});
