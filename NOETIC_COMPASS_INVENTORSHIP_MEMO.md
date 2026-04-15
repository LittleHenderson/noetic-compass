# Noetic Compass Inventorship Memo

Prepared on April 12, 2026 by Little Henderson.

This is a factual memo for counsel review. It is not a legal conclusion and not a filed document.

## Invention Family

This memo covers the **Noetic Compass system** claim family only:

- staged AI-response assessment through an ordered wrap pipeline
- scoring-mode separation and provenance
- external scorer separation from the generator
- human calibration and reconciliation workflows
- validation evidence capture, review, and benchmark separation

It is not intended to claim the entire CAS/TKS framework in the abstract.

## Short Description

The Noetic Compass system is a multi-stage AI assessment platform. It receives a prompt, routes it through a selected AI generator, evaluates the resulting output through an ordered 8-stage scoring pipeline, records scoring provenance such as which model generated, which model scored, and which scoring method was used, and presents the results together with calibration, benchmark, and evidence-review tooling.

## Claimed Technical Concepts

1. Multi-stage wrap pipeline for AI response assessment
2. Explicit scoring-mode separation with provenance-aware result reporting
3. External scorer resolution distinct from the generator when available
4. Human calibration and reconciliation workflow for disputed assessment items
5. Validation evidence subsystem with separated benchmark tables and error-case logging

## Human Conception by Concept

### Concept 1

- **Technical concept:** Multi-stage wrap pipeline for AI response assessment
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Conceived the 8-stage ordered pipeline structure: Input Analysis -> RPM Gate -> Dial Adjustment -> Base LLM Call -> Operator Scoring -> Domain Coherence -> Inversion Scan -> Output Gate
  - Selected and specified this pipeline shape as part of the Noetic Compass system design
- **Approximate conception timing:**
  - The underlying framework elements informing the pipeline were developed before the April 2026 implementation phase
  - The specific Noetic Compass pipeline architecture was conceived before implementation began on April 6, 2026
- **Supporting evidence:**
  - Technical Architecture Document (TAD v2 Corrected)
  - `api/pipeline/runner.py`
  - `api/pipeline/stages.py`

### Concept 2

- **Technical concept:** Explicit scoring-mode separation with provenance-aware result reporting
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified separation of three scoring modes: `heuristic_fallback`, `secondary_llm`, and `self_reported`
  - Specified result-level provenance fields including `scoring_method`, `scorer_provider`, and `scorer_model`
  - Directed this separation after adversarial audit identified self-scoring bias as a system risk
- **Approximate conception timing:**
  - Conceived April 9, 2026 during the adversarial audit and remediation cycle
- **Supporting evidence:**
  - `api/models.py`
  - `api/pipeline/runner.py`
  - Codex audit materials identifying the self-scoring problem

### Concept 3

- **Technical concept:** External scorer resolution distinct from the generator when available
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified the policy that an external scorer should be preferred over self-grading when available
  - Specified the practical fallback hierarchy for assessment scoring
  - Specified that self-scoring should be visibly distinguished from external scoring and heuristic scoring in stakeholder-facing results
- **Approximate conception timing:**
  - Conceived April 9, 2026 during the same audit and remediation cycle
- **Supporting evidence:**
  - `api/pipeline/runner.py`
  - Assessment UI changes exposing separate scoring controls and provenance

### Concept 4

- **Technical concept:** Human calibration and reconciliation workflow for disputed assessment items
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified the concept of queueing items where machine scores and human scores materially diverge
  - Specified the workflow in which human raters score prompt-response pairs, divergence cases are flagged, and a reconciliation disposition is recorded
  - Specified recording of notes and optional reconciled score snapshots
- **Approximate conception timing:**
  - Conceived April 8, 2026 as part of the validation-study design
- **Supporting evidence:**
  - `api/validation/calibration_sessions.py`
  - `api/routes/validation.py`
  - `dashboard/src/pages/ValidationPage.tsx`

### Concept 5

