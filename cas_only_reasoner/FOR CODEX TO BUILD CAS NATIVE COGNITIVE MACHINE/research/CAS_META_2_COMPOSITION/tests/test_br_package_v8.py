"""Synthetic ZIP/Git fixtures only; no model, native, budget, or provider work."""
import io
import json
from pathlib import Path
import stat
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import pytest

from aws import br_package_v8 as p


def zipped(members):
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        for name, raw in members.items():
            info = ZipInfo(name)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return stream.getvalue()


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    """Replace production pins only within this clearly synthetic unit fixture."""
    repo = tmp_path / "synthetic_repo"
    root = repo / p.PILOT
    (root / "records").mkdir(parents=True)
    monkeypatch.setattr(p, "ROOT", root)
    monkeypatch.setattr(p, "BASELINE_FILES", 1)
    monkeypatch.setattr(p, "ADDITIONS", ("cas_meta2/synthetic_br.py",))
    source_sha = "a" * 40
    new_path = root / p.ADDITIONS[0]
    new_path.parent.mkdir()
    new_path.write_bytes(b"# synthetic committed addition\n")
    committed = new_path.read_bytes()
    member = "research/CASFORMER_v0_1/synthetic_source.py"
    members = {member: b"# synthetic accepted source\n",
               **{wheel: b"synthetic inert wheel bytes " + str(i).encode() for i, wheel in enumerate(p.WHEELS)},
               p.PILOT + "requirements-gpu.txt": b"# synthetic dependency lock\n"}
    baseline = {"baseline_sha": p.BASELINE_SHA, "files": [
        {"path": member.removeprefix("research/"), "sha256": p.digest(members[member])}]}
    members[p.BASELINE_MANIFEST] = p.canonical(baseline)
    monkeypatch.setattr(p, "BASELINE_MANIFEST_SHA256", p.digest(members[p.BASELINE_MANIFEST]))
    members["launch_manifest.json"] = p.canonical({
        "pilot_dir": p.PILOT.rstrip("/"), "meta1_dir": "research/CAS_META_1_LEARNED_SELECTION",
        "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP",
        "dependency_lock": p.PILOT + "requirements-gpu.txt", "wheel_paths": list(p.WHEELS)})
    prefix = {"schema": "cas-meta2-prefix-source-package/8", "source_sha": p.BASE_SOURCE_SHA,
              "protected_baseline_files": 1, "frozen_source_files": 603, "addition_count": 11,
              "launch_enabled": False, "files_sha256": {n: p.digest(v) for n, v in members.items()}}
    members["prefix_source_manifest.json"] = p.canonical(prefix)
    monkeypatch.setattr(p, "BASE_MANIFEST_SHA256", p.digest(members["prefix_source_manifest.json"]))
    monkeypatch.setattr(p, "BASE_MEMBER_COUNT", len(members))
    raw = zipped(members)
    monkeypatch.setattr(p, "BASE_ARCHIVE_SHA256", p.digest(raw))
    monkeypatch.setattr(p, "BASE_ARCHIVE_BYTES", len(raw))
    base = root / "records/synthetic_base.zip"
    base.write_bytes(raw)
    calls = []
    def fake_git(*args):
        calls.append(args)
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo).encode()
        if args == ("rev-parse", source_sha + "^{commit}"):
            return source_sha.encode()
        if args == ("cat-file", "blob", source_sha + ":" + new_path.relative_to(repo).as_posix()):
            return committed
        raise AssertionError("Unexpected synthetic Git query: " + repr(args))
    monkeypatch.setattr(p, "git", fake_git)
    return {"base": base, "members": members, "source_sha": source_sha, "new_path": new_path,
            "output": root / "records/package", "calls": calls, "root": root}


def build(fixture):
    return p.build(fixture["base"], fixture["output"], source_sha=fixture["source_sha"])


def test_preserves_every_base_byte_and_binds_new_source_baseline_and_wheels(synthetic):
    result = build(synthetic)
    with ZipFile(result["archive"]) as archive:
        actual = {n: archive.read(n) for n in archive.namelist()}
    for name, raw in synthetic["members"].items():
        assert actual[name] == raw
    m = result["manifest"]
    assert m["root_manifest"] == "br_source_manifest.json"
    assert m["source_sha"] == synthetic["source_sha"]
    assert m["base"]["source_sha"] == p.BASE_SOURCE_SHA
    assert m["base"]["accepted_baseline"]["source_sha"] == p.BASELINE_SHA
    assert set(m["base"]["wheels"]) == set(p.WHEELS)
    assert "inert" in m["base"]["prefix_manifest_role"]
    assert set(actual) == set(m["files_sha256"]) | {p.MANIFEST_NAME}
    assert not any(m[k] for k in ("launch_enabled", "neural_execution", "native_execution", "training", "reservation_created"))
    assert p.inspect_archive(result["archive"], expected_sha256=result["archive_sha256"],
        expected_source_sha=result["source_sha"], expected_manifest_sha256=result["manifest_sha256"]) == m
    assert len(synthetic["calls"]) == 6  # Commit+local bytes checked before and after serialization.


def test_byte_deterministic_package(synthetic):
    first = build(synthetic)
    synthetic["output"] = synthetic["root"] / "records/second"
    second = build(synthetic)
    assert first["archive_sha256"] == second["archive_sha256"]
    assert first["manifest_sha256"] == second["manifest_sha256"]


def test_wrong_base_is_refused_before_git_or_output(synthetic):
    synthetic["base"].write_bytes(synthetic["base"].read_bytes() + b"changed")
    with pytest.raises(p.PackageRefused, match="EXACT_FROZEN_BASE"):
        build(synthetic)
    assert synthetic["calls"] == [] and not synthetic["output"].exists()


