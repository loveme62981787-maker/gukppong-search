window.AUTO_SCORES={"items": [{"id": "-uwvmDapKq4", "ver": "jp", "t": "Travelling South Japan In A Micro Camper-Van - Full Journey from Hiroshima To Fukuoka", "source": "claude_fm", "fm_sha256": "f124fa5a3f08e626c2225890f152f001bb70814afb946722acc2ce43c5762a26", "transcript_sha256": "a347ce500a1583a55f7a6d6649693cbda5d485a3e3eec2d2f1895fb0cbb2d3bb", "checked_at": "2026-10-21T14:08:39.736893+00:00", "min": 29.78, "p": 7.0, "s": [15, 14, 12, 13, 7, 9], "warn": ["Claude FM 채점. 자막 전문과 한국판·일본판 FM을 사용했습니다. 자동 생성·번역 자막 오류 가능성이 있으며 영상 화면은 검증하지 않았습니다. 원문 근거는 공개하지 않습니다."]}, {"id": "67IRq5gUPLw", "ver": "kr", "t": "Mi amiga española se casa en Corea en el PALACIO GYEONGBOKGUNG 🇰🇷💍🇪🇸", "source": "gemini_fm", "fm_sha256": "914b35b93e2306592c1d1a561865711532cfbe36abe3752d579160aa1f1a5ad1", "transcript_sha256": "0ac5de9f3f501913aae966bbb8c8bbeb652511f947899d9991cebea5ea8aa6ee", "checked_at": "2026-10-21T15:29:07.425543+00:00", "min": 10.8, "p": 3.0, "s": [13, 11, 10, 13, 7, 7], "warn": ["Gemini 1차 채점 · Codex 검증. 자막 전문과 한국판·일본판 FM을 사용했습니다. 자동 생성·번역 자막 오류 가능성이 있으며 영상 화면은 검증하지 않았습니다. 원문 근거는 공개하지 않습니다."]}]};

// 수동 채점은 같은 영상의 자동 채점보다 우선한다. 화면 담당 파일과 분리한다.
(() => {
  const manual = window.SCORES || {items: []};
  const rows = Array.isArray(manual.items) ? manual.items : [];
  const ids = new Set(rows.map(x => x.id));
  window.SCORES = {...manual, items: [...window.AUTO_SCORES.items.filter(x => !ids.has(x.id)), ...rows]};
  document.addEventListener('DOMContentLoaded', () => {
    for (const [key, label] of [['alert_kr', '🔔 텔레그램 (한국)'], ['alert_jp', '🔔 텔레그램 (일본)']]) {
      const chip = document.querySelector('#lists [data-k="' + key + '"]');
      if (chip && chip.firstChild && chip.firstChild.nodeType === 3) chip.firstChild.textContent = label;
    }
  });
})();
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
