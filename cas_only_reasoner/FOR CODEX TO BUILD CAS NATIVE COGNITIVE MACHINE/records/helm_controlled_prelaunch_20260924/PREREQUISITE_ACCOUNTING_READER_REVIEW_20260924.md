# Prerequisite slots, accounting and route reader: public review

**CHANGES_REQUIRED before new technical admission.** Claude's `3083ea0d013929df76d5fe4852a0769d4c5010b6` supplies a named remaining job plan and strengthens route evidence completeness. It does not yet establish a $57.59 worst-case completion guarantee or an enforced spending gate. No owner action is required; Claude received the bounded fixes in `codex-0007`.

## Counts and bookings

The revised candidate C plan has **10 attempts total, 7 future jobs and 4 main training jobs**. Full fallback has **12 total, 9 future and 6 main jobs**. Three attempts have occurred: capacity refusal, completed smoke and launched route check. Codex S0/S1 correspond to Claude S1/S2; this naming difference must not double-count them. Remaining jobs are P1b combined public reader/probe/admission validation, P2 custodian build, M1-M4 training, and E1 readout. P1b is not built. E1 is proposed on a T4 with a $2 allowance instead of the former $15 g7 slot; its feasibility and full cost scope remain open.

Claude reports that only typed-pointer training/smoke jobs use the canonical fixed-$15 reservation mechanism. Nontraining jobs use separate program-derived study-spend receipts. This yields proposed canonical totals of $90 for C and $120 with fallback, including the existing $30; bookings are not invoices. Codex has not changed the canonical ledger or verified a new launcher's complete admission wiring. The earlier $135/$165 proposals included nontraining bookings and are superseded as proposals, not erased historical records.

## Accounting findings

1. `study_spend.py` hardcodes the route bound as $1.66, below the launch record's $1.6639. Rounding up gives $1.67, but that formula covers compute/address/disk only. Reserve the inclusive $3 cap until a valid complete bound exists. Merely substituting $3 into Claude's arithmetic gives $58.93; this is an illustration, not a verified bound, because the other issues below remain open.
2. The script prints a static sum and returns0. It has no next-slot decision, no executable $30-before-third-training stop, and no mechanism that moves completed P1b/P2/M/E jobs from FUTURE into incurred spending. Re-running it alone is not admission enforcement.
3. Missing pointer elapsed time becomes0. Watcher amounts have no finite/nonnegative check or binding to the actual job/instance/source. Smoke inputs use moving branch refs without recorded receipt hashes. Missing/stale/unrelated receipts and nonfinite costs must fail closed. Retained storage, request/download and cleanup costs require an explicit nonduplicated scope.
4. P1b/E1 need pinned runtime/resource/cleanup bounds and measured feasibility. The proposed $11.56 training bound must cover the whole billed lifetime, not just a worker's main timer. E1 must explicitly include collection, retained evidence and partial-study reporting or reserve them separately inside $60. Calling work forward-only is not a timing receipt.

The future-slot arithmetic $51.24 and reported $57.59 sum are arithmetically consistent with Claude's chosen constants. Their conservatism and completeness are unproven. Main execution remains disabled. The proposed stronger rule reserves all remaining mandatory slots, including E1, before any next job; it needs implementation and validation before it can license execution. C, $60, the $30 stop, single-machine limit and no-auto-retry rule remain.

## Route evidence reader

The added `route_acceptance` requires `complete=true`, exactly d,c,b,a, four PASS results, stage0 success and no earlier integrity problem. Missing cleanup prevents acceptance. These are useful completeness checks for the registered route scope.

Remaining findings: lines112-113 check only that launch bundle/source fields are nonempty; they never compare returned `identity.json`. Line116 accepts any terminated watcher record with no volumes, without matching job/instance. Line125 exits0 for job PASS even when `route_acceptance` is `ROUTE_NOT_ACCEPTED`. Bind evidence to the exact launch and frozen inputs, add mismatch cases, and require explicit acceptance in the consumer or a separate strict exit status.

This is a post-launch evidence-aggregation change. Preserve frozen per-check scoring, original job verdict and raw receipts; pin this reader revision separately. No route result has been accepted, no active job source edited, and no retry requested.

## Checks and next handoff

Codex read the four exact public files listed in the JSON companion, compared the reader delta, hashed source bytes and rederived scalar slot/cost arithmetic. No project test/model/cloud execution, receipt-state generation or protected-output access occurred. Claude's reported six synthetic cases are not Codex-executed checks and no corresponding receipt was reviewed. The next handoff is the corrected, reviewed accounting/reader code with pinned public validation receipts; missing main reader/HSET/probe requirements remain open.
