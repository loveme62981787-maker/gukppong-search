import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// web/index.html 에서 라이선스 탭 로직만 잘라 실행한다 (단일 정적 파일 유지)
const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const block = html.slice(html.indexOf('// <license-view>'), html.indexOf('// </license-view>'));

const LIC = {
  items: {
    cc0000000001: {l: 'cc_by', c: '2026-10-30'},
    cc0000000002: {l: 'cc_by', c: '2026-10-01', e: 'blocked', s: 1},          // 재확인 실패: 지난 확인 기준
    fr0000000001: {l: 'standard', f: 'en_video', c: '2026-10-30'},             // 표준 + 무료 사용 문구
    st0000000001: {l: 'standard', c: '2026-10-30'},                             // 표준 확인, 허용 문구 없음 → 어느 탭에도 없음
    uk0000000001: {l: 'unknown', u: 'no_marker', c: '2026-10-30'},
    uk0000000002: {l: 'unknown', u: 'never_verified', e: 'network'},            // 확인 실패
    constructor: {l: 'cc_by'},
  },
};
const VIDEOS = [
  {id: 'cc0000000001', _form: 'long', _subj: '한국', _lists: ['krexp']},
  {id: 'cc0000000002', _form: 'short', _subj: '일본', _lists: ['jpexp']},
  {id: 'fr0000000001', _form: 'long', _subj: '한국', _lists: ['krexp', 'notion']},   // 여러 목록에 속해도 한 번
  {id: 'st0000000001', _form: 'long', _subj: '한국', _lists: ['krexp']},
  {id: 'uk0000000001', _form: 'long', _subj: '일본', _lists: ['jpexp']},
  {id: 'uk0000000002', _form: 'unk', _subj: '한국', _lists: ['krexp']},
  {id: 'nr0000000001', _form: 'long', _subj: '한국', _lists: ['krexp']},             // 기록 없음 = 확인 전
];

function make(extra = '') {
  const ctx = vm.createContext({window: {VIDEO_LICENSES: LIC}});
  vm.runInContext(`const V = ${JSON.stringify(VIDEOS)};` + block + `
    const viewSel = new Set(), hidden = new Set(), done = new Set();
    // index.html 의 pass() 와 같은 순서: 숨김·사용 완료 → 목록 → 나라 → 길이 → 라이선스
    function shown({list, ctry, len} = {}) {
      return V.filter(v => !hidden.has(v.id) && !done.has(v.id) && (!list || v._lists.includes(list)) && (!ctry || v._subj === ctry)
        && (!len || (len === 'default' ? v._form !== 'short' : v._form === len)) && licPass(v.id, viewSel)).map(v => v.id);
    }` + extra, ctx);
  return ctx;
}
const run = (ctx, s) => { const r = vm.runInContext(s, ctx); return Array.isArray(r) ? [...r] : r; };   // 다른 realm 의 배열을 deepEqual 로 비교할 수 있게 복사

test('CC BY / 무료 사용 / 미확인 탭 분류: 표준+허용 문구 없음은 어느 탭에도 없다', () => {
  const c = make();
  assert.equal(run(c, 'licCount("lic_cc")'), 2);
  assert.equal(run(c, 'licCount("lic_free")'), 1);
  assert.equal(run(c, 'licCount("lic_unk")'), 3);   // 표기 없음 + 확인 실패 + 확인 전
  assert.equal(run(c, 'LIC_KEYS.some(k => licMatch(licRec("st0000000001"), k))'), false);
  assert.equal(run(c, 'LIC_KEYS.some(k => licMatch(licRec("fr0000000001"), k))'), true);   // 표준이어도 허용 문구가 있으면 무료 사용 탭
  assert.equal(run(c, '[licUnkWhy(licRec("nr0000000001")), licUnkWhy(licRec("uk0000000002")), licUnkWhy(licRec("uk0000000001")), licUnkWhy(licRec("cc0000000001"))].join()'), 'unchecked,failed,no_marker,');
  assert.equal(run(c, 'licRec("constructor") && licRec("toString")'), null);   // 프로토타입 이름으로 조회되지 않는다
});

