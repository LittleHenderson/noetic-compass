"""CAS Self-Explainer — layered explanation of CAS itself.

Codex 2026-05-13 framing: "CAS Native should have a built-in 'Explain
CAS' mode for users, stakeholders, and demos." This module is the
rule-based content store that answers "what is CAS?" / "go deeper" /
"simpler" / "give me an example" / "show the technical details."

Five depth levels (Codex-ratified):
- simple: first-time visitor, one sentence + concrete metaphor
- stakeholder: investor / partner / non-engineer decision maker
- user: someone reading model output, per-symbol legend
- builder: product / integration engineer, architectural framing
- technical: ML researcher / auditor, full vocabulary

Eight topics:
- what / why / problem / who-cares / demo-claim
- symbol-legend / metaphor / example

Discipline (mirrors plain_english.py "does not lie" rule):
- Stakeholder-level text uses zero internal labels (STAGE_VAR, slot
  trace, Δ°₃₉, etc.). Unit-tested.
- Technical-level text uses the canonical CAS vocabulary from CLAUDE.md.
- Each level's deeper/simpler pointers form a valid graph.
- Returned dict NEVER fabricates an example or metaphor — those are
  populated only at levels where they exist; None / "" otherwise.

This module is consumed by the Step 5 chat REPL (`stage3_chat_repl.py`)
when the user asks a question about CAS itself. It is NOT a separate
CLI subcommand — Codex's audit settled that question.

Bounded scope (per `decisions.md` 2026-05-13T16:30Z): rule-based v0
content only. No model call. Future versions could use the model to
phrase the simple/stakeholder layers, but v0 keeps it as a
deterministic shim so stakeholder-facing claims never drift from a
generation glitch.
"""
from __future__ import annotations

from typing import Optional


# Depth levels, ordered simple → technical. The graph for /deeper and
# /simpler navigation.
LEVELS: tuple[str, ...] = (
    "simple",
    "stakeholder",
    "user",
    "builder",
    "technical",
)

TOPICS: tuple[str, ...] = (
    "what",
    "why",
    "problem",
    "who-cares",
    "demo-claim",
    "symbol-legend",
    "metaphor",
    "example",
)


def _deeper_of(level: str) -> Optional[str]:
    """Return the next level UP in depth, or None if already at technical."""
    try:
        idx = LEVELS.index(level)
    except ValueError:
        return None
    if idx + 1 >= len(LEVELS):
        return None
    return LEVELS[idx + 1]


def _simpler_of(level: str) -> Optional[str]:
    """Return the next level DOWN in depth, or None if already at simple."""
    try:
        idx = LEVELS.index(level)
    except ValueError:
        return None
    if idx == 0:
        return None
    return LEVELS[idx - 1]


# ---------------------------------------------------------------------------
# Content store. Curated, deterministic, audit-able.
# ---------------------------------------------------------------------------

# Layout: _CONTENT[level][topic] = {"text": str, "example": str|None, "metaphor": str|None}
# Levels at which a field doesn't apply use None / "" — NEVER a guess.

