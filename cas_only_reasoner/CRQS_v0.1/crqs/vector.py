"""The twelve-dimension Capability Vector, computed from topology and
suite evidence. Domain skills are reported separately and never mixed
into the core score."""

from __future__ import annotations

from typing import Dict, List, Tuple

DIMENSIONS = (
    "semantic_representation", "inference_validity", "deliberation",
    "memory", "planning_recursion", "uncertainty_discipline",
    "learning", "self_improvement", "robustness_stability",
    "traceability", "efficiency", "governance",
)

# Each dimension: (topology flag or suite name, points). Sum capped at 5.0.
RUBRIC: Dict[str, List[Tuple[str, float]]] = {
    "semantic_representation": [("language", 1.5), ("semantic_memory", 1.5),
                                ("provenance", 1.0), ("cassem", 1.0)],
    "inference_validity": [("inference", 2.0), ("mathematics", 1.5),
                           ("kernel_conformance", 1.5)],
    "deliberation": [("branches", 1.5), ("cdab", 1.5),
                     ("commitment_latch", 1.0), ("rollback", 1.0)],
    "memory": [("working_memory", 1.0), ("episodic_memory", 1.5),
               ("semantic_memory", 1.0), ("lacunarity", 1.5)],
    "planning_recursion": [("rpm_stack", 3.0),
                           ("kernel_conformance", 2.0)],
    "uncertainty_discipline": [("typed_uncertainty", 2.5),
                               ("lacunarity", 1.5), ("cassem", 1.0)],
    "learning": [("learning_writeback", 1.5), ("procedural_learning", 1.5),
                 ("rlp", 1.0), ("ccb_l1", 1.0)],
    "self_improvement": [("self_improvement", 2.5), ("rlp", 1.5),
                         ("rollback", 1.0)],
    "robustness_stability": [("typed_uncertainty", 1.5),
                             ("rollback", 1.0), ("governance", 1.0),
                             ("adversarial_suite", 1.5)],
    "traceability": [("trace_replay", 2.5), ("kernel_conformance", 2.5)],
    "efficiency": [("budget_management", 2.0), ("rlp", 1.0)],
    "governance": [("governance", 2.5), ("kernel_conformance", 2.5)],
}


def compute_vector(manifest: Dict) -> Dict:
    topology = manifest.get("topology", {})
    suites = {s.get("name"): s for s in manifest.get("evidence", {}).get("suites", [])}

    def present(key: str) -> bool:
        if key in topology:
            return bool(topology[key])
        suite = suites.get(key)
        return bool(suite and suite.get("passed", 0) == suite.get("tests", 0))

    vector: Dict[str, float] = {}
    for dim in DIMENSIONS:
        total = 0.0
        for key, points in RUBRIC.get(dim, []):
            if present(key):
                total += points
        vector[dim] = round(min(total, 5.0), 1)
    return vector


def weakest(vector: Dict, n: int = 3) -> List[str]:
    return sorted(vector, key=lambda d: vector[d])[:n]


def strongest(vector: Dict) -> str:
    return max(vector, key=lambda d: vector[d])
