"""Tests for the RPM gate (uses real api/notation/compiler)."""

from __future__ import annotations

import pytest

from cas_native.belief import check_rpm_chain


def test_clean_expression_with_observation_satisfies():
    r = check_rpm_chain("practice makes perfect", "^7^O", 1)
    assert r.satisfied is True
    stages = r.status["stages"]
    assert stages["A0"]["passed"] is True
    assert stages["Dn"]["passed"] is True
    assert stages["Wn"]["passed"] is True
    assert stages["Pn"]["passed"] is True


def test_zero_observations_blocks_at_a0():
    r = check_rpm_chain("practice makes perfect", "^7^O", 0)
    assert r.satisfied is False
    stages = r.status["stages"]
    assert stages["A0"]["passed"] is False
    # Pn must not pass because A0 didn't.
    assert stages["Pn"]["passed"] is False


def test_invalid_expression_blocks_at_dn():
    r = check_rpm_chain("nonsense", "not a CAS expression", 1)
    assert r.satisfied is False
    stages = r.status["stages"]
    assert stages["A0"]["passed"] is True
    assert stages["Dn"]["passed"] is False
    assert stages["Wn"]["passed"] is False  # cascade
    assert stages["Pn"]["passed"] is False
    assert r.status["compiler_valid"] is False
    assert r.status["compiler_error"] is not None


def test_empty_expression_rejected():
    r = check_rpm_chain("foo", "", 1)
    assert r.satisfied is False
    assert r.status["compiler_valid"] is False
    assert "empty" in r.status["compiler_error"].lower()


def test_compound_register_expression_passes():
    # CAS v7.7 register-set notation.
    r = check_rpm_chain("principled refusal", "^3^P|A", 2)
    assert r.satisfied is True


def test_drive_expression_passes():
    r = check_rpm_chain("connection-driven", "^2^C_{F4}", 1)
    assert r.satisfied is True


def test_observations_count_surfaced():
    r = check_rpm_chain("foo", "^4^P", 5)
    assert r.status["observations"] == 5
    assert r.status["stages"]["A0"]["observations"] == 5


def test_pn_stage_carries_type_kind_when_clean():
    r = check_rpm_chain("foo", "^4^P", 1)
    assert "type=" in r.status["stages"]["Pn"]["reason"]
