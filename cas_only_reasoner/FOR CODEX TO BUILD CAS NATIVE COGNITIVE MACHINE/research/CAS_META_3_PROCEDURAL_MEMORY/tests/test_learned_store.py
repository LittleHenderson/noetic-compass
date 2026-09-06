"""Synthetic persistence tests only: no learned skill or native run is claimed."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from cas_meta3 import learned_store as store
from cas_meta3 import learned_package as packages
from cas_meta3 import learning_evidence as evidence
from test_learned_handoff import fixture


def trust(inputs):
    return {name: value for name, value in inputs.items()
            if name in store.TRUST_FIELDS or name == "minimum_correct_gain"}


def saved(tmp_path):
    candidate, inputs = fixture()
    path = tmp_path / "candidate.sqlite"
    registry = store.LearnedCandidateStore(path)
    receipt = registry.save(candidate, **inputs)
    return path, candidate, inputs, receipt


def test_save_close_reopen_revalidates_raw_evidence_and_is_not_promotion(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    before = path.read_bytes()
    result = store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"], **trust(inputs))
    assert path.read_bytes() == before
    assert result["package"] == candidate
    assert result["storage_receipt"] == receipt
    assert result["retrieval_revalidated"] is True
    assert result["qualification_status"] == "UNQUALIFIED"
    assert result["promotion_granted"] is False
    assert result["handoff"]["fresh_native_reuse_tested"] is False
    assert receipt["sequence"] == 1 and receipt["previous_receipt_sha256"] is None
    assert receipt["receipt_sha256"] == evidence.digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})


def test_same_candidate_and_evidence_is_idempotent(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    before = path.read_bytes()
    assert store.LearnedCandidateStore(path).save(candidate, **inputs) == receipt
    assert path.read_bytes() == before


@pytest.mark.parametrize("key", list(store.RAW_FIELDS))
def test_invalid_audit_input_creates_no_file_or_parent_directory(tmp_path, key):
    candidate, inputs = fixture()
    inputs[key] += b" "
    path = tmp_path / "new-parent" / "candidate.sqlite"
    with pytest.raises(evidence.LearningEvidenceError):
        store.LearnedCandidateStore(path).save(candidate, **inputs)
    assert not path.parent.exists()


@pytest.mark.parametrize("key,value", [
    ("expected_inspection_sha256", "e" * 64),
    ("expected_stored_audit_sha256", "e" * 64),
    ("permitted_cjts", ["A", "B"]), ("case_index", 71),
])
def test_retrieval_requires_fresh_external_authority_not_saved_claims(tmp_path, key, value):
    path, candidate, inputs, receipt = saved(tmp_path)
    args = trust(inputs)
    args[key] = value
    before = path.read_bytes()
    with pytest.raises(ValueError):
        store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"], **args)
    assert path.read_bytes() == before


def test_omitted_external_trust_is_not_inferred_from_stored_audits(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    args = trust(inputs)
    del args["expected_inspection_sha256"]
    with pytest.raises(store.StoreError, match="EXTERNAL_RETRIEVAL_TRUST_REQUIRED"):
        store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"], **args)


def test_retrieval_cannot_override_saved_raw_evidence(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    with pytest.raises(store.StoreError, match="EXTERNAL_RETRIEVAL_TRUST_REQUIRED"):
        store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"],
            **trust(inputs), inspection_bytes=inputs["inspection_bytes"])


@pytest.mark.parametrize("field", list(store.PAYLOAD_NAMES) + ["receipt"])
def test_stored_byte_changes_are_detected_even_when_immutable_trigger_is_restored(tmp_path, field):
    path, candidate, inputs, receipt = saved(tmp_path)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TRIGGER candidates_no_update")
        conn.execute("UPDATE candidates SET " + field + "=?", (b"changed",))
        conn.execute(store.SQL["candidates_no_update"])
    with pytest.raises(ValueError):
        store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"], **trust(inputs))


@pytest.mark.parametrize("statement", ["DELETE FROM candidates", "UPDATE candidates SET sequence=9",
    "DELETE FROM metadata", "UPDATE metadata SET payload=x'00'"])
def test_normal_sql_update_and_delete_are_refused(tmp_path, statement):
    path, candidate, inputs, receipt = saved(tmp_path)
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(statement)


def test_unknown_and_nonexistent_stores_do_not_create_files(tmp_path):
    candidate, inputs = fixture()
    path = tmp_path / "missing.sqlite"
    with pytest.raises(store.StoreError, match="STORE_NOT_FOUND"):
        store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"], **trust(inputs))
    assert not path.exists()
    path, candidate, inputs, receipt = saved(tmp_path)
    with pytest.raises(store.StoreError, match="UNKNOWN_CANDIDATE"):
        store.LearnedCandidateStore(path).retrieve("d" * 64, **trust(inputs))


def test_child_version_preserves_parent_record_and_receipt_chain(tmp_path):
    path, candidate, inputs, parent_receipt = saved(tmp_path)
    parent_digest = inputs["expected_digest"]
    child = deepcopy(candidate)
    child["lineage"] = {"version": 2, "parent_package_sha256": parent_digest}
    child_inputs = {**inputs, "expected_digest": packages.package_digest(child),
                    "expected_parent_digest": parent_digest, "expected_version": 2}
    registry = store.LearnedCandidateStore(path)
    child_receipt = registry.save(child, **child_inputs)
    assert child_receipt["sequence"] == 2
    assert child_receipt["previous_receipt_sha256"] == parent_receipt["receipt_sha256"]
    assert registry.retrieve(parent_digest, **trust(inputs))["package"] == candidate
    assert registry.retrieve(child_inputs["expected_digest"], **trust(child_inputs))["package"] == child
    # This is versioned candidate storage, not demonstrated skill rollback.
    assert registry.retrieve(child_inputs["expected_digest"], **trust(child_inputs))["handoff"]["rollback_tested"] is False


def test_nonexistent_parent_is_not_admitted_to_existing_store(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    child = deepcopy(candidate)
    child["lineage"] = {"version": 2, "parent_package_sha256": "d" * 64}
    args = {**inputs, "expected_digest": packages.package_digest(child),
            "expected_parent_digest": "d" * 64, "expected_version": 2}
    before = path.read_bytes()
    with pytest.raises(store.StoreError, match="STORED_PARENT_REQUIRED"):
        store.LearnedCandidateStore(path).save(child, **args)
    assert path.read_bytes() == before


def test_cold_reader_process_receives_only_db_and_external_trust(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    external = tmp_path / "external-trust.json"
    external.write_text(json.dumps({"expected_digest": inputs["expected_digest"], **trust(inputs)}))
    code = """
