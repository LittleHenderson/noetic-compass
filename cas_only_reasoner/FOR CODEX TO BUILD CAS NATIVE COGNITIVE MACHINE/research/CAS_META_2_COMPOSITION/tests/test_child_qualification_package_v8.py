"""Synthetic source/ZIP/Git tests; no real archive, neural work or provider calls."""
import io
from pathlib import Path
import stat
import subprocess
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import pytest

from aws import child_qualification_package_v8 as p


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
    """All archive contents, repository blobs and identities here are synthetic."""
    h = p.helpers
    repo = tmp_path / "repo"
    root = repo / p.PILOT
    (root / "records").mkdir(parents=True)
    monkeypatch.setattr(p, "ROOT", root)
    preserved = {"cas_meta2/old.py": b"# synthetic preserved BR source\n",
                 "aws/br_package_v8.py": b"# synthetic preserved helper identity\n"}
    new = {"cas_meta2/new.py": b"# synthetic qualification source\n",
           "aws/child_qualification_package_v8.py": b"# synthetic new packager identity\n"}
    addition_bytes = {**preserved, **new}
    monkeypatch.setattr(p, "BR_PRESERVED_FILES", {n: p.digest(v) for n, v in preserved.items()})
    monkeypatch.setattr(p, "NEW_ADDITIONS", tuple(new))
    monkeypatch.setattr(p, "ADDITIONS", tuple(addition_bytes))
    for name, raw in addition_bytes.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    accepted = "research/CASFORMER_v0_1/accepted.py"
    members = {accepted: b"# synthetic baseline bytes\n",
               **{name: b"synthetic inert wheel " + str(i).encode() for i, name in enumerate(h.WHEELS)},
               p.PILOT + "requirements-gpu.txt": b"# synthetic lock\n"}
    baseline = {"baseline_sha": h.BASELINE_SHA,
                "files": [{"path": accepted.removeprefix("research/"), "sha256": p.digest(members[accepted])}]}
    members[h.BASELINE_MANIFEST] = p.canonical(baseline)
    monkeypatch.setattr(h, "BASELINE_FILES", 1)
    monkeypatch.setattr(h, "BASELINE_MANIFEST_SHA256", p.digest(members[h.BASELINE_MANIFEST]))
    members["launch_manifest.json"] = p.canonical({
        "pilot_dir": p.PILOT.rstrip("/"), "meta1_dir": "research/CAS_META_1_LEARNED_SELECTION",
        "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP",
        "dependency_lock": p.PILOT + "requirements-gpu.txt", "wheel_paths": list(h.WHEELS)})
    members["prefix_source_manifest.json"] = p.canonical({
        "schema": "cas-meta2-prefix-source-package/8", "source_sha": h.BASE_SOURCE_SHA,
        "protected_baseline_files": 1, "frozen_source_files": 603, "addition_count": 11,
        "launch_enabled": False, "files_sha256": {n: p.digest(v) for n, v in members.items()}})
    monkeypatch.setattr(h, "BASE_MANIFEST_SHA256", p.digest(members["prefix_source_manifest.json"]))
    monkeypatch.setattr(h, "BASE_MEMBER_COUNT", len(members))
    monkeypatch.setattr(p, "BASE_MEMBER_COUNT", len(members))
    raw = zipped(members)
    monkeypatch.setattr(h, "BASE_ARCHIVE_BYTES", len(raw))
    monkeypatch.setattr(h, "BASE_ARCHIVE_SHA256", p.digest(raw))
    base = root / "records/base.zip"
    base.write_bytes(raw)
    source_sha = "a" * 40
    calls = []
    blobs = {source_sha + ":" + (root / n).relative_to(repo).as_posix(): v
             for n, v in addition_bytes.items()}

    def fake_git(*args):
        calls.append(args)
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo).encode()
        if args == ("rev-parse", source_sha + "^{commit}"):
            return source_sha.encode()
        if len(args) == 3 and args[:2] == ("cat-file", "blob") and args[2] in blobs:
            return blobs[args[2]]
        raise AssertionError("Unexpected synthetic Git call: " + repr(args))
    monkeypatch.setattr(p, "git", fake_git)
    return {"repo": repo, "root": root, "base": base, "members": members,
            "source_sha": source_sha, "output": root / "records/package",
            "additions": addition_bytes, "blobs": blobs, "calls": calls}


