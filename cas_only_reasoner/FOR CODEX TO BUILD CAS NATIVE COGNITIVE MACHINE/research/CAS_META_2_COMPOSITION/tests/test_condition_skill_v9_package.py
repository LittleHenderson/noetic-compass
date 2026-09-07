"""Pure tests for the condition-skill v9 source package builder.

Most cases use fake Git objects. The integration case also reads the real
committed monorepo tree into memory, including every frozen baseline byte.
No network, tensor, database, or provider work occurs.
"""
import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest

from aws import condition_skill_v9_package as package


COMMIT = "f" * 40
CASFORMER_SOURCE = "research/CASFORMER_v0_1/casformer/core.py"
META1_SOURCE = package.META1 + "cas_meta1/baseline.py"
BASELINE_EXTRA = "research/CASFORMER_v0_1/README.md"
BASELINE_CJT = "research/CAS_CJT_TRANSFORMER_v0_2/schemas/runtime.json"
BASELINE_META0 = "research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/__init__.py"
REAL_COMMIT = "b777584792ac6a5fede4c97ac072d4d1313fe8c9"


def baseline_manifest_bytes(paths, blobs):
    return package.canonical({"schema": "cas-meta1.protected-baseline/1",
                              "baseline_sha": package.BASELINE_SHA,
                              "path_base": "sibling research directory",
                              "files": [{"path": path,
                                         "sha256": package.digest(blobs["research/" + path])}
                                        for path in paths]})


@pytest.fixture
def fake_blobs(monkeypatch):
    blobs = {}
    for index, name in enumerate(package.EXPLICIT_FILES):
        blobs[name] = b"explicit-%d" % index
    blobs[CASFORMER_SOURCE] = b"casformer-core"
    blobs[META1_SOURCE] = b"meta1-baseline"
    blobs[BASELINE_EXTRA] = b"baseline-readme"
    blobs[BASELINE_CJT] = b"cjt-schema"
    blobs[BASELINE_META0] = b"meta-zero-source"
    wheel_hashes = {}
    for index, name in enumerate(package.WHEELS):
        blobs[name] = b"synthetic-wheel-%d" % index
        wheel_hashes[name] = package.digest(blobs[name])
    paths = [name.removeprefix("research/") for name in
             (CASFORMER_SOURCE, BASELINE_EXTRA, BASELINE_CJT, BASELINE_META0, *package.WHEELS)]
    raw = baseline_manifest_bytes(paths, blobs)
    blobs[package.BASELINE_MANIFEST] = raw
    monkeypatch.setattr(package, "BASELINE_MANIFEST_SHA256", package.digest(raw))
    monkeypatch.setattr(package, "BASELINE_FILES", len(paths))
    monkeypatch.setattr(package, "WHEELS", wheel_hashes)
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
    expected = set(package.EXPLICIT_FILES) | {
        CASFORMER_SOURCE, META1_SOURCE, BASELINE_EXTRA, BASELINE_CJT, BASELINE_META0,
        *package.WHEELS}
    assert set(members) == expected
    assert members[BASELINE_EXTRA] == b"baseline-readme"


def test_resolve_members_rejects_baseline_path_outside_accepted_packages(fake, fake_blobs, monkeypatch):
    fake_blobs["research/somewhere/else.txt"] = b"elsewhere"
    raw = baseline_manifest_bytes(["somewhere/else.txt"], fake_blobs)
    fake_blobs[package.BASELINE_MANIFEST] = raw
    monkeypatch.setattr(package, "BASELINE_MANIFEST_SHA256", package.digest(raw))
    monkeypatch.setattr(package, "BASELINE_FILES", 1)
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
    with pytest.raises(ValueError, match="PACKAGE_BASELINE_BYTES_CHANGED"):
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


def test_baseline_manifest_identity_cannot_be_relabelled(fake, fake_blobs):
    document = json.loads(fake_blobs[package.BASELINE_MANIFEST])
    document["baseline_sha"] = "a" * 40
    fake_blobs[package.BASELINE_MANIFEST] = package.canonical(document)
    with pytest.raises(ValueError, match="PACKAGE_BASELINE_MANIFEST_CHANGED"):
        resolve(fake)


def test_missing_baseline_git_object_is_not_replaced_by_worktree(fake, fake_blobs):
    del fake_blobs[BASELINE_META0]
    with pytest.raises(KeyError, match="CASFORMER_v0_3_META_LOGIC_WIP"):
        resolve(fake)


def test_wheel_hashes_are_independently_frozen(fake, monkeypatch):
    monkeypatch.setattr(package, "WHEELS", {name: "0" * 64 for name in package.WHEELS})
    with pytest.raises(ValueError, match="PACKAGE_FROZEN_WHEEL_CHANGED"):
        resolve(fake)


