"""R5 meeting: greedy decode (repo grammar mask, lowest-id ties) of an input-blind slot+depth model fitted on the
128 SEEN rows with the job's per-example loss weighting (1/len), optionally times recency. No torch."""
import collections, json, random
from common import *
plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
order = list(range(plan["train_examples"])); random.Random(plan["seed"]).shuffle(order)
idx = [order[u % len(order)] for u in range(plan["max_updates"])]
train = read_jsonl(DATA / "visible_G_train.jsonl")[:plan["train_examples"]]
toks = [ast_to_tokens(parse(train[i]["observation"])) for i in idx]
MODEL = "BINARY PLUS STATE N7 D_E F_NONE REG_ABSENT STATE N7 D_C F_NONE REG_ABSENT EOS".split()
def fit(h):
    C = collections.defaultdict(collections.Counter)
    for r, s in enumerate(toks):
        w = 1.0 / len(s) * (0.5 ** ((127 - r) / h) if h else 1.0)
        for t, (k, d) in zip(s, slot_sequence(s)):
            C[(k, d if k == "expr" else None)][t] += w
    return C
def greedy(C):
    prefix = ()
    while True:
        allowed = allowed_next(prefix)
        if not allowed: break
        k, d = slot_sequence(prefix + (allowed[0],))[-1]
        c = C[(k, d if k == "expr" else None)]
        ch = min(allowed, key=lambda t: (-c[t], t))
        prefix += (ch,)
        if TOKENS[ch] == "EOS": break
    return [TOKENS[t] for t in prefix]
for h in (None, 128, 64, 32):
    g = greedy(fit(h))
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(MODEL, g)) if a != b]
    print("loss-weighted%s: %s | len %d | positions differing from model: %s" % ("" if h is None else " x recency h=%d" % h, " ".join(g), len(g), diff))
