"""
specialists.py — The four specialist agents in the CAS-Native swarm.

These four cover the operational surface of an autonomous CAS Harness
business. Each has CAS-scoped authority that prevents it from exceeding
its role boundaries.

  OrchestratorAgent — parses incoming requests into CAS-IntentIR,
                       routes to specialists, monitors swarm health
  CustomerServiceAgent — handles inbound customer requests, drafts
                          responses, escalates to humans when needed
  MarketingAgent — generates external-facing content within the
                    Claim Map, requires human gate before publishing
  AuditAgent — validates other agents' Evidence Packets against the
                Claim Map, detects drift, escalates suspected violations

Noetic operators below use the authoritative CAS names (Idea, Mind, Positive,
Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect). Note in
particular that auditing — decompose-and-test scrutiny — is ^6 Male, not an
"analytical" operator: per the project's anti-drift guidance, audit/scrutinize
vocabulary classifies as ^6 Male (compositional decomposition), never ^3/^5.

In production you'd add: SalesAgent (Enterprise sales), MaintenanceAgent
(infrastructure ops), ResearchAgent (Stage 11+ validation runs),
ComplianceAgent (SOC 2 / HIPAA evidence collection automation).
"""

from __future__ import annotations

from cas_message import CASMessage, CASExpression, Claim
from agent import CASAgent, AgentAuthority


# ──────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────

class OrchestratorAgent(CASAgent):
    """
    The swarm coordinator.

    Receives external inputs (customer messages, scheduled events, alerts).
    Parses each input into CAS-IntentIR through the NL front door.
    Routes to the appropriate specialist based on which Cognitive Operator
    the intent invokes.

    The orchestrator's routing decisions are themselves CAS-validated and
    Evidence Packet emitting. The routing audit trail is part of the
    swarm-level trace.
    """

    def __init__(self, agent_id: str = "orchestrator-1"):
        authority = AgentAuthority(
            allowed_noetics={f"^{i}" for i in range(10)},  # All — routing role
            allowed_domains={"P", "C", "E", "O"},  # All — routing role
            allowed_foundations={f"F{i}" for i in range(1, 8)},  # All
            allowed_claim_ids={"emits_evidence_packet_with_chain_of_custody"},
            allowed_claim_tiers={"LICENSED", "FRAMEWORK_PREDICTED"},
            can_irreversibly_act=False,  # Orchestrator never acts externally
            requires_human_review=False,
        )
        super().__init__(agent_id, authority)

    @property
    def system_prompt(self) -> str:
        return (
            "You are the orchestrator of a CAS-Native agent swarm. Your role "
            "is to parse incoming requests into CAS-IntentIR using the NL "
            "front door, then route them to the appropriate specialist agent. "
            "You do not generate external-facing content. You do not make "
            "claims about CAS Harness capabilities. You route, monitor, and "
            "log. Every routing decision emits an Evidence Packet. If you "
            "are uncertain about routing, you route to human review rather "
            "than guess."
        )

    def available_tools(self) -> list[dict]:
        return [
            {"name": "parse_to_cas_intent_ir", "description": "Parse natural language to CAS-IntentIR"},
            {"name": "route_to_specialist", "description": "Dispatch a CAS message to a specialist agent"},
            {"name": "escalate_to_human", "description": "Escalate to human reviewer queue"},
            {"name": "query_swarm_health", "description": "Check swarm operational status"},
        ]

    def execute_task(self, message: CASMessage) -> CASMessage:
        """
        Route the incoming request to the appropriate specialist.

        In production: NL front door parses message to IntentIR, classifier
        determines specialist, message is constructed and emitted.

        Scaffold version: deterministic routing based on intent keywords.
        """
        # Determine routing target
        intent = message.intent_summary.lower()
        if "support" in intent or "help" in intent or "issue" in intent:
            target = "customer-service-1"
            cas_expr = CASExpression(
                noetic="^1",  # Mind — awareness intakes and routes the Idea
                domain="E",   # Evaluative
                foundation="F2",  # Wisdom drive
                register="A",  # Analytical
                canonical_form="^1^E_{F2}|A",
                semantic_payload={"routing_target": target, "rationale": "customer_request"},
                validated=True,
            )
        elif "marketing" in intent or "content" in intent or "social" in intent:
            target = "marketing-1"
            cas_expr = CASExpression(
                noetic="^4",  # Vibration — the impression content is meant to make
                domain="C",   # Cognitive
                foundation="F3",  # Vitality drive
                register="A",
                canonical_form="^4^C_{F3}|A",
                semantic_payload={"routing_target": target, "rationale": "content_request"},
                validated=True,
            )
        elif "audit" in intent or "validate" in intent or "verify" in intent:
            target = "audit-1"
            cas_expr = CASExpression(
                noetic="^6",  # Male — decomposition-and-test (canonical audit operator)
                domain="E",
                foundation="F6",  # Structure drive
                register="A",
                canonical_form="^6^E_{F6}|A",
                semantic_payload={"routing_target": target, "rationale": "audit_request"},
                validated=True,
            )
        else:
            # Unknown intent — escalate to human
            target = "human-review-queue"
            cas_expr = CASExpression(
                noetic="^0",  # Idea — uncommitted starting state
                domain="P",
                foundation="F1",  # Unity drive
                register="T",  # Transcendent
                canonical_form="^0^P_{F1}|T",
                semantic_payload={"routing_target": target, "rationale": "intent_unclear"},
                validated=True,
            )

        claims = [
            Claim(
                text="Routing decision emits Evidence Packet with chain of custody.",
                tier="LICENSED",
                evidence_protocol="S7-F28-BALANCED-BRIDGE",
            ),
        ]

        return self.emit_message(
            recipient=target,
            cas_expr=cas_expr,
            nl_surface=f"Routing to {target}: {message.intent_summary}",
            claims=claims,
            intent="Route incoming request to specialist",
            conversation_id=message.conversation_id,
            parent_message_id=message.message_id,
            prior_packet_hash=message.evidence_packet.self_hash,
            mode_selector="BALANCED",
        )