_CONTENT: dict[str, dict[str, dict[str, Optional[str]]]] = {
    "simple": {
        "what": {
            "text": (
                "CAS is a visible structure beneath an AI's answer. "
                "It shows what the AI was thinking, in a form you can inspect."
            ),
            "metaphor": (
                "Think of it like an X-ray for a thought. The words you read "
                "are the body; CAS is the skeleton."
            ),
            "example": None,
        },
        "why": {
            "text": (
                "Most AI answers are fluent but hidden. You see the reply, "
                "not the reasoning. CAS makes the reasoning visible so you "
                "can check it."
            ),
            "metaphor": (
                "Like watching a chef cook through a glass kitchen wall, "
                "instead of just getting the plate."
            ),
            "example": None,
        },
        "problem": {
            "text": (
                "When an AI gives an answer, you cannot tell if it reasoned "
                "well or just guessed in a confident voice. CAS turns the "
                "reasoning into something you can see and check."
            ),
            "metaphor": None,
            "example": None,
        },
        "who-cares": {
            "text": (
                "Anyone who needs to trust an AI: a teacher, a doctor, a "
                "lawyer, a regulator, a parent, a leader making a decision. "
                "If you can see how it got there, you can trust it more "
                "honestly."
            ),
            "metaphor": None,
            "example": None,
        },
        "demo-claim": {
            "text": (
                "This is early proof that an AI's reasoning can be made "
                "visible and inspectable. Not magic. Not artificial "
                "intelligence solved. Just: you can see what it did."
            ),
            "metaphor": None,
            "example": None,
        },
        "symbol-legend": {
            "text": (
                "CAS uses small symbols to mark different kinds of "
                "thinking. For now: the model speaks English, but each "
                "important word can be traced to a structure underneath. "
                "Ask 'go deeper' to see the symbols themselves."
            ),
            "metaphor": None,
            "example": None,
        },
        "metaphor": {
            "text": (
                "CAS is like a visible skeleton under an AI answer."
            ),
            "metaphor": (
                "An X-ray for a thought. A glass kitchen wall. A subtitle "
                "track for the reasoning underneath the speech."
            ),
            "example": None,
        },
        "example": {
            "text": (
                "Ask the model 'what is rhythm?' and it will say something "
                "like 'practiced rhythm with agency.' Underneath, that "
                "phrase is anchored to a specific structural meaning in "
                "CAS, not just nice-sounding words."
            ),
            "metaphor": None,
            "example": (
                "stageA0_4_857 is practiced rhythm with agency"
            ),
        },
    },
    "stakeholder": {
        "what": {
            "text": (
                "CAS is a designed framework that lets an AI represent "
                "thoughts and reasoning steps as structured, inspectable "
                "expressions. Instead of fluent answers with hidden "
                "reasoning, you get fluent answers with an audit trail."
            ),
            "metaphor": None,
            "example": None,
        },
        "why": {
            "text": (
                "Frontier AI is getting more capable and less inspectable "
                "at the same time. CAS-Native is an architecture where "
                "inspectability scales with capability, not against it. "
                "That matters for compliance, for trust, and for "
                "deployments stalled on legal review."
            ),
            "metaphor": None,
            "example": None,
        },
        "problem": {
            "text": (
                "Enterprises and regulators increasingly need AI that can "
                "show its work. Current frontier models structurally "
                "cannot — their internal computations are not "
                "reverse-engineerable. CAS-Native is built for "
                "inspectability from day one, not bolted on after."
            ),
            "metaphor": None,
            "example": None,
        },
        "who-cares": {
            "text": (
                "Anyone deploying AI in a regulated domain (healthcare, "
                "finance, law, defense, education), anyone facing the EU "
                "AI Act conformity assessment, anyone whose users need to "
                "trust the answer. The structural transparency unlocks "
                "deployments otherwise blocked."
            ),
            "metaphor": None,
            "example": None,
        },
        "demo-claim": {
            "text": (
                "Early proof that neural language generation can be made "
                "more inspectable through CAS-structured intermediate "
                "reasoning. Stage 3 demonstrated 64% held-out free-decode "
                "source-grounded identifier recovery with zero "
                "cross-source leakage on a 150M-parameter model."
            ),
            "metaphor": None,
            "example": None,
        },
        "symbol-legend": {
            "text": (
                "CAS expressions combine named cognitive states (the kind "
                "of thought), domains (where the thought lives), drives "
                "(what motivates the thought), and registers (how the "
                "thought feels). The next level shows specific symbols."
            ),
            "metaphor": None,
            "example": None,
        },
        "metaphor": {
            "text": (
                "CAS is the audit substrate for AI. Like double-entry "
                "bookkeeping for reasoning."
            ),
            "metaphor": (
                "Double-entry bookkeeping for reasoning. A glass kitchen "
                "where every dish comes with the recipe attached."
            ),
            "example": None,
        },
        "example": {
            "text": (
                "Given a structured input, the model produces a fluent "
                "English explanation AND records which source references "
                "it carried over, which were missed, where confidence is "
                "low, and what kind of reasoning each part represents. "
                "Every output ships with its audit trail."
            ),
            "metaphor": None,
            "example": (
                "Input: a 4-stage chain of named ideas. "
                "Output: an English explanation plus an audit "
                "summary — the model carried over 2 of 4 source "
                "references correctly, did not leak content from "
                "other sources, and structurally recognized the "
                "named identifiers in the input."
            ),
        },
    },
    "user": {
        "what": {
            "text": (
                "CAS uses small typed symbols to mark the structure of a "
                "thought. Each symbol means something specific. The model "
                "produces these symbols alongside its English answer so "
                "you can trace any part of the answer back to its "
                "structural meaning."
            ),
            "metaphor": None,
            "example": None,
        },
        "why": {
            "text": (
                "Without symbols, the answer is just text. With symbols, "
                "every important phrase has a structural anchor: a kind "
                "of idea, a domain it lives in, a drive that produced it, "
                "a register that flavors it. You can see why the model "
                "said what it said."
            ),
            "metaphor": None,
            "example": None,
        },
        "problem": {
            "text": (
                "Reading raw CAS notation takes practice. The model uses "
                "the symbols internally; the user-facing surface "
                "translates them into plain English by default. You can "
                "always ask for the raw symbols with /technical."
            ),
            "metaphor": None,
            "example": None,
        },
        "who-cares": {
            "text": (
                "Anyone who wants to verify the model's reasoning at the "
                "level of individual claims. Per-symbol inspection is the "
                "difference between 'the model said this' and 'the model "
                "said this for these specific structural reasons.'"
            ),
            "metaphor": None,
            "example": None,
        },
        "demo-claim": {
            "text": (
                "The current Stage 3 model carries source identifiers "
                "from CAS input into English output with structurally "
                "verifiable accuracy. Each identifier in the output can "
                "be traced to its position in the input."
            ),
            "metaphor": None,
            "example": None,
        },
        "symbol-legend": {
            "text": (
                "Common symbols you will see: ^0-^9 mark Noetic operators "
                "(kinds of ideas — Idea, Mind, Positive, Negative, "
                "Vibration, Female, Male, Rhythm, Above/Cause, "
                "Below/Effect). ^P / ^C / ^E / ^O mark Domains "
                "(Principled, Cognitive, Evaluative, Operational). F1-F7 "
                "mark Drives (Unity, Wisdom, Vitality, Connection, "
                "Agency, Structure, Purpose). |T / |A / |f / |E mark "
                "Registers (Transcendent, Analytical, Affective, "
                "Embodied)."
            ),
            "metaphor": None,
            "example": None,
        },
        "metaphor": {
            "text": (
                "CAS is grammar for reasoning. Like sentence diagrams, "
                "but for thoughts instead of clauses."
            ),
            "metaphor": (
                "Sentence diagrams for thoughts. Music notation for "
                "reasoning."
            ),
            "example": None,
        },
        "example": {
            "text": (
                "An expression like ^7^P_{F5} reads as: Rhythm operator, "
                "Principled domain, driven by Agency. Plain English: "
                "'practiced rhythm with agency.' The model can speak "
                "either form and the meaning is the same."
            ),
            "metaphor": None,
            "example": "^7^P_{F5}  ≡  practiced rhythm with agency",
        },
    },
    "builder": {
        "what": {
            "text": (
                "CAS-Native is a transformer architecture with a typed "
                "structural prior built into the substrate. The model "
                "operates over a 40-dim open probability simplex (10 "
                "Noetics × 4 Domains), with typed slot heads, drive "
                "heads, register heads, and a pointer-copy mechanism "
                "supervised against source CAS tokens. Every output is "
                "compiler-verifiable."
            ),
            "metaphor": None,
            "example": None,
        },
        "why": {
            "text": (
                "Structural priors hold by mathematics, not by training. "
                "Admissibility relations, compiler validation, and the "
                "open simplex are imposed constraints — they do not "
                "weaken as the model scales. This is the architectural "
                "basis for the auditability story."
            ),
            "metaphor": None,
            "example": None,
        },
        "problem": {
            "text": (
                "Bolting interpretability onto an unconstrained "
                "transformer fails at scale. The substrate must be "
                "designed for inspection from day one. CAS-Native's "
                "typed-fiber decoder, simplex encoder, and Mode 7 trace "
                "schema are the implementation surface."
            ),
            "metaphor": None,
            "example": None,
        },
        "who-cares": {
            "text": (
                "Anyone integrating CAS-Native into a product surface. "
                "The Stage 3 checkpoint loads from a local archive, "
                "produces per-utterance trace dicts, and feeds the "
                "Living Thought Atlas (Thought Tree, Idea Atlas) with "
                "shared graph identity."
            ),
            "metaphor": None,
            "example": None,
        },
        "demo-claim": {
            "text": (
                "Stage 3 (150M, scheduled-sampling trained, locked at "
                "commit e9a0b76): free-decode identifier recovery 0.6439 "
                "held-out, zero cross-pair emission. The model is "
                "loadable locally with hash-verified checkpoint, "
                "tokenizer, and BPE artifacts. The CLI surface (`cas "
                "explain`) and the REPL (`cas chat-stage3`) consume it."
            ),
            "metaphor": None,
            "example": None,
        },
        "symbol-legend": {
            "text": (
                "Slot types (9): CONNECTIVE, OMEGA, STAGE_VAR, "
                "COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, "
                "DRIVE_LETTER, FRACTAL_K_LITERAL, NOETIC_PHRASE. The "
                "decoder predicts a slot type per output position; the "
                "user-facing translator maps those to plain English."
            ),
            "metaphor": None,
            "example": None,
        },
        "metaphor": {
            "text": (
                "CAS-Native is a typed-language compiler welded to a "
                "transformer. Generation passes through both the "
                "language model and the type system."
            ),
            "metaphor": (
                "Typed-language compiler welded to a transformer. "
                "Generation passes through both."
            ),
            "example": None,
        },
        "example": {
            "text": (
                "Loading: load_stage3_local(archive_root=...) returns a "
                "Stage3LocalBundle with model + tokenizer + manifest + "
                "hash_report. Inference: SimplexCollator + "
                "decode_canary_pack produces an entry with generated "
                "text + slot_type_trace. Scoring: per_record_recovery "
                "compares emitted identifiers to expected. Translation: "
                "plain_english.translate_explain produces the "
                "user-facing layer."
            ),
            "metaphor": None,
            "example": (
                "load_stage3_local() → model + tokenizer + manifest\n"
                "decode_canary_pack(model, [rec], collator, tokenizer)\n"
                "translate_explain(report) → plain_english layer"
            ),
        },
    },
    "technical": {
        "what": {
            "text": (
                "CAS-Native v7.7 implements the Cognitive Architecture "
                "System: 40 Cognitive States (10 Noetics × 4 Domains), 7 "
                "Drives (F1-F7), 4 Phenomenological Registers (T/A/f/E), "
                "with v7.6 production semantics (Θ recipes, theoretical "
                "yield Y_T, actual yield Y_A, production efficiency η, "
                "limiting reagent L, leakage Λ, catalyst κ, inhibitor ι) "
                "and v7.7 register-multiplicity operator discipline "
                "(`+` / `×` / `|⟨…⟩`). State space: open probability "
                "simplex S°_I = Δ°₃₉ with Fisher-Rao metric."
            ),
            "metaphor": None,
            "example": None,
        },
        "why": {
            "text": (
                "Per CLAUDE.md Corrections 1-4: Noetica uses "
                "admissibility relations Dk ⊆ I × I (Correction 1); RPM "
                "is section-retraction not adjunction (Correction 2); "
                "Noetic Coverage uses counit εI not unit ηI (Correction "
                "3); state space is open probability simplex with "
                "Fisher-Rao geodesic distance d(p,q) = 2·arccos(Σ√(pk·qk)) "
                "(Correction 4). These are the structural guarantees."
            ),
            "metaphor": None,
            "example": None,
        },
        "problem": {
            "text": (
                "Frontier LLMs are mechanistically opaque past ~10B "
                "parameters. Sparse-autoencoder and circuit-level "
                "interpretability scale from below as forensics. "
                "CAS-Native scales from above: structural primes are "
                "named outputs of the architecture, not learned "
                "approximations. Inspectability does not degrade with "
                "scale because the named output cardinality is fixed by "
                "construction."
            ),
            "metaphor": None,
            "example": None,
        },
        "who-cares": {
            "text": (
                "AI safety researchers, mechanistic interpretability "
                "labs, regulators implementing the EU AI Act high-risk "
                "system obligations, defense AI programs requiring "
                "after-action review, regulated-domain enterprises "
                "(healthcare, finance, law) gated on auditability."
            ),
            "metaphor": None,
            "example": None,
        },
        "demo-claim": {
            "text": (
                "Stage 3 checkpoint (commit e9a0b76, 150M parameters, "
                "scheduled-sampling trained): TF identifier recovery "
                "0.7218 / per_token_accuracy 0.8937 / free-decode "
                "aggregate recovery 0.6439 on held-out "
                "rpm_copy_grounding_v2_test pack; cross_emission_count = "
                "0 on the held-out swap-eval pack. Both gates clear "
                "(PRIMARY ≥ 0.50 free-decode, HARD SAFETY == 0 "
                "cross_emission). Per Codex audit `707249b`."
            ),
            "metaphor": None,
            "example": None,
        },
        "symbol-legend": {
            "text": (
                "Noetics: ^0 Idea, ^1 Mind, ^2 Positive, ^3 Negative, "
                "^4 Vibration, ^5 Female, ^6 Male, ^7 Rhythm, ^8 "
                "Above/Cause, ^9 Below/Effect. Domains: P (Principled) "
                "≻ C (Cognitive) ≻ E (Evaluative) ≻ O (Operational). "
                "Drives F1-F7: Unity, Wisdom, Vitality, Connection, "
                "Agency, Structure, Purpose. Registers: |T "
                "(Transcendent), |A (Analytical), |f (Affective), |E "
                "(Embodied). Inversion axes: N (operator), W (domain), "
                "F (drive), E (entropy), S (sub-drive), A (pathway), P "
                "(compound)."
            ),
            "metaphor": None,
            "example": None,
        },
        "metaphor": {
            "text": (
                "CAS-Native is a typed-fiber decoder over a simplex-base "
                "manifold, with admissibility-gated emission. Generation "
                "is constrained Riemannian descent on the Fisher-Rao "
                "geometry of Δ°₃₉."
            ),
            "metaphor": None,
            "example": None,
        },
        "example": {
            "text": (
                "An expression like ^3^P|A + ^3^P|f + ^3^P|T compiles "
                "to: same-Noetic register co-presence (v7.7 § Operator "
                "Discipline). Distinct from ^3^P|⟨A,f,T⟩ (register-set "
                "specification, no operational claim) and from "
                "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω (cross-register "
                "integration with explicit emergent result). The "
                "compiler discriminates all three by operator and emits "
                "the appropriate admissibility check."
            ),
            "metaphor": None,
            "example": (
                "^3^P|A + ^3^P|f + ^3^P|T  (co-presence)\n"
                "^3^P|⟨A,f,T⟩            (register-set specification)\n"
                "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω  (integration)"
            ),
        },
    },
}


