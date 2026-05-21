"""Stage 26 head/MLP component-attribution preregistration.

Stage 26 follows the Stage 24B and Stage 25 nulls. Static unembedding sonar
resolved broad token geometry but failed hard local contrasts; the Stage 25
SAE recovered aligned dense features but failed sparsity and causal-removal
gates. Stage 26 therefore changes decomposition level: from within-layer
feature discovery to across-component attribution over attention heads and MLP
blocks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage26Gate:
    name: str
    kind: str
    criterion: str


def stage26_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "probe_task": "Foundation interaction F1T..F7E",
        "n_foundation_classes": 28,
    }


def stage26_component_scope() -> dict[str, Any]:
    return {
        "attention_heads": {
            "layers": [0, 1, 2, 3, 4, 5],
            "heads_per_layer": 12,
            "total_heads": 72,
            "hook_target": "per-head attention output before residual addition",
        },
        "mlp_blocks": {
            "layers": [0, 1, 2, 3, 4, 5],
            "total_blocks": 6,
            "hook_target": "MLP block output before residual addition",
            "neuron_level": "deferred; Stage 26 block-level only unless a follow-up is preregistered",
        },
        "readout_position": "focus_token",
        "target_probe_layer": 6,
    }


def stage26_method() -> tuple[str, ...]:
    return (
        "Fit/recover the Stage 7 Foundation probe on locked layer-6 focus-token activations.",
        "Run Pythia-160M on the locked Stage 7 fixture with hooks for layers 0..5.",
        "For each attention head and MLP block, capture its focus-token contribution before residual addition.",
        "Rank components by projection of their contribution onto the Stage 7 Foundation probe subspace.",
        "Ablate top-ranked components during a fresh forward pass and re-score the locked Foundation probe at layer 6.",
        "Compare targeted ablations against same-count random component ablations and same-layer random controls.",
        "Report per-class disruption and whether the effect is specific or global activation damage.",
    )


def stage26_gates() -> tuple[Stage26Gate, ...]:
    return (
        Stage26Gate(
            name="capture_contract",
            kind="pass_floor",
            criterion="all 72 heads and 6 MLP blocks emit finite focus-token contribution tensors on the locked fixture",
        ),
        Stage26Gate(
            name="alignment_enrichment",
            kind="primary",
            criterion=(
                "top-ranked components have higher Foundation-subspace projection than matched random "
                "components, empirical p < 0.05"
            ),
        ),
        Stage26Gate(
            name="targeted_ablation_drop",
            kind="causal",
            criterion=(
                "ablating top-ranked components drops Stage 7 Foundation probe accuracy more than same-count "
                "random component ablations, empirical p < 0.05"
            ),
        ),
        Stage26Gate(
            name="class_specificity",
            kind="causal",
            criterion=(
                "top-component ablation disruption is concentrated in the predicted/claimed Foundation classes "
                "rather than uniform global damage"
            ),
        ),
        Stage26Gate(
            name="sanity_controls",
            kind="pass_floor",
            criterion=(
                "random same-layer ablations and no-op hooks preserve probe accuracy within the preregistered slack"
            ),
        ),
    )


def stage26_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_COMPONENT_ATTRIBUTION",
        "grey_status": "GREY_COMPONENT_ATTRIBUTION_UNDERPOWERED_OR_DIFFUSE",
        "null_status": "NULL_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED",
        "claim_if_pass": (
            "CAS Harness localizes bounded Stage 7 Foundation readout signal to specific "
            "attention-head or MLP-block components with alignment and ablation evidence."
        ),
        "claim_if_null": (
            "The Stage 7 Foundation readout remains real, but this head/MLP-block attribution "
            "run did not localize the signal to separable transformer components beyond controls."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, raw CAS-symbol understanding, "
            "internal CAS compiler behavior, free-form generation control, or cross-model "
            "component generality from Stage 26."
        ),
    }


def stage26_payload() -> dict[str, Any]:
    payload = {
        "stage": "26",
        "status": "PREREGISTERED_NO_GPU",
        "motivation": (
            "Stage 24B and Stage 25 constrained within-layer decomposition. Stage 26 tests "
            "whether the distributed CAS readout localizes across attention heads and MLP blocks."
        ),
        "formal_anchor": (
            "ACBE Axiom 4.2 / joint-surjectivity framing: multiple component morphisms may "
            "jointly cover the residual-stream target even when no sparse within-layer feature "
            "is individually causal."
        ),
        "required_inputs": stage26_required_inputs(),
        "component_scope": stage26_component_scope(),
        "method": stage26_method(),
        "gates": [asdict(gate) for gate in stage26_gates()],
        "claim_boundary": stage26_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_gpu_run",
            "implement_or_verify_component_hooks",
            "run_capture_and_alignment_ranking",
            "run_targeted_and_random_component_ablations",
            "record_report_and_artifact_manifest",
        ],
    }
    payload["validation"] = validate_stage26_payload(payload)
    return payload


def validate_stage26_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_NO_GPU":
        errors.setdefault("status", []).append("Stage 26 starts as no-GPU preregistration")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 26 must target Stage 7 layer 6")
    scope = payload.get("component_scope", {})
    heads = scope.get("attention_heads", {})
    if heads.get("total_heads") != 72:
        errors.setdefault("component_scope", []).append("Stage 26 head scope must be 72 heads")
    gates = [gate.get("name") for gate in payload.get("gates", [])]
    for required in ("alignment_enrichment", "targeted_ablation_drop", "class_specificity"):
        if required not in gates:
            errors.setdefault("gates", []).append(f"missing {required}")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "exact neurons" not in forbidden or "free-form generation control" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound exact-neuron and generation claims")
    return errors
