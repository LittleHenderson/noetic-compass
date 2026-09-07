"""Pure tests for the condition-skill v9 source package builder.

Git access is injected as fakes, so these tests run identically everywhere.
No network, tensor, database, or provider work occurs.
"""
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from aws import condition_skill_v9_package as package


COMMIT = "f" * 40
CASFORMER_SOURCE = "research/CASFORMER_v0_1/casformer/core.py"
META1_SOURCE = package.META1 + "cas_meta1/baseline.py"
BASELINE_EXTRA = package.META1 + "CASFORMER_v0_1/README.md"


def baseline_manifest_bytes(paths):
    return package.canonical({"baseline_sha": "baseline-sha",
                              "files": [{"path": path, "sha256": "x", "bytes": 1}
                                        for path in paths]})


@pytest.fixture
def fake_blobs():
    blobs = {}
    for index, name in enumerate(package.EXPLICIT_FILES):
        blobs[name] = b"explicit-%d" % index
    blobs[package.BASELINE_MANIFEST] = baseline_manifest_bytes(["CASFORMER_v0_1/README.md"])
    blobs[CASFORMER_SOURCE] = b"casformer-core"
    blobs[META1_SOURCE] = b"meta1-baseline"
    blobs[BASELINE_EXTRA] = b"baseline-readme"
    return blobs


@pytest.fixture
def fake(fake_blobs):
    class Fake:
        def bytes_fn(self, root, commit, path):
            assert commit == COMMIT
            return fake_blobs[path]

        def paths_fn(self, root, commit, directory):
            assert commit == COMMIT
            return sorted(key for key in fake_blobs
                          if key.startswith(directory) and key not in package.EXPLICIT_FILES
                          and key != package.BASELINE_MANIFEST)
    return Fake()


def resolve(fake):
    return package.resolve_members(Path("unused"), COMMIT,
                                   git_bytes_fn=fake.bytes_fn, git_paths_fn=fake.paths_fn)


def test_resolve_members_uses_only_git_objects(fake, fake_blobs):
    members = resolve(fake)
    expected = set(package.EXPLICIT_FILES) | {CASFORMER_SOURCE, META1_SOURCE, BASELINE_EXTRA}
    assert set(members) == expected
    assert members[BASELINE_EXTRA] == b"baseline-readme"


def test_resolve_members_rejects_non_casformer_baseline_path(fake, fake_blobs):
    fake_blobs[package.BASELINE_MANIFEST] = baseline_manifest_bytes(["somewhere/else.txt"])
    fake_blobs[package.META1 + "somewhere/else.txt"] = b"elsewhere"
    with pytest.raises(ValueError, match="PACKAGE_BASELINE_PATH"):
        resolve(fake)


def test_resolve_members_rejects_bad_commit(fake):
    with pytest.raises(ValueError, match="PACKAGE_EXACT_COMMIT_REQUIRED"):
        package.resolve_members(Path("unused"), "zz", git_bytes_fn=fake.bytes_fn,
                                git_paths_fn=fake.paths_fn)


def test_resolve_members_enforces_bounds(fake, monkeypatch):
    monkeypatch.setattr(package, "MAX_MEMBER_BYTES", 10)
    with pytest.raises(ValueError, match="PACKAGE_MEMBER_TOO_LARGE"):
        resolve(fake)
    monkeypatch.setattr(package, "MAX_MEMBER_BYTES", 4 * 1024**2)
    monkeypatch.setattr(package, "MAX_EXPANDED_BYTES", 5)
    with pytest.raises(ValueError, match="PACKAGE_EXPANDED_BOUND"):
        resolve(fake)
    monkeypatch.setattr(package, "MAX_EXPANDED_BYTES", 96 * 1024**2)
    monkeypatch.setattr(package, "MAX_MEMBER_COUNT", 1)
    with pytest.raises(ValueError, match="PACKAGE_MEMBER_COUNT_BOUND"):
        resolve(fake)


