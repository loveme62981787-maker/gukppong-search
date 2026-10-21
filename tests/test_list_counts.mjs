import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('선택 목록 합집합을 중복 없이 세고 목록 변경과 전체 초기화를 반영한다', () => {
  const chips = ['all','scored','A','B','C','H'].map(k => ({dataset:{k}, small:{textContent:''}, querySelector(){return this.small;}}));
  let ready;
  const ctx = vm.createContext({document:{addEventListener(_,fn){ready=fn;}, querySelectorAll(selector){return selector === '#scg .chip' ? chips : [];}}});
  vm.runInContext(`let selected = new Set(['kr','jp']);
    const V = [{id:'1', lists:['kr'], grade:'B'}, {id:'2', lists:['jp','kr'],grade:'A'}, {id:'3',lists:['other'],grade:'C'}, {id:'4',lists:['jp']}];
    const inList = v => !selected.size || v.lists.some(k=>selected.has(k));
    const scGradeOK = (v,k) => k === 'scored' ? !!v.grade : v.grade === k;
    function render() {}
  `, ctx);
  vm.runInContext(fs.readFileSync(new URL('../web/list_counts.js',import.meta.url),'utf8'),ctx);
  ready();
  assert.deepEqual(chips.map(c=>c.small.textContent),['3','2','1','1','0','0']);
  vm.runInContext("selected = new Set(['jp']); render();",ctx);
  assert.equal(chips[1].small.textContent,'1');
  vm.runInContext('selected.clear(); render();',ctx);
  assert.equal(chips[1].small.textContent,'3');
});
