"""Strategy-ledger evidence firewall for WASTE candidate formation.

The strategy ledger is research memory, not deployment authority. This module
uses it to keep WASTE from turning stale, failed, paper-only, or unknown research
ideas into live candidates. Passing this firewall only means "eligible for the
edge gate to test"; it never creates broker ACCEPT, owner ACCEPT, live trading
authorization, or a money-movement permission.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cas_forex.strategy_ledger import LEDGER_PATH, load_strategy_lead_ledger

REPORT_KIND = "cas_forex_waste_strategy_firewall"
ACTIVE_STATUS = "ACTIVE_RESEARCH_LEAD"
NOT_LICENSED = "NOT LICENSED"

CLAIM_BOUNDARY = (
    "Strategy-ledger firewall can allow a WASTE research candidate to be tested "
    "or suppress it as NO_TRADE. It does not authorize live trading, create "
    "broker ACCEPT, create owner ACCEPT, mint edge tokens, place orders, close "
    "positions, deposit, withdraw, transfer funds, or mark any lead LICENSED."
)


@dataclass(frozen=True)
class WasteStrategyFirewallDecision:
    symbol: str
    timeframe: str
    candidate_allowed: bool
    firewall_status: str
    lead_id: Optional[str]
    lead_status: Optional[str]
    deployment_status: Optional[str]
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    open_gates: tuple[str, ...] = ()
    matched_leads: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": REPORT_KIND,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "candidate_allowed": self.candidate_allowed,
            "firewall_status": self.firewall_status,
            "lead_id": self.lead_id,
            "lead_status": self.lead_status,
            "deployment_status": self.deployment_status,
            "reasons": list(self.reasons),
            "reason": "; ".join(self.reasons),
            "evidence_refs": list(self.evidence_refs),
            "open_gates": list(self.open_gates),
            "matched_leads": [dict(item) for item in self.matched_leads],
            "claim_boundary": CLAIM_BOUNDARY,
        }


def evaluate_waste_strategy_firewall(
    symbol: str,
    timeframe: str,
    *,
    ledger_path: Path | str = LEDGER_PATH,
    ledger: Optional[Mapping[str, Any]] = None,
) -> WasteStrategyFirewallDecision:
    """Return whether a symbol/timeframe may form a WASTE research candidate.

    Eligibility is intentionally narrow:
      * the symbol must be promoted by an ``ACTIVE_RESEARCH_LEAD``;
      * the timeframe must be listed in that lead's preferred timeframes;
      * the lead must still carry ``deployment_status == NOT LICENSED``.

    ``NOT LICENSED`` is preserved as a claim boundary, not used as an owner
    prohibition. The owner can update the ledger/evidence; WASTE must then obey
    the updated evidence state.
    """

    sym = str(symbol or "").strip()
    tf = _norm_tf(timeframe)
    if not sym:
        return _blocked(sym, tf, "NO_TRADE_NO_SYMBOL", None, ["missing symbol"])

    try:
        data = dict(ledger) if ledger is not None else load_strategy_lead_ledger(Path(ledger_path))
    except Exception as exc:
        return _blocked(
            sym,
            tf,
            "NO_TRADE_LEDGER_UNAVAILABLE",
            None,
            [f"strategy ledger unavailable: {type(exc).__name__}: {exc}"],
        )

    leads = [lead for lead in data.get("leads", []) if isinstance(lead, Mapping)]
    symbol_matches = [lead for lead in leads if _lead_mentions_symbol(lead, sym)]
    promoted_matches = [
        lead for lead in symbol_matches if sym in set(_strings(lead.get("symbols_promoted_for_next_tests")))
    ]
    active_symbol_matches = [
        lead
        for lead in promoted_matches
        if str(lead.get("status")) == ACTIVE_STATUS
        and str(lead.get("deployment_status")) == NOT_LICENSED
    ]
    eligible = [lead for lead in active_symbol_matches if _timeframe_allowed(lead, tf)]

    if eligible:
        lead = _best_lead(eligible)
        return WasteStrategyFirewallDecision(
            symbol=sym,
            timeframe=tf,
            candidate_allowed=True,
            firewall_status="ELIGIBLE_RESEARCH_LEAD",
            lead_id=str(lead.get("lead_id")),
            lead_status=str(lead.get("status")),
            deployment_status=str(lead.get("deployment_status")),
            reasons=(
                f"{sym} {tf} is tied to ACTIVE_RESEARCH_LEAD {lead.get('lead_id')}",
                "candidate may be formed for edge-gate testing only; live remains separately gated",
            ),
            evidence_refs=tuple(_strings(lead.get("evidence_refs"))),
            open_gates=tuple(_strings(lead.get("open_gates"))),
            matched_leads=_summaries(symbol_matches),
        )

    if active_symbol_matches:
        lead = _best_lead(active_symbol_matches)
        preferred = _preferred_timeframes(lead)
        return _blocked(
            sym,
            tf,
            "NO_TRADE_TIMEFRAME_BLOCKED",
            lead,
            [
                f"{sym} has active research lead {lead.get('lead_id')}, but {tf} is outside preferred_timeframes {preferred}",
                "add fresh no-lookahead evidence or update the owner-approved ledger before WASTE forms this timeframe",
            ],
            symbol_matches=symbol_matches,
        )

    if promoted_matches:
        lead = _best_lead(promoted_matches)
        return _blocked(
            sym,
            tf,
            "NO_TRADE_LEAD_STATUS_BLOCKED",
            lead,
            [
                f"{sym} is promoted in strategy_leads.json, but lead {lead.get('lead_id')} status is {lead.get('status')}",
                "WATCHLIST_ONLY, RETIRED, and PROMOTED_PAPER_LANE leads cannot form WASTE candidates",
            ],
            symbol_matches=symbol_matches,
        )

    if symbol_matches:
        lead = _best_lead(symbol_matches)
        return _blocked(
            sym,
            tf,
            "NO_TRADE_SYMBOL_NOT_PROMOTED",
            lead,
            [
                f"{sym} appears only as watchlist/excluded evidence in strategy_leads.json",
                "symbol must be in symbols_promoted_for_next_tests on an ACTIVE_RESEARCH_LEAD",
            ],
            symbol_matches=symbol_matches,
        )

    return _blocked(
        sym,
        tf,
        "NO_TRADE_NO_LEDGER_MATCH",
        None,
        [f"no strategy_leads.json entry mentions {sym}; unknown hypotheses stay in research, not WASTE execution"],
    )


def is_waste_strategy_candidate_allowed(symbol: str, timeframe: str) -> bool:
    return evaluate_waste_strategy_firewall(symbol, timeframe).candidate_allowed


def _blocked(
    symbol: str,
    timeframe: str,
    status: str,
    lead: Optional[Mapping[str, Any]],
    reasons: Sequence[str],
    *,
    symbol_matches: Sequence[Mapping[str, Any]] = (),
) -> WasteStrategyFirewallDecision:
    return WasteStrategyFirewallDecision(
        symbol=symbol,
        timeframe=timeframe,
        candidate_allowed=False,
        firewall_status=status,
        lead_id=str(lead.get("lead_id")) if lead else None,
        lead_status=str(lead.get("status")) if lead else None,
        deployment_status=str(lead.get("deployment_status")) if lead and lead.get("deployment_status") else None,
        reasons=tuple(str(reason) for reason in reasons),
        evidence_refs=tuple(_strings(lead.get("evidence_refs"))) if lead else (),
        open_gates=tuple(_strings(lead.get("open_gates"))) if lead else (),
        matched_leads=_summaries(symbol_matches),
    )


def _best_lead(leads: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return sorted(
        leads,
        key=lambda lead: (int(lead.get("priority", 999)), str(lead.get("lead_id", ""))),
    )[0]


def _lead_mentions_symbol(lead: Mapping[str, Any], symbol: str) -> bool:
    symbols = set(_lead_symbols(lead))
    return symbol in symbols


def _lead_symbols(lead: Mapping[str, Any]) -> tuple[str, ...]:
    symbols: list[str] = []
    for key in (
        "symbol",
        "symbols_promoted_for_next_tests",
        "symbols_watchlist",
        "symbols_excluded_until_condition_proof",
    ):
        symbols.extend(_strings(lead.get(key)))
    return tuple(dict.fromkeys(symbols))


def _timeframe_allowed(lead: Mapping[str, Any], timeframe: str) -> bool:
    preferred = _preferred_timeframes(lead)
    return bool(preferred) and timeframe in preferred


def _preferred_timeframes(lead: Mapping[str, Any]) -> tuple[str, ...]:
    condition_fit = lead.get("condition_fit")
    if not isinstance(condition_fit, Mapping):
        condition_fit = {}
    return tuple(_norm_tf(item) for item in _strings(condition_fit.get("preferred_timeframes")))


def _summaries(leads: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    for lead in leads:
        out.append(
            {
                "lead_id": lead.get("lead_id"),
                "status": lead.get("status"),
                "deployment_status": lead.get("deployment_status"),
                "priority": lead.get("priority"),
                "symbols": list(_lead_symbols(lead)),
                "preferred_timeframes": list(_preferred_timeframes(lead)),
            }
        )
    return tuple(out)


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(str(item) for item in value if str(item))
    except TypeError:
        return (str(value),)


def _norm_tf(value: Any) -> str:
    return str(value or "").strip().upper()
