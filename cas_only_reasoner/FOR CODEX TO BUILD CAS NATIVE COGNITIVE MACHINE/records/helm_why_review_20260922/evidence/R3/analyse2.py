import json, re
exec(open('analyse.py').read().split("out = {}")[0])  # reuse loaders (prints header line only)
def pred_file(v, s, n):
    art = data[(v,s)]['art']
    for pre in ('course','heldback'):
        f = art/('%s_p%02d_predictions.json' % (pre, n))
        if f.exists(): return J(f)
    return None
print('\n=== (2) TIMELINE of question correctness on the frozen 18 across checkpoints (1=all records right) ===')
focus = [q for q in POP if kind_of[q] == 'reach' or q in FLOOR]
for q in POP:
    line = []
    for v in VER:
        for s in SEEDS:
            at = data[(v,s)]['at']
            line.append(v+'/'+s[-2:]+':' + ''.join('1' if qok(at[n], q) else '0' for n in sorted(at)))
    tag = 'RANK' if q in RANK else ('ORACLE' if q in ORACLE else 'NONFLOOR')
    print(short(q), kind_of[q].ljust(12), tag.ljust(8), 'recs', len(q_records[q]), ' '.join(line))
print('checkpoints', sorted(data[('2.0','20260917')]['at']))
print('\n=== (3) RECORD-LEVEL answers for the two broken questions and the two above-floor questions ===')
for q in ['404166e8','36988555','7a391350','a3e70de9']:
    qq = [x for x in POP if short(x)==q][0]
    print('--- question', q, kind_of[qq], 'world', short(world_of[qq]), 'records', len(q_records[qq]))
    for rid in q_records[qq]:
        for v in VER:
            for s in SEEDS:
                cells = []
                for n in sorted(data[(v,s)]['at']):
                    pf = pred_file(v, s, n)
                    pr = [p for p in pf['predictions'] if p['record_id']==rid][0]
                    val = pr['answer']['value']
                    st = val.get('state') if isinstance(val, dict) else str(val)
                    via = (val.get('via') or '')[-2:] if isinstance(val, dict) and val.get('via') else ''
                    ok = data[(v,s)]['at'][n][rid]
                    cells.append('%s%s%s' % (st, ('/'+via) if via else '', '+' if ok else '-'))
                print('   ', short(rid), 'Helm', v, s[-2:], ' '.join(cells))
