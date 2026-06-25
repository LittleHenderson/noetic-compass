"""Tests for the forex_fury_set_application primitive."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cas_forex.forex_fury_set_application import (
    DEFAULT_SET_KEY_TO_REQUEST_KEY,
    EnrichedOrderRequest,
    SetParameter,
    SetPayload,
    apply_set_to_order_request,
    build_set_payload,
    materialize_set_payload,
    parse_set_text,
)


# ---------------------------------------------------------------------------
# parse_set_text
# ---------------------------------------------------------------------------


def test_parse_set_text_empty_returns_no_parameters_no_errors():
    parameters, errors = parse_set_text("")
    assert parameters == ()
    assert errors == ()


def test_parse_set_text_skips_comment_and_blank_lines():
    text = "\n".join(
        [
            "; this is a comment",
            "",
            "Lot_Size=0.01",
            ";; another comment",
            "",
        ]
    )
    parameters, errors = parse_set_text(text)
    assert errors == ()
    assert len(parameters) == 1
    assert parameters[0].key == "Lot_Size"
    assert parameters[0].value == "0.01"
    assert parameters[0].parsed_value == pytest.approx(0.01)
    assert parameters[0].optimize_min is None
    assert parameters[0].optimize_max is None
    assert parameters[0].optimize_step is None
    assert parameters[0].optimize_flag is None


def test_parse_set_text_bare_lot_size():
    parameters, errors = parse_set_text("Lot_Size=0.01")
    assert errors == ()
    (param,) = parameters
    assert param.key == "Lot_Size"
    assert param.value == "0.01"
    assert param.parsed_value == pytest.approx(0.01)


def test_parse_set_text_optimization_tuple_with_F_flag():
    # value, min, step, max, flag (F = fixed = 0)
    parameters, errors = parse_set_text("Stop_Loss=120,30,150,200,F")
    assert errors == ()
    (param,) = parameters
    assert param.key == "Stop_Loss"
    assert param.value == "120"
    assert param.parsed_value == 120
    assert param.optimize_min == pytest.approx(30.0)
    assert param.optimize_step == pytest.approx(150.0)
    assert param.optimize_max == pytest.approx(200.0)
    assert param.optimize_flag == 0  # F -> fixed -> 0


def test_parse_set_text_unparseable_line_recorded_as_error():
    text = "no_equals_here\nLot_Size=0.02"
    parameters, errors = parse_set_text(text)
    assert len(parameters) == 1
    assert parameters[0].key == "Lot_Size"
    assert len(errors) == 1
    assert "no_equals_here" in errors[0]
    assert "line 1" in errors[0]


# ---------------------------------------------------------------------------
# build_set_payload
# ---------------------------------------------------------------------------


def test_build_set_payload_populates_parameters_by_key_lookup():
    text = "Lot_Size=0.05\nStop_Loss=120\nMaxOrders=3"
    payload = build_set_payload(
        profile_id="ff-test",
        source_set_path="/virtual/path/test.set",
        source_sha256="deadbeef",
        set_text=text,
        platform="MT5",
    )
    assert isinstance(payload, SetPayload)
    assert payload.profile_id == "ff-test"
    assert payload.platform == "MT5"
    assert len(payload.parameters) == 3
    assert payload.parameters_by_key["Lot_Size"].parsed_value == pytest.approx(0.05)
    assert payload.parameters_by_key["Stop_Loss"].parsed_value == 120
    assert payload.parameters_by_key["MaxOrders"].parsed_value == 3


# ---------------------------------------------------------------------------
# apply_set_to_order_request
# ---------------------------------------------------------------------------


def _payload_from(text: str) -> SetPayload:
    return build_set_payload(
        profile_id="ff-test",
        source_set_path="/virtual/test.set",
        source_sha256="0" * 64,
        set_text=text,
        platform="MT5",
    )


def test_apply_set_lot_size_flows_into_lots_field():
    base = {"symbol": "EURUSD", "lots": 0.01}
    payload = _payload_from("Lot_Size=0.05")
    enriched = apply_set_to_order_request(
        base_order_request=base,
        set_payload=payload,
        now=datetime(2026, 6, 25, tzinfo=UTC),
    )
    assert isinstance(enriched, EnrichedOrderRequest)
    assert enriched.base_order_request["lots"] == pytest.approx(0.05)
    assert enriched.base_order_request["symbol"] == "EURUSD"
    assert enriched.applied_overrides["lots"] == pytest.approx(0.05)
    assert enriched.applied_at_iso == "2026-06-25T00:00:00+00:00"
    assert enriched.application_errors == ()


def test_apply_set_does_not_mutate_base_order_request():
    base = {"symbol": "EURUSD", "lots": 0.01}
    snapshot = dict(base)
    payload = _payload_from("Lot_Size=0.99\nStop_Loss=42")
    enriched = apply_set_to_order_request(
        base_order_request=base,
        set_payload=payload,
    )
    assert base == snapshot, "base_order_request was mutated"
    assert enriched.base_order_request is not base
    assert enriched.base_order_request["lots"] == pytest.approx(0.99)


def test_apply_overrides_for_filters_to_named_keys_only():
    base = {"lots": 0.01, "stop_loss_pips": 9}
    payload = _payload_from("Lot_Size=0.5\nStop_Loss=42")
    enriched = apply_set_to_order_request(
        base_order_request=base,
        set_payload=payload,
        apply_overrides_for=["Stop_Loss"],
    )
    # Only Stop_Loss applied; Lot_Size left at base.
    assert enriched.base_order_request["lots"] == pytest.approx(0.01)
    assert enriched.base_order_request["stop_loss_pips"] == 42
    assert "lots" not in enriched.applied_overrides
    assert enriched.applied_overrides["stop_loss_pips"] == 42


def test_apply_multiple_parameters_flow_through_via_default_key_map():
    text = "\n".join(
        [
            "Lot_Size=0.02",
            "Stop_Loss=80",
            "Take_Profit=160",
            "MaxOrders=5",
            "Magic_Number=12345",
            "MaxSpread=3.5",
            "InpUseGrid=true",
            "TradeOnMonday=true",
            "TradeOnFriday=false",
        ]
    )
    payload = _payload_from(text)
    base = {"symbol": "EURUSD"}
    enriched = apply_set_to_order_request(
        base_order_request=base,
        set_payload=payload,
    )
    out = enriched.base_order_request
    assert out["symbol"] == "EURUSD"
    assert out["lots"] == pytest.approx(0.02)
    assert out["stop_loss_pips"] == 80
    assert out["take_profit_pips"] == 160
    assert out["max_orders"] == 5
    assert out["magic_number"] == 12345
    assert out["max_spread"] == pytest.approx(3.5)
    assert out["uses_grid"] is True
    assert out["trade_on_monday"] is True
    assert out["trade_on_friday"] is False
    # Sanity: applied_overrides covers exactly the .set-derived keys.
    expected_keys = {
        "lots",
        "stop_loss_pips",
        "take_profit_pips",
        "max_orders",
        "magic_number",
        "max_spread",
        "uses_grid",
        "trade_on_monday",
        "trade_on_friday",
    }
    assert set(enriched.applied_overrides.keys()) == expected_keys


def test_default_key_map_covers_documented_parameters():
    # Guard against silent removal of mappings the broker bridge will rely on.
    must_have = {
        "Lot_Size",
        "Stop_Loss",
        "Take_Profit",
        "InpTPRatio",
        "MaxOrders",
        "Magic_Number",
        "InpMaxTradesPerDay",
        "MaxSpread",
        "Max_Slippage",
        "InpUseGrid",
        "InpGridLevelsDistanceMultiplier",
        "InpGridVolumeMultiplier",
        "InpUseTrailingStop",
        "InpUseCostAveraging",
        "StartTradingTime",
        "EndTradingTime",
        "TradeOnMonday",
        "TradeOnTuesday",
        "TradeOnWednesday",
        "TradeOnThursday",
        "TradeOnFriday",
    }
    assert must_have.issubset(set(DEFAULT_SET_KEY_TO_REQUEST_KEY.keys()))


# ---------------------------------------------------------------------------
# materialize_set_payload
# ---------------------------------------------------------------------------


def test_materialize_set_payload_with_matching_sha256(tmp_path: Path):
    set_text = "Lot_Size=0.01\nStop_Loss=120\n"
    rel = "scratch/profile.set"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(set_text, encoding="utf-8")

    sha = hashlib.sha256(target.read_bytes()).hexdigest()

    payload, error = materialize_set_payload(
        profile_id="ff-tmp",
        source_set_path=rel,
        expected_sha256=sha,
        repo_root=tmp_path,
        platform="MT4",
    )
    assert error is None
    assert payload is not None
    assert payload.profile_id == "ff-tmp"
    assert payload.platform == "MT4"
    assert payload.source_sha256 == sha
    assert payload.parameters_by_key["Lot_Size"].parsed_value == pytest.approx(0.01)
    assert payload.parameters_by_key["Stop_Loss"].parsed_value == 120


def test_materialize_set_payload_sha256_mismatch_returns_error(tmp_path: Path):
    rel = "scratch/profile.set"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Lot_Size=0.01\n", encoding="utf-8")

    payload, error = materialize_set_payload(
        profile_id="ff-tmp",
        source_set_path=rel,
        expected_sha256="0" * 64,
        repo_root=tmp_path,
    )
    assert payload is None
    assert error == "sha256 mismatch"


def test_materialize_set_payload_missing_file_returns_error(tmp_path: Path):
    payload, error = materialize_set_payload(
        profile_id="ff-tmp",
        source_set_path="does/not/exist.set",
        expected_sha256="deadbeef",
        repo_root=tmp_path,
    )
    assert payload is None
    assert error == "set file missing"
