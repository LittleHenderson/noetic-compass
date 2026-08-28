"""The repair recommendation ontology: failure signature -> deficiency
-> improvement, with the mandated repair ordering."""

from __future__ import annotations

from typing import Dict, List

SIGNATURES: List[Dict] = [
    {"signature": "wrong entities or roles",
     "deficiency": "semantic encoder fault",
     "improvement": "add CAS-Sem typing, role binding, round-trip tests"},
    {"signature": "fluent answer with no derivation",
     "deficiency": "candidate generator bypassed inference",
     "improvement": "require ^6 -> ^9 proof path before commitment"},
    {"signature": "always chooses first answer",
     "deficiency": "no deliberation",
     "improvement": "add branch manager and minimum candidate policy"},
    {"signature": "comparison seems unfair",
     "deficiency": "split bias or mismatched gain",
     "improvement": "one shared bias and matched comparator branches"},
    {"signature": "correct facts not recalled",
     "deficiency": "memory retrieval fault",
     "improvement": "add CMB indexing, provenance, refresh, query tests"},
    {"signature": "invents missing information",
     "deficiency": "no lacunarity or uncertainty state",
     "improvement": "add NEEDS_INFORMATION and memory-gap detection"},
    {"signature": "loses parent problem",
     "deficiency": "RPM stack failure",
     "improvement": "parent ID, return address, resume stage, cycle tests"},
    {"signature": "repeatedly changes decision",
     "deficiency": "commitment chatter",
     "improvement": "Schmitt hysteresis and stable commit thresholds"},
    {"signature": "loops without progress",
     "deficiency": "oscillation or missing halt logic",
     "improvement": "loop limit, progress metric, typed terminal status"},
    {"signature": "learns one example but not variants",
     "deficiency": "memorization without transfer",
     "improvement": "structural hold-outs and curriculum variation"},
    {"signature": "new skill damages old skills",
     "deficiency": "ungoverned write-back",
     "improvement": "protected regression suite and rollback"},
    {"signature": "self-modification changes its judge",
     "deficiency": "evaluator contamination",
     "improvement": "freeze verifier and benchmarks outside mutation authority"},
    {"signature": "healthy aggregate hides a failing branch",
     "deficiency": "hidden child failure",
     "improvement": "preserve child probes and per-branch reporting"},
    {"signature": "trace has unexplained state jumps",
     "deficiency": "unauthorized mutation",
     "improvement": "typed intents and a sole-writer coordinator"},
]

REPAIR_ORDER = [
    "safety and authority violations",
    "incorrect inference",
    "missing prerequisite machinery",
    "memory and provenance",
    "robustness",
    "learning",
    "efficiency",
    "additional capability",
]

MISSING_TOOL_RECOMMENDATIONS = [
    "add typed ToolIntent with capability and permission checks",
    "add fault-injection and adversarial-framing test variants",
    "add resource-exhaustion and budget-management halting tests",
    "add clarification requests for ambiguous or hostile inputs",
]


# Derived upgrade paths. MISSING_TOOL_RECOMMENDATIONS above stays as the
# G7 entry; every other target is derived from the manifest itself so the
# report never prints a recommendation the machine has already met.
SUITE_DEMANDS = {
    "CAS-G1": "one controlled cause-bias-effect junction suite",
    "CAS-G2": "a three-stage cascade suite with fault injection",
    "CAS-G3": "modus ponens, transitive, contradiction, missing premise",
    "CAS-G4": "three candidates under one shared bias, with rollback",
    "CAS-G5": "a memory-dependent before/after suite",
    "CAS-G6": "parent-child-parent recursion with return addresses",
    "CAS-G7": "paraphrase, noise, adversarial framing, tool failure, "
              "resource exhaustion",
    "CAS-G8": "correction, delayed retention, structural transfer, "
              "protected regression",
    "CAS-G9": "self-diagnosis, sandbox, reject-unauthorized, promote, "
              "parent replay",
    "CAS-G10": "a multi-domain long-horizon suite",
}


def upgrade_path(manifest, target, requirements):
    """Concrete steps from the current qualification to `target`.

    Derived, never asserted: missing topology flags, the missing
    qualification suite, and the demonstration the target still needs.
    """
    if target not in SUITE_DEMANDS:
        return [
            "CAS-GΩ is a research designation, not a qualification "
            "tier: multi-Mind collaboration, open-ended research, an "
            "expanding ecosystem - there is no gate to clear and no "
            "level to award"]
    recommendations = []
    topology = manifest.get("topology", {})
    missing = [flag for flag in requirements.get(target, [])
               if not topology.get(flag)]
    for flag in missing:
        recommendations.append(f"build the missing {target} machinery: {flag}")
    evidence = manifest.get("evidence", {})
    suites = {s.get("name") for s in evidence.get("suites", [])}
    if f"suite_{target}" not in suites:
        recommendations.append(
            f"run the {target} qualification suite: {SUITE_DEMANDS[target]}")
    needed = int(target.split("G")[1])
    stable = 0
    for demo in manifest.get("demonstrations", []):
        if demo.get("passed") and demo.get("stable"):
            stable = max(stable, int(demo["difficulty_grade"][1:]))
    if stable < needed:
        recommendations.append(
            f"demonstrate a STABLE D{needed} task "
            f"(the stable ceiling today is D{stable})")
    held_out = [s.get("name") for s in evidence.get("suites", [])
                if s.get("name", "").startswith("suite_")
                and not s.get("held_out")]
    if held_out:
        recommendations.append(
            "move these suites to held-out fixtures before the level is "
            "claimed: " + ", ".join(sorted(held_out)))
    if not recommendations:
        recommendations.append(
            f"no derived gap remains for {target}: seal the evidence and "
            f"re-qualify")
    return recommendations