test('목록·나라·길이 필터와 함께 동작하고 개수가 맞는다', () => {
  const c = make();
  run(c, 'viewSel.add("lic_cc")');
  assert.deepEqual(run(c, 'shown()'), ['cc0000000001', 'cc0000000002']);
  assert.deepEqual(run(c, 'shown({len: "default"})'), ['cc0000000001']);          // 숏폼 제외 기본 길이
  assert.deepEqual(run(c, 'shown({ctry: "일본"})'), ['cc0000000002']);
  assert.deepEqual(run(c, 'shown({list: "jpexp", len: "short"})'), ['cc0000000002']);
  run(c, 'viewSel.add("lic_free")');   // 탭을 함께 고르면 합집합
  assert.deepEqual(run(c, 'shown()'), ['cc0000000001', 'cc0000000002', 'fr0000000001']);
  assert.equal(run(c, 'shown({list: "notion"}).length'), 1);   // 여러 목록에 속한 영상도 한 번만
  run(c, 'viewSel.clear(); viewSel.add("lic_unk")');
  assert.deepEqual(run(c, 'shown({ctry: "한국", len: "unk"})'), ['uk0000000002']);
});

test('숨김·사용 완료 상태는 탭과 원래 목록이 같은 영상 ID 로 공유하고, 필터 초기화는 상태를 지우지 않는다', () => {
  const c = make();
  run(c, 'hidden.add("cc0000000001"); done.add("fr0000000001"); viewSel.add("lic_cc"); viewSel.add("lic_free")');
  assert.deepEqual(run(c, 'shown()'), ['cc0000000002']);                        // 탭에서도 숨김·사용 완료 영상은 빠진다
  assert.equal(run(c, 'shown().includes("cc0000000001")'), false);
  assert.equal(run(c, 'V.filter(v => v.id === "cc0000000001").length'), 1);     // 같은 ID 가 따로 복제되지 않는다
  run(c, 'LIC_KEYS.forEach(k => viewSel.delete(k))');                             // 전체 초기화(clearFilters)와 같은 동작
  assert.equal(run(c, 'shown({list: "krexp"}).includes("cc0000000001")'), false);  // 숨김 데이터는 그대로
  assert.equal(run(c, 'hidden.has("cc0000000001") && done.has("fr0000000001")'), true);
  assert.equal(run(c, 'shown().length'), 5);                                      // 라이선스 조건만 풀렸다
});

test('카드 안내는 고정 문구이고 지난 확인 기준·미확인 사유를 구분해 보인다', () => {
  const c = make();
  const notes = s => run(c, `JSON.stringify(licNotes(licRec("${s[0]}"), ${s[1]}))`);
  assert.match(notes(['cc0000000002', false]), /CC BY.*2026-10-01 확인.*지난 확인 기준/);
  assert.match(notes(['fr0000000001', false]), /무료 사용 허용 문구.*원문은 공개하지 않아요/);
  assert.equal(notes(['st0000000001', true]), '[]');
  assert.equal(notes(['uk0000000001', false]), '[]');                                // 미확인 탭을 안 골랐으면 안내를 늘리지 않는다
  assert.match(notes(['uk0000000002', true]), /확인 실패/);
  assert.match(notes(['nr0000000001', true]), /확인 전/);
  assert.match(notes(['uk0000000001', true]), /CC 표기 없음\(표준으로 단정하지 않음\)/);
});

