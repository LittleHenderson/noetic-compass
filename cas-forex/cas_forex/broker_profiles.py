"""Broker candidate profile matrix for CAS Forex.

The entries here are routing candidates supplied by the owner / research notes.
They are not legal/regulatory approval and they do not authorize live trading.
Actual live execution still requires the owner-controlled runtime gates:
credentials + selected broker/provider config + explicit owner enable flags.

Leverage values in this matrix are *research hints* only. The effective leverage
for any real account depends on the owner's country/residency, entity, account
type, product, broker approval, and current broker terms. CAS stores them so the
cockpit can compare candidate routes, not so it can assert that the owner is
eligible for those terms.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BrokerCandidate:
    broker_id: str
    display_name: str
    website: str
    platform_notes: str
    owner_research_leverage_note: str
    configured_env_prefix: str
    verification_status: str = "PENDING_EXTERNAL_VERIFICATION"
    live_use_status: str = "GATED_BY_RUNTIME_GATES"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BROKER_CANDIDATES: tuple[BrokerCandidate, ...] = (
    BrokerCandidate(
        broker_id="hugosway",
        display_name="Hugo'sWay",
        website="https://hugosway.com/",
        platform_notes="Owner-requested broker candidate; verify account terms, MT4/MT5 availability, entity, and funding rails before live use.",
        owner_research_leverage_note="Owner supplied Hugo'sWay as a candidate route; leverage/account terms require broker-side verification.",
        configured_env_prefix="CAS_FOREX_HUGOSWAY_",
    ),
    BrokerCandidate(
        broker_id="ig",
        display_name="IG",
        website="https://www.ig.com/",
        platform_notes="Owner note: best overall broker candidate for 2026; verify Switzerland entity/account terms.",
        owner_research_leverage_note="Owner note: up to 200:1 leverage in Switzerland.",
        configured_env_prefix="CAS_FOREX_IG_",
    ),
    BrokerCandidate(
        broker_id="saxo",
        display_name="Saxo",
        website="https://www.saxo.com/",
        platform_notes="Owner note: award-winning trading platform suite; verify account/API/MT4/MT5 support for intended workflow.",
        owner_research_leverage_note="Owner note: up to 66:1 leverage in Switzerland.",
        configured_env_prefix="CAS_FOREX_SAXO_",
    ),
    BrokerCandidate(
        broker_id="swissquote",
        display_name="Swissquote",
        website="https://www.swissquote.com/",
        platform_notes="Owner note: wide range of markets; verify Switzerland account/API/broker permissions.",
        owner_research_leverage_note="Owner note: up to 100:1 leverage.",
        configured_env_prefix="CAS_FOREX_SWISSQUOTE_",
    ),
    BrokerCandidate(
        broker_id="xtb",
        display_name="XTB",
        website="https://www.xtb.com/",
        platform_notes="Owner note: user-friendly platforms; verify entity, product set, account/API availability, and leverage rules.",
        owner_research_leverage_note="Owner note: up to 500:1 leverage.",
        configured_env_prefix="CAS_FOREX_XTB_",
    ),
    BrokerCandidate(
        broker_id="etoro",
        display_name="eToro",
        website="https://www.etoro.com/",
        platform_notes="Owner note: copy-trading candidate; verify Seychelles/entity path, API limitations, and whether automation is permitted.",
        owner_research_leverage_note="Owner note: up to 400:1 leverage via Seychelles entity.",
        configured_env_prefix="CAS_FOREX_ETORO_",
    ),
    BrokerCandidate(
        broker_id="exness",
        display_name="Exness",
        website="https://www.exness.com/",
        platform_notes="Owner note: high-leverage forex candidate; verify entity, jurisdiction, and account requirements.",
        owner_research_leverage_note="Owner note: 1:100 and 1:200 leverage options.",
        configured_env_prefix="CAS_FOREX_EXNESS_",
    ),
    BrokerCandidate(
        broker_id="fxtm",
        display_name="FXTM",
        website="https://www.forextime.com/",
        platform_notes="Owner note: forex broker candidate; verify entity, leverage, and platform/API availability.",
        owner_research_leverage_note="Owner note: 1:100 and 1:200 leverage options.",
        configured_env_prefix="CAS_FOREX_FXTM_",
    ),
    BrokerCandidate(
        broker_id="axiory",
        display_name="Axiory",
        website="https://www.axiory.com/",
        platform_notes="Owner note: forex broker candidate; verify account permissions, platform/API availability, and leverage terms.",
        owner_research_leverage_note="Owner note: 1:100 and 1:200 leverage options.",
        configured_env_prefix="CAS_FOREX_AXIORY_",
    ),
    BrokerCandidate(
        broker_id="fxcm",
        display_name="FXCM",
        website="https://www.fxcm.com/",
        platform_notes="Owner note: forex broker candidate; verify entity, region, leverage, and API availability.",
        owner_research_leverage_note="Owner note: 1:100 and 1:200 leverage options.",
        configured_env_prefix="CAS_FOREX_FXCM_",
    ),
    BrokerCandidate(
        broker_id="atc_brokers",
        display_name="ATC Brokers",
        website="https://atcbrokers.com/",
        platform_notes="Owner note: forex broker candidate; verify entity, platform/API availability, and leverage terms.",
        owner_research_leverage_note="Owner note: 1:100 and 1:200 leverage options.",
        configured_env_prefix="CAS_FOREX_ATC_",
    ),
)


BROKER_BY_ID = {broker.broker_id: broker for broker in BROKER_CANDIDATES}


def broker_candidates() -> list[dict[str, Any]]:
    return [broker.to_dict() for broker in BROKER_CANDIDATES]


def selected_broker_profile(selected_broker: str | None) -> dict[str, Any] | None:
    if not selected_broker:
        return None
    broker = BROKER_BY_ID.get(selected_broker.lower())
    return broker.to_dict() if broker else None
