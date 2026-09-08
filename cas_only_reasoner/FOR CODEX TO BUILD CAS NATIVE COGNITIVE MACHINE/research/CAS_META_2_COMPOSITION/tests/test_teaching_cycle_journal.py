"""Synthetic byte checkpoints only: no tensors, database, provider, or training."""
import ast
from hashlib import sha256
import os
from pathlib import Path

import pytest

from cas_meta2.teaching_cycle import journal

IDENTITY = {"source_sha256": "1" * 64, "experiment": "synthetic-no-tensor"}


def writer(payload=b"synthetic checkpoint: no tensors"):
    def write(path):
        with path.open("xb") as stream:
            stream.write(payload)
        return {"path": str(path), "sha256": sha256(payload).hexdigest(), "tensor_execution": False}
    return write


def make(tmp_path, **kwargs):
    return journal.CheckpointJournal(tmp_path / "journal", "test-run", IDENTITY, **kwargs)


def test_append_reopen_and_chain(tmp_path):
    first = make(tmp_path)
    assert first.latest() is None
    one = first.commit({"next_batch": 1}, writer())
    two = first.commit({"next_batch": 2}, writer(b"second synthetic checkpoint"))
    assert two["previous_receipt_sha256"] == one["receipt_sha256"]
    reopened = make(tmp_path).latest()
    assert reopened["metadata"] == {"next_batch": 2}
    assert reopened["receipt"] == two
    assert reopened["incomplete_staging"] == []
    assert reopened["receipt"]["candidate_only"] is True
    assert reopened["receipt"]["neural_execution_by_journal"] is False


@pytest.mark.parametrize("stage", ["writer_before", "writer_after", "metadata", "receipt", "rename"])
def test_interruption_preserves_prior_commit_and_reports_staging(tmp_path, monkeypatch, stage):
    store = make(tmp_path)
    prior = store.commit({"next_batch": 1}, writer())
    original_write, original_rename = journal._write_new, journal.os.rename
    def failing_write(path, payload):
        if path.name == stage + ".json":
            raise RuntimeError("synthetic interruption")
        return original_write(path, payload)
    def failing_writer(path):
        if stage == "writer_before":
            raise RuntimeError("synthetic interruption")
        receipt = writer()(path)
        if stage == "writer_after":
            raise RuntimeError("synthetic interruption")
        return receipt
    def failing_rename(source, destination):
        if stage == "rename":
            raise RuntimeError("synthetic interruption")
        return original_rename(source, destination)
    monkeypatch.setattr(journal, "_write_new", failing_write)
    monkeypatch.setattr(journal.os, "rename", failing_rename)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        store.commit({"next_batch": 2}, failing_writer)
    latest = store.latest()
    assert latest["receipt"] == prior
    assert latest["metadata"] == {"next_batch": 1}
    assert len(latest["incomplete_staging"]) == 1


@pytest.mark.parametrize("filename", ["candidate.pt", "metadata.json", "receipt.json"])
def test_any_earlier_transaction_tampering_rejects_latest(tmp_path, filename):
    store = make(tmp_path)
    store.commit({"epoch": 1}, writer())
    store.commit({"epoch": 2}, writer())
    with (store.root / "txn-00000001" / filename).open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(journal.JournalError):
        store.latest()


def test_gap_and_identity_mismatch_fail_closed(tmp_path):
    store = make(tmp_path)
    store.commit({}, writer())
    os.rename(store.root / "txn-00000001", store.root / "txn-00000002")
    with pytest.raises(journal.JournalError, match="CHAIN_GAP"):
        store.latest()
    with pytest.raises(journal.JournalError, match="IDENTITY_MISMATCH"):
        journal.CheckpointJournal(store.root, "another-run", IDENTITY)
    with pytest.raises(journal.JournalError, match="IDENTITY_MISMATCH"):
        journal.CheckpointJournal(store.root, "test-run", {**IDENTITY, "source_sha256": "2" * 64})


