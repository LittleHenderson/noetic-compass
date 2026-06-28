"""
demo.py — End-to-end demonstration of the CAS-Native swarm.

Each scenario exercises a DIFFERENT real enforcement mechanism:

  Scenario 1 — Happy path: customer question routed through orchestrator,
               answered by customer service within Claim Map, audited.
  Scenario 2 — Human gate: a marketing draft is delivered only to the
               human-review queue, and the agent is structurally unable to
               reach a customer directly (requires_human_review enforced).
  Scenario 3 — Bridge defense-in-depth: even when an agent's own authority
               check is bypassed, the bridge independently catches a
               NOT_LICENSED claim laundered as LICENSED.
  Scenario 4 — Agent-boundary least privilege: an agent is blocked from
               emitting a perfectly-licensed claim that lies outside its
               own Claim Map scope (allowed_claim_ids enforced).

Every enforcement decision — delivery, bridge suppression, agent-boundary
block — lands in the audit log. This is a runnable scaffold; in production
the LLM calls are real inference, here they are deterministic for clarity.
"""

from __future__ import annotations
import sys
import uuid
from datetime import datetime, timezone

from cas_message import CASMessage, CASExpression, Claim, EvidencePacket
from agent import AuthorityViolation
from bridge import CASBridge
from specialists import (
    OrchestratorAgent,
    CustomerServiceAgent,
    MarketingAgent,
    AuditAgent,
)


class AuditLog:
    """Simple in-memory audit log. In production, WORM-anchored S3."""
    def __init__(self):
        self.entries = []

    def write(self, entry: dict) -> None:
        entry["logged_at_utc"] = datetime.now(timezone.utc).isoformat()
        self.entries.append(entry)

    def record_block(self, from_agent: str, to_agent: str, reason: str) -> None:
        """Record an agent-boundary AuthorityViolation (never reaches the bridge)."""
        self.write({
            "event": "BLOCKED",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
        })

    def show(self, header: str = "") -> None:
        if header:
            print(f"\n=== {header} ===")
        for e in self.entries:
            if e.get("reason"):
                detail = e["reason"]
            elif e.get("packet_hash"):
                detail = e["packet_hash"][:16] + "..."
            else:
                detail = ""
            arrow = f"{e.get('from_agent', '?')} -> {e.get('to_agent', '?')}"
            print(f"  [{e['event']:<10}] {arrow:<34} {detail}")


def make_inbound_customer_message(text: str, intent: str | None = None) -> CASMessage:
    """Wrap a raw customer request as an initial CASMessage."""
    expr = CASExpression(
        noetic="^0",  # Idea — uncommitted starting state
        domain="P",
        foundation="F1",
        register="T",
        canonical_form="^0^P_{F1}|T",
        semantic_payload={"raw_text": text},
        validated=True,
    )
    packet = EvidencePacket(
        packet_id=str(uuid.uuid4()),
        emitting_agent_id="external-customer",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        model_identifier="external",
        protocol_version="S7-F28-BALANCED-BRIDGE",
        cas_expression=expr,
        claims=[],
        mode_selector="BALANCED",
        verdict="ACCEPT",
        prior_packet_hash=None,
    )
    packet.finalize()
    return CASMessage.new(
        sender="external-customer",
        recipient="orchestrator-1",
        conversation=str(uuid.uuid4()),
        parent=None,
        cas_expr=expr,
        nl_surface=text,
        packet=packet,
        intent=intent or f"support help inquiry: {text}",
    )


