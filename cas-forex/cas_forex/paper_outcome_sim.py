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

# Trailing-stop lock-in fractions tested per resolved trade (the implementable
# "bank winners early" policies: lock in this share of the best run so far).
TRAIL_FRACTIONS = (0.3, 0.5, 0.7)


def _trailing_dials() -> tuple[bool, float]:
    """Owner/operator trailing-stop dials: (enabled, lock_fraction). Off on any
    error. When enabled, resolved trades exit via the trailing stop — so the
    realized outcomes the learning loop sees reflect the exit policy in force."""
    try:
        from cas_forex.ai_control_authority import get_authority

        control = get_authority().control
        enabled = bool(int(control.get("trailing_stop_enabled")))
        frac = float(control.get("trailing_lock_fraction"))
        return enabled, frac
    except Exception:
        return False, 0.5

CLAIM_BOUNDARY = (
    "Paper outcome simulation resolves PAPER order attempts against real candles "
    "to produce realized paper P&L for the LEARNING ledger only. It is "
    "conservative by construction (ambiguous candles resolve as losses; full "
    "spread charged). It does not place or close broker orders, move money, mint "
    "edge tokens, create owner/broker ACCEPT, or feed the real-money promotion "
    "path — that still requires broker-verified MT5 history."
)

_LOCK = threading.RLock()

# Test/replay provenance markers. Rows whose decision_ref carries one of these
# are INJECTED test signals, not trades the loop earned. Discovered 2026-07-03:
# one 49-copy EUR/USD cluster (decision_refs 'micro_scalp_agent:test'/'dec-1',
# ONE broker ticket, identical $193.03 per copy) was +$9,458 = 90.4% of the
# entire paper net — it was flattering the scoreboard AND the learning ledger.
# Such rows are refused at ingest and can be quarantined out of an existing
# ledger (moved to a 'quarantined_test_artifacts' bucket, never destroyed).
_TEST_REF_EXACT = frozenset({"dec-1", "dec-2", "dec-3"})


def is_test_artifact(record: Mapping[str, Any]) -> bool:
    """True when a record/attempt's provenance marks it as an injected test
    signal rather than a trade the loop earned (see _TEST_REF_EXACT note)."""
    for key in ("decision_ref", "order_id"):
        ref = str(record.get(key) or "").lower()
        if ref in _TEST_REF_EXACT or ":test" in ref or ref.startswith("test-") or ref.endswith("_test"):
            return True
    return False


def purge_test_artifacts(ledger_path: Path | str = DEFAULT_LEDGER_PATH) -> dict[str, Any]:
    """Move injected test/replay rows out of ``history_records`` into a
    ``quarantined_test_artifacts`` bucket in the same ledger file (preserved,
    not destroyed — reversible by hand). Idempotent. Returns counts + the
    quarantined net P&L so the scoreboard correction is auditable."""
    with _LOCK:
        path = Path(ledger_path)
        ledger = _load_ledger(path)
        rows = [r for r in ledger.get("history_records", []) if isinstance(r, dict)]
        keep = [r for r in rows if not is_test_artifact(r)]
        quarantined = [r for r in rows if is_test_artifact(r)]
        if quarantined:
            ledger["history_records"] = keep
            ledger["quarantined_test_artifacts"] = list(
                ledger.get("quarantined_test_artifacts") or []
            ) + quarantined
            _save_ledger(path, ledger)
        return {
            "report_kind": "cas_forex_paper_ledger_test_artifact_purge",
            "quarantined_now": len(quarantined),
            "quarantined_total": len(ledger.get("quarantined_test_artifacts") or []),
            "remaining_records": len(keep) if quarantined else len(rows),
            "quarantined_net_pnl_usd": round(
                sum(float(r.get("profit") or 0.0) for r in (ledger.get("quarantined_test_artifacts") or [])), 2
            ),
            "ledger_path": str(path),
        }


# Open-paper-position snapshot cache (the risk gate reads this on every
# dispatch; a short TTL keeps it out of the 15s burst loop's hot path).
# Keyed by the (ledger, attempts) paths so callers with different stores
# never see each other's snapshot.
_OPEN_POS_CACHE: dict[str, Any] = {"at": 0.0, "positions": None, "key": None}
_OPEN_POS_TTL_SECONDS = 20.0


