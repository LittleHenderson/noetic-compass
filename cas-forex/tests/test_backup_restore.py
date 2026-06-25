"""Tests for cas_forex.backup_restore — operator state snapshot + restore."""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cas_forex import backup_restore as br


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def _write(p: Path, data: bytes | str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    p.write_bytes(data)


# ---------------------------------------------------------------- create_backup


def test_create_backup_empty_patterns_yields_empty_manifest(tmp_path):
    repo = _make_repo(tmp_path)
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo,
        snapshot_dir=snap_dir,
        file_patterns=(),
    )
    assert m.file_count == 0
    assert m.total_bytes == 0
    assert m.files == tuple()
    # A ZIP should still have been written successfully
    assert m.snapshot_path != ""
    assert Path(m.snapshot_path).exists()
    with zipfile.ZipFile(m.snapshot_path, "r") as zf:
        assert "manifest.json" in zf.namelist()


def test_create_backup_single_file_correct_sha(tmp_path):
    repo = _make_repo(tmp_path)
    payload = b'{"alpha": 1}'
    _write(repo / "strategy_leads.json", payload)

    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo,
        snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    assert m.file_count == 1
    assert m.total_bytes == len(payload)
    entry = m.files[0]
    assert entry["relative_path"] == "strategy_leads.json"
    assert entry["sha256"] == _sha(payload)
    assert entry["bytes"] == len(payload)


def test_create_backup_glob_matches_all_files(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "evidence_runs/push_subscriptions/subscriptions.jsonl", b'{"k":1}\n')
    _write(repo / "evidence_runs/webhook_subscriptions/subscriptions.jsonl", b'{"k":2}\n')

    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo,
        snapshot_dir=snap_dir,
        file_patterns=("evidence_runs/*/subscriptions.jsonl",),
    )
    rel_paths = {f["relative_path"] for f in m.files}
    assert "evidence_runs/push_subscriptions/subscriptions.jsonl" in rel_paths
    assert "evidence_runs/webhook_subscriptions/subscriptions.jsonl" in rel_paths
    assert m.file_count == 2


def test_create_backup_report_glob_keeps_latest_only(tmp_path):
    repo = _make_repo(tmp_path)
    older = repo / "evidence_runs/agent_memory/2026-06-01-report.json"
    newer = repo / "evidence_runs/agent_memory/2026-06-24-report.json"
    _write(older, b'{"old":true}')
    # Ensure mtime ordering
    os.utime(older, (1_700_000_000, 1_700_000_000))
    _write(newer, b'{"new":true}')
    os.utime(newer, (1_900_000_000, 1_900_000_000))

    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo,
        snapshot_dir=snap_dir,
        file_patterns=("evidence_runs/agent_memory/*-report.json",),
    )
    assert m.file_count == 1
    assert m.files[0]["relative_path"] == "evidence_runs/agent_memory/2026-06-24-report.json"


# ---------------------------------------------------------------- list_backups


def test_list_backups_sorted_desc_by_created_at(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b"v1")
    snap_dir = tmp_path / "snaps"
    snap_dir.mkdir()

    t1 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 6, 24, 18, 0, 0, tzinfo=timezone.utc)

    m1 = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",), now=t1,
    )
    m2 = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",), now=t2,
    )
    m3 = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",), now=t3,
    )

    listed = br.list_backups(snap_dir)
    iso_order = [m.created_at_iso for m in listed]
    assert iso_order == sorted(iso_order, reverse=True)
    assert iso_order[0] == m3.created_at_iso
    assert iso_order[-1] == m1.created_at_iso


# ---------------------------------------------------------------- evaluate_restore


def test_evaluate_restore_unchanged_repo_all_skipped(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b'{"a":1}')
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    r = br.evaluate_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)
    assert r.dry_run is True
    assert r.overwrite_count == 0
    assert r.missing_count == 0
    assert r.skipped_count == 1
    assert all(op.action == "SKIPPED_UNCHANGED" for op in r.operations)


def test_evaluate_restore_modified_file_would_overwrite(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b'{"a":1}')
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    # Mutate
    _write(repo / "strategy_leads.json", b'{"a":999}')
    r = br.evaluate_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)
    assert r.overwrite_count == 1
    assert any(op.action == "WOULD_OVERWRITE" for op in r.operations)


def test_evaluate_restore_deleted_file_would_restore_new(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b'{"a":1}')
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    (repo / "strategy_leads.json").unlink()
    r = br.evaluate_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)
    assert r.missing_count == 1
    assert any(op.action == "WOULD_RESTORE_NEW" for op in r.operations)


# ---------------------------------------------------------------- execute_restore


def test_execute_restore_writes_bytes_correctly(tmp_path):
    repo = _make_repo(tmp_path)
    original = b'{"signal": "restore-me"}'
    _write(repo / "strategy_leads.json", original)
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    # Corrupt the live file
    _write(repo / "strategy_leads.json", b"CORRUPT")
    assert (repo / "strategy_leads.json").read_bytes() == b"CORRUPT"

    r = br.execute_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)
    assert r.dry_run is False
    assert r.restored_count == 1
    assert r.overwrite_count == 1
    assert (repo / "strategy_leads.json").read_bytes() == original


