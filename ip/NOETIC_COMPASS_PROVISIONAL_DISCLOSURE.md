# Noetic Compass Provisional Patent Invention Disclosure

Prepared from the implemented `noetic-compass-scaffold/noetic-compass` codebase and the internal patent readiness memo.  
This document is for counsel review and filing triage. It is not legal advice.

## 1. Title

**Noetic Compass: A Computer-Implemented System for Multi-Stage Assessment, Scoring Provenance, Calibration, and Validation of AI-Generated Output**

## 2. Field of the Invention

This invention relates to computer-implemented AI evaluation systems, model scoring pipelines, validation tooling, and human-machine calibration workflows. The invention is specifically directed to a staged assessment system that evaluates a model response across multiple machine-readable dimensions, records scoring provenance, separates benchmark modes, and retains evidence for later calibration and review.

## 3. Background and Problem

Generic AI evaluation systems often reduce a model response to a single scalar score, or they rely on one model grading another without capturing enough provenance to show how the score was produced. That creates several technical and product problems:

1. The score is difficult to audit after the fact.
2. The generation model and scoring model are often conflated.
3. Different scoring modes get mixed into one ranking table, which weakens comparisons.
4. Human disagreement is collected inconsistently or not at all.
5. There is no durable evidence layer for scorer agreement, false positives, false negatives, or benchmark-run history.
6. Report surfaces often overstate certainty or fail to show whether a result is research-stage, heuristic, or externally scored.

The Noetic Compass system addresses those problems with a staged pipeline, explicit scoring provenance, a human calibration loop, and a validation evidence layer. The product is grounded in the current implementation in [api/routes/wrap.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/wrap.py), [api/pipeline/runner.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py), [api/pipeline/stages.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py), [api/routes/validation.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/validation.py), [api/validation/evidence.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/evidence.py), [api/validation/calibration_sessions.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/calibration_sessions.py), [dashboard/src/pages/ValidationPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationPage.tsx), and [dashboard/src/pages/ValidationLeaderboardPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationLeaderboardPage.tsx).

## 4. Summary of the Invention

Noetic Compass is a computer-implemented system that receives an input prompt, routes it through a selected AI generator, scores the resulting response across multiple structured dimensions, computes a composite assessment, and records the provenance of how the assessment was produced.

The system includes:

1. A multi-stage wrap pipeline that analyzes input, computes RPM prerequisite integrity, applies dial adjustments, calls a generator model, scores the generated response, computes domain coherence, scans for inversion patterns, and computes a final composite.
2. Selectable scoring modes, including `heuristic_fallback`, `secondary_llm`, and `self_reported`, with explicit scorer provenance captured in the result.
3. A validation and calibration subsystem that stores human labels, identifies disagreement cases, supports reconciliation sessions, and logs resolution decisions.
4. A validation evidence subsystem that stores scorer agreement cases, benchmark-suite runs, and false-positive/false-negative examples and exposes review, filtering, trend, and export tools.
5. Reporting and dashboard surfaces that show the assessment result, the scoring mode, the scorer provider/model, and research-prototype status so stakeholders can distinguish baseline, external-scorer, and self-reported results.

The invention is not the abstract CAS theory itself. The relevant invention is the implemented assessment, calibration, and validation system.

## 5. System Overview

### 5.1 Primary runtime flow

The wrap path is implemented as a routed API call in [api/routes/wrap.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/wrap.py). It constructs a pipeline runner and passes the request text, scoring mode, and optional scoring-provider/model fields into the pipeline in [api/pipeline/runner.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py).

The runner executes an ordered, multi-stage assessment:

1. Input analysis
2. RPM gate
3. Dial adjustment
4. Base LLM call
5. Operator scoring
6. Domain coherence
7. Inversion scan
8. Output gate / composite computation

Those stages are implemented in [api/pipeline/stages.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py).

### 5.2 Scoring provenance

The system explicitly tracks whether scoring came from:

