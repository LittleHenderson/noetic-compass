"""Stage 3: the 16 dev targets vs the constant prediction; partial overlap; mechanism-free baselines;
control check that the reconstructed update order is the real one. No torch."""
import collections
import json
import math
import random
from common import *
from learner_q4_representation import R0NearestNeighbor, from_visible_record

insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
preds = read_jsonl(RUN / "dev_predictions.jsonl")
assert [p["record_id"] for p in preds] == [c["record_id"] for c in insp]
print("distinct predicted ASTs:", len({canon(p["ast"]) for p in preds}), " outcomes:", collections.Counter(p["outcome"] for p in preds), " steps:", collections.Counter(p["steps"] for p in preds))
P = preds[0]["ast"]
Ptok = ast_to_tokens(P)
print("prediction:", show(P), " tokens:", [TOKENS[t] for t in Ptok], " len", len(Ptok))
targets = [c["checker_reference_ast"] for c in insp]
Ttok = [ast_to_tokens(t) for t in targets]
train = read_jsonl(DATA / "visible_G_train.jsonl")
tr = [parse(r["observation"]) for r in train]
dev_all = [parse(r["observation"]) for r in read_jsonl(DATA / "visible_G_dev.jsonl")]


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def bag(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b)
    return sum((ca & cb).values())


def posmatch(a, b):
    return sum(x == y for x, y in zip(a, b))


def leaf_fields_inorder(p, t):
    """Compare predicted leaf i with target leaf i (in-order), field by field, over min(#leaves)."""
    lp, lt = leaves(p), leaves(t)
    out = collections.Counter()
    for a, b in zip(lp, lt):
        for f in ("operator", "domain", "drive"):
            out[f] += a[f] == b[f]
        out["register"] += a.get("register", "ABSENT") == b.get("register", "ABSENT")
        out["whole_leaf"] += a == b
    return out


def metrics(pred, target):
    a, b = ast_to_tokens(pred), ast_to_tokens(target)
    lt = leaves(target)
    st = {(l["operator"], l["domain"]) for l in lt}
    return {"exact": pred == target, "target_len": len(b), "lcp": lcp(a, b), "posmatch": posmatch(a, b), "lcs": lcs(a, b), "bag": bag(a, b),
            "root_op_match": pred.get("op") == target.get("op"), "shape_match": shape(pred) == shape(target),
            "pred_leaf_states_in_target": sum((l["operator"], l["domain"]) in st for l in leaves(pred)),
            "leaves_pred": len(leaves(pred)), "leaves_target": len(lt), **{"inorder_" + k: v for k, v in leaf_fields_inorder(pred, target).items()}}


print("\nPER-RECORD: constant prediction vs each of the 16 references")
rows = []
for c, t in zip(insp, targets):
    m = metrics(P, t)
    rows.append(m)
    print(" %s tlen=%2d lcp=%2d pos=%2d lcs=%2d bag=%2d rootop=%s leaves %d/%d states_in_target=%d inorder(op,dom,drv,reg,leaf)=%s | %s" % (
        c["record_id"], m["target_len"], m["lcp"], m["posmatch"], m["lcs"], m["bag"], m["root_op_match"], m["leaves_pred"], m["leaves_target"],
        m["pred_leaf_states_in_target"], tuple(m.get("inorder_" + k, 0) for k in ("operator", "domain", "drive", "register", "whole_leaf")), c["input"]))


def summarize(name, rows):
    n = len(rows)
    T = sum(r["target_len"] for r in rows)
    print(" %-44s exact %d/%d | lcp mean %.4f | pos-match tokens %d/%d = %.6f | LCS %d/%d = %.6f | bag %d/%d = %.6f | root-op %d/%d | shape %d/%d | inorder leaf fields op %d dom %d drv %d reg %d whole %d (of %d compared leaves)" % (
        name, sum(r["exact"] for r in rows), n, sum(r["lcp"] for r in rows) / n, sum(r["posmatch"] for r in rows), T, sum(r["posmatch"] for r in rows) / T,
        sum(r["lcs"] for r in rows), T, sum(r["lcs"] for r in rows) / T, sum(r["bag"] for r in rows), T, sum(r["bag"] for r in rows) / T,
        sum(r["root_op_match"] for r in rows), n, sum(r["shape_match"] for r in rows), n,
        sum(r.get("inorder_operator", 0) for r in rows), sum(r.get("inorder_domain", 0) for r in rows), sum(r.get("inorder_drive", 0) for r in rows),
        sum(r.get("inorder_register", 0) for r in rows), sum(r.get("inorder_whole_leaf", 0) for r in rows), sum(min(r["leaves_pred"], r["leaves_target"]) for r in rows)))
    return rows


