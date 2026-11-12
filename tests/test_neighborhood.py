"""Cross-check neighborhoods by filtering independently enumerated subsets."""
from collections import Counter
from fractions import Fraction
from itertools import combinations
import time
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from few_distance.neighborhood import audit_neighborhood, run, sha256


class NeighborhoodTests(unittest.TestCase):
    def test_all_small_witnesses_against_brute_subsets(self):
        sites = [(x, y) for x in range(3) for y in range(2)]
        for fixed in combinations(sites, 4):
            expected = {}
            for subset in combinations(sites, 4):
                if len(set(fixed) ^ set(subset)) == 2:
                    score = len({Fraction((a[0] - b[0]) ** 2) + Fraction(2) * (a[1] - b[1]) ** 2
                                 for a, b in combinations(subset, 2)})
                    expected[frozenset(subset)] = score
            report = audit_neighborhood(3, 2, fixed)
            actual = {frozenset((set(fixed) - {tuple(m["removed"])}) | {tuple(m["added"])}): m["score"]
                      for m in report["moves"]}
            self.assertEqual(actual, expected)
            self.assertEqual(len(report["moves"]), len(actual))
            self.assertEqual(report["histogram"], dict(Counter(expected.values())))
            self.assertEqual(report["expected_neighbors"], 8)
            self.assertEqual(report["evaluated_neighbors"], 8)
            self.assertTrue(report["complete"])
            self.assertEqual(sum(report[k] for k in ("better", "equal", "worse")), 8)
            self.assertEqual(report["best_neighbor_score"], min(expected.values()))
            self.assertEqual(expected[frozenset(map(tuple, report["best_neighbor_points"]))], min(expected.values()))

    def test_invalid_points_and_dimensions(self):
        for points in ([], [(0, 0), (0, 0)], [(2, 0)], [(-1, 0)], [(True, 0)], [(0.0, 0)], [(0,)], [None]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                audit_neighborhood(2, 2, points)
        for width in (True, 0, -1, 1.0, 10001):
            with self.assertRaises(ValueError):
                audit_neighborhood(width, 2, [(0, 0)])

    def test_cap_preflight_and_deadline_before_objective(self):
        with patch("few_distance.neighborhood.distance_count") as objective:
            for cap in (-1, True, 10001, 2):
                with self.assertRaises(ValueError):
                    audit_neighborhood(2, 2, [(0, 0)], max_evaluations=cap)
            with self.assertRaises(TimeoutError):
                audit_neighborhood(2, 2, [(0, 0)], deadline=time.monotonic() - 1)
            objective.assert_not_called()

    def test_full_grid_has_no_neighbors(self):
        report = audit_neighborhood(2, 2, [(0, 0), (0, 1), (1, 0), (1, 1)], max_evaluations=0)
        self.assertTrue(report["complete"])
        self.assertEqual(report["evaluated_neighbors"], 0)
        self.assertIsNone(report["best_neighbor_points"])

    def test_batch_manifest_hashes_caps_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            witness = root / "witness.json"
            witness.write_text(json.dumps(dict(schema_version=1, metric=dict(q_num=2, q_den=1),
                grid=dict(width=3, height=2), points=[[0, 0], [0, 1], [1, 0], [1, 1]])))
            protocol_path = root / "protocol.json"
            protocol = dict(max_candidate_evaluations=7, max_runtime_seconds=10,
                            source_sha256={}, inputs=[dict(path=str(witness), sha256=sha256(witness))])
            protocol_path.write_text(json.dumps(protocol))
            output = root / "out"
            with patch("few_distance.neighborhood.distance_count") as objective:
                with self.assertRaises(ValueError):
                    run(output, protocol_path)
                objective.assert_not_called()
            self.assertFalse(output.exists())
            protocol["max_candidate_evaluations"] = 8
            protocol_path.write_text(json.dumps(protocol))
            result = run(output, protocol_path)
            self.assertEqual(result["evaluated_neighbors"], 8)
            self.assertEqual(result["verified_certificates"], 2)
            self.assertTrue(result["complete"])
            self.assertEqual(result["protocol_sha256"], sha256(protocol_path))
            for path, digest in result["artifact_sha256"].items():
                self.assertEqual(sha256(output / path), digest)
            with self.assertRaises(ValueError):
                run(output, protocol_path)
            witness.write_text(witness.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "input hash changed"):
                run(root / "second", protocol_path)
