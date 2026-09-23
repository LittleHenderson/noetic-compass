"""Stage 2: the 128 updates. Reconstruct which rows were used (frozen loop + seed), loss trend,
gradient norms, and input-blind baselines computed on the SAME examples. No torch."""
import collections
import json
import math
import random
from common import *

upd = read_jsonl(RUN / "updates.jsonl")
plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
assert [u["update"] for u in upd] == list(range(1, 129))
print("keys in update rows:", sorted(upd[0].keys()))
print("any example id field logged:", any(k for k in upd[0] if "id" in k.lower() or "index" in k.lower() or "example" in k.lower()))
loss = [u["loss"] for u in upd]
gn = [u["pre_clip_gradient_norm"] for u in upd]

# --- reconstruct the order exactly as q4_smoke_job.py:336-341 does ---
n_pool = plan["train_examples"]
order = list(range(n_pool))
random.Random(plan["seed"]).shuffle(order)
idx = [order[u % len(order)] for u in range(plan["max_updates"])]
print("pool", n_pool, "updates", len(idx), "distinct rows used", len(set(idx)), "first 8 indices", idx[:8])

train = read_jsonl(DATA / "visible_G_train.jsonl")[:n_pool]
tr = [parse(r["observation"]) for r in train]
toks_all = [ast_to_tokens(a) for a in tr]

# --- loss trend ---
def mean(x): return sum(x) / len(x)
def sd(x):
    m = mean(x); return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
print("\nloss first/last:", loss[0], loss[-1], " min", min(loss), "at update", loss.index(min(loss)) + 1, " max", max(loss), "at", loss.index(max(loss)) + 1)
for w in range(0, 128, 16):
    seg = loss[w:w + 16]
    print(" updates %3d-%3d loss mean %.6f sd %.6f min %.6f max %.6f" % (w + 1, w + 16, mean(seg), sd(seg), min(seg), max(seg)))
xs = list(range(1, 129))
def slope(xs, ys):
    mx, my = mean(xs), mean(ys)
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
print(" OLS slope all 128:", slope(xs, loss))
print(" OLS slope updates 65-128:", slope(xs[64:], loss[64:]))
print(" OLS slope updates 97-128:", slope(xs[96:], loss[96:]))
print(" updates with loss below 2.0:", [i + 1 for i, v in enumerate(loss) if v < 2.0][:5], "... count", sum(v < 2.0 for v in loss))
print(" first update with loss < 2.5:", next(i + 1 for i, v in enumerate(loss) if v < 2.5))
print("\ngrad norm pre-clip: min %.6f max %.6f mean %.6f; count > clip 1.0: %d; argmax update %d" % (
    min(gn), max(gn), mean(gn), sum(g > 1.0 for g in gn), gn.index(max(gn)) + 1))
for w in range(0, 128, 32):
    seg = gn[w:w + 32]
    print(" updates %3d-%3d gradnorm mean %.6f min %.6f max %.6f  >1.0: %d" % (w + 1, w + 32, mean(seg), min(seg), max(seg), sum(g > 1.0 for g in seg)))

# --- input-blind baselines, estimated from the whole 2,048-row pool ---
V = len(TOKENS)
print("\nvocabulary size", V, " ln(V) =", math.log(V))
uni = collections.Counter(t for s in toks_all for t in s)
tot = sum(uni.values())
slots_all = [slot_sequence(s) for s in toks_all]
by_slot = collections.defaultdict(collections.Counter)
by_slot_depth = collections.defaultdict(collections.Counter)
for s, sl in zip(toks_all, slots_all):
    for t, (k, d) in zip(s, sl):
        by_slot[k][t] += 1
        by_slot_depth[(k, d if k == "expr" else None)][t] += 1
for k, c in by_slot.items():
    n = sum(c.values())
    H = -sum(v / n * math.log(v / n) for v in c.values())
    print(" slot %-8s n=%5d entropy(nats)=%.6f  top: %s" % (k, n, H, [(TOKENS[t], v) for t, v in c.most_common(3)]))
for (k, d), c in sorted(by_slot_depth.items(), key=lambda x: (x[0][0], -1 if x[0][1] is None else x[0][1])):
    if k == "expr":
        n = sum(c.values())
        print(" expr slot at node-depth %s: %s" % (d, [(TOKENS[t], v, round(v / n, 6)) for t, v in c.most_common()]))

def ce(tokens, prob):
    sl = slot_sequence(tokens)
    return mean([-math.log(prob(t, k, d)) for t, (k, d) in zip(tokens, sl)])
