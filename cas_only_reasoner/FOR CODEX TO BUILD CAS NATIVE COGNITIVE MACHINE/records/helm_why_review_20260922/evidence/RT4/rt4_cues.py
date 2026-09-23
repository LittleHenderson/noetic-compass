"""RT4 structural question: does the VIA node follow the common-neighbour cue or a node-local cue?
Definitions fixed in PRE_RUN_DEFINITIONS.txt before this was run. Usage: rt4_cues.py <phase> [held]"""
import sys
from rt4_common import *
LOCAL = ['RL', 'RF', 'PP', 'PC', 'HPR']
SECONDARY = ['PP_unique', 'PC_unique', 'LPR']


def analyse(phase, runs):
    rows = []   # (run, rid, via, cues, meta)
    for ver, seed, d in runs:
        P = preds(d, phase)
        for rid, p in P.items():
            if p['answer']['kind'] != 'reach':
                continue
            v = via_rank(p)
            if v is None:
                continue
            c, m = cues(rid)
            rows.append(((ver, seed), rid, v, c, m))
    return rows


def share(a, n):
    return '%d/%d = %s' % (a, n, (repr(a / n) if n else 'undefined'))


def summarize(rows, cue_list, title):
    print('==', title, '| VIA-answered reach record x run pairs:', len(rows), '| distinct records:', len({r[1] for r in rows}))
    for k in ['CN'] + LOCAL:
        dd = [r for r in rows if r[3][k] is not None]
        print('   overall agreement VIA==%-4s %s' % (k, share(sum(r[2] == r[3][k] for r in dd), len(dd))))
    print('   VIA pointing at an argument node: %d' % sum(r[2] in (r[4]['whole'], r[4]['part']) for r in rows))
    union = set()
    res = {}
    for k in cue_list:
        D = [r for r in rows if r[3]['CN'] is not None and r[3][k] is not None and r[3]['CN'] != r[3][k]]
        drec = {r[1] for r in D}
        dq = {r[4]['qid'] for r in D}
        if k in LOCAL:
            union |= drec
        a_cn = sum(r[2] == r[3]['CN'] for r in D)
        a_k = sum(r[2] == r[3][k] for r in D)
        res[k] = (len(D), len(drec), a_cn, a_k)
        print('   D_%-9s pairs %3d | distinct records %3d | distinct questions %3d | VIA==CN %s | VIA==%s %s' % (
            k, len(D), len(drec), len(dq), share(a_cn, len(D)), k, share(a_k, len(D))))
    print('   distinct records in union of D_k over the five node-local cues:', len(union))
    return res, union


def verdict(res, union):
    if len(union) < 5:
        return 'INCONCLUSIVE (union of disagreement records %d < 5)' % len(union)
    testable = {k: v for k, v in res.items() if k in LOCAL and v[1] >= 5}
    untestable = [k for k in LOCAL if k not in testable]
    short = [k for k, (n, nr, acn, ak) in testable.items() if ak / n >= 0.80]
    struct = all(acn / n >= 0.80 and ak / n <= 0.30 for k, (n, nr, acn, ak) in testable.items())
    if struct and testable:
        v = 'STRUCTURAL'
    elif short:
        v = 'SHORTCUT via ' + ','.join(short)
    else:
        v = 'MIXED'
    return '%s (testable cues %s; untestable %s)' % (v, sorted(testable), untestable)


if __name__ == '__main__':
    phase = sys.argv[1] if len(sys.argv) > 1 else 'course_p10'
    rows = analyse(phase, RUNS)
    res, union = summarize(rows, LOCAL + SECONDARY, 'POOLED six runs, %s, all splits' % phase)
    print('   VERDICT (pooled, pre-registered rule):', verdict(res, union))
    for run in RUNS:
        rr = [r for r in rows if r[0] == run[:2]]
        res_r, un_r = summarize(rr, LOCAL, 'run Helm %s seed %s, %s' % (run[0], run[1], phase))
        print('   verdict (this run only):', verdict(res_r, un_r))
    hrows = [r for r in rows if r[4]['split'] == 'held']
    res_h, un_h = summarize(hrows, LOCAL + SECONDARY, 'POOLED six runs, %s, HELD records only (secondary)' % phase)
    print('   verdict (held only, secondary):', verdict(res_h, un_h))
