"""MetaTrader 5 Bridge — executes CAS-approved orders via MT5 Python API.

Supports:
- MT5 live accounts (Hugo's Way and others)
- MT5 demo/paper trading accounts
- Automatic duplicate detection via ExecutionGate
- Slippage validation against observed fill prices
- Connection health monitoring
- Graceful fallback to simulated execution when MT5 unavailable
"""

from abc import ABC, abstractmethod
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
from typing import Any, Dict, Mapping, Optional, Tuple

from cas_forex.config import config
from cas_forex.instruments import price_unit_size, resolve_broker_symbol, round_price
from cas_forex.mt5_permissions import build_mt5_permission_state, mt5_order_send_block_reason
from cas_forex.schemas.order import (
    BrokerLockReason,
    BrokerMode,
    BrokerOrderRequest,
    OrderOutcome,
    OrderStatus,
)
from cas_forex.schemas.forecast import Direction, pip_multiplier
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MT5_DEPS = REPO_ROOT / ".mt5deps"
COMMON_MT5_TERMINAL_PATHS = (
    r"C:\Program Files\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
)


def _effective_config():
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(config)
    except Exception:  # pragma: no cover - fall back to static config
        return config


def _resolve_mt5_terminal_path(cfg: object) -> str | None:
    configured = str(getattr(cfg, "mt5_path", "") or "").strip()
    if configured:
        return configured
    for candidate in COMMON_MT5_TERMINAL_PATHS:
        if Path(candidate).exists():
            return candidate
    return None

# Bound the MT5 connect handshake (ms). MetaTrader's Python IPC can be flaky and
# its default initialize timeout is 60s — far too long for a poller. Fail fast.
MT5_INIT_TIMEOUT_MS = 8000


