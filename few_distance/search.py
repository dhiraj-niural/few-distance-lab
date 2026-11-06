"""Bounded, exact-integer search on the rectangular q=2 lattice.

Coordinates are integer indices; their physical interpretation is (x, sqrt(2)y).
The search objective counts distinct positive squared distances dx**2 + 2*dy**2.
This module does not certify the local four-point condition; use the independent
checker on every saved witness. Exhaustive optimality refers only to this grid.
"""

from itertools import combinations
from math import comb
from random import Random
from time import perf_counter


MAX_SITES = 64
# The system Python on some supported machines is 3.9.
_popcount = int.bit_count if hasattr(int, "bit_count") else lambda value: bin(value).count("1")


def _positive_integer(name, value):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _validate_grid(width, height, n):
    _positive_integer("width", width)
    _positive_integer("height", height)
    if width * height > MAX_SITES:
        raise ValueError(f"grid must contain at most {MAX_SITES} sites")
    if type(n) is not int or not 4 <= n <= width * height:
        raise ValueError("n must be an integer between 4 and the number of sites")


class _Objective:
    """Precompute a compressed distance bit for each pair of grid sites."""

    def __init__(self, width, height):
        # This order makes combinations, and hence exhaustive ties, lexicographic
        # in the returned coordinates as well as in site indices.
        self.points = tuple((x, y) for x in range(width) for y in range(height))
        size = len(self.points)
        self.bits = [[0] * size for _ in range(size)]
        distance_bits = {}
        for i, (x, y) in enumerate(self.points):
            for j in range(i):
                a, b = self.points[j]
                distance = (x - a) ** 2 + 2 * (y - b) ** 2
                if distance not in distance_bits:
                    distance_bits[distance] = 1 << len(distance_bits)
                self.bits[i][j] = self.bits[j][i] = distance_bits[distance]

    def count(self, selection):
        mask = 0
        for offset, i in enumerate(selection):
            row = self.bits[i]
            for j in selection[:offset]:
                mask |= row[j]
        return _popcount(mask)


def _result(width, height, objective, selection, score, search, started):
    search["elapsed_seconds"] = perf_counter() - started
    return {
        "schema_version": 1,
        "metric": {"q_num": 2, "q_den": 1},
        "grid": {"width": width, "height": height},
        "points": [list(objective.points[i]) for i in selection],
        "claimed_distance_count": score,
        "search": search,
    }


def exhaustive(width, height, n, max_evaluations=200000):
    """Enumerate every n-subset, or reject before evaluation if above the cap.

    ``minimizer_count`` includes all labelled placements, without quotienting
    symmetries. The returned witness is the first coordinate-lexicographic
    minimizer. ``domain_optimal`` never asserts a global geometric optimum.
    """
    started = perf_counter()
    _validate_grid(width, height, n)
    _positive_integer("max_evaluations", max_evaluations)
    domain_size = comb(width * height, n)
    if domain_size > max_evaluations:
        raise ValueError(
            f"exhaustive domain has {domain_size} subsets, exceeding "
            f"max_evaluations={max_evaluations}"
        )
    objective = _Objective(width, height)
    best = None
    best_score = None
    minimizer_count = 0
    evaluations = 0
    for selection in combinations(range(width * height), n):
        score = objective.count(selection)
        evaluations += 1
        if best_score is None or score < best_score:
            best, best_score = selection, score
            minimizer_count = 1
        elif score == best_score:
            minimizer_count += 1
    return _result(width, height, objective, best, best_score, {
        "method": "exhaustive",
        "seed": None,
        "budget": max_evaluations,
        "evaluations": evaluations,
        "complete": True,
        "domain_optimal": True,
        "domain_size": domain_size,
        "minimizer_count": minimizer_count,
        "symmetry_pruning": False,
        "termination": "domain_exhausted",
    }, started)


def baseline(width, height, n, method, seed, budget):
    """Spend exactly ``budget`` objective evaluations using random or swap.

    Random draws independent uniform n-subsets, with replacement between draws.
    Swap starts from one random draw, then proposes single-site replacements.
    Improvements are accepted; at most ``max(4,n)`` plateau moves are accepted
    between strict improvements/restarts. After ``max(16,4*n)`` proposals without
    a strict current-state improvement, the next evaluation is a random restart.
    For a full grid, every evaluation after initialization is a restart (there
    are no legal swaps). Repeated candidates still consume evaluations.

    ``complete`` means the requested budget was spent, never exhaustive coverage.
    Initialization and restarts each consume one objective evaluation. Equal
    best scores select the lexicographically smallest witness observed.
    """
    started = perf_counter()
    _validate_grid(width, height, n)
    if method not in ("random", "swap"):
        raise ValueError("method must be 'random' or 'swap'")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    _positive_integer("budget", budget)
    objective = _Objective(width, height)
    rng = Random(seed)
    sites = tuple(range(width * height))
    best = None
    best_score = None
    current = None
    current_score = None
    stagnation = 0
    plateau_used = 0
    plateau_limit = max(4, n)
    restart_after = max(16, 4 * n)
    draws = restarts = proposals = accepted = improving = plateaus = rejected = 0

    for _ in range(budget):
        restart = method == "swap" and current is not None and (
            stagnation >= restart_after or n == len(sites)
        )
        draw = method == "random" or current is None or restart
        if draw:
            candidate = tuple(sorted(rng.sample(sites, n)))
            draws += 1
            if restart:
                restarts += 1
        else:
            occupied = set(current)
            outside = [site for site in sites if site not in occupied]
            removed = rng.randrange(n)
            candidate_list = list(current)
            candidate_list[removed] = rng.choice(outside)
            candidate = tuple(sorted(candidate_list))
            proposals += 1
        score = objective.count(candidate)
        if best_score is None or (score, candidate) < (best_score, best):
            best, best_score = candidate, score

        if method == "swap":
            if draw:
                current, current_score = candidate, score
                stagnation = plateau_used = 0
            elif score < current_score:
                current, current_score = candidate, score
                accepted += 1
                improving += 1
                stagnation = plateau_used = 0
            else:
                stagnation += 1
                if score == current_score and plateau_used < plateau_limit:
                    current = candidate
                    plateau_used += 1
                    accepted += 1
                    plateaus += 1
                else:
                    rejected += 1

    search = {
        "method": method,
        "seed": seed,
        "budget": budget,
        "evaluations": budget,
        "complete": True,
        "domain_optimal": False,
        "domain_size": comb(len(sites), n),
        "termination": "budget_exhausted",
        "random_draws": draws,
        "restarts": restarts,
        "swap_proposals": proposals,
        "accepted_moves": accepted,
        "improving_moves": improving,
        "plateau_acceptances": plateaus,
        "rejected_moves": rejected,
    }
    if method == "swap":
        search.update(plateau_limit=plateau_limit, restart_after=restart_after)
    return _result(width, height, objective, best, best_score, search, started)
