import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const src = fs.readFileSync(new URL('../web/hot_shorts_view.js', import.meta.url), 'utf8');
const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const dataSrc = fs.readFileSync(new URL('../web/hot_shorts.js', import.meta.url), 'utf8');

// 아주 작은 가짜 DOM: innerHTML 대입은 곧바로 실패시켜서 '데이터를 HTML 로 넣는 코드'가 생기면 테스트가 깨지게 한다
class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.className = ''; this._text = ''; this.attrs = {}; this.classList = {toggle: () => {}}; }
  set innerHTML(v) { throw new Error('innerHTML 사용 금지: ' + String(v).slice(0, 40)); }
  get textContent() { return this._text + this.children.map(c => c.textContent ?? String(c)).join(''); }
  set textContent(v) { this._text = String(v); this.children = []; }
  append(...xs) { this.children.push(...xs); }
  focus() {}
  addEventListener() {}
  walk(fn) { fn(this); this.children.forEach(c => c instanceof Node && c.walk(fn)); }
}
function boot(extra = {}) {
  const els = {};
  const document = {
    createElement: tag => new Node(tag),
    getElementById: id => els[id] ??= Object.assign(new Node('div'), {value: ''}),
    addEventListener() {},
  };
  els.hsq = Object.assign(new Node('input'), {value: ''}); els.hssort = Object.assign(new Node('select'), {value: 'views'});
  els.hskind = Object.assign(new Node('select'), {value: ''}); els.hsmine = Object.assign(new Node('select'), {value: ''});
  const ctx = vm.createContext({document, console, ...extra});
  ctx.window = ctx;
  const saved = [];
  vm.runInContext('const favs = new Set(), done = new Set(), hidden = new Set(), memos = {}; var __saved = 0; function saveAll() { __saved++; }', ctx);
  vm.runInContext(dataSrc, ctx);
  vm.runInContext(src, ctx);
  return {ctx, els, document, saved};
}
const D = (() => { const c = vm.createContext({}); c.window = c; vm.runInContext(dataSrc, c); return c.HOT_SHORTS; })();
const sets = ctx => vm.runInContext('({favs, done, hidden, memos})', ctx);

const ch = (o = {}) => Object.assign({id: 'UC' + 'a'.repeat(22), title: '채널', handle: '@c', country: 'TW', kind: 'reaction_edit', subs: 1000, sample_n: 20, sample_shorts: 16, shorts_ratio: 0.8, shorts_centered: false, all_shorts_strict: false, sample_pending: 0, hot_n: 1, checked: '2026-11-16'}, o);
const vd = (o = {}) => Object.assign({id: 'AAAAAAAAAAA', title: '영상', channel_id: 'UC' + 'a'.repeat(22), country: 'TW', views: 200000, sub_multiple: 5, median_multiple: 2.5, published: '2026-11-01', checked: '2026-11-16', short: true, short_signal: 'shorts_tab'}, o);

test('기준 문구는 내보낸 criteria 값에서 만들어진다 (코드 상수와 일치)', () => {
  const {ctx} = boot();
  const V = ctx.HotShortsView, c = D.criteria;
  const t = V.criteriaText(c);
  assert.ok(t.includes(c.min_views.toLocaleString('ko-KR')));
  assert.ok(t.includes('구독자 수와 무관'));   // 구독자·중앙값 배수는 입장 조건이 아니라 표시·정렬 보조
  assert.ok(!/구독자 대비 [0-9.]+배 이상/.test(t));
  assert.ok(t.includes(`최근 업로드 ${c.fetch_n}개`));
  assert.ok(t.includes(`최근 업로드 ${c.sample_n}개`));
  assert.ok(t.includes(`${Math.round(c.center_ratio * 100)}%`));
  assert.match(t, /최근 표본 기준/);
  assert.match(t, /이어받고/);
  assert.match(t, /제목에 외국인 신호와 대상국 이름이 함께/);
  assert.match(t, /3분 이하\)만으로는 쇼츠로 확정하지 않고/);
  const other = V.criteriaText({...c, min_views: 777000, sample_n: 33});
  assert.ok(other.includes('777,000') && other.includes('33개'));
});

