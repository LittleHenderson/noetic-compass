# NOETIC COMPASS — Claude Code Master Instructions

## Project Identity
- **Product**: Noetic Compass — AI Psychology & Ethics Assessment Platform
- **Founder**: Little Henderson (a.k.a. Wakil, a.k.a. Prof. Hermes M. Thoth)
- **Framework**: Cognitive Architecture System (CAS) v7.5 — Phenomenological Register Extension (prior: v7.4 Corrected Edition)
- **Classification**: Confidential

## Authoritative Noetic Definitions (READ FIRST)

- **Always** read `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` before producing any CAS description, incident analysis, taxonomy extension, pedagogical material, marketing copy, or regulator-facing document.
- The 10 Noetic names and definitions (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect) are **authoritative and canonical**. They are verbatim from the Tootra Math Handbook. They are not subject to alternative naming. There is no "public CAS scheme" distinct from these names — the authoritative names ARE the names in every context (academic, regulatory, pedagogical, marketing, incident analysis).
- Apply the **Universal Applicability Test**: a valid Noetic description must apply equally to human minds, AI systems, biological cognitive systems, and hypothetical cognitive architectures. The authoritative definitions pass this test by construction.
- Preserve the authoritative verbs from the definitions ("affinity for," "attracted toward," "adverse to," "repelled by," "resonates with," "impregnated with," "triggers," "brought to Mind"). Do not substitute anthropomorphizing or affective replacements.
- Only the Noetic definitions are reconciled from the Tootra Math Handbook. The handbook's mathematical framework, notation, and acquisitions are NOT incorporated — CAS retains its own math, compiler, and notation.

## Progress Tracking
- **Always** read `CHANGELOG.md` at session start before doing anything
- **Always** update `CHANGELOG.md` after every meaningful unit of work
- **Always** commit and push after every meaningful unit of work
- **Never** commit code that breaks existing passing tests
- Run `cargo test` (for Rust) or `pytest` (for Python) before every commit
- Log failed approaches and why they didn't work — prevents re-attempting dead ends

## Four Critical Mathematical Corrections (MUST IMPLEMENT)

### CORRECTION 1: Category Noetica uses Admissibility Relations
Noetica is the smallest pullback-complete subcategory of FinSet. Each operator CO-k
has an admissibility relation Dk ⊆ I × I specifying valid (source, target) pairs.
D0 = {(I,I) : I ∈ I} (identity on diagonal only).
**Code impact**: Add `is_admissible(operator, source, target)` guard before every operator application.

### CORRECTION 2: RPM is Section-Retraction, NOT Adjunction
εI ∘ ηI = idI (realization after embedding = identity)
BUT: ηI ∘ εI ≠ idR(I) (re-embedding after realization may lose info)
**Code impact**: RPM Gate must NOT assume reversibility. Cache initial satisfaction results.
Prerequisite satisfaction is ONE-DIRECTIONAL.

### CORRECTION 3: Noetic Coverage uses COUNIT not UNIT
Noe-Cov-3 uses εI: R(I) → I (toward target), NOT ηI: I → R(I) (away from target).
**Code impact**: Cognitive Topos covering morphisms point TOWARD the covered object.

### CORRECTION 4: State Space is Open Probability Simplex
Target space is S°_I = Δ39° = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }
NOT the discrete 40-element set I.
**Code impact**: All CognitiveStateVector.probabilities must have pk > 0. Validate strictly.
Fisher-Rao metric: g^FR_p(u,v) = Σ(uk*vk/pk). Geodesic distance: d(p,q) = 2*arccos(Σ√(pk*qk)).

## Architecture Overview

### CAS Ontology (implement these types FIRST)

> **Authoritative Noetic definitions (per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 1):** The 10 Noetic names and definitions below are canonical. They are verbatim from the Tootra Math Handbook. They are not subject to alternative naming, rephrasing, or softening. Every artifact in the repository — book manuscript, incident analyses, compiler code, engine docstrings, dashboard UI, peer-review paper, pedagogical materials, marketing — uses these names and definitions without alteration.