def open_paper_positions(
    *,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    order_attempt_state_path: Path | str = DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    max_age_seconds: float = _OPEN_POS_TTL_SECONDS,
) -> list[dict[str, Any]]:
    """Currently-OPEN paper positions: executed paper attempts the simulator has
    not yet resolved (or written off). This is the portfolio the pre-execution
    risk gate counts when the caller supplies no broker telemetry — it makes the
    open-position caps REAL for the paper loop instead of letting them compare
    against an empty portfolio (how 150+ positions piled up unchecked).
    Best-effort: any failure returns []."""
    now = time.monotonic()
    cache_key = (str(ledger_path), str(order_attempt_state_path))
    with _LOCK:
        cached = _OPEN_POS_CACHE["positions"]
        if (
            cached is not None
            and _OPEN_POS_CACHE["key"] == cache_key
            and max_age_seconds > 0
            and now - _OPEN_POS_CACHE["at"] <= max_age_seconds
        ):
            return [dict(p) for p in cached]
        try:
            ledger = _load_ledger(Path(ledger_path))
            known = {str(r.get("broker_ticket")) for r in ledger.get("history_records", [])}
            unresolvable = {str(k) for k in (ledger.get("unresolvable") or {})}
            eligible = [
                a for a in (_eligible_attempt(r) for r in _load_attempts(order_attempt_state_path)) if a
            ]
            open_rows = [
                {
                    "symbol": a["symbol"],
                    "direction": a["direction"],
                    "lots": float(a["lots"]),
                    "floating_pnl": 0.0,  # unknown without live quotes; count/lots caps still bite
                }
                for a in eligible
                if a["broker_ticket"] not in known
                and a["broker_ticket"] not in unresolvable
                and not is_test_artifact(a)
            ]
        except Exception:
            open_rows = []
        _OPEN_POS_CACHE["at"] = now
        _OPEN_POS_CACHE["positions"] = open_rows
        _OPEN_POS_CACHE["key"] = cache_key
        return [dict(p) for p in open_rows]


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
    entry = float(attempt["entry"])
    stop = float(attempt["stop_loss"])
    target = float(attempt["take_profit"])
    open_time: datetime = attempt["open_time"]

    # Max Favorable Excursion: the best price the trade reached in its favour
    # BEFORE it closed, and how many bars it took to get there. This is what
    # lets us test "bank big winners early" (owner idea) — did trades run far
    # into profit before reversing, or close near their peak already?
    best_price = entry
    best_bars = 0
    bars = 0

    for candle in candles:
        if candle["ts"] < open_time:
            continue
        bars += 1
        favorable = candle["high"] if direction == "LONG" else candle["low"]
        if (direction == "LONG" and favorable > best_price) or (direction == "SHORT" and favorable < best_price):
            best_price = favorable
            best_bars = bars
        hit_stop = candle["low"] <= stop if direction == "LONG" else candle["high"] >= stop
        hit_target = candle["high"] >= target if direction == "LONG" else candle["low"] <= target
        if hit_stop and hit_target:
            return _closed(attempt, exit_price=stop, close_reason="AMBIGUOUS_CANDLE_CONSERVATIVE_SL", close_time=candle["ts"], mfe_price=best_price, bars_to_peak=best_bars, bars_held=bars)
        if hit_stop:
            return _closed(attempt, exit_price=stop, close_reason="STOP_LOSS", close_time=candle["ts"], mfe_price=best_price, bars_to_peak=best_bars, bars_held=bars)
        if hit_target:
            return _closed(attempt, exit_price=target, close_reason="TAKE_PROFIT", close_time=candle["ts"], mfe_price=best_price, bars_to_peak=best_bars, bars_held=bars)
    return None  # still open at this resolution — re-walk next run


