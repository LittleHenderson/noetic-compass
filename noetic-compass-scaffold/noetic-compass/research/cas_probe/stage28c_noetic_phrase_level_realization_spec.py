"""Stage 28C Noetic phrase-level colloquialism realization pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from stage28b_noetic_colloquialism_realization_spec import stage28b_colloquialism_fixture


_NOETIC_LABELS = ("^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9", "^0")
_INVOLUTION_PAIRS = (("^2", "^3"), ("^5", "^6"), ("^8", "^9"))
_PRIMARY_READOUTS = (
    {
        "runtime_name": "phrase_mean",
        "stage9_key": "X_mean",
        "stage9_name": "mean_over_seq_len",
        "definition": "mean of all tokenizer states overlapping the quoted colloquial phrase span",
    },
    {
        "runtime_name": "phrase_last",
        "stage9_key": "X_final",
        "stage9_name": "final_token",
        "definition": "last tokenizer state overlapping the quoted colloquial phrase span",
    },
)
_BASELINE_READOUT = {
    "runtime_name": "phrase_first",
    "stage9_key": "X_focus",
    "stage9_name": "focus_token",
    "definition": "first tokenizer state overlapping the quoted colloquial phrase span",
}


@dataclass(frozen=True)
class Stage28CGate:
    name: str
    kind: str
    criterion: str


def stage28c_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "stage28b_fixture": "reuse exact Stage 28B 40-row colloquialism fixture",
        "n_colloquialism_rows": len(stage28b_colloquialism_fixture()),
        "stage9_fixture": "stage9_elements_pilot_20260517.jsonl",
        "stage9_activations": "stage9_elements_pilot_activations_20260517.npz",
        "activation_contract": "stage24b_40_element_cpu_recap_prereg_20260521.json",
        "locked_layer": 5,
        "baseline_readout": _BASELINE_READOUT,
        "primary_phrase_level_readouts": _PRIMARY_READOUTS,
        "task": "10-way Noetic realization readout from full-phrase natural-language colloquialisms",
        "involution_pairs": _INVOLUTION_PAIRS,
    }


def stage28c_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration before any Stage 28C result artifact is generated.",
        "Reuse the exact 40-row Stage 28B colloquialism fixture; do not edit phrases after seeing results.",
        "Fit three collapsed Stage 9 Noetic probes at layer 5: X_focus, X_mean, and X_final.",
        "Run Pythia-160M forward on each carrier sentence and capture all layer-5 token states overlapping the quoted phrase span.",
        "Score phrase_first with the X_focus probe only as the Stage 28B baseline replication.",
        "Score phrase_mean with the X_mean probe and phrase_last with the X_final probe as the two preregistered phrase-level candidates.",
        "Apply a two-candidate correction by requiring exact-binomial p<0.025 for a PASS on either phrase-level candidate.",
        "Report per-Noetic rows and target-vs-involution-partner margins for each readout.",
    )


def stage28c_gates() -> tuple[Stage28CGate, ...]:
    return (
        Stage28CGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B.",
        ),
        Stage28CGate(
            name="candidate_probe_floor",
            kind="pass_floor",
            criterion="A phrase-level candidate is eligible only if its matching Stage 9 Noetic probe has test accuracy at least 0.50.",
        ),
        Stage28CGate(
            name="corrected_exact_accuracy",
            kind="primary",
            criterion="At least one eligible phrase-level candidate has exact Noetic accuracy at least 0.45 and exact-binomial p<0.025 against 10-way chance.",
        ),
        Stage28CGate(
            name="target_probability_lift",
            kind="primary",
            criterion="The same passing candidate has mean target probability at least 0.15, i.e. +0.05 over 10-way chance.",
        ),
        Stage28CGate(
            name="top2_accuracy",
            kind="supporting",
            criterion="The same passing candidate has top-2 Noetic accuracy at least 0.65.",
        ),
        Stage28CGate(
            name="involution_partner_margin",
            kind="supporting",
            criterion="For rows whose Noetic has a formal involution partner, the same passing candidate beats partner probability on at least 0.60 of rows.",
        ),
        Stage28CGate(
            name="baseline_improvement",
            kind="diagnostic",
            criterion="Report the delta from Stage 28B phrase_first exact accuracy; this is diagnostic, not required for PASS.",
        ),
    )


def stage28c_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_NOETIC_PHRASE_LEVEL_REALIZATION",
        "grey_status": "GREY_NOETIC_PHRASE_LEVEL_REALIZATION_PARTIAL",
        "null_status": "NULL_NOETIC_PHRASE_LEVEL_REALIZATION_NOT_ESTABLISHED",
        "claim_if_pass": (
            "A preregistered phrase-level readout, using the matching Stage 9 readout probe, reads canonical "
            "Noetic colloquialisms above the corrected gates on Pythia-160M."
        ),
        "claim_if_null": (
            "Stage 28B's first-token null is not rescued by the preregistered phrase-mean or phrase-last readouts "
            "under the matching Stage 9 Noetic probes."
        ),
        "scope_boundary": (
            "Stage 28C tests phrase-level readout positions for single Noetic colloquialisms on Pythia-160M. "
            "It does not test Noetic clusters, retrained colloquialism probes, full TKS formulas, component-localized "
            "covers, exact neurons, or open-ended generation control."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, Noetic clusters, retrained colloquialism classifiers, "
            "40-Element hard-partner resolution, raw CAS-symbol understanding, free-form generation control, or "
            "cross-model generality from Stage 28C."
        ),
    }


def stage28c_payload() -> dict[str, Any]:
    payload = {
        "stage": "28C",
        "status": "PREREGISTERED_LOCAL_FORWARD_PASS",
        "motivation": (
            "Stage 28B tested only the first token of each colloquial phrase and returned a bounded null. "
            "Stage 28C tests the explicit measurement critique: colloquialisms are phrase-level cognitive acts, "
            "so phrase-mean or phrase-last activations may carry the intended Noetic more faithfully than the first token."
        ),
        "formal_anchor": (
            "Noetic colloquialisms are treated as natural-language realizations. This stage changes the measurement "
            "position from a token-local readout to a phrase-level readout while preserving the same Stage 9 artifact "
            "and the same Stage 28B phrase fixture."
        ),
        "required_inputs": stage28c_required_inputs(),
        "method": stage28c_method(),
        "gates": [asdict(gate) for gate in stage28c_gates()],
        "claim_boundary": stage28c_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_result_run",
            "fit_collapsed_noetic_probes_for_focus_mean_final_from_stage9_artifact",
            "run_pythia_forward_on_locked_stage28b_colloquialism_fixture",
            "score_phrase_mean_and_phrase_last_hidden_states_with_matching_noetic_probes",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage28c_payload(payload)
    return payload


def validate_stage28c_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_LOCAL_FORWARD_PASS":
        errors.setdefault("status", []).append("Stage 28C starts as a local forward-pass preregistration.")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_layer") != 5:
        errors.setdefault("required_inputs", []).append("Stage 28C must use layer 5.")
    candidates = tuple(inputs.get("primary_phrase_level_readouts", ()))
    candidate_names = {row.get("runtime_name") for row in candidates}
    if candidate_names != {"phrase_mean", "phrase_last"}:
        errors.setdefault("required_inputs", []).append("Stage 28C must lock phrase_mean and phrase_last candidates.")
    keys = {row.get("stage9_key") for row in candidates}
    if keys != {"X_mean", "X_final"}:
        errors.setdefault("required_inputs", []).append("Phrase-level candidates must use matching X_mean and X_final probes.")
    baseline = inputs.get("baseline_readout", {})
    if baseline.get("runtime_name") != "phrase_first" or baseline.get("stage9_key") != "X_focus":
        errors.setdefault("required_inputs", []).append("Baseline must preserve Stage 28B phrase_first/X_focus.")
    pairs = tuple(tuple(x) for x in inputs.get("involution_pairs", ()))
    if pairs != _INVOLUTION_PAIRS:
        errors.setdefault("required_inputs", []).append("involution pairs must be the preregistered TKS pairs.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("corrected_exact_accuracy", "target_probability_lift", "top2_accuracy", "involution_partner_margin"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "Noetic clusters" not in forbidden or "retrained colloquialism classifiers" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound clusters and retrained classifiers.")
    return errors
