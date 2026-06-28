---
title: "CAS-Native AI Global Public Launch Timeline"
subtitle: "Gated Roadmap From Research Prototype to Public LLM-Style Usage"
author: "Noetic Compass"
date: "2026-04-29"
---

# CAS-Native AI Global Public Launch Timeline

## Gated Roadmap From Research Prototype to Public LLM-Style Usage

**Starting point.** April 29, 2026.

**Purpose.** This document gives stakeholders a practical launch roadmap for CAS-Native AI as a public LLM-style system. It explains the major intervals, what must be built, what must be proven, and what should not be claimed too early.

**Important framing.** This is a gated roadmap, not a guaranteed calendar promise. CAS-Native should move to wider release only when its validation, safety, infrastructure, and product-readiness gates clear.

**Current status summary.** CAS has a working compiler, a CAS Synthetic Data Generator, recoverable Level 3 prompt data, and an early CAS-Native reranker path. The strongest latest result is the patched recoverable reranker run: 21 / 30 exact top-1, 26 / 30 top-5, 2.89 mean rank, 28 / 30 slot-match, and 30 / 30 compiler-valid outputs on the current 30-item evaluation slice.

# Executive Timeline

| Phase | Approximate interval from Apr 29, 2026 | Calendar window | Primary goal | Release posture |
|---|---:|---|---|---|
| Phase 0 | Current state | Apr 2026 | Research prototype and evidence base | Internal only |
| Phase 1 | 0-30 days | May 2026 | Evaluation hardening and meta_logic diagnosis | Internal / technical demos |
| Phase 2 | 1-3 months | Jun-Jul 2026 | Closed alpha CAS-Native assistant | Invite-only research alpha |
| Phase 3 | 3-6 months | Aug-Oct 2026 | Private beta with product workflows | Limited trusted users |
| Phase 4 | 6-9 months | Nov 2026-Jan 2027 | Public research preview | Public but constrained |
| Phase 5 | 9-12 months | Feb-Apr 2027 | Public beta API and app | Broader public usage |
| Phase 6 | 12-18 months | May-Oct 2027 | Global public launch candidate | Production-scale public LLM-style usage |
| Phase 7 | 18-36 months | Nov 2027-Apr 2029 | Multimodal CAS-native platform | Mature ecosystem |

The aggressive path reaches a constrained public research preview in 6-9 months and a public beta in 9-12 months. A credible global public LLM-style launch should be treated as a 12-18 month target unless the validation program outperforms expectations.

# What "Global Public Usage" Means

For stakeholders, "global public usage" should not mean merely putting a chatbot online.

It should mean:

1. **Reliable access.** Users can access CAS-Native through a web app and/or API with stable uptime.
2. **Compiler-grounded output.** CAS expressions are validated before being presented as formal outputs.
3. **Transparent uncertainty.** The system distinguishes exact recovery, likely interpretation, and ambiguous cases.
4. **Safe claims.** It does not present CAS interpretations as diagnosis, therapy, or behavioral certainty.
5. **Multimodal pathway.** Text, CAS notation, diagrams, voice, and visual artifacts can begin routing through a shared CAS representation layer.
6. **Auditability.** Outputs can be inspected, reproduced, scored, and traced to model, compiler, and candidate-selection behavior.

# Phase 0: Current State

## Where CAS-Native Is Today

| Area | Current status |
|---|---|
| CAS compiler | Broad grammar, typed meta-logic, clusters, set operations, diagrams, Rule 4 validation |
| CAS Synthetic Data Generator | Level 2 generator plus Level 3 recoverable prompt pipeline |
| Recoverable dataset | 19,454 compiler-valid Level 3 prompt-to-CAS examples |
| Semantic reranker | Patched run reached 21 / 30 exact top-1 and 26 / 30 top-5 |
| Constrained inference | Candidate-bank and prompt-slot filtering path exists |
| Free-form CAS generation | Not product-ready; model can learn tokens but not reliably assemble grammar alone |
| Public CAS-Native LLM | Not launched yet |

## Main Lesson From Current Work

The right near-term path is not unconstrained generation.

The right path is:

```text
natural-language prompt
  -> recoverable slot extraction
  -> compiler-valid candidate bank
  -> semantic reranker
  -> compiler validation
  -> CAS expression + explanation + diagram
```

