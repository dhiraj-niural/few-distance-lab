"""Record proven minima for every point count on square boards 3x3 to 7x7.

Run from the repository root:

    cc -O2 -o /tmp/exact_bb tools/exact_bb.c
    python3 tools/exact_study.py --c-binary /tmp/exact_bb --output results/reproduction-exact

Boards up to 6x6 are solved by both the Python module and the C program. The
7x7 board is solved by the C program for every count, and by Python for the
counts listed in --python-7 (2 to 24 by default; larger counts are slow in CPython).
Every witness is passed through both exact checkers. The run stops on any
disagreement.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from few_distance.checker import verify_certificate  # noqa: E402
from few_distance.exact import minimum  # noqa: E402
from few_distance.independent import audit_certificate  # noqa: E402

LEVELS = {  # the arrangements the game shows as optimal boards
    (4, 8): [[x, y] for x in range(4) for y in (0, 2)],
    (5, 12): [[x, y] for x in range(4) for y in range(3)],
    (6, 10): [[x, y] for x in (0, 4) for y in range(5)],
    (7, 20): [[x, y] for x in (0, 2, 4, 6) for y in range(5)],
}


def certificate(size, points, count):
    doc = {"schema_version": 1, "metric": {"q_num": 2, "q_den": 1},
           "grid": {"width": size, "height": size}, "points": sorted(points),
           "claimed_distance_count": count}
    for check in (verify_certificate, audit_certificate):
        verdict = check(doc)
        if not verdict["valid"]:
            raise SystemExit(f"checker rejected {size}x{size} n={len(points)}: {verdict}")
    return doc


def c_solver(binary, size, n, bound):
    run = subprocess.run([binary, str(size), str(size), str(n), str(bound), "2"],
                         capture_output=True, text=True, check=True)
    nodes = int(run.stderr.split()[-1])
    if run.stdout.startswith("NONE"):
        return None, nodes
    return [[int(v) for v in pair.split(",")] for pair in run.stdout.split()[1:]], nodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c-binary")
    parser.add_argument("--python-7", type=int, nargs="*", default=list(range(2, 25)))
    args = parser.parse_args()
    (args.output / "certificates").mkdir(parents=True, exist_ok=False)
    summary = {}
    for size in range(3, 8):
        rows, start = [], 1
        for n in range(2, size * size + 1):
            row = {"n": n}
            if size < 7 or n in args.python_7:
                result = minimum(size, size, n, start=start)
                row.update(minimum=result["claimed_distance_count"], points=result["points"],
                           python_refutation_nodes=result["search"]["refutation_nodes"])
            if args.c_binary:
                bound, refuted = start, 0
                while True:
                    points, nodes = c_solver(args.c_binary, size, n, bound)
                    if points is not None:
                        break
                    refuted, bound = refuted + nodes, bound + 1
                if row.setdefault("minimum", bound) != bound:
                    raise SystemExit(f"implementations disagree at {size}x{size} n={n}")
                row.setdefault("points", points)
                row["c_refutation_nodes"] = refuted
            if "minimum" not in row:
                raise SystemExit(f"no solver configured for {size}x{size} n={n}")
            if n >= 4:
                certificate(size, row["points"], row["minimum"])
            start = row["minimum"]
            rows.append(row)
            print(size, n, start, flush=True)
        doc = {"grid": {"width": size, "height": size}, "metric": {"q_num": 2, "q_den": 1},
               "claim": "minimum distinct distances over all n-subsets of this grid", "rows": rows}
        (args.output / f"frontier-{size}x{size}.json").write_text(json.dumps(doc, indent=1) + "\n")
        summary[f"{size}x{size}"] = [0, 0] + [row["minimum"] for row in rows]
    for (size, n), points in LEVELS.items():
        doc = certificate(size, points, summary[f"{size}x{size}"][n])
        (args.output / "certificates" / f"exact-{size}x{size}-n{n}.json").write_text(json.dumps(doc, indent=1) + "\n")
    (args.output / "minima.json").write_text(json.dumps(summary, indent=1) + "\n")


if __name__ == "__main__":
    main()
