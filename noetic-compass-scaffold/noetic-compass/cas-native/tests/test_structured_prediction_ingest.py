"""Tests for structured-prediction label extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from cas_native.model.structured_prediction import (
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
)
from cas_native.training.structured_prediction_ingest import (
    batch_targets_from_records,
    labels_from_level3_record,
    load_level3_jsonl,
)


def _record(bucket: str, expression: str) -> dict[str, object]:
    return {
        "id": f"rec-{bucket}",
        "source_level2_id": "level2-test",
        "bucket": bucket,
        "cas_expression": expression,
    }


def test_extracts_production_slots_without_treating_coefficients_as_integration():
    expression = (
        "\u0398(\u03a9_focus) = 0.40*^3^P_{F2}|A + "
        "0.60*^7^O_{F5}|E \u2192 \u03a9_focus"
    )

    labels = labels_from_level3_record(_record("v76_production", expression))

    assert EXPRESSION_FAMILY_LABELS[labels["expression_family"]] == "production"
    assert labels["noetic"] == 3
    assert labels["domain"] == 0
    assert labels["drive"] == 1
    assert labels["has_omega"] == 1
    assert REGISTER_MODE_LABELS[labels["register_mode"]] == "co_presence"
    assert labels["registers"][REGISTER_LABELS.index("A")] == 1.0
    assert labels["registers"][REGISTER_LABELS.index("E")] == 1.0


def test_extracts_omega_integration_slots():
    expression = "(^4_{F2}|E \u00d7 ^4_{F7}|A) = ^4|\u03a9_attunement"

    labels = labels_from_level3_record(_record("v77_omega", expression))

    assert EXPRESSION_FAMILY_LABELS[labels["expression_family"]] == "omega"
    assert labels["noetic"] == 4
    assert labels["drive"] == 1
    assert labels["has_omega"] == 1
    assert REGISTER_MODE_LABELS[labels["register_mode"]] == "integration"
    assert labels["registers"][REGISTER_LABELS.index("A")] == 1.0
    assert labels["registers"][REGISTER_LABELS.index("E")] == 1.0


def test_extracts_meta_logic_relation_targets():
    labels = labels_from_level3_record(
        _record("meta_logic", "Product(Noetics, Domains)")
    )

    assert EXPRESSION_FAMILY_LABELS[labels["expression_family"]] == "meta_logic"
    assert labels["has_meta_logic"] == 1
    assert labels["meta_relations"][META_RELATION_LABELS.index("product")] == 1.0


def test_batch_targets_from_records_are_tensorized():
    records = [
        _record("v75_register", "^2^C_{F4}|f"),
        _record("meta_logic", "NoeticCluster{^2, ^7} \u2286 Noetics"),
    ]

    targets = batch_targets_from_records(records)

    assert targets["turn_type"].shape == (2,)
    assert targets["registers"].shape == (2, len(REGISTER_LABELS))
    assert targets["meta_relations"].shape == (2, len(META_RELATION_LABELS))


def test_local_heldout_eval_records_are_parseable_when_present():
    repo_root = Path(__file__).resolve().parents[4]
    eval_path = (
        repo_root
        / "cas-synthetic"
        / "data"
        / "level2_scaffold"
        / "level3_recoverable_eval_1000.jsonl"
    )
    if not eval_path.exists():
        pytest.skip("held-out Level 3 eval file is not present in this checkout")

    records = load_level3_jsonl(eval_path, limit=20)
    targets = batch_targets_from_records(records)

    assert len(records) == 20
    assert targets["turn_type"].shape == (20,)
    assert targets["registers"].shape == (20, len(REGISTER_LABELS))