print("\nSUMMARY on the 16 dev records")
summarize("MODEL constant (^7^E + ^7^C)", rows)
print(" target root ops (16):", collections.Counter(t["op"] for t in targets), " all-256 dev root ops:", collections.Counter(t["op"] for t in dev_all))
print(" target leaves that are ^7^E / ^7^C (by noetic^domain):", sum(1 for t in targets for l in leaves(t) if (l["operator"], l["domain"]) == ("^7", "E")), "/", sum(1 for t in targets for l in leaves(t) if (l["operator"], l["domain"]) == ("^7", "C")), " of", sum(len(leaves(t)) for t in targets), "leaves")

# ---- chance level for 'any constant depth-1 tree' : use every train depth-1 tree as the constant ----
d1 = [a for a in tr if depth(a) == 1]
agg = collections.defaultdict(list)
for a in d1:
    rs = [metrics(a, t) for t in targets]
    T = sum(r["target_len"] for r in rs)
    agg["pos"].append(sum(r["posmatch"] for r in rs) / T)
    agg["lcs"].append(sum(r["lcs"] for r in rs) / T)
    agg["bag"].append(sum(r["bag"] for r in rs) / T)
    agg["lcp"].append(sum(r["lcp"] for r in rs) / 16)
mrow = rows
T = sum(r["target_len"] for r in mrow)
mv = {"pos": sum(r["posmatch"] for r in mrow) / T, "lcs": sum(r["lcs"] for r in mrow) / T, "bag": sum(r["bag"] for r in mrow) / T, "lcp": sum(r["lcp"] for r in mrow) / 16}
print("\nCHANCE: each of the %d train depth-1 trees used as a constant prediction on the same 16 targets" % len(d1))
for k in ("lcp", "pos", "lcs", "bag"):
    v = sorted(agg[k])
    rank = sum(x > mv[k] for x in v)
    print(" %-4s model %.6f | constants: min %.6f median %.6f max %.6f | constants strictly better than model: %d/%d" % (k, mv[k], v[0], v[len(v) // 2], v[-1], rank, len(v)))

# ---- mechanism-free baselines on the 16 ----
print("\nMECHANISM-FREE BASELINES on the same 16 dev records")
whole = collections.Counter(canon(a) for a in tr)
print(" whole train trees distinct:", len(whole), " max multiplicity:", max(whole.values()), "-> 'most common train tree' is a 2048-way tie; tie-break = first row in file")
first = tr[0]
summarize("MOST-COMMON-TRAIN-TREE (tie->row0) " + show(first)[:0], [metrics(first, t) for t in targets])
# modal skeleton: most common train bare shape, root op mode, every leaf filled with modal field values
shp = collections.Counter(json.dumps(shape(a)) for a in tr).most_common(1)[0]
print(" most common train bare shape:", shp)
L = [l for a in tr for l in leaves(a)]
mode_leaf = {"node": "StateLiteral", "operator": collections.Counter(l["operator"] for l in L).most_common(1)[0][0],
             "domain": collections.Counter(l["domain"] for l in L).most_common(1)[0][0], "drive": None}
modal = {"node": "BinaryExpr", "op": "PLUS", "left": mode_leaf, "right": mode_leaf}
summarize("MODAL-FIELDS depth-1 tree " + show(modal), [metrics(modal, t) for t in targets])
# modal depth-3 train tree skeleton filled with modal leaves
d3shape = collections.Counter(json.dumps(shape(a)) for a in tr if depth(a) == 3).most_common(1)[0]
def fill(s):
    return mode_leaf if s == "L" else {"node": "BinaryExpr", "op": "PLUS", "left": fill(s[1]), "right": fill(s[2])}
modal3 = fill(json.loads(d3shape[0]))
print(" most common depth-3 train bare shape:", d3shape)
summarize("MODAL depth-3 train skeleton, modal leaves", [metrics(modal3, t) for t in targets])
# R0 nearest neighbour (fixed byte-bag, from the lab's own module; no learning)
r0 = R0NearestNeighbor([(from_visible_record(r), canon(a)) for r, a in zip(train, tr)])
dev_vis = read_jsonl(DATA / "visible_G_dev.jsonl")[:16]
r0p = [json.loads(r0.predict(from_visible_record(v)).label) for v in dev_vis]
summarize("R0 byte-bag nearest train neighbour", [metrics(p, t) for p, t in zip(r0p, targets)])
# leaf-copy into modal depth-3 train skeleton with the right leaf count (regex for literals only, no brackets)
lit = re.compile(r"\^(\d)\^([PCEO])(?:_\{F([1-7])\})?(?:\|([TAfE]))?")
by_count = collections.defaultdict(collections.Counter)
for a in tr:
    by_count[len(leaves(a))][json.dumps(shape(a))] += 1
def leafcopy(text):
    ls = []
    for m in lit.finditer(text):
        d = {"node": "StateLiteral", "operator": "^" + m.group(1), "domain": m.group(2), "drive": ("F" + m.group(3)) if m.group(3) else None}
        if m.group(4):
            d["register"] = m.group(4)
        ls.append(d)
    ops = ["TIMES" if ch == "×" else "PLUS" for ch in text if ch in "+×"]
    s = json.loads(by_count[len(ls)].most_common(1)[0][0]) if by_count[len(ls)] else json.loads(shp[0])
    it, io = iter(ls), iter(ops)
    def build(s):
        if s == "L":
            return next(it)
        left = build(s[1]); op = next(io, "PLUS"); right = build(s[2])
        return {"node": "BinaryExpr", "op": op, "left": left, "right": right}
    return build(s)
lc = [leafcopy(v["observation"]) for v in dev_vis]
summarize("LEAF-COPY regex + modal train shape by leaf count", [metrics(p, t) for p, t in zip(lc, targets)])
# the deterministic parser (R5's 20-line parser) = ceiling
pp = [parse(v["observation"]) for v in dev_vis]
summarize("R5 PARSER (brackets + literal regex)", [metrics(p, t) for p, t in zip(pp, targets)])
print(" parser on all 256 dev: see s1 (16/16 checked against saved references only; the other 240 references are sealed and NOT opened)")

# ---- greedy decode of the input-blind depth-aware prior (B3) through the SAME grammar mask ----
toks_all = [ast_to_tokens(a) for a in tr]
cnt = collections.defaultdict(collections.Counter)
for s in toks_all:
    for t, (k, d) in zip(s, slot_sequence(s)):
        cnt[(k, d if k == "expr" else None)][t] += 1
prefix = ()
while True:
    allowed = allowed_next(prefix)
    if not allowed:
        break
    sl = slot_sequence(prefix + (allowed[0],))[-1]
    key = (sl[0], sl[1] if sl[0] == "expr" else None)
    if sl[0] == "eos":
        prefix += (TOKEN_IDS["EOS"],); break
    best = min(allowed, key=lambda t: (-cnt[key][t], t))
    prefix += (best,)
    if TOKENS[best] == "EOS":
        break
print("\nGREEDY decode of the input-blind prior B3 (slot + node depth), same grammar mask, lowest-id ties:")
print(" tokens:", [TOKENS[t] for t in prefix], " len", len(prefix))
from learner_q4_decoder import tokens_to_ast
g = tokens_to_ast(prefix)
print(" tree:", show(g), " same skeleton as model (shape, root op, drive, register):",
      shape(g) == shape(P) and g["op"] == P["op"] and all(a["drive"] == b["drive"] and ("register" in a) == ("register" in b) for a, b in zip(leaves(g), leaves(P))))
print(" token positions where model output differs from B3-greedy:", [(i, TOKENS[a], TOKENS[b]) for i, (a, b) in enumerate(zip(Ptok, prefix)) if a != b])
summarize("B3-GREEDY input-blind prior tree " + show(g), [metrics(g, t) for t in targets])

# ---- control: is the reconstructed order the real one? Pearson(model loss, B3 CE) under random orders ----
upd = read_jsonl(RUN / "updates.jsonl")
loss = [u["loss"] for u in upd]
def ce(tokens):
    return sum(-math.log(cnt[(k, d if k == "expr" else None)][t] / sum(cnt[(k, d if k == "expr" else None)].values())) if k != "eos" else 0.0
               for t, (k, d) in zip(tokens, slot_sequence(tokens))) / len(tokens)
def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
used = json.load(open("used_rows.json"))["idx"]
real = pearson(loss[96:], [ce(toks_all[i]) for i in used[96:]])
rng = random.Random(12345)
null = []
for _ in range(2000):
    o = list(range(2048)); rng.shuffle(o)
    null.append(pearson(loss[96:], [ce(toks_all[i]) for i in o[96:128]]))
null.sort()
print("\nORDER CONTROL: Pearson(loss upd 97-128, B3 CE) with reconstructed order = %.6f; 2000 random orders: max %.6f, 99th pct %.6f, #>=real %d" % (
    real, null[-1], null[int(0.99 * len(null))], sum(x >= real for x in null)))
