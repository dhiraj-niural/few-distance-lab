import {
  levels, freeLevel, par, key, squaredDistance, distanceGroups, validatePoints, checkFourPointCondition,
  encodeState, decodeState, witness, moveCosts, ruleBreakers, randomSource, randomPoints, swapStep, shareText,
} from './math.mjs';

const $ = id => document.getElementById(id);
const sourceRoot = 'https://github.com/dhiraj-niural/few-distance-lab/blob/main/';
const siteUrl = 'https://dhiraj-niural.github.io/few-distance-lab/';
const svgNS = 'http://www.w3.org/2000/svg';
const width = 420, pad = 43, usable = width - 2 * pad;
const BOT_BUDGET = 2000;

let level = levels[0], points = [], history = [], groups = new Map();
let selectedDistance = null, hoveredDistance = null;
// `shown` is 'reveal' or 'bot' while the board holds an arrangement the player did not build.
let shown = false, bot = null, flash = null, freshDistances = new Set();
let height = usable * Math.SQRT2 + 2 * pad;
const solved = new Set(), yourBest = new Map();

const remember = {
  load() {
    try {
      const saved = JSON.parse(localStorage.getItem('few-distance') ?? '{}');
      (saved.solved ?? []).forEach(id => solved.add(id));
      Object.entries(saved.best ?? {}).forEach(([id, score]) => yourBest.set(id, score));
      if (saved.costs === false) $('costs').checked = false;
    } catch { /* storage is optional */ }
  },
  save() {
    try {
      localStorage.setItem('few-distance', JSON.stringify({
        solved: [...solved], best: Object.fromEntries(yourBest), costs: $('costs').checked,
      }));
    } catch { /* storage is optional */ }
  },
};

function position([x, y]) {
  const step = usable / (level.size - 1);
  return [pad + x * step, height - pad - y * step * Math.SQRT2];
}

function svgLine(a, b, className) {
  const element = document.createElementNS(svgNS, 'line');
  const [x1, y1] = position(a), [x2, y2] = position(b);
  Object.entries({ x1, y1, x2, y2, class: className }).forEach(([k, v]) => element.setAttribute(k, v));
  return element;
}

function drawLines() {
  const svg = $('lines');
  svg.replaceChildren();
  for (let n = 0; n < level.size; n++) {
    svg.append(svgLine([n, 0], [n, level.size - 1], 'grid-line'), svgLine([0, n], [level.size - 1, n], 'grid-line'));
    const [x, y] = position([n, n]);
    for (const [tx, ty] of [[x, height - 17], [20, y + 3]]) {
      const label = document.createElementNS(svgNS, 'text');
      label.setAttribute('x', tx); label.setAttribute('y', ty);
      label.setAttribute('class', 'axis-label'); label.textContent = n; svg.append(label);
    }
  }
  const distance = hoveredDistance ?? selectedDistance;
  const pairs = groups.get(distance) ?? [];
  const active = new Set();
  if (flash && !pairs.length) {
    for (const other of points) {
      if (key(other) === key(flash.point)) continue;
      const fresh = flash.fresh.has(squaredDistance(other, flash.point));
      svg.append(svgLine(flash.point, other, `flash-line ${fresh ? 'fresh' : 'reused'}`));
    }
  }
  for (const [a, b] of pairs) {
    svg.append(svgLine(points[a], points[b], 'pair-line'));
    active.add(key(points[a])); active.add(key(points[b]));
  }
  document.querySelectorAll('.point').forEach(button => button.classList.toggle('in-pair', active.has(button.dataset.key)));
  document.querySelectorAll('.distance-chip').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.distance) === distance)));
  $('distance-detail').textContent = pairs.length
    ? `Squared length ${distance}: ${pairs.length} ${pairs.length === 1 ? 'pair has' : 'pairs share'} it.`
    : points.length < 2 ? 'Place two points to make your first distance.' : 'A repeated length counts once. Tall bars are doing the work.';
}

