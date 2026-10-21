// 대만 수집 목록과 숨긴 영상 관리. index.html과 분리해 유지한다.
document.addEventListener('DOMContentLoaded', () => {
  const twIds = new Set((window.TAIWAN_ITEMS || []).map(v => v.id));
  LISTS.splice(4, 0, ['twexp', '🇹🇼 대만 체험']);
  LISTKEYS.add('twexp'); LISTTAG.twexp = '🇹🇼 대만 체험 후보';
  LIST_NOTE.twexp = '외국인의 대만 여행·체험을 검색한 롱폼 후보입니다. 제목·채널 기준으로 선별했고, 영상 전문 검수와 FM 채점은 아직 하지 않았습니다.';
  const originalLists = computeLists;
  computeLists = function() {
    originalLists();
    V.forEach(v => {
      if (!twIds.has(v.id)) return;
      if (!v._lists.includes('twexp')) v._lists.push('twexp');
      v._hold = false;
      if (v.country === '대만') v._subj = '대만';
    });
  };
  computeLists();
  refreshListCounts();
  document.querySelector('header h1, header h2, h1').textContent = '🇰🇷🇯🇵🇹🇼 국뽕 영상 서칭';
  const tw = ce('button', 'chip', '🇹🇼 대만 체험'); tw.dataset.k = 'twexp'; tw.append(ce('small', '', String(twIds.size)));
  tw.onclick = () => { listSel.has('twexp') ? listSel.delete('twexp') : listSel.add('twexp'); ls.set('lists', [...listSel]); render(); };
  document.querySelector('#lists [data-k="jpexp"]').after(tw);
  if ((ls.get('lists', []) || []).includes('twexp')) listSel.add('twexp');

  const button = ce('button', 'chip', '🙈 숨긴 영상'); button.id = 'hidden-videos-tab';
  document.getElementById('mmy').after(button);
  const panel = ce('section', 'sc-wrap'); panel.hidden = true; panel.id = 'hidden-videos-view';
  document.getElementById('my-score-view').after(panel);
  let showing = false;
  const draw = () => {
    panel.replaceChildren(ce('h2', '', '숨긴 영상'), ce('p', 'sc-mute', '목록·국가 필터와 관계없이 이 브라우저에서 숨긴 영상을 모두 보여줍니다. 복원하면 기존 목록으로 돌아갑니다.'));
    const search = ce('input'); search.placeholder = '숨긴 영상 제목·채널 검색'; search.setAttribute('aria-label', search.placeholder); panel.append(search);
    const grid = ce('div', 'grid'); panel.append(grid);
    const show = () => {
      grid.replaceChildren();
      const q = search.value.trim().toLowerCase();
      const rows = V.filter(v => hidden.has(v.id) && (!q || (v.title + ' ' + v.channel).toLowerCase().includes(q)));
      if (!rows.length) grid.append(ce('p', 'empty', '숨긴 영상이 없습니다.'));
      for (const v of rows) {
        const card = ce('article', 'card my-card'), a = ce('a', 't', v.title); a.href = 'https://youtu.be/' + v.id; a.target = '_blank'; a.rel = 'noopener';
        const img = ce('img'); img.src = 'https://i.ytimg.com/vi/' + v.id + '/mqdefault.jpg'; img.alt = ''; img.loading = 'lazy';
        const restore = ce('button', 'chip', '↩ 숨김 해제 · 복원');
        restore.onclick = () => { hidden.delete(v.id); saveAll(); render(); draw(); };
        card.append(img, a, ce('p', 'sc-mute', v.channel), restore); grid.append(card);
      }
    };
    search.oninput = show; show();
  };
  const previousMode = setMode;
  setMode = function(m) {
    showing = m === 'hidden-videos'; previousMode(showing ? 's' : m); panel.hidden = !showing; button.classList.toggle('on', showing);
    if (showing) { document.getElementById('scview').hidden = true; document.getElementById('ms').classList.remove('on'); draw(); }
  };
  button.onclick = () => setMode('hidden-videos');
  const previousRender = render;
  render = function(...args) {
    previousRender.apply(this, args);
    button.textContent = '🙈 숨긴 영상 ' + V.filter(v => hidden.has(v.id)).length;
    for (const card of document.querySelectorAll('.card')) {
      const a = card.querySelector('a.t'); if (!a) continue;
      const id = a.getAttribute('href').split('/').pop();
      const hide = card.querySelector('.hd');
      if (hide) { hide.textContent = hidden.has(id) ? '↩ 숨김 해제' : '🙈 숨기기'; hide.title = '상단 숨긴 영상에서 확인하고 복원할 수 있습니다.'; }
      for (const tag of card.querySelectorAll('.tag')) {
        if (tag.title.includes('🏆 등급은')) tag.title = '아직 스크립트를 읽고 채점하지 않은 영상입니다.';
        if (twIds.has(id)) {
          if (tag.textContent === '🌐 기타') tag.textContent = '🇹🇼 대만';
          if (tag.title.includes('대상국이 불분명')) tag.title = '대만 여행·체험 후보. 외국인 원본 여부는 아직 전문 검수 전입니다.';
        }
      }
    }
  };
  render();
});