- **Technical concept:** Validation evidence subsystem with separated benchmark tables and error-case logging
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified separate storage and presentation of scorer-agreement cases, benchmark-suite runs, and false-positive/false-negative cases
  - Specified trend and export tooling organized by provider, model, and scoring mode
  - Specified a leaderboard/review surface for monitoring validation progress
- **Approximate conception timing:**
  - Conceived April 8, 2026 as part of the validation-study design
- **Supporting evidence:**
  - `api/validation/evidence.py`
  - `api/routes/validation.py`
  - `dashboard/src/pages/ValidationLeaderboardPage.tsx`

## Role of AI Assistance

### AI systems used

- Claude (Anthropic)
- Codex (OpenAI)
- Gemini (Google)

### What the AI was used for

- code implementation from human-specified architecture and design decisions
- document drafting from human-specified outlines and content requirements
- code auditing and bug detection
- testing and test generation
- architecture discussion and feedback

### Human decisions that controlled the Noetic Compass claim family

- Little Henderson directed the 8-stage Wrap pipeline architecture.
- Little Henderson specified the scoring-mode separation and provenance architecture.
- Little Henderson specified the external scorer architecture.
- Little Henderson directed the human calibration workflow and the validation evidence structure.
- Little Henderson directed the shift to research-prototype framing rather than overclaiming validated assessment science.

### Human-chosen, rejected, or reshaped technical decisions

**Chosen by human:**
- Dual-scorer architecture after audit revealed self-scoring bias
- Separate benchmark tables by scoring mode
- Research-prototype framing over certification-style framing

**Rejected by human:**
- Model-as-judge self-scoring as a default stakeholder-facing mode
- Synthetic validation labels in favor of real human labeling

**Reshaped by human:**
- Public terminology and product framing around CAS/TKS concepts
- Report language softened from certification claims to research/prototype language

## Contributions That Should Not Count as Inventorship by Themselves

The following are implementation-only or non-conception contributions and do not constitute inventorship by themselves:

- Claude: implementation assistance, drafting assistance, and architecture discussion under human specification
- Codex: code auditing, implementation assistance, and remediation assistance under human direction
- Gemini: feature suggestions and drafting assistance
- No AI system independently conceived any of the five claimed technical concepts
- No other human contributor is identified in this memo as contributing to conception of these specific concepts

Additional factual note:

- Ryan was approached for involvement in a related venture and declined. This memo does not identify him as contributing to conception of this claim family.

## Earliest Evidence of Conception

### Implementation timeline from local git history

- 2026-04-06T20:38:12-07:00 - initial project scaffold
- 2026-04-06T21:39:54-07:00 - API gateway and LLM connectors
- 2026-04-06T22:06:31-07:00 - frontend dashboard
- 2026-04-07T05:19:41-07:00 - audit-related fixes
- 2026-04-08 - validation-study design and calibration workflow
- 2026-04-09 - adversarial audit and scoring-mode separation work

These are implementation dates, not conception dates.

### Conception evidence predating April 2026

- TKS v3.x through v6.1 manuscripts
- TKS v7.4 Full Corrected manuscript
- TKS v7.4 Referee-Defensible manuscript
- pre-April-2026 project materials and related repo history, if confirmed

## Open Questions for Counsel

1. Confirm that the inventor name and residence used in the eventual filing match legal records.
2. Should the calibration and evidence subsystems remain in the same claim family as the core wrap pipeline, or be split?
3. Which contributions constitute claim-critical conception versus later implementation?

## Preliminary Human Inventor Position

- **Sole inventor:** Little Henderson
- **Residence:** Redmond, Washington, United States

This position is subject to counsel's claim-by-claim inventorship review.

## Signature Block

- **Name:** Little Henderson
- **Date:** April 12, 2026
- **Confirmation:** I confirm that this memo reflects my current factual understanding of the Noetic Compass claim family. AI tools were used as implementation assistants under my direction. The claim-family concepts described above were human-conceived design decisions to the best of my current knowledge.