This is closer to a structured reasoning engine than a standard chatbot.

# Phase 1: Evaluation Hardening

**Interval.** 0-30 days from April 29, 2026. Target window: May 2026.

**Goal.** Turn the promising 30-item result into a defensible evaluation program.

## Build Items

| Workstream | What needs to happen | Why it matters |
|---|---|---|
| meta_logic diagnosis | Find why meta_logic lags at 2 / 5 exact and mean rank 15.67 | It is the only major structural laggard |
| Larger held-out eval | Expand from 30 examples to 300-600 examples | 30 examples is too small for serious claims |
| Paraphrase holdout | Test prompts in styles not seen during training | Detects shallow prompt-format overfitting |
| Candidate-bank audit | Measure target scoreability and filter attrition by bucket | Ensures correct answer is available to reranker |
| Error taxonomy | Label failures by candidate missing, filter error, semantic confusion, type ambiguity | Makes fixes targeted instead of speculative |

## Gates to Clear

| Gate | Minimum target |
|---|---:|
| Compiler-valid outputs | 100% on constrained path |
| Exact top-1 on 300+ heldout examples | >= 60% |
| Ground-truth top-5 on 300+ heldout examples | >= 85% |
| Bucket with worst top-5 | >= 70% |
| meta_logic target scoreability | >= 95% |
| Paraphrase holdout degradation | Less than 15 percentage points |

## Deliverable

A stakeholder-grade validation report:

```text
CAS-Native Recoverable Prompt Evaluation v1
sample size: 300-600
by-bucket metrics
failure taxonomy
overfit checks
recommended release posture
```

# Phase 2: Closed Alpha CAS-Native Assistant

**Interval.** 1-3 months from April 29, 2026. Target window: June-July 2026.

**Goal.** Build a closed alpha assistant that can translate, explain, and teach CAS under controlled conditions.

## Core Product Capabilities

| Capability | User-facing behavior | Technical basis |
|---|---|---|
| Natural language to CAS | User describes a structure; assistant returns CAS notation | Recoverable prompt pipeline + reranker |
| CAS to natural language | User enters expression; assistant explains it | Compiler AST + natural-language mirror templates |
| CAS diagrams | User gets visual structure diagrams | Compiler diagram payload + renderer |
| Invalid expression help | User sees why expression failed and how to fix it | Parser/typechecker error explanations |
| Tutorial mode | Guided learning path from basic states to meta-logic | Level 3 examples + glossary/dictionary |

## Alpha Restrictions

The alpha should not claim:

1. Clinical diagnosis.
2. Behavior prediction.
3. Autonomous therapy.
4. General human mind-reading.
5. Full frontier-model equivalence.

It should claim:

1. Formal CAS translation assistance.
2. Compiler-grounded notation validation.
3. Structured cognitive representation.
4. Early CAS-native learning and explanation.

## Gates to Clear

| Gate | Minimum target |
|---|---:|
| Alpha user tasks completed without crash | >= 95% |
| CAS compiler validation for formal outputs | 100% where formal output is claimed |
| User-rated explanation clarity | >= 4 / 5 in guided alpha |
| Ambiguous prompt handling | Clarifying question or multiple candidates, not false certainty |
| P0 safety issues | 0 open |

# Phase 3: Private Beta With Product Workflows

**Interval.** 3-6 months from April 29, 2026. Target window: August-October 2026.

**Goal.** Move from a technical assistant to repeatable workflows for real users.

## Product Workflows

| Workflow | What the user does | CAS-Native output |
|---|---|---|
| Learn CAS | Works through guided examples | Explanations, diagrams, correction feedback |
| Analyze an idea | Enters a thought or project note | CAS interpretation + graph placement |
| Compare interpretations | Asks why one CAS expression differs from another | Side-by-side structural explanation |
| Build recipes | Describes outcome ingredients | Production expression + yield-style explanation |
| Explore clusters | Groups Noetics/states | Typed set/cluster diagrams |

## Infrastructure Work

| Infrastructure area | Required work |
|---|---|
| Authentication | User accounts and access control |
| Logging | Privacy-aware output/error telemetry |
| Model routing | Separate compiler, reranker, and language explanation paths |
| Caching | Candidate-bank and compiler-result caching |
| Observability | Per-bucket accuracy and failure dashboards |
| Abuse controls | Rate limits and safety filters |