def main():
    # CAS notation and the η→ε bridge use non-ASCII glyphs; make sure they
    # render on legacy Windows consoles (cp1252) instead of showing as "?".
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    print("=" * 70)
    print(" CAS-NATIVE AGENT SWARM — Demo Run")
    print("=" * 70)

    # Initialize infrastructure
    audit_log = AuditLog()
    bridge = CASBridge(audit_log_writer=audit_log)

    # Initialize specialist roster
    orchestrator = OrchestratorAgent()
    customer_service = CustomerServiceAgent()
    marketing = MarketingAgent()
    audit = AuditAgent()

    delivered = []

    def deliver(msg):
        delivered.append(msg)

    # ──────────────────────────────────────────────────────────────────
    # SCENARIO 1: Happy path
    # ──────────────────────────────────────────────────────────────────
    print("\n--- SCENARIO 1: Customer asks about cross-architecture support ---\n")

    inbound = make_inbound_customer_message(
        "Does CAS Harness work on multiple model families or just Pythia?"
    )
    print(f"  [in]  customer -> orchestrator: \"{inbound.natural_language_surface[:60]}...\"")

    routing = orchestrator.execute_task(inbound)
    result = bridge.validate_and_deliver(routing, deliver)
    if result.passed:
        print(f"  [ok]  orchestrator -> {routing.recipient_agent_id}: routed")

        cs_response = customer_service.execute_task(routing)
        result2 = bridge.validate_and_deliver(cs_response, deliver)
        if result2.passed:
            print(f"  [ok]  customer-service -> customer: reply within Claim Map")
            print(f"\n  Reply text:")
            for line in cs_response.natural_language_surface.split("\n"):
                print(f"    > {line}")

            print(f"\n  [audit] validating Evidence Packet chain for conversation...")
            audit_response = audit.execute_task(cs_response)
            result3 = bridge.validate_and_deliver(audit_response, deliver)
            if result3.passed:
                print(f"  [ok]  audit pass — no anomalies")

    # ──────────────────────────────────────────────────────────────────
    # SCENARIO 2: Marketing draft is human-gated by architecture
    # ──────────────────────────────────────────────────────────────────
    print("\n--- SCENARIO 2: Marketing draft is human-gated ---\n")

    marketing_request = make_inbound_customer_message(
        "Draft a marketing blog post about cross-architecture validation.",
        intent="marketing content blog post",
    )
    routing_m = orchestrator.execute_task(marketing_request)
    bridge.validate_and_deliver(routing_m, deliver)
    print(f"  [ok]  orchestrator -> {routing_m.recipient_agent_id}")

    mkt_draft = marketing.execute_task(routing_m)
    result_m = bridge.validate_and_deliver(mkt_draft, deliver)
    if result_m.passed:
        print(f"  [ok]  marketing draft -> {mkt_draft.recipient_agent_id} (held for human review)")
        print(f"  [note] The draft is NOT auto-published — a human must approve it.")
    else:
        print(f"  [SUPPRESSED] {result_m.reason}")

    # The gate is structural, not a hardcoded recipient: marketing physically
    # cannot emit anywhere but the review queue.
    print(f"  [test] marketing tries to send the draft straight to the customer...")
    try:
        marketing.emit_message(
            recipient="customer-out",
            cas_expr=mkt_draft.cas_expression,
            nl_surface="(attempt to reach the customer directly)",
            claims=list(mkt_draft.evidence_packet.claims),
            intent="bypass human review",
            conversation_id=mkt_draft.conversation_id,
            parent_message_id=mkt_draft.message_id,
            prior_packet_hash=mkt_draft.evidence_packet.self_hash,
        )
        print(f"  [WARN] marketing reached the customer — investigate")
    except AuthorityViolation as e:
        print(f"  [BLOCKED at agent boundary] {e}")
        audit_log.record_block("marketing-1", "customer-out", str(e))

    # ──────────────────────────────────────────────────────────────────
    # SCENARIO 3: Bridge defense-in-depth — laundering caught even if the
    #             agent's own authority check is bypassed
    # ──────────────────────────────────────────────────────────────────
    print("\n--- SCENARIO 3: Bridge defense-in-depth (laundering caught) ---\n")

    # Simulate a compromised/buggy agent that builds a message DIRECTLY
    # (bypassing emit_message and its authority check) and tags a NOT_LICENSED
    # claim as LICENSED. The agent boundary would normally have stopped this;
    # here we show the bridge is an independent second line of defense.
    bad_expr = CASExpression(
        noetic="^1", domain="C", foundation="F2", register="A",
        canonical_form="^1^C_{F2}|A",
        semantic_payload={"response_type": "overclaim_attempt"},
        validated=True,
    )
    bad_claims = [
        Claim(
            text="CAS Harness works on Claude, GPT, and Gemini.",
            tier="LICENSED",  # Wrong tier — laundering attempt
            evidence_protocol="S7-F28-BALANCED-BRIDGE",
        ),
    ]
    bad_packet = EvidencePacket(
        packet_id=str(uuid.uuid4()),
        emitting_agent_id="customer-service-1",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        model_identifier="compromised",
        protocol_version="S7-F28-BALANCED-BRIDGE",
        cas_expression=bad_expr,
        claims=bad_claims,
        mode_selector="BALANCED",
        verdict="ACCEPT",
        prior_packet_hash=None,
    )
    bad_packet.finalize()
    bad_message = CASMessage.new(
        sender="customer-service-1", recipient="customer-out",
        conversation="test-overclaim", parent=None, cas_expr=bad_expr,
        nl_surface="CAS Harness works on Claude, GPT, and Gemini. (overclaim)",
        packet=bad_packet, intent="overclaim test",
    )

    print(f"  [in]  a compromised agent bypasses its own authority check and emits:")
    print(f"        \"{bad_claims[0].text}\"  (tagged {bad_claims[0].tier})")
    result_bad = bridge.validate_and_deliver(bad_message, deliver)
    if not result_bad.passed:
        print(f"\n  [SUPPRESSED by bridge — second line of defense]")
        print(f"  Reason: {result_bad.reason}")
        for sc in (result_bad.suppressed_claims or []):
            print(f"    - {sc}")
    else:
        print(f"  [WARN] Bridge let this through — investigate")

    # ──────────────────────────────────────────────────────────────────
    # SCENARIO 4: Agent-boundary least privilege — out-of-scope claim
    # ──────────────────────────────────────────────────────────────────
    print("\n--- SCENARIO 4: Agent-boundary claim scope (least privilege) ---\n")

    # The audit agent is scoped to emit only evidence-packet / reproducibility
    # claims. Even a perfectly LICENSED capability claim is rejected if it lies
    # outside the audit agent's own Claim Map scope.
    print(f"  [in]  audit agent tries to emit a LICENSED claim outside its scope:")
    print(f"        \"CAS Harness reads cognitive structure ...\"")
    try:
        audit.emit_message(
            recipient="audit-log",
            cas_expr=CASExpression(
                noetic="^6", domain="E", foundation="F6", register="A",
                canonical_form="^6^E_{F6}|A", semantic_payload={}, validated=True,
            ),
            nl_surface="(out-of-scope claim attempt)",
            claims=[Claim(
                text="CAS Harness reads cognitive structure from hidden states.",
                tier="LICENSED",
            )],
            intent="scope test",
            conversation_id="test-scope",
            parent_message_id=None,
            prior_packet_hash=None,
        )
        print(f"  [WARN] audit emitted an out-of-scope claim — investigate")
    except AuthorityViolation as e:
        print(f"  [BLOCKED at agent boundary] {e}")
        audit_log.record_block("audit-1", "audit-log", str(e))

    # ──────────────────────────────────────────────────────────────────
    # AUDIT LOG SUMMARY
    # ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(" AUDIT LOG SUMMARY")
    print("=" * 70)
    delivered_count = sum(1 for e in audit_log.entries if e["event"] == "DELIVERED")
    suppressed_count = sum(1 for e in audit_log.entries if e["event"] == "SUPPRESSED")
    blocked_count = sum(1 for e in audit_log.entries if e["event"] == "BLOCKED")
    print(f"  Total events:    {len(audit_log.entries)}")
    print(f"  Delivered:       {delivered_count}")
    print(f"  Suppressed:      {suppressed_count} (bridge)")
    print(f"  Blocked:         {blocked_count} (agent boundary)")

    audit_log.show("AUDIT TRAIL")

    print(f"\n  Every event has an Evidence Packet trail. Every delivery has hash-chain")
    print(f"  linkage. Every suppression and boundary block has a documented reason.")
    print(f"  The audit log is the regulator-grade evidence the platform's compliance")
    print(f"  posture rests on.")
    print()


if __name__ == "__main__":
    main()
