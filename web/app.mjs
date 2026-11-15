import { levels, key, distanceGroups, validatePoints, checkFourPointCondition, encodeState, decodeState, witness } from './math.mjs';

const $ = id => document.getElementById(id);
const sourceRoot = 'https://github.com/dhiraj-niural/few-distance-lab/blob/main/';
let level = levels[0], points = [], history = [], selectedDistance = null, hoveredDistance = null;
let groups = new Map(), revealed = false;
const completed = new Set();
const svgNS = 'http://www.w3.org/2000/svg';
const width = 420, pad = 43, usable = width - 2 * pad;
let height = usable * Math.SQRT2 + 2 * pad;

function position([x, y]) {
  const step = usable / (level.size - 1);
  return [pad + x * step, height - pad - y * step * Math.SQRT2];
}

function line(a, b, className) {
  const element = document.createElementNS(svgNS, 'line');
  const [x1,y1] = position(a), [x2,y2] = position(b);
  Object.entries({x1,y1,x2,y2,class:className}).forEach(([k,v]) => element.setAttribute(k,v));
  return element;
}

function drawLines() {
  const svg = $('lines');
  svg.replaceChildren();
  for (let n = 0; n < level.size; n++) {
    svg.append(line([n,0],[n,level.size-1],'grid-line'), line([0,n],[level.size-1,n],'grid-line'));
    const [x,y] = position([n,n]);
    for (const [tx,ty] of [[x,height-17],[20,y+3]]) {
      const label = document.createElementNS(svgNS,'text');
      label.setAttribute('x',tx); label.setAttribute('y',ty);
      label.setAttribute('class','axis-label'); label.textContent=n; svg.append(label);
    }
  }
  const distance = hoveredDistance ?? selectedDistance;
  const pairs = groups.get(distance) ?? [];
  const active = new Set();
  for (const [a,b] of pairs) {
    svg.append(line(points[a],points[b],'pair-line'));
    active.add(key(points[a])); active.add(key(points[b]));
  }
  document.querySelectorAll('.point').forEach(button => button.classList.toggle('in-pair',active.has(button.dataset.key)));
  document.querySelectorAll('.distance-chip').forEach(button => button.setAttribute('aria-pressed',String(Number(button.dataset.distance) === distance)));
  $('distance-detail').textContent = pairs.length
    ? `Squared length ${distance} · ${pairs.length} ${pairs.length === 1 ? 'pair shares' : 'pairs share'} this distance. Tap again to clear.`
    : points.length < 2 ? 'Place two points to make your first distance.' : 'Repeated lengths count once. More shared pairs can mean fewer distances.';
}

function buildBoard() {
  $('board').style.aspectRatio = `${width} / ${height}`;
  $('lines').setAttribute('viewBox', `0 0 ${width} ${height}`);
  $('grid-points').replaceChildren();
  for (let y = level.size - 1; y >= 0; y--) for (let x = 0; x < level.size; x++) {
    const p = [x,y], button = document.createElement('button');
    button.type = 'button'; button.className = 'point'; button.dataset.key = key(p);
    button.setAttribute('aria-label',`Point (${x}, ${y})`);
    button.setAttribute('aria-pressed','false'); button.tabIndex = x === 0 && y === 0 ? 0 : -1;
    const [px,py] = position(p);
    button.style.left = `${100*px/width}%`; button.style.top = `${100*py/height}%`;
    button.addEventListener('click', () => togglePoint(p));
    button.addEventListener('focus', () => {
      document.querySelectorAll('.point').forEach(b => b.tabIndex = b === button ? 0 : -1);
    });
    button.addEventListener('keydown', event => {
      const delta = { ArrowLeft:[-1,0], ArrowRight:[1,0], ArrowUp:[0,1], ArrowDown:[0,-1] }[event.key];
      if (!delta) return;
      event.preventDefault();
      const next = [Math.max(0,Math.min(level.size-1,x+delta[0])), Math.max(0,Math.min(level.size-1,y+delta[1]))];
      document.querySelector(`.point[data-key="${key(next)}"]`).focus();
    });
    $('grid-points').append(button);
  }
}

