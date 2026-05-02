"""Tests for the v77_rule_four → v77_omega structural-overlap relabeler."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# Locate the script directory so we can import the module.
_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from relabel_v77_overlap import (  # noqa: E402
    _is_same_noetic_omega_emergent,
    main,
    relabel_record_if_overlap,
    relabel_records,
)


# ---- Pattern detector ----------------------------------------------------

@pytest.mark.parametrize("expression,expected", [
    # Same-Noetic ×=Ω_* — overlapping pattern → True
    ("(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_refusal", True),
    ("(^1|A × ^1|E) = ^1|Ω_presence", True),
    ("(^4_{F2}|E × ^4_{F7}|A) = ^4|Ω_attunement", True),
    # Different-Noetic ×=Ω → not the overlap
    ("(^4|f × ^7|A) = ^4|Ω_attunement", False),
    # `+` co-presence (no `×`) → not the overlap
    ("^3^P|A + ^3^P|f + ^3^P|T", False),
    # Same-Noetic × WITHOUT emergent (Rule 4 violation case) → not the overlap
    ("(^2^C|A × ^2^C|f)", False),
    # Bare state → not the overlap
    ("^2^C_{F4}|f", False),
    # Production recipe → not the overlap
    ("Θ(Ω_focus) = 0.40*^3^P_{F2}|A → Ω_focus", False),
])
def test_pattern_detector(expression: str, expected: bool):
    assert _is_same_noetic_omega_emergent(expression) is expected


# ---- Per-record relabel --------------------------------------------------

def test_relabel_only_fires_on_v77_rule_four_with_overlap():
    record = {
        "id": "r1",
        "bucket": "v77_rule_four",
        "cas_expression": "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_refusal",
    }
    out, was_relabeled = relabel_record_if_overlap(record)
    assert was_relabeled is True
    assert out["bucket"] == "v77_omega"
    assert out["bucket_relabeled_from"] == "v77_rule_four"
    assert out["bucket_relabel_reason"] == "structural_overlap_with_v77_omega"


def test_relabel_skips_v77_rule_four_copresence():
    record = {
        "id": "r2",
        "bucket": "v77_rule_four",
        "cas_expression": "^3^P|A + ^3^P|f + ^3^P|T",
    }
    out, was_relabeled = relabel_record_if_overlap(record)
    assert was_relabeled is False
    assert out["bucket"] == "v77_rule_four"


def test_relabel_skips_v77_omega_records_already():
    record = {
        "id": "r3",
        "bucket": "v77_omega",
        "cas_expression": "(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal",
    }
    out, was_relabeled = relabel_record_if_overlap(record)
    assert was_relabeled is False
    assert "bucket_relabeled_from" not in out


def test_relabel_is_idempotent_on_already_relabeled():
    record = {
        "id": "r4",
        "bucket": "v77_omega",
        "bucket_relabeled_from": "v77_rule_four",
        "cas_expression": "(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal",
    }
    out, was_relabeled = relabel_record_if_overlap(record)
    assert was_relabeled is False
    assert out == record


def test_relabel_does_not_mutate_input():
    record = {
        "id": "r5",
        "bucket": "v77_rule_four",
        "cas_expression": "(^1|A × ^1|E) = ^1|Ω_presence",
    }
    snapshot = dict(record)
    out, _ = relabel_record_if_overlap(record)
    assert record == snapshot
    assert out is not record


def test_relabel_preserves_all_other_fields():
    record = {
        "id": "r6",
        "bucket": "v77_rule_four",
        "cas_expression": "(^1|A × ^1|E) = ^1|Ω_presence",
        "user_prompt": "do not lose me",
        "source_level2_id": "level2-X",
        "scores": [0.1, 0.2, 0.3],
    }
    out, _ = relabel_record_if_overlap(record)
    assert out["user_prompt"] == "do not lose me"
    assert out["source_level2_id"] == "level2-X"
    assert out["scores"] == [0.1, 0.2, 0.3]


# ---- Aggregate / counts --------------------------------------------------

def test_relabel_records_counts_correctly():
    records = [
        {"bucket": "v74_baseline", "cas_expression": "^1^P|A"},
        {"bucket": "v77_rule_four", "cas_expression": "(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal"},
        {"bucket": "v77_rule_four", "cas_expression": "^3^P|A + ^3^P|f + ^3^P|T"},
        {"bucket": "v77_rule_four", "cas_expression": "(^2^C|A × ^2^C|f)"},  # violation, no Ω
        {"bucket": "v77_omega", "cas_expression": "(^4|f × ^4|A) = ^4|Ω_attunement"},
    ]
    out, counts = relabel_records(records)
    assert counts == {
        "n_total": 5,
        "n_v77_rule_four_input": 3,
        "n_relabeled_to_v77_omega": 1,
        "n_v77_rule_four_remaining": 2,
    }
    assert out[1]["bucket"] == "v77_omega"
    assert out[2]["bucket"] == "v77_rule_four"
    assert out[3]["bucket"] == "v77_rule_four"


# ---- CLI integration -----------------------------------------------------

def test_cli_writes_relabeled_jsonl(tmp_path: Path):
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    records = [
        {"bucket": "v77_rule_four",
         "cas_expression": "(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal"},
        {"bucket": "v74_baseline", "cas_expression": "^2^C|f"},
    ]
    in_path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    rc = main(["--in", str(in_path), "--out", str(out_path)])
    assert rc == 0

    written = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert len(written) == 2
    assert written[0]["bucket"] == "v77_omega"
    assert written[0]["bucket_relabeled_from"] == "v77_rule_four"
    assert written[1]["bucket"] == "v74_baseline"


def test_cli_dry_run_does_not_write(tmp_path: Path):
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    records = [
        {"bucket": "v77_rule_four",
         "cas_expression": "(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal"},
    ]
    in_path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    rc = main(["--in", str(in_path), "--out", str(out_path), "--dry-run"])
    assert rc == 0
    assert not out_path.exists()
