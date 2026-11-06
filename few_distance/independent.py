"""Independent certificate audit using rational squared distances.

This module deliberately does not import the search or primary checker. Its
small exhaustive oracle uses coordinate combinations and Python sets, rather
than the search implementation's distance masks. It verifies finite witnesses;
it cannot establish unrestricted planar optimality or mathematical novelty.
"""

from fractions import Fraction
from itertools import combinations

MAX_POINTS = 100
MAX_INTEGER_BITS = 256


def _integer(value, *, positive=False):
    return (
        type(value) is int
        and value.bit_length() <= MAX_INTEGER_BITS
        and (not positive or value > 0)
    )


def audit_certificate(doc):
    """Audit a parsed JSON certificate, returning errors rather than raising.

    Coordinates refer to points (x, sqrt(q) y), where q = q_num / q_den.
    Distances are computed as Fraction values independently of the primary
    checker's scaled integers. At most 100 points and 256-bit integers are
    accepted, bounding validation work.
    """
    report = {
        "valid": False,
        "errors": [],
        "distance_count": None,
        "checked_quadruples": 0,
    }
    errors = report["errors"]
    if type(doc) is not dict:
        errors.append("certificate must be a JSON object")
        return report
    if type(doc.get("schema_version")) is not int or doc["schema_version"] != 1:
        errors.append("schema_version must be integer 1")

    metric = doc.get("metric")
    if type(metric) is not dict or any(
        not _integer(metric.get(key), positive=True) for key in ("q_num", "q_den")
    ):
        errors.append("metric must contain positive integer q_num and q_den of at most 256 bits")
    grid = doc.get("grid")
    if type(grid) is not dict or any(
        not _integer(grid.get(key), positive=True) for key in ("width", "height")
    ):
        errors.append("grid must contain positive integer width and height of at most 256 bits")
    points = doc.get("points")
    if type(points) is not list or not 4 <= len(points) <= MAX_POINTS:
        errors.append("points must be a JSON array containing 4 through 100 points")
    elif any(
        type(point) is not list
        or len(point) != 2
        or not all(_integer(value) for value in point)
        for point in points
    ):
        errors.append("each point must be a JSON array of two integers of at most 256 bits")
    claimed = doc.get("claimed_distance_count")
    if "claimed_distance_count" in doc and (
        not _integer(claimed) or not 0 <= claimed <= MAX_POINTS * (MAX_POINTS - 1) // 2
    ):
        errors.append("claimed_distance_count must be an integer between 0 and 4950")
    if errors:
        return report

    coords = [tuple(point) for point in points]
    if len(set(coords)) != len(coords):
        errors.append("points must be distinct")
    if any(not (0 <= x < grid["width"] and 0 <= y < grid["height"]) for x, y in coords):
        errors.append("point outside grid bounds")
    if errors:
        return report

    stretch = Fraction(metric["q_num"], metric["q_den"])
    distances = {}
    for i, j in combinations(range(len(coords)), 2):
        x1, y1 = coords[i]
        x2, y2 = coords[j]
        distances[i, j] = Fraction((x1 - x2) ** 2) + stretch * (y1 - y2) ** 2
    report["distance_count"] = len(set(distances.values()))
    if "claimed_distance_count" in doc and claimed != report["distance_count"]:
        errors.append("claimed_distance_count does not match exact distance count")

    first_bad_quadruple = None
    for vertices in combinations(range(len(coords)), 4):
        report["checked_quadruples"] += 1
        if len({distances[i, j] for i, j in combinations(vertices, 2)}) < 3:
            if first_bad_quadruple is None:
                first_bad_quadruple = vertices
    if first_bad_quadruple is not None:
        errors.append("four-point subset has fewer than three distances")
        report["first_bad_quadruple_indices"] = list(first_bad_quadruple)
    report["valid"] = not errors
    return report


def independent_exhaustive(width, height, n):
    """Exhaust all n-subsets in a <=16-site grid, at the fixed stretch q=2.

    No symmetry quotient or heuristic pruning is used. Minimizer counts count
    actual coordinate subsets, including reflected and translated copies.
    The q=2 lattice theorem makes all distinct four-point subsets admissible;
    selected witnesses still require certificate audit before external claims.
    """
    if not all(_integer(value, positive=True) for value in (width, height, n)):
        raise ValueError("width, height and n must be positive integers of at most 256 bits")
    if width * height > 16 or not 4 <= n <= width * height:
        raise ValueError("require at most 16 grid sites and 4 <= n <= site count")
    sites = [(x, y) for x in range(width) for y in range(height)]
    best, multiplicity, witness, candidates = None, 0, None, 0
    for selected in combinations(sites, n):
        candidates += 1
        values = {
            (left[0] - right[0]) ** 2 + 2 * (left[1] - right[1]) ** 2
            for left, right in combinations(selected, 2)
        }
        score = len(values)
        if best is None or score < best:
            best, multiplicity, witness = score, 1, selected
        elif score == best:
            multiplicity += 1
    return {
        "width": width,
        "height": height,
        "n": n,
        "minimum_distances": best,
        "minimizer_count": multiplicity,
        "candidates": candidates,
        "points": [list(point) for point in witness],
        "scope": "all n-subsets of this finite grid at q=2",
    }
