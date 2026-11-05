import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const block = html.slice(html.indexOf('// <kr-regional>'), html.indexOf('// </kr-regional>'));
const ctx = vm.createContext({});
vm.runInContext('const hasKana = s => /[぀-ヿ]/.test(s);\n' + block + '\nthis.kind = krRegionalKind; this.subj = krRegionalSubject;', ctx);
const KR = /서울|부산|제주/, JP = /도쿄|후쿠오카|오사카/, TW = /타이베이|단수이|대만/;
const v = (o) => Object.assign({id: 'a', title: '후쿠오카 여행 브이로그', kr_regional: true, kr_country: '일본', kr_region: '후쿠오카', kr_words: ['여행', '브이로그'], kr_hashtag: true, _subj: '일본'}, o);

test('수집 근거가 있는 일본 한국어 제목 여행은 현지 편집(local)이 아니라 원본(foreign)으로 본다', () => {
  const k = ctx.kind(v());
  assert.equal(k[0], 'foreign');
  assert.match(k[1], /국적.*확인하지 않음/);
});
test('근거가 없거나 소재가 어긋나면 교정하지 않는다 (기존 판정 유지)', () => {
  assert.equal(ctx.kind(v({kr_regional: undefined})), null);
  assert.equal(ctx.kind(v({_subj: '한국'})), null);
  assert.equal(ctx.kind(v({title: 'ふくおか 旅行 후쿠오카'})), null);
  assert.equal(ctx.kind(v({title: 'Fukuoka vlog'})), null);
});
test('소재: 단수이 같은 지역도 수집 근거로 대만 소재, 한국 지명 혼합은 건드리지 않음', () => {
  assert.equal(ctx.subj(v({kr_country: '대만', title: '단수이 노을 여행'}), KR, JP, TW), '대만');
  assert.equal(ctx.subj(v({title: '서울 후쿠오카 여행'}), KR, JP, TW), null);
  assert.equal(ctx.subj(v({title: '후쿠오카 타이베이 여행'}), KR, JP, TW), null);
  assert.equal(ctx.subj(v({kr_regional: false}), KR, JP, TW), null);
});
test('수동 분류가 우선: kindOf 에서 개인 보정·공통 검토 뒤에 놓인다', () => {
  const i = html.indexOf('const kindOf = v =>');
  const body = html.slice(i, i + 4000);
  assert.ok(body.indexOf('own(kindVid, v.id)') < body.indexOf('krRegionalKind(v)'));
  assert.ok(body.indexOf('CURK.channels[v.channel_id]') < body.indexOf('krRegionalKind(v)'));
  assert.ok(body.indexOf('krRegionalKind(v)') < body.indexOf('hangulRatio(v.title)'));
});
test('중복 ID 가 합쳐져도 근거가 남도록 absorb 가 mark 로 kr_* 를 넘긴다', () => {
  assert.match(html, /absorb\(x, \{kr_regional: true, kr_country: x\.kr_country[^}]*\}, "kr_regional"\)/);
  assert.match(html, /SRC_NAMES = new Set\([^)]*"kr_regional"/);
});
