# Can two-point moves escape the barrier?

12 November 2026. Follow-up to the exact [single-point audit](one-exchange.md).

A single-point move worsens all seven saved compact constructions. This follow-up asks whether moving two points together escapes that barrier. The input coordinates and bounding grids are unchanged. This is a deterministic finite neighborhood audit, not an AI-generated search or a global optimization result.

## Counting the neighborhood

Choose two distinct occupied sites to remove and two distinct originally vacant sites to insert. For n points in a W×H grid there are exactly C(n,2) C(WH−n,2) neighbors. Each is unique because the set difference from the original determines both removed and added pairs. Returning an occupied point is excluded. These are exactly-two exchanges; conclusions about up to two exchanges also require the earlier single-point audit.

Squared distances are dx²+2dy². An exact bitset can represent the set of present integer distances: union is bitwise OR, and the number of distinct distances is the population count. For each removed pair, retain distances among the remaining points, then add distances from each inserted point to those retained points and the distance between the two inserted points. This evaluates the whole new configuration without floating-point tolerances.

## Interpretation

A lower-scoring neighbor would be a concrete improving construction. Equal scores permit a first plateau step; they do not establish a path to a later improvement. Distinct coordinates can also be congruent by translation or reflection, so a tie alone need not represent a genuinely different shape. The neighborhood is restricted to the same bounding grid and metric. No unrestricted-plane optimum, new theorem, or AI advantage follows.

## Results and reproduction

All **273,781** neighbors were checked: **zero improvements, three ties, 273,778 worse**.

| Grid | Points | Start distances | Neighbors | Best neighbor distances | Ties |
|---|---:|---:|---:|---:|---:|
| 6×6 | 10 | 8 | 14,625 | 8 | 1 |
| 6×6 | 15 | 13 | 22,050 | 14 | 0 |
| 6×6 | 18 | 15 | 23,409 | 21 | 0 |
| 6×6 | 24 | 20 | 18,216 | 21 | 0 |
| 7×7 | 12 | 10 | 43,956 | 10 | 1 |
| 7×7 | 20 | 17 | 77,140 | 17 | 1 |
| 7×7 | 30 | 25 | 74,385 | 26 | 0 |

Combining this with the single-point audit, four witnesses remain strict local minima under moves replacing up to two points. Three have equal-score two-point neighbors, so they are local minima without strictness under that larger neighborhood. This applies only to the fixed saved witnesses, not every construction tied in the earlier baseline.

## A different 20-point shape

Two ties simply translate the entire 10-point or 12-point witness upward by one grid index. They do not change its geometry.

The 20-point tie is different: remove (0,0) and (6,0), then insert (2,5) and (4,5). It still has 17 distinct distances. The original has squared distance 68 and lacks 50; the replacement has 50 and lacks 68. A Euclidean isometry preserves distances, so these configurations cannot be congruent. This is a genuinely different equal-score configuration in this audit, with no claim it is mathematically new.

A move accepting ties can therefore change the 20-point shape. We have not searched onward from it, so this does not establish an eventual improvement. The next useful test is whether traversing non-congruent equal-score configurations opens a route to fewer distances, compared with a fixed-budget conventional search. An AI proposal would still need to outperform that baseline.

## Verification

A separate implementation enumerated all neighbors using direct integer-distance set unions, without importing the production audit. Every move score, full histogram, minimum and deterministic move-stream SHA256 matched. The original seven and seven best-neighbor certificates passed both project validators; the reviewer also checked their pair distances and every quadruple independently. All 54 tests pass, including exhaustive small-grid subset oracles, cap/deadline preflight, empty neighborhoods, deterministic ordering and manifest/no-overwrite checks.

The [frozen protocol](protocols/two-exchange.json) binds the inputs and source hashes before execution. The [manifest](../results/2026-11-12-two-exchange/study.json) stores full histograms, certificate hashes and move-stream digests. Digests are compact reproduction checks, not a substitute for enumerating the full neighborhood. Production batch wall time was 0.981 seconds, with a 300,000-candidate and 60-second cap. Original-score and certificate checks are separate from candidate evaluations. No random seeds, model calls or paid compute were used.

```sh
python3 -m unittest discover -v
python3 -m few_distance.two_exchange --output results/two-exchange-reproduction --protocol docs/protocols/two-exchange.json
```

Run from the repository root using an empty output directory. The CLI uses a POSIX alarm; the library additionally checks a cooperative deadline. Python integer bitsets are exact; a population-count fallback supports Python 3.9. The older single-point module and its frozen protocol are unchanged.
