"""Stage 28D Noetic cluster colloquialism realization pre-registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_NOETIC_LABELS = ("^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9", "^0")
_PRIMARY_READOUTS = (
    {
        "runtime_name": "phrase_mean",
        "stage9_key": "X_mean",
        "stage9_name": "mean_over_seq_len",
        "definition": "mean of all tokenizer states overlapping the quoted cluster phrase span",
    },
    {
        "runtime_name": "phrase_last",
        "stage9_key": "X_final",
        "stage9_name": "final_token",
        "definition": "last tokenizer state overlapping the quoted cluster phrase span",
    },
)


@dataclass(frozen=True)
class Stage28DGate:
    name: str
    kind: str
    criterion: str


def stage28d_cluster_fixture() -> tuple[dict[str, Any], ...]:
    """Balanced compound-colloquialism fixture.

    Each row is multi-label: the target is a two-Noetic cluster rather than a
    single Noetic. These phrases are deliberately not CAS notation.
    """

    clusters = (
        (
            "attraction_cause",
            ("^2", "^8"),
            (
                "that reminds me of something I'm drawn to",
                "one thing leads me back to what speaks to me",
                "a memory triggered a pull toward it",
            ),
        ),
        (
            "aversion_analysis",
            ("^3", "^6"),
            (
                "I'm breaking down why I can't stomach it",
                "pulling apart the argument that rubs me the wrong way",
                "looking underneath what pushes me away",
            ),
        ),
        (
            "resonance_rhythm",
            ("^4", "^7"),
            (
                "it struck a chord and kept coming back",
                "the feeling resonated until I got into a groove",
                "it made an impression through repeated practice",
            ),
        ),
        (
            "mind_analysis",
            ("^1", "^6"),
            (
                "paying attention while unpacking the idea",
                "using my head to break it down",
                "making up my mind by looking underneath",
            ),
        ),
        (
            "identity_arising",
            ("^5", "^9"),
            (
                "out of nowhere it felt like part of who I am",
                "the thought came to me as something that makes me me",
                "it clicked as shaped by what came before",
            ),
        ),
        (
            "attraction_resonance",
            ("^2", "^4"),
            (
                "it resonated with me and pulled me toward it",
                "it struck a chord because it speaks to me",
                "the impression made it hard to resist",
            ),
        ),
        (
            "aversion_vibration",
            ("^3", "^4"),
            (
                "it hit me hard and rubbed me the wrong way",
                "the impression made me unable to stomach it",
                "it struck a sour chord I would not touch",
            ),
        ),
        (
            "mind_rhythm",
            ("^1", "^7"),
            (
                "I keep paying attention until practice makes perfect",
                "using my head while getting into a groove",
                "making up my mind through repeated practice",
            ),
        ),
    )
    rows: list[dict[str, Any]] = []
    for cluster_name, targets, phrases in clusters:
        for phrase in phrases:
            rows.append({"cluster": cluster_name, "targets": targets, "phrase": phrase})
    return tuple(rows)


def stage28d_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
        "cluster_fixture": "24 compound colloquialisms: 8 two-Noetic clusters x 3 phrases",
        "n_cluster_rows": len(stage28d_cluster_fixture()),
        "stage9_fixture": "stage9_elements_pilot_20260517.jsonl",
        "stage9_activations": "stage9_elements_pilot_activations_20260517.npz",
        "activation_contract": "stage24b_40_element_cpu_recap_prereg_20260521.json",
        "locked_layer": 5,
        "primary_phrase_level_readouts": _PRIMARY_READOUTS,
        "task": "multi-label Noetic cluster realization from compound natural-language colloquialisms",
    }


def stage28d_method() -> tuple[str, ...]:
    return (
        "Commit this pre-registration before any Stage 28D result artifact is generated.",
        "Use the locked 24-row compound-colloquialism cluster fixture.",
        "Fit collapsed Stage 9 Noetic probes at layer 5 for X_mean and X_final.",
        "Run Pythia-160M forward on each carrier sentence and capture all layer-5 token states overlapping the quoted phrase span.",
        "Score phrase_mean with the X_mean probe and phrase_last with the X_final probe.",
        "Use probe decision logits, standardized within each row, because clusters are multi-label and single-label softmax exact accuracy is the wrong target.",
        "For each row, compute the target-pair z-score and compare it against the maximum hard replacement-control pair score.",
        "Apply a two-candidate correction by requiring sign-test p<0.025 for a PASS on either phrase-level candidate.",
        "Report top labels and per-cluster margins for audit.",
    )


def stage28d_gates() -> tuple[Stage28DGate, ...]:
    return (
        Stage28DGate(
            name="artifact_contract",
            kind="pass_floor",
            criterion="Stage 9 activation artifact matches the preregistered local replacement contract used by Stage 24B.",
        ),
        Stage28DGate(
            name="candidate_probe_floor",
            kind="pass_floor",
            criterion="A phrase-level candidate is eligible only if its matching Stage 9 Noetic probe has test accuracy at least 0.50.",
        ),
        Stage28DGate(
            name="target_pair_margin",
            kind="primary",
            criterion="At least one eligible phrase-level candidate has mean target-pair z margin over hard replacement controls > 0.",
        ),
        Stage28DGate(
            name="corrected_sign_test",
            kind="primary",
            criterion="The same candidate has at least 18/24 positive target-over-control rows and sign-test p<0.025.",
        ),
        Stage28DGate(
            name="top4_target_coverage",
            kind="supporting",
            criterion="The same candidate has mean target-labels-in-top4 at least 0.90 out of 2.",
        ),
        Stage28DGate(
            name="per_cluster_coverage",
            kind="diagnostic",
            criterion="Report positive-row share per cluster; this is diagnostic, not required for PASS.",
        ),
    )


def stage28d_claim_boundary() -> dict[str, str]:
    return {
        "pass_status": "PASS_BOUNDED_NOETIC_CLUSTER_REALIZATION",
        "grey_status": "GREY_NOETIC_CLUSTER_REALIZATION_PARTIAL",
        "null_status": "NULL_NOETIC_CLUSTER_REALIZATION_NOT_ESTABLISHED",
        "claim_if_pass": (
            "A preregistered phrase-level readout shows that compound Noetic cluster colloquialisms jointly elevate "
            "their two target Noetics over hard replacement controls on Pythia-160M."
        ),
        "claim_if_null": (
            "Compound Noetic cluster colloquialisms do not jointly elevate their target Noetics over hard replacement "
            "controls under the preregistered phrase-level readouts."
        ),
        "scope_boundary": (
            "Stage 28D tests multi-label two-Noetic clusters on Pythia-160M using existing Stage 9 probes. It does "
            "not train a cluster classifier, test full formulas/equations, prove exact neurons, or establish generation control."
        ),
        "forbidden_claims": (
            "Do not claim exact neurons, complete circuits, retrained cluster classifiers, full TKS formulas, "
            "raw CAS-symbol understanding, free-form generation control, or cross-model generality from Stage 28D."
        ),
    }


def stage28d_payload() -> dict[str, Any]:
    payload = {
        "stage": "28D",
        "status": "PREREGISTERED_LOCAL_FORWARD_PASS",
        "motivation": (
            "Stages 28B/C showed that single-Noetic colloquialisms do not cleanly re-enter the Stage 9 Noetic probe "
            "space. Stage 28D tests the user's cluster hypothesis directly: compound phrases may be represented as "
            "joint Noetic elevations rather than single-label readouts."
        ),
        "formal_anchor": (
            "Noetic clusters are treated as compound natural-language realizations. Because the target is multi-label, "
            "Stage 28D evaluates joint target-pair elevation over replacement controls instead of single-class exact accuracy."
        ),
        "required_inputs": stage28d_required_inputs(),
        "cluster_fixture": list(stage28d_cluster_fixture()),
        "method": stage28d_method(),
        "gates": [asdict(gate) for gate in stage28d_gates()],
        "claim_boundary": stage28d_claim_boundary(),
        "execution_order": [
            "commit_preregistration_before_result_run",
            "fit_collapsed_noetic_probes_for_mean_and_final_from_stage9_artifact",
            "run_pythia_forward_on_locked_cluster_fixture",
            "score_joint_target_pair_elevation_against_hard_controls",
            "record_bounded_result",
        ],
    }
    payload["validation"] = validate_stage28d_payload(payload)
    return payload


def validate_stage28d_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if payload.get("status") != "PREREGISTERED_LOCAL_FORWARD_PASS":
        errors.setdefault("status", []).append("Stage 28D starts as a local forward-pass preregistration.")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_layer") != 5:
        errors.setdefault("required_inputs", []).append("Stage 28D must use layer 5.")
    candidates = tuple(inputs.get("primary_phrase_level_readouts", ()))
    if {row.get("runtime_name") for row in candidates} != {"phrase_mean", "phrase_last"}:
        errors.setdefault("required_inputs", []).append("Stage 28D must lock phrase_mean and phrase_last.")
    fixture = payload.get("cluster_fixture", [])
    clusters: dict[str, int] = {}
    for row in fixture:
        clusters[str(row.get("cluster"))] = clusters.get(str(row.get("cluster")), 0) + 1
        targets = tuple(row.get("targets", ()))
        if len(targets) != 2 or any(target not in _NOETIC_LABELS for target in targets):
            errors.setdefault("cluster_fixture", []).append("each cluster row must have exactly two valid Noetic targets.")
        phrase = str(row.get("phrase", ""))
        if "^" in phrase or "|" in phrase:
            errors.setdefault("cluster_fixture", []).append("cluster phrases must be natural language, not CAS symbols.")
    if len(clusters) != 8 or any(count != 3 for count in clusters.values()):
        errors.setdefault("cluster_fixture", []).append("fixture must contain 8 clusters with 3 rows each.")
    gate_names = {gate.get("name") for gate in payload.get("gates", [])}
    for required in ("target_pair_margin", "corrected_sign_test", "top4_target_coverage"):
        if required not in gate_names:
            errors.setdefault("gates", []).append(f"missing gate {required}.")
    forbidden = payload.get("claim_boundary", {}).get("forbidden_claims", "")
    if "retrained cluster classifiers" not in forbidden or "free-form generation control" not in forbidden:
        errors.setdefault("claim_boundary", []).append("forbidden claims must bound retraining and generation.")
    return errors
