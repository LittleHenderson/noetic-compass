"""R2 read-only analysis of Q3 v0.7 family G (visible train/dev files only) and the Q4 smoke record.

No torch, no model load, no sealed file, no eval file. Pure Python.
Measures:
  1. a ~40-line hand parser (mechanism-free) vs the 16 frozen dev reference ASTs saved in inspected_predictions.json
  2. byte lengths of the GRU input and AST-token lengths of the targets (targets derived from VISIBLE text by the hand parser)
  3. which 128 train rows the smoke actually saw (same shuffle as q4_smoke_job.py) and their depth mix
  4. an INPUT-FREE prior decoder (ignores the expression entirely) built from those 128 rows, greedy-decoded
     with the same grammar mask and tie rule as learner_q4_decoder.free_decode
  5. the input-free per-token cross-entropy vs the logged losses
"""
import collections
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
DATA = LAB / "data/q3_v0_7"
RUN = ROOT / "records/q4_authorized_20260922"
sys.path.insert(0, str(LAB))
import learner_q4_decoder as dec  # pure python codec + grammar mask; imports no torch

assert "torch" not in sys.modules


def read_jsonl(path):
    rows = []
    for line in path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8").split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


# ---------------- 1. the mechanism-free hand parser ----------------
class P:
    def __init__(self, s):
        self.s, self.i = s, 0

    def peek(self):
        while self.i < len(self.s) and self.s[self.i] == " ":
            self.i += 1
        return self.s[self.i] if self.i < len(self.s) else ""

    def take(self, ch):
        assert self.peek() == ch, (self.s, self.i, ch)
        self.i += 1

    def expr(self):
        if self.peek() == "(":
            self.take("(")
            left = self.expr()
            op = self.peek()
            self.i += 1
            right = self.expr()
            self.take(")")
            return {"node": "BinaryExpr", "op": {"+": "PLUS", "\u00d7": "TIMES"}[op], "left": left, "right": right}
        self.take("^")
        n = self.s[self.i]; self.i += 1
        self.take("^")
        d = self.s[self.i]; self.i += 1
        node = {"node": "StateLiteral", "operator": "^" + n, "domain": d, "drive": None}
        if self.s.startswith("_{F", self.i):
            node["drive"] = "F" + self.s[self.i + 3]
            self.i += 5
        if self.i < len(self.s) and self.s[self.i] == "|":
            node["register"] = self.s[self.i + 1]
            self.i += 2
        return node


def parse(s):
    p = P(s)
    tree = p.expr()
    assert p.peek() == "", s
    return tree


def depth(t):
    return 0 if t["node"] == "StateLiteral" else 1 + max(depth(t["left"]), depth(t["right"]))


