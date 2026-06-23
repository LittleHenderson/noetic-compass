"""Demo/paper broker receipt adapters for CAS FOREX paper proof.

Adapters in this module may prove that a paper/demo broker source was checked.
They do not place trades, create broker ACCEPT, or authorize live money.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Dict, List, Mapping, Optional, Sequence

from cas_forex.config import config
from cas_forex.instruments import broker_symbol
from cas_forex.paper_proof import (
    BROKER_API_VERIFIED,
    PaperProofPlan,
    append_paper_proof_day,
    validate_paper_broker_receipt,
)


ADAPTER_CLAIM_BOUNDARY = (
    "Demo broker receipt collection is paper-proof only. "
    "Live trading, broker ACCEPT, and payment transfers remain NOT LICENSED."
)


class PaperBrokerReceiptUnavailable(RuntimeError):
    """Raised when a broker receipt cannot be collected safely."""


@dataclass(frozen=True)
class PaperBrokerReceiptProbe:
    """Status artifact for a paper broker receipt collection attempt."""

    status: str
    broker: str
    trading_date: str
    receipt: Optional[Dict[str, Any]] = None
    reasons: List[str] = field(default_factory=list)
    claim_boundary: str = ADAPTER_CLAIM_BOUNDARY


class MT5DemoPaperReceiptAdapter:
    """Collect an API-verified receipt from a connected MT5 demo account."""

    def __init__(self, mt5_module: Any | None = None):
        self._mt5 = mt5_module

    def collect_receipt(self, plan: PaperProofPlan, trading_date: date) -> Dict[str, Any]:
        """Collect and validate a paper-proof receipt from MT5 demo history."""

        if config.live_mode or not config.paper_trading:
            raise PermissionError("MT5 paper receipt collection requires paper_trading=True and live_mode=False.")

        mt5 = self._mt5 or self._import_mt5()
        if mt5 is None:
            raise PaperBrokerReceiptUnavailable("MetaTrader5 Python package is unavailable.")
        self._initialize(mt5)
        if not self._is_connected(mt5):
            raise PaperBrokerReceiptUnavailable("MT5 terminal is not connected.")

        account = self._object_to_dict(mt5.account_info())
        if not account:
            raise PaperBrokerReceiptUnavailable("MT5 account_info is unavailable.")
        if not self._is_demo_account(mt5, account):
            raise PermissionError("MT5 account is not identified as demo/paper; refusing receipt verification.")

        terminal = self._object_to_dict(mt5.terminal_info())
        start = datetime.combine(trading_date, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        mt5_symbols = {broker_symbol(symbol) for symbol in plan.symbols}
        orders = self._fetch_records(mt5, "history_orders_get", start, end)
        deals = self._fetch_records(mt5, "history_deals_get", start, end)
        positions = self._fetch_open_positions(mt5)
        filtered_orders = [record for record in orders if str(record.get("symbol", "")) in mt5_symbols]
        filtered_deals = [record for record in deals if str(record.get("symbol", "")) in mt5_symbols]
        open_symbols = {str(record.get("symbol", "")) for record in positions}
        unexpected_open_symbols = sorted(symbol for symbol in open_symbols if symbol not in mt5_symbols)
        open_positions_reconciled = not unexpected_open_symbols
        snapshot = {
            "account": self._redacted_account(account),
            "terminal": terminal,
            "orders": filtered_orders,
            "deals": filtered_deals,
            "positions": positions,
            "unexpected_open_symbols": unexpected_open_symbols,
            "plan": {
                "plan_id": plan.plan_id,
                "lead_id": plan.lead_id,
                "strategy_setting": plan.strategy_setting,
                "symbols": plan.symbols,
                "timeframe": plan.timeframe,
            },
            "trading_date": trading_date.isoformat(),
        }
        broker_export_sha256 = _sha256_json(snapshot)
        orders_attempted = max(len(filtered_orders), len(filtered_deals))
        receipt = {
            "receipt_id": f"{plan.plan_id}-{trading_date.isoformat()}-mt5-demo-api",
            "source_attestation": BROKER_API_VERIFIED,
            "broker_mode": "PAPER_MT5",
            "trading_date": trading_date.isoformat(),
            "lead_id": plan.lead_id,
            "strategy_setting": plan.strategy_setting,
            "symbols": plan.symbols,
            "timeframe": plan.timeframe,
            "orders_attempted": orders_attempted,
            "orders_paper_executed": len(filtered_deals),
            "open_positions_reconciled": open_positions_reconciled,
            "live_mode": False,
            "broker_export_sha256": broker_export_sha256,
            "account_id_hash": self._account_hash(account),
            "server": str(account.get("server") or config.mt5_server or "MT5_DEMO"),
            "terminal_name": str(terminal.get("name") or "MetaTrader5"),
            "provider_receipt_id": broker_export_sha256[:16],
            "order_ids": [
                str(record.get("ticket") or record.get("order") or record.get("position_id"))
                for record in filtered_orders
            ],
            "adapter": "MT5DemoPaperReceiptAdapter",
            "claim_boundary": ADAPTER_CLAIM_BOUNDARY,
        }
        return validate_paper_broker_receipt(
            plan,
            receipt,
            expected_date=trading_date,
            allow_api_verified=True,
        )

    def append_verified_day(
        self,
        plan: PaperProofPlan,
        output_dir: str,
        trading_date: date,
    ) -> Dict[str, Any]:
        """Collect an MT5 demo receipt and append it to the proof ledger."""

        receipt = self.collect_receipt(plan, trading_date)
        return append_paper_proof_day(
            plan,
            output_dir,
            trading_date=trading_date,
            broker_receipt=receipt,
            allow_api_verified_receipt=True,
        )

    def probe(self, plan: PaperProofPlan, trading_date: date) -> PaperBrokerReceiptProbe:
        """Return a non-throwing probe result for CLIs and dashboards."""

        try:
            receipt = self.collect_receipt(plan, trading_date)
            return PaperBrokerReceiptProbe(
                status="BROKER_API_VERIFIED",
                broker="MT5",
                trading_date=trading_date.isoformat(),
                receipt=receipt,
            )
        except PermissionError as exc:
            return PaperBrokerReceiptProbe(
                status="BLOCKED",
                broker="MT5",
                trading_date=trading_date.isoformat(),
                reasons=[str(exc)],
            )
        except PaperBrokerReceiptUnavailable as exc:
            return PaperBrokerReceiptProbe(
                status="UNAVAILABLE",
                broker="MT5",
                trading_date=trading_date.isoformat(),
                reasons=[str(exc)],
            )

    def _import_mt5(self) -> Any | None:
        try:
            import MetaTrader5 as mt5  # type: ignore

            return mt5
        except ImportError:
            return None

    def _initialize(self, mt5: Any) -> None:
        if self._is_connected(mt5):
            return
        kwargs: Dict[str, Any] = {}
        if config.mt5_path:
            kwargs["path"] = config.mt5_path
        if config.mt5_login > 0:
            kwargs["login"] = config.mt5_login
            kwargs["password"] = config.mt5_password
            kwargs["server"] = config.mt5_server
        try:
            mt5.initialize(**kwargs)
        except Exception as exc:
            raise PaperBrokerReceiptUnavailable(f"MT5 initialize failed: {exc}") from exc

    def _is_connected(self, mt5: Any) -> bool:
        try:
            info = mt5.terminal_info()
        except Exception:
            return False
        return bool(info is not None and getattr(info, "connected", False))

    def _is_demo_account(self, mt5: Any, account: Mapping[str, Any]) -> bool:
        trade_mode = account.get("trade_mode")
        demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        if demo_const is not None and trade_mode == demo_const:
            return True
        server = str(account.get("server") or config.mt5_server or "").lower()
        company = str(account.get("company") or "").lower()
        return "demo" in server or "demo" in company

    def _fetch_records(
        self,
        mt5: Any,
        method_name: str,
        start: datetime,
        end: datetime,
    ) -> List[Dict[str, Any]]:
        method = getattr(mt5, method_name, None)
        if method is None:
            return []
        try:
            records = method(start, end)
        except Exception:
            return []
        return [self._object_to_dict(record) for record in records or []]

    def _fetch_open_positions(self, mt5: Any) -> List[Dict[str, Any]]:
        try:
            positions = mt5.positions_get()
        except Exception:
            return []
        return [self._object_to_dict(position) for position in positions or []]

    def _redacted_account(self, account: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "login_hash": self._account_hash(account),
            "server": account.get("server"),
            "company": account.get("company"),
            "trade_mode": account.get("trade_mode"),
            "currency": account.get("currency"),
            "leverage": account.get("leverage"),
        }

    def _account_hash(self, account: Mapping[str, Any]) -> str:
        payload = {
            "login": account.get("login") or config.mt5_login,
            "server": account.get("server") or config.mt5_server,
        }
        return _sha256_json(payload)

    def _object_to_dict(self, value: Any) -> Dict[str, Any]:
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


def _sha256_json(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