function updateURL() {
  window.history.replaceState(null, '', encodeState(level,points));
}

function changePoints(next, { baseline = false } = {}) {
  history.push({ points: points.map(p=>[...p]), revealed });
  points = validatePoints(next, level); revealed = baseline;
  $('action-message').textContent = ''; $('share-fallback').hidden = true;
  render(); updateURL();
}

function togglePoint(p) {
  const found = points.findIndex(q => key(p) === key(q));
  if (found >= 0) changePoints(points.filter((_,i)=>i !== found));
  else if (points.length < level.count) changePoints([...points,p]);
  else $('action-message').textContent = `All ${level.count} points are placed. Remove a point, then choose its new position.`;
}

function render() {
  groups = distanceGroups(points);
  if (!groups.has(selectedDistance)) selectedDistance = null;
  hoveredDistance = null;
  const complete = points.length === level.count, reached = complete && groups.size <= level.target;
  if (reached && !revealed) completed.add(level.id);
  $('point-count').replaceChildren(document.createTextNode(String(points.length)));
  const outOf = document.createElement('span'); outOf.textContent = `/ ${level.count}`; $('point-count').append(outOf);
  $('distance-count').textContent = groups.size;
  $('pair-count').textContent = `${points.length * (points.length - 1) / 2} pairs`;
  $('undo').disabled = !history.length; $('reset').disabled = !points.length;
  $('export').disabled = points.length < 4;
  const selected = new Set(points.map(key));
  document.querySelectorAll('.point').forEach(button => button.setAttribute('aria-pressed',String(selected.has(button.dataset.key))));
  const status = $('status'); status.classList.toggle('success',reached);
  if (!complete) status.textContent = `Place ${level.count-points.length} more ${level.count-points.length === 1 ? 'point' : 'points'}. Your goal: ${level.target} different distances with all ${level.count} points.`;
  else if (revealed) status.textContent = `Reference construction loaded: ${groups.size} distances. Try a change and see which repeated lengths disappear.`;
  else if (reached && level.proven) status.textContent = 'You found an optimal configuration for this board. Eight points, just six different distances.';
  else if (reached && groups.size < level.target) status.textContent = 'Below the saved target! Export this configuration and check it with the independent Python verifier. This alone is not a new global result.';
  else if (reached) status.textContent = `Target matched: ${level.count} points, ${groups.size} distances. Can you go lower? This project has not proved the minimum on this board.`;
  else status.textContent = `All points placed; ${groups.size-level.target} distances above the target. Try moving a point: remove it, then add it elsewhere.`;
  $('next').hidden = !reached || level === levels.at(-1);
  $('distances').replaceChildren();
  for (const [distance,pairs] of groups) {
    const chip = document.createElement('button'); chip.type = 'button'; chip.className = 'distance-chip';
    chip.textContent = distance; chip.dataset.distance = distance;
    chip.setAttribute('aria-label',`Squared length ${distance}, ${pairs.length} pairs`);
    chip.setAttribute('aria-pressed','false');
    chip.addEventListener('pointerenter',()=>{ hoveredDistance = distance; drawLines(); });
    chip.addEventListener('pointerleave',()=>{ hoveredDistance = null; drawLines(); });
    chip.addEventListener('focus',()=>{ hoveredDistance = distance; drawLines(); });
    chip.addEventListener('blur',()=>{ hoveredDistance = null; drawLines(); });
    chip.addEventListener('click',()=>{ selectedDistance = selectedDistance === distance ? null : distance; hoveredDistance = null; drawLines(); });
    $('distances').append(chip);
  }
  const condition = checkFourPointCondition(points);
  $('validity').textContent = points.length < 4 ? 'Place at least four points to check the rule on your selection.'
    : `Your current selection also passes a direct browser check of all ${condition.checked.toLocaleString()} four-point subsets.`;
  drawLines(); renderLevelTabs();
}

