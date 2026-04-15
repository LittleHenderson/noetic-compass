# CAS-Native Inventorship Memo Working Draft

Prepared on 2026-04-12 from project materials in `C:\Users\wakil\OneDrive\Desktop\tksCAS`.

This is a factual working memo for counsel review. It is not a legal conclusion and not a filed document.

## Invention Family

This memo covers the **CAS-native architecture** claim family only:

- fixed 40-slot latent cognitive-state architecture
- slot-level domain-descent attention
- structured supervision from CAS labels
- engine-aligned evaluation through the Rust CAS engine
- related prerequisite gating and auxiliary heads as embodiments

It is not intended to claim the entire CAS framework in the abstract.

## Short Description

The CAS-native architecture is a structured neural architecture implemented in `noetic-compass-scaffold/noetic-compass/cas-native`. It uses a fixed 40-slot latent cognitive-state representation, a slot-level domain-descent attention mechanism, structured supervision from labeled CAS scores, and an evaluation bridge into the Rust CAS engine.

## Claimed Technical Concepts

1. Fixed 40-slot latent cognitive-state architecture
2. Slot-level domain-descent attention over explicit cognitive-state slots
3. Structured supervision path from CAS labels into a 40-state target distribution
4. Engine-aligned evaluation path from model outputs into the Rust CAS engine
5. Combined architecture with prerequisite gating and auxiliary heads under a structured latent-state workflow

## Human Conception by Concept

### Concept 1

- Technical concept: Fixed 40-slot latent cognitive-state architecture
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - selected the fixed 40-slot cognitive-state bank rather than a generic hidden-state design
- Approximate conception timing:
  - current working position: pre-April-2026, based on the underlying framework that informed the implementation
- Supporting evidence:
  - `ip/CAS_NATIVE_ARCHITECTURE_PROVISIONAL_DISCLOSURE.md`
  - `ip/cas_native_provisional_package/CAS_NATIVE_PROVISIONAL_APPLICATION_DRAFT.md`
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/cas_native_model.py`
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/embedding.py`

### Concept 2

- Technical concept: Slot-level domain-descent attention over explicit cognitive-state slots
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - directed the shift from token-position tiling to explicit slot-level aggregation and slot attention
  - directed domain-ordered slot masking and feedback logic
- Approximate conception timing:
  - current working position: during the April 2026 architecture remediation cycle
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/domain_descent.py`
  - `noetic-compass-scaffold/noetic-compass/cas-native/tests/test_domain_descent.py`

### Concept 3

- Technical concept: Structured supervision path from CAS labels into a 40-state target distribution
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - directed use of `cas_scores` to build target cognitive-state distributions rather than using only generic next-token loss
- Approximate conception timing:
  - current working position: during the April 2026 implementation/remediation cycle
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/cas-native/training/trainer.py`
  - `noetic-compass-scaffold/noetic-compass/cas-native/training/data_pipeline.py`

### Concept 4

- Technical concept: Engine-aligned evaluation path from model outputs into the Rust CAS engine
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - directed the interface from learned 40-state outputs into PyO3/Rust engine scoring
  - directed use of the formal scoring engine rather than a local approximation
- Approximate conception timing:
  - current working position: during the April 2026 implementation/remediation cycle
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate.py`
  - `noetic-compass-scaffold/noetic-compass/cas-engine/src/python_bindings.rs`
  - `noetic-compass-scaffold/noetic-compass/cas-engine/src/scoring/mod.rs`

### Concept 5

- Technical concept: Combined architecture with prerequisite gating and auxiliary heads under a structured latent-state workflow
- Human contributor(s): Little Henderson
- Human contribution to conception:
  - integrated prerequisite gating, inversion detection, proposition scoring, and LM outputs around the structured slot bank
- Approximate conception timing:
  - current working position: during the April 2026 implementation cycle, with some aspects derived from earlier framework work
- Supporting evidence:
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/rpm_gate.py`
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/topos_reasoner.py`
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/fractal_attention.py`
  - `noetic-compass-scaffold/noetic-compass/cas-native/model/cas_native_model.py`

