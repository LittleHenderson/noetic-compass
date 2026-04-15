# Noetic Compass Inventorship Memo Working Draft

Prepared on 2026-04-12 from project materials in `C:\Users\wakil\OneDrive\Desktop\tksCAS`.

This is a factual working memo for counsel review. It is not a legal conclusion and not a filed document.

## Invention Family

This memo covers the **Noetic Compass** claim family only:

- staged AI-response assessment
- scoring-mode separation and provenance
- external scorer separation from the generator
- human calibration and reconciliation workflows
- validation evidence capture, review, and benchmark separation

It is not intended to claim the entire CAS/TKS framework in the abstract.

## Short Description

The Noetic Compass system is a multi-stage AI assessment platform implemented in the `noetic-compass-scaffold/noetic-compass` workspace. It receives a prompt, routes it through a selected generator, evaluates the resulting output through a staged scoring pipeline, records scoring provenance, and presents the results together with calibration, benchmark, and evidence-review tooling.

## Claimed Technical Concepts

1. Multi-stage wrap pipeline for AI response assessment
2. Explicit scoring-mode separation with provenance-aware result reporting
3. External scorer resolution distinct from the generator when available
4. Human calibration and reconciliation workflow for disputed assessment items
5. Validation evidence subsystem with separated benchmark tables and error-case logging

## Human Conception by Concept

### Concept 1

- Technical concept: Multi-stage wrap pipeline for AI response assessment
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - selected the staged wrap structure as a core system concept
  - defined the ordered pipeline shape used in the implementation
- Approximate conception timing:
  - conceived before the April 2026 implementation phase
  - implementation visible in local repo history beginning 2026-04-06
- Supporting evidence:
  - `ip/NOETIC_COMPASS_PROVISIONAL_DISCLOSURE.md`
  - `ip/noetic_compass_provisional_package/NOETIC_COMPASS_PROVISIONAL_APPLICATION_DRAFT.md`
  - `noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py`
  - `noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py`

### Concept 2

- Technical concept: Explicit scoring-mode separation with provenance-aware result reporting
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - directed separation of `heuristic_fallback`, `secondary_llm`, and `self_reported`
  - directed result-level provenance fields for scoring method, scorer provider, and scorer model
- Approximate conception timing:
  - current working date: 2026-04-09 during the adversarial audit/remediation cycle
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/api/models.py`
  - `noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py`
  - `noetic-compass-scaffold/noetic-compass/dashboard/src/pages/AssessmentPage.tsx`
  - `ip/NOETIC_COMPASS_PROVISIONAL_DISCLOSURE.md`

### Concept 3

- Technical concept: External scorer resolution distinct from the generator when available
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - specified that an external scorer should be preferred over self-grading when available
  - directed fallback handling and explicit scorer provenance recording
- Approximate conception timing:
  - current working date: 2026-04-09 during the same audit/remediation cycle
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py`
  - `noetic-compass-scaffold/noetic-compass/validation/VALIDATION_PROTOCOL.md`
  - benchmark separation logic in the validation subsystem

### Concept 4

- Technical concept: Human calibration and reconciliation workflow for disputed assessment items
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - specified queueing of disputed items
  - specified comparison of human panel scores to machine scores
  - specified reconciliation disposition, notes, and optional reconciled snapshots
- Approximate conception timing:
  - current working date: 2026-04-08 as part of validation-study design
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/api/validation/calibration_sessions.py`
  - `noetic-compass-scaffold/noetic-compass/api/routes/validation.py`
  - `noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationPage.tsx`

### Concept 5

- Technical concept: Validation evidence subsystem with separated benchmark tables and error-case logging
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - specified separate storage and presentation of scorer-agreement cases, benchmark-suite runs, and false-positive/false-negative cases
  - specified trend and export tooling by provider/model and scoring mode
- Approximate conception timing:
  - current working date: 2026-04-08
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/api/validation/evidence.py`
  - `noetic-compass-scaffold/noetic-compass/api/routes/validation.py`
  - `noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationLeaderboardPage.tsx`

## Role of AI Assistance

### AI systems used

- Claude (Anthropic), including Claude Code
- Codex (OpenAI)
- Gemini (Google)

### What the AI was used for

- code implementation from human-specified architecture
- document drafting from human-specified outlines and content
- code auditing and bug detection
- testing and test generation
- architecture discussion and feedback

### Human decisions that controlled the Noetic Compass claim family

- Little Henderson conceived the underlying human-directed framework that informed this claim family before AI-assisted implementation.
- Little Henderson directed the staged wrap pipeline shape used in Noetic Compass.
- Little Henderson directed separation of scoring modes after adversarial audit revealed self-scoring risk.
- Little Henderson directed use of an external scorer path distinct from the generator.
- Little Henderson directed the human calibration workflow and the validation evidence structure.
- Little Henderson directed the shift to research-prototype framing rather than overclaiming validated assessment science.

### Human-chosen, rejected, or reshaped technical decisions

- Chosen by human:
  - dual-scorer architecture after audit revealed self-scoring bias
  - separate benchmark tables by scoring mode
  - research-prototype framing over production-certification framing
- Rejected by human:
  - model-as-judge self-scoring as a default stakeholder-facing mode
  - synthetic validation labels in place of real human labeling
  - uncritical external AI assessments that missed serious code issues
- Reshaped by human:
  - public terminology and product framing around CAS/TKS concepts

## Contributions That Should Not Count as Inventorship by Themselves

The following are treated here as implementation-only or non-conception contributions:

- AI-assisted code generation, drafting, editing, and testing under human direction
- bug fixing or refactoring without conception of the claimed technical feature
- ordinary UI polishing or copyediting

Additional factual note:

- Ryan Wiese was approached for involvement and declined; this memo does not identify him as contributing to conception of the claim-family concepts listed above.

## Earliest Evidence of Conception

Known evidence visible from this workspace:

- local repo history shows implementation activity beginning on `2026-04-06` in `noetic-compass-scaffold/noetic-compass`
- early commit history includes:
  - `2026-04-06T20:38:12-07:00` initial scaffold
  - `2026-04-06T21:39:54-07:00` API gateway + connectors
  - `2026-04-06T22:06:31-07:00` frontend dashboard
  - `2026-04-07T05:19:41-07:00` audit-related fixes
- these are implementation dates, not necessarily conception dates

Additional evidence identified for counsel review:

- TKS v3.x through v6.1 manuscripts
- `TKS_v7_4_FULL_CORRECTED.pdf`
- `TKS_v7_4_REFEREE_DEFENSIBLE (1).pdf`
- pre-April-2026 project sites and related repo history, if confirmed

## Open Questions for Counsel

- Confirm that the filing name and residence used in the eventual application match the inventor's legal records.
- Confirm whether the calibration and evidence subsystems should remain in the same inventive family as the core wrap pipeline.
- Confirm which contributions are claim-critical conception versus later implementation.

## Preliminary Human Inventor Position

Current working position for this claim family:

- Sole inventor: Little Henderson
- Residence: Redmond, Washington, United States

This position is subject to counsel's claim-by-claim inventorship review.

## Signature Block

- Name: Little Henderson
- Date: April 12, 2026
- Confirmation:
  - I confirm that this memo reflects my current factual understanding of the Noetic Compass claim family.
  - AI tools were used as implementation assistants under my direction.
  - The claim-family concepts described above were human-conceived design decisions to the best of my current knowledge.
