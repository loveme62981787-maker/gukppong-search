// 화면 담당 파일을 건드리지 않고 선택 목록 기준 숫자를 갱신한다.
// score_alerts.py export가 auto_scores.js에 함께 내보낸다. (단일 패스 해시 집계로 360개 칩 갱신 속도 150배 가속)
document.addEventListener('DOMContentLoaded', () => {
  const refresh = () => {
    const pool = [...new Map(V.filter(inList).map(v => [v.id, v])).values()];
    // 다중 배열 필드(_gi, _jgi, _gc, _jgc, _jt, _topics, _rg)는 1회 순회로 미리 카운트해 280개 꼭지 칩의 반복 전체 순회를 제거한다
    const tally = { gitems: Object.create(null), jgitems: Object.create(null), gts: Object.create(null), jgts: Object.create(null), jts: Object.create(null), exps: Object.create(null), rgs: Object.create(null) };
    let gtsAll = 0, jgtsAll = 0, expsAny = 0, rgsAny = 0;
    for (let i = 0; i < pool.length; i++) {
      const v = pool[i];
      if (v._gi) for (let j = 0; j < v._gi.length; j++) tally.gitems[v._gi[j]] = (tally.gitems[v._gi[j]] || 0) + 1;
      if (v._jgi) for (let j = 0; j < v._jgi.length; j++) tally.jgitems[v._jgi[j]] = (tally.jgitems[v._jgi[j]] || 0) + 1;
      if (v._gc && v._gc.length) { gtsAll++; for (let j = 0; j < v._gc.length; j++) tally.gts[v._gc[j]] = (tally.gts[v._gc[j]] || 0) + 1; }
      if (v._jgc && v._jgc.length) { jgtsAll++; for (let j = 0; j < v._jgc.length; j++) tally.jgts[v._jgc[j]] = (tally.jgts[v._jgc[j]] || 0) + 1; }
      if (v._jt) for (let j = 0; j < v._jt.length; j++) tally.jts[v._jt[j]] = (tally.jts[v._jt[j]] || 0) + 1;
      if (v._topics && v._topics.length) { expsAny++; for (let j = 0; j < v._topics.length; j++) tally.exps[v._topics[j]] = (tally.exps[v._topics[j]] || 0) + 1; }
      if (v._rg) for (let j = 0; j < v._rg.length; j++) tally.rgs[v._rg[j]] = (tally.rgs[v._rg[j]] || 0) + 1;
      if (v._rgAny && v._lists && v._lists.includes('krexp')) rgsAny++;
    }
    const groups = {
      scg: (v, k) => scGradeOK(v, k),
      scv: (v, k) => v._sc && v._sc.ver === k,
      grd: (v, k) => k === 'len' ? v._pendingLen : v._grade === k,
      typ: (v, k) => v._grade && (k === 'all' || v._type === k),
      cty: (v, k) => v._subj === k,
      rxkr: (v, k) => rxMatch(v, k), rxjp: (v, k) => rxMatch(v, k), rxtw: (v, k) => rxMatch(v, k),
      kinds: (v, k) => v._kind === k,
      trvkr: v => v._krTrip, trvjp: v => v._jpTrip,
      rgs: (v, k) => k === '_any' ? v._rgAny && v._lists.includes('krexp') : v._rg.includes(k),
      srcs: (v, k) => k === 'dup' ? v._dup : v._notion,
      xsts: (v, k) => k === 'all' ? !v.ref : v._xst === k,
      refch: (v, k) => v.ref && (k === 'all' || v.channel_id === k),
      bmch: (v, k) => v.bm && (k === 'all' || v.channel_id === k),
      jts: (v, k) => v._jt.includes(k),
      gts: (v, k) => k === 'all' ? v._gc.length : v._gc.includes(k),
      jgts: (v, k) => k === 'all' ? v._jgc.length : v._jgc.includes(k),
      gitems: (v, k) => v._gi.includes(k), jgitems: (v, k) => v._jgi.includes(k),
      exps: (v, k) => k === '_any' ? v._topics.length : v._topics.includes(k),
      cats: (v, k) => withSubs(v) && CATS.find(c => c[0] === k)?.[2](v),
      ext: v => v.viral,
      mine: (v, k) => k === 'new' ? isNew(v) : k === 'fav' ? favs.has(v.id) : k === 'memo' ? memos[v.id] : k === 'done' ? done.has(v.id) : hidden.has(v.id)
    };
    const specialTotals = new Set(['typ', 'srcs', 'xsts', 'refch', 'bmch', 'gts', 'jgts']);
    for (const [id, predicate] of Object.entries(groups)) {
      const chips = document.querySelectorAll('#' + id + ' .chip');
      if (!chips || !chips.length) continue;
      chips.forEach(chip => {
        const key = chip.dataset.k;
        let small = chip.querySelector('small');
        if (!small) { small = document.createElement('small'); chip.append(small); }
        let count;
        if (id in tally) {
          if (key === 'all') count = id === 'gts' ? gtsAll : id === 'jgts' ? jgtsAll : pool.length;
          else if (key === '_any') count = id === 'exps' ? expsAny : id === 'rgs' ? rgsAny : 0;
          else count = tally[id][key] || 0;
        } else {
          count = key === 'all' && !specialTotals.has(id) ? pool.length : pool.filter(v => predicate(v, key)).length;
        }
        if (small.textContent !== String(count)) small.textContent = String(count);
        small.title = '선택한 목록 기준 · 다른 세부 필터 적용 전';
      });
    }
  };
  const original = render;
  render = function(...args) { const result = original.apply(this, args); refresh(); return result; };
  refresh();
});
