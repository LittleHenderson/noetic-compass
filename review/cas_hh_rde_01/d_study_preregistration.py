"""CAS-HH-RDE-01 / D — predeclared (frozen) diagnostic study.

OWNER: DeepSeek independent reviewer lane. Reviewer-only file.
STATUS: FROZEN BEFORE ANY CONFIRMATION RESULT. Frozen 2026-09-28 by the reviewer,
before the discovery/confirmation split was exercised and before any confirmation
case was scored. Nothing in this file may be edited after a confirmation result
exists; a change requires a new versioned file and an explicit note.

SCOPE OF THIS PILOT (shared directive s.6 ceilings, restated as this study's own)
  hypotheses admitted: 2 of a maximum 2
  candidate configurations: 4 of a maximum 4
  declared conditions including controls: 8 of a maximum 8
  HELM optimizer updates: 0
  discovery/confirmation split: by GRAPH STRUCTURE / FAMILY, never by random rows
  confirmation cases: never used to select the hypothesis, site, intervention or control
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STUDY_ID = "CAS-HH-RDE-01-D-DIAG-1"
VERSION = "1.0-frozen"

# ---------------------------------------------------------------------------
# 1. The first falsifiable diagnostic question
# ---------------------------------------------------------------------------
DIAGNOSTIC_QUESTION = (
    "On the HELM pointer-learner Parts/Reach path, does the existing CAS Harness "
    "capture and intervention machinery reach a real readout site at all, and if it "
    "does not, is that failure reported as INCOMPLETE rather than as a zero-valued "
    "observation?"
)

# ---------------------------------------------------------------------------
# 2. Two hypotheses (the maximum allowed)
# ---------------------------------------------------------------------------
HYPOTHESES = {
    "H1_HOOK_COVERAGE": {
        "statement": ("The unadapted harness capture reaches ZERO declared HELM readout "
                      "sites, and does so SILENTLY: the run completes and no receipt field "
                      "is marked incomplete."),
        "falsified_if": [
            "the coverage probe reports observed_sites > 0 for any declared readout site",
            "an empty capture is marked INCOMPLETE or INVALID instead of yielding an ordinary summary",
            "the harness source contains any generic or HELM-specific layer-lookup fallback",
        ],
        "mechanism_named": ("probe_runner._get_pythia_layers returns model.gpt_neox.layers or None; "
                            "capture_probes logs a warning and yields an empty CaptureState"),
    },
    "H2_INTERVENTION_APPLICATION": {
        "statement": ("A harness-shaped EraserIntervention whose coordinates are (layer, index) "
                      "pairs from the Pythia MLP grid is never applied to a HELM readout tensor, "
                      "so it is a SILENT NO-OP; scoping it to a HELM site by shape makes it apply."),
        "falsified_if": [
            "the Pythia-shaped intervention changes any element of a HELM-shaped readout tensor",
            "a correctly scoped intervention changes an undeclared coordinate",
            "a correctly scoped gain-0.0 intervention (the sham) changes any element",
            "an out-of-range index is clamped instead of refused",
        ],
        "mechanism_named": ("_apply_eraser compares intervention layer ids against the hooked layer "
                            "index and returns the SAME object when no layer matches"),
    },
}

# ---------------------------------------------------------------------------
# 3. Four candidate configurations (the maximum allowed)
# ---------------------------------------------------------------------------
CANDIDATE_CONFIGURATIONS = {
    "C0_UNMODIFIED": {"capture": "off", "intervention": None,
                      "role": "baseline reference for every paired comparison"},
    "C1_PYTHIA_HOOK": {"capture": "harness capture_probes, n_layers=layers(len)",
                       "intervention": None,
                       "role": "tests H1: does the existing hook reach any HELM site"},
    "C2_SHAPED_ERASER": {"capture": "harness capture_probes with an EraserIntervention scoped to a "
                                     "declared HELM readout site by shape",
                         "intervention": "bounded multiplicative suppression, gain declared frozen",
                         "role": "tests H2: does a correctly scoped intervention actually apply"},
    "C3_MATCHED_OFF_PATH": {"capture": "identical to C2 including hook overhead",
                            "intervention": "same size, same rank, same gain, off the declared path",
                            "role": "the matched control that distinguishes targeted effect from "
                                    "nonspecific damage (HH12)"},
}

# ---------------------------------------------------------------------------
# 4. Eight declared conditions including controls
# ---------------------------------------------------------------------------
CONDITIONS = [
    {"id": "A_BASELINE", "config": "C0_UNMODIFIED", "intervention": "none",
     "purpose": "original prediction and score, uninstrumented"},
    {"id": "B_OBSERVED", "config": "C0_UNMODIFIED + capture on", "intervention": "none",
     "purpose": "HH03 passive neutrality against A"},
    {"id": "C_NOOP_SHAM", "config": "C2_SHAPED_ERASER", "intervention": "scoped gain 0.0",
     "purpose": "HH10 sham matches baseline and its state"},
    {"id": "D_TARGET_SUPPRESS", "config": "C2_SHAPED_ERASER", "intervention": "target site, frozen gain",
     "purpose": "the declared intervention"},
    {"id": "E_MATCHED_OFF_PATH", "config": "C3_MATCHED_OFF_PATH", "intervention": "matched control",
     "purpose": "HH12 matched rank/norm/overhead control"},
    {"id": "F_INPUT_ONLY_CONTROL", "config": "C0_UNMODIFIED", "intervention": "none",
     "purpose": "input/metadata-only baseline: same stimulus statistics, no readout claim"},
    {"id": "G_SHUFFLED_LABEL_CONTROL", "config": "C0_UNMODIFIED", "intervention": "none",
     "purpose": "shuffled-label control for any probe-based readout claim (HH08)"},
    {"id": "H_INJECTED_CALIBRATION", "config": "C2_SHAPED_ERASER", "intervention": "deliberately injected fault",
     "purpose": "apparatus calibration ONLY; never counted as a discovered natural HELM defect"},
]

# ---------------------------------------------------------------------------
# 5. Discovery / confirmation split (fixed by graph structure, not by rows)
# ---------------------------------------------------------------------------
SPLIT = {
    "rule": ("discovery and confirmation are separated by GRAPH STRUCTURE / FAMILY. A structure "
             "used to choose the site, gain or control may never appear in confirmation."),
    "discovery": {"role": "name the candidate response configuration and fix the intervention",
                  "selection_frozen_before": "any confirmation case is scored"},
    "confirmation": {"role": "execute the frozen conditions only",
                     "may_not_change": ["hypothesis", "site", "gain", "control", "metric",
                                        "case list", "stopping rule"]},
    "development_panel_note": ("the existing 59-question development set covers six selected "
                               "structures and has guided prior choices; it is NOT an untouched "
                               "final examination and counts alone never identify which questions "
                               "changed"),
}

# ---------------------------------------------------------------------------
# 6. Frozen metrics and stopping rules
# ---------------------------------------------------------------------------
METRICS = {
    "primary": "paired change in checked Parts/Reach task answer, per condition versus A_BASELINE",
    "secondary": ["paired change in the independent evaluator's checked outcome",
                  "CAS readout value at the declared site",
                  "coverage: expected versus observed calls",
                  "charged overhead in bytes and nanoseconds"],
    "not_a_metric": ["probe-score collapse alone (a probe can fail while the task computation is intact)",
                     "aggregate-only accuracy differences used to infer per-item transitions",
                     "any statistic computed after seeing the confirmation result"],
    "uncertainty": ("report paired per-condition effects with family-level outcomes; do not present "
                    "an IID binomial over correlated questions, and do not invent a significance "
                    "threshold after results"),
}
STOPPING_RULES = [
    "stop at the declared condition list; a new condition needs a new frozen version",
    "a null or negative result CLOSES the pilot honestly and is retained",
    "an injected-fault condition calibrates the apparatus and is never reported as a natural defect",
    "no retry of a failed paid job inside this pilot",
    "at 80% of the admitted spend, stop discretionary work and protect the readout/cleanup reserve",
]

# ---------------------------------------------------------------------------
# 7. Claim ladder — what each outcome may and may not be called
# ---------------------------------------------------------------------------
CLAIM_LADDER = {
    "OBSERVED_CONFIGURATION": "activity captured at a named site with recorded shape and round",
    "STIMULUS_SELECTIVE": "the configuration responds differentially to permitted stimulus changes, "
                          "against shuffled/input/metadata controls",
    "CAS_READOUT_SUPPORTED": "a readout maps the configuration onto CAS labels fitted on the "
                             "discovery split only",
    "TASK_CAUSAL_CONTRIBUTION_SUPPORTED": "a matched intervention changes the task answer, not only "
                                          "the probe",
    "TARGETED_REPAIR_GAIN_SUPPORTED": "a deployable remedy without the correct answer at inference "
                                      "time beats its unchanged parent",
    "NATIVE_IMPROVEMENT_POLICY_GAIN_SUPPORTED": "HELM itself chose the improvement; an externally "
                                                "directed fix never qualifies",
}
NOT_SUFFICIENT = [
    "a readout change alone is not a Parts/Reach gain",
    "a projected output coordinate is not automatically a neuron",
    "attention weights or top-K activity are observations, not causal conclusions",
    "suppression degradation without matched controls can be nonspecific damage",
    "a rescue from a gold-chosen donor is a diagnostic upper bound, not deployable improvement",
]


def digest() -> str:
    body = {"study": STUDY_ID, "version": VERSION, "question": DIAGNOSTIC_QUESTION,
            "hypotheses": HYPOTHESES, "configurations": CANDIDATE_CONFIGURATIONS,
            "conditions": CONDITIONS, "split": SPLIT, "metrics": METRICS,
            "stopping": STOPPING_RULES, "claim_ladder": CLAIM_LADDER,
            "not_sufficient": NOT_SUFFICIENT}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def as_dict() -> dict:
    return {"study": STUDY_ID, "version": VERSION, "frozen_digest": digest(),
            "question": DIAGNOSTIC_QUESTION, "hypotheses": HYPOTHESES,
            "configurations": CANDIDATE_CONFIGURATIONS, "conditions": CONDITIONS,
            "split": SPLIT, "metrics": METRICS, "stopping_rules": STOPPING_RULES,
            "claim_ladder": CLAIM_LADDER, "not_sufficient": NOT_SUFFICIENT}


if __name__ == "__main__":
    print(json.dumps(as_dict(), indent=2, sort_keys=True))
