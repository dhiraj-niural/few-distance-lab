# A barrier for single-point search

12 November 2026. Exact neighborhoods of the seven saved compact constructions.

Can we improve the construction baseline just by moving one point? For these seven fixed witnesses, the answer is no: every legal single-point replacement increases the number of distances. This is an exhaustive finite check, not a statement about all configurations or the unrestricted plane.

## What was checked

Keep the same bounding grid and number of points. Remove one occupied site and insert one previously unoccupied site. A configuration with n points in a W×H grid has exactly n(WH−n) such neighbors. They are distinct: comparing a neighbor with the original uniquely identifies the removed and inserted sites. Returning the removed point to its old site is a no-op and is excluded.

We evaluated all 2,781 neighbors of the seven compact winners from the [8 November study](compact-rows.md). The metric remains the exact integer squared distance dx²+2dy². These witnesses were selected by the earlier construction study; this is a follow-up analysis of them, not a fresh held-out estimate of search performance.

| Grid | Points | Original distances | Neighbors | Fewest distances in any neighbor | Better / equal neighbors |
|---|---:|---:|---:|---:|---:|
| 6×6 | 10 | 8 | 260 | 9 | 0 / 0 |
| 6×6 | 15 | 13 | 315 | 14 | 0 / 0 |
| 6×6 | 18 | 15 | 324 | 22 | 0 / 0 |
| 6×6 | 24 | 20 | 288 | 22 | 0 / 0 |
| 7×7 | 12 | 10 | 444 | 11 | 0 / 0 |
| 7×7 | 20 | 17 | 580 | 18 | 0 / 0 |
| 7×7 | 30 | 25 | 570 | 27 | 0 / 0 |

Each fixed witness is therefore a **strict one-exchange local minimum**. In the 18-point example, even the best immediate neighbor introduces seven more distinct distances. The smallest increases are one in four of the cases.

## What this changes

A hill climber initialized at one of these exact witnesses and accepting only better or equal single-point replacements cannot move. Allowing plateau moves does not help at the first step because there are none. More proposals from the same state do not change that fact.

An improving path made of single-point replacements, if one exists, must first accept a worse score. Alternatively, a search can replace several points together or restart elsewhere. This does not show that any such method will find a better configuration; it identifies a necessary departure from monotone single-point refinement of these starts. The existing random-restart baseline is not claimed incapable of finding improvements globally.

This is a useful constraint for future model-designed search rules: suggest coordinated geometric changes or a justified way to cross a worse-scoring region, then compare against the construction baseline under a fixed budget. No model-generated method was tested here, and no paid model run was used.

## Verification and limits

A second implementation independently enumerated the same neighborhoods using direct pair-distance sets, without importing the audit or search code. Counts, minima and full score histograms agreed. The original and saved best-neighbor witnesses also pass both existing exact certificate validators. The earlier full-grid checks establish the four-point condition for every subset of these grids; the neighborhood audit is an objective/completeness check, not a new global lattice proof.

No grid-wide optimum, new general bound, AI-search advantage or mathematical novelty follows. Strict local optimality applies to the saved coordinates and bounding grids only, not to every tied member of the compact family or moves outside the grid.

## Reproduce

```sh
python3 -m unittest discover -v
python3 -m few_distance.neighborhood --output results/one-exchange-reproduction --protocol docs/protocols/one-exchange.json
```

Run from the repository root with an empty output directory. The CLI uses a POSIX alarm for its 60-second outer cap; the library also checks its deadline. The frozen protocol binds all seven input certificates and the audit/checker source hashes. It permits at most 10,000 neighbor evaluations; the recorded batch uses 2,781, plus seven original-score evaluations. No random seeds are needed because enumeration is deterministic.

The [recorded manifest](../results/2026-11-12-one-exchange/study.json) contains per-witness histograms, source/input/output hashes and both checker reports. The [move ledger](../results/2026-11-12-one-exchange/neighbors.csv) records every removed/added site and score. Original certificates remain in the previous study; seven new best-neighbor certificates are saved with this one. Recorded batch wall time was 0.738 seconds on the local machine; this is not a speed guarantee. All 49 tests passed, including a separate small-grid subset oracle and cap/input-validation checks.
