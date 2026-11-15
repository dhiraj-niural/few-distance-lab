# Does walking sideways escape the local minimum?

15 November 2026. Continuation of the [two-point audit](two-exchange.md), using the same saved 20-point construction in the 7×7 stretched grid. Every point has physical coordinates `(x, √2 y)` and squared distances `dx² + 2dy²`.

The original rectangle has 17 distinct distances. Replacing two corner points gives a different shape with the same score. The question is whether repeatedly accepting these ties eventually exposes a move to fewer distances.

## Result

**No. The connected equal-score component contains five coordinate configurations, all with 17 distances. Every one- and two-point neighbor of every configuration has at least 17 distances.**

The component is a path:

```text
A0 <-> B0 <-> A1 <-> B1 <-> A2
17     17     17     17     17 distances
```

Let `X = {0,2,4,6}`. For t = 0, 1, 2, `At = X × {t,t+1,t+2,t+3,t+4}`. For t = 0, 1, `Bt` removes `(0,t),(6,t)` from `At` and adds `(2,t+5),(4,t+5)`. Each arrow is one exact two-point exchange. `Bt` connects to `A(t+1)` by replacing `(2,t),(4,t)` with `(0,t+5),(6,t+5)`.

These are three vertical placements of the rectangle and two placements of the offset shape. No additional equal-score neighbor leaves this path. This is a finite, computer-verified closure result for this starting construction and move rule, not global optimality or mathematical novelty.

## Why symmetry fits the existing budget

The board reflections `(x,y) -> (6-x,y)` and `(x,y) -> (x,6-y)` preserve the grid, squared distances and one-/two-point exchanges. They therefore map an entire state's scored neighborhood bijectively to the reflected state's neighborhood. Swapping x and y is deliberately excluded: the metric weights the axes differently.

Taking the lexicographically smallest reflected coordinate tuple identifies three equivalence classes: `{A0,A2}`, `{B0,B1}`, and `{A1}`. Exhaustively scanning one representative per class is sufficient to test every possible improving exit. Every equal target must map to a scanned class before closure is reported. An independent implementation additionally lifts the equal edges to raw coordinates and confirms all five configurations are connected to the original seed; orbit membership alone would not prove connectivity.

Each representative has `20×29 = 580` one-point neighbors and `C(20,2)×C(29,2) = 77,140` exact two-point neighbors. The run scores **233,160** candidates across three representatives, within the frozen 300,000-candidate, three-state, 60-second bounds. Those neighborhoods represent 388,600 raw-state candidates by symmetry; **388,600 is not the number executed**. Original-score and certificate validation work is accounted separately.

The previous raw-coordinate pass used the same 233,160 evaluations but left a fourth state pending. This run completes the conclusion by removing symmetry duplication, without increasing the search budget. The earlier partial artifact remains unchanged.

## Baseline and implication

A strictly improving search scans the initial 77,720 neighbors and stops immediately. Allowing ties explores a different shape but does not improve its best score. The added work establishes a stronger negative result; it is not a performance win for optimization.

For this fixed grid and starting set, any path to fewer than 17 distances must either accept a temporary increase in distance count or include a move replacing at least three points at once. This says nothing about larger grids, other starting constructions or arbitrary planar point sets. No LLM proposals, paid compute or AI-search advantage were tested.

## Reproduce and inspect

Run from the repository root with an empty output directory:

```sh
python3 -m unittest discover -v
python3 -m few_distance.plateau --output results/plateau-reproduction --protocol docs/protocols/plateau.json
```

The [frozen protocol](protocols/plateau.json) binds the source and input hashes. The [manifest](../results/2026-11-15-plateau/study.json) records representative coordinates, all equal edges, per-neighborhood counts, score histograms, move-stream hashes, cap status and exact certificates. A complete flag requires all admitted neighborhoods scanned and no unadmitted equal target. Finding an improvement or reaching a bound is reported separately from component closure.

The independent audit uses direct Python distance sets without importing production search code, compares scored-neighborhood histograms and every equal edge, and reconstructs the raw connected component. Certificates are also checked by the project's separate integer and rational validators.
