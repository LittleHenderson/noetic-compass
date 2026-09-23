# Targeted follow-up plan

Status: preregistered proposals before execution. Do not run before A1-A6 submission barrier.
A0 will confirm selected gaps against A5's first report and the actual conference responses.
At most two follow-up rounds are allowed. Intended scope is one round of two record-only checks;
a second round is reserved only for an outcome-changing discrepancy. No model execution is allowed.

## F1 — exact lost-answer decoding, only if A5 has not already covered it

Proposed executor: A6, using its independently identified two lost reach questions/five input
records and their original course_p00/course_p10 saved prediction/slot-score records.
Subject source is Helm2 20208c923d41c24614504d4ecc2b289ecb66eda8, seeds 20260917/20260919;
the original artifact paths/hashes must come from SOURCE_AND_EVIDENCE_MANIFEST.json.

Compare the selected complete answer against the exact frozen decoder's admissible candidates,
score combination and tie rule. Preserve initial and final raw scores and chosen mode/via values.
Check finite values; a numeric-invalid result is not merely low accuracy. Distinguish an independently
translated ordering check from reusing the historical implementation. No checkpoint is loaded.

Predictions fixed before execution:
- Decoder discrepancy: the saved chosen answer violates the frozen ordering or tie rule, or the
  correct answer was omitted from the syntactic candidate set. This raises decoder/candidate repair priority.
- Changed learned scores: the correct answer is available and the saved chosen answer follows the
  frozen ordering, with the wrong complete answer ranked above the correct answer after training.
  This narrows the symptom to learned ranking but does not isolate architecture or optimizer cause.
- Incomplete score evidence or numeric invalidity: report the precise gap and do not infer either cause.

Stop after the five original records' two endpoints have been checked once. This is at most ten
saved prediction instances for two unique questions, not fresh evaluation. One stdlib script,
hard 120-second bound, one CPU slot, role-local output. If A5 already did the exact check, use that
existing result and cancel redundant execution.

## F2 — development label classes

Proposed executor: A3. Use each of six receipt subjects' manifest-bound
development_p00_predictions.json and development_p10_predictions.json (and saved scoring only
as a cross-check), joined to the shared compact development artifact from the historical source ZIP.
The artifact has 59 packets: 6 parts and 53 reach. Derive exact reach answers using A3's source-bound
independent graph routine, including the via node; group by 42 ABSENT, 8 DIRECT and 3 VIA labels.

Predictions fixed before execution:
- Class-balance explanation of aggregate accuracy: correctness mainly follows the 42 ABSENT cases,
  while exact positive-path performance over 11 DIRECT/VIA cases remains weak or changes differently.
- Transferable positive-path ability contributes: exact DIRECT/VIA answers improve from initialization
  as well as or instead of ABSENT performance. This weakens a blanket majority-class account.
- Mixed outcome across versions/seeds: report per-run classes rather than choose one overall story.

Stop after all six subjects' two endpoints on the 59 original packets. Report query/record counts,
not six independent datasets. One stdlib script, hard 120-second bound, one CPU slot, role-local output.
No new model prediction or fresh hidden evaluation is performed.

## Already answered; do not duplicate

A1's first report proposed intermediate endpoint chronology. A4's immutable first report already
checks it: the seed 17 lost query is wrong by pass 1; seed 19's lost query is correct through pass 8
and wrong at pass 10. Both precede the separate interference interval. Repeating that chronology
does not change the current conclusion unless a specific disagreement appears.

A2's source-insensitive analogy witness remains open to conference/final-judge challenge through
the original source/accepted sets and saved scores. Do not run neural forwards simply to repeat
saved evidence. A7 must inspect decisive raw artifacts directly.

All future training/forward proposals remain NOT RUN. They need an exact matched design, fresh
prospective evaluation and resource decision; none follows automatically from this record study.


## Selection confirmed after all six conference responses

F1 and F2 are selected unchanged from the predicted outcomes committed at259ed0be.
This confirmation occurs after all six real responses are committed and before either probe runs.
F1 targets the untested reach decoder; F2 targets development class balance. There is no selected
second round. No neural or training proposal becomes authorized by this selection.
