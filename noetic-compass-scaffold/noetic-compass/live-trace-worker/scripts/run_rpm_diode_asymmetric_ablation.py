#!/usr/bin/env python3
r"""RPM / diode asymmetric (directional) cross-ablation knockout test.

This is the sibling of ``run_stage9_40e_subspace_ablation.py`` that the
CAS-PCBA CJT/RPM assessment (docs/working/cas_harness_cjt_rpm_assessment_20260630.md)
identified as the one missing primitive. It differs from the Stage 9 runner in
exactly the three ways the assessment requires:

  1. TWO probes (a W / prerequisite probe and a P / dependent probe) over the
     SAME hidden states, instead of one fused operator|domain probe.
  2. CROSS-LABEL measurement with the readout HELD FIXED -- ablate the W
     subspace, then score the *unchanged* P probe (no retrain). The Stage 9
     runner re-fits the readout on the ablated states, which measures subspace
     RECOVERABILITY; this measures a genuine causal KNOCKOUT.
  3. A two-leg asymmetry verdict (W->P collapse AND P->W survival) plus a
     SUBSUMPTION control: a directional collapse at the pure-linear-ablation
     level is geometrically identical to "P lies inside span(W)", so a
     directional pattern with high subspace containment is reported as GREY,
     not as a validated prerequisite. This encodes the verifiers' sharpest
     objection as a guard rather than a caveat.

It is a diagnostic. It NEVER emits ACCEPT. Every verdict is ceilinged to
FLAG_FOR_HUMAN_REVIEW, and the whole run is gated behind a mandatory
surface-leakage screen status (the prior W0 attempt was BLOCKED_SURFACE_LEAKAGE).

Reserved-language claim ceiling: a PASS_DIRECTIONAL_PENDING_REVIEW licenses only
"on this open-weight model, at this layer, two CAS-typed directions show an
asymmetric ablation dependence consistent with -- not proof of -- a prerequisite
order; open-weight only; FLAG_FOR_HUMAN_REVIEW". It does NOT license "CAS Harness
detects/prevents/removes prompt injection internally" or "CJT/PCBA proves causal
control" (both NOT LICENSED).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

SCHEMA_VERSION = "cas_harness_rpm_diode_asymmetric_ablation.v1"
METHOD_LABEL = "RPM-DIODE-ASYMMETRIC-CROSS-ABLATION"
CLAIM_CEILING = "FLAG_FOR_HUMAN_REVIEW"  # CjtClaimCeiling has no ACCEPT by construction
SURFACE_SCREEN_READY = "READY_FOR_W0_CAPTURE"

# ----------------------------------------------------------------------------
# Helpers ported verbatim in contract from run_stage9_40e_subspace_ablation.py
# ----------------------------------------------------------------------------


def _build_linear_probe(C: float = 0.1, max_iter: int = 2000) -> Pipeline:
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(C=C, max_iter=max_iter, class_weight="balanced", solver="lbfgs"),
    )


def _fit_probe(X_train: np.ndarray, y_train: np.ndarray, *, C: float, max_iter: int) -> Pipeline:
    probe = _build_linear_probe(C=C, max_iter=max_iter)
    probe.fit(X_train, y_train)
    return probe


def _balanced_acc(probe: Pipeline, X: np.ndarray, y: np.ndarray) -> float:
    return float(balanced_accuracy_score(y, probe.predict(X)))


def _coef_subspace_basis(probe: Pipeline, *, tolerance: float = 1e-8) -> tuple[np.ndarray, int]:
    """Top numeric-rank right singular vectors of the (centered) logistic coef.

    Returned basis lives in the probe's STANDARDIZED hidden-state space, matching
    the Stage 9 runner so ablation can reuse the same scaler round-trip.
    """
    logistic = probe.named_steps["logisticregression"]
    coef = np.asarray(logistic.coef_, dtype=np.float64)
    coef_for_svd = coef - coef.mean(axis=0, keepdims=True) if coef.shape[0] > 1 else coef
    _, singular_values, vt = np.linalg.svd(coef_for_svd, full_matrices=False)
    numeric_rank = max(1, int((singular_values > tolerance).sum()))
    rank = min(numeric_rank, vt.shape[0])
    return vt[:rank].astype(np.float64, copy=True), rank


def _project_ablate_with_scaler(X: np.ndarray, *, scaler: StandardScaler, basis: np.ndarray) -> np.ndarray:
    X_scaled = scaler.transform(X)
    projected = X_scaled - (X_scaled @ basis.T) @ basis
    return scaler.inverse_transform(projected).astype(np.float64)


def _random_orthonormal_basis(rng: np.random.Generator, *, rank: int, dim: int) -> np.ndarray:
    raw = rng.normal(size=(dim, rank))
    q, _ = np.linalg.qr(raw, mode="reduced")
    return q.T.astype(np.float64)


def _group_split(labels_a: np.ndarray, labels_b: np.ndarray, groups: np.ndarray, *, test_size: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Group-aware split that keeps every class of BOTH labelings in the train
    fold and at least two classes of each in the test fold."""
    splitter = GroupShuffleSplit(n_splits=80, test_size=test_size, random_state=seed)
    all_a, all_b = set(labels_a.tolist()), set(labels_b.tolist())
    best: tuple[np.ndarray, np.ndarray] | None = None
    best_cov = -1
    for tr, te in splitter.split(labels_a, labels_a, groups=groups):
        cov = len(set(labels_a[tr].tolist())) + len(set(labels_b[tr].tolist()))
        if cov > best_cov:
            best, best_cov = (tr, te), cov
        if (
            set(labels_a[tr].tolist()) == all_a
            and set(labels_b[tr].tolist()) == all_b
            and len(set(labels_a[te].tolist())) >= 2
            and len(set(labels_b[te].tolist())) >= 2
        ):
            return tr, te
    if best is None:
        raise SystemExit("could not construct a group-aware train/test split")
    return best