def build(f):
    return p.build_package(f["base"], f["output"], source_sha=f["source_sha"])


def extract(f, result):
    target = f["root"] / "records/extracted"
    for name, raw in p.zip_members(Path(result["archive"]).read_bytes()).items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return target


def test_exact_production_closure_and_qualification_only_profile():
    assert len(p.BR_PRESERVED_FILES) == 13
    assert set(p.BR_PRESERVED_FILES) == set(p.helpers.ADDITIONS)
    assert len(p.NEW_ADDITIONS) == 9 and len(p.ADDITIONS) == len(set(p.ADDITIONS)) == 22
    assert p.BASE_MEMBER_COUNT + len(p.ADDITIONS) + 1 == 639
    assert "aws/child_qualification_package_v8.py" in p.NEW_ADDITIONS
    assert "tools/check_child_qualification_v8.py" in p.NEW_ADDITIONS
    assert p.EXPERIMENT == {"profile": "one_child_full_task_qualification_v8",
                            "entrypoint": "cas_meta2.child_qualification_gpu_v8"}
    assert p.build is p.build_package


def test_preserves_base_and_br_bytes_and_binds_qualification_commit(synthetic):
    result = build(synthetic)
    actual = p.zip_members(Path(result["archive"]).read_bytes())
    for name, raw in synthetic["members"].items():
        assert actual[name] == raw
    for name, raw in synthetic["additions"].items():
        assert actual[p.PILOT + name] == raw
    m = result["manifest"]
    assert result["schema"] == "cas-meta2-child-qualification-source-package-receipt/8"
    assert m["schema"] == "cas-meta2-child-qualification-source-package/8"
    assert m["root_manifest"] == "child_qualification_source_manifest.json"
    assert m["source_sha"] == synthetic["source_sha"]
    assert m["experiment"] == p.EXPERIMENT
    assert m["preserved_br"]["source_sha"] == p.BR_SOURCE_SHA
    assert m["preserved_br"]["files_sha256"] == {p.PILOT + n: h for n, h in p.BR_PRESERVED_FILES.items()}
    assert m["base"]["accepted_baseline"]["source_sha"] == p.helpers.BASELINE_SHA
    assert set(m["base"]["wheels"]) == set(p.helpers.WHEELS)
    assert "inert" in m["base"]["prefix_manifest_role"]
    assert not any(m[k] for k in ("launch_enabled", "neural_execution", "native_execution",
                                  "training", "reservation_created", "old_br_launch_authorized"))
    assert set(actual) == set(m["files_sha256"]) | {p.MANIFEST_NAME}
    assert p.inspect_archive(result["archive"], expected_sha256=result["archive_sha256"],
        expected_source_sha=result["source_sha"], expected_manifest_sha256=result["manifest_sha256"]) == m
    assert len(synthetic["calls"]) == 2 * (2 + len(p.ADDITIONS))


def test_byte_deterministic_output(synthetic):
    a = build(synthetic)
    synthetic["output"] = synthetic["root"] / "records/package2"
    b = build(synthetic)
    assert a["archive_sha256"] == b["archive_sha256"]
    assert a["manifest_sha256"] == b["manifest_sha256"]


def test_old_br_inspector_cannot_admit_new_root(synthetic):
    result = build(synthetic)
    assert "br_source_manifest.json" not in p.zip_members(Path(result["archive"]).read_bytes())
    with pytest.raises(p.PackageRefused, match="ROOT_MANIFEST_CHANGED"):
        p.helpers.inspect_archive(result["archive"], expected_sha256=result["archive_sha256"],
            expected_source_sha=result["source_sha"], expected_manifest_sha256=result["manifest_sha256"])


def test_returned_manifest_cannot_mutate_experiment_contract(synthetic):
    result = build(synthetic)
    result["manifest"]["experiment"]["entrypoint"] = "cas_meta2.train_v3"
    assert p.EXPERIMENT["entrypoint"] == "cas_meta2.child_qualification_gpu_v8"


def test_wrong_base_refuses_before_git_or_write(synthetic):
    synthetic["base"].write_bytes(b"not the pinned base")
    with pytest.raises(p.PackageRefused, match="EXACT_FROZEN_BASE"):
        build(synthetic)
    assert synthetic["calls"] == [] and not synthetic["output"].exists()


