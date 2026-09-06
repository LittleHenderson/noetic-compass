"""Synthetic clean-package fixtures; no original CAS modules or real CAS database."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from zipfile import ZipFile

import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "tools/verify_br_clean_package_v8.py"
    spec = importlib.util.spec_from_file_location("synthetic_br_clean_test", path)
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
    """Parent inspection is a declared synthetic stand-in, never a real package claim."""
    tool = module()
    root = tmp_path / "synthetic_original"
    root.mkdir()
    records = root / "records/child_call_v8_construction_001/br_clean"
    monkeypatch.setattr(tool, "ROOT", root)
    monkeypatch.setattr(tool, "RECORDS", records)
    # This source is shipped only inside this synthetic test archive. The fresh
    # child imports it instead of any actual original-worktree aws module.
    inspector_source = b"""from hashlib import sha256
import json
from pathlib import Path
decode = json.loads
def verify_extracted(package, manifest, *, imported_paths=()):
    package = Path(package)
    for name, expected in manifest['files_sha256'].items():
        assert sha256((package/name).read_bytes()).hexdigest() == expected
    return {'files_verified': len(manifest['files_sha256']) + 1, 'synthetic': True}
"""
    (root / "aws").mkdir()
    (root / "aws/br_package_v8.py").write_bytes(inspector_source)
    members = {tool.PILOT + "/pyproject.toml": b'[tool.pytest.ini_options]\ntestpaths = ["tests"]\naddopts = "-m \'not gpu\'"\n',
               tool.PILOT + "/aws/__init__.py": b"",
               tool.PILOT + "/aws/br_package_v8.py": inspector_source,
               tool.PILOT + "/cas_meta2/__init__.py": b"MARKER = 'extracted synthetic only'\n"}
    for name in tool.TESTS:
        members[tool.PILOT + "/tests/" + name] = (
            b"import cas_meta2\ndef test_synthetic_extracted_only():\n"
            b"    assert cas_meta2.MARKER == 'extracted synthetic only'\n")
    manifest = {"source_sha": "a" * 40,
                "files_sha256": {name: sha256(raw).hexdigest() for name, raw in members.items()},
                "files_bytes": {name: len(raw) for name, raw in members.items()}}
    members[tool.MANIFEST] = tool.canonical(manifest)
    archive = tmp_path / "synthetic.zip"
    archive.write_bytes(zipped(members))
    pins = {"archive_sha256": tool.digest(archive), "source_sha": "a" * 40,
            "manifest_sha256": sha256(members[tool.MANIFEST]).hexdigest()}
    calls = []
    def inspect(path, *, expected_sha256, expected_source_sha, expected_manifest_sha256):
        calls.append("inspect")
        assert not records.exists(), "Inspection must precede extraction output"
        if tool.digest(path) != expected_sha256:
            raise ValueError("synthetic archive pin mismatch")
        assert expected_source_sha == pins["source_sha"]
        assert expected_manifest_sha256 == pins["manifest_sha256"]
        return manifest
    def read_members(raw):
        with ZipFile(io.BytesIO(raw)) as source:
            return {name: source.read(name) for name in source.namelist()}
    def safe_name(name):
        if name.startswith("/") or "\\" in name or ":" in name or any(part in ("", ".", "..") for part in name.split("/")):
            raise ValueError("synthetic unsafe member")
        return name
    def verify(package, value, *, imported_paths=()):
        calls.append("verify")
        for name, expected in value["files_sha256"].items():
            assert tool.digest(Path(package) / name) == expected
        return {"files_verified": len(value["files_sha256"]) + 1, "synthetic": True}
    checker = SimpleNamespace(inspect_archive=inspect, read_file=lambda p: Path(p).read_bytes(),
                              zip_members=read_members, safe_name=safe_name, verify_extracted=verify)
    monkeypatch.setattr(tool, "package_validator", lambda: checker)
    return tool, archive, records / "checks_001", pins, manifest, members, calls, checker


def test_inspection_precedes_exact_extraction(synthetic):
    tool, archive, output, pins, manifest, members, calls, _ = synthetic
    result = tool.extract_checked(archive, output, **pins)
    assert calls == ["inspect", "verify"]
    package = Path(result["package"])
    assert {p.relative_to(package).as_posix(): p.read_bytes()
            for p in package.rglob("*") if p.is_file()} == members
    assert result["member_sha256"][tool.MANIFEST] == pins["manifest_sha256"]


def test_wrong_pin_refuses_before_extraction(synthetic):
    tool, archive, output, pins, *_ = synthetic
    pins["archive_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="pin mismatch"):
        tool.extract_checked(archive, output, **pins)
    assert not output.exists()


def test_existing_output_is_preserved(synthetic):
    tool, archive, output, pins, *_ = synthetic
    output.mkdir(parents=True)
    keep = output / "keep.txt"
    keep.write_bytes(b"keep")
    with pytest.raises(tool.CleanCheckRefused, match="NEW_SCOPED"):
        tool.extract_checked(archive, output, **pins)
    assert keep.read_bytes() == b"keep"


@pytest.mark.parametrize("name", ("not_checks", "checks_x", "checks_1"))
def test_output_name_is_explicitly_bounded(synthetic, name):
    tool, archive, output, pins, *_ = synthetic
    with pytest.raises(tool.CleanCheckRefused, match="NEW_SCOPED"):
        tool.extract_checked(archive, output.with_name(name), **pins)


def test_outside_output_is_refused(synthetic):
    tool, archive, output, pins, *_ = synthetic
    with pytest.raises(tool.CleanCheckRefused, match="NEW_SCOPED"):
        tool.extract_checked(archive, output.parents[2] / "checks_999", **pins)


def test_archive_mutation_between_inspection_and_read_is_refused(synthetic):
    tool, archive, output, pins, _, _, _, checker = synthetic
    checker.read_file = lambda _: b"changed after inspection"
    with pytest.raises(tool.CleanCheckRefused, match="CHANGED_BEFORE_EXTRACTION"):
        tool.extract_checked(archive, output, **pins)
    assert not output.exists()


def test_inspector_must_be_exact_shipped_version(synthetic):
    tool, archive, output, pins, *_ = synthetic
    (tool.ROOT / "aws/br_package_v8.py").write_bytes(b"changed inspector")
    with pytest.raises(tool.CleanCheckRefused, match="INSPECTOR_NOT_ARCHIVE_VERSION"):
        tool.extract_checked(archive, output, **pins)
    assert not output.exists()


def test_missing_shipped_test_is_refused(synthetic):
    tool, archive, output, pins, manifest, members, _, checker = synthetic
    name = tool.PILOT + "/tests/" + tool.TESTS[0]
    del members[name]
    del manifest["files_sha256"][name]
    checker.zip_members = lambda _: members
    with pytest.raises(tool.CleanCheckRefused, match="SHIPPED_TEST_MISSING"):
        tool.extract_checked(archive, output, **pins)


def test_member_mismatch_is_not_extracted(synthetic):
    tool, archive, output, pins, _, members, _, checker = synthetic
    altered = dict(members)
    altered[tool.PILOT + "/cas_meta2/__init__.py"] = b"changed"
    checker.zip_members = lambda _: altered
    with pytest.raises(tool.CleanCheckRefused, match="MEMBER_BYTES_CHANGED"):
        tool.extract_checked(archive, output, **pins)
    assert not output.exists()


def test_path_report_refuses_original_worktree_module(tmp_path):
    tool = module()
    original = tmp_path / "original.py"
    original.write_bytes(b"original")
    with pytest.raises(tool.CleanCheckRefused, match="ORIGINAL_WORKTREE_IMPORT"):
        tool.module_paths(tmp_path / "package", {"cas_meta2.bad": SimpleNamespace(__file__=str(original))})


def test_path_report_accepts_only_extracted_namespace_and_files(synthetic):
    tool, archive, output, pins, *_ = synthetic
    extracted = tool.extract_checked(archive, output, **pins)
    package = Path(extracted["package"])
    path = package / tool.PILOT / "cas_meta2/__init__.py"
    result = tool.module_paths(package, {
        "cas_meta2": SimpleNamespace(__file__=str(path)),
        "aws": SimpleNamespace(__file__=None, __path__=[str(package / tool.PILOT / "aws")]),
    })
    assert result["cas_meta2"]["sha256"] == tool.digest(path)
    assert len(result["aws"]["namespace_paths"]) == 1


def test_invalid_archive_failure_receipt_is_retained(synthetic):
    tool, archive, output, pins, *_ = synthetic
    pins["archive_sha256"] = "0" * 64
    assert tool.capture(archive, output, **pins) == 1
    receipt = json.loads((output / "receipt.json").read_bytes())
    assert receipt["status"] == "CLEAN_CHECK_REFUSED_OR_FAILED"
    assert receipt["native_execution"] is False and receipt["provider_access"] is False
    assert not (output / "package").exists()


def test_fresh_child_imports_only_synthetic_extracted_cas_modules(synthetic):
    tool, archive, output, pins, *_ = synthetic
    extracted = tool.extract_checked(archive, output, **pins)
    library = Path(importlib.util.find_spec("pytest").origin).resolve().parent.parent
    receipt_path = output / "child_receipt.json"
    command = [sys.executable, "-I", "-B", str(Path(tool.__file__).resolve()), "--child",
               extracted["package"], str(output / "pytest_tmp"), str(library),
               str(receipt_path), pins["manifest_sha256"]]
    completed = subprocess.run(command, cwd=Path(sys.executable).resolve().parent, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["passed"] is True
    assert receipt["pytest_exit_code"] == 0
    paths = [r["path"] for r in receipt["imported_modules"].values() if "path" in r]
    assert paths and all(Path(p).is_relative_to(Path(extracted["package"])) for p in paths)
    assert "6 passed" in completed.stdout
    assert all(Path(p) != tool.ROOT / "aws/br_package_v8.py" for p in paths)
    assert all("synthetic_original/records/" in p.replace("\\", "/") for p in paths)
