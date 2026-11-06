"""Independent, exact verification of rectangular-lattice certificates.

The point (x, y) denotes physical coordinates (x, sqrt(q) * y).  Integer
numerators over the common reduced denominator of q suffice to compare every
squared distance exactly.  No search implementation is imported here.
"""

from fractions import Fraction
from itertools import combinations


MAX_POINTS = 100
MAX_INTEGER_BITS = 256


def verify_certificate(doc: dict) -> dict:
    """Validate schema v1 and every four-point subset, without tolerances.

    Unknown metadata is ignored. Core containers must have JSON types and core
    integers must be actual ints (never bools). Coordinates are zero-based and
    must lie in [0, width) x [0, height). Integers are limited to 256 bits and
    certificates to 100 points to bound arithmetic and enumeration work.

    ``violating_quadruple`` contains zero-based point indices, or None. All
    quadruples are checked even if a violation is found; the first violation in
    lexicographic index order is returned. Malformed core input is rejected
    before geometry, with ``distance_count=None`` and zero checked quadruples.
    """
    result = {
        "valid": False,
        "errors": [],
        "distance_count": None,
        "squared_distances": [],
        "checked_quadruples": 0,
        "violating_quadruple": None,
    }
    errors = result["errors"]

    def integer(value, label, positive=False):
        if type(value) is not int:
            errors.append(f"{label} must be an integer (not bool or float)")
            return False
        if value.bit_length() > MAX_INTEGER_BITS:
            errors.append(f"{label} exceeds {MAX_INTEGER_BITS}-bit limit")
            return False
        if positive and value <= 0:
            errors.append(f"{label} must be positive")
            return False
        return True

    if type(doc) is not dict:
        errors.append("certificate must be a JSON object")
        return result
    version = doc.get("schema_version")
    if type(version) is not int or version != 1:
        errors.append("schema_version must be integer 1")
    metric = doc.get("metric")
    if type(metric) is not dict:
        errors.append("metric must be an object")
    else:
        integer(metric.get("q_num"), "metric.q_num", positive=True)
        integer(metric.get("q_den"), "metric.q_den", positive=True)
    grid = doc.get("grid")
    grid_ok = type(grid) is dict
    if not grid_ok:
        errors.append("grid must be an object")
    else:
        width_ok = integer(grid.get("width"), "grid.width", positive=True)
        height_ok = integer(grid.get("height"), "grid.height", positive=True)
        grid_ok = width_ok and height_ok
    if "claimed_distance_count" in doc:
        integer(doc["claimed_distance_count"], "claimed_distance_count", positive=True)
    points = doc.get("points")
    if type(points) is not list:
        errors.append("points must be an array")
        return result
    if not 4 <= len(points) <= MAX_POINTS:
        errors.append(f"points must contain between 4 and {MAX_POINTS} entries")
        return result
    seen = set()
    for index, point in enumerate(points):
        label = f"points[{index}]"
        if type(point) is not list or len(point) != 2:
            errors.append(f"{label} must be an array of two integers")
            continue
        x_ok = integer(point[0], f"{label}[0]")
        y_ok = integer(point[1], f"{label}[1]")
        if not (x_ok and y_ok):
            continue
        x, y = point
        if grid_ok and not (0 <= x < grid["width"] and 0 <= y < grid["height"]):
            errors.append(f"{label} is outside the grid")
        if (x, y) in seen:
            errors.append(f"{label} duplicates an earlier point")
        seen.add((x, y))
    if errors:
        return result

    q = Fraction(metric["q_num"], metric["q_den"])
    count = len(points)
    distances = [[0] * count for _ in points]
    distinct = set()
    for i, j in combinations(range(count), 2):
        dx = points[i][0] - points[j][0]
        dy = points[i][1] - points[j][1]
        numerator = dx * dx * q.denominator + dy * dy * q.numerator
        distances[i][j] = numerator
        distinct.add(numerator)
    result["distance_count"] = len(distinct)
    result["squared_distances"] = [str(Fraction(d, q.denominator)) for d in sorted(distinct)]
    for a, b, c, d in combinations(range(count), 4):
        result["checked_quadruples"] += 1
        lengths = {distances[a][b], distances[a][c], distances[a][d],
                   distances[b][c], distances[b][d], distances[c][d]}
        if len(lengths) < 3 and result["violating_quadruple"] is None:
            result["violating_quadruple"] = [a, b, c, d]
    if result["violating_quadruple"] is not None:
        errors.append("a four-point subset has fewer than three distinct distances")
    if "claimed_distance_count" in doc and doc["claimed_distance_count"] != len(distinct):
        errors.append("claimed_distance_count does not match the exact distance count")
    result["valid"] = not errors
    return result
