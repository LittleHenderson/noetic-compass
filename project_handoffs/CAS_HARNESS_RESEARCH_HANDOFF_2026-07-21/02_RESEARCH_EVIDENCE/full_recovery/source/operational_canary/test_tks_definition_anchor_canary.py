from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


CANARY_DIR = Path(__file__).resolve().parent
if str(CANARY_DIR) not in sys.path:
    sys.path.insert(0, str(CANARY_DIR))

import run_tks_definition_anchor_canary as canary


def scenario(group: str, suffix: str, foundation: str):
    return SimpleNamespace(
        split="stage7_val",
        group_id=group,
        scenario_id=f"{group}_{suffix}",
        foundation=foundation,
    )


def complete_pairs(count: int = 6):
    rows = []
    for index in range(count):
        group = f"pair_{index:02d}"
        rows.extend(
            [
                scenario(group, "a", "F1|T"),
                scenario(group, "b", "F1|A"),
            ]
        )
    return rows


def valid_capture_arrays(hidden_size: int = 5):
    digest = "a" * 64
    return {
        "eval_mean": np.zeros((8, 2, hidden_size), dtype=np.float16),
        "eval_last": np.ones((8, 2, hidden_size), dtype=np.float16),
        "eval_token_counts": np.full((8,), 7, dtype=np.int32),
        "eval_token_hashes": np.asarray([digest] * 8, dtype=np.str_),
        "definition_mean": np.zeros((3, 28, 2, hidden_size), dtype=np.float16),
        "definition_last": np.ones((3, 28, 2, hidden_size), dtype=np.float16),
        "definition_token_counts": np.full((3, 28), 11, dtype=np.int32),
        "definition_token_hashes": np.asarray([[digest] * 28] * 3, dtype=np.str_),
        "hidden_size": hidden_size,
    }


def test_pair_selection_is_order_independent_and_exactly_four_complete_pairs():
    rows = complete_pairs()
    selected_a, groups_a = canary.select_four_complete_stage7_val_pairs(rows)
    selected_b, groups_b = canary.select_four_complete_stage7_val_pairs(list(reversed(rows)))

    assert groups_a == groups_b
    assert len(groups_a) == 4
    assert len(selected_a) == len(selected_b) == 8
    assert [row.scenario_id for row in selected_a] == [
        row.scenario_id for row in selected_b
    ]
    assert {row.group_id for row in selected_a} == set(groups_a)
    assert all(sum(row.group_id == group for row in selected_a) == 2 for group in groups_a)


def test_pair_selection_fails_closed_on_incomplete_validation_pair():
    rows = complete_pairs()
    rows.pop()
    with pytest.raises(RuntimeError, match="Incomplete or malformed"):
        canary.select_four_complete_stage7_val_pairs(rows)


def test_capture_validation_accepts_exact_finite_float16_contract():
    result = canary.validate_capture_arrays(**valid_capture_arrays())
    assert result == {
        "eval_shape": [8, 2, 5],
        "definition_shape": [3, 28, 2, 5],
    }


@pytest.mark.parametrize("failure", ["nan", "too_long", "bad_hash", "float32"])
def test_capture_validation_fails_closed(failure: str):
    arrays = valid_capture_arrays()
    if failure == "nan":
        arrays["eval_mean"][0, 0, 0] = np.nan
    elif failure == "too_long":
        arrays["definition_token_counts"][0, 0] = 513
    elif failure == "bad_hash":
        arrays["eval_token_hashes"][0] = "not-a-sha256"
    elif failure == "float32":
        arrays["definition_last"] = arrays["definition_last"].astype(np.float32)
    with pytest.raises(RuntimeError):
        canary.validate_capture_arrays(**arrays)


def test_atomic_json_receipt_round_trip_and_no_overwrite(tmp_path: Path):
    path = tmp_path / "receipt.json"
    payload = {
        "status": "CANARY_PASS",
        "claim_eligible": False,
        "licensing_status": "NOT_LICENSED_CANARY_ONLY",
    }
    verification = canary.atomic_write_json(path, payload)

    assert verification["status"] == (
        "ATOMIC_JSON_WRITE_PREPUBLISH_AND_FINAL_REOPEN_VERIFIED"
    )
    assert verification["sha256"] == canary.sha256_file(path)
    assert canary.read_json(path) == payload
    with pytest.raises(FileExistsError):
        canary.atomic_write_json(path, payload)