1. `heuristic_fallback` - deterministic text heuristics
2. `secondary_llm` - a separate assessor model
3. `self_reported` - inline scores emitted by the generator model itself

The runner resolves a scorer connector only when the selected mode requires it, and it records `scoring_method`, `scorer_provider`, and `scorer_model` in the result payload. This is important because the same generator model should not be confused with the evaluator when the user chooses an external scorer.

### 5.3 Validation and evidence

The validation subsystem stores human labels and machine results, supports calibration sessions for disputed items, and builds evidence bundles and trend summaries. The relevant implementation is in [api/routes/validation.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/validation.py), [api/validation/evidence.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/evidence.py), and [api/validation/calibration_sessions.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/calibration_sessions.py).

The dashboard includes dedicated review surfaces in [dashboard/src/pages/ValidationPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationPage.tsx) and [dashboard/src/pages/ValidationLeaderboardPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationLeaderboardPage.tsx).

## 6. Detailed Embodiments

### 6.1 Embodiment: staged single-response assessment

A prompt is submitted to `/wrap`, which selects a generator provider and model, runs the prompt through the wrap pipeline, and returns a structured response object. The output includes:

- operator profile score
- domain coherence
- drive/RPM integrity
- pathway quality
- inversion resistance
- social-engineering resistance signals
- bias-flag count
- composite score
- certification tier
- stage-by-stage provenance
- interpretation text
- fractal analysis summary

This embodiment is useful when an operator wants one input prompt, one generated response, and a multi-dimensional assessment of the response rather than a single opaque score.

In the current implementation, `social_engineering` and `bias_flags` are included as machine-measured heuristic risk signals. They are part of the implemented prototype pipeline, but they should be described in any filing as heuristic or research-stage measurements rather than validated psychological instruments.

### 6.2 Embodiment: selectable scoring mode with explicit scorer separation

The scoring stage does not assume a single mode. The system supports:

- `heuristic_fallback` for a neutral baseline table
- `secondary_llm` with an external scorer provider
- `self_reported` only when the generator itself is allowed to emit scores

The implementation in [api/pipeline/runner.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py) resolves a different scorer when one is available, and [dashboard/src/pages/AssessmentPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/AssessmentPage.tsx) exposes that choice to the user. The scoring method is surfaced back to the UI and to exports so that stakeholders can tell whether a result came from heuristics, an external scorer, or self-reporting.

### 6.3 Embodiment: human-machine calibration queue

The validation page contains a calibration session workflow that shows disputed items, compares panel scores to machine scores, captures a disposition, optionally stores reconciled scores, and saves notes for later review. That workflow is implemented in [api/validation/calibration_sessions.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/calibration_sessions.py), exposed through [api/routes/validation.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/validation.py), and rendered in [dashboard/src/pages/ValidationPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationPage.tsx).

This is not just a label-entry screen. It is a reconciliation workflow for disagreements between human raters and machine scoring.

### 6.4 Embodiment: validation evidence and benchmark separation

The evidence layer stores three distinct categories:

- scorer agreement cases
- benchmark-suite runs
- false-positive / false-negative cases

Evidence is not mixed into one undifferentiated ranking. The leaderboard separates a neutral `heuristic_fallback` table from a `secondary_llm` table with a fixed external scorer. The relevant aggregation, filtering, and export logic is in [api/validation/evidence.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/evidence.py) and the display logic is in [dashboard/src/pages/ValidationLeaderboardPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationLeaderboardPage.tsx).

### 6.5 Embodiment: reporting and stakeholder disclosure

The exported reports and main results surfaces include explicit research-prototype and not-validated language. The dashboard implementation includes this in the main assessment view, validation views, and exports. See [dashboard/src/pages/AssessmentPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/AssessmentPage.tsx), [dashboard/src/pages/ValidationPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationPage.tsx), [dashboard/src/pages/ValidationLeaderboardPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationLeaderboardPage.tsx), [dashboard/src/lib/exportPdf.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/exportPdf.ts), [dashboard/src/lib/exportDocx.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/exportDocx.ts), and [dashboard/src/lib/exportMarkdown.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/exportMarkdown.ts).