inspected = json.loads((RUN / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
hits = sum(parse(c["input"]) == c["checker_reference_ast"] for c in inspected)
preds = {json.dumps(c["original_learned_prediction"]["ast"], sort_keys=True) for c in inspected}
print("1. hand parser vs frozen dev reference ASTs: %d / %d exact" % (hits, len(inspected)))
print("   distinct learned predictions among the 16:", len(preds))

# ---------------- 2. lengths ----------------
train = read_jsonl(DATA / "visible_G_train.jsonl")
dev = read_jsonl(DATA / "visible_G_dev.jsonl")
print("2. visible rows: train %d, dev %d" % (len(train), len(dev)))
for name, rows in (("train", train), ("dev", dev)):
    trees = [parse(r["observation"]) for r in rows]
    blen = [len(r["observation"].encode("utf-8")) for r in rows]
    tlen = [len(dec.ast_to_tokens(t)) for t in trees]
    dcount = collections.Counter(depth(t) for t in trees)
    print("   %s: depth counts %s" % (name, dict(sorted(dcount.items()))))
    print("   %s: input UTF-8 bytes min %d mean %.3f max %d" % (name, min(blen), sum(blen) / len(blen), max(blen)))
    print("   %s: target AST tokens (incl EOS) min %d mean %.3f max %d; rows with <=64 tokens: %d of %d"
          % (name, min(tlen), sum(tlen) / len(tlen), max(tlen), sum(x <= 64 for x in tlen), len(tlen)))
    if name == "dev":
        d3 = [(b, t) for b, t, tr in zip(blen, tlen, trees) if depth(tr) == 3]
        print("   dev depth-3 rows %d: bytes mean %.3f; tokens mean %.3f" % (len(d3), sum(b for b, _ in d3) / len(d3), sum(t for _, t in d3) / len(d3)))

# ---------------- 3. the 128 rows the smoke saw ----------------
order = list(range(len(train)))
random.Random(20260921).shuffle(order)
seen_idx = [order[u % len(order)] for u in range(128)]
seen = [dec.ast_to_tokens(parse(train[i]["observation"])) for i in seen_idx]
seen_trees = [parse(train[i]["observation"]) for i in seen_idx]
print("3. smoke saw %d updates over %d distinct rows (%.4f of the pool)" % (len(seen_idx), len(set(seen_idx)), len(set(seen_idx)) / len(train)))
print("   depth counts of seen rows:", dict(sorted(collections.Counter(depth(t) for t in seen_trees).items())))

# check: the first logged update's loss is the loss on seen[0]; report its token count
print("   first seen row:", train[seen_idx[0]]["observation"], "tokens", len(seen[0]))


# ---------------- 4. INPUT-FREE prior decoders ----------------
def slot_contexts(tokens):
    """Yield (context, token) with context = (slot kind, depth) exactly as allowed_next tracks it."""
    pending = [("expr", 0)]
    out = []
    for tok in tokens:
        name = dec.TOKENS[tok]
        if not pending:
            out.append((("END",), name))
            continue
        slot, d = pending.pop()
        out.append(((slot, d), name))
        if slot == "expr":
            if name == "STATE":
                pending.extend((k, d) for k in ("register", "drive", "domain", "noetic"))
            else:
                pending.extend((("expr", d + 1), ("expr", d + 1), ("op", d)))
    return out


def fit(seqs, key):
    table = collections.defaultdict(collections.Counter)
    for s in seqs:
        for ctx, name in slot_contexts(s):
            table[key(ctx)][name] += 1
    return table


def greedy(table, key):
    prefix = ()
    for _ in range(200):
        allowed = dec.allowed_next(prefix)
        if not allowed:
            break
        # context of the next slot
        pending = [("expr", 0)]
        for tok in prefix:
            name = dec.TOKENS[tok]
            slot, d = pending.pop()
            if slot == "expr":
                if name == "STATE":
                    pending.extend((k, d) for k in ("register", "drive", "domain", "noetic"))
                else:
                    pending.extend((("expr", d + 1), ("expr", d + 1), ("op", d)))
        ctx = pending[-1] if pending else ("END",)
        counts = table.get(key(ctx), collections.Counter())
        chosen = min(allowed, key=lambda t: (-counts.get(dec.TOKENS[t], 0), t))
        prefix += (chosen,)
        if dec.TOKENS[chosen] == "EOS":
            return dec.tokens_to_ast(prefix)
    return None


def show(t):
    if t["node"] == "StateLiteral":
        s = t["operator"] + "^" + t["domain"]
        if t["drive"]:
            s += "_{%s}" % t["drive"]
        if "register" in t:
            s += "|" + str(t["register"])
        return s
    return "(%s %s %s)" % (show(t["left"]), {"PLUS": "+", "TIMES": "x"}[t["op"]], show(t["right"]))


learned = inspected[0]["original_learned_prediction"]["ast"]
print("4. the smoke's learned prediction (all 16):", show(learned))
for label, key in (("slot kind only", lambda c: c[0]), ("slot kind + depth", lambda c: c)):
    for pool_name, pool in (("the 128 seen rows", seen), ("all 2048 train rows", [dec.ast_to_tokens(parse(r["observation"])) for r in train])):
        tab = fit(pool, key)
        g = greedy(tab, key)
        print("   input-free greedy [%s, fitted on %s]: %s  | equals learned prediction: %s" % (label, pool_name, show(g), g == learned))
        if label == "slot kind + depth" and pool_name == "the 128 seen rows":
            for ctx in (("noetic", 1), ("domain", 1), ("drive", 1), ("register", 1), ("op", 0), ("expr", 1)):
                print("      counts at", ctx, dict(tab.get(ctx, {})))


# ---------------- 5. input-free cross entropy vs logged losses ----------------
def mean_ce(seqs, table, key):
    per_example = []
    for s in seqs:
        ce = []
        for ctx, name in slot_contexts(s):
            c = table.get(key(ctx), collections.Counter())
            tot = sum(c.values())
            p = c.get(name, 0) / tot if tot else 0.0
            ce.append(-math.log(p) if p > 0 else float("inf"))
        per_example.append(sum(ce) / len(ce))
    return per_example


all_train = [dec.ast_to_tokens(parse(r["observation"])) for r in train]
upd = read_jsonl(RUN / "run_001/updates.jsonl")
losses = [u["loss"] for u in upd]
print("5. logged losses: n %d, first %r, last %r, mean of first 16 %.6f, mean of last 16 %.6f, min %.6f"
      % (len(losses), losses[0], losses[-1], sum(losses[:16]) / 16, sum(losses[-16:]) / 16, min(losses)))
print("   uniform over %d output tokens: ln = %.6f" % (len(dec.TOKENS), math.log(len(dec.TOKENS))))
for label, key in (("slot kind only", lambda c: c[0]), ("slot kind + depth", lambda c: c)):
    tab = fit(all_train, key)   # population prior (a decoder that sees NO input, perfectly calibrated on train)
    ce = mean_ce([seen[u] for u in range(128)], tab, key)
    print("   input-free CE on the same 128 updates [%s, prior fitted on all 2048 train]: mean %.6f, last-16 mean %.6f"
          % (label, sum(ce) / len(ce), sum(ce[-16:]) / 16))
    # alignment check with logged per-update losses
    diffs = [l - c for l, c in zip(losses, ce)]
    print("      logged minus input-free, last 16 updates: mean %.6f" % (sum(diffs[-16:]) / 16))
