"""Second-slice package tests use fake checkpoint bytes only."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import stat
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import pytest

from cas_meta2.teaching_cycle import continuation_package_v2 as package
from tools import inspect_teaching_continuation_v2 as inspector

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("second_slice_synthetic_fixture",
    ROOT / "tests/test_teaching_continuation_inspection_v2.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    seed = fixture.seed.__wrapped__(tmp_path_factory)
    args, frozen = fixture.publish(seed)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(inspector, "FROZEN_EVIDENCE", frozen)
        report = inspector.inspect_continuation(**args)
        report_path = seed["root"] / "inspection_v2.json"
        report_path.write_bytes(package.canonical(report))
        arguments = {**args, "inspection_report": report_path,
                     "inspection_sha256": sha256(report_path.read_bytes()).hexdigest()}
        output = seed["root"] / "package"
        receipt = package.build_package(**arguments, output_dir=output)
    return {"args": arguments, "frozen": frozen, "root": output, "receipt": receipt,
            "manifest": json.loads((output / "manifest.json").read_bytes())}


def validate(prepared, **overrides):
    values = {"archive": prepared["root"] / "prior_state.zip",
        "manifest": prepared["root"] / "manifest.json",
        "archive_sha256": prepared["receipt"]["archive"]["sha256"],
        "manifest_sha256": prepared["receipt"]["manifest"]["sha256"]}
    return package.validate_package(**{**values, **overrides})


def reseal(prepared, tmp_path, *, payload_change=None, manifest_change=None, duplicate=None, link=None):
    doc = deepcopy(prepared["manifest"])
    with ZipFile(prepared["root"] / "prior_state.zip") as source:
        payloads = {name: source.read(name) for name in doc["members"]}
    if payload_change:
        payload_change(payloads)
    doc["members"] = {n: {"bytes": len(b), "sha256": sha256(b).hexdigest()} for n, b in payloads.items()}
    doc["expanded_bytes"] = sum(v["bytes"] for v in doc["members"].values())
    if package.SUMMARY_PATH in payloads:
        doc["summary_sha256"] = sha256(payloads[package.SUMMARY_PATH]).hexdigest()
    if package.RETAINED_SUMMARY_PATH in payloads:
        doc["retained_summary_sha256"] = sha256(payloads[package.RETAINED_SUMMARY_PATH]).hexdigest()
    if manifest_change:
        manifest_change(doc)
    raw = package.canonical(doc)
    manifest, archive = tmp_path / "manifest.json", tmp_path / "prior.zip"
    manifest.write_bytes(raw)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as target:
        target.writestr("manifest.json", raw)
        for name, content in payloads.items():
            if name == link:
                info = ZipInfo(name)
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                target.writestr(info, content)
            else:
                target.writestr(name, content)
        if duplicate:
            target.writestr(duplicate, payloads[duplicate])
    return {"archive": archive, "manifest": manifest,
        "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "manifest_sha256": sha256(raw).hexdigest()}


def test_both_summaries_and_whole_history_preserved(prepared):
    result = validate(prepared)
    assert result["schema"] == "cas-teaching-prior-state/2"
    assert result["summary_path"] == package.SUMMARY_PATH
    assert result["retained_summary_path"] == package.RETAINED_SUMMARY_PATH
    assert prepared["receipt"]["schema"] == "cas-teaching-prior-state-build/2"
    assert prepared["receipt"]["private_targets_opened"] is prepared["receipt"]["launch_authorized"] is False
    with ZipFile(prepared["args"]["archive"]) as old, ZipFile(prepared["root"] / "prior_state.zip") as new:
        for name in result["members"]:
            assert old.read(name) == new.read(name)
    assert all(a["committed_optimizer_steps"] == 2 for a in result["arms"].values())


def test_repeat_build_is_deterministic(prepared, tmp_path, monkeypatch):
    monkeypatch.setattr(inspector, "FROZEN_EVIDENCE", prepared["frozen"])
    receipt = package.build_package(**prepared["args"], output_dir=tmp_path / "again")
    assert receipt["archive"]["sha256"] == prepared["receipt"]["archive"]["sha256"]
    assert receipt["manifest"]["sha256"] == prepared["receipt"]["manifest"]["sha256"]


@pytest.mark.parametrize("pin", ["parent_sha256", "complete_sha256", "inspection_sha256", "evaluation_sha256"])
def test_builder_rejects_changed_input_before_output(prepared, tmp_path, pin):
    with pytest.raises(package.PackageError, match="JSON_PIN_MISMATCH"):
        package.build_package(**{**prepared["args"], pin: "f" * 64}, output_dir=tmp_path / "not_created")
    assert not (tmp_path / "not_created").exists()


def test_builder_rejects_fresh_output_reuse(prepared):
    with pytest.raises(package.PackageError, match="EXCLUSIVE_FRESH_OUTPUT"):
        package.build_package(**prepared["args"], output_dir=prepared["root"])


@pytest.mark.parametrize("name", [package.SUMMARY_PATH, package.RETAINED_SUMMARY_PATH,
    "train/campaign/cas.aligned/events/step-00000001.intent.json",
    "train/campaign/cas.aligned/events/step-00000002.result.json",
    "train/campaign/cas.aligned/journal/txn-00000001/metadata.json"])
def test_history_or_summary_omission_rejected(prepared, tmp_path, name):
    with pytest.raises(package.PackageError):
        package.validate_package(**reseal(prepared, tmp_path, payload_change=lambda p: p.pop(name)))


@pytest.mark.parametrize("name", ["train_continued_001/worker_identity.json",
                                  "train_continued_002/campaign_summary.json",
                                  "evaluation_private/answers.json"])
def test_unrelated_roots_and_files_rejected(prepared, tmp_path, name):
    with pytest.raises(package.PackageError, match="MEMBER_PATH"):
        package.validate_package(**reseal(prepared, tmp_path,
            payload_change=lambda p: p.update({name: b"{}"})))


def test_summary_paths_cannot_be_swapped(prepared, tmp_path):
    with pytest.raises(package.PackageError, match="ORIGINAL_PATH_MISMATCH"):
        package.validate_package(**reseal(prepared, tmp_path,
            manifest_change=lambda d: d.update(summary_path=package.RETAINED_SUMMARY_PATH)))


def test_latest_summary_must_bind_retained_summary(prepared, tmp_path):
    def changed(payloads):
        summary = package.decode(payloads[package.SUMMARY_PATH])
        summary["resumed_summary_sha256"] = "f" * 64
        payloads[package.SUMMARY_PATH] = package.canonical(summary)
    with pytest.raises(package.PackageError, match="CAMPAIGN_IDENTITY_MISMATCH"):
        package.validate_package(**reseal(prepared, tmp_path, payload_change=changed))


def test_older_summary_cannot_replace_latest(prepared, tmp_path):
    with pytest.raises(package.PackageError):
        package.validate_package(**reseal(prepared, tmp_path,
            payload_change=lambda p: p.update({package.SUMMARY_PATH: p[package.RETAINED_SUMMARY_PATH]})))


@pytest.mark.parametrize("field,value", [("original_campaign_root", "/tmp/new"),
    ("profile", {"version": 2}), ("expanded_bytes", 1), ("boundary", "learning proved"),
    ("retained_summary_sha256", "f" * 64)])
def test_manifest_constraints_resealed(prepared, tmp_path, field, value):
    with pytest.raises(package.PackageError):
        package.validate_package(**reseal(prepared, tmp_path,
            manifest_change=lambda d: d.update({field: value})))


@pytest.mark.parametrize("pin", ["archive_sha256", "manifest_sha256"])
def test_external_package_pins_required(prepared, pin):
    with pytest.raises(package.PackageError):
        validate(prepared, **{pin: "f" * 64})


def test_external_retained_and_latest_bindings_supported(prepared):
    result = validate(prepared, expected_bindings={
        "summary_path": package.SUMMARY_PATH,
        "summary_sha256": prepared["manifest"]["summary_sha256"],
        "retained_summary_path": package.RETAINED_SUMMARY_PATH,
        "retained_summary_sha256": prepared["manifest"]["retained_summary_sha256"]})
    assert result == prepared["manifest"]
    with pytest.raises(package.PackageError, match="EXTERNAL_BINDING_MISMATCH"):
        validate(prepared, expected_bindings={"retained_summary_sha256": "f" * 64})


def test_duplicate_and_link_members(prepared, tmp_path):
    d = tmp_path / "duplicate"
    d.mkdir()
    with pytest.warns(UserWarning):
        args = reseal(prepared, d, duplicate=package.SUMMARY_PATH)
    with pytest.raises(package.PackageError, match="ZIP_MEMBER_COUNT"):
        package.validate_package(**args)
    link = tmp_path / "link"
    link.mkdir()
    with pytest.raises(package.PackageError, match="ZIP_FILE_TYPE"):
        package.validate_package(**reseal(prepared, link, link=package.RETAINED_SUMMARY_PATH))


def test_private_loaded_validator_imports_stdlib_only(prepared, monkeypatch):
    spec = importlib.util.spec_from_file_location("_second_slice_prior_validator", package.__file__)
    module = importlib.util.module_from_spec(spec)
    original = __import__
    def guarded(name, *args, **kwargs):
        assert not name.startswith(("cas_meta2", "tools", "torch", "numpy", "boto", "sqlite"))
        return original(name, *args, **kwargs)
    monkeypatch.setattr("builtins.__import__", guarded)
    spec.loader.exec_module(module)
    result = module.validate_package(prepared["root"] / "prior_state.zip", prepared["root"] / "manifest.json",
        archive_sha256=prepared["receipt"]["archive"]["sha256"],
        manifest_sha256=prepared["receipt"]["manifest"]["sha256"])
    assert result["summary_path"] == package.SUMMARY_PATH
    assert not {"torch", "numpy", "sqlite3", "boto3"}.intersection(sys.modules)
