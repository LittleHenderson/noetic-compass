"""Pure diagnostics over already independently audited recovery cases."""
from collections import Counter
from copy import deepcopy

ARM_NAMES = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
METRIC_FIELDS = ("task_correct", "procedure_correct", "binding_correct",
                 "dependency_correct", "actual_output_correct", "trace_valid")
RUN_FIELDS = ("cjt_id", "input_node", "input_sha256", "output_sha256")


def named_site_metrics(action, target):
    """Adapted from contrast_first_transition_v6_001/report.py; literal only."""
    expected = target["program"]["procedures"]
    program = action.get("program") if type(action) is dict else None
    candidate = program.get("procedures", {}) if type(program) is dict else {}
    if type(candidate) is not dict:
        candidate = {}
    counts, errors = Counter(), []
    counts["observation_binding_expected"] = 1
    counts["observation_binding_correct"] = int(
        type(action) is dict and type(action.get("binding")) is int
        and action["binding"] == target["binding"])
    for name, procedure in expected.items():
        actual = candidate.get(name, {})
        steps = actual.get("steps", []) if type(actual) is dict else []
        if type(steps) is not list:
            steps = []
        for index, step in enumerate(procedure["steps"]):
            found = steps[index] if index < len(steps) else None
            if type(found) is not dict:
                found = {}
            same_kind = found.get("kind") == step["kind"]
            counts["named_input_sites_expected"] += 1
            input_match = same_kind and found.get("input") == step["input"]
            counts["named_input_sites_correct"] += int(input_match)
            if not input_match:
                errors.append({"procedure": name, "step": index, "field": "input",
                               "expected": step["input"], "actual": found.get("input"),
                               "kind_matches": same_kind})
            if step["kind"] == "CALL":
                counts["named_child_sites_expected"] += 1
                child_match = same_kind and found.get("procedure") == step["procedure"]
                counts["named_child_sites_correct"] += int(child_match)
                if not child_match:
                    errors.append({"procedure": name, "step": index, "field": "child",
                                   "expected": step["procedure"], "actual": found.get("procedure"),
                                   "kind_matches": same_kind})
    for key in ("named_input_sites_expected", "named_input_sites_correct",
                "named_child_sites_correct", "named_child_sites_expected"):
        counts.setdefault(key, 0)
    return {"counts": dict(counts), "errors": errors}


def first_committed_run_difference(actual, expected, c):
    """Compare only committed RUNs; an absent future RUN has unknown content."""
    c.require(type(actual) is list and type(expected) is list, "REPORT_RUN_LIST_REQUIRED")
    for row in [*actual, *expected]:
        c.require(type(row) is dict and all(k in row for k in RUN_FIELDS),
                  "REPORT_RUN_FIELDS_REQUIRED")
    for index, row in enumerate(actual):
        candidate = {key: deepcopy(row[key]) for key in RUN_FIELDS}
        gold = ({key: deepcopy(expected[index][key]) for key in RUN_FIELDS}
                if index < len(expected) else None)
        if candidate == gold:
            continue
        changed = list(RUN_FIELDS) if gold is None else [k for k in RUN_FIELDS if candidate[k] != gold[k]]
        return {"committed_run_index": index, "changed_fields": changed,
                "candidate": candidate, "successful_rule": gold,
                "boundary": "Recorded committed RUN disagreement only; not a full CALL trajectory or failed-tick cause."}
    return None