## Role of AI Assistance

### AI systems used

- Claude (Anthropic), including Claude Code
- Codex (OpenAI)
- Gemini (Google)

### What the AI was used for

- code implementation of human-specified architecture
- adversarial auditing of the architecture
- architecture remediation under human direction
- test generation and verification

### Human decisions that controlled the CAS-native claim family

- Little Henderson conceived the fixed 40-slot architecture used in this claim family.
- Little Henderson specified that the state space should be the open probability simplex.
- Little Henderson specified that domain descent should follow the structured domain ordering reflected in the claim family.
- Little Henderson specified RPM section-retraction semantics as part of the underlying formal orientation informing the gate logic.
- Little Henderson directed the shift from token-position tiling to explicit 40-slot architecture after audit revealed the tiling approach was not faithful to the intended structure.
- Little Henderson directed that training must use real CAS labels rather than uniform targets.
- Little Henderson directed integration with the Rust CAS engine for evaluation rather than a local approximation.
- Little Henderson directed honest labeling of neural approximations versus formal CAS implementations.

### Human-chosen, rejected, or reshaped technical decisions

- Chosen by human:
  - 40-slot architecture over generic hidden states
  - open-simplex embedding over unconstrained latent vectors
  - Fisher-Rao-based drift loss
  - section-retraction-oriented RPM gate framing
- Rejected by human:
  - token-position tiling for domain descent
  - uniform 1/40 training targets
  - local evaluator approximations in place of Rust-engine scoring
- Reshaped by human:
  - topos reasoner labeled as a neural approximation rather than formal categorical reasoning
  - fractal attention labeled as an inspired heuristic rather than a direct formal law

## Contributions That Should Not Count as Inventorship by Themselves

The following are treated here as implementation-only or non-conception contributions:

- ordinary coding to a preselected architecture
- refactoring
- testing support
- copyediting or documentation polish
- AI-generated text or code without human conception of the claimed technical feature

This memo currently identifies no additional human contributor whose role was implementation-only or editorial-only.

## Earliest Evidence of Conception

Known evidence visible from this workspace:

- local repo history in `noetic-compass-scaffold/noetic-compass` begins on `2026-04-06`
- early commits include scaffold, scoring engine, API, and dashboard work on `2026-04-06`
- current CAS-native and CAS-engine implementations exist in the workspace and are reflected in the patent materials
- these are implementation dates, not necessarily conception dates

Additional evidence identified for counsel review:

- pre-April-2026 authored framework materials and manuscripts
- architecture notes describing the 40-slot design
- any earlier notes showing the slot-level attention concept and engine-integration decision

## Open Questions for Counsel

- Which CAS-native modules are claim-critical versus optional embodiments?
- Does the compiler/toolchain linkage belong in this architecture family or a separate family?
- Which contributions constitute conception of the structured neural architecture rather than implementation of an already chosen design?

## Current Working View of Claim-Critical Elements

The strongest current claim-family elements appear to be:

- 40-slot cognitive-state architecture
- slot-level domain-descent attention over cognitive-state slots rather than token-position tiling
- structured CAS-label supervision
- Rust-engine evaluation integration

Additional but likely narrower embodiments:

- fractal attention head
- proposition/topos head
- RPM prerequisite gate implementation details
- Fisher-Rao loss implementation details

## Preliminary Human Inventor Position

Current working position for this claim family:

- Sole inventor: Little Henderson
- Residence: Redmond, Washington, United States

This position is subject to counsel's claim-by-claim inventorship review.

## Signature Block

- Name: Little Henderson
- Date: April 12, 2026
- Confirmation:
  - I confirm that this memo reflects my current factual understanding of the CAS-native claim family.
  - AI tools were used as implementation assistants under my direction.
  - The claim-family architecture decisions described above were human-conceived design decisions to the best of my current knowledge.
