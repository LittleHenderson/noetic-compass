"""A7 bounded final-judge record verification. Standard library; no model imports."""
import collections
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import zipfile
from fractions import Fraction

START = time.perf_counter()
WATCHDOG = threading.Timer(115, lambda: os._exit(124))
WATCHDOG.daemon = True
WATCHDOG.start()
OUT = Path(__file__).resolve().parent
REC = OUT.parent.parent
WD = REC.parents[3]
MANIFEST = json.loads((REC / 'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
PACK = Path(r'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-research') / MANIFEST['cncm_relative_path'] / 'records/helm_failure_research_20260922'
FINGERPRINTS = {}
MEMBERS = []
CACHE = {}
SOURCE = {}
RESULT = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original(row):
    path = Path(row['path'])
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256_raw'], str(path)
    FINGERPRINTS[str(path)] = row
    return raw


def artifact(subject, name):
    rows = [x for x in subject['artifacts'] if Path(x['path']).name == name]
    assert len(rows) == 1, name
    key = rows[0]['path']
    if key not in CACHE:
        raw = original(rows[0])
        CACHE[key] = [json.loads(x) for x in raw.decode('utf-8').splitlines()] if name.endswith('.jsonl') else json.loads(raw)
    return CACHE[key]


def source_zip(subject):
    row = next(x for x in subject['artifacts'] if Path(x['path']).name == 'source.zip')
    return zipfile.ZipFile(io.BytesIO(original(row))), row


def member(subject, archive, archive_row, suffix):
    names = [n for n in archive.namelist() if n.endswith(suffix)]
    assert len(names) == 1, suffix
    name = names[0]
    raw = archive.read(name)
    # The manifest lists a representative member inventory per version, and
    # a separately fingerprinted full ZIP for each seed. Check both identities.
    package = next(p for p in MANIFEST['source_packages'] if p['version'] == subject['version'])
    row = next(r for r in package['members'] if r['member'] == name)
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    MEMBERS.append({'source_commit': subject['source_commit'], 'archive': archive_row['path'], **row})
    return raw


def nodes(world):
    return sorted(n['ref'] for n in world['nodes'])


def edges(world):
    return {(e['source'], e['target']) for e in world['contains']}


def mapping(left, right, flags=False):
    if len(left['nodes']) != len(right['nodes']) or len(left['contains']) != len(right['contains']):
        return None
    for perm in itertools.permutations(nodes(right)):
        match = dict(zip(nodes(left), perm))
        if {(match[u], match[v]) for u, v in edges(left)} != edges(right):
            continue
        if flags and (match[left['declared_whole']] != right['declared_whole'] or
                      [match[n] for n in left['declarations']['participants']] != right['declarations']['participants']):
            continue
        return match
    return None


def reach_target(world, query):
    adj = {n: sorted(v for u, v in edges(world) if u == n) for n in nodes(world)}
    start, end = query['arguments']['whole'], query['arguments']['part']
    def path_from(begin):
        queue = collections.deque([[begin]])
        seen = {begin}
        while queue:
            path = queue.popleft()
            if path[-1] == end:
                return path
            for child in adj[path[-1]]:
                if child not in seen:
                    seen.add(child)
                    queue.append(path + [child])
        return None
    if end in adj[start]:
        return {'state': 'DIRECT', 'via': None}, [start, end]
    if query['rule'] == 'first_direct_constituent_lexical_v1':
        for first in adj[start]:
            suffix = path_from(first)
            if suffix:
                return {'state': 'VIA', 'via': first}, [start] + suffix
    else:
        assert query['rule'] == 'bfs_immediate_predecessor_lexical_v1'
        path = path_from(start)
        if path:
            return {'state': 'VIA', 'via': path[-2]}, path
    return {'state': 'ABSENT', 'via': None}, None


# Bind each subject to its own saved source/data. Nothing from the ZIP is executed.
COURSE = DEV = None
for index, subject in enumerate(MANIFEST['subjects']):
    archive, archive_row = source_zip(subject)
    c = member(subject, archive, archive_row, 'checks_002/public_course.json')
    d = member(subject, archive, archive_row, 'development_001/compact_development.json')
    if COURSE is None:
        COURSE, DEV = c, d
    assert c == COURSE and d == DEV
    if index in (0, 3):
        for name in ['pointer_learner.py', 'pointer_inputs.py', 'checker.py', 'slots.py', 'answers.py']:
            SOURCE[(index, name)] = member(subject, archive, archive_row, 'typed_teaching/' + name).decode('utf-8')
COURSE, DEV = json.loads(COURSE), json.loads(DEV)
REG = {r['record_id']: r for r in COURSE['registry']}
WORLDS = {w['world_id']: w for w in COURSE['bank']['worlds']}


def check_gate():
    results = []
    for subject in MANIFEST['subjects']:
        gate = json.loads(original(subject['gate_reading']))
        conf = artifact(subject, 'config.json')
        assert conf['source_sha'] == subject['source_commit']
        assert gate['label'] == subject['recorded_label'] and gate['void_paths_taken'] == []
        saved = gate['seeds'][str(subject['seed'])]['G_LEARN_population']
        keys = saved['keys']
        assert len(keys) == 18 and sorted(keys) == sorted(gate['population']['question_ids'])
        assert sha(json.dumps(sorted(keys), sort_keys=True, separators=(',', ':')).encode()) == gate['population']['digest']
        held_ids = conf['design']['held_back_record_ids']
        assert len(held_ids) == 127
        pairs = []
        scoring = [artifact(subject, f'course_p{p:02d}_scoring.json') for p in (0, 10)]
        for qid in sorted(keys):
            grouped = [[r for r in sc['rows'] if r['query_id'] == qid and r['record_id'] in held_ids] for sc in scoring]
            assert grouped[0] and {r['record_id'] for r in grouped[0]} == {r['record_id'] for r in grouped[1]}
            pairs.append({'query_id': qid, 'kind': grouped[0][0]['kind'], 'world': REG[grouped[0][0]['record_id']]['query']['focus_world_id'],
                          'initial': all(r['correct'] for r in grouped[0]), 'final': all(r['correct'] for r in grouped[1]),
                          'record_ids': [r['record_id'] for r in grouped[0]]})
        gains = [x for x in pairs if not x['initial'] and x['final']]
        losses = [x for x in pairs if x['initial'] and not x['final']]
        b, c = len(gains), len(losses)
        p = Fraction(sum(math.comb(b+c, k) for k in range(b, b+c+1)), 2**(b+c))
        passed = b > c and p <= Fraction(1,100) and len({x['kind'] for x in gains}) >= 2 and len({x['world'] for x in gains}) >= 2
        assert (b,c,str(p),passed) == (saved['wrong_to_right'],saved['right_to_wrong'],saved['p_one_sided'],saved['passed'])
        families = {}
        for kind in gate['kinds']:
            qids = {REG[r]['query']['query_id'] for r in held_ids if REG[r]['query']['kind'] == kind}
            totals = [sum(all(r['correct'] for r in sc['rows'] if r['query_id'] == q and r['record_id'] in held_ids) for q in qids) for sc in scoring]
            families[kind] = {'initial':totals[0], 'final':totals[1], 'questions':len(qids)}
        results.append({'version':subject['version'],'seed':subject['seed'],'initial':sum(x['initial'] for x in pairs),'final':sum(x['final'] for x in pairs),
                        'gains':b,'losses':c,'p':str(p),'passed':passed,'historical_label':gate['label'],'pairs':pairs,'families':families,
                        'original_gate_test':saved,'population':gate['population']['by_kind']})
    return results


def check_lost_reach():
    f1 = json.loads((PACK/'agents/A6/F1_RESULTS.json').read_text(encoding='utf-8'))
    results = []
    for index,qid in [(3,'typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005'),(5,'typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f')]:
        subject = MANIFEST['subjects'][index]
        records = [r for r in REG.values() if r['query']['query_id'] == qid]
        for record in records:
            world = WORLDS[record['query']['focus_world_id']]
            target,path = reach_target(world,record['query'])
            options = ['ABSENT','DIRECT'] + [f'VIA_N{i}' for i in range(len(nodes(world)))]
            values = [{'state':'ABSENT','via':None},{'state':'DIRECT','via':None}] + [{'state':'VIA','via':n} for n in nodes(world)]
            correct = options[values.index(target)]
            for phase in (0,10):
                prediction = next(p for p in artifact(subject,f'course_p{phase:02d}_predictions.json')['predictions'] if p['record_id']==record['record_id'])
                assert len(prediction['scores']) == 1
                slot,scores = next(iter(prediction['scores'].items()))
                assert set(scores)==set(options) and all(math.isfinite(s) for s in scores.values())
                order = sorted(options,key=lambda s:-scores[s])
                answer = values[options.index(order[0])]
                assert prediction['answer']['value']==answer and prediction['decisions']['selected'][slot]==order[0]
                assert sum(s==scores[order[0]] for s in scores.values())==1
                peer = next(r for r in f1['rows'] if r['seed']==subject['seed'] and r['phase']==phase and r['record_id']==record['record_id'])
                assert prediction==peer['raw_prediction'] and target==peer['semantic_target'] and order==peer['candidate_rank_order']
                results.append({'seed':subject['seed'],'phase':phase,'record':record,'world':world,'target':target,'path':path,
                                'original_prediction':prediction,'order':order,'winner_minus_correct':scores[order[0]]-scores[correct],
                                'correct_rank':order.index(correct)+1})
    assert len(results)==10
    return results


def check_analogy():
    ids = ['typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e','typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a']
    aliases = {w:f'W{i}' for i,w in enumerate(sorted(WORLDS))}
    rows = []
    subject = MANIFEST['subjects'][4]
    predictions = artifact(subject,'course_p10_predictions.json')['predictions']
    for rid in ids:
        query = REG[rid]['query']; focus = WORLDS[query['focus_world_id']]
        assert query['arguments']=={}
        accepted = sorted(wid for wid,w in WORLDS.items() if w['declarations']['domain']!=focus['declarations']['domain'] and mapping(focus,w) is not None)
        prediction = next(p for p in predictions if p['record_id']==rid)
        assert len(prediction['scores'])==1
        scores = next(iter(prediction['scores'].values()))
        candidate_order = ['NO_MATCH'] + [aliases[w] for w in sorted(WORLDS)]
        assert set(candidate_order)==set(scores)
        top = max(candidate_order,key=lambda s:scores[s])
        assert next(iter(prediction['decisions']['selected'].values()))==top
        rows.append({'record':REG[rid],'focus_world':focus,'complete_accepted_world_ids':accepted,'raw_prediction':prediction,'candidate_order':candidate_order})
    left,right = rows
    a,b = set(left['complete_accepted_world_ids']),set(right['complete_accepted_world_ids'])
    assert len(a)==len(b)==9 and not a&b
    focuses = {r['record']['query']['focus_world_id'] for r in rows}
    assert not focuses & (a|b)
    scores = [next(iter(r['raw_prediction']['scores'].values())) for r in rows]
    comparisons = {wid:[s[aliases[wid]] for s in scores] for wid in sorted(a|b)}
    assert all(x==y for x,y in comparisons.values())
    all_nonfocus = [wid for wid in WORLDS if wid not in focuses]
    assert all(scores[0][aliases[w]]==scores[1][aliases[w]] for w in all_nonfocus)
    return {'subject_seed':subject['seed'],'source':subject['source_commit'],'rows':rows,'valid_candidate_score_pairs':comparisons,
            'equal_shared_nonfocus_columns':len(all_nonfocus),'contradiction':'Disjoint complete accepted sets have fixed common ranking and tie order; changed focus-only scores cannot solve both.'}


def check_graph_overlap():
    subject = MANIFEST['subjects'][5]
    conf = artifact(subject,'config.json')['design']
    batches = artifact(subject,'pass_01_batches.jsonl')
    trained_ids = {p['record_id'] for batch in batches for p in batch['predictions']}
    held_ids = set(conf['held_back_record_ids'])
    assert not trained_ids & held_ids and len(trained_ids)==358 and len(batches)==147
    trained_worlds = sorted({REG[r]['query']['focus_world_id'] for r in trained_ids})
    held_worlds = sorted({REG[r]['query']['focus_world_id'] for r in held_ids})
    assert len(trained_worlds)==19 and len(held_worlds)==5
    matches = []
    for h in held_worlds:
        found = [(t,mapping(WORLDS[h],WORLDS[t],True)) for t in trained_worlds]
        found = [(t,mp) for t,mp in found if mp is not None]
        assert found
        t,mp = found[0]
        matches.append({'held_world':WORLDS[h],'trained_world':WORLDS[t],'flags_preserved':True,'mapping':mp,'trained_match_count':len(found),
                        'actually_trained_record_ids':[r for r in sorted(trained_ids) if REG[r]['query']['focus_world_id']==t]})
    return {'subject_seed':subject['seed'],'trained_ids':sorted(trained_ids),'first_pass_batches':len(batches),'trained_focus_worlds':trained_worlds,'held_focus_worlds':held_worlds,'witnesses':matches}


def check_development():
    worlds = {w['world_id']:w for w in DEV['worlds']}
    targets = {}
    for row in DEV['records']:
        record = row['record'];q=record['query'];world=worlds[q['focus_world_id']]
        if q['kind']=='parts':
            target={'nodes':sorted(v for u,v in edges(world) if u==q['arguments']['whole'])};label='PARTS';path=None
        else:
            assert q['kind']=='reach'
            target,path=reach_target(world,q);label=target['state']
        targets[record['record_id']]={'query':q,'target':target,'class':label,'path':path}
    counts=dict(collections.Counter(t['class'] for t in targets.values()))
    assert counts=={'PARTS':6,'ABSENT':42,'DIRECT':8,'VIA':3}
    results=[]
    peer=json.loads((PACK/'agents/A3/F2_RESULTS.json').read_text(encoding='utf-8'))
    for subject in MANIFEST['subjects']:
        ends={}
        for phase in (0,10):
            predictions=artifact(subject,f'development_p{phase:02d}_predictions.json')['predictions']
            saved={r['record_id']:r for r in artifact(subject,f'development_p{phase:02d}_scoring.json')['rows']}
            assert len(predictions)==59 and {p['record_id'] for p in predictions}==set(targets)
            correct=collections.Counter({label:0 for label in counts});rows=[]
            for p in predictions:
                t=targets[p['record_id']];ok=p['answer']['value']==t['target']
                assert ok==saved[p['record_id']]['correct']
                correct[t['class']]+=ok
                rows.append({'record_id':p['record_id'],'answer':p['answer'],'correct':ok,'class':t['class']})
            ends[f'p{phase:02d}']={'correct':dict(correct),'all_correct':sum(correct.values()),'rows':rows}
        results.append({'version':subject['version'],'seed':subject['seed'],'endpoints':ends})
    assert peer['scoring_disagreements']==[]
    return {'targets':targets,'class_denominators':counts,'runs':results,'peer_result_read_sha256':sha((PACK/'agents/A3/F2_RESULTS.json').read_bytes())}


for function in (check_gate,check_lost_reach,check_analogy,check_graph_overlap,check_development):
    RESULT[function.__name__]=function()

# Read the frozen grader by commit; record original text, not a newer checkout.
EXCERPTS=[]
for row in MANIFEST['grading_sources'][:2]:
    proc=subprocess.run(['git','show',row['commit']+':'+row['repository_path']],cwd=WD,capture_output=True,timeout=10,check=True)
    raw=proc.stdout.replace(b'\r\n',b'\n');assert sha(raw)==row['sha256_lf']
    lines=raw.decode('utf-8').splitlines()
    EXCERPTS.append({'member':row['repository_path'],'commit':row['commit'],'sha256':sha(raw),'lines':{str(i):lines[i-1] for a,b in [(112,114),(283,338),(1142,1144)] for i in range(a,b+1)}})
RANGES={'pointer_learner.py':{0:[(993,1049),(1195,1213),(1300,1331),(1364,1366)],3:[(1045,1061),(1091,1156),(1303,1321),(1373,1422),(1484,1516),(1558,1565)]},
        'checker.py':{0:[(96,153),(200,237)]},'slots.py':{0:[(54,60),(94,107),(259,296),(335,348)]},
        'pointer_inputs.py':{0:[(339,421)]}}
for name, versions in RANGES.items():
    for index,ranges in versions.items():
        lines=SOURCE[(index,name)].splitlines()
        EXCERPTS.append({'member':name,'source_commit':MANIFEST['subjects'][index]['source_commit'],'sha256':sha(SOURCE[(index,name)].encode()),'lines':{str(i):lines[i-1] for a,b in ranges for i in range(a,b+1)}})
RESULT['source_excerpts']=EXCERPTS
RESULT['original_file_fingerprints']=list(FINGERPRINTS.values())
RESULT['zip_member_fingerprints']=MEMBERS
RESULT['execution']={'python':sys.version,'elapsed_seconds':time.perf_counter()-START,'functions':5,'executions':1,'repeat_executions':0,'neural_execution':False,
                     'manifest_sha256':sha((REC/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_bytes()),'probe_sha256':sha(Path(__file__).read_bytes()),
                     'working_directory':str(WD),'original_file_count':len(FINGERPRINTS),'source_member_observations':len(MEMBERS)}
(OUT/'ORIGINAL_RECORD_CHECKS.json').write_text(json.dumps(RESULT,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
WATCHDOG.cancel()
print(json.dumps({'status':'PASS','execution':RESULT['execution'],'output_sha256':sha((OUT/'ORIGINAL_RECORD_CHECKS.json').read_bytes()),
                  'gates':[{k:r[k] for k in ['version','seed','initial','final','gains','losses','p','passed']} for r in RESULT['check_gate']],
                  'analogy_sets':[len(r['complete_accepted_world_ids']) for r in RESULT['check_analogy']['rows']],
                  'overlap_counts':[w['trained_match_count'] for w in RESULT['check_graph_overlap']['witnesses']],
                  'development':[{ 'version':r['version'],'seed':r['seed'],'endpoints':{k:v['correct'] for k,v in r['endpoints'].items()}} for r in RESULT['check_development']['runs']]},indent=2))
