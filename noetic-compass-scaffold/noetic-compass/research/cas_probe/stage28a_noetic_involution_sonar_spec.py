"""Stage 28A Noetic involution sonar pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_INVOLUTION_PAIRS = (("^2", "^3"), ("^5", "^6"), ("^8", "^9"))


@dataclass(frozen=True)
class Stage28AGate:
    name: str
    kind: str
    criterion: str


def stage28a_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage9_elements_pilot_20260517.jsonl",
        "stage9_activations": "stage9_elements_pilot_activations_20260517.npz",
        "activation_contract": "stage24b_40_element_cpu_recap_prereg_20260521.json",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 5},
        "task": "10-way Noetic readout collapsed from the Stage 9 original-TKS 40 Element fixture",
        "involution_pairs": _INVOLUTION_PAIRS,
    }


def stage28a_method() -> tuple[str, ...]:
    return (
        "Collapse the Stage 9 40-Element labels into 10 Noetic labels (^1..^9,^0).",
        "Fit the locked focus-token layer-5 Noetic probe on the existing Stage 9 activation artifact.",
        "Project the 10 Noetic probe directions through Pythia-160M output embeddings.",
        "Center and normalize each Noetic token-signature vector.",
        "Measure whether involution pairs (^2/^3, ^5/^6, ^8/^9) have lower cosine similarity / higher opposition than non-involution Noetic pairs.",
        "Compare the involution-opposition margin against random-direction controls.",
        "Report top positive and negative readable tokens for each Noetic class for audit, but do not use human interpretation as the pass gate.",
    )


def stage28a_gates() -> tuple[Stage28AGate, ...]:
    return (
        Stage28AGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B.",
        ),
        Stage28AGate(
            name="probe_floor",
            kind="pass_floor",
            criterion="Noetic probe test accuracy is at least 0.50 on the 10-way collapsed Noetic task.",
        ),
        Stage28AGate(
            name="readable_signature_floor",
            kind="data_quality",
            criterion="Readable top-token rate is at least 0.50.",
        ),
        Stage28AGate(
            name="involution_opposition_margin",
            kind="sonar_contrast",
            criterion="non-involution mean cosine minus involution mean cosine is positive.",
        ),
        Stage28AGate(
            name="random_direction_control",
            kind="control",
            criterion="Involution-opposition margin exceeds random-direction controls with empirical p < 0.05.",
        ),
        Stage28AGate(
            name="pair_rank_floor",
            kind="diagnostic",
            criterion="At least 2 of 3 involution pairs fall below the global pairwise median cosine similarity.",
        ),
    )


def stage28a_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_NOETIC_INVOLUTION_SONAR",
        "grey_status": "GREY_NOETIC_INVOLUTION_SONAR_PARTIAL",
        "null_status": "NULL_NOETIC_INVOLUTION_SONAR_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Pythia-160M's Stage 9 Noetic readout directions show token-level opposition for the formal "
            "Noetic involution pairs, exceeding random-direction controls."
        ),
        "claim_if_null": (
            "The Stage 9 Noetic readout may remain valid, but static output-embedding sonar did not establish "
            "token-level involution opposition under the preregistered controls."
        ),
        "scope_boundary": (
            "Stage 28A tests Noetic classes collapsed from the 40-Element fixture. It does not test Noetic clusters, "
            "component-localized Noetic covers, or dynamic generation."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, 40-Element hard-partner resolution, Noetic clusters, "
            "raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28A."
        ),
    }


def stage28a_payload() -> dict[str, Any]:
    payload = {
        "stage": "28A",
        "status": "PREREGISTERED_NO_GPU",
        "motivation": (
            "Foundation hard-partner token sonar failed because same-drive/different-register classes share "
            "vocabulary. Stage 28A tests the sharper hypothesis: Noetic involution pairs are formal opposites "
            "and should therefore be more separable/opposed in static token-signature space."
        ),
        "formal_anchor": (
            "TKS/Noetic involution structure: ^2<->^3, ^5<->^6, and ^8<->^9 are treated as typed opposition "
            "pairs. The sonar asks whether Pythia's output embedding geometry reflects that opposition."
        ),
        "required_inputs": stage28a_required_inputs(),
        "method": stage28a_method(),
        "gates": [asdict(gate) for gate in stage28a_gates()],
        "claim_boundary": stage28a_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_result_run",
            "fit_collapsed_noetic_probe_from_stage9_artifact",
            "project_noetic_directions_to_token_space",
            "measure_involution_opposition_against_non_involution_and_random_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage28a_payload(payload)
    return payload


def validate_stage28a_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_NO_GPU":
        errors.setdefault("status", []).append("Stage 28A starts as no-GPU preregistration.")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_readout", {}).get("layer") != 5:
        errors.setdefault("required_inputs", []).append("Stage 28A must target the Stage 9 layer-5 readout.")
    pairs = tuple(tuple(x) for x in inputs.get("involution_pairs", ()))
    if pairs != _INVOLUTION_PAIRS:
        errors.setdefault("required_inputs", []).append("involution pairs must be the preregistered TKS pairs.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("involution_opposition_margin", "random_direction_control", "pair_rank_floor"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "Noetic clusters" not in forbidden or "free-form generation control" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound clusters and generation.")
    return errors
