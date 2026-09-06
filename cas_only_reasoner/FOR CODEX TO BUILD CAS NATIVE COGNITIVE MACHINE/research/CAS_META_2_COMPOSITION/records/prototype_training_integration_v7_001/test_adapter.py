"""Pure original-data and train-only boundary tests; no new generated curriculum."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import adapter as a

FIXTURE = a.ROOT / "records/contrast_v6_bundle_probe_001/dataset"
PIN = "36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1"
CONFIG = {"train_flat": 32, "train_pairs_per_cell": 8, "validation_flat": 8,
          "validation_pairs_per_cell": 2, "test_triplets": 3}


@pytest.fixture(scope="module")
def ctx():
    return a.Context()


@pytest.fixture(scope="module")
def originals(ctx):
    return a.original(ctx)


@pytest.fixture(scope="module")
def base(ctx):
    raw = {name: a.read(FIXTURE / name) for name in ("manifest.json", "train.json", *a.HELDOUT)}
    options = dict(expected_sha256=PIN, seed=926603, config=ctx.c.Config(**CONFIG), excluded=frozenset(), ctx=ctx)
    manifest, splits = a.admit_base(raw, **options)
    return raw, options, manifest, splits


@pytest.fixture(scope="module")
def merged(tmp_path_factory, base):
    path = Path(os.environ["V7_TEST_RECORD"]) / "positive_merge" / "bundle"
    receipt = a.merge(FIXTURE, path, **base[1])
    return path, receipt


def test_exact_pinned_originals_with_frozen_checkers(ctx, originals):
    tasks, receipt, checked = originals
    assert len(tasks) == 256 and checked["pairs"] == 128
    assert checked["depths"] == {"2": 128, "3": 128}
    assert ctx.source["frozen_source_sha"] == a.FROZEN_SOURCE
    assert len(ctx.source["frozen_files_sha256"]) == 16
    assert a.digest(a.read(a.ROOT / a.PROTOTYPE / "tasks.json")) == a.TASKS_SHA256


def test_actual_merge_counts_and_exact_original_fields(merged, base, originals):
    path, receipt = merged
    assert receipt["splits"] == {
        "train": {"tasks": 352, "depths": {"1": 32, "2": 160, "3": 160}},
        "validation": {"tasks": 24, "depths": {"1": 8, "2": 8, "3": 8}},
        "test": {"tasks": 9, "depths": {"3": 6, "4": 3}}}
    train = a.decode(a.read(path / "train.json"))
    assert a.canonical(train[:96]) == a.canonical(base[3]["train"])
    assert a.canonical(train[96:]) == a.canonical(originals[0])
    for name in a.HELDOUT:
        assert a.read(path / name) == base[0][name]
    assert a.read(path / "base_train.json") == base[0]["train.json"]
    assert receipt["training_performed"] is False and receipt["parent_reads_private_test_targets"] is True


def test_new_schema_and_original_provenance_map(merged, originals):
    path, _ = merged
    manifest = a.decode(a.read(path / "manifest.json"))
    imports = a.decode(a.read(path / "training_imports.json"))
    assert manifest["schema"] == a.SCHEMA != "cas-meta2-contrast-curriculum/6"
    assert manifest["source"]["frozen_source_sha"] == a.FROZEN_SOURCE
    assert imports["destination_split"] == "train"
    assert len(imports["records"]) == 256
    assert len({row["pair_id"] for row in imports["records"]}) == 128
    for row, task in zip(imports["records"], originals[0], strict=True):
        assert row["original_record_sha256"] == a.digest(a.canonical(task))
        assert row["original_provenance_sha256"] == a.digest(a.canonical(task["provenance"]))


def test_tokenizer_fits_only_352_training_problems(merged, ctx):
    path, _ = merged
    train = a.decode(a.read(path / "train.json"))
    expected = ctx.c.LosslessPublicTokenizer.fit_train([t["public"] for t in train], max_length=1024)
    recorded = a.decode(a.read(path / "tokenizer.json"))
    assert a.canonical(recorded) == a.canonical(expected.to_dict())
    assert recorded["fit_split"] == "train_only" and recorded["fitted_examples"] == 352
    m = a.decode(a.read(path / "manifest.json"))
    assert m["tokens"]["positive_action_token_coverage"]
    assert all(v["input_tokens"] <= 1024 and v["action_tokens"] <= 256
               for v in m["tokens"]["actual_maxima"].values())


@pytest.mark.parametrize("mutation", ["drop", "change", "reorder", "base_prefix", "split_map"])
def test_exact_append_rejects_mutations(base, originals, mutation):
    original = originals[0]
    train = deepcopy(base[3]["train"] + original)
    imports = a.import_map(base[3]["train"], original)
    if mutation == "drop":
        train.pop()
    elif mutation == "change":
        train[-1]["public"]["problem"] += " "
    elif mutation == "reorder":
        train[-1], train[-2] = train[-2], train[-1]
    elif mutation == "base_prefix":
        train[0]["target"]["binding"] = (train[0]["target"]["binding"] + 1) % 3
    else:
        imports["records"][-1]["train_index"] = 0
        imports["destination_split"] = "validation"
    with pytest.raises(ValueError, match="EXACT_APPEND|ORIGINAL_APPEND|BASE_TRAIN|TRAINING_IMPORT"):
        a.check_exact_merge(train, base[3]["train"], original, imports)


def test_original_cross_binding_rejected(ctx, originals):
    tasks, receipt, _ = originals
    changed = deepcopy(tasks)
    changed[1]["target"]["binding"] = (changed[1]["target"]["binding"] + 1) % 3
    with pytest.raises(ValueError, match="ORIGINAL_PAIR_CONTEXT_CHANGED"):
        a.check_original_records(changed, receipt, ctx)


def test_original_pair_split_identity_rejected(ctx, originals):
    tasks, receipt, _ = originals
    changed = deepcopy(tasks)
    changed[1]["contrast"]["pair_id"] = "different-pair"
    with pytest.raises(ValueError, match="ORIGINAL_PAIR_IDENTITY_CHANGED"):
        a.check_original_records(changed, receipt, ctx)


@pytest.mark.parametrize("kind", ["drop", "change", "duplicate"])
def test_pinned_original_raw_rejects_alteration(ctx, originals, kind):
    changed = deepcopy(originals[0])
    if kind == "drop":
        changed.pop()
    elif kind == "duplicate":
        changed[-1] = deepcopy(changed[0])
    else:
        changed[0]["provenance"]["evaluation_group"] = "train"
    with pytest.raises(ValueError, match="ORIGINAL_PROTOTYPE_BYTES_CHANGED"):
        a.original(ctx, a.canonical(changed) + b"\n")


@pytest.mark.parametrize("split", ["train", "validation", "test"])
@pytest.mark.parametrize("kind", ["graph", "observation", "task_id"])
def test_cross_partition_overlap_rejected(ctx, base, originals, split, kind):
    splits = deepcopy(base[3])
    original = originals[0][0]
    if kind == "graph":
        splits[split][0]["target"]["program"] = deepcopy(original["target"]["program"])
        code = "PROTOTYPE_GRAPH_OVERLAP:" + split
    elif kind == "observation":
        splits[split][0]["public"]["observations"][0]["values"] = list(original["public"]["observations"][0]["values"])
        code = "PROTOTYPE_OBSERVATION_OVERLAP:" + split
    else:
        splits[split][0]["task_id"] = original["task_id"]
        code = "PROTOTYPE_TASK_ID_OVERLAP:" + split
    with pytest.raises(ValueError, match=code):
        a.check_split_safety(splits, originals[0], ctx)


def reseal(path):
    manifest = a.decode(a.read(path / "manifest.json"))
    manifest["sha256"] = {name: a.digest(a.read(path / name)) for name in a.FILES}
    (path / "manifest.json").write_bytes(a.canonical(manifest) + b"\n")
    return a.digest(a.read(path / "manifest.json"))


@pytest.mark.parametrize("mutation", ["drop", "change", "split", "validation_leak", "test_private_leak", "test_public_leak", "tokenizer_leak"])
def test_resealed_output_does_not_bypass_semantic_checks(tmp_path, merged, base, originals, mutation):
    path = tmp_path / "resealed"
    shutil.copytree(merged[0], path)
    if mutation in ("drop", "change", "split"):
        train = a.decode(a.read(path / "train.json"))
        if mutation == "drop":
            train.pop()
        elif mutation == "change":
            train[-1]["target"]["binding"] = (train[-1]["target"]["binding"] + 1) % 3
        else:
            train[-2], train[-1] = train[-1], train[-2]
        (path / "train.json").write_bytes(a.canonical(train) + b"\n")
    elif mutation == "tokenizer_leak":
        tokenizer = a.decode(a.read(path / "tokenizer.json"))
        tokenizer["fitted_examples"] += 24
        tokenizer["fit_split"] = "train_and_validation"
        (path / "tokenizer.json").write_bytes(a.canonical(tokenizer) + b"\n")
    else:
        name = {"validation_leak": "validation.json", "test_private_leak": "test_private.json",
                "test_public_leak": "test_public.json"}[mutation]
        records = a.decode(a.read(path / name))
        records.append(deepcopy(originals[0][0] if mutation != "test_public_leak" else originals[0][0]["public"]))
        (path / name).write_bytes(a.canonical(records) + b"\n")
    options = {**base[1], "expected_sha256": reseal(path)}
    with pytest.raises(ValueError, match="EXACT_APPEND|ORIGINAL_APPEND|HELDOUT_BYTES_CHANGED|V7_COLD_RECONCILIATION"):
        a.validate_bundle(path, **options)


def test_base_external_manifest_required_before_output(tmp_path, base):
    options = {**base[1], "expected_sha256": "0" * 64}
    output = Path(os.environ["V7_TEST_RECORD"]) / "bad_base" / "never"
    with pytest.raises(ValueError, match="EXTERNAL_MANIFEST_DIGEST_MISMATCH"):
        a.merge(FIXTURE, output, **options)
    assert not output.exists()


def test_v7_external_manifest_required(merged, base):
    with pytest.raises(ValueError, match="EXTERNAL_V7_MANIFEST_DIGEST_MISMATCH"):
        a.validate_bundle(merged[0], **{**base[1], "expected_sha256": "0" * 64})


def test_existing_output_refused(merged, base):
    with pytest.raises(ValueError, match="NEW_V7_RECORD_OUTPUT_REQUIRED"):
        a.merge(FIXTURE, merged[0], **base[1])


def test_registered_live_seed_refused_before_any_source_read(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "read", lambda *_: pytest.fail("READ_REACHED"))
    with pytest.raises(ValueError, match="LIVE_V6_REGISTERED_DATASET_REFUSED"):
        a.merge(tmp_path / "missing", tmp_path / "out", expected_sha256="0" * 64,
                seed=2026092601, config=None, excluded=frozenset())


def test_no_generator_called_during_materialization(ctx, base, monkeypatch):
    monkeypatch.setattr(ctx.c, "generate", lambda *args, **kwargs: pytest.fail("GENERATOR_REACHED"))
    monkeypatch.setattr(ctx.c, "write", lambda *args, **kwargs: pytest.fail("GENERATOR_WRITE_REACHED"))
    monkeypatch.setattr(ctx.c.frozen, "_construct", lambda *args, **kwargs: pytest.fail("CONSTRUCTOR_REACHED"))
    _, manifest = a.materialize(base[0], **base[1])
    assert manifest["training_append_count"] == 256


@pytest.mark.parametrize("name", ["torch", "casformer", "cas_cjt", "boto3", "botocore"])
def test_forbidden_imports_rejected(name):
    with pytest.raises(RuntimeError, match="LOCAL_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN"):
        a.Guard().find_spec(name)


def test_source_bytes_verified_against_exact_git_objects(ctx):
    assert a.source_identity() == ctx.source
    assert not any(name.split(".")[0] in a.FORBIDDEN for name in sys.modules)
