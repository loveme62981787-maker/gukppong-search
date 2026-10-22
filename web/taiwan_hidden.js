// 대만 수집 목록과 숨긴 영상 관리. index.html과 분리해 유지한다.
document.addEventListener('DOMContentLoaded', () => {
  // 공개 소개에서 비대만인 출연자와 대만 현지 체험을 확인한 영상만 포함한다.
  // 기존 후보 데이터는 전체 목록에 보존하며, 국적/현지 체험 불명은 자동 승격하지 않는다.
  const twIds = new Set(["IKIwmB4zXNw", "U__G4YsNtiw", "kBE3UhVhsNI", "ZiBKnAIBD9U", "4u76mAAGrcw", "lz-EgkDnpTk", "j7-PsRQlcpU", "dnRPz16grio", "G2cICamw2Fc", "QkYBHJQwyk0", "vyu92BFHbKs", "pKlg2N1DrI4", "KknlT4bm4V0", "iNE5034ES-s", "lY831BJYsqs", "xXtlEkslsTg", "ix9q4OpCTAo", "4-HxQiZCT_U", "d2ci74qsbKg", "80g1CvTRsJM", "5Roqlrzlw8A", "rjtZsB5TeAw", "Y8qTC2x_04M", "zc8I4K5hzcY", "P0_woHrNcmU", "_cgQXAlgtyk", "_qerpc9lxqk", "G0-UFWOLMvI", "ZzH-Cd-6RXU", "2UPkezZ4lcI", "1pukmFkZJTg", "X6gG_5KUy4Q", "FhC_2oJI2X0", "4zStevSrTww", "t1Gu01Lu31M", "IqnjfZdYM-w", "847F9dESXZg", "WsU4UMjLk4A", "Cga4kCh2T3o"]);
  LISTS.splice(4, 0, ['twexp', '🇹🇼 대만체험']);
  LISTKEYS.add('twexp'); LISTTAG.twexp = '🇹🇼 대만체험';
  LIST_NOTE.twexp = '대만 사람이 아닌 출연자의 대만 현지 체험·생활 경험 영상입니다. 공개 영상 설명과 채널 소개를 확인해 선별했으며, 영상 전문 검수와 FM 채점 완료를 뜻하지 않습니다.';
  const originalLists = computeLists;
  computeLists = function() {
    originalLists();
    V.forEach(v => {
      if (v.alert && v.alert_country === '대만') {
        v._lists = v._lists.filter(k => k !== 'alert_kr' && k !== 'alert_jp');
        if (!v._lists.includes('alert_tw')) v._lists.push('alert_tw');
      }
    });
    V.forEach(v => {
      if (!twIds.has(v.id)) return;
      if (!v._lists.includes('twexp')) v._lists.push('twexp');
      v._hold = false;
      if (v.country === '대만') v._subj = '대만';
    });
  };
  LISTS.splice(LISTS.findIndex(x => x[0] === 'alert_jp') + 1, 0, ['alert_tw', '🔔 텔레그램(대만)']);
  LISTKEYS.add('alert_tw'); LISTTAG.alert_tw = '🔔 텔레그램(대만)';
  LIST_NOTE.alert_tw = '대만 텔레그램 알림으로 받은 영상입니다. 대만체험 편입과 스크립트 채점은 별도 검토합니다.';
  const twAlert = ce('button', 'chip', '🔔 텔레그램(대만)'); twAlert.dataset.k = 'alert_tw'; twAlert.append(ce('small', '', '0'));
  twAlert.onclick = () => { listSel.has('alert_tw') ? listSel.delete('alert_tw') : listSel.add('alert_tw'); ls.set('lists', [...listSel]); render(); };
  document.querySelector('#lists [data-k="alert_jp"]').after(twAlert);
  if ((ls.get('lists', []) || []).includes('alert_tw')) listSel.add('alert_tw');
  computeLists();
  refreshListCounts();
  document.querySelector('header h1, header h2, h1').textContent = '🇰🇷🇯🇵🇹🇼 국뽕 영상 서칭';
  const tw = ce('button', 'chip', '🇹🇼 대만체험'); tw.dataset.k = 'twexp'; tw.append(ce('small', '', String(twIds.size)));
  tw.onclick = () => { listSel.has('twexp') ? listSel.delete('twexp') : listSel.add('twexp'); ls.set('lists', [...listSel]); render(); };
  document.querySelector('#lists [data-k="jpexp"]').after(tw);
  if ((ls.get('lists', []) || []).includes('twexp')) listSel.add('twexp');
  // 목록 키와 클릭 동작은 유지하고 사용자 요청 표시명만 통일한다.
  const names = {notion:'📓 노션 수집목록', krexp:'🇰🇷 한국체험', jpexp:'🇯🇵 일본체험', twexp:'🇹🇼 대만체험', krguk:'🧭 국뽕채널(한국)', jpguk:'🎌 국뽕채널(일본)', ref:'📌 레퍼런스모음', bm:'🎯 벤치마킹', alert_kr:'🔔 텔레그램(한국)', alert_jp:'🔔 텔레그램(일본)', hold:'🗂 분류보류'};
  for (const entry of LISTS) {
    if (!names[entry[0]]) continue;
    entry[1] = names[entry[0]];
    const chip = document.querySelector('#lists [data-k="' + entry[0] + '"]');
    if (chip) {
      const count = chip.querySelector('small');
      chip.replaceChildren(document.createTextNode(entry[1]));
      if (count) chip.append(count);
    }
  }


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
          if (tag.title.includes('대상국이 불분명')) tag.title = '공개 소개에서 비대만인 출연자의 대만 현지 체험을 확인했습니다. 영상 전문 검수·채점은 별도입니다.';
        }
      }
    }
  };
  render();
});
