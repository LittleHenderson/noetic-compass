import json, sys
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
p = ROOT + "/research/helm_cas_expression_lab/data/q3_v0_7/baselines.json"
b = json.load(open(p, encoding="utf-8"))
print("top keys:", list(b.keys()))
for fam, v in b.items():
    if not isinstance(v, dict):
        print(fam, "=>", repr(v)[:300]); continue
    for split, bl in v.items():
        if not isinstance(bl, dict):
            print(fam, split, "=>", repr(bl)[:300]); continue
        for name, r in bl.items():
            if isinstance(r, dict):
                print(f"{fam}\t{split}\t{name}\texact={r.get('exact')}\tn={r.get('n')}")
            else:
                print(f"{fam}\t{split}\t{name}\t=> {repr(r)[:200]}")
