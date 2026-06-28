"""
claim_map.py — The canonical Claim Map: the single source of truth for what
the swarm may assert about CAS Harness, and the evidence tier each claim sits in.

Both the agent authority layer (agent.py) and the bridge (bridge.py) import
from here, so there is exactly ONE definition of the reserved-language
discipline. Previously the tier sets and the claim-id inference lived inside
bridge.py while the agents referenced claim-id strings by hand — two places
that could drift apart. Co-locating them here makes the Claim Map authoritative
for every layer that touches it.

In production this module is generated from the canonical Claim Map artifact
and the inference is embedding-based; mirrored here in code form with a keyword
matcher for scaffold completeness.
"""

from __future__ import annotations
from typing import Optional


# ──────────────────────────────────────────────────────────────────────
# THE THREE TIERS
# ──────────────────────────────────────────────────────────────────────

LICENSED_CLAIMS = {
    "reads_cognitive_structure",
    "causally_load_bearing_for_cognitive_readout",
    "conditions_next_token_distribution",
    "framework_predicted_mechanism",
    "emits_evidence_packet_with_chain_of_custody",
    "bit_identically_reproducible",
    "non_mutating_two_pass_inference",
    "cross_architecture_validated_pythia_olmo_qwen",
}

FRAMEWORK_PREDICTED_CLAIMS = {
    "may_generalize_to_other_decoder_only_architectures",
    "may_support_multi_turn_reconstruction",
}

# These are the third rail. Any agent output containing one of these — at any
# tier — gets the entire message suppressed at the bridge.
NOT_LICENSED_CLAIMS = {
    "steers_generation_at_scale",
    "reads_any_models_internal_state",
    "replaces_black_box_auditing",
    "reads_the_models_mind",
    "works_on_closed_api_models",
    "works_on_gpt_claude_gemini",
    "validated_on_encoder_only_architectures",
    "produces_anthropomorphized_cognition_reports",
}

# Sentinel returned by infer_claim_id when no canonical claim is recognized.
UNKNOWN_CLAIM = "unknown_claim"


# ──────────────────────────────────────────────────────────────────────
# CLAIM-ID INFERENCE AND TIER LOOKUP
# ──────────────────────────────────────────────────────────────────────

def infer_claim_id(claim_text: str) -> str:
    """
    Map free-text claim to its canonical identifier.

    Production uses an embedding-based lookup against the canonical Claim Map
    (recognizing paraphrases). The scaffold uses keyword matching: specific
    patterns are checked before generic ones, and the first match wins.
    Returns UNKNOWN_CLAIM when nothing matches — the Claim Map is ground truth,
    so an unrecognized claim is treated as out-of-vocabulary, not waved through.
    """
    t = claim_text.lower()

    # ─── NOT_LICENSED third-rail patterns (checked first) ───
    if "steer" in t and "generation" in t:
        return "steers_generation_at_scale"
    if "read" in t and "mind" in t:
        return "reads_the_models_mind"
    if "claude" in t or "gpt-" in t or "gemini" in t:
        return "works_on_closed_api_models"
    if "replace" in t and "black" in t and "box" in t:
        return "replaces_black_box_auditing"

    # ─── LICENSED patterns ───
    if "reads cognitive structure" in t or "cognitive structure" in t:
        return "reads_cognitive_structure"
    if "evidence packet" in t:
        return "emits_evidence_packet_with_chain_of_custody"
    if "conditions" in t and "distribution" in t:
        return "conditions_next_token_distribution"
    if "non-mutating" in t or "two-pass" in t:
        return "non_mutating_two_pass_inference"
    if "bit-identical" in t or "bit identical" in t:
        return "bit_identically_reproducible"
    if (
        ("architecture" in t and ("families" in t or "family" in t or "cross" in t))
        or "pythia" in t
        or "olmo" in t
        or "qwen" in t
    ):
        return "cross_architecture_validated_pythia_olmo_qwen"

    # ─── FRAMEWORK_PREDICTED patterns ───
    if "may generalize" in t:
        return "may_generalize_to_other_decoder_only_architectures"
    if "multi-turn" in t or "multi turn" in t:
        return "may_support_multi_turn_reconstruction"

    return UNKNOWN_CLAIM


def tier_of(claim_id: str) -> Optional[str]:
    """
    Return the tier a claim_id belongs to ("LICENSED", "FRAMEWORK_PREDICTED",
    "NOT_LICENSED"), or None if the id is not in the Claim Map at all.
    """
    if claim_id in LICENSED_CLAIMS:
        return "LICENSED"
    if claim_id in FRAMEWORK_PREDICTED_CLAIMS:
        return "FRAMEWORK_PREDICTED"
    if claim_id in NOT_LICENSED_CLAIMS:
        return "NOT_LICENSED"
    return None
