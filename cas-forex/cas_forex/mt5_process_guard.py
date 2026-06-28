"""Process-level watchdog for MetaTrader 5 Python calls.

The MetaTrader5 Python package makes blocking C-extension calls into the
MT5 terminal (order_send, positions_get, history_deals_get, etc.). When
the terminal is unresponsive, these calls can hang indefinitely. This
module wraps MT5 operations in a subprocess with a configurable timeout
so a hung MT5 call cannot block the CAS Forex agent loop.

Architecture:
    Parent process: calls run_mt5_operation_safe() with an operation spec.
                    Spawns a subprocess, waits with timeout, kills on hang.
    Worker process: python -m cas_forex.mt5_process_guard --worker <spec>
                    Loads MetaTrader5, executes the operation, prints JSON.

All inter-process communication is via temp-file JSON (spec) and stdout
JSON (result). No shared state, no pickle, no multiprocessing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MT5_DEPS = REPO_ROOT / ".mt5deps"
DEFAULT_MT5_TIMEOUT_SECONDS = 120
WORKER_SPEC_SCHEMA = "cas_forex_mt5_worker_spec.v1"
WORKER_RESULT_SCHEMA = "cas_forex_mt5_worker_result.v1"


# ---------------------------------------------------------------------------
# Operation spec
# ---------------------------------------------------------------------------


@dataclass
class MT5WorkerSpec:
    """Serializable spec for one MT5 worker operation."""

    operation: str
    mt5_path: str
    params: Dict[str, Any] = field(default_factory=dict)
    schema: str = WORKER_SPEC_SCHEMA
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_mt5_operation_safe(
    *,
    mt5_path: str | Path,
    operation: str,
    params: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = DEFAULT_MT5_TIMEOUT_SECONDS,
    extra_pythonpath: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run an MT5 operation in a timeout-guarded subprocess.

    Args:
        mt5_path: Absolute path to terminal64.exe.
        operation: One of 'execute_demo_order', 'get_deal_history',
                   'get_account_snapshot', 'get_open_positions',
                   'close_position'.
        params: Operation-specific parameters (see worker code).
        timeout_seconds: Max wall time before the subprocess is killed.
        extra_pythonpath: Additional directories to prepend to PYTHONPATH
                          in the worker process.

    Returns:
        Dict with ``success`` boolean. On success, ``result`` contains
        the operation output. On failure, ``error`` and optional
        ``stderr`` / ``traceback`` describe what happened.
    """
    spec = MT5WorkerSpec(
        operation=operation,
        mt5_path=str(mt5_path),
        params=params or {},
    )

    spec_file = None
    try:
        # Write spec to a temp file so the worker can read it
        fd, spec_path = tempfile.mkstemp(suffix=".json", prefix="mt5_worker_spec_")
        os.close(fd)
        spec_file = Path(spec_path)
        spec_file.write_text(
            json.dumps(asdict(spec), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Build environment with extra pythonpath entries
        env = os.environ.copy()
        pythonpath_parts: List[str] = []
        if extra_pythonpath:
            pythonpath_parts.extend(extra_pythonpath)
        # Always include repo root, cas_forex parent, and local MT5 deps
        pythonpath_parts.append(str(REPO_ROOT))
        if LOCAL_MT5_DEPS.exists():
            pythonpath_parts.append(str(LOCAL_MT5_DEPS))
        existing = env.get("PYTHONPATH", "")
        if existing:
            pythonpath_parts.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cas_forex.mt5_process_guard",
                "--worker",
                str(spec_file),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            cwd=str(REPO_ROOT),
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                parsed = json.loads(result.stdout.strip().split("\n")[-1])
                return parsed
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "MT5_WORKER_INVALID_JSON",
                    "stdout_preview": result.stdout[:2000],
                    "stderr_preview": result.stderr[:2000],
                    "returncode": result.returncode,
                }
        else:
            return {
                "success": False,
                "error": "MT5_WORKER_FAILED",
                "stderr": result.stderr[:4000],
                "stdout": result.stdout[:2000],
                "returncode": result.returncode,
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "MT5_TIMEOUT",
            "timeout_seconds": timeout_seconds,
            "message": (
                f"MT5 operation '{operation}' did not complete within "
                f"{timeout_seconds} seconds. The worker subprocess was killed. "
                f"Check that the MT5 terminal at {mt5_path} is running, "
                f"Algo Trading / AutoTrading is enabled, and the terminal "
                f"is responsive."
            ),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "MT5_GUARD_EXCEPTION",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
    finally:
        if spec_file is not None:
            try:
                spec_file.unlink(missing_ok=True)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Worker (runs in subprocess)
# ---------------------------------------------------------------------------


def _mt5_worker(spec_path: str) -> None:
    """Load an MT5WorkerSpec from disk, execute the operation, print JSON.

    This function runs inside the timeout-guarded subprocess. It must
    NOT access any shared state from the parent process.
    """
    try:
        spec_data = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    except Exception as exc:
        _worker_fail("MT5_WORKER_SPEC_READ_ERROR", str(exc))
        return

    operation = spec_data.get("operation", "")
    mt5_path = spec_data.get("mt5_path", "")
    params = spec_data.get("params") or {}

    if not operation or not mt5_path:
        _worker_fail("MT5_WORKER_INVALID_SPEC", "Missing operation or mt5_path")
        return

    # Import MetaTrader5 inside the worker
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        _worker_fail("MT5_IMPORT_ERROR", str(exc))
        return

    # Initialize connection
    try:
        init_kwargs: Dict[str, Any] = {"path": mt5_path}
        initialized = mt5.initialize(**init_kwargs)
        if not initialized:
            error_code = mt5.last_error()
            _worker_fail(
                "MT5_INIT_FAILED",
                f"mt5.initialize() returned False. "
                f"Last error: code={error_code[0]}, message={error_code[1]}",
            )
            return
    except Exception as exc:
        _worker_fail("MT5_INIT_EXCEPTION", str(exc))
        return

    try:
        if operation == "execute_demo_order":
            result = _worker_execute_demo_order(mt5, params)
        elif operation == "get_deal_history":
            result = _worker_get_deal_history(mt5, params)
        elif operation == "get_account_snapshot":
            result = _worker_get_account_snapshot(mt5, params)
        elif operation == "get_open_positions":
            result = _worker_get_open_positions(mt5, params)
        elif operation == "close_position":
            result = _worker_close_position(mt5, params)
        else:
            _worker_fail("MT5_UNKNOWN_OPERATION", f"No worker for '{operation}'")
            return
    except Exception as exc:
        _worker_fail(
            "MT5_OPERATION_EXCEPTION",
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        return
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    # Success — print JSON to stdout for the parent to read
    result_payload = {
        "success": True,
        "schema": WORKER_RESULT_SCHEMA,
        "operation": operation,
        "mt5_path": mt5_path,
        "result": result,
        "elapsed_seconds": 0.0,  # approximate
        "timestamp": time.time(),
    }
    print(json.dumps(result_payload, default=str, ensure_ascii=False))


def _worker_fail(error: str, message: str) -> None:
    """Print a failure result and exit the worker."""
    payload = {
        "success": False,
        "schema": WORKER_RESULT_SCHEMA,
        "error": error,
        "message": str(message)[:4000],
        "timestamp": time.time(),
    }
    print(json.dumps(payload, default=str, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Worker operations
# ---------------------------------------------------------------------------


def _worker_execute_demo_order(mt5: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a demo market order via MT5, optionally close it.

    Expected params:
        symbol: str
        direction: str ("LONG" or "SHORT")
        volume: float
        stop_loss: float | None
        take_profit: float | None
        close_after_send: bool (default True)
    """
    symbol = params.get("symbol", "EUR/USD")
    direction_str = params.get("direction", "LONG")
    volume = float(params.get("volume", 0.01))
    stop_loss = params.get("stop_loss")
    take_profit = params.get("take_profit")
    close_after_send = bool(params.get("close_after_send", True))

    # Get current price
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"error": "SYMBOL_TICK_UNAVAILABLE", "symbol": symbol}

    if direction_str.upper() == "LONG":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl = round(stop_loss, _digits(mt5, symbol)) if stop_loss else 0.0
        tp = round(take_profit, _digits(mt5, symbol)) if take_profit else 0.0
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl = round(stop_loss, _digits(mt5, symbol)) if stop_loss else 0.0
        tp = round(take_profit, _digits(mt5, symbol)) if take_profit else 0.0

    # Determine filling mode
    filling_mode = _symbol_filling_mode(mt5, symbol)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 0,
        "comment": "CAS_FOREX_DEMO",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }

    # -- order_check --
    check_result = mt5.order_check(request)
    check_summary = {
        "order_check_attempted": True,
        "order_check_status": "ORDER_CHECK_OK" if check_result is not None and check_result.retcode == 0 else "ORDER_CHECK_REJECTED",
        "order_check_retcode": check_result.retcode if check_result is not None else None,
        "order_check_comment": str(check_result.comment) if check_result is not None and hasattr(check_result, "comment") else None,
    }

    # -- order_send --
    raw_result = mt5.order_send(request)
    if raw_result is None:
        return {
            "execution_status": "ORDER_REJECTED",
            "error_message": "MT5 order_send returned None",
            "order_check": check_summary,
            "close_attempted": False,
            "close_success": False,
        }

    execution_status = "ORDER_EXECUTED" if raw_result.retcode == mt5.TRADE_RETCODE_DONE else "ORDER_REJECTED"
    broker_ticket = raw_result.order if raw_result.retcode == mt5.TRADE_RETCODE_DONE else None
    filled_price = raw_result.price if raw_result.retcode == mt5.TRADE_RETCODE_DONE else None

    # -- close if requested --
    close_attempted = False
    close_success = False
    if close_after_send and broker_ticket is not None:
        close_attempted = True
        close_success = _worker_close_single_position(mt5, broker_ticket)

    return {
        "execution_status": execution_status,
        "error_message": raw_result.comment if raw_result.retcode != mt5.TRADE_RETCODE_DONE else None,
        "broker_ticket": broker_ticket,
        "filled_price": filled_price,
        "raw_retcode": raw_result.retcode,
        "raw_request_hash": _json_hash(request),
        "order_check": check_summary,
        "close_attempted": close_attempted,
        "close_success": close_success,
    }


def _worker_get_deal_history(mt5: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get deal history for a position ticket.

    Expected params:
        ticket: int | str — position ticket / order ticket
        future_minutes: int (default 120) — lookback window
    """
    ticket = int(params.get("ticket", 0))
    future_minutes = int(params.get("future_minutes", 120))

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    date_from = now - timedelta(minutes=future_minutes)
    date_to = now + timedelta(minutes=5)

    deals = mt5.history_deals_get(date_from, date_to)
    if deals is None or len(deals) == 0:
        return {
            "raw_deal_count": 0,
            "ticket_filter": str(ticket),
            "deals": [],
        }

    # Filter deals related to this ticket (position_id or order)
    ticket_deals = []
    for deal in deals:
        deal_dict = deal._asdict() if hasattr(deal, "_asdict") else {}
        deal_position_id = deal_dict.get("position_id", 0) if isinstance(deal_dict, dict) else getattr(deal, "position_id", 0)
        deal_order = deal_dict.get("order", 0) if isinstance(deal_dict, dict) else getattr(deal, "order", 0)
        if int(deal_position_id) == ticket or int(deal_order) == ticket:
            ticket_deals.append(deal_dict if isinstance(deal_dict, dict) else {
                "ticket": getattr(deal, "ticket", 0),
                "position_id": int(deal_position_id),
                "order": int(deal_order),
                "time": str(getattr(deal, "time", 0)),
                "type": int(getattr(deal, "type", 0)),
                "entry": int(getattr(deal, "entry", 0)),
                "symbol": str(getattr(deal, "symbol", "")),
                "volume": float(getattr(deal, "volume", 0.0)),
                "price": float(getattr(deal, "price", 0.0)),
                "commission": float(getattr(deal, "commission", 0.0)),
                "swap": float(getattr(deal, "swap", 0.0)),
                "profit": float(getattr(deal, "profit", 0.0)),
                "comment": str(getattr(deal, "comment", "")),
            })

    return {
        "raw_deal_count": len(ticket_deals),
        "ticket_filter": str(ticket),
        "deals": ticket_deals,
    }


def _worker_get_account_snapshot(mt5: Any, params: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG001
    """Get current MT5 account snapshot."""
    info = mt5.account_info()
    if info is None:
        return {"error": "ACCOUNT_INFO_UNAVAILABLE"}

    terminal = mt5.terminal_info()
    return {
        "login": info.login,
        "server": str(info.server),
        "balance": float(info.balance),
        "equity": float(info.equity),
        "margin": float(info.margin),
        "margin_free": float(info.margin_free),
        "trade_mode": int(info.trade_mode),
        "is_demo": int(info.trade_mode) == 0,
        "terminal_connected": terminal is not None and terminal.connected if terminal else False,
        "terminal_trade_allowed": terminal.trade_allowed if terminal else False,
    }


def _worker_get_open_positions(mt5: Any, params: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG001
    """Get all open positions."""
    positions = mt5.positions_get()
    if positions is None:
        return {"position_count": 0, "positions": []}

    result = []
    for pos in positions:
        result.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": pos.type,
            "volume": pos.volume,
            "price_open": pos.price_open,
            "sl": pos.sl,
            "tp": pos.tp,
            "price_current": pos.price_current,
            "profit": pos.profit,
            "comment": pos.comment,
        })
    return {"position_count": len(result), "positions": result}


def _worker_close_position(mt5: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Close a single position by ticket.

    Expected params:
        ticket: int — position ticket
    """
    ticket = int(params.get("ticket", 0))
    if ticket == 0:
        return {"error": "INVALID_TICKET", "ticket": ticket}

    success = _worker_close_single_position(mt5, ticket)
    return {"ticket": ticket, "close_success": success}


def _worker_close_single_position(mt5: Any, ticket: int) -> bool:
    """Close one position. Returns True on success."""
    try:
        positions = mt5.positions_get(ticket=ticket)
        if positions is None or len(positions) == 0:
            return False

        pos = positions[0]
        symbol = pos.symbol
        volume = pos.volume

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False

        # Determine close price and type
        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            close_price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            close_price = tick.ask

        filling_mode = _symbol_filling_mode(mt5, symbol)

        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "position": ticket,
            "price": close_price,
            "deviation": 20,
            "magic": 0,
            "comment": "CAS_FOREX_DEMO_CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        result = mt5.order_send(close_request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _symbol_filling_mode(mt5: Any, symbol: str) -> int:
    """Return the first available filling mode for a symbol."""
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return getattr(mt5, "ORDER_FILLING_FOK", 1)
        modes = getattr(info, "filling_mode", 0) or 0
        for mode_flag, mode_const in [
            (mt5.SYMBOL_FILLING_FOK if hasattr(mt5, "SYMBOL_FILLING_FOK") else 1, getattr(mt5, "ORDER_FILLING_FOK", 1)),
            (mt5.SYMBOL_FILLING_IOC if hasattr(mt5, "SYMBOL_FILLING_IOC") else 2, getattr(mt5, "ORDER_FILLING_IOC", 2)),
        ]:
            try:
                if modes & mode_flag:
                    return mode_const
            except Exception:
                pass
        return getattr(mt5, "ORDER_FILLING_FOK", 1)
    except Exception:
        return getattr(mt5, "ORDER_FILLING_FOK", 1)


def _digits(mt5: Any, symbol: str) -> int:
    """Return the number of decimal places for a symbol."""
    try:
        info = mt5.symbol_info(symbol)
        return info.digits if info else 5
    except Exception:
        return 5


def _json_hash(obj: Any) -> str:
    """Stable JSON hash for request verification."""
    import hashlib
    raw = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# CLI entry point (for python -m cas_forex.mt5_process_guard --worker ...)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MT5 process guard worker (internal — invoked by run_mt5_operation_safe)",
    )
    parser.add_argument(
        "--worker",
        type=str,
        required=True,
        help="Path to MT5WorkerSpec JSON file",
    )
    args = parser.parse_args()
    _mt5_worker(args.worker)
