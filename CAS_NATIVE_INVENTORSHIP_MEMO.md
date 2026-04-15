# CAS-Native Inventorship Memo

Prepared on April 12, 2026 by Little Henderson.

This is a factual memo for counsel review. It is not a legal conclusion and not a filed document.

## Invention Family

This memo covers the **CAS-Native architecture** claim family only:

- fixed 40-slot latent cognitive-state architecture
- slot-level domain-descent attention
- structured supervision from CAS labels
- engine-aligned evaluation through the Rust CAS engine
- related prerequisite gating and auxiliary heads as embodiments

It is not intended to claim the entire CAS framework in the abstract.

## Short Description

The CAS-Native architecture is a structured neural architecture implemented in PyTorch. It uses a fixed 40-slot latent cognitive-state representation, a slot-level domain-descent attention mechanism enforcing ordered information flow across explicit cognitive-state slots, structured supervision from labeled CAS assessment scores mapped to 40-state target distributions, and an evaluation bridge into the Rust CAS scoring engine via PyO3.

## Claimed Technical Concepts

1. Fixed 40-slot latent cognitive-state architecture
2. Slot-level domain-descent attention over explicit cognitive-state slots
3. Structured supervision path from CAS labels into a 40-state target distribution
4. Engine-aligned evaluation path from model outputs into the Rust CAS engine
5. Combined architecture with prerequisite gating and auxiliary heads under a structured latent-state workflow

## Human Conception by Concept

### Concept 1

- **Technical concept:** Fixed 40-slot latent cognitive-state architecture
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Conceived the use of a fixed 40-slot cognitive-state bank as the explicit latent structure for a neural architecture, rather than using generic hidden states
  - Selected those slots based on the underlying framework that informed the architecture
- **Approximate conception timing:**
  - The underlying structured ontology predates the April 2026 implementation
  - The specific decision to use those states as fixed neural architecture slots was conceived before the April 2026 implementation phase
- **Supporting evidence:**
  - `cas-native/model/cas_native_model.py`
  - `cas-native/model/embedding.py`
  - related pre-April-2026 framework materials

### Concept 2

- **Technical concept:** Slot-level domain-descent attention over explicit cognitive-state slots
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified that domain descent should follow the ordered domain structure informing the architecture
  - Directed the shift from token-position tiling to explicit slot-level aggregation and slot attention after audit showed token-position tiling was not faithful to the intended structure
  - Specified domain-ordered slot masking and feedback logic
- **Approximate conception timing:**
  - The ordered domain concept predates the April 2026 implementation
  - The specific slot-level neural implementation was conceived and directed during the April 2026 architecture remediation cycle
- **Supporting evidence:**
  - `cas-native/model/domain_descent.py`
  - `cas-native/tests/test_domain_descent.py`
  - audit materials identifying the token-tiling issue

### Concept 3

- **Technical concept:** Structured supervision path from CAS labels into a 40-state target distribution
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified that training should use real CAS assessment scores to build target cognitive-state distributions rather than relying only on generic next-token loss or uniform targets
  - Directed this correction after audit showed the original training loop was not using scored CAS data properly
- **Approximate conception timing:**
  - Conceived during the April 2026 architecture design and remediation cycle
- **Supporting evidence:**
  - `cas-native/training/trainer.py`
  - `cas-native/training/data_pipeline.py`
  - audit materials identifying the training-target problem

### Concept 4

- **Technical concept:** Engine-aligned evaluation path from model outputs into the Rust CAS engine
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Specified that the learned model's outputs should be evaluated by the formal Rust CAS scoring engine rather than a local approximation
  - Directed the interface from learned 40-state outputs into PyO3/Rust engine scoring
- **Approximate conception timing:**
  - Conceived during the April 2026 architecture design and remediation cycle
- **Supporting evidence:**
  - `cas-native/evaluation/evaluate.py`
  - `cas-engine/src/python_bindings.rs`
  - `cas-engine/src/scoring/mod.rs`

### Concept 5

- **Technical concept:** Combined architecture with prerequisite gating and auxiliary heads under a structured latent-state workflow
- **Human contributor:** Little Henderson
- **Human contribution to conception:**
  - Integrated prerequisite gating, inversion detection, proposition scoring, and fractal-inspired attention around the structured 40-slot state bank
  - Directed the use of section-retraction-oriented RPM semantics as part of the gate framing that informed the implementation