## 7. Inputs, Processing, and Outputs

### Inputs

- user prompt text
- selected generator provider and model
- dial configuration
- scoring mode
- optional external scorer provider/model
- human validation labels
- calibration disposition and notes
- benchmark suite definitions and prompt collections

### Processing

- tokenize and analyze the input prompt
- compute RPM prerequisite integrity heuristics
- apply dial adjustments
- call the generator model
- score the generated response using one of the explicit modes
- compute domain averages and inversion-resistance measures
- compute composite output and certification tier
- compute composite output and a tiered research-stage classification (the legacy field name in code may still be `certification`)
- store provenance, evidence, and validation records
- aggregate benchmark summaries and trend data

### Outputs

- staged result object
- composite assessment and tier
- scorer provenance
- human-readable interpretation
- evidence records
- calibration history
- benchmark tables and trends
- exported report formats

## 8. Differentiators Over Generic AI Evaluation Pipelines

The strongest differentiators are technical, not theoretical:

1. The system separates generator, scorer, and human calibration rather than collapsing them into one score path.
2. The system records scoring provenance so the same result can be traced to heuristic, external-LLM, or self-reported scoring.
3. The system separates benchmark modes into distinct tables rather than mixing them into one ranking.
4. The system contains an explicit human reconciliation workflow for disputed items.
5. The system stores scorer-agreement, benchmark-suite, and error-case evidence and exposes trend summaries and export tools.
6. The system displays research-prototype status and not-validated language in the user-facing results and exports.
7. The system uses a staged assessment pipeline rather than a one-shot scalar classifier.

For patent drafting, it is safer to describe the final output as a composite score plus a tiered machine classification than to lean on any one public-facing label.

## 9. Possible Claim Families

These are not final claims. They are candidate claim families for counsel to refine.

### Family 1: Multi-stage AI response assessment with provenance

Independent claim direction: a computer-implemented method that receives a prompt, obtains a generated response, computes multiple structured scores, records the scoring mode and scorer identity, and produces a composite assessment.

Likely dependent claims:

- separate generator and scorer providers
- heuristic fallback mode
- self-reported mode
- explicit provenance output
- composite score plus tier output
- inversion and RPM sub-scores

### Family 2: Separate external scorer mode

Independent claim direction: a method where the generation model and scoring model are different machines, and where the system automatically resolves an external scorer when live providers are available.

Likely dependent claims:

- scorer-provider selection logic
- fallback to heuristics if the external scorer fails
- recording scorer model and provider in the result
- blocking same-provider judging for stakeholder-facing tables

### Family 3: Human-machine calibration workflow

Independent claim direction: a method for identifying disputed prompt-response items, presenting human panel scores alongside machine scores, accepting a reconciliation disposition, and saving a durable calibration record.

Likely dependent claims:

- queue of unresolved disagreements
- panel mean versus machine mean comparison
- optional reconciled score snapshot
- calibration notes and dispositions
- recent reconciliation history

### Family 4: Validation evidence and benchmark separation

Independent claim direction: a method for storing and summarizing scorer-agreement cases, benchmark-suite runs, and false-positive/false-negative cases in separate evidence categories and maintaining separate benchmark tables by scoring mode.

Likely dependent claims:

- provider/model trend summaries
- CSV export of evidence
- benchmark eligibility thresholds
- frozen prompt collections
- resilience against mixing scoring modes in one ranking

### Family 5: Research-prototype reporting surface

Independent claim direction: a reporting system that attaches provenance, validation status, and mode-specific caveats to generated assessment outputs and exports.

Likely dependent claims:

- research prototype notice on assessment and validation pages
- export footers with research-stage notices
- mode-specific wording in report exports