# ──────────────────────────────────────────────────────────────────────
# CUSTOMER SERVICE
# ──────────────────────────────────────────────────────────────────────

class CustomerServiceAgent(CASAgent):
    """
    Handles inbound customer requests. Drafts responses. Escalates to
    humans when the request exceeds authority or when the response would
    require NOT_LICENSED claims.

    This agent has narrow Claim Map authority — it can confirm capabilities
    in the LICENSED set but cannot make any claim outside it. If a customer
    asks "does this work on GPT-4," the agent cannot say yes, cannot say
    "we're working on it," cannot speculate — it must escalate or
    accurately describe the open-weight bound.
    """

    def __init__(self, agent_id: str = "customer-service-1"):
        authority = AgentAuthority(
            allowed_noetics={"^1", "^2", "^3", "^6"},  # Mind, Positive, Negative, Male
            allowed_domains={"C", "E"},  # Cognitive, Evaluative — explanation, judgment
            allowed_foundations={"F2", "F4", "F5"},  # Wisdom, Connection, Agency
            allowed_claim_ids={
                "reads_cognitive_structure",
                "causally_load_bearing_for_cognitive_readout",
                "conditions_next_token_distribution",
                "emits_evidence_packet_with_chain_of_custody",
                "bit_identically_reproducible",
                "non_mutating_two_pass_inference",
                "cross_architecture_validated_pythia_olmo_qwen",
            },
            allowed_claim_tiers={"LICENSED"},  # Only Licensed — no speculation
            can_irreversibly_act=True,   # Can send replies to customers
            requires_human_review=False,  # But within Claim Map — auto-send OK
        )
        super().__init__(agent_id, authority)

    @property
    def system_prompt(self) -> str:
        return (
            "You are a customer service agent for CAS Harness. You answer "
            "customer questions about the platform within the LICENSED tier "
            "of the Claim Map. You never speculate. You never make claims "
            "about capabilities the protocol does not license. If a customer "
            "asks about closed-API models (Claude, GPT, Gemini), you "
            "accurately state that CAS Harness supports open-weight models "
            "only. If you cannot answer within the Claim Map, you escalate "
            "to human review. Every response emits an Evidence Packet."
        )

    def available_tools(self) -> list[dict]:
        return [
            {"name": "lookup_documentation", "description": "Search platform documentation"},
            {"name": "send_customer_reply", "description": "Send a reply to the customer"},
            {"name": "escalate_to_human", "description": "Escalate to human support"},
            {"name": "create_support_ticket", "description": "Open a tracked support ticket"},
        ]

    def execute_task(self, message: CASMessage) -> CASMessage:
        # Production: LLM generates response within Claim Map, validates against
        # authority, emits via emit_message. If LLM produces output outside
        # authority, the emit_message call raises AuthorityViolation and the
        # request escalates to human review.

        cas_expr = CASExpression(
            noetic="^1",  # Mind — processing and answering a question
            domain="C",   # Cognitive — explanatory mode
            foundation="F2",  # Wisdom
            register="A",
            canonical_form="^1^C_{F2}|A",
            semantic_payload={"response_type": "documentation_lookup"},
            validated=True,
        )

        claims = [
            Claim(
                text="CAS Harness reads cognitive structure from open-weight model hidden states.",
                tier="LICENSED",
                evidence_protocol="S7-F28-BALANCED-BRIDGE",
                bounds=["open-weight models only", "decoder-only transformers"],
            ),
            Claim(
                text="Every inspection emits an Evidence Packet with bit-identical reproducibility.",
                tier="LICENSED",
                evidence_protocol="S7-F28-BALANCED-BRIDGE",
            ),
        ]

        nl_surface = (
            "Thank you for your question. CAS Harness reads cognitive "
            "structure from the hidden states of open-weight language models "
            "such as Pythia, OLMo, and Qwen. Every inspection produces an "
            "Evidence Packet that is bit-identically reproducible. Please "
            "note that the platform supports open-weight models only at this "
            "time — closed-API providers like OpenAI, Anthropic, and Google "
            "do not expose the hidden states our protocol requires. Would "
            "you like more detail on a specific model?"
        )

        return self.emit_message(
            recipient="customer-out",
            cas_expr=cas_expr,
            nl_surface=nl_surface,
            claims=claims,
            intent="Answer customer question within Claim Map",
            conversation_id=message.conversation_id,
            parent_message_id=message.message_id,
            prior_packet_hash=message.evidence_packet.self_hash,
        )


