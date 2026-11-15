// Integer lattice indices represent physical points (x, sqrt(2) y).
export const levels = [
  { id: 'eight', name: 'Find the pattern', size: 4, count: 8, target: 6, proven: true,
    hint: 'Try making several pairs share the same length. Two separated rows can help.',
    source: 'results/2026-11-06/certificates/exact-4x4-n8.json',
    baseline: [[0,0],[0,2],[1,0],[1,2],[2,0],[2,2],[3,0],[3,2]] },
  { id: 'ten', name: 'Make lengths collide', size: 6, count: 10, target: 8, proven: false,
    hint: 'A vertical gap and a slanted gap can have exactly the same length. Try two columns four steps apart.',
    source: 'results/2026-11-08-compact-rows/certificates/compact-6-n10.json',
    baseline: [[0,0],[0,1],[0,2],[0,3],[0,4],[4,0],[4,1],[4,2],[4,3],[4,4]] },
  { id: 'twenty', name: 'The 20-point challenge', size: 7, count: 20, target: 17, proven: false,
    hint: 'The saved construction uses four evenly spaced columns of five points. Matching it is a good start.',
    source: 'results/2026-11-08-compact-rows/certificates/compact-7-n20.json',
    baseline: [0,2,4,6].flatMap(x => [0,1,2,3,4].map(y => [x,y])) },
];

export const squaredDistance = (a, b) => (a[0]-b[0]) ** 2 + 2 * (a[1]-b[1]) ** 2;
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
  const params = new URLSearchParams({ level: level.id, points: points.map(key).join(';') });
  return '#' + params.toString();
}

export function decodeState(hash) {
  if (!hash || hash === '#') return { level: levels[0], points: [] };
  if (hash.length > 2000) throw new Error('This shared board link is too long.');
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  const level = levels.find(l => l.id === params.get('level'));
  if (!level) throw new Error('The shared link has an unknown challenge.');
  const raw = params.get('points');
  if (raw === null) throw new Error('The shared link is missing its points.');
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
