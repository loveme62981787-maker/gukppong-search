import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../web/taiwan_hidden.js',import.meta.url),'utf8');
test('대만체험은 검토한 ID만 추가하고 기존 목록과 미확인 영상을 보존한다',()=>{
 const setup=source.split("document.addEventListener('DOMContentLoaded', () => {")[1].split('  refreshListCounts();')[0];
 const context=vm.createContext({});
 vm.runInContext(`const LISTS=[];const LISTKEYS=new Set();const LISTTAG={};const LIST_NOTE={};
 const V=[{id:'kBE3UhVhsNI',country:'대만'},{id:'ASWget6dxVE',country:'대만'},{id:'Omk4X543OfA',country:'대만'}];
 function computeLists(){for(const v of V){v._lists=['notion'];v._hold=true;v._subj=v.country;}}
 `+setup,context);
 assert.equal(vm.runInContext('V[0]._lists.join(",")',context),'notion,twexp');
 assert.equal(vm.runInContext('V[1]._lists.includes("twexp")',context),false);
 assert.equal(vm.runInContext('V[2]._lists.includes("twexp")',context),false);
 assert.equal(vm.runInContext('V.length',context),3);
 vm.runInContext('computeLists();',context);
 assert.equal(vm.runInContext('V[0]._lists.filter(k=>k==="twexp").length',context),1);
});
