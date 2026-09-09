# Graph-first ^6 — representation correction 002 (PREPARED — with the MEASURED root cause, attempt 005)

Owner-directed, 2026-09-09 (three review rounds + one completed measurement).
No reservation or launch was made for anything in this document.
`ATTEMPT_LN3_005_RESULT.md` (result sha `c6822f24…`) MEASURED the earliest
stage where content becomes indistinguishable — before any pooling, before
the module:

> **The frozen encoder's embed lookup returned ONE vector for every token.**
> `embed(token_id)` indexed the projection through a string-keyed token map
> with INTEGER ids, so every token fell back to row 0. Measured: 10 distinct
> tag tokens (different part names included) all have norm
> `0.9902205467224121` and pairwise cosines `0.9999999675` — the identical
> vector. Fixed (ids are vocabulary positions; bounds guard), test-locked.

Everything below remains valid as the SPEC for re-measuring the corrected
pipeline (the count-vs-content question becomes real only now that distinct
tokens map to distinct frozen rows).

## Corrected claims (per the owner's mathematical review — these REPLACE the
first revision's wording)

1. **FIND_SHARED_PART's flatness is NOT explained by answer length — and its
   representation may still be collapsed.** Its options are each 2 tokens
   (`[OBS]` + one tag token): equal length, and sum = 2 × mean (proportional,
   not equal). Equal lengths do not rule out projected-vector collapse: the
   earlier GPU diagnostic measured near-parallel option vectors and
   near-identical scores, and a token-count inspection does not overturn
   those numerical observations. The distinct tag vectors must be measured
   before any blame moves to the ^6 module.
2. **Removing an exactly common contribution cannot, by itself, change which
   answer wins.** For scores `s_i = hᵀ o_i` with the SAME vector `c` removed
   from every option, `s'_i = hᵀ(o_i − c) = s_i − hᵀc`: every score loses
   the same amount, so softmax probabilities, the loss, and the task
   gradient to the module are unchanged in exact arithmetic.
3. **The implementation is per-occurrence and count-respecting.** The
   correction removes EVERY occurrence of any token present in all three
   options. Because shared tokens occur with DIFFERENT counts per option
   (framing tokens appear once per part), the vector removed from one option
   is NOT the same as the vector removed from another. The removal can
   therefore change score differences only through those count differences,
   and the remaining options can still contain different token counts — the
   count effect has not automatically disappeared. Any finite-precision
   benefit (large common contributions removed before summation) is a
   HYPOTHESIS to be measured, not an automatic recovery of information.

**The prepared change is therefore described as: a candidate removal of
shared contributions, whose effect on actual score differences and gradients
remains unmeasured.**

## What the inspection measured (pure, train+practice records only)

Tool `tools/graph_training_representation_inspection.py`; evidence
`training_mode_001/representation_inspection_001/inspection.json` (sha
`3a04dd98…`). REAL tokenizer, REAL public-record encoding; no sealed splits,
no answers consulted.

| Op | Option token counts | Length spread (median) | Shared by all 3 (median) | Unique-to-one tokens per option (median) |
|---|---|---|---|---|
| LIST_PARTS | 6–21 | **10.0** | 5.5 | 0.5 |
| FIND_SHARED_PART | 2–2 (always equal) | 0.0 | 1.0 (`[OBS]`) | 1.0 |
| REACHED_VIA | 2–4 | 2.0 | 1.0 (`[OBS]`) | 1.0 |

LIST_PARTS options are `str(list)` renders, so every part costs five framing
tokens on top of its name — sum-pooled differences are dominated by token
count. FIND_SHARED_PART tags are single units; that only establishes equal
length, NOT distinct projected vectors. Problem-side sensitivity (valid
synthetic edits): a connector retarget changes exactly 2 of ~62 problem
tokens; a node-content change adds 1 token — presence at the token level does
NOT establish how much numerical change survives averaging.

## Prepared corrections (code + tests committed; nothing launched)

**A. Candidate shared-contribution removal** (`real_framework.GraphLearner`,
per-occurrence, count-respecting). An option whose tokens are ALL shared by
the other two (a strict-subset option — measured: 10 of the 60
training+practice records have one) has empty content and is represented by
the ZERO vector: its score relative to the common baseline is exactly the
common shift (attempt 004's preserved crash on this case is fixed and
test-locked). Claim status per section above: candidate; effect on decisions
unmeasured.

**B. Matched framing comparison** (`aws/graph_training_launch.py` worker):
one candidate copy PER arm, second module's state cloned from the first,
separate optimizer state; the worker records both initial checkpoint
identities, fails closed if they differ (`INITIAL_WEIGHTS_NOT_IDENTICAL`),
and each arm's containment report verifies its own module only. Training one
copy leaves the other untouched by construction.

**C. Extended diagnostic** (`cas_meta2/graph_teaching/diagnostic.py`,
measurement-only, zero updates) now reports, per arm, on the SAME examples
and SAME fixed weights:

| Measurement | What it should establish |
|---|---|
| individual tag vectors BEFORE pooling (norms + pairwise cosines) | do different part names already map to nearly the same numbers? |
| OLD (sum over every occurrence) vs CORRECTED (shared removed) option vectors — actual score spreads, argmax, and cosines for BOTH | does the removal change actual score differences, or only cosine statistics? |
| graph-edit response: valid synthetic edits → SAME lessons framing → encoded → mean-pooled → module — output norm/cosine/difference + score sets and argmax under both | does a changed relationship survive encoding and change the output and the decision? |
| answer-score differences + alternative-target gradients (existing) | can corrective feedback distinguish which answer should be preferred? |
| module-output norms + pairwise cosines (existing) | is the module output nearly constant across records? |

The useful quantity is not "vectors look less parallel" — it is whether the
numerical difference between two part names survives into a different
possible decision and a different corrective signal. Both are measured
together.

## Explicitly NOT done

- `initial_saturation=100.0` is NOT touched. Saturation of the module's two
  tanh stages remains an UNMEASURED HYPOTHESIS.
- No teaching-allowance increase (64 steps / 600 s per condition unchanged).
- The training pilot stays PENDING regardless of the diagnostic outcome.
- No new reservation, no launch, no package build for this correction.

## Proposed next step (needs owner authorization)

**Step 1 only:** one GPU diagnostic run (measurement-only, the existing ln(3)
diagnostic launcher, one new `$4.00` reservation) on the correction-002
pipeline, reporting the comparison table above for both arms. The training
pilot decision comes only after these findings are returned.
