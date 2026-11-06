# Question and exact verification

Choose n distinct points P from {0,…,W−1} × {0,…,H−1}. An index pair (x,y) represents the physical point (x,√q y), for positive rational q.

Minimize D(P), the number of distinct positive squared distances between pairs, subject to every four-point subset determining at least three distances. Positive lengths and their squares have the same equality relation. The implemented searches fix q=2.

## Why this grid?

The known √2-stretched lattice avoids all six configurations of four planar points with exactly two distances. The classification reduces the exclusions to an equilateral triangle, a square and a pentagon trapezoid. Grayzel's 2026 paper applies this construction to Erdős #659; it is not a discovery of this project.

- A lattice triangle has area |k|√2/2 for integer k. An equilateral triangle with integer squared side L has area L√3/4. Equality would imply 8k²=3L², impossible for nonzero integers by parity of the exponent of 3.
- Rotating a lattice displacement (a,b√2) through 90 degrees gives (−b√2,a). Both can be lattice displacements only for the zero vector, excluding squares of any orientation.
- The pentagon trapezoid requires squared-distance ratio (3+√5)/2. Lattice squared distances are integers and have rational ratios.

This argument relies on the cited classification. Our finite results do not require accepting that classification: both checkers enumerate every quadruple of each full grid used in the study. Any subset inherits that verified property.

## Certificate v1

```json
{
  "schema_version": 1,
  "metric": {"q_num": 2, "q_den": 1},
  "grid": {"width": 2, "height": 2},
  "points": [[0,0], [0,1], [1,0], [1,1]],
  "claimed_distance_count": 3
}
```

Core integers must be JSON integers, not booleans or floats. Coordinates must be distinct and within the grid. Positive rational stretches need not be reduced. The claimed count is optional, but must agree when present. Verification accepts 4–100 points and integers of at most 256 bits. Search permits at most 64 grid sites; exhaustive search rejects domains above its explicit evaluation cap before enumeration.

The main checker compares dx²·denominator + dy²·numerator using exact integers. The second checker independently builds rational squared distances. Neither imports the search implementation. All quadruples are visited even after a failure; a witness identifies the first violation. A square with q=1 fails, while the q=2 rectangle above passes.

Search metadata is descriptive, not trusted evidence: an accepted certificate proves that configuration's distance count and local constraint. It does not authenticate a claimed budget, seed or optimum. Restricted optimality additionally requires reproducible exhaustive enumeration; a separate direct-set oracle checks the small-grid results.

## Limits

The domain fixes axis alignment, q and a bounding grid. A domain optimum is not an optimum over all planar point sets. Collinear subsets are allowed. Distinct translated/reflected placements are counted separately; the exhaustive tie witness is lexicographically first. Checkers certify rational stretched-grid coordinates, not arbitrary algebraic points or a formal proof of a general theorem.
