# Initial results · 6 November 2026

## Exhaustive reference

All n-subsets were enumerated, without symmetry pruning. The full domain grids pass both exact validators, so every enumerated subset is admissible. A separate direct-set exhaustive implementation reproduced all minima, minimizer counts and first witnesses.

| Grid | Points | Minimum distances | Minimizers | Subsets checked |
|---|---:|---:|---:|---:|
| 3×3 | 4 | 3 | 10 | 126 |
| 3×3 | 5 | 4 | 1 | 126 |
| 3×3 | 6 | 5 | 6 | 84 |
| 3×3 | 7 | 7 | 6 | 36 |
| 3×3 | 8 | 8 | 9 | 9 |
| 3×3 | 9 | 8 | 1 | 1 |
| 4×4 | 4 | 3 | 82 | 1,820 |
| 4×4 | 5 | 4 | 4 | 4,368 |
| 4×4 | 6 | 5 | 38 | 8,008 |
| 4×4 | 7 | 6 | 20 | 11,440 |
| 4×4 | 8 | 6 | 2 | 12,870 |
| 4×4 | 9 | 8 | 4 | 11,440 |
| 4×4 | 10 | 9 | 10 | 8,008 |
| 4×4 | 11 | 10 | 24 | 4,368 |
| 4×4 | 12 | 10 | 2 | 1,820 |
| 4×4 | 13 | 13 | 52 | 560 |
| 4×4 | 14 | 13 | 4 | 120 |
| 4×4 | 15 | 14 | 16 | 16 |
| 4×4 | 16 | 14 | 1 | 1 |

## Fixed-budget baselines

Seeds 0–9 per method and instance. Each 4×4 trial uses 1,000 candidate evaluations; each 5×5 trial uses 2,000. Smaller distance counts are better.

| Grid | Points | Method | Best | Median | Worst | Optimum hits / 10 |
|---|---:|---|---:|---:|---:|---|
| 4×4 | 6 | random | 5 | 5 | 5 | 10 |
| 4×4 | 6 | swap | 5 | 5 | 5 | 10 |
| 4×4 | 8 | random | 6 | 7 | 8 | 1 |
| 4×4 | 8 | swap | 6 | 6.5 | 7 | 5 |
| 4×4 | 10 | random | 9 | 9 | 10 | 7 |
| 4×4 | 10 | swap | 9 | 9 | 9 | 10 |
| 4×4 | 12 | random | 10 | 10.5 | 12 | 5 |
| 4×4 | 12 | swap | 10 | 10 | 11 | 8 |
| 5×5 | 8 | random | 7 | 8 | 9 | unknown optimum |
| 5×5 | 8 | swap | 6 | 7 | 7 | unknown optimum |
| 5×5 | 12 | random | 13 | 13 | 13 | unknown optimum |
| 5×5 | 12 | swap | 10 | 10 | 11 | unknown optimum |
| 5×5 | 16 | random | 16 | 16 | 17 | unknown optimum |
| 5×5 | 16 | swap | 14 | 14 | 15 | unknown optimum |

Random search draws uniform n-subsets, with replacement between draws. Swap search replaces one selected site at a time, accepts improvements and bounded plateau moves, and restarts after stagnation. Initialization, restarts and repeated candidates all consume evaluations. See the documented rule in `search.py`.

The most useful first signal is the 5×5, n=12 case: swap reached 10–11 distances across ten seeds, while random sampling reached 13 in every run. On the 4×4, n=8 calibration instance, swap found the proven domain optimum in 5/10 runs versus 1/10 for random sampling. This motivates testing stronger search rules, but does not establish general statistical superiority.

## Reproducibility and interpretation

This run used Python 3.9.6 and completed in 1.35 seconds on the local machine, including certificate checks. Timings are illustrative, hardware-dependent observations. Per-search timings include preprocessing but exclude subsequent verification.

The study records 19 exhaustive witnesses, 140 baseline winners and three full-domain certificates. Every certificate is checked twice. Source hashes, seeds, counts and per-run timings are saved alongside raw results. Equal evaluation budgets are not equal wall-clock budgets; the same seed label does not mean the methods see the same candidates.

No model-generated search arm, held-out model comparison, unrestricted geometric optimum or new mathematical discovery is claimed. The 5×5 optima have not been exhaustively established. Conventional structured constructions can already match some good witnesses, so a future AI-assisted method must also be compared against such constructions, not only random search.

## Next measurable test

Freeze these results. Compare a construction-guided search against the existing methods on a separate, prespecified set of larger instances and fixed budgets. Save every candidate winner for exact checking. Any model-authored heuristic must be evaluated separately from the cost and time used to produce it. Investigate a formula only after checking its predictions on additional sizes; finite agreement is not proof.