function buildBoard() {
  height = usable * Math.SQRT2 + 2 * pad;
  $('board').style.aspectRatio = `${width} / ${height}`;
  $('board').classList.toggle('dense', level.size >= 6);
  $('lines').setAttribute('viewBox', `0 0 ${width} ${height}`);
  $('grid-points').replaceChildren();
  for (let y = level.size - 1; y >= 0; y--) for (let x = 0; x < level.size; x++) {
    const p = [x, y], button = document.createElement('button');
    button.type = 'button'; button.className = 'point'; button.dataset.key = key(p);
    button.setAttribute('aria-pressed', 'false'); button.tabIndex = x === 0 && y === 0 ? 0 : -1;
    const [px, py] = position(p);
    button.style.left = `${100 * px / width}%`; button.style.top = `${100 * py / height}%`;
    button.addEventListener('click', () => togglePoint(p));
    button.addEventListener('focus', () => {
      document.querySelectorAll('.point').forEach(b => b.tabIndex = b === button ? 0 : -1);
    });
    button.addEventListener('keydown', event => {
      const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[event.key];
      if (!delta) return;
      event.preventDefault();
      const next = [Math.max(0, Math.min(level.size - 1, x + delta[0])), Math.max(0, Math.min(level.size - 1, y + delta[1]))];
      document.querySelector(`.point[data-key="${key(next)}"]`).focus();
    });
    $('grid-points').append(button);
  }
}

function updateURL() {
  window.history.replaceState(null, '', encodeState(level, points));
}

function changePoints(next, { show = false, placed = null } = {}) {
  history.push({ points: points.map(p => [...p]), shown });
  const before = new Set(distanceGroups(points).keys());
  points = validatePoints(next, level);
  // A revealed answer stays revealed until the board is cleared; a bot's board becomes yours once you edit it.
  shown = show ? 'reveal' : shown === 'reveal' && points.length > 0 ? 'reveal' : false;
  freshDistances = new Set([...distanceGroups(points).keys()].filter(d => !before.has(d)));
  flash = placed ? { point: placed, fresh: freshDistances } : null;
  $('action-message').textContent = ''; $('share-fallback').hidden = true;
  render(placed); updateURL();
  const current = flash;
  if (current) setTimeout(() => { if (flash === current) { flash = null; drawLines(); } }, 1300);
}

function togglePoint(p) {
  if (bot) return;
  const found = points.findIndex(q => key(p) === key(q));
  if (found >= 0) changePoints(points.filter((_, i) => i !== found));
  else if (points.length < level.count) changePoints([...points, p], { placed: p });
  else $('action-message').textContent = `All ${level.count} points are placed. Remove one, then put it somewhere better.`;
}

function setStatus(html, success = false) {
  $('status').innerHTML = html; $('status').classList.toggle('success', success);
}

