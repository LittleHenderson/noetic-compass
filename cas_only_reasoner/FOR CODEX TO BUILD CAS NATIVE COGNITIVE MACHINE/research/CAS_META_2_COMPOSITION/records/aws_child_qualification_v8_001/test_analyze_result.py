"""Small synthetic JSON-only tests. These do not create real qualification evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
from pathlib import Path
import unittest


def tool():
    path = Path(__file__).with_name("analyze_result.py")
    spec = importlib.util.spec_from_file_location("synthetic_child_result_analysis", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(value):
    return sha256(value.encode()).hexdigest()


def fake_execution(module, slot, combination, target, *, distinct=True):
    ticks = 6 if combination.endswith("CR") else 5
    rows = [{"cjt_id": c, "input_node": n - 1, "input_sha256": digest("in" + str(n)),
             "output_sha256": digest("prefix" + str(n))} for n, c in enumerate(("A", "B", "C", "R"))]
    rows.append({"cjt_id": "C", "input_node": 1 if combination.startswith("B_") else 3,
        "input_sha256": digest("child-input"), "output_sha256": digest(combination if distinct else target)})
    if ticks == 6:
        rows.append({"cjt_id": "R", "input_node": 4, "input_sha256": rows[-1]["output_sha256"],
                     "output_sha256": digest(combination if distinct else target)})
    correct = combination == target
    actual = {"status": "EXECUTED", "reference": slot == "reference", "native_trace_count": ticks,
        "reserved_policy_units": ticks * 10, "trace_valid": True, "integrity": True, "fixed_weights": True,
        "runtime_identity": {"synthetic": True}, "runtime_identity_after": {"synthetic": True}}
    stored = {"audit_method": "read-only-sqlite-source-replay/0.1", "trace_count": ticks,
        "reserved_policy_units": ticks * 10, "expected_action_checked": True,
        "stored_call_tree_verified": slot != "reference", "return_node": ticks - 1,
        "rows": rows, "final_output_sha256": rows[-1]["output_sha256"]}
    verdict = {k: correct for k in ("task_correct", "procedure_correct", "dependency_correct", "actual_output_correct")}
    verdict.update(binding_correct=True, trace_valid=True, stored_call_tree_verified=slot != "reference")
    return {"slot": slot, "status": "EXECUTED_AND_STORED_AUDITED", "execution_result": actual,
            "stored_audit": stored, "verification": verdict}


def fake_core(module, count=1, *, distinct=True):
    cases = []
    for index, target in enumerate(module.COMBINATIONS[:count]):
        executions = [fake_execution(module, slot, target if slot == "reference" else module.COMBINATIONS[number-1],
            target, distinct=distinct) for number, slot in enumerate(module.SLOTS)]
        cases.append({"index": index, "target_combination": target, "task": {"task_id": "SYNTHETIC-" + str(index)},
                      "status": "QUALIFIED" if distinct else "REFUSED", "executions": executions})
    executions = [r for c in cases for r in c["executions"]]
    status = "QUALIFIED" if count == 4 and distinct else "REFUSED"
    return {"schema": "cas-meta2-one-child-qualification/8", "status": status, "qualified": status == "QUALIFIED",
        "training": False, "cases": cases, "events": [], "scheduled_execution_count": 20, "scheduled_native_ticks": 110,
        "attempted_execution_count": len(executions), "reported_executed_count": len(executions),
        "completed_execution_count": len(executions),
        "audited_native_ticks": sum(r["stored_audit"]["trace_count"] for r in executions)}


class SyntheticAnalysisTests(unittest.TestCase):
    def test_full_counts_are_recomputed_not_assumed(self):
        m = tool()
        value = m.summarize_cases(fake_core(m, 4), None, lambda _: None, set())
        self.assertEqual(value["counts"]["observed_attempted_executions"], 20)
        self.assertEqual(value["counts"]["saved_audited_native_ticks"], 110)
        self.assertTrue(value["saved_runtime_identities_match"])
        self.assertTrue(all(r["required_discrimination_observed"] for c in value["cases"] for r in c["comparisons"]))

    def test_refusal_keeps_27_actual_ticks_and_identical_wrong_output(self):
        m = tool()
        core = fake_core(m, distinct=False)
        core["failure"] = {"type": "ValueError", "message": "QUALIFICATION_WRONG_CHOICE_FINAL_OUTPUT_NOT_DISTINCT"}
        result = m.summarize_cases(core, None, lambda _: None, set())
        self.assertEqual(result["counts"]["observed_attempted_executions"], 5)
        self.assertEqual(result["counts"]["saved_audited_native_ticks"], 27)
        self.assertEqual(result["counts"]["planned_native_ticks"], 110)
        self.assertFalse(result["cases"][0]["comparisons"][1]["final_output_differs_from_reference"])
        self.assertFalse(result["cases"][0]["comparisons"][1]["required_discrimination_observed"])
        self.assertEqual(result["core_failure"], core["failure"])
        self.assertIsNone(result["cases"][1]["target_combination"])

    def test_false_reported_total_is_not_promoted(self):
        m = tool()
        core = fake_core(m)
        core["completed_execution_count"] = 20
        with self.assertRaisesRegex(ValueError, "ACTUAL_COUNT_DISAGREEMENT"):
            m.summarize_cases(core, None, lambda _: None, set())

    def test_stored_final_hash_must_match_final_row(self):
        m = tool()
        core = fake_core(m)
        core["cases"][0]["executions"][0]["stored_audit"]["final_output_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "AUDITED_COUNTS_ROWS_OR_FINAL_HASH"):
            m.summarize_cases(core, None, lambda _: None, set())

    def test_post_deadline_result_file_is_separate_from_core_count(self):
        m = tool()
        core = fake_core(m)
        record = core["cases"][0]["executions"].pop()
        core["attempted_execution_count"] = 5
        core["reported_executed_count"] = core["completed_execution_count"] = 4
        core["audited_native_ticks"] -= record["stored_audit"]["trace_count"]
        core["cases"][0]["executions"].append({"slot": "candidate_03", "status": "ATTEMPTED"})
        filename = "qualification/cases/case_00/candidate_03/result.json"
        result = m.summarize_cases(core, None,
            lambda name: record["execution_result"] if name == filename else None, {filename})
        self.assertEqual(result["counts"]["available_executed_result_files_or_records"], 5)
        self.assertEqual(result["counts"]["saved_audited_executions"], 4)
        self.assertEqual(result["counts"]["core_reported_counts"]["reported_executed_count"], 4)

    def test_no_core_partial_attempt_event_does_not_invent_execution(self):
        m = tool()
        name = "qualification/cases/events/0001.json"
        event = {"event": "EXECUTION_ATTEMPTED", "case": 0, "slot": "reference"}
        result = m.summarize_cases(None, None, lambda n: event if n == name else None, {name})
        self.assertEqual(result["counts"]["observed_attempted_executions"], 1)
        self.assertEqual(result["counts"]["saved_audited_executions"], 0)
        self.assertEqual(result["counts"]["saved_audited_native_ticks"], 0)
        self.assertFalse(result["counts"]["core_receipt_present"])
        self.assertIsNone(result["saved_runtime_identities_match"])

    def test_old_br_core_status_is_not_qualification_evidence(self):
        m = tool()
        with self.assertRaisesRegex(ValueError, "NEW_CORE_RECEIPT_REQUIRED"):
            m.summarize_cases({"schema": "cas-meta2-br-construction/8", "status": "BR_COMPONENT_EXECUTED"},
                             None, lambda _: None, set())

    def test_cost_is_recorded_ec2_interval_and_retained_bucket_not_all_removed(self):
        m = tool()
        launch = {"events": [
            {"event": "INSTANCE_LAUNCH_ATTEMPTED", "utc": "2026-09-06T15:00:00.000000Z"},
            {"event": "INSTANCE_TERMINATION_CONFIRMED", "utc": "2026-09-06T15:10:00.500000Z"}],
            "termination_confirmed": True, "provider_preflight": {"instance_hourly_usd": "2.52"},
            "resources": {"bucket": "SYNTHETIC"}, "remaining_job_volumes": [], "cleanup_errors": []}
        result = m.interval_and_cleanup(launch)
        self.assertEqual(result["ec2_interval_estimate"]["interval_estimate_usd"], "0.42035")
        self.assertTrue(result["cleanup"]["bucket_retained"])
        self.assertFalse(result["cleanup"]["all_aws_resources_removed"])

    def test_missing_termination_does_not_estimate_finished_cost(self):
        m = tool()
        result = m.interval_and_cleanup({"events": [], "resources": {}})
        self.assertFalse(result["ec2_interval_estimate"]["available"])

    def test_synthetic_import_guards_are_declared(self):
        m = tool()
        self.assertTrue({"torch", "boto3", "botocore", "sqlite3", "cas_meta2"} <= m.FORBIDDEN)


if __name__ == "__main__":
    unittest.main()

