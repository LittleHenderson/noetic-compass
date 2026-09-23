import json, os
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
P=ROOT+"/records/typed_pointer_001/receipt_20260917/checkpoints/"
pr=json.load(open(P+"course_p10_predictions.json"))
print(pr.keys())
kinds={}
for p in pr["predictions"]:
    k=p["answer"]["kind"]; kinds[k]=kinds.get(k,0)+1
print(kinds)
for p in pr["predictions"]:
    if p["answer"]["kind"]=="reach":
        s=json.dumps(p)
        print(s[:4000]); break
sc=json.load(open(P+"course_p10_scoring.json"))
print(sc.keys())
for r in sc["rows"]:
    if r["kind"]=="reach":
        print(json.dumps(r)[:3000]); break