## 10. Alternative Embodiments

Counsel may want to keep these as optional embodiments or dependent claims:

1. Different external scorer providers, including OpenAI, Anthropic, Google, xAI, Meta, DeepSeek, or Qwen, depending on availability.
2. Different prompt collections, benchmark suites, or domain-specific prompt libraries.
3. Alternative storage backends for evidence and calibration records.
4. A different UI surface that exposes the same calibration workflow in a more compact or admin-only form.
5. A non-web client or CLI that produces the same staged assessment and evidence records.
6. Different composite weighting or thresholding functions without changing the underlying separation of scoring, calibration, and evidence capture.
7. Heuristic-only or scorer-only deployments when external providers are unavailable.

## 11. Figures To Draw

Suggested figures for counsel or a later utility filing:

1. System architecture diagram showing generator, scorer, pipeline runner, validation store, and dashboard.
2. Eight-stage wrap pipeline flowchart.
3. Scoring provenance decision tree showing `heuristic_fallback`, `secondary_llm`, and `self_reported`.
4. Human calibration queue and reconciliation flow.
5. Evidence storage and trend aggregation diagram.
6. Benchmark-table separation diagram showing neutral baseline versus external-scorer ranking.
7. Export/report generation flow with research-prototype notices.

## 12. Inventorship and Source-Material Notes

This disclosure is grounded in the implemented repository artifacts, especially:

- [PATENT_READINESS_MEMO.md](C:/Users/wakil/OneDrive/Desktop/tksCAS/PATENT_READINESS_MEMO.md)
- [api/routes/wrap.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/wrap.py)
- [api/pipeline/runner.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py)
- [api/pipeline/stages.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py)
- [api/routes/validation.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/validation.py)
- [api/validation/evidence.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/evidence.py)
- [api/validation/calibration_sessions.py](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/validation/calibration_sessions.py)
- [dashboard/src/pages/AssessmentPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/AssessmentPage.tsx)
- [dashboard/src/pages/ValidationPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationPage.tsx)
- [dashboard/src/pages/ValidationLeaderboardPage.tsx](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/pages/ValidationLeaderboardPage.tsx)
- [dashboard/src/lib/reportData.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/reportData.ts)
- [dashboard/src/lib/exportPdf.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/exportPdf.ts)
- [dashboard/src/lib/exportDocx.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/exportDocx.ts)
- [dashboard/src/lib/exportMarkdown.ts](C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/exportMarkdown.ts)

Inventorship should be confirmed by counsel. This codebase reflects a mix of direct human direction, human code review, and AI-assisted drafting. The patent record should preserve who conceived the core ideas, who reduced them to practice, and when each implementation milestone occurred.

## 13. Open Questions For Patent Counsel

1. Should the first filing be a provisional focused only on Noetic Compass assessment/calibration, or should the CAS-native compiler/toolchain be filed separately?
2. How should the claims be framed to avoid abstract-idea objections while still capturing the concrete pipeline, provenance, and calibration mechanics?
3. Should the theory-level CAS terminology be excluded from the claims entirely and retained only in the specification?
4. What is the earliest public-disclosure date that matters for the U.S. and for foreign filing strategy?
5. Should the external-scorer mode and the calibration/evidence layer be claimed in the same family or split into separate filings?
6. Which portions of the system are best kept as trade secrets rather than disclosed in a filing?
7. What inventor list is appropriate given the combination of human direction and AI-assisted drafting used to develop the codebase and documentation?
8. What supporting exhibits should be attached before filing: diagrams, logs, screenshots, benchmark exports, or example runs?

## 14. Counsel-Ready Takeaway

The most defensible invention here is not an abstract theory of cognition. It is the implemented Noetic Compass system: a staged AI-response assessment pipeline with selectable scoring provenance, human calibration, evidence logging, benchmark separation, and stakeholder-facing disclosure controls.

The patentable value is in the machine workflow and its technical structure.
