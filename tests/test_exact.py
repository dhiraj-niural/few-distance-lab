import json
import unittest
from itertools import combinations
from pathlib import Path

from few_distance.checker import verify_certificate
from few_distance.exact import find_within, frontier, minimum
from few_distance.independent import audit_certificate

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "results" / "2026-11-16-exact"


def brute_minimum(width, height, n, q=2):
    sites = [(x, y) for x in range(width) for y in range(height)]
    return min(
        len({(a[0] - b[0]) ** 2 + q * (a[1] - b[1]) ** 2 for a, b in combinations(chosen, 2)})
        for chosen in combinations(sites, n)
    )


class ExactSearchTest(unittest.TestCase):
    def test_matches_plain_enumeration_on_small_grids(self):
        for width, height, q in ((3, 3, 2), (4, 3, 2), (3, 4, 1), (4, 4, 2), (3, 3, 3)):
            for n in range(2, min(width * height, 9) + 1):
                with self.subTest(width=width, height=height, n=n, q=q):
                    found = minimum(width, height, n, q)
                    self.assertEqual(found["claimed_distance_count"], brute_minimum(width, height, n, q))

    def test_reproduces_the_first_study_minima(self):
        # docs/results.md, exhaustive reference table.
        self.assertEqual([r["claimed_distance_count"] for r in frontier(3, 3)][2:], [3, 4, 5, 7, 8, 8])
        self.assertEqual([r["claimed_distance_count"] for r in frontier(4, 4)][2:],
                         [3, 4, 5, 6, 6, 8, 9, 10, 10, 13, 13, 14, 14])

    def test_witnesses_pass_both_checkers(self):
        for n in (4, 8, 12):
            doc = minimum(5, 5, n)
            self.assertTrue(verify_certificate(doc)["valid"])
            self.assertTrue(audit_certificate(doc)["valid"])
            self.assertEqual(len(doc["points"]), n)

    def test_refutation_and_witness_at_the_boundary(self):
        self.assertFalse(find_within(6, 6, 10, 7)["found"])
        self.assertTrue(find_within(6, 6, 10, 8)["found"])
        self.assertFalse(find_within(5, 5, 12, 9)["found"])

    def test_node_limit_stops_instead_of_guessing(self):
        with self.assertRaises(RuntimeError):
            find_within(6, 6, 10, 7, node_limit=10)

    def test_rejects_bad_domains(self):
        for arguments in ((9, 9, 4, 3), (4, 4, 17, 3), (4, 4, 1, 3), (0, 4, 4, 3), (4, 4, 4, -1), (4, 4, True, 3)):
            with self.assertRaises(ValueError):
                find_within(*arguments)

    def test_recorded_frontiers_are_monotone_checked_and_consistent(self):
        minima = json.loads((RECORDED / "minima.json").read_text())
        for size in range(3, 8):
            doc = json.loads((RECORDED / f"frontier-{size}x{size}.json").read_text())
            values = [row["minimum"] for row in doc["rows"]]
            self.assertEqual(values, sorted(values))
            self.assertEqual(minima[f"{size}x{size}"][2:], values)
            for row in doc["rows"]:
                if row["n"] < 4:
                    continue
                cert = {"schema_version": 1, "metric": doc["metric"], "grid": doc["grid"],
                        "points": row["points"], "claimed_distance_count": row["minimum"]}
                self.assertTrue(verify_certificate(cert)["valid"])
                self.assertTrue(audit_certificate(cert)["valid"])

    def test_recorded_board_certificates_verify(self):
        files = sorted((RECORDED / "certificates").glob("*.json"))
        self.assertEqual(len(files), 4)
        for path in files:
            doc = json.loads(path.read_text())
            self.assertTrue(verify_certificate(doc)["valid"])
            self.assertTrue(audit_certificate(doc)["valid"])


if __name__ == "__main__":
    unittest.main()
