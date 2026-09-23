import json
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
T = ROOT+'/records/typed_pointer_001/'
for name in ['admission_helm1_certified','admission_001']:
    g = json.load(open(T+name+'/gate_reading.json','rb'))
    print('=====', name)
    oc = g['oracle_ceilings']
    for k in oc:
        if k not in ('note',):
            print(' oc.', k, '=', oc[k])
    print(' population keys', list(g['population'].keys()))
    print(' population by_kind', g['population']['by_kind'], 'total', g['population']['total'])
    print(' kinds', g['kinds'])
    print(' correspondence', {k:v for k,v in g['correspondence'].items() if k!='removed_questions'})
    for s,e in g['seeds'].items():
        print(' seed', s, 'checkpoints', e['checkpoints'], 'start', e['start_checkpoint'], 'first', e['first_checkpoint'], 'final', e['final_checkpoint'])
        print('   population_questions_correct', e['population_questions_correct'])
        print('   held_questions_correct', e['held_questions_correct'])
        print('   eligible_questions_correct', e['eligible_questions_correct'])
        print('   MORE_PRACTICE', {k:v for k,v in e['MORE_PRACTICE_population'].items() if k not in ('keys','improved_worlds')})
        print('   ALL_KINDS', {k:v for k,v in e['G_LEARN_all_kinds'].items() if k not in ('keys','improved_worlds')})