def test_nonempty_root_is_not_adopted(tmp_path):
    root = tmp_path / "existing"
    root.mkdir()
    with (root / "user-data").open("xb") as stream:
        stream.write(b"preserve")
    with pytest.raises(journal.JournalError, match="NONEMPTY_UNINITIALIZED_ROOT"):
        journal.CheckpointJournal(root, "test", IDENTITY)
    assert (root / "user-data").read_bytes() == b"preserve"


def test_wrong_writer_path_is_not_committed(tmp_path):
    store = make(tmp_path)
    def wrong(path):
        receipt = writer()(path)
        receipt["path"] = str(tmp_path / "outside.pt")
        return receipt
    with pytest.raises(journal.JournalError, match="PATH_ESCAPE"):
        store.commit({}, wrong)
    assert store.latest() is None
    assert len(store.incomplete_staging) == 1


def test_byte_limits_before_publication(tmp_path, monkeypatch):
    store = make(tmp_path, max_checkpoint_bytes=8, max_metadata_bytes=64)
    with pytest.raises(journal.JournalError, match="METADATA_BYTE_LIMIT"):
        store.commit({"large": "x" * 100}, writer())
    assert store.incomplete_staging == []
    with pytest.raises(journal.JournalError, match="CHECKPOINT_BYTE_LIMIT"):
        store.commit({}, writer(b"x" * 9))
    assert store.latest() is None
    called = []
    monkeypatch.setattr(journal, "TOTAL_BYTES", 10)
    with pytest.raises(journal.JournalError, match="PROSPECTIVE_JOURNAL_BYTE_LIMIT"):
        store.commit({}, lambda path: called.append(path))
    assert called == []


@pytest.mark.parametrize("identity", [{}, {"source_sha256": "0" * 64}, {"source_sha256": "bad"},
                                      {**IDENTITY, "number": float("nan")}, {**IDENTITY, 1: "not a JSON key"}])
def test_identity_must_be_real_nonzero_pin_and_finite_json(tmp_path, identity):
    with pytest.raises(journal.JournalError):
        journal.CheckpointJournal(tmp_path / "journal", "test", identity)


def test_hardlinked_checkpoint_rejected(tmp_path):
    store = make(tmp_path)
    original = tmp_path / "original.pt"
    with original.open("xb") as stream:
        stream.write(b"hardlink test")
    def linked(path):
        os.link(original, path)
        return {"path": str(path), "sha256": sha256(original.read_bytes()).hexdigest()}
    with pytest.raises(journal.JournalError, match="HARDLINK"):
        store.commit({}, linked)


def test_root_link_or_junction_guard_runs_before_initialization(tmp_path, monkeypatch):
    root = tmp_path / "journal"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == root or original(path))
    with pytest.raises(journal.JournalError, match="LINK_PATH_REJECTED"):
        make(tmp_path)
    assert not root.exists()


def test_missing_earlier_receipt_does_not_fall_back(tmp_path):
    store = make(tmp_path)
    store.commit({"epoch": 1}, writer())
    store.commit({"epoch": 2}, writer())
    earlier = store.root / "txn-00000001"
    os.rename(earlier / "receipt.json", earlier / "receipt-preserved-for-test.json")
    with pytest.raises(journal.JournalError, match="TRANSACTION_FILES_MISMATCH"):
        store.latest()


def test_failure_after_atomic_rename_recovers_committed_checkpoint(tmp_path, monkeypatch):
    store = make(tmp_path)
    sync = journal._sync_directory
    def fail_root(path):
        if path == store.root:
            raise OSError("synthetic post-publication interruption")
        return sync(path)
    monkeypatch.setattr(journal, "_sync_directory", fail_root)
    with pytest.raises(OSError, match="post-publication"):
        store.commit({"epoch": 1}, writer())
    latest = store.latest()
    assert latest["metadata"] == {"epoch": 1}
    assert latest["receipt"]["sequence"] == 1
    assert latest["incomplete_staging"] == []


def test_module_has_no_neural_database_or_provider_imports():
    tree = ast.parse(Path(journal.__file__).read_text(encoding="utf-8"))
    forbidden = {"torch", "numpy", "sqlite3", "boto3", "botocore", "casformer", "cas_cjt"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {n.name.split(".")[0] for n in node.names} & forbidden
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden
