"""Bounded exact BFS through equal-score one/two-exchange configurations."""
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
MAX_STATES = 3
_popcount = int.bit_count if hasattr(int, 'bit_count') else lambda x: bin(x).count('1')


def move_line(removed, added, score):
    """ASCII flattened removed coordinates, added coordinates, score and LF."""
    return (','.join(map(str, [v for p in removed + added for v in p] + [score])) + '\n').encode('ascii')


def state_key(points):
    return hashlib.sha256(json.dumps(points, separators=(',', ':')).encode('ascii')).hexdigest()


def canonical(points, width, height, symmetry='reflections'):
    """Board automorphisms only: identity, x/y reflections, and both.

    Transposition is not an isometry of dx²+2dy² and is never included.
    Translation is not a board automorphism and is never included.
    """
    if symmetry not in ('reflections', 'raw'):
        raise ValueError('symmetry must be reflections or raw')
    points = tuple(sorted(tuple(p) for p in points))
    if symmetry == 'raw':
        return points
    return min(tuple(sorted((width - 1 - x if rx else x,
                             height - 1 - y if ry else y) for x, y in points))
               for rx in (False, True) for ry in (False, True))


def candidates(width, height, fixed, order, deadline):
    """Exact bitset scores in lexicographic removed/added combination order."""
    if order not in (1, 2):
        raise ValueError('order must be one or two')
    check_deadline(deadline)
    occupied = set(fixed)
    vacant = tuple((x, y) for x in range(width) for y in range(height) if (x, y) not in occupied)
    def bit(a, b):
        return 1 << ((a[0] - b[0]) ** 2 + 2 * (a[1] - b[1]) ** 2)
    edges = {(i, j): bit(fixed[i], fixed[j]) for i, j in combinations(range(len(fixed)), 2)}
    cross = []
    for v in vacant:
        check_deadline(deadline)
        cross.append([bit(v, p) for p in fixed])
    for removed_indices in combinations(range(len(fixed)), order):
        check_deadline(deadline)
        kept = [i for i in range(len(fixed)) if i not in removed_indices]
        retained = 0
        for i, j in combinations(kept, 2):
            retained |= edges[i, j]
        cross_masks = []
        for row in cross:
            mask = 0
            for i in kept:
                mask |= row[i]
            cross_masks.append(mask)
        removed = tuple(fixed[i] for i in removed_indices)
        for inserted in combinations(range(len(vacant)), order):
            check_deadline(deadline)
            mask = retained
            for i in inserted:
                mask |= cross_masks[i]
            if order == 2:
                mask |= bit(vacant[inserted[0]], vacant[inserted[1]])
            yield removed, tuple(vacant[i] for i in inserted), _popcount(mask)


def traverse(width, height, points, *, max_evaluations=MAX_EVALUATIONS,
             max_states=MAX_STATES, deadline=None, symmetry='reflections'):
    """Scan admitted BFS states, retaining all equal edges and first improvement.

    Candidate cap counts scored neighbors, including repeats from different states.
    State cap counts admitted configurations including the initial configuration.
    Unadmitted equal targets make the result INCOMPLETE, even if all admitted
    states were fully scanned. Reflection classes use a canonical tuple identity,
    but scans retain first-seen raw representatives for reproducible moves.
    The first improving neighbor terminates the search immediately. Completion
    means the entire equal-score component has been scanned, never just the queue.
    """
    fixed = validate(width, height, points)
    if type(max_evaluations) is not int or not 0 <= max_evaluations <= MAX_EVALUATIONS:
        raise ValueError('invalid candidate cap')
    if type(max_states) is not int or not 1 <= max_states <= MAX_STATES:
        raise ValueError('invalid state cap')
    now = time.monotonic()
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('deadline must be finite')
    deadline = now + MAX_SECONDS if deadline is None else min(deadline, now + MAX_SECONDS)
    check_deadline(deadline)
    identity = lambda points: canonical(points, width, height, symmetry)
    initial_identity = identity(fixed)
    original = distance_count(fixed)
    states, ids, reports, equal_edges = [fixed], {initial_identity: 0}, [], []
    blocked, reasons = set(), set()
    evaluated, improving = 0, None
    expected = {k: math.comb(len(fixed), k) * math.comb(width * height - len(fixed), k) for k in (1, 2)}
    index = 0
    stopped = False
    while index < len(states) and not stopped:
        current = states[index]
        report = dict(id=index, key=state_key(identity(current)), points=[list(p) for p in current], score=original, neighborhoods={})
        for order in (1, 2):
            histogram, digest, count = Counter(), hashlib.sha256(), 0
            stream = candidates(width, height, current, order, deadline)
            while count < expected[order] and not stopped:
                if evaluated >= max_evaluations:
                    reasons.add('candidate_cap')
                    stopped = True
                    break
                try:
                    removed, added, score = next(stream)
                except TimeoutError:
                    reasons.add('runtime_cap')
                    stopped = True
                    break
                count += 1
                evaluated += 1
                histogram[score] += 1
                digest.update(move_line(removed, added, score))
                if score <= original:
                    target = tuple(sorted((set(current) - set(removed)) | set(added)))
                    move = dict(removed=[list(p) for p in removed], added=[list(p) for p in added], score=score)
                    if score < original and improving is None:
                        improving = dict(source=index, points=[list(p) for p in target], move=move)
                        reasons.add('first_improvement')
                        stopped = True
                    elif score == original:
                        target_identity = identity(target)
                        if target_identity not in ids and target_identity not in blocked:
                            if len(states) < max_states:
                                ids[target_identity] = len(states)
                                states.append(target)
                            else:
                                blocked.add(target_identity)
                                reasons.add('state_cap')
                        equal_edges.append(dict(source=index, target=ids.get(target_identity), target_key=state_key(target_identity),
                                                target_points=[list(p) for p in target], order=order, move=move))
            report['neighborhoods'][str(order)] = dict(expected_neighbors=expected[order], evaluated_neighbors=count,
                complete=count == expected[order], histogram=dict(sorted(histogram.items())),
                better=sum(v for k, v in histogram.items() if k < original), equal=histogram[original],
                worse=sum(v for k, v in histogram.items() if k > original), move_stream_sha256=digest.hexdigest())
        report['complete'] = all(r['complete'] for r in report['neighborhoods'].values())
        reports.append(report)
        index += 1
    # Every admitted state is recorded, including states whose scans never began.
    for index in range(len(reports), len(states)):
        reports.append(dict(id=index, key=state_key(identity(states[index])), points=[list(p) for p in states[index]],
                            score=original, complete=False, neighborhoods={}))
    if time.monotonic() >= deadline:
        reasons.add('runtime_cap')
        stopped = True
    complete = not stopped and not blocked and all(r['complete'] for r in reports)
    # Orbit members are symmetry images, not an assertion of raw reachability.
    for report in reports:
        pts = report['points']
        orbit = {tuple(sorted((width-1-x if rx else x, height-1-y if ry else y)
                              for x,y in pts))
                 for rx in (False,True) for ry in (False,True)}
        report['board_reflection_orbit'] = [[list(p) for p in member] for member in sorted(orbit)]
    initial = reports[0]
    first_improvement = improving if improving and improving['source'] == 0 else None
    baseline = dict(start_state=0, shared_initial_scan=True,
                    evaluated_neighbors=sum(r['evaluated_neighbors'] for r in initial['neighborhoods'].values()),
                    scan_complete=initial['complete'], accepts_equal=False,
                    improving_neighbor=first_improvement,
                    result='IMPROVEMENT_FOUND' if first_improvement else ('STUCK' if initial['complete'] else 'INCOMPLETE'))
    return dict(original_score=original, original_score_evaluations=1,
                evaluated_neighbors=evaluated, admitted_states=len(states), unadmitted_equal_states=len(blocked),
                symmetry=symmetry, complete=complete,
                status='IMPROVEMENT_FOUND' if improving else ('COMPLETE' if complete else 'INCOMPLETE'),
                stopping_reasons=sorted(reasons), reports=reports, equal_edges=equal_edges,
                improving_witness=improving, strict_baseline=baseline,
                closed_without_improvement=complete and improving is None)


