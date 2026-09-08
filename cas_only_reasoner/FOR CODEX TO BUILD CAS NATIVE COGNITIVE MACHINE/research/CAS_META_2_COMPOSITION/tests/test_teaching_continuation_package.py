"""Synthetic byte checkpoints only; no tensors, cloud calls or real final data."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import pytest

from cas_meta2.teaching_cycle import continuation_package as package

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("synthetic_prior_fixture",
    ROOT / "tests/test_teaching_cycle_continuation_inspection.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    packet = fixture.original.__wrapped__(tmp_path_factory)
    # Adjust this synthetic fixture, never the actual collected job's summary.
    summary_path = packet["root"] / "extracted/train/campaign_summary.json"
    summary_path.write_bytes(summary_path.read_bytes().replace(
        b"/srv/original-teaching/train/campaign", package.ORIGINAL_ROOT.encode()))
    _, _, bundle = fixture.worker_contract.archive_payloads(packet["root"] / "extracted/input/source.zip",
        packet["bindings"]["archive_sha256"], packet["bindings"]["manifest_sha256"])
    for key in ("training_cases_sha256", "development_cases_sha256"):
        packet["bindings"][key] = bundle["manifest"][key]
    args = fixture.publish(packet)
    inspected = fixture.tool.inspect_continuation(**args)
    report = packet["root"] / "inspection.json"
    report.write_bytes(package.canonical(inspected))
    return {**args, "inspection_report": report, "inspection_sha256": sha256(report.read_bytes()).hexdigest()}


@pytest.fixture(scope="module")
def built(originals, tmp_path_factory):
    destination = tmp_path_factory.mktemp("prior_state_capture") / "package"
    before = fixture.identities(originals["extracted_root"])
    receipt = package.build_package(**originals, output_dir=destination)
    assert before == fixture.identities(originals["extracted_root"])
    return {"receipt": receipt, "root": destination,
        "manifest": json.loads((destination / "manifest.json").read_bytes())}


def validate(built, **overrides):
    args = {"archive": built["root"] / "prior_state.zip", "manifest": built["root"] / "manifest.json",
        "archive_sha256": built["receipt"]["archive"]["sha256"],
        "manifest_sha256": built["receipt"]["manifest"]["sha256"],
        "expected_bindings": {"logical_run_id": built["manifest"]["logical_run_id"],
            **{key: built["manifest"][key] for key in package.PIN_FIELDS}}}
    args.update(overrides)
    return package.validate_package(**args)


def reseal(tmp_path, built, *, change_manifest=None, change_payloads=None, duplicate=None, symlink=None):
    document = deepcopy(built["manifest"])
    with ZipFile(built["root"] / "prior_state.zip") as original:
        payloads = {name: original.read(name) for name in document["members"]}
    if change_payloads:
        change_payloads(payloads)
    document["members"] = {name: {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
                           for name, raw in payloads.items()}
    document["expanded_bytes"] = sum(len(raw) for raw in payloads.values())
    document["summary_sha256"] = sha256(payloads[package.SUMMARY_PATH]).hexdigest()
    if change_manifest:
        change_manifest(document)
    raw = package.canonical(document)
    manifest, archive = tmp_path / "manifest.json", tmp_path / "prior.zip"
    manifest.write_bytes(raw)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as target:
        target.writestr("manifest.json", raw)
        for name, payload in payloads.items():
            if name == symlink:
                info = ZipInfo(name)
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                target.writestr(info, payload)
            else:
                target.writestr(name, payload)
        if duplicate:
            target.writestr(duplicate, payloads[duplicate])
    return {"archive": archive, "manifest": manifest, "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "manifest_sha256": sha256(raw).hexdigest()}


def test_exact_prior_bytes_and_no_neural_claim(originals, built):
    result = validate(built)
    assert result == built["manifest"]
    assert result["original_campaign_root"] == package.ORIGINAL_ROOT
    assert result["profile"] == package.PROFILE
    assert set(result["arms"]) == set(package.ARMS)
    with ZipFile(originals["archive"]) as prior, ZipFile(built["root"] / "prior_state.zip") as current:
        expected = {name for name in prior.namelist()
                    if name == package.SUMMARY_PATH or name.startswith("train/campaign/")}
        assert set(result["members"]) == expected
        for name in expected:
            assert current.read(name) == prior.read(name)
    assert built["receipt"]["actual_gpu_restore"] == "UNEXECUTED"
    assert built["receipt"]["private_targets_opened"] is False
    assert built["receipt"]["launch_authorized"] is False


def test_builder_repeat_is_deterministic(originals, built, tmp_path):
    other = package.build_package(**originals, output_dir=tmp_path / "again")
    assert other["archive"]["sha256"] == built["receipt"]["archive"]["sha256"]
    assert other["manifest"]["sha256"] == built["receipt"]["manifest"]["sha256"]


def test_fresh_output_required(originals, built):
    with pytest.raises(package.PackageError, match="EXCLUSIVE_FRESH_OUTPUT"):
        package.build_package(**originals, output_dir=built["root"])


@pytest.mark.parametrize("field", ["parent_sha256", "complete_sha256", "inspection_sha256"])
def test_builder_external_pins_required(originals, tmp_path, field):
    args = {**originals, field: "f" * 64}
    with pytest.raises(package.PackageError, match="JSON_PIN_MISMATCH"):
        package.build_package(**args, output_dir=tmp_path / "not_written")
    assert not (tmp_path / "not_written").exists()


def test_builder_rechecks_saved_inspection_semantics(originals, tmp_path):
    report = json.loads(Path(originals["inspection_report"]).read_bytes())
    report["arms"]["cas.aligned"]["committed_optimizer_steps"] += 1
    path = tmp_path / "changed_inspection.json"
    path.write_bytes(package.canonical(report))
    with pytest.raises(package.PackageError, match="INSPECTION_SEMANTICS_CHANGED"):
        package.build_package(**{**originals, "inspection_report": path,
            "inspection_sha256": sha256(path.read_bytes()).hexdigest()}, output_dir=tmp_path / "not_written")


def test_builder_checks_current_frozen_source(originals, tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    for name in fixture.worker_contract.WORKER_FILES:
        target = source_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    (source_root / "cas_meta2/policy.py").write_bytes(b"changed\n")
    monkeypatch.setattr(package, "ROOT", source_root)
    with pytest.raises(package.PackageError, match="CURRENT_WORKER_SOURCE_CHANGED:cas_meta2/policy.py"):
        package.build_package(**originals, output_dir=tmp_path / "not_written")


@pytest.mark.parametrize("field", ["archive_sha256", "manifest_sha256"])
def test_package_external_pins_required(built, field):
    with pytest.raises(package.PackageError, match="PIN_MISMATCH"):
        validate(built, **{field: "f" * 64})


def test_launch_bindings_not_substituted(built):
    with pytest.raises(package.PackageError, match="EXTERNAL_BINDING_MISMATCH"):
        validate(built, expected_bindings={"logical_run_id": "new-cloud-job-is-not-logical-run"})


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'])
def test_strict_json(raw):
    with pytest.raises(package.PackageError):
        package.decode(raw)


@pytest.mark.parametrize("field,value", [("original_campaign_root", "/tmp/campaign"),
    ("profile", {"version": 2}), ("expanded_bytes", 1), ("boundary", "GPU restore passed")])
def test_resealed_manifest_changes_rejected(built, tmp_path, field, value):
    args = reseal(tmp_path, built, change_manifest=lambda doc: doc.update({field: value}))
    with pytest.raises(package.PackageError):
        package.validate_package(**args)


def test_summary_identity_cannot_be_rewritten(built, tmp_path):
    def mutate(payloads):
        summary = package.decode(payloads[package.SUMMARY_PATH])
        summary["run_id"] = "changed"
        payloads[package.SUMMARY_PATH] = package.canonical(summary)
    with pytest.raises(package.PackageError, match="CAMPAIGN_IDENTITY_MISMATCH"):
        package.validate_package(**reseal(tmp_path, built, change_payloads=mutate))


def test_no_final_targets_or_extra_paths(built, tmp_path):
    args = reseal(tmp_path, built, change_payloads=lambda rows: rows.update({"evaluator_private/test.json": b"{}"}))
    with pytest.raises(package.PackageError, match="MEMBER_PATH"):
        package.validate_package(**args)


def test_complete_history_cannot_be_trimmed(built, tmp_path):
    name = "train/campaign/cas.aligned/events/step-00000001.intent.json"
    args = reseal(tmp_path, built, change_payloads=lambda rows: rows.pop(name))
    with pytest.raises(package.PackageError, match="COMPLETE_COMMITTED_INVENTORY"):
        package.validate_package(**args)


def test_duplicate_and_symlink_zip_members_rejected(built, tmp_path):
    first = tmp_path / "duplicate"
    first.mkdir()
    with pytest.warns(UserWarning, match="Duplicate name"):
        args = reseal(first, built, duplicate=package.SUMMARY_PATH)
    with pytest.raises(package.PackageError, match="ZIP_MEMBER_COUNT"):
        package.validate_package(**args)
    second = tmp_path / "symlink"
    second.mkdir()
    args = reseal(second, built, symlink=package.SUMMARY_PATH)
    with pytest.raises(package.PackageError, match="ZIP_FILE_TYPE"):
        package.validate_package(**args)


def test_changed_checkpoint_bytes_rejected(built, tmp_path):
    path = tmp_path / "archive.zip"
    shutil.copyfile(built["root"] / "prior_state.zip", path)
    with path.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(package.PackageError, match="PACKAGE_ARCHIVE_PIN_MISMATCH"):
        validate(built, archive=path)


def test_hardlinked_input_file_rejected(tmp_path):
    source, linked = tmp_path / "source.json", tmp_path / "linked.json"
    source.write_bytes(b"{}")
    os.link(source, linked)
    with pytest.raises(package.PackageError, match="REGULAR_SINGLE_LINK"):
        package.file_identity(source)


def test_input_file_size_bound_enforced(tmp_path):
    source = tmp_path / "bounded.json"
    source.write_bytes(b"1234")
    with pytest.raises(package.PackageError, match="BOUNDED_FILE_REQUIRED"):
        package.file_identity(source, limit=3)


def test_parent_component_rejected_before_read(tmp_path):
    with pytest.raises(package.PackageError, match="PARENT_PATH_REJECTED"):
        package.file_identity(tmp_path / ".." / "outside.json")


def test_duplicate_key_in_stored_event_rejected_even_after_reseal(built, tmp_path):
    name = "train/campaign/cas.aligned/events/step-00000001.intent.json"
    args = reseal(tmp_path, built, change_payloads=lambda rows: rows.update({name: b'{"x":1,"x":2}'}))
    with pytest.raises(package.PackageError, match="DUPLICATE_JSON_KEY"):
        package.validate_package(**args)


def test_private_import_validator_needs_no_repo_or_model_imports(built, monkeypatch):
    spec = importlib.util.spec_from_file_location("_prior_support_validator", Path(package.__file__))
    isolated = importlib.util.module_from_spec(spec)
    original_import = __import__
    def guarded(name, *args, **kwargs):
        assert not name.startswith(("cas_meta2", "tools", "torch", "numpy", "sqlite", "boto"))
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr("builtins.__import__", guarded)
    spec.loader.exec_module(isolated)
    result = isolated.validate_package(built["root"] / "prior_state.zip", built["root"] / "manifest.json",
        archive_sha256=built["receipt"]["archive"]["sha256"], manifest_sha256=built["receipt"]["manifest"]["sha256"])
    assert result["logical_run_id"] == built["manifest"]["logical_run_id"]
    assert not {"torch", "numpy", "sqlite3", "boto3"}.intersection(sys.modules)
