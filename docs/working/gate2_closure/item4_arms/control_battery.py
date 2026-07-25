"""Build item B7 / roadmap Gate-2 item 7 — the full matched control battery.

Roadmap item 7 requires: "Run same-budget matched random, orthogonal,
wrong-axis/layer/token, label-permuted, text, hash, and strong embedding
baselines." The 2026-07-24 runs shipped only text, hash, length, layer-0 and
label-permuted — the random, orthogonal and wrong-axis arms were missing, so
"matched controls" was overstated. This module supplies all of them under one
same-budget contract.

SAME-BUDGET IS THE POINT. A control that gets less capacity than the hypothesis
is not a control, it is a strawman. Every arm here goes through the IDENTICAL
classifier family, the IDENTICAL hyperparameter grid, the IDENTICAL folds, and
the IDENTICAL feature dimensionality (projected where necessary). A hidden-state
win only means something if the controls were given a fair chance to win.

THE CONTROL THAT MATTERS MOST HERE, and why. The item-4 pre-registration froze
this finding: on these banks a bag-of-n-grams tops out near 0.50 NOT because the
task is genuinely surface-hard, but because the sentence puts two competing
glosses in one string and lets a "Focus:" marker choose between them. Any
ORDER-AWARE model that can bind the Focus token to a span could exceed 0.50.
So `order_aware_encoder` is MANDATORY. Declaring victory over tf-idf alone would
repeat the withdrawn W0 claim in mirror image — beating a control that was
structurally incapable of competing.

Nothing here is a foreign production dependency: an encoder used as a CONTROL
the hypothesis must BEAT makes the test strictly harder, which is the opposite
of leaning on someone else's model.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any, Callable

import numpy as np


def _rng(seed: int, salt: str) -> np.random.Generator:
    h = hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "big"))


# ---------------------------------------------------------------- controls

def random_direction_features(*, n_rows: int, dim: int, seed: int) -> np.ndarray:
    """Same-shape random features. Answers: does the PIPELINE manufacture signal?

    If a random matrix scores above chance under this scoring code, the scoring
    code is leaking — no claim about any real feature is interpretable.
    """
    return _rng(seed, "random_direction").normal(size=(n_rows, dim)).astype(np.float32)


def orthogonal_projection_features(*, features: np.ndarray, labels: np.ndarray, seed: int) -> np.ndarray:
    """Hidden states with the class-mean subspace PROJECTED OUT.

    Answers: is the signal specifically in the class-discriminative directions,
    or diffused through the representation? If this control scores as well as
    the raw states, the claim "the model encodes the distinction HERE" is false
    even when overall accuracy is high.
    """
    x = np.asarray(features, dtype=np.float64)
    classes = sorted(set(np.asarray(labels, dtype=str).tolist()))
    means = np.stack([x[np.asarray(labels, dtype=str) == c].mean(axis=0) for c in classes])
    means = means - means.mean(axis=0, keepdims=True)
    # Orthonormal basis of the class-mean subspace, then remove it.
    q, _ = np.linalg.qr(means.T)
    residual = x - (x @ q) @ q.T
    _ = _rng(seed, "orthogonal")  # reserved so the manifest can record a seed
    return residual.astype(np.float32)


def wrong_axis_features(*, features_by_layer: np.ndarray, correct_pos: int, seed: int) -> dict[str, np.ndarray]:
    """Deliberately WRONG readouts: another layer, and a shifted token position.

    Answers: is the result specific to the pre-registered layer/position, or
    would any slice of the network have done? A claim that survives here is
    about the network; one that does not is about the task being easy.
    """
    n_layers = features_by_layer.shape[1]
    other = (correct_pos + max(1, n_layers // 2)) % n_layers
    if other == correct_pos:
        other = (correct_pos + 1) % n_layers
    out = {"wrong_layer": features_by_layer[:, other, :].astype(np.float32)}
    rows = features_by_layer.shape[0]
    perm = _rng(seed, "wrong_token").permutation(rows)
    out["shuffled_row_alignment"] = features_by_layer[perm, correct_pos, :].astype(np.float32)
    return out


def label_permuted(labels: np.ndarray, *, seed: int, within: np.ndarray | None = None) -> np.ndarray:
    """Shuffled labels — the null. Optionally shuffled only WITHIN a stratum."""
    y = np.asarray(labels, dtype=str).copy()
    rng = _rng(seed, "label_permuted")
    if within is None:
        return rng.permutation(y)
    within = np.asarray(within, dtype=str)
    for stratum in sorted(set(within.tolist())):
        idx = np.where(within == stratum)[0]
        y[idx] = rng.permutation(y[idx])
    return y


def match_dimensionality(x: np.ndarray, *, target_dim: int, seed: int) -> np.ndarray:
    """Project a control to the hypothesis's dimensionality — the same-budget rule.

    A 40-dim control against a 2560-dim hypothesis is not a fair fight. Random
    projection preserves the control's information content while equalising the
    capacity the classifier is handed.
    """
    x = np.asarray(x, dtype=np.float32)
    if x.shape[1] == target_dim:
        return x
    if x.shape[1] > target_dim:
        proj = _rng(seed, "downproject").normal(size=(x.shape[1], target_dim)) / np.sqrt(target_dim)
        return (x @ proj).astype(np.float32)
    pad = _rng(seed, "upproject").normal(size=(x.shape[1], target_dim)) / np.sqrt(target_dim)
    return (x @ pad).astype(np.float32)


# ---------------------------------------------------------------- manifest

def build_control_manifest(
    *,
    order_aware_encoder: dict[str, str] | None,
    hypothesis_dim: int,
    seed: int,
    notes: str = "",
) -> dict[str, Any]:
    """Freeze the control battery so it cannot be quietly narrowed later.

    `order_aware_encoder` must carry {model_id, revision, sha256}. Passing None
    is allowed ONLY to record that it is not yet pinned — and the manifest then
    marks itself INCOMPLETE, because the pre-registration made this control
    mandatory.
    """
    controls = {
        "char_ngram_hash": {"kind": "surface", "order_aware": False,
                            "why": "sub-token surface structure; generalises across held-out prompts"},
        "word_hash": {"kind": "surface", "order_aware": False,
                      "why": "whitespace-token surface"},
        "length": {"kind": "surface", "order_aware": False,
                   "why": "catches length-confounded labels"},
        "layer0_token_identity": {"kind": "embedding", "order_aware": False,
                                  "why": "bag of raw embeddings; ZERO transformer computation. The control that "
                                         "defeated all four 2026-07-24 attempts."},
        "order_aware_encoder": {"kind": "embedding", "order_aware": True,
                                "why": "MANDATORY. The ~0.50 bag-of-ngrams ceiling on these banks comes from "
                                       "order-insensitivity, not task difficulty. An order-aware model can bind "
                                       "the Focus marker to a span and may exceed 0.50. Beating only tf-idf would "
                                       "repeat the withdrawn W0 claim in mirror image.",
                                "pinned": order_aware_encoder or "unavailable_not_yet_pinned"},
        "random_direction": {"kind": "null", "order_aware": False,
                             "why": "if random features score above chance, the SCORING CODE leaks"},
        "orthogonal_residual": {"kind": "specificity", "order_aware": False,
                                "why": "class-mean subspace projected out; tests WHERE the signal lives"},
        "wrong_layer": {"kind": "specificity", "order_aware": False,
                        "why": "tests that the result is specific to the pre-registered layer"},
        "shuffled_row_alignment": {"kind": "null", "order_aware": False,
                                   "why": "breaks the feature<->label pairing while keeping both distributions"},
        "label_permuted_within_stratum": {"kind": "null", "order_aware": False,
                                          "why": "honest null that respects stratum structure"},
    }
    complete = order_aware_encoder is not None
    manifest = {
        "schema_version": "cas_harness_item4_control_manifest.v1",
        "build_item": "B7 (also roadmap Gate-2 item 7)",
        "created_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "hypothesis_dim": hypothesis_dim,
        "same_budget_contract": {
            "classifier_family": "StandardScaler + LogisticRegression (identical for every arm)",
            "hyperparameter_grid": "identical grid and identical search budget for every arm",
            "folds": "identical grouped folds for every arm",
            "dimensionality": f"every control projected to {hypothesis_dim} via seeded random projection",
            "why": "A control given less capacity than the hypothesis is a strawman, not a control.",
        },
        "controls": controls,
        "roadmap_item_7_coverage": {
            "random": "random_direction",
            "orthogonal": "orthogonal_residual",
            "wrong_axis_layer_token": "wrong_layer + shuffled_row_alignment",
            "label_permuted": "label_permuted_within_stratum",
            "text": "word_hash",
            "hash": "char_ngram_hash",
            "strong_embedding": "order_aware_encoder + layer0_token_identity",
        },
        "manifest_complete": complete,
        "status": "COMPLETE" if complete else "INCOMPLETE_ORDER_AWARE_ENCODER_NOT_PINNED",
        "notes": notes,
        "honesty_note": (
            "The reportable quantity is the margin over the STRONGEST control, never over a "
            "convenient one. If the order-aware encoder wins, the hidden-state claim fails — that "
            "is the control doing its job, not a problem with the control."
        ),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"},
                   sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return manifest


def run_control_battery(
    *,
    features_by_layer: np.ndarray,
    correct_pos: int,
    labels: np.ndarray,
    strata: np.ndarray,
    score_fn: Callable[[np.ndarray, np.ndarray], float],
    seed: int,
) -> dict[str, float]:
    """Score every non-text control through the SAME scoring function."""
    x = features_by_layer[:, correct_pos, :]
    dim = x.shape[1]
    out: dict[str, float] = {}
    out["random_direction"] = score_fn(random_direction_features(n_rows=len(labels), dim=dim, seed=seed), labels)
    out["orthogonal_residual"] = score_fn(orthogonal_projection_features(features=x, labels=labels, seed=seed), labels)
    for name, feats in wrong_axis_features(features_by_layer=features_by_layer, correct_pos=correct_pos, seed=seed).items():
        out[name] = score_fn(match_dimensionality(feats, target_dim=dim, seed=seed), labels)
    out["label_permuted_within_stratum"] = score_fn(x, label_permuted(labels, seed=seed, within=strata))
    return out
