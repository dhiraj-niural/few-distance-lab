import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { levels, squaredDistance, distanceGroups, validatePoints, checkFourPointCondition, encodeState, decodeState, witness } from './math.mjs';

test('vertical stretching gives exact collisions between visibly different displacements', () => {
  assert.equal(squaredDistance([0,0],[1,0]),1);
  assert.equal(squaredDistance([0,0],[0,1]),2);
  assert.equal(squaredDistance([0,0],[3,0]),9);
  assert.equal(squaredDistance([0,0],[1,2]),9);
  assert.equal(squaredDistance([0,0],[0,3]),squaredDistance([0,0],[4,1]));
});

for (const level of levels) {
  test(`${level.id}: exact preset agrees with its existing, independently verified certificate`, () => {
    const cert = JSON.parse(readFileSync(new URL('../'+level.source,import.meta.url)));
    assert.deepEqual(witness(level,level.baseline).points,cert.points);
    assert.equal(distanceGroups(level.baseline).size,cert.claimed_distance_count);
    assert.equal(level.target,cert.claimed_distance_count);
    assert.deepEqual([...distanceGroups(level.baseline).keys()].map(String),cert.verification.primary.squared_distances);
    assert.deepEqual(checkFourPointCondition(level.baseline),{valid:true,checked:cert.verification.primary.checked_quadruples});
    assert.equal(level.proven,cert.search.domain_optimal);
  });
  test(`${level.id}: shares round-trip empty, partial, complete and reflected boards`, () => {
    for (const points of [[],level.baseline.slice(0,3),level.baseline,level.baseline.map(([x,y])=>[level.size-1-x,level.size-1-y])]) {
      assert.deepEqual(decodeState(encodeState(level,points)),{level,points});
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
  for(const hash of ['#level=nope&points=','#level=eight','#level=eight&points=0,0;0,0','#level=eight&points=4,0','#level=eight&points=-1,0','#level=eight&points=0.5,0','#level=eight&points=0,','#level=eight&points=0,0,0','#level=eight&points='+('0'.repeat(2100))]) assert.throws(()=>decodeState(hash));
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