import sys,json
from pathlib import Path
from tools.validate_local import NoNeuralImports
sys.meta_path.insert(0, NoNeuralImports())
from cas_meta3.learned_store import LearnedCandidateStore
args=json.loads(Path(sys.argv[2]).read_bytes())
result=LearnedCandidateStore(sys.argv[1]).retrieve(**args)
assert 'torch' not in sys.modules and 'boto3' not in sys.modules
print(json.dumps({'package':result['package'],'revalidated':result['retrieval_revalidated'],'qualification':result['qualification_status']}))
"""
    root = Path(__file__).resolve().parents[1]
    run = subprocess.run([sys.executable, "-B", "-c", code, str(path), str(external)],
        cwd=root, env=dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result == {"package": candidate, "revalidated": True, "qualification": "UNQUALIFIED"}


def test_missing_parent_cannot_create_an_unusable_empty_store(tmp_path):
    candidate, inputs = fixture()
    candidate["lineage"] = {"version": 2, "parent_package_sha256": "d" * 64}
    inputs.update(expected_digest=packages.package_digest(candidate),
                  expected_version=2, expected_parent_digest="d" * 64)
    path = tmp_path / "new" / "candidate.sqlite"
    with pytest.raises(store.StoreError, match="STORED_PARENT_REQUIRED"):
        store.LearnedCandidateStore(path).save(candidate, **inputs)
    assert not path.parent.exists()


def test_rehashed_storage_receipt_cannot_authorize_changed_audit_bytes(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT * FROM candidates").fetchone()
        payloads = list(row[2:-1])
        payloads[1] += b" "
        forged = store._receipt(1, inputs["expected_digest"], payloads, None)
        conn.execute("DROP TRIGGER candidates_no_update")
        conn.execute("UPDATE candidates SET inspection_bytes=?,receipt=?",
                     (payloads[1], evidence.canonical(forged)))
        conn.execute(store.SQL["candidates_no_update"])
    with pytest.raises(evidence.LearningEvidenceError, match="TRUSTED_RECEIPT_DIGEST_MISMATCH"):
        store.LearnedCandidateStore(path).retrieve(inputs["expected_digest"], **trust(inputs))


def test_rewritten_sequence_cannot_hide_a_missing_parent_on_retrieval(tmp_path):
    path, candidate, inputs, receipt = saved(tmp_path)
    child = deepcopy(candidate)
    child["lineage"] = {"version": 2, "parent_package_sha256": inputs["expected_digest"]}
    child_inputs = {**inputs, "expected_digest": packages.package_digest(child),
        "expected_version": 2, "expected_parent_digest": inputs["expected_digest"]}
    store.LearnedCandidateStore(path).save(child, **child_inputs)
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT * FROM candidates WHERE sequence=2").fetchone()
        forged = store._receipt(1, child_inputs["expected_digest"], row[2:-1], None)
        conn.execute("DROP TRIGGER candidates_no_update")
        conn.execute("DROP TRIGGER candidates_no_delete")
        conn.execute("DELETE FROM candidates WHERE sequence=1")
        conn.execute("UPDATE candidates SET sequence=1,receipt=?", (evidence.canonical(forged),))
        conn.execute(store.SQL["candidates_no_update"])
        conn.execute(store.SQL["candidates_no_delete"])
    with pytest.raises(store.StoreError, match="STORED_PARENT_REQUIRED"):
        store.LearnedCandidateStore(path).retrieve(child_inputs["expected_digest"], **trust(child_inputs))


def test_candidate_limit_rejects_new_version_without_changing_store(tmp_path, monkeypatch):
    path, candidate, inputs, receipt = saved(tmp_path)
    child = deepcopy(candidate)
    child["lineage"] = {"version": 2, "parent_package_sha256": inputs["expected_digest"]}
    child_inputs = {**inputs, "expected_digest": packages.package_digest(child),
        "expected_version": 2, "expected_parent_digest": inputs["expected_digest"]}
    monkeypatch.setattr(store, "MAX_CANDIDATES", 1)
    before = path.read_bytes()
    with pytest.raises(store.StoreError, match="STORE_CANDIDATE_CEILING"):
        store.LearnedCandidateStore(path).save(child, **child_inputs)
    assert before == path.read_bytes()


def test_file_size_limit_applies_before_opening_database(tmp_path, monkeypatch):
    path, candidate, inputs, receipt = saved(tmp_path)
    monkeypatch.setattr(store, "MAX_FILE_BYTES", 1)
    with pytest.raises(store.StoreError, match="STORE_BYTE_CEILING"):
        store.LearnedCandidateStore(path)
