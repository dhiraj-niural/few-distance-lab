"""Exact minima by branch and bound on the rectangular stretched grid.

For a bound B, decide whether some n-subset of the W x H grid determines at
most B distinct squared distances dx**2 + q*dy**2. Distance sets only grow as
points are added, so a partial selection that already exceeds B can be
discarded together with every completion. The search is exhaustive: a "none"
answer is a proof for this grid, metric and n, not a statement about the plane.

This module does not import the baseline search or either checker. Witnesses
should still be passed through both checkers before they are saved.
"""

from time import perf_counter

MAX_SITES = 64
_popcount = int.bit_count if hasattr(int, "bit_count") else lambda value: bin(value).count("1")


def _check(width, height, n, q):
    for name, value in (("width", width), ("height", height), ("q", q)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if width * height > MAX_SITES:
        raise ValueError(f"grid must contain at most {MAX_SITES} sites")
    if type(n) is not int or not 2 <= n <= width * height:
        raise ValueError("n must be an integer between 2 and the number of sites")


def _pair_bits(width, height, q):
    """Column-major sites and one bit per distinct squared distance."""
    sites = [(x, y) for x in range(width) for y in range(height)]
    index = {}
    bits = []
    for ax, ay in sites:
        row = []
        for bx, by in sites:
            d = (ax - bx) ** 2 + q * (ay - by) ** 2
            row.append(0 if d == 0 else 1 << index.setdefault(d, len(index)))
        bits.append(row)
    return sites, bits


def find_within(width, height, n, bound, q=2, node_limit=None):
    """Return a witness with at most `bound` distances, or None if none exists.

    Forward checking: every remaining candidate carries the distance bits it
    would add; candidates that would exceed the bound are dropped, and a branch
    dies as soon as too few candidates remain.
    """
    _check(width, height, n, q)
    if type(bound) is not int or bound < 0:
        raise ValueError("bound must be a non-negative integer")
    sites, bits = _pair_bits(width, height, q)
    nodes = 0
    chosen = []

    def extend(mask, candidates):
        # candidates: list of (site, bits this site adds against all chosen)
        nonlocal nodes
        nodes += 1
        if node_limit is not None and nodes > node_limit:
            raise RuntimeError("node limit reached before the search finished")
        need = n - len(chosen)
        if need == 0:
            return True
        for position, (site, own) in enumerate(candidates):
            if len(candidates) - position < need:
                return False
            new_mask = mask | own
            row = bits[site]
            rest = []
            for other, other_bits in candidates[position + 1:]:
                merged = other_bits | row[other]
                if _popcount(new_mask | merged) <= bound:
                    rest.append((other, merged))
            if len(rest) < need - 1:
                continue
            chosen.append(site)
            if extend(new_mask, rest):
                return True
            chosen.pop()
        return False

    started = perf_counter()
    found = extend(0, [(site, 0) for site in range(len(sites))])
    result = {"found": found, "nodes": nodes, "elapsed_seconds": perf_counter() - started}
    if found:
        result["points"] = sorted([list(sites[s]) for s in chosen])
    return result


def minimum(width, height, n, q=2, start=1, node_limit=None):
    """Smallest distance count for n points, with a witness and the refutation size."""
    _check(width, height, n, q)
    bound, refuted_nodes = max(start, 1 if n > 1 else 0), 0
    while True:
        result = find_within(width, height, n, bound, q, node_limit)
        if result["found"]:
            return {
                "schema_version": 1,
                "metric": {"q_num": q, "q_den": 1},
                "grid": {"width": width, "height": height},
                "points": result["points"],
                "claimed_distance_count": bound,
                "search": {"method": "branch-and-bound", "refutation_nodes": refuted_nodes,
                           "witness_nodes": result["nodes"]},
            }
        refuted_nodes += result["nodes"]
        bound += 1


def frontier(width, height, q=2, node_limit=None):
    """Minimum for every n from 2 to the full grid; minima are monotone in n."""
    rows, start = [], 1
    for n in range(2, width * height + 1):
        row = minimum(width, height, n, q, start, node_limit)
        start = row["claimed_distance_count"]
        rows.append(row)
    return rows
