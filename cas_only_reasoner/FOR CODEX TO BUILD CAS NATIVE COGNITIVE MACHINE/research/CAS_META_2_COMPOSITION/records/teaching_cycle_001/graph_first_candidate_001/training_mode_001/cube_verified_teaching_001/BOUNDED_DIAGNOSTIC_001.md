# BOUNDED_DIAGNOSTIC_001 — the answer-selection readout, specified and not run

Status: **prepared, not authorised, not executed.** Nothing here reserves
capacity, contacts a provider, loads a model or trains. This document packages
one bounded measurement so it can be approved or refused as a whole, instead of
being dribbled out as micro-runs.

## The question it answers

> What rule is the learner actually using when it chooses an answer?

Attempt 007's retained telemetry answers this partly and points the way:

- on the taught component questions whose answer is `absent`, the
  checked-component learner selected a *positive* reach answer — `via:Wheel` or
  `direct` — **15 times out of 16**, and `absent` once;
- it learned the positive-answer questions well: `FIND_SHARED_PART` 7/8,
  `LIST_PARTS` 7/8, and the taught `via:Wheel` question 6/8;
- the control, taught only three positive-answer questions, reached **63/64** on
  them, and on the probe it scored 7/44 — which is *exactly* what a
  "never answer absence" rule scores on this panel;
- the probe is 33/44 absence (75.0 %), and a constant "prefer absence" rule
  scores 34/44.

So the working hypothesis is precise and testable:

> **The learner carries a positive-answer preference: it answers `via:`/`direct`
> where the graph requires `absent`, and 64 updates on two absence examples did
> not overcome it.**

What the retained data cannot supply is *which answers it selected on the probe*:
the delivered report kept only the after-training per-operation breakdown, so the
per-question rows are gone and a paired comparison between conditions is not
computable. That is the measurement this diagnostic takes — and it takes it
without any training.

## What it measures — one pass, zero updates, no training

Against **both retained checkpoints** from Attempt 007
(`checkpoint_checked_component_teaching.pt` sha256
`e4b41c74e423636faeff006c78622bafeba5447ca859872cc44d17c5f28025b0`,
`checkpoint_final_answer_only.pt` sha256
`67f18a4cb93c1db15a7d702a3b32e4757eb9f94b8f2ed14ac0a1ce17a1c59142`), with the
optimizer disabled and **zero optimizer steps**:

1. **The 44-question probe, per question.** For each question: its public
   identity, the expected answer and its absence/positive category, the selected
   answer and its category, the delivered option order, the selected slot, the
   scores and the loss. This yields the paired per-question comparison between
   the two conditions that Attempt 007 could not deliver (McNemar over the
   discordant pairs), and it tests the hypothesis directly: *how often does the
   learner answer `absent` when absence is required?*
2. **The taught questions, per question**, on the same checkpoint, so the taught
   and untaught readings are comparable on one instrument.
3. **The contrast set that is already prepared** — the zero-update contrast probe
   named in the campaign: original, consistently renamed, harmlessly reordered
   and rewired presentations of the same scene, plus the option-length readings.
   It separates *reading the graph relationships* from *preferring a familiar
   answer wording*: if the learner's answers do not move when the labels move,
   its choices are not being read off the relations.
4. **The absence-inventory control.** The same 44 questions asked with the
   absence option removed from the choice set (where the design permits it), so a
   positive-answer preference can be seen as a preference rather than as an
   inability.

Every reading is recorded per question. Nothing is averaged away, because the
whole point is which individual questions moved.

## Bounds — what it will not do

- **No training, no optimizer step, no curriculum change, no probe change.**
  `zero_updates: true`, `optimizer_steps: 0`, `learning_rate: 0.0`.
- **No retraining and no re-measurement of Attempt 007.** The checkpoints are
  read exactly as delivered, by their recorded hashes.
- **Attempt 007's missing telemetry stays missing.** This fills a gap forward; it
  never backfills a historical file.
- One instance, one job, one reservation, no automatic retries, and the same
  termination-and-collection discipline as every other run: verified collection
  before the bucket is deleted, evidence retained otherwise.
- It produces **no claim about teaching**: it is a readout of a fixed model's
  choice rule, not a training result.

## Cost and shape

| item | value |
| --- | --- |
| instance | one `g7.2xlarge`, no training |
| expected wall time | under 15 minutes: two checkpoint loads, four question sets, no optimizer steps |
| reservation | `$7.00` at the campaign's standard ceiling, refunded by the ledger if unused? **No** — reservations are not refunded; the amount is the same as every other attempt |
| launcher | the existing candidate launcher, unchanged, with a new inert request binding a new package |

## What would make this unnecessary

If the owner judges the retained evidence sufficient — the 15-of-16 positive
answers where absence was required, the 7/44 probe score against a 34/44 constant
rule — then the hypothesis is already supported well enough to act on, and this
diagnostic's value drops to confirming it on the probe. The smallest change the
retained evidence justifies on its own is: **stop teaching the positive-answer
questions in isolation and present absence and presence side by side**, since 64
updates on two absence examples produced one correct absence answer in sixteen.
That is a teaching-design change, not a diagnostic, and it is the owner's call.

## Not authorised by this document

No part of this diagnostic may run without a separate, hash-bound owner
instruction naming the request, the authority and the package. This document
reserves nothing, launches nothing, and executes nothing.
