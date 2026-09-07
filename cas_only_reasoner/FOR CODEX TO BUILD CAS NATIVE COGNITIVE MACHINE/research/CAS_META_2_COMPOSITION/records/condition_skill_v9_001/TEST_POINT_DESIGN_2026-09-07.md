# Test-point layer design (owner directive, 2026-09-07)

Recorded from the owner's directive. Scope is the smallest useful automatic
test-point (TP) layer around the existing machinery. This layer observes and
reports; it does not intervene, and it does not modify any frozen experiment,
trainer, dataset, adjudicator, or execution timing.

## Three initial outputs

1. **Startup identity report** — are we testing the intended source, model,
   and state? Hashes the frozen source set and dataset manifest; each check is
   `OK`, `MISMATCH`, `MISSING`, or `NOT_CHECKED`. Missing evidence is
   incompleteness, never a failure.
2. **Per-transition failure record** — what entered, what executed, what came
   out, and which check failed. Exact shape follows the saved-repair example:
   operation, tick, actual output, required output for that fixture, verifier
   outcome, attempt occurred, accepted result, next tick reached, repair open,
   outer caller restored. "Not reached" is never reported as "failed".
3. **Scheduled development scorecard** — from an existing v9 trainer
   `result.json`: initial-versus-trained joint accuracy, per-bit accuracy,
   first-wrong-bit counts, equality/unit-margin slices, per family and split,
   with improvement flags. With no run yet, the status is `NO_RUN`, not a
   failure. Never opens private test targets.

## Boundaries (non-negotiable)

- Pure: no neural, provider, SQLite, or network imports; read-only.
- Monitoring is separate from answer leakage: the layer never reads dataset
  partition bytes beyond the sealed evidence already produced.
- Observation is separate from intervention: no weights, Bias, memory, random
  state, budget, or caller state are touched.
- Flow health is separate from correctness: an executed transition with a
  valid trace does not establish a correct answer.
- Neural checks stay inside the authorized AWS GPU job; the layer consumes
  their recorded outputs.
- Optional history is bounded; required durable evidence stays in receipts.
- The layer must be self-tested: known-valid and deliberately-invalid fixtures
  through each checker, asserting it distinguishes them and names the first
  observed failed check.

## Deferred (explicitly out of scope now)

- Learned test-point placement (a planner choosing optional probes) waits for
  fault evidence to teach and evaluate it. Basic contract-derived attachment
  comes first.
- Any change to the frozen v9 experiment or its evaluation timing would need
  a documented owner-approved pre-run amendment.

## Precedents cited by the owner (for context only)

CAS PCBA Engineer §23.8-23.10 (built-in test signals, checker vs expected
traces, scheduled self-tests, exercised-component questions); LLVM XRay
(instrumentation placement separate from runtime collection; flight-recorder
bounded buffers); PyTorch profiler (detailed capture overhead, GPU sync
costs); OpenTelemetry (observe-before-storing); Google ML Test Score (testing
and monitoring as complementary).
