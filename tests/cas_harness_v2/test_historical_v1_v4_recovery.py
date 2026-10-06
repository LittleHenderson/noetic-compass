from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT
    / "docs/working/project_coherence/gate5/history/"
    "HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json"
)
SOURCE_REVISION = "d9c1879762233855cd5974676b8179b1e4e75d16"
V3_RESULT_PATH = (
    ROOT
    / "docs/working/research_intervention_pythia160m_v3/runs/"
    "pythia160m-riv3-20260729161708aa2f7f3eb5b9c6cdfacd/result.json"
)
V4_EXECUTOR_PATH = (
    ROOT
    / "noetic-compass-scaffold/noetic-compass/api/services/"
    "cas_harness_pythia160m_layer_specificity_executor_v4.py"
)
V4_DELEGATE_PATH = (
    ROOT
    / "noetic-compass-scaffold/noetic-compass/api/services/"
    "cas_harness_pythia160m_research_executor.py"
)


def _load_manifest() -> dict[str, object]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _source_tree() -> dict[str, tuple[str, str]]:
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--full-tree", SOURCE_REVISION],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    records: dict[str, tuple[str, str]] = {}
    for line in completed.stdout.splitlines():
        metadata, path = line.split("\t", 1)
        mode, object_type, object_sha1 = metadata.split(" ", 2)
        assert object_type == "blob"
        records[path] = (mode, object_sha1)
    return records


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def test_recovered_current_tree_matches_every_declared_source_blob() -> None:
    manifest = _load_manifest()
    files = manifest["files"]
    assert isinstance(files, list)
    assert len(files) == 537
    source_tree = _source_tree()
    canonical_lines: list[bytes] = []
    total_bytes = 0
    paths: list[str] = []

    for record in files:
        assert isinstance(record, dict)
        relative_path = str(record["path"])
        paths.append(relative_path)
        payload = (ROOT / relative_path).read_bytes()
        total_bytes += len(payload)
        assert len(payload) == int(record["byte_count"])
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert _git_blob_sha1(payload) == record["current_git_blob_sha1"]
        assert record["current_git_blob_sha1"] == record["source_git_blob_sha1"]
        assert source_tree[relative_path] == (
            record["source_mode"],
            record["source_git_blob_sha1"],
        )
        assert record["exact_source_bytes"] is True
        canonical_lines.append(
            (
                f"{relative_path}\0{len(payload)}\0{record['sha256']}\n"
            ).encode("utf-8")
        )

    assert paths == sorted(paths)
    current_tree = manifest["current_tree"]
    assert isinstance(current_tree, dict)
    assert current_tree["file_count"] == len(files)
    assert current_tree["total_byte_count"] == total_bytes == 95_945_579
    assert current_tree["exact_source_file_count"] == len(files)
    assert current_tree["source_byte_mismatch_count"] == 0
    inventory_sha256 = hashlib.sha256(b"".join(canonical_lines)).hexdigest()
    assert inventory_sha256 == current_tree["inventory_sha256"]
    assert inventory_sha256 == (
        "361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f"
    )
    assert manifest["claim_and_gate_status_change"] == "NONE"


def test_known_v3_lf_crlf_binding_inconsistency_is_reproduced_exactly() -> None:
    manifest = _load_manifest()
    verification = manifest["frozen_binding_verification"]
    assert isinstance(verification, dict)
    mismatch = verification["mismatch"]
    assert isinstance(mismatch, dict)
    committed = mismatch["committed_source"]
    expected = mismatch["terminal_manifest_expectation"]
    reproduced = mismatch["deterministic_lf_to_crlf_reproduction"]
    assert isinstance(committed, dict)
    assert isinstance(expected, dict)
    assert isinstance(reproduced, dict)

    payload = V3_RESULT_PATH.read_bytes()
    assert b"\r\n" not in payload
    assert len(payload) == committed["byte_count"] == 467_781
    assert hashlib.sha256(payload).hexdigest() == committed["sha256"]
    crlf_payload = payload.replace(b"\n", b"\r\n")
    assert len(crlf_payload) == expected["byte_count"] == 478_182
    assert hashlib.sha256(crlf_payload).hexdigest() == expected["sha256"]
    assert reproduced["byte_count"] == expected["byte_count"]
    assert reproduced["sha256"] == expected["sha256"]
    assert reproduced["matches_manifest"] is True
    assert verification["terminal_binding_classification"] == (
        "HISTORICALLY_INCONSISTENT / NOT_INDEPENDENTLY_BYTE_CLOSED / FAIL_CLOSED"
    )


def test_known_v4_guard_name_defect_remains_fail_closed_and_unrepaired() -> None:
    executor = V4_EXECUTOR_PATH.read_text(encoding="utf-8")
    delegate = V4_DELEGATE_PATH.read_text(encoding="utf-8")

    assert "guard = base.ZeroNetworkGuard()" in executor
    assert "class CompatibleZeroNetworkGuard:" in delegate
    assert "class ZeroNetworkGuard:" not in delegate
    assert "base.CompatibleZeroNetworkGuard" not in executor


def test_supplemental_v1_scope_and_remaining_dependencies_are_explicit() -> None:
    manifest = _load_manifest()
    source_tree = _source_tree()
    restored = {
        "noetic-compass-scaffold/noetic-compass/api/services/"
        "cas_harness_research_intervention_worker.py": (
            "d8ef2f0ebea33076f2b2868a9166a3df680f400b",
            "c1b7f4a3535f05504e7b862d23470f72f88ae7ac88757768288b1316f966a13d",
        ),
        "noetic-compass-scaffold/noetic-compass/tests/"
        "test_cas_harness_research_intervention_worker.py": (
            "b0d99a0babd183d995abf46175da00dbac264644",
            "23e5a73c72a9b49a716f68dd0e90f84499dcfdf4ce086676648f8879dfb05457",
        ),
    }
    for relative_path, (blob_sha1, file_sha256) in restored.items():
        payload = (ROOT / relative_path).read_bytes()
        assert source_tree[relative_path] == ("100644", blob_sha1)
        assert _git_blob_sha1(payload) == blob_sha1
        assert hashlib.sha256(payload).hexdigest() == file_sha256

    remaining_dependencies = (
        "noetic-compass-scaffold/noetic-compass/api/services/"
        "cas_harness_research_intervention_auditor.py",
        "noetic-compass-scaffold/noetic-compass/scenarios/"
        "research_intervention_plan_v0.json",
        "noetic-compass-scaffold/noetic-compass/scenarios/"
        "research_intervention_synthetic_fixture_v0.json",
        "noetic-compass-scaffold/noetic-compass/tests/"
        "test_cas_harness_research_intervention_auditor.py",
        "docs/working/cas_harness_research_intervention_worker_v0.md",
    )
    for relative_path in remaining_dependencies:
        assert relative_path in source_tree
        assert not (ROOT / relative_path).exists()

    supplemental = manifest["supplemental_v1_worker_test_run"]
    assert isinstance(supplemental, dict)
    assert supplemental["classification"] == "HISTORICAL_FIXTURE_DEPENDENCIES_ABSENT"
    assert supplemental["model_loads"] == 0
    assert supplemental["network_calls"] == 0
    assert supplemental["live_worker_calls"] == 0
    assert supplemental["paid_compute_calls"] == 0
