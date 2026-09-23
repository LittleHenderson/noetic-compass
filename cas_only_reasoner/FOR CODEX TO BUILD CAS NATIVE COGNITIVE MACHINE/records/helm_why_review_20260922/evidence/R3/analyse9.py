import json
src = open('analyse.py').read().split("out = {}")[0]
exec(src)
shortcut = set(g2['population']['shortcut_question_ids'])
ELIG = sorted(set(held_q) - shortcut)
print('=== (10) PAIRED Helm 1.0 final vs Helm 2.0 final, same seed (b = 1.0 wrong & 2.0 right; c = 1.0 right & 2.0 wrong) ===')
for label, qs in [('FROZEN 18', POP), ('ELIGIBLE 45', ELIG), ('HELD 50', held_q)]:
    for s in SEEDS:
        A = {q: qok(data[('1.0',s)]['at'][10], q) for q in qs}; B = {q: qok(data[('2.0',s)]['at'][10], q) for q in qs}
        b = [q for q in qs if not A[q] and B[q]]; c = [q for q in qs if A[q] and not B[q]]
        print(label, s, 'b=%d c=%d p(2.0 better)=%s' % (len(b), len(c), tail(len(b), len(b)+len(c))), 'b kinds', sorted(kind_of.get(q, rec_kind[q_records[q][0]]) for q in b), 'c kinds', sorted(rec_kind[q_records[q][0]] for q in c))
for s in SEEDS:
    for label, ids in [('HELD 127 recs', HELD), ('ALL 564 recs', list(r00))]:
        A = data[('1.0',s)]['at'][10]; B = data[('2.0',s)]['at'][10]
        b = sum(1 for r in ids if not A[r] and B[r]); c = sum(1 for r in ids if A[r] and not B[r])
        bn = sum(1 for r in ids if not A[r] and B[r] and rec_kind[r] != 'correspondence'); cn = sum(1 for r in ids if A[r] and not B[r] and rec_kind[r] != 'correspondence')
        print(label, s, 'b=%d c=%d | excluding correspondence b=%d c=%d' % (b, c, bn, cn))
print('\n=== (11) untrained start by version (records correct at p00) ===')
for s in SEEDS:
    for v in VER:
        at = data[(v,s)]['at'][0]
        print('Helm', v, s, 'p00 all', sum(at[r] for r in r00), 'held', sum(at[r] for r in HELD), 'frozen18 questions', sum(qok(at,q) for q in POP))
