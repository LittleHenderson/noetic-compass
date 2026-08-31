"""protected_eval.py -- the SINGLE protected evaluation pass (GATE 1A.2 rebuild).

v2 (section 6+7): the arbitrary evaluate_arm_seed callback is REMOVED. This
entry accepts only DATA (records, digest-pinned feature maps, digest-bound
checkpoint paths, validated receipts); every executable step -- prediction,
scoring, the Claim-A probe, baselines -- is the committed code in
exec/protected_scoring.py, exec/baselines.py, and this module. The one-use
protected lock (exec/protected_lock.py) is claimed atomically before the first
protected record is touched and BURNED on success, failure, or interruption.

Laws enforced here:
- REAL mode: require_gpu() is the first statement (no CPU fallback);
  SYNTHETIC_CONFORMANCE runs on CPU and is permanently non-claim-bearing;
- the receipt set must already have passed the schedule validator; every
  checkpoint is digest-verified against its receipt before it predicts;
- protected ids must be 1000, unique, strictly ascending, pattern p######;
- one pass: every (arm, seed) scores every protected passage exactly once;
- the Claim-A probe runs INSIDE the same pass (no extra protected read);
- B0/B1 are computed on protected inside the same pass;
- the RAW results carry the COMPLETE evidence chain (section 10) and are
  written through the canonical writer; the lock burn binds their digest.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    from exec.gpu_guard import require_gpu
    from exec.baselines import score_split
    from exec.fsio import write_utf8_lf
    from exec.protected_scoring import (GoldScorer, build_prediction_input,
                                        load_checkpoint_head, predict_arm_seed)
    from exec.labels import CLASSES
except ImportError:
    from gpu_guard import require_gpu
    from baselines import score_split
    from fsio import write_utf8_lf
    from protected_scoring import (GoldScorer, build_prediction_input,
                                   load_checkpoint_head, predict_arm_seed)
    from labels import CLASSES

ARM_IDS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7")
PROBE_STEPS, PROBE_LR, PROBE_WD = 1000, 1.0e-3, 0.01


def regenerate_protected(package_root: Path, protected_salt_hex: str = None):
    """In-memory protected records via the frozen generator machinery + the
    digest-equality gate against the pre-registered manifest value."""
    sys.path.insert(0, str(package_root / "tools"))
    sys.path.insert(0, str(package_root))
    import generate_construction_gold as gen
    from independent_roundtrip_checker import check_record
    bodies, manifest = gen.generate_all(protected_salt_hex)
    records = [json.loads(x) for x in
               bodies["protected"].decode("utf-8").splitlines()]
    digest = hashlib.sha256(bodies["protected"]).hexdigest()
    frozen = json.loads(
        (package_root / "DATASET_MANIFEST_CANDIDATE.json").read_text("utf-8"))
    pinned = frozen["splits"]["protected"]["content_sha256"]
    if protected_salt_hex is None and digest != pinned:
        raise RuntimeError(f"DATASET_INTEGRITY_FAILURE: protected regenerated "
                           f"{digest} != pre-registered {pinned}")
    for rec in records:
        ok, reason = check_record(rec)
        if not ok:
            raise RuntimeError(
                f"DATASET_INTEGRITY_FAILURE: {rec['passage_id']} {reason}")
    return records, digest


def passage_order_digest(ids) -> str:
    return hashlib.sha256(
        json.dumps(list(ids), separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_protected_ids(ids):
    if len(ids) != 1000 or len(set(ids)) != 1000:
        raise RuntimeError("PROTECTED_IDS_INVALID: need exactly 1000 unique ids")
    import re
    if not all(re.match(r"^p[0-9]{6}$", i) for i in ids):
        raise RuntimeError("PROTECTED_IDS_INVALID: id pattern violation")
    if ids != sorted(ids):
        raise RuntimeError("PROTECTED_IDS_INVALID: ids not in ascending order")


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


def _idea_tensors(records, features):
    """Stack per-Idea hidden states + gold class indices for the Claim-A probe
    (committed preprocessing; the probe is a registered diagnostic)."""
    import torch
    hs, ys = [], []
    for r in records:
        f = features[r["passage_id"]]
        for i, cls in enumerate(r["idea_labels"]):
            hs.append(f["h"][i].float())
            ys.append(CLASSES.index(cls))
    return torch.stack(hs), torch.tensor(ys)


def _shuffled_labels(records):
    from exec.labels import s5_random_label
    import torch
    ys = []
    for r in records:
        for i in range(len(r["idea_labels"])):
            ys.append(CLASSES.index(s5_random_label(r["passage_id"], i)))
    return torch.tensor(ys)


def run_protected_evaluation(package_root: Path, mode: str, *,
                             campaign_id: str,
                             protected_records: list, protected_features: dict,
                             train_records: list, train_features: dict,
                             checkpoints: dict, receipts_by_key: dict,
                             widths: dict, verb_to_class: dict, seeds: list,
                             lock,
                             surface_baselines_trainval: dict,
                             evidence_chain: dict, out_path: Path) -> dict:
    """The one protected pass. ALL arguments are data; every executable step is
    committed code. Claim-order law (adversarial-review fix): the DRIVER claims
    the one-use lock atomically BEFORE regenerating or featurizing any protected
    record; this entry refuses to run unless the lock is already in
    PROTECTED_RUNNING for this campaign, and burns it on every outcome."""
    if mode == "REAL":
        require_gpu()                                  # FIRST -- fail closed
    elif mode != "SYNTHETIC_CONFORMANCE":
        raise RuntimeError(f"unknown mode {mode!r}")
    ids = [r["passage_id"] for r in protected_records]
    validate_protected_ids(ids)
    order_digest = passage_order_digest(ids)
    if lock.state(campaign_id) != "PROTECTED_RUNNING":
        raise RuntimeError(
            f"PROTECTED_LOCK_NOT_CLAIMED: campaign {campaign_id} is in "
            f"{lock.state(campaign_id)}; the driver must claim the one-use lock "
            "BEFORE any protected record is touched")
    try:
        arms = {}
        for arm in ARM_IDS:
            inputs = [build_prediction_input(r, arm, verb_to_class)
                      for r in protected_records]
            per_seed = {}
            for seed in seeds:
                key = (arm, seed)
                receipt = receipts_by_key[key]
                head = load_checkpoint_head(
                    arm, widths[arm], checkpoints[key],
                    receipt["checkpoint_sha256"])      # digest-verified
                preds = predict_arm_seed(head, inputs, protected_features)
                scorer = GoldScorer(protected_records)
                vec = [scorer.score(pid, preds[pid], arm, seed,
                                    receipt["checkpoint_sha256"])
                       for pid in ids]
                per_seed[str(seed)] = vec
            arms[arm] = {"per_seed_correct": per_seed,
                         "passage_order_digest": order_digest}
        h_tr, y_tr = _idea_tensors(train_records, train_features)
        h_pr, y_pr = _idea_tensors(protected_records, protected_features)
        probe_acc = claim_a_probe(h_tr, y_tr, h_pr, y_pr, seed=11)
        shuf_acc = claim_a_probe(h_tr, _shuffled_labels(train_records),
                                 h_pr, y_pr, seed=23)
        results = {
            "schema": "RAW_GATE1_RESULTS_v2",
            "evidence_chain": dict(evidence_chain),
            "protected_passage_ids": ids,
            "arms": arms,
            "claim_a": {"probe_protected_accuracy": probe_acc,
                        "shuffled_control_accuracy": shuf_acc},
            "surface_baselines": {
                "train": surface_baselines_trainval["train"],
                "val": surface_baselines_trainval["val"],
                "protected": {"B0": score_split(protected_records, "B0"),
                              "B1": score_split(protected_records, "B1")}},
        }
        text = json.dumps(results, indent=2) + "\n"
        write_utf8_lf(out_path, text)
        results_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        burn = lock.burn(campaign_id, final_state_reason="SUCCESS",
                         result_or_failure_sha256=results_sha)
        return {"results": results, "results_sha256": results_sha,
                "lock_receipt": burn}
    except BaseException as exc:
        failure_sha = hashlib.sha256(
            f"{type(exc).__name__}: {exc}".encode("utf-8")).hexdigest()
        try:
            lock.burn(campaign_id,
                      final_state_reason=f"FAILURE:{type(exc).__name__}",
                      result_or_failure_sha256=failure_sha)
        finally:
            pass
        raise
