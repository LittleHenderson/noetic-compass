import json, hashlib
from collections import Counter
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
T=ROOT+"/records/typed_pointer_001/"
for rc in ["receipt_20260917","receipt_helm1_certified_20260917"]:
    for loc in ["checkpoints","collected/results/artifacts"]:
        import os
        p=T+rc+"/"+loc
        print(rc,loc,os.path.isdir(p), len(os.listdir(p)) if os.path.isdir(p) else None)
    for f in ["ablation_baseline","ablation_heads","ablation_round_mix","ablation_core_block","ablation_query_and_readout","course_p00","course_p10","heldback_p08"]:
        a=json.load(open(T+rc+"/checkpoints/"+f+"_predictions.json",encoding="utf-8"))
        ks=Counter(p["answer"]["kind"] for p in a["predictions"])
        print(" ",f,a.get("phase"),len(a["predictions"]),dict(ks))
    # identical to collected copy?
    for f in ["course_p10_predictions.json","course_p00_scoring.json","ablation_heads_predictions.json"]:
        a=open(T+rc+"/checkpoints/"+f,"rb").read(); b=open(T+rc+"/collected/results/artifacts/"+f,"rb").read() if os.path.exists(T+rc+"/collected/results/artifacts/"+f) else b""
        print("  same bytes",f,hashlib.sha256(a).hexdigest()==hashlib.sha256(b).hexdigest())
pm=json.load(open(T+"receipt_20260917/collected/results/artifacts/protocol_material.json",encoding="utf-8"))
print([k for k in pm.keys()])
print({k:len(pm[k]) for k in ["held_back_record_ids","trained_record_ids","excluded_record_ids"]})
