"""Pure remote-lifecycle contracts. No model, network, or cloud job is run."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prefix_remote_v8", ROOT / "aws/prefix_remote_v8.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


@pytest.fixture
def config():
    with ZipFile(ROOT / "records/child_call_v8_diagnostic_001/source_001/source.zip") as zipped:
        manifest = json.loads(zipped.read("prefix_source_manifest.json"))
        old = json.loads(zipped.read("launch_manifest.json"))
    return {"schema": "cas-meta2-prefix-remote-config/8", "job": "cas-meta2-20260906000000-12345678",
            "bucket": "cas-meta2-20260906000000-12345678-807562639912", "region": "us-west-2",
            "account_id": "807562639912", "parent_source_sha": "a" * 40, "worker_source_sha": r.SOURCE_SHA,
            "source_archive_sha256": r.SOURCE_ARCHIVE_SHA, "development_archive_sha256": r.DEVELOPMENT_ARCHIVE_SHA,
            "bundle_manifest_sha256": r.BUNDLE_SHA, "source_manifest_sha256": r.MANIFEST_SHA,
            "max_worker_seconds": 1800, "artifact_bytes_max": 256 * 1024**2,
            "evidence_expanded_bytes_max": 512 * 1024**2, "source_manifest": manifest,
            "package_layout": {key: old[key] for key in ("pilot_dir", "meta1_dir", "meta_runtime_dir", "dependency_lock", "wheel_paths")},
            "resource_plan": {"instance_type": "g7.2xlarge", "instance_count": 1,
                              "runtime_seconds_max": 3600, "automatic_retries": 0}}


def test_import_and_render_do_not_run_a_process_or_model(config, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no process in render")
    monkeypatch.setattr(r.subprocess, "run", forbidden)
    monkeypatch.setattr(r.subprocess, "Popen", forbidden)
    source = r.render_remote(config)
    compile(source, "rendered-prefix-remote", "exec")
    assert source.startswith("CONFIG = ")
    assert "cas_meta2.diagnostic_v8.gpu" in source
    # The frozen manifest names historical code; no old coordinator is invoked.
    assert "prototype_remote_v7.py" not in source.split("\n", 1)[1]
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(sys.modules)


@pytest.mark.parametrize("key,value", [("region", "us-east-1"), ("account_id", "wrong"),
    ("max_worker_seconds", 1801), ("worker_source_sha", "a" * 40), ("source_archive_sha256", "a" * 64),
    ("development_archive_sha256", "a" * 64), ("bucket", "outside"), ("parent_source_sha", "short"),
    ("artifact_bytes_max", 2**30), ("job", "cas-meta2-;bad")])
def test_changed_remote_scope_refused(config, key, value):
    config[key] = value
    with pytest.raises(ValueError, match="PREFIX_REMOTE_"):
        r.validate_config(config)


def test_changed_manifest_and_old_layout_refused(config):
    bad = deepcopy(config)
    bad["source_manifest"]["source_sha"] = "a" * 40
    with pytest.raises(ValueError, match="PREFIX_REMOTE_SOURCE_MANIFEST"):
        r.validate_config(bad)
    config["package_layout"]["pilot_dir"] = "elsewhere"
    with pytest.raises(ValueError, match="PREFIX_REMOTE_PACKAGE_LAYOUT"):
        r.validate_config(config)


def test_guest_shutdown_is_armed_before_network(config):
    source = r.user_data(config, "a" * 64)
    assert source.index("sleep 3400") < source.index("timeout 90 aws s3 cp")
    assert "shutdown -h now' EXIT" in source
    assert "AWS_MAX_ATTEMPTS=1" in source
    assert "SUPPORTED_PYTHON_REQUIRED" in source
    assert "CAS_META2_PREFIX_REMOTE=1" in source
    assert len(source.encode()) <= 16384


def test_no_local_execution_even_with_synthetic_config(config, monkeypatch):
    monkeypatch.setattr(r.sys, "platform", "win32")
    with pytest.raises(ValueError, match="PREFIX_AWS_GUEST_REQUIRED"):
        r.run_remote(config)


def test_earlier_guest_shutdown_controls_all_stage_deadlines():
    now = 1788699000
    assert r.effective_deadline(now + 3480, str(now + 3400), now) == now + 3400
    assert r.effective_deadline(now + 3000, str(now + 3200), now) == now + 3000
    for guest in (None, "", str(now - 1), str(now + 3600)):
        with pytest.raises(ValueError, match="PREFIX_GUEST"):
            r.effective_deadline(now + 3480, guest, now)


@pytest.mark.parametrize("name", ["../a", "/a", "a//b", "C:/a", "a\\b", "a/./b"])
def test_archive_names_cannot_escape(name):
    with pytest.raises(ValueError, match="PREFIX_UNSAFE_ZIP_PATH"):
        r.safe_name(name)


def test_checked_extraction_preserves_bytes_and_rejects_overwrite(tmp_path):
    archive = tmp_path / "source.zip"
    with ZipFile(archive, "x") as zipped:
        zipped.writestr("a/b.txt", b"example")
    output = tmp_path / "extracted"
    mapping = {"a/b.txt": r.sha256(b"example").hexdigest()}
    r.extract_checked(archive, output, r.file_hash(archive), mapping)
    assert (output / "a/b.txt").read_bytes() == b"example"
    with pytest.raises(ValueError, match="PREFIX_ARCHIVE_OR_NEW_DIRECTORY"):
        r.extract_checked(archive, output, r.file_hash(archive), mapping)


def test_result_collection_preserves_failure_and_missing_worker_output(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "stderr.txt").write_bytes(b"admission failed before output directory")
    record = {"job": "fixture", "source_sha": r.SOURCE_SHA, "returncode": 1, "experiment": r.EXPERIMENT}
    archive = tmp_path / "artifacts.zip"
    got = r.collect_artifacts({"lifecycle": logs, "diagnostic": tmp_path / "absent"}, archive, record)
    assert got["returncode"] == 1 and got["omitted_full_file_count"] == 0
    assert got["partial_evidence"] is False  # failure is complete evidence, not success
    with ZipFile(archive) as zipped:
        assert zipped.read("lifecycle/stderr.txt") == b"admission failed before output directory"
        assert json.loads(zipped.read("artifact_collection_receipt.json"))["returncode"] == 1


def test_oversize_collection_never_claims_success(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "stdout.txt").write_bytes(b"x" * (2 * 1024**2))
    got = r.collect_artifacts({"lifecycle": logs}, tmp_path / "artifacts.zip", {"returncode": 0}, limit=3 * 1024**2)
    assert got["partial_evidence"] is True and got["returncode"] == 1
    assert got["omitted_full_file_count"] == 1


def test_process_start_failure_has_a_receipt_without_a_child(tmp_path, monkeypatch):
    def failed(*args, **kwargs):
        raise OSError("synthetic failed start")
    monkeypatch.setattr(r.subprocess, "Popen", failed)
    with pytest.raises(ValueError, match="PREFIX_CHILD_PROCESS_FAILED"):
        r.stage_process(["not-executed"], tmp_path / "stage", env={}, cwd=tmp_path,
                        seconds=2, deadline=r.time.time() + 2, output_root=tmp_path)
    receipt = json.loads((tmp_path / "stage/receipt.json").read_bytes())
    assert receipt["pid"] is None and receipt["exit_code"] is None
    assert receipt["failure"]["type"] == "OSError"
    assert receipt["outputs"]["stdout.txt"]["bytes"] == 0


def test_collection_deadline_and_emergency_receipt_are_not_success(tmp_path):
    with pytest.raises(ValueError, match="PREFIX_COLLECTION_TIME_BOUND"):
        r.collect_artifacts({"lifecycle": tmp_path}, tmp_path / "expired.zip", {"returncode": 0}, deadline=0)
    receipt = r.emergency_artifacts(tmp_path / "failure.zip", {"returncode": 0}, ValueError("expired"))
    assert receipt["returncode"] == 1 and receipt["partial_evidence"] is True
    assert receipt["full_file_counts_known"] is False and receipt["omitted_full_file_count"] is None
