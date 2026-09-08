"""Pure byte/Git fixtures. No wheel install, model import or provider work."""
import ast
from copy import deepcopy
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from zipfile import ZipFile, ZipInfo

import pytest

from cas_meta2.teaching_cycle import package
from cas_meta2.teaching_cycle import worker_contract as contract

SOURCE = "a" * 40


@pytest.fixture(scope="module")
def frozen_wheel():
    commit = package._git(["rev-parse", "HEAD"]).decode().strip()
    path = str(PurePosixPath(package._prefix()).parent / package.WHEEL_SOURCE)
    raw = package._git_blob(commit, path)
    assert contract.digest(raw) == contract.WHEEL_SHA256
    return raw


@pytest.fixture
def fixture_inputs(tmp_path, monkeypatch, frozen_wheel):
    prefix = package._prefix()
    blobs = {prefix + name: ("# Synthetic committed-code fixture: " + name + "\n").encode()
             for name in contract.WORKER_FILES}
    for name in contract.CASE_FILES:
        blobs[prefix + package.MATERIAL + name] = (package.ROOT / package.MATERIAL / name).read_bytes()
    wheel_path = str(PurePosixPath(prefix).parent / package.WHEEL_SOURCE)
    blobs[wheel_path] = frozen_wheel
    seen = []
    def read(commit, name):
        assert commit == SOURCE
        seen.append(name)
        return blobs[name]
    monkeypatch.setattr(package, "RECORDS", tmp_path)
    return {"blobs": blobs, "reader": read, "seen": seen, "output": tmp_path / "package"}


@pytest.fixture
def built(tmp_path, fixture_inputs):
    receipt = package.build_bundle(SOURCE, fixture_inputs["output"], _read_blob=fixture_inputs["reader"])
    root = tmp_path / "worker"
    result = contract.extract_bundle(receipt["archive"], root, receipt["archive_sha256"], receipt["manifest_sha256"])
    return receipt, root, result


def reseal(root, update=None):
    path = root / contract.MANIFEST_NAME
    manifest = json.loads(path.read_bytes())
    if update:
        update(manifest)
    raw = contract.canonical(manifest) + b"\n"
    path.write_bytes(raw)
    return contract.digest(raw)


def refresh_entry(root, manifest, name):
    raw = (root / name).read_bytes()
    manifest["files"][name] = {"sha256": contract.digest(raw), "bytes": len(raw)}


def test_curated_bundle_contains_only_worker_and_teaching_inputs(fixture_inputs, built):
    receipt, root, result = built
    assert receipt["member_count"] == 17 and receipt["provider_calls"] == 0
    assert receipt["source_reader"] == "synthetic_injected_blob_reader"
    assert receipt["counts"] == {"training": 256, "development": 64}
    assert receipt["reservation_created"] is False
    with ZipFile(receipt["archive"]) as zipped:
        assert set(zipped.namelist()) == contract.ALL_FILES
        assert zipped.read(contract.WHEEL_NAME) == fixture_inputs["blobs"][next(
            name for name in fixture_inputs["blobs"] if name.endswith(".whl"))]
    assert all(not any(part in name for part in ("data.py", "package.py", "final", "heldout", "private"))
               for name in contract.ALL_FILES)
    assert set(fixture_inputs["seen"]) == set(fixture_inputs["blobs"])
    manifest = result["manifest"]
    assert manifest["source_sha256"] == contract.canonical_sha256({name: contract.digest((root / name).read_bytes())
                                                                  for name in contract.WORKER_FILES})
    assert manifest["training_cases_sha256"] == contract.canonical_sha256(sorted(
        result["training_cases"], key=lambda case: case["family_id"]))
    assert manifest["development_cases_sha256"] == contract.canonical_sha256(result["development_cases"])
    assert not {"torch", "numpy", "casformer", "cas_cjt", "boto3", "sqlite3"}.intersection(sys.modules)


@pytest.mark.parametrize("name", ["cas_meta2/teaching_cycle/data.py", "final.public.json", "final.targets.json", "unexpected.txt"])
def test_extra_file_never_reaches_lesson_validation(built, monkeypatch, name):
    receipt, root, _ = built
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"must not load")
    monkeypatch.setattr(contract, "validate_payloads", lambda *args: pytest.fail("extra file reached semantic validation"))
    with pytest.raises(contract.BundleError, match="UNEXPECTED_FILE"):
        contract.load_bundle(root, receipt["manifest_sha256"])


def test_extra_empty_directory_is_rejected(built):
    receipt, root, _ = built
    (root / "teacher").mkdir()
    with pytest.raises(contract.BundleError, match="UNEXPECTED_DIRECTORY"):
        contract.load_bundle(root, receipt["manifest_sha256"])


def test_missing_worker_file_is_rejected(built):
    receipt, root, _ = built
    (root / "cas_meta2/policy.py").unlink()
    with pytest.raises(contract.BundleError, match="BUNDLE_INVENTORY"):
        contract.load_bundle(root, receipt["manifest_sha256"])


def test_wrong_external_manifest_pin_is_rejected(built):
    _, root, _ = built
    with pytest.raises(contract.BundleError, match="MANIFEST_PIN_MISMATCH"):
        contract.load_bundle(root, "0" * 64)


def test_changed_code_is_rejected_before_lesson_import(built):
    receipt, root, _ = built
    (root / "cas_meta2/policy.py").write_bytes(b"import forbidden_model\n")
    with pytest.raises(contract.BundleError, match="FILE_IDENTITY"):
        contract.load_bundle(root, receipt["manifest_sha256"])


