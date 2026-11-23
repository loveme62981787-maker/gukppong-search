import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

// index.html 의 일반 목록 길이 정책(10분 이하 롱폼 제외)을 실제 코드 그대로 꺼내 실행한다
const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8').replace(/\r\n/g, '\n');
const m = /const GENERAL_LONG_MIN_SEC = 601;\n(for \(let i = V\.length[^\n]*\n)/.exec(html);

test('일반 목록은 181~600초만 빼고 숏폼·길이 미확인·601초+ 는 유지한다', () => {
  assert.ok(m, '정책 코드를 찾지 못함');
  const ctx = vm.createContext({});
  vm.runInContext(`const LONG_MIN_SEC = 181; const GENERAL_LONG_MIN_SEC = 601;
    const V = [180, 181, 600, 601, null, 59].map((s, i) => ({id: 'v' + i, duration_sec: s}));
    ${m[1]}
    this.ids = V.map(v => v.id).join();`, ctx);
  assert.equal(ctx.ids, 'v0,v3,v4,v5');   // 180, 601, 미확인, 59
});

test('길이 필터 문구가 10분 초과 정책을 말한다', () => {
  assert.match(html, /롱폼만 \(10분 초과\)/);
  assert.doesNotMatch(html, /롱폼만 \(181초\+\)/);
  assert.match(html, /const LONG_MIN_SEC = 181;/);   // 숏폼 분류 기준은 그대로
});

// 로컬 web/ 과 배포용(_site) 이 index.html 의 실제 병합 코드로 만든 V 의 ID 집합이 같아야 한다 (미확인·충돌 사본 부활 방지)
function mergedIds(dir) {
  const a = html.indexOf('const V = (window.VIDEOS');
  const e = 'V.splice(i, 1);\n';
  const code = html.slice(a, html.indexOf(e, a) + e.length);
  const ctx = vm.createContext({console, localStorage: {getItem: () => null}});
  ctx.window = ctx;
  const idx = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
  for (const [, s] of idx.matchAll(/<script[^>]+src="([^"?#]+)/g)) {
    const f = path.join(dir, s);
    if (!fs.existsSync(f) || /hot_shorts/.test(s)) continue;
    try { vm.runInContext(fs.readFileSync(f, 'utf8'), ctx); } catch {}
  }
  vm.runInContext(code + '\nthis.__ids = V.map(v => v.id);', ctx);
  return new Set(ctx.__ids);
}

test('로컬 V 와 배포 V 의 ID 집합이 같다', () => {
  const src = fileURLToPath(new URL('../web', import.meta.url));
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'pp-')) + path.sep + '_site';
  const r = spawnSync('python', ['prepare_pages.py', '--src', src, '--out', out, '--report', out + '.report.json'], {cwd: fileURLToPath(new URL('..', import.meta.url)), encoding: 'utf8'});
  assert.equal(r.status, 0, r.stderr);
  const local = mergedIds(src), dep = mergedIds(out);
  assert.ok(local.size > 1000, 'V 가 비어 있음');
  const blocked = new Set(JSON.parse(fs.readFileSync(out + '.report.json', 'utf8')).channel_blocked_ids || []);
  assert.deepEqual([...dep].sort(), [...local].filter(id => !blocked.has(id)).sort());
});
