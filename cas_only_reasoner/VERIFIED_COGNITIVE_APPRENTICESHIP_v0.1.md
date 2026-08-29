# Verified Cognitive Apprenticeship v0.1

**Source:** owner directive, 2026-08-28.
**Status:** ADOPTED. The teacher-model doctrine for the CNCM's
language acquisition. Governing principle:

    Foreign proposals are permitted.
    Foreign commitments are prohibited.

The larger model is a TEMPORARY MASTER TEACHER supplying candidate
lessons to a student whose acceptance law is stricter than the
teacher. This is not distillation: the machine learns from a more
capable model, but only through lessons that survive its own
acceptance law. The teacher helps raise the brain, then steps out of
the room.

## The compositional refinement (no grain-of-sand sandbox)

English is NOT learned as thousands of unrelated sentence templates.
The CNCM learns a small number of reusable CONSTRUCTIONS that compose:
word meanings, morphological rules, phrase structures, semantic
roles, sentence constructions, reference rules, discourse rules,
pragmatic conventions. One passive construction
(`NP_patient + passive aux + VERB_participle + by + NP_agent` →
`event(predicate, agent, patient, voice=passive)`) handles unseen
nouns and verbs forever. The machine is not learning sentences; it is
learning how English constructs meaning.

## The CCB-L1 subboard family

    CCB-L1
    ├── LEX      lexicon and word-sense learning   (EXISTS: acquirer)
    ├── MORPH    inflection, derivation, tense     (v0.1: morph table)
    ├── GRAM     learnable grammar constructions   (BUILT this round)
    ├── ROLE     agent/patient/recipient/...       (in GRAM frames v0.1)
    ├── REF      pronouns, anaphora                (open; discourse.py seed)
    ├── DISC     topic, turns, context             (open; CCB-D1 later)
    └── REALIZE  CAS-Sem -> grammatical English    (open)

## The LanguageLessonPacket

Typed lessons only - never prose. Fields: lesson_id, lesson_type,
teacher_model + teacher_revision (identity receipts), prerequisite
rules, surface_pattern, semantic_transformation, positive_examples,
minimal_pairs, counterexamples, ambiguity_cases, exceptions,
expected_CAS_Sem, claimed_scope, teacher_confidence (INFORMATIONAL -
no promotion authority), provenance.

## The grammar acceptance law (the promotion ladder)

    PROPOSED -> SCHEMA_VALID -> COMPILED -> POSITIVE_EXAMPLES_PASS
    -> CONTRAST_TESTS_PASS -> HELD_OUT_GENERALIZATION_PASS
    -> PRIOR_GRAMMAR_REGRESSION_PASS -> AMBIGUITY_BEHAVIOR_PASS
    -> PROMOTED_PROVISIONALLY -> DELAYED_RETENTION_PASS
    -> PROMOTED_DURABLY

A rule promotes only if: schema valid AND every positive example
produces the intended meaning AND role-reversed/negated contrasts
remain DIFFERENT AND unseen examples generalize AND previously
mastered constructions do not regress AND ambiguous inputs produce
alternatives or clarification (never invented certainty) AND
deterministic replay reproduces the result AND provenance is
complete. States: ACTIVE / QUARANTINED / SUPERSEDED / ROLLED_BACK.

## Minimal pairs are language fault-injection

Passive: SemGraph("the cat chased the dog") == SemGraph("the dog was
chased by the cat") AND != SemGraph("the dog chased the cat").
Negation: polarity positive vs negative, never collapsed.
Quantification: every/some/no must not collapse into one proposition.

## The teacher stays out of its own examination room

Separate evidence channels: the teacher proposes the lesson; the
CAS-SDG development generator expands examples and contrasts; a
PROTECTED fixture generator produces unseen cases from separate
templates and seeds; the frozen verifier evaluates semantic
correctness; CAS-RRK controls promotion and rollback. High-impact
rules need a second teacher source or a human-authored semantic
anchor - otherwise the student confuses the teacher's consistency
with correctness.

## Three kinds of language learning, kept distinct

1. LEXICAL (what does this word mean) - exists.
2. GRAMMATICAL (how does structure change meaning) - built this
   round.
3. PRAGMATIC/DIALOGUE (intent, reference, context) - after core
   grammar; partly CCB-D1. Plus surface REALIZATION as a fourth
   layer.

## The three model modes

- TEACHER MODE (offline/controlled): generates lessons, examples,
  curriculum candidates - everything passes the acceptance law.
- RUNTIME CONSULTANT MODE: only on typed native failure
  (UNKNOWN_CONSTRUCTION / AMBIGUOUS_PARSE / UNKNOWN_LEXEME /
  INSUFFICIENT_COVERAGE); CAS still grounds, compares, commits.
- SHADOW MODE: native handles the turn; the teacher separately
  proposes; outputs compared WITHOUT teacher influence on commitment
  - the measurement of whether the student actually learned.

## Teacher retirement (the endgame)

Metrics: native coverage rate, teacher intervention rate, semantic
fidelity, unknown-word honesty, compositional generalization, grammar
regression rate, native latency, rule provenance coverage. Proposed
retirement profile per domain: native coverage >= 95%, semantic
fidelity >= 98%, role-reversal discrimination >= 99%, unknown-term
honesty >= 98%, protected grammar regression 0 critical, teacher
intervention <= 5%, unauthorized teacher commits 0. Then: organ ->
consultant -> teacher -> occasional specialist. The English already
learned STAYS in the CNCM as inspectable structures (LexiconRecord,
GrammarConstruction, SemanticFrame, RoleBindingRule, ReferenceRule,
DialogueProcedure, ExceptionRecord, TeachingEpisode,
RegressionReceipt, VersionLineage) - a living, testable grammar
codebase, which weights can never give.

## CAS-Ohm's role

Never decides whether a rule is correct (the verifier does). It
measures WHERE learning is blocked and WHETHER teaching lowered the
capability resistance: before - high R_cap(role_binding), low I,
wrong roles; after - R_cap down, I active, effect correct. RPM
selects the first weak language prerequisite; CAS-Ohm records whether
the lesson actually repaired the path (learning_repair_record,
already implemented).

## The teacher cannot supply all intelligence

Language learning != world knowledge. Science, history, culture,
people, rare facts come from documents, verified databases, books,
tool results, human teaching, episodic experience, CAS-GEM. A native
board may understand a question perfectly while lacking the answer:
that yields LANGUAGE_UNDERSTOOD + KNOWLEDGE_MISSING - never a blamed
grammar, never a fabricated answer.

## The construction sequence

    L1  learnable grammar kernel        BUILT this round (CCB-L1 GRAM)
    L2  teacher lesson protocol         schema built; live teacher
                                        generation queued
    L3  CAS-SDG curriculum              queued (existing factory)
    L4  shadow apprenticeship           compare harness built
    L5  native-first runtime            wired (router tries L1 core,
                                        then GRAM store, then cortex)
    L6  teacher-dependence decay        coverage counters wired