def simulate_trailing_stop(
    attempt: Mapping[str, Any],
    candles: list[dict[str, Any]],
    *,
    trail_fraction: float,
) -> Optional[float]:
    """Realistic, IMPLEMENTABLE version of "bank winners early": a trailing stop
    that locks in ``trail_fraction`` of the best run so far.

    As price moves favourably the stop ratchets to
    ``entry + trail_fraction * (best_favorable - entry)`` (mirrored for SHORT),
    never worse than the original stop. The trade exits at the trailing stop on a
    pullback, or at the original take-profit, or the original stop.

    NO intra-bar lookahead: the trailing level for a bar is computed from the peak
    as of the PREVIOUS bar (you cannot lock in a level the price only reached
    later in the same bar). Ambiguous within-bar ordering resolves against the
    trade (stop before target). Returns realized net P&L, or None if unresolved.
    """
    direction = attempt["direction"]
    entry = float(attempt["entry"])
    orig_stop = float(attempt["stop_loss"])
    target = float(attempt["take_profit"])
    open_time: datetime = attempt["open_time"]
    frac = max(0.0, min(1.0, float(trail_fraction)))

    best = entry
    for candle in candles:
        if candle["ts"] < open_time:
            continue
        # Trailing level from the peak BEFORE this bar (no intra-bar lookahead).
        # Until a confirmed favourable move (best beyond entry), the stop stays
        # at the ORIGINAL stop — a trailing stop must not sit at breakeven and
        # get knocked out by ordinary noise before the trade ever runs.
        if direction == "LONG":
            trail = orig_stop if best <= entry else max(orig_stop, entry + frac * (best - entry))
            hit_trail = candle["low"] <= trail
            hit_target = candle["high"] >= target
        else:
            trail = orig_stop if best >= entry else min(orig_stop, entry - frac * (entry - best))
            hit_trail = candle["high"] >= trail
            hit_target = candle["low"] <= target
        if hit_trail:
            return _net_pnl(attempt, exit_price=trail)  # conservative: pullback first
        if hit_target:
            return _net_pnl(attempt, exit_price=target)
        # Update the peak with THIS bar's favourable extreme for the next bar.
        favorable = candle["high"] if direction == "LONG" else candle["low"]
        if (direction == "LONG" and favorable > best) or (direction == "SHORT" and favorable < best):
            best = favorable
    return None


def _net_pnl(attempt: Mapping[str, Any], *, exit_price: float) -> float:
    symbol = attempt["symbol"]
    lots = float(attempt["lots"])
    entry = float(attempt["entry"])
    sign = 1.0 if attempt["direction"] == "LONG" else -1.0
    value_per_unit = value_per_price_unit_per_lot(symbol, entry)
    gross = (float(exit_price) - entry) * sign * value_per_unit * lots
    cost = _spread_price(symbol) * value_per_unit * lots
    return round(gross - cost, 6)


def _closed(
    attempt: Mapping[str, Any],
    *,
    exit_price: float,
    close_reason: str,
    close_time: datetime,
    mfe_price: float | None = None,
    bars_to_peak: int = 0,
    bars_held: int = 0,
) -> dict[str, Any]:
    symbol = attempt["symbol"]
    lots = float(attempt["lots"])
    entry = float(attempt["entry"])
    sign = 1.0 if attempt["direction"] == "LONG" else -1.0
    value_per_unit = value_per_price_unit_per_lot(symbol, entry)
    gross = (exit_price - entry) * sign * value_per_unit * lots
    cost = _spread_price(symbol) * value_per_unit * lots  # full spread, always charged
    net = round(gross - cost, 6)
    # MFE in P&L terms: what the trade was worth at its best point (gross of the
    # single exit-spread cost, which would apply to an early bank too).
    mfe = float(mfe_price) if mfe_price is not None else entry
    mfe_gross = (mfe - entry) * sign * value_per_unit * lots
    mfe_pnl = round(mfe_gross - cost, 6)
    # How much of the peak the actual close captured (1.0 = closed at peak;
    # low = gave back a big winner). Undefined when the peak never went positive.
    captured = round(net / mfe_pnl, 4) if mfe_pnl > 0 else None
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
        "mfe_price": round(mfe, 8),
        "mfe_pnl": mfe_pnl,
        "captured_fraction_of_peak": captured,
        "bars_to_peak": int(bars_to_peak),
        "bars_held": int(bars_held),
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
    trailing_enabled, trail_fraction = _trailing_dials()
    with _LOCK:
        path = Path(ledger_path)
        ledger = _load_ledger(path)
        known = {str(r.get("broker_ticket")) for r in ledger.get("history_records", [])}
        unresolvable = dict(ledger.get("unresolvable") or {})

        raw_attempts = list(attempts) if attempts is not None else _load_attempts(order_attempt_state_path)
        eligible = [a for a in (_eligible_attempt(r) for r in raw_attempts) if a]
        # Ingest guard: injected test/replay signals never enter the ledger —
        # they flatter the scoreboard and poison the learning loop (see
        # _TEST_REF_EXACT note; 2026-07-03 audit).
        test_artifacts_skipped = sum(1 for a in eligible if is_test_artifact(a))
        pending = [
            a
            for a in eligible
            if a["broker_ticket"] not in known
            and a["broker_ticket"] not in unresolvable
            and not is_test_artifact(a)
        ]

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
                # Always record the counterfactual trailing outcomes for the
                # analysis. If the owner/operator has trailing ENABLED, the
                # trade's ACTUAL realized exit IS the trailing stop — so the
                # ledger (and everything downstream) reflects the live policy.
                record["trailing_pnl_by_fraction"] = {
                    f"{frac}": simulate_trailing_stop(attempt, candles, trail_fraction=frac)
                    for frac in TRAIL_FRACTIONS
                }
                record["hold_profit"] = record["profit"]  # keep the hold-to-SL/TP value
                if trailing_enabled:
                    trail_pnl = simulate_trailing_stop(attempt, candles, trail_fraction=trail_fraction)
                    if trail_pnl is not None:
                        record["profit"] = trail_pnl
                        record["exit_policy"] = "TRAILING_STOP"
                        record["trailing_lock_fraction"] = trail_fraction
                        record["close_reason"] = "TRAILING_STOP"
                    else:
                        record["exit_policy"] = "HOLD_TO_SL_TP"
                else:
                    record["exit_policy"] = "HOLD_TO_SL_TP"
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
            "test_artifacts_skipped": test_artifacts_skipped,
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


