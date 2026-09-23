import sys, torch
if not torch.cuda.is_available(): print('GPU_REQUIRED'); sys.exit(2)
"""RT1 forward-only diagnostic of the saved Q4 checkpoint. Inference only, no training, no optimizer.
Reads: checkpoint (read-only), visible_G_train/dev via q3_load.load_visible, run_001 records, R5 scratch helpers.
Never opens sealed_* or eval files. Writes ONLY into SCRATCH/RT1. Every number: DIAGNOSTIC_NOT_CLAIM_BEARING.
Pre-run record: SCRATCH/RT1/PREREG_RT1.txt (sha256 856013c2392a033184577f1393835326c92c0ef6eb80e70797e70991af26787a)."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import collections
import json
import math
import random
from pathlib import Path

ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
SCRATCH = Path("C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review")
OUT = SCRATCH / "RT1"
RUN = ROOT / "records/q4_authorized_20260922/run_001"
REC = ROOT / "records/q4_authorized_20260922"
DATA = LAB / "data/q3_v0_7"
WEIGHTS_SHA = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(SCRATCH / "R5"))

from common import parse, depth, canon, slot_sequence, read_jsonl  # R5 helpers (pure Python)
from learner_q4_decoder import TOKENS, TOKEN_IDS, ast_to_tokens, tokens_to_ast, allowed_next, free_decode
from learner_q4_representation import from_visible_record, Bottleneck
from q3_load import load_visible
from q4_checkpoint import load_checkpoint

torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
DEV = "cuda:0"
R = {"label": "DIAGNOSTIC_NOT_CLAIM_BEARING"}


def say(*a):
    print(*a, flush=True)


manifest = json.loads((RUN / "checkpoint/manifest.json").read_text(encoding="utf-8"))
model = load_checkpoint(RUN / "checkpoint", expected_identity=manifest["identity"],
                        expected_weights_sha256=WEIGHTS_SHA, width=64, device=DEV)
say("model device:", model._device(), "| params:", sum(p.numel() for p in model.parameters()),
    "| torch", torch.__version__, "| cuda", torch.version.cuda, "|", torch.cuda.get_device_name(0))

train_vis = load_visible(DATA, "G", "train")[:2048]
dev_vis = load_visible(DATA, "G", "dev")[:16]
saved = read_jsonl(RUN / "dev_predictions.jsonl")
insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
assert [r["record_id"] for r in dev_vis] == [s["record_id"] for s in saved] == [c["record_id"] for c in insp]

# ---------------- step 0: sanity re-decode ----------------
say("\n== STEP 0: re-decode the 16 dev inputs and compare with run_001/dev_predictions.jsonl")
dev_in = [from_visible_record(r) for r in dev_vis]
dev_vec = [model.encode(x) for x in dev_in]
step0 = []
for row, s, vec in zip(dev_vis, saved, dev_vec):
    p = free_decode(vec, model.next_logits)
    step0.append({"record_id": row["record_id"], "outcome_eq": p.outcome == s["outcome"], "ast_eq": p.ast == s["ast"],
                  "steps_eq": p.steps == s["steps"], "outcome": p.outcome, "steps": p.steps})
n0 = sum(r["outcome_eq"] and r["ast_eq"] and r["steps_eq"] for r in step0)
say("step0 exact reproductions (outcome, ast, steps all equal): %d/16" % n0)
R["step0"] = {"reproduced": n0, "of": 16, "rows": step0}
if n0 != 16:
    say("RULE (a) FIRES: BUG in checkpoint save/load or decoding. Stopping as the rule requires.")
    (OUT / "rt1_results.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
    sys.exit(0)

# ---------------- rows ----------------
order = list(range(2048))
random.Random(20260921).shuffle(order)
seen_idx, unseen_idx = order[:128], order[128:256]
r5_used = json.loads((SCRATCH / "R5/used_rows.json").read_text(encoding="utf-8"))["idx"]
say("\nseen idx == SCRATCH/R5/used_rows.json idx:", seen_idx == r5_used, "| overlap seen/unseen:", len(set(seen_idx) & set(unseen_idx)))
tr_ast = [parse(r["observation"]) for r in train_vis]
roundtrip = sum(tokens_to_ast(ast_to_tokens(a)) == a for a in tr_ast)
say("parser round-trip tokens_to_ast(ast_to_tokens(parse(obs))) == parse(obs) on 2048 train rows: %d/2048" % roundtrip)
say("train depth counts (parser):", dict(sorted(collections.Counter(depth(a) for a in tr_ast).items())))
dev_tgt = [c["checker_reference_ast"] for c in insp]
say("parser(dev observation) == checker_reference_ast: %d/16" % sum(parse(r["observation"]) == t for r, t in zip(dev_vis, dev_tgt)))

# ---------------- step 1: spread ----------------
say("\n== STEP 1: bottleneck spread")
seen_in = [from_visible_record(train_vis[i]) for i in seen_idx]
unseen_in = [from_visible_record(train_vis[i]) for i in unseen_idx]
seen_vec = [model.encode(x) for x in seen_in]
unseen_vec = [model.encode(x) for x in unseen_in]


def spread(vecs):
    X = torch.tensor([v.values for v in vecs], dtype=torch.float64, device=DEV)
    D = ((X[:, None, :] - X[None, :, :]) ** 2).sum(-1).sqrt()
    n = X.shape[0]
    iu = torch.triu_indices(n, n, offset=1, device=DEV)
    pair = D[iu[0], iu[1]]
    norms = X.norm(dim=1)
    Xn = X / norms[:, None]
    cos = (Xn @ Xn.T)[iu[0], iu[1]]
    return {"n": n, "mean_pairwise_L2": pair.mean().item(), "mean_norm": norms.mean().item(),
            "relative_spread": (pair.mean() / norms.mean()).item(), "min_pairwise_L2": pair.min().item(),
            "max_pairwise_L2": pair.max().item(), "mean_pairwise_cosine": cos.mean().item(),
            "min_pairwise_cosine": cos.min().item(), "mean_per_dim_std": X.std(dim=0).mean().item(),
            "mean_abs_value": X.abs().mean().item(), "max_abs_value": X.abs().max().item()}


S1 = {"dev16": spread(dev_vec), "seen128": spread(seen_vec), "unseen128": spread(unseen_vec),
      "all272": spread(dev_vec + seen_vec + unseen_vec)}
for k, v in S1.items():
    say(" %-9s %s" % (k, json.dumps(v)))
R["step1"] = S1

# ---------------- step 2: decoder use of the bottleneck ----------------
say("\n== STEP 2: next_logits with TRUE / ZERO / SWAP bottleneck (swap partner = dev (i+1) mod 16)")
T = TOKEN_IDS
ZERO = Bottleneck(tuple(0.0 for _ in range(64)))
P0, P1, P2 = (), (T["BINARY"],), (T["BINARY"], T["PLUS"])


def gaps(b):
    out = {}
    for pname, pref in (("P0_empty", P0), ("P1_BINARY", P1), ("P2_BINARY_PLUS", P2)):
        L = model.next_logits(b, pref)
        out[pname] = {"TIMES_minus_PLUS": L[T["TIMES"]] - L[T["PLUS"]], "BINARY_minus_STATE": L[T["BINARY"]] - L[T["STATE"]]}
    return out


step2 = []
for i in range(16):
    variants = {"TRUE": dev_vec[i], "ZERO": ZERO, "SWAP": dev_vec[(i + 1) % 16]}
    g = {k: gaps(b) for k, b in variants.items()}
    dec = {k: free_decode(b, model.next_logits) for k, b in variants.items()}
    step2.append({"record_id": dev_vis[i]["record_id"], "gaps": g,
                  "decode_tokens": {k: [TOKENS[t] for t in d.tokens] for k, d in dec.items()},
                  "decode_changed": {k: dec[k].tokens != dec["TRUE"].tokens for k in ("ZERO", "SWAP")}})
# the two pre-declared rule gaps: G1 at P1, G2 at P2
changes = []
for r in step2:
    for v in ("ZERO", "SWAP"):
        for pname, gname in (("P1_BINARY", "TIMES_minus_PLUS"), ("P2_BINARY_PLUS", "BINARY_minus_STATE")):
            changes.append({"record_id": r["record_id"], "variant": v, "gap": pname + ":" + gname,
                            "true": r["gaps"]["TRUE"][pname][gname], "variant_value": r["gaps"][v][pname][gname],
                            "change": r["gaps"][v][pname][gname] - r["gaps"]["TRUE"][pname][gname]})
absch = [abs(c["change"]) for c in changes]
n_zero = sum(r["decode_changed"]["ZERO"] for r in step2)
n_swap = sum(r["decode_changed"]["SWAP"] for r in step2)
n_either = sum(r["decode_changed"]["ZERO"] or r["decode_changed"]["SWAP"] for r in step2)
say(" per input: G1 = logit[TIMES]-logit[PLUS] after (BINARY,) ; G2 = logit[BINARY]-logit[STATE] after (BINARY,PLUS)")
for r in step2:
    g = r["gaps"]
    say("  %s G1 true %+.6f zero %+.6f swap %+.6f | G2 true %+.6f zero %+.6f swap %+.6f | root(B-S) true %+.6f zero %+.6f swap %+.6f | changed zero=%s swap=%s" % (
        r["record_id"], g["TRUE"]["P1_BINARY"]["TIMES_minus_PLUS"], g["ZERO"]["P1_BINARY"]["TIMES_minus_PLUS"], g["SWAP"]["P1_BINARY"]["TIMES_minus_PLUS"],
        g["TRUE"]["P2_BINARY_PLUS"]["BINARY_minus_STATE"], g["ZERO"]["P2_BINARY_PLUS"]["BINARY_minus_STATE"], g["SWAP"]["P2_BINARY_PLUS"]["BINARY_minus_STATE"],
        g["TRUE"]["P0_empty"]["BINARY_minus_STATE"], g["ZERO"]["P0_empty"]["BINARY_minus_STATE"], g["SWAP"]["P0_empty"]["BINARY_minus_STATE"],
        r["decode_changed"]["ZERO"], r["decode_changed"]["SWAP"]))
for v in ("ZERO", "SWAP"):
    for gname in ("P1_BINARY:TIMES_minus_PLUS", "P2_BINARY_PLUS:BINARY_minus_STATE"):
        sel = [c["change"] for c in changes if c["variant"] == v and c["gap"] == gname]
        say("  %s %s: mean change %+.6f, mean |change| %.6f, max |change| %.6f" % (v, gname, sum(sel) / len(sel), sum(map(abs, sel)) / len(sel), max(map(abs, sel))))
say(" max |gap change| over 64 rule values: %.6f ; count |change| >= 0.1: %d ; >= 0.5: %d" % (max(absch), sum(a >= 0.1 for a in absch), sum(a >= 0.5 for a in absch)))
say(" greedy decode changed: ZERO %d/16, SWAP %d/16, EITHER %d/16" % (n_zero, n_swap, n_either))
true_g1 = [r["gaps"]["TRUE"]["P1_BINARY"]["TIMES_minus_PLUS"] for r in step2]
true_g2 = [r["gaps"]["TRUE"]["P2_BINARY_PLUS"]["BINARY_minus_STATE"] for r in step2]
say(" EXTRA: TRUE G1 across 16 inputs min %+.6f max %+.6f range %.6f ; TRUE G2 min %+.6f max %+.6f range %.6f" % (
    min(true_g1), max(true_g1), max(true_g1) - min(true_g1), min(true_g2), max(true_g2), max(true_g2) - min(true_g2)))
say(" distinct TRUE decodes over 16:", len({tuple(r["decode_tokens"]["TRUE"]) for r in step2}),
    "| ZERO decode:", " ".join(step2[0]["decode_tokens"]["ZERO"]))
R["step2"] = {"rows": step2, "rule_changes": changes, "max_abs_change": max(absch),
              "count_abs_change_ge_0_1": sum(a >= 0.1 for a in absch), "count_abs_change_ge_0_5": sum(a >= 0.5 for a in absch),
              "decode_changed_zero": n_zero, "decode_changed_swap": n_swap, "decode_changed_either": n_either}

# ---------------- step 3: free decode on train rows ----------------
say("\n== STEP 3: free decode on 128 seen and 128 unseen train rows")


def decode_set(vecs, asts):
    by = {}
    outs = collections.Counter()
    for v, t in zip(vecs, asts):
        p = free_decode(v, model.next_logits)
        key = str(depth(t))
        s = by.setdefault(key, {"n": 0, "generated": 0, "canonical_exact": 0})
        s["n"] += 1
        s["generated"] += p.outcome == "GENERATED"
        s["canonical_exact"] += p.ast == t
        outs[canon(p.ast) if p.ast is not None else "OUTCOME:" + p.outcome] += 1
    return {"by_depth": dict(sorted(by.items())), "distinct_outputs": len(outs), "outputs": outs.most_common()}


seen_ast = [tr_ast[i] for i in seen_idx]
unseen_ast = [tr_ast[i] for i in unseen_idx]
S3 = {"seen128": decode_set(seen_vec, seen_ast), "unseen128": decode_set(unseen_vec, unseen_ast)}
all_out = collections.Counter()
for k in S3:
    for o, c in S3[k]["outputs"]:
        all_out[o] += c
S3["distinct_outputs_seen_plus_unseen"] = len(all_out)
for k in ("seen128", "unseen128"):
    say(" %s by depth %s | distinct outputs %d" % (k, json.dumps(S3[k]["by_depth"]), S3[k]["distinct_outputs"]))
    for o, c in S3[k]["outputs"]:
        say("   %4d x %s" % (c, o))
say(" distinct outputs over all 256 train rows:", len(all_out))
R["step3"] = S3

# ---------------- step 4: teacher-forced CE ----------------
say("\n== STEP 4: teacher-forced cross-entropy")
F = torch.nn.functional


def gru_ce(inputs, asts):
    per_row, tok_sum, tok_n, per_slot = [], 0.0, 0, collections.defaultdict(lambda: [0.0, 0])
    for x, t in zip(inputs, asts):
        tgt = ast_to_tokens(t)
        with torch.no_grad():
            logits = model.teacher_forced_logits(x, tgt[:-1])
            gold = torch.tensor(tgt, dtype=torch.long, device=model._device())
            ce_tok = F.cross_entropy(logits, gold, reduction="none")
            ce = F.cross_entropy(logits, gold)
        per_row.append(ce.item())
        tok_sum += ce_tok.sum().item()
        tok_n += len(tgt)
        for c, (k, d) in zip(ce_tok.tolist(), slot_sequence(tgt)):
            per_slot[k][0] += c
            per_slot[k][1] += 1
    model.eval()
    return per_row, tok_sum / tok_n, {k: v[0] / v[1] for k, v in per_slot.items()}


V = len(TOKENS)
seen_tok = [ast_to_tokens(a) for a in seen_ast]  # update order
# IB1: online bigram k=1 alpha=0.1, no grammar (R5 s5_meeting.py preq)
ALPHA = 0.1
C1 = collections.defaultdict(collections.Counter)
ib1_preq = []
for s in seen_tok:
    full = (V,) + tuple(s)
    tot = 0.0
    for i in range(1, len(full)):
        c = C1[full[i - 1:i]]
        tot += -math.log((c[full[i]] + ALPHA) / (sum(c.values()) + ALPHA * V))
    ib1_preq.append(tot / (len(full) - 1))
    for i in range(1, len(full)):
        C1[full[i - 1:i]][full[i]] += 1


def ib1_row(s):
    full = (V,) + tuple(s)
    vals = []
    for i in range(1, len(full)):
        c = C1[full[i - 1:i]]
        vals.append(-math.log((c[full[i]] + ALPHA) / (sum(c.values()) + ALPHA * V)))
    return vals


# IB2: loss-weighted slot+depth prior (R5 s7_greedy_lw.py fit(None)); IB3 EXTRA: unweighted
def slot_fit(weighted):
    C = collections.defaultdict(collections.Counter)
    for s in seen_tok:
        w = 1.0 / len(s) if weighted else 1.0
        for t, (k, d) in zip(s, slot_sequence(s)):
            C[(k, d if k == "expr" else None)][t] += w
    return C


C2, C3 = slot_fit(True), slot_fit(False)
SMOOTH = 0.01


def slot_row(C, s):
    vals, zeros = [], 0
    for i, (t, (k, d)) in enumerate(zip(s, slot_sequence(s))):
        if k == "eos":
            vals.append(0.0)
            continue
        legal = allowed_next(tuple(s[:i]))
        c = C[(k, d if k == "expr" else None)]
        zeros += c[t] == 0
        vals.append(-math.log((c[t] + SMOOTH) / (sum(c[u] for u in legal) + SMOOTH * len(legal))))
    return vals, zeros


def summarize(rows_vals, slots_list):
    per_row = [sum(v) / len(v) for v in rows_vals]
    flat = [x for v in rows_vals for x in v]
    ps = collections.defaultdict(list)
    for v, sl in zip(rows_vals, slots_list):
        for x, (k, d) in zip(v, sl):
            ps[k].append(x)
    return per_row, sum(flat) / len(flat), {k: sum(x) / len(x) for k, x in ps.items()}


def mean(x):
    return sum(x) / len(x)


sets = {"seen128": (seen_in, seen_ast), "unseen128": (unseen_in, unseen_ast), "dev16": (dev_in, dev_tgt)}
S4 = {}
for name, (xs, asts) in sets.items():
    toks = [ast_to_tokens(a) for a in asts]
    slots = [slot_sequence(s) for s in toks]
    g_rows, g_tok, g_slot = gru_ce(xs, asts)
    b1 = summarize([ib1_row(s) for s in toks], slots)
    r2 = [slot_row(C2, s) for s in toks]
    b2 = summarize([v for v, _ in r2], slots)
    r3 = [slot_row(C3, s) for s in toks]
    b3 = summarize([v for v, _ in r3], slots)
    S4[name] = {"GRU": {"row_mean": mean(g_rows), "token_mean": g_tok, "per_slot": g_slot},
                "IB1_bigram_final": {"row_mean": mean(b1[0]), "token_mean": b1[1], "per_slot": b1[2]},
                "IB2_lossweighted_slot": {"row_mean": mean(b2[0]), "token_mean": b2[1], "per_slot": b2[2],
                                          "unsmoothed_zero_count_tokens": sum(z for _, z in r2)},
                "IB3_EXTRA_unweighted_slot": {"row_mean": mean(b3[0]), "token_mean": b3[1], "per_slot": b3[2],
                                              "unsmoothed_zero_count_tokens": sum(z for _, z in r3)},
                "GRU_rows_below_IB1": sum(a < b for a, b in zip(g_rows, b1[0])),
                "GRU_rows_below_IB2": sum(a < b for a, b in zip(g_rows, b2[0])), "n": len(g_rows)}
    if name == "seen128":
        upd = read_jsonl(RUN / "updates.jsonl")
        S4[name]["GRU_logged_online_loss_row_mean"] = mean([u["loss"] for u in upd])
        S4[name]["IB1_prequential_row_mean"] = mean(ib1_preq)
        S4[name]["GRU_final_minus_logged_per_row_mean"] = mean([a - u["loss"] for a, u in zip(g_rows, upd)])
    say(" %s: GRU row-mean %.6f token-mean %.6f | IB1 bigram %.6f / %.6f | IB2 lw-slot %.6f / %.6f (zero-count tokens %d) | IB3 slot %.6f / %.6f | GRU rows below IB1 %d/%d, below IB2 %d/%d" % (
        name, S4[name]["GRU"]["row_mean"], g_tok, S4[name]["IB1_bigram_final"]["row_mean"], b1[1],
        S4[name]["IB2_lossweighted_slot"]["row_mean"], b2[1], S4[name]["IB2_lossweighted_slot"]["unsmoothed_zero_count_tokens"],
        S4[name]["IB3_EXTRA_unweighted_slot"]["row_mean"], b3[1],
        S4[name]["GRU_rows_below_IB1"], len(g_rows), S4[name]["GRU_rows_below_IB2"], len(g_rows)))
    for model_name in ("GRU", "IB1_bigram_final", "IB2_lossweighted_slot"):
        say("    per-slot token CE %-22s %s" % (model_name, json.dumps({k: round(v, 6) for k, v in sorted(S4[name][model_name]["per_slot"].items())})))
if "seen128" in S4:
    say(" seen128 extra: GRU logged online loss mean %.6f | IB1 prequential mean %.6f | GRU final-minus-logged per-row mean %+.6f" % (
        S4["seen128"]["GRU_logged_online_loss_row_mean"], S4["seen128"]["IB1_prequential_row_mean"], S4["seen128"]["GRU_final_minus_logged_per_row_mean"]))
R["step4"] = S4

# ---------------- EXTRA: teacher-forced CE with true / zero / swapped bottleneck ----------------
say("\n== EXTRA: teacher-forced CE with TRUE / ZERO / SWAP bottleneck (swap partner (i+1) mod n within the set)")


def tf_with(vec_values, tgt):
    h = torch.tensor([[list(vec_values)]], dtype=torch.float32, device=model._device())
    with torch.no_grad():
        values, _ = model.decoder(model.output_embedding(model._prefix_tensor(tuple(tgt[:-1]))), h)
        logits = model.output_head(values[0])
        return F.cross_entropy(logits, torch.tensor(tgt, dtype=torch.long, device=model._device())).item()


EX = {}
for name, vecs, asts in (("seen128", seen_vec, seen_ast), ("unseen128", unseen_vec, unseen_ast), ("dev16", dev_vec, dev_tgt)):
    toks = [ast_to_tokens(a) for a in asts]
    n = len(vecs)
    tr_ = [tf_with(vecs[i].values, toks[i]) for i in range(n)]
    ze = [tf_with(ZERO.values, toks[i]) for i in range(n)]
    sw = [tf_with(vecs[(i + 1) % n].values, toks[i]) for i in range(n)]
    EX[name] = {"TRUE": mean(tr_), "ZERO": mean(ze), "SWAP": mean(sw), "rows_true_below_swap": sum(a < b for a, b in zip(tr_, sw)),
                "rows_true_below_zero": sum(a < b for a, b in zip(tr_, ze)), "n": n}
    say(" %s: TRUE %.6f | ZERO %.6f | SWAP %.6f | rows TRUE<SWAP %d/%d, TRUE<ZERO %d/%d" % (
        name, EX[name]["TRUE"], EX[name]["ZERO"], EX[name]["SWAP"], EX[name]["rows_true_below_swap"], n, EX[name]["rows_true_below_zero"], n))
model.eval()
R["extra_tf_bottleneck_swap"] = EX

# ---------------- deterministic rule reading (per PREREG_RT1.txt) ----------------
say("\n== RULE READING (per PREREG_RT1.txt)")
rules = {}
rules["a_bug"] = n0 != 16
rules["b_encoder_collapse"] = S1["dev16"]["relative_spread"] < 0.05 and S1["seen128"]["relative_spread"] < 0.05
spread_ok = S1["dev16"]["relative_spread"] >= 0.05 and S1["seen128"]["relative_spread"] >= 0.05
rules["c_decoder_ignores"] = spread_ok and n_either == 0 and max(absch) < 0.1
rules["d_input_used_weakly"] = n_either >= 2 or max(absch) >= 0.5
seen_exact = sum(v["canonical_exact"] for v in S3["seen128"]["by_depth"].values())
unseen_exact = sum(v["canonical_exact"] for v in S3["unseen128"]["by_depth"].values())
rules["e_pipeline_maps"] = seen_exact >= 1
ce_primary = all(S4[k]["GRU"]["row_mean"] >= min(S4[k]["IB1_bigram_final"]["row_mean"], S4[k]["IB2_lossweighted_slot"]["row_mean"]) for k in ("seen128", "unseen128"))
ce_strict = all(S4[k]["GRU"]["row_mean"] >= max(S4[k]["IB1_bigram_final"]["row_mean"], S4[k]["IB2_lossweighted_slot"]["row_mean"]) for k in ("seen128", "unseen128"))
distinct_ok = 1 <= S3["distinct_outputs_seen_plus_unseen"] <= 2
rules["f_too_little_training_primary"] = seen_exact == 0 and unseen_exact == 0 and distinct_ok and ce_primary
rules["f_too_little_training_strict"] = seen_exact == 0 and unseen_exact == 0 and distinct_ok and ce_strict
rules["inputs"] = {"step0_reproduced": n0, "spread_dev16": S1["dev16"]["relative_spread"], "spread_seen128": S1["seen128"]["relative_spread"],
                   "decode_changed_either": n_either, "max_abs_gap_change": max(absch), "seen_exact": seen_exact, "unseen_exact": unseen_exact,
                   "distinct_outputs_256": S3["distinct_outputs_seen_plus_unseen"], "ce_condition_primary": ce_primary, "ce_condition_strict": ce_strict}
for k, v in rules.items():
    say(" %s: %s" % (k, v))
R["rules"] = rules
say("\ncuda peak allocated bytes:", torch.cuda.max_memory_allocated(0))
(OUT / "rt1_results.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
say("wrote", OUT / "rt1_results.json")
