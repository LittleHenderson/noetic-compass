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