def run(output, protocol_path):
    began = time.monotonic()
    output, protocol_path = Path(output), Path(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    seconds = protocol['max_runtime_seconds']
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError('invalid runtime cap')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('use an empty output directory')
    for path, expected_hash in protocol['source_sha256'].items():
        if sha256(path) != expected_hash:
            raise ValueError('frozen source changed: ' + path)
    item = protocol['input']
    if sha256(item['path']) != item['sha256']:
        raise ValueError('frozen input changed')
    doc = json.loads(Path(item['path']).read_text())
    if doc['metric'] != {'q_num': 2, 'q_den': 1}:
        raise ValueError('q=2 required')
    check_deadline(began + seconds)
    original_checks = dual_check(doc)
    check_deadline(began + seconds)
    result = traverse(doc['grid']['width'], doc['grid']['height'], doc['points'],
                      max_evaluations=protocol['max_candidate_evaluations'], max_states=protocol['max_states'],
                      deadline=began + seconds, symmetry=protocol['symmetry'])
    if result['original_score'] != original_checks['primary']['distance_count']:
        raise ValueError('original checker disagreement')
    certificates = {}
    for report in result['reports']:
        check_deadline(began + seconds)
        certificate = dict(schema_version=1, metric=doc['metric'], grid=doc['grid'],
                           points=report['points'], claimed_distance_count=report['score'])
        certificate['verification'] = dual_check(certificate)
        certificates['state-%d.json' % report['id']] = certificate
    if result['improving_witness']:
        witness = result['improving_witness']
        certificate = dict(schema_version=1, metric=doc['metric'], grid=doc['grid'],
                           points=witness['points'], claimed_distance_count=witness['move']['score'])
        certificate['verification'] = dual_check(certificate)
        certificates['improvement.json'] = certificate
    # If validation cannot finish in time, fail rather than publish a certified result.
    check_deadline(began + seconds)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'certificates').mkdir()
    for name, certificate in certificates.items():
        write_json(output / 'certificates' / name, certificate)
    result.update(created_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  protocol=protocol, protocol_sha256=sha256(protocol_path), original_verification=original_checks,
                  dual_certificate_checks=1 + len(certificates), model_calls=0, external_compute=False,
                  scope='Equal-score component of this fixed witness in this grid under exactly one/two exchanges. No domain or global optimum.',
                  artifact_sha256={str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},
                  elapsed_seconds=time.monotonic() - began)
    check_deadline(began + seconds)
    write_json(output / 'study.json', result)
    if time.monotonic() >= began + seconds:
        (output / 'study.json').unlink()
        raise TimeoutError('runtime cap reached while writing manifest')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=Path('docs/protocols/plateau.json'))
    args = parser.parse_args()
    # The hard CLI guard is deliberately not caught by cooperative timeout code.
    class HardDeadline(BaseException):
        pass
    def expired(signum, frame):
        raise HardDeadline('60-second hard runtime cap reached')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS)
    try:
        result = run(args.output, args.protocol)
        print(json.dumps({k: result[k] for k in ('status', 'admitted_states', 'evaluated_neighbors', 'closed_without_improvement', 'elapsed_seconds')}))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    main()
