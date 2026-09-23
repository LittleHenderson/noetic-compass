import sys, json, time, pathlib
sys.dont_write_bytecode=True
P=pathlib.Path("D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0]=[str(P),str(P/"research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import pointer_inputs as PI
t=time.time(); rec=PI._build_cache(P); print("cache s",round(time.time()-t,1)); assert "torch" not in sys.modules
ids=rec["declaration_ids"]
bank=json.loads((P/"records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]
for f in PI.DECLARATION_FIELDS:
    toks=set(); strs=set()
    for w in bank:
        s=w["declarations"][f]; strs.add(s); toks.update(ids[s])
    print(f,"distinct strings",len(strs),"distinct tokens (trained rows)",len(toks))
# fresh words example: encode a few invented words
for s in ["zorvic","plimbet","quandrel"]:
    e=PI._encode_text(s,rec["lookup"],rec["max_tokens"]); print(s,e)
from collections import Counter
print("domains",Counter(w["declarations"]["domain"] for w in bank))
