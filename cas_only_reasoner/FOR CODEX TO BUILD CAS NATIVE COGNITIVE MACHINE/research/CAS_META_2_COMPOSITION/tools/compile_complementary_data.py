"""Reconcile exact archived PURE generators; deny neural/provider imports.

Each archive is reconstructed in a fresh interpreter through zipimport. No
training runner, checkpoint or model is executed. Technical failures are treated
as exposed: the full public generator supply is excluded conservatively.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.check_structural_supply_20260916 import shape_key, graph_key
from cas_meta2.complementary_teaching.course import digest
from cas_meta2.complementary_teaching.data import build_panels, validate_manifest

CHILD = r'''
import sys, json, importlib.abc, importlib.util
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','boto3','botocore','cas_cjt','casformer','requests','socket'}:
            raise RuntimeError('PURE_EXCLUSION_IMPORT_FORBIDDEN:' + fullname)
sys.meta_path.insert(0,Deny())
sys.path[:] = [sys.argv[1] + '/research/CAS_META_2_COMPOSITION'] + [p for p in sys.path if p and 'CAS_META_2_COMPOSITION' not in p]
from cas_meta2.graph_teaching import lessons
graphs=[]; counts={}; errors=[]
def add(graph):
    if all(r['kind']=='contains' for r in graph['relations']): graphs.append(graph)
for records in lessons.build_dataset(seed=20260909).values():
    for record in records: add(record['graph'])
counts['dataset']=len(graphs)
try:
    if importlib.util.find_spec('cas_meta2.graph_teaching.fresh_panel') is not None:
        from cas_meta2.graph_teaching import fresh_panel
        for case in fresh_panel.build_panel(panel_seed=20260920)['cases']: add(case['record']['graph'])
except Exception as e: errors.append('fresh_panel:'+str(e))
try:
    if importlib.util.find_spec('cas_meta2.graph_teaching.curriculum') is None: raise ModuleNotFoundError()
    from cas_meta2.graph_teaching import curriculum
    for record in curriculum.varied_records(seed=20260925): add(record['graph'])
except ModuleNotFoundError: pass
except Exception as e: errors.append('curriculum:'+str(e))
try:
    if importlib.util.find_spec('cas_meta2.graph_teaching.final_panel') is None: raise ModuleNotFoundError()
    from cas_meta2.graph_teaching import final_panel
    if hasattr(final_panel,'select_patterns'):
        for _,shape in final_panel.select_patterns(45):
            add(final_panel._shape_record(shape))
    else:
        p=final_panel.build_final_panel()
        for case in p['cases']: add(case['record']['graph'])
except ModuleNotFoundError: pass
except Exception as e: errors.append('final_panel:'+str(e))
try:
    if importlib.util.find_spec('cas_meta2.graph_teaching.face_corpus') is None: raise ModuleNotFoundError()
    from cas_meta2.graph_teaching import face_corpus,face_tasks,face_evaluation
    for family in face_corpus.families():
        add(face_tasks.family_graph(family).to_record())
        try: add(face_tasks.family_graph(face_evaluation.rewired_family(family)).to_record())
        except Exception as e: errors.append('rewire:'+str(e))
except ModuleNotFoundError: pass
except Exception as e: errors.append('faces:'+str(e))
print(json.dumps({'graphs':graphs,'counts':counts,'errors':errors}))
'''


def compile_exclusions(root=ROOT):
    inventory_path = root / 'records/structural_supply_20260916/EXPOSURE_BINDINGS.json'
    inventory = json.loads(inventory_path.read_bytes())
    paths = {}
    for entry in inventory['entries']:
        paths[entry['source_archive']['path']] = entry['source_archive']['sha256']
        if sha256((root / entry['result']['path']).read_bytes()).hexdigest() != entry['result']['sha256']:
            raise ValueError('EXPOSURE_RESULT_CHANGED:' + entry['result']['path'])
    all_results = list(inventory['earlier_attempt_result_inventory']) + list(inventory['rescued_seed_20260912_result_candidates'])
    for row in all_results:
        result = root / row['path']
        if sha256(result.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('EXPOSURE_RESULT_CHANGED:' + row['path'])
        archive = result.parent / 'source.zip'
        if not archive.exists():
            raise ValueError('EXPOSURE_ARCHIVE_MISSING:' + str(archive))
        paths[str(archive.relative_to(root)).replace('\\','/')] = sha256(archive.read_bytes()).hexdigest()
    rows, banned, failures = [], set(), []
    # Repeat archives need one computation, but every location remains hash-bound.
    cache = {}
    for relative, expected in sorted(paths.items()):
        archive = root / relative
        actual = sha256(archive.read_bytes()).hexdigest()
        if expected != actual:
            raise ValueError('EXPOSURE_ARCHIVE_CHANGED:' + relative)
        if actual not in cache:
            result = subprocess.run([sys.executable, '-c', CHILD, str(archive)], cwd=root,
                                    text=True, capture_output=True, timeout=90)
            if result.returncode:
                cache[actual] = {'graphs': [], 'errors': [result.stderr[-3000:]]}
            else:
                cache[actual] = json.loads(result.stdout)
        payload = cache[actual]
        keys = {graph_key(graph) for graph in payload['graphs']}
        banned |= keys
        rows.append({'path': relative, 'sha256': actual, 'graph_records': len(payload['graphs']),
                     'topologies': len(keys), 'errors': payload['errors']})
        failures.extend({'archive':relative, 'error':error} for error in payload['errors'])
    return {'schema':'cas.complementary-exclusions/0.1', 'complete':not failures,
            'inventory_sha256':sha256(inventory_path.read_bytes()).hexdigest(),
            'archives':rows, 'excluded_topologies':sorted(banned), 'failures':failures,
            'rule':'All generated historical dataset/varied/45 final candidates and all face/rewired families; technical attempts conservatively exposed.',
            'actual_neural_presentations':0,'actual_provider_calls':0}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    exclusions=compile_exclusions()
    (args.output/'historical_exclusions.json').write_text(json.dumps(exclusions,indent=2)+'\n',encoding='utf-8')
    if not exclusions['complete']:
        print(json.dumps({'status':'HISTORICAL_EXCLUSIONS_BLOCKED','failures':exclusions['failures']}))
        return 2
    panels=validate_manifest(build_panels(exclusions,topology_key=shape_key))
    (args.output/'data_manifest.json').write_text(json.dumps(panels,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'DATA_COMPILED_NEURAL_UNTESTED','sha256':panels['data_sha256'],
                      'counts':panels['counts'],'exclusions':len(exclusions['excluded_topologies'])}))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
