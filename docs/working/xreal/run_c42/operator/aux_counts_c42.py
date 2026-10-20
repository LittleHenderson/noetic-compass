"""Operator AUXILIARY counts for RUN_RESULT_XREAL_C42.md (not the reading; the verdict and words come only from
XREAL_READING.json). Runs AFTER the frozen reader, from the same fresh extract of the sealed zip, importing the frozen
package modules unchanged (score_xr, sample_xr, common_xr). Writes counts and item ids only; prints no exam text.

1. Coordinator's sensitivity line (custodian FLAG_FOR_HUMAN_REVIEW, carried forward): the published answerability draw
   (A-XR-16 seed text, never the owner's seed) is recomputed from the custodian's public frames exactly as the
   custodian's ovl.py did; the exam items whose source_id falls in that draw are identified by their exam item id (no
   content); then the R-ASIS and R-REBOUND tallies (FULL and every R arm) are given with and without those items, using
   the frozen score_xr.score_r on the same host records and keys.
2. 'asks' per arm (frozen score_xr.is_asking on the presented status) for Parts S and R, and the arithmetic check
   (items where HELM answered: value equal to the key's yield, and limiting equal).
3. Part F per kind: CAUGHT (found), CAUGHT and held (acted on CAUGHT worlds whose damaged object the probe touched),
   FALSE_ALARM on clean worlds, for every F arm (the frozen score_xr.f_class).

Usage: python -B -I -X utf8 aux_counts_c42.py <pkg dir> <MERGE_INPUT_XREAL.json> <custody frames dir> <out.json>"""
import hashlib
import json
import sys
from pathlib import Path

pkg, mi_path, frames, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(pkg))
from xreal import common_xr as C  # noqa: E402
from xreal import sample_xr as SM  # noqa: E402
from xreal import score_xr as S  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


mi = json.loads(mi_path.read_text(encoding='utf-8'))
exam = Path(mi['exam_dir'])
host = C.load_doc(mi['host'], mi['host_sha256'])
pins = json.loads((exam / C.PINS_NAME).read_text(encoding='utf-8'))
inputs_doc = C.load_doc(exam / C.INPUTS_NAME, pins['pins']['INPUTS']['sha256'])
keys = C.load_doc(exam / C.KEYS_NAME, pins['pins']['KEYS']['sha256'])['keys']
inputs = {it['id']: it for it in inputs_doc['items']}


def unit(uid):
    return ((host['units'].get(uid) or {}).get('result') or {})


# ---------------------------------------------------------------- 1. the published answerability draw overlap
r_all = SM.read_jsonl(frames / 'FRAME_R_PG.jsonl') + SM.read_jsonl(frames / 'FRAME_R_WB.jsonl')
idx = SM.PartnerIndex(r_all)
rb = [r for r in r_all if r['rebound_eligible'] and idx.full_partners(r)]
AN = SM.sample_r(rb, C.ANSWERABILITY_SEED_TEXT, 'XB', C.N_R_REBOUND, set(), idx, require_full=True)
drawn = set(str(a['id']) for _rk, a, _b in AN['chosen'])
overlap = {p: sorted(it['id'] for it in inputs_doc['items'] if it['part'] == p and str(it['source_id']) in drawn)
           for p in ('R_REBOUND', 'R_ASIS')}
excl = set(overlap['R_REBOUND']) | set(overlap['R_ASIS'])


def tally(recs, part_ids_excluded=frozenset()):
    t = {'items': 0, 'RIGHT': 0, 'WRONG': 0, 'UNDETERMINED': 0, 'NOT_SCORED': 0, 'asks': 0, 'answered': 0,
         'answered_value_exact': 0, 'answered_value_and_limiting_exact': 0, 'answer_keys': 0, 'answer_keys_right': 0}
    for r in recs:
        if r['id'] in part_ids_excluded:
            continue
        k = keys[r['id']]['key']
        sc = S.score_r(k, r)
        t['items'] += 1
        t[sc['score']] += 1
        st = sc['status']
        if S.is_asking(st):
            t['asks'] += 1
        if k['key'] == 'ANSWER':
            t['answer_keys'] += 1
            t['answer_keys_right'] += sc['score'] == 'RIGHT'
            if st in S.ANSWERING:
                turn = r['turns'][r['probe_index']]
                t['answered'] += 1
                from fractions import Fraction
                ok_v = turn['presented_value'] is not None and Fraction(str(turn['presented_value'])) == Fraction(str(k['yield']))
                t['answered_value_exact'] += ok_v
                t['answered_value_and_limiting_exact'] += ok_v and (k.get('tie') or turn['presented_limiting'] == k['limiting'])
    t['scored'] = t['RIGHT'] + t['WRONG'] + t['UNDETERMINED']
    return t


