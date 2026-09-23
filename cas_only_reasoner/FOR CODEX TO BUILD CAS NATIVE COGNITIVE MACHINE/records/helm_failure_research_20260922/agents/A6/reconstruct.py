"""Independent saved-record arithmetic; no project modules, checkpoint loads or model calls."""
import hashlib, itertools, json, sys, time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

START = time.monotonic()
BASE = Path(__file__).resolve().parent
MANIFEST = BASE.parents[1] / 'SOURCE_AND_EVIDENCE_MANIFEST.json'
m = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
identities = {}
for s in m['subjects']:
    for a in s['artifacts'] + [s['gate_reading']]: identities[str(Path(a['path']))] = a
for a in m['additional_required_sources']: identities[str(Path(a['path']))] = a
reads = {}

def read(path):
    assert time.monotonic() - START < 115, '120-second bound approaching'
    p = Path(path)
    blob = p.read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    expect = identities[str(p)]
    assert sha == expect['sha256_raw'], str(p)
    assert len(blob) == expect['bytes'], str(p)
    reads[str(p)] = {'sha256': sha, 'bytes': len(blob)}
    return json.loads(blob.decode('utf-8-sig'))

def fair_coin_tail(gains, losses):
    # Exhaust all bit patterns instead of copying the historical combination-sum implementation.
    n = gains + losses
    assert n <= 18
    successes = sum(sum(bits) >= gains for bits in itertools.product((0, 1), repeat=n))
    return Fraction(successes, 2 ** n)

course_path = next(a['path'] for a in m['additional_required_sources'] if a['path'].endswith('public_course.json'))
course = read(course_path)
registry = {r['record_id']: r for r in course['registry']}
all_rows = []
lost_raw = []
for subject in m['subjects']:
    gate = read(subject['gate_reading']['path'])
    population = set(gate['label_key_population'])  # Scope deliberately fixed to the saved gate population.
    assert len(population) == 18
    before_path = Path(subject['receipt_root']) / 'checkpoints/course_p00_scoring.json'
    after_path = Path(subject['receipt_root']) / 'checkpoints/course_p10_scoring.json'
    phases = [read(before_path), read(after_path)]
    records = {q: sorted(rid for rid, r in registry.items() if r['query']['query_id'] == q) for q in population}
    assert all(records.values())
    outcomes = []
    for phase in phases:
        scored = {r['record_id']: r for r in phase['rows']}
        assert len(scored) == len(phase['rows'])
        outcomes.append({q: all(scored[rid]['correct'] for rid in ids) for q, ids in records.items()})
    transitions = []
    for q in sorted(population):
        query = registry[records[q][0]]['query']
        transitions.append({'query_id': q, 'kind': query['kind'], 'world': query['focus_world_id'],
            'before': outcomes[0][q], 'after': outcomes[1][q], 'record_ids': records[q]})
    gains = [t for t in transitions if not t['before'] and t['after']]
    losses = [t for t in transitions if t['before'] and not t['after']]
    p = fair_coin_tail(len(gains), len(losses))
    kinds = sorted({t['kind'] for t in gains})
    worlds = sorted({t['world'] for t in gains})
    passed = len(gains) > len(losses) and p <= Fraction(1,100) and len(kinds) >= 2 and len(worlds) >= 2
    printed = gate['seeds'][str(subject['seed'])]['G_LEARN_population']
    assert (len(gains), len(losses), str(p), passed) == (printed['wrong_to_right'],printed['right_to_wrong'],printed['p_one_sided'],printed['passed'])
    assert kinds == printed['improved_kinds'] and worlds == printed['improved_worlds']
    row = {'version':subject['version'],'seed':subject['seed'],'source_commit':subject['source_commit'],
        'n_questions':18,'record_cases':sum(map(len,records.values())),'gains':len(gains),'losses':len(losses),
        'p':str(p),'p_decimal':float(p),'passed':passed,'matches_saved_gate':True,'improved_kinds':kinds,
        'improved_worlds':worlds,'transitions':transitions,'saved_label':gate['label'],
        'p_if_lost_question_were_retained':str(fair_coin_tail(len(gains),0)) if losses else None}
    all_rows.append(row)
    if losses:
        preds = [read(Path(subject['receipt_root']) / ('checkpoints/course_p%02d_predictions.json' % phase)) for phase in (0,10)]
        tables = [{r['record_id']:r for r in phase['predictions']} for phase in preds]
        score_tables = [{r['record_id']:r for r in phase['rows']} for phase in phases]
        for loss in losses:
            for rid in loss['record_ids']:
                lost_raw.append({'version':subject['version'],'seed':subject['seed'],'query_id':loss['query_id'],
                    'packet':registry[rid], 'before_prediction':tables[0][rid], 'after_prediction':tables[1][rid],
                    'before_score':score_tables[0][rid], 'after_score':score_tables[1][rid]})
    print(json.dumps({k:row[k] for k in ('version','seed','gains','losses','p','passed','record_cases')}, sort_keys=True))

# Save source excerpts with exact existing line numbers; never execute the historic checker.
grader = next(a['path'] for a in m['additional_required_sources'] if a['path'].endswith('evaluate_gates.py'))
p = Path(grader); blob = p.read_bytes(); expected = identities[str(p)]
assert hashlib.sha256(blob).hexdigest() == expected['sha256_raw']
reads[str(p)] = {'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob)}
lines = blob.decode('utf-8').splitlines()
ranges = [(110,115),(283,338),(740,764),(1045,1078)]
(BASE/'source_lines.txt').write_text('Source: '+grader+'\nSHA256: '+reads[str(p)]['sha256']+'\n'+'\n'.join(f'{n}: {lines[n-1]}' for lo,hi in ranges for n in range(lo,hi+1))+'\n',encoding='utf-8')
(BASE/'reconstruction.json').write_text(json.dumps({'rows':all_rows,'reading_fingerprints':reads,
    'manifest_sha256':hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-START,
    'test_functions':0,'diagnostic_functions':2,'diagnostic_executions':1,'seed_cases':6,
    'question_transition_cases':108,'execution_scope':'Saved correctness aggregation and independent exact coin enumeration; not checker rerun or new model run.'},indent=2)+'\n',encoding='utf-8')
(BASE/'lost_answers.json').write_text(json.dumps(lost_raw,indent=2)+'\n',encoding='utf-8')
print('lost_record_rows='+str(len(lost_raw)))
