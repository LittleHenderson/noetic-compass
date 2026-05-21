"""Stage 27D within-head slice cover pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_SELECTED_STAGE27_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


@dataclass(frozen=True)
class Stage27DGate:
    name: str
    kind: str
    criterion: str


def stage27d_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "stage7_activations": "stage7_foundation_pilot_activations_20260517.npz",
        "stage7_activation_sha256": "d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f",
        "stage27c_report": "stage27c_per_class_component_covers_20260521.json",
        "stage27c_status": "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "global_selected_components": _SELECTED_STAGE27_COMPONENTS,
        "source_cover_size": 3,
        "slices_per_head": 8,
        "slice_cover_size": 8,
        "learn_rows_per_class": 4,
        "eval_rows_per_class": 4,
    }


def stage27d_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration and runner before any Stage 27D GPU result is generated.",
        "Refit the locked Stage 7 28-way Foundation probe on the locked layer-6 focus-token artifact.",
        "Verify Stage 27C is PASS and was built from a locked Stage 7 artifact plus the Stage 26/27A six-head family.",
        "Use Stage 27C per-class three-head covers as the candidate head set for each Foundation class.",
        "Split each candidate head's 64-dimensional pre-output-projection slice into eight contiguous 8-dimensional slices.",
        "Build a balanced slice-learning subset from Stage 7 train rows and a disjoint balanced evaluation subset from Stage 7 test rows.",
        "For each learning row, globally ablate the six selected heads, then patch each candidate slice individually.",
        "Score each candidate slice by target-vs-hard-partner Foundation probe-logit margin lift over the globally ablated state.",
        "For each Foundation class, define an eight-slice class-local cover as the top slices by mean lift on learn rows for that class.",
        "On held-out evaluation rows, compare class-local slice covers against same-size random slice covers sampled from the same class candidate heads.",
        "Report the full Stage 27C class-head cover as the ceiling for each row; it is diagnostic, not the primary control.",
    )


def stage27d_gates() -> tuple[Stage27DGate, ...]:
    return (
        Stage27DGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 7 activation artifact hash matches the locked manifest.",
        ),
        Stage27DGate(
            name="stage27c_contract",
            kind="pass_floor",
            criterion="Stage 27C source report is PASS, uses the locked artifact, and exposes per-class covers over the selected six-head family.",
        ),
        Stage27DGate(
            name="learn_eval_separation",
            kind="pass_floor",
            criterion="Slice-cover learning rows come only from train split; scoring rows come only from test split.",
        ),
        Stage27DGate(
            name="matched_random_slice_control",
            kind="primary",
            criterion="Per-class slice covers beat per-row random same-size slice-cover mean margin on at least 60% of eval rows with sign-test p<0.05.",
        ),
        Stage27DGate(
            name="positive_margin_floor",
            kind="primary",
            criterion="At least 55% of eval rows have positive target-vs-hard-partner margin under the per-class slice cover.",
        ),
        Stage27DGate(
            name="head_cover_gain_fraction",
            kind="supporting",
            criterion="Mean slice-cover gain is at least 25% of the mean Stage 27C class-head-cover gain.",
        ),
        Stage27DGate(
            name="head_cover_ceiling",
            kind="diagnostic",
            criterion="Report slice-cover margin as a fraction of the full Stage 27C class-head cover margin; this is diagnostic, not required for PASS.",
        ),
    )


def stage27d_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS",
        "grey_status": "GREY_WITHIN_HEAD_SLICE_COVERS_PARTIAL",
        "null_status": "NULL_WITHIN_HEAD_SLICE_COVERS_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Within the Stage 27C per-class Pythia-160M attention-head covers, smaller contiguous within-head slices "
            "recover held-out hard-partner readout margins above matched random slice controls."
        ),
        "claim_if_null": (
            "Stage 27C class-local head covers remain valid, but this contiguous within-head slice decomposition did not "
            "recover held-out hard-partner readout margins under the preregistered controls."
        ),
        "scope_boundary": (
            "Stage 27D is bounded to contiguous slices of the pre-output-projection attention-head vectors inside the "
            "Pythia-160M Stage 27C Foundation covers. It is not exact neuron discovery, an MLP-neuron claim, a complete "
            "circuit, token sonar, Noetic/40-Element coverage, raw CAS-symbol understanding, or generation control."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, MLP-neuron localization, raw CAS-symbol understanding, an "
            "internal CAS compiler, Noetic/40-Element component causality, free-form generation control, or cross-model "
            "component generality from Stage 27D."
        ),
    }


def stage27d_payload() -> dict[str, Any]:
    payload = {
        "stage": "27D",
        "status": "PREREGISTERED_GPU_RECOMMENDED",
        "motivation": (
            "Stage 27C found that hard-partner fineness lives in class-local attention-head covers. Stage 27D asks whether "
            "those class-local covers can be narrowed further to contiguous within-head vector slices without claiming "
            "literal neurons."
        ),
        "formal_anchor": (
            "Refined local-cover framing: Stage 26/27A gives a global head cover, Stage 27C gives class-indexed subcovers, "
            "and Stage 27D tests whether each class-indexed cover admits a smaller within-head subcover."
        ),
        "required_inputs": stage27d_required_inputs(),
        "method": stage27d_method(),
        "gates": [asdict(gate) for gate in stage27d_gates()],
        "claim_boundary": stage27d_claim_boundary(),
        "execution_order": [
            "commit_preregistration_and_runner_before_gpu_result",
            "verify_stage27c_contract",
            "learn_per_class_slice_covers_on_train_split_only",
            "evaluate_hard_partner_margins_on_test_split_only",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage27d_payload(payload)
    return payload


def validate_stage27d_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_GPU_RECOMMENDED":
        errors.setdefault("status", []).append("Stage 27D starts as GPU-recommended preregistration.")
    inputs = payload.get("required_inputs", {})
    if tuple(inputs.get("global_selected_components", ())) != _SELECTED_STAGE27_COMPONENTS:
        errors.setdefault("required_inputs", []).append("selected components must match the Stage 26/27A top-six family.")
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 27D must target the Stage 7 layer-6 Foundation readout.")
    if int(inputs.get("slice_cover_size", 0)) >= int(inputs.get("source_cover_size", 0)) * int(inputs.get("slices_per_head", 0)):
        errors.setdefault("required_inputs", []).append("slice cover must be a strict subcover of the per-class candidate slices.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("matched_random_slice_control", "positive_margin_floor", "head_cover_gain_fraction", "learn_eval_separation"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    for phrase in ("exact neurons", "MLP-neuron", "free-form generation control", "Noetic/40-Element"):
        if phrase not in forbidden:
            errors.setdefault("claim_boundary", []).append(f"forbidden claims must bound {phrase}.")
    return errors
