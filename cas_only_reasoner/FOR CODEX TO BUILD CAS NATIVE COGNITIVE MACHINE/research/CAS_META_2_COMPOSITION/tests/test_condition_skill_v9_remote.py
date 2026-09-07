"""Pure tests for the condition-skill v9 remote worker.

Process creation is injected as fakes; the real trainer never runs. No
network, tensor, database, or provider work occurs.
"""
import io
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZipInfo

import pytest

from aws import condition_skill_v9_package as package
from aws import condition_skill_v9_remote as remote


COMMIT = "f" * 40


class FakePopen:
    instances = []

    def __init__(self, command, cwd, env, stdout, stderr, *, exit_code=0,
                 write_output=True, timeout_expired=False, **kwargs):
        self.command, self.cwd, self.env = command, cwd, env
        self.stdout, self.stderr = stdout, stderr
        self.exit_code = exit_code
        self.write_output = write_output
        self.timeout_expired = timeout_expired
        self.pid = 424242
        FakePopen.instances.append(self)

    def wait(self, timeout=None):
        if self.timeout_expired:
            self.timeout_expired = False
            raise subprocess.TimeoutExpired(self.command, timeout)
        if self.write_output:
            output = Path(self.command[5]).absolute()
            output.mkdir(parents=True, exist_ok=True)
            allowed = [("result.json", {"schema": "x"}),
                       ("config.json", {"schema": "x"}),
                       ("cas.selected.pt", b"weights"),
                       ("cas.trained.predictions.json", []),
                       ("cas.trained.controls.json", []),
                       ("validation.baselines.json", [])]
            for name, value in allowed:
                if isinstance(value, bytes):
                    (output / name).write_bytes(value)
                else:
                    (output / name).write_text(json.dumps(value))
        return self.exit_code


@pytest.fixture
def built_package(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()

    blobs = {}
    for index, name in enumerate(package.EXPLICIT_FILES):
        blobs[name] = b"explicit-%d" % index
    blobs[package.BASELINE_MANIFEST] = package.canonical(
        {"baseline_sha": "baseline-sha", "files": [{"path": "CASFORMER_v0_1/README.md"}]})
    blobs[package.META1 + "CASFORMER_v0_1/README.md"] = b"baseline-readme"
    blobs["research/CASFORMER_v0_1/casformer/core.py"] = b"casformer-core"

    class Fake:
        def bytes_fn(self, unused_root, commit, path):
            assert commit == COMMIT
            return blobs[path]

        def paths_fn(self, unused_root, commit, directory):
            return sorted(key for key in blobs
                          if key.startswith(directory)
                          and key not in package.EXPLICIT_FILES
                          and key != package.BASELINE_MANIFEST)

    original = package.ROOT
    package.ROOT = root
    try:
        receipt = package.build_package(root / "records" / "package_001", source_sha=COMMIT,
                                        git_bytes_fn=Fake().bytes_fn,
                                        git_paths_fn=Fake().paths_fn)
    finally:
        package.ROOT = original
    return root / "records" / "package_001", receipt


def test_allowed_trainer_output_predicate():
    allowed = ["result.json", "config.json", "selection.json", "test_predictions_blind.json",
               "training_history.json", "cas.initial.pt", "generic_attention.selected.pt",
               "cas.untrained.predictions.json", "generic_attention.trained.controls.json",
               "test_instances.baselines.json"]
    refused = ["evil.py", "result.json.bak", "other.initial.pt", "cas.predictions.json",
               "unknown.baselines.json", "train.json", "manifest.json", "../result.json"]
    assert all(remote.allowed_trainer_output(name) for name in allowed)
    assert not any(remote.allowed_trainer_output(name) for name in refused)


def test_extract_archive_rejects_unsafe_members(tmp_path):
    destination = tmp_path / "out"
    # zipfile normalizes backslashes on write, so the backslash rule is
    # checked directly against the name validator instead of a round-trip.
    with pytest.raises(ValueError, match="REMOTE_UNSAFE_MEMBER_NAME"):
        remote.safe_member_name("a\\backslash.py", set())
    bad = [
        ("../escape.py", b"x"),
        ("/absolute.py", b"x"),
        ("a//double.py", b"x"),
        ("a/./dot.py", b"x"),
        ("a/../up.py", b"x"),
    ]
    for name, payload in bad:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as zipped:
            zipped.writestr(name, payload)
        archive = tmp_path / "bad.zip"
        archive.write_bytes(buffer.getvalue())
        with pytest.raises(ValueError, match="REMOTE_UNSAFE_MEMBER_NAME"):
            remote.extract_archive(archive, destination)
        assert not destination.exists()


def test_extract_archive_rejects_duplicate_and_symlink_members(tmp_path):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zipped:
        zipped.writestr("a.txt", b"one")
        zipped.writestr("a.txt", b"two")
    archive = tmp_path / "dup.zip"
    archive.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError, match="REMOTE_DUPLICATE_MEMBER_NAME"):
        remote.extract_archive(archive, tmp_path / "out")

    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zipped:
        info = ZipInfo("link.txt")
        info.create_system = 3
        info.external_attr = (0o120777 << 16) | 0x10
        zipped.writestr(info, b"target")
    archive = tmp_path / "link.zip"
    archive.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError, match="REMOTE_SYMLINK_MEMBER"):
        remote.extract_archive(archive, tmp_path / "out2")


def test_extract_archive_enforces_member_and_expanded_bounds(tmp_path, monkeypatch):
    monkeypatch.setattr(remote, "MAX_MEMBER_BYTES", 4)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zipped:
        zipped.writestr("big.bin", b"x" * 5)
    archive = tmp_path / "big.zip"
    archive.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError, match="REMOTE_MEMBER_SIZE"):
        remote.extract_archive(archive, tmp_path / "out")


