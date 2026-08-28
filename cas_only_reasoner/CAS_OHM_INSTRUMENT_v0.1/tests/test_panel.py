"""The instrument panel: the paper's restrictions as executable rules."""

import pytest

from panel.asom import classify
from panel.calibrate import fit_effective_resistance, validate
from panel.panel import demo_run, run
from panel.protocol import (ProtocolError, make_manifest, synthetic_series)
from panel.report import RESTRICTIONS, format_report


def test_splits_must_be_disjoint():
    with pytest.raises(ProtocolError):
        make_manifest("p", [0, 1], [1, 2], [1.0, 1.0], [0.5, 0.5])


def test_indices_must_be_in_range():
    with pytest.raises(ProtocolError):
        make_manifest("p", [0], [9], [1.0], [0.5])


def test_synthetic_source_is_labeled():
    doses, responses = synthetic_series("profile_demo")
    manifest = make_manifest("profile_demo", [0], [1], doses, responses)
    assert manifest["source"] == "synthetic_mock"


def test_calibration_is_profile_specific_and_split_only():
    result = demo_run()
    assert result["calibration"]["fitted_on_indices"] == [0, 1, 2, 3, 4, 5]
    assert result["manifest"]["validation_indices"] == [6, 7, 8, 9, 10, 11]
    assert "no live calibration" in result["calibration"]["note"]


def test_residuals_rank_only_never_identify():
    result = demo_run()
    assert result["validation"]["residuals_rank_follow_up_probes"] is True
    assert result["validation"]["residuals_identify_causes"] is False


def test_asom_keeps_region_and_outcome_independent():
    assert classify("active", "correct") == "Aligned"
    assert classify("active", "incorrect") == "Misaligned"
    assert classify("active", "off_axis") == "Misaligned"
    assert classify("saturation", "correct") == "Oversaturated"
    assert classify("saturation", "incorrect") == "Misaligned"
    assert classify("cutoff", "correct") == "Starved"


def test_active_does_not_mean_intelligent():
    # An active but WRONG response is Misaligned, never Aligned.
    assert classify("active", "incorrect") != "Aligned"


def test_report_prints_every_restriction():
    text = format_report(demo_run())
    for restriction in RESTRICTIONS:
        assert restriction in text
    assert "Live calibration admitted: NO" in text
    assert "Causal claims made: NONE" in text
    assert "Attention measured: NO" in text
    assert "Controlled experiments: PENDING" in text
    assert "synthetic_mock" in text


def test_panel_is_deterministic():
    a = format_report(demo_run())
    b = format_report(demo_run())
    assert a == b


def test_manifest_digest_seals_the_protocol():
    result = demo_run()
    assert result["manifest"]["digest"]