def _summary(rows, c):
    total = len(rows)
    metrics = {}
    for key in c.FIELDS:
        values = [row["verification"][key] for row in rows]
        correct = sum(value is True for value in values)
        wrong = sum(value is False for value in values)
        metrics[key] = {"correct": correct, "incorrect": wrong,
                        "unknown": sum(value is None for value in values),
                        "known": correct + wrong, "attempted": total}
    counts, boundaries, categories, run_fields = Counter(), Counter(), Counter(), Counter()
    native_runs = units = 0
    repair_required = repair_success = repair_unknown = 0
    for row in rows:
        counts.update(row["named_site_diagnostic"]["counts"])
        boundary = row.get("first_observed_boundary")
        if boundary is not None:
            boundaries[boundary] += 1
        difference = row.get("first_observed_difference")
        if difference:
            categories.update(difference["categories"])
        run_difference = row.get("first_committed_run_disagreement")
        if run_difference:
            run_fields.update(run_difference["changed_fields"])
        partial = row["partial_work"]
        if partial is not None:
            native_runs += partial["committed_native_runs"]
            units += partial["committed_reserved_policy_units"]
        else:
            native_runs += row["verification"].get("native_runs", 0)
            units += row["verification"].get("reserved_policy_units", 0)
        required = row["verification"].get("repair_required")
        if required is True:
            repair_required += 1
            repair_success += row["verification"].get("repair_success") is True
            repair_unknown += row["verification"].get("repair_success") is None
    failed = sum(row["execution_status"] == c.FAILURE for row in rows)
    return {"attempted": total, "correct": metrics["task_correct"]["correct"],
            "task_accuracy": metrics["task_correct"]["correct"] / total,
            "verifier_metrics": metrics, "named_site_counts": dict(counts),
            "model_rejections": sum(row["model_rejection"] for row in rows),
            "post_admission_runtime_failures": failed,
            "first_observed_boundaries": dict(boundaries),
            "complete_trace_first_difference_categories": dict(categories),
            "committed_run_first_difference_fields": dict(run_fields),
            "repair": {"required": repair_required, "success": repair_success,
                       "success_unknown": repair_unknown},
            "committed_native_runs_lower_bound": native_runs,
            "reserved_policy_units_lower_bound": units,
            "compute_complete": failed == 0, "all_cases_in_denominator": True}