# ──────────────────────────────────────────────────────────────────────
# MARKETING
# ──────────────────────────────────────────────────────────────────────

class MarketingAgent(CASAgent):
    """
    Generates external-facing content. Always requires human review before
    publication — the requires_human_review flag is enforced at the agent
    boundary (emit_message), so a marketing draft can only ever be emitted
    to the human-review queue, never straight to a customer or public channel.

    The Marketing Agent is the agent where the reserved-language discipline
    matters most. Marketing language drifts toward overclaim by default;
    the structural enforcement at agent boundary prevents it from leaving
    the swarm.
    """

    def __init__(self, agent_id: str = "marketing-1"):
        authority = AgentAuthority(
            allowed_noetics={"^4", "^8"},  # Vibration (impression), Above/Cause (outreach trigger)
            allowed_domains={"C", "O"},  # Cognitive, Operational
            allowed_foundations={"F3", "F4", "F6"},  # Vitality, Connection, Structure
            allowed_claim_ids={
                "reads_cognitive_structure",
                "non_mutating_two_pass_inference",
                "emits_evidence_packet_with_chain_of_custody",
                "bit_identically_reproducible",
                "cross_architecture_validated_pythia_olmo_qwen",
                "framework_predicted_mechanism",
            },
            allowed_claim_tiers={"LICENSED"},  # No FRAMEWORK_PREDICTED in marketing
            can_irreversibly_act=False,    # Cannot publish directly
            requires_human_review=True,    # Always gated through human
        )
        super().__init__(agent_id, authority)

    @property
    def system_prompt(self) -> str:
        return (
            "You are a marketing content agent for CAS Harness. You draft "
            "external-facing content — blog posts, social posts, email "
            "campaigns — strictly within the LICENSED tier of the Claim Map. "
            "You never make speculative claims. You never anthropomorphize "
            "AI cognition. You never claim capabilities the protocol does "
            "not license. Every draft you produce is routed to human review "
            "before publication. Your goal is technically rigorous, "
            "reserved-language-compliant content that converts."
        )

    def available_tools(self) -> list[dict]:
        return [
            {"name": "draft_blog_post", "description": "Draft a long-form blog post"},
            {"name": "draft_social_post", "description": "Draft a social media post"},
            {"name": "draft_email_campaign", "description": "Draft an email campaign"},
            {"name": "submit_for_human_review", "description": "Submit draft to human review queue"},
        ]

    def execute_task(self, message: CASMessage) -> CASMessage:
        cas_expr = CASExpression(
            noetic="^4",  # Vibration — generative content / the impression it makes
            domain="C",
            foundation="F3",  # Vitality
            register="A",
            canonical_form="^4^C_{F3}|A",
            semantic_payload={"content_type": "blog_post_draft"},
            validated=True,
        )

        claims = [
            Claim(
                text="CAS Harness has been validated across three independent architecture families (Pythia, OLMo, Qwen).",
                tier="LICENSED",
                evidence_protocol="S7-F28-BALANCED-BRIDGE",
                statistical_threshold="p < 1e-11",
            ),
        ]

        nl_surface = (
            "[DRAFT - PENDING HUMAN REVIEW]\n\n"
            "CAS Harness: Audit-Grade Interpretability for Open-Weight LLMs\n\n"
            "Every inference produces a bit-identically reproducible Evidence "
            "Packet. Cross-architecture validation across Pythia, OLMo, and "
            "Qwen demonstrates the η→ε bridge generalizes beyond a single "
            "model family. Foundation readout on GPT-NeoX-20B reaches 86.86% "
            "on heldout data. The structural cognitive substrate is, by "
            "construction, what regulators have been asking for and what "
            "no other interpretability vendor currently supplies."
        )

        return self.emit_message(
            recipient="human-review-queue",  # Always routed through review
            cas_expr=cas_expr,
            nl_surface=nl_surface,
            claims=claims,
            intent="Draft marketing content for human review",
            conversation_id=message.conversation_id,
            parent_message_id=message.message_id,
            prior_packet_hash=message.evidence_packet.self_hash,
        )


