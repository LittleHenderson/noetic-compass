"""MT5 paper/demo execution verifier for CAS Forex.

This verifier proves the MT5 order path in layers:

1. connect to the local MT5 demo account,
2. build the exact MT5 request shape from a CAS BrokerOrderRequest,
3. optionally run MT5 order_check when the terminal exposes it,
4. only send a demo order when both explicit execution flags are true.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from cas_forex import mt5_connect_guard
from cas_forex.broker.mt5_bridge import MT5Bridge
from cas_forex.config import config
from cas_forex.instruments import pip_multiplier, resolve_broker_symbol, round_price
from cas_forex.mt5_terminal_api_verifier import build_mt5_terminal_api_verifier_report
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderStatus
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MT5_DEPS = REPO_ROOT / ".mt5deps"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt5_paper_execution_verifier"
REPORT_KIND = "cas_forex_mt5_paper_execution_verifier_report"
VERIFIER_SCHEMA = "cas_forex_mt5_paper_execution_verifier.v1"
CLAIM_BOUNDARY = (
    "MT5 paper execution verifier proves the MT5 demo/paper order path. It "
    "does not place live broker orders, create broker ACCEPT, deposit, "
    "withdraw, move bank/card funds, automate payouts, or override runtime "
    "gates. A demo order is sent only when execute_demo_order and "
    "confirm_demo_order are both true."
)


class MT5PaperExecutionVerifierError(ValueError):
    """Raised when MT5 paper execution verifier evidence is invalid."""


def build_mt5_paper_execution_verifier_report(
    *,
    mt5_path: Optional[Path | str] = None,
    trading_date: Optional[date | str] = None,
    symbol: str = "EUR/USD",
    direction: str | Direction = Direction.LONG,
    volume: float = 0.01,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    order_request: Optional[BrokerOrderRequest | Mapping[str, Any]] = None,
    reference_entry_price: Optional[float] = None,
    execute_demo_order: bool = False,
    confirm_demo_order: bool = False,
    close_after_send: bool = True,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    mt5_module: Any | None = None,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build one MT5 paper/demo execution verifier report."""

    _add_local_mt5_deps()
    resolved_date = date.fromisoformat(trading_date) if isinstance(trading_date, str) else trading_date or utc_now().date()
    resolved_direction = direction if isinstance(direction, Direction) else Direction(str(direction).upper())
    old_mt5_path = config.mt5_path
    old_live_mode = config.live_mode
    old_paper_trading = config.paper_trading
    if mt5_path is not None:
        config.mt5_path = str(mt5_path)
    config.live_mode = False
    config.paper_trading = True
    try:
        api_report = build_mt5_terminal_api_verifier_report(
            mt5_path=mt5_path,
            trading_date=resolved_date,
            output_dir=Path(output_dir) / "_api_probe",
            mt5_module=mt5_module,
            write_report=False,
        )
        mt5 = mt5_module or _import_mt5()
        terminal_snapshot = _connect_snapshot(mt5=mt5, mt5_path=mt5_path)
        if order_request is not None:
            order_payload, mt5_request, order_error = _build_order_request_probe(
                mt5=mt5,
                order_request=order_request,
                reference_entry_price=reference_entry_price,
            )
        else:
            order_payload, mt5_request, order_error = _build_probe_order(
                mt5=mt5,
                symbol=symbol,
                direction=resolved_direction,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
        check_result = _run_order_check(mt5, mt5_request) if mt5_request else {}
        execution_result = _execute_demo_order(
            mt5=mt5,
            order_payload=order_payload,
            execute_demo_order=execute_demo_order,
            confirm_demo_order=confirm_demo_order,
            close_after_send=close_after_send,
        ) if order_payload else {"execution_attempted": False, "reason": order_error}
    finally:
        config.mt5_path = old_mt5_path
        config.live_mode = old_live_mode
        config.paper_trading = old_paper_trading

    summary = _summary(
        api_report=api_report,
        terminal_snapshot=terminal_snapshot,
        order_payload=order_payload,
        mt5_request=mt5_request,
        check_result=check_result,
        execution_result=execution_result,
        order_error=order_error,
    )
    verifier_status = _verifier_status(
        summary=summary,
        execute_demo_order=execute_demo_order,
        confirm_demo_order=confirm_demo_order,
    )
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "verifier_status": verifier_status,
        "schema": VERIFIER_SCHEMA,
        "trading_date": resolved_date.isoformat(),
        "mt5_path": str(mt5_path) if mt5_path is not None else config.mt5_path,
        "execution_controls": {
            "execute_demo_order": bool(execute_demo_order),
            "confirm_demo_order": bool(confirm_demo_order),
            "close_after_send": bool(close_after_send),
            "live_mode_forced_off": True,
            "paper_trading_forced_on": True,
        },
        "api_verifier": _compact_api_report(api_report),
        "terminal_snapshot": terminal_snapshot,
        "order": order_payload or {},
        "mt5_request": mt5_request or {},
        "order_check": check_result,
        "execution_result": execution_result,
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(verifier_status),
        "operator_commands": _operator_commands(mt5_path),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_mt5_paper_execution_verifier_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_mt5_paper_execution_verifier_report(report)
    return report


def write_mt5_paper_execution_verifier_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt5_paper_execution_verifier_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt5-paper-execution-verifier-{stamp}-report.json"
    md_path = target_dir / f"mt5-paper-execution-verifier-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt5_paper_execution_verifier_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_mt5_paper_execution_verifier_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt5-paper-execution-verifier-*-report.json"))
    if not files:
        raise MT5PaperExecutionVerifierError(f"No MT5 paper execution verifier reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt5_paper_execution_verifier_report(payload)
    return payload


def validate_mt5_paper_execution_verifier_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "verifier_status",
        "schema",
        "trading_date",
        "execution_controls",
        "api_verifier",
        "terminal_snapshot",
        "order",
        "mt5_request",
        "order_check",
        "execution_result",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT5PaperExecutionVerifierError(f"MT5 paper execution verifier report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT5PaperExecutionVerifierError("unexpected MT5 paper execution verifier report_kind")
    if payload.get("schema") != VERIFIER_SCHEMA:
        raise MT5PaperExecutionVerifierError("unexpected MT5 paper execution verifier schema")
    if "does not place live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT5PaperExecutionVerifierError("MT5 paper execution verifier claim boundary must preserve live-order boundary")


def render_mt5_paper_execution_verifier_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex MT5 Paper Execution Verifier",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('verifier_status')}`",
        f"Trading date: `{report.get('trading_date')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- MT5 API verified: `{summary.get('mt5_api_verified')}`",
        f"- Terminal connected: `{summary.get('terminal_connected')}`",
        f"- Demo account confirmed: `{summary.get('demo_account_confirmed')}`",
        f"- Order request built: `{summary.get('order_request_built')}`",
        f"- Order check status: `{summary.get('order_check_status')}`",
        f"- Execution attempted: `{summary.get('execution_attempted')}`",
        f"- Execution status: `{summary.get('execution_status')}`",
        f"- Close attempted: `{summary.get('close_attempted')}`",
        f"- Close success: `{summary.get('close_success')}`",
        "",
        f"Next action: {report.get('next_action')}",
    ]
    return "\n".join(lines) + "\n"


def _add_local_mt5_deps() -> None:
    if LOCAL_MT5_DEPS.exists():
        path = str(LOCAL_MT5_DEPS)
        if path not in sys.path:
            sys.path.insert(0, path)


def _import_mt5() -> Any | None:
    try:
        import MetaTrader5 as mt5  # type: ignore

        return mt5
    except ImportError:
        return None


def _connect_snapshot(*, mt5: Any | None, mt5_path: Optional[Path | str]) -> Dict[str, Any]:
    if mt5 is None:
        return {"mt5_package_available": False, "initialize_ok": False, "terminal": {}, "account": {}, "positions": []}
    kwargs: Dict[str, Any] = {}
    path = str(mt5_path or config.mt5_path or "")
    if path:
        kwargs["path"] = path
    try:
        terminal = _object_to_dict(mt5.terminal_info())
        if not terminal or not bool(terminal.get("connected")):
            mt5_connect_guard.guarded_initialize(mt5, **kwargs)
            terminal = _object_to_dict(mt5.terminal_info())
        account = _object_to_dict(mt5.account_info())
        positions = [_object_to_dict(position) for position in (mt5.positions_get() or [])]
        return {
            "mt5_package_available": True,
            "initialize_ok": bool(terminal),
            "terminal": _terminal_info_snapshot(terminal),
            "account": _redacted_account_snapshot(account),
            "demo_account_confirmed": _is_demo_account(mt5, account),
            "positions": [_position_snapshot(position) for position in positions],
            "positions_sha256": _sha256_json(positions),
        }
    except Exception as exc:
        return {
            "mt5_package_available": True,
            "initialize_ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
            "terminal": {},
            "account": {},
            "positions": [],
            "demo_account_confirmed": False,
        }


def _build_probe_order(
    *,
    mt5: Any | None,
    symbol: str,
    direction: Direction,
    volume: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None, str | None]:
    if mt5 is None:
        return None, None, "MetaTrader5 Python package is unavailable."
    resolution = resolve_broker_symbol(
        symbol,
        broker=mt5,
        overrides=getattr(config, "mt5_symbol_overrides", ""),
    )
    if not resolution.selected_symbol:
        return None, None, resolution.detail or f"MT5 symbol unresolved for {symbol}."
    mt5_symbol = resolution.selected_symbol
    price = _current_price(mt5, mt5_symbol, direction)
    if price is None or price <= 0:
        return None, None, f"No usable MT5 tick price for {mt5_symbol}."
    resolved_sl, resolved_tp = _default_sl_tp(symbol, direction, price, stop_loss, take_profit)
    try:
        order = BrokerOrderRequest(
            order_id=f"mt5-paper-exec-{utc_now().strftime('%Y%m%d%H%M%S')}",
            decision_ref="mt5-paper-execution-verifier",
            symbol=symbol,
            direction=direction,
            volume=volume,
            price=price,
            stop_loss=resolved_sl,
            take_profit=resolved_tp,
            comment="CAS_MT5_VERIFY",
        )
        bridge = MT5Bridge()
        bridge._mt5 = mt5
        bridge._connected = True
        mt5_request = bridge._build_mt5_request(order)
        return order.model_dump(mode="json"), mt5_request, None
    except Exception as exc:
        return None, None, str(exc)


def _build_order_request_probe(
    *,
    mt5: Any | None,
    order_request: BrokerOrderRequest | Mapping[str, Any],
    reference_entry_price: Optional[float],
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None, str | None]:
    if mt5 is None:
        return None, None, "MetaTrader5 Python package is unavailable."
    try:
        order = (
            order_request
            if isinstance(order_request, BrokerOrderRequest)
            else BrokerOrderRequest.model_validate(dict(order_request))
        )
        resolution = resolve_broker_symbol(
            order.symbol,
            broker=mt5,
            overrides=getattr(config, "mt5_symbol_overrides", ""),
        )
        if not resolution.selected_symbol:
            return None, None, resolution.detail or f"MT5 symbol unresolved for {order.symbol}."
        mt5_symbol = resolution.selected_symbol
        current_price = _current_price(mt5, mt5_symbol, order.direction)
        if order.price <= 0:
            if current_price is None or current_price <= 0:
                return None, None, f"No usable MT5 tick price for {mt5_symbol}."
            order = _market_order_with_current_geometry(
                order,
                current_price=current_price,
                reference_entry_price=reference_entry_price,
            )
        bridge = MT5Bridge()
        bridge._mt5 = mt5
        bridge._connected = True
        mt5_request = bridge._build_mt5_request(order)
        return order.model_dump(mode="json"), mt5_request, None
    except Exception as exc:
        return None, None, str(exc)


def _market_order_with_current_geometry(
    order: BrokerOrderRequest,
    *,
    current_price: float,
    reference_entry_price: Optional[float],
) -> BrokerOrderRequest:
    """Move an agent market-order SL/TP shape onto the current broker tick."""

    ref = _positive_float(reference_entry_price) or _infer_reference_entry(order)
    pip = 1.0 / pip_multiplier(order.symbol)
    if ref is not None and ref > 0:
        stop_distance = abs(ref - float(order.stop_loss))
        take_distance = abs(float(order.take_profit) - ref)
    else:
        stop_distance = 20.0 * pip
        take_distance = 30.0 * pip
    stop_distance = max(stop_distance, 3.0 * pip)
    take_distance = max(take_distance, 1.0 * pip)
    price = round_price(order.symbol, current_price)
    if order.direction == Direction.LONG:
        stop_loss = round_price(order.symbol, price - stop_distance)
        take_profit = round_price(order.symbol, price + take_distance)
    else:
        stop_loss = round_price(order.symbol, price + stop_distance)
        take_profit = round_price(order.symbol, price - take_distance)
    return order.model_copy(
        update={
            "price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
    )


def _infer_reference_entry(order: BrokerOrderRequest) -> Optional[float]:
    if order.price > 0:
        return float(order.price)
    if order.direction == Direction.LONG and order.stop_loss < order.take_profit:
        return (float(order.stop_loss) + float(order.take_profit)) / 2.0
    if order.direction == Direction.SHORT and order.take_profit < order.stop_loss:
        return (float(order.take_profit) + float(order.stop_loss)) / 2.0
    return None


def _positive_float(value: Optional[float]) -> Optional[float]:
    try:
        parsed = float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    return parsed if parsed is not None and parsed > 0 else None


def _run_order_check(mt5: Any | None, mt5_request: Mapping[str, Any] | None) -> Dict[str, Any]:
    if mt5 is None or not mt5_request:
        return {"attempted": False, "status": "NOT_AVAILABLE"}
    method = getattr(mt5, "order_check", None)
    if method is None:
        return {"attempted": False, "status": "METHOD_MISSING"}
    try:
        result = method(dict(mt5_request))
        payload = _object_to_dict(result)
        retcode = payload.get("retcode")
        ok_codes = {0, getattr(mt5, "TRADE_RETCODE_DONE", None), getattr(mt5, "TRADE_RETCODE_PLACED", None)}
        ok_codes.discard(None)
        return {
            "attempted": True,
            "status": "ORDER_CHECK_OK" if retcode in ok_codes else "ORDER_CHECK_REJECTED",
            "retcode": retcode,
            "comment": payload.get("comment"),
            "payload": payload,
            "raw_response_hash": _sha256_json(payload),
        }
    except Exception as exc:
        return {"attempted": True, "status": "ORDER_CHECK_ERROR", "error_type": type(exc).__name__, "message": str(exc)}


def _execute_demo_order(
    *,
    mt5: Any | None,
    order_payload: Mapping[str, Any] | None,
    execute_demo_order: bool,
    confirm_demo_order: bool,
    close_after_send: bool,
) -> Dict[str, Any]:
    if not execute_demo_order:
        return {"execution_attempted": False, "status": "DRY_RUN_NO_ORDER_SENT"}
    if not confirm_demo_order:
        return {"execution_attempted": False, "status": "SEND_NOT_CONFIRMED"}
    if mt5 is None or not order_payload:
        return {"execution_attempted": False, "status": "ORDER_UNAVAILABLE"}
    bridge = MT5Bridge()
    bridge._mt5 = mt5
    bridge._connected = True
    order = BrokerOrderRequest.model_validate(dict(order_payload))
    outcome = bridge.execute_order(order)
    outcome_payload = outcome.model_dump(mode="json")
    close_attempted = False
    close_success = False
    if close_after_send and outcome.broker_ticket is not None:
        close_attempted = True
        close_success = bridge.close_position(int(outcome.broker_ticket))
    return {
        "execution_attempted": True,
        "status": f"ORDER_{outcome.status.value}",
        "outcome": outcome_payload,
        "close_attempted": close_attempted,
        "close_success": close_success,
    }


def _summary(
    *,
    api_report: Mapping[str, Any],
    terminal_snapshot: Mapping[str, Any],
    order_payload: Mapping[str, Any] | None,
    mt5_request: Mapping[str, Any] | None,
    check_result: Mapping[str, Any],
    execution_result: Mapping[str, Any],
    order_error: str | None,
) -> Dict[str, Any]:
    api_summary = api_report.get("summary") if isinstance(api_report.get("summary"), Mapping) else {}
    terminal = terminal_snapshot.get("terminal") if isinstance(terminal_snapshot.get("terminal"), Mapping) else {}
    account = terminal_snapshot.get("account") if isinstance(terminal_snapshot.get("account"), Mapping) else {}
    outcome = execution_result.get("outcome") if isinstance(execution_result.get("outcome"), Mapping) else {}
    return {
        "mt5_api_verified": api_report.get("verifier_status") == "MT5_API_VERIFIER_BROKER_API_VERIFIED",
        "api_verifier_status": api_report.get("verifier_status"),
        "terminal_connected": bool(terminal.get("connected")),
        "terminal_name": terminal.get("name") or api_summary.get("terminal_name"),
        "terminal_trade_allowed": bool(terminal.get("trade_allowed")),
        "server": account.get("server") or api_summary.get("server"),
        "demo_account_confirmed": bool(terminal_snapshot.get("demo_account_confirmed")),
        "account_snapshot_present": bool(account),
        "account_balance": account.get("balance") or api_summary.get("account_balance"),
        "account_equity": account.get("equity") or api_summary.get("account_equity"),
        "open_position_count_before": len(terminal_snapshot.get("positions") or []),
        "order_request_built": bool(order_payload and mt5_request),
        "order_error": order_error,
        "symbol": (order_payload or {}).get("symbol"),
        "direction": (order_payload or {}).get("direction"),
        "volume": (order_payload or {}).get("volume"),
        "raw_request_hash": _sha256_json(mt5_request or {}),
        "order_check_attempted": bool(check_result.get("attempted")),
        "order_check_status": check_result.get("status"),
        "execution_attempted": bool(execution_result.get("execution_attempted")),
        "execution_status": execution_result.get("status"),
        "execution_error_message": outcome.get("error_message"),
        "broker_ticket": outcome.get("broker_ticket"),
        "filled_price": outcome.get("filled_price"),
        "close_attempted": bool(execution_result.get("close_attempted")),
        "close_success": bool(execution_result.get("close_success")),
        "raw_response_hash": outcome.get("raw_response_hash"),
        "live_mode_used": False,
    }


def _verifier_status(*, summary: Mapping[str, Any], execute_demo_order: bool, confirm_demo_order: bool) -> str:
    if not summary.get("mt5_api_verified"):
        return "MT5_PAPER_EXECUTION_BLOCKED_BY_API_VERIFIER"
    if not summary.get("terminal_connected"):
        return "MT5_PAPER_EXECUTION_TERMINAL_DISCONNECTED"
    if not summary.get("demo_account_confirmed"):
        return "MT5_PAPER_EXECUTION_BLOCKED_NON_DEMO_ACCOUNT"
    if not summary.get("order_request_built"):
        return "MT5_PAPER_EXECUTION_ORDER_BUILD_FAILED"
    if execute_demo_order and not confirm_demo_order:
        return "MT5_PAPER_EXECUTION_SEND_NOT_CONFIRMED"
    if not execute_demo_order:
        if summary.get("order_check_status") == "ORDER_CHECK_REJECTED":
            return "MT5_PAPER_EXECUTION_DRY_RUN_CHECK_REJECTED"
        return "MT5_PAPER_EXECUTION_DRY_RUN_READY"
    if summary.get("execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"}:
        return "MT5_PAPER_EXECUTION_DEMO_ORDER_EXECUTED"
    if summary.get("execution_status") == "ORDER_PENDING":
        return "MT5_PAPER_EXECUTION_DEMO_ORDER_PENDING"
    return "MT5_PAPER_EXECUTION_DEMO_ORDER_REJECTED"


def _next_action(status: str) -> str:
    if status == "MT5_PAPER_EXECUTION_DRY_RUN_READY":
        return "Dry-run MT5 paper/demo request path is ready. To send one demo order, rerun with --execute-demo-order --confirm-demo-order after confirming the MT5 terminal allows demo trading."
    if status == "MT5_PAPER_EXECUTION_SEND_NOT_CONFIRMED":
        return "Add --confirm-demo-order if you intentionally want this verifier to send one MT5 demo order."
    if status == "MT5_PAPER_EXECUTION_DEMO_ORDER_EXECUTED":
        return "Demo order path executed; rerun receipt/history ingest, memory, daily rollup, and terminal operability."
    if status == "MT5_PAPER_EXECUTION_DEMO_ORDER_REJECTED":
        return "Demo order send reached MT5 but was rejected. If the error says AutoTrading disabled by client, turn on Algo Trading/AutoTrading in the MT5 terminal and rerun the verifier."
    if status == "MT5_PAPER_EXECUTION_BLOCKED_BY_API_VERIFIER":
        return "Resolve the MT5 terminal API verifier first so account state is broker/API verified."
    if status == "MT5_PAPER_EXECUTION_BLOCKED_NON_DEMO_ACCOUNT":
        return "Log into an MT5 demo account before using this verifier for paper/demo execution."
    if status == "MT5_PAPER_EXECUTION_ORDER_BUILD_FAILED":
        return "Fix symbol, quote, lot, stop-loss, or take-profit inputs so a valid MT5 request can be built."
    return "Inspect the verifier summary and rerun after resolving the reported execution blocker."


def _operator_commands(mt5_path: Optional[Path | str]) -> Dict[str, str]:
    path = str(mt5_path or config.mt5_path or "<MT5_TERMINAL64_EXE>")
    return {
        "dry_run": f'py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path "{path}" --summary-only',
        "demo_order": f'py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path "{path}" --execute-demo-order --confirm-demo-order --summary-only',
        "operability_refresh": "py -3.12 scripts/run_terminal_operability_verifier.py --summary-only",
    }


def _compact_api_report(api_report: Mapping[str, Any]) -> Dict[str, Any]:
    summary = api_report.get("summary") if isinstance(api_report.get("summary"), Mapping) else {}
    return {
        "verifier_status": api_report.get("verifier_status"),
        "trading_date": api_report.get("trading_date"),
        "summary": {
            "terminal_connected": summary.get("terminal_connected"),
            "broker_mode": summary.get("broker_mode"),
            "receipt_validation_status": summary.get("receipt_validation_status"),
            "server": summary.get("server"),
            "account_snapshot_present": summary.get("account_snapshot_present"),
            "open_position_count": summary.get("open_position_count"),
        },
    }


def _current_price(mt5: Any, symbol: str, direction: Direction) -> float | None:
    try:
        tick = mt5.symbol_info_tick(symbol)
    except Exception:
        tick = None
    if tick is None:
        return None
    price = getattr(tick, "ask", None) if direction == Direction.LONG else getattr(tick, "bid", None)
    try:
        return round(float(price), 5)
    except (TypeError, ValueError):
        return None


def _default_sl_tp(
    symbol: str,
    direction: Direction,
    price: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> tuple[float, float]:
    if stop_loss is not None and take_profit is not None:
        return stop_loss, take_profit
    pip = 1.0 / pip_multiplier(symbol)
    stop_distance = 20.0 * pip
    take_distance = 30.0 * pip
    if direction == Direction.LONG:
        return round(stop_loss if stop_loss is not None else price - stop_distance, 5), round(take_profit if take_profit is not None else price + take_distance, 5)
    return round(stop_loss if stop_loss is not None else price + stop_distance, 5), round(take_profit if take_profit is not None else price - take_distance, 5)


def _is_demo_account(mt5: Any, account: Mapping[str, Any]) -> bool:
    demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    if demo_const is not None and account.get("trade_mode") == demo_const:
        return True
    server = str(account.get("server") or "").lower()
    company = str(account.get("company") or "").lower()
    return "demo" in server or "demo" in company


def _terminal_info_snapshot(terminal: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "connected": bool(terminal.get("connected")),
        "name": terminal.get("name"),
        "path": terminal.get("path"),
        "data_path": terminal.get("data_path"),
        "trade_allowed": terminal.get("trade_allowed"),
        "build": terminal.get("build"),
    }


def _redacted_account_snapshot(account: Mapping[str, Any]) -> Dict[str, Any]:
    if not account:
        return {}

    def number(key: str) -> float | None:
        value = account.get(key)
        if value is None:
            return None
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    return {
        "account_id_hash": _sha256_json({"login": account.get("login"), "server": account.get("server")}),
        "server": account.get("server"),
        "company": account.get("company"),
        "currency": account.get("currency"),
        "balance": number("balance"),
        "equity": number("equity"),
        "margin": number("margin"),
        "margin_free": number("margin_free"),
        "leverage": account.get("leverage"),
        "trade_mode": account.get("trade_mode"),
    }


def _position_snapshot(position: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "ticket": position.get("ticket"),
        "symbol": position.get("symbol"),
        "type": position.get("type"),
        "volume": position.get("volume"),
        "price_open": position.get("price_open"),
        "price_current": position.get("price_current"),
        "profit": position.get("profit"),
        "comment": position.get("comment"),
        "magic": position.get("magic"),
    }


def _object_to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    data: Dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        try:
            attr = getattr(value, key)
        except Exception:
            continue
        if callable(attr):
            continue
        if isinstance(attr, (str, int, float, bool, type(None))):
            data[key] = attr
    return data


def _sha256_json(payload: Mapping[str, Any] | list[Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
