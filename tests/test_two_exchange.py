"""Independent subset oracle: do not derive expected subsets via exchanges."""
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from few_distance.two_exchange import audit_neighborhood, run, sha256


class TwoExchangeTests(unittest.TestCase):
    def test_all_small_witnesses_against_subset_oracle(self):
        sites = [(x, y) for x in range(3) for y in range(3)]
        for n in (2, 4, 7):
            for fixed in combinations(sites, n):
                expected = {}
                for subset in combinations(sites, n):
                    if len(set(fixed) ^ set(subset)) == 4:
                        expected[frozenset(subset)] = len({Fraction((a[0] - b[0]) ** 2) +
                            2 * Fraction((a[1] - b[1]) ** 2) for a, b in combinations(subset, 2)})
                report = audit_neighborhood(3, 3, fixed, retain_moves=True)
                actual = {frozenset((set(fixed) - set(map(tuple, m['removed']))) |
                                    set(map(tuple, m['added']))): m['score'] for m in report['moves']}
                self.assertEqual(actual, expected)
                self.assertEqual(len(actual), len(report['moves']))
                self.assertEqual(report['histogram'], dict(Counter(expected.values())))
                self.assertEqual(report['expected_neighbors'], math.comb(n, 2) * math.comb(9 - n, 2))
                self.assertEqual(report['evaluated_neighbors'], len(expected))
                self.assertTrue(report['complete'])
                self.assertEqual(sum(report[k] for k in ('better', 'equal', 'worse')), len(expected))
                self.assertEqual(report['best_neighbor_score'], min(expected.values()))
                self.assertEqual(expected[frozenset(map(tuple, report['best_neighbor_points']))], min(expected.values()))
                digest = hashlib.sha256()
                for move in report['moves']:
                    vals = [v for p in move['removed'] + move['added'] for v in p] + [move['score']]
                    digest.update((','.join(str(v) for v in vals) + '\n').encode())
                self.assertEqual(report['move_stream_sha256'], digest.hexdigest())

    def test_cap_and_timeout_preflight(self):
        with patch('few_distance.two_exchange.distance_count') as objective:
            for cap in (-1, True, 300001, 5):
                with self.assertRaises(ValueError):
                    audit_neighborhood(3, 2, [(0, 0), (0, 1), (1, 0), (1, 1)], max_evaluations=cap)
            with self.assertRaises(TimeoutError):
                audit_neighborhood(3, 2, [(0, 0)], deadline=time.monotonic() - 1)
            objective.assert_not_called()

    def test_no_neighbors_and_invalid_input(self):
        sites = [(x, y) for x in range(2) for y in range(2)]
        for points in (sites, sites[:3], sites[:1]):
            report = audit_neighborhood(2, 2, points, max_evaluations=0)
            self.assertEqual(report['evaluated_neighbors'], 0)
            self.assertTrue(report['complete'])
            self.assertIsNone(report['best_neighbor_points'])
        for points in ([], [(0, 0), (0, 0)], [(2, 0)], [(True, 0)]):
            with self.assertRaises(ValueError):
                audit_neighborhood(2, 2, points)

    def test_deterministic_order_and_minimum(self):
        fixed = [(0, 0), (0, 1), (1, 0), (1, 1)]
        report = audit_neighborhood(3, 2, fixed, retain_moves=True)
        self.assertEqual(report, audit_neighborhood(3, 2, list(reversed(fixed)), retain_moves=True))
        self.assertEqual(report['best_move'], next(m for m in report['moves'] if m['score'] == report['best_neighbor_score']))
        self.assertEqual([m['removed'] for m in report['moves']], [[list(p) for p in pair] for pair in combinations(fixed, 2)])

    def test_batch_hashes_caps_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            witness, protocol_path, output = root / 'witness.json', root / 'protocol.json', root / 'out'
            witness.write_text(json.dumps(dict(schema_version=1, metric=dict(q_num=2, q_den=1),
                grid=dict(width=3, height=2), points=[[0, 0], [0, 1], [1, 0], [1, 1]])))
            protocol = dict(max_candidate_evaluations=5, max_runtime_seconds=10,
                            expected_candidate_evaluations=6, source_sha256={},
                            inputs=[dict(path=str(witness), sha256=sha256(witness))])
            protocol_path.write_text(json.dumps(protocol))
            with patch('few_distance.two_exchange.distance_count') as objective:
                with self.assertRaises(ValueError):
                    run(output, protocol_path)
                objective.assert_not_called()
            self.assertFalse(output.exists())
            protocol['max_candidate_evaluations'] = 6
            protocol_path.write_text(json.dumps(protocol))
            result = run(output, protocol_path)
            self.assertEqual(result['evaluated_neighbors'], 6)
            self.assertEqual(result['verified_certificates'], 2)
            self.assertTrue(result['complete'])
            self.assertEqual(result['protocol_sha256'], sha256(protocol_path))
            for path, digest in result['artifact_sha256'].items():
                self.assertEqual(sha256(output / path), digest)
            with self.assertRaises(ValueError):
                run(output, protocol_path)
            witness.write_text(witness.read_text() + ' ')
            with self.assertRaisesRegex(ValueError, 'input hash changed'):
                run(root / 'second', protocol_path)
