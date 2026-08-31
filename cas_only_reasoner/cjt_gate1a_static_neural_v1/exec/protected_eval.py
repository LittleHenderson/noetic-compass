"""protected_eval.py -- the SINGLE protected evaluation pass (Gate 1B step 7).

Laws enforced here:
- runs ONLY after all 25 training runs have receipts (refuses otherwise);
- regenerates the protected split in-memory from the frozen generator and
  REQUIRES its content digest to equal DATASET_MANIFEST_CANDIDATE.json's
  pre-registration (DATASET_INTEGRITY_FAILURE otherwise; if the owner chose the
  salted derivation, the salt is supplied HERE and only here);
- evaluates every arm/seed on protected EXACTLY ONCE (one pass, no retry);
- computes the Claim-A probe INSIDE the same pass (no extra protected read);
- computes B0/B1 surface baselines on protected inside the same pass;
- writes RAW_GATE1_RESULTS.json in the frozen schema (RAW_GATE1_RESULTS.schema.json)
  with the passage_order_digest binding every arm to the same frozen order;
- after this pass the protected split is BURNED (burned-split law).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    from exec.gpu_guard import require_gpu
    from exec.arms import ARM_IDS, build_arm_head
    from exec.dataset_assembly import assemble_examples
    from exec.baselines import score_split
except ImportError:
    from gpu_guard import require_gpu
    from arms import ARM_IDS, build_arm_head
    from dataset_assembly import assemble_examples
    from baselines import score_split

SEEDS = (11, 23, 47)
PROBE_STEPS, PROBE_LR, PROBE_WD = 1000, 1.0e-3, 0.01


def regenerate_protected(package_root: Path, protected_salt_hex: str = None):
    """In-memory protected records via the frozen generator machinery + the
    digest-equality gate against the pre-registered manifest value."""
    sys.path.insert(0, str(package_root / "tools"))
    sys.path.insert(0, str(package_root))
    import generate_construction_gold as gen
    from exec.prng import HashPRNG
    from independent_roundtrip_checker import check_record
    seed = gen.GATE1A_SEED
    if protected_salt_hex is not None:
        rng = HashPRNG(f"CONSTRUCTION_GOLD_PROTECTED|{seed}|{protected_salt_hex}")
    else:                                # status quo: replay the full public stream
        rng = HashPRNG(f"CONSTRUCTION_GOLD|{seed}")
        for split in ("train", "val"):   # consume the stream exactly as generation did
            _consume_split(gen, rng, split)
    records = _consume_split(gen, rng, "protected")
    body = "\n".join(gen.canonical_line(r) for r in records) + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    manifest = json.loads(
        (package_root / "DATASET_MANIFEST_CANDIDATE.json").read_text("utf-8"))
    pinned = manifest["splits"]["protected"]["content_sha256"]
    if digest != pinned:
        raise RuntimeError(f"DATASET_INTEGRITY_FAILURE: protected regenerated "
                           f"{digest} != pre-registered {pinned}")
    for rec in records:
        ok, reason = check_record(rec)
        if not ok:
            raise RuntimeError(f"DATASET_INTEGRITY_FAILURE: {rec['passage_id']} {reason}")
    return records


def _consume_split(gen, rng, split):
    records, idx, qcycle = [], 0, 0
    while len(records) < gen.SIZES[split]:
        rec = gen.build_passage(rng, split, idx, gen.QTYPES[qcycle % len(gen.QTYPES)])
        idx += 1
        if rec is None:
            continue
        from independent_roundtrip_checker import check_record
        ok, _ = check_record(rec)
        if ok:
            records.append(rec)
            qcycle += 1
    return records


def passage_order_digest(ids) -> str:
    return hashlib.sha256(
        json.dumps(list(ids), separators=(",", ":")).encode("utf-8")).hexdigest()


def claim_a_probe(h_train, y_train, h_protected, y_protected, seed: int):
    """4-way multinomial logistic probe on cached h_i (frozen: AdamW, 1000
    full-batch steps, lr 1e-3, weight_decay 0.01). Returns protected accuracy."""
    import torch
    torch.manual_seed(seed)
    probe = torch.nn.Linear(h_train.shape[1], 4)
    opt = torch.optim.AdamW(probe.parameters(), lr=PROBE_LR, weight_decay=PROBE_WD)
    loss_fn = torch.nn.CrossEntropyLoss()
    for _ in range(PROBE_STEPS):
        opt.zero_grad(set_to_none=True)
        loss_fn(probe(h_train), y_train).backward()
        opt.step()
    with torch.no_grad():
        pred = probe(h_protected).argmax(dim=1)
    return float((pred == y_protected).float().mean())


def run_protected_evaluation(package_root: Path, run_receipts: list,
                             evaluate_arm_seed, claim_a_inputs,
                             surface_baselines_trainval: dict,
                             out_path: Path, protected_salt_hex: str = None):
    """The one protected pass. evaluate_arm_seed(arm, seed, records) -> [0/1]*1000
    (the caller wires cached activations + trained heads in); claim_a_inputs
    supplies the probe tensors; surface_baselines_trainval carries the step-2b
    B0/B1 results for train and val. Writes the frozen raw-results file."""
    require_gpu()                                       # FIRST -- fail closed
    if len(run_receipts) != 25:
        raise RuntimeError(f"PROTECTED_REFUSED: {len(run_receipts)}/25 training "
                           "receipts present; protected runs only after ALL runs")
    records = regenerate_protected(package_root, protected_salt_hex)
    ids = [r["passage_id"] for r in records]
    order_digest = passage_order_digest(ids)
    arms = {}
    for arm in ARM_IDS:
        per_seed = {}
        for seed in SEEDS:
            vec = evaluate_arm_seed(arm, seed, records)
            if len(vec) != len(ids) or any(v not in (0, 1) for v in vec):
                raise RuntimeError(f"EVAL_OUTPUT_INVALID: {arm}/{seed}")
            per_seed[str(seed)] = list(vec)
        arms[arm] = {"per_seed_correct": per_seed,
                     "passage_order_digest": order_digest}
    probe_acc = claim_a_probe(*claim_a_inputs["gold"])
    shuf_acc = claim_a_probe(*claim_a_inputs["shuffled"])
    results = {
        "schema": "RAW_GATE1_RESULTS_v1",
        "protected_passage_ids": ids,
        "arms": arms,
        "claim_a": {"probe_protected_accuracy": probe_acc,
                    "shuffled_control_accuracy": shuf_acc},
        "surface_baselines": {
            "train": surface_baselines_trainval["train"],
            "val": surface_baselines_trainval["val"],
            "protected": {"B0": score_split(records, "B0"),
                          "B1": score_split(records, "B1")}},
    }
    out_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8",
                        newline="\n")
    return results
