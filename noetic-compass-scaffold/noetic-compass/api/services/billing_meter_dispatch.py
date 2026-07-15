"""Lifespan-owned, at-most-once Stripe Meter Event dispatcher.

The safety order is deliberately asymmetric:

1. discover and validate a bounded set of pending rows (bounded retries are
   allowed here because Stripe has not been contacted);
2. durably move exactly one row to ``delivery_uncertain``;
3. make one and only one provider call with the stored deterministic identifier;
4. persist the exact acknowledgement when it is available.

Any exception, timeout, cancellation, process death, or acknowledgement-write
failure after step 2 leaves the row quarantined as ``delivery_uncertain``. It is
never rediscovered and never automatically sent again after restart. This
prefers a manual under-billing review over an accidental duplicate charge.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Mapping, Protocol

from api.services.billing_reconciliation import (
    BillingReconciliationConflict,
    BillingReconciliationError,
    BillingReconciliationStore,
    UsageOutboxRecord,
)


logger = logging.getLogger("noetic.billing.meter_dispatch")


@dataclass(frozen=True, slots=True)
class MeterEventProviderReceipt:
    response: Mapping[str, object]
    provider_request_id: str | None
    response_sha256: str


class MeterEventProvider(Protocol):
    async def submit_meter_event(
        self, *, request: Mapping[str, object]
    ) -> MeterEventProviderReceipt: ...


@dataclass(frozen=True, slots=True)
class MeterDispatchRun:
    candidates: int
    submitted: int
    quarantined: int
    skipped: int


class StripeMeterEventDispatcher:
    """Consume pending measured usage without ever replaying send authority."""

    def __init__(
        self,
        *,
        reconciliation: BillingReconciliationStore,
        provider: MeterEventProvider,
        batch_size: int = 25,
        preflight_retries: int = 3,
        preflight_backoff_seconds: float = 0.05,
    ) -> None:
        if batch_size < 1 or batch_size > 100:
            raise ValueError("meter dispatch batch size must be 1..100")
        if preflight_retries < 1 or preflight_retries > 5:
            raise ValueError("meter dispatch preflight retries must be 1..5")
        if preflight_backoff_seconds < 0 or preflight_backoff_seconds > 5:
            raise ValueError(
                "meter dispatch preflight backoff must be between 0 and 5 seconds"
            )
        self._reconciliation = reconciliation
        self._provider = provider
        self._batch_size = batch_size
        self._preflight_retries = preflight_retries
        self._preflight_backoff_seconds = preflight_backoff_seconds

    async def run_once(self) -> MeterDispatchRun:
        candidates = await self._preflight_candidates()
        submitted = 0
        quarantined = 0
        skipped = 0
        for candidate in candidates:
            authority = self._reserve(candidate)
            if authority is None:
                skipped += 1
                continue

            # This is the only provider call in the dispatcher. There is no
            # retry loop around it. The Stripe adapter also overrides the SDK's
            # per-request max_network_retries to zero.
            try:
                receipt = await self._provider.submit_meter_event(
                    request=authority.meter_event_request()
                )
            except asyncio.CancelledError:
                # Cancellation can arrive after the provider accepted the HTTP
                # body. The durable row is already quarantined; propagate
                # process control without creating another send path.
                logger.warning(
                    "Stripe Meter Event dispatch was cancelled after reservation; "
                    "automatic replay is blocked"
                )
                raise
            except Exception:
                quarantined += 1
                logger.exception(
                    "Stripe Meter Event outcome is uncertain; automatic replay is blocked"
                )
                continue

            try:
                self._reconciliation.mark_usage_submitted(
                    tenant_id=authority.tenant_id,
                    usage_id=authority.usage_id,
                    response=receipt.response,
                    provider_request_id=receipt.provider_request_id,
                    provider_response_sha256=receipt.response_sha256,
                )
            except Exception:
                quarantined += 1
                logger.exception(
                    "Stripe acknowledged Meter Event but durable acknowledgement failed; "
                    "automatic replay is blocked"
                )
                continue
            submitted += 1
        return MeterDispatchRun(
            candidates=len(candidates),
            submitted=submitted,
            quarantined=quarantined,
            skipped=skipped,
        )

    async def run_forever(
        self,
        *,
        stop_event: asyncio.Event,
        interval_seconds: float,
    ) -> None:
        if interval_seconds < 0.1 or interval_seconds > 300:
            raise ValueError("meter dispatch interval must be 0.1..300 seconds")
        while not stop_event.is_set():
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Candidate preflight may fail due to temporary state-store
                # availability. No provider call occurs until preflight succeeds.
                logger.exception("Stripe Meter Event dispatcher preflight failed")
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=interval_seconds
                )
            except TimeoutError:
                pass

    async def _preflight_candidates(self) -> tuple[UsageOutboxRecord, ...]:
        last_error: Exception | None = None
        for attempt in range(self._preflight_retries):
            try:
                return self._reconciliation.pending_usage_global(
                    limit=self._batch_size
                )
            except (BillingReconciliationError, OSError) as exc:
                last_error = exc
                if attempt + 1 >= self._preflight_retries:
                    break
                await asyncio.sleep(
                    self._preflight_backoff_seconds * (attempt + 1)
                )
        if last_error is None:  # pragma: no cover - constructor forbids zero retries
            raise BillingReconciliationError("meter dispatch preflight did not run")
        raise last_error

    def _reserve(self, candidate: UsageOutboxRecord) -> UsageOutboxRecord | None:
        try:
            authority = self._reconciliation.reserve_usage_delivery(
                tenant_id=candidate.tenant_id,
                usage_id=candidate.usage_id,
            )
        except (BillingReconciliationConflict, BillingReconciliationError):
            # Another process may have won the durable reservation race, or a
            # different tenant transition may briefly own the lease. Neither
            # grants this process authority to contact Stripe.
            return None
        if (
            authority.outbox_state != "delivery_uncertain"
            or authority.attempt_count != candidate.attempt_count + 1
            or authority.meter_event_identifier
            != candidate.meter_event_identifier
            or authority.meter_event_request_sha256
            != candidate.meter_event_request_sha256
        ):
            raise BillingReconciliationConflict(
                "durable usage reservation returned contradictory send authority"
            )
        return authority


__all__ = [
    "MeterDispatchRun",
    "MeterEventProvider",
    "MeterEventProviderReceipt",
    "StripeMeterEventDispatcher",
]
