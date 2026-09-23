"""RT4: structure of the public bank only (no predictions read). stdlib only."""
import json
from collections import Counter
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
pc=json.load(open(ROOT+"/records/typed_course_001/checks_002/public_course.json",encoding="utf-8"))
rk=lambda ref:int(ref.split('/')[-1][1:])
c=Counter()
for w in pc['bank']['worlds']:
    refs=sorted([n['ref'] for n in w['nodes']])
    n=len(refs)
    assert [rk(r) for r in refs]==list(range(n)), refs
    E=[(rk(e['source']),rk(e['target'])) for e in w['contains']]
    indeg=Counter(t for s,t in E); outdeg=Counter(s for s,t in E)
    parts=[rk(p) for p in w['declarations']['participants']]
    c[('n',n)]+=1
    c[('participants_ranks',tuple(parts))]+=1
    c[('nonparticipant_nodes',tuple(sorted(set(range(n))-set(parts))))]+=1
    c[('max_indegree',max(indeg.values()) if indeg else 0)]+=1
    c[('edges',len(E))]+=1
    c[('declared_whole_rank',rk(w['declared_whole']))]+=1
    c[('prim==part', w['declarations']['primary_labels']==w['declarations']['participants'])]+=1
for k,v in sorted(c.items(),key=str): print(k,v)
