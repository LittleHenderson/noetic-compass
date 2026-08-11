from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cas_forex.entry_capacity_pressure import (
    load_entry_capacity_pressure,
    record_entry_capacity_observation,
)


def _report(
    *,
    at: datetime,
    intent_id: str,
    symbol: str,
    blockers: list[str] | None = None,
    total_exposure_lots: float = 0.04,
    open_position_count: int = 4,
    max_open_position_count: int = 4,
) -> dict:
    blockers = (
        blockers
        if blockers is not None
        else ["open-position cap is already full (4 / 4)"]
    )
    return {
        "generated_at": at.isoformat(),
        "status": "ALL_CANDIDATES_BLOCKED_BEFORE_OPERATOR",
        "candidates": [
            {
                "intent_id": intent_id,
                "symbol": symbol,
                "timeframe": "M1",
                "direction": "LONG",
                "entry_lane": "MICRO_SCALP",
                "status": "BLOCKED_NO_COMPLIANT_SIZE",
                "minimum_lot_risk_usd": 1.25,
                "minimum_lot_risk_pct_equity": 0.0028,
                "max_feasible_lots": 1.8,
                "broker_min_lot": 0.01,
                "operator_sizing_plan": {
                    "blockers": blockers,
                    "portfolio_snapshot": {
                        "open_position_count": open_position_count,
                        "total_exposure_lots": total_exposure_lots,
                    },
                    "cap_snapshot": {
                        "max_open_position_count": max_open_position_count,
                        "max_total_exposure_lots": 2.0,
                    },
                },
            }
        ],
    }


def _record(path, report, *, now, overrides=()):
    return record_entry_capacity_observation(
        report,
        mode="PAPER_FALLBACK",
        state_path=path,
        now=now,
        control_values={
            "max_concurrent_trades": 4,
            "max_total_exposure_lots": 2.0,
        },
        control_bounds={"max_concurrent_trades": {"min": 1, "max": 50}},
        explicit_owner_override_keys=overrides,
    )


def test_repeated_cross_market_low_exposure_blocks_trigger_one_slot_review(tmp_path):
    path = tmp_path / "capacity.json"
    start = datetime(2026, 7, 14, 16, 0, tzinfo=timezone.utc)
    report = None
    for index, symbol in enumerate(("EUR/USD", "GBP/JPY", "USD/CHF")):
        now = start + timedelta(minutes=index)
        report = _record(
            path,
            _report(
                at=now,
                intent_id=f"intent-{index}",
                symbol=symbol,
            ),
            now=now,
        )

    assert report is not None
    assert report["status"] == "POSITION_CAPACITY_STARVATION"
    assert report["cap_block_event_count"] == 3
    assert report["distinct_symbol_count"] == 3
    assert report["current_open_position_count"] == 4
    assert report["current_max_open_position_count"] == 4
    assert report["exposure_utilization_pct"] == 2.0
    assert report["autonomous_one_slot_review_allowed"] is True
    assert report["recommended_review_cap"] == 5
    assert report["broker_order_touched"] is False
    assert load_entry_capacity_pressure(path)["event_hash"] == report["event_hash"]


def test_high_exposure_retains_pressure_but_does_not_invite_cap_increase(tmp_path):
    path = tmp_path / "capacity.json"
    start = datetime(2026, 7, 14, 16, 0, tzinfo=timezone.utc)
    report = None
    for index, symbol in enumerate(("EUR/USD", "GBP/JPY", "USD/CHF")):
        now = start + timedelta(minutes=index)
        report = _record(
            path,
            _report(
                at=now,
                intent_id=f"intent-{index}",
                symbol=symbol,
                total_exposure_lots=1.5,
            ),
            now=now,
        )

    assert report is not None
    assert report["status"] == "POSITION_CAPACITY_PRESSURE_OBSERVED"
    assert report["exposure_utilization_pct"] == 75.0
    assert report["autonomous_one_slot_review_allowed"] is False
    assert report["recommended_review_cap"] is None
    assert any("exposure" in reason for reason in report["review_blockers"])


def test_mixed_sizing_blockers_do_not_masquerade_as_capacity_starvation(tmp_path):
    now = datetime(2026, 7, 14, 16, 0, tzinfo=timezone.utc)
    report = _record(
        tmp_path / "capacity.json",
        _report(
            at=now,
            intent_id="intent-mixed",
            symbol="EUR/USD",
            blockers=[
                "open-position cap is already full (4 / 4)",
                "remaining total exposure is below broker minimum",
            ],
        ),
        now=now,
    )

    assert report["status"] == "NO_POSITION_CAPACITY_PRESSURE"
    assert report["cap_block_event_count"] == 0


def test_explicit_owner_concurrency_override_prevents_autonomous_review(tmp_path):
    path = tmp_path / "capacity.json"
    start = datetime(2026, 7, 14, 16, 0, tzinfo=timezone.utc)
    report = None
    for index, symbol in enumerate(("EUR/USD", "GBP/JPY", "USD/CHF")):
        now = start + timedelta(minutes=index)
        report = _record(
            path,
            _report(
                at=now,
                intent_id=f"intent-{index}",
                symbol=symbol,
            ),
            now=now,
            overrides=("max_concurrent_trades",),
        )

    assert report is not None
    assert report["status"] == "POSITION_CAPACITY_PRESSURE_OBSERVED"
    assert report["explicit_owner_override_active"] is True
    assert report["autonomous_one_slot_review_allowed"] is False
    assert any("owner" in reason for reason in report["review_blockers"])


def test_fresh_feasible_cycle_clears_stale_capacity_pressure(tmp_path):
    path = tmp_path / "capacity.json"
    start = datetime(2026, 7, 14, 16, 0, tzinfo=timezone.utc)
    for index, symbol in enumerate(("EUR/USD", "GBP/JPY", "USD/CHF")):
        now = start + timedelta(minutes=index)
        report = _record(
            path,
            _report(at=now, intent_id=f"blocked-{index}", symbol=symbol),
            now=now,
        )
    assert report["status"] == "POSITION_CAPACITY_STARVATION"

    cleared_at = start + timedelta(minutes=3)
    cleared = _record(
        path,
        _report(
            at=cleared_at,
            intent_id="fresh-feasible",
            symbol="XAU/USD",
            blockers=[],
            open_position_count=2,
        ),
        now=cleared_at,
    )

    assert cleared["status"] == "POSITION_CAPACITY_PRESSURE_CLEARED"
    assert cleared["current_open_position_count"] == 2
    assert cleared["current_max_open_position_count"] == 4
    assert cleared["current_cycle_cap_only_block_count"] == 0
    assert cleared["autonomous_one_slot_review_allowed"] is False
    assert cleared["recommended_review_cap"] is None
