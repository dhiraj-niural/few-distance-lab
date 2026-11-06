"""Independent set-based reference checks for the bitset search objectives."""

from itertools import combinations
from unittest import TestCase, main
from unittest.mock import patch

from few_distance.search import baseline, exhaustive


def reference_score(points):
    return len({(x - a) ** 2 + 2 * (y - b) ** 2
                for (x, y), (a, b) in combinations(points, 2)})


def reference_exhaustive(width, height, n):
    candidates = combinations([(x, y) for x in range(width)
                               for y in range(height)], n)
    scored = [(reference_score(points), points) for points in candidates]
    optimum = min(score for score, _ in scored)
    minimizers = [points for score, points in scored if score == optimum]
    return optimum, len(minimizers), [list(point) for point in min(minimizers)]


class SearchTests(TestCase):
    def assert_witness(self, result, n):
        points = result["points"]
        self.assertEqual(len(points), n)
        self.assertEqual(len(set(map(tuple, points))), n)
        self.assertEqual(points, sorted(points))
        self.assertTrue(all(0 <= x < result["grid"]["width"] and
                            0 <= y < result["grid"]["height"] for x, y in points))
        self.assertEqual(result["claimed_distance_count"], reference_score(points))
        self.assertEqual(result["metric"], {"q_num": 2, "q_den": 1})
        self.assertEqual(result["schema_version"], 1)

    def test_exhaustive_matches_independent_reference(self):
        for width, height, n in [(2, 2, 4), (2, 3, 4), (3, 2, 4),
                                 (3, 3, 5), (1, 6, 4), (6, 1, 4)]:
            with self.subTest(width=width, height=height, n=n):
                score, count, points = reference_exhaustive(width, height, n)
                result = exhaustive(width, height, n)
                self.assert_witness(result, n)
                self.assertEqual(result["claimed_distance_count"], score)
                self.assertEqual(result["points"], points)
                search = result["search"]
                self.assertEqual(search["minimizer_count"], count)
                self.assertEqual(search["evaluations"], search["domain_size"])
                self.assertTrue(search["complete"])
                self.assertTrue(search["domain_optimal"])

    def test_exhaustive_cap_rejects_before_objective_construction(self):
        with patch("few_distance.search._Objective") as objective:
            with self.assertRaisesRegex(ValueError, "exceeding"):
                exhaustive(8, 8, 32, max_evaluations=200000)
            objective.assert_not_called()
        self.assertEqual(exhaustive(2, 3, 4, 15)["search"]["evaluations"], 15)
        with self.assertRaises(ValueError):
            exhaustive(2, 3, 4, 14)

    def test_determinism_and_budget_accounting(self):
        for method in ("random", "swap"):
            for budget in (1, 2, 137):
                with self.subTest(method=method, budget=budget):
                    first = baseline(4, 3, 5, method, 29, budget)
                    second = baseline(4, 3, 5, method, 29, budget)
                    self.assert_witness(first, 5)
                    first["search"].pop("elapsed_seconds")
                    second["search"].pop("elapsed_seconds")
                    self.assertEqual(first, second)
                    search = first["search"]
                    self.assertEqual(search["evaluations"], budget)
                    self.assertEqual(search["random_draws"] +
                                     search["swap_proposals"], budget)
                    self.assertEqual(search["accepted_moves"] +
                                     search["rejected_moves"], search["swap_proposals"])
                    self.assertEqual(search["improving_moves"] +
                                     search["plateau_acceptances"], search["accepted_moves"])
                    self.assertTrue(search["complete"])
                    self.assertFalse(search["domain_optimal"])
                    if method == "random":
                        self.assertEqual(search["random_draws"], budget)
                        self.assertEqual(search["restarts"], 0)
                    else:
                        self.assertEqual(search["random_draws"], search["restarts"] + 1)

    def test_actual_objective_calls_equal_budget(self):
        from few_distance.search import _Objective
        original = _Objective.count
        for method in ("random", "swap"):
            calls = []

            def counted(instance, selection):
                calls.append(selection)
                return original(instance, selection)

            with patch.object(_Objective, "count", counted):
                baseline(3, 3, 4, method, 11, 71)
            self.assertEqual(len(calls), 71)

    def test_full_grid_swap_terminates_and_counts_restarts(self):
        for budget in (1, 25):
            result = baseline(2, 2, 4, "swap", 0, budget)
            self.assert_witness(result, 4)
            search = result["search"]
            self.assertEqual(search["evaluations"], budget)
            self.assertEqual(search["random_draws"], budget)
            self.assertEqual(search["restarts"], budget - 1)
            self.assertEqual(search["swap_proposals"], 0)
            self.assertFalse(search["domain_optimal"])

    def test_plateaus_bounded_and_random_restarts_occur(self):
        # A constant objective isolates plateau behavior from improvements.
        with patch("few_distance.search._Objective.count", return_value=10):
            search = baseline(3, 3, 4, "swap", 0, 35)["search"]
        self.assertEqual(search["restarts"], 2)
        self.assertEqual(search["swap_proposals"], 32)
        self.assertEqual(search["plateau_acceptances"], 8)
        self.assertEqual(search["rejected_moves"], 24)

    def test_invalid_arguments(self):
        bad_grids = [(0, 3, 4), (-1, 4, 4), (2.0, 3, 4),
                     (True, 4, 4), (2, 0, 4), (9, 8, 4),
                     (2, 2, 3), (2, 2, 5), (2, 2, 4.0), (2, 2, True)]
        for args in bad_grids:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    exhaustive(*args)
                with self.assertRaises(ValueError):
                    baseline(*args, "random", 0, 1)
        for cap in (0, -1, 1.0, True):
            with self.assertRaises(ValueError):
                exhaustive(2, 2, 4, cap)
            with self.assertRaises(ValueError):
                baseline(2, 2, 4, "swap", 0, cap)
        for seed in (None, 1.0, True, "1"):
            with self.assertRaises(ValueError):
                baseline(2, 2, 4, "random", seed, 1)
        for method in (None, "exhaustive", "other"):
            with self.assertRaises(ValueError):
                baseline(2, 2, 4, method, 0, 1)


if __name__ == "__main__":
    main()
