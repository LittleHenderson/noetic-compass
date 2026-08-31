"""protected_scoring.py -- the ONE committed protected scoring path (GATE 1A.2 s.6).

There is no evaluate_arm_seed callback, no caller-provided correctness vector,
and no caller-provided Claim-A tensor anywhere in the protected phase. The
model-facing prediction object carries ONLY: passage id, passage text, question
text, question type, clause texts, candidate strings, candidate count, and the
arm-specific auxiliary profile tensor (for S2-S7, construction-gold labels are
converted by the committed preprocessing in exec/labels.py into the registered
profile vectors -- the RAW labels never reach the predictor). It never carries:
answer, answer index, seed_trace, or raw idea_labels.

A separate deterministic GoldScorer holds the gold answer table; it receives
only (passage_id, predicted_candidate_index, arm, seed, checkpoint_sha256),
computes correctness AFTER prediction, and cannot modify predictions (it reads
integers; it returns a fresh provenance record).
"""
from __future__ import annotations

try:
    from exec.labels import profile_vectors
    from exec.arms import ARM_STRUCT, MAX_IDEAS, build_arm_head
except ImportError:
    from labels import profile_vectors
    from arms import ARM_STRUCT, MAX_IDEAS, build_arm_head

PREDICTION_ALLOWED_KEYS = frozenset(
    ["passage_id", "text", "question", "question_type", "clauses",
     "candidates", "n_ideas", "profiles"])
PREDICTION_FORBIDDEN_KEYS = frozenset(
    ["answer", "answer_index", "seed_trace", "idea_labels"])


class ScoringViolation(RuntimeError):
    pass


def build_prediction_input(record: dict, arm_id: str, verb_to_class=None) -> dict:
    """The committed model-facing object. Gold classes are consumed HERE (by the
    committed preprocessing) to produce the registered auxiliary profile tensor;
    they never appear in the output."""
    ex = {"passage_id": record["passage_id"], "text": record["text"],
          "question": record["question"], "question_type": record["question_type"],
          "clauses": [c["text"] for c in record["clauses"]],
          "candidates": list(record["candidates"]),
          "n_ideas": len(record["clauses"]),
          "profiles": profile_vectors(arm_id, record, verb_to_class)}
    # typed raise, not a bare assert (asserts vanish under python -O; this law
    # must hold in every interpreter mode)
    leaked = set(ex) & PREDICTION_FORBIDDEN_KEYS
    if leaked or not set(ex) <= PREDICTION_ALLOWED_KEYS:
        raise ScoringViolation(f"GOLD_LEAK_REFUSED: prediction input carries "
                               f"{sorted(leaked) or sorted(set(ex) - PREDICTION_ALLOWED_KEYS)}")
    return ex


def predict_arm_seed(head, prediction_inputs, features):
    """Committed predictor: one argmax per passage over the masked candidate
    logits. features[passage_id] = {"h": (N,896), "g": (896,), "cand": (C,896)}.
    Returns {passage_id: predicted_candidate_index}."""
    import torch
    head = head.float().eval()
    out = {}
    with torch.no_grad():
        for ex in prediction_inputs:
            f = features[ex["passage_id"]]
            n, c = f["h"].shape[0], f["cand"].shape[0]
            h = torch.zeros(1, MAX_IDEAS, f["h"].shape[1])
            h[0, :n] = f["h"].float()
            idea_mask = torch.zeros(1, MAX_IDEAS, dtype=torch.bool)
            idea_mask[0, :n] = True
            p = None
            if ex["profiles"] is not None:
                p = torch.zeros(1, MAX_IDEAS, 4)
                p[0, :n] = torch.tensor(ex["profiles"], dtype=torch.float32)
            cand_enc = f["cand"].float().unsqueeze(0)
            cand_mask = torch.ones(1, c, dtype=torch.bool)
            logits = head(h, f["g"].float().unsqueeze(0), p, idea_mask,
                          cand_enc, cand_mask)
            out[ex["passage_id"]] = int(logits[0].argmax())
    return out


class GoldScorer:
    """Holds the gold table; computes correctness AFTER prediction; append-only
    provenance. It receives prediction INTEGERS, never tensors or records, so
    it cannot modify predictions."""

    def __init__(self, records):
        self._gold = {r["passage_id"]: r["candidates"].index(r["answer"])
                      for r in records}
        self.provenance = []

    def score(self, passage_id: str, predicted_candidate_index: int,
              arm: str, seed: int, checkpoint_sha256: str) -> int:
        if passage_id not in self._gold:
            raise ScoringViolation(f"unknown passage {passage_id!r}")
        if type(predicted_candidate_index) is not int:
            raise ScoringViolation("prediction must be an integer candidate index")
        if not isinstance(checkpoint_sha256, str) or len(checkpoint_sha256) != 64:
            raise ScoringViolation(
                "CHECKPOINT_PROVENANCE_MISSING: every scored prediction must "
                "name the 64-hex checkpoint digest it came from")
        correct = 1 if predicted_candidate_index == self._gold[passage_id] else 0
        self.provenance.append(
            {"passage_id": passage_id, "arm": arm, "seed": seed,
             "checkpoint_sha256": checkpoint_sha256,
             "predicted_candidate_index": predicted_candidate_index,
             "correct": correct})
        return correct


def load_checkpoint_head(arm_id: str, widen_w: int, checkpoint_path,
                         expected_sha256: str):
    """Digest-verified checkpoint loading: the state dict must hash to the
    receipt-bound value before it can predict anything."""
    import hashlib
    from pathlib import Path
    import torch
    raw = Path(checkpoint_path).read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha256:
        raise ScoringViolation(
            f"CHECKPOINT_DIGEST_MISMATCH: {checkpoint_path} sha {got} != "
            f"receipt {expected_sha256}")
    head = build_arm_head(arm_id, widen_w)
    head.load_state_dict(torch.load(checkpoint_path, map_location="cpu",
                                    weights_only=True))
    return head
