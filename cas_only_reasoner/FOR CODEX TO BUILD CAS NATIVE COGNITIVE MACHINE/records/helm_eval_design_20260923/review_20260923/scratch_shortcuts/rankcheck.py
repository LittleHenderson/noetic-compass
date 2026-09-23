import json, collections
P="D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_course_001/checks_002/public_course.json"
d=json.load(open(P,encoding='utf-8')); W=d['bank']['worlds']
topo=0; whole_rank=collections.Counter(); part_ranks=collections.Counter()
for w in W:
    refs=sorted(x['ref'] for x in w['nodes']); idx={r:i for i,r in enumerate(refs)}
    E=[(idx[c['source']],idx[c['target']]) for c in w['contains']]
    topo+= all(a<b for a,b in E)
    whole_rank[(len(refs),idx[w['declared_whole']])]+=1
    p=[idx[r] for r in w['declarations']['participants']]
    part_ranks[tuple(p)]+=1
print("worlds whose rank order is a topological order:",topo,"/",len(W))
print("declared-whole rank by size:",dict(whole_rank))
print("distinct participant rank tuples:",len(part_ranks))
# analogy/world count & focus-in-bank in registry
reg=d['registry']; print(type(reg), (list(reg.keys())[:10] if isinstance(reg,dict) else len(reg)))
