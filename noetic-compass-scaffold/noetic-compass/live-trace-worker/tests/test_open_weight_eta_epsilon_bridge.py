from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_open_weight_eta_epsilon_bridge import (
    base_prompt,
    canonical_foundation,
    condition_prefix,
    interpret_bridge_status,
    key_comparisons,
    load_stage7_scenario_meta,
    parse_foundation_label,
    select_stage7_bridge_indices,
    split_from_scenario_meta,
    summarize_correctness_buckets,
    summarize_conditions,
)


def test_foundation_labels_accept_original_and_worker_forms():
    assert canonical_foundation("F1T") == "F1|T"
    assert canonical_foundation("F7|E") == "F7|E"
    assert parse_foundation_label("F3f") == (3, "f")
    assert canonical_foundation("drive") == ""


def test_condition_prefix_preserves_original_stage7_controls():
    gold = "F1|T"
    probe = "F2|A"
    partner = "F3|f"

    assert condition_prefix("none", gold, probe, partner) == ""
    assert condition_prefix("gold_raw", gold, probe, partner) == "CAS frame: F1|T.\n"
    assert "Foundation code: F2|A" in condition_prefix("probe_readable", gold, probe, partner)
    assert "Foundation code: F3|f" in condition_prefix("partner_readable", gold, probe, partner)
    assert base_prompt("A is one role. Focus: A.").endswith("The focused role is about")


def test_stage7_selection_uses_test_same_register_drive_cycle_rows_only(tmp_path: Path):
    scenario_path = tmp_path / "stage7.json"
    scenarios = []
    scenario_ids = []
    labels = []
    for drive in range(1, 8):
        next_drive = 1 if drive == 7 else drive + 1
        sid = f"cycle-{drive}"
        scenario_ids.append(sid)
        labels.append(f"F{drive}|T")
        scenarios.append(
            {
                "id": sid,
                "prompt": f"A is drive {drive}; B is drive {next_drive}. Focus: A.",
                "expected_cas_axes": {
                    "drive": f"F{drive}",
                    "register": "T",
                    "foundation": f"F{drive}|T",
                },
                "metadata": {
                    "split": "test",
                    "foundation": f"F{drive}|T",
                    "foundation_label": f"F{drive}T",
                    "contrast_partner_foundation": f"F{next_drive}T",
                    "pair_kind": "same_register_drive_cycle_T",
                },
            }
        )
        ignored_sid = f"same-drive-{drive}"
        scenario_ids.append(ignored_sid)
        labels.append(f"F{drive}|A")
        scenarios.append(
            {
                "id": ignored_sid,
                "prompt": "Ignored row.",
                "expected_cas_axes": {
                    "drive": f"F{drive}",
                    "register": "A",
                    "foundation": f"F{drive}|A",
                },
                "metadata": {
                    "split": "test",
                    "foundation": f"F{drive}|A",
                    "foundation_label": f"F{drive}A",
                    "contrast_partner_foundation": f"F{drive}T",
                    "pair_kind": "same_drive_register_T_A",
                },
            }
        )
    for split_name in ("train", "val"):
        sid = f"{split_name}-extra"
        scenario_ids.append(sid)
        labels.append("F1|T")
        scenarios.append(
            {
                "id": sid,
                "prompt": f"{split_name} row.",
                "expected_cas_axes": {"drive": "F1", "register": "T", "foundation": "F1|T"},
                "metadata": {
                    "split": split_name,
                    "foundation": "F1|T",
                    "foundation_label": "F1T",
                    "contrast_partner_foundation": "F2T",
                    "pair_kind": "same_register_drive_cycle_T",
                },
            }
        )
    scenario_path.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    meta = load_stage7_scenario_meta(scenario_path)
    scenario_id_array = np.asarray(scenario_ids)
    split = split_from_scenario_meta(scenario_id_array, meta)
    selected = select_stage7_bridge_indices(
        scenario_ids=scenario_id_array,
        labels=np.asarray(labels),
        split=split,
        scenario_meta=meta,
        per_drive=1,
        seed=11,
    )

    assert [scenario_ids[idx] for idx in selected] == [f"cycle-{drive}" for drive in range(1, 8)]


def test_bridge_status_uses_original_probe_readable_gate():
    margins = {
        "none": [0.0] * 8,
        "gold_readable": [0.6] * 8,
        "probe_readable": [0.55] * 8,
        "partner_readable": [0.1] * 8,
        "gold_raw": [0.0] * 8,
        "probe_raw": [0.0] * 8,
        "partner_raw": [0.0] * 8,
    }

    summaries = summarize_conditions(margins)
    key = key_comparisons(summaries)
    status, implication = interpret_bridge_status(summaries, key)

    assert status == "PROBE_PREDICTED_ETA_EPSILON_BRIDGE_PASS"
    assert key["probe_readable_delta_vs_none"] == 0.55
    assert "Raw CAS-symbol prefixes remain non-load-bearing" in implication


def test_correctness_buckets_expose_readout_handoff_failure_mode():
    def case(*, foundation_correct: bool, drive_correct: bool, none: float, probe: float, gold: float, partner: float):
        return {
            "foundation_correct": foundation_correct,
            "drive_correct": drive_correct,
            "condition_scores": {
                "none": {"margin": none},
                "probe_readable": {"margin": probe},
                "gold_readable": {"margin": gold},
                "partner_readable": {"margin": partner},
            },
        }

    buckets = summarize_correctness_buckets(
        [
            case(foundation_correct=True, drive_correct=True, none=0.0, probe=0.7, gold=0.7, partner=-0.1),
            case(foundation_correct=False, drive_correct=True, none=0.0, probe=0.5, gold=0.6, partner=-0.2),
            case(foundation_correct=False, drive_correct=False, none=0.0, probe=-0.3, gold=0.8, partner=-0.1),
        ]
    )

    assert buckets["foundation_correct"]["n"] == 1
    assert buckets["foundation_correct"]["probe_readable_delta_vs_none"] == 0.7
    assert buckets["drive_correct"]["n"] == 2
    assert buckets["drive_correct"]["probe_readable_delta_vs_none"] == 0.6
    assert buckets["foundation_wrong"]["n"] == 2
    assert buckets["foundation_wrong"]["probe_readable_delta_vs_none"] == 0.1
