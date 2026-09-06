# Saved-state repair diagnostic

## Question and boundary

Can the existing C-to-R repair path repair the exact failed R result, without
changing the authored target, model weights, verifier, or accepted runtime?

The source failure is the sixth committed tick of the R_CR candidate in job
`cas-meta2-20260906155525-195f5ad8`: R produced L0 instead of L1. The runtime
opened a repair, but the generated one-call wrapper had no continuation.
The output mismatch and missing continuation are distinct findings. Whether
the changed input, recurrent state, or their interaction caused the mismatch
remains unresolved.

This new diagnostic copies the exact saved database. It reconstructs the
unexecuted repair subgoal using the recorded pre-state and requires the same
repair frame and subgoal identity. It then permits at most:

1. C at tick 7 on that exact repair subgoal, expected L2.
2. R at tick 8 on C's accepted effect, expected L1, with the original repair ID.

The second call runs only if the first produces an accepted published effect.
There are no retries, label changes, Bias resets or alternate branches. The
original six ticks must stay unchanged. Success requires a RETURNED repair
outcome, no pending original R repair, valid stored history, unchanged weights
and source, and both newly committed ticks. The original frame remains OPEN
as an immutable historical record; the separate outcome records closure.

Attempted native calls and GPU forwards are counted separately from committed
ticks. A rejected repair can perform a forward but fail before saving a tick.
The GPU guard counts module pre-hook entries, not independent model invocations.
A read-only hook saves bounded proposal bytes and the frozen decoder's symbol
even if verification then fails before commit. It returns None, changes no
model output, and performs no additional neural forward. These observations
are not published Effects or commit receipts.

## What this does not prove

The saved database does not include the outer program's caller stack or
remaining budget. This test does not restore that stack or claim full-task
return, curriculum qualification, new learning, general reasoning, or a
CAS-specific advantage. A later candidate wrapper needs explicit multi-step
repair accounting and an end-to-end task test before training uses it.

The earlier held-out CAS 0/72 and familiar-program 24/24 results remain
separate evidence. Neither is overwritten by this diagnostic.

## Scope and reproduction

- Original evidence archive SHA256:
  `39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f`.
- Database member: `qualification/cases/case_00/candidate_03/native.db`,
  1,523,712 bytes, SHA256
  `41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2`.
- Frozen 639-member source archive SHA256:
  `d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3`.
  All base members remain unchanged. The new 644-member package adds only
  three new source files, the inert prior evidence ZIP, and a new root manifest.
- Runtime limit: 600 seconds, two native calls, 16,384 native policy units.
  The policy-unit allowance differs from the saved repair-frame budget of
  four units and from the dollar reservation.
- One AWS g7.2xlarge / RTX PRO 4500, one GPU, no T4, no automatic retry.
  Instance limit 3,600 seconds with scheduled shutdown. One $4 conservative
  reservation within the existing $400 campaign cap. This is not an invoice.
- All actual model, tensor and SQLite work runs on AWS. Local checks use only
  fake objects, source inspection and opaque bytes. No laptop model execution.
- Accepted executor, verifier, model and sibling sources are not edited.
  No merge, push or deployment follows.

Pure test capture:
`python -B tools/check_saved_repair_v8.py records/aws_saved_repair_v8_001/checks_001`.

After source freeze, `register_launch.py` builds the package and records a new
request under existing authority. It does not reserve money or call AWS.
The generated `registration_001/capture_parent.py` is the PAID one-shot
entrypoint. Never run it again after its start marker exists.

At preparation time, no new paid run or successful repair is claimed. Actual
run receipts and results must be recorded separately after execution.

## Pre-launch verification

The combined guarded local capture in checks_001 passed 131 tests in 2.23
seconds. Neural/provider imports, SQLite connections and network operations
were blocked. Tested source and the revision-15 campaign ledger were unchanged.
The tests use fake operations and opaque byte fixtures; they prove no native
repair or learning result. Review corrected a raw-payload versus metadata-bound
artifact-hash comparison before launch. It also added per-attempt GPU guard
observations without treating an uncommitted attempt as a saved tick.

An earlier ad-hoc wrapper-only invocation omitted its temporary parent directory:
28 fixture setup errors and 28 passes. Creating that directory, without code
changes, gave 56 passes. The complete checks_001 capture above creates its
directory itself and is the source-bound pre-launch result.