- **Approximate conception timing:**
  - The underlying structures predate the April 2026 implementation
  - The specific neural architecture integration was conceived during the April 2026 implementation cycle
- **Supporting evidence:**
  - `cas-native/model/rpm_gate.py`
  - `cas-native/model/topos_reasoner.py`
  - `cas-native/model/fractal_attention.py`
  - `cas-native/model/cas_native_model.py`

## Role of AI Assistance

### AI systems used

- Claude (Anthropic)
- Codex (OpenAI)
- Gemini (Google)

### What the AI was used for

- code implementation of human-specified architecture
- adversarial auditing of the architecture
- architecture remediation under human direction
- test generation and verification
- documentation drafting under human direction

### Human decisions that controlled the CAS-Native claim family

- Little Henderson conceived the fixed 40-slot architecture used in this claim family.
- Little Henderson specified the structured state-space choice used in the architecture.
- Little Henderson specified the ordered domain-descent behavior reflected in the claim family.
- Little Henderson directed the shift from token-position tiling to explicit 40-slot architecture after audit showed the tiling approach was not faithful to the intended structure.
- Little Henderson directed that training must use real CAS labels rather than uniform targets.
- Little Henderson directed integration with the Rust CAS engine for evaluation rather than a local approximation.
- Little Henderson directed honest labeling of neural approximations versus formal CAS implementations.

### Human-chosen, rejected, or reshaped technical decisions

**Chosen by human:**
- 40-slot architecture over generic hidden states
- structured latent-state supervision over uniform targets
- engine-aligned evaluation over local approximation
- section-retraction-oriented RPM gate framing

**Rejected by human:**
- token-position tiling for domain descent
- uniform 1/40 training targets
- local evaluator approximations in place of Rust-engine scoring

**Reshaped by human:**
- topos reasoner labeled as a neural approximation rather than formal categorical reasoning
- fractal attention labeled as a heuristic rather than a direct formal law

## Contributions That Should Not Count as Inventorship by Themselves

The following are implementation-only or non-conception contributions and do not constitute inventorship by themselves:

- Claude: implementation assistance under human specification
- Codex: auditing and implementation assistance under human direction
- Gemini: feature suggestions and drafting assistance
- No AI system independently conceived any of the five claimed technical concepts
- No other human contributor is identified in this memo as contributing to conception of these specific concepts

Additional factual note:

- Ryan was approached for involvement in a related venture and declined. This memo does not identify him as contributing to conception of this claim family.

## Earliest Evidence of Conception

### Implementation timeline from local git history

- 2026-04-06T20:38:12-07:00 - initial project scaffold
- 2026-04-09 - CAS-Native architecture implementation began
- 2026-04-10 - adversarial audit and remediation cycle

These are implementation dates, not conception dates.

### Conception evidence predating April 2026

- framework manuscripts documenting the structured ontology and related concepts
- related authored materials predating the April 2026 implementation
- pre-April-2026 project sites and related repo history, if confirmed

## Current Working View of Claim-Critical Elements

**Strongest claim-family elements:**
- 40-slot cognitive-state architecture
- slot-level domain-descent attention over cognitive-state slots rather than token-position tiling
- structured CAS-label supervision
- Rust-engine evaluation integration

**Additional but likely narrower embodiments:**
- fractal attention head
- proposition/topos head
- RPM prerequisite gate implementation details
- Fisher-Rao-loss implementation details

## Open Questions for Counsel

1. Which CAS-Native modules are claim-critical versus optional embodiments?
2. Does the compiler/toolchain linkage belong in this architecture family or a separate family?
3. Which contributions constitute conception of the structured neural architecture rather than implementation of an already chosen design?

## Preliminary Human Inventor Position

- **Sole inventor:** Little Henderson
- **Residence:** Redmond, Washington, United States

This position is subject to counsel's claim-by-claim inventorship review.

## Signature Block

- **Name:** Little Henderson
- **Date:** April 12, 2026
- **Confirmation:** I confirm that this memo reflects my current factual understanding of the CAS-Native claim family. AI tools were used as implementation assistants under my direction. The claim-family architecture decisions described above were human-conceived design decisions to the best of my current knowledge.
