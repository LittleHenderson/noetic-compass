"""Fake bundle-launcher checks only: no package build or child process is run."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tools import build_teaching_bundle as builder
from cas_meta2.teaching_cycle import package, worker, worker_contract

SOURCE = "a" * 40
ARCHIVE = "b" * 64
MANIFEST = "c" * 64


@pytest.fixture
def launch(tmp_path, monkeypatch):
    output, events = tmp_path / "output", []
    flags = {name: getattr(sys.flags, name) for name in dir(sys.flags) if not name.startswith("_")}
    monkeypatch.setattr(builder.sys, "flags", SimpleNamespace(**{**flags, "isolated": 1}))
    monkeypatch.setattr(builder.sys, "dont_write_bytecode", True)
    monkeypatch.setattr(builder.sys, "path", list(sys.path))
    monkeypatch.setattr(builder, "guard", lambda: events.append(("guard",)))
    receipt = {"archive_sha256": ARCHIVE, "manifest_sha256": MANIFEST, "source_commit": SOURCE}

    def build(source, target):
        events.append(("build", source, target))
        assert source == SOURCE and target == output
        target.mkdir()
        (target / "training.zip").write_bytes(b"fake archive; never opened as a package")
        return dict(receipt)

    def extract(archive, destination, archive_pin, manifest_pin):
        events.append(("extract", archive, destination, archive_pin, manifest_pin))
        assert archive == output / "training.zip"
        assert (archive_pin, manifest_pin) == (ARCHIVE, MANIFEST)
        assert archive.is_file() and not destination.exists()
        destination.mkdir()

    def run(command, **kwargs):
        events.append(("run", command, kwargs))
        assert (output / "extracted").is_dir()
        return SimpleNamespace(returncode=0, stdout=b"fake clean admission\n", stderr=b"fake diagnostic\n")

    monkeypatch.setattr(package, "build_bundle", build)
    monkeypatch.setattr(worker_contract, "extract_bundle", extract)
    monkeypatch.setattr(builder.subprocess, "run", run)
    return SimpleNamespace(output=output, events=events, receipt=receipt,
        args=["--source-sha", SOURCE, "--output", str(output)])


def result(setup):
    receipt = json.loads((setup.output / "clean_check.json").read_bytes())
    for stream in ("stdout", "stderr"):
        raw = (setup.output / f"clean_{stream}.txt").read_bytes()
        assert receipt[stream + "_sha256"] == sha256(raw).hexdigest()
    assert receipt["source_commit"] == SOURCE
    assert receipt["archive_sha256"] == ARCHIVE
    assert receipt["manifest_sha256"] == MANIFEST
    return receipt


def test_short_fixed_child_cwd_after_verified_extraction(launch):
    assert builder.main(launch.args) == 0
    assert [event[0] for event in launch.events] == ["guard", "build", "extract", "run"]
    _, command, options = launch.events[-1]
    assert command == [sys.executable, "-I", "-B", str(Path(builder.__file__).resolve()),
        "--child", str(launch.output / "extracted"), "--manifest-sha256", MANIFEST]
    assert Path(options["cwd"]) == Path(sys.executable).parent
    assert Path(options["cwd"]) != launch.output / "extracted"
    assert options["capture_output"] is True and options["timeout"] == 120
    assert options["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    receipt = result(launch)
    assert Path(receipt["cwd"]) == Path(sys.executable).parent
    assert receipt["command"] == command and receipt["exit_code"] == 0
    assert (launch.output / "clean_stdout.txt").read_bytes() == b"fake clean admission\n"
    assert (launch.output / "clean_stderr.txt").read_bytes() == b"fake diagnostic\n"


@pytest.mark.parametrize("flag", ["--cwd", "--child-cwd", "--working-directory"])
def test_cli_cannot_override_child_working_folder(launch, flag):
    with pytest.raises(SystemExit) as stopped:
        builder.main(launch.args + [flag, str(launch.output)])
    assert stopped.value.code == 2
    assert not launch.events and not launch.output.exists()


@pytest.mark.parametrize("name", ["isolated", "bytecode"])
def test_isolation_guard_precedes_build(launch, monkeypatch, name):
    if name == "isolated":
        monkeypatch.setattr(builder.sys.flags, "isolated", 0)
    else:
        monkeypatch.setattr(builder.sys, "dont_write_bytecode", False)
    with pytest.raises(AssertionError):
        builder.main(launch.args)
    assert not launch.events and not launch.output.exists()


def test_extraction_rejection_never_runs_child(launch, monkeypatch):
    def reject(*args):
        raise ValueError("fake extraction identity rejection")
    monkeypatch.setattr(worker_contract, "extract_bundle", reject)
    with pytest.raises(ValueError, match="fake extraction identity rejection"):
        builder.main(launch.args)
    assert not any(event[0] == "run" for event in launch.events)
    assert not (launch.output / "clean_check.json").exists()


def test_existing_output_is_not_overwritten(launch):
    launch.output.mkdir()
    sentinel = launch.output / "clean_check.json"
    sentinel.write_bytes(b"old receipt must survive")
    with pytest.raises(FileExistsError):
        builder.main(launch.args)
    assert sentinel.read_bytes() == b"old receipt must survive"
    assert not any(event[0] in ("extract", "run") for event in launch.events)


def test_nonzero_child_exit_retains_raw_outputs_and_exit_code(launch, monkeypatch):
    def nonzero(command, **kwargs):
        return SimpleNamespace(returncode=19, stdout=b"partial child stdout\x00\n", stderr=b"raw child failure\r\n")
    monkeypatch.setattr(builder.subprocess, "run", nonzero)
    assert builder.main(launch.args) == 19
    receipt = result(launch)
    assert receipt["exit_code"] == 19
    assert (launch.output / "clean_stdout.txt").read_bytes() == b"partial child stdout\x00\n"
    assert (launch.output / "clean_stderr.txt").read_bytes() == b"raw child failure\r\n"


def test_launch_oserror_retains_bound_failure_receipt(launch, monkeypatch):
    def invalid_cwd(command, **kwargs):
        error = OSError(267, "fake directory name is invalid")
        error.winerror = 267
        raise error
    monkeypatch.setattr(builder.subprocess, "run", invalid_cwd)
    assert builder.main(launch.args) != 0
    receipt = result(launch)
    assert receipt["exit_code"] != 0
    assert Path(receipt["cwd"]) == Path(sys.executable).parent
    assert "267" in json.dumps(receipt)
    assert "fake directory name is invalid" in json.dumps(receipt)


def test_timeout_retains_partial_stdout_and_stderr(launch, monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 120, output=b"partial before timeout\n", stderr=b"timeout details\n")
    monkeypatch.setattr(builder.subprocess, "run", timeout)
    assert builder.main(launch.args) != 0
    receipt = result(launch)
    assert receipt["exit_code"] != 0
    assert (launch.output / "clean_stdout.txt").read_bytes() == b"partial before timeout\n"
    assert b"timeout details" in (launch.output / "clean_stderr.txt").read_bytes()


def test_worker_receipt_never_replaces_preexisting_file(launch, monkeypatch):
    original = worker_contract.extract_bundle

    def extract_and_leave_receipt(*args):
        original(*args)
        (launch.output / "clean_check.json").write_bytes(b"prior immutable receipt")

    monkeypatch.setattr(worker_contract, "extract_bundle", extract_and_leave_receipt)
    with pytest.raises(FileExistsError):
        builder.main(launch.args)
    assert (launch.output / "clean_check.json").read_bytes() == b"prior immutable receipt"


def test_guard_statically_blocks_neural_provider_and_database_imports():
    assert {"torch", "numpy", "sqlite3", "_sqlite3", "boto3", "botocore", "casformer", "cas_cjt", "cas_meta"} <= builder.FORBIDDEN
    with pytest.raises(RuntimeError, match="PURE_BUNDLE_FORBIDDEN_IMPORT:torch"):
        builder.Guard().find_spec("torch", None)
    tree = ast.parse(Path(builder.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert not {name.name.split(".")[0] for name in node.names} & builder.FORBIDDEN
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in builder.FORBIDDEN


def test_child_admits_bundle_before_source_verification_and_reports_bound_identity(launch, monkeypatch, capsys):
    child = launch.output / "already-extracted"
    events = []

    def admitted(root, pin):
        assert root == child and pin == MANIFEST
        events.append("load")
        return {"manifest": {"source_commit": SOURCE, "source_sha256": "e" * 64},
            "manifest_sha256": MANIFEST, "training_cases": [None] * 256, "development_cases": [None] * 64}

    def verified(root):
        assert root == child and events == ["load"]
        events.append("verify")

    monkeypatch.setattr(worker_contract, "load_bundle", admitted)
    monkeypatch.setattr(worker, "verify_loaded_sources", verified)
    assert builder.main(["--child", str(child), "--manifest-sha256", MANIFEST]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert events == ["load", "verify"]
    assert receipt["status"] == "CLEAN_EXTRACTED_PURE_ADMISSION_PASSED"
    assert receipt["manifest_sha256"] == MANIFEST and receipt["source_commit"] == SOURCE
    assert receipt["train"] == 256 and receipt["development"] == 64
    assert receipt["neural_execution"] is False and receipt["provider_calls"] == 0
    assert not any(event[0] in ("build", "extract", "run") for event in launch.events)