# ----------------------------------------------------------------------------
# Subsumption control (the verifiers' load-bearing objection, made measurable)
# ----------------------------------------------------------------------------


def _raw_space_basis(probe: Pipeline, *, tolerance: float = 1e-8) -> np.ndarray:
    """Orthonormal basis of the probe's discriminative subspace in RAW hidden
    space (undo the scaler so two probes are comparable in one geometry)."""
    logistic = probe.named_steps["logisticregression"]
    scaler = probe.named_steps["standardscaler"]
    coef = np.asarray(logistic.coef_, dtype=np.float64)
    coef_for_svd = coef - coef.mean(axis=0, keepdims=True) if coef.shape[0] > 1 else coef
    raw = coef_for_svd / scaler.scale_[None, :]  # standardized-space dir -> raw-space dir
    q, r = np.linalg.qr(raw.T, mode="reduced")
    keep = np.abs(np.diag(r)) > tolerance
    if not keep.any():
        keep[0] = True
    return q[:, keep].T  # (rank, H) orthonormal rows in raw space


def _subspace_containment(B_outer: np.ndarray, B_inner: np.ndarray) -> float:
    """Fraction of span(B_inner) energy captured by span(B_outer) in [0, 1].

    ~1.0 means B_inner lies inside span(B_outer) -> ablating B_outer trivially
    destroys B_inner by geometric subsumption, NOT necessarily by prerequisite
    order. This is the confound a directional cross-ablation cannot, on its own,
    rule out at the linear level.
    """
    # singular values of (B_outer @ B_inner^T) are cosines of principal angles
    m = B_outer @ B_inner.T
    sv = np.linalg.svd(m, compute_uv=False)
    sv = np.clip(sv, 0.0, 1.0)
    return float(np.sum(sv**2) / B_inner.shape[0])


# ----------------------------------------------------------------------------
# One directional leg: ablate the SOURCE subspace, score the FIXED TARGET probe
# ----------------------------------------------------------------------------


