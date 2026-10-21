// 화면 담당 파일을 건드리지 않고 선택 목록 기준 숫자를 갱신한다.
// score_alerts.py export가 auto_scores.js에 함께 내보낸다.
document.addEventListener('DOMContentLoaded', () => {
  const refresh = () => {
    const pool = [...new Map(V.filter(inList).map(v => [v.id, v])).values()];
    const groups = {
      scg: (v, k) => scGradeOK(v, k),
      scv: (v, k) => v._sc && v._sc.ver === k,
      grd: (v, k) => k === 'len' ? v._pendingLen : v._grade === k,
      typ: (v, k) => v._grade && (k === 'all' || v._type === k),
      cty: (v, k) => v._subj === k,
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
      document.querySelectorAll('#' + id + ' .chip').forEach(chip => {
        const key = chip.dataset.k;
        let small = chip.querySelector('small');
        if (!small) { small = document.createElement('small'); chip.append(small); }
        const count = key === 'all' && !specialTotals.has(id) ? pool.length : pool.filter(v => predicate(v, key)).length;
        if (small.textContent !== String(count)) small.textContent = String(count);
        small.title = '선택한 목록 기준 · 다른 세부 필터 적용 전';
      });
    }
  };
  // 모든 기존 클릭/초기화/분류 보정 경로가 render를 사용한다.
  const original = render;
  render = function(...args) { const result = original.apply(this, args); refresh(); return result; };
  refresh();
});