## Gates to Clear

| Gate | Minimum target |
|---|---:|
| Private beta users | 50-200 trusted users |
| Formal output compiler-validity | 100% on compiler-routed formal claims |
| Task success rate | >= 80% |
| Average latency for compiler/reranker path | < 5 seconds for common queries |
| Ambiguous prompt false-certainty incidents | < 2% |

# Phase 4: Public Research Preview

**Interval.** 6-9 months from April 29, 2026. Target window: November 2026-January 2027.

**Goal.** Public access with explicit research-preview limits.

## What Ships

1. Public CAS compiler.
2. Natural-language-to-CAS assistant in constrained mode.
3. CAS-to-natural-language mirror explanations.
4. Diagram rendering.
5. Basic Idea Atlas integration.
6. Documentation, tutorials, glossary, and examples.
7. Public safety and limitations page.

## What Does Not Ship Yet

1. Open-ended behavioral prediction.
2. Clinical/mental-health interpretation.
3. Unreviewed autonomous advice.
4. Unlimited API usage.
5. Claims of human-level psychological understanding.

## Gates to Clear

| Gate | Minimum target |
|---|---:|
| Public uptime | >= 99% for preview window |
| Formal CAS outputs compiler-valid | 100% where formal output is claimed |
| Heldout exact top-1 | >= 70% on recoverable prompts |
| Heldout top-5 | >= 90% on recoverable prompts |
| Human explanation quality | >= 4 / 5 average |
| Published limitation policy | Complete |

# Phase 5: Public Beta API and App

**Interval.** 9-12 months from April 29, 2026. Target window: February-April 2027.

**Goal.** Broader public usage with developer/API access and scaled infrastructure.

## API Surface

| Endpoint class | Function |
|---|---|
| Compile | Validate CAS expression, return AST, type, bytecode, diagram payload |
| Translate | Natural language to CAS candidates |
| Explain | CAS expression to natural-language explanation |
| Diagram | CAS expression to visual graph/containment/radial layout |
| Rerank | Rank compiler-valid candidates against a prompt |
| Tutorial | Return guided examples and feedback |
| Idea Atlas | Capture and map ideas |

## Production Infrastructure

| Need | Requirement |
|---|---|
| Model serving | GPU or optimized CPU service for reranker/LLM paths |
| Compiler service | Low-latency deterministic parser/typechecker |
| Storage | User histories, idea graphs, audit logs |
| Privacy | Clear data retention and deletion policy |
| Versioning | CAS grammar version and model version attached to outputs |
| Monitoring | Accuracy drift, latency, error rates, safety events |

## Gates to Clear

| Gate | Minimum target |
|---|---:|
| API availability | >= 99.5% |
| Formal output validation | 100% compiler-valid formal outputs |
| Public beta satisfaction | >= 4 / 5 from target users |
| Security review | Complete |
| Privacy review | Complete |
| Cost per query | Sustainable under pricing model |

# Phase 6: Global Public Launch Candidate

**Interval.** 12-18 months from April 29, 2026. Target window: May-October 2027.

**Goal.** Public LLM-style CAS-Native usage at meaningful scale.

## Launch Candidate Capabilities

| Capability | Expected launch-candidate behavior |
|---|---|
| Conversational CAS tutoring | Explains notation, corrects mistakes, teaches progressively |
| Natural-language CAS translation | Converts recoverable prompts into validated CAS expressions |
| CAS-native explanation | Maps every expression part to plain-language meaning |
| Diagram-native output | Shows graph, containment, radial, recipe, and dependency diagrams |
| Voice input | Speech-to-text routed into CAS interpretation |
| Voice output | Natural-language explanations read aloud |
| Vision input, limited | Images or diagrams can be described and mapped into CAS-relevant structures where appropriate |
| Multimodal output | Text, CAS notation, diagrams, and possibly sonification from shared CAS representation |
| API integration | Developers can build CAS-aware tools |
| Audit trail | Outputs include model/compiler/version metadata |

## Global Launch Gates

