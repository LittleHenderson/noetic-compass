"""Pure structural reuse tests with synthetic stored learning evidence."""
from copy import deepcopy

import pytest

from cas_meta3 import learned_linker as linker
from cas_meta3 import learned_package as packages
from cas_meta3 import learning_evidence as evidence
from cas_meta3.learned_store import LearnedCandidateStore
from test_learned_handoff import fixture
from test_learned_store import trust


def saved(tmp_path):
    package, inputs = fixture()
    path = tmp_path / "candidate.sqlite"
    LearnedCandidateStore(path).save(package, **inputs)
    return path, package, inputs


@pytest.mark.parametrize("count,selected", [(1, 0), (2, 0), (2, 1), (4, 0), (4, 3)])
def test_real_retrieval_renames_all_nested_calls_and_preserves_selected_return(tmp_path, count, selected):
    path, package, inputs = saved(tmp_path)
    before = path.read_bytes()
    result = linker.retrieve_for_reuse(path, expected_digest=inputs["expected_digest"],
        call_count=count, return_call=selected, **trust(inputs))
    assert path.read_bytes() == before
    action, receipt = result["action"], result["link_receipt"]
    assert action["binding"] == package["binding"]
    assert receipt["procedure_mapping"] == {"main": "p0", "p0": "p1"}
    assert action["program"]["procedures"]["p0"]["steps"][1]["procedure"] == "p1"
    assert action["program"]["procedures"]["p1"] == package["program"]["procedures"]["p0"]
    assert action["program"]["procedures"]["main"]["return"] == "v" + str(selected)
    expected = [{"cjt_id": cjt, "input_node": source} for i in range(count)
        for cjt, source in (("A", -1), ("B", i * 3), ("C", i * 3 + 1))]
    assert receipt["expected_native_edges"] == expected
    assert receipt["expected_return_node"] == selected * 3 + 2
    assert receipt["derived_bounds"]["expanded_run_count"] == count * 3
    assert receipt["derived_bounds"]["max_call_depth"] == 3
    assert receipt["qualification_status"] == "UNQUALIFIED"
    assert not any(receipt[k] for k in ("promotion_granted", "native_execution_performed", "learning_performed"))
    assert receipt["receipt_sha256"] == evidence.digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})


@pytest.mark.parametrize("key,value", [("call_count", True), ("call_count", 0), ("call_count", 5),
    ("return_call", True), ("return_call", -1), ("return_call", 2),
    ("max_expanded_runs", True), ("max_expanded_runs", 0), ("max_expanded_runs", 257)])
def test_bad_link_request_is_rejected_before_even_opening_missing_store(tmp_path, key, value):
    with pytest.raises(linker.LinkError):
        linker.retrieve_for_reuse(tmp_path / "missing.sqlite", expected_digest="a" * 64, **{key: value})
    assert not (tmp_path / "missing.sqlite").exists()


def test_compute_limit_counts_every_repeated_call_not_only_returned_call(tmp_path):
    path, package, inputs = saved(tmp_path)
    with pytest.raises(linker.LinkError, match="REUSE_COMPUTE_CEILING_EXCEEDED"):
        linker.retrieve_for_reuse(path, expected_digest=inputs["expected_digest"],
            max_expanded_runs=5, **trust(inputs))
    result = linker.retrieve_for_reuse(path, expected_digest=inputs["expected_digest"],
        max_expanded_runs=6, **trust(inputs))
    assert result["link_receipt"]["derived_bounds"]["expanded_run_count"] == 6


def test_linker_does_not_supply_itself_missing_permissions(tmp_path):
    path, package, inputs = saved(tmp_path)
    args = trust(inputs)
    args["permitted_cjts"] = ["A", "B"]
    with pytest.raises(packages.PackageError, match="CALLER_CJT_SCOPE_DENIED"):
        linker.retrieve_for_reuse(path, expected_digest=inputs["expected_digest"], **args)


def test_linker_does_not_replace_external_evidence_trust_with_stored_claims(tmp_path):
    path, package, inputs = saved(tmp_path)
    args = trust(inputs)
    args["expected_inspection_sha256"] = "d" * 64
    with pytest.raises(evidence.LearningEvidenceError, match="TRUSTED_RECEIPT_DIGEST_MISMATCH"):
        linker.retrieve_for_reuse(path, expected_digest=inputs["expected_digest"], **args)
