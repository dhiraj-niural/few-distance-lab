"""Bounded, reproducible first study; no model or network dependencies."""
from datetime import datetime, timezone
import csv
import hashlib
import json
import platform
from pathlib import Path
import statistics
import time

from .checker import verify_certificate
from .independent import audit_certificate
from .search import baseline, exhaustive


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def checked(certificate):
    primary = verify_certificate(certificate)
    independent = audit_certificate(certificate)
    if not primary["valid"] or not independent["valid"]:
        raise ValueError({"primary": primary, "independent": independent})
    if primary["distance_count"] != independent["distance_count"]:
        raise ValueError("Independent objective disagreement")
    return {"primary": primary, "independent": independent}


def run_study(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory is not empty; use a fresh destination")
    output.mkdir(parents=True, exist_ok=True)
    certificates = output / "certificates"
    certificates.mkdir()
    began = time.perf_counter()
    domain_checks = []
    for side in (3, 4, 5):
        full_grid = {"schema_version": 1, "metric": {"q_num": 2, "q_den": 1},
                     "grid": {"width": side, "height": side},
                     "points": [[x, y] for x in range(side) for y in range(side)]}
        full_grid["verification"] = checked(full_grid)
        name = f"domain-{side}x{side}.json"
        write_json(certificates / name, full_grid)
        domain_checks.append(f"certificates/{name}")
    exact = []
    for side in (3, 4):
        for n in range(4, side * side + 1):
            result = exhaustive(side, side, n, max_evaluations=200000)
            result["verification"] = checked(result)
            name = f"exact-{side}x{side}-n{n}.json"
            write_json(certificates / name, result)
            exact.append({"side": side, "n": n, "distances": result["claimed_distance_count"],
                          "evaluations": result["search"]["evaluations"],
                          "minimizer_count": result["search"]["minimizer_count"],
                          "certificate": f"certificates/{name}"})
    optima = {(r["side"], r["n"]): r["distances"] for r in exact}
    trials = []
    for side, sizes, budget in ((4, (6, 8, 10, 12), 1000), (5, (8, 12, 16), 2000)):
        for n in sizes:
            for method in ("random", "swap"):
                for seed in range(10):
                    result = baseline(side, side, n, method, seed, budget)
                    verdicts = checked(result)
                    name = f"{method}-{side}x{side}-n{n}-seed{seed}.json"
                    result["verification"] = verdicts
                    write_json(certificates / name, result)
                    trials.append({"side": side, "n": n, "method": method, "seed": seed,
                                   "budget": budget, "evaluations": result["search"]["evaluations"],
                                   "distances": result["claimed_distance_count"],
                                   "seconds": result["search"]["elapsed_seconds"],
                                   "known_domain_optimum": optima.get((side, n)),
                                   "certificate": f"certificates/{name}"})
    with (output / "trials.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(trials[0]))
        writer.writeheader()
        writer.writerows(trials)
    summary = []
    for side, n, method in sorted({(r["side"], r["n"], r["method"]) for r in trials}):
        rows = [r for r in trials if (r["side"], r["n"], r["method"]) == (side, n, method)]
        values = [r["distances"] for r in rows]
        optimum = optima.get((side, n))
        summary.append({"side": side, "n": n, "method": method, "runs": len(rows),
                        "best": min(values), "median": statistics.median(values), "worst": max(values),
                        "domain_optimum": optimum,
                        "optimum_hits": None if optimum is None else values.count(optimum),
                        "total_evaluations": sum(r["evaluations"] for r in rows)})
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(Path(__file__).parent.glob("*.py"))}
    manifest = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(), "source_sha256": source_hashes,
                "scope": "q=2 stretched-grid subsets; fixed candidate-evaluation budgets",
                "exhaustive": exact, "baseline_summary": summary,
                "domain_checks": domain_checks,
                "trials": len(trials), "verified_certificates": len(exact) + len(trials) + len(domain_checks),
                "elapsed_seconds": time.perf_counter() - began,
                "model_calls": 0, "external_compute": False,
                "claim": "Restricted-domain optima and heuristic observations; no unrestricted planar or novelty claim."}
    write_json(output / "study.json", manifest)
    return {"output": str(output), "verified_certificates": manifest["verified_certificates"],
            "trials": len(trials), "elapsed_seconds": manifest["elapsed_seconds"]}