// ---- 실제 연결(index.html 의 <license-tabs> 블록)을 가짜 DOM 위에서 그대로 실행한다 ----
const wiring = html.slice(html.indexOf('// <license-tabs>'), html.indexOf('// </license-tabs>'));
class El {
  constructor(id) { this.id = id; this.dataset = {}; this.kids = []; this.parentNode = null; this.hidden = false; this.title = ''; this.textContent = ''; this.cls = new Set();
    this.classList = {add: c => this.cls.add(c), remove: c => this.cls.delete(c), contains: c => this.cls.has(c), toggle: (c, f) => ((f === undefined ? !this.cls.has(c) : f) ? this.cls.add(c) : this.cls.delete(c))}; }
  set className(v) { this.cls = new Set(v.split(' ').filter(Boolean)); }
  append(x) { if (x instanceof El) { x.parentNode = this; this.kids.push(x); } }
  after(...els) { const p = this.parentNode, i = p.kids.indexOf(this); els.forEach(e => e.parentNode = p); p.kids.splice(i + 1, 0, ...els); }
  querySelector(sel) { return this.kids.find(k => k.tag === sel); }
}
function harness() {
  const els = {}, bar = new El('bar'), out = {}, ids = ['mv', 'mc', 'ms', 'mmy', 'hidden-videos-tab', 'licnote'];
  ids.forEach(i => { els[i] = new El(i); if (i !== 'licnote') { els[i].parentNode = bar; bar.kids.push(els[i]); } });
  els.mv.cls.add('on');
  const vmode = new El('vmode');
  let ready;
  const document = {getElementById: i => els[i], querySelector: s => s === '.vmode' ? vmode : null, createElement: tag => { const e = new El(); e.tag = tag; return e; },
    addEventListener: (ev, fn) => { if (ev === 'DOMContentLoaded') ready = fn; }};
  const ctx = vm.createContext({window: {VIDEO_LICENSES: LIC}, document, out, els, vmode, bar, console});
  vm.runInContext(`const V = ${JSON.stringify(VIDEOS)}; ${block}
    const viewSel = new Set(), hidden = new Set(), done = new Set(), listSel = new Set(), MULTIS = [];
    const inList = v => !listSel.size || v._lists.some(k => listSel.has(k));
    let modeNow = 'v', shownLog = [];
    // 기존 setMode/render 와 같은 역할의 기본 구현 (index.html 의 pass 순서: 숨김·사용 완료 → 목록 → 라이선스)
    function setMode(m) { modeNow = m === true ? 'c' : m === false || m === 'v' ? 'v' : String(m); vmode.hidden = modeNow !== 'v'; els.mv.classList.toggle('on', modeNow === 'v'); if (modeNow === 'v') render({keep: true}); }
    function render() { shownLog.push(V.filter(v => !hidden.has(v.id) && !done.has(v.id) && inList(v) && licPass(v.id, viewSel)).map(v => v.id)); }
    ${wiring}`, ctx);
  ready();
  const run = s => { const r = vm.runInContext(s, ctx); return Array.isArray(r) ? [...r] : r; };
  const tabs = () => bar.kids.filter(k => k.cls.has('lictab'));
  return {run, els, bar, vmode, tabs, click: k => tabs().find(b => b.dataset.k === k).onclick(), counts: () => tabs().map(b => b.kids[0].textContent).join(','), last: () => run('shownLog[shownLog.length - 1]')};
}

test('실제 연결: 탭 3개가 🙈 숨긴 영상 탭 바로 뒤에 들어가고 개수는 선택한 목록 기준이다', () => {
  const h = harness();
  assert.deepEqual(h.bar.kids.map(k => k.id || k.dataset.k), ['mv', 'mc', 'ms', 'mmy', 'hidden-videos-tab', 'lic_cc', 'lic_free', 'lic_unk']);
  assert.equal(h.counts(), '2,1,3');
  h.run('listSel.add("jpexp"); render()');
  assert.equal(h.counts(), '1,0,1');   // 일본 체험 목록 안에서만 센다 (CC BY 1개, 미확인 1개)
  assert.match(h.els.licnote.textContent, /이 목록 2개 중/);
});

