"""Pure byte-custody and reference-count tests; no checkpoint deserialization."""
from copy import deepcopy
from pathlib import Path
import os
import shutil
import sys

import pytest

from cas_meta2.diagnostic_v8 import bundle as b

# Tests deliberately require the real pinned upstream development inputs and
# checkpoint bytes, never a fabricated packet or a skipped custody check.
EXTRACTED = Path(os.environ.get("CAS_META2_V8_TEST_EXTRACTION", str(
    b.ROOT / "records/prototype_v7_partial_review_001/extracted_001"))).absolute()


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    base = tmp_path_factory.mktemp("diagnostic_v8_bundle")
    result = b.prepare(EXTRACTED, base / "original")
    return Path(result["bundle"]), result["manifest_sha256"]


@pytest.fixture
def copied(prepared, tmp_path):
    original, expected = prepared
    output = tmp_path / "copy"
    shutil.copytree(original, output)
    return output, expected


def reseal(output):
    path = output / "manifest.json"
    manifest = b.decode(path.read_bytes())
    for name in manifest["files"]:
        raw = (output / name).read_bytes()
        manifest["files"][name] = {"bytes": len(raw), "sha256": b.digest(raw)}
    path.write_bytes(b.canonical(manifest) + b"\n")
    return b.digest(path.read_bytes())


def test_real_bundle_has_exact_counts_and_no_final_inputs(prepared):
    output, expected = prepared
    loaded = b.validate_bundle(output, expected_manifest_sha256=expected)
    assert set(loaded) == {"manifest", "manifest_sha256", "cohorts", "tokenizer",
                           "registration", "training_receipt", "checkpoints", "saved_development"}
    assert {name: len(tasks) for name, tasks in loaded["cohorts"].items()} == {
        "train_probe": 24, "validation": 96}
    assert loaded["manifest"]["limits"]["selected_role_opportunities_per_checkpoint"] == 2272
    assert loaded["manifest"]["limits"]["next_tokens_per_checkpoint"] == 9728
    assert loaded["manifest"]["cohorts"]["train_probe"]["decision_counts"]["overall"]["next_tokens"] == 1984
    assert loaded["manifest"]["cohorts"]["validation"]["decision_counts"]["overall"]["next_tokens"] == 7744
    assert len(list(output.rglob("*.pt"))) == 4
    assert all("test_public" not in name and "test_private" not in name
               and "neural_predictions" not in name for name in loaded["manifest"]["files"])
    assert len(loaded["saved_development"]) == 4
    assert loaded["manifest"]["boundary"]["checkpoint_deserialization"] is False
    assert loaded["checkpoints"]["generic_selected"]["record"]["epoch"] == 180
    assert loaded["checkpoints"]["cas_selected"]["record"]["epoch"] == 200


def test_prepare_has_no_neural_import_or_final_file_read(tmp_path, monkeypatch):
    opened = []
    original_read = b.read
    def recording_read(path):
        name = str(path).replace("\\", "/")
        assert not name.endswith(("/test_public.json", "/test_private.json"))
        assert "/neural_predictions" not in name
        opened.append(name)
        return original_read(path)
    class ImportGuard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"torch", "numpy", "casformer", "cas_cjt",
                                         "cas_meta", "boto3", "botocore"}:
                raise AssertionError("Unexpected non-pure import: " + fullname)
    monkeypatch.setattr(b, "read", recording_read)
    monkeypatch.setattr(sys, "meta_path", [ImportGuard(), *sys.meta_path])
    result = b.prepare(EXTRACTED, tmp_path / "pure")
    assert result["status"] == "DEVELOPMENT_ONLY_BUNDLE_PREPARED"
    assert any(name.endswith("/trainer_input/train.json") for name in opened)
    assert not any(name.endswith("/test_private.json") for name in opened)


def test_existing_destination_is_preserved(prepared):
    output, expected = prepared
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(b.BundleError, match="NEW_OUTPUT_REQUIRED"):
        b.prepare(EXTRACTED, output)
    assert (output / "manifest.json").read_bytes() == before
    assert b.digest(before) == expected


def test_output_outside_candidate_is_refused():
    outside = b.ROOT.parent / "not_an_authorized_diagnostic_output"
    with pytest.raises(b.BundleError, match="OUTPUT_MUST_BE_INSIDE_CANDIDATE"):
        b.prepare(EXTRACTED, outside)
    assert not outside.exists()


