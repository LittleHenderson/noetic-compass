"""Synthetic-only tests for the isolated child qualification package check."""
from hashlib import sha256
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "tools/verify_child_qualification_clean_v8.py"
    spec = importlib.util.spec_from_file_location("synthetic_qualification_clean_test", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def zipped(members):
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
    return stream.getvalue()


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    """639 tiny synthetic members; no real source package, CAS database or model."""
    tool = module()
    original = tmp_path / "synthetic_original"
    original.mkdir()
    records = original / "records/child_qualification_v8_001/clean"
    monkeypatch.setattr(tool, "ROOT", original)
    monkeypatch.setattr(tool, "RECORDS", records)
    inspector = b"""from hashlib import sha256
from pathlib import Path
def verify_extracted(package, manifest, *, imported_paths=()):
    package = Path(package)
    for name, expected in manifest['files_sha256'].items():
        assert sha256((package/name).read_bytes()).hexdigest() == expected
    return {'files_verified': len(manifest['files_sha256']) + 1,
            'source_sha': manifest['source_sha'], 'synthetic': True}
"""
    members = {
        tool.PILOT + "/pyproject.toml": b'[tool.pytest.ini_options]\naddopts = "--do-not-use-this-addopt"\n',
        tool.PILOT + "/aws/__init__.py": b"",
        tool.PILOT + "/" + tool.INSPECTOR: inspector,
        tool.PILOT + "/cas_meta2/__init__.py": b"MARKER = 'extracted synthetic only'\n",
    }
    for name in tool.TESTS:
        members[tool.PILOT + "/tests/" + name] = (
            b"import cas_meta2\ndef test_synthetic_extracted_only():\n"
            b"    assert cas_meta2.MARKER == 'extracted synthetic only'\n")
    while len(members) < tool.EXPECTED_MEMBERS - 1:
        members[f"synthetic/filler_{len(members):04d}.txt"] = b"synthetic only\n"
    archive = tmp_path / "synthetic.zip"

    def seal():
        content = {n: raw for n, raw in members.items() if n != tool.MANIFEST}
        manifest = {"schema": "cas-meta2-child-qualification-source-package/8",
                    "root_manifest": tool.MANIFEST, "source_sha": "a" * 40,
                    "files_sha256": {n: sha256(raw).hexdigest() for n, raw in content.items()},
                    "files_bytes": {n: len(raw) for n, raw in content.items()}}
        members[tool.MANIFEST] = tool.canonical(manifest)
        archive.write_bytes(zipped(members))
        return manifest, {"archive_sha256": tool.digest(archive), "source_sha": "a" * 40,
            "manifest_sha256": sha256(members[tool.MANIFEST]).hexdigest()}

    manifest, pins = seal()
    return SimpleNamespace(tool=tool, archive=archive, output=records / "checks_001",
        members=members, manifest=manifest, pins=pins, seal=seal)


def test_exact_pins_precede_all_639_extracted_members(synthetic):
    f = synthetic
    result = f.tool.extract_checked(f.archive, f.output, **f.pins)
    package = Path(result["package"])
    assert result["extracted_check"]["files_verified"] == 639
    assert result["extracted_check"]["synthetic"] is True
    assert {p.relative_to(package).as_posix(): p.read_bytes()
            for p in package.rglob("*") if p.is_file()} == f.members
    assert len(result["member_sha256"]) == 639
    assert result["member_sha256"][f.tool.MANIFEST] == f.pins["manifest_sha256"]


@pytest.mark.parametrize("pin,code", (("archive_sha256", "ARCHIVE_PIN"),
    ("manifest_sha256", "MANIFEST_PIN"), ("source_sha", "ROOT_SOURCE_IDENTITY")))
def test_wrong_external_pins_refuse_before_extraction(synthetic, pin, code):
    f = synthetic
    pins = dict(f.pins, **{pin: "b" * len(f.pins[pin])})
    with pytest.raises(f.tool.CleanCheckRefused, match=code):
        f.tool.extract_checked(f.archive, f.output, **pins)
    assert not f.output.exists()


def test_missing_mandatory_test_even_with_639_members_is_refused(synthetic):
    f = synthetic
    removed = f.members.pop(f.tool.PILOT + "/tests/" + f.tool.TESTS[0])
    f.members["synthetic/replacement.txt"] = removed
    _, pins = f.seal()
    with pytest.raises(f.tool.CleanCheckRefused, match="SHIPPED_TEST_OR_INSPECTOR_MISSING"):
        f.tool.extract_checked(f.archive, f.output, **pins)
    assert not f.output.exists()


def test_resealed_outer_zip_does_not_hide_member_hash_mismatch(synthetic):
    f = synthetic
    f.members[f.tool.PILOT + "/cas_meta2/__init__.py"] = b"tampered synthetic"
    f.archive.write_bytes(zipped(f.members))
    pins = dict(f.pins, archive_sha256=f.tool.digest(f.archive))
    with pytest.raises(f.tool.CleanCheckRefused, match="MEMBER_HASH"):
        f.tool.extract_checked(f.archive, f.output, **pins)
    assert not f.output.exists()


def test_wrong_member_size_is_refused_with_matching_outer_pins(synthetic):
    f = synthetic
    f.manifest["files_bytes"][f.tool.PILOT + "/cas_meta2/__init__.py"] += 1
    f.members[f.tool.MANIFEST] = f.tool.canonical(f.manifest)
    raw = zipped(f.members)
    with pytest.raises(f.tool.CleanCheckRefused, match="MEMBER_SIZE"):
        f.tool.inspect_bytes(raw, archive_sha256=sha256(raw).hexdigest(),
            source_sha=f.pins["source_sha"], manifest_sha256=sha256(f.members[f.tool.MANIFEST]).hexdigest())


def test_manifest_member_count_cannot_be_relabelled(synthetic):
    f = synthetic
    f.members["synthetic/one_extra.txt"] = b"extra"
    _, pins = f.seal()
    with pytest.raises(f.tool.CleanCheckRefused, match="MEMBER_COUNT"):
        f.tool.extract_checked(f.archive, f.output, **pins)


@pytest.mark.parametrize("name", ("../out", "/absolute", "C:/drive", "a\\b", "a/./b", "x./b", "x /b", "a\x00b"))
def test_unsafe_zip_names_are_refused(name):
    tool = module()
    with pytest.raises(tool.CleanCheckRefused, match="UNSAFE_ZIP_NAME"):
        tool.safe_names([ZipInfo(name)])


@pytest.mark.parametrize("names", (("a", "a"), ("a", "A"), ("a", "a/b"), ("A", "a/b")))
def test_duplicate_casefold_and_file_directory_collisions_are_refused(names):
    tool = module()
    with pytest.raises(tool.CleanCheckRefused, match="MEMBER_COLLISION"):
        tool.safe_names([ZipInfo(n) for n in names])


def test_zip_symbolic_link_refused():
    tool = module()
    info = ZipInfo("synthetic_link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(tool.CleanCheckRefused, match="LINK_SPECIAL"):
        tool.safe_names([info])


def test_existing_failed_output_cannot_be_replaced(synthetic):
    f = synthetic
    f.output.mkdir(parents=True)
    keep = f.output / "stderr.txt"
    keep.write_bytes(b"earlier failure evidence")
    with pytest.raises(f.tool.CleanCheckRefused, match="NEW_SCOPED_OUTPUT"):
        f.tool.capture(f.archive, f.output, **f.pins)
    assert keep.read_bytes() == b"earlier failure evidence"


@pytest.mark.parametrize("name", ("checks_1", "checks_x", "not_checks"))
def test_output_name_must_be_explicit_new_check(synthetic, name):
    f = synthetic
    with pytest.raises(f.tool.CleanCheckRefused, match="NEW_SCOPED_OUTPUT"):
        f.tool.extract_checked(f.archive, f.output.with_name(name), **f.pins)


def test_output_outside_declared_records_is_refused(synthetic):
    f = synthetic
    with pytest.raises(f.tool.CleanCheckRefused, match="NEW_SCOPED_OUTPUT"):
        f.tool.extract_checked(f.archive, f.output.parents[2] / "checks_999", **f.pins)


def test_exact_extracted_inspector_has_no_original_worktree_fallback(synthetic):
    f = synthetic
    original_inspector = f.tool.ROOT / f.tool.INSPECTOR
    original_inspector.parent.mkdir()
    original_inspector.write_bytes(b"raise RuntimeError('original must not execute')\n")
    result = f.tool.extract_checked(f.archive, f.output, **f.pins)
    package = Path(result["package"])
    assert result["extracted_check"]["synthetic"] is True
    (package / f.tool.PILOT / f.tool.INSPECTOR).write_bytes(b"raise RuntimeError('tampered')")
    with pytest.raises(f.tool.CleanCheckRefused, match="EXTRACTED_INSPECTOR_CHANGED"):
        f.tool.package_validator(package, f.manifest)


def test_loaded_module_paths_refuse_original_and_accept_extracted(synthetic):
    f = synthetic
    package = Path(f.tool.extract_checked(f.archive, f.output, **f.pins)["package"])
    path = package / f.tool.PILOT / "cas_meta2/__init__.py"
    records = f.tool.module_paths(package, {"cas_meta2": SimpleNamespace(__file__=str(path)),
        "aws": SimpleNamespace(__file__=None, __path__=[str(package / f.tool.PILOT / "aws")])})
    assert records["cas_meta2"]["sha256"] == f.tool.digest(path)
    with pytest.raises(f.tool.CleanCheckRefused, match="ORIGINAL_WORKTREE_IMPORT"):
        f.tool.module_paths(package, {"cas_meta2.bad": SimpleNamespace(__file__=f.tool.__file__)})
    with pytest.raises(f.tool.CleanCheckRefused, match="UNOWNED_NAMESPACE"):
        f.tool.module_paths(package, {"aws": SimpleNamespace(__file__=None, __path__=[str(f.tool.ROOT)])})


@pytest.mark.parametrize("name", ("torch", "torch.nn", "boto3", "botocore", "casformer", "cas_cjt", "cas_meta"))
def test_import_guard_refuses_neural_and_provider_before_import(tmp_path, name):
    tool = module()
    with pytest.raises(RuntimeError, match="NEURAL_PROVIDER_IMPORT_REFUSED"):
        tool.ImportGuard(tmp_path).find_spec(name)


def test_import_guard_refuses_outside_aws_origin_before_execution(tmp_path, monkeypatch):
    tool = module()
    spec = importlib.machinery.ModuleSpec("aws", loader=None, origin=str(tmp_path / "original/aws.py"))
    monkeypatch.setattr(importlib.machinery.PathFinder, "find_spec", lambda *a, **k: spec)
    with pytest.raises(tool.CleanCheckRefused, match="IMPORT_FALLBACK_REFUSED"):
        tool.ImportGuard(tmp_path / "extracted").find_spec("aws")


def test_hook_counts_do_not_promote_skips_failures_or_subtests():
    tool = module()
    reports = tool.TestReceipt()
    reports.pytest_collection_finish(SimpleNamespace(items=[
        SimpleNamespace(path=Path("test_one.py")), SimpleNamespace(path=Path("test_two.py"))]))
    for when, outcome, context in (
        ("setup", "passed", None), ("call", "passed", None),
        ("call", "passed", {"synthetic_subtest": 1}),
        ("call", "failed", {"synthetic_subtest": 2}), ("setup", "skipped", None),
        ("teardown", "failed", None)):
        reports.pytest_runtest_logreport(SimpleNamespace(nodeid="synthetic", when=when, outcome=outcome, context=context))
    assert reports.counts() == {"collected": 2, "passed": 1, "failed_reports": 1, "skipped_reports": 1,
                               "subtest_reports": 2, "failed_subtest_reports": 1}


def test_invalid_archive_records_failure_without_extraction(synthetic):
    f = synthetic
    assert f.tool.capture(f.archive, f.output, **dict(f.pins, archive_sha256="0" * 64)) == 1
    receipt = json.loads((f.output / "receipt.json").read_bytes())
    assert receipt["passed"] is False and receipt["status"] == "CLEAN_CHECK_REFUSED_OR_FAILED"
    assert "ARCHIVE_PIN" in receipt["failure"]["message"]
    assert receipt["postcheck_errors"]["input_identity"]
    assert receipt["native_execution"] is False and receipt["provider_access"] is False
    assert not (f.output / "package").exists()


def test_child_start_failure_keeps_raw_logs_and_postchecks(synthetic, monkeypatch):
    f = synthetic
    def fail(command, *, cwd, env, stdout, stderr):
        assert command[1:3] == ["-I", "-B"]
        assert cwd == Path(sys.executable).resolve().parent
        assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1" and "PYTHONPATH" not in env
        stdout.write(b"synthetic child start attempt\n")
        stderr.write(b"synthetic launch failure\n")
        raise OSError("synthetic launch refusal")
    monkeypatch.setattr(f.tool.subprocess, "Popen", fail)
    assert f.tool.capture(f.archive, f.output, **f.pins) == 1
    receipt = json.loads((f.output / "receipt.json").read_bytes())
    assert "synthetic launch refusal" in receipt["failure"]["message"]
    assert receipt["postcheck"]["files_verified"] == 639
    assert receipt["outputs"]["stderr.txt"]["sha256"] == sha256(b"synthetic launch failure\n").hexdigest()
    assert receipt["outputs"]["stdout.txt"]["sha256"] == sha256(b"synthetic child start attempt\n").hexdigest()
    assert receipt["exit_code"] is None and receipt["postcheck_errors"] == {}


def test_failed_child_and_mutated_source_keep_both_failures(synthetic, monkeypatch):
    f = synthetic
    def fail(command, *, cwd, env, stdout, stderr):
        (f.output / "package" / f.tool.PILOT / "cas_meta2/__init__.py").write_bytes(b"changed synthetic")
        stderr.write(b"synthetic child failure")
        raise OSError("synthetic first failure")
    monkeypatch.setattr(f.tool.subprocess, "Popen", fail)
    assert f.tool.capture(f.archive, f.output, **f.pins) == 1
    receipt = json.loads((f.output / "receipt.json").read_bytes())
    assert receipt["failure"]["message"] == "synthetic first failure"
    assert receipt["postcheck_errors"]["extracted_source"]
    assert receipt["outputs"]["stderr.txt"]["sha256"] == sha256(b"synthetic child failure").hexdigest()


def test_fresh_isolated_child_uses_only_extracted_modules_and_all_five_files(synthetic):
    f = synthetic
    assert f.tool.capture(f.archive, f.output, **f.pins) == 0, (f.output / "stderr.txt").read_text()
    parent = json.loads((f.output / "receipt.json").read_bytes())
    receipt = parent["child_receipt"]
    assert parent["passed"] is True and parent["status"] == "CLEAN_PURE_TESTS_PASSED"
    assert parent["extracted_check"] == parent["postcheck"]
    assert receipt["before_check"] == receipt["after_check"]
    assert receipt["collected_test_files"] == sorted(f.tool.TESTS)
    assert receipt["counts"] == {"collected": 5, "passed": 5, "failed_reports": 0, "skipped_reports": 0,
                                 "subtest_reports": 0, "failed_subtest_reports": 0}
    package = Path(parent["package"])
    argv = receipt["pytest_argv"]
    assert argv[argv.index("-c") + 1] == str(package / f.tool.PILOT / "pyproject.toml")
    assert argv[argv.index("--rootdir") + 1] == argv[argv.index("--confcutdir") + 1] == str(package / f.tool.PILOT)
    paths = [r["path"] for r in receipt["imported_modules"].values() if "path" in r]
    assert paths and all(Path(p).is_relative_to(package) for p in paths)
    assert str(f.tool.ROOT) not in receipt["sys_path"]
    assert "5 passed" in (f.output / "stdout.txt").read_text()
    for name, record in parent["outputs"].items():
        assert record["sha256"] == f.tool.digest(f.output / name)


@pytest.mark.parametrize("test_body,expected", (
    ("import pytest\npytest.skip('synthetic skip')", "skipped_reports"),
    ("assert False, 'synthetic assertion failure'", "failed_reports"),
    ("import torch", "failed_reports"),
    ("import boto3", "failed_reports"),
    ("import sqlite3\nsqlite3.connect(':memory:')", "failed_reports"),
    ("import socket\nsocket.getaddrinfo('localhost', 1)", "failed_reports"),
))
def test_fresh_child_failure_skip_and_operations_refusals_are_never_passes(synthetic, test_body, expected):
    f = synthetic
    f.members[f.tool.PILOT + "/tests/" + f.tool.TESTS[0]] = (
        "def test_synthetic_refusal():\n" + "".join("    " + line + "\n" for line in test_body.splitlines())).encode()
    _, pins = f.seal()
    assert f.tool.capture(f.archive, f.output, **pins) == 1
    receipt = json.loads((f.output / "receipt.json").read_bytes())
    assert receipt["passed"] is False and receipt["postcheck_errors"] == {}
    assert receipt["child_receipt"]["counts"][expected] >= 1
    assert receipt["child_receipt"]["before_check"] == receipt["child_receipt"]["after_check"]
    assert receipt["outputs"]["stdout.txt"]["bytes"] > 0
    if "sqlite3" in test_body:
        assert "DATABASE_CONNECTION_REFUSED" in (f.output / "stdout.txt").read_text()
    if "socket" in test_body:
        assert "NETWORK_OPERATION_REFUSED" in (f.output / "stdout.txt").read_text()

