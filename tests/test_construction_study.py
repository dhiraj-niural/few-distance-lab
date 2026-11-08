"""Check recorded experimental coverage and budget accounting on a small batch."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from few_distance.construction_study import run
from few_distance.independent import audit_certificate


class ConstructionStudyTests(unittest.TestCase):
    def test_complete_record_and_refusal_to_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol = root / "protocol.json"
            protocol.write_text(json.dumps({"instances": [[3, 4], [3, 5]],
                                            "seeds": [100, 101], "long_budget": 20,
                                            "methods": ["random", "swap"]}))
            output = root / "result"
            run(output, protocol)
            manifest = json.loads((output / "study.json").read_text())
            with (output / "trials.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 18)
            self.assertEqual(manifest["verified_certificates"], 19)
            self.assertEqual(manifest["protocol_sha256"], hashlib.sha256(protocol.read_bytes()).hexdigest())
            self.assertEqual(manifest["model_calls"], 0)
            refs = [r["certificate"] for r in rows] + manifest["domain_checks"]
            self.assertEqual(len(set(refs)), 19)
            self.assertEqual(set(refs), {str(p.relative_to(output)) for p in (output / "certificates").glob("*.json")})
            family_budgets = {int(r["n"]): int(r["evaluations"]) for r in rows if r["method"] == "compact_rows"}
            for row in rows:
                doc = json.loads((output / row["certificate"]).read_text())
                verdict = audit_certificate(doc)
                self.assertTrue(verdict["valid"])
                self.assertEqual(verdict["distance_count"], int(row["distances"]))
                self.assertEqual(doc["search"]["evaluations"], int(row["evaluations"]))
                expected = 20 if row["budget_kind"] == "long" else family_budgets[int(row["n"])]
                self.assertEqual(int(row["evaluations"]), expected)
                self.assertFalse(doc["search"]["domain_optimal"])
            before = (output / "study.json").read_bytes()
            with self.assertRaises(ValueError):
                run(output, protocol)
            self.assertEqual(before, (output / "study.json").read_bytes())