function render(placed = null) {
  groups = distanceGroups(points);
  if (!groups.has(selectedDistance)) selectedDistance = null;
  hoveredDistance = null;
  const n = points.length, d = groups.size, best = par(level.size, n);
  const full = n === level.count, over = d - best;
  const atMinimum = n >= 2 && over === 0;
  const done = level.free ? atMinimum && n >= 8 : full && atMinimum;

  if (!shown && !bot && !level.free && full) {
    yourBest.set(level.id, Math.min(d, yourBest.get(level.id) ?? Infinity));
    if (done) solved.add(level.id);
    remember.save();
  }

  $('point-count').replaceChildren(document.createTextNode(String(n)));
  const outOf = document.createElement('span'); outOf.textContent = `/ ${level.count}`; $('point-count').append(outOf);
  $('distance-count').textContent = d;
  $('distance-count').classList.toggle('level-with-par', atMinimum);
  $('par-count').textContent = best;
  $('par-label').textContent = n < 2 ? 'proven minimum' : `proven minimum for ${n} points`;
  $('pair-count').textContent = `${n * (n - 1) / 2} pairs`;
  $('undo').disabled = !history.length || !!bot; $('reset').disabled = !n || !!bot;
  $('export').disabled = n < 4;

  const selected = new Set(points.map(key));
  const costs = $('costs').checked && n >= 1 && n < level.count && !bot ? moveCosts(points, level.size) : new Map();
  document.querySelectorAll('.point').forEach(button => {
    const on = selected.has(button.dataset.key), cost = costs.get(button.dataset.key);
    button.setAttribute('aria-pressed', String(on));
    button.classList.toggle('pop', placed !== null && button.dataset.key === key(placed));
    if (cost === undefined) { delete button.dataset.cost; delete button.dataset.heat; }
    else { button.dataset.cost = cost; button.dataset.heat = cost >= 4 ? 3 : cost >= 2 ? 2 : 1; }
    const [x, y] = button.dataset.key.split(',');
    button.setAttribute('aria-label', on ? `Point (${x}, ${y}), placed`
      : cost === undefined ? `Point (${x}, ${y})` : `Point (${x}, ${y}), adds ${cost} ${cost === 1 ? 'distance' : 'distances'}`);
  });

  const left = level.count - n;
  if (bot) { /* the bot writes its own status */ }
  else if (n === 0 && level.free) setStatus('Place as many points as you like. The proven minimum updates with every point.');
  else if (n === 0) setStatus(`Place ${level.count} points. No arrangement on this board uses fewer than <strong>${level.target}</strong> distances. Find one that uses exactly ${level.target}.`);
  else if (n === 1) setStatus('One point, no distances yet. The numbers on the board show how many new distances each next point would add.');
  else if (shown === 'bot' && full) setStatus(atMinimum ? `Local search found a ${d}-distance board, the proven minimum.` : `Local search ended here with <strong>${d} distances</strong>, ${over} over the minimum. Move a point and finish the job.`);
  else if (shown && full) setStatus(`This arrangement uses ${d} distances${atMinimum ? ', the proven minimum' : ''}. Move a point and watch which lengths appear.`, false);
  else if (done && level.free) setStatus(`<strong>${n} points, ${d} distances.</strong> Nothing on this board does better with ${n} points. Add another and try to stay level.`, true);
  else if (done) setStatus(`<strong>${n} points, ${d} distances. That is optimal.</strong> ${winLine()}`, true);
  else if (full) setStatus(`All ${n} points placed with ${d} distances, <strong>${over} over</strong> the minimum. Remove a point that creates lonely lengths (short bars) and try another spot.`);
  else if (level.free) setStatus(over === 0 ? `Level with the proven minimum for ${n} points.` : `${over} over the proven minimum for ${n} points.`);
  else if (over === 0) setStatus(`${left} to go. You are level with the best possible ${n}-point arrangement, though not every such arrangement can be finished in ${level.target}.`);
  else setStatus(`${left} to go. You already have ${d} distances; the target for all ${level.count} points is ${level.target}${d > level.target ? ', so something has to move' : ''}.`);

  const canPost = done && !shown && !bot;
  $('win-actions').hidden = !canPost;
  $('next').hidden = level.free || level === levels.at(-1);

  $('distances').replaceChildren();
  const tallest = Math.max(1, ...[...groups.values()].map(pairs => pairs.length));
  for (const [distance, pairs] of groups) {
    const chip = document.createElement('button'); chip.type = 'button'; chip.className = 'distance-chip';
    chip.classList.toggle('fresh', placed !== null && freshDistances.has(distance));
    const bar = document.createElement('i'); bar.style.height = `${4 + 34 * pairs.length / tallest}px`;
    chip.append(bar, document.createTextNode(distance)); chip.dataset.distance = distance;
    chip.setAttribute('aria-label', `Squared length ${distance}, ${pairs.length} pairs`);
    chip.setAttribute('aria-pressed', 'false');
    chip.addEventListener('pointerenter', () => { hoveredDistance = distance; drawLines(); });
    chip.addEventListener('pointerleave', () => { hoveredDistance = null; drawLines(); });
    chip.addEventListener('focus', () => { hoveredDistance = distance; drawLines(); });
    chip.addEventListener('blur', () => { hoveredDistance = null; drawLines(); });
    chip.addEventListener('click', () => { selectedDistance = selectedDistance === distance ? null : distance; hoveredDistance = null; drawLines(); });
    $('distances').append(chip);
  }
  const condition = checkFourPointCondition(points);
  $('validity').textContent = n < 4 ? ''
    : `Your current board passes a direct check of all ${condition.checked.toLocaleString()} of its four-point subsets.`;
  drawLines(); renderLevelTabs(); renderMachines();
}

