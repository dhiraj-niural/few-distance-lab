"""Compare a finite geometric family against stochastic searches, without models."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

from .constructions import compact_row_baseline
from .search import baseline
from .study import checked, write_json


def run(output, protocol_path):
    output, protocol_path = Path(output), Path(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory is not empty; use a fresh destination")
    output.mkdir(parents=True, exist_ok=True)
    certificates = output / "certificates"
    certificates.mkdir()
    began = time.perf_counter()
    rows, domains = [], []

    def save(doc, name):
        doc["verification"] = checked(doc)
        write_json(certificates / name, doc)
        return "certificates/" + name

    for side in sorted({side for side, _ in protocol["instances"]}):
        doc = {"schema_version": 1, "metric": {"q_num": 2, "q_den": 1},
               "grid": {"width": side, "height": side},
               "points": [[x, y] for x in range(side) for y in range(side)]}
        domains.append(save(doc, f"domain-{side}.json"))

    for side, n in protocol["instances"]:
        doc = compact_row_baseline(side, side, n)
        count = doc["search"]["evaluations"]
        ref = save(doc, f"compact-{side}-n{n}.json")
        rows.append(dict(side=side, n=n, method="compact_rows", budget_kind="family",
                         seed=None, evaluations=count, distances=doc["claimed_distance_count"],
                         seconds=doc["search"]["elapsed_seconds"], certificate=ref))
        for kind, budget in (("matched", count), ("long", protocol["long_budget"])):
            for method in protocol["methods"]:
                for seed in protocol["seeds"]:
                    doc = baseline(side, side, n, method, seed, budget)
                    ref = save(doc, f"{method}-{side}-n{n}-{kind}-seed{seed}.json")
                    rows.append(dict(side=side, n=n, method=method, budget_kind=kind,
                                     seed=seed, evaluations=doc["search"]["evaluations"],
                                     distances=doc["claimed_distance_count"],
                                     seconds=doc["search"]["elapsed_seconds"], certificate=ref))
    with (output / "trials.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summaries = []
    keys = sorted({(r["side"], r["n"], r["method"], r["budget_kind"]) for r in rows})
    for side, n, method, kind in keys:
        group = [r for r in rows if (r["side"], r["n"], r["method"], r["budget_kind"]) ==
                 (side, n, method, kind)]
        values = [r["distances"] for r in group]
        summaries.append(dict(side=side, n=n, method=method, budget_kind=kind,
                              runs=len(group), best=min(values), median=statistics.median(values),
                              worst=max(values), evaluations_per_run=group[0]["evaluations"]))
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                    protocol=protocol, protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                    source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(Path(__file__).parent.glob("*.py"))},
                    summary=summaries, domain_checks=domains, verified_certificates=len(rows)+len(domains),
                    trials=len(rows), elapsed_seconds=time.perf_counter()-began,
                    model_calls=0, external_compute=False,
                    claim="Finite construction/search comparison; no unrestricted optimum or AI advantage.")
    write_json(output / "study.json", manifest)
    return {key: manifest[key] for key in ("trials", "verified_certificates", "elapsed_seconds", "summary")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path("docs/protocols/compact-rows.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.protocol), indent=2))
