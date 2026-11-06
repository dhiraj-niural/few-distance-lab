"""Adversarial boundary tests for the independent rational certificate audit."""

import copy
import math
import unittest

from few_distance.independent import audit_certificate, independent_exhaustive


def certificate(q_num=2, q_den=1):
    return {
        "schema_version": 1,
        "metric": {"q_num": q_num, "q_den": q_den},
        "grid": {"width": 2, "height": 2},
        "points": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "claimed_distance_count": 3,
    }


class IndependentAuditTests(unittest.TestCase):
    def test_stretched_rectangle_and_nonreduced_metric(self):
        for numerator, denominator in [(2, 1), (4, 2), (1, 2), (2, 4)]:
            result = audit_certificate(certificate(numerator, denominator))
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["distance_count"], 3)
            self.assertEqual(result["checked_quadruples"], 1)

    def test_square_is_rejected_despite_honest_count(self):
        doc = certificate(1, 1)
        doc["claimed_distance_count"] = 2
        result = audit_certificate(doc)
        self.assertFalse(result["valid"])
        self.assertEqual(result["distance_count"], 2)
        self.assertEqual(result["first_bad_quadruple_indices"], [0, 1, 2, 3])

    def test_claim_optional_but_mismatch_rejected(self):
        doc = certificate()
        del doc["claimed_distance_count"]
        self.assertTrue(audit_certificate(doc)["valid"])
        doc["claimed_distance_count"] = 4
        self.assertFalse(audit_certificate(doc)["valid"])
        self.assertEqual(audit_certificate(doc)["checked_quadruples"], 1)

    def test_all_quadruples_checked_even_after_failure(self):
        doc = certificate(1, 1)
        doc["grid"]["width"] = 3
        doc["points"].append([2, 0])
        del doc["claimed_distance_count"]
        result = audit_certificate(doc)
        self.assertFalse(result["valid"])
        self.assertEqual(result["checked_quadruples"], math.comb(5, 4))

    def test_malformed_documents_do_not_raise(self):
        malformed = [None, [], 1, "{}", {}, {"schema_version": True}]
        for doc in malformed:
            with self.subTest(doc=doc):
                self.assertFalse(audit_certificate(doc)["valid"])

    def test_nested_types_bounds_duplicates_and_resource_limits(self):
        changes = [
            ("schema_version", True),
            ("metric", {"q_num": True, "q_den": 1}),
            ("metric", {"q_num": 0, "q_den": 1}),
            ("metric", {"q_num": 2, "q_den": -1}),
            ("metric", {"q_num": 2.0, "q_den": 1}),
            ("metric", {"q_num": 2**256, "q_den": 1}),
            ("grid", {"width": 2, "height": False}),
            ("grid", {"width": 2**256, "height": 2}),
            ("points", [[0, 0], [0, 1], [1, 0], [True, 1]]),
            ("points", [[0, 0], [0, 1], [1, 0], [1.0, 1]]),
            ("points", [[0, 0], [0, 1], [1, 0], [1, 1, 1]]),
            ("points", [[0, 0], [0, 1], [1, 0], [-1, 1]]),
            ("points", [[0, 0], [0, 1], [1, 0], [2, 1]]),
            ("points", [[0, 0], [0, 1], [1, 0], [0, 0]]),
            ("points", [[0, 0], [0, 1], [1, 0]]),
            ("points", [[0, 0]] * 101),
            ("claimed_distance_count", True),
            ("claimed_distance_count", 3.0),
            ("claimed_distance_count", -1),
            ("claimed_distance_count", None),
        ]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                doc = certificate()
                doc[key] = value
                result = audit_certificate(doc)
                self.assertFalse(result["valid"], result)
                self.assertEqual(result["checked_quadruples"], 0)

    def test_large_exact_integers_have_no_float_rounding(self):
        doc = certificate()
        side = 2**255
        doc["grid"] = {"width": side + 1, "height": side + 1}
        doc["points"] = [[0, 0], [0, side], [side, 0], [side, side]]
        original = copy.deepcopy(doc)
        self.assertTrue(audit_certificate(doc)["valid"])
        self.assertEqual(doc, original)

    def test_small_exhaustive_hand_calculable_line(self):
        result = independent_exhaustive(5, 1, 4)
        self.assertEqual(result["candidates"], 5)
        self.assertEqual(result["minimum_distances"], 3)
        self.assertEqual(result["minimizer_count"], 2)

    def test_full_rectangle(self):
        result = independent_exhaustive(2, 2, 4)
        self.assertEqual(result["minimum_distances"], 3)
        self.assertEqual(result["minimizer_count"], 1)
        self.assertEqual(result["candidates"], 1)

    def test_exhaustive_bounds(self):
        for arguments in [(5, 5, 4), (4, 4, 17), (2, 2, 3), (True, 4, 4), (0, 4, 4)]:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                independent_exhaustive(*arguments)


if __name__ == "__main__":
    unittest.main()
