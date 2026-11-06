"""Command-line entry point. All computation is local and CPU-only."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description="Exact few-distance geometry")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="independently check a point certificate")
    verify.add_argument("certificate", type=Path)
    search = sub.add_parser("search", help="search the sqrt(2)-stretched grid")
    search.add_argument("--width", type=int, required=True)
    search.add_argument("--height", type=int, required=True)
    search.add_argument("--points", type=int, required=True)
    search.add_argument("--method", choices=["exhaustive", "random", "swap"], default="swap")
    search.add_argument("--budget", type=int, default=1000)
    search.add_argument("--seed", type=int, default=0)
    search.add_argument("--output", type=Path)
    study = sub.add_parser("study", help="reproduce the bounded initial study")
    study.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            from .checker import verify_certificate
            from .independent import audit_certificate
            doc = json.loads(args.certificate.read_text())
            result = {"primary": verify_certificate(doc), "independent": audit_certificate(doc)}
            print(json.dumps(result, indent=2))
            return 0 if all(v["valid"] for v in result.values()) else 1
        if args.command == "study":
            from .study import run_study
            result = run_study(args.output)
            print(json.dumps(result, indent=2))
            return 0
        from .search import baseline, exhaustive
        from .checker import verify_certificate
        from .independent import audit_certificate
        if args.method == "exhaustive":
            result = exhaustive(args.width, args.height, args.points, max_evaluations=args.budget)
        else:
            result = baseline(args.width, args.height, args.points, args.method, args.seed, args.budget)
        for check in (verify_certificate, audit_certificate):
            verdict = check(result)
            if not verdict["valid"]:
                raise ValueError(f"Certificate verification failed: {verdict['errors']}")
        output = json.dumps(result, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output)
        else:
            print(output, end="")
        return 0
    except (ValueError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
