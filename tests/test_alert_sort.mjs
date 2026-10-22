import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
test('대만 채점 배지는 대만 국기와 국가 이름을 사용한다', () => {
  const code = fs.readFileSync(new URL('../web/my_scores.js', import.meta.url), 'utf8');
  const part = code.slice(code.indexOf('  SC_VER.tw'), code.indexOf('  const tab'));
  const context = {SC_VER:{kr:'한국판'}, scTagEl:()=>({textContent:'🎯 70 · A 🇰🇷'})};
  vm.runInNewContext(part, context);
  assert.equal(context.SC_VER.tw, '🇹🇼 대만판');
  assert.equal(context.scTagEl({ver:'tw'}).textContent, '🎯 70 · A 🇹🇼');
  assert.equal(context.scTagEl({ver:'kr'}).textContent, '🎯 70 · A 🇰🇷');
});
const start = html.indexOf('  const val = v => sort === "score"');
const end = html.indexOf('  updateUI(a.length', start);
assert.ok(start >= 0 && end > start);
const sorting = html.slice(start, end);

test('모든 정렬 방향에서 C는 미채점·보류보다 뒤이고 기존 그룹 내 정렬을 유지한다', () => {
  for (const sort of ['new', 'pub', 'views', 'ratio', 'score', 'myscore', 'subs', 'length']) {
    for (const direction of ['asc', 'desc']) {
      const fixture = (id, n, grade) => ({id, views:n, subs:n, duration_sec:n, _score:n,
        published:`2026-10-${String(n).padStart(2,'0')}`, first_seen:'2026-10-21',
        _sc: grade === 'U' ? null : grade === 'H' ? {held:true} : {grade,total:n}});
      const a = [fixture('c1',1,'C'), fixture('b1',2,'B'), fixture('u',3,'U'), fixture('h',4,'H'), fixture('c2',5,'C'), fixture('b2',6,'B')];
      vm.runInNewContext(sorting, {a,sort,document:{getElementById:()=>({value:direction})},
        scTot:s=>s.total, scGrade:s=>s.grade, ratio:v=>v.views});
      assert.deepEqual(a.slice(-2).map(v=>v.id).sort(), ['c1','c2'], `${sort}/${direction}`);
      assert.deepEqual(a.filter(v=>v.id.startsWith('b')).map(v=>v.id), direction==='asc'?['b1','b2']:['b2','b1']);
    }
  }
});

test('사이트 인라인 스크립트 문법', () => {
  for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
    new vm.Script(match[1]);
  }
});
