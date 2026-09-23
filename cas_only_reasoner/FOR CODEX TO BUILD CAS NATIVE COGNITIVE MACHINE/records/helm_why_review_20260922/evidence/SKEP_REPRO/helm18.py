import json, os, sys
R=sys.argv[1]; T=os.path.join(R,'records','typed_pointer_001')
g=json.load(open(os.path.join(T,'admission_001','gate_reading.json')))
pq=g['label_key_population']
print('population_questions type',type(pq).__name__, (len(pq) if pq else None))
pop=set(pq if isinstance(pq,list) else pq.get('ids',[]))
oc=g['oracle_ceilings']; floor=set(oc['population_ids_the_rule_solves'])|set(oc['rank_last_ids_the_rule_solves'])
print('floor size',len(floor),'floor subset pop',floor<=pop)
g1=json.load(open(os.path.join(T,'admission_helm1_certified','gate_reading.json')))
print('same population in 1.0 reading', set(g1['label_key_population'])==pop, 'pop==question_ids', pop==set(g['population']['question_ids']))
def load(rd,ph):
    s=json.load(open(os.path.join(T,rd,'checkpoints','%s_scoring.json'%ph)))
    return {r['query_id']:r for r in s['rows']}
short=lambda q:q.split('-')[-1][:8]
kind={}
for tag,pref in (('2.0','receipt_'),('1.0','receipt_helm1_certified_')):
    for seed in ('20260917','20260918','20260919'):
        rd=pref+seed
        st=load(rd,'course_p00'); fi=load(rd,'course_p10')
        for q in pop: kind[q]=fi[q]['kind']
        sc={q for q in pop if st[q]['correct']}; fc={q for q in pop if fi[q]['correct']}
        b=len(fc-sc); c=len(sc-fc)
        out=sorted(short(q) for q in fc-floor)
        missed_floor=sorted(short(q) for q in floor-fc)
        print(tag,seed,'start',len(sc),'final',len(fc),'b',b,'c',c,'final-minus-11',len(fc)-11,'right outside floor',out,'floor missed',missed_floor, 'net vs floor', len(fc-floor)-len(floor-fc))
print('kinds of pop', sorted((short(q),kind[q]) for q in pop))
# 36988555 trajectory in 2.0 seed 20260919
q=[x for x in pop if short(x)=='36988555'][0]
for tag,rd in (('2.0','receipt_20260919'),('1.0','receipt_helm1_certified_20260919')):
    traj=[]
    for ph in ('course_p00','heldback_p02','heldback_p04','heldback_p06','heldback_p08','course_p10'):
        try: traj.append((ph,load(rd,ph)[q]['correct']))
        except Exception as e: traj.append((ph,'NA:'+type(e).__name__))
    print(tag,'36988555',traj)
for s in ('20260917','20260918','20260919'):
    x=g['seeds'][s]['G_LEARN_population']; y=g1['seeds'][s]['G_LEARN_population']
    print('frozen 2.0',s,x['wrong_to_right'] if isinstance(x['wrong_to_right'],int) else len(x['wrong_to_right']),x['right_to_wrong'] if isinstance(x['right_to_wrong'],int) else len(x['right_to_wrong']),x['p_one_sided'],x['passed'],'| 1.0',y['p_one_sided'],y['passed'])
print('row keys', sorted(load('receipt_20260919','course_p10')[q].keys()))
