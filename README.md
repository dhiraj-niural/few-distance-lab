# Few-distance lab

How few distances can a set of points have if every four points must determine at least three?

This project studies finite subsets of the stretched grid `(x, √2 y)`. Squared distances are integers, `dx² + 2dy²`, so every result can be checked without floating-point tolerances.

## Latest result · 15 November 2026

The equal-score component of the saved 20-point construction is now closed: **five connected configurations, all with 17 distances, and no improving one- or two-point exit**. Board reflections reduce the exhaustive check to three representatives and **233,160 scored neighbors**. Independent distance-set enumeration agrees; all 62 tests pass. This closes one local search route, not the global problem. [Plateau result and reproduction](docs/plateau.md).

## Two-point audit · 12 November 2026

An exact audit of **273,781 two-point replacements** found no improvements, but one genuinely different 20-point configuration with the same count of 17 distinct distances. Two other ties are translations. Together with the earlier single-point audit, this identifies local barriers and a shape-changing plateau move, without proving global optimality or an improving path. All 54 tests pass; an independent implementation agrees on every move score. [Two-point audit](docs/two-exchange.md) · [Single-point audit](docs/one-exchange.md).

## Construction baseline · 8 November 2026

A compact-row construction beat the swap search's median on all seven new 6×6/7×7 instances, evaluating only 5–84 configurations versus 2,000 per swap run. It beat the best observed swap run on three instances and tied it on four. All 289 saved certificates pass both exact validators. This is a conventional geometric baseline, with no AI advantage or unrestricted optimum claimed. [Comparison and reproduction](docs/compact-rows.md).

## First results · 6 November 2026

- Exhaustively enumerated **65,221 subsets** across 3×3 and 4×4 grids, establishing 19 restricted-domain optima.
- Compared uniform random sampling with restarted single-point swaps: **140 trials, 200,000 candidate evaluations**.
- For 12 points on a 5×5 grid, random sampling reached 13 distances at best; swaps reached 10. Ten-seed medians were also 13 and 10, at 2,000 evaluations per run.
- Saved **162 certificates**, checked by independent integer and rational implementations. Full-grid audits establish that every subset in these finite domains satisfies the four-point condition.

These are reproducible finite experiments, not new global bounds or evidence of an AI-search advantage. [Full results and limitations](docs/results.md).

## Run

Python 3.9 or later. Standard library only. Run from the repository root:

```sh
python3 -m unittest discover -v
python3 -m few_distance verify results/2026-11-06/certificates/exact-4x4-n8.json
python3 -m few_distance search --width 5 --height 5 --points 12 --method swap --budget 2000 --seed 0
python3 -m few_distance study --output results/reproduction
```

Use an empty destination for each study. Seeds and candidate counts are reproducible; timestamps and elapsed times are not. The initial run used Python 3.9.6. No model calls, network access or external compute are required by the experiment.

## Inspect

- [Mathematical question and certificate format](docs/mathematics.md)
- [Recorded study](results/2026-11-06/study.json) and [individual trials](results/2026-11-06/trials.csv)
- `few_distance/checker.py`: exact integer verification, independent of search
- `few_distance/independent.py`: rational verification and a separate exhaustive oracle
- `few_distance/search.py`: exhaustive enumeration, random and swap baselines

## Research context

The stretched-lattice construction comes from existing mathematics. The immediate starting point is Benjamin Grayzel's [paper on Erdős problem #659](https://arxiv.org/abs/2601.09102v2), January 2026. Earlier lattice work includes [Moree and Osburn](https://arxiv.org/abs/math/0604163). This repository explores small finite instances of that construction.

The tested 20-point plateau cannot escape through non-increasing one- or two-point moves. Controlled worsening or larger coordinated moves are possible next research directions, not demonstrated improvements. A numerical pattern would be a conjecture to investigate, not a proof.
