"""R5 meeting: does per-example loss averaging (R4-F9) or recency change which leaf labels are 'modal'?
Pure Python, visible files only, no torch. Weight of a token = 1/len(target) (mean-over-tokens CE, batch 1)."""
import collections
import json
import random
from common import *

plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
order = list(range(plan["train_examples"]))
random.Random(plan["seed"]).shuffle(order)
idx = [order[u % len(order)] for u in range(plan["max_updates"])]
train = read_jsonl(DATA / "visible_G_train.jsonl")[:plan["train_examples"]]
seen = [parse(train[i]["observation"]) for i in idx]
toks = [ast_to_tokens(a) for a in seen]

# R4-F9 check: depth-1 expr slot P(BINARY), token-count vs loss-weighted
tc = collections.Counter(); lw = collections.Counter()
for s in toks:
    for t, (k, d) in zip(s, slot_sequence(s)):
        if k == "expr" and d == 1:
            tc[TOKENS[t]] += 1
            lw[TOKENS[t]] += 1.0 / len(s)
print("depth-1 expr slot token-count:", dict(tc), " P(BINARY) = %.5f" % (tc["BINARY"] / sum(tc.values())))
print("depth-1 expr slot loss-weighted P(BINARY) = %.5f" % (lw["BINARY"] / sum(lw.values())))
print("token share of depth-1 examples: %d/%d = %.5f" % (sum(len(s) for s, a in zip(toks, seen) if depth(a) == 1),
                                                      sum(len(s) for s in toks),
                                                      sum(len(s) for s, a in zip(toks, seen) if depth(a) == 1) / sum(len(s) for s in toks)))

for h in (None, 64, 32, 16):
    nw = collections.Counter(); dw = collections.Counter()
    for r, (s, a) in enumerate(zip(toks, seen)):
        w = 1.0 / len(s)
        if h:
            w *= 0.5 ** ((127 - r) / h)
        for l in leaves(a):
            nw[l["operator"]] += w
            dw[l["domain"]] += w
    print("loss-weighted%s: noetic top4 %s | domain %s" % (
        "" if h is None else " x recency h=%d" % h,
        [(k, round(v, 4)) for k, v in nw.most_common(4)], [(k, round(v, 4)) for k, v in dw.most_common()]))
