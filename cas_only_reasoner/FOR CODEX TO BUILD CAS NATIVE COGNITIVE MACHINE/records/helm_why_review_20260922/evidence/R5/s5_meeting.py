"""Meeting checks (R5). Pure Python, visible files only, no torch.
1. Seen-128 field counts (any depth, depth-1 leaves, leaf position in 2-leaf trees).
2. Input-blind count models fitted ONLY on the 128 seen rows, greedy-decoded through the repo's grammar mask.
3. Recency-weighted counts.
4. Prequential n-gram learners that are NOT handed the grammar, vs the GRU's logged loss.
5. Operator-bearing bare shapes (R6-F6 '(x + x)' 44/128, 476/2048).
6. R4-F7 byte-cue check."""
import collections
import json
import math
import random
from common import *

upd = read_jsonl(RUN / "updates.jsonl")
plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
loss = [u["loss"] for u in upd]
order = list(range(plan["train_examples"]))
random.Random(plan["seed"]).shuffle(order)
idx = [order[u % len(order)] for u in range(plan["max_updates"])]
train = read_jsonl(DATA / "visible_G_train.jsonl")[:plan["train_examples"]]
tr = [parse(r["observation"]) for r in train]
seen = [tr[i] for i in idx]
seen_tok = [ast_to_tokens(a) for a in seen]
V = len(TOKENS)


def leafpos(a, d=0, out=None):
    out = [] if out is None else out
    if a["node"] == "BinaryExpr":
        leafpos(a["left"], d + 1, out)
        leafpos(a["right"], d + 1, out)
    else:
        out.append((d, a))
    return out


print("== 1. field counts over the 128 SEEN rows")
noe = collections.Counter(); dom = collections.Counter()
noe_d1 = collections.Counter(); dom_d1 = collections.Counter()
for a in seen:
    for d, l in leafpos(a):
        noe[l["operator"]] += 1
        dom[l["domain"]] += 1
        if d == 1:
            noe_d1[l["operator"]] += 1
            dom_d1[l["domain"]] += 1
print(" noetic any depth", noe.most_common(), "total", sum(noe.values()))
print(" domain any depth", dom.most_common())
print(" noetic depth-1 leaves", noe_d1.most_common(), "total", sum(noe_d1.values()))
print(" domain depth-1 leaves", dom_d1.most_common())
p3n = collections.Counter(); p4d = collections.Counter(); p8n = collections.Counter(); p9d = collections.Counter()
for s in seen_tok:
    n = [TOKENS[t] for t in s]
    if n[:3] == ["BINARY", "PLUS", "STATE"]:
        p3n[n[3]] += 1
        p4d[n[4]] += 1
    if len(n) == 13 and n[1] == "PLUS":
        p8n[n[8]] += 1
        p9d[n[9]] += 1
print(" pos3 noetic after prefix BINARY PLUS STATE:", p3n.most_common(4), "n", sum(p3n.values()))
print(" pos4 domain after that prefix:", p4d.most_common())
print(" 2-leaf PLUS trees: pos8 noetic", p8n.most_common(4), "| pos9 domain", p9d.most_common())


def greedy(prob_fn):
    prefix = ()
    for _ in range(200):
        allowed = allowed_next(prefix)
        if not allowed:
            break
        sc = {t: prob_fn(prefix, t) for t in allowed}
        c = min(allowed, key=lambda t: (-sc[t], t))
        prefix += (c,)
        if TOKENS[c] == "EOS":
            break
    return " ".join(TOKENS[t] for t in prefix)


def ngram_counts(rows, k, weights=None):
    C = collections.defaultdict(collections.Counter)
    for r, s in enumerate(rows):
        w = 1.0 if weights is None else weights[r]
        full = (V,) + tuple(s)
        for i in range(1, len(full)):
            C[full[max(0, i - k):i]][full[i]] += w
    return C


def backoff_prob(Cs, kmax):
    def f(prefix, t):
        full = (V,) + prefix
        for k in range(kmax, 0, -1):
            c = Cs[k].get(full[max(0, len(full) - k):])
            if c and sum(c.values()) > 0:
                return c[t] / sum(c.values())
        return 0.0
    return f


def slot_model(rows, weights=None):
    C = collections.defaultdict(collections.Counter)
    for r, s in enumerate(rows):
        w = 1.0 if weights is None else weights[r]
        for t, (k, d) in zip(s, slot_sequence(s)):
            C[(k, d if k == "expr" else None)][t] += w

    def f(prefix, t):
        k, d = slot_sequence(prefix + (t,))[-1]
        c = C[(k, d if k == "expr" else None)]
        n = sum(c.values())
        return c[t] / n if n else 0
    return f


