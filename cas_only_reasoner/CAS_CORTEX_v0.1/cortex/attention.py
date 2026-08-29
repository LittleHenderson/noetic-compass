"""The native CAS-Ohm attention plane, v0.1 slice.

MODE: native_runtime - every quantity here is AUTHORED, exact by
construction (the runtime defines its attention physics the way a
game engine defines gravity). This is NOT the neural profile mode and
NOT a claim about the Transformer's hidden states; the declared bridge
for those lives in the protocol document, unbuilt.

AUTHORITY LAW (protocol section 15, executable discipline): this
module is COMPUTE-ONLY. It reads a finished TurnTrace and returns a
CASOhmStageRecord; nothing in the router's decision path consults it.
A test proves that removing it changes no answer.

Semantics (protocol sections 3, 5, 6, 11):
  V_drive        authored drive rail for a conversational turn
  R_*            authored resistance contributions, activated by the
                 typed gate outcomes the trace already carries
  I_pred         V / R_nominal - the flow the DECLARED nominal
                 constraint model predicts for a clean turn
  I_obs          V / R_total_active - the flow actually admitted
                 through the gate network this turn
  delta_I        I_obs - I_pred: a residual that RANKS probes and
                 never names causes
  operating_region  cutoff / active (region only - semantic outcome
                 is classified separately, and this module cannot see
                 external gold labels)
"""

from __future__ import annotations

from typing import Dict

V_DRIVE = 6.0          # authored conversational drive rail
R_BASE = 1.0           # nominal path resistance, clean turn

# Authored resistance contributions per typed gate outcome.
R_CONTRIB = {
    "native_parse_failed": ("R_capability", 2.0),
    "proposal_rejected": ("R_policy", 8.0),
    "no_packet": ("R_lexical", 4.0),
    "ungrounded": ("R_lexical", 8.0),
    "content_mismatch_R1": ("R_context", 6.0),
    "content_mismatch_R2": ("R_role_binding", 6.0),
    "diagnostic_hold": ("R_policy", 4.0),
}


def stage_record(trace: Dict) -> Dict:
    """Read a sealed TurnTrace; author the native attention record."""
    resistances = {"R_capability": 0.0, "R_lexical": 0.0,
                   "R_role_binding": 0.0, "R_context": 0.0,
                   "R_policy": 0.0, "R_compute": 0.0}

    def add(outcome_key: str) -> None:
        name, value = R_CONTRIB[outcome_key]
        resistances[name] += value

    if trace.get("native_error") is not None:
        add("native_parse_failed")

    validation = trace.get("validation") or {}
    if validation.get("outcome") == "REJECTED":
        add("proposal_rejected")
    elif validation.get("outcome") == "NO_PACKET":
        add("no_packet")
    if (validation.get("grounding") or {}).get("outcome") == "UNGROUNDED":
        add("ungrounded")
    faithfulness = validation.get("faithfulness") or {}
    if faithfulness.get("outcome") == "CONTENT_MISMATCH":
        if faithfulness.get("rule") == "R1_dropped_known_content":
            add("content_mismatch_R1")
        else:
            add("content_mismatch_R2")
    if trace.get("mode") == "CORTEX_DIAGNOSTIC" \
            and trace.get("route") == "cortex" \
            and validation.get("outcome") == "ACCEPTED":
        add("diagnostic_hold")

    r_total = R_BASE + sum(resistances.values())
    i_pred = round(V_DRIVE / R_BASE, 4)
    i_obs = round(V_DRIVE / r_total, 4)
    committed = bool(trace.get("committed"))

    return {
        "mode": "native_runtime",
        "stage_id": "language_pipeline",
        "V_drive": V_DRIVE,
        **{k: round(v, 4) for k, v in resistances.items()},
        "R_total": round(r_total, 4),
        "I_pred": i_pred,
        "I_obs": i_obs,
        "delta_I": round(i_obs - i_pred, 4),
        "operating_region": "active" if committed else "cutoff",
        "effect_type": (trace.get("answer") or {}).get("status"),
        "semantic_outcome": "not classified here - external grading "
                            "only; healthy flow does not imply a "
                            "correct effect",
        "uncertainty": "authored quantities, exact by construction; "
                       "no empirical claim about any neural substrate",
        "provenance": "cas_ohm_attention_plane_v0.1",
        "authority_note": "compute-only: no truth, validity, meaning, "
                          "commitment, or permission decision may read "
                          "this record",
    }
