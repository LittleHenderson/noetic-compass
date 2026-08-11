from __future__ import annotations

import importlib.util
from pathlib import Path

from cas_forex.account_chat_truth import (
    compose_active_account_chat_reply,
    project_active_account_chat_truth,
)


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "redteam_active_account_chat_truth.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redteam_active_account_chat_truth",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _active_report() -> dict:
    return {
        "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
        "objective_account_established": True,
        "authoritative_account_source": "mt5_account_snapshot",
        "account": {
            "login": 1000694,
            "server": "Hugosway-Demo",
            "is_demo": True,
            "balance_usd": 45080.90,
            "equity_usd": 45110.36,
            "floating_pnl_usd": 29.46,
            "position_price_pnl_usd": 32.71,
            "open_swap_usd": -3.25,
            "open_commission_usd": 0.0,
            "unattributed_open_pnl_usd": 0.0,
        },
        "open_exposure": {"open_position_count": 6},
        "snapshot": {
            "observed_at": "2026-07-14T19:00:34+00:00",
            "age_seconds": 1.2,
            "fresh": True,
        },
        "growth_measurement": {
            "cashflow_adjusted_realized_growth_usd": -54919.10,
            "realized_today_usd": 39.41,
            "realized_month_usd": -54918.97,
            "net_external_capital_flow_usd": 100000.0,
            "current_balance_is_profit": False,
            "account_growth_reconciliation": {"reconciled": True},
            "open_pnl_decomposition": {
                "price_pnl_usd": 32.71,
                "swap_or_carry_usd": -3.25,
                "commission_usd": 0.0,
                "account_net_open_pnl_usd": 29.46,
                "unattributed_open_pnl_usd": 0.0,
            },
        },
        "secondary_simulator": {
            "scope": "SEPARATE_PAPER_SIMULATOR_EVIDENCE",
            "account": {"balance_usd": 5000.0},
        },
    }


def test_redteam_requires_cross_surface_identity_accounting_and_chat_truth(monkeypatch):
    active = _active_report()
    projection = project_active_account_chat_truth(
        active,
        simulator_evidence={
            "scope": "PAPER_SIMULATOR_PERFORMANCE",
            "honest_paper_balance_usd": 3040.87,
            "balance_growth_net_pnl_usd": 1040.87,
        },
    )
    reply = compose_active_account_chat_reply(projection)

    def fake_get(url, *, timeout):  # noqa: ARG001
        if url.endswith("/account/active"):
            body = active
        elif url.endswith("/mt5/account"):
            body = {
                "account": {"login": 1000694, "server": "Hugosway-Demo"},
                "open_position_count": 6,
            }
        elif url.endswith("/live-telemetry"):
            body = {
                "telemetry_source": "mt5_demo_account_snapshot",
                "totals": {
                    "open_position_count": 6,
                    "gross_floating_pnl": 32.71,
                    "total_swap": -3.25,
                    "total_commission": 0.0,
                    "total_open_pnl_after_costs": 29.46,
                },
                "movement_source_truth": {
                    "account_login": 1000694,
                    "account_server": "Hugosway-Demo",
                },
            }
        else:
            body = {
                "open_position_count": 6,
                "broker_truth_open_position_count": 6,
                "live_telemetry_source": "mt5_demo_account_snapshot",
                "live_movement_source_truth": {
                    "account_login": 1000694,
                    "account_server": "Hugosway-Demo",
                },
            }
        return {"http_status": 200, "elapsed_ms": 8, "body": body}

    def fake_post(url, payload, *, timeout):  # noqa: ARG001
        if "/ai-operator/" in url:
            body = {
                "chat_path_status": "LOCAL_ACTIVE_ACCOUNT_TRUTH",
                "model_attempted": False,
                "response_source": "LOCAL_RUNTIME_TRUTH",
                "active_account_truth": projection,
                "reply": reply,
                "proposed_command": None,
                "command_preview": None,
            }
        else:
            body = {
                "source": "local",
                "reply": reply,
                "proposed_command": None,
                "command_preview": None,
            }
        return {"http_status": 200, "elapsed_ms": 11, "body": body}

    monkeypatch.setattr(MODULE, "_get_json", fake_get)
    monkeypatch.setattr(MODULE, "_post_json", fake_post)

    report = MODULE.build_report("http://127.0.0.1:8765/api/forex")

    assert report["status"] == "PASS_ACTIVE_ACCOUNT_CHAT_TRUTH"
    assert all(report["invariant_checks"].values())
    assert report["surface_truth"]["briefing_broker_truth_open_position_count"] == 6
    assert report["operator_chat"]["chat_path_status"] == "LOCAL_ACTIVE_ACCOUNT_TRUTH"
    assert report["invariant_checks"][
        "repeated_active_reads_preserve_bounded_growth_truth"
    ] is True
    assert len(report["active_account_repeated_reads"]) == 2
    assert report["broker_touched"] is False
    assert report["money_moved"] is False
    assert report["settings_changed"] is False
    assert len(report["event_hash"]) == 64