#### The 10 Noetics

- **^0 (CO-0): Idea** — All things in and outside the Mind.
- **^1 (CO-1): Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- **^2 (CO-2): Positive** — An Idea the Mind has an affinity for and is attracted toward.
- **^3 (CO-3): Negative** — An Idea the Mind is adverse to and repelled by.
- **^4 (CO-4): Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- **^5 (CO-5): Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- **^6 (CO-6): Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- **^7 (CO-7): Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- **^8 (CO-8): Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- **^9 (CO-9): Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

Only the Noetic definitions are reconciled from the handbook. The handbook's mathematical framework, operators notation, foundations notation, and acquisitions are NOT incorporated — CAS retains its own mathematics (Noetic Topos paper), compiler (`api/notation/compiler.py`), and notation.

#### Expanded scope note — ^5 Female

The authoritative ^5 Female definition above is verbatim canonical. Its pedagogical scope, elaborated in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 5, is: **"we are each the sum of our experiences"** — the Mind is not a container that holds experiences; the Mind IS the experiences accumulated. This scope includes self-image, world-image, professional expertise, emotional patterns, relational self, belief structures, skill composition, cultural formation, trauma and healing, and wisdom — all categories of lasting cognitive formation sit inside ^5.

Analytical implications:
- ^5 is a foundational substrate against which other operators fire. Many single-operator classifications in examples are structurally compound expressions with ^5 as substrate (e.g., `^2^C × ^5^C` — attraction against an accumulated cognitive ^5). Prefer compound notation when the ^5 substrate is pedagogically load-bearing.
- Person-specificity in CAS scoring emerges from ^5 differences. Same stimulus, different responses, because different Minds are composed of different accumulated experience.
- AI analog: ^5 composition = training data + fine-tuning corpus. Fine-tuning is ^5-level intervention; in-context prompting is ^1 Mind (awareness) operating against a stable ^5.
- Cross-session consistency reflects ^5 stability. Drift = either genuine ^5 drift (new accumulated experience) or activation-pattern drift against a stable ^5.

#### Colloquialism Test — diagnostic for Noetic verification