print("\n== 2. input-blind models fitted on the 128 SEEN rows only, greedy through allowed_next")
Cs = {k: ngram_counts(seen_tok, k) for k in range(1, 14)}
for k in (1, 2, 3, 4, 6, 8, 13):
    print(" context %2d tokens (backoff): %s" % (k, greedy(backoff_prob(Cs, k))))
print(" slot+depth marginal: %s" % greedy(slot_model(seen_tok)))

print("\n== 3. recency-weighted (weight = 0.5**((127-r)/h), r = update index 0..127)")
for h in (4, 8, 16, 32, 64, 1e9):
    w = [0.5 ** ((127 - r) / h) for r in range(128)]
    print(" h=%-6s slot+depth: %s" % (h if h < 1e8 else "inf", greedy(slot_model(seen_tok, w))))
for h in (4, 8, 16, 32):
    w = [0.5 ** ((127 - r) / h) for r in range(128)]
    Cw = {k: ngram_counts(seen_tok, k, w) for k in range(1, 5)}
    print(" h=%-6s context-4 backoff: %s" % (h, greedy(backoff_prob(Cw, 4))))
for h in (8, 16, 32):
    w = [0.5 ** ((127 - r) / h) for r in range(128)]
    nw = collections.Counter(); dw = collections.Counter()
    for r, a in enumerate(seen):
        for d, l in leafpos(a):
            nw[l["operator"]] += w[r]
            dw[l["domain"]] += w[r]
    print(" h=%s noetic top3 %s | domain %s" % (h, [(k, round(v, 3)) for k, v in nw.most_common(3)],
                                               [(k, round(v, 3)) for k, v in dw.most_common()]))

print("\n== 4. prequential n-gram learners NOT handed the grammar (they learn it only from past rows)")


def preq(k, alpha):
    C = collections.defaultdict(collections.Counter)
    out = []
    for s in seen_tok:
        full = (V,) + tuple(s)
        tot = 0.0
        for i in range(1, len(full)):
            c = C[full[max(0, i - k):i]]
            n = sum(c.values())
            tot += -math.log((c[full[i]] + alpha) / (n + alpha * V))
        out.append(tot / (len(full) - 1))
        for i in range(1, len(full)):
            C[full[max(0, i - k):i]][full[i]] += 1
    return out


def mean(x):
    return sum(x) / len(x)


for k in (1, 2, 3, 4):
    for alpha in (0.1, 0.5, 1.0):
        b = preq(k, alpha)
        below = sum(l < v for l, v in zip(loss, b))
        below32 = sum(l < v for l, v in zip(loss[96:], b[96:]))
        print(" k=%d alpha=%.1f: upd 1-16 %.6f | 97-128 %.6f | 113-128 %.6f || GRU below it %d/128, last32 %d/32" % (
            k, alpha, mean(b[:16]), mean(b[96:]), mean(b[112:]), below, below32))
print(" GRU logged: 1-16 %.6f | 97-128 %.6f | 113-128 %.6f" % (mean(loss[:16]), mean(loss[96:]), mean(loss[112:])))

print("\n== 5. operator-bearing bare shapes")


def opshape(a):
    if a["node"] == "BinaryExpr":
        return "(%s %s %s)" % (opshape(a["left"]), "+" if a["op"] == "PLUS" else "*", opshape(a["right"]))
    return "x"


print(" seen-128 top 5:", collections.Counter(opshape(a) for a in seen).most_common(5))
print(" pool-2048 top 5:", collections.Counter(opshape(a) for a in tr).most_common(5))
print(" operator-free (B,L,L): seen", sum(shape(a) == ["B", "L", "L"] for a in seen),
      "pool", sum(shape(a) == ["B", "L", "L"] for a in tr))

print("\n== 6. byte-cue check (R4-F7)")
ok1 = sum((r["observation"][1] == "(") == (a["left"]["node"] == "BinaryExpr") for r, a in zip(train, tr))
ok2 = sum((r["observation"].rstrip()[-2] == ")") == (a["right"]["node"] == "BinaryExpr") for r, a in zip(train, tr))
print(" train: char[1]=='(' iff left child binary %d/2048; char[-2]==')' iff right child binary %d/2048" % (ok1, ok2))
dev = read_jsonl(DATA / "visible_G_dev.jsonl")[:16]
dv = [parse(r["observation"]) for r in dev]
print(" dev16 left child binary %d/16, right child binary %d/16, root PLUS %d/16" % (
    sum(a["left"]["node"] == "BinaryExpr" for a in dv), sum(a["right"]["node"] == "BinaryExpr" for a in dv),
    sum(a["op"] == "PLUS" for a in dv)))