base = unit('XR_BASELINES').get('baselines') or {}
R = {}
for part, pname in (('RA', 'R_ASIS'), ('RB', 'R_REBOUND')):
    arms = {a: unit('XR_%s_%s' % (part, a)).get('records') or [] for a in ('FULL', 'FULL+EYE_SCAN', 'FULL+EYE_SCAN_REPLAY', '-VOICE')}
    for b in ('B-ASK', 'B-KEYCALC'):
        arms[b] = [x for x in base.get(b, []) if x['part'] == pname]
    R[pname] = {a: {'all_items': tally(rs), 'without_overlap': tally(rs, frozenset(overlap[pname]))} for a, rs in arms.items()}

# ---------------------------------------------------------------- 2. Part S asks per arm
s_arms = {a: unit('XR_S_' + a).get('records') or [] for a in ('FULL', 'FULL+EYE_SCAN', 'FULL+EYE_SCAN_REPLAY', '-ENGLISH_IN', '-VOICE')}
for b in ('B-ASK', 'B-KEYCALC', 'B-ECHO'):
    s_arms[b] = [x for x in base.get(b, []) if x['part'] == 'S']
S_aux = {}
for a, rs in s_arms.items():
    t = {'items': 0, 'RIGHT': 0, 'WRONG': 0, 'UNDETERMINED': 0, 'NOT_SCORED': 0, 'asks': 0, 'invented_number': 0,
         'writes_total': 0, 'by_key': {}}
    for r in rs:
        k = keys[r['id']]['key']
        sc = S.score_s(k, r, inputs[r['id']]['turns'][0])
        t['items'] += 1
        t[sc['score']] += 1
        t['asks'] += bool(sc['status'] and S.is_asking(sc['status']))
        t['invented_number'] += sc['invented'] is not None
        t['writes_total'] += sc['writes']
        bk = t['by_key'].setdefault(k['key'], {'items': 0, 'RIGHT': 0, 'WRONG': 0, 'UNDETERMINED': 0, 'NOT_SCORED': 0})
        bk['items'] += 1
        bk[sc['score']] += 1
    S_aux[a] = t

# ---------------------------------------------------------------- 3. Part F per kind
plan = unit('XR_FPLAN').get('plan') or {'sessions': {}, 'worlds': []}
F = {}
for arm in ('FULL', 'FULL+EYE_SCAN', 'FULL+EYE_SCAN_REPLAY', 'EYE_SCAN_REPORT_ONLY', 'CHECKLIST', 'WATCHDOG'):
    per = {}
    for r in unit('XR_F_' + arm).get('records') or []:
        if r.get('void'):
            c = {'class': 'VOID'}
        else:
            part = 'S' if r['session'].startswith('S:') else 'R'
            twin = (plan['sessions'].get(r['session']) or {}).get('twin')
            c = S.f_class(r, keys[r['session']]['key'], part, twin)
        k = per.setdefault(r['kind'], {'worlds': 0, 'classes': {}, 'caught': 0, 'caught_touched': 0, 'caught_touched_held': 0,
                                       'caught_held': 0, 'false_alarm': 0})
        k['worlds'] += 1
        k['classes'][c['class']] = k['classes'].get(c['class'], 0) + 1
        if c['class'] == 'CAUGHT':
            k['caught'] += 1
            k['caught_held'] += bool(c.get('held'))
            if c.get('caught_touched'):
                k['caught_touched'] += 1
                k['caught_touched_held'] += bool(c.get('held'))
        if c['class'] == 'FALSE_ALARM':
            k['false_alarm'] += 1
    F[arm] = per

doc = {'schema': 'helm.xreal.operator-aux-counts/1', 'not_the_reading': True,
       'reading_sha256': sha(mi_path.parent / 'XREAL_READING.json'),
       'frames_sha256': {n: sha(frames / n) for n in ('FRAME_R_PG.jsonl', 'FRAME_R_WB.jsonl')},
       'answerability_draw': {'seed_text': C.ANSWERABILITY_SEED_TEXT, 'frame': len(rb), 'drawn': len(AN['chosen'])},
       'overlap_item_ids': overlap, 'overlap_counts': {p: len(v) for p, v in overlap.items()},
       'R': R, 'S': S_aux, 'F': F}
out_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({'out': str(out_path), 'sha256': sha(out_path), 'overlap_counts': doc['overlap_counts']}))
