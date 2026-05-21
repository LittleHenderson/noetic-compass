"""Stage 28B Noetic colloquialism realization probe pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_NOETIC_LABELS = ("^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9", "^0")
_INVOLUTION_PAIRS = (("^2", "^3"), ("^5", "^6"), ("^8", "^9"))


@dataclass(frozen=True)
class Stage28BGate:
    name: str
    kind: str
    criterion: str


def stage28b_colloquialism_fixture() -> tuple[dict[str, str], ...]:
    """Balanced canonical phrase fixture.

    These are natural-language realization phrases, not CAS symbols. The core
    phrases come from Clarification 6 in docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md,
    with one balancing phrase added where the source lists fewer than four.
    """

    return (
        {"noetic": "^1", "name": "Mind", "phrase": "paying attention"},
        {"noetic": "^1", "name": "Mind", "phrase": "making up my mind"},
        {"noetic": "^1", "name": "Mind", "phrase": "using my head"},
        {"noetic": "^1", "name": "Mind", "phrase": "becoming aware"},
        {"noetic": "^2", "name": "Positive", "phrase": "drawn to it like a moth to a flame"},
        {"noetic": "^2", "name": "Positive", "phrase": "speaks to me"},
        {"noetic": "^2", "name": "Positive", "phrase": "can't resist it"},
        {"noetic": "^2", "name": "Positive", "phrase": "pulled toward it"},
        {"noetic": "^3", "name": "Negative", "phrase": "can't stomach it"},
        {"noetic": "^3", "name": "Negative", "phrase": "rubs me the wrong way"},
        {"noetic": "^3", "name": "Negative", "phrase": "wouldn't touch it with a ten-foot pole"},
        {"noetic": "^3", "name": "Negative", "phrase": "pushed away from it"},
        {"noetic": "^4", "name": "Vibration", "phrase": "hit me hard"},
        {"noetic": "^4", "name": "Vibration", "phrase": "struck a chord"},
        {"noetic": "^4", "name": "Vibration", "phrase": "resonated with me"},
        {"noetic": "^4", "name": "Vibration", "phrase": "made an impression"},
        {"noetic": "^5", "name": "Female", "phrase": "we are the sum of our experiences"},
        {"noetic": "^5", "name": "Female", "phrase": "it's who I am"},
        {"noetic": "^5", "name": "Female", "phrase": "part of what makes me me"},
        {"noetic": "^5", "name": "Female", "phrase": "shaped by what came before"},
        {"noetic": "^6", "name": "Male", "phrase": "unpacking an idea"},
        {"noetic": "^6", "name": "Male", "phrase": "breaking it down"},
        {"noetic": "^6", "name": "Male", "phrase": "looking at what's underneath"},
        {"noetic": "^6", "name": "Male", "phrase": "pulling apart the argument"},
        {"noetic": "^7", "name": "Rhythm", "phrase": "practice makes perfect"},
        {"noetic": "^7", "name": "Rhythm", "phrase": "you are what you repeatedly do"},
        {"noetic": "^7", "name": "Rhythm", "phrase": "getting into a groove"},
        {"noetic": "^7", "name": "Rhythm", "phrase": "muscle memory"},
        {"noetic": "^8", "name": "Above/Cause", "phrase": "that reminds me"},
        {"noetic": "^8", "name": "Above/Cause", "phrase": "one thing leads to another"},
        {"noetic": "^8", "name": "Above/Cause", "phrase": "triggered a memory"},
        {"noetic": "^8", "name": "Above/Cause", "phrase": "made me think of something else"},
        {"noetic": "^9", "name": "Below/Effect", "phrase": "it just popped into my head"},
        {"noetic": "^9", "name": "Below/Effect", "phrase": "out of nowhere I thought of it"},
        {"noetic": "^9", "name": "Below/Effect", "phrase": "the thought came to me"},
        {"noetic": "^9", "name": "Below/Effect", "phrase": "it just clicked"},
        {"noetic": "^0", "name": "Idea", "phrase": "it's all in your head"},
        {"noetic": "^0", "name": "Idea", "phrase": "a thought on my mind"},
        {"noetic": "^0", "name": "Idea", "phrase": "something on my mind"},
        {"noetic": "^0", "name": "Idea", "phrase": "the idea itself"},
    )


def stage28b_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "fixture_source": "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarification 6 plus balanced source-compatible variants",
        "n_colloquialism_rows": len(stage28b_colloquialism_fixture()),
        "stage9_fixture": "stage9_elements_pilot_20260517.jsonl",
        "stage9_activations": "stage9_elements_pilot_activations_20260517.npz",
        "activation_contract": "stage24b_40_element_cpu_recap_prereg_20260521.json",
        "locked_probe_readout": {"name": "focus_token", "key": "X_focus", "layer": 5},
        "runtime_readout": {
            "name": "phrase_first_token",
            "layer": 5,
            "definition": "first tokenizer token overlapping the quoted colloquial phrase span",
        },
        "task": "10-way Noetic realization readout from natural-language colloquial phrases",
        "involution_pairs": _INVOLUTION_PAIRS,
    }


def stage28b_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration before any Stage 28B result artifact is generated.",
        "Collapse the Stage 9 40-Element labels into the same 10 Noetic labels used in Stage 28A.",
        "Fit the locked focus-token layer-5 Noetic probe on the existing Stage 9 activation artifact.",
        "Construct a balanced 40-row colloquialism fixture: four natural-language phrases per Noetic class.",
        "Run Pythia-160M forward on each carrier sentence and capture the layer-5 hidden state at the first token overlapping the phrase span.",
        "Score each captured state with the locked Noetic probe.",
        "Evaluate exact accuracy, top-2 accuracy, mean target probability lift over chance, and target-vs-involution-partner margins.",
        "Report per-Noetic rows and failures for audit. Human readability of phrases is not a scoring gate because the fixture is locked natural language.",
    )


def stage28b_gates() -> tuple[Stage28BGate, ...]:
    return (
        Stage28BGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B.",
        ),
        Stage28BGate(
            name="probe_floor",
            kind="pass_floor",
            criterion="Noetic probe test accuracy is at least 0.50 on the 10-way collapsed Stage 9 task.",
        ),
        Stage28BGate(
            name="realization_exact_accuracy",
            kind="primary",
            criterion="Colloquial phrase exact Noetic accuracy is at least 0.45 and exact-binomial p<0.05 against 10-way chance.",
        ),
        Stage28BGate(
            name="target_probability_lift",
            kind="primary",
            criterion="Mean target probability is at least 0.15, i.e. +0.05 over 10-way chance.",
        ),
        Stage28BGate(
            name="top2_accuracy",
            kind="supporting",
            criterion="Top-2 Noetic accuracy is at least 0.65.",
        ),
        Stage28BGate(
            name="involution_partner_margin",
            kind="supporting",
            criterion="For rows whose Noetic has a formal involution partner, target probability beats partner probability on at least 0.60 of rows.",
        ),
    )


def stage28b_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_NOETIC_COLLOQUIALISM_REALIZATION",
        "grey_status": "GREY_NOETIC_COLLOQUIALISM_REALIZATION_PARTIAL",
        "null_status": "NULL_NOETIC_COLLOQUIALISM_REALIZATION_NOT_ESTABLISHED",
        "claim_if_pass": (
            "Pythia-160M's hidden states for canonical natural-language Noetic colloquialisms are readable by the "
            "Stage 9 Noetic probe above the preregistered gates, supporting the η→ε realization route for Noetic language."
        ),
        "claim_if_null": (
            "Noetic readouts may remain valid on the Stage 9 fixture, but this colloquialism realization fixture did "
            "not establish that canonical Noetic phrases produce the matching hidden-state readout under the locked probe."
        ),
        "scope_boundary": (
            "Stage 28B tests single Noetic colloquial phrases on Pythia-160M. It does not test Noetic clusters, "
            "full TKS formulas, component-localized covers, exact neurons, or open-ended generation control."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, Noetic clusters, 40-Element hard-partner resolution, "
            "raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28B."
        ),
    }


def stage28b_payload() -> dict[str, Any]:
    payload = {
        "stage": "28B",
        "status": "PREREGISTERED_LOCAL_FORWARD_PASS",
        "motivation": (
            "Static output-embedding sonar failed to resolve most hard local Noetic contrasts. Stage 28B tests a "
            "different route: feed the model natural-language colloquialisms that realize Noetic operators and read "
            "the resulting hidden states with the existing Stage 9 Noetic probe."
        ),
        "formal_anchor": (
            "η→ε bridge framing: colloquialisms are readable realization language (ε-side) rather than raw CAS symbols "
            "or static W_U projections. The probe tests whether the realized phrase re-enters the hidden-state Noetic "
            "readout (η-side)."
        ),
        "required_inputs": stage28b_required_inputs(),
        "colloquialism_fixture": list(stage28b_colloquialism_fixture()),
        "method": stage28b_method(),
        "gates": [asdict(gate) for gate in stage28b_gates()],
        "claim_boundary": stage28b_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_result_run",
            "fit_collapsed_noetic_probe_from_stage9_artifact",
            "run_pythia_forward_on_locked_colloquialism_fixture",
            "score_phrase_hidden_states_with_noetic_probe",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage28b_payload(payload)
    return payload


def validate_stage28b_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_LOCAL_FORWARD_PASS":
        errors.setdefault("status", []).append("Stage 28B starts as a local forward-pass preregistration.")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_probe_readout", {}).get("layer") != 5:
        errors.setdefault("required_inputs", []).append("Stage 28B must use the Stage 9 layer-5 probe.")
    if inputs.get("runtime_readout", {}).get("name") != "phrase_first_token":
        errors.setdefault("required_inputs", []).append("runtime readout must be the preregistered phrase-first-token state.")
    fixture = payload.get("colloquialism_fixture", [])
    counts: dict[str, int] = {}
    for row in fixture:
        counts[str(row.get("noetic"))] = counts.get(str(row.get("noetic")), 0) + 1
        phrase = str(row.get("phrase", ""))
        if "^" in phrase or "|" in phrase or "F3" in phrase:
            errors.setdefault("colloquialism_fixture", []).append("fixture phrases must be natural language, not CAS symbols.")
    if set(counts) != set(_NOETIC_LABELS) or any(count != 4 for count in counts.values()):
        errors.setdefault("colloquialism_fixture", []).append("fixture must contain exactly four rows for each of ten Noetics.")
    pairs = tuple(tuple(x) for x in inputs.get("involution_pairs", ()))
    if pairs != _INVOLUTION_PAIRS:
        errors.setdefault("required_inputs", []).append("involution pairs must be the preregistered TKS pairs.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("realization_exact_accuracy", "target_probability_lift", "top2_accuracy", "involution_partner_margin"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "Noetic clusters" not in forbidden or "free-form generation control" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound clusters and generation.")
    return errors
