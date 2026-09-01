"""run_pilot.py -- CJT-DEV-P1 static neural coupling development pilot (owner
directive CJT-DEV-P1 + amendment CJT-DEV-P1-S7Delta). DEVELOPMENT-ONLY,
NON-CLAIM-BEARING.

Four heads trained over FROZEN Qwen2.5-0.5B activations (cached once), comparing:
  S0   plain matched head (no attention, no profiles)
  S3   exact construction-gold CAS profile (one-hot ^2/^3/^6/^8, UNCHANGED)
  S6   uniform-profile matched-capacity control ([.25,.25,.25,.25])
  S7D  the soft WordNet semantic simplex control S7_DELTA_WN1 (Delta^3 profiles)

Reuses the frozen Gate 1B building blocks in ../cjt_gate1a_static_neural_v1/exec:
activation_extraction (cache-once), dataset_assembly (gold-isolation), arms
(one ArmHead module + capacity matcher), baselines (B0 floor / B1 ceiling),
layer_select (S0-only L*). The only additions here are the soft-profile source
for S7D and per-checkpoint validation.

NO protected split is generated, read, or evaluated. NO claim is promoted. No
"CAS-specific" language. GPU required (no CPU neural fallback). Runs on a cloud
AWS GPU instance (owner directive 2026-08-31: "no local, use cloud aws or runpod").

Stages:  --stage P0  (all 4 arms, seed 11, 100 updates: smoke)
          --stage P1  (4 arms x seeds 11/23/47 x 1000 updates)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tools"))

from exec.activation_extraction import extract_split, MODEL_ID          # noqa: E402
from exec.arms import build_arm_head, match_capacity, trainable_param_count  # noqa: E402
from exec.dataset_assembly import assemble_examples                     # noqa: E402
from exec.baselines import score_split                                  # noqa: E402
from exec.layer_select import CANDIDATE_LAYERS, select_layer            # noqa: E402

SEEDS = [11, 23, 47]
CHECKPOINTS = [0, 50, 100, 250, 500, 750, 1000]
BATCH_SIZE = 32
LR, BETAS, WD, WARMUP_FRAC, CLIP = 1.0e-3, (0.9, 0.999), 0.01, 0.05, 1.0
# arm_id -> the frozen ArmHead module structure it uses
ARM_MODULE = {"S0": "S0", "S3": "S3", "S6": "S6", "S7D": "S3"}
ARMS = ["S0", "S3", "S6", "S7D"]

# device/cost provenance (set from CLI in main); the authoritative billed cost
# for a cloud run is the instance-runtime * rate, recorded by the orchestrator --
# this in-pilot figure is the compute-wall lower bound
DEVICE_NOTE = "cloud GPU"
COST_PER_HOUR = 0.0


def load_records(split):
    p = PKG / "data" / "candidate" / f"{split}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l]


def soft_profiles(clause_texts, v2p):
    verbs = list(v2p)
    out = []
    for ct in clause_texts:
        hits = [v for v in verbs if re.search(rf"\b{re.escape(v)}\b", ct)]
        if len(hits) != 1:
            raise ValueError(f"S7DELTA_LOOKUP_FAILURE: {len(hits)} verbs in {ct!r}")
        out.append([float(x) for x in v2p[hits[0]]])
    return out


def assemble(records, arm, delta_v2p):
    if arm == "S7D":
        exs = assemble_examples(records, "S0")     # skeleton, gold-isolated
        for ex in exs:
            ex["profiles"] = soft_profiles(ex["clauses"], delta_v2p)
        return exs
    return assemble_examples(records, arm)


def pack_batches(examples, features, order):
    import torch
    from exec.arms import MAX_IDEAS
    ordered = [examples[i] for i in order]
    batches = []
    for start in range(0, len(ordered), BATCH_SIZE):
        chunk = ordered[start:start + BATCH_SIZE]
        b = len(chunk)
        max_c = max(features[ex["passage_id"]]["cand"].shape[0] for ex in chunk)
        h = torch.zeros(b, MAX_IDEAS, 896)
        g = torch.zeros(b, 896)
        idea_mask = torch.zeros(b, MAX_IDEAS, dtype=torch.bool)
        cand_enc = torch.zeros(b, max_c, 896)
        cand_mask = torch.zeros(b, max_c, dtype=torch.bool)
        answer_index = torch.zeros(b, dtype=torch.long)
        has_p = chunk[0]["profiles"] is not None
        p = torch.zeros(b, MAX_IDEAS, 4) if has_p else None
        qts = []
        for j, ex in enumerate(chunk):
            f = features[ex["passage_id"]]
            n, c = f["h"].shape[0], f["cand"].shape[0]
            h[j, :n] = f["h"].float(); g[j] = f["g"].float()
            idea_mask[j, :n] = True
            cand_enc[j, :c] = f["cand"].float(); cand_mask[j, :c] = True
            answer_index[j] = ex["answer_index"]
            qts.append(ex["question_type"])
            if p is not None:
                p[j, :n] = torch.tensor(ex["profiles"], dtype=torch.float32)
        batches.append({"h": h, "g": g, "p": p, "idea_mask": idea_mask,
                        "cand_enc": cand_enc, "cand_mask": cand_mask,
                        "answer_index": answer_index, "qt": qts})
    return batches


def seeded_order(n, seed):
    import torch
    return torch.randperm(n, generator=torch.Generator().manual_seed(seed)).tolist()


def lr_lambda(updates):
    warm = max(1, int(updates * WARMUP_FRAC))
    def f(step):
        if step < warm:
            return (step + 1) / warm
        t = (step - warm) / max(1, updates - warm)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, t)))
    return f


def evaluate(head, val_batches, device):
    import torch
    head.eval()
    ce = torch.nn.CrossEntropyLoss(reduction="sum")
    tot, correct, loss_sum = 0, 0, 0.0
    per = {}
    with torch.no_grad():
        for bt in val_batches:
            logits = head(bt["h"].to(device), bt["g"].to(device),
                          None if bt["p"] is None else bt["p"].to(device),
                          bt["idea_mask"].to(device), bt["cand_enc"].to(device),
                          bt["cand_mask"].to(device))
            tgt = bt["answer_index"].to(device)
            loss_sum += float(ce(logits, tgt).item())
            pred = logits.argmax(dim=1)
            ok = (pred == tgt)
            correct += int(ok.sum().item()); tot += len(tgt)
            for i, qt in enumerate(bt["qt"]):
                a, c = per.get(qt, (0, 0))
                per[qt] = (a + int(ok[i].item()), c + 1)
    head.train()
    return {"val_accuracy": correct / tot, "val_loss": loss_sum / tot,
            "per_question_type": {qt: {"accuracy": a / c, "correct": a, "total": c}
                                  for qt, (a, c) in sorted(per.items())}}


def train_arm(arm, seed, widen_w, train_batches, val_batches, updates, device):
    import torch
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats()
    head = build_arm_head(ARM_MODULE[arm], widen_w).float().to(device)
    opt = torch.optim.AdamW(head.parameters(), lr=LR, betas=BETAS, weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda(updates))
    loss_fn = torch.nn.CrossEntropyLoss()
    curve = []
    cps = set(CHECKPOINTS)
    t0 = time.time()
    if 0 in cps:                                    # checkpoint before any update
        ev = evaluate(head, val_batches, device)
        curve.append({"step": 0, "train_loss": None, **ev})
    it = iter(train_batches)
    last_train_loss = None
    for step in range(updates):
        try:
            bt = next(it)
        except StopIteration:
            it = iter(train_batches); bt = next(it)
        logits = head(bt["h"].to(device), bt["g"].to(device),
                      None if bt["p"] is None else bt["p"].to(device),
                      bt["idea_mask"].to(device), bt["cand_enc"].to(device),
                      bt["cand_mask"].to(device))
        loss = loss_fn(logits, bt["answer_index"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(head.parameters(), CLIP)
        opt.step(); sched.step()
        last_train_loss = float(loss.item())
        if not math.isfinite(last_train_loss):
            raise RuntimeError(f"NONFINITE_LOSS at step {step} arm {arm} seed {seed}")
        if (step + 1) in cps:
            ev = evaluate(head, val_batches, device)
            curve.append({"step": step + 1, "train_loss": last_train_loss, **ev})
    wall = time.time() - t0
    peak_mb = (torch.cuda.max_memory_allocated() / 1e6
               if device.startswith("cuda") else 0.0)
    return {"arm": arm, "seed": seed, "widen_w": widen_w,
            "trainable_params": trainable_param_count(head),
            "curve": curve, "final": curve[-1],
            "wall_clock_seconds": round(wall, 2),
            "peak_gpu_mem_mb": round(peak_mb, 1)}


def build_features(cache, layer):
    return {pid: {"h": v["layers"][layer][0], "g": v["layers"][layer][1],
                  "cand": v["cand"]} for pid, v in cache.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["P0", "P1"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results"))
    ap.add_argument("--updates", type=int, default=None)
    ap.add_argument("--device-note", default="cloud GPU",
                    help="human-readable device provenance recorded in outputs")
    ap.add_argument("--cost-per-hour", type=float, default=0.0,
                    help="instance on-demand USD/hour, for a compute-wall cost estimate")
    args = ap.parse_args()
    global DEVICE_NOTE, COST_PER_HOUR
    DEVICE_NOTE = args.device_note
    COST_PER_HOUR = args.cost_per_hour
    import torch
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CUDA device (no CPU neural fallback)")
    device = args.device
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    updates = args.updates or (100 if args.stage == "P0" else 1000)
    t_start = time.time()

    delta = json.loads((HERE / "S7_DELTA_WN1.json").read_text(encoding="utf-8"))
    delta_v2p = delta["verb_to_profile"]
    delta_sha = hashlib.sha256((HERE / "S7_DELTA_WN1.json").read_bytes()).hexdigest()

    train_recs = load_records("train")
    val_recs = load_records("val")

    # ---- frozen model + one-pass activation extraction (cache once) ----
    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to(device).eval()
    is_real = (device.startswith("cuda") and next(model.parameters()).is_cuda)
    cache_dir = out / "cache"; cache_dir.mkdir(exist_ok=True)
    caches = {}
    for split, recs in (("train", train_recs), ("val", val_recs)):
        cf = cache_dir / f"{split}_acts.pt"
        if cf.is_file():
            caches[split] = torch.load(cf, map_location="cpu", weights_only=False)
        else:
            te = time.time()
            caches[split] = extract_split(recs, tok, model, list(CANDIDATE_LAYERS), device)
            torch.save(caches[split], cf)
            print(f"[extract] {split}: {len(recs)} passages, "
                  f"{time.time()-te:.1f}s -> {cf.name}")
    del model
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    # candidate-tensor presence check (no cand=None may reach a head)
    for split in ("train", "val"):
        for pid, v in caches[split].items():
            if v["cand"] is None:
                raise RuntimeError(f"CANDIDATE_ENCODING_MISSING: {split}/{pid}")

    # ---- baselines B0 (floor) / B1 (ceiling) ----
    baselines = {"B0_floor_train": score_split(train_recs, "B0"),
                 "B0_floor_val": score_split(val_recs, "B0"),
                 "B1_ceiling_train": score_split(train_recs, "B1"),
                 "B1_ceiling_val": score_split(val_recs, "B1")}

    # capacity match: S0 widened to S3's trainable count; S3/S6/S7D are structural S3
    ref = trainable_param_count(build_arm_head("S3", 0))
    widen = {"S0": match_capacity("S0", ref), "S3": 0, "S6": 0, "S7D": 0}
    param_counts = {a: trainable_param_count(build_arm_head(ARM_MODULE[a], widen[a]))
                    for a in ARMS}

    # ---- layer selection: S0 only, val accuracy, lowest-index tie-break ----
    layer_val = {}
    for L in CANDIDATE_LAYERS:
        ftr = build_features(caches["train"], L)
        fva = build_features(caches["val"], L)
        ex_tr = assemble(train_recs, "S0", delta_v2p)
        ex_va = assemble(val_recs, "S0", delta_v2p)
        tb = pack_batches(ex_tr, ftr, seeded_order(len(ex_tr), 11))
        vb = pack_batches(ex_va, fva, list(range(len(ex_va))))
        r = train_arm("S0", 11, widen["S0"], tb, vb, updates, device)
        layer_val[L] = r["final"]["val_accuracy"]
        print(f"[layer-select] L={L} S0 val_acc={layer_val[L]:.4f}")
    Lstar = select_layer(layer_val)
    print(f"[layer-select] L*={Lstar}")

    # ---- the arm runs at L* ----
    ftr = build_features(caches["train"], Lstar)
    fva = build_features(caches["val"], Lstar)
    seeds = [11] if args.stage == "P0" else SEEDS
    runs = []
    val_order = list(range(len(val_recs)))
    for arm in ARMS:
        ex_tr = assemble(train_recs, arm, delta_v2p)
        ex_va = assemble(val_recs, arm, delta_v2p)
        vb = pack_batches(ex_va, fva, val_order)
        for seed in seeds:
            tb = pack_batches(ex_tr, ftr, seeded_order(len(ex_tr), seed))
            r = train_arm(arm, seed, widen[arm], tb, vb, updates, device)
            r["layer"] = Lstar
            runs.append(r)
            print(f"[{args.stage}] arm={arm:4} seed={seed} L*={Lstar} "
                  f"final_val_acc={r['final']['val_accuracy']:.4f} "
                  f"val_loss={r['final']['val_loss']:.4f} "
                  f"params={r['trainable_params']} {r['wall_clock_seconds']}s "
                  f"{r['peak_gpu_mem_mb']}MB")

    total_wall = time.time() - t_start
    write_outputs(out, args.stage, updates, Lstar, layer_val, param_counts,
                  baselines, runs, seeds, delta_sha, is_real, total_wall, device)
    return 0


def _mean_std(xs):
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    return m, math.sqrt(v)


def write_outputs(out, stage, updates, Lstar, layer_val, param_counts,
                  baselines, runs, seeds, delta_sha, is_real, total_wall, device):
    # per-arm aggregate over seeds (final val accuracy)
    by_arm = {}
    for a in ARMS:
        accs = [r["final"]["val_accuracy"] for r in runs if r["arm"] == a]
        losses = [r["final"]["val_loss"] for r in runs if r["arm"] == a]
        m, s = _mean_std(accs)
        by_arm[a] = {"final_val_accuracy_mean": round(m, 6),
                     "final_val_accuracy_std": round(s, 6),
                     "final_val_accuracy_by_seed": {r["seed"]: round(r["final"]["val_accuracy"], 6)
                                                    for r in runs if r["arm"] == a},
                     "final_val_loss_mean": round(sum(losses) / len(losses), 6),
                     "trainable_params": param_counts[a]}

    def updates_to(arm, thr):
        vals = []
        for r in runs:
            if r["arm"] != arm:
                continue
            hit = next((c["step"] for c in r["curve"] if c["val_accuracy"] >= thr), None)
            vals.append(hit)
        got = [v for v in vals if v is not None]
        return (round(sum(got) / len(got), 1) if got else None)

    comparison = {
        "S3_minus_S0": round(by_arm["S3"]["final_val_accuracy_mean"] - by_arm["S0"]["final_val_accuracy_mean"], 6),
        "S3_minus_S6": round(by_arm["S3"]["final_val_accuracy_mean"] - by_arm["S6"]["final_val_accuracy_mean"], 6),
        "S3_minus_S7D": round(by_arm["S3"]["final_val_accuracy_mean"] - by_arm["S7D"]["final_val_accuracy_mean"], 6),
        "updates_to_0.80": {a: updates_to(a, 0.80) for a in ARMS},
        "updates_to_0.90": {a: updates_to(a, 0.90) for a in ARMS},
        "updates_to_0.95": {a: updates_to(a, 0.95) for a in ARMS}}

    status, reason = dev_status(stage, by_arm, comparison, runs, seeds)

    raw = {"pilot": "CJT-DEV-P1", "amendment": "CJT-DEV-P1-S7Delta",
           "stage": stage, "non_claim_bearing": True, "is_real_model": is_real,
           "device": device, "model_id": MODEL_ID,
           "updates": updates, "batch_size": BATCH_SIZE, "seeds": seeds,
           "checkpoints": CHECKPOINTS, "selected_layer": Lstar,
           "layer_selection_val_accuracy": {str(k): round(v, 6) for k, v in layer_val.items()},
           "s7_delta_table_sha256": delta_sha,
           "baselines": baselines, "arms": by_arm, "arm_comparison": comparison,
           "runs": runs, "total_wall_clock_seconds": round(total_wall, 1),
           "total_cost_usd": round(total_wall / 3600.0 * COST_PER_HOUR, 4),
           "cost_note": (f"{DEVICE_NOTE}; compute-wall cost estimate at "
                         f"${COST_PER_HOUR:.4f}/hr (authoritative billed cost = "
                         f"instance-runtime * rate, in DEV_PILOT_RECEIPT)"),
           "development_status": status, "development_status_reason": reason}
    (out / "DEV_PILOT_RAW_RESULTS.json").write_text(json.dumps(raw, indent=2) + "\n",
                                                    encoding="utf-8")
    (out / "DEV_PILOT_ARM_COMPARISON.json").write_text(
        json.dumps({"arms": by_arm, "comparison": comparison,
                    "baselines": baselines, "development_status": status,
                    "reason": reason}, indent=2) + "\n", encoding="utf-8")

    # learning curves CSV
    with (out / "DEV_PILOT_LEARNING_CURVES.csv").open("w", newline="",
                                                      encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["arm", "seed", "layer", "step", "train_loss", "val_loss",
                    "val_accuracy"])
        for r in runs:
            for c in r["curve"]:
                w.writerow([r["arm"], r["seed"], r["layer"], c["step"],
                            "" if c["train_loss"] is None else round(c["train_loss"], 6),
                            round(c["val_loss"], 6), round(c["val_accuracy"], 6)])

    receipt = {"receipt_id": "DEV_PILOT_RECEIPT", "stage": stage,
               "non_claim_bearing": True, "is_real_model": is_real,
               "raw_results_sha256": hashlib.sha256(
                   (out / "DEV_PILOT_RAW_RESULTS.json").read_bytes()).hexdigest(),
               "s7_delta_table_sha256": delta_sha, "selected_layer": Lstar,
               "development_status": status, "total_wall_clock_seconds": round(total_wall, 1),
               "total_cost_usd": 0.0}
    (out / "DEV_PILOT_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                                encoding="utf-8")
    write_summary(out, stage, updates, Lstar, by_arm, comparison, baselines,
                  status, reason, runs, total_wall, is_real)
    print(f"\nDEVELOPMENT STATUS: {status}\n  {reason}")


def dev_status(stage, by_arm, comp, runs, seeds):
    if stage == "P0":
        finite = all(math.isfinite(r["final"]["val_loss"]) for r in runs)
        return ("PILOT_PIPELINE_FAILURE" if not finite
                else "P0_SMOKE_OK"), "P0 smoke: all arms trained, losses finite"
    s3 = by_arm["S3"]["final_val_accuracy_mean"]
    beats = all(comp[k] >= 0.02 for k in ("S3_minus_S0", "S3_minus_S6", "S3_minus_S7D"))
    # same-sign advantage in >= 2/3 seeds vs each of S0/S6/S7D
    def sign_ok(other):
        cnt = 0
        for sd in seeds:
            a3 = next(r["final"]["val_accuracy"] for r in runs if r["arm"] == "S3" and r["seed"] == sd)
            ao = next(r["final"]["val_accuracy"] for r in runs if r["arm"] == other and r["seed"] == sd)
            cnt += 1 if (a3 - ao) >= 0.02 else 0
        return cnt >= 2
    consistent = all(sign_ok(o) for o in ("S0", "S6", "S7D"))
    if beats and consistent:
        return "PROMISING_DEV_SIGNAL", ("S3 beats S0, S6 and S7-Delta by >=0.02 mean "
                                        "val accuracy with same-sign advantage in >=2/3 seeds")
    ties = (comp["S3_minus_S0"] < 0.02 or comp["S3_minus_S6"] < 0.02
            or comp["S3_minus_S7D"] < 0.02)
    if ties:
        return "NO_DEV_SIGNAL", ("S3 does not clear all three controls by >=0.02: "
                                 f"S3-S0={comp['S3_minus_S0']} S3-S6={comp['S3_minus_S6']} "
                                 f"S3-S7D={comp['S3_minus_S7D']}")
    return "INCONCLUSIVE_DEV_SIGNAL", "arm differences conflict across seeds/question types"


def write_summary(out, stage, updates, Lstar, by_arm, comp, baselines, status,
                  reason, runs, total_wall, is_real):
    L = ["# CJT-DEV-P1 development pilot summary", "",
         f"**Stage:** {stage} | **updates:** {updates} | **selected layer L\\*:** {Lstar} "
         f"| **is_real_model:** {is_real} | **status:** `{status}`", "",
         "Development-only, non-claim-bearing. No protected split, no claim, no "
         f"CAS-specific language. Device: {DEVICE_NOTE}.", "",
         "## Final validation accuracy (mean over seeds)", "",
         "| arm | mean val acc | std | val loss | params |",
         "|---|---|---|---|---|"]
    names = {"S0": "S0 plain", "S3": "S3 CAS (one-hot)", "S6": "S6 uniform",
             "S7D": "S7-Δ WordNet soft"}
    for a in ARMS:
        b = by_arm[a]
        L.append(f"| {names[a]} | {b['final_val_accuracy_mean']:.4f} | "
                 f"{b['final_val_accuracy_std']:.4f} | {b['final_val_loss_mean']:.4f} "
                 f"| {b['trainable_params']} |")
    L += ["", "## Arm comparison (mean val accuracy)", "",
          f"- **S3 − S0** = {comp['S3_minus_S0']:+.4f}",
          f"- **S3 − S6** = {comp['S3_minus_S6']:+.4f}",
          f"- **S3 − S7-Δ** = {comp['S3_minus_S7D']:+.4f}",
          f"- updates to 0.80 val acc: {comp['updates_to_0.80']}",
          f"- updates to 0.90 val acc: {comp['updates_to_0.90']}",
          f"- updates to 0.95 val acc: {comp['updates_to_0.95']}", "",
          "## Registered surface references", "",
          f"- **B0 floor** (val): {baselines['B0_floor_val']['overall']:.4f}",
          f"- **B1 ceiling** (val): {baselines['B1_ceiling_val']['overall']:.4f} "
          "(the task is exactly surface-solvable)", "",
          f"## Development verdict: `{status}`", "", reason, "",
          f"Total wall-clock: {total_wall:.1f}s across {len(runs)} runs.", ""]
    (out / "DEV_PILOT_SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
