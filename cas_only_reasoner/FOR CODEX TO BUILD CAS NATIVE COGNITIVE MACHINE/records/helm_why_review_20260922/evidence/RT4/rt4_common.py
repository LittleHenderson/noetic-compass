"""RT4 shared loaders. Read-only, stdlib only, no torch. Public bank only (never private_targets / sealed)."""
import json
from pathlib import Path
from collections import defaultdict
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT / 'records/typed_pointer_001'
J = lambda p: json.loads(Path(p).read_bytes())
RUNS = [('2.0', '20260917', 'receipt_20260917'), ('2.0', '20260918', 'receipt_20260918'), ('2.0', '20260919', 'receipt_20260919'),
        ('1.0', '20260917', 'receipt_helm1_certified_20260917'), ('1.0', '20260918', 'receipt_helm1_certified_20260918'),
        ('1.0', '20260919', 'receipt_helm1_certified_20260919')]
course = J(ROOT / 'records/typed_course_001/checks_002/public_course.json')
W = {w['world_id']: w for w in course['bank']['worlds']}
REG = {r['record_id']: r for r in course['registry']}
rk = lambda ref: int(ref.split('/')[-1][1:])
pm = J(T / 'receipt_20260917/collected/results/artifacts/protocol_material.json')
SPLIT = {**{r: 'held' for r in pm['held_back_record_ids']}, **{r: 'trained' for r in pm['trained_record_ids']},
         **{r: 'excluded' for r in pm['excluded_record_ids']}}


def world(wid):
    w = W[wid]
    n = len(w['nodes'])
    E = set((rk(e['source']), rk(e['target'])) for e in w['contains'])
    prank = {rk(ref): i + 1 for i, ref in enumerate(w['declarations']['participants'])}
    return n, E, prank


def preds(run_dir, name):
    return {p['record_id']: p for p in J(T / run_dir / 'checkpoints' / (name + '_predictions.json'))['predictions']}


def scoring(run_dir, name):
    return {r['record_id']: r for r in J(T / run_dir / 'checkpoints' / (name + '_scoring.json'))['rows']}


def cues(rid):
    q = REG[rid]['query']
    n, E, prank = world(q['focus_world_id'])
    wh, pa = rk(q['arguments']['whole']), rk(q['arguments']['part'])
    C = [x for x in range(n) if x not in (wh, pa)]
    indeg = defaultdict(int)
    outdeg = defaultdict(int)
    for s, t in E:
        outdeg[s] += 1
        indeg[t] += 1
    cn = [x for x in C if (wh, x) in E and (x, pa) in E]
    pp = [x for x in C if (x, pa) in E]
    pc = [x for x in C if indeg[x] >= 1 and outdeg[x] >= 1]
    parts = [x for x in C if prank.get(x, 0) > 0]
    out = {
        'CN': min(cn) if cn else None,
        'RL': max(C) if C else None,
        'RF': min(C) if C else None,
        'PP': min(pp) if pp else None,
        'PC': min(pc) if pc else None,
        'HPR': max(parts, key=lambda x: prank[x]) if parts else None,
        # secondary variants, not used in the verdict
        'PP_unique': pp[0] if len(pp) == 1 else None,
        'PC_unique': pc[0] if len(pc) == 1 else None,
        'LPR': min(parts, key=lambda x: prank[x]) if parts else None,
    }
    meta = dict(n=n, whole=wh, part=pa, C=C, n_cn=len(cn), n_pp=len(pp), n_pc=len(pc), direct=(wh, pa) in E,
                world=q['focus_world_id'], qid=q['query_id'], rule=q['rule'], split=SPLIT.get(rid), E=E, prank=prank)
    return out, meta


def via_rank(p):
    v = p['answer']['value']
    if v.get('state') != 'VIA' or v.get('via') is None:
        return None
    return rk(v['via'])
