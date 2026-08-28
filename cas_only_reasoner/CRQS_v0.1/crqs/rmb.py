"""The Reference Model Benchmark (RMB): per-dimension reference bands.

The owner's hybrid-machine doctrine (2026-08-28) sets the reporting
law: capability against reference language models is reported PER
DIMENSION against named historical bands - never compressed into a
single equivalence number. A band verdict exists ONLY when the
identical-conditions checklist (spec section 16) is attested and per-
domain results are supplied; otherwise the status is NOT RUN.

Bands are engineering reference points, not finish lines: a smaller,
better-architected machine may sit ABOVE a band in one dimension and
BELOW it in another, and the report says both.
"""

from __future__ import annotations

from typing import Dict, List

# Historical reference bands (sources: the doctrine's citations).
REFERENCE_BANDS: List[Dict] = [
    {"band": "GPT-1", "params": "117M",
     "reference": "Radford et al. 2018, generative pretraining + "
                  "supervised fine-tuning; 9/12 SOTA tasks"},
    {"band": "GPT-2", "params": "1.5B",
     "reference": "Radford et al. 2019, WebText; zero-shot multitask "
                  "behavior, coherent paragraph generation"},
    {"band": "GPT-3", "params": "175B",
     "reference": "Brown et al. 2020, few-shot in-context learning; "
                  "note: 1.3B InstructGPT preferred over 175B GPT-3 "
                  "on instruction following (Ouyang et al. 2022)"},
]

BAND_NAMES = [b["band"] for b in REFERENCE_BANDS]

# Per-domain verdicts. CAS_SPECIFIC marks capabilities the reference
# models do not possess in comparable form (e.g. deterministic replay).
OUTCOMES = ("PASS", "PARTIAL", "BELOW", "ABOVE", "CAS_SPECIFIC")

# Spec section 16: a comparison is valid ONLY under identical conditions.
IDENTICAL_CONDITIONS = (
    "task_set", "input_representation", "tool_permissions",
    "time_budget", "operation_budget", "memory_access",
    "temperature_seed_policy", "scoring_method", "held_out_split",
)


class RMBError(Exception):
    pass


def validate_rmb(rmb: Dict) -> Dict:
    """Validate an RMB block. Returns the normalized block.

    Refuses: single-number equivalence claims, band verdicts without
    the full identical-conditions attestation, unknown bands, unknown
    outcomes. An absent or unrun block normalizes to NOT RUN.
    """
    if not rmb or rmb.get("status") in (None, "NOT RUN"):
        if rmb and rmb.get("bands"):
            raise RMBError("band results present but status is NOT RUN")
        return {"status": "NOT RUN"}

    if "equivalence_claim" in rmb or "equivalent_to" in rmb:
        raise RMBError(
            "single-number equivalence claims are refused: report per "
            "dimension against named bands")

    if rmb.get("status") != "RUN":
        raise RMBError(f"unknown RMB status {rmb.get('status')!r}")

    conditions = rmb.get("identical_conditions", {})
    missing = [c for c in IDENTICAL_CONDITIONS if not conditions.get(c)]
    if missing:
        raise RMBError(
            "band verdicts require the identical-conditions attestation; "
            "missing: " + ", ".join(missing))

    bands = rmb.get("bands", [])
    if not bands:
        raise RMBError("status RUN requires at least one band result")
    for band in bands:
        if band.get("band") not in BAND_NAMES:
            raise RMBError(f"unknown reference band {band.get('band')!r}")
        domains = band.get("domains", [])
        if not domains:
            raise RMBError(f"band {band['band']} carries no domain results")
        for domain in domains:
            if domain.get("outcome") not in OUTCOMES:
                raise RMBError(
                    f"unknown outcome {domain.get('outcome')!r} in band "
                    f"{band['band']}")
            if not domain.get("evidence"):
                raise RMBError(
                    f"domain {domain.get('domain')!r} in band "
                    f"{band['band']} has no evidence artifact")
    return rmb


def band_summary(band: Dict) -> str:
    """One line per band: PASS if all domains pass, PARTIAL otherwise."""
    outcomes = [d["outcome"] for d in band.get("domains", [])]
    if all(o in ("PASS", "ABOVE", "CAS_SPECIFIC") for o in outcomes):
        verdict = "PASS"
    elif all(o == "BELOW" for o in outcomes):
        verdict = "BELOW"
    else:
        verdict = "PARTIAL"
    return f"{band['band']} band: {verdict}"


def format_rmb(rmb: Dict) -> List[str]:
    """Render the RMB section lines for the section-10 report."""
    block = validate_rmb(rmb)
    if block.get("status") == "NOT RUN":
        return ["    NOT RUN"]
    lines: List[str] = []
    for band in block["bands"]:
        lines.append(f"    {band_summary(band)}")
        for domain in band.get("domains", []):
            label = domain.get("domain", "?")
            outcome = domain["outcome"]
            if outcome == "CAS_SPECIFIC":
                outcome = "CAS-specific capability"
            lines.append(f"        {label}: {outcome}")
    return lines
