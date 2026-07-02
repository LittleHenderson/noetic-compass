"""Paper-outcome simulator — realized P&L for paper trades from REAL candles.

The learning loop dispatches paper orders, but without a connected MT5 terminal
their realized profit/loss is never captured, so the learn-from-mistakes ledger
stays empty. This module closes that gap WITHOUT a broker: for every executed
paper order attempt (entry, stop-loss, take-profit, direction, lots) it walks the
REAL M1 candles after the open and resolves which level was touched first, then
computes the realized P&L with the SAME money math position sizing uses
(``value_per_price_unit_per_lot``), minus an explicit spread cost.

NULL-DISCIPLINE RULES (a subtly-wrong simulator fabricates fake edges):
  * REAL candles only — fetched from the live connector chain; nothing synthetic.
  * First-touch resolution at M1: if ONE candle spans BOTH stop and target, the
    outcome is unknowable at this resolution — it is resolved CONSERVATIVELY as
    a LOSS at the stop. The simulator may under-report performance, never
    flatter it.
  * A full spread cost is charged on every resolved trade (per asset class,
    conservative defaults) — winners shrink, losers grow.
  * Trades whose levels were never touched stay OPEN (no record) and are re-
    walked on the next run. Trades older than the fetchable candle window are
    marked unresolvable and excluded — never guessed.
  * Naive candle timestamps are treated as UTC (``timestamp_basis`` records
    this). Unit correctness is proven by tests with injected candles.

Boundary: simulated outcomes feed the LEARNING ledger only. The promotion-grade
outcome binding (PASS-token → owner review → live) keeps reading broker-verified
MT5 history exclusively; nothing simulated can advance the real-money path.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from cas_forex.instruments import get_instrument, price_unit_size
from cas_forex.time_utils import utc_now
from cas_forex.trade_management import value_per_price_unit_per_lot

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER_PATH = REPO_ROOT / "runtime" / "paper-outcomes.json"
DEFAULT_ORDER_ATTEMPT_STATE_PATH = REPO_ROOT / "runtime" / "order-attempts.json"

REPORT_KIND = "cas_forex_paper_outcome_sim"
LEDGER_REPORT_KIND = "cas_forex_paper_outcome_ledger"
OUTCOME_SOURCE = "paper_simulated_first_touch"

# Conservative full-spread cost per resolved round trip, in the instrument's
# quoted movement units (pips for FX, points for indices/metals).
DEFAULT_SPREAD_UNITS = {"FX": 1.5, "INDEX": 2.0, "METAL": 2.5}
FALLBACK_SPREAD_UNITS = 2.0

DEFAULT_MAX_CANDLES = 1500  # M1 ⇒ ~25 hours of walk window per run
MAX_ATTEMPT_AGE_DAYS = 5  # older unresolved attempts are marked unresolvable

CLAIM_BOUNDARY = (
    "Paper outcome simulation resolves PAPER order attempts against real candles "
    "to produce realized paper P&L for the LEARNING ledger only. It is "
    "conservative by construction (ambiguous candles resolve as losses; full "
    "spread charged). It does not place or close broker orders, move money, mint "
    "edge tokens, create owner/broker ACCEPT, or feed the real-money promotion "
    "path — that still requires broker-verified MT5 history."
)

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Ledger I/O
# ---------------------------------------------------------------------------
def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "report_kind": LEDGER_REPORT_KIND,
            "ingest_status": "PAPER_OUTCOME_SIMULATED",
            "history_records": [],
            "unresolvable": {},
            "updated_at": None,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("report_kind", LEDGER_REPORT_KIND)
    data.setdefault("ingest_status", "PAPER_OUTCOME_SIMULATED")
    data.setdefault("history_records", [])
    data.setdefault("unresolvable", {})
    return data


def _save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    ledger["updated_at"] = utc_now().isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(ledger, indent=1, sort_keys=True, default=str)
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(path)
            return
        except OSError as exc:  # transient OneDrive/AV lock
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
    if last_error is not None:
        raise last_error


def load_paper_outcome_history(path: Path | str = DEFAULT_LEDGER_PATH) -> dict[str, Any]:
    """The simulated closed-outcome ledger in MT5-history-report shape, so the
    learning engine's existing join consumes it unchanged."""
    with _LOCK:
        return _load_ledger(Path(path))