def test_resealed_replacement_wheel_still_fails_frozen_pin(built):
    _, root, _ = built
    (root / contract.WHEEL_NAME).write_bytes(b"not the accepted wheel")
    pin = reseal(root, lambda manifest: refresh_entry(root, manifest, contract.WHEEL_NAME))
    with pytest.raises(contract.BundleError, match="FROZEN_WHEEL_CHANGED"):
        contract.load_bundle(root, pin)


def test_development_order_is_part_of_its_pin(built):
    _, root, result = built
    development = list(reversed(result["development_cases"]))
    (root / "development.json").write_bytes(contract.canonical(development))
    pin = reseal(root, lambda manifest: refresh_entry(root, manifest, "development.json"))
    with pytest.raises(contract.BundleError, match="DEVELOPMENT_CASES_PIN_MISMATCH"):
        contract.load_bundle(root, pin)


def test_training_pin_uses_family_sort_not_file_order(built):
    _, root, result = built
    training = list(reversed(result["training_cases"]))
    (root / "train.json").write_bytes(contract.canonical(training))
    pin = reseal(root, lambda manifest: refresh_entry(root, manifest, "train.json"))
    loaded = contract.load_bundle(root, pin)
    assert loaded["manifest"]["training_cases_sha256"] == result["manifest"]["training_cases_sha256"]


@pytest.mark.parametrize("change", [lambda m: m["profile"].update(seed=8),
    lambda m: m["profile"]["allocation"].update(maximum_cycles=4096.0),
    lambda m: m.update(source_sha256="0" * 64)])
def test_resealed_profile_or_source_mapping_drift_is_rejected(built, change):
    _, root, _ = built
    pin = reseal(root, change)
    with pytest.raises(contract.BundleError):
        contract.load_bundle(root, pin)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{"x":Infinity}'])
def test_ambiguous_or_nonfinite_json_is_rejected(raw):
    with pytest.raises(contract.BundleError):
        contract.decode_json(raw)


def test_hardlink_is_rejected(built, tmp_path):
    receipt, root, _ = built
    os.link(root / "train.json", tmp_path / "alias.json")
    with pytest.raises(contract.BundleError, match="HARDLINK"):
        contract.load_bundle(root, receipt["manifest_sha256"])


def test_linked_bundle_directory_is_rejected(built, tmp_path):
    receipt, root, _ = built
    linked = tmp_path / "alias"
    try:
        linked.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("Host does not permit creating directory symlinks")
    with pytest.raises(contract.BundleError, match="LINKED_PATH"):
        contract.load_bundle(linked, receipt["manifest_sha256"])


@pytest.mark.parametrize("mode", ["traversal", "duplicate", "symlink", "extra"])
def test_resealed_unsafe_zip_is_rejected_before_extraction(built, tmp_path, mode):
    receipt, _, _ = built
    with ZipFile(receipt["archive"]) as source:
        entries = [(info.filename, source.read(info)) for info in source.infolist()]
    if mode == "traversal":
        entries[0] = ("../escape.py", entries[0][1])
    elif mode == "duplicate":
        entries[0] = (entries[1][0], entries[0][1])
    elif mode == "extra":
        entries.append(("teacher.py", b"not allowed"))
    raw = io.BytesIO()
    with ZipFile(raw, "w") as output:
        for index, (name, body) in enumerate(entries):
            info = ZipInfo(name)
            info.create_system = 3
            info.external_attr = ((stat.S_IFLNK | 0o777) if mode == "symlink" and index == 0 else 0o100644) << 16
            output.writestr(info, body)
    path = tmp_path / "unsafe.zip"
    path.write_bytes(raw.getvalue())
    destination = tmp_path / "must-stay-absent"
    with pytest.raises(contract.BundleError):
        contract.extract_bundle(path, destination, contract.digest(raw.getvalue()), receipt["manifest_sha256"])
    assert not destination.exists()


def test_archive_size_bound_precedes_zip_parsing(tmp_path):
    path = tmp_path / "oversized.zip"
    with path.open("wb") as stream:
        stream.truncate(contract.ARCHIVE_BYTES_MAX + 1)
    with pytest.raises(contract.BundleError, match="FILE_BYTES_BOUND"):
        contract.archive_payloads(path, "0" * 64, "0" * 64)


def test_bundle_build_and_extraction_never_overwrite(fixture_inputs, built):
    receipt, root, _ = built
    with pytest.raises(contract.BundleError, match="FRESH_TEACHING_OUTPUT_REQUIRED"):
        package.build_bundle(SOURCE, fixture_inputs["output"], _read_blob=fixture_inputs["reader"])
    with pytest.raises(contract.BundleError, match="FRESH_DESTINATION_REQUIRED"):
        contract.extract_bundle(receipt["archive"], root, receipt["archive_sha256"], receipt["manifest_sha256"])


def test_worker_contract_has_no_teacher_or_neural_imports():
    tree = ast.parse(Path(contract.__file__).read_bytes())
    names = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    names += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    assert not any(name and any(part in name.split(".") for part in
        ("data", "package", "torch", "numpy", "boto3", "casformer", "cas_cjt")) for name in names)
    assert not any(isinstance(node, ast.Name) and node.id == "build_dataset" for node in ast.walk(tree))
    assert contract.ARCHIVE_BYTES_MAX == 32 * 1024**2
    assert contract.EXPANDED_BYTES_MAX == 64 * 1024**2
    assert len(contract.ALL_FILES) <= 20
