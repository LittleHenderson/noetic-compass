import sys, torch
if not torch.cuda.is_available(): print('GPU_REQUIRED'); sys.exit(2)
"""RT2: ONE bounded diagnostic re-training of the Q4 StrictR1 (width 64), held in memory only.
Same code path as q4_smoke_job.py:320-355 (lab modules imported read-only); only the row schedule differs:
update u trains row S[(u-1) % 256], S = first 256 rows of random.Random(20260921).shuffle(list(range(2048))).
Caps: 2,000 updates or 300 s wall since just before update 1 (including in-run evaluations), whichever first.
Targets: R5 parser on VISIBLE observations. Sealed and eval files are never opened. Writes ONLY into SCRATCH/RT2.
Pre-run record: SCRATCH/RT2/PREREG_RT2.txt (sha256 a1f457d6e2925f04aed8cf9f5dcc71453c582252f8594d7def3e4a1cc026a430).
Every number: DIAGNOSTIC_NOT_CLAIM_BEARING."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import collections
import json
import math
import random
import time
from pathlib import Path

T_PROC0 = time.monotonic()
ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
SCRATCH = Path("C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review")
OUT = SCRATCH / "RT2"
RUN = ROOT / "records/q4_authorized_20260922/run_001"
REC = ROOT / "records/q4_authorized_20260922"
DATA = LAB / "data/q3_v0_7"
WEIGHTS_SHA = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
SEED, WIDTH, LR, CLIP = 20260921, 64, 0.001, 1.0
MAX_UPDATES, MAX_WALL, PROC_GUARD = 2000, 300.0, 285.0
EVAL_AT = (500, 1000)
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(SCRATCH / "R5"))

from common import parse, depth, canon, shape, leaves, slot_sequence, read_jsonl  # R5 helpers (pure Python)
from learner_q4_decoder import TOKENS, ast_to_tokens, allowed_next, free_decode
from learner_q4_representation import from_visible_record
from learner_q4_neural import NeuralConfig, build_model
from q3_load import load_visible
from q4_checkpoint import load_checkpoint

F = torch.nn.functional
DEV = "cuda:0"
R = {"label": "DIAGNOSTIC_NOT_CLAIM_BEARING", "prereg_sha256": "a1f457d6e2925f04aed8cf9f5dcc71453c582252f8594d7def3e4a1cc026a430"}


def say(*a):
    print(*a, flush=True)


# ---------------- data (visible files only) ----------------
train_vis = load_visible(DATA, "G", "train")[:2048]
dev_vis = load_visible(DATA, "G", "dev")
assert len(train_vis) == 2048 and len(dev_vis) == 256
tr_ast = [parse(r["observation"]) for r in train_vis]
tr_tok = [ast_to_tokens(a) for a in tr_ast]
tr_in = [from_visible_record(r) for r in train_vis]
dev_ast = [parse(r["observation"]) for r in dev_vis]
dev_in = [from_visible_record(r) for r in dev_vis]
insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
assert [c["record_id"] for c in insp] == [r["record_id"] for r in dev_vis[:16]]
dev16_ref_ok = sum(c["checker_reference_ast"] == a for c, a in zip(insp, dev_ast[:16]))

order = list(range(2048))
random.Random(SEED).shuffle(order)
S = order[:256]
shp = lambda a: json.dumps(shape(a))
S_shapes = {shp(tr_ast[i]) for i in S}
train_shapes = {shp(a) for a in tr_ast}
set2 = [i for i in order[256:] if shp(tr_ast[i]) in S_shapes][:128]
assert len(set2) == 128 and not set(set2) & set(S)
say("S: %d rows, %d bare shapes (train pool has %d) | set(ii): %d rows, first/last position in order[256:]: %d/%d" % (
    len(S), len(S_shapes), len(train_shapes), len(set2), order[256:].index(set2[0]), order[256:].index(set2[-1])))
say("depth counts S:", dict(sorted(collections.Counter(depth(tr_ast[i]) for i in S).items())),
    "| set(ii):", dict(sorted(collections.Counter(depth(tr_ast[i]) for i in set2).items())),
    "| dev256:", dict(sorted(collections.Counter(depth(a) for a in dev_ast).items())))
say("dev256 bare shapes: %d, shared with train pool: %d | parser(dev obs) == checker_reference_ast rows 1-16: %d/16" % (
    len({shp(a) for a in dev_ast}), len({shp(a) for a in dev_ast} & train_shapes), dev16_ref_ok))
R["sets"] = {"S_idx": S, "set2_idx": set2, "S_shapes": len(S_shapes), "train_shapes": len(train_shapes),
             "dev16_parser_matches_reference": dev16_ref_ok}

# ---------------- saved checkpoint (read-only), loaded BEFORE seeding so its init does not touch the seeded RNG ----------------
manifest = json.loads((RUN / "checkpoint/manifest.json").read_text(encoding="utf-8"))
ck = load_checkpoint(RUN / "checkpoint", expected_identity=manifest["identity"], expected_weights_sha256=WEIGHTS_SHA, width=WIDTH, device=DEV)
ck_state = {k: v.detach().clone() for k, v in ck.state_dict().items()}
del ck
smoke_updates = read_jsonl(RUN / "updates.jsonl")

# ---------------- training setup: q4_smoke_job.py:327-335 ----------------
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
model = build_model(NeuralConfig(WIDTH), device=DEV)
optimizer = torch.optim.AdamW(model.parameters(), lr=LR)
say("model params:", sum(p.numel() for p in model.parameters()), "| torch", torch.__version__, "| cuda", torch.version.cuda,
    "|", torch.cuda.get_device_name(0))

# ---------------- input-blind learners fed the same row stream ----------------
V = len(TOKENS)
ALPHA, SMOOTH = 0.1, 0.01
IB1 = collections.defaultdict(collections.Counter)   # online bigram, no grammar
IB2 = collections.defaultdict(collections.Counter)   # loss-weighted slot prior


def ib_feed(C1, C2, s):
    full = (V,) + tuple(s)
    for i in range(1, len(full)):
        C1[full[i - 1:i]][full[i]] += 1
    w = 1.0 / len(s)
    for t, (k, d) in zip(s, slot_sequence(s)):
        C2[(k, d if k == "expr" else None)][t] += w


def ib1_row(C1, s):
    full = (V,) + tuple(s)
    v = []
    for i in range(1, len(full)):
        c = C1[full[i - 1:i]]
        v.append(-math.log((c[full[i]] + ALPHA) / (sum(c.values()) + ALPHA * V)))
    return sum(v) / len(v)


def ib2_row(C2, s):
    v = []
    for i, (t, (k, d)) in enumerate(zip(s, slot_sequence(s))):
        if k == "eos":
            v.append(0.0)
            continue
        legal = allowed_next(tuple(s[:i]))
        c = C2[(k, d if k == "expr" else None)]
        v.append(-math.log((c[t] + SMOOTH) / (sum(c[u] for u in legal) + SMOOTH * len(legal))))
    return sum(v) / len(v)


# EXTRA: one pass over S
IB1_one, IB2_one = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
for i in S:
    ib_feed(IB1_one, IB2_one, tr_tok[i])


def mean(x):
    return sum(x) / len(x) if x else float("nan")


# ---------------- evaluation ----------------
SETS = {"S": ([tr_in[i] for i in S], [tr_ast[i] for i in S]),
        "set2": ([tr_in[i] for i in set2], [tr_ast[i] for i in set2]),
        "dev256": (dev_in, dev_ast)}


def spread(vals):
    X = torch.tensor(vals, dtype=torch.float64, device=DEV)
    n = X.shape[0]
    iu = torch.triu_indices(n, n, offset=1, device=DEV)
    D = ((X[:, None, :] - X[None, :, :]) ** 2).sum(-1).sqrt()[iu[0], iu[1]]
    return (D.mean() / X.norm(dim=1).mean()).item()


def score(preds, asts):
    by, outs, pdepth = {}, collections.Counter(), collections.Counter()
    shape_eq = leaf_eq = in_train_shape = 0
    for p, t in zip(preds, asts):
        s = by.setdefault(str(depth(t)), {"n": 0, "generated": 0, "canonical_exact": 0})
        s["n"] += 1
        s["generated"] += p["outcome"] == "GENERATED"
        s["canonical_exact"] += p["ast"] == t
        outs[canon(p["ast"]) if p["ast"] is not None else "OUTCOME:" + p["outcome"]] += 1
        if p["ast"] is not None:
            pdepth[depth(p["ast"])] += 1
            shape_eq += shape(p["ast"]) == shape(t)
            leaf_eq += leaves(p["ast"]) == leaves(t)
            in_train_shape += shp(p["ast"]) in train_shapes
        else:
            pdepth["none"] += 1
    return {"by_depth": dict(sorted(by.items())), "exact": sum(v["canonical_exact"] for v in by.values()), "n": len(asts),
            "distinct_outputs": len(outs), "top_outputs": outs.most_common(3),
            "EXTRA_pred_depth_hist": {str(k): v for k, v in sorted(pdepth.items(), key=lambda kv: str(kv[0]))},
            "EXTRA_shape_equal": shape_eq, "EXTRA_leaf_sequence_equal": leaf_eq, "EXTRA_pred_shape_is_a_train_shape": in_train_shape}


def evaluate(tag, updates_done):
    t0 = time.monotonic()
    ev = {"updates_done": updates_done, "complete": True}
    for name, (xs, asts) in SETS.items():
        preds, vecs = [], []
        for x in xs:
            if time.monotonic() - T_PROC0 > PROC_GUARD:
                ev["complete"] = False
                break
            v = model.encode(x)
            vecs.append(v.values)
            p = free_decode(v, model.next_logits)
            preds.append({"outcome": p.outcome, "ast": p.ast, "steps": p.steps})
        sc = score(preds, asts[:len(preds)])
        # teacher-forced CE, same formula as q4_smoke_job.py:344-346
        g = []
        with torch.no_grad():
            for x, a in zip(xs, asts):
                tgt = ast_to_tokens(a)
                logits = model.teacher_forced_logits(x, tgt[:-1])
                g.append(F.cross_entropy(logits, torch.tensor(tgt, dtype=torch.long, device=DEV)).item())
        toks = [ast_to_tokens(a) for a in asts]
        b1 = [ib1_row(IB1, s) for s in toks]
        b2 = [ib2_row(IB2, s) for s in toks]
        b1o = [ib1_row(IB1_one, s) for s in toks]
        b2o = [ib2_row(IB2_one, s) for s in toks]
        sc["CE"] = {"GRU": mean(g), "IB1_online_bigram_same_stream": mean(b1), "IB2_lossweighted_slot_same_stream": mean(b2),
                    "EXTRA_IB1_one_pass_S": mean(b1o), "EXTRA_IB2_one_pass_S": mean(b2o),
                    "GRU_rows_below_IB1": sum(a < b for a, b in zip(g, b1)), "GRU_rows_below_IB2": sum(a < b for a, b in zip(g, b2))}
        sc["EXTRA_bottleneck_relative_spread"] = spread(vecs) if len(vecs) > 1 else None
        if name == "dev256":
            ev["dev16"] = score(preds[:16], asts[:16])
            ev["dev16"]["CE"] = {"GRU": mean(g[:16]), "IB1_online_bigram_same_stream": mean(b1[:16]),
                                 "IB2_lossweighted_slot_same_stream": mean(b2[:16])}
            ev["dev16"]["predictions"] = preds[:16]
            ev["dev256_predictions"] = [canon(p["ast"]) if p["ast"] is not None else "OUTCOME:" + p["outcome"] for p in preds]
        ev[name] = sc
    ev["eval_seconds"] = time.monotonic() - t0
    say("\n== EVAL %s (after %d updates, %.3f s, complete=%s)" % (tag, updates_done, ev["eval_seconds"], ev["complete"]))
    for name in ("S", "set2", "dev16", "dev256"):
        sc = ev[name]
        say(" %-6s exact %d/%d by depth %s | distinct outputs %d | shape== %d leaf-seq== %d pred-shape-in-train %d | pred depth %s" % (
            name, sc["exact"], sc["n"], json.dumps({k: [v["canonical_exact"], v["n"]] for k, v in sc["by_depth"].items()}),
            sc["distinct_outputs"], sc["EXTRA_shape_equal"], sc["EXTRA_leaf_sequence_equal"], sc["EXTRA_pred_shape_is_a_train_shape"],
            json.dumps(sc["EXTRA_pred_depth_hist"])))
        c = sc["CE"]
        say("        CE GRU %.6f | IB1 bigram %.6f | IB2 lw-slot %.6f%s" % (
            c["GRU"], c["IB1_online_bigram_same_stream"], c["IB2_lossweighted_slot_same_stream"],
            "" if name == "dev16" else " | EXTRA one-pass IB1 %.6f IB2 %.6f | GRU rows below IB1 %d, below IB2 %d | spread %s" % (
                c["EXTRA_IB1_one_pass_S"], c["EXTRA_IB2_one_pass_S"], c["GRU_rows_below_IB1"], c["GRU_rows_below_IB2"],
                "%.6f" % sc["EXTRA_bottleneck_relative_spread"] if sc["EXTRA_bottleneck_relative_spread"] is not None else "n/a")))
    return ev


# ---------------- training loop: q4_smoke_job.py:339-355 with the S schedule ----------------
log, evals, fidelity = [], {}, None
budget_limited, stop_reason = False, "MAX_UPDATES"
T_TRAIN0 = time.monotonic()
u = 0
while u < MAX_UPDATES:
    if time.monotonic() - T_TRAIN0 >= MAX_WALL:
        budget_limited, stop_reason = True, "WALL_CAP_300S"
        break
    index = S[u % 256]
    target = tr_tok[index]
    optimizer.zero_grad(set_to_none=True)
    logits = model.teacher_forced_logits(tr_in[index], target[:-1])
    gold = torch.tensor(target, dtype=torch.long, device=model._device())
    loss = F.cross_entropy(logits, gold)
    if not torch.isfinite(loss).item():
        raise SystemExit("NUMERICAL_FAILURE: training loss at update %d" % (u + 1))
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP, error_if_nonfinite=True)
    optimizer.step()
    u += 1
    log.append({"update": u, "row": index, "loss": float(loss.item()), "pre_clip_gradient_norm": float(norm.item())})
    ib_feed(IB1, IB2, target)
    if u == 128:
        st = model.state_dict()
        eq = {k: bool(torch.equal(st[k], ck_state[k])) for k in ck_state}
        mad = max((st[k] - ck_state[k]).abs().max().item() for k in ck_state)
        loss_eq = sum(a["loss"] == b["loss"] for a, b in zip(log, smoke_updates))
        norm_eq = sum(a["pre_clip_gradient_norm"] == b["pre_clip_gradient_norm"] for a, b in zip(log, smoke_updates))
        fidelity = {"all_tensors_equal_checkpoint": all(eq.values()), "tensors_equal": sum(eq.values()), "tensors": len(eq),
                    "max_abs_diff": mad, "losses_equal_smoke_log": loss_eq, "grad_norms_equal_smoke_log": norm_eq,
                    "seconds_since_train_start": time.monotonic() - T_TRAIN0}
        say("FIDELITY @128: %s" % json.dumps(fidelity))
    if u in EVAL_AT:
        evals[str(u)] = evaluate(str(u), u)
train_wall = time.monotonic() - T_TRAIN0
say("\nTRAINING STOPPED: updates %d, reason %s, budget_limited %s, wall since update 1 %.3f s (includes in-run evals)" % (
    u, stop_reason, budget_limited, train_wall))
evals["end"] = evaluate("end", u)

# ---------------- loss curve summary ----------------
def seg(a, b):
    xs = [r["loss"] for r in log[a:b]]
    return mean(xs)


curve = {"%d-%d" % (a + 1, b): seg(a, b) for a, b in ((0, 128), (128, 256), (256, 512), (512, 1024), (1024, 1536), (1536, 2000)) if a < len(log)}
say("mean training loss by update window:", json.dumps(curve))
R.update({"fidelity_at_128": fidelity, "updates_done": u, "stop_reason": stop_reason, "budget_limited": budget_limited,
          "train_wall_seconds_incl_inrun_evals": train_wall, "loss_windows": curve,
          "evals": {k: {kk: vv for kk, vv in v.items()} for k, v in evals.items()}})

# ---------------- rule reading (per PREREG_RT2.txt item 8), END only ----------------
E = evals["end"]
Sd = E["S"]["by_depth"]
s_d1_rate = Sd["1"]["canonical_exact"] / Sd["1"]["n"]
ce_S = E["S"]["CE"]
bug_ce_primary = ce_S["GRU"] >= min(ce_S["IB1_online_bigram_same_stream"], ce_S["IB2_lossweighted_slot_same_stream"])
bug_ce_strict = ce_S["GRU"] >= max(ce_S["IB1_online_bigram_same_stream"], ce_S["IB2_lossweighted_slot_same_stream"])
bug = s_d1_rate < 0.10 and E["S"]["distinct_outputs"] <= 2 and bug_ce_primary
bug_strict = s_d1_rate < 0.10 and E["S"]["distinct_outputs"] <= 2 and bug_ce_strict


def d12(sc):
    return sum(sc["by_depth"].get(k, {"canonical_exact": 0})["canonical_exact"] for k in ("1", "2"))


tlt = d12(E["S"]) > 0 and d12(E["set2"]) > 0 and E["S"]["distinct_outputs"] > 2 and E["set2"]["distinct_outputs"] > 2
tlt_perdepth = all(E[n]["by_depth"][k]["canonical_exact"] > 0 for n in ("S", "set2") for k in ("1", "2")) and \
    E["S"]["distinct_outputs"] > 2 and E["set2"]["distinct_outputs"] > 2
tlt_distinct1 = d12(E["S"]) > 0 and d12(E["set2"]) > 0 and E["S"]["distinct_outputs"] > 1 and E["set2"]["distinct_outputs"] > 1
s2d3 = E["set2"]["by_depth"]["3"]
s2d3_rate = s2d3["canonical_exact"] / s2d3["n"]
dev_exact = E["dev256"]["exact"]
design = s2d3_rate >= 0.25 and dev_exact == 0
transfer = dev_exact >= 1
inconclusive = dev_exact == 0 and 0 < s2d3_rate < 0.25
fired = [name for name, f in (("BUG_OR_OPTIMISATION_FAILURE", bug), ("TOO_LITTLE_TRAINING", tlt), ("TASK_DESIGN_LIMIT", design),
                              ("SHAPE_TRANSFER_POSSIBLE", transfer), ("INCONCLUSIVE", inconclusive)) if f]
if budget_limited:
    fired.append("BUDGET_LIMITED")
rules = {"fired": fired,
         "inputs": {"updates_done": u, "S_depth1_exact_rate": s_d1_rate, "S_depth1": Sd["1"], "S_distinct": E["S"]["distinct_outputs"],
                    "CE_S": ce_S, "bug_ce_primary": bug_ce_primary, "bug_ce_strict": bug_ce_strict, "bug_strict": bug_strict,
                    "S_exact_depth12": d12(E["S"]), "set2_exact_depth12": d12(E["set2"]), "set2_distinct": E["set2"]["distinct_outputs"],
                    "tlt_perdepth_variant": tlt_perdepth, "tlt_distinct_gt1_variant": tlt_distinct1,
                    "set2_depth3": s2d3, "set2_depth3_rate": s2d3_rate, "dev256_exact": dev_exact, "dev16_exact": E["dev16"]["exact"]},
         "design_axis_fits_none": (not design and not transfer and not inconclusive)}
say("\n== RULE READING (per PREREG_RT2.txt item 8, END reading)")
say(json.dumps(rules, indent=1))
R["rules"] = rules
R["cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated(0)
R["process_seconds"] = time.monotonic() - T_PROC0
(OUT / "rt2_results.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
with (OUT / "rt2_updates.jsonl").open("w", encoding="utf-8") as fh:
    for r in log:
        fh.write(json.dumps(r) + "\n")
say("cuda peak allocated bytes:", R["cuda_peak_allocated_bytes"], "| process seconds %.3f" % R["process_seconds"])
say("wrote", OUT / "rt2_results.json", "and", OUT / "rt2_updates.jsonl")