B = {
    "B0_uniform34": lambda t, k, d: 1 / V,
    "B1_unigram_no_grammar": lambda t, k, d: uni[t] / tot,
    "B2_grammar_slot_marginal": lambda t, k, d: 1.0 if k == "eos" else by_slot[k][t] / sum(by_slot[k].values()),
    "B3_slot_plus_expr_depth": lambda t, k, d: 1.0 if k == "eos" else (by_slot_depth[(k, d if k == "expr" else None)][t] / sum(by_slot_depth[(k, d if k == "expr" else None)].values())),
}
used = [toks_all[i] for i in idx]
print("\nper-example mean-token cross-entropy on the SAME 128 examples, in update order:")
bl = {name: [ce(s, f) for s in used] for name, f in B.items()}
for name, v in bl.items():
    print(" %-26s all128 mean %.6f | upd 1-16 %.6f | upd 97-128 %.6f | upd 113-128 %.6f" % (
        name, mean(v), mean(v[:16]), mean(v[96:]), mean(v[112:])))
print(" %-26s all128 mean %.6f | upd 1-16 %.6f | upd 97-128 %.6f | upd 113-128 %.6f" % (
    "MODEL_logged_loss", mean(loss), mean(loss[:16]), mean(loss[96:]), mean(loss[112:])))
for name in ("B1_unigram_no_grammar", "B2_grammar_slot_marginal", "B3_slot_plus_expr_depth"):
    diff = [m - b for m, b in zip(loss, bl[name])]
    print(" model minus %s: upd 97-128 mean %.6f, #updates(97-128) where model < baseline: %d/32; all128 model<baseline: %d/128" % (
        name, mean(diff[96:]), sum(d < 0 for d in diff[96:]), sum(d < 0 for d in diff)))

def pearson(a, b):
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
lens = [len(s) for s in used]
print("\nPearson(model loss, B3 CE) upd 65-128: %.6f ; upd 97-128: %.6f" % (pearson(loss[64:], bl["B3_slot_plus_expr_depth"][64:]), pearson(loss[96:], bl["B3_slot_plus_expr_depth"][96:])))
print("Pearson(model loss, B1 CE) upd 65-128: %.6f" % pearson(loss[64:], bl["B1_unigram_no_grammar"][64:]))
print("Pearson(model loss, target length) upd 65-128: %.6f" % pearson(loss[64:], lens[64:]))
# sanity: B3 per-example spread
print("B3 CE range on used examples: min %.6f max %.6f" % (min(bl["B3_slot_plus_expr_depth"]), max(bl["B3_slot_plus_expr_depth"])))

# --- what the 128 examples contained ---
print("\n128 used examples: depth", dict(sorted(collections.Counter(depth(tr[i]) for i in idx).items())),
      " token lengths", dict(sorted(collections.Counter(len(toks_all[i]) for i in idx).items())))
print(" supervised target tokens total:", sum(lens), " mean per example:", mean(lens))
UL = [l for i in idx for l in leaves(tr[i])]
print(" leaves seen:", len(UL), " distinct noetic^domain states seen:", len({l['operator'] + l['domain'] for l in UL}), "of 40")
sc = collections.Counter(l["operator"] + "^" + l["domain"] for l in UL)
print(" min/max count per state:", min(sc.values()), max(sc.values()), " ^7^E:", sc["^7^E"], " ^7^C:", sc["^7^C"])
print(" distinct full leaf literals seen:", len({canon(l) for l in UL}), " of 1600 possible (10x4x8x5)")
print(" noetic counts in used leaves:", sorted(collections.Counter(l["operator"] for l in UL).items()))
print(" depth-3 examples among used:", sum(depth(tr[i]) == 3 for i in idx))
# recency: last 16 / 8 updates
for k in (8, 16, 32):
    last = [l for i in idx[-k:] for l in leaves(tr[i])]
    print(" last %d updates: leaves %d, noetic top3 %s, domain %s, ^7^E %d, ^7^C %d, root ops %s, depth %s" % (
        k, len(last), collections.Counter(l["operator"] for l in last).most_common(3),
        collections.Counter(l["domain"] for l in last).most_common(),
        sum(1 for l in last if (l["operator"], l["domain"]) == ("^7", "E")),
        sum(1 for l in last if (l["operator"], l["domain"]) == ("^7", "C")),
        collections.Counter(tr[i]["op"] for i in idx[-k:]).most_common(),
        dict(sorted(collections.Counter(depth(tr[i]) for i in idx[-k:]).items()))))
print(" last 4 updates' observations:")
for u in range(124, 128):
    print("  update", u + 1, "row", idx[u], train[idx[u]]["record_id"], train[idx[u]]["observation"], "loss", loss[u])
json.dump({"idx": idx, "record_ids": [train[i]["record_id"] for i in idx]}, open("used_rows.json", "w"))
