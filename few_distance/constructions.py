"""Deterministic compact-row candidates on the q=2 integer-index lattice.

This is a restricted construction family, not exhaustive search of the grid.
The independent certificate validators remain responsible for certification.
"""

from math import comb
from time import perf_counter

from .search import _Objective, _result, _validate_grid


def compact_row_candidates(width, height, n):
    """Return every distinct feasible member of the anchored row family.

    For each 1 <= c <= n, use n // c full, contiguous c-column rows,
    then a final contiguous row of n % c points if needed. The partial row
    starts at each offset from zero through c - (n % c). Include each shape
    and its transpose, with every positive integer x/y spacing fitting the
    grid. Coordinates have minimum x and y zero: translations are omitted.
    Reflection of the row order is not an additional family operation.

    A spacing on an unused axis produces no new coordinates and is represented
    once. Deduplicate identical coordinate sets across all parameter choices.
    Return sorted immutable candidates, each containing sorted coordinates.
    Bounds and point counts follow the search module's <=64-site limits.
    """
    _validate_grid(width, height, n)
    candidates = set()
    for columns in range(1, n + 1):
        full_rows, remainder = divmod(n, columns)
        full = [(x, y) for y in range(full_rows) for x in range(columns)]
        offsets = range(columns - remainder + 1) if remainder else (0,)
        for offset in offsets:
            shape = full + [(offset + x, full_rows) for x in range(remainder)]
            for transpose in (False, True):
                oriented = [(y, x) if transpose else (x, y) for x, y in shape]
                span_x = max(x for x, _ in oriented)
                span_y = max(y for _, y in oriented)
                max_step_x = (width - 1) // span_x if span_x else 1
                max_step_y = (height - 1) // span_y if span_y else 1
                for step_x in range(1, max_step_x + 1):
                    for step_y in range(1, max_step_y + 1):
                        candidates.add(tuple(sorted(
                            (x * step_x, y * step_y) for x, y in oriented
                        )))
    return tuple(sorted(candidates))


def compact_row_baseline(width, height, n):
    """Evaluate the complete compact-row family once per distinct candidate.

    Ties select the lexicographically first configuration. ``family_optimal``
    refers only to this documented family, never all subsets of the grid or
    unrestricted planar point sets. Geometry and objective use exact integers;
    elapsed_seconds is descriptive wall-clock metadata only.
    """
    started = perf_counter()
    candidates = compact_row_candidates(width, height, n)
    objective = _Objective(width, height)
    best = best_score = None
    for candidate in candidates:
        selection = tuple(x * height + y for x, y in candidate)
        score = objective.count(selection)
        if best_score is None or score < best_score:
            best, best_score = selection, score
    return _result(width, height, objective, best, best_score, {
        "method": "compact_rows",
        "seed": None,
        "budget": len(candidates),
        "evaluations": len(candidates),
        "complete": True,
        "domain_optimal": False,
        "domain_size": comb(width * height, n),
        "family_optimal": True,
        "family_size": len(candidates),
        "translation_policy": "minimum_x_and_y_zero",
        "termination": "family_exhausted",
    }, started)
