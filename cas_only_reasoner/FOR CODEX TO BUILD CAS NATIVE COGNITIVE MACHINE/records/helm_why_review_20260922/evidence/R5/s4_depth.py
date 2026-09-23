import collections, json, math
from common import *
upd = read_jsonl(RUN / "updates.jsonl"); loss = [u["loss"] for u in upd]
idx = json.load(open("used_rows.json"))["idx"]
train = read_jsonl(DATA / "visible_G_train.jsonl"); tr = [parse(r["observation"]) for r in train]
toks = [ast_to_tokens(a) for a in tr]
cnt = collections.defaultdict(collections.Counter)
for s in toks:
    for t, (k, d) in zip(s, slot_sequence(s)):
        cnt[(k, d if k == "expr" else None)][t] += 1
def ce(s):
    return sum(0.0 if k == "eos" else -math.log(cnt[(k, d if k == "expr" else None)][t] / sum(cnt[(k, d if k == "expr" else None)].values())) for t, (k, d) in zip(s, slot_sequence(s))) / len(s)
for lo, hi in ((0, 64), (64, 128)):
    g = collections.defaultdict(list)
    for u in range(lo, hi):
        i = idx[u]; g[depth(tr[i])].append((loss[u], ce(toks[i])))
    for d in sorted(g):
        v = g[d]
        print("updates %d-%d depth %d: n=%d model mean %.6f  B3 mean %.6f  gap %.6f" % (lo + 1, hi, d, len(v), sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v), sum(a - b for a, b in v) / len(v)))
dev = [parse(r["observation"]) for r in read_jsonl(DATA / "visible_G_dev.jsonl")]
print("dev targets longer than every train target (max train tokens %d):" % max(len(t) for t in toks), sum(len(ast_to_tokens(a)) > max(len(t) for t in toks) for a in dev), "of", len(dev), "; in first 16:", sum(len(ast_to_tokens(a)) > 41 for a in dev[:16]))
print("train depth-3 leaves per tree:", dict(sorted(collections.Counter(len(leaves(a)) for a in tr if depth(a) == 3).items())))
print("bits per leaf log2(10*4*8*5) =", math.log2(10 * 4 * 8 * 5))
