import json, re
exec(open('analyse2.py').read().split("print('\n=== (2)")[0])
KINDS = ['reach','analogy','correspondence','parts','context','definition','edge_account','role_set']
HS = set(HELD); TS = set(TRAINED); ES = set(EXCL)
elig = set(g2['population']['eligible_questions']) if False else None
# eligible 45 = held questions minus shortcut 5
shortcut = set(g2['population']['shortcut_question_ids'])
ELIG = sorted(set(held_q) - shortcut)
print('eligible held questions', len(ELIG))
def rec_counts(at, ids):
    by = {}
    for r in ids:
        k = rec_kind[r]; c = by.setdefault(k, [0,0]); c[1]+=1; c[0]+= at[r]
    return by
def fmt(v,s,n,ids):
    at = data[(v,s)]['at'][n]; return rec_counts(at, ids)
print('\n=== (6) RECORD level by kind, final checkpoint p10 (and p00), Helm 1.0 -> 2.0 ===')
for label, ids in [('ALL 564', list(r00)), ('HELD 127', HELD), ('TRAINED 358', TRAINED), ('EXCLUDED 79', EXCL)]:
    print('--', label)
    tot = {}
    for k in KINDS:
        cells = []
        for s in SEEDS:
            a0 = fmt('1.0',s,0,ids).get(k,[0,0]); a = fmt('1.0',s,10,ids).get(k,[0,0]); b0 = fmt('2.0',s,0,ids).get(k,[0,0]); b = fmt('2.0',s,10,ids).get(k,[0,0])
            cells.append('%s: 1.0 %d->%d | 2.0 %d->%d of %d (d=%+d)' % (s[-2:], a0[0], a[0], b0[0], b[0], a[1], b[0]-a[0]))
        print('  ', k.ljust(14), ' ; '.join(cells))
    for s in SEEDS:
        A = sum(data[('1.0',s)]['at'][10][r] for r in ids); B = sum(data[('2.0',s)]['at'][10][r] for r in ids)
        A0 = sum(data[('1.0',s)]['at'][0][r] for r in ids); B0 = sum(data[('2.0',s)]['at'][0][r] for r in ids)
        print('   TOTAL seed', s, '1.0 %d->%d  2.0 %d->%d  of %d  final diff %+d' % (A0, A, B0, B, len(ids), B-A))
print('\n=== (7) QUESTION level by kind at p10 (all records right), frozen 18 / eligible 45 / held 50 ===')
for label, qs in [('FROZEN 18', POP), ('ELIGIBLE 45', ELIG), ('HELD 50', held_q)]:
    print('--', label)
    for k in KINDS:
        n = sum(1 for q in qs if rec_kind[q_records[q][0]]==k)
        if n==0: continue
        cells = []
        for s in SEEDS:
            A = sum(1 for q in qs if rec_kind[q_records[q][0]]==k and qok(data[('1.0',s)]['at'][10], q))
            B = sum(1 for q in qs if rec_kind[q_records[q][0]]==k and qok(data[('2.0',s)]['at'][10], q))
            cells.append('%s: %d -> %d' % (s[-2:], A, B))
        print('  ', k.ljust(14), 'of %2d' % n, ' ; '.join(cells))
    for s in SEEDS:
        A = sum(1 for q in qs if qok(data[('1.0',s)]['at'][10], q)); B = sum(1 for q in qs if qok(data[('2.0',s)]['at'][10], q))
        print('   TOTAL', s, '1.0 %d  2.0 %d of %d' % (A, B, len(qs)))
print('\n=== (8) RETENTION and DEVELOPMENT (worker_report) ===')
for s in SEEDS:
    for v in VER:
        wr = data[(v,s)]['wr']; rs = wr['retention_scores']
        dev = wr['development_scores']
        print('Helm', v, s, 'retention before %d/%d after %d/%d' % (rs['before']['correct'], rs['before']['total'], rs['after']['correct'], rs['after']['total']),
              'held_world %d->%d/%d trained_world %d->%d/%d' % (rs['before_by_side']['held_world']['correct'], rs['after_by_side']['held_world']['correct'], rs['after_by_side']['held_world']['total'], rs['before_by_side']['trained_world']['correct'], rs['after_by_side']['trained_world']['correct'], rs['after_by_side']['trained_world']['total']),
              'interference_updates', rs['interference_updates'], '| dev', [d['correct'] for d in dev], 'of', dev[0]['total'])
