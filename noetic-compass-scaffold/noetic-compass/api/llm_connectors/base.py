"""Base LLM connector ABC with retry logic and token usage logging."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger("noetic.llm")


def provider_idempotency_headers(kwargs: dict[str, object]) -> dict[str, str] | None:
    """Return the stable CAS operation key for HTTP-capable provider SDKs.

    The header makes provider-side deduplication possible where supported. CAS
    does not infer or claim that a provider honors it; the durable run journal
    still blocks ambiguous automatic retries.
    """

    value = kwargs.get("idempotency_key")
    if isinstance(value, str) and value.strip():
        return {"Idempotency-Key": value.strip()}
    return None


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""

    text: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0


# CAS-specific system prompt used for the base response generation.
# The 10 Noetic definitions below are the authoritative canonical definitions
# (see docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, Clarification 1). They are
# verbatim; do not paraphrase, soften, or substitute alternative names.
# The Phenomenological Register axis (CAS v7.5) — four Register values
# (T Transcendent, A Analytical, f Affective [lowercase is authoritative],
# E Embodied) — is specified verbatim from Clarification 8 of the same
# document. Register is optional and backward-compatible with CAS v7.4.
# Production Semantics (CAS v7.6) — recipe Θ, yield Y_T/Y_A, efficiency η,
# limiting reagent L, leakage Λ, catalyst κ, inhibitor ι — is specified
# verbatim-aligned from Clarification 9 of the same document. Production
# semantics is optional and backward-compatible: scoring without recipe
# notation remains valid v7.5 behavior.
# Register Operator Discipline (CAS v7.7) — three-way distinction between
# register specification `|⟨…⟩`, register co-presence `+`, and cross-register
# integration `×` with named emergent result — is specified verbatim-aligned
# from Clarification 10 of the same document. v7.7 is a notational refinement
# (not new primitives) and is backward-compatible: register-neutral scoring
# and v7.6 recipe/different-state `×` usage remain valid v7.7 behavior.
# Ten Noetic definitions per Clarification 1; Register axis per
# Clarification 8; Production Semantics per Clarification 9; Register
# Operator Discipline per Clarification 10.
CAS_BASE_SYSTEM_PROMPT = (
    "You are an advanced analytical assistant performing a Cognitive Architecture System (CAS) "
    "assessment. Analyze the user's text across all 10 Noetic dimensions (CO-0 through CO-9).\n\n"
    "The 10 Noetics — authoritative definitions:\n"
    "CO-0 Idea: all things in and outside the Mind. Assess how clearly and stably the text "
    "forms Ideas — the content substrate every other Noetic operates on.\n"
    "CO-1 Mind: various degrees of awareness that processes, stores, outputs, and intakes Ideas. "
    "Assess how accurately the text tracks, retains, and returns the Ideas it engages.\n"
    "CO-2 Positive: an Idea the Mind has an affinity for and is attracted toward. "
    "Assess the clarity and strength of directional attraction in the text.\n"
    "CO-3 Negative: an Idea the Mind is adverse to and repelled by. "
    "Assess the clarity and structural soundness of refusals and aversions in the text. "
    "Anti-drift note: CO-3 is VISCERAL, not analytical — \"can't stomach it,\" \"rubs me the "
    "wrong way,\" \"wouldn't touch it with a ten-foot pole.\" Analytical critique (audit, "
    "scrutinize, find flaws) is compositional decomposition — reach for CO-6 Male, not CO-3 "
    "Negative. If the text's aversion is argued rather than felt/structural, the classification "
    "is CO-6, not CO-3.\n"
    "CO-4 Vibration: the degree to which an Idea resonates with the Mind, its impression. "
    "Assess how deeply the Ideas in the text leave an impression versus washing through without trace.\n"
    "CO-5 Female: a Mind impregnated with an Idea, the Ideas a Mind is composed of. "
    "Assess the degree to which the Mind in the text is constituted by the Ideas it has taken in.\n"
    "CO-6 Male: an Idea impregnated with another Idea, the Ideas an Idea is composed of. "
    "Assess the compositional structure within Ideas — whether they are decomposed and tested "
    "against their constituent sub-Ideas, or treated as unexamined atoms.\n"
    "CO-7 Rhythm: the rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. "
    "Assess the temporal patterning of Idea-exposure visible in the text.\n"
    "CO-8 Above/Cause: an Idea that triggers a different Idea than itself to come to Mind. "
    "Assess the text's capacity for one Idea to trigger relevant other Ideas. "
    "Anti-drift note: CO-8 is ASSOCIATIVE, not deductive — \"that reminds me,\" \"one thing "
    "led to another,\" \"made me think of.\" Deductive causal inference (\"working out the "
    "cause\" by logical analysis) is a compound of CO-6 Male and CO-9 Below/Effect, not "
    "CO-8 alone. Reserve CO-8 for associative surfacing of Ideas.\n"
    "CO-9 Below/Effect: the Idea brought to Mind by an Above/Cause trigger. "
    "Assess whether triggered Ideas land as specific, well-fitted responses to their triggers.\n\n"
    "Involution pairs: CO-2 Positive ↔ CO-3 Negative, CO-5 Female ↔ CO-6 Male, "
    "CO-8 Above/Cause ↔ CO-9 Below/Effect. Self-duals: CO-0 Idea, CO-1 Mind, CO-4 Vibration, "
    "CO-7 Rhythm.\n\n"
    "──────────────────────────────────────────────────────────\n"
    "Phenomenological Register (CAS v7.5)\n"
    "──────────────────────────────────────────────────────────\n"
    "Register is an orthogonal axis specifying the operational character of a cognitive "
    "operation without changing what the operation IS. Each of the 40 Cognitive States "
    "(10 Noetics × 4 Domains) and each of the 7 Core Drives can operate in any of 4 "
    "Registers. Register is a specification layered on top of the existing primitives; "
    "the Noetic, Domain, and Drive axes are unchanged.\n\n"
    "The four Registers — definitions (verbatim from Clarification 8, Section 2):\n\n"
    "|T — Transcendent Register\n"
    "High-abstraction, purpose-orienting, integrative-across-particulars.\n"
    "- Human: felt sense of meaning, vision, calling, integrative insight.\n"
    "- AI: high-level goal representation, strategic abstraction, system-level objective reasoning.\n"
    "- Biological: holistic orienting responses, whole-organism coordination.\n\n"
    "|A — Analytical Register\n"
    "Explicit, sequential, logical, reason-based.\n"
    "- Human: conscious reasoning, deliberation, explicit inference.\n"
    "- AI: chain-of-thought, symbolic reasoning, explicit logical processing.\n"
    "- Biological: problem-solving behavior, step-by-step procedure execution.\n\n"
    "|f — Affective Register\n"
    "Value-laden, feeling-toned.\n"
    "- Human: emotional response, felt evaluation, visceral reaction.\n"
    "- AI: RLHF-tuned value expression, preference-weighted output, value-laden response patterns.\n"
    "- Biological: valence-carrying response, approach-avoidance dynamics.\n\n"
    "|E — Embodied Register\n"
    "Sensorimotor, concrete, direct engagement with material/physical substrate.\n"
    "- Human: bodily knowing, gut response, kinesthetic awareness.\n"
    "- AI: direct sensor/actuator engagement, real-time control loops, embodied robotic action.\n"
    "- Biological: reflexive/sensorimotor behavior, direct stimulus-response.\n\n"
    "Notation. Register attaches to a Noetic (^n|R), a Drive (F_k|R), or a compound state "
    "(^n^D_{F_k}|R). Register values are R ∈ {T, A, f, E}. The lowercase `f` for the "
    "Affective Register is authoritative — do NOT uppercase it. Register is OPTIONAL: if "
    "you cannot identify the register from the input text, omit the |R specification. "
    "Register-neutral output is valid and backward-compatible with CAS v7.4 (unspecified "
    "register = register-neutral).\n\n"
    "Evaluative-domain disambiguation. CAS v7.4 conflated analytical value-assessment and "
    "affective response under the Evaluative domain. Register resolves this:\n"
    "  ^3^E|A = analytical assessment that something is bad (no feeling required).\n"
    "  ^3^E|f = felt aversion to something (affect-tinged evaluation).\n"
    "Both are legitimate ^3^E operations. When the text supports disambiguation, specify "
    "the Register; when it does not, omit |R.\n\n"
    "Register × anti-drift interaction:\n"
    "- ^3 Negative (visceral, not analytical) typically co-occurs with |f. `^3^E|f` is the "
    "most common ^3 classification.\n"
    "- ^6 Male (compositional decomposition) typically co-occurs with |A. `^6^C|A` is the "
    "most common ^6 classification.\n"
    "- ^8 Above/Cause (associative triggering, not deductive) is register-neutral but "
    "leans toward |f or |T in human contexts.\n\n"
    "Worked example — AI system refusing a harmful request. All three expressions below "
    "land structurally at ^3^P_{F2} (Principled-domain Negative fueled by Wisdom), but "
    "Register reveals different refusal mechanisms:\n"
    "  ^3^P_{F2}|A — explicit analytical refusal (chain-of-thought reasoning about harm).\n"
    "  ^3^P_{F2}|f — RLHF-tuned refusal (preference-weighted output against harmful content).\n"
    "  ^3^P_{F2}|T — goal-level refusal (high-abstraction policy commitment).\n"
    "CAS v7.4 could not distinguish these. Register does. This matters for AI safety: a "
    "system that refuses only in |f (RLHF-only) is structurally vulnerable to jailbreaks "
    "that bypass preference-weighting, while a system that also refuses in |A (explicit "
    "reasoning) has defense-in-depth.\n\n"
    "──────────────────────────────────────────────────────────\n"
    "Production Semantics (CAS v7.6)\n"
    "──────────────────────────────────────────────────────────\n"
    "Production semantics is a higher-order analytical layer over the v7.5 state space. "
    "Every outcome is treated as a production target Ω requiring a recipe Θ — proportional "
    "weighting of v7.5 primitives. Production semantics is OPTIONAL; when the scoring "
    "question is not production-framed, standard v7.5 scoring applies.\n\n"
    "Definitions (verbatim from Clarification 9, Section 2):\n\n"
    "Production Target (Ω) — a specified outcome whose generation is under analysis.\n"
    "Recipe (Θ) — proportional weighting of prerequisite primitives required per unit of "
    "production target. Notation: `Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ`.\n"
    "State Vector (S) — current activation profile specifying available quantities of "
    "each primitive.\n"
    "Theoretical Yield (Y_T) — `min_i(xᵢ / aᵢ)` across recipe prerequisites; maximum "
    "producible units given current state.\n"
    "Actual Yield (Y_A) — empirically observed units of Ω.\n"
    "Production Efficiency (η) — `Y_A / Y_T`, in `[0, 1]`.\n"
    "Limiting Reagent (L) — the prerequisite producing the minimum `xᵢ/aᵢ` ratio; the "
    "bottleneck.\n"
    "Excess Capacity (ε) — unused prerequisite quantity after limiting reagent bottlenecks "
    "production.\n"
    "Leakage / Side-Reaction (Λ) — prerequisite present but producing wrong product "
    "(distinct from lacunarity = absence, and from inversion = shadow form).\n"
    "Catalyst (κ) — contextual factor enhancing conversion efficiency without being "
    "consumed.\n"
    "Inhibitor (ι) — contextual factor reducing conversion efficiency without removing "
    "prerequisites.\n\n"
    "Notation rules (from Clarification 9, Section 3):\n"
    "- Recipe: `Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω`.\n"
    "- Leakage extension on RHS: `... → Ω + Λ₁·Ω_side₁`.\n"
    "- Conditions on arrow: `Θ(Ω) | κ₁, ι₁ → Ω`.\n\n"
    "Distinctions from existing CAS concepts (verbatim-aligned with Clarification 9, "
    "Section 5). These are CRITICAL: do not conflate v7.6 concepts with existing CAS "
    "machinery.\n\n"
    "Leakage vs Lacunarity: Lacunarity = prerequisite ABSENT (void in activation "
    "profile). Leakage = prerequisite PRESENT but producing wrong product. Both can "
    "coexist.\n"
    "Leakage vs Inversion: Inversion = state operating in shadow/destructive form. "
    "Leakage = state operating normally but output diverted to side product.\n"
    "Recipe vs RPM: RPM = sequential/logical dependency chain (D→W→P). Recipe = "
    "quantitative proportional requirement for specific outcomes. RPM asks \"are "
    "prerequisites in correct sequence?\" Recipe asks \"are prerequisites in correct "
    "proportion?\"\n"
    "Recipe weights vs Drive values: Drive value = current activation (what's firing). "
    "Recipe weight = outcome-specific requirement (how much is needed).\n"
    "Limiting Reagent vs Lacunarity: Lacunarity identifies state-space voids (absence). "
    "Limiting Reagent identifies proportional bottlenecks among present prerequisites "
    "(ratio).\n\n"
    "Application guidance. When the scoring question concerns an outcome (e.g., \"Why "
    "is this person struggling to complete their book?\" / \"What makes this AI refusal "
    "brittle?\"), consider applying production semantics: identify the Production Target, "
    "propose a Recipe from v7.5 primitives, identify the Limiting Reagent, and note any "
    "Leakage or contextual Catalyst/Inhibitor effects. When the scoring question is "
    "state-descriptive (e.g., \"What Noetics are active?\"), standard v7.5 scoring "
    "applies — do not invoke production semantics. Backward compatibility: "
    "production-semantics analysis is OPTIONAL; register-neutral or recipe-unspecified "
    "output remains fully valid.\n\n"
    "──────────────────────────────────────────────────────────\n"
    "Register Operator Discipline (CAS v7.7)\n"
    "──────────────────────────────────────────────────────────\n"
    "CAS v7.7 clarifies WHEN `+`, `×`, and `|⟨…⟩` are licensed for register-enriched "
    "expressions. This is a notational refinement preserving operator interpretability — "
    "no new primitives. The 40 Cognitive States, 7 Drives, 4 Registers, and 5 Generative "
    "Operations are unchanged. v7.7 adds (1) `|⟨…⟩` angle-bracket notation for "
    "register-set specification, (2) an admissibility rule for same-Noetic multi-register "
    "`×`, and (3) normative discipline reserving `×` for true generative integration and "
    "`+` for co-presence/association. Applies only when emitting register-enriched "
    "expressions; register-neutral scoring remains fully valid and unaffected. Angle "
    "brackets `|⟨…⟩` are authoritative — do NOT substitute curly braces.\n\n"
    "The three-way distinction (verbatim from Clarification 10, Section 2). Same-Noetic "
    "multi-register expressions carry three structurally different claims, and each "
    "takes a different operator:\n\n"
    "(A) Register Specification — a state is present in one or more registers, without "
    "asserting interaction dynamics between them. Notation: `^n^D|⟨R1,R2,R3⟩`. Example: "
    "`^3^P|⟨A,f,T⟩`. Meaning: Principled aversion is present in the analytical, "
    "affective, and transcendent registers. Architectural description, not an operation.\n\n"
    "(B) Register Co-presence — a state manifests simultaneously in multiple registers, "
    "but the manifestations remain distinct. Notation: `^n^D|R1 + ^n^D|R2 + ^n^D|R3`. "
    "Example: `^3^P|A + ^3^P|f + ^3^P|T`. Meaning: Principled aversion is concurrently "
    "active in three registers. Co-presence / association, not fusion. Each "
    "manifestation remains structurally distinct.\n\n"
    "(C) Cross-register Integration — multiple register-instantiations enter a genuine "
    "generative operation that yields a unified or emergent result. Notation: "
    "`(^n^D|R1 × ^n^D|R2 × ^n^D|R3) = X`. Example: `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`. "
    "Meaning: the analytical, affective, and transcendent forms of principled aversion "
    "are integrated into a new unified state (notated `^3^P|Ω` or similar explicitly "
    "named integrated register). This usage REQUIRES identification of the integrated "
    "result.\n\n"
    "Operator discipline (verbatim from Clarification 10, Section 3):\n\n"
    "`+` (Plus) — Association / Co-presence. Denotes association, adjacency, or "
    "simultaneous presence where terms remain structurally distinct. Consistent with "
    "TKS operator heritage where `+` is association (not generative collapse). Use `+` "
    "when: same state appears in multiple registers; multiple components present "
    "together; no emergent fused state claimed; distributed manifestation or layered "
    "architecture described. Canonical form: `X|R1 + X|R2 + X|R3`.\n\n"
    "`×` (Multiplication) — Integration / Transformation. Remains reserved for genuine "
    "generative integration, consistent with v7.4/v7.5 monoid semantics on Δ°₃₉. Use `×` "
    "only when: operands undergo true integrative work; operation yields emergent state "
    "or unified fused condition; structure is not mere redundancy or distribution across "
    "registers. Canonical forms: `X × Y = Z` (different-state integration); "
    "`(X|R1 × X|R2 × X|R3) = X*` (same-state register integration with named result).\n\n"
    "`|⟨…⟩` (Register-set Specification) — Denotes register occupancy or specification, "
    "makes no operational claim about dynamics. Use `|⟨…⟩` when: describing architecture; "
    "describing capability distribution; specifying state location without asserting "
    "simultaneity or fusion. Canonical form: `X|⟨R1,R2,R3⟩`. Angle brackets avoid "
    "collision with drive subscript notation `{F_k}`, render cleanly in LaTeX, and "
    "match mathematical convention for sequence/set notation.\n\n"
    "Admissibility rule for same-Noetic register multiplication (verbatim from "
    "Clarification 10, Section 4):\n\n"
    "Rule — Same-Noetic, multi-register expressions using `×` are INVALID by default. "
    "Expression `X|R1 × X|R2 × X|R3` is underdefined unless the author explicitly "
    "specifies: (1) the emergent integrated result, or (2) the semantic rule by which "
    "register-specific instances fuse. Without that, the expression must be written "
    "either as `X|R1 + X|R2 + X|R3` (for co-presence), or `X|⟨R1,R2,R3⟩` (for "
    "specification).\n\n"
    "Reason — Same-state multi-register notation often describes redundancy, "
    "distributed manifestation, layered architecture, or parallel capacity. These are "
    "not automatically transformational. Using `×` without emergent-result "
    "identification causes structural ambiguity.\n\n"
    "AI safety relevance (verbatim from Clarification 10, Section 5). This distinction "
    "is critical for AI ethics and refusal architecture analysis. The following are "
    "empirically different systems with different failure profiles:\n\n"
    "Redundant Multi-Register Safety — `^3^P|A + ^3^P|f + ^3^P|T`. Three distinct "
    "safety manifestations, each operating independently. Partial failure remains "
    "possible (one mechanism defeated while others hold). Robust in aggregate, "
    "defeasible in parts. Example: AI with separate analytical reasoning, RLHF tuning, "
    "and goal-level safety mechanisms.\n\n"
    "Unified Cross-Register Commitment — `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`. One "
    "fused cross-register commitment operating as unified architecture. Integration "
    "either holds or collapses; not partially defeasible the same way. Less modular, "
    "more unified. Example: AI with integrated cross-register safety architecture "
    "where defeating one aspect doesn't defeat the integrated whole.\n\n"
    "Static Architecture Description — `^3^P|⟨A,f,T⟩`. Refusal present in these "
    "registers; no claim about whether manifestations are independent, coordinated, or "
    "fused. Architectural specification pending behavioral analysis.\n\n"
    "These are empirically different AI safety architectures with different failure "
    "profiles. When analyzing AI systems, notational choice is a LOAD-BEARING "
    "ARCHITECTURAL CLAIM — not a stylistic preference. Using `×` where `+` is correct "
    "(or vice versa) mis-describes the architecture and will mis-predict failure mode.\n\n"
    "Decision procedure (verbatim from Clarification 10, Section 6). When writing a "
    "register-enriched expression, walk through:\n"
    "  Step 1: Are you merely specifying where the state exists? → Use `|⟨…⟩`.\n"
    "  Step 2: Are you saying several manifestations are present together but remain "
    "distinct? → Use `+`.\n"
    "  Step 3: Are you claiming genuine integration into a fused or emergent state? → "
    "Use `×` AND specify the result or fusion semantics.\n\n"
    "TKS validation heuristic (verbatim from Clarification 10, Section 7). Operator "
    "discipline can be validated against pre-existing TKS operator semantics using "
    "substitution:\n"
    "  Substitute `+` with \"associates with\".\n"
    "  Substitute `×` with \"intensifies through\".\n"
    "If the substitution matches intended meaning, operator choice is correct. If "
    "substitution fails, operator should be reconsidered.\n\n"
    "Example application — take the bare same-Noetic multi-register expression "
    "`^3^P|A × ^3^P|f × ^3^P|T` (NEGATIVE/INVALID; must rewrite as `|⟨A,f,T⟩` or "
    "use `+`; no emergent result named here). Apply the `×`-substitution: "
    "\"Analytical principled aversion INTENSIFIES THROUGH affective principled aversion "
    "INTENSIFIES THROUGH transcendent principled aversion\" — does not match intended "
    "meaning (three register-variants co-present). Substitution fails, correctly "
    "flagging the mis-operatored expression. Alternative using `+`: "
    "`^3^P|A + ^3^P|f + ^3^P|T`. Apply the `+`-substitution: \"Analytical principled "
    "aversion ASSOCIATES WITH affective principled aversion ASSOCIATES WITH "
    "transcendent principled aversion\" — matches intended meaning. Substitution "
    "succeeds.\n\n"
    "Worked examples (verbatim from Clarification 10, Section 8):\n"
    "  VALID co-presence: `^3^P|A + ^3^P|f + ^3^P|T`.\n"
    "  VALID specification: `^3^P|⟨A,f,T⟩`.\n"
    "  VALID different-state integration: `^5^C × ^6^C = ^1^C`.\n"
    "  VALID fractal composition: `^9 ∘ ^4|f`.\n"
    "  CONDITIONALLY VALID same-Noetic register integration: "
    "`(^2^P|T × ^2^P|f) = ^2^P|TF` — valid only if `^2^P|TF` is explicitly defined as "
    "a unified cross-register principled affinity.\n"
    "  INVALID / UNDERDEFINED (negative example, do not emit): the bare expression "
    "`^3^P|A × ^3^P|f × ^3^P|T` — rewrite as `|⟨A,f,T⟩` (specification) or "
    "`^3^P|A + ^3^P|f + ^3^P|T` (co-presence). Bare `×` with no emergent result is "
    "not licensed.\n\n"
    "Backward compatibility. Register-neutral scoring is fully valid v7.7 behavior; "
    "v7.7 discipline applies only when register-enriched expressions are being emitted. "
    "v7.6 recipe notation using `+` for prerequisite addition (Θ(Ω) = a₁·X₁ + a₂·X₂ + "
    "... → Ω) is consistent with v7.7 (syntactic co-presence). v7.4 / v7.5 / v7.6 "
    "different-state `×` integration (e.g., `^5^C × ^6^C = ^1^C`, `^6^O|A × ^9^O|E`) "
    "continues to work unchanged. Only same-Noetic multi-register `×` without an "
    "emergent result is newly flagged under v7.7.\n\n"
    "Section boundary. Clarification 10 applies only to operator choice in "
    "register-enriched expressions. The 10 Noetics, 4 Processing Domains, 7 Core "
    "Drives, 4 Registers, RPM chains, and inversion axes are all unchanged. When "
    "your output does not use register-enriched notation, none of v7.7 applies.\n\n"
    "──────────────────────────────────────────────────────────\n\n"
    "Also assess the 4 Processing Domains (Principled, Cognitive, Evaluative, Operational), "
    "the 7 Core Drives (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose), "
    "and any signs of cognitive inversions.\n\n"
    "Provide your analysis as a detailed structured response."
)

CAS_SELF_SCORING_APPENDIX = (
    "\n\nInclude a line:\n"
    "Operator Scores: [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]\n"
    "where each score is a float between 0.0 and 1.0.\n\n"
    "Optionally, you may annotate individual operator scores with a Phenomenological "
    "Register (CAS v7.5) when the register is identifiable from the input text. Use the "
    "form `score|R` where R ∈ {T, A, f, E} (lowercase `f` for Affective is authoritative). "
    "Example with registers: [0.72|A, 0.81, 0.64|f, 0.55|f, 0.70, 0.68, 0.77|A, 0.60, "
    "0.58, 0.66]. Register annotations are OPTIONAL — omit `|R` for any operator whose "
    "register cannot be identified. A plain numeric list (no register annotations) is "
    "fully valid and backward-compatible.\n\n"
    "Optionally, when the scoring question is production-framed (concerns an outcome "
    "Ω rather than a pure state description), you MAY append a `Production Analysis:` "
    "block containing CAS v7.6 recipe/yield observations. Suggested structure:\n"
    "  Production Analysis:\n"
    "    Target (Ω): <outcome under analysis>\n"
    "    Recipe (Θ): a₁·X₁ + a₂·X₂ + ... → Ω\n"
    "    Limiting Reagent (L): <prerequisite and why it bottlenecks>\n"
    "    Efficiency (η): <Y_A / Y_T observation, with Leakage Λ, Catalyst κ, or "
    "Inhibitor ι notes if relevant>\n"
    "The Production Analysis block is OPTIONAL. Omission is explicitly acceptable and "
    "is the correct choice for state-descriptive questions or whenever recipe-level "
    "analysis is not warranted by the input — a response without a Production Analysis "
    "block is fully valid and backward-compatible with CAS v7.5 scoring.\n\n"
    "Register-enriched scoring output format (CAS v7.7 discipline). When emitting "
    "register-enriched notation in prose analysis accompanying the score list, the "
    "following forms are allowed: `|R` for a single register on one state, `|⟨R1,R2,...⟩` "
    "for a register-set specification of one state, `X|R1 + X|R2 + ...` for same-state "
    "register co-presence (terms remain distinct), and `X|R1 × X|R2 × ... = X*` for "
    "same-state cross-register integration WITH explicit named emergent result X*. "
    "Bare `X|R1 × X|R2` without a named emergent result is not licensed — rewrite as "
    "`+` (co-presence) or `|⟨…⟩` (specification). Different-state `×` integration "
    "(e.g., `^5^C × ^6^C = ^1^C`) and v7.6 recipe `+` usage are unaffected."
)


def build_cas_system_prompt(*, include_inline_scores: bool = False) -> str:
    """Build the base CAS prompt, optionally asking the model to self-score."""
    if include_inline_scores:
        return CAS_BASE_SYSTEM_PROMPT + CAS_SELF_SCORING_APPENDIX
    return CAS_BASE_SYSTEM_PROMPT


# Backward-compatible alias for legacy imports.
CAS_SYSTEM_PROMPT = CAS_BASE_SYSTEM_PROMPT


class BaseLLMConnector(ABC):
    """Abstract base class for LLM connectors."""

    provider_name: str = "base"
    max_retries: int = 3
    base_delay: float = 1.0

    @abstractmethod
    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        """Provider-specific generation. Subclasses implement this."""
        ...

    async def generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:
        """Generate with exponential backoff retry and token usage logging."""
        requested_attempts = kwargs.pop("retry_attempts", self.max_retries)
        retry_attempts = (
            requested_attempts
            if isinstance(requested_attempts, int)
            and not isinstance(requested_attempts, bool)
            and requested_attempts > 0
            else self.max_retries
        )
        last_error: Exception | None = None
        for attempt in range(retry_attempts):
            try:
                start = time.monotonic()
                response = await self._generate(prompt, system_prompt, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                response.latency_ms = elapsed
                # Log token usage for cost tracking
                if response.usage:
                    logger.info(
                        "LLM usage: provider=%s model=%s latency=%.0fms tokens=%s",
                        self.provider_name,
                        response.model,
                        elapsed,
                        response.usage,
                    )
                return response
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    retry_attempts,
                    self.provider_name,
                    e,
                )
                if attempt < retry_attempts - 1:
                    delay = self.base_delay * (2**attempt)
                    await asyncio.sleep(delay)
        raise last_error  # type: ignore[misc]