# ---------------------------------------------------------------------------
# Attempt loading
# ---------------------------------------------------------------------------
def _load_attempts(state_path: Path | str) -> list[dict[str, Any]]:
    path = Path(state_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    attempts = payload.get("attempts") if isinstance(payload, Mapping) else {}
    if not isinstance(attempts, Mapping):
        return []
    return [dict(row) for row in attempts.values() if isinstance(row, Mapping)]


def _eligible_attempt(row: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """A paper attempt the simulator can resolve: executed, has a ticket, has
    entry/SL/TP, and is NOT a real-money attempt."""
    if not bool(row.get("executed", False)):
        return None
    mode = str(row.get("mode") or "").upper()
    outcome = row.get("outcome") if isinstance(row.get("outcome"), Mapping) else {}
    broker_mode = str(outcome.get("broker_mode") or "").upper()
    if "LIVE" in mode or ("LIVE" in broker_mode and "PAPER" not in broker_mode):
        return None
    order = row.get("order") if isinstance(row.get("order"), Mapping) else {}
    ticket = outcome.get("broker_ticket")
    entry = outcome.get("filled_price") or order.get("price")
    stop = order.get("stop_loss")
    target = order.get("take_profit")
    direction = str(order.get("direction") or row.get("direction") or "").upper()
    symbol = str(order.get("symbol") or row.get("symbol") or "")
    lots = order.get("volume") or row.get("volume")
    opened = row.get("created_at") or order.get("created_at")
    try:
        entry_f = float(entry)
        stop_f = float(stop)
        target_f = float(target)
        lots_f = float(lots)
    except (TypeError, ValueError):
        return None
    if not ticket or not symbol or direction not in {"LONG", "SHORT"} or lots_f <= 0:
        return None
    if direction == "LONG" and not (stop_f < entry_f < target_f):
        return None
    if direction == "SHORT" and not (target_f < entry_f < stop_f):
        return None
    open_dt = _parse_ts(opened)
    if open_dt is None:
        return None
    return {
        "broker_ticket": str(ticket),
        "symbol": symbol,
        "direction": direction,
        "entry": entry_f,
        "stop_loss": stop_f,
        "take_profit": target_f,
        "lots": lots_f,
        "open_time": open_dt,
        "decision_ref": row.get("decision_ref"),
        "order_id": row.get("order_id"),
    }


def _parse_ts(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # timestamp_basis: naive == UTC
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Candles
# ---------------------------------------------------------------------------
def _fetch_candles(symbol: str, *, bars: int) -> list[dict[str, Any]]:
    """Real M1 candles via the live connector chain. Empty list on failure."""
    from cas_forex.waste_market_data import _connector_candidates, _normalize_connector_candles

    for connector in _connector_candidates(None):
        try:
            raw = connector.fetch_historical(symbol, bars=bars, timeframe="M1")
            candles = _normalize_connector_candles(raw)
        except Exception:
            continue
        if candles:
            return candles
    return []


def _candle_rows(candles: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candle in candles:
        ts = _parse_ts(candle.get("timestamp") or candle.get("time"))
        if ts is None:
            continue
        try:
            rows.append(
                {
                    "ts": ts,
                    "high": float(candle.get("high")),
                    "low": float(candle.get("low")),
                    "close": float(candle.get("close")),
                }
            )
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda r: r["ts"])
    return rows


# ---------------------------------------------------------------------------
# First-touch resolution + P&L
# ---------------------------------------------------------------------------
def _spread_price(symbol: str) -> float:
    try:
        spec = get_instrument(symbol)
        units = DEFAULT_SPREAD_UNITS.get(str(spec.asset_class).upper(), FALLBACK_SPREAD_UNITS)
    except Exception:
        units = FALLBACK_SPREAD_UNITS
    return float(units) * float(price_unit_size(symbol))


def resolve_first_touch(
    attempt: Mapping[str, Any],
    candles: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Walk candles strictly after the open; return a closed record or None.

    Conservative: a candle spanning BOTH levels resolves as a LOSS at the stop
    (``close_reason: AMBIGUOUS_CANDLE_CONSERVATIVE_SL``)."""
    direction = attempt["direction"]
    stop = float(attempt["stop_loss"])
    target = float(attempt["take_profit"])
    open_time: datetime = attempt["open_time"]

    for candle in candles:
        if candle["ts"] < open_time:
            continue
        hit_stop = candle["low"] <= stop if direction == "LONG" else candle["high"] >= stop
        hit_target = candle["high"] >= target if direction == "LONG" else candle["low"] <= target
        if hit_stop and hit_target:
            return _closed(attempt, exit_price=stop, close_reason="AMBIGUOUS_CANDLE_CONSERVATIVE_SL", close_time=candle["ts"])
        if hit_stop:
            return _closed(attempt, exit_price=stop, close_reason="STOP_LOSS", close_time=candle["ts"])
        if hit_target:
            return _closed(attempt, exit_price=target, close_reason="TAKE_PROFIT", close_time=candle["ts"])
    return None  # still open at this resolution — re-walk next run


def _closed(
    attempt: Mapping[str, Any],
    *,
    exit_price: float,
    close_reason: str,
    close_time: datetime,
) -> dict[str, Any]:
    symbol = attempt["symbol"]
    lots = float(attempt["lots"])
    entry = float(attempt["entry"])
    sign = 1.0 if attempt["direction"] == "LONG" else -1.0
    value_per_unit = value_per_price_unit_per_lot(symbol, entry)
    gross = (exit_price - entry) * sign * value_per_unit * lots
    cost = _spread_price(symbol) * value_per_unit * lots  # full spread, always charged
    net = round(gross - cost, 6)
    return {
        "broker_ticket": str(attempt["broker_ticket"]),
        "symbol": symbol,
        "direction": attempt["direction"],
        "broker_mode": "PAPER_SIM",
        "profit": net,
        "gross_profit": round(gross, 6),
        "commission": round(-cost, 6),
        "swap": 0.0,
        "close_reason": close_reason,
        "open_time": attempt["open_time"].isoformat(),
        "close_time": close_time.isoformat(),
        "entry": entry,
        "exit": float(exit_price),
        "lots": lots,
        "decision_ref": attempt.get("decision_ref"),
        "order_id": attempt.get("order_id"),
        "outcome_source": OUTCOME_SOURCE,
        "timestamp_basis": "naive_candle_timestamps_treated_as_utc",
    }


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------
def resolve_paper_outcomes(
    *,
    attempts: Iterable[Mapping[str, Any]] | None = None,
    candles_by_symbol: Mapping[str, list[Mapping[str, Any]]] | None = None,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    order_attempt_state_path: Path | str = DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    max_candles: int = DEFAULT_MAX_CANDLES,
) -> dict[str, Any]:
    """Resolve every eligible unresolved paper attempt. Idempotent per ticket."""
    with _LOCK:
        path = Path(ledger_path)
        ledger = _load_ledger(path)
        known = {str(r.get("broker_ticket")) for r in ledger.get("history_records", [])}
        unresolvable = dict(ledger.get("unresolvable") or {})

        raw_attempts = list(attempts) if attempts is not None else _load_attempts(order_attempt_state_path)
        eligible = [a for a in (_eligible_attempt(r) for r in raw_attempts) if a]
        pending = [a for a in eligible if a["broker_ticket"] not in known and a["broker_ticket"] not in unresolvable]

        now = utc_now()
        resolved: list[dict[str, Any]] = []
        still_open = 0
        newly_unresolvable = 0
        candle_cache: dict[str, list[dict[str, Any]]] = {}

        for attempt in pending:
            symbol = attempt["symbol"]
            if symbol not in candle_cache:
                if candles_by_symbol is not None:
                    candle_cache[symbol] = _candle_rows(candles_by_symbol.get(symbol) or [])
                else:
                    candle_cache[symbol] = _candle_rows(_fetch_candles(symbol, bars=max_candles))
            candles = candle_cache[symbol]
            if not candles:
                still_open += 1  # no data this run; retry later
                continue
            if attempt["open_time"] < candles[0]["ts"] - timedelta(minutes=2):
                # Candle window no longer covers the open — never guess.
                unresolvable[attempt["broker_ticket"]] = "candle_window_missed_open"
                newly_unresolvable += 1
                continue
            record = resolve_first_touch(attempt, candles)
            if record is not None:
                resolved.append(record)
            elif now - attempt["open_time"] > timedelta(days=MAX_ATTEMPT_AGE_DAYS):
                unresolvable[attempt["broker_ticket"]] = "unresolved_after_max_age"
                newly_unresolvable += 1
            else:
                still_open += 1

        if resolved or newly_unresolvable:
            ledger["history_records"] = list(ledger.get("history_records", [])) + resolved
            ledger["unresolvable"] = unresolvable
            _save_ledger(path, ledger)

        wins = sum(1 for r in resolved if r["profit"] > 0)
        losses = sum(1 for r in resolved if r["profit"] < 0)
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "eligible_attempts": len(eligible),
            "already_resolved": len(known),
            "newly_resolved": len(resolved),
            "newly_resolved_wins": wins,
            "newly_resolved_losses": losses,
            "newly_resolved_net_pnl": round(sum(r["profit"] for r in resolved), 4),
            "still_open": still_open,
            "newly_unresolvable": newly_unresolvable,
            "total_resolved": len(known) + len(resolved),
            "ledger_path": str(path),
            "read_only_market_data": True,
            "broker_touched": False,
            "money_moved": False,
            "edge_token_minted": False,
            "owner_accept_created": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }


# ---------------------------------------------------------------------------
# Guarded refresh (called best-effort by the AI operator before it reads)
# ---------------------------------------------------------------------------
def maybe_refresh_paper_outcomes(
    *,
    max_age_seconds: int = 600,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
) -> Optional[dict[str, Any]]:
    """Run the resolver only if the ledger is older than ``max_age_seconds``."""
    with _LOCK:
        ledger = _load_ledger(Path(ledger_path))
        updated = _parse_ts(ledger.get("updated_at"))
    if updated is not None and (utc_now() - updated).total_seconds() < max_age_seconds:
        return None
    try:
        return resolve_paper_outcomes(ledger_path=ledger_path)
    except Exception:
        return None  # best-effort: a failed refresh must never break the caller


__all__ = [
    "DEFAULT_LEDGER_PATH",
    "LEDGER_REPORT_KIND",
    "OUTCOME_SOURCE",
    "REPORT_KIND",
    "load_paper_outcome_history",
    "maybe_refresh_paper_outcomes",
    "resolve_first_touch",
    "resolve_paper_outcomes",
]
