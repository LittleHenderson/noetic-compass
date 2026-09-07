"""Pure dataset packaging and target-visibility checks; no model execution."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from cas_meta2.condition_skill_v9 import bundle


@pytest.fixture(scope="module")
def packaged(monkeypatch_module, tmp_path_factory):
    # Keep test output inside pytest's disposable directory while preserving the
    # production builder's scoped-output check against its configured ROOT.
    parent = tmp_path_factory.mktemp("condition_bundle")
    monkeypatch_module.setattr(bundle, "ROOT", parent)
    (parent / "records").mkdir()
    root = parent / "records" / "dataset"
    receipt = bundle.build(root)
    return root, receipt


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as patch:
        yield patch


def test_declared_counts_and_separate_files(packaged):
    root, receipt = packaged
    assert receipt["counts"] == {"train": 1536, "validation": 384,
        "test_instances": 384, "test_direction_pair": 384}
    manifest, digest = bundle.inspect(root)
    assert digest == receipt["manifest_sha256"]
    assert manifest["claims"]["learning_measured"] is False
    assert set(manifest["files"]) == set(bundle.FILES)


def test_training_loader_never_parses_test_data(packaged, monkeypatch):
    root, receipt = packaged
    private_bytes = {bundle.read_bytes(root / name) for name in bundle.FILES if name.startswith("test_")}
    original = bundle.decoded
    parsed_count = 0
    def guarded(payload):
        nonlocal parsed_count
        assert payload not in private_bytes
        parsed_count += 1
        return original(payload)
    monkeypatch.setattr(bundle, "decoded", guarded)
    result = bundle.read_partitions(root, ["train.json", "validation.json"], receipt["manifest_sha256"])
    assert parsed_count == 3  # Manifest, training, validation only.
    assert set(result["partitions"]) == {"train.json", "validation.json"}


def test_public_evaluation_files_contain_no_target(packaged):
    root, receipt = packaged
    result = bundle.read_partitions(root,
        ["test_instances.public.json", "test_direction_pair.public.json"], receipt["manifest_sha256"])
    for rows in result["partitions"].values():
        for row in rows:
            assert set(row) == {"schema", "task_id", "conditions"}
            assert "target" not in row and "bits" not in row and "symbol" not in row


def test_private_targets_match_independent_integer_rule(packaged):
    root, receipt = packaged
    result = bundle.read_partitions(root, [name for name in bundle.FILES if name.startswith("test_")],
                                    receipt["manifest_sha256"])
    for split in ("test_instances", "test_direction_pair"):
        publics = result["partitions"][split + ".public.json"]
        targets = result["partitions"][split + ".targets.json"]
        assert len(publics) == len(targets) == 384
        for public, saved in zip(publics, targets, strict=True):
            assert saved["task_id"] == public["task_id"]
            assert saved["target"] == bundle.data.oracle(public)


def test_manifest_pin_change_is_rejected(packaged):
    with pytest.raises(ValueError, match="DATASET_MANIFEST_CHANGED"):
        bundle.inspect(packaged[0], expected_manifest_sha256="0" * 64)


def test_payload_change_is_rejected_without_parsing(packaged, monkeypatch):
    root, receipt = packaged
    original = bundle.read_bytes
    def changed(path):
        raw = original(path)
        return raw + b" " if str(path).endswith("test_instances.targets.json") else raw
    monkeypatch.setattr(bundle, "read_bytes", changed)
    with pytest.raises(ValueError, match="DATASET_FILE_CHANGED"):
        bundle.read_partitions(root, ["train.json"], receipt["manifest_sha256"])


@pytest.mark.parametrize("names", [[], ["../train.json"], ["train.json", "train.json"], "train.json"])
def test_only_explicit_unique_partition_names(packaged, names):
    with pytest.raises(ValueError, match="EXPLICIT_DATASET_PARTITIONS_REQUIRED"):
        bundle.read_partitions(packaged[0], names)


def test_builder_never_overwrites_existing_output(packaged):
    with pytest.raises(ValueError, match="FRESH_SCOPED_DATASET_DIRECTORY_REQUIRED"):
        bundle.build(packaged[0])


@pytest.mark.parametrize("payload", [b'{"x":1,"x":2}', b'{"x":NaN}'])
def test_strict_json(payload):
    with pytest.raises(ValueError):
        bundle.decoded(payload)


def test_current_builder_source_is_required(packaged, monkeypatch):
    original = bundle.read_bytes
    def changed(path):
        raw = original(path)
        return raw + b"\n" if str(path) == str(bundle.data.__file__) else raw
    monkeypatch.setattr(bundle, "read_bytes", changed)
    with pytest.raises(ValueError, match="DATASET_BUILDER_SOURCE_CHANGED"):
        bundle.inspect(packaged[0])
