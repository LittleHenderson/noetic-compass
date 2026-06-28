# CAS-Native Agent Swarm — Scaffold

A reference implementation of a multi-agent system built on the CAS-Native
substrate. This is **not** generic CrewAI / LangGraph / AutoGen with CAS
branding. The substrate-level differences change the architecture.

## What makes this different from a generic agent swarm

Most multi-agent systems today have agents passing JSON-wrapped natural
language to each other. Drift, hallucination, overclaim, and context loss
propagate through the swarm with no structural defense. The orchestration
layer can route work and the LLM layer can reason, but the **substrate
between them is unconstrained**.

A CAS-Native swarm has agents passing **CAS-validated structured
expressions** through a bridge that enforces:

1. **Compiler validation** — every inter-agent message is a structured
   CAS expression (noetic, domain, foundation, register) that the
   compiler verifies before delivery.
2. **Claim Map enforcement** — every claim in every message is tagged
   to its evidence tier (LICENSED, FRAMEWORK_PREDICTED, NOT_LICENSED).
   The bridge rejects any output containing a NOT_LICENSED claim,
   regardless of how it's tagged.
3. **Hash-chained Evidence Packets** — every message carries an
   Evidence Packet with cryptographic linkage to the prior packet
   in the conversation. Tampering is detectable.
4. **Agent authority scoping** — each agent declares the noetics,
   domains, foundations, and Claim Map entries it can emit. Output
   exceeding scope is rejected at the agent boundary.
5. **Mode 7 cross-agent attribution** — when a multi-agent decision
   needs auditing, the Evidence Packet chain across all participating
   agents is reproducible end-to-end.

The result: drift between agents is structurally prevented, not
behaviorally hoped for. Marketing agents cannot overclaim. Customer
service agents cannot promise capabilities outside the protocol's
licensed bounds. The audit trail is regulator-grade by construction.

## Files in this scaffold

| File | Purpose |
|------|---------|
| `cas_message.py` | Inter-agent message format, Evidence Packet, Claim, CAS expression |
| `claim_map.py` | The canonical Claim Map: tier sets + claim-id inference, shared by the bridge and the agent authority layer |
| `bridge.py` | The η→ε bridge as message validator; enforces Claim Map and hash chain |
| `agent.py` | Base agent class with CAS-scoped authority (claim scope + human-review / irreversible-action gates) |
| `specialists.py` | Four reference specialists: Orchestrator, Customer Service, Marketing, Audit |
| `demo.py` | End-to-end runnable demo with four scenarios |

## Running the demo

```bash
python demo.py      # or: python3 demo.py
```

The demo shows four scenarios, each exercising a different real enforcement
mechanism:
- **Scenario 1 — Happy path**: customer question routed through orchestrator,
  answered by customer service within Claim Map, audited by audit agent.
- **Scenario 2 — Human gate**: a marketing draft is delivered only to the
  human-review queue, and the agent is *structurally* unable to reach a
  customer directly (`requires_human_review` enforced at the agent boundary,
  not by a hardcoded recipient).
- **Scenario 3 — Bridge defense-in-depth**: even when an agent's own authority
  check is bypassed, the bridge independently catches a NOT_LICENSED claim
  laundered as LICENSED and suppresses the message.
- **Scenario 4 — Agent-boundary least privilege**: an agent is blocked from
  emitting a perfectly-licensed claim that lies *outside its own* Claim Map
  scope (`allowed_claim_ids` enforced).

Every enforcement decision — delivery, bridge suppression, and agent-boundary
block — is recorded in the audit trail printed at the end of the run.

## The four reference specialists

### OrchestratorAgent
Parses incoming requests into CAS-IntentIR, routes to specialists based
on which Cognitive Operator the intent invokes. Has authority across all
noetics/domains/foundations (routing role) but cannot make external-facing
claims. Routing decisions themselves emit Evidence Packets.

### CustomerServiceAgent
Handles inbound customer requests within the LICENSED tier of the Claim
Map. Cannot speculate. Cannot promise capabilities outside the protocol's
licensed bounds. If a customer asks about closed-API models, the agent
accurately describes the open-weight bound rather than guessing.

### MarketingAgent
Generates external-facing content. Always requires human review before
publication. Has access to a narrower Claim Map subset than customer
service (only LICENSED tier; no FRAMEWORK_PREDICTED tier even). Drafts
that exceed Claim Map vocabulary are suppressed by the bridge.

### AuditAgent
The watchdog. Validates other agents' Evidence Packets against the
Claim Map. Detects drift, scope violations, hash chain anomalies. The
bi-agent audit methodology from the CAS Harness Spec Sheet applied to
the swarm itself.

## Extending the swarm — additional specialists you'd want in production

| Specialist | Role | Notes |
|------------|------|-------|
| `SalesAgent` | Enterprise sales motion | Human-led for actual pitches; agent handles qualification, scheduling, contract prep |
| `MaintenanceAgent` | Infrastructure ops | Monitors platform health, files incidents, auto-restarts within bounds |
| `ResearchAgent` | Stage 11+ validation runs | Long-running async — initiates GPU runs, monitors progress, emits results |
| `ComplianceAgent` | SOC 2 / HIPAA evidence collection | Automates evidence gathering for compliance audits |
| `BillingAgent` | Stripe / subscription management | Within tight Claim Map scope around financial claims |
| `DocsAgent` | Documentation lookup and synthesis | Internal-facing only, helps customer service with deep lookups |

Each subclass of `CASAgent` declares its `AgentAuthority` and provides
its `system_prompt` and `available_tools`. The bridge does the rest.

## Operational architecture in production

The scaffold runs the agents inline for demonstration. In production:

- **Persistent runtime**: each agent runs in its own container or function,
  with messages flowing through a durable queue (SQS, Pub/Sub, or Temporal).
- **Triggers**: webhooks for ticket arrivals, cron jobs for scheduled
  marketing/maintenance, event-driven invocations from the platform.
- **Evidence Packet storage**: WORM-anchored S3 bucket (Object Lock enabled)
  for the regulator-grade audit trail. Each Evidence Packet is independently
  inspectable forever.
- **Hash chain anchoring**: periodic chain anchors written to a public
  blockchain or notary service for tamper-evident long-term audit.
- **Mode 7 trace export**: cross-agent traces exported on demand for
  customer audit requests or regulatory inquiries.

## What this scaffold proves

The architectural commitments from the CAS Harness Spec Sheet —
reserved-language discipline, Evidence Packet methodology, bit-identical
reproducibility, mechanically verifiable claims, tiered claim attribution
— compose naturally to the multi-agent layer. The Claim Map isn't just
for the core inference; it governs every agent's output. The Evidence
Packet isn't just per-inference; it's per-message-per-agent, with
cross-agent chain of custody.

This is the differentiated swarm architecture that other multi-agent
platforms can't offer because their substrate doesn't permit it.

## What this scaffold does NOT do

- Real LLM inference (specialists return deterministic responses for clarity)
- Real CAS compiler validation (`validated=True` is set rather than computed)
- Real persistent storage (audit log is in-memory)
- Real network routing between agents (single-process delivery)
- Real authority differentiation between user identity and agent identity

In production each of these has a real implementation. The scaffold's job
is to demonstrate the structural shape, not to be deployable as-is.

## Status

Reference implementation. Pending IP attorney review (Provisional
#64/037,173 plus the four potentially-separate filings identified in
the Spec Sheet) before any external deployment.
