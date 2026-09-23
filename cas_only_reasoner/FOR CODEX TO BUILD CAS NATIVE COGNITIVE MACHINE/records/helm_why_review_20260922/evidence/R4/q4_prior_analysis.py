"""R4 Q4 forensics: pure-Python, no torch, no model. Reads only VISIBLE G train/dev rows,
run_001 records, and inspected_predictions.json (a record). Never opens sealed_* or eval files.

Targets are rebuilt by parsing the VISIBLE observation text (reconstruction task: target = parse).
The parser is validated against the 16 frozen dev references stored in inspected_predictions.json.
"""
import json, math, random, sys, collections, pathlib

ROOT = pathlib.Path(sys.argv[1])
LAB = ROOT / "research" / "helm_cas_expression_lab"
REC = ROOT / "records" / "q4_authorized_20260922"
sys.path.insert(0, str(LAB))
import learner_q4_decoder as dec  # pure Python; imports learner_q4_representation (pure Python)

TOK, TID, V = dec.TOKENS, dec.TOKEN_IDS, len(dec.TOKENS)


def parse(text):
    i = 0

    def expr():
        nonlocal i
        if text[i] == "(":
            i += 1
            left = expr()
            assert text[i] == " ", (text, i)
            op = {"+": "PLUS", "×": "TIMES"}[text[i + 1]]
            assert text[i + 2] == " "
            i += 3
            right = expr()
            assert text[i] == ")"
            i += 1
            return {"node": "BinaryExpr", "op": op, "left": left, "right": right}
        assert text[i] == "^"
        operator = text[i:i + 2]; i += 2
        assert text[i] == "^"
        domain = text[i + 1]; i += 2
        drive = None
        if text.startswith("_{F", i):
            drive = "F" + text[i + 3]; assert text[i + 4] == "}"; i += 5
        node = {"node": "StateLiteral", "operator": operator, "domain": domain, "drive": drive}
        if i < len(text) and text[i] == "|":
            node["register"] = text[i + 1]; i += 2
        return node

    tree = expr()
    assert i == len(text), (text, i)
    return tree


def depth(t):
    return 0 if t["node"] == "StateLiteral" else 1 + max(depth(t["left"]), depth(t["right"]))


def shape(t):
    return "s" if t["node"] == "StateLiteral" else "(" + shape(t["left"]) + shape(t["right"]) + ")"


def show(t):
    if t["node"] == "StateLiteral":
        s = t["operator"] + "^" + t["domain"]
        if t["drive"]: s += "_{%s}" % t["drive"]
        if "register" in t: s += "|%s" % t["register"]
        return s
    return "(%s %s %s)" % (show(t["left"]), "+" if t["op"] == "PLUS" else "x", show(t["right"]))


def rows(name):
    return [json.loads(l) for l in (LAB / "data" / "q3_v0_7" / name).read_text(encoding="utf-8").split("\n") if l.strip()]


train = rows("visible_G_train.jsonl")
dev = rows("visible_G_dev.jsonl")
train_ast = [parse(r["observation"]) for r in train]
dev_ast = [parse(r["observation"]) for r in dev]