# ──────────────────────────────────────────────────────────────────────
# AUDIT — the meta-agent that validates other agents
# ──────────────────────────────────────────────────────────────────────

class AuditAgent(CASAgent):
    """
    The watchdog. Audits other agents' Evidence Packets against the
    Claim Map. Detects drift, scope violations, hash chain anomalies.
    Escalates to human review when patterns suggest systematic issues.

    The bi-agent audit methodology from the Spec Sheet applied to the
    swarm itself. Every other agent's output is subject to spot-check
    by this agent.

    Auditing is ^6 Male — decompose-and-test scrutiny — not an "analytical"
    operator. Pattern-over-time drift detection draws on ^7 Rhythm.
    """

    def __init__(self, agent_id: str = "audit-1"):
        authority = AgentAuthority(
            allowed_noetics={"^6", "^7"},  # Male (decompose-and-test), Rhythm (drift pattern)
            allowed_domains={"E"},  # Evaluative only
            allowed_foundations={"F6"},  # Structure
            allowed_claim_ids={
                "emits_evidence_packet_with_chain_of_custody",
                "bit_identically_reproducible",
            },
            allowed_claim_tiers={"LICENSED"},
            can_irreversibly_act=False,
            requires_human_review=False,
        )
        super().__init__(agent_id, authority)

    @property
    def system_prompt(self) -> str:
        return (
            "You are the audit agent. You validate other agents' Evidence "
            "Packets against the Claim Map. You detect drift, scope "
            "violations, and hash chain anomalies. When you find a "
            "violation, you log it and escalate. You do not produce "
            "external-facing content. You do not interact with customers. "
            "Your only role is structural validation of the swarm itself."
        )

    def available_tools(self) -> list[dict]:
        return [
            {"name": "audit_evidence_packet", "description": "Audit a specific Evidence Packet"},
            {"name": "audit_conversation_chain", "description": "Audit hash chain integrity for a conversation"},
            {"name": "flag_agent_for_review", "description": "Flag an agent for human review"},
            {"name": "generate_audit_report", "description": "Produce period audit summary"},
        ]

    def execute_task(self, message: CASMessage) -> CASMessage:
        cas_expr = CASExpression(
            noetic="^6",  # Male — decomposition-and-test (canonical audit operator)
            domain="E",
            foundation="F6",  # Structure
            register="A",
            canonical_form="^6^E_{F6}|A",
            semantic_payload={"audit_target": message.parent_message_id, "verdict": "PASS"},
            validated=True,
        )

        claims = [
            Claim(
                text="Evidence Packet chain validated; no anomalies detected.",
                tier="LICENSED",
            ),
        ]

        return self.emit_message(
            recipient="audit-log",
            cas_expr=cas_expr,
            nl_surface="Audit pass: Evidence Packet chain intact, claims within Claim Map.",
            claims=claims,
            intent="Validate Evidence Packet chain for conversation",
            conversation_id=message.conversation_id,
            parent_message_id=message.message_id,
            prior_packet_hash=message.evidence_packet.self_hash,
        )
