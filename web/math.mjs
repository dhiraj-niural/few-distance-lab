// Integer lattice indices represent physical points (x, sqrt(2) y).
// Proven minimum number of distinct distances for n points on each square board,
// indexed by n. Source: results/2026-11-16-exact/frontier-*.json (exhaustive
// branch and bound, two independent implementations).
export const frontiers = {
  4: [0,0,1,2,3,4,5,6,6,8,9,10,10,13,13,14,14],
  5: [0,0,1,2,3,4,5,6,6,8,8,10,10,12,13,13,14,16,16,17,17,19,21,21,22,22],
  6: [0,0,1,2,3,4,5,6,6,8,8,9,10,11,12,13,14,15,15,17,17,19,19,20,20,22,22,24,24,25,25,28,28,30,30,31,31],
  7: [0,0,1,2,3,4,5,6,6,8,8,9,10,11,11,12,13,14,15,16,17,17,19,20,20,22,22,23,24,25,25,26,28,28,29,29,31,32,32,34,34,35,35,38,39,39,41,41,42,42],
};
export const par = (size, n) => frontiers[size][n];

// Recorded in results/2026-11-16-exact/baselines.json, 2,000 evaluations per run.
// random, swap: [best, median] over ten seeds of the Python baselines (swap restarts).
// plain: [runs out of 200 that reach the minimum, median score] for the restart-free
// local search the page animates. proof: nodes visited refuting (target - 1).
export const levels = [
  { id: 'eight', name: 'Find the pattern', size: 4, count: 8, target: 6,
    hint: 'Two full rows, with a gap between them, repeat the same few lengths over and over.',
    source: 'results/2026-11-16-exact/certificates/exact-4x4-n8.json',
    search: { random: [6, 7], swap: [6, 6] , plain: [2, 7] }, proof: 130,
    baseline: [[0,0],[0,2],[1,0],[1,2],[2,0],[2,2],[3,0],[3,2]] },
  { id: 'twelve', name: 'Pack them tight', size: 5, count: 12, target: 10,
    hint: 'A compact block beats a spread-out one. Try four columns and three neighbouring rows.',
    source: 'results/2026-11-16-exact/certificates/exact-5x5-n12.json',
    search: { random: [13, 13], swap: [10, 10] , plain: [122, 10] }, proof: 3138,
    baseline: [0,1,2,3].flatMap(x => [0,1,2].map(y => [x,y])) },
  { id: 'ten', name: 'Make lengths collide', size: 6, count: 10, target: 8,
    hint: 'A vertical gap and a slanted gap can have exactly the same length. Try two columns four steps apart.',
    source: 'results/2026-11-16-exact/certificates/exact-6x6-n10.json',
    search: { random: [11, 12], swap: [9, 9] , plain: [1, 9] }, proof: 6484,
    baseline: [[0,0],[0,1],[0,2],[0,3],[0,4],[4,0],[4,1],[4,2],[4,3],[4,4]] },
  { id: 'twenty', name: 'The 20-point board', size: 7, count: 20, target: 17,
    hint: 'Four evenly spaced columns of five points reach 17. So do three spaced-out rows.',
    source: 'results/2026-11-16-exact/certificates/exact-7x7-n20.json',
    search: { random: [27, 28], swap: [17, 19] , plain: [79, 18] }, proof: 1696518,
    baseline: [0,2,4,6].flatMap(x => [0,1,2,3,4].map(y => [x,y])) },
];

export const freeLevel = size => {
  if (!frontiers[size]) throw new Error('Free play boards are 4 to 7 points wide.');
  return { id: 'free', name: 'Free play', size, count: size * size, free: true };
};

export const squaredDistance = (a, b, q = 2) => (a[0]-b[0]) ** 2 + q * (a[1]-b[1]) ** 2;
export const key = p => p.join(',');

export function distanceGroups(points) {
  const groups = new Map();
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      const d = squaredDistance(points[i], points[j]);
      if (!groups.has(d)) groups.set(d, []);
      groups.get(d).push([i, j]);
    }
  }
  return new Map([...groups].sort(([a], [b]) => a - b));
}

export function validatePoints(points, level) {
  if (!Array.isArray(points)) throw new Error('Enter an array of coordinate pairs, such as [[0,0],[1,0]].');
  if (points.length > level.count) throw new Error(`This challenge allows at most ${level.count} points.`);
  const seen = new Set();
  for (const p of points) {
    if (!Array.isArray(p) || p.length !== 2 || !p.every(Number.isInteger)) {
      throw new Error('Each point needs exactly two whole-number coordinates.');
    }
    if (p.some(c => c < 0 || c >= level.size)) throw new Error(`Coordinates must be between 0 and ${level.size - 1}.`);
    if (seen.has(key(p))) throw new Error(`Point (${p.join(', ')}) appears more than once.`);
    seen.add(key(p));
  }
  return points.map(p => [...p]);
}