def _position_opened_at_iso(position: Any) -> str | None:
    try:
        timestamp = float(getattr(position, "time", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _add_local_mt5_deps() -> None:
    """Make MetaTrader5 importable, preferring a working environment install.

    A properly pip-installed ``MetaTrader5`` (with its compiled ``_core``) always
    wins — if it imports, we touch nothing. The project-local ``.mt5deps`` wheel
    is only a FALLBACK for machines without a system install; we never let it
    shadow a working install (the vendored copy can be built for a different
    Python ABI and then fail with ``No module named 'MetaTrader5._core'``).
    """

    try:
        import MetaTrader5  # noqa: F401 - a working install is preferred, untouched
        return
    except Exception:
        pass

    if LOCAL_MT5_DEPS.exists():
        path = str(LOCAL_MT5_DEPS)
        if path not in sys.path:
            sys.path.insert(0, path)


class BrokerBridge(ABC):
    """Abstract interface for broker execution bridges."""

    @abstractmethod
    def execute_order(self, order: BrokerOrderRequest) -> OrderOutcome:
        """Send a validated order to the broker and return the outcome."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the broker connection is alive."""
        ...

    @abstractmethod
    def get_account_info(self) -> Dict[str, float]:
        """Return account balance, equity, margin info."""
        ...

    @abstractmethod
    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        """Close a specific open position by ticket number."""
        ...

    @abstractmethod
    def modify_position(
        self,
        ticket: int,
        *,
        stop_loss: float,
        take_profit: Optional[float] = None,
    ) -> OrderOutcome:
        """Move an OPEN position's stop-loss (and optionally take-profit).

        This is the broker primitive behind the breakeven principal-lock: it
        amends the protective stop on an EXISTING, already-authorized position
        (typically moving the SL toward the entry price once the trade is in
        profit). ``take_profit=None`` leaves the existing TP untouched.

        HONESTY / risk posture: modifying the stop of an open position is
        RISK-REDUCING — it can only tighten downside on a position the edge gate
        already authorized to open. It therefore does NOT require an edge PASS
        token (no new market exposure is created). It can never manufacture an
        edge or open a position; the most it does is protect principal already
        committed. A LIVE modify still passes the owner live-trading
        authorization, exactly like ``execute_order`` / ``close_position`` — see
        each bridge's implementation.

        Returns an :class:`OrderOutcome` (``EXECUTED`` on success, ``REJECTED``
        for an unknown ticket, a broker error, or an unauthorized live modify).
        """
        ...

    @abstractmethod
    def get_open_positions(self) -> list:
        """List all currently open positions."""
        ...

    def will_execute_real_order(self) -> bool:
        """Whether dispatching an order through this bridge would reach a real
        broker terminal (not a pure paper simulator / mailbox).

        Defaults to False; real bridges override. The execution guard consults
        this so the owner live-trading authorization is required for ANY real
        dispatch — independent of the ``config.live_mode`` flag, which a real,
        connected account does not depend on to fill orders.
        """
        return False


class MT5Bridge(BrokerBridge):
    """Real MetaTrader 5 connection via the MetaTrader5 Python package.

    Install: pip install MetaTrader5
    """

    def __init__(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        prefer_mt5: bool = True,
        runtime_config: Any = None,
    ):
        cfg = runtime_config or _effective_config()
        self._runtime_config = cfg
        self.login = login or cfg.mt5_login
        self.password = password or cfg.mt5_password
        self.server = server or cfg.mt5_server
        self.prefer_mt5 = prefer_mt5 if prefer_mt5 is not None else bool(getattr(cfg, "prefer_mt5", True))
        self.mt5_path = _resolve_mt5_terminal_path(cfg)
        self._mt5 = None
        self._connected = False
        self.last_symbol_resolution: dict[str, Any] = {}

    def _initialize(self):
        """Attempt to initialize MT5 connection."""
        self._connected = False
        try:
            _add_local_mt5_deps()
            import MetaTrader5 as mt5
            self._mt5 = mt5

            # MT5 may hang if terminal isn't running — catch everything
            try:
                # Bound the connect so a flaky/unreachable terminal fails fast
                # (default MT5 timeout is 60s, which would freeze callers).
                path_kw = {"timeout": MT5_INIT_TIMEOUT_MS}
                if self.mt5_path:
                    path_kw["path"] = self.mt5_path
                # Prefer ATTACHING to the already-running, already-logged-in
                # terminal (a bare initialize). Forcing a re-login with
                # login/password/server into a terminal that's already logged in
                # fails with "IPC send failed" (-10001); attaching succeeds.
                result = mt5.initialize(**path_kw)
                if self.login and self.login > 0:
                    if result:
                        acc = mt5.account_info()
                        # Only re-login if the terminal is on a DIFFERENT account
                        # than the one configured.
                        if acc is None or getattr(acc, "login", None) != self.login:
                            mt5.shutdown()
                            result = mt5.initialize(
                                login=self.login, password=self.password,
                                server=self.server, **path_kw,
                            )
                    else:
                        # Couldn't attach — fall back to a full credentialed login.
                        result = mt5.initialize(
                            login=self.login, password=self.password,
                            server=self.server, **path_kw,
                        )
            except Exception:
                return

            if result:
                self._connected = True
        except ImportError:
            pass

    def connect(self) -> bool:
        """Try to connect to MT5. Must be called explicitly."""
        if self._connected:
            return True
        self._initialize()
        return self._connected

    def is_connected(self) -> bool:
        """Check if MT5 is connected and terminal is ready."""
        if not self._connected or not self._mt5:
            return False
        try:
            info = self._mt5.terminal_info()
            return info is not None and info.connected
        except Exception:
            return False

    def will_execute_real_order(self) -> bool:
        """A connected LIVE (non-demo) MT5 terminal places real-money orders via
        ``order_send``. The execution guard requires owner live-trading
        authorization for these, regardless of ``config.live_mode``. A connected
        DEMO account is paper; a disconnected bridge falls back to simulation."""
        return self.is_connected() and not self.is_demo_account()

    def is_demo_account(self) -> bool:
        """Best-effort: is the connected MT5 account a DEMO (paper) account?

        Fail-closed in the LIVE direction: ONLY a positive MT5 trade_mode ==
        ACCOUNT_TRADE_MODE_DEMO match confirms demo. A live/contest/unknown
        trade_mode, an unavailable constant, or missing account info is treated
        as LIVE (return False) so the live-trading gate is required before any
        real ``order_send``. We deliberately do NOT infer demo from the broker's
        server/company name — those strings are broker/operator-controlled, so a
        live account whose server label merely contains "demo" must not be
        downgraded to paper and skip the gate.

        The owner can explicitly declare the account paper via the
        ``mt5_treat_account_as_demo`` config override (a deliberate, env-set
        loosening), in which case it is treated as demo.
        """
        cfg = getattr(self, "_runtime_config", None) or _effective_config()
        if bool(getattr(cfg, "mt5_treat_account_as_demo", False)):
            return True
        if not self.is_connected():
            return False
        try:
            info = self._mt5.account_info()
        except Exception:
            return False
        if info is None:
            return False
        trade_mode = getattr(info, "trade_mode", None)
        demo_const = getattr(self._mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        return demo_const is not None and trade_mode == demo_const

    def _live_gate_block(self, order_ref: str = "live-gate") -> Optional[OrderOutcome]:
        """Return a REJECTED outcome if a connected LIVE account is not
        owner-authorized for live trading, else None. Shared by every real
        ``order_send`` path (execute_order, close_position) so the live-trading
        gate is enforced uniformly — never just on one method."""
        if self.is_demo_account():
            return None
        from cas_forex import runtime_gates

        try:
            runtime_gates.require_authorized(
                "live_trading",
                getattr(self, "_runtime_config", None) or config,
            )
        except PermissionError as exc:
            return OrderOutcome(
                order_ref=order_ref,
                status=OrderStatus.REJECTED,
                error_message=f"Live-trading gate not authorized: {exc}",
                timestamp=utc_now(),
                broker_mode=self._broker_mode(),
                is_real_broker=False,
                is_demo_account=False,
                server=self.server,
                account_id_hash=self._account_id_hash(),
            )
        return None

    def _terminal_permission_block(self, order_ref: str = "mt5-permission") -> Optional[OrderOutcome]:
        """Reject before order_send when MT5 explicitly reports trade is disabled."""
        permission_state = self.order_send_permission_state()
        if not permission_state:
            return None
        reason = mt5_order_send_block_reason(permission_state)
        if reason is None:
            return None
        return OrderOutcome(
            order_ref=order_ref,
            status=OrderStatus.REJECTED,
            error_message=reason,
            timestamp=utc_now(),
            broker_mode=self._broker_mode(),
            is_real_broker=False,
            is_demo_account=(self.is_demo_account() if self.is_connected() else None),
            terminal_name="MetaTrader5",
            account_id_hash=self._account_id_hash(),
            server=self.server,
        )

    def get_account_info(self) -> Dict[str, float]:
        """Get current account state from MT5."""
        if not self.is_connected():
            return {"balance": 0, "equity": 0, "margin": 0, "margin_free": 0}

        try:
            info = self._mt5.account_info()
            if info is None:
                return {"balance": 0, "equity": 0, "margin": 0, "margin_free": 0}
            return {
                "balance": float(info.balance),
                "equity": float(info.equity),
                "margin": float(info.margin),
                "margin_free": float(info.margin_free),
                "leverage": int(info.leverage),
            }
        except Exception:
            return {"balance": 0, "equity": 0, "margin": 0, "margin_free": 0}

    def execute_order(self, order: BrokerOrderRequest) -> OrderOutcome:
        """Send order to MT5 and return outcome.

        In paper/live mode, sends real order. Falls back to simulation
        when MT5 is not connected (returns REJECTED or simulates).
        """
        if not self.is_connected():
            if _effective_config().live_mode:
                return OrderOutcome(
                    order_ref=order.order_id,
                    status=OrderStatus.REJECTED,
                    error_message="MT5 not connected in live mode",
                    timestamp=utc_now(),
                    broker_mode=BrokerMode.LIVE_MT5,
                    is_real_broker=False,
                )
            # Paper trading: simulate execution
            return self._simulate_execution(order)

        # Real-money guard AT THE BRIDGE: a connected LIVE (non-demo) account
        # fills real-money orders via order_send. Require the owner live-trading
        # gate here so a direct caller (one not routed through the execution
        # guard) still cannot place a real order without authorization. Demo
        # accounts are paper and pass through.
        gate_block = self._live_gate_block(order.order_id)
        if gate_block is not None:
            return gate_block
        permission_block = self._terminal_permission_block(order.order_id)
        if permission_block is not None:
            return permission_block
        is_demo_account = self.is_demo_account()

        try:
            request = self._build_mt5_request(order)
            result = self._mt5.order_send(request)

            if result is None:
                return OrderOutcome(
                    order_ref=order.order_id,
                    status=OrderStatus.REJECTED,
                    error_message="MT5 order_send returned None",
                    timestamp=utc_now(),
                    broker_mode=self._broker_mode(),
                    is_real_broker=True,
                    is_demo_account=is_demo_account,
                    server=self.server,
                    account_id_hash=self._account_id_hash(),
                    raw_request_hash=_hash_payload(request),
                    raw_request_snapshot=_request_payload(request),
                    broker_symbol=request.get("symbol"),
                    broker_symbol_resolution=dict(self.last_symbol_resolution or {}),
                )

            retcode = getattr(result, "retcode", None)
            order_ticket = getattr(result, "order", 0) or 0
            deal_ticket = getattr(result, "deal", 0) or 0
            ticket = order_ticket if order_ticket > 0 else (deal_ticket if deal_ticket > 0 else None)
            comment = getattr(result, "comment", "")

            # MT5 return codes
            if retcode == self._mt5.TRADE_RETCODE_DONE:
                status = OrderStatus.EXECUTED
                error = None
            elif retcode == self._mt5.TRADE_RETCODE_DONE_PARTIAL:
                status = OrderStatus.PARTIAL
                error = f"Partial fill: {comment}"
            elif retcode == self._mt5.TRADE_RETCODE_REJECT:
                status = OrderStatus.REJECTED
                error = f"Rejected: {comment}"
            elif retcode == self._mt5.TRADE_RETCODE_CANCEL:
                status = OrderStatus.CANCELLED
                error = f"Cancelled: {comment}"
            elif retcode == getattr(self._mt5, "TRADE_RETCODE_CLIENT_DISABLES_AT", 10027):
                status = OrderStatus.REJECTED
                error = f"AutoTrading disabled by client: {comment}"
            else:
                status = OrderStatus.REJECTED
                error = f"Unknown retcode {retcode}: {comment}"
            lock_reason = None
            if status == OrderStatus.REJECTED and "margin" in str(error or "").lower():
                lock_reason = BrokerLockReason.MARGIN_REJECT

            result_price = getattr(result, "price", None)
            fill_price = float(result_price) if result_price and result_price > 0 else None
            expected_price = order.price if order.price > 0 else fill_price
            slippage_pips = None
            if fill_price and expected_price:
                slippage_pips = abs(fill_price - expected_price) * pip_multiplier(order.symbol)
            commission = getattr(result, "commission", None)

            return OrderOutcome(
                order_ref=order.order_id,
                broker_ticket=ticket,
                status=status,
                filled_price=fill_price,
                slippage_pips=round(slippage_pips, 2) if slippage_pips else None,
                commission=float(commission) if commission is not None else None,
                timestamp=utc_now(),
                error_message=error,
                is_duplicate=False,
                is_abnormal_slippage=(
                    slippage_pips is not None
                    and slippage_pips > self._slippage_points_to_pips(
                        order.symbol,
                        order.slippage,
                    )
                ),
                broker_mode=self._broker_mode(),
                is_real_broker=True,
                is_demo_account=is_demo_account,
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
                raw_request_hash=_hash_payload(request),
                raw_request_snapshot=_request_payload(request),
                raw_response_hash=_hash_payload(_result_payload(result)),
                broker_symbol=request.get("symbol"),
                broker_symbol_resolution=dict(self.last_symbol_resolution or {}),
                lock_reason=lock_reason,
            )

        except ValueError as e:
            lock_reason = None
            if "volume" in str(e).lower():
                lock_reason = BrokerLockReason.VOLUME_MISMATCH
            elif "symbol" in str(e).lower():
                lock_reason = BrokerLockReason.SYMBOL_MISMATCH
            return OrderOutcome(
                order_ref=order.order_id,
                status=OrderStatus.REJECTED,
                error_message=str(e),
                timestamp=utc_now(),
                broker_mode=self._broker_mode(),
                is_real_broker=False,
                is_demo_account=is_demo_account,
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
                broker_symbol_resolution=dict(self.last_symbol_resolution or {}),
                lock_reason=lock_reason,
            )
        except Exception as e:
            return OrderOutcome(
                order_ref=order.order_id,
                status=OrderStatus.REJECTED,
                error_message=str(e),
                timestamp=utc_now(),
                broker_mode=self._broker_mode(),
                is_real_broker=True,
                is_demo_account=is_demo_account,
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
            )

    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        """Close a position by ticket number.

        A close is a real ``order_send``, so it is gated the same way as
        ``execute_order``: on a connected LIVE (non-demo) account the owner
        live-trading gate must be authorized, else the close is refused.
        """
        if not self.is_connected():
            return False
        if self._live_gate_block() is not None:
            return False
        if self._terminal_permission_block(f"close-{ticket}") is not None:
            return False
        try:
            # Get position to determine close direction
            positions = self._mt5.positions_get(ticket=ticket)
            if not positions:
                return False
            pos = positions[0]

            symbol = pos.symbol
            close_volume = volume or pos.volume
            close_type = (
                self._mt5.ORDER_TYPE_SELL
                if pos.type == self._mt5.POSITION_TYPE_BUY
                else self._mt5.ORDER_TYPE_BUY
            )

            price = self._mt5.symbol_info_tick(symbol)
            close_price = price.bid if close_type == self._mt5.ORDER_TYPE_SELL else price.ask

            request = {
                "action": self._mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": close_volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": 30,
                "magic": 20260601,
                "comment": "CAS_CLOSE",
                "type_time": getattr(self._mt5, "ORDER_TIME_GTC", 0),
                "type_filling": self._symbol_filling_mode(symbol),
            }

            result = self._mt5.order_send(request)
            return result is not None and result.retcode == self._mt5.TRADE_RETCODE_DONE

        except Exception:
            return False

    def modify_position(
        self,
        ticket: int,
        *,
        stop_loss: float,
        take_profit: Optional[float] = None,
    ) -> OrderOutcome:
        """Amend an open MT5 position's SL/TP via ``TRADE_ACTION_SLTP``.

        Risk-reducing breakeven-lock primitive (see the ABC docstring). A modify
        on a connected LIVE (non-demo) account touches a real position, so it is
        gated EXACTLY like ``execute_order`` / ``close_position``: the owner
        live-trading gate must be authorized, else the modify is REJECTED. Demo
        accounts are paper and pass through. ``take_profit=None`` preserves the
        position's existing TP.
        """
        order_ref = f"modify-{ticket}"
        if not self.is_connected():
            return OrderOutcome(
                order_ref=order_ref,
                status=OrderStatus.REJECTED,
                error_message="MT5 not connected",
                timestamp=utc_now(),
                broker_mode=self._broker_mode(),
                is_real_broker=False,
                server=self.server,
                account_id_hash=self._account_id_hash(),
            )
        gate_block = self._live_gate_block(order_ref)
        if gate_block is not None:
            return gate_block
        permission_block = self._terminal_permission_block(order_ref)
        if permission_block is not None:
            return permission_block
        is_demo_account = self.is_demo_account()
        try:
            positions = self._mt5.positions_get(ticket=ticket)
            if not positions:
                return OrderOutcome(
                    order_ref=order_ref,
                    status=OrderStatus.REJECTED,
                    error_message=f"No open position for ticket {ticket}",
                    timestamp=utc_now(),
                    broker_mode=self._broker_mode(),
                    is_real_broker=True,
                    is_demo_account=is_demo_account,
                    terminal_name="MetaTrader5",
                    account_id_hash=self._account_id_hash(),
                    server=self.server,
                )
            pos = positions[0]
            # take_profit=None means "leave TP as-is": carry the position's
            # current TP into the request so the modify only moves the stop.
            tp_value = float(take_profit) if take_profit is not None else float(
                getattr(pos, "tp", 0.0) or 0.0
            )
            request = {
                "action": self._mt5.TRADE_ACTION_SLTP,
                "symbol": pos.symbol,
                "position": ticket,
                "sl": float(stop_loss),
                "tp": tp_value,
                "magic": getattr(pos, "magic", 20260601),
                "comment": "CAS_BREAKEVEN",
            }
            result = self._mt5.order_send(request)
            if result is None:
                return OrderOutcome(
                    order_ref=order_ref,
                    status=OrderStatus.REJECTED,
                    error_message="MT5 order_send returned None",
                    timestamp=utc_now(),
                    broker_mode=self._broker_mode(),
                    is_real_broker=True,
                    is_demo_account=is_demo_account,
                    terminal_name="MetaTrader5",
                    account_id_hash=self._account_id_hash(),
                    server=self.server,
                    raw_request_hash=_hash_payload(request),
                    raw_request_snapshot=_request_payload(request),
                )
            retcode = getattr(result, "retcode", None)
            comment = getattr(result, "comment", "")
            done = (
                retcode == self._mt5.TRADE_RETCODE_DONE
                or retcode == getattr(self._mt5, "TRADE_RETCODE_DONE_PARTIAL", None)
            )
            return OrderOutcome(
                order_ref=order_ref,
                broker_ticket=ticket,
                status=OrderStatus.EXECUTED if done else OrderStatus.REJECTED,
                error_message=None if done else f"Modify failed (retcode {retcode}): {comment}",
                timestamp=utc_now(),
                broker_mode=self._broker_mode(),
                is_real_broker=True,
                is_demo_account=is_demo_account,
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
                raw_request_hash=_hash_payload(request),
                raw_request_snapshot=_request_payload(request),
                raw_response_hash=_hash_payload(_result_payload(result)),
            )
        except Exception as e:
            return OrderOutcome(
                order_ref=order_ref,
                status=OrderStatus.REJECTED,
                error_message=str(e),
                timestamp=utc_now(),
                broker_mode=self._broker_mode(),
                is_real_broker=True,
                is_demo_account=is_demo_account,
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
            )

    def order_send_permission_state(self) -> dict[str, Any]:
        """Current terminal/account ability to accept ``order_send``.

        This is terminal capability only. It does not authorize CAS live
        trading and does not call ``order_send``.
        """

        if self._mt5 is None:
            return {}
        try:
            return build_mt5_permission_state(
                self._mt5.terminal_info(),
                self._mt5.account_info(),
                is_demo=self.is_demo_account(),
            )
        except Exception:
            return {}

    def _slippage_points_to_pips(self, symbol: str, points: int) -> float:
        """Convert MT5 deviation points to forex pips for evidence checks."""
        point_size = None
        if self._mt5 is not None and hasattr(self._mt5, "symbol_info"):
            resolved = str((self.last_symbol_resolution or {}).get("selected_symbol") or "")
            candidates = [resolved, symbol, symbol.replace("/", "")]
            for candidate in [value for value in candidates if value]:
                try:
                    info = self._mt5.symbol_info(candidate)
                    point_size = getattr(info, "point", None) if info is not None else None
                except Exception:
                    point_size = None
                if point_size and point_size > 0:
                    break

        if point_size and point_size > 0:
            return float(points) * float(point_size) * pip_multiplier(symbol)
        return float(points) / 10.0

    def _broker_mode(self) -> BrokerMode:
        return BrokerMode.PAPER_MT5 if self.is_demo_account() else BrokerMode.LIVE_MT5

    def _account_id_hash(self) -> Optional[str]:
        if not self.login:
            return None
        return _hash_payload({"login": self.login, "server": self.server})[:16]

    def get_open_positions(self) -> list:
        """List all currently open CAS Forex positions."""
        if not self.is_connected():
            return []
        try:
            positions = self._mt5.positions_get()
            if not positions:
                return []
            return [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": p.volume,
                    "open_price": p.price_open,
                    "current_price": p.price_current,
                    "stop_loss": getattr(p, "sl", 0.0),
                    "take_profit": getattr(p, "tp", 0.0),
                    "profit": p.profit,
                    "swap": p.swap,
                    "comment": p.comment,
                    "opened_at_iso": _position_opened_at_iso(p),
                }
                for p in positions
                if "CAS" in (p.comment or "")
            ]
        except Exception:
            return []

    def get_all_open_positions(self) -> list:
        """List every open MT5 position, including manual/outside-CAS rows."""
        if not self.is_connected():
            return []
        try:
            positions = self._mt5.positions_get()
            if not positions:
                return []
            return [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": p.volume,
                    "open_price": p.price_open,
                    "current_price": p.price_current,
                    "stop_loss": getattr(p, "sl", 0.0),
                    "take_profit": getattr(p, "tp", 0.0),
                    "profit": p.profit,
                    "swap": getattr(p, "swap", 0.0),
                    "comment": getattr(p, "comment", ""),
                    "opened_at_iso": _position_opened_at_iso(p),
                }
                for p in positions
            ]
        except Exception:
            return []

    def get_pending_orders(self) -> list:
        """List pending MT5 orders for emergency review/cancel."""
        if not self.is_connected():
            return []
        try:
            orders = self._mt5.orders_get()
            if not orders:
                return []
            return [
                {
                    "ticket": getattr(order, "ticket", getattr(order, "order", 0)),
                    "symbol": getattr(order, "symbol", ""),
                    "type": getattr(order, "type", ""),
                    "volume": getattr(order, "volume_current", getattr(order, "volume_initial", 0.0)),
                    "price_open": getattr(order, "price_open", getattr(order, "price", 0.0)),
                    "comment": getattr(order, "comment", ""),
                }
                for order in orders
            ]
        except Exception:
            return []

    def cancel_pending_order(self, ticket: int) -> bool:
        """Cancel one pending order by ticket.

        A pending-order cancel changes broker state, so connected LIVE accounts
        use the same owner live-trading and terminal-permission gate as
        ``execute_order`` and ``close_position`` before ``order_send``.
        """
        if not self.is_connected():
            return False
        order_ref = f"cancel-{ticket}"
        if self._live_gate_block(order_ref) is not None:
            return False
        if self._terminal_permission_block(order_ref) is not None:
            return False
        try:
            remove_action = getattr(self._mt5, "TRADE_ACTION_REMOVE", None)
            if remove_action is None:
                return False
            request = {
                "action": remove_action,
                "order": int(ticket),
                "magic": 20260601,
                "comment": "CAS_CANCEL_PENDING",
            }
            result = self._mt5.order_send(request)
            if result is None:
                return False
            done = (
                getattr(result, "retcode", None) == getattr(self._mt5, "TRADE_RETCODE_DONE", None)
                or getattr(result, "retcode", None) == getattr(self._mt5, "TRADE_RETCODE_DONE_PARTIAL", None)
            )
            return bool(done)
        except Exception:
            return False

    def shutdown(self):
        """Cleanly shut down MT5 connection."""
        if self._mt5:
            try:
                self._mt5.shutdown()
            except Exception:
                pass
            self._connected = False

    def _build_mt5_request(self, order: BrokerOrderRequest) -> dict:
        """Convert CAS order to MT5 request dictionary."""
        mt5 = self._mt5

        order_type_map = {
            (Direction.LONG, "MARKET"): mt5.ORDER_TYPE_BUY,
            (Direction.SHORT, "MARKET"): mt5.ORDER_TYPE_SELL,
            (Direction.LONG, "LIMIT"): mt5.ORDER_TYPE_BUY_LIMIT,
            (Direction.SHORT, "LIMIT"): mt5.ORDER_TYPE_SELL_LIMIT,
            (Direction.LONG, "STOP"): mt5.ORDER_TYPE_BUY_STOP,
            (Direction.SHORT, "STOP"): mt5.ORDER_TYPE_SELL_STOP,
        }
        ot = order_type_map.get(
            (order.direction, order.order_type.value.upper()), mt5.ORDER_TYPE_BUY
        )

        resolution = resolve_broker_symbol(
            order.symbol,
            broker=mt5,
            overrides=getattr(_effective_config(), "mt5_symbol_overrides", ""),
        )
        self.last_symbol_resolution = resolution.as_dict()
        if not resolution.selected_symbol:
            raise ValueError(resolution.detail or f"MT5 symbol unresolved for {order.symbol}")
        symbol = resolution.selected_symbol
        symbol_info = self._safe_symbol_info(symbol)
        self._validate_broker_contract(order, broker_symbol_value=symbol, info=symbol_info)

        # Get current price for market orders
        price = order.price
        if price == 0.0:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                price = tick.ask if order.direction == Direction.LONG else tick.bid

        sl, tp = self._broker_valid_market_stops(
            order,
            broker_symbol_value=symbol,
            execution_price=float(price) if price > 0 else 0.0,
            symbol_info=symbol_info,
        )

        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(order.volume),
            "type": ot,
            "price": float(price) if price > 0 else 0.0,
            "sl": sl,
            "tp": tp,
            "deviation": order.slippage,
            "magic": order.magic_number,
            "comment": order.comment[:27],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._symbol_filling_mode(symbol),
        }

    def _broker_valid_market_stops(
        self,
        order: BrokerOrderRequest,
        *,
        broker_symbol_value: str,
        execution_price: float,
        symbol_info: Any = None,
    ) -> tuple[float, float]:
        """Return SL/TP widened to the broker's minimum market stop distance.

        MT5 rejects market orders with retcode 10016 ("Invalid stops") when the
        submitted SL/TP are closer than the symbol's trade_stops_level or inside
        the freeze level. Manual index defaults can be valid CAS geometry while
        still too close for a specific broker symbol, so normalize at the last
        broker-aware point before order_send.
        """
        sl = float(order.stop_loss)
        tp = float(order.take_profit)
        if execution_price <= 0:
            return sl, tp
        info = symbol_info if symbol_info is not None else self._safe_symbol_info(broker_symbol_value)
        point = _positive_float(getattr(info, "point", None)) or price_unit_size(order.symbol)
        stops_level = _positive_float(getattr(info, "trade_stops_level", None))
        if stops_level is None:
            stops_level = _positive_float(getattr(info, "stops_level", None)) or 0.0
        freeze_level = _positive_float(getattr(info, "trade_freeze_level", None)) or 0.0
        min_distance = max(stops_level, freeze_level) * point
        required = max(min_distance + point, point)
        if order.direction == Direction.LONG:
            if sl >= execution_price:
                raise ValueError(
                    "MT5 market price invalidates order geometry: "
                    f"LONG {order.symbol} requires stop_loss < current ask < take_profit "
                    f"(stop_loss={sl}, current={execution_price}, take_profit={tp})"
                )
            if tp <= execution_price:
                raise ValueError(
                    "MT5 market price invalidates order geometry: "
                    f"LONG {order.symbol} requires stop_loss < current ask < take_profit "
                    f"(stop_loss={sl}, current={execution_price}, take_profit={tp})"
                )
            if (execution_price - sl) < required:
                sl = execution_price - required
            if (tp - execution_price) < required:
                tp = execution_price + required
        else:
            if sl <= execution_price:
                raise ValueError(
                    "MT5 market price invalidates order geometry: "
                    f"SHORT {order.symbol} requires take_profit < current bid < stop_loss "
                    f"(take_profit={tp}, current={execution_price}, stop_loss={sl})"
                )
            if tp >= execution_price:
                raise ValueError(
                    "MT5 market price invalidates order geometry: "
                    f"SHORT {order.symbol} requires take_profit < current bid < stop_loss "
                    f"(take_profit={tp}, current={execution_price}, stop_loss={sl})"
                )
            if (sl - execution_price) < required:
                sl = execution_price + required
            if (execution_price - tp) < required:
                tp = execution_price - required
        sl = self._round_broker_price(order.symbol, sl, info)
        tp = self._round_broker_price(order.symbol, tp, info)
        return sl, tp

    def _safe_symbol_info(self, broker_symbol_value: str) -> Any:
        try:
            return self._mt5.symbol_info(broker_symbol_value) if self._mt5 is not None else None
        except Exception:
            return None

    def _validate_broker_contract(
        self,
        order: BrokerOrderRequest,
        *,
        broker_symbol_value: str,
        info: Any,
    ) -> None:
        """Reject order sizes the connected MT5 symbol contract cannot accept."""
        if info is None:
            return
        mt5 = self._mt5
        disabled_const = getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", None) if mt5 is not None else None
        trade_mode = getattr(info, "trade_mode", None)
        if disabled_const is not None and trade_mode == disabled_const:
            raise ValueError(f"MT5 broker symbol reject: {broker_symbol_value} is disabled for trading.")

        volume = float(order.volume)
        min_lot = _positive_float(getattr(info, "volume_min", None))
        max_lot = _positive_float(getattr(info, "volume_max", None))
        step = _positive_float(getattr(info, "volume_step", None))
        if min_lot is not None and volume < min_lot - 1e-9:
            raise ValueError(
                "MT5 broker contract reject: "
                f"{broker_symbol_value} volume {volume:g} is below broker minimum {min_lot:g}."
            )
        if max_lot is not None and volume > max_lot + 1e-9:
            raise ValueError(
                "MT5 broker contract reject: "
                f"{broker_symbol_value} volume {volume:g} exceeds broker maximum {max_lot:g}."
            )
        if step is not None and not _volume_matches_step(volume, min_lot or 0.0, step):
            raise ValueError(
                "MT5 broker contract reject: "
                f"{broker_symbol_value} volume {volume:g} does not align with broker volume_step {step:g}."
            )

    @staticmethod
    def _round_broker_price(cas_symbol: str, price: float, info: Any = None) -> float:
        digits = getattr(info, "digits", None)
        try:
            if digits is not None:
                return round(float(price), int(digits))
        except (TypeError, ValueError):
            pass
        return float(round_price(cas_symbol, float(price)))

    def _symbol_filling_mode(self, symbol: str) -> int:
        """Return the MT5 order filling constant supported by this symbol."""

        mt5 = self._mt5
        fallback = getattr(mt5, "ORDER_FILLING_IOC", 1)
        try:
            info = mt5.symbol_info(symbol)
        except Exception:
            info = None
        raw = getattr(info, "filling_mode", None) if info is not None else None
        flag_to_order = {
            1: getattr(mt5, "ORDER_FILLING_FOK", fallback),
            2: getattr(mt5, "ORDER_FILLING_IOC", fallback),
            4: getattr(mt5, "ORDER_FILLING_RETURN", fallback),
        }
        if raw in flag_to_order:
            return flag_to_order[raw]
        constants = [
            value
            for value in (
                getattr(mt5, "ORDER_FILLING_FOK", None),
                getattr(mt5, "ORDER_FILLING_IOC", None),
                getattr(mt5, "ORDER_FILLING_RETURN", None),
            )
            if value is not None
        ]
        if raw is not None and raw in constants:
            return int(raw)
        return fallback

    def _simulate_execution(self, order: BrokerOrderRequest) -> OrderOutcome:
        """Simulate order execution for paper trading."""
        fill_price = order.price if order.price > 0 else (
            order.stop_loss * 1.001 if order.direction == Direction.LONG
            else order.stop_loss * 0.999
        )
        return OrderOutcome(
            order_ref=order.order_id,
            broker_ticket=hash(order.order_id) % 100000000,
            status=OrderStatus.EXECUTED,
            filled_price=fill_price,
            slippage_pips=0.02,
            timestamp=utc_now(),
            is_duplicate=False,
            is_abnormal_slippage=False,
            broker_mode=BrokerMode.SIMULATED,
            is_real_broker=False,
            raw_request_hash=_hash_payload(order.model_dump(mode="json")),
        )


