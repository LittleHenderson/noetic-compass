"""Stage 27H prefix-plus-neuron steering pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage27HGate:
    name: str
    kind: str
    criterion: str


def stage27h_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_prefix_report": "stage7_cas_prefix_likelihood_20260517.json",
        "stage27f_report": "stage27f_targeted_mlp_neuron_covers_20260521.json",
        "stage27g_report": "stage27g_mlp_neuron_cover_steering_20260521.json",
        "stage7_prefix_status": "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD",
        "stage27f_status": "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS",
        "stage27g_status": "PASS_BOUNDED_MLP_NEURON_COVER_STEERING",
        "amplification_scale": 2.0,
        "polarity_flip_scale": -1.0,
        "per_drive": 16,
    }


def stage27h_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27H GPU result is generated.",
        "Reuse the Stage 7 CAS-prefix likelihood row selection and readable plain-prefix wording.",
        "Verify Stage 27F and Stage 27G source reports are PASS and expose the class-specific MLP-neuron covers.",
        "Score correct-drive versus hard-partner-drive continuation likelihood under no prefix and readable prefix.",
        "During likelihood scoring, amplify the target class's Stage 27F neuron cover and compare prefix-plus-amplification against prefix-only.",
        "Compare the prefix-plus-amplification increment against same-size/same-layer random neuron-cover amplification controls.",
        "Polarity-flip the target cover under the same readable prefix and compare the margin reduction against random polarity-flip controls.",
        "Report neuron-only amplification and partner-cover amplification as diagnostics, not primary PASS gates.",
    )


def stage27h_gates() -> tuple[Stage27HGate, ...]:
    return (
        Stage27HGate(
            name="source_contracts",
            kind="pass_floor",
            criterion="Stage 7 readable-prefix, Stage 27F, and Stage 27G source reports have the preregistered PASS statuses.",
        ),
        Stage27HGate(
            name="prefix_floor",
            kind="pass_floor",
            criterion="Readable prefix-only margin delta versus no-prefix is positive and at least +0.10 on average.",
        ),
        Stage27HGate(
            name="prefix_plus_target_amplification",
            kind="primary",
            criterion="Prefix-plus-target-cover amplification beats random-cover amplification increments on at least 60% of rows with sign-test p<0.05.",
        ),
        Stage27HGate(
            name="prefix_plus_target_flip",
            kind="primary",
            criterion="Prefix-plus-target-cover polarity flip reduces margin more than random-cover polarity flips on at least 60% of rows with sign-test p<0.05.",
        ),
        Stage27HGate(
            name="bidirectional_effect_share",
            kind="primary",
            criterion="Both amplification increments and polarity-flip reductions are positive on at least 55% of rows.",
        ),
    )


def stage27h_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_PREFIX_PLUS_NEURON_STEERING",
        "grey_status": "GREY_PREFIX_PLUS_NEURON_STEERING_PARTIAL",
        "null_status": "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within Pythia-160M, a readable CAS realization prefix plus internal amplification of the matching "
            "Stage 27F MLP-neuron cover shifts semantic continuation likelihood beyond prefix-only and matched "
            "random-cover controls; polarity-flipping the same cover pushes the likelihood margin in the opposite direction."
        ),
        "claim_if_null": (
            "Stage 7 prefix conditioning and Stage 27G readout steering remain valid separately, but their combined "
            "effect on continuation likelihood was not established under the preregistered controls."
        ),
        "scope_boundary": (
            "Stage 27H is output-distribution likelihood steering, not free-form visible-text control, not weight "
            "editing, not model-wide control, not a complete circuit, and not cross-model evidence."
        ),
        "forbidden_claims": (
            "Do not claim open-ended generation control, exact circuit completion, model-wide control, weight editing, "
            "cross-model steering, or raw CAS-symbol understanding from Stage 27H."
        ),
    }


def stage27h_payload() -> dict[str, Any]:
    payload = {
        "stage": "27H",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 7 proved readable-prefix likelihood conditioning. Stage 27G proved MLP-neuron cover readout "
            "steering. Stage 27H tests whether the two routes combine at the semantic likelihood level."
        ),
        "formal_anchor": (
            "External realization plus internal cover intervention: epsilon-readable prefix supplies the realized "
            "CAS frame, while the Stage 27F/27G neuron cover amplifies the matching internal readout path."
        ),
        "required_inputs": stage27h_required_inputs(),
        "method": stage27h_method(),
        "gates": [asdict(gate) for gate in stage27h_gates()],
        "claim_boundary": stage27h_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_source_contracts",
            "score_prefix_only_and_prefix_plus_neuron_interventions",
            "compare_against_same_layer_random_neuron_cover_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27h_payload(payload)
    return payload


def validate_stage27h_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27H starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if float(inputs.get("amplification_scale", 0.0)) <= 1.0:
        errors.setdefault("required_inputs", []).append("amplification scale must be greater than 1.0.")
    if float(inputs.get("polarity_flip_scale", 0.0)) >= 0.0:
        errors.setdefault("required_inputs", []).append("polarity flip scale must be negative.")
    for key in ("stage7_prefix_status", "stage27f_status", "stage27g_status"):
        if not str(inputs.get(key, "")).startswith(("READABLE_PREFIX", "PASS_")):
            errors.setdefault("required_inputs", []).append(f"{key} must be a preregistered source PASS status.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("prefix_floor", "prefix_plus_target_amplification", "prefix_plus_target_flip"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("open-ended generation control", "model-wide control", "weight editing", "cross-model"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
