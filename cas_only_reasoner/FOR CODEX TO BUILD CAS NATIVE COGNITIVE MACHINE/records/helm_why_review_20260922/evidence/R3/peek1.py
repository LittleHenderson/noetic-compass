import json, sys
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
for name in ['admission_helm1_certified','admission_001']:
    g = json.load(open(ROOT+'/records/typed_pointer_001/'+name+'/gate_reading.json','rb'))
    print('=====', name)
    print('top keys', list(g.keys()))
    for k in ['label','label_rule','alpha','min_passing_b','min_improved_kinds','min_improved_worlds','label_key_population_size','label_key_kinds','flags','void_paths_taken']:
        print(k, '=', g.get(k))
    print('gates keys', list(g['gates'].keys()))
    print('G_LEARN_population gate', g['gates'].get('G_LEARN_population'))
    for s, e in g['seeds'].items():
        t = e['G_LEARN_population']
        print(s, {k: t[k] for k in t if k!='keys'})