class MT4EABridge(BrokerBridge):
    """Mailbox-based MT4 Expert Advisor bridge for paper proof only."""

    def __init__(
        self,
        mailbox_dir: Optional[str] = None,
        *,
        enabled: Optional[bool] = None,
        runtime_config: Any = None,
    ):
        from cas_forex.mt4_control import resolve_mt4_control

        ctrl = resolve_mt4_control(runtime_config)
        resolved_dir = mailbox_dir or ctrl.mailbox_dir
        self.mailbox_dir = Path(resolved_dir)
        self._enabled_override = enabled
        self._runtime_config = runtime_config
        self.orders_path = self.mailbox_dir / "orders.jsonl"
        self.acks_path = self.mailbox_dir / "acks.jsonl"
        self.heartbeat_path = self.mailbox_dir / "heartbeat.json"
        self.positions_path = self.mailbox_dir / "positions.jsonl"

    def connect(self) -> bool:
        from cas_forex.mt4_control import resolve_mt4_control

        cfg = self._runtime_config or _effective_config()
        route_enabled = (
            bool(self._enabled_override)
            if self._enabled_override is not None
            else resolve_mt4_control(cfg).enabled
        )
        if not route_enabled or cfg.live_mode or not cfg.paper_trading:
            return False
        if not self.is_connected():
            return False
        self.mailbox_dir.mkdir(parents=True, exist_ok=True)
        return True

    def is_connected(self) -> bool:
        # Connected only when the EA heartbeat is present AND fresh — a stale
        # heartbeat from a dead EA must not read as connected.
        from cas_forex.mt4_control import read_ea_heartbeat

        heartbeat = read_ea_heartbeat(self.mailbox_dir)
        return bool(heartbeat["present"] and heartbeat["fresh"])

    def execute_order(self, order: BrokerOrderRequest) -> OrderOutcome:
        if not self.connect():
            return OrderOutcome(
                order_ref=order.order_id,
                status=OrderStatus.REJECTED,
                error_message=(
                    "MT4 bridge requires enabled paper mailbox mode and a fresh "
                    "EA heartbeat before demo/paper commands can be dispatched"
                ),
                broker_mode=BrokerMode.PAPER_MT4,
                is_real_broker=False,
            )
        payload = {
            "order": order.model_dump(mode="json"),
            "intent_hash": _hash_payload(order.model_dump(mode="json")),
            "created_at": utc_now().isoformat(),
        }
        with self.orders_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
        # Also write the EA-readable command file the running EA actually polls
        # (commands/<id>.json). orders.jsonl above stays as a local audit log.
        # Best-effort: a mailbox-write hiccup must not fail the dispatch.
        try:
            from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge

            MT4MailboxBridge(self.mailbox_dir).write_order_intent(
                order, broker_mode=BrokerMode.PAPER_MT4, live_authorized=False
            )
        except Exception:
            pass
        return OrderOutcome(
            order_ref=order.order_id,
            status=OrderStatus.PENDING,
            broker_mode=BrokerMode.PAPER_MT4,
            is_real_broker=False,
            terminal_name="MetaTrader4-EA",
            raw_request_hash=payload["intent_hash"],
        )

    def get_account_info(self) -> Dict[str, float]:
        return {"balance": 0, "equity": 0, "margin": 0, "margin_free": 0}

    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        return False

    def modify_position(
        self,
        ticket: int,
        *,
        stop_loss: float,
        take_profit: Optional[float] = None,
    ) -> OrderOutcome:
        """Write a MODIFY_SL mailbox command to move an open position's SL/TP.

        Mirrors ``execute_order``'s mailbox-command pattern (a new MODIFY_SL
        command file the running EA polls). This is the breakeven principal-lock
        primitive: risk-reducing, so it does NOT require an edge token. The
        EA-side handler that reads MODIFY_SL and calls ``OrderModify`` is OUT OF
        SCOPE (the running CASForexBridgeEA must add a MODIFY_SL branch).

        The mailbox itself is paper/demo-only (``connect`` refuses when
        ``config.live_mode``), so this path can never move real money; it returns
        PENDING because the EA fills asynchronously, exactly like
        ``execute_order``.
        """
        if not self.connect():
            return OrderOutcome(
                order_ref=f"modify-{ticket}",
                status=OrderStatus.REJECTED,
                error_message=(
                    "MT4 bridge requires enabled paper mailbox mode and a fresh "
                    "EA heartbeat before demo/paper commands can be dispatched"
                ),
                broker_mode=BrokerMode.PAPER_MT4,
                is_real_broker=False,
            )
        from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge

        command = MT4MailboxBridge(self.mailbox_dir).write_modify_intent(
            ticket,
            stop_loss=stop_loss,
            take_profit=take_profit,
            broker_mode=BrokerMode.PAPER_MT4,
            live_authorized=False,
        )
        return OrderOutcome(
            order_ref=command["command_id"],
            broker_ticket=ticket,
            status=OrderStatus.PENDING,
            broker_mode=BrokerMode.PAPER_MT4,
            is_real_broker=False,
            terminal_name="MetaTrader4-EA",
            raw_request_hash=command["raw_request_hash"],
        )

    def get_open_positions(self) -> list:
        if not self.positions_path.exists():
            return []
        positions = []
        for line in self.positions_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    positions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return positions