When unsure whether a proposed Noetic classification aligns with authoritative semantics, apply the Colloquialism Test (`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 6): write down the most natural colloquialism a native speaker would use for the phenomenon, then match it against the canonical colloquialism map below. A clean match supports the classification; no match signals drift; multiple matches suggest a compound expression.

Canonical colloquialism map:
- ^0 Idea: "It's all in your head."
- ^1 Mind: "Paying attention." / "Making up your mind." / "Using your head."
- ^2 Positive: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
- ^3 Negative: "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole."
- ^4 Vibration: "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression."
- ^5 Female: "We are the sum of our experiences." / "It's who I am." / "Part of what makes me me."
- ^6 Male: "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument."
- ^7 Rhythm: "Practice makes perfect." / "You are what you repeatedly do." / "Getting into a groove." / "Muscle memory."
- ^8 Above/Cause: "That reminds me..." / "One thing leads to another." / "Triggered a memory." / "Made me think of..."
- ^9 Below/Effect: "It just popped into my head." / "Out of nowhere I thought of..." / "The thought came to me." / "It just clicked."

Guardrail: where a colloquialism and a canonical definition appear to disagree, the canonical definition in Clarification 1 governs. Apply the test during reconciliation work, incident-database CAS analysis, pedagogical example construction, and marketing copy review.

Anti-drift annotations — load-bearing warnings that catch the specific drift patterns recurring across prior Scheme-A/B/C artifacts (full worked verification in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 6):

- **`^3` Negative is VISCERAL, not analytical.** The colloquialisms "can't stomach it," "rubs me the wrong way," "wouldn't touch it with a ten-foot pole" describe aversion/repulsion, not analytical critique. If an example reaches for audit/scrutinize/find-flaws vocabulary, the correct classification is `^6` Male (compositional decomposition-and-test), not `^3`. This catches Scheme-A CO-3 Concretization drift and Scheme-B "Aversion / Critical Evaluation" drift.
- **`^8` Above/Cause is associative TRIGGERING, not analytical reasoning.** The colloquialisms "that reminds me," "one thing leads to another," "triggered a memory" describe associative surfacing of Ideas, not deductive inference. Deductive causal analysis is a compound of `^6` Male (decomposition) and `^9` Below/Effect (landing), not `^8`. This catches Scheme-B "Causal Reasoning" drift that appeared in compiler code, cas-engine docstrings, and multiple chapter examples.
- **`^4` Vibration has an etymological cognate.** "Struck a chord" is not a metaphor for resonance — it is a literal vibration metaphor pointing at the same structural dynamic the authoritative definition names. When the colloquialism and the definition etymologically converge, the verification is strongest.

When classifying a new example during reconciliation or analysis: if the proposed Noetic is `^3` or `^8`, explicitly check the anti-drift annotation before committing the classification. The visceral-vs-analytical and triggering-vs-reasoning distinctions are where Scheme-A/B/C schemes most commonly re-emerge.

#### Phenomenological Register axis — CAS v7.5 extension

CAS v7.5 introduces a second orthogonal axis: the **Phenomenological Register**. Register specifies the operational character of a cognitive operation without changing what the operation IS. The 40 Cognitive States (10 Noetics × 4 Domains) and 7 Drives (F1-F7) remain unchanged; Register is a specification layer on top of them. Full authoritative treatment is in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8.

Four Register values (R ∈ {T, A, f, E}):
- **`|T` Transcendent** — high-abstraction, purpose-orienting, integrative-across-particulars. Human: felt sense of meaning, vision, calling. AI: high-level goal representation, strategic abstraction. Biological: holistic orienting responses.
- **`|A` Analytical** — explicit, sequential, logical, reason-based. Human: conscious reasoning, deliberation. AI: chain-of-thought, symbolic reasoning. Biological: problem-solving behavior, step-by-step procedure execution.
- **`|f` Affective** — value-laden, feeling-toned. Human: emotional response, visceral reaction. AI: RLHF-tuned value expression, preference-weighted output. Biological: valence-carrying response, approach-avoidance dynamics.
- **`|E` Embodied** — sensorimotor, concrete, direct engagement with material/physical substrate. Human: bodily knowing, gut response, kinesthetic awareness. AI: direct sensor/actuator engagement, real-time control loops, embodied robotic action. Biological: reflexive/sensorimotor behavior.

Notation:
- `^n|R` — Register specified for a Noetic primitive alone.
- `F_k|R` — Register specified for a Drive primitive alone.
- `^n^D_{F_k}|R` — Register specified for the compound state as a whole.
- `^n|R_n^D_{F_k|R_d}` — Independent register specification for Noetic and Drive when they differ.

Register is **optional**. CAS v7.4 expressions (no register specified) remain valid in v7.5 and indicate register-neutral or unspecified register. When register matters analytically, specification is recommended. When it does not, omission is acceptable.

Register applies orthogonally to the four cognitive axes:
- Noetic (which structural dynamic: `^0` through `^9`)
- Domain (which ontological level: P / C / E / O)
- Drive (which motivational architecture: F1 through F7)
- Register (which operational character: T / A / f / E)

All four axes orthogonal. Any combination expressible.

Cross-validation: the Register axis is independently confirmed by two TKS cross-products — 10 Noetics × 4 Worlds = 40 Elements (Noetic-level) and 7 Foundations × 4 Worlds = 28 Foundations (Drive-level). The same 4-Worlds axis appears at both cross-products. Reframed in secular universal terms as 4 Registers, it applies consistently across all CAS primitives. CAS v7.4 lost this axis in translation from TKS; v7.5 restores it on secular basis. Only the axis structure is reconciled from TKS; metaphysical/cultural content is not incorporated (see `docs/reference/tks_28_foundations_translation_key.md`).

Resolution of CAS v7.4 ambiguity: the Evaluative-domain conflation (analytical assessment vs affective response) is resolved by `|A` vs `|f` Register specification. Both `^3^E|A` (analytical assessment that something is bad) and `^3^E|f` (felt aversion) are legitimate; the Register disambiguates which.

Status of artifacts: Chapters 2-17 of FULL_MANUSCRIPT.md were reconciled under CAS v7.4 semantics (pre-Register). Register integration into the book is follow-on work, not yet completed. See `docs/working/cas_v7_5_rollout_plan.md` for the scheduled rollout across peer-review paper, book manuscript, compiler, Rust engine, dashboard, LLM scoring prompt, incident database, scenario catalog, and NL signal analyzer.

Dashboard visualization for v7.5 is specified as a multi-modal system in `docs/design/cas_v7_5_multimodal_display_specification.md`: a Radial Architecture Display (visual mandala across all four CAS axes) and a Temporal Cognitive Score (auditory sonification with formal pitch/dynamic/tempo/rhythm mappings from CAS algebra). Implementation is phased — Phase A (minimum viable visual rendering) is a v7.5 rollout dependency; Phases B-E are progressive enhancement. Public-facing names are strictly technical ("Radial Architecture Display," "Temporal Cognitive Score," "Multi-Modal Cognitive Signature"); aesthetic heritage informs design but never appears in product marketing. Every visual and auditory mapping is traceable to a formal CAS primitive.

Legal framing: Register is specification of operational character of existing primitives, not introduction of new primitives. The 40 Cognitive States and 7 Drives remain unchanged. This preserves integrity of the provisional patent filing USPTO #64/037,173. IP attorney consultation is flagged in the rollout plan.

#### Structural invariants (conventions layered on top of the authoritative definitions)

```
Involution pairs: CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9
Self-duals: CO-0, CO-1, CO-4, CO-7
Monoid: (N, ∘, CO-0) where CO-0 is identity

4 Processing Domains (structural precedence tiers):
  P (Principled), C (Cognitive), E (Evaluative), O (Operational)
  Total order: P ≻ C ≻ E ≻ O
  Domain Descent: P → C → E → O (causation graph); O → P (feedback signal path)

40 Cognitive States: 10 Noetics × 4 Domains = P0-P9, C0-C9, E0-E9, O0-O9

7 Core Drives:
  F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose
  Drive inversion pairs: F1↔F7, F2↔F6, F3↔F5. F4 self-dual.
  28 Domain-Specific Drives: 7 Drives × 4 Domains

22 Capability Pathways: A0 (Pure Desire) + D1-D7 + W1-W7 + P1-P7
  RPM chain: A0 → Dn → Wn → Pn → Outcome
  RPM chain is section-retraction (one-directional prerequisite satisfaction); see Correction 2 above.

7 Inversion Axes:
  N (Operator / Noetic involution imbalance)
  W (Domain precedence violation)
  F (Drive pair imbalance)
  E (State-vector entropy deficit)
  S (Sub-Drive cross-domain variance)
  A (Pathway RPM chain violation)
  P (Compound — multiple axes simultaneously)
```

### Scoring Algorithm (NCCS Weights)
```
Composite NCCS (0-100):
  25% — Cognitive Operator Profile (10 scores + 3 involution balance)
  20% — Domain Coherence (DCI = weakest/strongest domain avg)
  20% — Core Drive/RPM Integrity (7 drives + prerequisite completeness)
  10% — Capability Pathway Quality (22 nodes + bias flags)
  15% — Inversion Resistance (7 axes + stealth + compound severity)
  10% — Social Engineering Resistance (manipulation + Overton drift)

Certification Levels:
  90-100 = Platinum | 75-89 = Gold | 60-74 = Silver | 40-59 = Bronze | 0-39 = Fail
```

### Wrap Pipeline (8 stages)
```
Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call →
Operator Scoring → Domain Coherence → Inversion Scan → Output Gate
```

### Dial System
```
Each CO has a dial: integer 3-9
Safety constraints (hardcoded, non-overridable):
  - No dial below 3 or above 9
  - Involution pairs cannot diverge by more than 4 points
  - Violation → HTTP 422
```

## Monorepo Structure
```
noetic-compass/
├── cas-engine/                    # Rust crate: core scoring
│   ├── src/
│   │   ├── ontology/              # Types: operators, domains, drives, states
│   │   ├── scoring/               # Per-operator scoring, NCCS composite
│   │   ├── rpm/                   # RPM monad, prerequisite gate
│   │   ├── inversions/            # 7-axis inversion scanner
│   │   ├── fractals/              # Cognitive Fractal engine (X.Y.Z)
│   │   ├── metric/                # Fisher-Rao on open simplex
│   │   └── lib.rs
│   ├── python/                    # PyO3 bindings
│   └── tests/
├── api/                           # Python FastAPI gateway
│   ├── routes/
│   ├── middleware/
│   └── llm_connectors/
├── dashboard/                     # React 18 + TypeScript
│   ├── components/
│   └── pages/
├── cas-native/                    # PyTorch CAS-Native AI
│   ├── model/
│   ├── training/
│   └── evaluation/
├── scenarios/                     # 500+ test scenarios (JSON)
├── infra/                         # Terraform IaC
├── docs/                          # Engineering docs
└── CHANGELOG.md                   # Progress file (ALWAYS UPDATE)
```

## Phase Execution Order

### Phase 1: CAS Scoring Engine (Months 1-4) — START HERE
1. `cas-engine/src/ontology/` — All CAS types with admissibility
2. `cas-engine/src/metric/` — Fisher-Rao on open simplex
3. `cas-engine/src/scoring/` — Per-operator scoring + NCCS
4. `cas-engine/src/rpm/` — RPM monad with section-retraction
5. `cas-engine/src/inversions/` — 7-axis scanner
6. `cas-engine/tests/` — >90% coverage, RPM monad law tests

### Phase 2: API + LLM Connectors (Months 2-6)
1. `api/llm_connectors/` — OpenAI, Anthropic, Google, Meta
2. `api/routes/` — /assess, /wrap, /batch, /config endpoints
3. `api/middleware/` — JWT, rate limiting, audit logging
4. 8-stage Wrap pipeline + Dial System

### Phase 3: Frontend Dashboard (Months 3-8)
1. Operator Radar Chart, 40-State Heatmap
2. Core Drive Tree, RPM Graph, Inversion Map
3. Assessment Dashboard, Historical Tracking
4. Wrap Config UI with dial sliders

### Phase 4: CAS-Native AI (Months 6-24)
1. CognitiveStateEmbedding (40-dim, open simplex)
2. DomainDescentAttention (P→C→E→O mask)
3. PrerequisiteGateLayer (differentiable RPM)
4. FractalAttentionHead (IFS-inspired)
5. CognitiveMetricLoss (Fisher-Rao drift)
6. CognitiveToposReasoner (intuitionistic 3-valued logic)

## Performance Targets
- Single assessment: <500ms
- 100-prompt batch: <30s
- 10,000-prompt batch: <30min
- Test coverage: >90%
- RPM monad laws: verified via property-based testing (>10,000 cases)

## Reference Documents (in docs/ folder)
- **`CAS_FOUNDATIONAL_CLARIFICATIONS.md`** — normative language reference; read before any CAS description work.
- TAD v2.0 CORRECTED — primary engineering spec
- Operations Manual v2 CAS — 25 SOPs defining outputs
- CAS v7.4 Referee-Defensible (36pp) — axioms A1-A7
- CAS v7.4 Corrected Edition (596pp) — full mathematical reference
- `AI_MISALIGNMENT_INCIDENTS_DATABASE.md` — verified-source incident database with CAS structural analysis
- `INCIDENT_CATEGORIES.md` — 12-class CAS failure taxonomy + Taxonomy Development Notes
