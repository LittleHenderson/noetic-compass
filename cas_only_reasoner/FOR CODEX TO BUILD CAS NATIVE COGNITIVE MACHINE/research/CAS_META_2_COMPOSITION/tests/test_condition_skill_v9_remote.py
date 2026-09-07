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
JOB = "cas-meta2-20260907150000-abcdef12"


def make_venv(root):
    python = root / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"fake interpreter; never executed")
    (python.parent.parent / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    return python


def layout(root, *, extracted=False):
    package_dir = root / "extracted"
    pilot = package_dir / remote.PILOT_DIR
    output, dataset = pilot / "runs" / JOB, pilot / remote.DATASET_DIR
    if not extracted:
        output.parent.mkdir(parents=True)
        dataset.mkdir(parents=True)
    return package_dir, output, dataset, make_venv(root)


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
        stdout.write(b"fake trainer stdout\n")
        stderr.write(b"fake trainer stderr\n")
        FakePopen.instances.append(self)

    def wait(self, timeout=None):
        if self.timeout_expired:
            self.timeout_expired = False
            raise subprocess.TimeoutExpired(self.command, timeout)
        if self.write_output:
            output = Path(self.command[self.command.index("--output") + 1]).absolute()
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
def built_package(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()

    blobs = {}
    for index, name in enumerate(package.EXPLICIT_FILES):
        blobs[name] = b"explicit-%d" % index
    baseline = {
        "research/CASFORMER_v0_1/casformer/core.py": b"casformer-core",
        "research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/network.py": b"cjt-core",
        "research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/__init__.py": b"meta-zero",
    }
    wheel_hashes = {}
    for index, name in enumerate(package.WHEELS):
        baseline[name] = b"synthetic-wheel-%d" % index
        wheel_hashes[name] = package.digest(baseline[name])
    blobs.update(baseline)
    blobs[package.META1 + "cas_meta1/baseline.py"] = b"meta-one"
    raw = package.canonical({"schema": "cas-meta1.protected-baseline/1",
        "baseline_sha": package.BASELINE_SHA, "path_base": "sibling research directory",
        "files": [{"path": name.removeprefix("research/"), "sha256": package.digest(value)}
                  for name, value in baseline.items()]})
    blobs[package.BASELINE_MANIFEST] = raw
    monkeypatch.setattr(package, "BASELINE_MANIFEST_SHA256", package.digest(raw))
    monkeypatch.setattr(package, "BASELINE_FILES", len(baseline))
    monkeypatch.setattr(package, "WHEELS", wheel_hashes)

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


def test_run_trainer_sets_flags_paths_and_job(tmp_path, monkeypatch):
    package_dir, output, dataset, python = layout(tmp_path)
    monkeypatch.setenv("PYTHONPATH", "untrusted/source/CASFORMER_v0_1")
    monkeypatch.setenv("PYTHONHOME", "untrusted")
    monkeypatch.setenv("PYTHONUSERBASE", "untrusted")
    FakePopen.instances.clear()

    def popen(command, cwd, env, stdout, stderr, **kwargs):
        return FakePopen(command, cwd, env, stdout, stderr, **kwargs)

    outcome = remote.run_trainer(package_dir, output, dataset,
                                 JOB, python_executable=python, popen=popen)
    assert outcome["exit_code"] == 0 and outcome["timed_out"] is False
    process = FakePopen.instances[0]
    assert process.env["CAS_META2_RUN_CONDITION_SKILL_V9"] == "1"
    assert process.env["CAS_META2_AWS_JOB_ID"] == "cas-meta2-20260907150000-abcdef12"
    assert process.env["CUDA_VISIBLE_DEVICES"] == "0"
    assert process.command == [str(python), "-s", "-B", "-m", "cas_meta2.condition_skill_v9.train",
                               "--output", str(output), "--dataset", str(dataset)]
    assert process.env["PYTHONPATH"] == str(package_dir / remote.PILOT_DIR)
    assert process.env["PYTHONNOUSERSITE"] == "1"
    assert "PYTHONHOME" not in process.env and "PYTHONUSERBASE" not in process.env
    assert outcome["trainer_config"]["max_seconds"] == 600
    assert outcome["automatic_retries"] == 0 and outcome["process_attempts"] == 1


def test_run_trainer_rejects_bad_job_label(tmp_path):
    package_dir, output, dataset, python = layout(tmp_path)
    with pytest.raises(ValueError, match="REMOTE_JOB_LABEL_REQUIRED"):
        remote.run_trainer(package_dir, output, dataset, "bad-job",
                           python_executable=python, popen=FakePopen)


def test_run_trainer_timeout_kills_tree(tmp_path):
    package_dir, output, dataset, python = layout(tmp_path)
    killed = []

    def popen(command, cwd, env, stdout, stderr, **kwargs):
        return FakePopen(command, cwd, env, stdout, stderr, timeout_expired=True, **kwargs)

    def kill_tree(process):
        killed.append(process.pid)

    outcome = remote.run_trainer(package_dir, output, dataset, JOB, python_executable=python,
                                 popen=popen, kill_tree=kill_tree, timeout=1)
    assert outcome["timed_out"] is True and killed == [424242]


def test_collect_trainer_output_allowlist_and_bound(tmp_path, monkeypatch):
    output = tmp_path / "out"
    output.mkdir()
    (output / "result.json").write_text(json.dumps({"schema": "x"}))
    (output / "evil.py").write_text("x")
    with pytest.raises(ValueError, match="REMOTE_UNALLOWED_TRAINER_OUTPUT"):
        remote.collect_trainer_output(output, tmp_path / "out.evidence")
    assert not (tmp_path / "out.evidence").exists()
    (output / "evil.py").unlink()
    (output / "cas.selected.pt").write_bytes(b"weights")
    collected = remote.collect_trainer_output(output, tmp_path / "out.evidence")
    assert set(collected["files"]) == {"result.json", "cas.selected.pt"}

    oversized = tmp_path / "big"
    oversized.mkdir()
    (oversized / "result.json").write_text(json.dumps({"schema": "x"}))
    (oversized / "cas.selected.pt").write_bytes(b"x" * 32)
    monkeypatch.setattr(remote, "TRAINER_OUTPUT_BYTES_MAX", 31)
    with pytest.raises(ValueError, match="REMOTE_FILE_BOUND"):
        remote.collect_trainer_output(oversized, tmp_path / "big.evidence")


def test_collect_trainer_output_retains_partial_files_without_result(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    (output / "config.json").write_text("{}")
    result = remote.collect_trainer_output(output, tmp_path / "out.evidence")
    assert result["errors"] == ["REMOTE_RESULT_JSON_MISSING"]
    assert not result["result_present"]
    assert (tmp_path / "out.evidence" / "config.json").read_bytes() == b"{}"
    assert not (tmp_path / "out.evidence" / "result.json").exists()


def test_orchestrate_end_to_end_with_fake_trainer(built_package, tmp_path):
    package_dir_out, receipt = built_package
    destination, output, dataset, python = layout(tmp_path, extracted=True)
    FakePopen.instances.clear()
    result = remote.orchestrate(package_dir_out / "source.zip", destination, output, dataset,
                                JOB, python_executable=python,
                                expected_sha256=receipt["archive_sha256"],
                                expected_source_sha=COMMIT,
                                expected_manifest_sha256=receipt["manifest_sha256"],
                                popen=FakePopen)
    assert result["status"] == "REMOTE_FINISHED"
    assert result["extraction"]["members"] == receipt["member_count"]
    assert result["collected"]["files"]["result.json"]["sha256"]
    evidence = output.with_name(output.name + ".evidence")
    assert (evidence / "remote_receipt.json").is_file()
    assert FakePopen.instances[0].cwd == str(destination / remote.PILOT_DIR)


def test_orchestrate_records_failure_without_retry(built_package, tmp_path):
    package_dir_out, receipt = built_package
    destination, output, dataset, python = layout(tmp_path, extracted=True)

    def failing(command, cwd, env, stdout, stderr, **kwargs):
        return FakePopen(command, cwd, env, stdout, stderr, exit_code=1, **kwargs)

    result = remote.orchestrate(package_dir_out / "source.zip", destination, output, dataset,
                                JOB, python_executable=python,
                                expected_sha256=receipt["archive_sha256"],
                                expected_source_sha=COMMIT,
                                expected_manifest_sha256=receipt["manifest_sha256"],
                                popen=failing)
    assert result["status"] == "REMOTE_FAILED"
    assert result["outcome"]["exit_code"] == 1
    assert result["claims"]["provider_identity_proved"] is False


@pytest.mark.parametrize("mode", ["nonzero_no_output", "zero_no_output", "spawn_failure", "partial"])
def test_orchestrate_retains_early_failure_receipt_and_logs(built_package, tmp_path, mode):
    source, identity = built_package
    destination, output, dataset, python = layout(tmp_path, extracted=True)
    calls = []

    def failing(command, cwd, env, stdout, stderr, **kwargs):
        calls.append(command)
        if mode == "spawn_failure":
            stderr.write(b"fixture spawn refused\n")
            raise OSError("fixture process could not start")
        if mode == "partial":
            output.mkdir()
            (output / "config.json").write_bytes(b"{}")
        return FakePopen(command, cwd, env, stdout, stderr,
                         exit_code=0 if mode == "zero_no_output" else 1,
                         write_output=False, **kwargs)

    result = remote.orchestrate(source / "source.zip", destination, output, dataset, JOB,
        expected_sha256=identity["archive_sha256"], expected_source_sha=COMMIT,
        expected_manifest_sha256=identity["manifest_sha256"], python_executable=python, popen=failing)
    evidence = output.with_name(output.name + ".evidence")
    assert result["status"] == "REMOTE_FAILED" and len(calls) == 1
    assert result["outcome"]["automatic_retries"] == 0
    assert "REMOTE_RESULT_JSON_MISSING" in result["collected"]["errors"]
    assert (evidence / "remote_receipt.json").is_file()
    assert (evidence / "trainer.stdout.log").is_file()
    assert (evidence / "trainer.stderr.log").read_bytes()
    assert not (evidence / "result.json").exists()
    assert not result["claims"]["learning_improvement_claimed"]
    if mode == "partial":
        assert (evidence / "config.json").read_bytes() == b"{}"
    elif mode == "spawn_failure":
        assert not result["outcome"]["process_started"]
        assert result["outcome"]["exit_code"] is None
        assert result["outcome"]["failure"]["type"] == "OSError"


@pytest.mark.parametrize("timeout", [0, -1, 601, True, "600", float("inf"), float("nan")])
def test_run_trainer_rejects_invalid_timeout_before_process(tmp_path, timeout):
    package_dir, output, dataset, python = layout(tmp_path)
    with pytest.raises(ValueError, match="REMOTE_TIMEOUT_BOUND"):
        remote.run_trainer(package_dir, output, dataset, JOB,
            python_executable=python, timeout=timeout, popen=lambda *args, **kw: pytest.fail("launched"))
    assert list(output.parent.iterdir()) == []


def test_run_trainer_rejects_changed_scalar_config_before_process(tmp_path, monkeypatch):
    from cas_meta2.condition_skill_v9 import train
    package_dir, output, dataset, python = layout(tmp_path)
    monkeypatch.setitem(train.DEFAULT_CONFIG, "max_seconds", 601)
    with pytest.raises(ValueError, match="REMOTE_TRAINER_CONFIG_BOUND"):
        remote.run_trainer(package_dir, output, dataset, JOB, python_executable=python,
            popen=lambda *args, **kw: pytest.fail("launched"))


@pytest.mark.parametrize("change,error", [
    ("outside_output", "REMOTE_OUTPUT_MUST_BE_PILOT_RUN_JOB"),
    ("accepted_records", "REMOTE_OUTPUT_MUST_BE_PILOT_RUN_JOB"),
    ("outside_dataset", "REMOTE_FROZEN_DATASET_PATH_REQUIRED"),
    ("dataset_traversal", "REMOTE_PATH_LINK_OR_TRAVERSAL"),
    ("existing_output", "REMOTE_FRESH_OUTPUT_REQUIRED"),
    ("existing_evidence", "REMOTE_FRESH_EVIDENCE_REQUIRED"),
    ("outside_python", "REMOTE_TASK_VENV_REQUIRED"),
    ("shell", "REMOTE_EXPLICIT_VENV_PYTHON_REQUIRED"),
    ("relative_python", "REMOTE_EXPLICIT_VENV_PYTHON_REQUIRED"),
    ("system_site", "REMOTE_ISOLATED_VENV_REQUIRED"),
])
def test_command_rejects_out_of_scope_paths(tmp_path, change, error):
    package_dir, output, dataset, python = layout(tmp_path)
    if change == "outside_output":
        output = tmp_path / JOB
    elif change == "accepted_records":
        output = package_dir / remote.PILOT_DIR / "records" / JOB
    elif change == "outside_dataset":
        dataset = tmp_path / "other_dataset"
    elif change == "dataset_traversal":
        dataset = dataset / ".." / "dataset_001"
    elif change == "existing_output":
        output.mkdir()
    elif change == "existing_evidence":
        output.with_name(output.name + ".evidence").mkdir()
    elif change == "outside_python":
        python = tmp_path / "other" / "bin" / "python"
    elif change == "shell":
        python = python.with_name("bash")
    elif change == "relative_python":
        python = Path("venv/bin/python")
    elif change == "system_site":
        (python.parent.parent / "pyvenv.cfg").write_text("include-system-site-packages = true\n")
    with pytest.raises(ValueError, match=error):
        remote.trainer_command(package_dir, output, dataset, JOB, python_executable=python)


def test_run_trainer_refuses_existing_logs_without_overwrite(tmp_path):
    package_dir, output, dataset, python = layout(tmp_path)
    log = output.with_name(output.name + ".trainer.stdout.log")
    log.write_bytes(b"prior evidence")
    with pytest.raises(ValueError, match="REMOTE_FRESH_LOGS_REQUIRED"):
        remote.run_trainer(package_dir, output, dataset, JOB, python_executable=python, popen=FakePopen)
    assert log.read_bytes() == b"prior evidence"


def test_collect_logs_discloses_bounded_prefix(tmp_path, monkeypatch):
    stdout, stderr = tmp_path / "stdout.log", tmp_path / "stderr.log"
    stdout.write_bytes(b"123456789")
    stderr.write_bytes(b"err")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr(remote, "LOG_BYTES_MAX", 5)
    result = remote.collect_logs({"stdout_log": str(stdout), "stderr_log": str(stderr)}, evidence)
    assert (evidence / "trainer.stdout.log").read_bytes() == b"12345"
    assert result["trainer.stdout.log"]["source_bytes"] == 9
    assert result["trainer.stdout.log"]["truncated"] is True
    assert result["trainer.stderr.log"]["truncated"] is False


def test_output_bounds_checked_before_content_read(tmp_path, monkeypatch):
    output = tmp_path / "out"
    output.mkdir()
    (output / "result.json").write_bytes(b"1234")
    (output / "config.json").write_bytes(b"1234")
    monkeypatch.setattr(remote, "TRAINER_OUTPUT_BYTES_MAX", 7)
    monkeypatch.setattr(remote, "read_bounded", lambda *args: pytest.fail("read before size gate"))
    with pytest.raises(ValueError, match="REMOTE_TRAINER_OUTPUT_BOUND"):
        remote.collect_trainer_output(output, tmp_path / "out.evidence")
    assert not (tmp_path / "out.evidence").exists()


@pytest.mark.parametrize("kind", ["output", "archive", "log"])
def test_hardlinked_inputs_are_refused(tmp_path, kind):
    original = tmp_path / "original"
    original.write_bytes(b"bytes")
    output = tmp_path / "out"
    output.mkdir()
    link = output / "result.json"
    try:
        os.link(original, link)
    except OSError as error:
        pytest.skip("hardlink fixture unavailable: " + str(error))
    with pytest.raises(ValueError, match="REMOTE_REGULAR_SINGLE_LINK_FILE_REQUIRED"):
        if kind == "output":
            remote.collect_trainer_output(output, tmp_path / "out.evidence")
        elif kind == "archive":
            remote.extract_archive(link, tmp_path / "extracted")
        else:
            evidence = tmp_path / "evidence"
            evidence.mkdir()
            remote.collect_logs({"stdout_log": str(link), "stderr_log": str(link)}, evidence)


def test_symlinked_parent_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip("symlink fixture unavailable: " + str(error))
    with pytest.raises(ValueError, match="REMOTE_PATH_LINK_OR_TRAVERSAL"):
        remote.safe_path(link / "new")


@pytest.mark.parametrize("names,error", [
    (["a", "a/b"], "REMOTE_FILE_DIRECTORY_COLLISION"),
    (["Name", "name"], "REMOTE_DUPLICATE_MEMBER_NAME"),
    (["C:escape"], "REMOTE_UNSAFE_MEMBER_NAME"),
    (["trailing."], "REMOTE_UNSAFE_MEMBER_NAME"),
])
def test_archive_name_collisions_refused_before_destination(tmp_path, names, error):
    archive = tmp_path / "source.zip"
    with ZipFile(archive, "w") as zipped:
        for name in names:
            zipped.writestr(name, b"x")
    with pytest.raises(ValueError, match=error):
        remote.extract_archive(archive, tmp_path / "destination")
    assert not (tmp_path / "destination").exists()