function winLine() {
  const [hits] = level.search.plain;
  return `Plain local search gets here in ${hits} of 200 runs.`;
}

function renderLevelTabs() {
  document.querySelectorAll('.level').forEach((button, i) => {
    const item = levels[i];
    button.setAttribute('aria-current', String(item ? item === level : !!level.free));
    if (item) button.querySelector('b').textContent = solved.has(item.id) ? '✓' : String(i + 1).padStart(2, '0');
  });
}

function renderMachines() {
  $('machines').hidden = !!level.free;
  if (level.free) return;
  const { random, swap, plain } = level.search, mine = yourBest.get(level.id);
  const rows = [
    ['Random sampling', `typical <b>${random[1]}</b> · best ${random[0]}`],
    ['Local search, with restarts', `typical <b>${swap[1]}</b> · best ${swap[0]}`],
    ['Local search, plain (watch it below)', `typical <b>${plain[1]}</b> · optimal in ${plain[0]} of 200 runs`],
    ['Exhaustive proof', `<b>${level.target}</b> is the minimum · ${level.proof.toLocaleString()} nodes`],
    ['You', mine === undefined ? '—' : `<b>${mine}</b>${mine === level.target ? ' · optimal' : ''}`],
  ];
  $('machine-rows').replaceChildren(...rows.map(([name, value], i) => {
    const tr = document.createElement('tr'), a = document.createElement('td'), b = document.createElement('td');
    if (i === rows.length - 1) tr.className = 'you';
    a.textContent = name; b.innerHTML = value; tr.append(a, b); return tr;
  }));
}

function selectLevel(next, nextPoints = []) {
  stopBot();
  level = next; points = validatePoints(nextPoints, level); history = []; shown = false; flash = null;
  selectedDistance = null; hoveredDistance = null; freshDistances = new Set();
  $('board-label').textContent = `${level.size} × ${level.size} grid, rows stretched by √2`;
  $('challenge-number').textContent = level.free ? 'FREE PLAY' : `BOARD ${String(levels.indexOf(level) + 1).padStart(2, '0')}`;
  $('challenge-title').textContent = level.name;
  $('objective').textContent = level.free
    ? 'Any number of points. The minimum is proven for every count on every board here.'
    : `${level.count} points, ${level.target} distances. Proven to be the fewest possible on this board.`;
  $('size-picker').hidden = !level.free;
  document.querySelectorAll('#size-picker button').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.size) === level.size)));
  document.querySelector('.hint').hidden = !!level.free; $('baseline').hidden = !!level.free;
  if (!level.free) { $('hint-text').textContent = level.hint; $('certificate-link').href = sourceRoot + level.source; }
  else $('certificate-link').href = `${sourceRoot}results/2026-11-16-exact/frontier-${level.size}x${level.size}.json`;
  $('action-message').textContent = ''; $('bot-message').textContent = ''; $('input-error').textContent = ''; $('coordinates').value = '';
  $('share-fallback').hidden = true;
  buildBoard(); render();
}

// Watch plain local search: random start, move one point at a time, never accept a worse board.
function stopBot() {
  if (!bot) return;
  cancelAnimationFrame(bot.frame); bot = null;
  $('bot').textContent = '▶ Watch local search try';
}

