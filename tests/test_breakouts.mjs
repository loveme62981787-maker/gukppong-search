import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const load = () => {
  const ctx = vm.createContext({document: {addEventListener() {}}});
  vm.runInContext(fs.readFileSync(new URL('../web/breakouts.js', import.meta.url), 'utf8'), ctx);
  return ctx;
};
const isHot = v => v.views / Math.max(v.subs, 1000) >= 3 && v.views >= 500;
const mk = o => ({id: 'x', subs: 1000, views: 5000, _kind: 'foreign', _lists: ['krexp'], ...o});

test('체험 목록 + 구독자 대비 높음만 나라별 터진 영상 키를 받는다', () => {
  const keys = (o) => [...load().breakoutKeys(mk(o), isHot)];   // vm 컨텍스트 배열을 일반 배열로 바꿔 비교
  assert.deepEqual(keys({_lists: ['krexp', 'jpexp', 'twexp']}), ['hot_kr', 'hot_jp', 'hot_tw']);
  assert.deepEqual(keys({_lists: ['twexp']}), ['hot_tw']);
  assert.deepEqual(keys({views: 2000}), []);          // 3배 미만
  assert.deepEqual(keys({_lists: ['krguk']}), []);    // 체험 목록 아님
  for (const o of [{ref: true}, {bm: true}, {_kind: 'local'}, {_kind: 'inst'}, {subs: 0}, {subs: null}, {views: NaN}])
    assert.deepEqual(keys(o), [], JSON.stringify(o));
});

test('채널 중앙값: 같은 채널·같은 형식·중복 제거·유효 조회수·최소 4개', () => {
  const {channelMedianRatio} = load();
  const v = {id: 'v', channel_id: 'c', _form: 'long', views: 10000};
  const row = (id, views, o = {}) => ({id, channel_id: 'c', _form: 'long', views, ...o});
  const pool = [v, row('a', 1000), row('b', 2000), row('c', 3000), row('d', 4000),
    row('d', 999999),                           // 같은 ID 중복은 한 번만
    row('s', 5, {_form: 'short'}), row('o', 5, {channel_id: 'z'}), row('n', NaN), row('u', undefined)];
  assert.deepEqual({...channelMedianRatio(v, pool)}, {n: 4, median: 2500, x: 4});
  assert.equal(channelMedianRatio(v, pool.slice(0, 4)), null);              // 표본 3개 → 생략
  assert.equal(channelMedianRatio({...v, _form: 'unk'}, pool), null);       // 길이 미확인
  assert.equal(channelMedianRatio({...v, channel_id: ''}, pool), null);
  assert.equal(channelMedianRatio(v, [v, ...[1, 2, 3, 4].map(i => row('z' + i, 0))]), null);   // 중앙값 0
});

test('터진 영상 목록이 아니면 카드 설명이 없고, 표본이 부족하면 중앙값만 생략한다', () => {
  const {breakoutInfo} = load();
  const ratio = v => v.views / Math.max(v.subs, 1000);
  assert.equal(breakoutInfo(mk({_lists: ['krexp']}), [], ratio), null);
  const info = breakoutInfo(mk({_lists: ['krexp', 'hot_kr']}), [], ratio);
  assert.equal(info.sub, 5); assert.equal(info.med, null);
});
