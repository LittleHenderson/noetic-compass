# R6 scratch: which visible expression shape dominated the 128 rows the Q4 smoke trained on? VISIBLE files only.
import json, random, re, collections, math
from pathlib import Path
D = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/data/q3_v0_7")
train = [json.loads(l) for l in (D / "visible_G_train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
order = list(range(len(train))); random.Random(20260921).shuffle(order)
used = [train[i]["observation"] for i in order[:128]]
leaf = re.compile(r"\^\d\^[PCEO](?:_\{F\d\})?(?:\|[AfET])?")
def bare(s):  # replace every leaf by x, keep operators and brackets
    return leaf.sub("x", s)
c = collections.Counter(bare(s) for s in used)
print("used128 distinct bare strings:", len(c)); print(c.most_common(6))
call = collections.Counter(bare(r["observation"]) for r in train)
print("train2048 distinct bare strings:", len(call)); print(call.most_common(4))
print("uniform per-token loss over 34 output tokens ln(34) =", math.log(34))
