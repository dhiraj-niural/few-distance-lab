"""Exact geometric examples and malformed-certificate regression tests."""

import copy
import math
import unittest

from few_distance.checker import verify_certificate


def rectangle(q_num=2, q_den=1):
    return {
        "schema_version": 1,
        "metric": {"q_num": q_num, "q_den": q_den},
        "grid": {"width": 2, "height": 2},
        "points": [[0, 0], [1, 0], [0, 1], [1, 1]],
    }


class CheckerTests(unittest.TestCase):
    def test_square_fails_with_exact_witness(self):
        result = verify_certificate(rectangle(1))
        self.assertFalse(result["valid"])
        self.assertEqual(result["squared_distances"], ["1", "2"])
        self.assertEqual(result["distance_count"], 2)
        self.assertEqual(result["violating_quadruple"], [0, 1, 2, 3])
        self.assertEqual(result["checked_quadruples"], 1)

    def test_q2_rectangle_valid(self):
        doc = rectangle()
        doc["claimed_distance_count"] = 3
        result = verify_certificate(doc)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["squared_distances"], ["1", "2", "3"])
        self.assertEqual(result["errors"], [])
        self.assertIsNone(result["violating_quadruple"])

    def test_fractional_and_unreduced_metrics(self):
        self.assertEqual(verify_certificate(rectangle(2, 4))["squared_distances"],
                         ["1/2", "1", "3/2"])
        self.assertEqual(verify_certificate(rectangle(4, 2)),
                         verify_certificate(rectangle(2, 1)))

    def test_near_square_keeps_distinct_exact_lengths(self):
        result = verify_certificate(rectangle(10**30 + 1, 10**30))
        self.assertTrue(result["valid"])
        self.assertEqual(result["distance_count"], 3)

    def test_q2_three_by_three_grid(self):
        doc = rectangle()
        doc["grid"] = {"width": 3, "height": 3}
        doc["points"] = [[x, y] for x in range(3) for y in range(3)]
        result = verify_certificate(doc)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["distance_count"], 8)
        self.assertEqual(result["squared_distances"], ["1", "2", "3", "4", "6", "8", "9", "12"])
        self.assertEqual(result["checked_quadruples"], math.comb(9, 4))

    def test_all_quadruples_checked_after_violation(self):
        doc = rectangle(1)
        doc["grid"] = {"width": 3, "height": 2}
        doc["points"].append([2, 1])
        result = verify_certificate(doc)
        self.assertFalse(result["valid"])
        self.assertEqual(result["checked_quadruples"], 5)

    def test_claim_mismatch(self):
        doc = rectangle()
        doc["claimed_distance_count"] = 2
        result = verify_certificate(doc)
        self.assertFalse(result["valid"])
        self.assertEqual(result["distance_count"], 3)
        self.assertEqual(result["checked_quadruples"], 1)

    def test_metadata_ignored_and_input_unchanged(self):
        doc = rectangle()
        doc["metadata"] = {"note": "not a mathematical claim"}
        before = copy.deepcopy(doc)
        self.assertTrue(verify_certificate(doc)["valid"])
        self.assertEqual(doc, before)

    def assertMalformed(self, doc):
        result = verify_certificate(doc)
        self.assertFalse(result["valid"], result)
        self.assertTrue(result["errors"])
        self.assertIsNone(result["distance_count"])
        self.assertEqual(result["squared_distances"], [])
        self.assertEqual(result["checked_quadruples"], 0)
        self.assertIsNone(result["violating_quadruple"])

    def test_invalid_metric_values(self):
        for field in ("q_num", "q_den"):
            for value in (0, -1, True, False, 2.0, "2", None, [], 1 << 256):
                with self.subTest(field=field, value=value):
                    doc = rectangle()
                    doc["metric"][field] = value
                    self.assertMalformed(doc)

    def test_invalid_point_values(self):
        for point in ([0.0, 0], [True, 0], [0, False], [0, "0"], [-1, 0],
                      [2, 0], [0, 2], [0, -1], [0, 0, 0], [0], None,
                      (0, 0), [1 << 256, 0], [1, 1]):
            with self.subTest(point=point):
                doc = rectangle()
                doc["points"][0] = point
                self.assertMalformed(doc)

    def test_invalid_grid(self):
        for field in ("width", "height"):
            for value in (0, -2, True, 2.0, "2", None, 1 << 256):
                with self.subTest(field=field, value=value):
                    doc = rectangle()
                    doc["grid"][field] = value
                    self.assertMalformed(doc)

    def test_missing_fields_and_bad_containers(self):
        for field in ("schema_version", "metric", "grid", "points"):
            doc = rectangle()
            del doc[field]
            self.assertMalformed(doc)
        for field in ("metric", "grid", "points"):
            for value in (None, 1, "x", True):
                doc = rectangle()
                doc[field] = value
                self.assertMalformed(doc)
        for doc in (None, [], "", True, 0):
            self.assertMalformed(doc)
        for field in ("q_num", "q_den"):
            doc = rectangle()
            del doc["metric"][field]
            self.assertMalformed(doc)

    def test_invalid_version_and_claim(self):
        for value in (True, 1.0, "1", 2, None):
            doc = rectangle()
            doc["schema_version"] = value
            self.assertMalformed(doc)
        for value in (True, 3.0, "3", None, 0, -1, 1 << 256):
            doc = rectangle()
            doc["claimed_distance_count"] = value
            self.assertMalformed(doc)

    def test_point_count_resource_guards(self):
        for points in ([], [[0, 0]], [[0, 0]] * 3, [[0, 0]] * 101):
            doc = rectangle()
            doc["points"] = points
            self.assertMalformed(doc)


if __name__ == "__main__":
    unittest.main()
