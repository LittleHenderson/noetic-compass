"""Forex Fury .set file application primitive.

Pure module that loads a MetaTrader ``.set`` file, verifies its sha256,
parses it into a structured payload, and applies its parameters to a
broker order-request dict. This module does NOT integrate with any broker
adapter — that integration belongs in ``cas_forex/broker/mt5_bridge.py``
and is intentionally out of scope. This is the primitive the bridge can
call later.

Claim boundary: this primitive performs strategy-parameter mapping only.
It does not place orders, create broker ACCEPT, deposit, withdraw, move
bank/card funds, or automate payouts.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence


__all__ = [
    "SetParameter",
    "SetPayload",
    "EnrichedOrderRequest",
    "DEFAULT_SET_KEY_TO_REQUEST_KEY",
    "parse_set_text",
    "build_set_payload",
    "apply_set_to_order_request",
    "materialize_set_payload",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SetParameter:
    """A single parsed entry from a .set file.

    ``value`` is the raw textual value as it appeared in the file.
    ``parsed_value`` is a best-effort typed conversion (int / float / str /
    bool / None). ``optimize_min``, ``optimize_max``, ``optimize_step`` and
    ``optimize_flag`` are extracted from the optional optimization tuple
    suffix (e.g. ``Stop_Loss=120,30,150,200,F``).

    ``optimize_flag`` convention:
      - ``0`` — fixed (suffix ``F``)
      - ``1`` — optimize (suffix ``1`` / ``T``)
      - any other parseable int is preserved as-is.
    """

    key: str
    value: str
    parsed_value: Any
    optimize_min: Optional[float] = None
    optimize_max: Optional[float] = None
    optimize_step: Optional[float] = None
    optimize_flag: Optional[int] = None


@dataclass(frozen=True)
class SetPayload:
    """Structured payload built from a single .set file."""

    profile_id: str
    source_set_path: str
    source_sha256: str
    platform: str
    parameters: tuple[SetParameter, ...]
    parameters_by_key: Mapping[str, SetParameter] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True)
class EnrichedOrderRequest:
    """An order-request dict enriched with parameters drawn from a .set."""

    base_order_request: Mapping[str, Any]
    applied_set_payload: Optional[SetPayload]
    applied_overrides: Mapping[str, Any]
    applied_at_iso: str
    application_errors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# Mapping from .set parameter key -> order-request key. When the .set
# parameter is present, its parsed_value is copied to this key on a NEW
# order-request dict. The base dict is never mutated.
DEFAULT_SET_KEY_TO_REQUEST_KEY: Mapping[str, str] = MappingProxyType(
    {
        "Lot_Size": "lots",
        "Stop_Loss": "stop_loss_pips",
        "Take_Profit": "take_profit_pips",
        "InpTPRatio": "tp_sl_ratio",
        "MaxOrders": "max_orders",
        "Magic_Number": "magic_number",
        "InpMaxTradesPerDay": "max_trades_per_day",
        "MaxSpread": "max_spread",
        "Max_Slippage": "max_slippage",
        "InpUseGrid": "uses_grid",
        "InpGridLevelsDistanceMultiplier": "grid_level_distance_multiplier",
        "InpGridVolumeMultiplier": "grid_volume_multiplier",
        "InpUseTrailingStop": "uses_trailing_stop",
        "InpUseCostAveraging": "uses_cost_averaging",
        "StartTradingTime": "start_trading_time",
        "EndTradingTime": "end_trading_time",
        "TradeOnMonday": "trade_on_monday",
        "TradeOnTuesday": "trade_on_tuesday",
        "TradeOnWednesday": "trade_on_wednesday",
        "TradeOnThursday": "trade_on_thursday",
        "TradeOnFriday": "trade_on_friday",
    }
)


# ---------------------------------------------------------------------------
# Pure parsers
# ---------------------------------------------------------------------------


def parse_set_text(text: str) -> tuple[tuple[SetParameter, ...], tuple[str, ...]]:
    """Parse the raw text of a .set file.

    The accepted line shapes are:

      - ``Key=Value``  — a bare parameter.
      - ``Key=Value,Min,Step,Max,Flag`` — optimization tuple. ``Flag`` is
        one of ``F`` (fixed, mapped to ``0``), ``1``/``T`` (optimize,
        mapped to ``1``), or any parseable integer (preserved as-is).
      - Lines starting with ``;`` are treated as comments and skipped.
      - Blank lines are skipped.

    Returns ``(parameters, errors)`` where ``errors`` is a tuple of human
    readable strings describing unparseable lines. The function never
    raises on malformed input.
    """

    if not isinstance(text, str):  # pragma: no cover - defensive
        raise TypeError("parse_set_text expects str input")

    parameters: list[SetParameter] = []
    errors: list[str] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(";"):
            continue
        if "=" not in line:
            errors.append(f"line {line_number}: missing '=' separator ({raw_line!r})")
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            errors.append(f"line {line_number}: empty key ({raw_line!r})")
            continue
        try:
            param = _build_parameter(key, value)
        except ValueError as exc:
            errors.append(f"line {line_number}: {exc}")
            continue
        parameters.append(param)

    return tuple(parameters), tuple(errors)


def _build_parameter(key: str, raw_value: str) -> SetParameter:
    """Construct a SetParameter from a single ``Key=Value`` line.

    Detects optimization-tuple suffix ``value,min,step,max,flag``.
    """

    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) >= 5 and _looks_like_optimize_flag(parts[-1]):
        head = parts[0]
        opt_min = _coerce_optional_float(parts[1])
        opt_step = _coerce_optional_float(parts[2])
        opt_max = _coerce_optional_float(parts[3])
        flag = _coerce_optimize_flag(parts[-1])
        return SetParameter(
            key=key,
            value=head,
            parsed_value=_coerce_parsed(head),
            optimize_min=opt_min,
            optimize_max=opt_max,
            optimize_step=opt_step,
            optimize_flag=flag,
        )

    return SetParameter(
        key=key,
        value=raw_value,
        parsed_value=_coerce_parsed(raw_value),
    )


def _looks_like_optimize_flag(token: str) -> bool:
    upper = token.strip().upper()
    if upper in {"F", "T"}:
        return True
    try:
        int(upper)
        return True
    except ValueError:
        return False


def _coerce_optimize_flag(token: str) -> int:
    upper = token.strip().upper()
    if upper == "F":
        return 0
    if upper == "T":
        return 1
    try:
        return int(upper)
    except ValueError as exc:  # pragma: no cover - guarded above
        raise ValueError(f"unparseable optimize flag {token!r}") from exc


def _coerce_optional_float(token: str) -> Optional[float]:
    token = token.strip()
    if token == "":
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _coerce_parsed(value: str) -> Any:
    """Best-effort typed coercion of a raw value string."""
    stripped = value.strip()
    if stripped == "":
        return ""
    lower = stripped.lower()
    if lower in {"true"}:
        return True
    if lower in {"false"}:
        return False
    if stripped == "(null)":
        return None
    # int first, then float
    try:
        as_int = int(stripped)
        if str(as_int) == stripped or (stripped.startswith("-") and str(as_int) == stripped):
            return as_int
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return stripped


# ---------------------------------------------------------------------------
# Payload + order-request application
# ---------------------------------------------------------------------------


def build_set_payload(
    *,
    profile_id: str,
    source_set_path: str,
    source_sha256: str,
    set_text: str,
    platform: str,
) -> SetPayload:
    """Build a SetPayload from raw .set text.

    Caller is responsible for verifying ``source_sha256`` matches the bytes
    backing ``set_text`` before invoking this function. ``materialize_set_payload``
    does that verification for the disk-backed path.
    """

    parameters, _errors = parse_set_text(set_text)
    by_key = MappingProxyType({param.key: param for param in parameters})
    return SetPayload(
        profile_id=profile_id,
        source_set_path=source_set_path,
        source_sha256=source_sha256,
        platform=platform,
        parameters=parameters,
        parameters_by_key=by_key,
    )


def apply_set_to_order_request(
    *,
    base_order_request: Mapping[str, Any],
    set_payload: SetPayload,
    now: Optional[datetime] = None,
    apply_overrides_for: Optional[Sequence[str]] = None,
    key_map: Mapping[str, str] = DEFAULT_SET_KEY_TO_REQUEST_KEY,
) -> EnrichedOrderRequest:
    """Apply selected .set parameters to ``base_order_request``.

    The base dict is never mutated. The returned ``EnrichedOrderRequest``
    holds a NEW dict in ``base_order_request`` that is the original merged
    with the overrides drawn from ``set_payload``.

    When ``apply_overrides_for`` is provided, ONLY those .set keys are
    applied (others are ignored even if present in the .set).
    """

    if not isinstance(base_order_request, Mapping):  # pragma: no cover - defensive
        raise TypeError("base_order_request must be a Mapping")

    overrides: dict[str, Any] = {}
    errors: list[str] = []

    allowed: Optional[set[str]] = None
    if apply_overrides_for is not None:
        allowed = {str(key) for key in apply_overrides_for}

    for set_key, request_key in key_map.items():
        if allowed is not None and set_key not in allowed:
            continue
        param = set_payload.parameters_by_key.get(set_key)
        if param is None:
            continue
        overrides[request_key] = param.parsed_value

    if allowed is not None:
        unknown = allowed.difference(key_map.keys())
        for missing in sorted(unknown):
            errors.append(f"unknown set key in apply_overrides_for: {missing!r}")

    merged = dict(base_order_request)
    merged.update(overrides)

    applied_at = (now or datetime.now(UTC)).isoformat()

    return EnrichedOrderRequest(
        base_order_request=merged,
        applied_set_payload=set_payload,
        applied_overrides=MappingProxyType(dict(overrides)),
        applied_at_iso=applied_at,
        application_errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Disk-touching helper
# ---------------------------------------------------------------------------


def materialize_set_payload(
    *,
    profile_id: str,
    source_set_path: str,
    expected_sha256: str,
    repo_root: Path,
    platform: str = "MT5",
) -> tuple[Optional[SetPayload], Optional[str]]:
    """Load a .set file from disk, verify sha256, return SetPayload.

    Returns ``(payload, None)`` on success or ``(None, error_message)`` on
    any failure. Never raises.
    """

    try:
        root = Path(repo_root).expanduser().resolve()
    except OSError as exc:
        return None, f"repo root unreadable: {exc}"

    rel = Path(source_set_path)
    target = (root / rel) if not rel.is_absolute() else rel

    if not target.exists() or not target.is_file():
        return None, "set file missing"

    try:
        data = target.read_bytes()
    except OSError as exc:
        return None, f"set file unreadable: {exc}"

    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha.lower() != str(expected_sha256).lower():
        return None, "sha256 mismatch"

    text = _decode_set_bytes(data)

    payload = build_set_payload(
        profile_id=profile_id,
        source_set_path=str(target),
        source_sha256=actual_sha,
        set_text=text,
        platform=platform,
    )
    return payload, None


def _decode_set_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
