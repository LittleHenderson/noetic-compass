"""R7 contrarian checks on the Q4 smoke. Pure Python. No torch. Visible files + records only.

Never opens sealed_* files. Reads: visible_G_train.jsonl, visible_G_dev.jsonl,
records/q4_authorized_20260922/inspected_predictions.json, run_001/updates.jsonl,
run_001/dev_predictions.jsonl.
"""
import collections
import json
import math
import random
import re
import sys

ROOT = (r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
        r"/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
DATA = ROOT + "/research/helm_cas_expression_lab/data/q3_v0_7"
REC = ROOT + "/records/q4_authorized_20260922"

LIT = re.compile(r"\^(\d)\^([PCEO])(?:_\{(F[1-7])\})?(?:\|([TAfE]))?")


def parse(text):
    """My own 20-line parser for the G surface grammar -> lab AST dict."""
    pos = 0

    def expr():
        nonlocal pos
        if text[pos] == "(":
            pos += 1
            left = expr()
            assert text[pos] == " "
            pos += 1
            op = {"+": "PLUS", "\u00d7": "TIMES"}[text[pos]]
            pos += 1
            assert text[pos] == " "
            pos += 1
            right = expr()
            assert text[pos] == ")"
            pos += 1
            return {"node": "BinaryExpr", "op": op, "left": left, "right": right}
        m = LIT.match(text, pos)
        assert m, (text, pos)
        pos = m.end()
        node = {"node": "StateLiteral", "operator": "^" + m.group(1), "domain": m.group(2), "drive": m.group(3)}
        if m.group(4) is not None:
            node["register"] = m.group(4)
        return node

    ast = expr()
    assert pos == len(text), (text, pos)
    return ast


def shape(ast):
    if ast["node"] == "BinaryExpr":
        return ("B", shape(ast["left"]), shape(ast["right"]))
    return "L"


def depth(s):
    return 0 if s == "L" else 1 + max(depth(s[1]), depth(s[2]))


def tokens(ast):
    out = []

    def visit(n, d):
        if n["node"] == "StateLiteral":
            reg = "REG_ABSENT" if "register" not in n else ("REG_NULL" if n["register"] is None else "REG_" + n["register"])
            out.append(("expr", d, "STATE"))
            out.append(("noetic", d, "N" + n["operator"][1:]))
            out.append(("domain", d, "D_" + n["domain"]))
            out.append(("drive", d, "F_NONE" if n["drive"] is None else n["drive"]))
            out.append(("register", d, reg))
        else:
            out.append(("expr", d, "BINARY"))
            out.append(("op", d, n["op"]))
            visit(n["left"], d + 1)
            visit(n["right"], d + 1)

    visit(ast, 0)
    out.append(("end", 0, "EOS"))
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    train = load(DATA + "/visible_G_train.jsonl")
    dev = load(DATA + "/visible_G_dev.jsonl")
    insp = json.load(open(REC + "/inspected_predictions.json", encoding="utf-8"))["cases"]
    print("train rows", len(train), "dev rows", len(dev), "inspected cases", len(insp))

    # 1. my parser vs the frozen reference ASTs for the 16 inspected dev cases
    agree = sum(parse(c["input"]) == c["checker_reference_ast"] for c in insp)
    print("MY_PARSER_EXACT_VS_REFERENCE", agree, "/", len(insp))
    in_dev_order = [c["record_id"] for c in insp] == [r["record_id"] for r in dev[:16]]
    print("inspected cases are the first 16 dev rows in file order:", in_dev_order)

    # 2. depth / shape facts from visible text only
    tr_ast = [parse(r["observation"]) for r in train]
    dv_ast = [parse(r["observation"]) for r in dev]
    tr_shapes = collections.Counter(shape(a) for a in tr_ast)
    dv_shapes = collections.Counter(shape(a) for a in dv_ast)
    print("train depth counts", dict(sorted(collections.Counter(depth(shape(a)) for a in tr_ast).items())))
    print("dev depth counts", dict(sorted(collections.Counter(depth(shape(a)) for a in dv_ast).items())))
    print("train bare shapes", len(tr_shapes), "dev bare shapes", len(dv_shapes),
          "shared", len(set(tr_shapes) & set(dv_shapes)))
    top = tr_shapes.most_common(3)
    print("most common train shapes", [(str(s), n) for s, n in top])

    # 3. the prediction
    preds = load(REC + "/run_001/dev_predictions.jsonl")
    uniq = {json.dumps(p["ast"], sort_keys=True) for p in preds}
    pred_ast = preds[0]["ast"]
    print("distinct predicted ASTs", len(uniq), "pred shape", shape(pred_ast), "depth", depth(shape(pred_ast)),
          "pred shape in train shapes:", shape(pred_ast) in tr_shapes, "count", tr_shapes.get(shape(pred_ast)))
    exact_in_train = sum(a == pred_ast for a in tr_ast)
    print("predicted tree appears verbatim in train:", exact_in_train, "times")

    # 4. which 128 train rows were used (frozen loop: random.Random(seed).shuffle(range(2048)); first 128)
    order = list(range(len(train)))
    random.Random(20260921).shuffle(order)
    seen = order[:128]
    print("distinct seen indices", len(set(seen)), "first five", seen[:5])
    seen_ast = [tr_ast[i] for i in seen]
    print("seen depth counts", dict(sorted(collections.Counter(depth(shape(a)) for a in seen_ast).items())))

    # slot-majority input-blind statistics over the 128 seen rows and over all 2048
    for label, pool in (("seen128", seen_ast), ("all2048", tr_ast)):
        slots = collections.defaultdict(collections.Counter)
        for a in pool:
            for kind, d, tok in tokens(a):
                slots[(kind, min(d, 3))][tok] += 1
                slots[(kind, "any")][tok] += 1
        print("==", label)
        for key in (("expr", 0), ("expr", 1), ("expr", 2), ("op", 0), ("op", "any"), ("noetic", 1), ("noetic", "any"),
                    ("domain", 1), ("domain", "any"), ("drive", "any"), ("register", "any")):
            print("  ", key, slots[key].most_common(5))

    # 5. input-blind loss floor: per-token cross-entropy of a model that knows ONLY the generator's
    # slot distributions (no input). Structure decisions use empirical all-2048 slot frequencies by depth.
    struct = collections.defaultdict(collections.Counter)
    for a in tr_ast:
        for kind, d, tok in tokens(a):
            if kind in ("expr", "op", "end"):
                struct[(kind, d)][tok] += 1
    gen = {"noetic": {("N%d" % k): 0.1 for k in range(10)},
           "domain": {("D_" + x): 0.25 for x in "PCEO"},
           "drive": dict({"F_NONE": 0.5}, **{("F%d" % k): 0.5 / 7 for k in range(1, 8)}),
           "register": dict({"REG_ABSENT": 0.5}, **{("REG_" + x): 0.125 for x in "TAfE"})}

    def blind_loss(a):
        tot, n = 0.0, 0
        for kind, d, tok in tokens(a):
            if kind in gen:
                p = gen[kind][tok]
            elif kind == "end":
                p = 1.0
            else:
                c = struct[(kind, d)]
                p = c[tok] / sum(c.values())
            tot += -math.log(p)
            n += 1
        return tot / n

    upd = load(REC + "/run_001/updates.jsonl")
    losses = [u["loss"] for u in upd]
    print("updates", len(upd), "first", losses[0], "last", losses[-1], "ln(34)", math.log(34))
    for lo, hi in ((0, 16), (96, 128), (112, 128)):
        logged = sum(losses[lo:hi]) / (hi - lo)
        blind = sum(blind_loss(tr_ast[seen[i]]) for i in range(lo, hi)) / (hi - lo)
        print("updates %d-%d mean logged loss %.6f ; input-blind prior loss on the SAME examples %.6f" % (lo + 1, hi, logged, blind))
    lastk = [(i + 1, losses[i], blind_loss(tr_ast[seen[i]])) for i in range(120, 128)]
    for row in lastk:
        print("  update %d logged %.6f blind %.6f" % row)
    below = sum(losses[i] < blind_loss(tr_ast[seen[i]]) for i in range(96, 128))
    print("of updates 97-128, logged loss below the input-blind prior loss:", below, "/ 32")

    # 6. same-input check: is the model's prediction a function of the input at all? (all 16 identical)
    print("16 inputs distinct:", len({c["input"] for c in insp}), "; predictions distinct:", len(uniq))


if __name__ == "__main__":
    sys.exit(main())
