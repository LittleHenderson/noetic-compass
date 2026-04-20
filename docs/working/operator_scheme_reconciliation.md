# Operator Naming Scheme Reconciliation — Audit Findings and Proposed Resolution

**Prepared:** 2026-04-19, Phase 2 Session 1 (standing down on reformation work pending authority decision).
**Purpose:** Catalog every place in the repository where English-language names are attached to the 10 Cognitive Operators (CO-0 through CO-9), identify inconsistencies, and propose a path forward.
**Scope:** Audit only. No edits to FULL_MANUSCRIPT.md, CLAUDE.md, or docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md were made. Reformation work on the manuscript is held pending Wakil's resolution of the authority question below.

---

## Executive summary

The repository contains **three parallel, inconsistent operator-naming schemes.** They are semantically different — not cosmetic variations of one scheme. Any attempt to reform one scheme toward another constitutes a framework-level renaming, not a language reformation.

**Scheme A (Book scheme)** lives only in `book/manuscript/FULL_MANUSCRIPT.md`.

**Scheme B (Clarifications/Compiler scheme)** lives in the Noetic Compass assessment infrastructure: the CAS notation compiler, parts of the Rust engine, `CLAUDE.md` (as of tonight's reformation commit `7802da7`), and `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (created tonight in commit `b8bbf74`).

**Scheme C (Dashboard/Interpreter scheme)** lives in the user-facing Noetic Compass platform: the React dashboard, the Python pipeline interpreter, and the LLM scoring prompt.

The patent filings, peer-review paper, Rust core engine, and CAS language specification are **scheme-agnostic** — they reference operators by index (CO-0 through CO-9) without committing to any specific English naming convention. This gives Wakil full flexibility on which scheme becomes canonical; no IP or academic-submission constraint locks in any of the three.

---

## Section A — What each authoritative source actually says

### A.1 The CAS v7.4 Corrected Edition book manuscript (Scheme A)

Source of truth: `book/manuscript/FULL_MANUSCRIPT.md`, Chapter 2 (lines 358–615) and Appendix D (lines 6127–6303).

| Index | Book name | Citation |
|-------|-----------|----------|
| CO-0 | **Identity** | FULL_MANUSCRIPT.md L381 ("CO-0: Identity (The Core Axiom)"); L6193 (Appendix D: "CO-0 Identity. The self-dual operator…") |
| CO-1 | **Differentiation** | FULL_MANUSCRIPT.md L402 ("CO-1: Differentiation (The Architect)"); L6195 ("CO-1 Differentiation. The operator that separates one category or entity from another. Self-dual.") |
| CO-2 | **Abstractification** | FULL_MANUSCRIPT.md L412 ("CO-2: Abstractification (The Theorist)"); L6197 ("CO-2 Abstractification. The operator that extracts general patterns from specifics.") |
| CO-3 | **Concretization** | FULL_MANUSCRIPT.md L421 ("CO-3: Concretization (The Builder)"); L6199 ("CO-3 Concretization. The operator that instantiates general patterns into specific realizations. Involution of CO-2.") |
| CO-4 | **Integration** | FULL_MANUSCRIPT.md L447 ("CO-4: Integration (The Synthesizer)"); L6201 ("CO-4 Integration. The self-dual operator that merges multiple states into a coherent whole.") |
| CO-5 | **Empathetic Alignment** (short form: **Empathy**) | FULL_MANUSCRIPT.md L456 ("CO-5: Empathetic Alignment (The Harmonizer)"); L6203 ("CO-5 Empathy. The operator that resonates with another's state. Involution of CO-6.") |
| CO-6 | **Critical Evaluation** (short form: **Critique**) | FULL_MANUSCRIPT.md L465 ("CO-6: Critical Evaluation (The Judge)"); L6205 ("CO-6 Critique. The operator that judges a state against a standard. Involution of CO-5.") |
| CO-7 | **Momentum** | FULL_MANUSCRIPT.md L495 ("CO-7: Momentum (The Engine)"); L6207 ("CO-7 Momentum. The self-dual operator that sustains effort across time.") |
| CO-8 | **Expansion** | FULL_MANUSCRIPT.md L504 ("CO-8: Expansion (The Explorer)"); L6209 ("CO-8 Expansion. The operator that widens scope, generates alternatives, or spreads outward. Involution of CO-9.") |
| CO-9 | **Contraction** | FULL_MANUSCRIPT.md L513 ("CO-9: Contraction (The Sniper)"); L6211 ("CO-9 Contraction. The operator that narrows scope to a single focus. Involution of CO-8.") |

### A.2 The Foundational Clarifications / Compiler scheme (Scheme B)

Sources:
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (authored tonight, commit `b8bbf74`)
- `CLAUDE.md` as of tonight's reformation commit `7802da7` (pre-reformation CLAUDE.md at commit `37e04ea` listed no English names; named scheme was introduced tonight)
- `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`, `OPERATOR_NAMES` list at lines 32–43
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/scoring/lacunarity.rs` lines 166–168
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/rpm/recursive.rs` docstrings at lines 6–9

| Index | Clarifications/Compiler name | Cross-source variance |
|-------|------------------------------|----------------------|
| CO-0 | **Generative Potential** | Consistent |
| CO-1 | **Directed Attention** | Consistent |
| CO-2 | **Attraction** | Compiler adds "/ Affinity" |
| CO-3 | **Critical Evaluation** | Compiler adds "/ Aversion" |
| CO-4 | **Encoding Intensity** | Consistent |
| CO-5 | **Receptive Integration** | Consistent |
| CO-6 | **Projective Assertion** | Consistent |
| CO-7 | **Pattern Entrainment** | Consistent |
| CO-8 | **Causal Reasoning** | Compiler uses "Causal Initiation" |
| CO-9 | **Consequential Grounding** | Consistent |

Note: Scheme B was **introduced into CLAUDE.md tonight** as part of the reformation pass. Prior to tonight's commits `b8bbf74` and `7802da7`, CLAUDE.md listed only `CO-0 through CO-9` without English names. So Scheme B's formal textual statement in the repo is 24 hours old. Its presence in the compiler and Rust engine predates tonight, however.

### A.3 The Dashboard/Interpreter scheme (Scheme C)

Sources:
- `noetic-compass-scaffold/noetic-compass/dashboard/src/lib/constants.ts`, `OPERATOR_LABELS` array at lines 3–14
- `noetic-compass-scaffold/noetic-compass/api/pipeline/interpreter.py`, `OPERATOR_NAMES` list at lines 17–21
- `noetic-compass-scaffold/noetic-compass/api/llm_connectors/base.py`, LLM scoring prompt at lines 28–37

| Index | Dashboard/Interpreter name |
|-------|----------------------------|
| CO-0 | **Identity** |
| CO-1 | **Reflection** |
| CO-2 | **Abstraction** |
| CO-3 | **Concretization** |
| CO-4 | **Integration** |
| CO-5 | **Differentiation** |
| CO-6 | **Unification** |
| CO-7 | **Transformation** |
| CO-8 | **Expansion** |
| CO-9 | **Contraction** |

### A.4 Scheme-agnostic authoritative sources

The following sources **do not take a position** — they reference operators only by numeric index or category-theoretic label:

- **Provisional patent filings** (`ip/noetic_compass_provisional_package/NOETIC_COMPASS_SPECIFICATION_FOR_FILING.md` and the CAS-Native package). Both use the generic term "operator" throughout; neither commits to English names. This is a deliberate drafting choice that preserves scheme flexibility.
- **Peer-review paper** (`peer_review/journal_submission/main.tex`, 543 lines). Operators appear only as category-theoretic indices; no English names are used.
- **Rust core engine operator type** (`cas-engine/src/ontology/operators.rs`). The `CognitiveOperator` enum has variants `CO0`…`CO9` only — no English names in the core type definition.
- **CAS Language Specification** (`noetic-compass-scaffold/noetic-compass/docs/CAS_LANGUAGE_SPEC.md`). Uses indexed form only: `CO-2^C_{F2}`.

---

## Section B — Internal inconsistencies

### B.1 Cross-scheme label collisions at different indices

Several labels appear in more than one scheme, but assigned to **different operator indices** in each. These are the most dangerous collisions because they can silently corrupt cross-document references.

| Label | Scheme A position | Scheme B position | Scheme C position |
|-------|-------------------|-------------------|-------------------|
| **Identity** | CO-0 | — (uses "Generative Potential") | CO-0 |
| **Differentiation** | **CO-1** | — | **CO-5** |
| **Critical Evaluation** | **CO-6** | **CO-3** | — (uses "Unification") |
| **Integration** | CO-4 | — (uses "Encoding Intensity") | CO-4 |

The `Differentiation` collision is the most serious: the book names CO-1 "Differentiation," but the dashboard names CO-5 "Differentiation." A user reading the book and then looking at the dashboard's operator radar chart would see "Differentiation" plotted at the CO-5 position and reasonably conclude the book is talking about the same operator at a different index — when in fact the concepts are different.

The `Critical Evaluation` collision is also serious: both the book (at CO-6) and the Clarifications (at CO-3) use this label, but they mean different operators at different indices.

### B.2 Mixed-scheme usage already present in FULL_MANUSCRIPT.md

The book manuscript is **not internally consistent** with its own Scheme A. Grep shows at least two Scheme-B intrusions deep in the text:

- **Line 1716:** *"CO-3 × CO-8 = CO-1: Critical Evaluation composed with Causal Reasoning produces Directed Attention."* This sentence uses Scheme B names: CO-3 = "Critical Evaluation" (Scheme B — in Scheme A, CO-3 is "Concretization"), CO-8 = "Causal Reasoning" (Scheme B — in Scheme A, CO-8 is "Expansion"), CO-1 = "Directed Attention" (Scheme B — in Scheme A, CO-1 is "Differentiation"). Inside a single CAS equation, an author consistent with Scheme A throughout the rest of Chapter 2 has reached for Scheme B names. Either unintentional drift or deliberate cross-reference; either way, the book's own operator vocabulary is not uniform.
- **Line 6189 (Appendix D):** *"Critical Evaluation. The process carried out by the CO-6 Critique operator in any domain…"* This entry uses the Scheme A assignment (CO-6 = Critique, aka Critical Evaluation) but the entry name uses the Scheme B short form ("Critical Evaluation"). The label collides with the Scheme B term at CO-3.

### B.3 Scheme-B variance inside Scheme B

Even within what I'm calling "Scheme B," the compiler and the Foundational Clarifications do not agree on two labels:

- **CO-3:** Clarifications say "Critical Evaluation"; compiler says "Aversion / Critical Evaluation" (with "Aversion" listed first as the primary).
- **CO-8:** Clarifications say "Causal Reasoning"; compiler says "Causal Initiation."

These are close enough that they were probably not an intentional divergence — most likely drift from one edit pass to another.

### B.4 No scheme has yet been applied to the patent filings or peer-review paper

Both the patent and the paper treat operators as unlabeled indices. A future decision on canonical naming can flow cleanly into those documents without creating retroactive conflicts — but it also means the patent's claim-scope language does not lock in any particular naming.

---

## Section C — Recommended path forward

### C.1 Decision required from Wakil

The reformation work on FULL_MANUSCRIPT.md cannot proceed until one question is resolved:

> **Which naming scheme is canonical for the Cognitive Operators?**

Three paths, with honest assessment of the effort and downstream work each entails:

#### Path 1 — Book scheme (A) is canonical

Adopt the book's names (Identity, Differentiation, Abstractification, Concretization, Integration, Empathetic Alignment, Critical Evaluation, Momentum, Expansion, Contraction) as authoritative.

**What must change:**
- `CLAUDE.md` — revert tonight's Scheme B annotations in the Ontology block; replace with Scheme A names.
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — rewrite §1 operator-by-operator guidance using Scheme A names. This is a substantial rewrite because the structural-semantic clarifications were written around Scheme B's specific concepts (e.g., "Attraction" as "geometric pull between substrate and object"). Scheme A's "Abstractification" has a different structural semantic ("extraction of a general pattern") that the Clarifications would need to articulate fresh.
- `api/notation/compiler.py` — rename `OPERATOR_NAMES` entries to Scheme A.
- `api/pipeline/interpreter.py`, `api/llm_connectors/base.py`, `dashboard/src/lib/constants.ts` — rename to Scheme A. These are currently using Scheme C, so this path requires changing them too (Scheme C would also be deprecated).
- `cas-engine/src/scoring/lacunarity.rs` line 166, `cas-engine/src/rpm/recursive.rs` lines 6–9 — rename to Scheme A.
- Technical Feature Overview revision deliverable (`docs/working/technical_feature_overview_revised.md`) — update Revision 1 which assumed Scheme B (CO-3 = "Critical Evaluation"); revise to match Scheme A (CO-3 = "Concretization", so the Attraction/Aversion→Critical Evaluation change becomes Abstraction/Concretization which may or may not already be correct).
- FULL_MANUSCRIPT.md line 1716 (and similar Scheme-B intrusions) — revise to Scheme A names.

Pros: minimal change to the book, which is the primary external deliverable going to Atticus/KDP. The book stays stable.
Cons: substantial codebase rewrites. The Foundational Clarifications document as currently written loses its semantic content and needs a full rewrite. Tonight's Phase 1 reformation commits for CLAUDE.md and the Technical Feature Overview revisions are partially invalidated.

#### Path 2 — Clarifications/Compiler scheme (B) is canonical

Adopt Scheme B's names as authoritative.

**What must change:**
- `FULL_MANUSCRIPT.md` Chapter 2 + Appendix D + every in-book reference to operators by name → renamed to Scheme B. Rough impact: ~258-line Chapter 2 requires operator-name revision throughout; Appendix D requires every `CO-n` entry updated; Chapter 6 (Inversions) likely refers to operators by name; Chapters 7–11 (The Language) discuss operator compositions by name; Chapters 12–17 use operators in human-application contexts; Chapter 2's supporting illustrations (The Architect / The Theorist / The Builder / The Synthesizer / The Harmonizer / The Judge / The Engine / The Explorer / The Sniper) all need to be rethought because they attach to Scheme A concepts.
- `api/pipeline/interpreter.py`, `api/llm_connectors/base.py`, `dashboard/src/lib/constants.ts` — rename from Scheme C to Scheme B.
- `dashboard/src/lib/interpretations.ts` and related user-facing copy — rename.
- Minor cleanup: unify CO-3 and CO-8 naming across the Clarifications and the compiler (either remove "Aversion" from the compiler or add it to the Clarifications as an alternate; either make CO-8 uniformly "Causal Reasoning" or uniformly "Causal Initiation").

Pros: keeps the Foundational Clarifications document intact as written. Aligns the platform code with the Clarifications. Scheme B's structural framing (geometric pull, geometric push, compositional ontology) fits the book's eventual pedagogical need for structural-not-emotional teaching better than Scheme A's more Aristotelian action-verbs naming.
Cons: **massive book rewrite.** Chapter 2 + Chapter 6 + Appendix D + every other operator reference across 124,178 words. Scheme A's pedagogical illustrations ("The Architect," "The Builder," etc.) would all need to be replaced, since they attach to concepts Scheme B doesn't have. This is a multi-week project.

#### Path 3 — Scheme C (Dashboard/Interpreter) is canonical

Adopt Dashboard names as authoritative.

This path has the weakest claim. Scheme C appears to be a naming choice made for user-facing labels that then propagated to the interpreter prompt and LLM scoring prompt, but was never codified in a specification document. It is not what the book uses. It is not what the Foundational Clarifications document uses. It is not what the Noetic Compass compiler uses. Adopting it would require rewriting all other sources.

**Not recommended.** Treat Scheme C as an early UI implementation detail that drifted from the book and needs to be reconciled to whichever of Paths 1 or 2 is chosen.

#### Path 4 — Hybrid / both-scheme documentation

Keep Schemes A and B in parallel with a formal mapping document. The book uses Scheme A for pedagogical continuity with the CAS v7.4 Corrected Edition; the Noetic Compass platform uses Scheme B for technical precision in assessment; a canonical mapping document (potentially `docs/CAS_OPERATOR_NAMING_TABLE.md`) lists both sets of names side by side with the explicit mapping between them.

This requires the two schemes to **describe the same operators** (same structural semantics, different labels). Based on the evidence in Section A, that is **not currently true** — Scheme A's "Abstractification" (extraction of patterns) and Scheme B's "Attraction" (geometric pull between Mind and Idea) are not the same operation. Adopting Path 4 would require editorial work to reconcile the structural semantics so that the same mathematical operator has a Scheme-A name and a Scheme-B name that mean structurally equivalent things. Possible but nontrivial.

Pros: preserves the book exactly as written while letting the Noetic Compass platform use its own terminology. Reduces immediate rewrite pressure on both sides.
Cons: semantic reconciliation work required first. Two parallel vocabularies is a cognitive load on every reader who encounters both. Risk of future drift if the two schemes evolve independently.

### C.2 My recommendation

**Path 4 (hybrid) with a formal reconciliation document** is the lowest-risk choice for the immediate term. The book ships as-is (Scheme A) and is what goes to KDP. The platform ships as-is (Scheme B in compiler/Clarifications, Scheme C to be aligned with Scheme B in dashboard/interpreter). A new document `docs/CAS_OPERATOR_NAMING_TABLE.md` is authored that:
1. States explicitly that both schemes exist.
2. Maps them side by side.
3. Documents the structural equivalence (or documented non-equivalence) between each corresponding pair.
4. Names each scheme's scope (book-scheme for teaching, platform-scheme for assessment).

This is subject to the semantic-reconciliation work being doable. If the structural semantics of "Abstractification" and "Attraction" cannot be reconciled as names for the same mathematical operator, then Path 4 collapses and one of Paths 1 or 2 is required. Determining this is itself a framework-level decision requiring Wakil's authorial input.

**If Path 4 is not achievable, my fallback recommendation is Path 1 (book is canonical).** Reasons:
- The book is the primary external deliverable with the strongest claim to being "the CAS definition," because the CAS framework was defined authorially by Wakil in the book-class documents.
- The patent and the peer-review paper are both scheme-agnostic; no IP or academic commitment is lost by adopting Scheme A.
- The platform changes required to adopt Scheme A are codebase renamings — mechanically tractable, not editorially difficult.
- The Foundational Clarifications document rewrite is genuine work but a much smaller scope than a 124K-word manuscript rewrite.

### C.3 Next actions by decision outcome

- **If Wakil chooses Path 1:** I revert tonight's Scheme B annotations in CLAUDE.md, rewrite the Foundational Clarifications document using Scheme A's structural semantics, rename the compiler's OPERATOR_NAMES, rename the dashboard/interpreter/LLM-prompt labels from Scheme C to Scheme A, and then Phase 2 reformation work on FULL_MANUSCRIPT.md proceeds with the structural-language pass only (no renaming needed because Scheme A is already the book's scheme).
- **If Wakil chooses Path 2:** we defer the book's reformation pass to a multi-session Scheme-A-to-Scheme-B rewrite project. Phase 2 as originally scoped becomes Phase 2.5 or Phase 3; the current Phase 2 tonight is officially closed as "audit-only."
- **If Wakil chooses Path 4:** I draft `docs/CAS_OPERATOR_NAMING_TABLE.md` in a future session, including per-operator structural-semantic reconciliation; Phase 2 reformation proceeds on the book using Scheme A labels and structural-not-emotional language revisions consistent with Scheme A's semantics.

### C.4 What I recommend doing **tonight** regardless of Wakil's choice

1. Commit this audit document (this file).
2. Hold FULL_MANUSCRIPT.md reformation work until Wakil chooses a path.
3. Do not touch CLAUDE.md or docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md until the path is chosen (tonight's Foundational Clarifications is built around Scheme B; rewriting it before the path is chosen wastes the work if Scheme B survives).
4. The three preparatory Phase 2 commits that have already landed tonight (preservation snapshot `90db69c`, archive of stale drafts `f46c1d5`, UTF-8 conversion `126569c`) stand regardless of path choice. None of them touch operator naming.

Session 1 of Phase 2 closes at this audit. Phase 2 Session 2 resumes after the authority question is settled.
