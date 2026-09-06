"""Synthetic-only orchestration tests. No native executor or database is used."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
from cas_meta2 import child_curriculum_v8 as curriculum
from cas_meta2 import child_qualification_v8 as q


@pytest.fixture
def tasks():
    return curriculum.qualification_tasks()


class FakeOperations:
    evidence_kind = "SYNTHETIC_TEST_ONLY"

    def __init__(self, output, *, defect=None, cross_public_prefix=False):
        self.output, self.defect = output, defect
        self.cross_public_prefix = cross_public_prefix
        self.events, self.audits = [], {}
        self.current_reference = None
        self.references = 0
        self.candidates = 0

    def assert_identity(self):
        if self.defect == "identity":
            raise ValueError("SYNTHETIC_IDENTITY_FAILURE")

    def reference_task(self, task, directory):
        sealed = json.loads((self.output / "candidates_sealed.json").read_bytes())
        assert sealed["candidate_count"] == 16
        assert sum(len(c["candidates"]) for c in sealed["cases"]) == 16
        assert all(c["formal_public_target_checked"] for c in sealed["cases"])
        self.events.append(("reference", task["task_id"]))
        self.references += 1
        actual = self.make(task["public"], task["target"], directory, True)
        self.current_reference = deepcopy(self.audits[str(directory)])
        return actual

    def execute_task(self, public, action, directory):
        assert set(public) == {"problem", "observations"}
        self.events.append(("candidate", q.digest(action)))
        self.candidates += 1
        if self.defect == "execution_failure":
            directory.mkdir()
            (directory / "failure.json").write_text('{"synthetic_failure":true}')
            raise RuntimeError("SYNTHETIC_EXECUTION_FAILED")
        if self.defect == "seal_mutation":
            (self.output / "candidates_sealed.json").write_bytes(b"SYNTHETIC_CHANGED")
        return self.make(public, action, directory, False)

    def make(self, public, action, directory, reference):
        directory.mkdir()
        (directory / "native.db").write_bytes(b"SYNTHETIC TEST BYTES - NOT A DATABASE")
        plan = q.action_plan(action)
        base = q.digest(public) if self.cross_public_prefix else q.digest(public["observations"])
        rows = []
        for edge in plan["edges"]:
            input_hash = base if edge["input_node"] == -1 else rows[edge["input_node"]]["output_sha256"]
            rows.append({**edge, "input_sha256": input_hash,
                         "output_sha256": q.digest({"cjt": edge["cjt_id"], "input": input_hash})})
        is_wrong = not reference and rows != self.current_reference["rows"]
        if is_wrong and self.defect == "wrong_final_equal":
            rows[-1]["output_sha256"] = self.current_reference["final_output_sha256"]
        if not reference and self.defect == "prefix":
            rows[0]["input_sha256"] = "f" * 64
        audit = {"audit_method": "read-only-sqlite-source-replay/0.1", "stored_call_tree_verified": not reference,
            "rows": rows, "trace_count": len(rows), "return_node": len(rows) - 1,
            "final_output_sha256": rows[-1]["output_sha256"], "reserved_policy_units": len(rows) * 72}
        if not reference and self.defect == "calltree":
            audit["stored_call_tree_verified"] = False
        if self.defect == "audit_count":
            audit["trace_count"] += 1
        self.audits[str(directory)] = audit
        identity = {"model": {"model_digest": "1" * 64}, "software_digest": "2" * 64}
        actual = {"status": "EXECUTED", "reference": reference, "selected_action": deepcopy(action),
            "public_digest": q.digest(public), "output_dir": str(directory), "native_database": str(directory / "native.db"),
            "runtime_identity": identity, "runtime_identity_after": deepcopy(identity),
            "native_trace_count": len(rows), "reserved_policy_units": len(rows) * 72,
            "trace_valid": True, "integrity": True, "fixed_weights": True}
        if not reference and self.defect == "identity_after":
            actual["runtime_identity_after"]["software_digest"] = "3" * 64
        if not reference and self.defect == "binding":
            actual["selected_action"]["binding"] = 1
        if not reference and self.defect == "reference_flag":
            actual["reference"] = True
        (directory / "result.json").write_bytes(q.encoded(actual))
        return actual

    def audit(self, result, public, *, expected_action=None, allow_private_reference=False):
        self.events.append(("audit", result["reference"]))
        assert expected_action == result["selected_action"]
        assert allow_private_reference is result["reference"]
        return {**deepcopy(self.audits[result["output_dir"]]),
                "expected_action_checked": self.defect != "sealed_action_audit"}

    def verify_reference_task(self, task, reference):
        self.events.append(("verify_reference", task["task_id"]))
        return {**{key: True for key in q.FLAGS}, "native_runs": reference["native_trace_count"],
            "reserved_policy_units": reference["reserved_policy_units"], "stored_call_tree_verified": False,
            "candidate_task_evaluation": False, "verdict_kind": "PRIVATE_NATIVE_REFERENCE_CHECK"}

    def verify_task(self, task, actual, reference):
        self.events.append(("verify_candidate", q.digest(actual["selected_action"])))
        correct = actual["selected_action"] == task["target"]
        verdict = {**{key: correct for key in q.FLAGS}, "trace_valid": True, "binding_correct": True,
            "stored_call_tree_verified": True, "native_runs": actual["native_trace_count"],
            "reserved_policy_units": actual["reserved_policy_units"]}
        if self.defect == "wrong_accepted" and not correct:
            verdict["task_correct"] = True
        if self.defect == "wrong_output_flag" and not correct:
            verdict["actual_output_correct"] = True
        if self.defect == "trace_flag":
            verdict["trace_valid"] = False
        if self.defect == "correct_rejected" and correct:
            verdict["actual_output_correct"] = verdict["task_correct"] = False
        if self.defect == "verifier_count":
            verdict["native_runs"] += 1
        return verdict


def run(tmp_path, tasks, **kwargs):
    output = tmp_path / "qualification"
    ops = FakeOperations(output, **kwargs)
    receipt = q.run_qualification(tasks, ops, output)
    return receipt, ops, output


def test_every_stored_audit_must_report_its_sealed_action_check(tmp_path, tasks):
    receipt, _, _ = run(tmp_path, tasks, defect="sealed_action_audit")
    assert receipt["status"] == "REFUSED"
    assert receipt["failure"]["message"] == "QUALIFICATION_SEALED_ACTION_AUDIT_REQUIRED"
    assert receipt["completed_execution_count"] == 0


def test_all_sixteen_concrete_candidates_sealed_before_any_private_execution(tasks):
    prepared = q.prepare(tasks)
    assert prepared["candidate_count"] == 16
    assert prepared["scheduled_execution_count"] == 20 and prepared["scheduled_native_ticks"] == 110
    assert all(tuple(c["combination"] for c in case["candidates"]) == q.COMBINATIONS for case in prepared["cases"])
    assert all(sum(c["action"] == case["task"]["target"] for c in case["candidates"]) == 1 for case in prepared["cases"])
    assert all(case["formal_public_target_checked"] is True for case in prepared["cases"])


def test_full_fake_qualification_counts_only_returned_and_separately_audited_work(tmp_path, tasks):
    receipt, ops, output = run(tmp_path, tasks)
    assert receipt["status"] == "QUALIFIED" and receipt["qualified"] is True and receipt["training"] is False
    assert receipt["evidence_kind"] == "SYNTHETIC_TEST_ONLY"
    assert receipt["attempted_execution_count"] == receipt["reported_executed_count"] == receipt["completed_execution_count"] == 20
    assert receipt["audited_native_ticks"] == receipt["completed_native_ticks"] == 110
    assert receipt["unattempted_execution_count"] == receipt["failed_or_unaudited_attempts"] == 0
    assert ops.references == 4 and ops.candidates == 16
    assert sum(label == "audit" for label, _ in ops.events) == 20
    assert len(receipt["cases"]) == 4 and all(len(c["executions"]) == 5 for c in receipt["cases"])
    assert json.loads((output / "qualification_receipt.json").read_bytes()) == receipt
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(sys.modules)


def test_prefix_match_is_within_same_public_not_across_different_requests(tmp_path, tasks):
    receipt, _, _ = run(tmp_path, tasks, cross_public_prefix=True)
    assert receipt["status"] == "QUALIFIED"
    prefixes = [q.digest(c["prelude_audit_rows"]) for c in receipt["cases"]]
    assert len(set(prefixes)) == 4


def test_all_four_candidates_are_run_before_final_hash_discrimination_failure(tmp_path, tasks):
    receipt, ops, output = run(tmp_path, tasks, defect="wrong_final_equal")
    assert receipt["status"] == "REFUSED" and receipt["qualified"] is False
    assert "WRONG_CHOICE_FINAL_OUTPUT_NOT_DISTINCT" in receipt["failure"]["message"]
    assert ops.references == 1 and ops.candidates == 4
    assert receipt["completed_execution_count"] == receipt["attempted_execution_count"] == 5
    assert receipt["audited_native_ticks"] == 27 and receipt["completed_native_ticks"] is None
    assert len(receipt["cases"][0]["executions"]) == 5
    assert (output / "case_00/candidate_03_qualification.json").exists()
    assert receipt["unattempted_execution_count"] == 15


@pytest.mark.parametrize("defect,reason", [("calltree", "STORED_CALL_TREE"),
    ("prefix", "FOUR_STEP_PREFIX"), ("identity_after", "RUNTIME_NOT_FIXED"),
    ("binding", "EXECUTION_IDENTITY"), ("reference_flag", "EXECUTION_IDENTITY"),
    ("audit_count", "AUDITED_COUNTS"), ("verifier_count", "VERIFIER_AUDIT_COUNTS"),
    ("wrong_accepted", "WRONG_CHOICE_NOT_REJECTED"), ("correct_rejected", "CORRECT_CANDIDATE_FAILED"),
    ("wrong_output_flag", "WRONG_CHOICE_NOT_REJECTED"),
    ("seal_mutation", "SEAL_CHANGED")])
def test_evidence_or_verifier_defect_refuses_without_fallback(tmp_path, tasks, defect, reason):
    receipt, ops, output = run(tmp_path, tasks, defect=defect)
    assert receipt["status"] == "REFUSED" and receipt["qualified"] is False
    assert reason in receipt["failure"]["message"]
    assert ops.references <= 1 and ops.candidates <= 4
    assert receipt["completed_execution_count"] < 20
    assert receipt["completed_native_ticks"] is None
    assert (output / "qualification_receipt.json").exists()


def test_execution_exception_retains_actual_attempt_and_failure_files_no_retry(tmp_path, tasks):
    receipt, ops, output = run(tmp_path, tasks, defect="execution_failure")
    assert receipt["status"] == "REFUSED"
    assert receipt["attempted_execution_count"] == 2 and receipt["completed_execution_count"] == 1
    assert receipt["audited_native_ticks"] == 5 and receipt["failed_or_unaudited_attempts"] == 1
    assert receipt["unattempted_execution_count"] == 18
    assert (output / "case_00/candidate_00/failure.json").exists()
    assert ops.candidates == 1


def test_refused_verifier_response_is_retained_not_replaced_by_failure_label(tmp_path, tasks):
    receipt, ops, _ = run(tmp_path, tasks, defect="trace_flag")
    assert receipt["status"] == "REFUSED"
    candidate = receipt["cases"][0]["executions"][1]
    assert candidate["verification"]["trace_valid"] is False
    assert candidate["stored_audit"]["stored_call_tree_verified"] is True


def test_public_target_disagreement_stops_before_execution(tmp_path, tasks):
    tasks[0]["target"] = deepcopy(tasks[1]["target"])
    receipt, ops, _ = run(tmp_path, tasks)
    assert receipt["status"] == "REFUSED" and receipt["attempted_execution_count"] == 0
    assert ops.references == ops.candidates == 0
    assert "TARGET_MISMATCH" in receipt["failure"]["message"]


def test_duplicate_target_panel_rejected_without_execution(tmp_path, tasks):
    tasks[3] = deepcopy(tasks[0])
    receipt, ops, _ = run(tmp_path, tasks)
    assert receipt["status"] == "REFUSED" and "TARGET_COVERAGE" in receipt["failure"]["message"]
    assert ops.references == ops.candidates == 0


def test_identity_failure_is_receipted_before_reference(tmp_path, tasks):
    receipt, ops, _ = run(tmp_path, tasks, defect="identity")
    assert receipt["status"] == "REFUSED"
    assert receipt["attempted_execution_count"] == 0 and ops.references == 0


def test_positive_float_remaining_time_accepted(tmp_path, tasks):
    output = tmp_path / "qualification"
    result = q.run_qualification(tasks, FakeOperations(output), output, max_seconds=1799.5)
    assert result["status"] == "QUALIFIED"


@pytest.mark.parametrize("seconds", [True, 0, -1, 1801, float("inf"), float("nan")])
def test_invalid_clock_limit_never_creates_output(tmp_path, tasks, seconds):
    output = tmp_path / "qualification"
    with pytest.raises(ValueError, match="TIME_BOUND"):
        q.run_qualification(tasks, FakeOperations(output), output, max_seconds=seconds)
    assert not output.exists()


def test_deadline_refusal_reports_zero_not_planned_work(tmp_path, tasks):
    ticks = iter([0.0, 2000.0, 2000.1])
    output = tmp_path / "qualification"
    result = q.run_qualification(tasks, FakeOperations(output), output, clock=lambda: next(ticks))
    assert result["status"] == "REFUSED" and result["attempted_execution_count"] == 0
    assert result["audited_native_ticks"] == 0 and result["completed_native_ticks"] is None
    assert "DEADLINE" in result["failure"]["message"]


def test_output_limit_refuses_without_native_work_or_discarding_files(tmp_path, tasks):
    output = tmp_path / "qualification"
    result = q.run_qualification(tasks, FakeOperations(output), output, max_output_bytes=1)
    assert result["status"] == "REFUSED" and result["attempted_execution_count"] == 0
    assert result["receipt_saved"] is False and output.exists()


def test_existing_output_is_never_overwritten(tmp_path, tasks):
    output = tmp_path / "qualification"
    output.mkdir()
    original = output / "user.txt"
    original.write_bytes(b"keep")
    with pytest.raises(ValueError, match="FRESH_OUTPUT"):
        q.run_qualification(tasks, FakeOperations(output), output)
    assert original.read_bytes() == b"keep"
