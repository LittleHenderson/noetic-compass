from __future__ import annotations

import torch

from scripts.run_open_weight_cover_ablation import (
    build_scoring_text,
    foundation_verbalizers,
    make_eraser_hook,
    parse_cover_axis,
    random_like_cover,
    select_balanced_scenarios,
    summarise_rows,
)
from scripts.probe_dataset_common import LabeledProbeScenario


def test_parse_cover_axis_keeps_declared_layer_and_hidden_bounds():
    parsed = parse_cover_axis(
        {
            "F1": {"layer": 31, "neuron_cover": ["L31N1", "L31N2", "L30N3", "L31N99"]},
            "F2": {"layer": 32, "neuron_cover": ["L32N4", "bad", "L32N4"]},
        },
        hidden_size=10,
    )

    assert parsed == {"F1": [(31, 1), (31, 2)], "F2": [(32, 4)]}


def test_eraser_hook_suppresses_coordinates_without_mutating_input():
    output = torch.ones((1, 3, 5))
    hook = make_eraser_hook([1, 3], gain=1.0)

    modified = hook(None, None, output)

    assert torch.equal(output, torch.ones((1, 3, 5)))
    assert modified[0, :, 1].tolist() == [0.0, 0.0, 0.0]
    assert modified[0, :, 3].tolist() == [0.0, 0.0, 0.0]
    assert modified[0, :, 0].tolist() == [1.0, 1.0, 1.0]


def test_random_like_cover_preserves_layer_counts():
    class TinyRng:
        def sample(self, population, count):
            return list(population)[:count]

    coords = [(11, 1), (11, 2), (31, 9)]

    assert random_like_cover(coords, hidden_size=5, rng=TinyRng()) == [(11, 0), (11, 1), (31, 0)]


def test_build_scoring_text_uses_plain_label_verbalizer():
    prompt, continuation = build_scoring_text("A person needs consent.", "drive", "F5")

    assert prompt.endswith("The CAS drive most expressed here is:")
    assert continuation == " F5 Agency, choice, consent, responsibility, and control."


def test_build_scoring_text_supports_28_foundation_labels():
    prompt, continuation = build_scoring_text("A person needs consent.", "foundation", "F5|A")

    assert prompt.endswith("The CAS foundation most expressed here is:")
    assert continuation == (
        " F5|A Agency, choice, consent, responsibility, and control in the analytical register."
    )
    assert len(foundation_verbalizers()) == 28


def test_select_balanced_scenarios_round_robins_by_axis_label():
    scenarios = [
        LabeledProbeScenario(f"id-{idx}", "prompt", {"drive": label})
        for idx, label in enumerate(["F7", "F7", "F7", "F1", "F1", "F2"])
    ]

    selected = select_balanced_scenarios(scenarios, axis="drive", limit=5)

    assert [item.labels["drive"] for item in selected] == ["F1", "F2", "F7", "F1", "F7"]


def test_summarise_rows_reports_target_vs_controls():
    summary = summarise_rows(
        [
            {
                "target_drop": 3.0,
                "random_mean_drop": 1.0,
                "wrong_drop": 0.5,
                "target_drop_minus_random_mean": 2.0,
                "target_drop_minus_wrong_drop": 2.5,
            },
            {
                "target_drop": 1.0,
                "random_mean_drop": 2.0,
                "wrong_drop": 0.5,
                "target_drop_minus_random_mean": -1.0,
                "target_drop_minus_wrong_drop": 0.5,
            },
        ]
    )

    assert summary["evaluated_rows"] == 2
    assert summary["mean_target_drop"] == 2.0
    assert summary["mean_target_drop_minus_random"] == 0.5
    assert summary["target_drop_beats_random_mean_rows"] == 1
    assert summary["target_drop_beats_wrong_rows"] == 2