EARLY_BANK_REPORT_KIND = "cas_forex_early_banking_analysis"
DEFAULT_BANK_FRACTIONS = (0.4, 0.5, 0.6, 0.7, 0.8)


def build_early_banking_analysis(
    *,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    bank_fractions: tuple[float, ...] = DEFAULT_BANK_FRACTIONS,
    min_trades: int = 20,
) -> dict[str, Any]:
    """Test the owner's "bank big winners early" idea on realized paper trades.

    For each resolved trade we know its actual net AND its max-favorable-excursion
    P&L (the best it was ever worth). A "bank at fraction f" policy is modeled
    conservatively: if the trade's peak was profitable, assume we could have
    exited at ``f * mfe_pnl`` (a trade that reached its peak passed through every
    lower level first); otherwise the trade keeps its actual (losing) outcome —
    early banking never rescues a loser. This compares total net under each
    banking policy against holding to the real SL/TP.

    Honest caveats surfaced in the result: this assumes the fractional level was
    reachable (true for a monotone run to the peak, optimistic for a jagged one),
    ignores that banking early frees capital sooner (a plus it does NOT credit),
    and says nothing about real-money edge. Directional signal for the operator
    and owner, not a promise."""
    ledger = load_paper_outcome_history(ledger_path)
    rows = [r for r in ledger.get("history_records", []) if isinstance(r, Mapping) and r.get("mfe_pnl") is not None]
    actual_net = round(sum(_num(r.get("profit")) for r in rows), 4)
    winners = [r for r in rows if _num(r.get("mfe_pnl")) > 0]
    # How much of the peak winners actually kept (low => big give-back => early
    # banking likely helps; high => trades already close near their peak).
    captured = [_num(r.get("captured_fraction_of_peak")) for r in winners if r.get("captured_fraction_of_peak") is not None]
    avg_captured = round(sum(captured) / len(captured), 4) if captured else None

    policies = []
    for f in bank_fractions:
        total = 0.0
        banked = 0
        for r in rows:
            mfe_pnl = _num(r.get("mfe_pnl"))
            actual = _num(r.get("profit"))
            if mfe_pnl > 0:
                total += f * mfe_pnl  # banked at fraction of peak
                banked += 1
            else:
                total += actual  # loser keeps its real outcome
        policies.append(
            {
                "bank_fraction_of_peak": f,
                "modeled_net_pnl": round(total, 4),
                "delta_vs_hold": round(total - actual_net, 4),
                "trades_banked_early": banked,
            }
        )
    best = max(policies, key=lambda p: p["modeled_net_pnl"]) if policies else None
    return {
        "report_kind": EARLY_BANK_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "resolved_trades_with_mfe": len(rows),
        "enough_data": len(rows) >= max(1, int(min_trades)),
        "min_trades": max(1, int(min_trades)),
        "actual_net_pnl_hold_to_sl_tp": actual_net,
        "winner_count": len(winners),
        "avg_captured_fraction_of_peak": avg_captured,
        "policies": policies,
        "best_policy": best,
        "verdict": (
            "not enough resolved trades with MFE yet — keep trading and re-check"
            if len(rows) < max(1, int(min_trades))
            else (
                f"modeled early-banking at {best['bank_fraction_of_peak']} of peak would change paper net by "
                f"{best['delta_vs_hold']} vs holding to SL/TP (directional, see caveats)"
                if best
                else "no policy computed"
            )
        ),
        "caveats": [
            "assumes the fractional profit level was reachable (optimistic on jagged runs)",
            "does not credit the capital-efficiency benefit of banking sooner",
            "paper-only; says nothing about real-money edge",
        ],
        "read_only": True,
        "money_moved": False,
    }


