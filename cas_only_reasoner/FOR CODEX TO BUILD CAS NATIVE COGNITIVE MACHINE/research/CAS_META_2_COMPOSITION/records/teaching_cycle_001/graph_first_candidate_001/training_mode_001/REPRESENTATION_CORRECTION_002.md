# Graph-first ^6 — representation correction 002 (PREPARED, NOT LAUNCHED)

Owner-directed, 2026-09-09. No reservation, no launch, no GPU work was made
for anything in this document. Attempt 011 is preserved with a narrowed
interpretation (`ATTEMPT_GRAPH_011_RESULT.md`).

## What the inspection measured (pure, train+practice records only)

Tool `tools/graph_training_representation_inspection.py`; evidence
`training_mode_001/representation_inspection_001/inspection.json`. Uses the
REAL tokenizer and the REAL public-record encoding; no sealed splits, no
answers consulted.

| Op | Option token counts | Length spread (median) | Shared by all 3 (median) | Content-unique tokens per option (median) |
|---|---|---|---|---|
| LIST_PARTS | 6–21 | **10.0** | 5.5 | 0.5 |
| FIND_SHARED_PART | 2–2 (always equal) | 0.0 | 1.0 (`[OBS]`) | 1.0 |
| REACHED_VIA | 2–4 | 2.0 | 1.0 (`[OBS]`) | 1.0 |

Decoded samples show why: LIST_PARTS options are `str(list)` renders —
`['idea2', 'idea3']` — so every part costs five framing tokens
(`[ ' , space ' ]`) on top of its name. Sum-pooled differences are therefore
dominated by token count (the owner's "different amounts of text"), and
FIND_SHARED_PART options are `[OBS]` + one tag token each — content-only,
equal-length — yet still exactly ln 3. So FIND_SHARED_PART's flatness is NOT
a representation artifact; it is an unmeasured module-output question.
Problem-side sensitivity (graph-valid synthetic edits): a connector retarget
changes exactly 2 of ~62 problem tokens; a node-content change adds exactly
1 token — the change IS present in the problem sequence, diluted to ~1/62 in
the mean-pooled module input.

## Prepared corrections (code + tests committed; nothing launched)

**A. Content-only option vectors** (`real_framework.GraphLearner`,
`adapter` docs): each option vector now sums ONLY the tokens NOT shared by
all three options. A component present in every option adds the same value
to every score and cancels exactly in the softmax; removing it removes the
count artifact (median spread 10 → 0 for LIST_PARTS framing tokens) and
leaves the part names as the signal. FIND_SHARED_PART is unchanged by
construction (only `[OBS]` was shared). Fail-closed: an option with no
content raises `OPTION_CONTENT_REQUIRED`.

**B. Matched framing comparison** (`aws/graph_training_launch.py`
worker): one candidate copy PER arm, built from the same initial weights
(second module's state cloned from the first), with separate optimizer
state. The future framing comparison is two matched starts, not two
sequential phases.

**C. Module-output measurement** (`cas_meta2/graph_teaching/diagnostic.py`):
per-record module output norm + pairwise cosines across the first few
records — the measurement FIND_SHARED_PART needs. Measurement-only; no
optimizer step.

Test-locked: 95 graph tests pass (content-exclusion behavior, empty-content
fail-closed, per-arm module copies in the rendered worker, module-output
measurement).

## Explicitly NOT done

- `initial_saturation=100.0` is NOT touched. Saturation of the module's two
  tanh stages remains an UNMEASURED HYPOTHESIS.
- No teaching-allowance increase (64 steps / 600 s per condition unchanged).
- No new reservation, no launch, no package build for this correction.

## Proposed next steps (each needs its own authorization)

1. **One GPU diagnostic run** (measurement-only, the existing ln(3)
   diagnostic launcher, one new `$4.00` reservation) on the correction-002
   pipeline: per-record scores, option geometry, and module-output norms/
   cosines — answers whether FIND_SHARED_PART's identical scores come from a
   near-constant module output (measured) and whether the content-only
   options now produce content-driven score differences.
2. **Then, if the diagnostic supports it:** one bounded training pilot with
   corrections A + B (per-arm module copies), same frozen budget, fresh
   evaluation framing — a new owner-signed record and reservation.
