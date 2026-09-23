import json, re
exec(open('analyse2.py').read().split("print('\n=== (2)")[0])
print('\n=== (4) PRIMARY TEST AT EVERY CHECKPOINT vs START (frozen rule: b>c, p<=1/100, >=2 kinds, >=2 worlds) ===')
for v in VER:
    for s in SEEDS:
        at = data[(v,s)]['at']; cks = sorted(at); st = cks[0]
        before = {q: qok(at[st], q) for q in POP}
        cells = []
        for n in cks[1:]:
            after = {q: qok(at[n], q) for q in POP}
            b = sum(1 for q in POP if not before[q] and after[q]); c = sum(1 for q in POP if before[q] and not after[q])
            p = tail(b, b+c); kinds = {kind_of[q] for q in POP if not before[q] and after[q]}; worlds = {world_of[q] for q in POP if not before[q] and after[q]}
            ok = b > c and p <= Fraction(1,100) and len(kinds)>=2 and len(worlds)>=2
            cells.append('p%02d:%d/%d%s' % (n, b, c, 'P' if ok else 'F'))
        print('Helm', v, s, 'start', sum(before.values()), ' '.join(cells))
print('\n=== (5) score margins on broken question 36988555 records (VIA_N3 correct) ===')
qq = [x for x in POP if short(x)=='36988555'][0]
for v,s,n in [('2.0','20260919',10),('2.0','20260919',8),('2.0','20260918',4),('2.0','20260918',10),('1.0','20260919',10)]:
    pf = pred_file(v,s,n)
    for rid in q_records[qq]:
        pr = [p for p in pf['predictions'] if p['record_id']==rid][0]
        sc = list(pr['scores'].values())[0]
        print(v, s, 'p%02d'%n, short(rid), {k: round(x,4) for k,x in sc.items()}, 'N3-N1 =', sc['VIA_N3']-sc['VIA_N1'])
qq = [x for x in POP if short(x)=='404166e8'][0]
print('--- 404166e8 (VIA_N3 correct)')
for v in VER:
    for s in SEEDS:
        for n in (0,10):
            pf = pred_file(v,s,n)
            for rid in q_records[qq]:
                pr = [p for p in pf['predictions'] if p['record_id']==rid][0]
                sc = list(pr['scores'].values())[0]
                print(v, s, 'p%02d'%n, short(rid), 'DIRECT', sc['DIRECT'], 'VIA_N3', sc['VIA_N3'], 'N3-DIRECT', sc['VIA_N3']-sc['DIRECT'])
