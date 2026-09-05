"""Synthetic byte packets only. No fixture is native semantic or AWS evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import zipfile

import pytest

from test_launch import launch, synthetic_roots, encoded
from cas_meta3.native_demo import fixed_task, source_identity

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta3_outer_inspector_tested", ROOT / "tools/inspect_cloud_packet.py")
inspect_packet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect_packet)


@pytest.fixture
def isolated_inspector(tmp_path, monkeypatch):
    # Exercise packet/extraction paths inside short test scratch. Real source
    # authority is explicitly mocked, not passed off as Git/native evidence.
    fake_root = tmp_path / "pilot"
    fake_root.mkdir()
    monkeypatch.setattr(inspect_packet, "ROOT", fake_root)
    monkeypatch.setattr(inspect_packet, "_trusted_launcher", lambda manifest, source: launch)
    monkeypatch.setattr(inspect_packet, "_code_hashes", lambda: {"mock_test_source_gate": "a" * 64})
    return fake_root


def full_fixture(tmp_path, change=None, *, partial=False):
    job, demo, native, roots = synthetic_roots(tmp_path)
    source = source_identity()  # Pure file hashes only; no model/label generation.
    source_sha, archive_sha = "b" * 40, "e" * 64
    raw_receipt = json.loads((demo / "memory_demo_receipt.json").read_bytes())
    environment = {"job": job, "cuda_device": "cuda:0", "gpu_name": "NVIDIA RTX PRO 4500",
                   "torch": "2.11.0+cu128", "cuda_runtime": "12.8",
                   "deterministic_algorithms": True, "tf32": False}
    raw_receipt.update(source=source, environment=environment)
    for role in ("writer", "reader"):
        path = demo / (role + "_receipt.json")
        value = json.loads(path.read_bytes())
        value.update(source=source, environment=environment)
        path.write_bytes(encoded(value))
    (demo / "trusted_compatibility.json").write_bytes(encoded({"source": source}))
    for role in ("reference", "candidate"):
        folder = native / role
        members = {"native.db": b"MOCK SQLITE PLACEHOLDER",
                   "native_traces.json": encoded([{}, {}, {}]), "composition_events.json": encoded([]),
                   "native_kernel_events.json": encoded([])}
        for name, raw in members.items():
            (folder / name).write_bytes(raw)
        output = raw_receipt["native_output"] + "/" + role
        result = {"status": "EXECUTED", "reference": role == "reference", "trace_valid": True,
                  "integrity": True, "fixed_weights": True, "runtime_identity": {"mock": True},
                  "runtime_identity_after": {"mock": True}, "native_trace_count": 3,
                  "gpu_forward_audit": {"calls": 3, "device": "cuda:0"}, "output_dir": output,
                  "native_database": output + "/native.db", "selected_action": fixed_task()["target"],
                  "evidence_sha256": {name: sha256(raw).hexdigest() for name, raw in members.items()}}
        (folder / "result.json").write_bytes(encoded(result))
        (demo / (role + "_result.json")).write_bytes(encoded(result))
        (demo / (role + "_verdict.json")).write_bytes(encoded({key: True for key in inspect_packet.legacy.VERDICT_FIELDS}))
    cloud = tmp_path / "cloud_job"
    runtime = {"cuda_matmul_passed": True, "gpu": environment["gpu_name"],
               "torch": environment["torch"], "cuda": environment["cuda_runtime"]}
    (cloud / "runtime.json").write_bytes(encoded(runtime))
    command = ["/opt/cas-meta3/venv/bin/python", "-m", "cas_meta3.native_demo",
               "--output", raw_receipt["output"], "--native-output", raw_receipt["native_output"],
               "--max-wall-seconds", "1200"]
    (cloud / "command.json").write_bytes(encoded(command))
    for family in ("contract", "policy"):
        prefix = cloud / ("gpu_" + family)
        Path(str(prefix) + "_receipt.json").write_bytes(encoded({"passed": 4, "tests": 4, "failures": 0, "errors": 0, "skipped": 0}))
        cases = "".join('<testcase name="' + name + '"/>' for name in sorted(inspect_packet.legacy.GPU_CASES[family]))
        Path(str(prefix) + "_tests.xml").write_text('<testsuites><testsuite tests="4" failures="0" errors="0" skipped="0">' + cases + '</testsuite></testsuites>')
        target = "tests/test_execution_contract.py" if family == "contract" else "tests/test_policy_gpu.py"
        Path(str(prefix) + "_command.json").write_bytes(encoded(["python", "-m", "pytest", "-m", "gpu", target]))
        Path(str(prefix) + "_tests.log").write_text("SYNTHETIC GPU REPORT; NO GPU RAN")
    wheels = [{"download_info": {"archive_info": {"hashes": {"sha256": value}}}}
              for value in ("c" * 64, "d" * 64)]
    (cloud / "frozen_wheel_install.json").write_bytes(encoded({"install": wheels}))
    (cloud / "torch_install.json").write_bytes(encoded({"fixture": True}))
    (cloud / "dependency_install.json").write_bytes(encoded({"fixture": True}))
    (cloud / "pip_freeze.txt").write_text("torch==2.11.0+cu128\n")
    mapping = {"research/CAS_META_3_PROCEDURAL_MEMORY/cas_meta3/" + name: value
               for name, value in source["demo_files_sha256"].items()}
    mapping.update({"research/" + name: value for name, value in source["native_files_sha256"].items()})
    mapping.update({"research/CAS_META_2_COMPOSITION/" + name: value for name, value in source["dependency"]["files"].items()})
    mapping["research/CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"] = source["protected_manifest_sha256"]
    mapping["research/" + source["native_schema_path"]] = source["native_schema_sha256"]
    mapping.update({"wheel1.whl": "c" * 64, "wheel2.whl": "d" * 64})
    manifest = {"schema": "cas-meta3-launch/1", "source_sha": source_sha, "baseline_sha": inspect_packet.BASELINE_SHA,
                "entrypoint": "cas_meta3.native_demo", "files_sha256": mapping,
                "protected_baseline_files": source["protected_files"], "wheel_paths": ["wheel1.whl", "wheel2.whl"]}
    if change:
        change(demo, native, cloud, raw_receipt, manifest)
    entries = []
    for kind, base in (("demo", demo), ("native", native)):
        for path in sorted(base.rglob("*")):
            if path.is_file() and not (base == demo and path.name in ("file_index.json", "memory_demo_receipt.json")):
                raw = path.read_bytes()
                entries.append({"root": kind, "path": path.relative_to(base).as_posix(),
                                "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    index = {"schema": "cas-meta3-file-index/0.1",
             "roots": {"demo": raw_receipt["output"], "native": raw_receipt["native_output"]},
             "entries": entries, "entries_sha256": sha256(encoded(entries).rstrip(b"\n")).hexdigest()}
    (demo / "file_index.json").write_bytes(encoded(index))
    raw_receipt["file_index_sha256"] = sha256(encoded(index)).hexdigest()
    (demo / "memory_demo_receipt.json").write_bytes(encoded(raw_receipt))
    job_record = {"job": job, "source_sha": source_sha, "baseline_sha": inspect_packet.BASELINE_SHA,
                  "archive_sha256": archive_sha, "returncode": 0, "entrypoint": "cas_meta3.native_demo",
                  "learning_performed": False, "qualification_status": "UNQUALIFIED"}
    (cloud / "job.json").write_bytes(encoded(job_record))
    roots.append(("cloud_job", cloud, True))
    stage = tmp_path / "stage"
    launch.collect_roots(roots, stage, 8 * 1024 * 1024)
    names = {path.relative_to(stage).as_posix() for path in stage.rglob("*") if path.is_file()}
    # Construct the sidecar binding directly so malformed fixtures reach the
    # independent inspector; never call the launcher's success gate to fix them.
    binding = {"status": "META3_COMPLETE_BYTE_INVENTORY_VERIFIED", "indexed_files": len(entries),
               "qualification_status": "UNQUALIFIED", "learning_performed": False,
               "memory_demo_receipt_sha256": sha256((demo / "memory_demo_receipt.json").read_bytes()).hexdigest(),
               "file_index_sha256": raw_receipt["file_index_sha256"], "demo_prefix": "cloud_job/demo/",
               "native_prefix": "meta2_native/meta3_" + job + "/", "job": job, "source_sha": source_sha,
               "boundary": "Recorded fresh reader and native reuse only; no suspended-call restart or skill qualification."}
    job_record["native_demo_binding"] = binding
    archive = tmp_path / "packet.zip"
    launch.build_evidence_bundle(stage, archive, 8 * 1024 * 1024, job_record, 8 * 1024 * 1024, partial)
    return archive, {"launch_manifest": manifest, "archive_sha256": archive_sha}, job


def inspect_fixture(archive, wrapper, job, fake_root):
    return inspect_packet.inspect_packet(archive, expected_sha256=sha256(archive.read_bytes()).hexdigest(),
        source_sha="b" * 40, job=job, source_manifest=wrapper,
        output=fake_root / "records/inspection", extract=fake_root / "records/full_extracted")


def test_full_synthetic_byte_packet_preserves_all_bytes_and_sidecars(tmp_path, isolated_inspector):
    archive, wrapper, job = full_fixture(tmp_path)
    receipt = inspect_fixture(archive, wrapper, job, isolated_inspector)
    assert receipt["status"] == "CAS_META_3_PACKET_FULL_EVIDENCE_VERIFIED"
    assert receipt["neural_execution_performed"] is False and receipt["provider_query_performed"] is False
    assert receipt["stored_semantic_reverification_performed"] is False
    inputs = receipt["semantic_audit_inputs"]
    assert inputs["source_sha"] == "b" * 40 and inputs["job"] == job
    demo, native = Path(inputs["demo_root"]), Path(inputs["native_root"])
    assert not demo.is_relative_to(native) and not native.is_relative_to(demo)
    assert sha256((demo / "memory_demo_receipt.json").read_bytes()).hexdigest() == inputs["demo_receipt_sha256"]
    with zipfile.ZipFile(archive) as packet:
        for name in packet.namelist():
            assert (Path(receipt["extraction"]["path"]) / name).read_bytes() == packet.read(name)


def test_partial_packet_never_supplies_completed_semantic_audit_inputs(tmp_path, isolated_inspector):
    archive, wrapper, job = full_fixture(tmp_path, partial=True)
    receipt = inspect_fixture(archive, wrapper, job, isolated_inspector)
    assert not receipt["completed_run_evidence_verified"]
    assert receipt["semantic_audit_inputs"] is None


@pytest.mark.parametrize("kind", ["gpu", "runtime", "command", "source", "native", "learning"])
def test_resealed_malformed_records_do_not_pass(tmp_path, isolated_inspector, kind):
    def change(demo, native, cloud, receipt, manifest):
        if kind == "gpu":
            (cloud / "gpu_policy_receipt.json").write_bytes(encoded({"passed": 3}))
        elif kind == "runtime":
            (cloud / "runtime.json").write_bytes(encoded({"cuda_matmul_passed": True, "gpu": "T4", "torch": "2.11.0+cu128", "cuda": "12.8"}))
        elif kind == "command":
            (cloud / "command.json").write_bytes(encoded(["python", "-m", "cas_meta2.campaign"]))
        elif kind == "source":
            receipt["source"] = {**receipt["source"], "demo_files_sha256": {}}
        elif kind == "native":
            (native / "candidate/native.db").write_bytes(b"Changed without changing native result hashes")
        else:
            receipt["learning_performed"] = True
    archive, wrapper, job = full_fixture(tmp_path, change)
    receipt = inspect_fixture(archive, wrapper, job, isolated_inspector)
    assert not receipt["completed_run_evidence_verified"] and receipt["issues"]
    assert receipt["semantic_audit_inputs"] is None


@pytest.mark.parametrize("name", ["../escape", "C:/escape", "folder\\bad", "CON.txt", "safe."])
def test_unsafe_zip_members_rejected_before_extraction(tmp_path, isolated_inspector, name):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(name, b"x")
    wrapper = {"launch_manifest": {}, "archive_sha256": "e" * 64}
    with pytest.raises(inspect_packet.PacketInvalid):
        inspect_fixture(archive, wrapper, "cas-meta3-fixture-only", isolated_inspector)
    assert not (isolated_inspector / "records/full_extracted").exists()


def test_duplicate_and_symbolic_zip_members_rejected(tmp_path, isolated_inspector):
    archive = tmp_path / "link.zip"
    entry = zipfile.ZipInfo("link")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(entry, "../elsewhere")
    with pytest.raises(inspect_packet.PacketInvalid, match="SYMLINK"):
        inspect_fixture(archive, {"launch_manifest": {}, "archive_sha256": "e" * 64},
                        "cas-meta3-fixture-only", isolated_inspector)


def test_expected_packet_hash_is_required_before_source_trust(tmp_path, isolated_inspector):
    archive = tmp_path / "x.zip"
    archive.write_bytes(b"not a zip")
    with pytest.raises(inspect_packet.PacketInvalid, match="PACKET_SHA256_MISMATCH"):
        inspect_packet.inspect_packet(archive, expected_sha256="0" * 64, source_sha="b" * 40,
            job="cas-meta3-fixture-only", source_manifest={"archive_sha256": "e" * 64},
            output=isolated_inspector / "records/check", extract=isolated_inspector / "records/full_extracted")


def test_output_must_be_new_under_meta3_records_and_disjoint(tmp_path, isolated_inspector):
    with pytest.raises(inspect_packet.PacketInvalid, match="OUTPUT_OUTSIDE_META3"):
        inspect_packet._new_output(tmp_path / "outside")
    existing = isolated_inspector / "records/existing"
    existing.mkdir(parents=True)
    with pytest.raises(inspect_packet.PacketInvalid, match="OUTPUT_MUST_BE_NEW"):
        inspect_packet._new_output(existing)


def test_frozen_archive_helper_digest_and_objects_are_unchanged():
    assert sha256(inspect_packet.LEGACY_PATH.read_bytes()).hexdigest() == inspect_packet.LEGACY_SHA256
    assert inspect_packet.Packet is inspect_packet.legacy.Packet
    assert inspect_packet.safe_name is inspect_packet.legacy.safe_name
    assert "_safe_infos(archive)" in Path(inspect_packet.__file__).read_text()
    assert "legacy._extract(packet, target)" in Path(inspect_packet.__file__).read_text()


@pytest.mark.parametrize("second", ["same", "SAME"])
def test_duplicate_or_case_alias_zip_is_rejected(tmp_path, isolated_inspector, second):
    archive = tmp_path / "aliases.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("same", b"first")
        output.writestr(second, b"second")
    with pytest.raises(inspect_packet.PacketInvalid, match="DUPLICATE_OR_CASE_COLLIDING"):
        inspect_fixture(archive, {"launch_manifest": {}, "archive_sha256": "e" * 64},
                        "cas-meta3-fixture-only", isolated_inspector)


def test_wrong_sidecar_hash_cannot_reach_semantic_audit(tmp_path, isolated_inspector):
    archive, wrapper, job = full_fixture(tmp_path)
    changed = tmp_path / "changed-sidecar.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(changed, "w", zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            raw = source.read(name)
            if name == "artifact_collection_receipt.json":
                record = json.loads(raw)
                record["native_demo_binding"]["file_index_sha256"] = "0" * 64
                raw = encoded(record)
            target.writestr(name, raw)
    receipt = inspect_fixture(changed, wrapper, job, isolated_inspector)
    assert not receipt["completed_run_evidence_verified"]
    assert any("TRUSTED_DEMO_SIDECAR_BINDING" in issue for issue in receipt["issues"])
    assert receipt["semantic_audit_inputs"] is None


def mock_git_authority(monkeypatch, *, changed=None):
    repo = ROOT.parent.parent
    def git_run(command, **kwargs):
        assert command[0] == "git" and kwargs["check"] and kwargs["timeout"] == 60
        if command[1:] == ["rev-parse", "--show-toplevel"]:
            return SimpleNamespace(stdout=str(repo))
        assert command[1] == "show" and command[2].startswith("b" * 40 + ":")
        path = repo / command[2].split(":", 1)[1]
        raw = path.read_bytes()
        if changed is not None and path.resolve() == changed.resolve():
            raw += b"\nDIFFERENT_COMMITTED_BYTES\n"
        return SimpleNamespace(stdout=raw)
    monkeypatch.setattr(inspect_packet.subprocess, "run", git_run)


def test_real_source_gate_rejects_unbound_local_code_before_import(monkeypatch):
    manifest = {"schema": "cas-meta3-launch/1", "source_sha": "b" * 40,
                "baseline_sha": inspect_packet.BASELINE_SHA, "entrypoint": "cas_meta3.native_demo",
                "files_sha256": {}}
    def forbid_import(*args, **kwargs):
        raise AssertionError("UNVERIFIED_LAUNCH_CODE_IMPORTED")
    mock_git_authority(monkeypatch)
    monkeypatch.setattr(inspect_packet.importlib.util, "spec_from_file_location", forbid_import)
    with pytest.raises(inspect_packet.PacketInvalid, match="LOCAL_INSPECTION_SOURCE_DOES_NOT_MATCH"):
        inspect_packet._trusted_launcher(manifest, "b" * 40)


@pytest.mark.parametrize("package,relative", [
    ("meta3", "aws/launch.py"), ("meta3", "aws/frozen_helpers.py"),
    ("meta3", "tools/build_launch_bundle.py"), ("meta3", "tools/inspect_cloud_packet.py"),
    ("meta2", "aws/launch.py"), ("meta2", "aws/budget.py"),
    ("meta2", "tools/experiment_profiles.py"),
])
def test_manifest_matching_local_code_cannot_override_git_before_import(monkeypatch, package, relative):
    paths = [ROOT / value for value in ("aws/launch.py", "aws/frozen_helpers.py",
             "tools/build_launch_bundle.py", "tools/inspect_cloud_packet.py")]
    paths += [inspect_packet.META2 / value for value in
              ("aws/launch.py", "aws/budget.py", "tools/experiment_profiles.py")]
    # Every manifest digest agrees with the current bytes, but one committed
    # dependency differs. No dynamic import may occur before that rejection.
    manifest = {"schema": "cas-meta3-launch/1", "source_sha": "b" * 40,
                "baseline_sha": inspect_packet.BASELINE_SHA, "entrypoint": "cas_meta3.native_demo",
                "files_sha256": {path.relative_to(ROOT.parent.parent).as_posix():
                                  sha256(path.read_bytes()).hexdigest() for path in paths}}
    changed = (ROOT if package == "meta3" else inspect_packet.META2) / relative
    mock_git_authority(monkeypatch, changed=changed)
    def forbid_import(*args, **kwargs):
        raise AssertionError("UNVERIFIED_LAUNCH_CODE_IMPORTED")
    monkeypatch.setattr(inspect_packet.importlib.util, "spec_from_file_location", forbid_import)
    with pytest.raises(inspect_packet.PacketInvalid, match="LOCAL_INSPECTION_SOURCE_DIFFERS_FROM_GIT"):
        inspect_packet._trusted_launcher(manifest, "b" * 40)
