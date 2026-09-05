"""Pure mocked-stored-result role checks. No native execution evidence."""
import ast
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import struct

import pytest

from cas_meta2 import native
from cas_meta2.curriculum import check_native_topology, generate_dataset
from cas_meta2.executor import digest

pytestmark = pytest.mark.not_gpu


@pytest.fixture
def mocked_reference(monkeypatch):
    task = generate_dataset(counts={"train": 2, "validation": 2, "test": 2})["splits"]["train"][0]
    structure = check_native_topology(task["target"]["program"])
    observation = next(row for row in task["public"]["observations"] if row["slot"] == task["target"]["binding"])
    input_sha = sha256(struct.pack("<8f", *observation["values"])).hexdigest()
    audit = {"rows": [{"cjt_id": row["cjt_id"], "input_node": row["input_node"],
                       "input_sha256": input_sha if row["input_node"] == -1 else digest(["input", index]),
                       "output_sha256": digest(["output", index])} for index, row in enumerate(structure["runs"])],
             "return_node": structure["return_node"], "trace_count": len(structure["runs"]),
             "reserved_policy_units": 123, "audit_method": "MOCK_ONLY", "stored_call_tree_verified": False}
    reference = {"status": "EXECUTED", "reference": True, "selected_action": deepcopy(task["target"]),
                 "public_digest": digest(task["public"]), "runtime_identity": {"mock": True},
                 "runtime_identity_after": {"mock": True}}
    calls = []
    def mock_stored(result, public, **kwargs):
        calls.append((result, public, kwargs))
        return deepcopy(audit)
    monkeypatch.setattr(native, "_stored", mock_stored)
    return task, reference, audit, calls


def test_mock_private_reference_uses_explicit_role_and_not_candidate_evaluation(mocked_reference):
    task, reference, audit, calls = mocked_reference
    verdict = native.verify_reference_task(task, reference)
    assert verdict["task_correct"] is True
    assert verdict["candidate_task_evaluation"] is False
    assert verdict["stored_call_tree_verified"] is False
    assert verdict["verdict_kind"] == "PRIVATE_NATIVE_REFERENCE_CHECK"
    assert verdict["reserved_policy_units"] == 123
    assert calls == [(reference, task["public"], {"expected_action": task["target"], "allow_private_reference": True})]


def test_mock_candidate_verifier_unconditionally_rejects_private_result(mocked_reference):
    task, reference, audit, calls = mocked_reference
    with pytest.raises(ValueError, match="CANDIDATE_MUST_NOT_BE_PRIVATE_REFERENCE"):
        native.verify_task(task, reference, reference)
    assert calls == []


def test_mock_candidate_role_may_not_be_omitted(mocked_reference):
    task, reference, audit, calls = mocked_reference
    candidate = deepcopy(reference)
    del candidate["reference"]
    with pytest.raises(ValueError, match="CANDIDATE_MUST_NOT_BE_PRIVATE_REFERENCE"):
        native.verify_task(task, candidate, reference)
    assert calls == []


def test_mock_private_verifier_refuses_candidate_record(mocked_reference):
    task, reference, audit, calls = mocked_reference
    reference["reference"] = False
    with pytest.raises(ValueError, match="PRIVATE_NATIVE_REFERENCE_REQUIRED"):
        native.verify_reference_task(task, reference)
    assert calls == []


@pytest.mark.parametrize("field", ["status", "selected_action", "public_digest", "runtime_identity_after"])
def test_mock_private_record_identity_and_target_are_checked_before_store(mocked_reference, field):
    task, reference, audit, calls = mocked_reference
    reference[field] = "wrong"
    with pytest.raises(ValueError):
        native.verify_reference_task(task, reference)
    assert calls == []


@pytest.mark.parametrize("field", ["cjt_id", "input_node"])
def test_mock_reference_independent_topology_check(mocked_reference, field):
    task, reference, audit, calls = mocked_reference
    audit["rows"][0][field] = "wrong"
    with pytest.raises(ValueError, match="PRIVATE_REFERENCE_STRUCTURE_MISMATCH"):
        native.verify_reference_task(task, reference)


def test_mock_reference_independent_public_input_check(mocked_reference):
    task, reference, audit, calls = mocked_reference
    audit["rows"][0]["input_sha256"] = "wrong"
    with pytest.raises(ValueError, match="PRIVATE_REFERENCE_INPUT_MISMATCH"):
        native.verify_reference_task(task, reference)


def test_campaign_self_checks_use_only_explicit_private_reference_api():
    source = Path(native.__file__).with_name("campaign.py").read_text()
    tree = ast.parse(source)
    for name in ("run_smoke", "_case_worker"):
        function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
        private_calls, candidate_calls = [], []
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "verify_reference_task":
                    private_calls.append(node)
                if node.func.id == "verify_task":
                    candidate_calls.append(node)
        assert len(private_calls) == len(candidate_calls) == 1
        assert [ast.unparse(argument) for argument in private_calls[0].args] == ["task", "reference"]
        assert [ast.unparse(argument) for argument in candidate_calls[0].args] == ["task", "result", "reference"]