@pytest.mark.parametrize("source_sha", ["HEAD", "a" * 39, "A" * 40, None])
def test_full_commit_required(synthetic, source_sha):
    synthetic["source_sha"] = source_sha
    with pytest.raises(p.PackageRefused, match="EXACT_COMMIT"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_commit_resolver_must_match_exact_sha(synthetic, monkeypatch):
    monkeypatch.setattr(p, "git", lambda *args: b"b" * 40)
    with pytest.raises(p.PackageRefused, match="EXACT_COMMIT"):
        build(synthetic)
    assert not synthetic["output"].exists()


@pytest.mark.parametrize("name", ["cas_meta2/old.py", "cas_meta2/new.py",
                                  "aws/child_qualification_package_v8.py"])
def test_uncommitted_addition_refused_including_own_package(synthetic, name):
    (synthetic["root"] / name).write_bytes(b"changed")
    with pytest.raises(p.PackageRefused, match="ADDITION_NOT_COMMITTED"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_committed_changed_br_file_still_refused(synthetic):
    name = "cas_meta2/old.py"
    (synthetic["root"] / name).write_bytes(b"new committed but changed BR bytes")
    synthetic["blobs"][synthetic["source_sha"] + ":" +
        (synthetic["root"] / name).relative_to(synthetic["repo"]).as_posix()] = b"new committed but changed BR bytes"
    with pytest.raises(p.PackageRefused, match="PRESERVED_BR_CHANGED"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_second_read_rejects_mid_build_edit(synthetic, monkeypatch):
    original = p.committed_additions
    calls = 0
    def reread(source_sha):
        nonlocal calls
        calls += 1
        if calls == 2:
            (synthetic["root"] / "cas_meta2/new.py").write_bytes(b"late edit")
        return original(source_sha)
    monkeypatch.setattr(p, "committed_additions", reread)
    with pytest.raises(p.PackageRefused, match="ADDITION_NOT_COMMITTED"):
        build(synthetic)
    assert not synthetic["output"].exists()


def test_preserved_base_cannot_be_overwritten(synthetic, monkeypatch):
    name = next(iter(synthetic["members"]))
    monkeypatch.setattr(p, "committed_additions", lambda _: {name: b"replacement"})
    with pytest.raises(p.PackageRefused, match="MEMBER_COLLISION"):
        build(synthetic)
    assert not synthetic["output"].exists()


@pytest.mark.parametrize("field,value", [
    ("training", True), ("old_br_launch_authorized", True), ("launch_enabled", True),
    ("experiment", {"entrypoint": "cas_meta2.br_construction_v8", "profile": "same_state_br_construction_v8"}),
    ("experiment", {"entrypoint": "cas_meta2.train_v3", "profile": "training"}),
])
def test_resealed_wrong_authority_or_profile_is_rejected(synthetic, field, value):
    result = build(synthetic)
    members = p.zip_members(Path(result["archive"]).read_bytes())
    manifest = p.decode(members[p.MANIFEST_NAME])
    manifest[field] = value
    members[p.MANIFEST_NAME] = p.canonical(manifest)
    with pytest.raises(p.PackageRefused, match="MANIFEST_CLOSURE_CHANGED"):
        p.validate_members(members, source_sha=result["source_sha"],
                           manifest_sha256=p.digest(members[p.MANIFEST_NAME]))


def test_resealed_preserved_br_change_rejected(synthetic):
    result = build(synthetic)
    members = p.zip_members(Path(result["archive"]).read_bytes())
    name = p.PILOT + "cas_meta2/old.py"
    members[name] = b"changed"
    manifest = p.decode(members[p.MANIFEST_NAME])
    manifest["files_sha256"][name] = p.digest(members[name])
    manifest["files_bytes"][name] = len(members[name])
    members[p.MANIFEST_NAME] = p.canonical(manifest)
    with pytest.raises(p.PackageRefused, match="PRESERVED_BR_CHANGED"):
        p.validate_members(members, source_sha=result["source_sha"],
                           manifest_sha256=p.digest(members[p.MANIFEST_NAME]))


@pytest.mark.parametrize("pin", ["archive", "manifest", "commit"])
def test_inspection_exact_pins(synthetic, pin):
    result = build(synthetic)
    args = dict(expected_sha256=result["archive_sha256"], expected_source_sha=result["source_sha"],
                expected_manifest_sha256=result["manifest_sha256"])
    args[{"archive": "expected_sha256", "manifest": "expected_manifest_sha256",
          "commit": "expected_source_sha"}[pin]] = "0" * (40 if pin == "commit" else 64)
    with pytest.raises(p.PackageRefused):
        p.inspect_archive(result["archive"], **args)


def test_new_in_scope_output_and_preservation(synthetic):
    synthetic["output"].mkdir()
    (synthetic["output"] / "keep").write_bytes(b"keep")
    with pytest.raises(p.PackageRefused, match="NEW_IN_SCOPE_OUTPUT"):
        build(synthetic)
    assert (synthetic["output"] / "keep").read_bytes() == b"keep"
    synthetic["output"] = synthetic["root"] / "outside"
    with pytest.raises(p.PackageRefused, match="NEW_IN_SCOPE_OUTPUT"):
        build(synthetic)


def test_extracted_closure_actual_import_path_and_changed_bytes(synthetic):
    result = build(synthetic)
    extracted = extract(synthetic, result)
    imported = extracted / p.PILOT / "aws/child_qualification_package_v8.py"
    assert p.verify_extracted(extracted, result["manifest"], imported_paths=[imported])["files_verified"] == result["member_count"]
    with pytest.raises(p.PackageRefused, match="IMPORTED_SOURCE_OUTSIDE"):
        p.verify_extracted(extracted, result["manifest"], imported_paths=[synthetic["root"] / "cas_meta2/new.py"])
    imported.write_bytes(b"tamper")
    with pytest.raises(p.PackageRefused, match="MANIFEST_CLOSURE_CHANGED"):
        p.verify_extracted(extracted, result["manifest"])


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\b", "a//b",
                                 "./a", "a/../b", "a\x00b", "a. "])
def test_shared_path_guard_rejects_unsafe_members(name):
    with pytest.raises(p.PackageRefused, match="UNSAFE_MEMBER_PATH"):
        p.safe_name(name)


@pytest.mark.parametrize("names", [("A.py", "a.py"), ("a", "a/b")])
def test_shared_zip_guard_rejects_collisions(names):
    with pytest.raises(p.PackageRefused, match="COLLISION"):
        p.zip_members(zipped({n: b"x" for n in names}))


def test_shared_zip_guard_rejects_links():
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        info = ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    with pytest.raises(p.PackageRefused, match="LINK_SPECIAL"):
        p.zip_members(stream.getvalue())


def test_shared_json_guard_and_helper_identity(monkeypatch):
    with pytest.raises(p.PackageRefused, match="DUPLICATE_JSON_KEY"):
        p.decode(b'{"x":1,"x":2}')
    monkeypatch.setattr(p, "HELPER_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="HELPER_CHANGED"):
        p.helper_bytes()


def test_isolated_copy_import_uses_only_shipped_helper(tmp_path):
    # Copy packaging source only, not any runtime or real archive. The copied
    # package must import without the original worktree on sys.path.
    package = tmp_path / "isolated"
    package.mkdir()
    package_source = Path(p.__file__).read_bytes()
    _, helper_source = p.helper_bytes()
    (package / "child_qualification_package_v8.py").write_bytes(package_source)
    (package / "br_package_v8.py").write_bytes(helper_source)
    code = ("import importlib.util,pathlib,sys;"
            "path=pathlib.Path(sys.argv[1]);"
            "spec=importlib.util.spec_from_file_location('isolated_qualification_package',path);"
            "module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);"
            "assert pathlib.Path(module.helpers.__file__).parent==path.parent;"
            "assert not {'torch','cas_cjt','casformer','boto3','botocore','sqlite3'} & set(sys.modules);"
            "print(module.SCHEMA)")
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code,
                             str(package / "child_qualification_package_v8.py")],
                            cwd=Path(sys.executable).parent, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == p.SCHEMA
    assert not list(package.rglob("*.pyc"))


def test_no_neural_native_provider_or_sqlite_imports():
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(
        name.split(".")[0] for name in sys.modules)
