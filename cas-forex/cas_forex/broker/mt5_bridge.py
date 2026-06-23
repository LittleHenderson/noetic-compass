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
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from cas_forex.config import config
from cas_forex.instruments import broker_symbol
from cas_forex.schemas.order import (
    BrokerLockReason,
    BrokerMode,
    BrokerOrderRequest,
    OrderOutcome,
    OrderStatus,
)
from cas_forex.schemas.forecast import Direction, pip_multiplier
from cas_forex.time_utils import utc_now


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
    def get_open_positions(self) -> list:
        """List all currently open positions."""
        ...


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
    ):
        self.login = login or config.mt5_login
        self.password = password or config.mt5_password
        self.server = server or config.mt5_server
        self.prefer_mt5 = prefer_mt5
        self._mt5 = None
        self._connected = False

    def _initialize(self):
        """Attempt to initialize MT5 connection."""
        self._connected = False
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5

            # MT5 may hang if terminal isn't running — catch everything
            try:
                result = mt5.initialize(
                    login=self.login,
                    password=self.password,
                    server=self.server,
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
            if config.live_mode:
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
                    server=self.server,
                    account_id_hash=self._account_id_hash(),
                    raw_request_hash=_hash_payload(request),
                )

            retcode = result.retcode
            ticket = result.order if result.order > 0 else None

            # MT5 return codes
            if retcode == self._mt5.TRADE_RETCODE_DONE:
                status = OrderStatus.EXECUTED
                error = None
            elif retcode == self._mt5.TRADE_RETCODE_DONE_PARTIAL:
                status = OrderStatus.PARTIAL
                error = f"Partial fill: {result.comment}"
            elif retcode == self._mt5.TRADE_RETCODE_REJECT:
                status = OrderStatus.REJECTED
                error = f"Rejected: {result.comment}"
            elif retcode == self._mt5.TRADE_RETCODE_CANCEL:
                status = OrderStatus.CANCELLED
                error = f"Cancelled: {result.comment}"
            else:
                status = OrderStatus.REJECTED
                error = f"Unknown retcode {retcode}: {result.comment}"
            lock_reason = None
            if status == OrderStatus.REJECTED and "margin" in str(error or "").lower():
                lock_reason = BrokerLockReason.MARGIN_REJECT

            fill_price = float(result.price) if result.price > 0 else None
            expected_price = order.price if order.price > 0 else fill_price
            slippage_pips = None
            if fill_price and expected_price:
                slippage_pips = abs(fill_price - expected_price) * pip_multiplier(order.symbol)

            return OrderOutcome(
                order_ref=order.order_id,
                broker_ticket=ticket,
                status=status,
                filled_price=fill_price,
                slippage_pips=round(slippage_pips, 2) if slippage_pips else None,
                commission=float(result.commission) if result.commission else None,
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
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
                raw_request_hash=_hash_payload(request),
                raw_response_hash=_hash_payload(_result_payload(result)),
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
                terminal_name="MetaTrader5",
                account_id_hash=self._account_id_hash(),
                server=self.server,
            )

    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        """Close a position by ticket number."""
        if not self.is_connected():
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
            }

            result = self._mt5.order_send(request)
            return result is not None and result.retcode == self._mt5.TRADE_RETCODE_DONE

        except Exception:
            return False

    def _slippage_points_to_pips(self, symbol: str, points: int) -> float:
        """Convert MT5 deviation points to forex pips for evidence checks."""
        point_size = None
        if self._mt5 is not None and hasattr(self._mt5, "symbol_info"):
            for candidate in (symbol, symbol.replace("/", "")):
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
        return BrokerMode.LIVE_MT5 if config.live_mode else BrokerMode.PAPER_MT5

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
                    "profit": p.profit,
                    "swap": p.swap,
                    "comment": p.comment,
                }
                for p in positions
                if "CAS" in (p.comment or "")
            ]
        except Exception:
            return []

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

        symbol = broker_symbol(order.symbol)

        # Get current price for market orders
        price = order.price
        if price == 0.0:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                price = tick.ask if order.direction == Direction.LONG else tick.bid

        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(order.volume),
            "type": ot,
            "price": float(price) if price > 0 else 0.0,
            "sl": float(order.stop_loss),
            "tp": float(order.take_profit),
            "deviation": order.slippage,
            "magic": order.magic_number,
            "comment": order.comment[:27],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

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

    def __init__(self, mailbox_dir: Optional[str] = None):
        self.mailbox_dir = Path(mailbox_dir or config.mt4_mailbox_dir or "mt4_mailbox")
        self.orders_path = self.mailbox_dir / "orders.jsonl"
        self.acks_path = self.mailbox_dir / "acks.jsonl"
        self.heartbeat_path = self.mailbox_dir / "heartbeat.json"
        self.positions_path = self.mailbox_dir / "positions.jsonl"

    def connect(self) -> bool:
        if not config.mt4_enabled or config.live_mode or not config.paper_trading:
            return False
        self.mailbox_dir.mkdir(parents=True, exist_ok=True)
        return True

    def is_connected(self) -> bool:
        return self.heartbeat_path.exists()

    def execute_order(self, order: BrokerOrderRequest) -> OrderOutcome:
        if not self.connect():
            return OrderOutcome(
                order_ref=order.order_id,
                status=OrderStatus.REJECTED,
                error_message="MT4 bridge requires enabled paper mailbox mode",
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
        return OrderOutcome(
            order_ref=order.order_id,
            status=OrderStatus.PENDING,
            broker_mode=BrokerMode.PAPER_MT4,
            is_real_broker=True,
            terminal_name="MetaTrader4-EA",
            raw_request_hash=payload["intent_hash"],
        )

    def get_account_info(self) -> Dict[str, float]:
        return {"balance": 0, "equity": 0, "margin": 0, "margin_free": 0}

    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        return False

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
    ):
        self._positions: Dict[int, dict] = {}
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

    def is_connected(self) -> bool:
        return True

    def get_account_info(self) -> Dict[str, float]:
        return {
            "balance": self._balance,
            "equity": self._equity,
            "margin": 0.0,
            "margin_free": self._equity,
            "leverage": 100,
        }

    def execute_order(self, order: BrokerOrderRequest) -> OrderOutcome:
        rejection = self._reject_reason(order)
        if rejection is not None:
            message, lock_reason = rejection
            return self._rejected(order, message, lock_reason=lock_reason)

        partial = order.volume > self.max_lot
        filled_volume = min(order.volume, self.max_lot)
        ticket = self._ticket_counter
        self._ticket_counter += 1

        fill_price = order.price if order.price > 0 else (
            order.stop_loss * 1.0005
            if order.direction == Direction.LONG
            else order.stop_loss * 0.9995
        )
        slip = self.simulated_slippage_pips / pip_multiplier(order.symbol)
        fill_price = fill_price + slip if order.direction == Direction.LONG else fill_price - slip

        self._positions[ticket] = {
            "order": order,
            "fill_price": fill_price,
            "volume": filled_volume,
            "timestamp": utc_now(),
        }

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

    def close_position(self, ticket: int, volume: Optional[float] = None) -> bool:
        if ticket in self._positions:
            del self._positions[ticket]
            return True
        return False

    def get_open_positions(self) -> list:
        return [
            {
                "ticket": t,
                "symbol": p["order"].symbol,
                "type": p["order"].direction.value,
                "volume": p.get("volume", p["order"].volume),
                "open_price": p["fill_price"],
                "current_price": p["fill_price"],
                "profit": 0.0,
                "swap": 0.0,
                "comment": p["order"].comment,
            }
            for t, p in self._positions.items()
        ]


def get_bridge() -> BrokerBridge:
    """Factory: return the configured broker bridge."""
    _enforce_live_legal_gates()
    if config.live_mode and config.mt5_login > 0:
        bridge = MT5Bridge()
        if not bridge.connect():
            raise ConnectionError("MT5 live bridge connection failed; refusing live fallback")
        return bridge
    if config.paper_trading:
        if config.mt4_enabled and config.mt4_mailbox_dir:
            mt4 = MT4EABridge()
            if mt4.connect():
                return mt4
        # Prefer real MT5 for paper if available
        if config.mt5_login > 0:
            bridge = MT5Bridge()
            if bridge.connect():
                return bridge
        return SimulatedBrokerBridge()
    return SimulatedBrokerBridge()


def _enforce_live_legal_gates() -> None:
    if not config.live_mode:
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

    runtime_gates.require_authorized("live_trading", config)


def _hash_payload(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _result_payload(result) -> dict:
    if hasattr(result, "_asdict"):
        return dict(result._asdict())
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"repr": repr(result)}