def test_execute_restore_atomic_on_simulated_io_error(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    original = b"good data"
    _write(repo / "strategy_leads.json", original)
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    _write(repo / "strategy_leads.json", b"mutated")

    real_replace = os.replace

    def boom(src, dst):
        # Cleanup the temp file just like a real failure path would expect
        try:
            os.unlink(src)
        except Exception:
            pass
        raise OSError("simulated disk full")

    monkeypatch.setattr(br.os, "replace", boom)

    r = br.execute_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)
    # The live file must be untouched (still 'mutated', not 'good data', and not partial)
    assert (repo / "strategy_leads.json").read_bytes() == b"mutated"
    # No successful restore
    assert r.restored_count == 0
    # The operation should have been recorded as a write error skip
    assert any(op.action == "SKIPPED_WRITE_ERROR" for op in r.operations)


def test_execute_restore_only_files_limits_scope(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b"leads-original")
    _write(repo / "evidence_runs/operator_audit/operator-audit.jsonl", b"audit-original\n")
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=(
            "strategy_leads.json",
            "evidence_runs/operator_audit/operator-audit.jsonl",
        ),
    )
    # Corrupt both
    _write(repo / "strategy_leads.json", b"BAD-leads")
    _write(repo / "evidence_runs/operator_audit/operator-audit.jsonl", b"BAD-audit\n")

    r = br.execute_restore(
        snapshot_path=Path(m.snapshot_path),
        repo_root=repo,
        only_files=["strategy_leads.json"],
    )
    # Only the leads file should be restored
    assert (repo / "strategy_leads.json").read_bytes() == b"leads-original"
    assert (
        repo / "evidence_runs/operator_audit/operator-audit.jsonl"
    ).read_bytes() == b"BAD-audit\n"
    assert r.restored_count == 1
    assert len(r.operations) == 1
    assert r.operations[0].file_path == "strategy_leads.json"


def test_out_of_root_paths_rejected_with_skipped_out_of_root(tmp_path):
    repo = _make_repo(tmp_path)
    snap_dir = tmp_path / "snaps"
    snap_dir.mkdir()

    # Hand-craft a malicious ZIP whose manifest claims a path traversing outside repo
    snap_path = snap_dir / "cas-forex-backup-20260625T000000Z.zip"
    bad_rel = "../escaped.json"
    payload = b"PWNED"
    manifest = {
        "snapshot_id": "abcdef0123456789",
        "created_at_iso": "2026-06-25T00:00:00Z",
        "repo_root": str(repo),
        "file_count": 1,
        "total_bytes": len(payload),
        "files": [
            {
                "relative_path": bad_rel,
                "sha256": _sha(payload),
                "bytes": len(payload),
            }
        ],
    }
    with zipfile.ZipFile(snap_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr(bad_rel, payload)

    # Evaluate
    eval_r = br.evaluate_restore(snapshot_path=snap_path, repo_root=repo)
    assert any(op.action == "SKIPPED_OUT_OF_ROOT" for op in eval_r.operations)

    # Execute should also refuse
    exec_r = br.execute_restore(snapshot_path=snap_path, repo_root=repo)
    assert any(op.action == "SKIPPED_OUT_OF_ROOT" for op in exec_r.operations)
    assert exec_r.restored_count == 0
    # The escape path must not have been written anywhere reachable
    escape = (repo / bad_rel).resolve()
    assert not escape.exists() or escape.read_bytes() != payload


def test_execute_restore_idempotent(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b"original")
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    _write(repo / "strategy_leads.json", b"mutated")

    r1 = br.execute_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)
    r2 = br.execute_restore(snapshot_path=Path(m.snapshot_path), repo_root=repo)

    # First run restores; second run sees content already equals backup → SKIPPED_UNCHANGED
    assert r1.restored_count == 1
    assert r2.restored_count == 0
    assert any(op.action == "SKIPPED_UNCHANGED" for op in r2.operations)
    # File content unchanged across the second invocation
    assert (repo / "strategy_leads.json").read_bytes() == b"original"


def test_backup_archive_includes_manifest_json_at_root(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "strategy_leads.json", b'{"a":1}')
    snap_dir = tmp_path / "snaps"
    m = br.create_backup(
        repo_root=repo, snapshot_dir=snap_dir,
        file_patterns=("strategy_leads.json",),
    )
    with zipfile.ZipFile(m.snapshot_path, "r") as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        payload = json.loads(zf.read("manifest.json").decode("utf-8"))
    assert payload["snapshot_id"] == m.snapshot_id
    assert payload["file_count"] == 1
    assert payload["files"][0]["relative_path"] == "strategy_leads.json"
