import json
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
a = json.load(open(ROOT+'/records/typed_pointer_001/trust_anchor_helm2_experimental_20208c92.json','rb'))
print(list(a.keys()))
print(list(a['population'].keys()))
for k,v in a['population'].items():
    print(k, type(v).__name__, len(v) if hasattr(v,'__len__') else v)
print(a['pass_rule'])
print(a['grader'])
a1 = json.load(open(ROOT+'/records/typed_pointer_001/trust_anchor_helm1_certified.json','rb'))
print(a1['pass_rule'], a1['grader'])
