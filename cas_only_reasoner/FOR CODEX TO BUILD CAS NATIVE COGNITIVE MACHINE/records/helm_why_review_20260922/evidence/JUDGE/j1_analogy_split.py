# JUDGE spot check: analogy answers per run, split by trained / held / excluded (protocol_material.json). Pure JSON.
import json, collections, os
BASE = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001"
def load(p):
    with open(os.path.join(BASE, p), encoding='utf-8') as f:
        return json.load(f)
for ver, rec in (('2.0', 'receipt_%s'), ('1.0', 'receipt_helm1_certified_%s')):
    for seed in ('20260917', '20260918', '20260919'):
        ck = (rec % seed) + '/checkpoints/'
        pm = load(ck + 'protocol_material.json')
        side = {}
        for name, key in (('trained', 'trained_record_ids'), ('held', 'held_back_record_ids'), ('excluded', 'excluded_record_ids')):
            for rid in pm[key]:
                side[rid] = name
        p = load(ck + 'course_p10_predictions.json')['predictions']
        s = {r['record_id']: r['correct'] for r in load(ck + 'course_p10_scoring.json')['rows']}
        ans = collections.Counter(); tot = collections.Counter(); ok = collections.Counter()
        for x in p:
            if x['answer']['kind'] != 'analogy':
                continue
            rid = x['record_id']
            ans[x['answer']['value']['world_id'][6:14]] += 1
            sd = side.get(rid, 'unlisted'); tot[sd] += 1; ok[sd] += int(bool(s[rid]))
        print(ver, seed, 'analogy', sum(ans.values()), 'answers', dict(ans),
              'correct', {k: '%d/%d' % (ok[k], tot[k]) for k in sorted(tot)}, 'total correct', sum(ok.values()))