@pytest.mark.parametrize("source_sha", ["HEAD", "a" * 39, "A" * 40, None])
def test_exact_source_commit_required(synthetic, source_sha):
    synthetic["source_sha"] = source_sha
    with pytest.raises(p.PackageRefused, match="EXACT_COMMIT"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_uncommitted_added_bytes_are_refused(synthetic):
    synthetic["new_path"].write_bytes(b"changed worktree\n")
    with pytest.raises(p.PackageRefused, match="ADDITION_NOT_COMMITTED"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_changed_added_bytes_during_serialization_are_refused(synthetic, monkeypatch):
    original = p.committed_additions
    calls = 0
    def changed(sha):
        nonlocal calls
        calls += 1
        if calls == 2:
            synthetic["new_path"].write_bytes(b"late change")
        return original(sha)
    monkeypatch.setattr(p, "committed_additions", changed)
    with pytest.raises(p.PackageRefused, match="ADDITION_NOT_COMMITTED"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_added_member_cannot_overwrite_preserved_base(synthetic, monkeypatch):
    name = next(iter(synthetic["members"]))
    monkeypatch.setattr(p, "committed_additions", lambda _: {name: b"replacement"})
    with pytest.raises(p.PackageRefused, match="MEMBER_COLLISION"):
        build(synthetic)
    assert not synthetic["output"].exists()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\b", "a//b", "./a", "a/../b", "a\x00b", "a. "])
def test_unsafe_archive_names_are_refused(name):
    with pytest.raises(p.PackageRefused, match="UNSAFE_MEMBER_PATH"):
        p.safe_name(name)


@pytest.mark.parametrize("unsafe", [b"a\\b", b"a\x00b"])
def test_original_zip_names_are_checked_before_platform_normalization(unsafe):
    raw = zipped({"aXb": b"synthetic"}).replace(b"aXb", unsafe)
    with pytest.raises(p.PackageRefused, match="UNSAFE_MEMBER_PATH"):
        p.zip_members(raw)


@pytest.mark.parametrize("members", [{"A.py": b"a", "a.py": b"b"}, {"a": b"a", "a/b": b"b"}])
def test_case_and_file_directory_collisions_are_refused(members):
    with pytest.raises(p.PackageRefused, match="COLLISION"):
        p.zip_members(zipped(members))


def test_zip_links_and_special_files_are_refused():
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        info = ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "target")
    with pytest.raises(p.PackageRefused, match="LINK_SPECIAL"):
        p.zip_members(stream.getvalue())


@pytest.mark.parametrize("bound", ["MAX_ARCHIVE_BYTES", "MAX_EXPANDED_BYTES", "MAX_ADDITION_BYTES"])
def test_size_bounds_are_fail_closed(synthetic, monkeypatch, bound):
    monkeypatch.setattr(p, bound, 1)
    with pytest.raises(p.PackageRefused, match="SIZE_LIMIT|BOUNDED_REGULAR"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_existing_or_outside_output_is_refused(synthetic):
    synthetic["output"].mkdir()
    (synthetic["output"] / "keep.txt").write_bytes(b"keep")
    with pytest.raises(p.PackageRefused, match="NEW_IN_SCOPE"):
        build(synthetic)
    assert (synthetic["output"] / "keep.txt").read_bytes() == b"keep"
    synthetic["output"] = synthetic["root"] / "outside_records"
    with pytest.raises(p.PackageRefused, match="NEW_IN_SCOPE"):
        build(synthetic)


def test_wrong_archive_or_manifest_pin_refuses_inspection(synthetic):
    result = build(synthetic)
    with pytest.raises(p.PackageRefused, match="SOURCE_ARCHIVE_CHANGED"):
        p.inspect_archive(result["archive"], expected_sha256="0" * 64,
            expected_source_sha=result["source_sha"], expected_manifest_sha256=result["manifest_sha256"])
    with pytest.raises(p.PackageRefused, match="ROOT_MANIFEST_CHANGED"):
        p.inspect_archive(result["archive"], expected_sha256=result["archive_sha256"],
            expected_source_sha=result["source_sha"], expected_manifest_sha256="0" * 64)


def test_resealed_changed_baseline_cannot_become_a_new_base(synthetic):
    members = dict(synthetic["members"])
    members[next(iter(members))] = b"changed accepted bytes"
    with pytest.raises(p.PackageRefused, match="BASE_MEMBER_CHANGED"):
        p.base_identity(members)


def test_extracted_closure_and_import_paths_are_checked(synthetic):
    result = build(synthetic)
    extracted = synthetic["root"] / "records/extracted"
    with ZipFile(result["archive"]) as archive:
        for name in archive.namelist():
            path = extracted / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
    imported = extracted / p.PILOT / p.ADDITIONS[0]
    assert p.verify_extracted(extracted, result["manifest"], imported_paths=[imported])["files_verified"] == result["member_count"]
    with pytest.raises(p.PackageRefused, match="IMPORTED_SOURCE_OUTSIDE"):
        p.verify_extracted(extracted, result["manifest"], imported_paths=[synthetic["new_path"]])
    imported.write_bytes(b"tampered")
    with pytest.raises(p.PackageRefused, match="MANIFEST_CLOSURE_CHANGED"):
        p.verify_extracted(extracted, result["manifest"])


def test_duplicate_json_keys_and_no_model_provider_imports():
    with pytest.raises(p.PackageRefused, match="DUPLICATE_JSON_KEY"):
        p.decode(b'{"x":1,"x":2}')
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(
        name.split(".")[0] for name in sys.modules)
