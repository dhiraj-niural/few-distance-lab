// How often does the watchable in-browser local search reach the proven minimum?
// Seeds 0-199, at most 2,000 proposals each, stopping early at the minimum.
//   node tools/bot_study.mjs > results/reproduction-bot.json
import { levels, randomSource, randomPoints, swapStep, distanceCount } from '../web/math.mjs';

export function botStudy(level, seeds = 200, budget = 2000) {
  const scores = [];
  for (let seed = 0; seed < seeds; seed++) {
    const random = randomSource(seed);
    let points = randomPoints(level, random), score = distanceCount(points);
    for (let t = 0; t < budget && score !== level.target; t++) ({ points, score } = swapStep(points, level.size, random));
    scores.push(score);
  }
  scores.sort((a, b) => a - b);
  return { seeds, budget, hits: scores.filter(s => s === level.target).length, median: scores[seeds >> 1], worst: scores.at(-1) };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(JSON.stringify(Object.fromEntries(levels.map(l => [l.id, botStudy(l)])), null, 1));
}
