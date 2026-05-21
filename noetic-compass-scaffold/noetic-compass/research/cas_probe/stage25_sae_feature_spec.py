"""Stage 25 SAE feature-localization preregistration for CAS Harness.

Stage 25 is deliberately separate from Stage 24A/24B. Static sonar reached a
hard-contrast resolution ceiling, so this stage authorizes a paid GPU sparse
autoencoder pilot to test whether the Stage 7 Foundation subspace decomposes
into sparse, CAS-aligned features.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage25Gate:
    name: str
    kind: str
    criterion: str


def stage25_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "activations": "stage7_foundation_pilot_activations_20260517.npz",
        "activation_layer": 6,
        "activation_readout": "focus_token",
        "probe_labels": 28,
        "probe_task": "Foundation interaction F1T..F7E",
    }


def stage25_training_config() -> dict[str, Any]:
    return {
        "sae_family": "residual_stream_relu_sae",
        "input_dim": 768,
        "feature_multiplier": 8,
        "n_features": 6144,
        "optimizer": "AdamW",
        "learning_rate": 0.001,
        "batch_size": 1024,
        "max_steps": 5000,
        "l1_coefficient": 0.001,
        "dead_feature_threshold": 1e-6,
        "random_seed": 25025,
        "expected_gpu_budget_usd": "200-500",
    }


def stage25_gates() -> tuple[Stage25Gate, ...]:
    return (
        Stage25Gate(
            name="reconstruction_quality",
            kind="pass_floor",
            criterion="heldout_explained_variance >= 0.80 and heldout_mse finite",
        ),
        Stage25Gate(
            name="sparsity_noncollapse",
            kind="pass_floor",
            criterion="mean_active_features_per_row between 5 and 250 and dead_feature_rate < 0.80",
        ),
        Stage25Gate(
            name="cas_alignment",
            kind="primary",
            criterion=(
                "top SAE decoder features align to Stage 7 Foundation probe directions above "
                "matched random decoder-vector controls, empirical p < 0.05"
            ),
        ),
        Stage25Gate(
            name="feature_specificity",
            kind="primary",
            criterion=(
                "CAS-aligned features show heldout class-selective activation; top-class "
                "mean activation exceeds random feature controls, empirical p < 0.05"
            ),
        ),
        Stage25Gate(
            name="causal_feature_drop",
            kind="causal",
            criterion=(
                "removing top CAS-aligned SAE feature contributions degrades Stage 7 Foundation "
                "probe accuracy more than matched random feature removals"
            ),
        ),
    )


def stage25_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_SAE_FEATURE_READOUT",
        "grey_status": "GREY_SAE_FEATURE_READOUT_UNDERPOWERED_OR_TEXT_EXPLAINED",
        "null_status": "NULL_SAE_FEATURE_READOUT_NOT_ESTABLISHED",
        "claim_if_pass": (
            "In this first pilot, SAE-derived features provide a bounded, inspectable "
            "feature basis from which CAS Foundation signals are recoverable above "
            "pre-registered baselines on the tested model, layer, fixture, and held-out split."
        ),
        "claim_if_pass_with_ablation": (
            "If targeted SAE-feature removal clears the causal gate, CAS Harness may also "
            "claim readout-level causal relevance of the selected feature set under controls."
        ),
        "claim_if_null": (
            "The Stage 7 Foundation readout remains real, but this SAE configuration did not "
            "recover sparse CAS-aligned features beyond controls."
        ),
        "claim_if_grey": (
            "SAE-derived features show suggestive structure, but the result is underpowered, "
            "text-explained, unstable across controls, or not reliably above baseline."
        ),
        "forbidden_claims": (
            "Do not claim exact causal neurons, true CAS neurons, model thoughts, a complete "
            "neuron-by-neuron causal map, generated-language steering, raw CAS-symbol "
            "understanding, an internal CAS compiler, solved black-box interpretability, or "
            "generalization to arbitrary models/tasks/frontier scale."
        ),
    }


def stage25_payload() -> dict[str, Any]:
    payload = {
        "stage": "25",
        "status": "AUTHORIZED_GPU_SAE_PREREGISTERED",
        "motivation": (
            "Stage 24A/24B static sonar detected broad token geometry but failed hard local "
            "contrasts. This suggests polysemantic readout directions and motivates SAE "
            "feature decomposition."
        ),
        "required_inputs": stage25_required_inputs(),
        "training_config": stage25_training_config(),
        "gates": [asdict(gate) for gate in stage25_gates()],
        "claim_boundary": stage25_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_gpu_run",
            "run_stage25_sae_training",
            "rank_features_by_cas_alignment",
            "evaluate_feature_specificity",
            "evaluate_feature_removal_against_random_controls",
            "record_report_and_checkpoint_manifest",
        ],
    }
    payload["validation"] = validate_stage25_payload(payload)
    return payload


def validate_stage25_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "AUTHORIZED_GPU_SAE_PREREGISTERED":
        errors.setdefault("status", []).append("Stage 25 must be explicitly authorized before GPU execution")
    inputs = payload.get("required_inputs", {})
    if inputs.get("activation_layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 25 is locked to Stage 7 layer 6")
    config = payload.get("training_config", {})
    if int(config.get("n_features", 0)) <= int(config.get("input_dim", 0)):
        errors.setdefault("training_config", []).append("SAE must be overcomplete")
    gate_names = [gate.get("name") for gate in payload.get("gates", [])]
    for required in ("cas_alignment", "feature_specificity", "causal_feature_drop"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing {required}")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "exact" not in forbidden or "generated-language steering" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound exact-neuron and generation claims")
    return errors
