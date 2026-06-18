"""Post-trade reconciliation and lock detection."""

from __future__ import annotations

import uuid
from typing import Optional

from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus, PostTradeObservation
from cas_forex.schemas.live_lock import LiveLockReason
from cas_forex.schemas.order import BrokerOrderRequest, OrderOutcome
from cas_forex.verifier.live_lock import LiveLockController


class PostTradeHarness:
    """Reconciles broker state with CAS-approved order evidence."""

    def __init__(
        self,
        broker,
        evidence_store: Optional[EvidenceStore] = None,
        live_lock_controller: Optional[LiveLockController] = None,
    ):
        self.broker = broker
        self.evidence_store = evidence_store
        self.live_lock_controller = live_lock_controller

    def observe(
        self,
        trace_id: str,
        expected_order: Optional[BrokerOrderRequest] = None,
        outcome: Optional[OrderOutcome] = None,
    ) -> PostTradeObservation:
        connected = self.broker.is_connected()
        open_positions = self.broker.get_open_positions()
        account = self.broker.get_account_info()
        lock_reason = None
        mismatch = False

        if not connected and open_positions:
            lock_reason = LiveLockReason.BROKER_DISCONNECT_OPEN_TRADE
        if expected_order is not None and outcome is not None:
            if outcome.status.value == "REJECTED" and outcome.lock_reason is not None:
                lock_reason = LiveLockReason.MARGIN_ERROR
            for pos in open_positions:
                if pos.get("ticket") == outcome.broker_ticket:
                    if pos.get("symbol") != expected_order.symbol:
                        mismatch = True
                    if abs(float(pos.get("volume", 0)) - expected_order.volume) > 0.0001:
                        mismatch = True
            if mismatch:
                lock_reason = LiveLockReason.EXECUTION_MISMATCH

        observation = PostTradeObservation(
            trace_id=trace_id,
            broker_ticket=outcome.broker_ticket if outcome else None,
            symbol=expected_order.symbol if expected_order else "",
            status="CONNECTED" if connected else "DISCONNECTED",
            floating_profit=sum(float(p.get("profit", 0.0)) for p in open_positions),
            slippage_pips=outcome.slippage_pips if outcome else None,
            margin_level_pct=account.get("margin_level") or account.get("margin_level_pct"),
            mismatch_detected=mismatch,
            lock_reason=lock_reason.value if lock_reason else None,
            evidence={"open_positions": open_positions, "account": account},
        )
        self._emit_packet(observation, expected_order, outcome)
        if lock_reason and self.live_lock_controller:
            self.live_lock_controller.lock([lock_reason], details=observation.model_dump(mode="json"))
        return observation

    def _emit_packet(
        self,
        observation: PostTradeObservation,
        expected_order: Optional[BrokerOrderRequest],
        outcome: Optional[OrderOutcome],
    ) -> None:
        packet = ForexEvidencePacket(
            packet_id=str(uuid.uuid4()),
            trace_id=observation.trace_id,
            status=PacketStatus.LIVE_LOCKED if observation.lock_reason else PacketStatus.EXECUTED,
            order_request=expected_order.model_dump(mode="json") if expected_order else None,
            order_outcome=outcome.model_dump(mode="json") if outcome else None,
            notes=[observation.model_dump_json()],
        )
        packet.finalize()
        if self.evidence_store is not None:
            try:
                self.evidence_store.append(packet, source="post_trade")
            except Exception as exc:
                if self.live_lock_controller is not None:
                    self.live_lock_controller.lock(
                        [LiveLockReason.EVIDENCE_WRITE_FAILURE],
                        details={"trace_id": observation.trace_id, "error": str(exc)},
                    )
