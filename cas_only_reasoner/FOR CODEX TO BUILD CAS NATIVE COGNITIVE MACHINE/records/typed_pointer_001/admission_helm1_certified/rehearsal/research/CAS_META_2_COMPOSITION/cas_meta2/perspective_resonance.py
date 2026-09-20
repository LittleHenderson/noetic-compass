"""Opt-in connected presentation and read-only response profiles; no torch imports.

Native routing and calibrated activation response are different namespaces.
The selected recurrent student's _DecomposeTransform has no native flow producer
or intervention port. Missing measurements are explicit, never inferred.
"""
from __future__ import annotations

import copy
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

from .graph_teaching.graph import canonical, digest, require

SCHEMA = "cas.perspective-resonance/0.1"
DIRECTIVE = "CAS_PERSPECTIVE_RESONANCE_001"
CONDITIONS = ("CANONICAL_REVISIT", "CONNECTED_PERSPECTIVES")
DIMENSIONS = ("mental_formal", "physical_action_record",
              "emotional_purpose_context", "analogy", "context")
PRIVATE_FIELDS = frozenset(("correct", "expected_answer", "encoded_correct_index",
                            "teacher_target", "teacher_targets"))
NATIVE_STATUS = "UNAVAILABLE_NO_NATIVE_FLOW_TAP"
EMPIRICAL_STATUS = "UNAVAILABLE_NO_APPROVED_INTERVENTION_PORT"
NATIVE_PRODUCER_SHA256 = "03521d2b17311680fd91cde7076e4bf5b38393f0d6db115d47be20f63413fc96"


