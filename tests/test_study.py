"""End-to-end study artifact checks against the independent exact oracle."""

import csv
import hashlib
import json
from math import comb
from pathlib import Path
import tempfile
import unittest

from few_distance.independent import audit_certificate, independent_exhaustive
from few_distance.study import run_study


ROOT = Path(__file__).resolve().parents[1]


class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.fresh = Path(cls.temporary.name) / "study"
        cls.run_result = run_study(cls.fresh)
        cls.oracles = {
            (side, n): independent_exhaustive(side, side, n)
            for side in (3, 4) for n in range(4, side * side + 1)
        }

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def assert_study_consistent(self, folder):
        manifest = json.loads((folder / "study.json").read_text())
        with (folder / "trials.csv").open(newline="") as stream:
            trials = list(csv.DictReader(stream))
        self.assertEqual(manifest["verified_certificates"], 162)
        self.assertEqual(manifest["trials"], 140)
        self.assertEqual(len(trials), 140)
        self.assertEqual(manifest["model_calls"], 0)
        self.assertIs(manifest["external_compute"], False)
        self.assertEqual(len(manifest["exhaustive"]), 19)
        self.assertEqual(
            {(row["side"], row["n"]) for row in manifest["exhaustive"]},
            set(self.oracles),
        )
        self.assertEqual(len(manifest["domain_checks"]), 3)
        referenced = [row["certificate"] for row in manifest["exhaustive"] + trials] + manifest["domain_checks"]
        self.assertEqual(len(set(referenced)), 162)
        self.assertEqual(
            set(referenced),
            {str(p.relative_to(folder)) for p in (folder / "certificates").glob("*.json")},
        )
        certificates = {}
        for name in referenced:
            doc = json.loads((folder / name).read_text())
            certificates[name] = doc
            verdict = audit_certificate(doc)
            self.assertTrue(verdict["valid"], (name, verdict))
            if "claimed_distance_count" in doc:
                self.assertEqual(verdict["distance_count"], doc["claimed_distance_count"])
            self.assertEqual(verdict["checked_quadruples"], comb(len(doc["points"]), 4))
            self.assertEqual(verdict, doc["verification"]["independent"])
            primary = doc["verification"]["primary"]
            for field in ("valid", "distance_count", "checked_quadruples"):
                self.assertEqual(verdict[field], primary[field], (name, field))
            self.assertEqual(doc["metric"], {"q_num": 2, "q_den": 1})
        domain_sides = set()
        for name in manifest["domain_checks"]:
            doc = certificates[name]
            side = doc["grid"]["width"]
            domain_sides.add(side)
            self.assertEqual(doc["grid"]["height"], side)
            self.assertEqual({tuple(point) for point in doc["points"]}, {(x, y) for x in range(side) for y in range(side)})
        self.assertEqual(domain_sides, {3, 4, 5})
        for row in manifest["exhaustive"]:
            side, n = row["side"], row["n"]
            oracle = self.oracles[side, n]
            doc = certificates[row["certificate"]]
            self.assertEqual(doc["grid"], {"width": side, "height": side})
            self.assertEqual(len(doc["points"]), n)
            self.assertEqual(row["distances"], oracle["minimum_distances"])
            self.assertEqual(row["distances"], doc["claimed_distance_count"])
            self.assertEqual(row["minimizer_count"], oracle["minimizer_count"])
            self.assertEqual(row["minimizer_count"], doc["search"]["minimizer_count"])
            self.assertEqual(row["evaluations"], comb(side * side, n))
            self.assertEqual(row["evaluations"], doc["search"]["evaluations"])
            self.assertEqual(doc["points"], oracle["points"])
            self.assertIs(doc["search"]["domain_optimal"], True)
            self.assertEqual(doc["search"]["termination"], "domain_exhausted")
        self.assertEqual(sum(row["evaluations"] for row in manifest["exhaustive"]), 65221)

        expected_keys = {
            (side, n, method, seed)
            for side, ns in ((4, (6, 8, 10, 12)), (5, (8, 12, 16)))
            for n in ns for method in ("random", "swap") for seed in range(10)
        }
        observed_keys, groups = set(), {}
        for row in trials:
            side, n, seed = int(row["side"]), int(row["n"]), int(row["seed"])
            method = row["method"]
            key = (side, n, method, seed)
            self.assertNotIn(key, observed_keys)
            observed_keys.add(key)
            doc = certificates[row["certificate"]]
            search = doc["search"]
            budget = 1000 if side == 4 else 2000
            self.assertEqual(int(row["budget"]), budget)
            self.assertEqual(int(row["evaluations"]), budget)
            self.assertEqual(search["budget"], budget)
            self.assertEqual(search["evaluations"], budget)
            self.assertEqual(search["random_draws"] + search["swap_proposals"], budget)
            self.assertEqual(search["method"], method)
            self.assertEqual(search["seed"], seed)
            self.assertIs(search["domain_optimal"], False)
            self.assertEqual(search["termination"], "budget_exhausted")
            self.assertEqual(doc["grid"], {"width": side, "height": side})
            self.assertEqual(len(doc["points"]), n)
            self.assertEqual(int(row["distances"]), doc["claimed_distance_count"])
            self.assertEqual(float(row["seconds"]), search["elapsed_seconds"])
            self.assertGreaterEqual(float(row["seconds"]), 0)
            optimum = self.oracles[side, n]["minimum_distances"] if side == 4 else None
            self.assertEqual(row["known_domain_optimum"], str(optimum) if optimum is not None else "")
            groups.setdefault((side, n, method), []).append(row)
        self.assertEqual(observed_keys, expected_keys)
        self.assertEqual(sum(int(row["evaluations"]) for row in trials), 200000)
        self.assertEqual(len(manifest["baseline_summary"]), len(groups))
        self.assertEqual(
            {(row["side"], row["n"], row["method"]) for row in manifest["baseline_summary"]},
            set(groups),
        )
        for summary in manifest["baseline_summary"]:
            key = (summary["side"], summary["n"], summary["method"])
            rows = groups[key]
            scores = sorted(int(row["distances"]) for row in rows)
            self.assertEqual(summary["runs"], 10)
            self.assertEqual(summary["best"], scores[0])
            self.assertEqual(summary["worst"], scores[-1])
            self.assertEqual(summary["median"], (scores[4] + scores[5]) / 2)
            optimum = self.oracles[key[:2]]["minimum_distances"] if key[0] == 4 else None
            self.assertEqual(summary["domain_optimum"], optimum)
            self.assertEqual(summary["optimum_hits"], scores.count(optimum) if optimum is not None else None)
            self.assertEqual(summary["total_evaluations"], sum(int(row["evaluations"]) for row in rows))

    def test_full_study_outputs_match_independent_oracle(self):
        self.assert_study_consistent(self.fresh)
        self.assertEqual(self.run_result["verified_certificates"], 162)
        manifest = json.loads((self.fresh / "study.json").read_text())
        self.assertEqual(
            manifest["source_sha256"],
            {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "few_distance").glob("*.py")},
        )

    def test_saved_initial_study_is_consistent(self):
        self.assert_study_consistent(ROOT / "results" / "2026-11-06")

    def test_existing_outputs_are_not_overwritten(self):
        manifest = (self.fresh / "study.json").read_bytes()
        with self.assertRaises(ValueError):
            run_study(self.fresh)
        self.assertEqual((self.fresh / "study.json").read_bytes(), manifest)


if __name__ == "__main__":
    unittest.main()
