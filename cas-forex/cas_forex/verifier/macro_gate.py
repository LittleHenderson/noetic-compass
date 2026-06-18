"""Macro Gate - blackout and shock windows around high-impact events."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable, Optional, Protocol

from cas_forex.config import config
from cas_forex.schemas.decision import GateResult, GateStatus
from cas_forex.schemas.live_lock import LiveLockReason
from cas_forex.schemas.macro import MacroEventState, MacroEventType, MacroImpact
from cas_forex.time_utils import ensure_utc, utc_now


class MacroCalendarProvider(Protocol):
    def events(self) -> Iterable[MacroEventState]:
        ...


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=UTC)


class StaticMacroCalendarProvider:
    """Static 2026 seed calendar for plan-compliance tests and paper mode."""

    def __init__(self, events: Optional[list[MacroEventState]] = None):
        self._events = events or self._default_events()

    def events(self) -> Iterable[MacroEventState]:
        return list(self._events)

    @staticmethod
    def _event(
        event_id: str,
        event_type: MacroEventType,
        scheduled_at: datetime,
        currency: str = "USD",
        impact: MacroImpact = MacroImpact.HIGH,
    ) -> MacroEventState:
        return MacroEventState(
            event_id=event_id,
            event_type=event_type,
            currency=currency,
            scheduled_at_utc=scheduled_at,
            impact=impact,
            blackout_before_minutes=config.blackout_before_nfp_minutes,
            blackout_after_minutes=config.blackout_after_nfp_minutes,
            shock_threshold=config.macro_shock_threshold_default,
        )

    @classmethod
    def _default_events(cls) -> list[MacroEventState]:
        events: list[MacroEventState] = []
        cpi = [
            (1, 15, 13, 30), (2, 12, 13, 30), (3, 11, 12, 30),
            (4, 15, 12, 30), (5, 13, 12, 30), (6, 10, 12, 30),
            (7, 15, 12, 30), (8, 12, 12, 30), (9, 16, 12, 30),
            (10, 15, 12, 30), (11, 12, 13, 30), (12, 10, 13, 30),
        ]
        nfp = [
            (1, 9, 13, 30), (2, 6, 13, 30), (3, 6, 13, 30),
            (4, 3, 12, 30), (5, 1, 12, 30), (6, 5, 12, 30),
            (7, 2, 12, 30), (8, 7, 12, 30), (9, 4, 12, 30),
            (10, 2, 12, 30), (11, 6, 13, 30), (12, 4, 13, 30),
        ]
        fomc = [
            (1, 29, 19, 0), (3, 19, 18, 0), (5, 7, 18, 0),
            (6, 17, 18, 0), (7, 30, 18, 0), (9, 17, 18, 0),
            (11, 6, 19, 0), (12, 10, 19, 0),
        ]
        for idx, (month, day, hour, minute) in enumerate(cpi, 1):
            events.append(cls._event(f"2026-cpi-{idx:02d}", MacroEventType.CPI, _dt(2026, month, day, hour, minute)))
        for idx, (month, day, hour, minute) in enumerate(nfp, 1):
            events.append(cls._event(f"2026-nfp-{idx:02d}", MacroEventType.NFP, _dt(2026, month, day, hour, minute)))
        for idx, (month, day, hour, minute) in enumerate(fomc, 1):
            event = cls._event(f"2026-fomc-{idx:02d}", MacroEventType.FOMC, _dt(2026, month, day, hour, minute))
            event.blackout_before_minutes = config.blackout_before_fomc_minutes
            event.blackout_after_minutes = config.blackout_after_fomc_minutes
            events.append(event)

        # Plan-required event families. These are seed fixtures until an external
        # economic calendar feed is wired.
        events.extend([
            cls._event("2026-gdp-q2-advance", MacroEventType.GDP, _dt(2026, 7, 30, 12, 30)),
            cls._event("2026-unemployment-jul", MacroEventType.UNEMPLOYMENT, _dt(2026, 8, 7, 12, 30)),
            cls._event("2026-fed-speech-seed", MacroEventType.CENTRAL_BANK_SPEECH, _dt(2026, 6, 24, 16, 0), impact=MacroImpact.MEDIUM),
            cls._event("2026-rate-decision-seed", MacroEventType.RATE_DECISION, _dt(2026, 6, 17, 18, 0)),
        ])
        return events


class MacroGate:
    def __init__(
        self,
        blackout_before: Optional[int] = None,
        blackout_after: Optional[int] = None,
        fomc_before: Optional[int] = None,
        fomc_after: Optional[int] = None,
        provider: Optional[MacroCalendarProvider] = None,
    ):
        self.blackout_before = config.blackout_before_nfp_minutes if blackout_before is None else blackout_before
        self.blackout_after = config.blackout_after_nfp_minutes if blackout_after is None else blackout_after
        self.fomc_before = config.blackout_before_fomc_minutes if fomc_before is None else fomc_before
        self.fomc_after = config.blackout_after_fomc_minutes if fomc_after is None else fomc_after
        self.provider = provider or StaticMacroCalendarProvider()

    def evaluate(self, at: Optional[datetime] = None) -> GateResult:
        now = ensure_utc(at) if at is not None else utc_now()
        evidence = {"checked_at": now.isoformat()}

        for event in self.provider.events():
            before = (
                self.fomc_before
                if event.event_type == MacroEventType.FOMC
                else event.blackout_before_minutes or self.blackout_before
            )
            after = (
                self.fomc_after
                if event.event_type == MacroEventType.FOMC
                else event.blackout_after_minutes or self.blackout_after
            )
            scheduled_at = ensure_utc(event.scheduled_at_utc)
            start = scheduled_at - timedelta(minutes=before)
            end = scheduled_at + timedelta(minutes=after)
            event_evidence = {
                **evidence,
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "currency": event.currency,
                "scheduled_at_utc": scheduled_at.isoformat(),
                "impact": event.impact.value,
                "blackout_start": start.isoformat(),
                "blackout_end": end.isoformat(),
                "shock_active": event.shock_active,
            }
            if start <= now <= end and event.shock_active and event.impact == MacroImpact.HIGH:
                return GateResult(
                    gate_name="macro",
                    status=GateStatus.FAIL,
                    confidence=1.0,
                    reason=f"LIVE_LOCKED: macro shock {event.event_type.value}",
                    evidence={**event_evidence, "lock_reason": LiveLockReason.MACRO_SHOCK.value},
                    claim_ceiling="OPEN",
                )
            if start <= now <= end:
                return GateResult(
                    gate_name="macro",
                    status=GateStatus.FAIL,
                    confidence=0.95,
                    reason=f"Macro blackout: {event.event_type.value}",
                    evidence=event_evidence,
                    claim_ceiling="OPEN",
                )

        return GateResult(
            gate_name="macro",
            status=GateStatus.PASS,
            confidence=0.95,
            reason="No macro blackout active.",
            evidence=evidence,
        )
