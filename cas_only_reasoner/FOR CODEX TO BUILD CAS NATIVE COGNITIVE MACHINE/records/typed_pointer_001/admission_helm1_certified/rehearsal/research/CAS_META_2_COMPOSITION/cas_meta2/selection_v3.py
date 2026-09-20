"""Pure candidate scoring and fixed training-token weights, not task verification.

No model, parser, native execution, file access, or private-test access belongs
here. A caller supplies development tasks and freely generated candidate actions.
"""
from __future__ import annotations

from fractions import Fraction
import math

from .codec import action_to_tokens, validate_action
from .ir import validate_program
from .selection_v2 import generated_metrics, selection_key as validate_old_score

SCHEMA = "cas-meta2-depth-selection/3"
SEMANTIC_LOSS_WEIGHT = 3.0
STRUCTURAL_LOSS_WEIGHT = 1.0
SEMANTIC_ROLES = frozenset(("observation_binding", "procedure_name", "step_kind",
                           "run_cjt", "call_target", "step_input", "return_value"))
COUNT_FIELDS = ("total", "valid_programs", "program_correct", "binding_correct", "joint_correct")


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _depths(value):
    _require(type(value) in (list, tuple) and value and all(type(n) is int and 1 <= n <= 32 for n in value)
             and list(value) == sorted(set(value)), "V3_SORTED_UNIQUE_DEPTHS_REQUIRED")
    return tuple(value)


def depth_generated_metrics(actions, tasks, *, expected_depths=(1, 2, 3)):
    """Keep every rejection; derive depth from the actual target's checked IR."""
    depths = _depths(expected_depths)
    total = generated_metrics(actions, tasks)
    rows = {depth: [] for depth in depths}
    for index, task in enumerate(tasks):
        depth = validate_program(task["target"]["program"])["max_call_depth"]
        _require(depth in rows, "V3_UNREGISTERED_VALIDATION_DEPTH")
        if "provenance" in task and "depth" in task["provenance"]:
            _require(type(task["provenance"]["depth"]) is int
                     and task["provenance"]["depth"] == depth, "V3_TARGET_DEPTH_MISMATCH")
        rows[depth].append(index)
    _require(all(rows.values()), "V3_MISSING_VALIDATION_DEPTH")
    groups = {str(depth): generated_metrics([actions[i] for i in indices], [tasks[i] for i in indices])
              for depth, indices in rows.items()}
    return {"schema": SCHEMA, "expected_depths": list(depths), "overall": total, "by_depth": groups,
            "boundary": "Development program/binding match, not native task correctness. Caller must keep test data out."}


def selection_key(validation, *, expected_depths=(1, 2, 3)):
    """Higher wins: worst depth, macro depth, overall joint, lower loss, earlier."""
    _require(type(validation) is dict, "V3_VALIDATION_RECORD_REQUIRED")
    loss = validation.get("token_cross_entropy")
    _require(type(loss) in (int, float) and math.isfinite(loss) and loss >= 0, "V3_INVALID_SELECTION_LOSS")
    epoch = validation.get("epoch")
    _require(type(epoch) is int and epoch >= 1, "V3_MEASURED_TRAINING_EPOCH_REQUIRED")
    scored = validation.get("generation")
    _require(type(scored) is dict and scored.get("schema") == SCHEMA, "V3_DEPTH_GENERATION_REQUIRED")
    depths = _depths(scored.get("expected_depths"))
    _require(depths == _depths(expected_depths), "V3_REGISTERED_DEPTHS_CHANGED")
    groups = scored.get("by_depth")
    _require(type(groups) is dict and set(groups) == {str(depth) for depth in depths}, "V3_DEPTH_COVERAGE_MISMATCH")
    overall = scored.get("overall")
    validate_old_score({"token_cross_entropy": loss, "generation": overall})
    rates = []
    for depth in depths:
        group = groups[str(depth)]
        validate_old_score({"token_cross_entropy": loss, "generation": group})
        rates.append(Fraction(group["joint_correct"], group["total"]))
    _require(all(sum(groups[str(depth)][key] for depth in depths) == overall[key] for key in COUNT_FIELDS),
             "V3_DEPTH_TOTALS_MISMATCH")
    return (min(rates), sum(rates) / len(rates), Fraction(overall["joint_correct"], overall["total"]),
            -float(loss), -epoch)


def target_token_roles(action, *, max_length=512):
    """Training-only labels in the frozen codec's exact token order, including BOS."""
    validate_action(action)
    tokens = action_to_tokens(action, max_length=max_length)
    roles = ["bos", "observation_binding"]
    for _, procedure in sorted(action["program"]["procedures"].items(), key=lambda item: (item[0] != "main", item[0])):
        roles.extend(("proc_marker", "procedure_name", "allow_marker"))
        roles.extend("allowed_cjt" for _ in procedure["allowed_cjts"])
        roles.append("endallow_marker")
        for step in procedure["steps"]:
            roles.extend(("step_kind", "call_target" if step["kind"] == "CALL" else "run_cjt",
                          "step_input", "step_output"))
        roles.extend(("return_marker", "return_value", "endproc_marker"))
    roles.append("eos")
    _require(len(roles) == len(tokens), "V3_TOKEN_ROLE_ALIGNMENT_FAILURE")
    return tuple(roles)


def target_loss_weights(action, *, max_length=512):
    """One positive fixed weight per next-token target; BOS is not predicted."""
    return tuple(SEMANTIC_LOSS_WEIGHT if role in SEMANTIC_ROLES else STRUCTURAL_LOSS_WEIGHT
                 for role in target_token_roles(action, max_length=max_length)[1:])