TRAILING_REPORT_KIND = "cas_forex_trailing_stop_analysis"


def build_trailing_stop_analysis(
    *,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    min_trades: int = 20,
) -> dict[str, Any]:
    """The IMPLEMENTABLE test of "bank winners early": realized paper net if each
    trade had used a trailing stop (lock in f of the best run) vs holding to the
    original SL/TP. Unlike the idealized 'bank at f×peak' ceiling, a trailing
    stop is a real order you can place, so these numbers are achievable — modulo
    the usual paper caveats (M1 resolution, real spread charged, no real-money
    edge claim)."""
    ledger = load_paper_outcome_history(ledger_path)
    rows = [
        r for r in ledger.get("history_records", [])
        if isinstance(r, Mapping) and isinstance(r.get("trailing_pnl_by_fraction"), Mapping)
    ]
    actual_net = round(sum(_num(r.get("profit")) for r in rows), 4)
    fractions = sorted({k for r in rows for k in (r.get("trailing_pnl_by_fraction") or {}).keys()})
    policies = []
    for key in fractions:
        vals = [r["trailing_pnl_by_fraction"].get(key) for r in rows]
        vals = [_num(v) for v in vals if v is not None]
        if not vals:
            continue
        total = round(sum(vals), 4)
        policies.append(
            {
                "trail_lock_fraction": float(key),
                "modeled_net_pnl": total,
                "delta_vs_hold": round(total - actual_net, 4),
                "trades": len(vals),
            }
        )
    best = max(policies, key=lambda p: p["modeled_net_pnl"]) if policies else None
    return {
        "report_kind": TRAILING_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "resolved_trades_with_trailing": len(rows),
        "enough_data": len(rows) >= max(1, int(min_trades)),
        "min_trades": max(1, int(min_trades)),
        "actual_net_pnl_hold_to_sl_tp": actual_net,
        "policies": policies,
        "best_policy": best,
        "verdict": (
            "not enough trades with trailing data yet — accumulates as new trades close"
            if len(rows) < max(1, int(min_trades))
            else (
                f"an achievable trailing stop locking {best['trail_lock_fraction']:.0%} of the run would change "
                f"paper net by {best['delta_vs_hold']:+.2f} vs holding to SL/TP"
                if best
                else "no policy computed"
            )
        ),
        "note": "trailing stop is an IMPLEMENTABLE order (unlike the idealized bank-at-peak ceiling); real spread charged; paper-only.",
        "read_only": True,
        "money_moved": False,
    }


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "DEFAULT_LEDGER_PATH",
    "EARLY_BANK_REPORT_KIND",
    "LEDGER_REPORT_KIND",
    "OUTCOME_SOURCE",
    "REPORT_KIND",
    "TRAILING_REPORT_KIND",
    "TRAIL_FRACTIONS",
    "build_early_banking_analysis",
    "build_trailing_stop_analysis",
    "load_paper_outcome_history",
    "maybe_refresh_paper_outcomes",
    "resolve_first_touch",
    "resolve_paper_outcomes",
    "simulate_trailing_stop",
]