def _leg(
    *,
    source_probe: Pipeline,
    target_probe: Pipeline,
    target_clean_ba: float,
    X_test: np.ndarray,
    y_target_test: np.ndarray,
    n_random: int,
    guard_margin: float,
    rng: np.random.Generator,
) -> dict[str, Any]:
    scaler = source_probe.named_steps["standardscaler"]
    basis, rank = _coef_subspace_basis(source_probe)

    X_ablated = _project_ablate_with_scaler(X_test, scaler=scaler, basis=basis)
    target_ablated_ba = _balanced_acc(target_probe, X_ablated, y_target_test)
    true_disruption = target_clean_ba - target_ablated_ba

    random_disruptions = []
    for _ in range(n_random):
        rbasis = _random_orthonormal_basis(rng, rank=rank, dim=X_test.shape[1])
        X_rand = _project_ablate_with_scaler(X_test, scaler=scaler, basis=rbasis)
        random_disruptions.append(target_clean_ba - _balanced_acc(target_probe, X_rand, y_target_test))
    random_max = float(np.max(random_disruptions)) if random_disruptions else 0.0
    margin_over_random = float(true_disruption - random_max)
    collapse = margin_over_random >= guard_margin

    return {
        "source_subspace_rank": int(rank),
        "target_clean_balanced_accuracy": float(target_clean_ba),
        "target_ablated_balanced_accuracy": float(target_ablated_ba),
        "true_disruption": float(true_disruption),
        "random_same_rank_max_disruption": random_max,
        "random_same_rank_mean_disruption": float(np.mean(random_disruptions)) if random_disruptions else 0.0,
        "margin_over_random_max": margin_over_random,
        "guard_margin": float(guard_margin),
        "collapse": bool(collapse),
        "readout_fixed_no_retrain": True,
    }


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def run_asymmetric_ablation(
    *,
    features: np.ndarray,
    layer_index: int,
    labels_W: np.ndarray,
    labels_P: np.ndarray,
    groups: np.ndarray,
    surface_screen_status: str,
    probe_C: float = 0.1,
    probe_max_iter: int = 2000,
    test_size: float = 0.25,
    n_random: int = 15,
    guard_margin: float = 0.05,
    readout_floor: float = 0.65,
    subsumption_threshold: float = 0.5,
    seed: int = 2026,
) -> dict[str, Any]:
    """Run the two-leg directional knockout. Returns a diagnostic report dict.

    W is the claimed prerequisite (anode); P is the claimed dependent (cathode).
    The directional claim under test: ablating W collapses P, ablating P spares W.
    """
    labels_W = np.asarray(labels_W)
    labels_P = np.asarray(labels_P)
    groups = np.asarray(groups)

    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "method_label": METHOD_LABEL,
        "claim_ceiling": CLAIM_CEILING,
        "packet_decision": "not_applicable_directional_ablation_diagnostic_only",
        "created_at": datetime.now(UTC).isoformat(),
        "layer_index": int(layer_index),
        "surface_screen_status": surface_screen_status,
        "important_limit": (
            "Directional cross-ablation diagnostic. Never an ACCEPT. A directional "
            "collapse at the linear level is geometrically identical to subspace "
            "containment; the subsumption control downgrades such results to GREY."
        ),
    }

    # Gate 0: mandatory surface-leakage preflight (the prior W0 FAIL discipline).
    if surface_screen_status != SURFACE_SCREEN_READY:
        return {**base, "verdict": "BLOCKED_SURFACE_LEAKAGE",
                "reason": f"surface_screen_status={surface_screen_status!r} != {SURFACE_SCREEN_READY!r}; "
                          "ablation refused until the surface-leakage screen passes."}

    X = np.asarray(features)[:, layer_index, :].astype(np.float64)
    tr, te = _group_split(labels_W, labels_P, groups, test_size=test_size, seed=seed)

    probe_W = _fit_probe(X[tr], labels_W[tr], C=probe_C, max_iter=probe_max_iter)
    probe_P = _fit_probe(X[tr], labels_P[tr], C=probe_C, max_iter=probe_max_iter)
    W_clean = _balanced_acc(probe_W, X[te], labels_W[te])
    P_clean = _balanced_acc(probe_P, X[te], labels_P[te])

    base["readout"] = {
        "W_clean_balanced_accuracy": W_clean,
        "P_clean_balanced_accuracy": P_clean,
        "readout_floor": readout_floor,
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "probe_strength_gap": float(abs(W_clean - P_clean)),
    }

    # Gate 1: both probes must carry real signal to test a dependency at all.
    if W_clean < readout_floor or P_clean < readout_floor:
        return {**base, "verdict": "BLOCKED_LOW_READOUT",
                "reason": f"clean balanced accuracy below readout_floor={readout_floor} "
                          f"(W={W_clean:.3f}, P={P_clean:.3f}); no signal to knock out."}

    rng = np.random.default_rng(seed)
    leg_WP = _leg(source_probe=probe_W, target_probe=probe_P, target_clean_ba=P_clean,
                  X_test=X[te], y_target_test=labels_P[te], n_random=n_random,
                  guard_margin=guard_margin, rng=rng)
    leg_PW = _leg(source_probe=probe_P, target_probe=probe_W, target_clean_ba=W_clean,
                  X_test=X[te], y_target_test=labels_W[te], n_random=n_random,
                  guard_margin=guard_margin, rng=rng)

    # Subsumption control: how much of P's raw-space direction sits inside span(W)?
    Bw_raw = _raw_space_basis(probe_W)
    Bp_raw = _raw_space_basis(probe_P)
    containment_P_in_W = _subspace_containment(Bw_raw, Bp_raw)
    containment_W_in_P = _subspace_containment(Bp_raw, Bw_raw)

    base["leg_W_to_P_collapse"] = leg_WP
    base["leg_P_to_W_survival"] = leg_PW
    base["subsumption_control"] = {
        "containment_P_in_span_W": containment_P_in_W,
        "containment_W_in_span_P": containment_W_in_P,
        "threshold": subsumption_threshold,
        "note": "containment ~1.0 means a directional collapse is explained by geometric "
                "subsumption, not prerequisite order; such a directional result is GREY.",
    }

    wp, pw = leg_WP["collapse"], leg_PW["collapse"]
    if wp and not pw:
        verdict = "PASS_DIRECTIONAL_PENDING_REVIEW"
    elif wp and pw:
        verdict = "FALSIFY_SYMMETRIC"
    elif (not wp) and pw:
        verdict = "FALSIFY_REVERSED"
    else:
        verdict = "FALSIFY_NO_DEPENDENCE"

    # Subsumption override: a directional pass that rides containment is GREY.
    if verdict == "PASS_DIRECTIONAL_PENDING_REVIEW" and containment_P_in_W >= subsumption_threshold:
        verdict = "GREY_SUBSUMPTION_CONFOUND"

    base["verdict"] = verdict
    base["verdict_rationale"] = {
        "PASS_DIRECTIONAL_PENDING_REVIEW": "W->P collapsed past the random-same-rank guard AND P->W survived; subsumption below threshold. Pending human review; never ACCEPT.",
        "GREY_SUBSUMPTION_CONFOUND": "W->P collapsed and P->W survived, BUT P's direction is largely contained in span(W); the asymmetry is not distinguishable from geometric subsumption at the linear level.",
        "FALSIFY_SYMMETRIC": "Both legs collapsed; this is undirected correlation, not a one-way prerequisite.",
        "FALSIFY_REVERSED": "P->W collapsed while W->P survived; the prerequisite order is the reverse of the claim.",
        "FALSIFY_NO_DEPENDENCE": "W->P did not collapse past the guard; no causal dependence of P on W.",
        "BLOCKED_SURFACE_LEAKAGE": "Surface-leakage screen not passed.",
        "BLOCKED_LOW_READOUT": "A probe lacked enough clean signal to test.",
    }[verdict]
    return base


