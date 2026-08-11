"""Cross-check active MT5 account truth across cockpit and both owner chats."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "redteam-active-account-chat-truth-latest.json"
ACCOUNT_QUESTION = "What is our current account balance, P&L, and realized growth?"


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return {
            "http_status": int(response.status),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "body": json.loads(response.read().decode("utf-8")),
        }


def _post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return {
            "http_status": int(response.status),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "body": json.loads(response.read().decode("utf-8")),
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _near(left: Any, right: Any, *, tolerance: float = 0.011) -> bool:
    left_number = _number(left)
    right_number = _number(right)
    return (
        left_number is not None
        and right_number is not None
        and abs(left_number - right_number) <= tolerance
    )


def _compact_active(body: Mapping[str, Any]) -> dict[str, Any]:
    account = _mapping(body.get("account"))
    exposure = _mapping(body.get("open_exposure"))
    snapshot = _mapping(body.get("snapshot"))
    growth = _mapping(body.get("growth_measurement"))
    reconciliation = _mapping(growth.get("account_growth_reconciliation"))
    last_reconciled = _mapping(growth.get("last_reconciled_growth"))
    return {
        "status": body.get("status"),
        "source": body.get("authoritative_account_source"),
        "login": account.get("login"),
        "server": account.get("server"),
        "balance_usd": account.get("balance_usd"),
        "equity_usd": account.get("equity_usd"),
        "floating_pnl_usd": account.get("floating_pnl_usd"),
        "position_price_pnl_usd": account.get("position_price_pnl_usd"),
        "open_swap_usd": account.get("open_swap_usd"),
        "open_commission_usd": account.get("open_commission_usd"),
        "unattributed_open_pnl_usd": account.get("unattributed_open_pnl_usd"),
        "open_position_count": exposure.get("open_position_count"),
        "snapshot_observed_at": snapshot.get("observed_at"),
        "snapshot_age_seconds": snapshot.get("age_seconds"),
        "snapshot_fresh": snapshot.get("fresh"),
        "cashflow_adjusted_realized_growth_usd": growth.get(
            "cashflow_adjusted_realized_growth_usd"
        ),
        "realized_today_usd": growth.get("realized_today_usd"),
        "realized_month_usd": growth.get("realized_month_usd"),
        "net_external_capital_flow_usd": growth.get("net_external_capital_flow_usd"),
        "growth_truth_status": reconciliation.get("truth_status"),
        "growth_reconciled": reconciliation.get("reconciled"),
        "last_reconciled_available": last_reconciled.get("available"),
        "last_reconciled_generated_at": last_reconciled.get("generated_at"),
        "pending_balance_delta_usd": last_reconciled.get(
            "pending_balance_delta_usd"
        ),
    }


def _bounded_growth_truth(body: Mapping[str, Any]) -> bool:
    growth = _mapping(body.get("growth_measurement"))
    reconciliation = _mapping(growth.get("account_growth_reconciliation"))
    last_reconciled = _mapping(growth.get("last_reconciled_growth"))
    exact = bool(
        reconciliation.get("reconciled") is True
        and growth.get("cashflow_adjusted_realized_growth_usd") is not None
        and growth.get("net_external_capital_flow_usd") is not None
    )
    pending = bool(
        reconciliation.get("truth_status")
        == "PENDING_BROKER_HISTORY_RECONCILIATION"
        and last_reconciled.get("available") is True
        and last_reconciled.get("cashflow_adjusted_realized_growth_usd") is not None
        and last_reconciled.get("net_external_capital_flow_usd") is not None
        and last_reconciled.get("pending_balance_delta_usd") is not None
    )
    return exact or pending


def _reply_covers_growth_truth(reply: str) -> bool:
    low = reply.lower()
    exact = "cashflow-adjusted realized growth:" in low and "external capital" in low
    pending = bool(
        "broker-history refresh pending" in low
        and "last reconciled at" in low
        and "pending broker-history classification" in low
        and "not being guessed" in low
    )
    return exact or pending


def _request(
    fn: Any,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        return fn(*args, **kwargs)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "http_status": None,
            "elapsed_ms": None,
            "body": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_report(api_base: str, *, timeout: float = 20.0) -> dict[str, Any]:
    base = api_base.rstrip("/")
    active_response = _request(_get_json, f"{base}/account/active", timeout=timeout)
    mt5_response = _request(_get_json, f"{base}/mt5/account", timeout=timeout)
    telemetry_response = _request(_get_json, f"{base}/live-telemetry", timeout=timeout)
    briefing_response = _request(_get_json, f"{base}/operator-briefing", timeout=timeout)
    operator_response = _request(
        _post_json,
        f"{base}/ai-operator/chat",
        {"message": ACCOUNT_QUESTION},
        timeout=timeout,
    )
    assistant_response = _request(
        _post_json,
        f"{base}/assistant/chat",
        {"message": ACCOUNT_QUESTION, "history": []},
        timeout=timeout,
    )
    repeat_active_responses = [
        _request(_get_json, f"{base}/account/active", timeout=timeout)
        for _ in range(2)
    ]

    active = _mapping(active_response.get("body"))
    mt5 = _mapping(mt5_response.get("body"))
    telemetry = _mapping(telemetry_response.get("body"))
    briefing = _mapping(briefing_response.get("body"))
    operator = _mapping(operator_response.get("body"))
    assistant = _mapping(assistant_response.get("body"))
    active_account = _mapping(active.get("account"))
    active_exposure = _mapping(active.get("open_exposure"))
    mt5_account = _mapping(mt5.get("account"))
    telemetry_totals = _mapping(telemetry.get("totals"))
    telemetry_truth = _mapping(telemetry.get("movement_source_truth"))
    briefing_truth = _mapping(briefing.get("live_movement_source_truth"))
    operator_truth = _mapping(operator.get("active_account_truth"))
    operator_account = _mapping(operator_truth.get("account"))
    operator_exposure = _mapping(operator_truth.get("open_exposure"))
    operator_growth = _mapping(operator_truth.get("growth_measurement"))
    operator_decomposition = _mapping(operator_growth.get("open_pnl_decomposition"))

    active_internal_pnl = sum(
        float(active_account.get(key) or 0.0)
        for key in (
            "position_price_pnl_usd",
            "open_swap_usd",
            "open_commission_usd",
            "unattributed_open_pnl_usd",
        )
    )
    telemetry_internal_pnl = sum(
        float(telemetry_totals.get(key) or 0.0)
        for key in ("gross_floating_pnl", "total_swap", "total_commission")
    )
    operator_internal_pnl = sum(
        float(operator_decomposition.get(key) or 0.0)
        for key in (
            "price_pnl_usd",
            "swap_or_carry_usd",
            "commission_usd",
            "unattributed_open_pnl_usd",
        )
    )
    account_login = str(active_account.get("login") or "")
    account_server = str(active_account.get("server") or "")
    expected_count = int(active_exposure.get("open_position_count") or 0)
    required_reply_labels = (
        "Current active execution account:",
        "Net open P&L after reported costs",
        "price P&L",
        "swap/carry",
        "commission",
        "Secondary evidence stays separate:",
        "Neither is added to the active MT5 account.",
    )
    operator_reply = str(operator.get("reply") or "")
    assistant_reply = str(assistant.get("reply") or "")

    responses = {
        "active_account": active_response,
        "mt5_account": mt5_response,
        "live_telemetry": telemetry_response,
        "operator_briefing": briefing_response,
        "operator_chat": operator_response,
        "assistant_chat": assistant_response,
        "active_account_repeat_1": repeat_active_responses[0],
        "active_account_repeat_2": repeat_active_responses[1],
    }
    checks = {
        "all_http_200": all(
            response.get("http_status") == 200 for response in responses.values()
        ),
        "active_mt5_account_established": (
            active.get("objective_account_established") is True
            and active.get("authoritative_account_source") == "mt5_account_snapshot"
            and bool(account_login)
            and bool(account_server)
        ),
        "account_identity_agrees": (
            str(mt5_account.get("login") or "") == account_login
            and str(mt5_account.get("server") or "") == account_server
            and str(telemetry_truth.get("account_login") or "") == account_login
            and str(telemetry_truth.get("account_server") or "") == account_server
            and str(briefing_truth.get("account_login") or "") == account_login
            and str(briefing_truth.get("account_server") or "") == account_server
            and str(operator_account.get("login") or "") == account_login
            and str(operator_account.get("server") or "") == account_server
        ),
        "position_count_agrees": (
            int(mt5.get("open_position_count") or 0) == expected_count
            and int(telemetry_totals.get("open_position_count") or 0) == expected_count
            and int(briefing.get("open_position_count") or 0) == expected_count
            and int(briefing.get("broker_truth_open_position_count") or 0) == expected_count
            and int(operator_exposure.get("open_position_count") or 0) == expected_count
        ),
        "active_open_pnl_reconciles": _near(
            active_internal_pnl,
            active_account.get("floating_pnl_usd"),
        ),
        "telemetry_open_pnl_reconciles": _near(
            telemetry_internal_pnl,
            telemetry_totals.get("total_open_pnl_after_costs"),
        ),
        "operator_open_pnl_reconciles": _near(
            operator_internal_pnl,
            operator_decomposition.get("account_net_open_pnl_usd"),
        ),
        "operator_uses_bounded_account_truth": (
            operator.get("chat_path_status") == "LOCAL_ACTIVE_ACCOUNT_TRUTH"
            and operator.get("model_attempted") is False
            and operator.get("response_source") == "LOCAL_RUNTIME_TRUTH"
            and operator_truth.get("report_kind") == "cas_forex_active_account_chat_truth"
        ),
        "assistant_uses_local_account_truth": assistant.get("source") == "local",
        "operator_reply_covers_required_facts": (
            account_login in operator_reply
            and all(label in operator_reply for label in required_reply_labels)
            and _reply_covers_growth_truth(operator_reply)
        ),
        "assistant_reply_covers_required_facts": (
            account_login in assistant_reply
            and all(label in assistant_reply for label in required_reply_labels)
            and _reply_covers_growth_truth(assistant_reply)
        ),
        "realized_growth_is_cashflow_adjusted": (
            _bounded_growth_truth(active)
            and operator_growth.get("current_balance_is_profit") is False
            and (
                operator_growth.get("account_growth_reconciled") is True
                or _mapping(operator_growth.get("last_reconciled_growth")).get(
                    "available"
                )
                is True
            )
        ),
        "repeated_active_reads_preserve_bounded_growth_truth": all(
            _bounded_growth_truth(_mapping(response.get("body")))
            for response in repeat_active_responses
        ),
        "secondary_evidence_not_authoritative": (
            _mapping(operator_truth.get("secondary_evidence")).get(
                "authoritative_for_active_account"
            )
            is False
        ),
        "no_chat_command_or_money_side_effect": (
            operator.get("proposed_command") is None
            and operator.get("command_preview") is None
            and assistant.get("proposed_command") is None
            and assistant.get("command_preview") is None
        ),
    }
    passed = all(checks.values())
    report: dict[str, Any] = {
        "report_kind": "cas_forex_redteam_active_account_chat_truth",
        "status": (
            "PASS_ACTIVE_ACCOUNT_CHAT_TRUTH"
            if passed
            else "FAIL_ACTIVE_ACCOUNT_CHAT_TRUTH"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base": base,
        "question": ACCOUNT_QUESTION,
        "active_account": _compact_active(active),
        "active_account_repeated_reads": [
            _compact_active(_mapping(response.get("body")))
            for response in repeat_active_responses
        ],
        "surface_truth": {
            "mt5_open_position_count": mt5.get("open_position_count"),
            "telemetry_open_position_count": telemetry_totals.get("open_position_count"),
            "briefing_open_position_count": briefing.get("open_position_count"),
            "briefing_broker_truth_open_position_count": briefing.get(
                "broker_truth_open_position_count"
            ),
            "telemetry_source": telemetry.get("telemetry_source"),
            "briefing_source": briefing.get("live_telemetry_source"),
        },
        "operator_chat": {
            "http_status": operator_response.get("http_status"),
            "elapsed_ms": operator_response.get("elapsed_ms"),
            "chat_path_status": operator.get("chat_path_status"),
            "response_source": operator.get("response_source"),
            "model_attempted": operator.get("model_attempted"),
            "truth_fingerprint": operator_truth.get("evidence_fingerprint"),
            "reply": operator_reply,
        },
        "assistant_chat": {
            "http_status": assistant_response.get("http_status"),
            "elapsed_ms": assistant_response.get("elapsed_ms"),
            "source": assistant.get("source"),
            "reply": assistant_reply,
        },
        "invariant_checks": checks,
        "broker_touched": False,
        "money_moved": False,
        "settings_changed": False,
        "claim_boundary": (
            "This no-touch artifact proves only that these exact cockpit and chat "
            "reads agreed on the current active account and that both chats explained "
            "its after-cost accounting. It issued no order, command, transfer, or "
            "settings mutation and does not prove future profitability."
        ),
    }
    hash_input = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    report["event_hash"] = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8765/api/forex")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.api_base, timeout=args.timeout)
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_ACTIVE_ACCOUNT_CHAT_TRUTH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
