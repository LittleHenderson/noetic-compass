"""Stage 24A CAS Sonar + component-attribution pilot specification.

This module is intentionally no-GPU and declarative. It locks the experiment
contract before implementation scripts run against Pythia-160M artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Stage24ATrack:
    name: str
    subject: str
    status: str
    question: str
    primary_artifact: str
    method: tuple[str, ...]
    pass_gate: tuple[str, ...]
    null_gate: tuple[str, ...]
    claim_if_pass: str
    claim_if_null: str
    forbidden_claims: tuple[str, ...]


def stage24a_tracks() -> tuple[Stage24ATrack, ...]:
    return (
        Stage24ATrack(
            name="sonar_token_signatures",
            subject="cas_harness_pythia160m_foundation_subspace",
            status="next_to_build",
            question=(
                "Do Stage 7 Foundation probe directions induce class-specific "
                "vocabulary signatures through the model's unembedding/token space?"
            ),
            primary_artifact="STAGE24A_SONAR_TOKEN_SIGNATURES_20260520",
            method=(
                "Recover the locked Stage 7 Foundation probe raw-space class directions.",
                "Project each Foundation class direction through Pythia-160M output embeddings.",
                "Report top positive and negative tokens per Foundation, Drive, and Register.",
                "Compare within-drive/same-register similarity against hard-partner and random controls.",
                "Check involution/contrast pairs for token-signature opposition where applicable.",
            ),
            pass_gate=(
                "Top-token signatures are stable under bootstrap or split-resample controls.",
                "Same-Drive or same-Register classes are more similar than hard-partner controls.",
                "Random same-rank directions do not reproduce the observed class-specific structure.",
            ),
            null_gate=(
                "Class signatures are no more stable than random directions.",
                "Within-axis similarity does not beat hard-partner or random controls.",
                "Top tokens are dominated by tokenizer artifacts or corpus leakage terms.",
            ),
            claim_if_pass=(
                "CAS Harness maps bounded CAS readout directions to model-native token signatures."
            ),
            claim_if_null=(
                "Stage 7 readout remains valid, but token-level vocabulary signatures are not established."
            ),
            forbidden_claims=(
                "Do not claim the model would necessarily generate the top sonar tokens.",
                "Do not claim token signatures are neuron-level causal circuits.",
                "Do not claim universal sonar transfer before cross-model runs.",
            ),
        ),
        Stage24ATrack(
            name="component_attribution_pilot",
            subject="pythia160m_attention_heads_and_mlp_intermediates",
            status="design_locked_gpu_optional",
            question=(
                "Can CAS Harness localize Foundation readout signal from the residual "
                "subspace down to specific transformer components?"
            ),
            primary_artifact="STAGE24A_COMPONENT_ATTRIBUTION_PILOT_20260520",
            method=(
                "Hook attention-head outputs and MLP intermediate activations on the locked Stage 7 fixture.",
                "Rank components by projection/alignment to the Stage 7 Foundation subspace.",
                "Ablate top-ranked components and matched random controls.",
                "Measure Foundation probe accuracy drop, per-class disruption, and specificity.",
                "Cross-reference high-ranking components with sonar token signatures when available.",
            ),
            pass_gate=(
                "Top-ranked component ablation degrades Foundation readout more than matched random controls.",
                "Disruption is class-specific rather than a global activation-damage artifact.",
                "At least one component family clears a pre-registered effect floor.",
            ),
            null_gate=(
                "Top-ranked components do not beat matched random controls.",
                "Ablation damage is nonspecific or equivalent across classes.",
                "Signal appears too distributed for component-level localization without SAE methods.",
            ),
            claim_if_pass=(
                "CAS Harness can localize bounded CAS readout signal to transformer components with causal evidence."
            ),
            claim_if_null=(
                "Component-level localization is not established; SAE/path-patching becomes the next research route."
            ),
            forbidden_claims=(
                "Do not claim exact monosemantic neurons from component-level evidence.",
                "Do not claim full generation control from readout-component disruption.",
                "Do not claim SAE-level feature localization unless SAEs are trained and tested.",
            ),
        ),
    )


def stage24a_required_inputs() -> dict[str, Any]:
    return {
        "model": "EleutherAI/pythia-160m",
        "fixture": "stage7_foundation_pilot_20260517.jsonl",
        "activations": "stage7_foundation_pilot_activations_20260517.npz",
        "probe_report": "stage7_foundation_pilot_probe_report_20260517.json",
        "ablation_report": "stage7_foundation_layer6_ablation_report_20260517.json",
        "locked_readout": {"name": "focus_token", "key": "X_focus", "layer": 6},
        "foundation_classes": 28,
        "random_controls_required": True,
    }


def stage24a_claim_boundary() -> dict[str, str]:
    return {
        "licensed_if_pass": (
            "Stage 24A can support token-level CAS sonar and bounded component-level "
            "causal localization claims, depending on which track passes."
        ),
        "not_yet_claimed": (
            "Exact neuron-level or SAE-disentangled feature causality remains untested "
            "until a separate SAE/path-patching stage runs."
        ),
        "product_relevance": (
            "Stage 24A strengthens CAS Harness evidence depth; it is not a blocker for "
            "Evidence Packet or Verification Stack productization."
        ),
    }


def validate_stage24a_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    track_names = [track["name"] for track in payload.get("tracks", [])]
    if track_names != ["sonar_token_signatures", "component_attribution_pilot"]:
        errors.setdefault("tracks", []).append("tracks must run sonar before component attribution")
    for track in payload.get("tracks", []):
        name = str(track.get("name"))
        if not track.get("forbidden_claims"):
            errors.setdefault(name, []).append("forbidden_claims required")
        if "SAE" in str(track.get("claim_if_pass", "")):
            errors.setdefault(name, []).append("Stage 24A pass claim must not imply SAE evidence")
        if not track.get("pass_gate") or not track.get("null_gate"):
            errors.setdefault(name, []).append("pass_gate and null_gate required")
    inputs = payload.get("required_inputs", {})
    if inputs.get("locked_readout", {}).get("layer") != 6:
        errors.setdefault("required_inputs", []).append("Stage 24A is locked to Stage 7 layer 6")
    if not inputs.get("random_controls_required"):
        errors.setdefault("required_inputs", []).append("random controls are required")
    return errors


def stage24a_preregistration_payload() -> dict[str, Any]:
    payload = {
        "stage": "24A",
        "status": "PREREGISTERED_NO_GPU",
        "scope": "cas_sonar_and_component_attribution_pilot",
        "execution_order": [
            "sonar_token_signatures",
            "component_attribution_pilot",
            "sae_feature_localization_followup_if_needed",
        ],
        "required_inputs": stage24a_required_inputs(),
        "tracks": [asdict(track) for track in stage24a_tracks()],
        "claim_boundary": stage24a_claim_boundary(),
        "sae_followup": {
            "status": "deferred_not_launch_blocker",
            "trigger": (
                "Run if component attribution is distributed/polysemantic or if exact "
                "feature-level causal localization becomes the explicit research goal."
            ),
            "not_authorized_by_stage24a": True,
        },
    }
    payload["validation"] = validate_stage24a_payload(payload)
    return payload
