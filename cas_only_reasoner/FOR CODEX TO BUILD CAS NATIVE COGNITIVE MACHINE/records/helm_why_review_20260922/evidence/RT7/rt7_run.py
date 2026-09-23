import sys, torch
if not torch.cuda.is_available(): print('GPU_REQUIRED'); sys.exit(2)
"""RT7: ONE bounded 8-row overfit re-training of the Q4 StrictR1 (width 64), held in memory only.
Built from SCRATCH/RT2/rt2_run.py (bit-faithful per RT2-F1). ONE change: update u trains row S8[(u-1) % 8],
S8 = first 8 rows of random.Random(20260921).shuffle(list(range(2048))) (the smoke's first 8 rows).
Caps: 2,000 updates or 270 s since process start (checked before each update), whichever first.
Targets: R5 parser on VISIBLE observations. Sealed and eval files are never opened. Writes ONLY into SCRATCH/RT7.
Pre-run record: SCRATCH/RT7/PREREG_RT7.txt. Every number: DIAGNOSTIC_NOT_CLAIM_BEARING."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import collections
import hashlib
import json
import random
import time
from pathlib import Path

T_PROC0 = time.monotonic()
ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
SCRATCH = Path("C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review")
OUT = SCRATCH / "RT7"
RUN = ROOT / "records/q4_authorized_20260922/run_001"
REC = ROOT / "records/q4_authorized_20260922"
DATA = LAB / "data/q3_v0_7"
SEED, WIDTH, LR, CLIP = 20260921, 64, 0.001, 1.0
MAX_UPDATES, PROC_CAP = 2000, 270.0
EVAL_AT = (250, 500, 1000, 2000)
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(SCRATCH / "R5"))

from common import parse, depth, canon, show, shape, leaves, slot_sequence, read_jsonl  # R5 helpers (pure Python)
from learner_q4_decoder import TOKENS, ast_to_tokens, tokens_to_ast, allowed_next, free_decode
from learner_q4_representation import from_visible_record
from learner_q4_neural import NeuralConfig, build_model
from q3_load import load_visible

F = torch.nn.functional
DEV = "cuda:0"
PREREG = OUT / "PREREG_RT7.txt"
R = {"label": "DIAGNOSTIC_NOT_CLAIM_BEARING", "prereg_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest()}


def say(*a):
    print(*a, flush=True)


say("prereg sha256", R["prereg_sha256"])

# ---------------- data (visible files only) ----------------
train_vis = load_visible(DATA, "G", "train")[:2048]
dev_vis = load_visible(DATA, "G", "dev")
assert len(train_vis) == 2048 and len(dev_vis) == 256
order = list(range(2048))
random.Random(SEED).shuffle(order)
S8 = order[:8]
s8_ast = [parse(train_vis[i]["observation"]) for i in S8]
s8_tok = [ast_to_tokens(a) for a in s8_ast]
s8_in = [from_visible_record(train_vis[i]) for i in S8]
s8_slots = [[k for k, _ in slot_sequence(t)] for t in s8_tok]
roundtrip = sum(tokens_to_ast(t) == a for t, a in zip(s8_tok, s8_ast))
dev16_ast = [parse(r["observation"]) for r in dev_vis[:16]]
dev16_in = [from_visible_record(r) for r in dev_vis[:16]]
insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
assert [c["record_id"] for c in insp] == [r["record_id"] for r in dev_vis[:16]]
dev16_ref_ok = sum(c["checker_reference_ast"] == a for c, a in zip(insp, dev16_ast))
say("S8 train-pool indices:", S8)
for k, i in enumerate(S8):
    say("  row %d idx %4d record %s depth %d target-len %d | %s" % (k, i, train_vis[i]["record_id"], depth(s8_ast[k]), len(s8_tok[k]), show(s8_ast[k])))
say("token round-trip on S8: %d/8 | dev16 parser == checker_reference_ast: %d/16" % (roundtrip, dev16_ref_ok))
slot_counts = collections.Counter(k for s in s8_slots for k in s)
say("S8 gold positions by slot class:", dict(sorted(slot_counts.items())))
R["S8"] = [{"row": k, "train_index": i, "record_id": train_vis[i]["record_id"], "depth": depth(s8_ast[k]), "target": show(s8_ast[k]),
            "target_tokens": [TOKENS[t] for t in s8_tok[k]]} for k, i in enumerate(S8)]
R["sanity"] = {"token_roundtrip_S8": roundtrip, "dev16_parser_matches_reference": dev16_ref_ok, "S8_slot_counts": dict(slot_counts)}
smoke_updates = read_jsonl(RUN / "updates.jsonl")

# ---------------- training setup: q4_smoke_job.py:327-336 ----------------
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

LEAF = ("noetic", "domain", "drive", "register")
STRUCT = ("expr", "op", "eos")
CLASSES = ("expr", "op", "noetic", "domain", "drive", "register", "eos")


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def spread(vals):
    X = torch.tensor(vals, dtype=torch.float64, device=DEV)
    n = X.shape[0]
    D = ((X[:, None, :] - X[None, :, :]) ** 2).sum(-1).sqrt()
    iu = torch.triu_indices(n, n, offset=1, device=DEV)
    pair = D[iu[0], iu[1]]
    norms = X.norm(dim=1)
    Xn = X / norms[:, None]
    cos = (Xn @ Xn.T)[iu[0], iu[1]]
    return {"relative_spread": (pair.mean() / norms.mean()).item(), "mean_pairwise_L2": pair.mean().item(),
            "mean_norm": norms.mean().item(), "min_pairwise_cosine": cos.min().item(), "mean_pairwise_cosine": cos.mean().item()}


def decode_with_hidden(hidden, prefix):
    """Same parts and order as learner_q4_neural.py:103-105, with an externally chosen starting state."""
    values, _ = model.decoder(model.output_embedding(model._prefix_tensor(prefix)), hidden)
    return model.output_head(values[0])


def pooled(rows, classes, key):
    num = sum(r[key][c][0] for r in rows for c in classes)
    den = sum(r[key][c][1] for r in rows for c in classes)
    return num / den if den else float("nan")


def evaluate(updates_done):
    t0 = time.monotonic()
    ev = {"updates_done": updates_done}
    # (i) free decode
    preds, vecs = [], []
    for x in s8_in:
        v = model.encode(x)
        vecs.append(v.values)
        preds.append(free_decode(v, model.next_logits))
    rows = []
    for k in range(8):
        p = preds[k]
        rows.append({"row": k, "depth": depth(s8_ast[k]), "outcome": p.outcome, "exact": p.ast == s8_ast[k],
                     "pred": show(p.ast) if p.ast is not None else "OUTCOME:" + p.outcome,
                     "shape_equal": p.ast is not None and shape(p.ast) == shape(s8_ast[k]),
                     "leaf_seq_equal": p.ast is not None and leaves(p.ast) == leaves(s8_ast[k])})
    ev["exact_S8"] = sum(r["exact"] for r in rows)
    ev["distinct_outputs_S8"] = len({r["pred"] for r in rows})
    # (ii)/(iii) teacher-forced
    with torch.no_grad():
        H = [model._encode_tensor(x) for x in s8_in]
        tf_identity = 0
        for k in range(8):
            tgt = s8_tok[k]
            gold = torch.tensor(tgt, dtype=torch.long, device=DEV)
            lg_true = model.teacher_forced_logits(s8_in[k], tgt[:-1])
            lg_true2 = decode_with_hidden(H[k], tgt[:-1])
            tf_identity += bool(torch.equal(lg_true, lg_true2))
            lg_swap = decode_with_hidden(H[(k + 1) % 8], tgt[:-1])
            ce_true = F.cross_entropy(lg_true, gold, reduction="none").tolist()
            ce_swap = F.cross_entropy(lg_swap, gold, reduction="none").tolist()
            ce_all = [F.cross_entropy(decode_with_hidden(H[j], tgt[:-1]), gold, reduction="none").tolist() for j in range(8) if j != k]
            am = torch.argmax(lg_true, dim=-1).tolist()
            am_masked = []
            for pos in range(len(tgt)):
                legal = allowed_next(tuple(tgt[:pos]))
                row = lg_true[pos].tolist()
                am_masked.append(min(legal, key=lambda t: (-row[t], t)))
            r = rows[k]
            r["acc"] = {c: [0, 0] for c in CLASSES}
            r["acc_masked"] = {c: [0, 0] for c in CLASSES}
            r["ce_true"] = {c: [0.0, 0] for c in CLASSES}
            r["ce_swap"] = {c: [0.0, 0] for c in CLASSES}
            r["ce_swapall"] = {c: [0.0, 0] for c in CLASSES}
            for pos, c in enumerate(s8_slots[k]):
                r["acc"][c][0] += am[pos] == tgt[pos]; r["acc"][c][1] += 1
                r["acc_masked"][c][0] += am_masked[pos] == tgt[pos]; r["acc_masked"][c][1] += 1
                r["ce_true"][c][0] += ce_true[pos]; r["ce_true"][c][1] += 1
                r["ce_swap"][c][0] += ce_swap[pos]; r["ce_swap"][c][1] += 1
                r["ce_swapall"][c][0] += mean([ce[pos] for ce in ce_all]); r["ce_swapall"][c][1] += 1
            r["row_ce_true"] = mean(ce_true)
            r["row_ce_swap"] = mean(ce_swap)
            r["argmax_tokens"] = [TOKENS[t] for t in am]
    ev["tf_true_logits_bit_identical_rows"] = tf_identity
    ev["acc_by_class"] = {c: pooled(rows, (c,), "acc") for c in CLASSES}
    ev["acc_masked_by_class"] = {c: pooled(rows, (c,), "acc_masked") for c in CLASSES}
    ev["ce_true_by_class"] = {c: pooled(rows, (c,), "ce_true") for c in CLASSES}
    ev["ce_swap_by_class"] = {c: pooled(rows, (c,), "ce_swap") for c in CLASSES}
    ev["ce_swapall_by_class"] = {c: pooled(rows, (c,), "ce_swapall") for c in CLASSES}
    ev["leaf_acc_pooled"] = pooled(rows, LEAF, "acc")
    ev["struct_acc_pooled"] = pooled(rows, STRUCT, "acc")
    ev["leaf_acc_masked_pooled"] = pooled(rows, LEAF, "acc_masked")
    ev["struct_acc_masked_pooled"] = pooled(rows, STRUCT, "acc_masked")
    ev["leaf_ce_true_pooled"] = pooled(rows, LEAF, "ce_true")
    ev["leaf_ce_swap_pooled"] = pooled(rows, LEAF, "ce_swap")
    ev["leaf_ce_swapall_pooled"] = pooled(rows, LEAF, "ce_swapall")
    ev["leaf_ce_swap_minus_true"] = ev["leaf_ce_swap_pooled"] - ev["leaf_ce_true_pooled"]
    ev["struct_ce_true_pooled"] = pooled(rows, STRUCT, "ce_true")
    ev["struct_ce_swap_pooled"] = pooled(rows, STRUCT, "ce_swap")
    ev["spread_S8"] = spread(vecs)
    ev["rows"] = rows
    ev["eval_seconds"] = time.monotonic() - t0
    say("\n== EVAL after %d updates (%.3f s)" % (updates_done, ev["eval_seconds"]))
    say(" S8 exact %d/8 | distinct outputs %d | TF(true) logits == teacher_forced_logits on %d/8 rows" % (
        ev["exact_S8"], ev["distinct_outputs_S8"], tf_identity))
    for r in rows:
        say("   row %d depth %d exact %-5s shape== %-5s leaf== %-5s | row CE true %.6f swap %.6f | pred %s" % (
            r["row"], r["depth"], r["exact"], r["shape_equal"], r["leaf_seq_equal"], r["row_ce_true"], r["row_ce_swap"], r["pred"]))
    say(" TF argmax acc by class: " + " ".join("%s %s" % (c, repr(ev["acc_by_class"][c])) for c in CLASSES))
    say(" TF CE TRUE by class:    " + " ".join("%s %s" % (c, repr(ev["ce_true_by_class"][c])) for c in CLASSES))
    say(" TF CE SWAP by class:    " + " ".join("%s %s" % (c, repr(ev["ce_swap_by_class"][c])) for c in CLASSES))
    say(" pooled leaf acc %r | structure acc %r | leaf CE TRUE %r SWAP %r SWAP-TRUE %r | EXTRA SWAP-ALL %r" % (
        ev["leaf_acc_pooled"], ev["struct_acc_pooled"], ev["leaf_ce_true_pooled"], ev["leaf_ce_swap_pooled"],
        ev["leaf_ce_swap_minus_true"], ev["leaf_ce_swapall_pooled"]))
    say(" EXTRA masked-argmax: leaf %r structure %r | structure CE TRUE %r SWAP %r" % (
        ev["leaf_acc_masked_pooled"], ev["struct_acc_masked_pooled"], ev["struct_ce_true_pooled"], ev["struct_ce_swap_pooled"]))
    say(" bottleneck spread S8: %s" % json.dumps(ev["spread_S8"]))
    return ev


# ---------------- training loop: q4_smoke_job.py:339-355 with the S8 schedule ----------------
log, evals, fidelity = [], {}, None
budget_limited, stop_reason = False, "MAX_UPDATES"
T_TRAIN0 = time.monotonic()
u = 0
while u < MAX_UPDATES:
    if time.monotonic() - T_PROC0 >= PROC_CAP:
        budget_limited, stop_reason = True, "PROCESS_CAP_270S"
        break
    k = u % 8
    target = s8_tok[k]
    optimizer.zero_grad(set_to_none=True)
    logits = model.teacher_forced_logits(s8_in[k], target[:-1])
    gold = torch.tensor(target, dtype=torch.long, device=model._device())
    loss = F.cross_entropy(logits, gold)
    if not torch.isfinite(loss).item():
        raise SystemExit("NUMERICAL_FAILURE: training loss at update %d" % (u + 1))
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP, error_if_nonfinite=True)
    optimizer.step()
    u += 1
    log.append({"update": u, "row": k, "train_index": S8[k], "loss": float(loss.item()), "pre_clip_gradient_norm": float(norm.item())})
    if u == 8:
        loss_eq = [a["loss"] == b["loss"] for a, b in zip(log, smoke_updates[:8])]
        norm_eq = [a["pre_clip_gradient_norm"] == b["pre_clip_gradient_norm"] for a, b in zip(log, smoke_updates[:8])]
        fidelity = {"losses_equal": sum(loss_eq), "grad_norms_equal_EXTRA": sum(norm_eq), "n": 8,
                    "ours": [r["loss"] for r in log], "smoke": [r["loss"] for r in smoke_updates[:8]],
                    "smoke_update_ids": [r["update"] for r in smoke_updates[:8]]}
        say("FIDELITY PRE-CHECK (first 8 losses vs run_001/updates.jsonl updates 1-8): %s" % json.dumps(fidelity))
        if not all(loss_eq):
            R.update({"fidelity": fidelity, "outcome": "SCRIPT_DEFECT"})
            (OUT / "rt7_results.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
            say("SCRIPT_DEFECT: fidelity pre-check failed; stopping with no reading.")
            sys.exit(3)
    if u in EVAL_AT:
        evals[str(u)] = evaluate(u)
train_wall = time.monotonic() - T_TRAIN0
say("\nTRAINING STOPPED: updates %d, reason %s, budget_limited %s, wall since update 1 %.3f s (includes in-run evals)" % (
    u, stop_reason, budget_limited, train_wall))
if str(u) not in evals:
    evals[str(u)] = evaluate(u)
FINAL = evals[str(u)]

# ---------------- (v) mean training loss per 8-update pass ----------------
passes = [mean([r["loss"] for r in log[8 * p:8 * p + 8]]) for p in range(len(log) // 8)]
say("\nmean training loss per pass: pass1 %r pass2 %r pass31 %r pass32 %r pass62 %r pass63 %r pass125 %r pass250 %r (passes complete: %d)" % tuple(
    [passes[i] if i < len(passes) else None for i in (0, 1, 30, 31, 61, 62, 124, 249)] + [len(passes)]))
for p0 in range(0, len(passes), 25):
    say("  passes %3d-%3d: %s" % (p0 + 1, min(p0 + 25, len(passes)), " ".join("%.6f" % x for x in passes[p0:p0 + 25])))
last_pass = passes[-1]
say("per-row loss at the last pass (updates %d-%d): %s" % (log[-8]["update"], log[-1]["update"], json.dumps([r["loss"] for r in log[-8:]])))

# ---------------- context only: dev rows 1-16 ----------------
dev_rows = []
for x, a, rv in zip(dev16_in, dev16_ast, dev_vis[:16]):
    p = free_decode(model.encode(x), model.next_logits)
    dev_rows.append({"record_id": rv["record_id"], "depth": depth(a), "exact": p.ast == a,
                     "pred": show(p.ast) if p.ast is not None else "OUTCOME:" + p.outcome})
say("\nCONTEXT ONLY (not a rule input): dev rows 1-16 exact %d/16 | distinct outputs %d | outputs: %s" % (
    sum(r["exact"] for r in dev_rows), len({r["pred"] for r in dev_rows}), json.dumps(collections.Counter(r["pred"] for r in dev_rows).most_common())))

# ---------------- rule reading (PREREG_RT7.txt item 7), FINAL evaluation only ----------------
ex = FINAL["exact_S8"]
fits = ex >= 7
bug = ex <= 1 and FINAL["leaf_acc_pooled"] < 0.50 and last_pass > 0.5
bnu = ex <= 1 and FINAL["struct_acc_pooled"] >= 0.95 and FINAL["leaf_ce_swap_minus_true"] < 0.05
fired = [n for n, f in (("FITS", fits), ("BUG_OR_OPTIMISATION_FAILURE", bug), ("BOTTLENECK_NOT_USED", bnu)) if f]
if not fired:
    fired = ["INCONCLUSIVE"]
if budget_limited:
    fired.append("BUDGET_LIMITED")
rules = {"fired": fired, "inputs": {"updates_done": u, "exact_S8": ex, "leaf_acc_pooled": FINAL["leaf_acc_pooled"],
                                    "struct_acc_pooled": FINAL["struct_acc_pooled"], "last_pass_mean_loss": last_pass,
                                    "leaf_ce_true_pooled": FINAL["leaf_ce_true_pooled"], "leaf_ce_swap_pooled": FINAL["leaf_ce_swap_pooled"],
                                    "leaf_ce_swap_minus_true": FINAL["leaf_ce_swap_minus_true"]}}
say("\n== RULE READING (PREREG_RT7.txt item 7, FINAL evaluation)")
say(json.dumps(rules, indent=1))
R.update({"fidelity": fidelity, "updates_done": u, "stop_reason": stop_reason, "budget_limited": budget_limited,
          "train_wall_seconds_incl_inrun_evals": train_wall, "pass_mean_losses": passes, "evals": evals,
          "dev16_context": dev_rows, "rules": rules, "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(0),
          "process_seconds": time.monotonic() - T_PROC0})
(OUT / "rt7_results.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
with (OUT / "rt7_updates.jsonl").open("w", encoding="utf-8") as fh:
    for r in log:
        fh.write(json.dumps(r) + "\n")
say("cuda peak allocated bytes:", R["cuda_peak_allocated_bytes"], "| process seconds %.3f" % R["process_seconds"])
say("wrote", OUT / "rt7_results.json", "and", OUT / "rt7_updates.jsonl")