| Gate | Minimum target |
|---|---:|
| Formal output compiler-validity | 100% for formal CAS claims |
| Recoverable prompt exact top-1 | >= 80% on large heldout |
| Recoverable prompt top-5 | >= 95% on large heldout |
| Worst-bucket top-5 | >= 85% |
| Ambiguity handling | Clarifies or offers alternatives in >= 95% of ambiguous test cases |
| Production uptime | >= 99.9% |
| Security/privacy review | Passed |
| Public documentation | Complete |
| Support and incident process | Operational |

# Phase 7: Mature Multimodal CAS-Native Platform

**Interval.** 18-36 months from April 29, 2026. Target window: November 2027-April 2029.

**Goal.** CAS-Native becomes a platform where all modalities can route through shared CAS structure.

## What "All Modalities Operating in All Modalities" Means

The long-term architecture should not treat text, image, voice, diagram, and audio as separate products.

It should treat CAS as the shared intermediate representation:

```text
speech -> text -> CAS -> explanation
text -> CAS -> diagram
CAS -> natural language -> voice
image -> scene/diagram features -> CAS hypothesis
CAS -> radial diagram -> sonification
conversation history -> CAS memory graph -> future retrieval
```

## Mature Capability Targets

| Modality | Input | Output | CAS role |
|---|---|---|---|
| Text | Prompts, notes, dialogue | Explanations, summaries, CAS translations | Main interaction channel |
| Symbolic notation | CAS expressions | AST, validation, diagrams, explanations | Formal language channel |
| Diagram | User views or edits structure | Graph/containment/radial/recipe views | Visual reasoning channel |
| Voice | Spoken thoughts/questions | Spoken explanations | Accessibility and mobile capture |
| Image | Diagrams, sketches, screenshots, visual artifacts | CAS hypotheses and structured descriptions | Vision-to-structure bridge |
| Audio/sonification | Temporal Cognitive Score | Auditory representation | Pattern perception channel |
| Memory graph | Prior user ideas and CAS states | Retrieval, comparison, longitudinal maps | Continuity channel |

# Risk Register

| Risk | Why it matters | Mitigation |
|---|---|---|
| Overfitting to recoverable prompt style | Model may perform well only on one template style | Paraphrase holdouts and external eval prompts |
| Candidate-bank gaps | Reranker cannot select missing ground truth | Scoreability audits and bank expansion |
| meta_logic lag | Advanced constructs may remain weak | Local diagnosis before more GPU training |
| Overclaiming | Stakeholder trust can be damaged | Use precise current/expected/hoped language |
| Latency | Public users will not tolerate slow responses | Cache compiler/candidates and optimize reranker service |
| Privacy | Idea Atlas and cognitive notes are sensitive | Data minimization, deletion, consent, encryption |
| Safety misuse | Users may treat CAS as diagnosis | Clear disclaimers and safety policy |
| Cost scaling | Public LLM usage can become expensive | Tiered model routing and compiler-first paths |

# Decision Points

## Decision Point 1: After Phase 1

Question: Did the larger heldout evaluation confirm the patched reranker result?

If yes, proceed to closed alpha.

If no, do not launch. Diagnose data/candidate/filter failure.

## Decision Point 2: After Phase 2

Question: Can real users complete guided CAS tasks without expert handholding?

If yes, proceed to private beta.

If no, improve tutorial, explanations, and error recovery.

## Decision Point 3: After Phase 3

Question: Are workflows valuable outside the development team?

If yes, proceed to public research preview.

If no, narrow the product wedge.

## Decision Point 4: Before Phase 6

Question: Is the system safe, useful, stable, and honest enough for global public usage?

If yes, launch candidate.

If no, keep it in public beta.

# Recommended Stakeholder Framing

Use this short framing:

> CAS-Native AI is being built as a compiler-grounded cognitive language model. The launch plan is intentionally gated: first prove formal recovery and explanation, then closed alpha, then private beta, then public research preview, then global launch. The goal is not to release another generic chatbot. The goal is to release an AI system that can translate, validate, explain, diagram, and eventually reason across CAS structures in text, symbols, voice, vision, diagrams, and memory.

# Practical Next Step

The immediate next step is not more public marketing.

The immediate next step is:

1. Terminate any idle GPU pod.
2. Diagnose the meta_logic bucket locally.
3. Patch candidate coverage or filtering if needed.
4. Run a larger heldout recoverable evaluation.
5. Only then move toward closed alpha.