function runBot() {
  if (bot) { const score = bot.score; stopBot(); $('bot-message').textContent = `Stopped at ${score} distances.`; render(); updateURL(); return; }
  history.push({ points: points.map(p => [...p]), shown });
  const random = randomSource(Date.now());
  bot = { random, tries: 0, score: null, frame: 0 };
  points = randomPoints(level, random); shown = 'bot'; flash = null;
  $('bot').textContent = '■ Stop'; $('win-actions').hidden = true;
  const perFrame = matchMedia('(prefers-reduced-motion: reduce)').matches ? BOT_BUDGET : 6;
  const tick = () => {
    for (let i = 0; i < perFrame && bot.tries < BOT_BUDGET; i++) {
      const step = swapStep(points, level.size, random);
      points = step.points; bot.score = step.score; bot.tries++;
      if (step.score === level.target) break;
    }
    render();
    const hit = bot.score === level.target, spent = bot.tries >= BOT_BUDGET;
    setStatus(`Local search: <strong>${bot.score} distances</strong> after ${bot.tries.toLocaleString()} of ${BOT_BUDGET.toLocaleString()} tries. Minimum: ${level.target}.`);
    if (hit || spent) {
      const tries = bot.tries, score = bot.score; stopBot();
      $('bot-message').textContent = hit
        ? `Found the minimum in ${tries.toLocaleString()} tries this time. Over 200 recorded runs it managed that ${level.search.plain[0]} times.`
        : `Stopped at ${score} after ${BOT_BUDGET.toLocaleString()} tries, ${score - level.target} over the minimum. Can you fix its board?`;
      render(); updateURL();
    } else bot.frame = requestAnimationFrame(tick);
  };
  tick();
}

async function copyText(text, message) {
  try { await navigator.clipboard.writeText(text); $('action-message').textContent = message; }
  catch {
    $('share-fallback').hidden = false; $('share-url').value = text; $('share-url').focus(); $('share-url').select();
    $('action-message').textContent = 'Copy the selected text below.';
  }
}

// A result link opens the board empty, so sharing a score does not spoil the answer.
const resultUrl = () => siteUrl + encodeState(level, []).replace(/&?points=$/, '');

levels.forEach((item, i) => {
  const button = document.createElement('button'); button.type = 'button'; button.className = 'level';
  const number = document.createElement('b'), label = document.createElement('span'), small = document.createElement('small');
  number.textContent = String(i + 1).padStart(2, '0'); label.textContent = item.name;
  small.textContent = `${item.count} points · ${item.target} distances`;
  label.append(small); button.append(number, label);
  button.addEventListener('click', () => { if (level !== item) { selectLevel(item); updateURL(); } });
  $('levels').append(button);
});
{
  const button = document.createElement('button'); button.type = 'button'; button.className = 'level';
  const number = document.createElement('b'), label = document.createElement('span'), small = document.createElement('small');
  number.textContent = '∞'; label.textContent = 'Free play'; small.textContent = 'any count · 4×4 to 7×7';
  label.append(small); button.append(number, label);
  button.addEventListener('click', () => { if (!level.free) { selectLevel(freeLevel(7)); updateURL(); } });
  $('levels').append(button);
}
for (const size of [4, 5, 6, 7]) {
  const button = document.createElement('button'); button.type = 'button'; button.dataset.size = size;
  button.textContent = `${size} × ${size}`;
  button.addEventListener('click', () => { selectLevel(freeLevel(size)); updateURL(); });
  $('size-picker').append(button);
}