def test_manifest_closure_roundtrip_and_tamper_detection(fake):
    members = resolve(fake)
    baseline = json.loads(members[package.BASELINE_MANIFEST].decode("utf-8"))
    manifest = package.manifest_for(members, COMMIT, baseline["baseline_sha"])
    raw = package.canonical(manifest)
    members[package.MANIFEST_NAME] = raw
    assert package.validate_members(members, source_sha=COMMIT,
                                    manifest_sha256=package.digest(raw)) == manifest
    tampered = dict(members)
    tampered[CASFORMER_SOURCE] = b"changed-bytes"
    with pytest.raises(ValueError, match="PACKAGE_SOURCE_CLOSURE_CHANGED"):
        package.validate_members(tampered, source_sha=COMMIT,
                                 manifest_sha256=package.digest(raw))
    with pytest.raises(ValueError, match="PACKAGE_SOURCE_SHA_MISMATCH"):
        package.validate_members(members, source_sha="a" * 40,
                                 manifest_sha256=package.digest(raw))


def test_build_package_zip_readback_receipt_and_extract(fake, monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()
    monkeypatch.setattr(package, "ROOT", root)
    output = root / "records" / "condition_skill_v9_package_001"
    receipt = package.build_package(output, source_sha=COMMIT,
                                    git_bytes_fn=fake.bytes_fn, git_paths_fn=fake.paths_fn)
    assert receipt["status"] == "SOURCE_ONLY_NO_LAUNCH"
    assert receipt["member_count"] == receipt["manifest"]["member_count"]
    archive = output / "source.zip"
    assert archive.read_bytes()
    inspected = package.inspect_archive(archive, expected_sha256=receipt["archive_sha256"],
                                        expected_source_sha=COMMIT,
                                        expected_manifest_sha256=receipt["manifest_sha256"])
    assert inspected["schema"] == package.SCHEMA
    extracted = root / "records" / "extracted"
    extracted.mkdir()
    with ZipFile(archive) as zipped:
        zipped.extractall(extracted)
    verified = package.verify_extracted(extracted, inspected, imported_paths=(CASFORMER_SOURCE,))
    assert verified["files_verified"] == receipt["member_count"]


def test_build_package_refuses_existing_or_unscoped_output(fake, monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()
    monkeypatch.setattr(package, "ROOT", root)
    with pytest.raises(ValueError, match="PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED"):
        package.build_package(root, source_sha=COMMIT, git_bytes_fn=fake.bytes_fn,
                              git_paths_fn=fake.paths_fn)


def test_inspect_archive_rejects_wrong_hash(fake, monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()
    monkeypatch.setattr(package, "ROOT", root)
    output = root / "records" / "condition_skill_v9_package_002"
    receipt = package.build_package(output, source_sha=COMMIT,
                                    git_bytes_fn=fake.bytes_fn, git_paths_fn=fake.paths_fn)
    with pytest.raises(ValueError, match="PACKAGE_ARCHIVE_HASH"):
        package.inspect_archive(output / "source.zip", expected_sha256="0" * 64,
                                expected_source_sha=COMMIT,
                                expected_manifest_sha256=receipt["manifest_sha256"])


def test_archive_with_extra_member_breaks_closure(fake, monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()
    monkeypatch.setattr(package, "ROOT", root)
    members = resolve(fake)
    baseline = json.loads(members[package.BASELINE_MANIFEST].decode("utf-8"))
    manifest = package.manifest_for(members, COMMIT, baseline["baseline_sha"])
    members[package.MANIFEST_NAME] = package.canonical(manifest)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zipped:
        for name in sorted(members):
            zipped.writestr(name, members[name])
        zipped.writestr("research/EXTRA/evil.py", b"evil")
    with pytest.raises(ValueError, match="PACKAGE_SOURCE_CLOSURE_CHANGED"):
        with ZipFile(io.BytesIO(buffer.getvalue())) as zipped:
            readback = {name: zipped.read(name) for name in zipped.namelist()}
        package.validate_members(readback, source_sha=COMMIT,
                                 manifest_sha256=package.digest(members[package.MANIFEST_NAME]))
