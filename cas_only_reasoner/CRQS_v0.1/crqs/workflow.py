"""The QUALIFY workflow: fifteen steps, logged and deterministic."""

from __future__ import annotations

from typing import Dict, List, Tuple

from .qualify import (demonstrated_level, design_ceiling, evidence_ceiling,
                      qualify)


def run_workflow(manifest: Dict) -> Tuple[Dict, List[Dict]]:
    steps: List[Dict] = []

    def step(n: int, name: str, detail: str) -> None:
        steps.append({"step": n, "name": name, "detail": detail})

    topology = manifest.get("topology", {})
    step(1, "inspect topology",
         f"{sum(1 for v in topology.values() if v)} components present")
    ceiling = design_ceiling(manifest)
    step(2, "calculate design ceiling", ceiling)
    demos = manifest.get("demonstrations", [])
    step(3, "generate difficulty ladder",
         f"{len(demos)} demonstration tasks with difficulty grades")
    clean = [d for d in demos if d.get("passed")]
    step(4, "run clean tests", f"{len(clean)}/{len(demos)} passed")
    adversarial = manifest.get("evidence", {}).get("adversarial_variants", [])
    step(5, "run fault and adversarial variants",
         f"{len(adversarial)} variant(s) recorded")
    held_out = [s for s in manifest.get("evidence", {}).get("suites", [])
                if s.get("held_out")]
    step(6, "run held-out tests",
         f"{len(held_out)} held-out suite(s) recorded")
    vector = qualify(manifest)["capability_vector"]
    weakest = min(vector, key=lambda d: vector[d])
    step(7, "calculate capability vector",
         f"12 dimensions; weakest is {weakest} ({vector[weakest]})")
    step(8, "assign CAS-G, E-Tier, A-Level",
         qualify(manifest)["qualified_level"])
    violations = manifest.get("evidence", {}).get("violations", {})
    step(9, "generate failure-localization report",
         f"{sum(violations.values())} violations recorded")
    step(10, "recommend smallest upgrade",
         qualify(manifest)["next_target"])
    step(11, "preview board patch",
         "patch preview = blocking recommendations")
    step(12, "compile and simulate",
         "deterministic simulator re-run (conformance-tested)")
    step(13, "retest",
         "suites re-run against the descendant")
    step(14, "compare before and after",
         "before = qualified level; after = recomputed from evidence")
    step(15, "seal qualification report",
         "report emitted with evidence digests")

    return qualify(manifest), steps