class SimulatedBrokerBridge(BrokerBridge):
    """Pure simulation bridge for backtesting and paper trading.

    Generates deterministic outcomes and broker-like rejects. Used when MT5 is
    unavailable or when tests need a safe paper-mode broker.
    """

    def __init__(
        self,
        market_open: bool = True,
        disabled_symbols: Optional[set[str]] = None,
        current_spread_pips: float = 1.0,
        max_spread_pips: float = 5.0,
        simulated_slippage_pips: float = 0.02,
        max_slippage_pips: float = 3.0,
        min_lot: float = 0.01,
        max_lot: float = 1.0,
        min_stop_distance_pips: float = 5.0,
        margin_per_lot: float = 1000.0,
        state_path: Optional[Path | str] = None,
        closed_ticket_ledger_path: Optional[Path | str] = None,
    ):
        self._positions: Dict[int, dict] = {}
        self._close_events: list[dict[str, Any]] = []
        self._void_events: list[dict[str, Any]] = []
        self._order_reference_prices: Dict[str, float] = {}
        self._ticket_counter = 100000
        self._balance = 10000.0
        self._equity = 10000.0
        self.market_open = market_open
        self.disabled_symbols = disabled_symbols or set()
        self.current_spread_pips = current_spread_pips
        self.max_spread_pips = max_spread_pips
        self.simulated_slippage_pips = simulated_slippage_pips
        self.max_slippage_pips = max_slippage_pips
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.min_stop_distance_pips = min_stop_distance_pips
        self.margin_per_lot = margin_per_lot
        self._state_path = Path(state_path) if state_path is not None else None
        self._closed_ticket_ledger_path = (
            Path(closed_ticket_ledger_path)
            if closed_ticket_ledger_path is not None
            else None
        )
        self._state_lock = threading.RLock()
        self._load_persistent_state()

    def is_connected(self) -> bool:
        return True

    def get_account_info(self) -> Dict[str, float]:
        self._refresh_persistent_state()
        return {
            "balance": self._balance,
            "equity": self._equity,
            "margin": 0.0,
            "margin_free": self._equity,
            "leverage": 100,
        }

    def execute_order(self, order: BrokerOrderRequest) -> OrderOutcome:
        self._refresh_persistent_state()
        rejection = self._reject_reason(order)
        if rejection is not None:
            message, lock_reason = rejection
            return self._rejected(order, message, lock_reason=lock_reason)

        existing = next(
            (
                (ticket, position)
                for ticket, position in self._positions.items()
                if position["order"].order_id == order.order_id
            ),
            None,
        )
        if existing is not None:
            ticket, position = existing
            return OrderOutcome(
                order_ref=order.order_id,
                broker_ticket=ticket,
                status=OrderStatus.REJECTED,
                filled_price=float(position["fill_price"]),
                error_message="Simulated broker duplicate order_id rejected",
                is_duplicate=True,
                broker_mode=BrokerMode.SIMULATED,
                is_real_broker=False,
                raw_request_hash=_hash_payload(order.model_dump(mode="json")),
            )

        partial = order.volume > self.max_lot
        filled_volume = min(order.volume, self.max_lot)
        ticket = self._stable_ticket(order.order_id)

        reference_price = self._order_reference_prices.pop(str(order.order_id), None)
        fill_price = order.price if order.price > 0 else (
            float(reference_price)
            if reference_price is not None and float(reference_price) > 0
            else (
                order.stop_loss * 1.0005
                if order.direction == Direction.LONG
                else order.stop_loss * 0.9995
            )
        )
        slip = self.simulated_slippage_pips / pip_multiplier(order.symbol)
        fill_price = fill_price + slip if order.direction == Direction.LONG else fill_price - slip

        self._positions[ticket] = {
            "order": order,
            "fill_price": fill_price,
            "volume": filled_volume,
            "timestamp": utc_now(),
        }
        self._persist_state()

        return OrderOutcome(
            order_ref=order.order_id,
            broker_ticket=ticket,
            status=OrderStatus.PARTIAL if partial else OrderStatus.EXECUTED,
            filled_price=fill_price,
            slippage_pips=self.simulated_slippage_pips,
            timestamp=utc_now(),
            is_duplicate=False,
            is_abnormal_slippage=self.simulated_slippage_pips > self.max_slippage_pips,
            broker_mode=BrokerMode.SIMULATED,
            is_real_broker=False,
            raw_request_hash=_hash_payload(order.model_dump(mode="json")),
            raw_response_hash=_hash_payload({
                "ticket": ticket,
                "fill_price": fill_price,
                "filled_volume": filled_volume,
                "partial": partial,
            }),
        )

    def _stable_ticket(self, order_id: str) -> int:
        """Stable positive ticket with collision probing across this bridge.

        A fresh simulator used to restart at ticket 100000 every cycle, causing
        unrelated paper attempts to collapse into one outcome-ledger identity.
        Binding the ticket to the order id keeps attribution stable even if the
        process later recreates the bridge.
        """

        digest = hashlib.sha256(str(order_id).encode("utf-8")).hexdigest()
        ticket = 100_000_000 + (int(digest[:16], 16) % 900_000_000)
        while ticket in self._positions:
            existing = self._positions[ticket]["order"].order_id
            if existing == order_id:
                return ticket
            ticket = 100_000_000 + ((ticket - 100_000_000 + 1) % 900_000_000)
        self._ticket_counter = max(self._ticket_counter, ticket + 1)
        return ticket

    def _reject_reason(self, order: BrokerOrderRequest) -> Optional[Tuple[str, Optional[BrokerLockReason]]]:
        if not self.market_open:
            return "Simulated broker reject: market closed", None
        if order.symbol in self.disabled_symbols:
            return "Simulated broker reject: symbol disabled", BrokerLockReason.SYMBOL_MISMATCH
        if self.current_spread_pips > self.max_spread_pips:
            return "Simulated broker reject: spread too wide", None
        if order.volume < self.min_lot:
            return "Simulated broker reject: volume below min lot", BrokerLockReason.VOLUME_MISMATCH
        if self.simulated_slippage_pips > self.max_slippage_pips:
            return "Simulated broker reject: slippage exceeds broker tolerance", BrokerLockReason.FILL_PRICE_MISMATCH
        if self._margin_required(order) > self._equity:
            return "Simulated broker reject: insufficient margin", BrokerLockReason.MARGIN_REJECT
        effective_price = order.price if order.price > 0 else (
            (order.stop_loss + order.take_profit) / 2.0
        )
        stop_distance = abs(effective_price - order.stop_loss) * pip_multiplier(order.symbol)
        if stop_distance < self.min_stop_distance_pips:
            return "Simulated broker reject: stop distance below minimum", None
        return None

    def _margin_required(self, order: BrokerOrderRequest) -> float:
        return order.volume * self.margin_per_lot

    def _rejected(
        self,
        order: BrokerOrderRequest,
        message: str,
        lock_reason: Optional[BrokerLockReason] = None,
    ) -> OrderOutcome:
        return OrderOutcome(
            order_ref=order.order_id,
            status=OrderStatus.REJECTED,
            error_message=message,
            broker_mode=BrokerMode.SIMULATED,
            is_real_broker=False,
            raw_request_hash=_hash_payload(order.model_dump(mode="json")),
            lock_reason=lock_reason,
        )

    def modify_position(
        self,
        ticket: int,
        *,
        stop_loss: float,
        take_profit: Optional[float] = None,
    ) -> OrderOutcome:
        """Move the in-memory open position's SL (and optionally TP).

        Pure-paper breakeven-lock primitive: it amends the protective stop on a
        position THIS simulator already opened. No edge token is required (it is
        risk-reducing and opens no new exposure), and there is no real money to
        move. An unknown ticket is REJECTED. The new SL/TP are recorded on the
        stored position as overrides so subsequent ``get_open_positions`` reflect
        the locked stop.
        """
        self._refresh_persistent_state()
        order_ref = f"modify-{ticket}"
        pos = self._positions.get(ticket)
        if pos is None:
            return OrderOutcome(
                order_ref=order_ref,
                status=OrderStatus.REJECTED,
                error_message=f"No open position for ticket {ticket}",
                broker_mode=BrokerMode.SIMULATED,
                is_real_broker=False,
            )
        pos["stop_loss"] = float(stop_loss)
        if take_profit is not None:
            pos["take_profit"] = float(take_profit)
        self._persist_state()
        return OrderOutcome(
            order_ref=order_ref,
            broker_ticket=ticket,
            status=OrderStatus.EXECUTED,
            timestamp=utc_now(),
            broker_mode=BrokerMode.SIMULATED,
            is_real_broker=False,
            raw_request_hash=_hash_payload(
                {
                    "ticket": ticket,
                    "stop_loss": float(stop_loss),
                    "take_profit": (None if take_profit is None else float(take_profit)),
                }
            ),
        )

    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        self._refresh_persistent_state()
        pos = self._positions.get(ticket)
        if pos is None:
            return False
        current_volume = float(pos.get("volume", pos["order"].volume))
        if volume is None or float(volume) >= current_volume - 1e-12:
            self._record_close_event(
                ticket,
                pos,
                closed_volume=current_volume,
                remaining_volume=0.0,
                full_close=True,
            )
            del self._positions[ticket]
            self._persist_state()
            return True
        close_volume = float(volume)
        if close_volume <= 0:
            return False
        remaining = round(current_volume - close_volume, 8)
        self._record_close_event(
            ticket,
            pos,
            closed_volume=close_volume,
            remaining_volume=remaining,
            full_close=False,
        )
        pos["volume"] = remaining
        self._persist_state()
        return True

    def set_reference_price(self, ticket: int, price: float) -> bool:
        """Attach the fresh management quote used for a simulated close."""

        self._refresh_persistent_state()
        pos = self._positions.get(int(ticket))
        if pos is None or float(price) <= 0:
            return False
        pos["current_price"] = float(price)
        self._persist_state()
        return True

    def set_order_reference_price(self, order_id: str, price: float) -> bool:
        """Attach the fresh side-specific quote used for a simulated market fill."""

        try:
            parsed = float(price)
        except (TypeError, ValueError):
            return False
        if not str(order_id or "").strip() or parsed <= 0:
            return False
        self._order_reference_prices[str(order_id)] = parsed
        return True

    def cancel_pending_order(self, ticket: int) -> bool:
        return False

    def get_open_positions(self) -> list:
        self._refresh_persistent_state()
        return [
            {
                "ticket": t,
                "symbol": p["order"].symbol,
                "type": p["order"].direction.value,
                "volume": p.get("volume", p["order"].volume),
                "open_price": p["fill_price"],
                "current_price": p.get("current_price", p["fill_price"]),
                "stop_loss": p.get("stop_loss", p["order"].stop_loss),
                "take_profit": p.get("take_profit", p["order"].take_profit),
                "profit": 0.0,
                "swap": 0.0,
                "comment": p["order"].comment,
                "opened_at_iso": (
                    p.get("timestamp").isoformat()
                    if isinstance(p.get("timestamp"), datetime)
                    else None
                ),
            }
            for t, p in self._positions.items()
        ]

    def get_all_open_positions(self) -> list:
        return self.get_open_positions()

    def get_pending_orders(self) -> list:
        return []

    def void_position(
        self,
        ticket: int,
        *,
        reason: str,
        evidence: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        """Quarantine a corrupted paper position without fabricating a close/P&L."""

        self._refresh_persistent_state()
        try:
            key = int(ticket)
        except (TypeError, ValueError):
            return False
        position = self._positions.pop(key, None)
        if position is None:
            return False
        order = position["order"]
        self._void_events.append(
            {
                "broker_ticket": str(key),
                "order_id": order.order_id,
                "decision_ref": order.decision_ref,
                "symbol": order.symbol,
                "direction": order.direction.value,
                "volume": float(position.get("volume", order.volume)),
                "fill_price": float(position["fill_price"]),
                "opened_at": (
                    position["timestamp"].isoformat()
                    if isinstance(position.get("timestamp"), datetime)
                    else str(position.get("timestamp") or "")
                ),
                "voided_at": utc_now().isoformat(),
                "reason": str(reason),
                "evidence": dict(evidence or {}),
                "claim_boundary": (
                    "A void event preserves a corrupted simulated position as audit "
                    "evidence. It is not a market close and creates no realized P&L."
                ),
            }
        )
        self._persist_state()
        return True

    def get_void_events(self) -> list[dict[str, Any]]:
        self._refresh_persistent_state()
        return [dict(row) for row in self._void_events]

    def _refresh_persistent_state(self) -> None:
        if self._state_path is None:
            return
        with self._state_lock:
            self._load_persistent_state()
            if self._drop_closed_paper_tickets():
                self._persist_state()

    def _load_persistent_state(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            return
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        loaded: Dict[int, dict] = {}
        rows = payload.get("positions") if isinstance(payload.get("positions"), dict) else {}
        for raw_ticket, raw in rows.items():
            if not isinstance(raw, dict) or not isinstance(raw.get("order"), dict):
                continue
            try:
                ticket = int(raw_ticket)
                order = BrokerOrderRequest.model_validate(raw["order"])
                timestamp = datetime.fromisoformat(str(raw.get("timestamp") or "").replace("Z", "+00:00"))
                loaded[ticket] = {
                    "order": order,
                    "fill_price": float(raw.get("fill_price")),
                    "volume": float(raw.get("volume", order.volume)),
                    "timestamp": timestamp,
                }
                if raw.get("current_price") not in (None, ""):
                    loaded[ticket]["current_price"] = float(raw["current_price"])
                if raw.get("stop_loss") not in (None, ""):
                    loaded[ticket]["stop_loss"] = float(raw["stop_loss"])
                if raw.get("take_profit") not in (None, ""):
                    loaded[ticket]["take_profit"] = float(raw["take_profit"])
            except (TypeError, ValueError):
                continue
        self._positions = loaded
        self._close_events = [
            dict(row)
            for row in (payload.get("close_events") or [])
            if isinstance(row, dict)
        ]
        self._void_events = [
            dict(row)
            for row in (payload.get("void_events") or [])
            if isinstance(row, dict)
        ]
        self._balance = float(payload.get("balance", self._balance))
        self._equity = float(payload.get("equity", self._equity))
        self._ticket_counter = int(payload.get("ticket_counter", self._ticket_counter))

    def _persist_state(self) -> None:
        if self._state_path is None:
            return
        with self._state_lock:
            payload = {
                "report_kind": "cas_forex_simulated_broker_state",
                "updated_at": utc_now().isoformat(),
                "balance": self._balance,
                "equity": self._equity,
                "ticket_counter": self._ticket_counter,
                "open_position_count": len(self._positions),
                "close_event_count": len(self._close_events),
                "close_events": list(self._close_events),
                "void_event_count": len(self._void_events),
                "void_events": list(self._void_events),
                "positions": {
                    str(ticket): {
                        "order": position["order"].model_dump(mode="json"),
                        "fill_price": position["fill_price"],
                        "volume": position.get("volume", position["order"].volume),
                        "timestamp": (
                            position["timestamp"].isoformat()
                            if isinstance(position.get("timestamp"), datetime)
                            else str(position.get("timestamp") or "")
                        ),
                        "current_price": position.get("current_price"),
                        "stop_loss": position.get("stop_loss"),
                        "take_profit": position.get("take_profit"),
                    }
                    for ticket, position in self._positions.items()
                },
                "claim_boundary": (
                    "Durable internal paper broker state contains simulated positions only. "
                    "It cannot authorize or reach a live broker account."
                ),
            }
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._state_path.with_suffix(
                f"{self._state_path.suffix}.{os.getpid()}.{threading.get_ident()}.tmp"
            )
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self._state_path)

    def _record_close_event(
        self,
        ticket: int,
        position: dict[str, Any],
        *,
        closed_volume: float,
        remaining_volume: float,
        full_close: bool,
    ) -> None:
        sequence = 1 + sum(
            1 for row in self._close_events if str(row.get("parent_broker_ticket")) == str(ticket)
        )
        event_ticket = str(ticket) if full_close else f"{ticket}:partial:{sequence}"
        self._close_events.append(
            {
                "event_ticket": event_ticket,
                "parent_broker_ticket": str(ticket),
                "order_id": position["order"].order_id,
                "decision_ref": position["order"].decision_ref,
                "symbol": position["order"].symbol,
                "direction": position["order"].direction.value,
                "entry": float(position["fill_price"]),
                "exit": float(position.get("current_price", position["fill_price"])),
                "closed_volume": float(closed_volume),
                "remaining_volume": float(remaining_volume),
                "full_close": bool(full_close),
                "opened_at": (
                    position["timestamp"].isoformat()
                    if isinstance(position.get("timestamp"), datetime)
                    else str(position.get("timestamp") or "")
                ),
                "closed_at": utc_now().isoformat(),
                "source": "AI_HEDGE_SIMULATED_MANAGEMENT",
            }
        )

    def _drop_closed_paper_tickets(self) -> bool:
        path = self._closed_ticket_ledger_path
        if path is None or not path.exists() or not self._positions:
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        closed = {
            str(row.get("broker_ticket"))
            for row in (payload.get("history_records") or [])
            if isinstance(row, dict) and row.get("broker_ticket") not in (None, "")
        }
        closed.update(str(ticket) for ticket in (payload.get("unresolvable") or {}))
        remove = [ticket for ticket in self._positions if str(ticket) in closed]
        for ticket in remove:
            self._positions.pop(ticket, None)
        return bool(remove)


def get_bridge() -> BrokerBridge:
    """Factory: return the configured broker bridge."""
    _enforce_live_legal_gates()
    cfg = _effective_config()
    if cfg.live_mode and cfg.mt5_login > 0:
        bridge = MT5Bridge()
        if not bridge.connect():
            raise ConnectionError("MT5 live bridge connection failed; refusing live fallback")
        return bridge
    if cfg.paper_trading:
        if cfg.mt4_enabled and cfg.mt4_mailbox_dir:
            mt4 = MT4EABridge(
                mailbox_dir=getattr(cfg, "mt4_mailbox_dir", None),
                enabled=getattr(cfg, "mt4_enabled", None),
                runtime_config=cfg,
            )
            if mt4.connect():
                return mt4
        # Prefer real MT5 for paper if available
        if cfg.mt5_login > 0:
            bridge = MT5Bridge()
            if bridge.connect():
                return bridge
        return SimulatedBrokerBridge()
    return SimulatedBrokerBridge()


def _enforce_live_legal_gates() -> None:
    cfg = _effective_config()
    if not cfg.live_mode:
        return
    # Owner-controlled authorization (fail-closed). Live execution is only
    # allowed when the owner has satisfied the live-trading gate: explicit
    # enable flag(s) ON, broker credentials present, live broker configured, and
    # account/source-of-funds acknowledgments signed. This is not a
    # permanent lock - the gate reports exactly what is still missing and the
    # owner authorizes it by providing those items. The check stays at the real
    # execution path so a real-money order can never be placed without explicit
    # owner authorization + credentials + config.
    from cas_forex import runtime_gates

    runtime_gates.require_authorized("live_trading", cfg)


def _positive_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _volume_matches_step(volume: float, min_lot: float, step: float) -> bool:
    if step <= 0:
        return True
    base = min_lot if min_lot > 0 else 0.0
    if volume < base - 1e-9:
        return False
    steps = (volume - base) / step
    return abs(steps - round(steps)) <= 1e-8


def _hash_payload(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _request_payload(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {}
    allowed = {
        "action",
        "symbol",
        "volume",
        "type",
        "position",
        "price",
        "sl",
        "tp",
        "deviation",
        "magic",
        "comment",
        "type_time",
        "type_filling",
    }
    return {str(k): v for k, v in request.items() if k in allowed}


def _result_payload(result) -> dict:
    if hasattr(result, "_asdict"):
        return dict(result._asdict())
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"repr": repr(result)}