test('JP·TW 채널명은 한국어 병기명이 있으면 함께 보여준다', () => {
  const {ctx} = boot();
  const V = ctx.HotShortsView;
  assert.equal(V.chName(ch({title: '外國人看台灣', name_ko: '외국인이 본 대만'})), '外國人看台灣 (외국인이 본 대만)');
  assert.equal(V.chName(ch({title: '코리아', name_ko: ''})), '코리아');
  assert.equal(V.chName(ch({title: '같은', name_ko: '같은'})), '같은');
});

test('나라별로 60개씩만 그리고 더 보기로 늘린다 (수집 한도 아님)', () => {
  const src2 = fs.readFileSync(new URL('../web/hot_shorts_view.js', import.meta.url), 'utf8');
  assert.match(src2, /PAGE = 60/);
  assert.match(src2, /더 보기/);
});

test('배지: 쇼츠 중심과 엄격한 전부 쇼츠는 별개이고 영구 단정 문구가 없다', () => {
  const {ctx} = boot();
  const lab = c => ctx.HotShortsView.channelBadges(c).map(b => b[0]).join('|');
  assert.match(lab(ch({shorts_centered: true})), /쇼츠 중심 \(최근 표본 기준\)/);
  assert.doesNotMatch(lab(ch({shorts_centered: true})), /전부 쇼츠/);
  assert.match(lab(ch({shorts_centered: true, all_shorts_strict: true})), /표본 전부 쇼츠 \(엄격\)/);
  assert.match(lab(ch()), /혼합 또는 표본 부족/);
  assert.doesNotMatch(lab(ch({shorts_centered: true, all_shorts_strict: true})), /영원|항상|계속 쇼츠|쇼츠 전용 채널/);
});

test('편집 채널과 미확인 채널은 재사용 가능한 원본으로 표시되지 않는다', () => {
  const {ctx} = boot();
  const K = ctx.HotShortsView.KIND_BADGE;
  assert.match(K.reaction_edit[0], /재사용 가능한 원본 아님/);
  assert.match(K.unverified[0], /재사용 가능한 원본으로 보지 않아요/);
  assert.doesNotMatch(K.travel_original[0], /재사용 가능한 원본입니다|CC BY/);
  assert.match(K.travel_original[0], /영상별로 따로 확인/);
  for (const c of D.channels) assert.ok(K[c.kind], c.kind);   // 데이터의 모든 종류가 표시 문구를 가진다
});

test('독립 보기: 길이 필드와 무관하게 쇼츠가 나오고, 숨김·사용 완료는 같은 집합을 따른다', () => {
  const {ctx} = boot();
  const F = ctx.HotShortsView.filterVideos;
  const chById = {['UC' + 'a'.repeat(22)]: ch()};
  const vids = [vd({id: 'AAAAAAAAAAA', duration_sec: 30}), vd({id: 'BBBBBBBBBBB'}), vd({id: 'CCCCCCCCCCC', duration_sec: undefined}), vd({id: 'DDDDDDDDDDD'})];
  const st = {favs: new Set(['CCCCCCCCCCC']), done: new Set(['BBBBBBBBBBB']), hidden: new Set(['DDDDDDDDDDD']), memos: {AAAAAAAAAAA: '메모 텍스트'}};
  const ids = o => F(vids, chById, {state: st, ...o}).map(v => v.id);
  assert.deepEqual(ids({}), ['AAAAAAAAAAA', 'CCCCCCCCCCC']);            // 기본: 사용 완료·숨김 제외 (180초 이하 영상도 그대로)
  assert.deepEqual(ids({mine: 'done'}), ['BBBBBBBBBBB']);
  assert.deepEqual(ids({mine: 'hidden'}), ['DDDDDDDDDDD']);
  assert.deepEqual(ids({mine: 'fav'}), ['CCCCCCCCCCC']);
  assert.deepEqual(ids({mine: 'memo'}), ['AAAAAAAAAAA']);
  assert.deepEqual(ids({q: '메모 텍스트'}), ['AAAAAAAAAAA']);
  assert.deepEqual(ids({country: 'KR'}), []);
  assert.deepEqual(ids({kind: 'unverified'}), []);
  assert.ok(!/lenmode|LONG_MIN_SEC|duration_sec/.test(src.replace(/\/\/.*$/gm, '')), '길이 필터를 쓰지 않는다');
});