test('실제 연결: 탭 선택은 영상 화면의 필터이고 한 번에 하나이며 같은 영상 ID 상태를 공유한다', () => {
  const h = harness();
  h.click('lic_cc');
  assert.deepEqual(h.last(), ['cc0000000001', 'cc0000000002']);
  assert.equal(h.els.mv.classList.contains('on'), false);   // 라이선스 탭을 고른 동안 '🎬 영상'은 꺼진다
  assert.equal(h.tabs()[0].classList.contains('on'), true);
  h.click('lic_free');   // 다른 탭을 누르면 교체
  assert.deepEqual(h.last(), ['fr0000000001']);
  assert.equal(h.run('[...viewSel].join()'), 'lic_free');
  h.run('hidden.add("fr0000000001")'); h.run('render()');
  assert.deepEqual(h.last(), []);   // 숨김은 탭에서도 적용 (같은 ID 상태 공유)
  h.run('hidden.clear(); listSel.add("jpexp")'); h.click('lic_cc');
  assert.deepEqual(h.last(), ['cc0000000002']);   // 목록 필터와 함께
  h.click('lic_cc');   // 같은 탭을 다시 누르면 해제되고 영상이 켜진다
  assert.equal(h.run('viewSel.size'), 0);
  assert.equal(h.els.mv.classList.contains('on'), true);
  assert.equal(h.last().length, 2);
});

test('실제 연결: 숨긴 영상·채널·채점·내 채점·영상 화면으로 옮기면 라이선스 선택이 풀리고 강조가 맞는다', () => {
  for (const m of ['hidden-videos', 'my', 's', true, false]) {
    const h = harness();
    h.click('lic_unk');
    assert.equal(h.run('viewSel.has("lic_unk")'), true);
    h.run(`setMode(${JSON.stringify(m)})`);
    assert.equal(h.run('viewSel.size'), 0, String(m));
    assert.equal(h.tabs().some(b => b.classList.contains('on')), false, String(m));
    assert.equal(h.els.mv.classList.contains('on'), m === false, String(m));
    if (m === false) assert.equal(h.last().length, 7);   // 영상 화면은 필터 없이 다시 그려진다
  }
  const h = harness();   // 다른 화면에서 탭을 누르면 영상 화면으로 돌아와 적용
  h.run('setMode("hidden-videos")'); assert.equal(h.vmode.hidden, true);
  h.click('lic_cc');
  assert.equal(h.vmode.hidden, false); assert.equal(h.run('modeNow'), 'v'); assert.deepEqual(h.last(), ['cc0000000001', 'cc0000000002']);
});

test('실제 연결: 전체 초기화는 탭만 풀고 숨김 데이터는 그대로 둔다', () => {
  const h = harness();
  h.run('hidden.add("cc0000000001")'); h.click('lic_cc');
  assert.deepEqual(h.last(), ['cc0000000002']);
  h.run('MULTIS.forEach(m => { m.keys.forEach(k => m.sel.delete(k)); m.sync(); }); render()');   // index.html clearFilters 와 같은 동작
  assert.equal(h.tabs().some(b => b.classList.contains('on')), false);
  assert.equal(h.els.mv.classList.contains('on'), true);
  assert.equal(h.last().includes('cc0000000001'), false);
  assert.equal(h.run('hidden.has("cc0000000001")'), true);
});

test('index.html 배선: 로드 실패 대체값, 필터·카드 연결, 아래쪽 중복 줄 없음', () => {
  assert.match(html, /<script src="video_licenses\.js" onerror="window\.VIDEO_LICENSES=\{schema:1,items:\{\}\}"><\/script>/);
  assert.match(html, /licPass\(v\.id, viewSel\)/);
  assert.doesNotMatch(html, /id="licrow"|id="lic"/);   // 목록·패널 아래 별도 줄 없음
  assert.doesNotMatch(html, /innerHTML[^\n]*licNotes/);   // 안내 문구는 DOM 텍스트로만 넣는다
});