function renderLevelTabs() {
  // Keep focused navigation elements stable as the board changes.
  document.querySelectorAll('.level').forEach((button,i)=>{
    button.setAttribute('aria-current',String(levels[i] === level));
    button.querySelector('b').textContent = completed.has(levels[i].id) ? '✓' : String(i+1).padStart(2,'0');
  });
}

function selectLevel(next, nextPoints = []) {
  level = next; points = validatePoints(nextPoints,level); history = []; revealed = false;
  selectedDistance = null; hoveredDistance = null;
  $('board-label').textContent = `${level.size} × ${level.size} stretched grid`;
  $('challenge-number').textContent = `CHALLENGE ${String(levels.indexOf(level)+1).padStart(2,'0')}`;
  $('challenge-title').textContent = level.name;
  $('objective').textContent = `Place ${level.count} points using ${level.target} different distances. ${level.proven ? 'The proven minimum on this board.' : 'A known target; the minimum is unproved here.'}`;
  $('hint-text').textContent = level.hint;
  $('certificate-link').href = sourceRoot + level.source;
  $('action-message').textContent = ''; $('input-error').textContent = ''; $('coordinates').value = '';
  $('share-fallback').hidden = true;
  buildBoard(); render();
}

levels.forEach((item,i)=>{
  const button = document.createElement('button'); button.type='button'; button.className='level';
  const number=document.createElement('b'), label=document.createElement('span'), small=document.createElement('small');
  number.textContent=String(i+1).padStart(2,'0'); label.textContent=item.name; small.textContent=`${item.count} points · target ${item.target}`;
  label.append(small); button.append(number,label);
  button.addEventListener('click',()=>{ if (level !== item) { selectLevel(item); updateURL(); } });
  $('levels').append(button);
});
$('undo').addEventListener('click',()=>{
  const previous = history.pop(); if (!previous) return;
  points = previous.points; revealed = previous.revealed; $('action-message').textContent=''; render(); updateURL();
});
$('reset').addEventListener('click',()=>changePoints([]));
$('baseline').addEventListener('click',()=>changePoints(level.baseline,{baseline:true}));
$('next').addEventListener('click',()=>{ const next=levels[levels.indexOf(level)+1]; if(next){selectLevel(next);updateURL();$('challenge-title').scrollIntoView({block:'nearest'});} });
$('share').addEventListener('click',async()=>{
  const url = new URL(location.href); url.hash = encodeState(level,points);
  try { await navigator.clipboard.writeText(url.href); $('action-message').textContent = 'Board link copied. Anyone with the link can load these points.'; }
  catch { $('share-fallback').hidden=false; $('share-url').value=url.href; $('share-url').focus(); $('share-url').select(); $('action-message').textContent='Copy the selected link below.'; }
});
$('export').addEventListener('click',()=>{
  try {
    const data=witness(level,points), blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob), link=document.createElement('a'); link.href=url; link.download='witness.json'; link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('action-message').textContent=`Exported ${points.length} points and ${groups.size} distinct distances. See the verifier command below.`;
  } catch(error) { $('action-message').textContent=error.message; }
});
$('load-coordinates').addEventListener('click',()=>{
  try { const parsed=JSON.parse($('coordinates').value); const valid=validatePoints(parsed,level); changePoints(valid); $('input-error').textContent=`Loaded ${valid.length} points.`; }
  catch(error) { $('input-error').textContent=error instanceof SyntaxError ? 'Use valid JSON, such as [[0,0],[1,0]].' : error.message; }
});
function loadHash() {
  try { const state=decodeState(location.hash); selectLevel(state.level,state.points); }
  catch(error) { selectLevel(levels[0]); $('action-message').textContent=`Could not load this board: ${error.message}`; }
}
window.addEventListener('hashchange',loadHash);
loadHash();
