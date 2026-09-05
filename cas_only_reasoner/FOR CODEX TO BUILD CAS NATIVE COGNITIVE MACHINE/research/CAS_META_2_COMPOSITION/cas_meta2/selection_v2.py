"""Pure generated-validation scoring. No native-answer correctness claim."""
from __future__ import annotations

import math

from .codec import canonical_sha256, validate_action


def generated_metrics(actions, tasks):
    if type(actions) is not list or type(tasks) is not list or not tasks or len(actions) != len(tasks):
        raise ValueError("GENERATION_DENOMINATOR_INVALID")
    counts = {"valid_programs": 0, "program_correct": 0, "binding_correct": 0, "joint_correct": 0}
    for action, task in zip(actions, tasks, strict=True):
        target = task["target"]
        validate_action(target)
        try:
            validate_action(action)
        except ValueError:
            continue
        counts["valid_programs"] += 1
        program = canonical_sha256(action["program"]) == canonical_sha256(target["program"])
        binding = action["binding"] == target["binding"]
        counts["program_correct"] += int(program)
        counts["binding_correct"] += int(binding)
        counts["joint_correct"] += int(program and binding)
    return {"total": len(tasks), **counts, "all_cases_in_denominator": True,
            "native_execution_performed": False,
            "boundary": "Freely generated exact program and binding, not native task outcome."}


def selection_key(validation):
    """Higher wins. Initial/unmeasured snapshots cannot silently qualify."""
    loss = validation.get("token_cross_entropy")
    if type(loss) not in (int, float) or not math.isfinite(loss) or loss < 0:
        raise ValueError("SELECTION_LOSS_INVALID")
    generation = validation.get("generation")
    if type(generation) is not dict or generation.get("all_cases_in_denominator") is not True:
        raise ValueError("SELECTION_GENERATION_REQUIRED")
    total = generation.get("total")
    if type(total) is not int or total < 1:
        raise ValueError("SELECTION_DENOMINATOR_INVALID")
    fields = ("valid_programs", "program_correct", "binding_correct", "joint_correct")
    for name in fields:
        value = generation.get(name)
        if type(value) is not int or not 0 <= value <= total:
            raise ValueError("SELECTION_COUNT_INVALID:" + name)
    valid, program, binding, joint = (generation[name] for name in fields)
    if max(program, binding) > valid or joint > min(program, binding) or joint < program + binding - valid:
        raise ValueError("SELECTION_COUNTS_INCONSISTENT")
    if generation.get("native_execution_performed") is not False:
        raise ValueError("SELECTION_EVIDENCE_SCOPE_INVALID")
    return (joint / total, program / total, binding / total, -float(loss))
