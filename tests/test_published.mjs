import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// web/index.html 에서 absorb 와 카드의 날짜 표기 식만 잘라 실행한다 (단일 정적 파일 유지)
const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const start = html.indexOf('function absorb(');
const absorbSrc = html.slice(start, html.indexOf('(window.VIRAL', start));
const label = html.match(/\.m"\)\.textContent = v\.channel \+ " · " \+ (\(.*?\));\s*\/\//)[1];

function ctx(V) {
  const c = {V, normLen: x => ({sec: x.duration_sec ?? null, text: x.length ?? null}), addSrc: () => {}};
  vm.createContext(c);
  vm.runInContext(absorbSrc, c);
  return c;
}

test('기존 영상의 빈 날짜는 채우고, 다른 경로는 덮어쓰지 않으며, 확인된 CC 날짜(KST)는 추정 날짜를 대체한다', () => {
  const V = [{id: 'a', published: ''}, {id: 'b', published: '2020-01-01'}, {id: 'c'}];
  const c = ctx(V);
  c.absorb({id: 'a', published: '2024-05-01'}, null, 'cc_discovery');
  c.absorb({id: 'b', published: '2024-05-01'}, null, 'discovery');
  c.absorb({id: 'c', published: ''}, null, 'cc_discovery');
  assert.equal(V[0].published, '2024-05-01');
  assert.equal(V[1].published, '2020-01-01');
  assert.ok(!V[2].published);
});

test('카드 날짜: 업로드일만 표시하고 없으면 미확인 (수집일을 쓰지 않는다)', () => {
  const show = v => vm.runInNewContext(label, {v});
  assert.equal(show({published: '2024-05-01'}), '업로드 2024-05-01');
  assert.equal(show({published: '', first_seen: '2026-10-31'}), '업로드 날짜 미확인');
  assert.equal(show({first_seen: '2026-10-31'}), '업로드 날짜 미확인');
  assert.equal(show({viral: true, age_text: '3일 전', published: ''}), '3일 전');
});