def test_manifest_declares_required_sibling_layout_and_wheels(fake):
    members = resolve(fake)
    manifest = package.manifest_for(members, COMMIT, package.BASELINE_SHA)
    assert manifest["baseline_manifest"]["files_verified"] == package.BASELINE_FILES
    assert manifest["baseline_manifest"]["manifest_sha256"] == package.BASELINE_MANIFEST_SHA256
    assert manifest["git_path_prefix"] == package.GIT_PREFIX
    assert manifest["package_layout"] == {
        "pilot_dir": package.PILOT.rstrip("/"),
        "meta1_dir": package.META1.rstrip("/"),
        "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP",
        "dependency_lock": package.PILOT + "requirements-gpu.txt",
        "wheel_paths": list(package.WHEELS),
    }
    assert manifest["wheels"] == {name: {"sha256": expected, "bytes": len(members[name])}
                                   for name, expected in package.WHEELS.items()}


def test_git_access_uses_exact_monorepo_key_and_preserves_archive_paths(monkeypatch):
    calls = []
    directory = package.SOURCE_DIRS[0]
    path = directory + "/core.py"

    def run(args, cwd):
        calls.append(args)
        if "ls-tree" in args:
            return 0, ("100644 blob " + "b" * 40 + "\t" + package.GIT_PREFIX + path + "\0").encode()
        return 0, b"committed-bytes"

    monkeypatch.setattr(package, "_run_git", run)
    assert package.git_bytes(Path("unused"), COMMIT, path) == b"committed-bytes"
    assert package.git_blob(Path("unused"), COMMIT, path) == b"committed-bytes"
    assert package.git_tree_paths(Path("unused"), COMMIT, directory) == [path]
    assert calls[0][-1] == COMMIT + ":" + package.GIT_PREFIX + path
    assert calls[1][-1] == COMMIT + ":" + package.GIT_PREFIX + path
    assert "--full-tree" in calls[2] and calls[2][-1] == package.GIT_PREFIX + directory


@pytest.mark.parametrize("mode,kind", [("120000", "blob"), ("160000", "commit")])
def test_git_source_directory_refuses_nonregular_entries(monkeypatch, mode, kind):
    directory = package.SOURCE_DIRS[0]
    raw = (mode + " " + kind + " " + "b" * 40 + "\t" + package.GIT_PREFIX + directory + "/link\0").encode()
    monkeypatch.setattr(package, "_run_git", lambda args, cwd: (0, raw))
    with pytest.raises(ValueError, match="PACKAGE_GIT_REGULAR_FILE_REQUIRED"):
        package.git_tree_paths(Path("unused"), COMMIT, directory)


def test_real_committed_git_tree_resolves_complete_baseline_and_memory_archive():
    # Fixed published commit: no HEAD/working-tree fallback and no synthetic blobs.
    members = package.resolve_members(package.ROOT, REAL_COMMIT)
    assert package.digest(members[package.BASELINE_MANIFEST]) == package.BASELINE_MANIFEST_SHA256
    records = package.baseline_records(members[package.BASELINE_MANIFEST])
    assert len(records) == 316
    counts = {name: sum(path.startswith("research/" + name + "/") for path in records)
              for name in package.BASELINE_ROOTS}
    assert counts == {"CASFORMER_v0_1": 28, "CAS_CJT_TRANSFORMER_v0_2": 103,
                      "CASFORMER_v0_3_META_LOGIC_WIP": 185}
    assert package.META1 + "cas_meta1/__init__.py" in members
    assert package.META1 + "cas_meta1/baseline.py" in members
    assert package.PILOT + "cas_meta2/__init__.py" in members
    for name, expected in package.WHEELS.items():
        assert package.digest(members[name]) == expected
        with ZipFile(io.BytesIO(members[name])) as wheel:
            module = "casformer" if "casformer_reference" in name else "cas_cjt"
            assert module + "/__init__.py" in wheel.namelist()
    manifest = package.manifest_for(members, REAL_COMMIT, package.BASELINE_SHA)
    members[package.MANIFEST_NAME] = package.canonical(manifest)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, raw in members.items():
            assert not name.startswith(package.GIT_PREFIX)
            archive.writestr(name, raw)
    with ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        readback = {name: archive.read(name) for name in archive.namelist()}
    assert readback == members
    assert package.validate_members(readback, source_sha=REAL_COMMIT,
                                    manifest_sha256=package.digest(members[package.MANIFEST_NAME])) == manifest