def build_report(tasks, predictions, audited_cases, differences, c):
    """No file reads. Caller must bind source, sealed inputs and independent audit."""
    c.require(tuple(c.ARMS) == ARM_NAMES and tuple(c.FIELDS) == METRIC_FIELDS,
              "REPORT_FIXED_CONTRACT_REQUIRED")
    c.require(all(type(value) is list and len(value) == 72
                  for value in (tasks, predictions, audited_cases)), "REPORT_EXACT_72_REQUIRED")
    c.require(len({t["task_id"] for t in tasks}) == 72, "REPORT_UNIQUE_TASKS_REQUIRED")
    groups = {"all": [], "depth_3": [], "depth_4": [], "same_depth": [],
              "wording_shift": [], "deeper_calls": []}
    rows = []
    for index, (task, prediction, case) in enumerate(zip(tasks, predictions, audited_cases, strict=True)):
        c.require(type(case.get("case_index")) is int and case["case_index"] == index
                  and case["task_id"] == task["task_id"]
                  and set(case["arms"]) == set(c.ARMS)
                  and set(prediction["actions"]) == set(c.ARMS), "REPORT_CASE_MAPPING")
        if "task_id" in prediction:
            c.require(prediction["task_id"] == task["task_id"], "REPORT_PREDICTION_TASK_MAPPING")
        depth, side = task["provenance"]["depth"], task["contrast_side"]
        c.require(type(depth) is int and side in ("same_depth", "wording_shift", "deeper_calls")
                  and depth == (4 if side == "deeper_calls" else 3)
                  and task["provenance"]["evaluation_group"] == "test", "REPORT_SPLIT_IDENTITY")
        for key in ("all", "depth_" + str(depth), side):
            groups[key].append(index)
        rule = case["arms"]["rule"]
        c.require(case["reference_verification"]["task_correct"] is True
                  and rule["verification"]["task_correct"] is True
                  and rule["action"] == task["target"]
                  and rule["execution_status"] == "EXECUTED"
                  and rule["complete_trace"] is True
                  and type(rule["composition_events"]) is list, "REPORT_CORRECT_RULE_REQUIRED")
        gold = differences.normalize(deepcopy(rule["composition_events"]))
        for arm in c.ARMS:
            item = case["arms"][arm]
            status, verdict = item["execution_status"], item["verification"]
            c.require(type(item["case_index"]) is int and item["case_index"] == index
                      and item["arm"] == arm and item["action"] == prediction["actions"][arm],
                      "REPORT_ARM_OR_ACTION_MAPPING")
            c.require(status in ("EXECUTED", "REJECTED", c.FAILURE)
                      and type(item["model_rejection"]) is bool
                      and item["model_rejection"] is (status == "REJECTED"), "REPORT_STATUS_CLASSIFICATION")
            c.require(all(type(verdict[k]) is bool or verdict[k] is None for k in c.FIELDS)
                      and type(verdict["task_correct"]) is bool, "REPORT_VERDICT_TYPES")
            partial = item["partial_work"]
            if status == c.FAILURE:
                c.require(verdict["task_correct"] is False and partial is not None
                          and item["complete_trace"] is False and item["composition_events"] is None
                          and partial["rows"] == item["rows"]
                          and partial["compute_complete"] is False and partial["failed_tick_compute"] is None
                          and all(type(partial[k]) is int and partial[k] >= 0 for k in
                              ("committed_native_runs", "committed_reserved_policy_units")),
                          "REPORT_PARTIAL_BOUNDARY")
            else:
                c.require(partial is None and all(type(verdict[k]) is bool for k in c.FIELDS),
                          "REPORT_COMPLETE_METRICS_REQUIRED")
                c.require(all(type(verdict.get(k, 0)) is int and verdict.get(k, 0) >= 0
                              for k in ("native_runs", "reserved_policy_units")), "REPORT_COMPUTE_COUNTS")
                c.require(item["complete_trace"] is (status == "EXECUTED")
                          and (type(item["composition_events"]) is list if status == "EXECUTED"
                               else item["composition_events"] is None and item["rows"] == []),
                          "REPORT_TRACE_STATUS")
                if status == "REJECTED":
                    c.require(verdict["task_correct"] is False, "REPORT_REJECTED_SUCCESS")
            row = {"case_index": index, "task_id": task["task_id"], "arm": arm,
                   "depth": depth, "condition": side, "task_correct": verdict["task_correct"],
                   "execution_status": status, "model_rejection": item["model_rejection"],
                   "verification": deepcopy(verdict), "partial_work": deepcopy(partial),
                   "named_site_diagnostic": named_site_metrics(item["action"], task["target"])}
            if not verdict["task_correct"]:
                if status == "REJECTED":
                    row["first_observed_boundary"] = "pre_execution_rejection"
                    row["generation_reason"] = (item["action"].get("reason")
                                                if type(item["action"]) is dict else None)
                elif status == c.FAILURE:
                    row["first_observed_boundary"] = "post_admission_runtime_failure"
                    row["first_committed_run_disagreement"] = first_committed_run_difference(
                        item["rows"], rule["rows"], c)
                    row["committed_prefix"] = {"candidate_runs": len(item["rows"]),
                        "successful_rule_runs": len(rule["rows"]), "complete_trajectory": False,
                        "failed_tick_cause": None, "comparison_reference": "independently_correct_rule",
                        "next_sealed_run": deepcopy(item.get("next_sealed_run")),
                        "note": "Next sealed RUN is a planned action, not proof of the failed tick. Missing future rows stay unknown."}
                else:
                    actual = differences.normalize(deepcopy(item["composition_events"]))
                    difference = differences.first_difference(actual, deepcopy(gold))
                    row["first_observed_difference"] = deepcopy(difference)
                    row["first_observed_boundary"] = ("recorded_trajectory_divergence" if difference
                        else "unresolved_no_difference_in_selected_fields")
            rows.append(row)
    c.require({key: len(value) for key, value in groups.items()} ==
              {"all": 72, "depth_3": 48, "depth_4": 24, "same_depth": 24,
               "wording_shift": 24, "deeper_calls": 24}, "REPORT_GROUP_COUNTS")
    summaries = {}
    for group, indices in groups.items():
        summaries[group] = {arm: _summary([r for r in rows if r["arm"] == arm
                                         and r["case_index"] in indices], c) for arm in c.ARMS}
    before_after = {}
    for group, summary in summaries.items():
        before_after[group] = {}
        for family in ("cas", "generic"):
            before, after = summary[family + "_untrained"], summary[family + "_trained"]
            before_after[group][family] = {
                "attempted_before": before["attempted"], "attempted_after": after["attempted"],
                "correct_before": before["correct"], "correct_after": after["correct"],
                "correct_change": after["correct"] - before["correct"]}
    return {"schema": "cas-meta2-recovery-diagnostic-report/6", "cases": rows,
            "case_count": 72, "arm_rows": 360, "summaries": summaries, "before_after": before_after,
            "neural_execution": False, "learning_accepted": False,
            "boundary": "Correctness is supplied by the independent frozen-verifier audit, not inferred from trace validity. "
                        "Unknown verifier fields remain unknown. Literal named-site scores can penalize equivalent renaming; "
                        "their site order is not execution order. Complete-event differences use the caller's source-bound helper. "
                        "A partial committed-RUN disagreement is not a full CALL difference or failed-tick cause. "
                        "A shorter matching committed prefix does not establish an early trajectory end. "
                        "The 72 tasks are 24 related triplets, not 72 independent structures. "
                        "This report does not train, change checkpoints, or independently accept learning."}
