"""Builder compatibility and timing checks. Run only on the selected AWS CPU."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def save(name, value):
    p = HERE / name
    p.with_suffix('.tmp').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    p.with_suffix('.tmp').replace(p)


def verify_inputs():
    manifest = json.loads((ROOT / 'INPUT_MANIFEST.json').read_bytes())
    for row in manifest['files']:
        raw = (ROOT / row['path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise RuntimeError('INPUT_CHANGED:' + row['path'])
    return manifest


def compatibility():
    before = verify_inputs()
    from cas_meta2.typed_teaching import checker as old, checker_v2 as new, course, slots, slots_v2, source
    started = time.monotonic()
    material = json.loads((ROOT / 'records/typed_course_001/checks_002/public_course.json').read_bytes())
    if len(material['registry']) != 564:
        raise RuntimeError('REGISTRY_COUNT')
    reports = {'schema': 'helm.stage2-builder-compatibility/1', 'status': 'RUNNING',
        'input_manifest_sha256': hashlib.sha256((ROOT / 'INPUT_MANIFEST.json').read_bytes()).hexdigest(),
        'frozen_profile': old.checker_profile(), 'new_profile': new.checker_profile(),
        'target_records': 0, 'unique_targets': 0, 'slot_plans': 0, 'predictions': 0,
        'target_mismatches': [], 'witness_mismatches': [], 'slot_mismatches': [], 'check_mismatches': [],
        'unique_check_inputs': 0, 'reused_identical_check_inputs': 0, 'prediction_files': [],
        'device': {'platform': platform.platform(), 'cpu': platform.processor(), 'logical_cpus': os.cpu_count()},
        'source_commit': before['source_commit'], 'historical_model_sources': {
            'helm1': 'af0970cfa6d54a85aeb16e5a99a84d791ace59c0',
            'helm2': '20208c923d41c24614504d4ecc2b289ecb66eda8'}}
    targets = {}; checks = {}; rows = {r['record_id']: r for r in material['registry']}
    # Reuse only exact semantic inputs. Do not retain all large public packets or slot plans.
    for idx, row in enumerate(material['registry']):
        packet = {'source': course._public(material['bank'], row['source_world_id']), 'record': row}
        public, query = packet['source'], row['query']
        key = source.digest([public, query])
        if key not in targets:
            targets[key] = (old.derive_target(public, query), new.derive_target(public, query))
        a, b = targets[key]
        if canonical(a['admissible_answers']) != canonical(b['admissible_answers']):
            reports['target_mismatches'].append(row['record_id'])
        if canonical(a['witnesses']) != canonical(b['witnesses']) or a['coverage'] != b['coverage']:
            reports['witness_mismatches'].append(row['record_id'])
        if canonical(slots.compile_slots(packet)) != canonical(slots_v2.compile_slots(packet)):
            reports['slot_mismatches'].append(row['record_id'])
        slots.clear_slot_cache(); slots_v2.clear_slot_cache()
        reports['target_records'] += 1; reports['slot_plans'] += 1
        if idx % 25 == 0:
            reports['elapsed_seconds'] = time.monotonic() - started
            save('compatibility.json', reports); print('records', idx + 1, flush=True)
    reports['unique_targets'] = len(targets)
    targets.clear()
    for study, prefix in [('helm1', 'receipt_helm1_certified_'), ('helm2', 'receipt_')]:
        for seed in (20260917, 20260918, 20260919):
            for phase in ('course_p00', 'course_p10'):
                path = ROOT / ('records/typed_pointer_001/' + prefix + str(seed) + '/collected/results/artifacts/' + phase + '_predictions.json')
                raw = path.read_bytes(); predictions = json.loads(raw)['predictions']
                if len(predictions) != 564 or {p['record_id'] for p in predictions} != set(rows):
                    raise RuntimeError('PREDICTION_REGISTRY_COVERAGE:' + str(path))
                counts = Counter()
                for prediction in predictions:
                    row = rows[prediction['record_id']]
                    public = course._public(material['bank'], row['source_world_id'])
                    query = row['query']; answer = prediction['answer']
                    key = source.digest([public, query, answer])
                    if key not in checks:
                        a = old.check_answer(public, query, answer)
                        b = new.check_answer(public, query, answer)
                        checks[key] = (a['correct'], b['correct'])
                        reports['unique_check_inputs'] += 1
                    else:
                        reports['reused_identical_check_inputs'] += 1
                    a, b = checks[key]
                    if a != b:
                        reports['check_mismatches'].append([study, seed, phase, prediction['record_id']])
                    counts['correct' if b else 'incorrect'] += 1
                    reports['predictions'] += 1
                reports['prediction_files'].append({'study': study, 'seed': seed, 'phase': phase,
                    'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'counts': dict(counts)})
                reports['elapsed_seconds'] = time.monotonic() - started
                save('compatibility.json', reports); print(study, seed, phase, dict(counts), flush=True)
    if verify_inputs() != before:
        raise RuntimeError('INPUT_MANIFEST_CHANGED')
    reports.update(status='PASS' if reports['predictions'] == 6768 and not any(reports[k] for k in (
        'target_mismatches', 'witness_mismatches', 'slot_mismatches', 'check_mismatches')) else 'FAIL',
        elapsed_seconds=time.monotonic()-started, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save('compatibility.json', reports)
    print(json.dumps({k:reports[k] for k in ('status','target_records','slot_plans','predictions','elapsed_seconds')}))
    if reports['status'] != 'PASS':
        raise SystemExit(1)


def family(n, domain, shape=0):
    labels = tuple('Node%d' % i for i in range(n))
    edges = [(i, i+1) for i in range(n-1)] if shape == 0 else [(0,1),(1,2),(2,3),(0,4)]
    return {'family_id': 'stage2-bench:' + domain, 'domain': domain, 'archetype': 'unused',
            'rendering': 0, 'kind': 'declared kind', 'labels': labels,
            'branches': tuple({'source':labels[a],'target':labels[b]} for a,b in edges),
            'split':'training', 'setting':'declared setting', 'function':'declared function'}


def benchmark():
    verify_inputs()
    from cas_meta2.typed_teaching import answers, checker_v2 as new, source
    started = time.monotonic(); max_permutations = 0; total_permutations = 0
    for index in range(1000):
        focus = family(5, 'focus-' + str(index))
        bank = source.freeze_bank([focus, family(5,'match-'+str(index)), family(5,'decoy-'+str(index),1)])
        public = source.public_source(source.compile_source(focus, bank=bank))
        query = answers.compile_query(public, kind='analogy', arguments={})
        target = new.derive_target(public, query)
        count = sum(r['permutations_checked'] for r in target['coverage']['decisions'])
        max_permutations = max(max_permutations, count); total_permutations += count
        if index % 100 == 0: print('benchmark', index, flush=True)
    report = {'schema':'helm.stage2-aws-benchmark/1','questions':1000,'nodes_per_world':5,
              'worlds_in_each_bank':3,'generated_unique_source_questions':True,
              'maximum_actual_permutations_per_question':max_permutations,
              'total_permutations_checked':total_permutations,
              'theoretical_six_node_64_world_maximum':46080,
              'elapsed_seconds':time.monotonic()-started,
              'device':'AWS t3.large CPU; one process; CPUQuota=100%',
              'local_cpu_measurement':'NOT_RUN_OWNER_SELECTED_AWS',
              'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    save('performance.json',report); print(json.dumps(report))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['compatibility','benchmark'])
    args=parser.parse_args()
    if args.mode=='compatibility': compatibility()
    else: benchmark()
