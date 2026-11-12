"""Exhaustive fixed-witness two-exchange audit for exact q=2 distances."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import signal
import time

from .neighborhood import check_deadline, distance_count, dual_check, sha256, validate, write_json

MAX_EVALUATIONS = 300000
MAX_SECONDS = 60

# Preserve compatibility with the project's Python 3.9 runtime.
_popcount = int.bit_count if hasattr(int, 'bit_count') else lambda value: bin(value).count('1')


def move_line(removed, added, score):
    """Digest serialization: rx1,ry1,rx2,ry2,ax1,ay1,ax2,ay2,score + LF."""
    return (','.join(map(str, (*removed[0], *removed[1], *added[0], *added[1], score))) + '\n').encode('ascii')


def audit_neighborhood(width, height, points, *, max_evaluations=MAX_EVALUATIONS,
                       deadline=None, retain_moves=False):
    """Replace two occupied sites with two *originally* vacant sites.

    Every resulting subset uniquely determines both pairs by difference from
    the fixed witness. Thus C(n,2) C(WH-n,2) is the exact distinct-neighbor count.
    Bit d of each integer mask records the exact squared distance d; OR and
    bit_count give the cardinality of the union without floating-point work.
    """
    fixed = validate(width, height, points)
    if type(max_evaluations) is not int or not 0 <= max_evaluations <= MAX_EVALUATIONS:
        raise ValueError('evaluation cap must be an integer in [0, 300000]')
    expected = math.comb(len(fixed), 2) * math.comb(width * height - len(fixed), 2)
    if expected > max_evaluations:
        raise ValueError('entire neighborhood exceeds evaluation cap')
    if deadline is None:
        deadline = time.monotonic() + MAX_SECONDS
    check_deadline(deadline)
    original = distance_count(fixed)
    occupied = set(fixed)
    vacant = tuple((x, y) for x in range(width) for y in range(height)
                   if (x, y) not in occupied) if expected else ()
    def bit(a, b):
        return 1 << ((a[0] - b[0]) ** 2 + 2 * (a[1] - b[1]) ** 2)
    # Only precompute edges needed for this neighborhood, after cap preflight.
    fixed_edges = {(i, j): bit(fixed[i], fixed[j]) for i, j in combinations(range(len(fixed)), 2)}
    cross = [[bit(v, p) for p in fixed] for v in vacant]
    added_pairs = [(i, j, bit(vacant[i], vacant[j])) for i, j in combinations(range(len(vacant)), 2)]
    histogram, digest, moves = Counter(), hashlib.sha256(), []
    best_score, best_points, best_move, evaluated = None, None, None, 0
    for left, right in combinations(range(len(fixed)), 2):
        check_deadline(deadline)
        kept_indices = [i for i in range(len(fixed)) if i not in (left, right)]
        kept_mask = 0
        for i, j in combinations(kept_indices, 2):
            kept_mask |= fixed_edges[i, j]
        cross_masks = []
        for edges in cross:
            mask = 0
            for i in kept_indices:
                mask |= edges[i]
            cross_masks.append(mask)
        removed = (fixed[left], fixed[right])
        for i, j, pair_mask in added_pairs:
            if evaluated % 1024 == 0:
                check_deadline(deadline)
            added = (vacant[i], vacant[j])
            score = _popcount(kept_mask | cross_masks[i] | cross_masks[j] | pair_mask)
            histogram[score] += 1
            evaluated += 1
            digest.update(move_line(removed, added, score))
            if retain_moves or best_score is None or score < best_score:
                move = dict(removed=[list(p) for p in removed], added=[list(p) for p in added], score=score)
                if retain_moves:
                    moves.append(move)
                if best_score is None or score < best_score:
                    best_score, best_move = score, move
                    best_points = sorted([fixed[k] for k in kept_indices] + list(added))
    check_deadline(deadline)
    report = dict(original_score=original, expected_neighbors=expected,
                  evaluated_neighbors=evaluated, complete=evaluated == expected,
                  better=sum(v for k, v in histogram.items() if k < original),
                  equal=histogram.get(original, 0),
                  worse=sum(v for k, v in histogram.items() if k > original),
                  histogram=dict(sorted(histogram.items())), best_neighbor_score=best_score,
                  best_neighbor_points=[list(p) for p in best_points] if best_points is not None else None,
                  best_move=best_move, move_stream_sha256=digest.hexdigest())
    if retain_moves:
        report['moves'] = moves
    return report


def run(output, protocol_path):
    began = time.monotonic()
    created_at = datetime.now(timezone.utc).isoformat()
    output, protocol_path = Path(output), Path(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    cap, seconds = protocol['max_candidate_evaluations'], protocol['max_runtime_seconds']
    if type(cap) is not int or not 0 <= cap <= MAX_EVALUATIONS:
        raise ValueError('invalid batch candidate cap')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError('invalid runtime cap')
    deadline = began + seconds
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('use an empty output directory')
    for path, digest in protocol['source_sha256'].items():
        if sha256(path) != digest:
            raise ValueError('frozen source hash changed: ' + path)
    inputs, expected = [], 0
    for item in protocol['inputs']:
        path = Path(item['path'])
        if sha256(path) != item['sha256']:
            raise ValueError('frozen input hash changed: ' + str(path))
        doc = json.loads(path.read_text())
        if doc.get('metric') != {'q_num': 2, 'q_den': 1}:
            raise ValueError('audit supports q=2 only')
        width, height = doc['grid']['width'], doc['grid']['height']
        points = validate(width, height, doc['points'])
        expected += math.comb(len(points), 2) * math.comb(width * height - len(points), 2)
        inputs.append((path, doc))
    if expected > cap:
        raise ValueError('whole batch exceeds candidate cap')
    if expected != protocol['expected_candidate_evaluations']:
        raise ValueError('expected candidate count disagrees with protocol')
    if len({p.resolve() for p, _ in inputs}) != len(inputs):
        raise ValueError('duplicate input path')
    reports, certificates = [], {}
    for path, doc in inputs:
        check_deadline(deadline)
        original_checks = dual_check(doc)
        report = audit_neighborhood(doc['grid']['width'], doc['grid']['height'],
                                    doc['points'], max_evaluations=cap, deadline=deadline)
        if report['original_score'] != original_checks['primary']['distance_count']:
            raise ValueError('original score disagrees with checkers')
        report.update(input=str(path), input_sha256=sha256(path), grid=doc['grid'],
                      n=len(doc['points']), original_verification=original_checks)
        if report['best_neighbor_points'] is not None:
            best = dict(schema_version=1, metric=doc['metric'], grid=doc['grid'],
                        points=report['best_neighbor_points'],
                        claimed_distance_count=report['best_neighbor_score'])
            best['verification'] = dual_check(best)
            name = path.stem + '-best-two-exchange.json'
            certificates[name] = best
            report['best_neighbor_certificate'] = 'certificates/' + name
        reports.append(report)
    check_deadline(deadline)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'certificates').mkdir(exist_ok=True)
    for name, doc in certificates.items():
        write_json(output / 'certificates' / name, doc)
    evaluated = sum(r['evaluated_neighbors'] for r in reports)
    manifest = dict(created_at=created_at, python=platform.python_version(), protocol=protocol,
                    protocol_sha256=sha256(protocol_path), expected_neighbors=expected,
                    evaluated_neighbors=evaluated,
                    complete=evaluated == expected and all(r['complete'] for r in reports),
                    original_score_evaluations=len(inputs),
                    verified_certificates=len(inputs) + len(certificates),
                    reports=reports, model_calls=0, external_compute=False,
                    scope='Fixed-witness exact two-exchange neighborhood only; no global or domain optimum.',
                    artifact_sha256={str(p.relative_to(output)): sha256(p)
                                     for p in sorted(output.rglob('*')) if p.is_file()})
    check_deadline(deadline)
    manifest['elapsed_seconds'] = time.monotonic() - began
    write_json(output / 'study.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=Path('docs/protocols/two-exchange.json'))
    args = parser.parse_args()
    def expired(signum, frame):
        raise TimeoutError('60-second hard runtime cap reached')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(MAX_SECONDS)
    try:
        result = run(args.output, args.protocol)
        print(json.dumps({k: result[k] for k in ('complete', 'evaluated_neighbors', 'elapsed_seconds')}))
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