def test_run_trainer_sets_flags_paths_and_job(tmp_path):
    package_dir = tmp_path / "package"
    (package_dir / remote.PILOT_DIR).mkdir(parents=True)
    output = tmp_path / "runs" / "job"
    dataset = tmp_path / "dataset"
    output.parent.mkdir(parents=True)
    FakePopen.instances.clear()

    def popen(command, cwd, env, stdout, stderr, **kwargs):
        return FakePopen(command, cwd, env, stdout, stderr, **kwargs)

    outcome = remote.run_trainer(package_dir, output, dataset,
                                 "cas-meta2-20260907150000-abcdef12", popen=popen)
    assert outcome["exit_code"] == 0 and outcome["timed_out"] is False
    process = FakePopen.instances[0]
    assert process.env["CAS_META2_RUN_CONDITION_SKILL_V9"] == "1"
    assert process.env["CAS_META2_AWS_JOB_ID"] == "cas-meta2-20260907150000-abcdef12"
    assert process.env["CUDA_VISIBLE_DEVICES"] == "0"
    assert process.command[3] == "cas_meta2.condition_skill_v9.train"
    assert "CASFORMER_v0_1" in process.env["PYTHONPATH"]


def test_run_trainer_rejects_bad_job_label(tmp_path):
    package_dir = tmp_path / "package"
    (package_dir / remote.PILOT_DIR).mkdir(parents=True)
    with pytest.raises(ValueError, match="REMOTE_JOB_LABEL_REQUIRED"):
        remote.run_trainer(package_dir, tmp_path / "o", tmp_path / "d", "bad-job",
                           popen=FakePopen)


def test_run_trainer_timeout_kills_tree(tmp_path):
    package_dir = tmp_path / "package"
    (package_dir / remote.PILOT_DIR).mkdir(parents=True)
    killed = []

    def popen(command, cwd, env, stdout, stderr, **kwargs):
        return FakePopen(command, cwd, env, stdout, stderr, timeout_expired=True, **kwargs)

    def kill_tree(process):
        killed.append(process.pid)

    outcome = remote.run_trainer(package_dir, tmp_path / "o", tmp_path / "d",
                                 "cas-meta2-20260907150000-abcdef12",
                                 popen=popen, kill_tree=kill_tree, timeout=1)
    assert outcome["timed_out"] is True and killed == [424242]


def test_collect_trainer_output_allowlist_and_bound(tmp_path, monkeypatch):
    output = tmp_path / "out"
    output.mkdir()
    (output / "result.json").write_text(json.dumps({"schema": "x"}))
    (output / "evil.py").write_text("x")
    with pytest.raises(ValueError, match="REMOTE_UNALLOWED_TRAINER_OUTPUT"):
        remote.collect_trainer_output(output, tmp_path / "evidence")
    (output / "evil.py").unlink()
    (output / "cas.selected.pt").write_bytes(b"weights")
    collected = remote.collect_trainer_output(output, tmp_path / "evidence2")
    assert set(collected["files"]) == {"result.json", "cas.selected.pt"}

    oversized = tmp_path / "big"
    oversized.mkdir()
    (oversized / "result.json").write_text(json.dumps({"schema": "x"}))
    (oversized / "cas.selected.pt").write_bytes(b"x" * (remote.TRAINER_OUTPUT_BYTES_MAX + 1))
    with pytest.raises(ValueError, match="REMOTE_TRAINER_OUTPUT_BOUND"):
        remote.collect_trainer_output(oversized, tmp_path / "evidence3")


def test_collect_trainer_output_requires_result_json(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    (output / "config.json").write_text("{}")
    with pytest.raises(ValueError, match="REMOTE_RESULT_JSON_MISSING"):
        remote.collect_trainer_output(output, tmp_path / "evidence")


def test_orchestrate_end_to_end_with_fake_trainer(built_package, tmp_path):
    package_dir_out, receipt = built_package
    destination = tmp_path / "extracted"
    output = tmp_path / "runs" / "job"
    dataset = tmp_path / "dataset"
    output.parent.mkdir(parents=True)
    FakePopen.instances.clear()
    result = remote.orchestrate(package_dir_out / "source.zip", destination, output, dataset,
                                "cas-meta2-20260907150000-abcdef12",
                                expected_sha256=receipt["archive_sha256"],
                                expected_source_sha=COMMIT,
                                expected_manifest_sha256=receipt["manifest_sha256"],
                                popen=FakePopen)
    assert result["status"] == "REMOTE_FINISHED"
    assert result["extraction"]["members"] == receipt["member_count"]
    assert result["collected"]["files"]["result.json"]["sha256"]
    evidence = output.parent / "job.evidence"
    assert (evidence / "remote_receipt.json").is_file()
    assert FakePopen.instances[0].cwd == str(destination / remote.PILOT_DIR)


def test_orchestrate_records_failure_without_retry(built_package, tmp_path):
    package_dir_out, receipt = built_package
    destination = tmp_path / "extracted"
    output = tmp_path / "runs" / "job"
    dataset = tmp_path / "dataset"
    output.parent.mkdir(parents=True)

    def failing(command, cwd, env, stdout, stderr, **kwargs):
        return FakePopen(command, cwd, env, stdout, stderr, exit_code=1, **kwargs)

    result = remote.orchestrate(package_dir_out / "source.zip", destination, output, dataset,
                                "cas-meta2-20260907150000-abcdef12",
                                expected_sha256=receipt["archive_sha256"],
                                expected_source_sha=COMMIT,
                                expected_manifest_sha256=receipt["manifest_sha256"],
                                popen=failing)
    assert result["status"] == "REMOTE_FAILED"
    assert result["outcome"]["exit_code"] == 1
    assert result["claims"]["provider_identity_proved"] is False