# 1. parser validation against the frozen references kept in the record
insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
ok = sum(parse(c["input"]) == c["checker_reference_ast"] for c in insp)
print("PARSER_CHECK: my parse == frozen reference AST for %d/%d inspected dev cases" % (ok, len(insp)))
ids16 = [c["record_id"] for c in insp]
print("inspected ids == first 16 dev ids:", ids16 == [r["record_id"] for r in dev[:16]])
preds = [json.loads(l) for l in (REC / "run_001" / "dev_predictions.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()]
uniq = {json.dumps(p["ast"], sort_keys=True) for p in preds}
print("saved predictions: n=%d unique=%d shown=%s steps=%s" % (len(preds), len(uniq), show(preds[0]["ast"]), sorted({p["steps"] for p in preds})))

# 2. training order exactly as q4_smoke_job.py:336-341
order = list(range(len(train)))
random.Random(20260921).shuffle(order)
seen = [order[u % len(order)] for u in range(128)]
print("distinct examples used in 128 updates:", len(set(seen)), "of pool", len(train))

tok = [dec.ast_to_tokens(t) for t in train_ast]
dtok = [dec.ast_to_tokens(t) for t in dev_ast]
C = collections.Counter
print("depth pool:", sorted(C(depth(t) for t in train_ast).items()))
print("depth 128 seen:", sorted(C(depth(train_ast[i]) for i in seen).items()))
print("depth dev all 256:", sorted(C(depth(t) for t in dev_ast).items()), " first16:", sorted(C(depth(t) for t in dev_ast[:16]).items()))
print("target token length: pool mean %.4f; seen mean %.4f; dev16 mean %.4f; predicted 13" % (
    sum(map(len, tok)) / len(tok), sum(len(tok[i]) for i in seen) / 128, sum(map(len, dtok[:16])) / 16))
print("input bytes: seen mean %.4f; dev16 mean %.4f" % (
    sum(len(train[i]["observation"].encode()) for i in seen) / 128,
    sum(len(r["observation"].encode()) for r in dev[:16]) / 16))
tr_shapes = {shape(t) for t in train_ast}
print("dev16 bare shapes present in train pool:", sum(shape(t) in tr_shapes for t in dev_ast[:16]), "/16")
pred_ast = preds[0]["ast"]
print("predicted tree appears verbatim in train pool:", sum(t == pred_ast for t in train_ast),
      "; its shape (ss) count in pool:", sum(shape(t) == "(ss)" for t in train_ast),
      "; in 128 seen:", sum(shape(train_ast[i]) == "(ss)" for i in seen))


# 3. slot contexts (derived ONLY from the generated prefix, exactly like the decoder mask)
import functools
@functools.lru_cache(maxsize=None)
def slot_of(prefix):
    allowed = dec.allowed_next(prefix)
    names = {TOK[a] for a in allowed}
    if not names or names == {"EOS"}:
        return "end"
    if names <= {"STATE", "BINARY"}: return "expr"
    for k in ("op", "noetic", "domain", "drive", "register"):
        if names <= dec._FIELDS[k]: return k
    return "?"


@functools.lru_cache(maxsize=None)
def expr_depth(prefix):
    # depth of the slot being filled (replicates pending-stack logic of allowed_next)
    pending = [("expr", 0)]
    for t in prefix:
        slot, d = pending.pop()
        if slot == "expr":
            if TOK[t] == "STATE":
                pending.extend((k, d) for k in ("register", "drive", "domain", "noetic"))
            else:
                pending.extend((("expr", d + 1), ("expr", d + 1), ("op", d)))
    return pending[-1][1] if pending else -1


CTX = {
    "slot": lambda p: slot_of(p),
    "slot+depth": lambda p: (slot_of(p), expr_depth(p)),
    "slot+position": lambda p: (slot_of(p), len(p)),
}


def fit(indices, ctxf):
    counts = collections.defaultdict(collections.Counter)
    for i in indices:
        t = tok[i]
        for j in range(len(t)):
            counts[ctxf(t[:j])][t[j]] += 1
    return counts


def nll(counts, ctxf, t, alpha):
    total = 0.0
    for j in range(len(t)):
        c = counts.get(ctxf(t[:j]), collections.Counter())
        p = (c[t[j]] + alpha) / (sum(c.values()) + alpha * V)
        total -= math.log(p)
    return total / len(t)


logged = [json.loads(l) for l in (REC / "run_001" / "updates.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()]
assert [r["update"] for r in logged] == list(range(1, 129))
model_loss = [r["loss"] for r in logged]
print("\nln(34) = %.10f ; logged loss update 1 = %.10f" % (math.log(V), model_loss[0]))


def window(xs, a, b):
    return sum(xs[a:b]) / (b - a)


print("\nMEAN per-token cross-entropy (nats) on the example scored at each update (loss is computed BEFORE that update's step,")
print("and every example is used once, so each logged loss is on an example the model had not yet trained on):")
print("%-44s %10s %10s %10s %10s" % ("predictor", "upd1-16", "upd57-72", "upd113-128", "upd97-128"))
print("%-44s %10.4f %10.4f %10.4f %10.4f" % ("R1 GRU logged loss", window(model_loss, 0, 16), window(model_loss, 56, 72), window(model_loss, 112, 128), window(model_loss, 96, 128)))
uni = [math.log(V)] * 128
print("%-44s %10.4f %10.4f %10.4f %10.4f" % ("uniform over 34 tokens (input-blind)", *(window(uni, a, b) for a, b in ((0, 16), (56, 72), (112, 128), (96, 128)))))
for alpha in (1.0, 0.1):
    for name, ctxf in CTX.items():
        preq = []
        for u in range(128):
            counts = fit(seen[:u], ctxf)  # only examples of earlier updates, like the model
            preq.append(nll(counts, ctxf, tok[seen[u]], alpha))
        print("%-44s %10.4f %10.4f %10.4f %10.4f" % ("prequential input-blind count[%s] a=%g" % (name, alpha),
              *(window(preq, a, b) for a, b in ((0, 16), (56, 72), (112, 128), (96, 128)))))
for name, ctxf in CTX.items():
    full = fit(range(len(tok)), ctxf)
    fl = [nll(full, ctxf, tok[i], 1e-9) for i in seen]
    print("%-44s %10.4f %10.4f %10.4f %10.4f" % ("input-blind count[%s] fit on all 2048" % name,
          *(window(fl, a, b) for a, b in ((0, 16), (56, 72), (112, 128), (96, 128)))))

# 4. what an INPUT-BLIND greedy decoder produces (callback ignores the bottleneck)
from learner_q4_representation import Bottleneck
print("\nGreedy decode through the repo's own free_decode, with an input-blind count model as next_logits:")
for pool_name, pool in (("128 seen", seen), ("2048 pool", list(range(len(tok))))):
    for name, ctxf in CTX.items():
        counts = fit(pool, ctxf)

        def logits(_b, prefix, counts=counts, ctxf=ctxf):
            c = counts.get(ctxf(prefix), collections.Counter())
            n = sum(c.values())
            return tuple(math.log((c[k] + 1e-6) / (n + 1e-6 * V)) for k in range(V))

        r = dec.free_decode(Bottleneck((0.0,)), logits)
        print("  fit=%-9s ctx=%-14s -> %s  steps=%d  same_as_R1=%s" % (pool_name, name, show(r.ast) if r.ast else r.outcome, r.steps, r.ast == pred_ast))

# 5. the expr-slot choice statistics that decide tree depth under greedy decoding
print("\nP(BINARY) at expr slots by slot depth (input-blind frequencies):")
for pool_name, pool in (("128 seen", seen), ("2048 pool", range(len(tok)))):
    c = collections.defaultdict(collections.Counter)
    for i in pool:
        t = tok[i]
        for j in range(len(t)):
            if slot_of(t[:j]) == "expr":
                c[expr_depth(t[:j])][TOK[t[j]]] += 1
    print("  %s:" % pool_name, {d: "%d/%d=%.4f" % (v["BINARY"], v["BINARY"] + v["STATE"], v["BINARY"] / (v["BINARY"] + v["STATE"])) for d, v in sorted(c.items())})
    c2 = collections.defaultdict(collections.Counter)
    for i in pool:
        t = tok[i]
        for j in range(len(t)):
            c2[(slot_of(t[:j]), len(t[:j]))][TOK[t[j]]] += 1
    for j in range(13):
        best = [(k, (s, jj)) for (s, jj), k in c2.items() if jj == j]
        agg = collections.Counter()
        for k, _ in best: agg.update(k)
        top = agg.most_common(3)
        print("    pos %2d top: %s" % (j, top))

print("\nNoetic / domain / drive / register frequencies in the 128 seen targets:")
agg = collections.Counter(TOK[x] for i in seen for x in tok[i])
for k in ("noetic", "domain", "drive", "register", "op"):
    print("  %-8s" % k, sorted(((n, agg[n]) for n in dec._FIELDS[k]), key=lambda kv: -kv[1]))
