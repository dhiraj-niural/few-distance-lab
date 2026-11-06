# Few-distance lab

How few distances can a set of points have if every four points must determine at least three?

This project studies finite subsets of the stretched grid `(x, √2 y)`. Squared distances are integers, `dx² + 2dy²`, so every result can be checked without floating-point tolerances.

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

The next research question is whether a proposed construction or search procedure can outperform these baselines on fresh instances under the same candidate budget. A numerical pattern would be a conjecture to investigate, not a proof.
