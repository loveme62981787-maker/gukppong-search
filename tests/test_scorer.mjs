// 간이 채점기(web/scorer.js) 테스트: node --test tests/test_scorer.mjs
// 키워드 규칙으로 센 값이므로 '정확한 점수'가 아니라 범위·형식·경고가 맞는지만 확인한다.
import test from "node:test";
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require = createRequire(import.meta.url);
const S = require("../web/scorer.js");

const happyKr = `
So we just landed in Seoul and took the airport express train. It was so clean and the subway map is incredible. I didn't expect it to be this easy.
We went to a convenience store at midnight and the kimbap was so good. The staff were super friendly and helpful.
Then we walked along the Han River at night and it felt really safe. Honestly I can't believe how peaceful it is.
We tried Korean barbecue and the pork belly was the best I have ever had. The side dishes were unlimited and the staff grilled it for us. Wow.
Next day we visited the palace in hanbok. The hanok village was beautiful and the view from the mountain was stunning.
I bought skincare at Olive Young and it was so cheap compared to home. The cafe had the best latte and the dessert was delicious.
Surprisingly, the whole thing turned out better than I expected. We loved it and we will come back.
`.repeat(4);

const grumpy = `
We arrived and everything was terrible. The room was dirty and expensive and the staff were rude. I am so tired and annoyed.
The restaurant was overpriced and the food was bad. It was crowded and chaotic and I hated the subway.
Honestly the worst trip. I wasted my money and I want a refund.
`.repeat(10);

test("기준 데이터: 항목 배점 합은 100, 등급 기준은 큰 값부터", () => {
  assert.equal(S.RUBRIC.reduce((a, r) => a + r.max, 0), 100);
  const mins = S.GRADES.map(g => g.min);
  assert.deepEqual(mins, [...mins].sort((a, b) => b - a));
  assert.equal(S.gradeOf(85), "S"); assert.equal(S.gradeOf(70), "A"); assert.equal(S.gradeOf(55), "B"); assert.equal(S.gradeOf(54), "C"); assert.equal(S.gradeOf(0), "C");
});

test("갈래는 한국·일본 각각 12개", () => {
  assert.equal(S.CATS.kr.length, 12); assert.equal(S.CATS.jp.length, 12);
});

test("호의적인 영어 스크립트: 범위 안의 점수와 포인트를 낸다", () => {
  const r = S.estimate(happyKr, {ver: "kr", minutes: 20});
  assert.ok(r.points >= 5, "포인트 " + r.points);
  assert.ok(r.total > 40 && r.total <= 100, "총점 " + r.total);
  Object.entries(r.parts).forEach(([k, v]) => { const max = S.RUBRIC.find(x => x.key === k).max; assert.ok(v >= 0 && v <= max, k + "=" + v); });
  assert.equal(r.grade, S.gradeOf(r.total));
  assert.ok(r.perCat.length >= 3);
  assert.ok(r.quotes.length > 0);
});

test("불평이 많은 스크립트는 호의 일관성이 낮고 총점이 호의적인 것보다 낮다", () => {
  const good = S.estimate(happyKr, {ver: "kr", minutes: 20}), bad = S.estimate(grumpy, {ver: "kr", minutes: 20});
  assert.ok(bad.parts.favor < good.parts.favor);
  assert.ok(bad.total < good.total);
});

test("분량: 직접 입력 > 시간 표시 > 단어 수 순서로 쓴다", () => {
  const withTime = "(00:10) We love Seoul and the food was delicious. " + "x ".repeat(10) + "(30:00) The palace was beautiful and we loved the view.";
  assert.equal(S.estimate(withTime, {minutes: 12}).minutes, 12);
  assert.equal(S.estimate(withTime, {}).minutes, 30);
  assert.ok(S.estimate("The food was delicious and we love it so much. ".repeat(20), {}).minutes >= 1);
});

test("빈 입력·음악뿐인 입력도 예외 없이 낮은 점수와 경고를 낸다", () => {
  const empty = S.estimate("", {});
  assert.equal(empty.points, 0); assert.ok(empty.flags.length > 0);
  const music = S.estimate("[music] [music] Heat. Heat. [music] ".repeat(30), {});
  assert.ok(music.total < 30); assert.ok(music.flags.some(f => f.includes("음악") || f.includes("짧")));
  assert.doesNotThrow(() => S.estimate(null, {})); assert.doesNotThrow(() => S.estimate(undefined, {ver: "jp"}));
});

test("광고·민감 주제·욕설 경고", () => {
  const t = "This video is sponsored by Klook, use my code for a discount. We visited Dokdo and it was amazing. " + "What the fuck, this is fucking shit. ".repeat(3) + "The food was delicious and we love it. ".repeat(10);
  const r = S.estimate(t, {});
  assert.ok(r.flags.some(f => f.includes("광고")));
  assert.ok(r.flags.some(f => f.includes("민감")));
  assert.ok(r.flags.some(f => f.includes("욕설")));
});

test("일본 버전은 일본 갈래로 센다", () => {
  const jp = "We went to Akihabara and the anime shops were incredible. The ramen at the izakaya was so good and the staff were super polite. The shinkansen was on time and clean. ".repeat(6);
  const r = S.estimate(jp, {ver: "jp", minutes: 10});
  assert.ok(r.perCat.some(c => ["쇼핑·애니·게임", "일식·첫입", "접객·친절·배려"].includes(c.name)));
  assert.ok(!r.perCat.some(c => c.name === "K팝·팬덤·콘텐츠"));
});

test("영어가 아닌 스크립트는 정확도 경고", () => {
  const es = "Hola chicos hoy vamos a la calle y vamos a comer algo muy rico porque tenemos hambre y luego vamos a casa a descansar un poco. ".repeat(12);
  assert.ok(S.estimate(es, {}).flags.some(f => f.includes("영어")));
});