export function checkFourPointCondition(points) {
  let checked = 0;
  for (let a = 0; a < points.length; a++) for (let b = a + 1; b < points.length; b++) {
    for (let c = b + 1; c < points.length; c++) for (let d = c + 1; d < points.length; d++) {
      checked++;
      if (distanceGroups([points[a], points[b], points[c], points[d]]).size < 3) return { valid: false, checked };
    }
  }
  return { valid: true, checked };
}

export function encodeState(level, points) {
  validatePoints(points, level);
  const params = new URLSearchParams({ level: level.id, ...(level.free ? { size: level.size } : {}), points: points.map(key).join(';') });
  return '#' + params.toString();
}

export function decodeState(hash) {
  if (!hash || hash === '#') return { level: levels[0], points: [] };
  if (hash.length > 2000) throw new Error('This shared board link is too long.');
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  let level = levels.find(l => l.id === params.get('level'));
  if (params.get('level') === 'free') {
    if (!/^[4-7]$/.test(params.get('size') ?? '')) throw new Error('The shared link has an unknown board size.');
    level = freeLevel(Number(params.get('size')));
  }
  if (!level) throw new Error('The shared link has an unknown challenge.');
  const raw = params.get('points') ?? '';
  const points = raw === '' ? [] : raw.split(';').map(pair => {
    if (!/^\d+,\d+$/.test(pair)) throw new Error('The shared link contains an invalid coordinate.');
    return pair.split(',').map(Number);
  });
  return { level, points: validatePoints(points, level) };
}

export function witness(level, points) {
  validatePoints(points, level);
  if (points.length < 4) throw new Error('Place at least four points to export a verifiable witness.');
  return {
    schema_version: 1,
    metric: { q_num: 2, q_den: 1 },
    grid: { width: level.size, height: level.size },
    points: points.map(p => [...p]).sort((a,b) => a[0]-b[0] || a[1]-b[1]),
    claimed_distance_count: distanceGroups(points).size,
  };
}

export function distanceCount(points, q = 2) {
  const seen = new Set();
  for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length; j++) seen.add(squaredDistance(points[i], points[j], q));
  return seen.size;
}

// For every empty site: how many new distances would a point there add?
export function moveCosts(points, size) {
  const have = new Set(), taken = new Set(points.map(key)), costs = new Map();
  for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length; j++) have.add(squaredDistance(points[i], points[j]));
  for (let x = 0; x < size; x++) for (let y = 0; y < size; y++) {
    if (taken.has(key([x, y]))) continue;
    const added = new Set();
    for (const p of points) { const d = squaredDistance(p, [x, y]); if (!have.has(d)) added.add(d); }
    costs.set(key([x, y]), added.size);
  }
  return costs;
}

// Four-point subsets of the full size x size grid with fewer than three
// distances, when rows are stretched by sqrt(q). q = 2 has none.
export function ruleBreakers(size, q) {
  const sites = [], found = [];
  for (let x = 0; x < size; x++) for (let y = 0; y < size; y++) sites.push([x, y]);
  let total = 0;
  for (let a = 0; a < sites.length; a++) for (let b = a + 1; b < sites.length; b++)
    for (let c = b + 1; c < sites.length; c++) for (let d = c + 1; d < sites.length; d++) {
      total++;
      const four = [sites[a], sites[b], sites[c], sites[d]];
      if (distanceCount(four, q) < 3) found.push(four);
    }
  return { total, found };
}

// Small deterministic generator so a watched search run can be replayed in tests.
export function randomSource(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function randomPoints(level, random) {
  const sites = [];
  for (let x = 0; x < level.size; x++) for (let y = 0; y < level.size; y++) sites.push([x, y]);
  for (let i = sites.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1)); [sites[i], sites[j]] = [sites[j], sites[i]];
  }
  return sites.slice(0, level.count);
}

// One proposal of plain local search: move one point to an empty site and keep
// the move unless it adds distances. No restarts, no lookahead.
export function swapStep(points, size, random) {
  const taken = new Set(points.map(key));
  const index = Math.floor(random() * points.length);
  let site;
  do { site = [Math.floor(random() * size), Math.floor(random() * size)]; } while (taken.has(key(site)));
  const next = points.map((p, i) => i === index ? site : p);
  const before = distanceCount(points), after = distanceCount(next);
  return after <= before ? { points: next, score: after, moved: true } : { points, score: before, moved: false };
}

// Spoiler-free picture of a result: one bar per distance, taller for lengths
// that more pairs share.
export function distanceBars(points) {
  const sizes = [...distanceGroups(points).values()].map(pairs => pairs.length).sort((a, b) => b - a);
  const top = sizes[0] ?? 1, blocks = '▁▂▃▄▅▆▇█';
  return sizes.map(n => blocks[Math.max(0, Math.ceil(n / top * 8) - 1)]).join('');
}

export function shareText(level, points) {
  const n = points.length, d = distanceCount(points), best = par(level.size, n);
  const verdict = d === best ? 'the proven minimum' : `${d - best} over the proven minimum of ${best}`;
  return `${n} points, ${d} distances on a ${level.size}×${level.size} board: ${verdict}.\n${distanceBars(points)}\nfew-distance lab`;
}