test('잘못된 영상 ID 는 목록에서 빠지고 링크로 만들어지지 않는다', () => {
  const {ctx} = boot();
  const V = ctx.HotShortsView;
  const st = {favs: new Set(), done: new Set(), hidden: new Set(), memos: {}};
  const bad = [vd({id: 'x"><script>alert(1)</script>'}), vd({id: 'short'}), vd({id: 'AAAAAAAAAAA'})];
  assert.equal(V.filterVideos(bad, {}, {state: st}).length, 1);
  assert.equal(V.safeChannelId('UC' + 'a'.repeat(22)), 'UC' + 'a'.repeat(22));
  assert.equal(V.safeChannelId('javascript:alert(1)'), null);
  assert.equal(V.safeVideoId('../../evil'), null);
});

test('XSS: 제목·채널명·메모는 textContent 로만 들어가고 innerHTML 은 쓰지 않는다', () => {
  const {ctx} = boot();
  const V = ctx.HotShortsView, evil = '<img src=x onerror=alert(1)>"\'</script>';
  const st = {favs: new Set(), done: new Set(), hidden: new Set(), memos: {AAAAAAAAAAA: evil}};
  const c = ch({title: evil, handle: evil, note: evil});
  const card = V.videoCard(vd({title: evil}), c, st, () => {});
  const ccard = V.channelCard(c);
  let titles = 0;
  for (const root of [card, ccard]) root.walk(n => {
    if (n.tag === 'a' && n.href) assert.match(n.href, /^https:\/\/(www\.youtube\.com|i\.ytimg\.com)\//);
    if (n.tag === 'img') assert.match(n.src, /^https:\/\/i\.ytimg\.com\/vi\/[A-Za-z0-9_-]{11}\//);
    if (n.textContent.includes('onerror=alert')) titles++;
    if (n.tag === 'a') assert.equal(n.rel, 'noopener noreferrer');
  });
  assert.ok(titles > 0);   // 문자열 그대로 '글자'로 보인다 (태그로 해석되지 않음)
  assert.ok(!/\.innerHTML\s*=|insertAdjacentHTML|outerHTML|document\.write/.test(src), '데이터를 HTML 로 넣는 코드 없음');
  assert.ok(!/\beval\(|new Function/.test(src));
});

test('저장·사용 완료·숨김·메모 버튼은 영상 화면과 같은 집합에 쓰고 saveAll 로 저장한다', () => {
  const {ctx} = boot();
  const V = ctx.HotShortsView, S = sets(ctx);
  let changes = 0;
  const card = V.videoCard(vd(), ch(), S, () => { changes++; ctx.saveAll(); });
  const btns = {}; card.walk(n => { if (n.tag === 'button') btns[n.className.split(' ')[0] + ':' + (n.className.split(' ')[1] || '')] = n; });
  const find = cls => { let r; card.walk(n => { if (n.tag === 'button' && n.className.split(' ').includes(cls)) r = n; }); return r; };
  find('fav').onclick(); find('ok').onclick(); find('hd').onclick();
  assert.ok(S.favs.has('AAAAAAAAAAA') && S.done.has('AAAAAAAAAAA') && S.hidden.has('AAAAAAAAAAA'));
  find('hd').onclick();
  assert.ok(!S.hidden.has('AAAAAAAAAAA'));
  let ta; card.walk(n => { if (n.tag === 'textarea') ta = n; });
  ta.value = '내 메모'; ta.oninput();
  assert.equal(S.memos.AAAAAAAAAAA, '내 메모');
  assert.ok(changes >= 4 && vm.runInContext('__saved', ctx) >= 4);
});

test('실제 데이터로 화면이 3개 국가 제목과 채널·영상 카드를 만든다', () => {
  const {ctx, els} = boot();
  ctx.renderHotShorts();
  const body = els.hsbody;
  const h2 = []; let cards = 0;
  body.walk(n => { if (n.tag === 'h2') h2.push(n.textContent); if (n.className.startsWith('card')) cards++; });
  assert.deepEqual(h2, ['🔥 터진 쇼츠 (한국)', '🔥 터진 쇼츠 (일본)', '🔥 터진 쇼츠 (대만)']);
  assert.ok(cards >= D.channels.length);
  const text = body.textContent;
  assert.ok(text.includes('@lianxinfanyin'));
  assert.match(text, /구독자 대비/); assert.match(text, /표본 중앙값 대비/); assert.match(text, /확인 20\d\d-\d\d-\d\d/); assert.match(text, /쇼츠 표본 \d+\/\d+/);
  assert.match(els.hscty.textContent, /터진 쇼츠 \(한국\)/); assert.match(els.hscty.textContent, /터진 쇼츠 \(일본\)/); assert.match(els.hscty.textContent, /터진 쇼츠 \(대만\)/);
});

test('index.html 연결: 버튼·독립 뷰·모드 전환·스크립트 순서', () => {
  assert.doesNotMatch(html, /id="mhs"/, '상단 탭이 아니라 목록 줄 버튼');
  const li = html.indexOf('id="lists"'), bi = html.indexOf('[["KR", "🔥 터진 쇼츠 (한국)"], ["JP", "🔥 터진 쇼츠 (일본)"], ["TW", "🔥 터진 쇼츠 (대만)"]]');
  assert.ok(li > -1 && bi > li, '세 버튼은 #lists 줄에 붙는다');
  assert.ok(html.indexOf('["hold", "🗂 분류 보류"]') < bi, '분류 보류 바로 오른쪽');
  assert.match(html, /id="listrow"/); assert.doesNotMatch(html, /class="[^"]*vmode[^"]*" id="listrow"/);
  assert.ok(html.includes('.chip:not([data-hs])'), '기존 목록 칩 개수·선택 로직이 새 버튼을 건드리지 않는다');
  assert.match(html, /<div id="hsview" hidden>/);
  assert.ok(html.indexOf('<div id="hsview"') > -1 && !/<div id="hsview"[^>]*class="[^"]*vmode/.test(html), '롱폼 영상 화면(.vmode)과 별개');
  assert.match(html, /document\.getElementById\("hsview"\)\.hidden = mode !== "hs"/);
  assert.match(html, /m === "hs" \? m : "v"/);
  assert.ok(html.indexOf('<script src="hot_shorts.js') > -1 && html.indexOf('<script src="hot_shorts.js') < html.indexOf('const V = (window.VIDEOS'), '데이터가 메인 스크립트보다 먼저');
  assert.ok(html.lastIndexOf('hot_shorts_view.js') > html.lastIndexOf('render(); ls.set("lastVisit"'), '뷰 스크립트는 메인 스크립트(favs 등 정의) 뒤에');
});

test('배지: 16/20 채널은 쇼츠 중심 기준 미충족을 정확히 표시하고 사용자 지정 참고 채널로 포함된다', () => {
  const {ctx} = boot();
  const labs = ctx.HotShortsView.channelBadges(ch({user_reference: true}), 0.9).map(b => b[0]).join('|');
  assert.match(labs, /쇼츠 중심 기준 미충족 \(20개 중 16개 확인, 80%\)/);
  assert.doesNotMatch(labs, /전부 쇼츠|🎯 쇼츠 중심/);
  assert.match(labs, /사용자 지정 참고 채널/);
  const lx = D.channels.find(c => c.id === 'UC0MUbD8ISz4koLlo0LfgNng');
  assert.equal(lx.country, 'TW'); assert.equal(lx.sample_shorts, 16); assert.equal(lx.user_reference, true);
});

test('터진 쇼츠 화면: 국가 선택은 setCountry 로 하고 대만 화면에 예시 채널이 보인다', () => {
  const {ctx, els} = boot();
  ctx.HotShortsView.setCountry('TW');
  ctx.renderHotShorts();
  const h2 = []; els.hsbody.walk(n => { if (n.tag === 'h2') h2.push(n.textContent); });
  assert.deepEqual(h2, ['🔥 터진 쇼츠 (대만)']);
  assert.match(els.hsbody.textContent, /@lianxinfanyin/);
  assert.match(els.hsbody.textContent, /쇼츠 중심 기준 미충족/);
});