$('costs').addEventListener('change', () => { remember.save(); render(); });
$('undo').addEventListener('click', () => {
  const previous = history.pop(); if (!previous) return;
  points = previous.points; shown = previous.shown; flash = null; $('action-message').textContent = ''; render(); updateURL();
});
$('reset').addEventListener('click', () => { changePoints([]); $('bot-message').textContent = ''; });
$('baseline').addEventListener('click', () => { stopBot(); changePoints(level.baseline, { show: true }); });
$('bot').addEventListener('click', runBot);
$('next').addEventListener('click', () => {
  const next = levels[levels.indexOf(level) + 1];
  if (next) { selectLevel(next); updateURL(); $('levels').scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
});
$('post').addEventListener('click', () => {
  const intent = new URL('https://twitter.com/intent/tweet');
  intent.searchParams.set('text', shareText(level, points)); intent.searchParams.set('url', resultUrl());
  window.open(intent.href, '_blank', 'noopener');
});
$('copy-result').addEventListener('click', () => copyText(`${shareText(level, points)}\n${resultUrl()}`, 'Result copied. The link opens this board empty, so it spoils nothing.'));
$('share').addEventListener('click', () => {
  const url = new URL(location.href); url.hash = encodeState(level, points);
  copyText(url.href, 'Board link copied. Anyone with the link sees these exact points.');
});
$('export').addEventListener('click', () => {
  try {
    const data = witness(level, points), blob = new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = 'witness.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('action-message').textContent = `Exported ${points.length} points and ${groups.size} distances. The verifier command is further down the page.`;
  } catch (error) { $('action-message').textContent = error.message; }
});
$('load-coordinates').addEventListener('click', () => {
  try { stopBot(); const valid = validatePoints(JSON.parse($('coordinates').value), level); changePoints(valid, { show: false }); $('input-error').textContent = `Loaded ${valid.length} points.`; }
  catch (error) { $('input-error').textContent = error instanceof SyntaxError ? 'Use valid JSON, such as [[0,0],[1,0]].' : error.message; }
});

// Why the grid is stretched: count rule-breaking quadruples for a few stretches.
const stretches = [
  { q: 1, label: '1 (square grid)' }, { q: 2, label: '√2' }, { q: 3, label: '√3' }, { q: 4, label: '2' },
];
let stretch = stretches[0], breakers = null, example = 0;

function drawStretch() {
  const size = 5, svg = $('stretch-board'), scale = Math.sqrt(stretch.q);
  const w = 300, h = 330, m = 18, unit = Math.min((w - 2 * m) / (size - 1), (h - 2 * m) / ((size - 1) * scale));
  const x0 = (w - unit * (size - 1)) / 2, y0 = (h + unit * (size - 1) * scale) / 2;
  const at = ([x, y]) => [x0 + x * unit, y0 - y * unit * scale];
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`); svg.replaceChildren();
  const four = breakers.found.length ? breakers.found[example % breakers.found.length] : [];
  if (four.length) {
    const shortest = Math.min(...four.flatMap((a, i) => four.slice(i + 1).map(b => squaredDistance(a, b, stretch.q))));
    four.forEach((a, i) => four.slice(i + 1).forEach(b => {
      const line = document.createElementNS(svgNS, 'line'), [x1, y1] = at(a), [x2, y2] = at(b);
      Object.entries({ x1, y1, x2, y2 }).forEach(([k, v]) => line.setAttribute(k, v));
      if (squaredDistance(a, b, stretch.q) !== shortest) line.setAttribute('class', 'second');
      svg.append(line);
    }));
  }
  const bad = new Set(four.map(key));
  for (let x = 0; x < size; x++) for (let y = 0; y < size; y++) {
    const dot = document.createElementNS(svgNS, 'circle'), [cx, cy] = at([x, y]);
    dot.setAttribute('cx', cx); dot.setAttribute('cy', cy); dot.setAttribute('r', bad.has(key([x, y])) ? 6 : 3.5);
    if (bad.has(key([x, y]))) dot.setAttribute('class', 'bad');
    svg.append(dot);
  }
  const total = breakers.total.toLocaleString(), count = breakers.found.length;
  $('stretch-result').innerHTML = count
    ? `<strong>${count} of the ${total} four-point sets</strong> on this 5 × 5 grid have only two distances (solid and dashed). Erdős’s rule forbids every one of them.`
    : `<strong>0 of ${total}.</strong> Every four points on this grid have at least three distances, so any board you build above is legal. And the squared lengths x² + 2y² still collide constantly.`;
  $('stretch-next').hidden = count < 2;
  document.querySelectorAll('#stretch-picker button').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.q) === stretch.q)));
}
for (const item of stretches) {
  const button = document.createElement('button'); button.type = 'button'; button.dataset.q = item.q;
  button.textContent = `× ${item.label}`;
  button.addEventListener('click', () => { stretch = item; breakers = ruleBreakers(5, item.q); example = 0; drawStretch(); });
  $('stretch-picker').append(button);
}
$('stretch-next').addEventListener('click', () => { example += 7; drawStretch(); });

function loadHash() {
  try {
    const state = decodeState(location.hash); selectLevel(state.level, state.points);
    // A complete board arriving by link is someone's answer, not a solve by this visitor.
    if (!state.level.free && state.points.length === state.level.count) { shown = 'reveal'; render(); }
  }
  catch (error) { selectLevel(levels[0]); $('action-message').textContent = `Could not load this board: ${error.message}`; }
}
remember.load();
window.addEventListener('hashchange', loadHash);
loadHash();
breakers = ruleBreakers(5, 1); drawStretch();