# ----------------------------------------------------------------------------
# .npz loader + CLI (multi-label: accepts labels_W / labels_P, or named pair)
# ----------------------------------------------------------------------------


def _as_text(v: Any) -> str:
    return v.decode("utf-8") if isinstance(v, bytes) else str(v)


def load_multilabel_npz(path: Path, *, w_key: str, p_key: str, group_key: str = "groups") -> dict[str, Any]:
    data = np.load(path, allow_pickle=True)
    for needed in ("features", "layers", w_key, p_key):
        if needed not in data.files:
            raise SystemExit(f"dataset missing required key: {needed!r}; present={sorted(data.files)}")
    features = np.asarray(data["features"])
    if features.ndim != 3:
        raise SystemExit(f"features must be [N, num_layers, hidden_dim]; got {features.shape}")
    labels_W = np.array([_as_text(v) for v in data[w_key]])
    labels_P = np.array([_as_text(v) for v in data[p_key]])
    if group_key in data.files:
        groups = np.array([_as_text(v) for v in data[group_key]])
    elif "prompts" in data.files:
        groups = np.array([_as_text(v) for v in data["prompts"]])
    else:
        groups = np.arange(features.shape[0]).astype(str)
    return {"features": features, "layers": np.asarray(data["layers"]),
            "labels_W": labels_W, "labels_P": labels_P, "groups": groups}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--w-label-key", default="labels_W")
    p.add_argument("--p-label-key", default="labels_P")
    p.add_argument("--group-key", default="groups")
    p.add_argument("--layer", type=int, default=None, help="layer id (default: first layer)")
    p.add_argument("--surface-screen-status", default="UNVERIFIED",
                   help=f"must be {SURFACE_SCREEN_READY!r} for ablation to run")
    p.add_argument("--guard-margin", type=float, default=0.05)
    p.add_argument("--n-random", type=int, default=15)
    p.add_argument("--readout-floor", type=float, default=0.65)
    p.add_argument("--subsumption-threshold", type=float, default=0.5)
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()

    bundle = load_multilabel_npz(args.dataset, w_key=args.w_label_key, p_key=args.p_label_key, group_key=args.group_key)
    layers = [int(x) for x in bundle["layers"].tolist()]
    layer_index = 0 if args.layer is None else layers.index(args.layer)
    report = run_asymmetric_ablation(
        features=bundle["features"], layer_index=layer_index,
        labels_W=bundle["labels_W"], labels_P=bundle["labels_P"], groups=bundle["groups"],
        surface_screen_status=args.surface_screen_status, n_random=args.n_random,
        guard_margin=args.guard_margin, readout_floor=args.readout_floor,
        subsumption_threshold=args.subsumption_threshold, seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote RPM/diode asymmetric-ablation report: {args.output}")
    print(f"verdict={report['verdict']}  (claim_ceiling={report['claim_ceiling']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
