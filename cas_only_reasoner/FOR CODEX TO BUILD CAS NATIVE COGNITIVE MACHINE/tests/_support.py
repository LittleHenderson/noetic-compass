from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from cncm.engine import CognitiveMachine
from cncm.kernel import StateStore, TraceFabric, TransactionCoordinator, boot_state
from cncm.model import Intent, IntentType, ProblemPacket


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
SCHEMAS = ROOT / "schemas"


def fixture_document(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name / "problem.json").read_text(encoding="utf-8"))


def fixture_packet(name: str) -> ProblemPacket:
    return ProblemPacket.from_dict(fixture_document(name))


def run_fixture(name: str):
    return CognitiveMachine().run(fixture_packet(name))


def coordinator_for(name: str, *, state=None):
    packet = fixture_packet(name)
    initial = boot_state(packet) if state is None else state
    store = StateStore(initial)
    trace = TraceFabric()
    coordinator = TransactionCoordinator(store=store, trace=trace, problem=packet)
    return packet, store, trace, coordinator


def make_intent(
    coordinator: TransactionCoordinator,
    *,
    intent_type: IntentType,
    issuer: str,
    capability: str,
    scope: str,
    branch_id: str | None,
    mutation: Mapping[str, Any],
) -> Intent:
    state = coordinator.store.snapshot()
    return Intent.create(
        intent_type=intent_type,
        issuer_subsystem=issuer,
        required_capability=capability,
        target_scope=scope,
        branch_id=branch_id,
        goal_id=state.active_goal_id,
        precondition={"state_hash": state.state_hash},
        proposed_mutation=mutation,
        created_at_tick=state.logical_tick,
    )


def execute(coordinator: TransactionCoordinator, *intents: Intent):
    components = tuple(sorted({intent.issuer_subsystem for intent in intents}))
    return coordinator.execute(
        enabled_components=components,
        scheduled_components=components,
        intents=intents,
    )
