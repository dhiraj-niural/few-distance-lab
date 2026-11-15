"""Direct subset oracles independent of the production bitset scorer."""
from itertools import combinations
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from few_distance.plateau import canonical, candidates, run, sha256, traverse
from few_distance.neighborhood import dual_check


def score(points):
    return len({(x-a)**2 + 2*(y-b)**2 for (x,y),(a,b) in combinations(points, 2)})


class PlateauTests(unittest.TestCase):
    def test_all_small_neighborhoods(self):
        sites = tuple((x,y) for x in range(3) for y in range(2))
        for n in range(1, 7):
            for fixed in combinations(sites, n):
                for order in (1,2):
                    expected = {subset:score(subset) for subset in combinations(sites,n)
                                if len(set(subset)^set(fixed)) == 2*order}
                    moves = list(candidates(3,2,fixed,order,time.monotonic()+10))
                    actual = {tuple(sorted(set(fixed)-set(r)|set(a))):s for r,a,s in moves}
                    self.assertEqual(expected, actual)
                    self.assertEqual(len(moves), len(actual))

    def test_reflections_preserve_metric_and_no_transpose(self):
        points = ((0,0),(0,1),(2,0))
        key = canonical(points,3,3)
        for rx,ry in ((0,0),(0,1),(1,0),(1,1)):
            transformed = tuple((2-x if rx else x,2-y if ry else y) for x,y in points)
            self.assertEqual(canonical(transformed,3,3),key)
            self.assertEqual(score(transformed),score(points))
        self.assertNotEqual(canonical(tuple((y,x) for x,y in points),3,3),key)
        self.assertEqual(canonical(points,3,3,'raw'),tuple(sorted(points)))
        with self.assertRaises(ValueError):
            canonical(points,3,3,'transpose')

    def test_complete_tiny_components_against_subset_graph(self):
        # One point has score zero everywhere; full subset graph is independently known.
        for width,height in ((1,1),(2,1),(2,2),(3,2)):
            sites = tuple((x,y) for x in range(width) for y in range(height))
            for mode in ('raw','reflections'):
                identities = {canonical((p,),width,height,mode) for p in sites}
                result = traverse(width,height,[sites[0]],symmetry=mode)
                self.assertEqual(result['complete'],len(identities)<=3)
                self.assertEqual(result['admitted_states'],min(3,len(identities)))
                self.assertEqual(result['unadmitted_equal_states'],max(0,len(identities)-3))
                self.assertEqual({r['key'] for r in result['reports']},
                                 {e['target_key'] for e in result['equal_edges'] if e['target'] is not None}
                                 if len(sites)>1 else {result['reports'][0]['key']})
                self.assertEqual(result['evaluated_neighbors'],min(3,len(identities))*(len(sites)-1))
                self.assertIsNone(result['improving_witness'])

    def test_empty_full_and_caps(self):
        full = [(x,y) for x in range(2) for y in range(2)]
        result = traverse(2,2,full,max_evaluations=0)
        self.assertTrue(result['complete'])
        self.assertEqual(result['evaluated_neighbors'],0)
        self.assertEqual(result['strict_baseline']['result'],'STUCK')
        for cap in (0,1,2):
            result = traverse(3,2,[(0,0)],max_evaluations=cap)
            self.assertFalse(result['complete'])
            self.assertEqual(result['evaluated_neighbors'],cap)
            self.assertIn('candidate_cap',result['stopping_reasons'])
        # Exactly exhausting a complete component at the cap is still complete.
        self.assertTrue(traverse(2,1,[(0,0)],max_evaluations=1)['complete'])
        for args in ({'max_states':0},{'max_states':4},{'max_states':True},
                     {'max_evaluations':-1},{'max_evaluations':300001},
                     {'max_evaluations':True},{'deadline':float('inf')},{'symmetry':'bad'}):
            with self.assertRaises(ValueError):
                traverse(2,2,[(0,0)],**args)
        with self.assertRaises(ValueError):
            traverse(2,2,[])
        with patch('few_distance.plateau.distance_count') as objective:
            with self.assertRaises(TimeoutError):
                traverse(2,2,[(0,0)],deadline=time.monotonic()-1)
            objective.assert_not_called()

    def test_first_improvement_and_determinism(self):
        points = [(0,0),(0,1),(2,0)]
        result = traverse(3,2,points)
        self.assertEqual(result['status'],'IMPROVEMENT_FOUND')
        self.assertFalse(result['complete'])
        witness = result['improving_witness']
        self.assertEqual(score(witness['points']),witness['move']['score'])
        self.assertLess(witness['move']['score'],score(points))
        # Direct set scoring establishes which lexicographic move improves first.
        fixed = tuple(sorted(points))
        vacant = tuple((x,y) for x in range(3) for y in range(2) if (x,y) not in fixed)
        direct = [score(set(fixed)-{r}|{a}) for r in fixed for a in vacant]
        first = next(i for i,s in enumerate(direct,1) if s < score(points))
        self.assertEqual(result['evaluated_neighbors'],first)
        self.assertEqual(result['strict_baseline']['result'],'IMPROVEMENT_FOUND')
        self.assertEqual(result,traverse(3,2,list(reversed(points))))

    def test_four_point_improvement_is_dually_certifiable(self):
        points = [(0,0),(0,1),(1,0),(2,1)]
        result = traverse(3,2,points)
        witness = result['improving_witness']
        self.assertIsNotNone(witness)
        certificate = dict(schema_version=1,metric=dict(q_num=2,q_den=1),
            grid=dict(width=3,height=2),points=witness['points'],
            claimed_distance_count=witness['move']['score'])
        self.assertTrue(all(r['valid'] for r in dual_check(certificate).values()))

    def test_runtime_during_scan_is_incomplete(self):
        def expired(*args):
            raise TimeoutError()
            yield
        with patch('few_distance.plateau.candidates',expired):
            result = traverse(2,1,[(0,0)])
        self.assertFalse(result['complete'])
        self.assertEqual(result['stopping_reasons'],['runtime_cap'])
        self.assertEqual(result['evaluated_neighbors'],0)

    def test_manifest_freeze_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            witness,protocol,output = root/'w.json',root/'p.json',root/'out'
            witness.write_text(json.dumps(dict(schema_version=1,metric=dict(q_num=2,q_den=1),
                grid=dict(width=2,height=2),points=[[0,0],[0,1],[1,0],[1,1]],claimed_distance_count=3)))
            config = dict(max_runtime_seconds=10,max_candidate_evaluations=10,max_states=3,
                symmetry='reflections',source_sha256={},input=dict(path=str(witness),sha256=sha256(witness)))
            protocol.write_text(json.dumps(config))
            result = run(output,protocol)
            self.assertTrue(result['complete'])
            for path,digest in result['artifact_sha256'].items():
                self.assertEqual(sha256(output/path),digest)
            with self.assertRaises(ValueError):
                run(output,protocol)
            config['source_sha256']={str(witness):'wrong'}
            protocol.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'frozen source changed'):
                run(root/'other',protocol)
