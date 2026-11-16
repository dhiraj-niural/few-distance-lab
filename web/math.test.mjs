import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { levels, freeLevel, frontiers, par, squaredDistance, distanceGroups, distanceCount, validatePoints, checkFourPointCondition, encodeState, decodeState, witness, moveCosts, ruleBreakers, randomSource, randomPoints, swapStep, distanceBars, shareText } from './math.mjs';
import { botStudy } from '../tools/bot_study.mjs';
const results = name => JSON.parse(readFileSync(new URL('../results/2026-11-16-exact/'+name,import.meta.url)));

test('vertical stretching gives exact collisions between visibly different displacements', () => {
  assert.equal(squaredDistance([0,0],[1,0]),1);
  assert.equal(squaredDistance([0,0],[0,1]),2);
  assert.equal(squaredDistance([0,0],[3,0]),9);
  assert.equal(squaredDistance([0,0],[1,2]),9);
  assert.equal(squaredDistance([0,0],[0,3]),squaredDistance([0,0],[4,1]));
});

for (const level of levels) {
  test(`${level.id}: target is the proven minimum and the shown board is a checked certificate`, () => {
    const cert = JSON.parse(readFileSync(new URL('../'+level.source,import.meta.url)));
    assert.deepEqual(witness(level,level.baseline).points,cert.points);
    assert.equal(distanceCount(level.baseline),cert.claimed_distance_count);
    assert.equal(level.target,cert.claimed_distance_count);
    assert.equal(level.target,par(level.size,level.count));
    assert.equal(checkFourPointCondition(level.baseline).valid,true);
    const row = results(`frontier-${level.size}x${level.size}.json`).rows.find(r => r.n === level.count);
    assert.equal(row.minimum,level.target);
    assert.equal(results('baselines.json')[level.id].proof.python_nodes,level.proof);
  });
  test(`${level.id}: displayed search results match the recorded runs`, () => {
    const recorded = results('baselines.json')[level.id];
    assert.deepEqual(level.search.random,[recorded.random.best,recorded.random.median]);
    assert.deepEqual(level.search.swap,[recorded.swap.best,recorded.swap.median]);
    assert.deepEqual(level.search.plain,[recorded.plain.hits,recorded.plain.median]);
  });
  test(`${level.id}: shares round-trip empty, partial, complete and reflected boards`, () => {
    for (const points of [[],level.baseline.slice(0,3),level.baseline,level.baseline.map(([x,y])=>[level.size-1-x,level.size-1-y])]) {
      assert.deepEqual(decodeState(encodeState(level,points)),{level,points});
    }
    assert.deepEqual(decodeState(`#level=${level.id}`),{level,points:[]});
    {
    }
  });
}

test('groups include every pair once, with equal distances sharing a group', () => {
  const points=levels[0].baseline, groups=distanceGroups(points);
  assert.deepEqual([...groups.keys()],[1,4,8,9,12,17]);
  const pairs=[...groups.values()].flat();
  assert.equal(pairs.length,28);
  assert.equal(new Set(pairs.map(p=>p.join(','))).size,28);
  assert.ok(groups.get(9).length>1);
});

test('coordinate validation rejects duplicates, bounds, wrong types, fractions and overflow', () => {
  const bad=[null,{},[[0,0],[0,0]],[[4,0]],[[-1,0]],[[0.5,1]],[[true,0]],[[0,'1']],[[1]],[[1,2,3]],[[Infinity,0]],Array(9).fill([0,0])];
  for(const points of bad) assert.throws(()=>validatePoints(points,levels[0]));
  const p=[[0,0],[3,3]];
  const copy=validatePoints(p,levels[0]); copy[0][0]=2;
  assert.deepEqual(p,[[0,0],[3,3]]);
});

test('malformed or oversized shared state cannot bypass coordinate validation', () => {
  for(const hash of ['#level=nope&points=','#level=eight&points=0,0;0,0','#level=eight&points=4,0','#level=eight&points=-1,0','#level=eight&points=0.5,0','#level=eight&points=0,','#level=eight&points=0,0,0','#level=eight&points='+('0'.repeat(2100))]) assert.throws(()=>decodeState(hash));
  assert.deepEqual(decodeState(''),{level:levels[0],points:[]});
});

test('export is a minimal exact certificate and rejects fewer than four points', () => {
  assert.throws(()=>witness(levels[0],[[0,0],[1,0]]));
  assert.deepEqual(witness(levels[0],[[1,1],[0,1],[1,0],[0,0]]),{
    schema_version:1,metric:{q_num:2,q_den:1},grid:{width:4,height:4},points:[[0,0],[0,1],[1,0],[1,1]],claimed_distance_count:3,
  });
});

test('all selectable points on each board satisfy the four-point condition', () => {
  for(const size of new Set(levels.map(l=>l.size))) {
    const points=Array.from({length:size*size},(_,i)=>[i%size,Math.floor(i/size)]);
    const result=checkFourPointCondition(points), n=points.length;
    assert.equal(result.valid,true);
    assert.equal(result.checked,n*(n-1)*(n-2)*(n-3)/24);
  }
});

test('embedded minima equal the recorded exhaustive results for every board and count', () => {
  const minima = results('minima.json');
  for (const size of [4,5,6,7]) assert.deepEqual(frontiers[size],minima[`${size}x${size}`]);
});

test('move costs are the exact increase in distinct distances', () => {
  const points = [[0,0],[1,0],[2,0],[0,2]];
  for (const [site,cost] of moveCosts(points,4)) {
    assert.equal(cost,distanceCount([...points,site.split(',').map(Number)])-distanceCount(points));
  }
  assert.equal(moveCosts(points,4).size,12);
  assert.equal(moveCosts(points,4).get('1,2'),0);
});

test('only the sqrt(2) stretch among 1, sqrt(2), sqrt(3), 2 keeps the four-point rule on a 5x5 grid', () => {
  assert.deepEqual([1,2,3,4].map(q => ruleBreakers(5,q).found.length),[50,0,46,18]);
  assert.equal(ruleBreakers(5,2).total,12650);
});

test('local search is replayable, never accepts a worse board and keeps points distinct', () => {
  const level = levels[3], random = randomSource(7);
  let points = randomPoints(level,random), score = distanceCount(points);
  for (let i = 0; i < 300; i++) {
    const step = swapStep(points,level.size,random);
    assert.ok(step.score <= score); assert.equal(step.score,distanceCount(step.points));
    assert.equal(new Set(step.points.map(String)).size,level.count);
    ({ points, score } = step);
  }
  assert.deepEqual(randomPoints(level,randomSource(7)),randomPoints(level,randomSource(7)));
});

test('the bot study is reproducible on the first board', () => {
  assert.deepEqual(botStudy(levels[0]),results('baselines.json').eight.plain);
});

test('free play accepts boards 4 to 7 wide and round-trips through links', () => {
  const level = freeLevel(6), points = [[5,5],[0,0]];
  assert.deepEqual(decodeState(encodeState(level,points)),{level,points});
  assert.throws(() => decodeState('#level=free&size=9&points='),/board size/);
  assert.throws(() => freeLevel(8));
});

test('a shared result names the score without revealing the points', () => {
  const text = shareText(levels[0],levels[0].baseline);
  assert.match(text,/8 points, 6 distances on a 4×4 board: the proven minimum/);
  assert.equal(distanceBars(levels[0].baseline).length,6);
  assert.doesNotMatch(text,/\d,\d/);
  assert.match(shareText(levels[0],[[0,0],[1,0],[3,1],[2,3]]),/over the proven minimum of 3/);
});