@pytest.mark.parametrize("pin", [None, "", "z" * 64, "0" * 64])
def test_external_pin_is_required(prepared, pin):
    output, _ = prepared
    with pytest.raises(b.BundleError, match="EXTERNAL_MANIFEST_PIN_REQUIRED|MANIFEST_BYTES_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=pin)


@pytest.mark.parametrize("mutation", ["extra_file", "extra_directory", "missing_file"])
def test_exact_file_set(copied, mutation):
    output, expected = copied
    if mutation == "extra_file":
        (output / "test_private.json").write_bytes(b"[]")
    elif mutation == "extra_directory":
        (output / "unused").mkdir()
    else:
        (output / "validation.json").unlink()
    with pytest.raises(b.BundleError, match="BUNDLE_FILE_SET|EXTRA_BUNDLE_DIRECTORY"):
        b.validate_bundle(output, expected_manifest_sha256=expected)


def test_checkpoint_mutation_cannot_be_resealed(copied):
    output, _ = copied
    target = output / "checkpoints/cas_selected.pt"
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    expected = reseal(output)
    with pytest.raises(b.BundleError, match="UPSTREAM_BYTES_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=expected)


@pytest.mark.parametrize("mutation", ["reorder", "duplicate", "target"])
def test_changed_cohort_cannot_be_resealed(copied, mutation):
    output, _ = copied
    path = output / "train_probe.json"
    rows = b.decode(path.read_bytes())
    if mutation == "reorder":
        rows = rows[::-1]
    elif mutation == "duplicate":
        rows[0] = deepcopy(rows[1])
    else:
        rows[0]["target"]["binding"] = (rows[0]["target"]["binding"] + 1) % 3
    path.write_bytes(b.canonical(rows) + b"\n")
    expected = reseal(output)
    with pytest.raises(b.BundleError, match="COHORT_CONTENT_OR_ORDER_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=expected)


def test_changed_metadata_cannot_be_resealed(copied):
    output, _ = copied
    path = output / "metadata/registration.json"
    data = b.decode(path.read_bytes())
    data["config"]["seed"] += 1
    path.write_bytes(b.canonical(data) + b"\n")
    expected = reseal(output)
    with pytest.raises(b.BundleError, match="UPSTREAM_BYTES_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=expected)


def test_changed_counts_cannot_be_resealed(copied):
    output, _ = copied
    path = output / "manifest.json"
    data = b.decode(path.read_bytes())
    data["cohorts"]["train_probe"]["decision_counts"]["overall"]["tasks"] = 23
    path.write_bytes(b.canonical(data) + b"\n")
    with pytest.raises(b.BundleError, match="MANIFEST_CONTENT_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=b.digest(path.read_bytes()))


@pytest.mark.parametrize("mutation", ["float_count", "integer_boolean"])
def test_manifest_scalar_types_cannot_be_resealed(copied, mutation):
    output, _ = copied
    path = output / "manifest.json"
    data = b.decode(path.read_bytes())
    if mutation == "float_count":
        data["limits"]["cohort_tasks"] = 120.0
    else:
        data["boundary"]["learning_result"] = 0
    path.write_bytes(b.canonical(data) + b"\n")
    with pytest.raises(b.BundleError, match="MANIFEST_CONTENT_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=b.digest(path.read_bytes()))


@pytest.mark.parametrize("name", ["../x", "/x", "C:/x", "x\\y", "x/../y", "./x", "x//y"])
def test_unsafe_relative_paths_are_refused(name):
    with pytest.raises(b.BundleError, match="RELATIVE_PATH_REQUIRED"):
        b.relative_path(name)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}'])
def test_duplicate_and_nonfinite_json_are_refused(raw):
    with pytest.raises(b.BundleError):
        b.decode(raw)


def test_manifest_path_escape_is_refused(copied):
    output, _ = copied
    path = output / "manifest.json"
    data = b.decode(path.read_bytes())
    data["files"]["../outside"] = {"bytes": 0, "sha256": "0" * 64}
    path.write_bytes(b.canonical(data) + b"\n")
    with pytest.raises(b.BundleError, match="RELATIVE_PATH_REQUIRED"):
        b.validate_bundle(output, expected_manifest_sha256=b.digest(path.read_bytes()))


def test_link_detection_rejects_without_following(prepared, monkeypatch):
    output, expected = prepared
    target = output / "tokenizer.json"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == target or original(self))
    with pytest.raises(b.BundleError, match="LINK_REFUSED"):
        b.validate_bundle(output, expected_manifest_sha256=expected)


def test_pinned_helper_change_is_refused(prepared, monkeypatch):
    output, expected = prepared
    original = b.read
    def changed(path):
        raw = original(path)
        return raw + b"\n" if Path(path) == b.ROOT / "cas_meta2/grammar_v3.py" else raw
    monkeypatch.setattr(b, "read", changed)
    with pytest.raises(b.BundleError, match="SOURCE_CHANGED"):
        b.validate_bundle(output, expected_manifest_sha256=expected)


def test_static_counts_keep_zero_call_groups(prepared):
    output, expected = prepared
    loaded = b.validate_bundle(output, expected_manifest_sha256=expected)
    score = b.decision_counts(loaded["cohorts"]["train_probe"])
    assert score["by_depth"]["1"]["roles"]["call_target"] == 0
    assert score["by_depth"]["1"]["roles"]["child_return"] == 0
    assert score["by_depth"]["2"]["roles"]["call_target"] == 32
    assert score["by_depth"]["3"]["roles"]["child_return"] == 24
    # A locally forced singleton is not silently counted as a meaningful choice.
    assert score["by_depth"]["1"]["nonsingleton_roles"]["run_input"] == 56
    assert score["by_depth"]["1"]["roles"]["run_input"] == 64
