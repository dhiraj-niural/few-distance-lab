"""Check the row family, exact accounting and independently audited witnesses."""

from itertools import combinations
from unittest import TestCase, main
from unittest.mock import patch

from few_distance.checker import verify_certificate
from few_distance.constructions import compact_row_baseline, compact_row_candidates
from few_distance.independent import audit_certificate
from few_distance.search import _Objective


def score(points):
    return len({(x - a) ** 2 + 2 * (y - b) ** 2
                for (x, y), (a, b) in combinations(points, 2)})


class ConstructionTests(TestCase):
    def test_known_full_rectangle(self):
        expected = ((0, 0), (0, 1), (1, 0), (1, 1))
        self.assertEqual(compact_row_candidates(2, 2, 4), (expected,))
        result = compact_row_baseline(2, 2, 4)
        self.assertEqual(result["points"], [list(p) for p in expected])
        self.assertEqual(result["claimed_distance_count"], 3)
        self.assertEqual(result["search"]["evaluations"], 1)

    def test_manually_enumerated_partial_rows(self):
        # Four points in 3x2: two 2x2 orientations coincide, and the
        # 3-wide full row has three possible final singleton positions.
        expected = {
            ((0, 0), (0, 1), (1, 0), (1, 1)),
            ((0, 0), (0, 1), (2, 0), (2, 1)),
            ((0, 0), (0, 1), (1, 0), (2, 0)),
            ((0, 0), (1, 0), (1, 1), (2, 0)),
            ((0, 0), (1, 0), (2, 0), (2, 1)),
        }
        self.assertEqual(set(compact_row_candidates(3, 2, 4)), expected)

    def test_contiguous_remainder_offsets(self):
        candidates = compact_row_candidates(4, 2, 6)
        full = [(x, 0) for x in range(4)]
        for offset in range(3):
            expected = tuple(sorted(full + [(offset, 1), (offset + 1, 1)]))
            self.assertIn(expected, candidates)
        self.assertNotIn(tuple(sorted(full + [(0, 1), (3, 1)])), candidates)

    def test_collinear_spacings_and_unused_axis_deduplication(self):
        expected = tuple(tuple((x * step, 0) for x in range(4))
                         for step in (1, 2, 3))
        self.assertEqual(compact_row_candidates(10, 1, 4), expected)
        self.assertEqual(compact_row_candidates(1, 10, 4), tuple(
            tuple((y, x) for x, y in candidate) for candidate in expected))
        result = compact_row_baseline(10, 1, 4)
        self.assertEqual(result["claimed_distance_count"], 3)
        self.assertEqual(result["search"]["evaluations"], 3)
        self.assertEqual(result["points"], [list(p) for p in expected[0]])

    def test_independent_axis_spacings_and_transposition(self):
        rectangle = ((0, 0), (0, 3), (2, 0), (2, 3))
        self.assertIn(rectangle, compact_row_candidates(3, 4, 4))
        for width, height, n in ((4, 3, 5), (2, 5, 7), (1, 8, 4)):
            original = compact_row_candidates(width, height, n)
            transposed = {tuple(sorted((y, x) for x, y in candidate))
                          for candidate in original}
            self.assertEqual(transposed, set(compact_row_candidates(height, width, n)))

    def test_feasibility_cardinality_order_and_deduplication(self):
        for width in range(1, 6):
            for height in range(1, 6):
                for n in range(4, width * height + 1):
                    candidates = compact_row_candidates(width, height, n)
                    self.assertTrue(candidates)
                    self.assertEqual(candidates, tuple(sorted(set(candidates))))
                    for candidate in candidates:
                        self.assertEqual(len(candidate), n)
                        self.assertEqual(candidate, tuple(sorted(set(candidate))))
                        self.assertEqual(min(x for x, _ in candidate), 0)
                        self.assertEqual(min(y for _, y in candidate), 0)
                        self.assertTrue(all(type(x) is int and type(y) is int
                                            and 0 <= x < width and 0 <= y < height
                                            for x, y in candidate))

    def test_exact_objective_accounting_and_both_validators(self):
        for width, height, n in ((3, 2, 4), (3, 4, 7), (5, 3, 9), (1, 8, 5)):
            with self.subTest(width=width, height=height, n=n):
                calls = []
                original = _Objective.count

                def counted(instance, selection):
                    calls.append(selection)
                    return original(instance, selection)

                candidates = compact_row_candidates(width, height, n)
                with patch.object(_Objective, "count", counted):
                    result = compact_row_baseline(width, height, n)
                self.assertEqual(len(calls), len(set(calls)))
                self.assertEqual(len(calls), len(candidates))
                expected_score, expected_points = min((score(p), p) for p in candidates)
                self.assertEqual(result["claimed_distance_count"], expected_score)
                self.assertEqual(result["points"], [list(p) for p in expected_points])
                self.assertTrue(verify_certificate(result)["valid"])
                self.assertTrue(audit_certificate(result)["valid"])
                metadata = result["search"]
                self.assertEqual(metadata["evaluations"], len(calls))
                self.assertEqual(metadata["family_size"], len(calls))
                self.assertTrue(metadata["family_optimal"])
                self.assertTrue(metadata["complete"])
                self.assertFalse(metadata["domain_optimal"])

    def test_deterministic_certificate_except_timing(self):
        first = compact_row_baseline(4, 4, 7)
        second = compact_row_baseline(4, 4, 7)
        first["search"].pop("elapsed_seconds")
        second["search"].pop("elapsed_seconds")
        self.assertEqual(first, second)

    def test_malformed_arguments_rejected_before_objective(self):
        bad_inputs = ((0, 4, 4), (-1, 4, 4), (2.0, 3, 4), (True, 4, 4),
                      (2, 0, 4), (2, False, 4), (2, "3", 4), (9, 8, 4),
                      (2, 2, 3), (2, 2, 5), (2, 2, 4.0), (2, 2, True),
                      (None, 4, 4), (4, 4, None))
        with patch("few_distance.constructions._Objective") as objective:
            for args in bad_inputs:
                for function in (compact_row_candidates, compact_row_baseline):
                    with self.subTest(args=args, function=function.__name__):
                        with self.assertRaises(ValueError):
                            function(*args)
            objective.assert_not_called()


if __name__ == "__main__":
    main()
