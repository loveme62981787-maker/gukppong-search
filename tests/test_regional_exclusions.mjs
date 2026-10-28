import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// web/index.html 에서 필요한 부분만 잘라 실행한다 (단일 정적 파일 유지)
const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const cut = (a, b) => html.slice(html.indexOf(a), html.indexOf(b));
const line = name => html.split('\n').find(l => l.startsWith('const ' + name + ' ='));
const code = [
  cut('const rx = (ascii', 'V.forEach(v => { const r = regionsOf'),   // 기존 한국 지역 분류(regionsOf 등)
  line('KR_PLACE_RE'), line('TW_RE'), line('JP_PLACE_RE'),
  cut('// <regional-exclusions>', '// </regional-exclusions>'),
  'this.rxMatch = rxMatch;'
].join('\n');
const ctx = vm.createContext({});
vm.runInContext(code, ctx);
const m = (subj, title, k) => ctx.rxMatch({_subj: subj, title}, k);

test('한국: 다른 지역 근거가 있고 서울·부산·제주가 없을 때만 통과', () => {
  assert.equal(m('한국', 'Foreigners in Gyeongju temple stay', 'kr_ex'), true);
  assert.equal(m('한국', '강릉 속초 여행', 'kr_ex'), true);
  assert.equal(m('한국', 'Seoul and Gyeongju trip', 'kr_ex'), false);   // 혼합 여정
  assert.equal(m('한국', '부산 해운대 그리고 전주', 'kr_ex'), false);
  assert.equal(m('한국', 'Jeju and Gangneung', 'kr_ex'), false);
  assert.equal(m('한국', '우도 성산일출봉 여행', 'kr_ex'), false);   // 제주도 전역 제외
  assert.equal(m('한국', 'Korean food in the countryside', 'kr_ex'), false);   // 위치 미확인은 지방 추정 금지
  assert.equal(m('한국', 'Gyeongju and Osaka trip', 'kr_ex'), false);   // 다른 나라 지명
  assert.equal(m('일본', 'Gyeongju trip', 'kr_ex'), false);   // 소재 나라가 다름
});

test('일본: 도쿄를 빼고 다른 지역이 명시된 경우만 통과', () => {
  assert.equal(m('일본', 'Kyoto temples vlog', 'jp_ex'), true);
  assert.equal(m('일본', '오사카 먹방 여행', 'jp_ex'), true);
  assert.equal(m('일본', '北海道 旅行', 'jp_ex'), true);
  assert.equal(m('일본', 'Tokyo to Osaka by train', 'jp_ex'), false);
  assert.equal(m('일본', '도쿄 신주쿠 교토', 'jp_ex'), false);
  assert.equal(m('일본', 'Living in Japan', 'jp_ex'), false);   // 위치 미확인
  assert.equal(m('일본', '나라를 사랑하는 마음', 'jp_ex'), false);   // 한글 '나라'는 지명이 아님
  assert.equal(m('일본', 'Kyoto and Taiwan', 'jp_ex'), false);
});

test('대만: 타이베이를 빼고, 신베이는 별개 지역으로 본다', () => {
  assert.equal(m('대만', 'Kaohsiung night market', 'tw_ex'), true);
  assert.equal(m('대만', '台南 美食', 'tw_ex'), true);
  assert.equal(m('대만', '지우펀 여행', 'tw_ex'), true);
  assert.equal(m('대만', 'New Taipei Jiufen day trip', 'tw_ex'), true);   // 신베이는 타이베이가 아님
  assert.equal(m('대만', '신베이 단수이', 'tw_ex'), true);
  assert.equal(m('대만', 'Taipei to Tainan', 'tw_ex'), false);
  assert.equal(m('대만', 'Ximending and Kenting', 'tw_ex'), false);
  assert.equal(m('대만', 'New Taipei and Taipei 101', 'tw_ex'), false);
  assert.equal(m('대만', 'Living in Taiwan', 'tw_ex'), false);   // 위치 미확인
  assert.equal(m('대만', 'Tainan and Seoul', 'tw_ex'), false);
});
