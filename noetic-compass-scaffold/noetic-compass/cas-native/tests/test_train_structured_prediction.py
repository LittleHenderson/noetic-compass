"""Tests for the local structured-prediction smoke trainer and train/eval harness."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cas_native.training.train_structured_prediction import (
    _is_heldout_eval_path,
    HASH_FEATURE_BASELINE_ALL_HEADS_EXACT_RATE,
    evaluate_structured_token_prediction,
    evaluate_structured_prediction,
    train_structured_prediction_local,
    train_structured_prediction_smoke,
    train_structured_token_prediction_local,
)
from cas_native.model.structured_prediction import StructuredPredictionHead
from cas_native.tokenizer import StructuredTokenVocabulary


def _records():
    return [
        {
            "id": "v75",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Noetic 2 in cognitive domain with drive F4 and affective register.",
        },
        {
            "id": "v76",
            "bucket": "v76_production",
            "cas_expression": (
                "\u0398(\u03a9_focus) = 0.40*^3^P_{F2}|A + "
                "0.60*^7^O_{F5}|E \u2192 \u03a9_focus"
            ),
            "user_prompt": "Recipe target Omega focus from Noetic 3 P F2 A and Noetic 7 O F5 E.",
        },
        {
            "id": "v77",
            "bucket": "v77_omega",
            "cas_expression": "(^4_{F2}|E \u00d7 ^4_{F7}|A) = ^4|\u03a9_attunement",
            "user_prompt": "Omega attunement integrates Noetic 4 embodied F2 and analytical F7.",
        },
        {
            "id": "meta",
            "bucket": "meta_logic",
            "cas_expression": "Product(Noetics, Domains)",
            "user_prompt": "Represent the Cartesian product of Noetics and Domains.",
        },
    ]


def test_smoke_trainer_runs_and_reports_metrics():
    _head, metrics = train_structured_prediction_smoke(
        _records(),
        d_model=32,
        bottleneck_dim=16,
        steps=3,
        lr=0.01,
    )

    assert metrics["records"] == 4.0
    assert metrics["loss"] > 0.0
    assert 0.0 <= metrics["expression_family_acc"] <= 1.0
    assert 0.0 <= metrics["register_exact_acc"] <= 1.0


def test_heldout_eval_path_guard_is_specific():
    assert _is_heldout_eval_path(Path("level3_recoverable_eval_1000.jsonl"))
    assert not _is_heldout_eval_path(Path("level3_recoverable_full.jsonl"))


def test_evaluate_structured_prediction_returns_per_bucket_metrics():
    head = StructuredPredictionHead(d_model=32, bottleneck_dim=16)
    head.eval()
    records = _records()
    manifest = evaluate_structured_prediction(head, records, d_model=32, batch_size=2)

    assert manifest["n"] == 4
    assert 0 <= manifest["all_heads_exact"] <= 4
    assert 0.0 <= manifest["all_heads_exact_rate"] <= 1.0
    assert "per_head_acc" in manifest
    assert "turn_type" in manifest["per_head_acc"]
    assert "registers" in manifest["per_head_acc"]
    assert "meta_relations" in manifest["per_head_acc"]
    assert set(manifest["by_bucket"].keys()) == {
        "v75_register",
        "v76_production",
        "v77_omega",
        "meta_logic",
    }
    for bucket_metrics in manifest["by_bucket"].values():
        assert bucket_metrics["n"] == 1
        assert bucket_metrics["per_head_acc"]["turn_type"] in (0.0, 1.0)
    assert len(manifest["samples"]) == 4
    assert all("head_correct" in sample for sample in manifest["samples"])


def test_train_structured_prediction_local_runs_one_epoch_and_returns_manifest():
    records = _records()
    head, manifest = train_structured_prediction_local(
        records,
        records,
        d_model=32,
        bottleneck_dim=16,
        batch_size=2,
        epochs=2,
        eval_every_steps=None,
        lr=0.05,
        seed=11,
        progress_print=False,
        filter_eval_overlaps=False,
    )

    assert manifest["config"]["n_train"] == 4
    assert manifest["config"]["n_eval"] == 4
    assert manifest["training"]["total_steps"] == 2 * 2
    assert len(manifest["training"]["history"]) == 2
    final = manifest["eval"]
    assert final["n"] == 4
    assert 0.0 <= final["all_heads_exact_rate"] <= 1.0
    assert final["all_heads_exact_rate"] >= manifest["training"]["history"][0]["all_heads_exact_rate"], (
        "best-eval checkpoint must not be worse than first eval snapshot"
    )
    assert head.parameter_count > 0


def test_train_structured_prediction_local_writes_artifacts():
    records = _records()
    tmp_root = Path("C:/tmp")
    if not tmp_root.exists():
        pytest.skip("C:/tmp is not available for artifact-write smoke")
    out_dir = tmp_root / "cas_structured_prediction_artifact_test"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    try:
        try:
            _head, manifest = train_structured_prediction_local(
                records,
                records,
                d_model=32,
                bottleneck_dim=16,
                batch_size=2,
                epochs=1,
                lr=0.05,
                seed=7,
                out_dir=out_dir,
                progress_print=False,
                filter_eval_overlaps=False,
            )
        except PermissionError as exc:
            pytest.skip(f"artifact-write smoke blocked by filesystem permissions: {exc}")

        assert (out_dir / "manifest.json").exists()
        assert (out_dir / "best_head.pt").exists()
        assert (out_dir / "samples.jsonl").exists()

        on_disk = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        assert on_disk["eval"]["n"] == manifest["eval"]["n"]
        sample_lines = (out_dir / "samples.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(sample_lines) == 4
        parsed = [json.loads(line) for line in sample_lines]
        assert {sample["bucket"] for sample in parsed} == {
            "v75_register",
            "v76_production",
            "v77_omega",
            "meta_logic",
        }
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_train_structured_prediction_local_runs_without_eval_records():
    records = _records()
    _head, manifest = train_structured_prediction_local(
        records,
        eval_records=None,
        d_model=32,
        bottleneck_dim=16,
        batch_size=2,
        epochs=1,
        lr=0.05,
        seed=3,
        progress_print=False,
    )
    assert manifest["config"]["n_eval"] == 0
    assert manifest["training"]["total_steps"] == 2
    assert manifest["eval"]["n"] == 0
    assert manifest["training"]["history"] == []


def test_structured_token_train_eval_runner_returns_manifest_and_comparison():
    records = _records()
    _model, vocab, manifest = train_structured_token_prediction_local(
        records,
        records,
        d_model=32,
        bottleneck_dim=16,
        batch_size=2,
        epochs=2,
        lr=0.01,
        seed=23,
        progress_print=False,
        filter_eval_overlaps=False,
        max_length=32,
    )

    assert manifest["config"]["mode"] == "structured_token"
    assert manifest["config"]["vocab_size"] == len(vocab)
    assert manifest["config"]["n_train"] == 4
    assert manifest["config"]["n_eval"] == 4
    assert manifest["training"]["total_steps"] == 4
    assert len(manifest["training"]["history"]) == 2
    assert manifest["eval"]["n"] == 4
    comparison = manifest["eval"]["baseline_comparison"]
    assert comparison["baseline_all_heads_exact_rate"] == HASH_FEATURE_BASELINE_ALL_HEADS_EXACT_RATE
    assert comparison["candidate_all_heads_exact_rate"] == manifest["eval"]["all_heads_exact_rate"]


def test_structured_token_eval_reports_per_bucket_metrics():
    records = _records()
    model, vocab, _manifest = train_structured_token_prediction_local(
        records,
        eval_records=None,
        d_model=32,
        bottleneck_dim=16,
        batch_size=2,
        epochs=1,
        lr=0.01,
        seed=29,
        progress_print=False,
        max_length=32,
    )

    eval_manifest = evaluate_structured_token_prediction(
        model,
        records,
        vocab,
        batch_size=2,
        max_length=32,
    )

    assert eval_manifest["n"] == 4
    assert set(eval_manifest["by_bucket"].keys()) == {
        "v75_register",
        "v76_production",
        "v77_omega",
        "meta_logic",
    }
    assert len(eval_manifest["samples"]) == 4


def test_structured_token_vocabulary_builds_from_train_prompts_only():
    train_records = [
        {
            "id": "train",
            "bucket": "v74_baseline",
            "cas_expression": "^1^P_{F1}|T",
            "user_prompt": "plain train prompt only",
            "assistant_response": "answer leak ^9^O_{F7}|E",
        }
    ]

    _model, vocab, manifest = train_structured_token_prediction_local(
        train_records,
        eval_records=None,
        d_model=16,
        bottleneck_dim=8,
        batch_size=1,
        epochs=1,
        lr=0.01,
        seed=31,
        progress_print=False,
        max_length=16,
    )

    assert manifest["config"]["mode"] == "structured_token"
    assert "cas:^9^O_{F7}|E" not in vocab.token_to_id
    assert "surf:plain" in vocab.token_to_id


def test_structured_token_train_eval_writes_artifacts():
    records = _records()
    tmp_root = Path("C:/tmp")
    if not tmp_root.exists():
        pytest.skip("C:/tmp is not available for artifact-write smoke")
    out_dir = tmp_root / "cas_structured_token_prediction_artifact_test"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    try:
        try:
            _model, _vocab, manifest = train_structured_token_prediction_local(
                records,
                records,
                d_model=32,
                bottleneck_dim=16,
                batch_size=2,
                epochs=1,
                lr=0.01,
                seed=37,
                out_dir=out_dir,
                progress_print=False,
                filter_eval_overlaps=False,
                max_length=32,
            )
        except PermissionError as exc:
            pytest.skip(f"artifact-write smoke blocked by filesystem permissions: {exc}")

        assert (out_dir / "manifest.json").exists()
        assert (out_dir / "best_structured_token_model.pt").exists()
        assert (out_dir / "structured_token_vocab.json").exists()
        assert (out_dir / "samples.jsonl").exists()

        on_disk = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        loaded_vocab = StructuredTokenVocabulary.load(out_dir / "structured_token_vocab.json")
        assert on_disk["config"]["vocab_size"] == len(loaded_vocab)
        assert on_disk["eval"]["n"] == manifest["eval"]["n"]
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
