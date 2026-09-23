"""RT2 POST-HOC (written AFTER the run; NOT a rule input). Pure Python, no torch, visible files + RT2 outputs only.
1. Round-trip check: a correct token sequence scores as exact (tokens_to_ast(ast_to_tokens(t)) == t) on S, set(ii), dev256.
2. Training loss per pass over S (256 updates each) from rt2_updates.jsonl.
3. Reference CEs: input-blind slot prior (IB2, one pass over S) with the tree-structure slots given free ('shape oracle'),
   and with structure + operator slots given free ('shape+op oracle'). A model that knew shape (and op) perfectly but leaf
   content only at the prior would score about these. DIAGNOSTIC_NOT_CLAIM_BEARING."""
import collections, json, math, random, sys
from pathlib import Path
SCR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCR / "R5"))
from common import parse, depth, slot_sequence, DATA, read_jsonl
from learner_q4_decoder import ast_to_tokens, tokens_to_ast, allowed_next
from q3_load import load_visible
R = json.loads((SCR / "RT2/rt2_results.json").read_text(encoding="utf-8"))
train = load_visible(DATA, "G", "train")[:2048]
dev = load_visible(DATA, "G", "dev")
tr = [parse(r["observation"]) for r in train]
dv = [parse(r["observation"]) for r in dev]
S, set2 = R["sets"]["S_idx"], R["sets"]["set2_idx"]
order = list(range(2048)); random.Random(20260921).shuffle(order)
assert S == order[:256]
sets = {"S": [tr[i] for i in S], "set2": [tr[i] for i in set2], "dev256": dv}
for k, v in sets.items():
    print("round-trip exact-if-correct %s: %d/%d" % (k, sum(tokens_to_ast(ast_to_tokens(a)) == a for a in v), len(v)))
log = read_jsonl(SCR / "RT2/rt2_updates.jsonl")
print("updates logged:", len(log), "| rows follow S cycle:", all(r["row"] == S[(r["update"] - 1) % 256] for r in log))
for p in range(8):
    seg = log[p * 256:(p + 1) * 256]
    if seg:
        print(" pass %d (updates %d-%d): mean loss %.6f  min %.6f  max %.6f" % (p + 1, seg[0]["update"], seg[-1]["update"],
              sum(r["loss"] for r in seg) / len(seg), min(r["loss"] for r in seg), max(r["loss"] for r in seg)))
C = collections.defaultdict(collections.Counter)
for i in S:
    s = ast_to_tokens(tr[i])
    for t, (k, d) in zip(s, slot_sequence(s)):
        C[(k, d if k == "expr" else None)][t] += 1.0 / len(s)
def ref(s, free):
    v, share = [], collections.Counter()
    for i, (t, (k, d)) in enumerate(zip(s, slot_sequence(s))):
        share[k] += 1
        if k == "eos" or k in free:
            v.append(0.0); continue
        legal = allowed_next(tuple(s[:i])); c = C[(k, d if k == "expr" else None)]
        v.append(-math.log((c[t] + 0.01) / (sum(c[u] for u in legal) + 0.01 * len(legal))))
    return sum(v) / len(v), share
for k, v in sets.items():
    toks = [ast_to_tokens(a) for a in v]
    full = [ref(s, ())[0] for s in toks]
    shp = [ref(s, ("expr",))[0] for s in toks]
    shpop = [ref(s, ("expr", "op"))[0] for s in toks]
    share = collections.Counter()
    for s in toks:
        share.update(ref(s, ())[1])
    tot = sum(share.values())
    gru = R["evals"]["end"][k]["CE"]["GRU"]
    print("%s: GRU(end) %.6f | IB2 prior %.6f | shape-oracle+prior %.6f | shape+op-oracle+prior %.6f | token share %s" % (
        k, gru, sum(full) / len(full), sum(shp) / len(shp), sum(shpop) / len(shpop),
        json.dumps({kk: round(vv / tot, 6) for kk, vv in sorted(share.items())})))
