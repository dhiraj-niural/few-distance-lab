# Geometry before more search

8 November 2026. A conventional construction baseline on seven new finite instances.

The initial experiment showed that local swaps outperform uniform random sampling. That left an obvious missing control: can a small geometric family do better without searching arbitrary point sets?

We tried full rows of equally spaced points, optionally followed by one shorter contiguous row. Enumerate row widths, the shorter row's offset, positive integer axis spacings and both orientations, subject to the bounding grid. Translation does not change distances, so anchor the configurations at the origin. Deduplicate before evaluating. This is a deliberately limited family, not a classification of all useful configurations.

The metric is `dx² + 2dy²`. Transposing a configuration can change its score, so both orientations are evaluated rather than treated as equivalent.

## Recorded comparison

Grid sizes and point counts, seeds100–109, methods and budgets were saved in [the protocol](protocols/compact-rows.json) before the batch. These larger grids were not part of the initial study. Each random/swap method received both a budget matching the construction family's candidate count and a separate 2,000-evaluation budget. We report all seeds. The construction is deterministic and runs once per instance, not ten fictitious independent repetitions.

Smaller distance counts are better. Best/median/worst describe ten stochastic runs; no unrestricted optima are known here.

| Grid | Points | Construction candidates | Construction score | Random, 2,000 evaluations: best / median / worst | Swap, 2,000 evaluations: best / median / worst |
|---|---:|---:|---:|---|---|
| 6×6 | 10 | 64 | 8 | 10 / 13 / 14 | 9 / 9 / 10 |
| 6×6 | 15 | 23 | 13 | 17 / 19 / 19 | 13 / 14 / 15 |
| 6×6 | 18 | 16 | 15 | 21 / 21 / 22 | 16 / 16 / 18 |
| 6×6 | 24 | 5 | 20 | 24 / 25 / 25 | 20 / 22 / 22 |
| 7×7 | 12 | 84 | 10 | 15 / 18 / 19 | 10 / 12 / 13 |
| 7×7 | 20 | 42 | 17 | 26 / 27 / 28 | 18 / 19 / 19 |
| 7×7 | 30 | 14 | 25 | 33 / 34.5 / 36 | 25 / 27.5 / 28 |

The construction beat the long-budget swap median on all seven instances. It strictly beat the best observed swap run on three and tied it on four. At matched candidate counts, it strictly beat every observed random and swap winner. These statements describe this batch, not population-wide superiority or a statistical significance claim.

For example, ten points on the 6×6 grid need only eight distances in the saved construction. None of the ten swap runs found that score within2,000 evaluations. The configuration is an exactly checkable witness, not proof that eight is the domain or global minimum.

## Why that ten-point witness works

The winner is two vertical columns: `(0,j)` and `(4,j)` for `j=0,…,4`. Remember that index coordinates represent physical points `(x,√2 y)`. Within a column the squared distances are `{2,8,18,32}`. Between columns they are `{16,18,24,34,48}`. Both sets contain18, leaving eight distinct values in their union.

More generally, two columns spaced `a` apart with `b` equally spaced points each have

```text
D(a,b) = 2b − 1 − C(a,b)
C(a,b) = number of integer pairs (r,s) satisfying
         a² = 2(s² − r²), 0 ≤ r < b, 1 ≤ s < b.
```

This follows by counting the union of `{2s²:1≤s<b}` and `{a²+2r²:0≤r<b}`. Each set has no duplicates internally, so each solution subtracts exactly one shared value. With `a=4,b=5`, the sole overlap is `(r,s)=(1,3)`: `16=2(9−1)`, giving `9−1=8` distances. An independent direct-distance check agreed for all132 cases `a=1,…,12`, `b=2,…,12`.

This elementary counting identity explains the observed witness; it is not presented as a new formula or a solution to the unrestricted problem. It suggests a concrete direction for future search: choose spacings that create more repeated squared distances, rather than merely moving points at random.

## Verification and limits

All 287 winners and both full-domain grids pass independent integer and rational checkers: **289 certificates**. Full-domain audits cover 58,905 quadruples for 6×6 and 211,876 for 7×7. Their subsets inherit the checked four-point condition. The batch contains seven deterministic construction runs and 280 stochastic trials, totaling 285,208 candidate evaluations.

Every distinct member of each defined construction family is evaluated once. Family optimality is distinct from optimality over all grid subsets. Stochastic initialization, restarts and repeated candidates all consume evaluations. Candidate equality does not imply equal runtime: construction enumeration and search setup have different costs, and certificate verification occurs afterward. Per-run search timing and total batch timing are recorded, without a speed guarantee.

The family was chosen after seeing the initial small-grid results, and this is one prespecified exploratory batch. There is no tuned AI method or unbiased estimate of AI's contribution. No model calls, external compute, new mathematical formula or novelty claim. The known stretched-lattice construction remains attributed in [the mathematics note](mathematics.md).

The practical result is a stronger baseline: a future model-designed search rule should compete against compact constructions as well as random sampling and swaps. A useful next question is whether local improvement from these structured starting points adds anything. The later [one-exchange audit](one-exchange.md) checks the immediate neighborhood of each saved winner; the 8 November batch itself did not run that follow-up.

## Reproduce

```sh
python3 -m unittest discover -v
python3 -m few_distance.construction_study --output results/compact-reproduction
python3 -m few_distance verify results/2026-11-08-compact-rows/certificates/compact-6-n10.json
```

Use an empty output directory. [Manifest and summaries](../results/2026-11-08-compact-rows/study.json), [all trials](../results/2026-11-08-compact-rows/trials.csv), source hashes and exact winner coordinates are saved. Seeds and candidate counts reproduce; timestamps and timings vary.