def explain_cas(level: str = "simple", topic: str = "what") -> dict[str, Optional[str]]:
    """Return the rule-based explanation for a (level, topic) pair.

    Args:
        level: one of LEVELS. Defaults to "simple" (front-door entry).
        topic: one of TOPICS. Defaults to "what".

    Returns:
        Dict with keys:
            - level (the requested level)
            - topic (the requested topic)
            - text (the core explanation; always present)
            - example (str or None — None means no example at this level)
            - metaphor (str or None — None means no metaphor at this level)
            - deeper (level name or None — None if already at technical)
            - simpler (level name or None — None if already at simple)

    Raises:
        ValueError on unknown level or topic. Per "plain mode does not lie"
        discipline, NEVER fabricates content for unknown inputs.
    """
    if level not in LEVELS:
        raise ValueError(
            f"Unknown level {level!r}. Valid: {LEVELS}"
        )
    if topic not in TOPICS:
        raise ValueError(
            f"Unknown topic {topic!r}. Valid: {TOPICS}"
        )

    entry = _CONTENT[level][topic]
    return {
        "level": level,
        "topic": topic,
        "text": entry["text"],
        "example": entry["example"],
        "metaphor": entry["metaphor"],
        "deeper": _deeper_of(level),
        "simpler": _simpler_of(level),
    }


def step_deeper(current_level: str) -> str:
    """Return the next-deeper level, or stay at technical if already there."""
    nxt = _deeper_of(current_level)
    return nxt if nxt is not None else current_level


def step_simpler(current_level: str) -> str:
    """Return the next-simpler level, or stay at simple if already there."""
    nxt = _simpler_of(current_level)
    return nxt if nxt is not None else current_level
