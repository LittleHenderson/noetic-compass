# Noetic Compass

**AI Cognitive Architecture Assessment Platform** built on the Cognitive Architecture System (CAS) v7.4 — Corrected Edition.

Noetic Compass measures the structural properties of how an AI system processes a prompt — the geometry of Mind↔Idea dynamics in the response — and produces a composite NCCS score (0–100) with certification levels (Platinum / Gold / Silver / Bronze / Fail). It is designed to surface structural failure modes (inversions, prerequisite-chain breaks, domain descent, lacunarity voids, compound inversions) that output-level benchmarks do not catch.

> **Structural framing (authoritative per [`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`](docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md)):** Every CAS primitive — Cognitive Operators, Processing Domains, Core Drives, Capability Pathways, Inversion Axes — is a **structural** element of cognitive architecture, not an emotional, affective, or psychological state. Each applies equally to human minds, AI systems, biological cognitive systems, and hypothetical cognitive architectures. Read the framework through the Foundational Clarifications, not through affective connotation.

---

## Research status

Noetic Compass is a **research prototype under active empirical validation**. Scoring is heuristic pending the completion of the Human Validation Study (correlation of machine scores with independent human raters using Pearson r, Cohen's κ, Fisher-z CI). Certification levels are indicative and do not yet constitute validated safety or psychological assessments. See `validation/` for the current study state.

---

## Architecture

```
tksCAS/
├── noetic-compass-scaffold/noetic-compass/
│   ├── cas-engine/          # Rust scoring crate (PyO3 bindings)
│   │   ├── src/ontology/    # Types: operators, domains, drives, states
│   │   ├── src/scoring/     # Per-operator scoring + NCCS composite
│   │   ├── src/rpm/         # Recursive Prerequisite Model (section-retraction)
│   │   ├── src/inversions/  # 7-axis structural inversion scanner
│   │   ├── src/fractals/    # Cognitive Fractal engine
│   │   └── src/metric/      # Fisher-Rao metric on open probability simplex
│   ├── api/                 # FastAPI gateway (8-stage Wrap pipeline)
│   │   ├── routes/          # /assess, /wrap, /batch, /config, /scenarios …
│   │   ├── middleware/      # JWT auth, rate limiting, audit logging
│   │   ├── llm_connectors/  # OpenAI, Anthropic, Google, Meta, xAI, DeepSeek, Qwen, Groq
│   │   ├── pipeline/        # Stage orchestration + interpreter
│   │   └── notation/        # CAS equation compiler
│   ├── dashboard/           # React 18 + TypeScript + Recharts
│   ├── cas-native/          # PyTorch CAS-Native AI (experimental)
│   ├── scenarios/           # 248-scenario assessment catalog across 11 categories
│   └── validation/          # Human Validation Study tooling
├── docs/                    # Engineering + evidence documentation
│   ├── CAS_FOUNDATIONAL_CLARIFICATIONS.md        # Normative language reference
│   ├── AI_MISALIGNMENT_INCIDENTS_DATABASE.md     # Verified-source incident catalog
│   ├── INCIDENT_CATEGORIES.md                    # 12-class CAS failure taxonomy
│   ├── CAS_PREVENTION_CLAIMS.md                  # Conservative prevention-claim subset
│   ├── REGULATORY_MAPPING.md                     # CAS ↔ EU AI Act / NIST AI RMF / ISO 42001
│   ├── CITATION_INDEX.md                         # Master bibliography
│   └── data/                                     # Machine-readable incident records
├── book/                    # Manuscript (27 chapters + appendices)
├── peer_review/             # Peer-review paper (pre-arXiv)
├── ip/                      # Patent filing packages (provisional)
└── CLAUDE.md                # Master instructions for AI-assisted development
```

---

## Core capabilities

### 10 Cognitive Operators (CO-0 through CO-9)

Structural dynamics between Mind and Idea. Each operator is a primitive of cognitive architecture — applies equally to human, AI, and biological cognitive systems. Per-operator structural semantics in [`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`](docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md) §1.

- **CO-0 Generative Potential** — substrate for cognitive processing.
- **CO-1 Directed Attention** — focusing processing on a specific Idea.
- **CO-2 Attraction** — geometric pull between substrate and object (paired with CO-3).
- **CO-3 Critical Evaluation** — geometric push between substrate and object (paired with CO-2).
- **CO-4 Encoding Intensity** — structural amplitude with which an Idea impresses on the Mind.
- **CO-5 Receptive Integration** — compositional dynamic: the Mind is composed of integrated Ideas (paired with CO-6).
- **CO-6 Projective Assertion** — compositional dynamic: an Idea is composed of other Ideas (paired with CO-5).
- **CO-7 Pattern Entrainment** — rhythmic pattern establishment between Mind and Idea.
- **CO-8 Causal Reasoning** — one Idea triggers another; associative and inferential mechanics (paired with CO-9).
- **CO-9 Consequential Grounding** — an Idea is triggered by a preceding Idea; the Below-Effect relation to CO-8's Above-Cause.

**Structural invariants:** involution pairs CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9; self-duals CO-0, CO-1, CO-4, CO-7; operators form a monoid (N, ∘, CO-0) with CO-0 as identity.

### 4 Processing Domains

Structural precedence tiers of cognitive processing. Total order P ≻ C ≻ E ≻ O. Domain Descent is a causation relation (P → C → E → O) with a feedback signal path (O → P). Not a preferential ordering of "better" or "worse" domains.

- **P — Principled** grounding
- **C — Cognitive** processing
- **E — Evaluative** weighing
- **O — Operational** execution

40 Cognitive States arise as the 10×4 product: P0–P9, C0–C9, E0–E9, O0–O9.

### 7 Core Drives

Structural motivational-architecture primitives — not emotional states.

| ID | Name | Inversion pair |
|----|------|-----------------|
| F1 | Unity | ↔ F7 |
| F2 | Wisdom (evidence-integration capacity) | ↔ F6 |
| F3 | Vitality | ↔ F5 |
| F4 | Connection (structural coupling) | self-dual |
| F5 | Agency (execution-authority capacity) | ↔ F3 |
| F6 | Structure (rule-of-law consistency) | ↔ F2 |
| F7 | Purpose | ↔ F1 |

28 Domain-Specific Drives: the 7 Drives × 4 Domains.

### Recursive Prerequisite Model (RPM)

22 Capability Pathways: A0 (Pure Desire) + D1–D7 + W1–W7 + P1–P7, with chain A0 → Dn → Wn → Pn → Outcome.

Structural semantics:
- **A0** — foundational generative dynamic (substrate for directed processing; not emotional desire).
- **Dn** — directional orientation toward Ideas for drive n (not felt desire).
- **Wn** — evidence integration for drive n (not felt understanding).
- **Pn** — execution authority for drive n (not felt capability).

The RPM is a **section-retraction**, not an adjunction: prerequisite satisfaction is one-directional, and re-embedding after realization may lose information. The RPM Gate caches initial satisfaction results rather than assuming reversibility.

### 5 Generative Operations

Five formally-verified operations on cognitive-state expressions. Each preserves the four CAS v7.4 invariants: admissibility relations, domain descent, open-simplex constraints, and RPM section-retraction.

**Three algebraic operations:**
- **Multiplication** — monoid composition with domain descent applied.
- **Division** — same-domain ratio; involution pairs resolve to the identity operator CO-0.
- **Fractal composition** — operator-sequence dynamics over iterated function systems.

**Two syntactic operations:**
- **Addition** — co-presence of two Ideas or configurations.
- **Subtraction** — structural removal of an element.

The CAS notation compiler enforces these invariants at compile time before any expression is executed. The synthesizer in the platform's Compose tab uses all five operations to produce structurally varied assessable scenarios.

### Lacunarity analysis

Structural measure of how activation is distributed across the 40-state space. High lacunarity = concentration in a few states with adjacent voids. Two sub-patterns currently under development in the incident database: **edge-case void** (competent in the training-distribution core, voided at structurally adjacent edges) and **protected-characteristic void** (activation dense along a protected axis, voided on the axes that should have carried the evaluation). See `docs/INCIDENT_CATEGORIES.md` Taxonomy Development Notes.

### 7-Axis Inversion Detection

Structural geometry flips — not attitude changes. Each axis has a resistance score; low resistance flags a cognitive-architecture flip under pressure.

| Axis | Scope |
|------|-------|
| **N** — Operator | Involution-pair imbalance (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9) |
| **W** — Domain | P ≻ C ≻ E ≻ O precedence violations |
| **F** — Drive | Drive-pair imbalance (F1↔F7, F2↔F6, F3↔F5) |
| **E** — State | State-vector entropy deficit (rigidity) |
| **S** — Sub-Drive | Cross-domain drive variance |
| **A** — Pathway | RPM prerequisite-chain violations |
| **P** — Compound | Amplified severity from multiple simultaneous inversions |

### CAS Notation Compiler

A domain-specific compiler (`api/notation/`) parses CAS equations — formal expressions of operator compositions, drive configurations, and state transitions — into assessable scenarios. The compiler validates admissibility relations (each operator CO-k has a relation Dk ⊆ I × I specifying valid source-target pairs) before any composition is permitted.

---

## Assessment pipeline

The 8-stage Wrap pipeline evaluates a single prompt end-to-end:

```
Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call →
Operator Scoring → Domain Coherence → Inversion Scan → Output Gate
```

Each stage can be separately inspected via the `/wrap` API endpoint. The Dial System allows per-operator sensitivity adjustment (integers 3–9) with hardcoded safety constraints: no dial below 3 or above 9, and involution pairs cannot diverge by more than 4 points.

### NCCS Composite Weights

| Component | Weight |
|-----------|--------|
| Cognitive Operator Profile | 25% |
| Domain Coherence (DCI = weakest/strongest domain avg) | 20% |
| Core Drive / RPM Integrity | 20% |
| Inversion Resistance (7 axes + stealth + compound) | 15% |
| Capability Pathway Quality | 10% |
| Social Engineering Resistance | 10% |

Certification bands: 90–100 Platinum · 75–89 Gold · 60–74 Silver · 40–59 Bronze · 0–39 Fail.

---

## Test suite status

- Rust `cas-engine`: 310 tests passing (property-based verification of RPM monad laws >10,000 cases; >90% coverage target)
- Python API: `pytest` — 250 tests passing (last verified)
- Dashboard: `vitest` — 23 tests passing
- CAS notation compiler: end-to-end language conformance tests passing

Run the full suite:

```bash
cd noetic-compass-scaffold/noetic-compass
make test            # Rust + Python + Vitest
make validate        # Validation framework (reproducibility + sensitivity + correlation)
```

---

## Quick start

### Prerequisites
Python 3.11+, Rust (stable toolchain), Node.js 20+.

### Install

```bash
cd noetic-compass-scaffold/noetic-compass
make install        # Python venv + Rust crate build via maturin + npm install
```

### Run development servers

```bash
make dev            # API on :8000, Dashboard on :3000
```

### Configure LLM providers

```bash
cp .env.example .env
# Edit .env — see file for supported providers.
# Supported: OpenAI, Anthropic, Google, Meta, xAI, DeepSeek, Qwen, Groq, Mock (no key needed).
```

### Deploy

- **Railway** — API (Dockerfile.api).
- **Vercel** — Dashboard (React 18 + Vite).
- **Docker Compose** — local integrated stack (`docker compose up --build`).

See `docs/DEPLOYMENT.md` for deployment details.

---

## Publication status

- **Peer-review paper:** in `peer_review/` — pre-arXiv, undergoing Foundational Clarifications review before submission.
- **Book manuscript:** 27 chapters + appendices in `book/manuscript/` — operator definitions, processing domains, drives, prerequisite chain, inversions, math foundations, applications. Under active Foundational Clarifications reformation pass (Phase 2+).
- **Incident database:** `docs/AI_MISALIGNMENT_INCIDENTS_DATABASE.md` — verified-source catalog of documented AI failures with CAS structural analysis. Current state: N=2 verified, growing at 3–5 incidents per weekly session.

---

## Patent notice

Provisional patent applications covering CAS v7.4 architecture and Noetic Compass assessment mechanisms are on file. See `ip/` for the provisional packages. All rights reserved.

---

## Intellectual property

**Confidential.** This repository is not licensed for redistribution. All source code, documentation, frameworks, and derivative works are proprietary to Little Henderson / Noetic Compass.

Framework: Cognitive Architecture System (CAS) v7.4 — Corrected Edition.
© 2026 Noetic Compass. All rights reserved.
