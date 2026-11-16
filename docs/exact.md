# Proven minima · 16 November 2026

## Result

For every square board from 3×3 to 7×7 and every number of points, the minimum number of distinct distances is now known exactly. In particular:

| Board | Points | Minimum | Subsets | Nodes to rule out one fewer |
|---|---:|---:|---:|---:|
| 4×4 | 8 | 6 | 12,870 | 130 |
| 5×5 | 12 | 10 | 5,200,300 | 3,138 |
| 6×6 | 10 | 8 | 254,186,856 | 6,484 |
| 7×7 | 20 | 17 | 28,277,527,346,376 | 1,696,518 |

**No 20-point subset of the 7×7 board has 16 or fewer distances.** The saved 17-distance construction is optimal on that board. This settles what the [single-point](one-exchange.md), [two-point](two-exchange.md) and [plateau](plateau.md) audits approached locally: those showed no nearby improvement, this shows none anywhere on the board.

All minima: [minima.json](../results/2026-11-16-exact/minima.json). Witnesses and node counts per board: `results/2026-11-16-exact/frontier-NxN.json`.

## Method

Adding a point never removes a distance. So once a partial selection has more than B distances, no completion has B or fewer, and the whole branch can be dropped. The search keeps, for each remaining site, the distances it would add; sites that would exceed B are removed, and a branch ends when too few sites remain. A “none” answer means every n-subset was either visited or excluded by that monotone argument.

Two implementations:

- `few_distance/exact.py`: Python, column-major sites, arbitrary-precision bit sets.
- `tools/exact_bb.c`: C, row-major sites, 128-bit sets. It shares no code with the Python package.

They agree on every minimum for boards up to 6×6 and on the 7×7 board for 2–24 points. For 25–49 points on 7×7 only the C program was run (265 million nodes in total for that board; the Python run was not taken that far). A third, simpler C search without forward checking also returned “none” for 20 points and bound 16 after 54.5 million nodes; it is not kept in the repository. The Python result reproduces all 19 minima of the [first exhaustive study](results.md), which enumerated subsets without pruning. Every witness with at least four points passes both exact checkers.

## Search baselines on the game boards

2,000 evaluations per run. Smaller is better.

| Board | Points | Minimum | Random, median of 10 | Swap with restarts, median of 10 | Plain swap, median of 200 | Plain swap reaches minimum |
|---|---:|---:|---:|---:|---:|---:|
| 4×4 | 8 | 6 | 7 | 6 | 7 | 2 / 200 |
| 5×5 | 12 | 10 | 13 | 10 | 10 | 122 / 200 |
| 6×6 | 10 | 8 | 12 | 9 | 9 | 1 / 200 |
| 7×7 | 20 | 17 | 28 | 19 | 18 | 79 / 200 |

Random and restarting swap are the Python baselines in `few_distance/search.py`. Plain swap is the restart-free search animated on the web page (`web/math.mjs`, `tools/bot_study.mjs`): move one point, keep the move unless it adds distances. The methods are not tuned and budgets are not wall-clock equal; the table says how these particular searches behave, not what local search can do in general. [Raw numbers](../results/2026-11-16-exact/baselines.json).

## Reproduce

```sh
python3 -m few_distance exact --width 7 --height 7 --points 20      # about 20 s
cc -O2 -o /tmp/exact_bb tools/exact_bb.c
/tmp/exact_bb 7 7 20 16 2                                           # NONE, about 1.5 s
python3 tools/exact_study.py --c-binary /tmp/exact_bb --output results/reproduction-exact
node tools/bot_study.mjs
```

## Limits

These are minima over subsets of one finite, axis-aligned grid with stretch √2. They are not bounds for arbitrary planar point sets, and no new theorem is claimed. The search is an ordinary branch and bound; nothing here involves model-generated search. Node counts depend on site order and are not comparable across implementations as a measure of difficulty.
