"""`definition_anchored_prototype_readout_v1` — the concept-construction mechanism.

This is the fix for the defect that made Gate 2 item 4 a NON-EXPERIMENT. The
existing `evaluate_stage9_elements_pilot.py` trains a probe on hidden states
against integer labels; the definition text never enters it, so running it six
times returns six identical numbers. Verified: grep for
`definition|gloss_text|def_text` in that file returns zero.

Implemented EXACTLY as frozen in GATE2_ITEM4_PREREGISTRATION.md section 2.0
(`required_run_bindings[17]`). Nothing here is improvised; where the
pre-registration forbids something, the code refuses it rather than trusting a
caller to remember.

    Step 1  anchor pass. For arm a and class code c, take ONLY the definition
            BODY. `code` and `title` are DISCARDED -- titles are byte-identical
            between Arm A and Arm B on 0/40 elements, so including them would
            inject a constant that dilutes the treatment and hand every TKS arm
            a shared cue Arm E cannot have. Render into K=4 frozen frames, one
            short forward pass each, body starting at position 0. Read at the
            final token of the constant trailing scaffold. Average over frames.
    Step 2  item pass. The bank's `english` string through the SAME four frames,
            same read position. Computed ONCE and shared byte-identically by
            every arm -- no arm's text ever enters an item pass.
    Step 3  centering. u = l2norm(a_c - mean over the 40 classes of a);
            v = l2norm(b_i - mean over CALIBRATION items of b).
    Step 4  readout. argmax_c cos(v_i, u_c). ZERO fitted parameters.

WHAT VARIES ACROSS ARMS: exactly the 40 definition body strings in Step 1. The
arm label enters this module only as a path to a JSON file of strings.

WHAT THIS MODULE WILL NOT DO, per the pre-registration:
  * no classifier, ridge, or logistic regression -- an argmax over cosines has
    no parameters that could be tuned per arm;
  * no per-arm whitening or per-arm shrinkage. The optional whitened diagnostic
    uses a SINGLE shared shrinkage of 0.1 with covariance fitted on the pooled
    union of calibration items and all arms' anchors, so the transform is
    byte-identical for every arm. A per-arm Ledoit-Wolf shrinkage would be an
    arm-varying hyperparameter masquerading as a hold-constant, and is refused;
  * no use of the contaminated fixture whose 816/816 rows embed Arm B's
    definition verbatim -- Arm B would win by string match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

# Frozen in the pre-registration and hashed into required_run_bindings[19].
# Frame text carries NO ontology vocabulary: no code, no title, no domain word,
# no register word -- so no frame can favour one arm's vocabulary.
FRAMES: tuple[str, ...] = (
    "Definition: {body}\nThat role describes:",
    "The following describes one role.\n{body}\nThat role describes:",
    "Consider this description.\n{body}\nThat role describes:",
    "Description: {body}\nThat role describes:",
)
READ_SCAFFOLD = "That role describes:"
SHARED_WHITEN_SHRINKAGE = 0.1

# `encode(texts) -> (n_texts, dim)`: one short forward pass per text, reading
# residual_post at the pinned layer at the FINAL TOKEN of READ_SCAFFOLD.
EncodeFn = Callable[[Sequence[str]], np.ndarray]


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n < 1e-12, 1.0, n)


def frame_texts(bodies: Sequence[str]) -> list[str]:
    """Every body rendered into all K frames, in frozen order."""
    return [f.format(body=b) for b in bodies for f in FRAMES]


def _encode_framed(encode: EncodeFn, bodies: Sequence[str]) -> np.ndarray:
    """Encode through all frames and average -> (n_bodies, dim)."""
    flat = encode(frame_texts(bodies))
    flat = np.asarray(flat, dtype=np.float64)
    k = len(FRAMES)
    if flat.shape[0] != len(bodies) * k:
        raise ValueError(f"encode returned {flat.shape[0]} rows; expected {len(bodies) * k}")
    return flat.reshape(len(bodies), k, -1).mean(axis=1)


@dataclass(frozen=True)
class ArmReadout:
    arm_id: str
    class_codes: tuple[str, ...]
    u: np.ndarray            # (n_classes, dim) centered + l2-normalised anchors
    anchor_raw: np.ndarray   # (n_classes, dim) pre-centering, for auditing


def build_arm_anchors(*, arm_id: str, definitions: dict[str, str], encode: EncodeFn) -> ArmReadout:
    """Step 1 + the anchor half of Step 3. `definitions` maps class code -> BODY."""
    if not definitions:
        raise ValueError("arm has no definitions")
    codes = tuple(sorted(definitions))
    bodies = [definitions[c] for c in codes]
    if any(not str(b).strip() for b in bodies):
        raise ValueError(f"arm {arm_id} has an empty definition body")
    a = _encode_framed(encode, bodies)
    # Arm-INTERNAL class centering: removes what is constant across this arm
    # (its voice, register, mean length). Domain-block style and per-class length
    # SURVIVE this -- see pre-registration 3.3; the equal-budget replicate and F5
    # are the instruments for that residual, not this step.
    u = _l2(a - a.mean(axis=0, keepdims=True))
    return ArmReadout(arm_id=arm_id, class_codes=codes, u=u, anchor_raw=a)


def build_item_states(
    *, items: Sequence[str], calibration_mask: np.ndarray, encode: EncodeFn
) -> np.ndarray:
    """Step 2 + the item half of Step 3. ARM-INDEPENDENT: compute once, share.

    The calibration mean is label-free, so no label information reaches the
    centering, and it is identical for every arm by construction.
    """
    calibration_mask = np.asarray(calibration_mask, dtype=bool)
    if calibration_mask.shape[0] != len(items):
        raise ValueError("calibration_mask length must match items")
    if not calibration_mask.any():
        raise ValueError("need at least one calibration item for the item mean")
    b = _encode_framed(encode, items)
    return _l2(b - b[calibration_mask].mean(axis=0, keepdims=True))


def predict(*, v: np.ndarray, arm: ArmReadout) -> np.ndarray:
    """Step 4 — argmax over cosine. No fitted parameter can change this."""
    sims = np.asarray(v, dtype=np.float64) @ arm.u.T   # both sides l2-normalised
    return np.array([arm.class_codes[i] for i in sims.argmax(axis=1)], dtype=str)


def macro_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=str)
    y_pred = np.asarray(y_pred, dtype=str)
    per = [float((y_pred[y_true == c] == c).mean()) for c in sorted(set(y_true.tolist()))]
    return float(np.mean(per)) if per else 0.0


def shared_whitening(*, calibration_states: np.ndarray, all_arm_anchors: Sequence[np.ndarray]) -> np.ndarray:
    """SECONDARY, NON-GATING diagnostic. One shared transform for every arm.

    Covariance is fitted on the pooled union of calibration items and EVERY
    arm's anchors, with a single shared shrinkage, so the transform cannot
    advantage one arm. Per-arm shrinkage is forbidden by the pre-registration.
    """
    pooled = np.vstack([np.asarray(calibration_states, dtype=np.float64)]
                       + [np.asarray(a, dtype=np.float64) for a in all_arm_anchors])
    pooled = pooled - pooled.mean(axis=0, keepdims=True)
    cov = np.cov(pooled, rowvar=False)
    cov = (1.0 - SHARED_WHITEN_SHRINKAGE) * cov + SHARED_WHITEN_SHRINKAGE * np.eye(cov.shape[0]) * np.trace(cov) / cov.shape[0]
    vals, vecs = np.linalg.eigh(cov)
    return vecs @ np.diag(1.0 / np.sqrt(np.maximum(vals, 1e-10))) @ vecs.T


def score_arm(
    *, arm_id: str, definitions: dict[str, str], items: Sequence[str],
    labels: np.ndarray, calibration_mask: np.ndarray, item_states: np.ndarray,
    encode: EncodeFn, evaluate_mask: np.ndarray | None = None,
) -> dict:
    """Full readout for one arm against SHARED item states."""
    arm = build_arm_anchors(arm_id=arm_id, definitions=definitions, encode=encode)
    labels = np.asarray(labels, dtype=str)
    mask = np.asarray(evaluate_mask, dtype=bool) if evaluate_mask is not None else ~np.asarray(calibration_mask, dtype=bool)
    pred = predict(v=item_states[mask], arm=arm)
    return {
        "arm_id": arm_id,
        "n_classes": len(arm.class_codes),
        "n_evaluated": int(mask.sum()),
        "chance": round(1.0 / len(arm.class_codes), 6),
        "macro_accuracy": round(macro_accuracy(labels[mask], pred), 6),
        "fitted_parameters": 0,
        "note": "argmax over cosine; the only per-arm scalar anywhere is a softmax temperature used for ECE only, which is monotone and cannot change a prediction",
    }
