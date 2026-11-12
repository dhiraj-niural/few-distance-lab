"""Exact one-exchange audit of fixed q=2 witnesses; no search trajectory."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import signal
import time

from .checker import verify_certificate
from .independent import audit_certificate

MAX_EVALUATIONS = 10000
MAX_SECONDS = 60


def distance_count(points):
    """Direct integer pair distances, independent of search representations."""
    return len({(a[0] - b[0]) ** 2 + 2 * (a[1] - b[1]) ** 2
                for a, b in combinations(points, 2)})


def validate(width, height, points):
    if any(type(v) is not int or v <= 0 for v in (width, height)):
        raise ValueError("positive integer grid dimensions required")
    if width * height > 10000:
        raise ValueError("at most 10000 sites allowed")
    if not isinstance(points, (list, tuple)) or not 1 <= len(points) <= 100:
        raise ValueError("require 1 through 100 points")
    for point in points:
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or any(type(v) is not int for v in point)):
            raise ValueError("points must be integer pairs")
        if not (0 <= point[0] < width and 0 <= point[1] < height):
            raise ValueError("point outside grid")
    fixed = tuple(sorted(tuple(p) for p in points))
    if len(set(fixed)) != len(fixed):
        raise ValueError("duplicate point")
    return fixed


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("audit runtime cap reached")


def audit_neighborhood(width, height, points, *, max_evaluations=MAX_EVALUATIONS,
                       deadline=None):
    """Enumerate each removed occupied / added vacant pair once.

    Different pairs give different subsets: their symmetric difference from
    the fixed witness uniquely identifies the removed and added points.
    No translation/reflection quotient, plateau traversal, or stochastic work.
    """
    fixed = validate(width, height, points)
    if type(max_evaluations) is not int or not 0 <= max_evaluations <= MAX_EVALUATIONS:
        raise ValueError("evaluation cap must be an integer in [0, 10000]")
    expected = len(fixed) * (width * height - len(fixed))
    if expected > max_evaluations:
        raise ValueError("entire neighborhood exceeds evaluation cap")
    if deadline is None:
        deadline = time.monotonic() + MAX_SECONDS
    check_deadline(deadline)
    occupied = set(fixed)
    vacant = [(x, y) for x in range(width) for y in range(height)
              if (x, y) not in occupied]
    original = distance_count(fixed)
    moves, histogram = [], Counter()
    best_points, best_score, best_move = None, None, None
    for removed in fixed:
        kept = tuple(p for p in fixed if p != removed)
        for added in vacant:
            check_deadline(deadline)
            candidate = tuple(sorted(kept + (added,)))
            score = distance_count(candidate)
            moves.append({"removed": list(removed), "added": list(added), "score": score})
            histogram[score] += 1
            if best_score is None or score < best_score:
                best_points, best_score = candidate, score
                best_move = moves[-1]
    check_deadline(deadline)
    return dict(original_score=original, expected_neighbors=expected,
                evaluated_neighbors=len(moves), complete=len(moves) == expected,
                better=sum(v for k, v in histogram.items() if k < original),
                equal=histogram[original],
                worse=sum(v for k, v in histogram.items() if k > original),
                histogram=dict(sorted(histogram.items())), best_neighbor_score=best_score,
                best_neighbor_points=[list(p) for p in best_points] if best_points else None,
                best_move=best_move, moves=moves)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def dual_check(doc):
    checks = {"primary": verify_certificate(doc), "independent": audit_certificate(doc)}
    if not all(r["valid"] for r in checks.values()):
        raise ValueError(checks)
    if checks["primary"]["distance_count"] != checks["independent"]["distance_count"]:
        raise ValueError("checker disagreement")
    return checks


def run(output, protocol_path):
    began = time.monotonic()
    created_at = datetime.now(timezone.utc).isoformat()
    output, protocol_path = Path(output), Path(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    cap, seconds = protocol["max_candidate_evaluations"], protocol["max_runtime_seconds"]
    if type(cap) is not int or not 0 <= cap <= MAX_EVALUATIONS:
        raise ValueError("invalid batch candidate cap")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError("invalid runtime cap")
    deadline = began + seconds
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("use an empty output directory")
    for path, digest in protocol["source_sha256"].items():
        if sha256(path) != digest:
            raise ValueError("frozen source hash changed: " + path)
    inputs, expected = [], 0
    for item in protocol["inputs"]:
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError("frozen input hash changed: " + str(path))
        doc = json.loads(path.read_text())
        if doc.get("metric") != {"q_num": 2, "q_den": 1}:
            raise ValueError("audit supports q=2 only")
        width, height = doc["grid"]["width"], doc["grid"]["height"]
        points = validate(width, height, doc["points"])
        expected += len(points) * (width * height - len(points))
        inputs.append((path, doc))
    if expected > cap:
        raise ValueError("whole batch exceeds candidate cap")
    if len({str(p) for p, _ in inputs}) != len(inputs):
        raise ValueError("duplicate input path")
    reports, certificates, all_moves = [], {}, []
    for path, doc in inputs:
        check_deadline(deadline)
        original_checks = dual_check(doc)
        report = audit_neighborhood(doc["grid"]["width"], doc["grid"]["height"],
                                    doc["points"], max_evaluations=cap, deadline=deadline)
        if report["original_score"] != original_checks["primary"]["distance_count"]:
            raise ValueError("direct original score disagrees with checkers")
        moves = report.pop("moves")
        for move in moves:
            all_moves.append(dict(witness=path.stem, removed_x=move["removed"][0],
                                  removed_y=move["removed"][1], added_x=move["added"][0],
                                  added_y=move["added"][1], score=move["score"]))
        report.update(input=str(path), input_sha256=sha256(path), grid=doc["grid"],
                      n=len(doc["points"]), original_verification=original_checks)
        if report["best_neighbor_points"] is not None:
            best = dict(schema_version=1, metric=doc["metric"], grid=doc["grid"],
                        points=report["best_neighbor_points"],
                        claimed_distance_count=report["best_neighbor_score"])
            best["verification"] = dual_check(best)
            name = path.stem + "-best-neighbor.json"
            certificates[name] = best
            report["best_neighbor_certificate"] = "certificates/" + name
        reports.append(report)
    check_deadline(deadline)
    output.mkdir(parents=True, exist_ok=True)
    (output / "certificates").mkdir(exist_ok=True)
    for name, doc in certificates.items():
        write_json(output / "certificates" / name, doc)
    with (output / "neighbors.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["witness", "removed_x", "removed_y", "added_x", "added_y", "score"])
        writer.writeheader()
        writer.writerows(all_moves)
    manifest = dict(created_at=created_at, python=platform.python_version(), protocol=protocol,
                    protocol_sha256=sha256(protocol_path), expected_neighbors=expected,
                    evaluated_neighbors=len(all_moves), complete=len(all_moves) == expected,
                    original_score_evaluations=len(inputs),
                    verified_certificates=len(inputs) + len(certificates),
                    reports=reports, model_calls=0, external_compute=False,
                    scope="Fixed-witness one-exchange local optimality only; equality is a plateau opportunity, not a proven escape. No domain/global optimality.",
                    artifact_sha256={str(p.relative_to(output)): sha256(p)
                                     for p in sorted(output.rglob("*")) if p.is_file()})
    check_deadline(deadline)
    manifest["elapsed_seconds"] = time.monotonic() - began
    write_json(output / "study.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path("docs/protocols/one-exchange.json"))
    args = parser.parse_args()
    # Hard CLI wall-time ceiling, in addition to cooperative library checks.
    def expired(signum, frame):
        raise TimeoutError("60-second hard runtime cap reached")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(MAX_SECONDS)
    try:
        result = run(args.output, args.protocol)
        print(json.dumps({k: result[k] for k in ("complete", "evaluated_neighbors", "elapsed_seconds")}))
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
