import json, os, sys
T=os.path.join(sys.argv[1],'records','typed_pointer_001','receipt_20260919','checkpoints')
for ph in ('course_p00','heldback_p02','heldback_p04','heldback_p06','heldback_p08','course_p10'):
    P=json.load(open(os.path.join(T,ph+'_predictions.json')))['predictions']
    for p in P:
        if '36988555' in p['answer']['query_id']:
            sc=list(p['scores'].values())[0]
            print(ph, p['answer']['query_id'][12:20], p['decisions']['record_id'][12:20], 'N3-N1', repr(sc['VIA_N3']-sc['VIA_N1']), 'sel', list(p['decisions']['selected'].values()))
