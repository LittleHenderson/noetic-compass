"""Bounded stdlib source/record/algebra probes. Never loads or runs a neural model."""
import ast
import collections
import hashlib
import itertools
import json
import math
import pathlib
import sys
import time

START = time.monotonic()
BASE = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
MANIFEST = json.loads((BASE / 'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
VERIFIED = []


def checked_json(entry):
    raw = pathlib.Path(entry['path']).read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    assert h == entry['sha256_raw'], entry['path']
    VERIFIED.append({'path': entry['path'], 'sha256': h, 'bytes': len(raw)})
    return json.loads(raw)


def member_function(version, name):
    p = OUT / 'source_copies' / version / 'pointer_learner.py'
    tree = ast.parse(p.read_text(encoding='utf-8'))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    # Remove docstrings; source comments are deliberately not evidence of executable behavior.
    if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        node.body = node.body[1:]
    return ast.dump(node, include_attributes=False), [node.lineno, node.end_lineno]


def test_source_identity():
    rows = json.loads((OUT / 'source_copy_manifest.json').read_text())
    extra = json.loads((OUT / 'supplemental_source_manifest.json').read_text())
    for index, package in enumerate(MANIFEST['source_packages'], 1):
        raw = pathlib.Path(package['package']['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == package['package']['sha256_raw']
        for r in [r for r in rows + extra if r['version'] == package['version']]:
            p = OUT / 'source_copies' / f'helm{index}' / pathlib.PurePosixPath(r['member']).name
            assert hashlib.sha256(p.read_bytes()).hexdigest() == r['sha256']
    funcs = {}
    for name in ['_graph_blocks', '_query_vector', '_encode_query', '_pooled_worlds', '_world_scores', '_declaration_embeddings']:
        one, a = member_function('helm1', name)
        two, b = member_function('helm2', name)
        assert one == two, name
        funcs[name] = {'executable_ast_equal': True, 'helm1_lines': a, 'helm2_lines': b}
    return {'source_packages_verified': 2, 'source_members_verified': len(rows + extra), 'unchanged_functions': funcs}


def test_dependency_paths():
    # This is a symbolic dependency-set calculation, not a learned forward pass.
    neighbors = [{1}, {0, 2}, {1, 3}, {2}]
    initial = [{i} for i in range(4)]
    frozen = [x | set().union(*(initial[j] for j in neighbors[i])) for i, x in enumerate(initial)]
    recursive = initial
    traces = []
    for r in range(1, 9):
        recursive = [x | set().union(*(recursive[j] for j in neighbors[i])) for i, x in enumerate(recursive)]
        traces.append({'round': r, 'helm1_node0_raw_row_dependencies': sorted(frozen[0]),
                       'helm2_node0_raw_row_dependencies': sorted(recursive[0])})
    assert traces[-1]['helm1_node0_raw_row_dependencies'] == [0, 1]
    assert traces[2]['helm2_node0_raw_row_dependencies'] == [0, 1, 2, 3]
    return {'input_case': 'four-node path 0->1->2->3; raw feature row provenance only', 'trace': traces,
            'scope': 'possible local dependencies; no claim that learned weights preserve or use them'}


def canon(world):
    refs = sorted(n['ref'] for n in world['nodes'])
    pos = {r: i for i, r in enumerate(refs)}
    edges = [(pos[e['source']], pos[e['target']]) for e in world['contains']]
    return (len(refs), min(tuple(sorted((p[a], p[b]) for a, b in edges)) for p in itertools.permutations(range(len(refs)))))


COURSE = checked_json(next(a for a in MANIFEST['additional_required_sources'] if a['path'].endswith('public_course.json')))
WORLDS = {w['world_id']: w for w in COURSE['bank']['worlds']}
WORLD_IDS = sorted(WORLDS)
RECORDS = {r['record_id']: r for r in COURSE['registry']}
CANON = {key: canon(world) for key, world in WORLDS.items()}


def valid_analogy(record):
    f = record['query']['focus_world_id']
    return sorted(w for w in WORLD_IDS if CANON[w] == CANON[f] and WORLDS[w]['declarations']['domain'] != WORLDS[f]['declarations']['domain'])


def test_analogy_constraints():
    rows = [r for r in RECORDS.values() if r['query']['kind'] == 'analogy']
    assert all(r['query']['arguments'] == {} for r in rows)
    pair = None
    for a, b in itertools.combinations(rows, 2):
        fa, fb = a['query']['focus_world_id'], b['query']['focus_world_id']
        va, vb = valid_analogy(a), valid_analogy(b)
        if va and vb and not (set(va) & set(vb)) and not ({fa, fb} & (set(va) | set(vb))):
            pair = [a, b]
            break
    assert pair is not None
    witness = []
    for row in pair:
        f = row['query']['focus_world_id']
        witness.append({'record_id': row['record_id'], 'query': row['query'], 'focus_world': WORLDS[f],
                        'valid_world_ids': valid_analogy(row), 'canonical_graph': CANON[f]})
    return {'registry_analogy_cases': len(rows), 'bank_worlds': len(WORLDS),
            'all_queries_have_no_node_arguments': True, 'witness': witness,
            'claim': 'Two correct-set lists are nonempty and disjoint; all candidates in both lists are non-focus in both questions. Their relative scores are source-independent in both pinned implementations. A deterministic common candidate order cannot satisfy both questions.'}


def test_saved_scores():
    results = []
    for subject in MANIFEST['subjects']:
        for filename in ['course_p00_predictions.json', 'course_p10_predictions.json']:
            entry = next(a for a in subject['artifacts'] if pathlib.Path(a['path']).name == filename)
            saved = checked_json(entry)
            predictions = saved['predictions']
            buckets = collections.defaultdict(list)
            analogy_correct = 0
            choices = collections.Counter()
            correspondence_equal, correspondence_total = 0, 0
            for p in predictions:
                row = RECORDS[p['record_id']]
                kind, focus = row['query']['kind'], row['query']['focus_world_id']
                if kind == 'analogy':
                    assert len(p['scores']) == 1
                    scores = next(iter(p['scores'].values()))
                    for symbol, value in scores.items():
                        if symbol != 'NO_MATCH':
                            world_id = WORLD_IDS[int(symbol[1:])]
                            if world_id != focus:
                                buckets[symbol].append(value)
                    choice = p['answer']['value']['world_id']
                    choices[str(choice)] += 1
                    valid = valid_analogy(row)
                    analogy_correct += (choice in valid) if valid else choice is None
                if kind == 'correspondence':
                    mapping = [v for v in p['scores'].values() if all(k.startswith('N') and k[1:].isdigit() for k in v)]
                    correspondence_total += 1
                    correspondence_equal += bool(mapping) and all(v == mapping[0] for v in mapping[1:])
            spans = {k: max(v) - min(v) for k, v in buckets.items()}
            # Exact equality is expected for saved values if the source trace is complete.
            assert all(span == 0 for span in spans.values()), (subject['version'], subject['seed'], filename, max(spans.values()))
            if subject['version'] == 'Helm 1.0':
                assert correspondence_equal == correspondence_total
            results.append({'version': subject['version'], 'seed': subject['seed'], 'artifact': filename,
                            'predictions': len(predictions), 'analogy_cases': sum(choices.values()),
                            'analogy_correct_rederived_rule': analogy_correct, 'choices': dict(choices),
                            'nonfocus_candidate_columns': len(spans), 'max_saved_score_range': max(spans.values()),
                            'correspondence_cases': correspondence_total, 'all_source_rows_identical_cases': correspondence_equal})
    return {'artifacts': results, 'caveat': 'Existing saved numeric outputs only; no model rerun. Analogy correctness independently applies the pinned graph-isomorphism/domain rule and does not recertify a gate.'}


def logsumexp(values):
    top = max(values)
    return top + math.log(sum(math.exp(x - top) for x in values))


def test_bijection_score_algebra():
    results = []
    for n in [2, 3, 4]:
        perms = list(itertools.permutations(range(n)))
        row = list(range(1, n + 1))
        h1 = [sum(row[p[i]] for i in range(n)) for p in perms]
        assert len(set(h1)) == 1
        raw = [[float((i * 7 + j * 3 + i * j * 2) % 11) for j in range(n)] for i in range(n)]
        scores = [r[:] for r in raw]
        for _ in range(3):
            scores = [[x - logsumexp(r) for x in r] for r in scores]
            col = [logsumexp([scores[i][j] for i in range(n)]) for j in range(n)]
            scores = [[x - col[j] for j, x in enumerate(r)] for r in scores]
        sums0 = [sum(raw[i][p[i]] for i in range(n)) for p in perms]
        sums1 = [sum(scores[i][p[i]] for i in range(n)) for p in perms]
        l0, l1 = logsumexp(sums0), logsumexp(sums1)
        error = max(abs((a - l0) - (b - l1)) for a, b in zip(sums0, sums1))
        assert error < 1e-12
        results.append({'n': n, 'permutation_cases': len(perms), 'helm1_unique_joint_mapping_sums': len(set(h1)),
                        'sinkhorn_three_steps_max_log_probability_error': error})
    return {'matrices': results, 'scope': 'Non-neural score algebra, not trained-network behavior. For complete bijections row/column additive normalizers contribute the same total to every candidate and cancel in the decoder mapping normalization.'}


TESTS = [test_source_identity, test_dependency_paths, test_analogy_constraints, test_saved_scores, test_bijection_score_algebra]
RESULTS = {}
for test in TESTS:
    assert time.monotonic() - START < 110, 'BOUND_EXCEEDED'
    RESULTS[test.__name__] = test()
receipt = {'status': 'PASS', 'python': sys.version, 'neural_execution': False,
           'test_functions': len(TESTS), 'suite_executions': 1, 'repeat_executions': 0,
           'elapsed_seconds': time.monotonic() - START, 'verified_artifacts': VERIFIED, 'results': RESULTS}
(OUT / 'probe_results.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'status': receipt['status'], 'test_functions': len(TESTS), 'elapsed_seconds': receipt['elapsed_seconds'],
                  'saved_artifacts': len(RESULTS['test_saved_scores']['artifacts']),
                  'witness_records': [x['record_id'] for x in RESULTS['test_analogy_constraints']['witness']],
                  'saved_score_summary': [{k: v for k, v in row.items() if k != 'choices'} for row in RESULTS['test_saved_scores']['artifacts']]}, indent=2))