def identity(value):
    return digest(canonical(value))


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _no_private(value):
    if isinstance(value, dict):
        require(not PRIVATE_FIELDS.intersection(value), "PRIVATE_TARGET_IN_PUBLIC")
        for item in value.values():
            _no_private(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _no_private(item)


def _edges(graph):
    require(graph.get("inventory_complete") is True, "UNKNOWN_IS_NOT_ABSENT")
    nodes = graph["nodes"]
    require(len(nodes) == len(set(nodes)) and nodes, "INVALID_NODES")
    edges = [tuple(edge) for edge in graph["contains"]]
    require(len(edges) == len(set(edges)), "DUPLICATE_DIRECTED_EDGE")
    require(all(len(edge) == 2 and edge[0] != edge[1] and
                all(node in nodes for node in edge) for edge in edges),
            "INVALID_DIRECTED_ENDPOINT")
    return set(edges)


def reference_answer(public):
    """Pure checker for authored complete containment scenes, not an inference model."""
    edges = _edges(public["graph"])
    args = public["question"]["named_arguments"]
    whole = args["whole_id"]
    require(whole in public["graph"]["nodes"], "UNKNOWN_WHOLE")
    direct = sorted(b for a, b in edges if a == whole)
    operation = public["question"]["operation"]
    if operation == "LIST_PARTS":
        return direct
    require(operation == "REACHED_VIA", "UNSUPPORTED_PERSPECTIVE_OPERATION")
    candidate = args["candidate_id"]
    require(candidate in public["graph"]["nodes"], "UNKNOWN_CANDIDATE")
    if candidate in direct:
        return "direct"
    via = sorted(part for part in direct if (part, candidate) in edges)
    require(len(via) <= 1, "AMBIGUOUS_TWO_HOP_ROUTE")
    return "via:" + via[0] if via else "absent"


def semantic_answer(value, mapping):
    """Map labels to base coordinates; never compare option slots."""
    inverse = {view: base for base, view in mapping.items()}
    require(len(inverse) == len(mapping), "NONINJECTIVE_CORRESPONDENCE")
    if isinstance(value, list):
        require(all(item in inverse for item in value), "UNMAPPED_ANSWER")
        return sorted(inverse[item] for item in value)
    if isinstance(value, str) and value.startswith("via:"):
        require(value[4:] in inverse, "UNMAPPED_ANSWER")
        return "via:" + inverse[value[4:]]
    if isinstance(value, str) and value in inverse:
        return inverse[value]
    require(value in ("direct", "absent", "none"), "UNSUPPORTED_SEMANTIC_ANSWER")
    return value


def validate_family(family):
    base = family["base_graph"]
    base_edges = _edges(base)
    require(len({view["variant_id"] for view in family["views"]}) ==
            len(family["views"]), "DUPLICATE_VARIANT")
    for view in family["views"]:
        mapping = view["base_to_view_map"]
        require(set(mapping) == set(base["nodes"]) and
                set(mapping.values()) == set(view["graph"]["nodes"]) and
                len(set(mapping.values())) == len(mapping),
                "INCOMPLETE_DIRECTED_MAPPING")
        current = _edges(view["graph"])
        mapped = {(mapping[a], mapping[b]) for a, b in base_edges}
        if view["preserves_scoped_relation"]:
            require(current == mapped, "DIRECTED_RELATION_NOT_PRESERVED")
            require(view["relation_change"] == "NONE", "CONFLICTING_INVARIANCE")
        else:
            require(view["relation_change"] == "MOVE_WRENCH_TO_KIT",
                    "UNSUPPORTED_RELATION_CHANGE")
            expected = mapped - {(mapping["Toolbox"], mapping["Wrench"])}
            expected.add((mapping["Kit"], mapping["Wrench"]))
            require(current == expected, "DECLARED_REWIRING_MISMATCH")
        actions = view.get("authored_actions")
        if actions is not None:
            require({(a["container"], a["item"]) for a in actions} == current,
                    "ACTION_RECORD_GRAPH_MISMATCH")
    return True


def compile_family(family, public_rows, targets):
    """Compile supplied authored examples into the real three-slot public codec.

    Public ids/order are computed before the teacher join. The private join only
    supplies supervised labels and validates authoring, never inference inputs.
    """
    validate_family(family)
    views = {view["variant_id"]: view for view in family["views"]}
    public_index = {}
    for row in public_rows:
        _no_private(row)
        key = row["exercise_id"]
        require(key not in public_index, "DUPLICATE_PUBLIC_EXERCISE")
        require(key == "exercise:" + identity({k: v for k, v in row.items()
                                               if k != "exercise_id"}),
                "PUBLIC_EXERCISE_ID_MISMATCH")
        require(len(row["choices"]) == 3 and
                len({identity(c) for c in row["choices"]}) == 3,
                "THREE_DISTINCT_PUBLIC_CHOICES_REQUIRED")
        graph = row["graph"]
        _edges(graph)
        lines = ["node " + node + " kind=idea" for node in graph["nodes"]]
        lines += ["rel " + a + " contains " + b + " common=constituent," + b
                  for a, b in graph["contains"]]
        args = row["question"]["named_arguments"]
        problem = row["context_text"] + "\n" + "\n".join(lines)
        problem += "\nQuestion: " + row["question"]["operation"] + " " + json.dumps(args, sort_keys=True)
        public = {"problem": problem, "observations": [
            {"slot": i, "tag": json.dumps(option, sort_keys=True),
             "values": [0.0] * 8} for i, option in enumerate(row["choices"])]}
        public_index[key] = {"record_id": identity(public), "public": public,
                             "options": copy.deepcopy(row["choices"])}
    require(len(targets) == len(public_index) and
            {t["exercise_id"] for t in targets} == set(public_index),
            "TEACHER_JOIN_MISMATCH")
    private = []
    pairs = {}
    for target in targets:
        source = next(row for row in public_rows if row["exercise_id"] == target["exercise_id"])
        require(reference_answer(source) == target["expected_answer"],
                "TEACHER_TARGET_NOT_SUPPORTED")
        view = views[target["variant_id"]]
        require(source["graph"] == view["graph"], "VARIANT_GRAPH_JOIN_MISMATCH")
        require(sum(option == target["expected_answer"] for option in source["choices"]) == 1,
                "TEACHER_TARGET_NOT_UNIQUE")
        record = public_index[target["exercise_id"]]
        private.append({"record_id": record["record_id"], "exercise_id": target["exercise_id"],
                        "root_family_id": family["root_family_id"],
                        "variant_id": target["variant_id"],
                        "operation": source["question"]["operation"],
                        "base_to_view_map": view["base_to_view_map"],
                        "expected_answer": target["expected_answer"],
                        "semantic_expected_answer": semantic_answer(
                            target["expected_answer"], view["base_to_view_map"])})
        pairs[(target["variant_id"], source["question"]["operation"])] = private[-1]
    comparisons = []
    for operation in ("REACHED_VIA", "LIST_PARTS"):
        baseline = pairs[("formal", operation)]
        for view in family["views"]:
            if view["variant_id"] == "formal":
                continue
            other = pairs[(view["variant_id"], operation)]
            equal = baseline["semantic_expected_answer"] == other["semantic_expected_answer"]
            require(equal == view["preserves_scoped_relation"], "QUESTION_CONTRAST_NOT_SUPPORTED")
            comparisons.append({"root_family_id": family["root_family_id"],
                "kind": "invariant" if equal else "changed_relation",
                "left": baseline["record_id"], "right": other["record_id"]})
    return {"schema": SCHEMA, "status": "AUTHORED_REFERENCE_ONLY",
            "public": list(public_index.values()), "teacher_targets": private,
            "comparisons": comparisons,
            "manifest": {"public_sha256": identity(list(public_index.values())),
                         "target_sha256": identity(private),
                         "comparison_sha256": identity(comparisons),
                         "rows": len(public_index), "families": 1}}


def transform_public(task, *, round_index, slot_index, condition):
    """Compilation hook into complementary course; input targets never read.

    Maintenance and role-recognition excerpts retain their original presentation.
    Every numerical task keeps its graph, question, options and supported target.
    Context enters the existing tokenizer; no parameter, readout or state changes.
    """
    require(condition in CONDITIONS, "PERSPECTIVE_CONDITION_UNKNOWN")
    require(type(round_index) is int and 0 <= round_index < 16 and
            type(slot_index) is int and 0 <= slot_index < 72, "PERSPECTIVE_SLOT_OUTSIDE_PARENT")
    result = copy.deepcopy(task)
    if condition == "CANONICAL_REVISIT" or slot_index >= 64:
        return result
    public = copy.deepcopy(task["public"])
    _no_private(public)
    # Only explicit graph lines are interpreted. Role excerpts without a complete
    # scene are left intact; made-up physical actions would be misleading there.
    # Guided episodes contain three support graphs then the query graph. Use the
    # last contiguous node/rel block, so the added account has one explicit scope.
    graph_lines, in_graph = [], False
    for line in public["problem"].splitlines():
        if line.startswith(("node ", "rel ")):
            if not in_graph:
                graph_lines = []
            graph_lines.append(line)
            in_graph = True
        else:
            in_graph = False
    edges = re.findall(r"^rel\s+(\S+)\s+(?:--contains-->|contains)\s+(\S+)(?:\s|$)", "\n".join(graph_lines), re.M)
    if not edges:
        return result
    dimension = DIMENSIONS[round_index % len(DIMENSIONS)]
    edges = list(dict.fromkeys(edges))
    if dimension == "mental_formal":
        addition = "The supplied directed containment statements define this complete authored scene."
    elif dimension == "physical_action_record":
        addition = "Authored placement record, not sensor data: " + "; ".join(
            "place " + b + " in " + a for a, b in edges) + "."
    elif dimension == "emotional_purpose_context":
        addition = ("Authored purpose: a careful reviewer wants an accurate account of the supplied scene. "
                    "Their stated concern adds no containment fact.")
    elif dimension == "analogy":
        labels = sorted({node for edge in edges for node in edge})
        mapping = {node: "Folder" + str(index + 1) for index, node in enumerate(labels)}
        addition = "Partial folder comparison (containment only): " + "; ".join(
            node + "=" + mapping[node] for node in labels)
        addition += ". Connections: " + "; ".join(
            mapping[a] + " contains " + mapping[b] for a, b in edges)
        addition += ". Other properties unspecified."
    else:
        addition = ("Irrelevant context variant: the authored scene is described on a quiet afternoon. "
                    "Time of day changes none of its supplied connections.")
    public["problem"] = addition + "\n" + public["problem"]
    result["public"] = public
    result["record_id"] = identity(public)
    result["semantic_question_id"] = task.get("semantic_question_id", task["record_id"])
    result["perspective"] = {"dimension": dimension, "source": "AUTHORED_PUBLIC_GRAPH",
        "assistance": "PUBLIC_RELATION_RESTATEMENT_NO_QUERY_ANSWER",
        "context_status": "AUTHORED_NOT_EMBODIED_OR_AFFECTIVE_EXPERIENCE",
        "added_utf8_bytes": len(addition.encode("utf-8")) + 1}
    return result


def native_flow_snapshot(*, checkpoint_identity, depth):
    """Read-only honest binding for the selected standalone recurrent producer."""
    require(bool(checkpoint_identity) and depth in (1, 2, 4, 8), "NATIVE_CONTEXT_MISSING")
    return {"namespace": "native_flow", "status": NATIVE_STATUS,
            "producer": "cas_cjt.neural._DecomposeTransform",
            "producer_source_sha256": NATIVE_PRODUCER_SHA256,
            "producer_equation": "merge(concat(tanh(left(value)), tanh(right(value))))",
            "selected_runtime": "cas_meta2.recurrent_cjt.learner.RecurrentGraphLearner",
            "checkpoint_identity": checkpoint_identity, "depth": depth,
            "quantity_kind": "UNAVAILABLE", "raw_current": None,
            "total_current": None, "normalized_allocation": None,
            "reason": "Selected operation returns transformed vectors, not CASformer routing telemetry.",
            "architecture_modified": False}


def calibrated_response_request(profile, *, execution_authorized=False):
    """Guard optional measurements; existing student exposes no approved dose port.

    Pure fitting of retained rows is available below. Enabling a profile cannot
    silently insert a neural steering mechanism into the current learner.
    """
    require(execution_authorized is True, "EMPIRICAL_EXECUTION_NOT_AUTHORIZED")
    validate_response_profile(profile)
    raise ValueError(EMPIRICAL_STATUS)


def validate_response_profile(profile):
    required = ("model_identity", "runtime_identity", "input_adapter_identity",
                "tokenizer_identity", "test_point", "direction_identity",
                "intervention_port", "depth", "dose_grid", "calibration_families",
                "calibration_holdout_families", "final_audit_families",
                "units", "max_holdout_rmse", "minimum_positive_slope", "uncertainty_method")
    require(all(k in profile for k in required), "EMPIRICAL_PROFILE_INCOMPLETE")
    require(profile["units"] == {"a": "alpha", "delta_y": "activation",
                                 "r_eff": "alpha_per_activation"}, "EMPIRICAL_UNITS_INCOMPATIBLE")
    sets = [set(profile[k]) for k in ("calibration_families",
            "calibration_holdout_families", "final_audit_families")]
    require(all(sets) and not any(sets[i] & sets[j] for i in range(3) for j in range(i)),
            "CALIBRATION_SPLITS_OVERLAP_OR_EMPTY")
    require(profile["depth"] in (1, 2, 4, 8), "EMPIRICAL_DEPTH")
    require(all(profile[k] for k in required[:7]), "EMPIRICAL_IDENTITY_EMPTY")
    grid = profile["dose_grid"]
    require(len(grid) >= 3 and all(_finite(a) for a in grid) and 0 in grid
            and len(set(grid)) == len(grid), "EMPIRICAL_DOSE_GRID")
    require(_finite(profile["max_holdout_rmse"]) and profile["max_holdout_rmse"] >= 0 and
            _finite(profile["minimum_positive_slope"]) and profile["minimum_positive_slope"] > 0,
            "EMPIRICAL_TOLERANCE")
    require(profile["uncertainty_method"] == "ROOT_FAMILY_BOOTSTRAP_2000",
            "EMPIRICAL_UNCERTAINTY_UNSUPPORTED")
    return identity(profile)


def fit_response(profile, rows):
    """Fit calibration roots, validate holdout roots; never a/y round-trip proof.

    This is ordinary through-origin regression with explicit diagnostics against
    zero, constant, affine and quadratic alternatives. All raw rows are retained.
    """
    profile_id = validate_response_profile(profile)
    allowed = set(profile["calibration_families"]) | set(profile["calibration_holdout_families"])
    indexed = {}
    for row in rows:
        require(row["profile_sha256"] == profile_id, "EMPIRICAL_PROFILE_MISMATCH")
        require(row["root_family_id"] in allowed, "FINAL_AUDIT_USED_FOR_CALIBRATION")
        require(row["a"] in profile["dose_grid"] and _finite(row["delta_y"]), "EMPIRICAL_ROW_INVALID")
        key = (row["root_family_id"], row["a"])
        require(key not in indexed, "DUPLICATE_CALIBRATION_ROW")
        indexed[key] = row
    require(set(indexed) == {(family, dose) for family in allowed for dose in profile["dose_grid"]},
            "INCOMPLETE_CALIBRATION_GRID")
    require(all(indexed[(f, 0)]["delta_y"] == 0 for f in allowed), "BASELINE_SUBTRACTION_MISSING")
    train = [r for r in rows if r["root_family_id"] in profile["calibration_families"]]
    test = [r for r in rows if r["root_family_id"] in profile["calibration_holdout_families"]]
    slope = sum(r["a"] * r["delta_y"] for r in train) / sum(r["a"] ** 2 for r in train)
    rmse = lambda predict: math.sqrt(sum((r["delta_y"] - predict(r["a"])) ** 2 for r in test) / len(test))
    mean_x = sum(r["a"] for r in train) / len(train)
    mean_y = sum(r["delta_y"] for r in train) / len(train)
    affine_slope = sum((r["a"] - mean_x) * (r["delta_y"] - mean_y) for r in train) / sum(
        (r["a"] - mean_x) ** 2 for r in train)
    intercept = mean_y - affine_slope * mean_x
    s2, s3, s4 = (sum(r["a"] ** n for r in train) for n in (2, 3, 4))
    xy, x2y = (sum(r["a"] ** n * r["delta_y"] for r in train) for n in (1, 2))
    determinant = s2 * s4 - s3 * s3
    quadratic = None
    if abs(determinant) > 1e-12:
        b1, b2 = (xy * s4 - x2y * s3) / determinant, (x2y * s2 - xy * s3) / determinant
        quadratic = {"linear": b1, "quadratic": b2, "holdout_rmse": rmse(lambda a: b1 * a + b2 * a * a)}
    roots = list(profile["calibration_families"])
    rng = random.Random(719)
    slopes = []
    for _ in range(2000):
        selected = [rng.choice(roots) for _ in roots]
        sample = [r for f in selected for r in train if r["root_family_id"] == f]
        slopes.append(sum(r["a"] * r["delta_y"] for r in sample) / sum(r["a"] ** 2 for r in sample))
    slopes.sort()
    interval = [slopes[49], slopes[1949]]
    error = rmse(lambda a: a * slope)
    reasons = []
    if slope <= profile["minimum_positive_slope"] or interval[0] <= profile["minimum_positive_slope"]:
        reasons.append("NONPOSITIVE_OR_SIGN_UNCERTAIN_SLOPE")
    if error > profile["max_holdout_rmse"]:
        reasons.append("HOLDOUT_FIT_INADEQUATE")
    if quadratic and error - quadratic["holdout_rmse"] > profile["max_holdout_rmse"]:
        reasons.append("MEANINGFUL_NONLINEARITY")
    return {"namespace": "calibrated_activation_response", "profile_sha256": profile_id,
            "status": "FIT_REJECTED" if reasons else "ESTIMATED_LOCAL_PROFILE",
            "fit_method": "ORDINARY_THROUGH_ORIGIN_LINEAR_REGRESSION",
            "slope": slope, "slope_root_family_interval": interval,
            "r_eff": None if reasons else 1.0 / slope, "holdout_rmse": error,
            "alternatives": {"zero_rmse": rmse(lambda a: 0), "constant_rmse": rmse(lambda a: mean_y),
                "affine_rmse": rmse(lambda a: intercept + affine_slope * a), "quadratic": quadratic},
            "failures": reasons, "raw_rows": copy.deepcopy(rows),
            "native_flow_equivalence": False, "semantic_mastery_claimed": False,
            "measurement_provenance": sorted({str(row.get("provenance", "UNVERIFIED_RETAINED_ROWS")) for row in rows}),
            "instrumentation_verified": False,
            "limitations": ["Small root-family counts can produce degenerate bootstrap intervals.",
                           "No physical law or out-of-profile generalization established."]}


def seal_predictions(rows):
    """No teacher fields can enter the sealed prediction record."""
    _no_private(rows)
    require(len({row["record_id"] for row in rows}) == len(rows), "DUPLICATE_PREDICTION")
    body = copy.deepcopy(rows)
    return {"schema": SCHEMA, "rows": body, "prediction_sha256": identity(body)}


def behavioral_report(sealed, targets, comparisons):
    """Restore correctness after sealing; missing predictions remain in denominator."""
    require(identity(sealed["rows"]) == sealed["prediction_sha256"], "PREDICTION_SEAL_MISMATCH")
    _no_private(sealed["rows"])
    target_index = {row["record_id"]: row for row in targets}
    require(len(target_index) == len(targets), "DUPLICATE_TARGET")
    predictions = {row["record_id"]: row for row in sealed["rows"]}
    require(set(predictions) <= set(target_index), "UNASSIGNED_PREDICTION")
    scored, per_root = {}, {}
    for key, target in target_index.items():
        present = key in predictions
        selected = predictions[key].get("selected") if present else None
        semantic = semantic_answer(selected, target["base_to_view_map"]) if selected is not None else None
        correct = semantic == target["semantic_expected_answer"] if present else False
        scored[key] = {"present": present, "correct": correct, "selected_semantic": semantic}
        counts = per_root.setdefault(target["root_family_id"], {"assigned": 0, "correct": 0, "missing": 0})
        counts["assigned"] += 1
        counts["correct"] += int(correct)
        counts["missing"] += int(not present)
    pair_stats = {}
    for pair in comparisons:
        require(pair["kind"] in ("invariant", "changed_relation"), "PAIR_KIND_UNKNOWN")
        require(pair["left"] in scored and pair["right"] in scored, "PAIR_UNASSIGNED")
        require(target_index[pair["left"]]["root_family_id"] ==
                target_index[pair["right"]]["root_family_id"] == pair["root_family_id"],
                "PAIR_CROSSES_ROOT_FAMILY")
        a, b = scored[pair["left"]], scored[pair["right"]]
        bucket = pair_stats.setdefault(pair["kind"], {"assigned": 0, "both_correct": 0, "agreement": 0, "missing": 0})
        bucket["assigned"] += 1
        bucket["both_correct"] += int(a["correct"] and b["correct"])
        bucket["missing"] += int(not a["present"] or not b["present"])
        bucket["agreement"] += int(a["present"] and b["present"] and
                                   a["selected_semantic"] == b["selected_semantic"])
    return {"schema": SCHEMA, "prediction_sha256": sealed["prediction_sha256"],
            "assigned": len(targets), "observed": len(predictions),
            "correct": sum(row["correct"] for row in scored.values()),
            "missing": len(targets) - len(predictions), "pairs": pair_stats,
            "per_root_family": per_root, "scored": scored,
            "native_flow_status": NATIVE_STATUS, "calibration_status": "UNMEASURED",
            "retention_status": "NOT_MEASURED_BY_THIS_REPORT"}


def paired_root_effect(first, second):
    """Paired root-family mean accuracy difference and clustered bootstrap interval."""
    require(set(first["per_root_family"]) == set(second["per_root_family"]),
            "PAIRED_ROOT_ASSIGNMENTS_DIFFER")
    effects = []
    for root, a in first["per_root_family"].items():
        b = second["per_root_family"][root]
        require(a["assigned"] == b["assigned"] and a["assigned"] > 0, "PAIRED_DENOMINATOR_MISMATCH")
        effects.append((b["correct"] - a["correct"]) / a["assigned"])
    require(effects, "EMPTY_PAIRED_REPORT")
    rng = random.Random(723)
    boot = sorted(sum(rng.choice(effects) for _ in effects) / len(effects) for _ in range(2000))
    return {"effect": sum(effects) / len(effects), "interval": [boot[49], boot[1949]],
            "root_families": len(effects), "method": "PAIRED_ROOT_FAMILY_BOOTSTRAP_2000",
            "small_family_warning": len(effects) < 10}


def shadow_proposal(report, *, evidence_scope):
    require(evidence_scope in ("development", "runtime_qualification"),
            "FINAL_AUDIT_CANNOT_SELECT_LESSONS")
    return {"schema": SCHEMA, "type": "TeachingAdjustmentProposal",
            "mode": "SHADOW_ONLY", "evidence_scope": evidence_scope,
            "evidence_sha256": identity(report),
            "recommendation": "Inspect supported mappings and component/whole errors before changing drive.",
            "adaptive_policy_enabled": False, "direct_control_mutation": False,
            "automatic_pass_increase": False}


def view_coverage(tasks):
    dimensions = Counter(t.get("perspective", {}).get("dimension", "canonical") for t in tasks)
    return {"presentations": len(tasks), "dimensions": dict(dimensions),
            "unique_semantic_questions": len({t.get("semantic_question_id", t["record_id"]) for t in tasks}),
            "families": len({t.get("family_id") for t in tasks if t.get("family_id")}),
            "added_utf8_bytes": sum(t.get("perspective", {}).get("added_utf8_bytes", 0) for t in tasks),
            "token_count": None, "token_count_status": "COUNT_WITH_BOUND_TOKENIZER_AT_PREPARATION",
            "source_support": "One authored graph per question; repeated views are dependent.",
            "exposure_rhythm": "Recorded parent slot order; no physical frequency claim."}

def compile_comparison(seed):
    """Bind both content conditions to one frozen ALT complementary schedule."""
    from .complementary_teaching import course
    base = course.compile_complementary_course(seed, course.CONDITIONS[0])
    schedules = {}
    for condition in CONDITIONS:
        def transform(task, *, _condition=condition, **kwargs):
            return transform_public(task, **dict(kwargs, condition=_condition))
        schedule = course.compile_complementary_course(
            seed, course.CONDITIONS[0], public_transform=transform)
        require(schedule["counts"] == base["counts"], "PERSPECTIVE_CHANGED_CFC_ALLOCATION")
        require(schedule["depths"] == base["depths"], "PERSPECTIVE_CHANGED_DEPTHS")
        changed = sum("perspective" in task for batch in schedule["batches"] for task in batch["tasks"])
        if condition == "CONNECTED_PERSPECTIVES":
            require(changed >= 256, "PERSPECTIVE_CONTENT_NOT_DELIVERED")
        else:
            require(changed == 0 and schedule["batches"] == base["batches"],
                    "PERSPECTIVE_CANONICAL_NOT_UNCHANGED")
        schedules[condition] = schedule
    return {"seed": seed, "parent_schedule_sha256": base["schedule_sha256"],
            "parent_condition": course.CONDITIONS[0], "schedules": schedules,
            "counts_per_learner": base["counts"]}


def idea_response_profile(*, context, sealed_predictions, behavioral=None,
                          response_fit=None, coverage=None, cost=None):
    """Join descriptive axes under a context identity without granting control."""
    required = ("root_family_id", "graph_revision", "cube_revision", "view_revision",
                "model_identity", "checkpoint_identity", "input_adapter_identity",
                "tokenizer_identity", "recurrent_profile", "scoring_profile", "depth",
                "assistance_profile", "source_event_references")
    require(all(key in context and context[key] is not None for key in required),
            "IDEA_CONTEXT_INCOMPLETE")
    require(identity(sealed_predictions["rows"]) == sealed_predictions["prediction_sha256"],
            "PREDICTION_SEAL_MISMATCH")
    if behavioral is not None:
        require(behavioral["prediction_sha256"] == sealed_predictions["prediction_sha256"],
                "BEHAVIOR_FROM_DIFFERENT_PREDICTIONS")
    return {"schema": SCHEMA, "type": "IdeaResponseProfile",
            "display_alias": "vibratory_signature",
            "scope": "MODEL_CHECKPOINT_CONTEXT_AND_MEASUREMENT_RELATIVE",
            "context": copy.deepcopy(context), "context_sha256": identity(context),
            "predictions": copy.deepcopy(sealed_predictions),
            "native_flow": native_flow_snapshot(checkpoint_identity=context["checkpoint_identity"],
                                                depth=context["depth"]),
            "calibrated_activation_response": copy.deepcopy(response_fit) if response_fit else
                {"status": EMPIRICAL_STATUS, "r_eff": None},
            "behavioral_competence": copy.deepcopy(behavioral) if behavioral else {"status":"UNASSESSED"},
            "exposure_rhythm": copy.deepcopy(coverage) if coverage else {"status":"UNASSESSED"},
            "cost": copy.deepcopy(cost) if cost else {"status":"UNASSESSED"},
            "single_resonance_score": None, "physical_frequency_claimed": False,
            "universal_signature_measured": False,
            "adaptive_policy_enabled": False, "direct_control_mutation": False,
            "missingness": ["native flow unavailable", "approved intervention port unavailable"],
            "limitations": ["Software conformance does not establish neural learning.",
                           "Authored purpose and action text are not emotion or embodiment.",
                           "Cold restart is saved-state usability, not biological consolidation."]}


def perspective_panels(base_tasks):
    """Real callback: shared fresh-family cross-view and changed-route audits.

    Mutations are derived from the public graph, never from its target field.
    Derived views retain their parent root family for split/uncertainty grouping.
    """
    from .graph_teaching.graph import Graph, Relation
    from .graph_teaching import reference
    from .complementary_teaching.course import _record_task
    originals = base_tasks["final_application"] if isinstance(base_tasks, dict) else base_tasks
    canonical_tasks, cross_view, changed_tasks = [], [], []
    for task in originals:
        canonical_task = copy.deepcopy(task)
        canonical_task["perspective_pair_kind"] = "canonical"
        canonical_tasks.append(canonical_task)
        viewed = transform_public(task, round_index=3, slot_index=0,
                                  condition="CONNECTED_PERSPECTIVES")
        require(viewed["public"] != task["public"], "CROSS_VIEW_NOT_NUMERICALLY_DELIVERED")
        viewed["perspective_pair_kind"] = "invariant"
        viewed["canonical_record_id"] = task["record_id"]
        cross_view.append(viewed)
        if task["op"] != "REACHED_VIA":
            continue
        graph = Graph.from_record(task["graph"])
        question = task["question"]
        whole, candidate = question["idea"], question["part"]
        direct = any(r.kind == "contains" and r.source == whole and r.target == candidate
                     for r in graph.relations)
        relations = [r for r in graph.relations if not (r.kind == "contains" and r.target == candidate)]
        if not direct:
            relations.append(Relation("contains", whole, candidate, ("constituent", candidate)))
        changed_graph = Graph(nodes=graph.nodes, relations=tuple(relations)).validate()
        answer = reference.reach_kind(changed_graph, candidate, whole)
        require(answer != reference.reach_kind(graph, candidate, whole), "RELATION_CHANGE_NO_ANSWER_CHANGE")
        changed = _record_task(changed_graph, question, copy.deepcopy(task["encoded_options"]),
                               answer, task["family_id"])
        # _record_task shuffles by its public ID. Hold the original three slots
        # fixed so a relation intervention cannot also become an order change.
        changed["encoded_options"] = copy.deepcopy(task["encoded_options"])
        changed["public"]["observations"] = copy.deepcopy(task["public"]["observations"])
        changed["record_id"] = identity(changed["public"])
        changed["encoded_correct_index"] = changed["encoded_options"].index(answer)
        changed["split"] = "final"
        changed["perspective_pair_kind"] = "changed_relation"
        changed["canonical_record_id"] = task["record_id"]
        changed["relation_change"] = ("REMOVE_CANDIDATE_FROM_ALL_CONTAINERS" if direct else
                                     "MOVE_CANDIDATE_DIRECTLY_TO_QUERY_WHOLE")
        changed_tasks.append(changed)
    require(canonical_tasks and changed_tasks, "PERSPECTIVE_AUDIT_SUPPLY_EMPTY")
    return {"perspective_canonical": canonical_tasks,
            "perspective_cross_view": cross_view,
            "perspective_changed_relation": changed_tasks}


def perspective_target_manifest(panels):
    """Offline-only targets and semantic pair definitions for retained predictions."""
    targets, comparisons = {}, []
    for tasks in panels.values():
        for task in tasks:
            mapping = {node["identifier"]: node["identifier"] for node in task["graph"]["nodes"]}
            targets[task["record_id"]] = {
                "record_id": task["record_id"], "root_family_id": task["family_id"],
                "base_to_view_map": mapping, "expected_answer": task["correct"],
                "semantic_expected_answer": semantic_answer(task["correct"], mapping)}
            if task.get("canonical_record_id"):
                comparisons.append({"root_family_id": task["family_id"],
                    "kind": task["perspective_pair_kind"], "left": task["canonical_record_id"],
                    "right": task["record_id"]})
    return {"teacher_targets": list(targets.values()), "comparisons": comparisons}