def test_archive_file_size_is_checked_before_opening(tmp_path, monkeypatch):
    path = tmp_path / "small.zip"
    path.write_bytes(b"two")
    monkeypatch.setattr(package, "MAX_ARCHIVE_BYTES", 1)
    opened = []
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: opened.append(args) or pytest.fail("opened oversized file"))
    with pytest.raises(ValueError, match="PACKAGE_BOUNDED_REGULAR_FILE_REQUIRED"):
        package.inspect_archive(path, expected_sha256="0" * 64,
                                expected_source_sha=COMMIT, expected_manifest_sha256="0" * 64)
    assert opened == []


@pytest.mark.parametrize("case,reason", [
    ("duplicate", "PACKAGE_MEMBER_COLLISION"),
    ("case_collision", "PACKAGE_MEMBER_COLLISION"),
    ("parent_collision", "PACKAGE_FILE_DIRECTORY_COLLISION"),
    ("normalized_name", "PACKAGE_ARCHIVE_NORMALIZED_MEMBER_NAME"),
    ("nonregular", "PACKAGE_ARCHIVE_NONREGULAR_OR_ENCRYPTED_MEMBER"),
    ("encrypted", "PACKAGE_ARCHIVE_NONREGULAR_OR_ENCRYPTED_MEMBER"),
    ("count", "PACKAGE_ARCHIVE_MEMBER_COUNT_BOUND"),
    ("member_bytes", "PACKAGE_ARCHIVE_MEMBER_SIZE_BOUND"),
    ("expanded_bytes", "PACKAGE_ARCHIVE_EXPANDED_BOUND"),
])
def test_archive_metadata_is_rejected_before_any_member_read(monkeypatch, case, reason):
    first, second = ZipInfo("first.txt"), ZipInfo("second.txt")
    infos = [first, second]
    for info in infos:
        info.file_size = 1
        info.external_attr = stat.S_IFREG << 16
    if case == "duplicate":
        second.orig_filename = second.filename = first.filename
    elif case == "case_collision":
        second.orig_filename = second.filename = first.filename.upper()
    elif case == "parent_collision":
        second.orig_filename = second.filename = first.filename + "/child.txt"
    elif case == "normalized_name":
        first.orig_filename = "different.txt"
    elif case == "nonregular":
        first.external_attr = stat.S_IFLNK << 16
    elif case == "encrypted":
        first.flag_bits = 1
    elif case == "count":
        monkeypatch.setattr(package, "MAX_MEMBER_COUNT", 1)
    elif case == "member_bytes":
        monkeypatch.setattr(package, "MAX_MEMBER_BYTES", 0)
    elif case == "expanded_bytes":
        monkeypatch.setattr(package, "MAX_EXPANDED_BYTES", 1)

    class MetadataOnlyArchive:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def infolist(self):
            return infos

        def read(self, info):
            pytest.fail("member was read before all metadata passed")

    monkeypatch.setattr(package, "ZipFile", lambda stream: MetadataOnlyArchive())
    with pytest.raises(ValueError, match=reason):
        package.archive_members(b"metadata-only fake")


def minimal_extracted_manifest(name):
    return {"files_bytes": {name: 1}, "files_sha256": {name: package.digest(b"x")},
            "members": [name], "member_count": 2}


@pytest.mark.parametrize("name", ["../outside.txt", "sub/../../outside.txt", "C:/outside.txt"])
def test_extracted_names_reject_parent_escape_before_any_read(tmp_path, monkeypatch, name):
    monkeypatch.setattr(package, "read_file", lambda *args: pytest.fail("read unsafe extracted path"))
    with pytest.raises(ValueError, match="PACKAGE_UNSAFE_MEMBER_PATH"):
        package.verify_extracted(tmp_path, minimal_extracted_manifest(name))


@pytest.mark.parametrize("kind,reason", [
    ("symlink", "PACKAGE_PATH_LINK_OR_ESCAPE"),
    ("parent_junction", "PACKAGE_PATH_LINK_OR_ESCAPE"),
    ("hardlink", "PACKAGE_BOUNDED_REGULAR_FILE_REQUIRED"),
])
def test_extracted_links_are_rejected_before_any_content_read(tmp_path, monkeypatch, kind, reason):
    directory = tmp_path / "sub"
    directory.mkdir()
    target = directory / "member.txt"
    target.write_bytes(b"x")
    (tmp_path / package.MANIFEST_NAME).write_bytes(b"{}")
    if kind == "symlink":
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == target)
    elif kind == "parent_junction":
        monkeypatch.setattr(Path, "is_junction", lambda path: path == directory, raising=False)
    else:
        original = Path.stat

        def metadata(path, *args, **kwargs):
            if path == target:
                return SimpleNamespace(st_mode=stat.S_IFREG, st_nlink=2, st_size=1)
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", metadata)
    monkeypatch.setattr(package, "read_file", lambda *args: pytest.fail("read linked extracted content"))
    with pytest.raises(ValueError, match=reason):
        package.verify_extracted(tmp_path, minimal_extracted_manifest("sub/member.txt"))
