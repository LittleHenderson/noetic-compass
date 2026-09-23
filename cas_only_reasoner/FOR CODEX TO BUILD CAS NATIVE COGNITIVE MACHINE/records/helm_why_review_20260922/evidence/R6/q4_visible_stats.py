# R6 scratch: pure-Python stats over VISIBLE Q3 v0.7 G train/dev rows only. No torch, no sealed/eval files.
import json, random, re, collections, sys
from pathlib import Path
D = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/data/q3_v0_7")
def rows(name):
    return [json.loads(l) for l in (D / name).read_text(encoding="utf-8").splitlines() if l.strip()]
leaf_re = re.compile(r"\^(\d)\^([PCEO])(?:_\{(F\d)\})?(?:\|([AfET]))?")
def depth(s):
    d = m = 0
    for ch in s:
        if ch == "(": d += 1; m = max(m, d)
        elif ch == ")": d -= 1
    return m
train = rows("visible_G_train.jsonl"); dev = rows("visible_G_dev.jsonl")
order = list(range(len(train))); random.Random(20260921).shuffle(order)
used = [train[i] for i in order[:128]]
for label, rs in (("train_all_2048", train), ("train_used_first128", used), ("dev_all_256", dev), ("dev_first16", dev[:16])):
    dep = collections.Counter(depth(r["observation"]) for r in rs)
    leaves = collections.Counter(len(leaf_re.findall(r["observation"])) for r in rs)
    print(label, "n=%d" % len(rs), "depth(paren-nesting)=", dict(sorted(dep.items())), "leaves=", dict(sorted(leaves.items())))
# leaf-type vocabulary in the 128 used rows
lt = collections.Counter()
for r in used:
    for n, dom, f, reg in leaf_re.findall(r["observation"]):
        lt[(n, dom, f or "-", reg or "-")] += 1
print("used128: total leaves", sum(lt.values()), "distinct full leaf types", len(lt))
nd = collections.Counter((n, dom) for (n, dom, f, reg) in lt.elements())
print("used128: distinct noetic x domain", len(nd), "most common", nd.most_common(5))
print("used128: count of ^7^E leaves", nd[("7","E")], "^7^C leaves", nd[("7","C")])
alln = collections.Counter()
for r in train:
    for n, dom, f, reg in leaf_re.findall(r["observation"]): alln[(n, dom)] += 1
print("train2048: most common noetic x domain", alln.most_common(6))
# does every dev-first-16 observation contain a full parse? leaf count sanity
print("dev_first16 distinct observations", len({r['observation'] for r in dev[:16]}))
# overlap of exact observation strings between train and dev
ts = {r["observation"] for r in train}
print("dev observations also in train (exact string)", sum(r["observation"] in ts for r in dev), "of", len(dev))
