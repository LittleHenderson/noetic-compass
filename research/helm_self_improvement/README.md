# First SI1-to-SI2 connection

Implemented, not yet executed on AWS. This is an externally authored H1/H2
engineering harness around the existing native CAS acquisition boundary.
It does not invoke HELM's neural learner, change any model weights, establish
native modification decisions, or authorize model promotion. CASalescence is
parked. The original replication source and supervision are untouched.

The new path observes the existing public nested-equation task with acquisition
disabled (an explicitly injected configuration failure), retains its original
failed output/trace, builds a typed proposal,
and executes a separate native machine using the selected configuration.
`CHANGE_CONFIG(True)` really supplies `allow_acquisition=True` to the existing
`run_episode`/`controlled_step`/`CompoundMachine.advance` path. The native
coordinator still owns acquisition, exact returns, checks and commitment.
`COMPOSE_SUPPORTED_COMPONENTS` selects the supported acquisition stage while
retaining parent and verification stages; it does not invent code or replace
the coordinator. `NO_CHANGE` remains eligible and its failed episode is kept.

The baseline and candidate receive identical original inputs and a maximum of
32 host entries each. Actual operations, primitive counters, original output
and wall time are retained. Wall-bearing receipts are integrity identities of
one run; they are not deterministic equality targets. The unchanged original-
input Effect checker and native replay decide whether a checked repair may be
retained in the research archive. This fixture contains no learned prediction.

Source identity comes from `PUBLIC_SOURCE_MANIFEST.json`: CAS
`aa6006683d9e798c85667dc0d389a604b0e99053`, runtime
`8182ad52b4468f18f140837dffee0e7debcfe786`. This is a new public export repository,
not a reconstruction of upstream Git history. All 108 runtime dependencies
are already materialized and tracked; do not run the original Git bootstrap
against this export. Historical evidence and failed AWS packages are not
reclassified as acceptance of this new code.

## Acceptance, only after AWS admission

From this export root, in a new bounded AWS CPU worker:

```sh
python -B -m pytest -q -p no:cacheprovider research/helm_self_improvement/test_contracts.py research/helm_self_improvement/test_episode.py
python -B -m research.helm_self_improvement.episode witness --output /opt/helm-si-output/episode
python -B -m research.helm_self_improvement.episode reload --directory /opt/helm-si-output/episode --expected-episode-digest <digest-retained-from-witness-stdout>
```

Use a new output directory. The test also invokes replay in a fresh process.
Archive the caller-held digest outside candidate write access. A recomputable
digest is not a signature or independent reviewer approval.

The first command is the next acceptance command, not evidence that a worker
was launched. The current HELM experiment/readout has priority. A CPU job needs
a new exact source/package/test inventory, current price, legitimate finite
SI allowance, enforced timeout, retry count zero and ownership-scoped cleanup.
The old CAS launcher has a stale instance exception and must not be reused.
No local pytest, native runtime, benchmark or model execution was performed.

## Covered paths and open gates

| Requirement | New executable coverage | Current status |
|---|---|---|
| SI-T01 | Disabled/shadow keep actual parent operations, state and output | NOT_RUN |
| SI-T02 | Exact public observation fields reject future/evaluator channels | NOT_RUN |
| SI-T03 | Source/runtime/branch/schema/checkpoint/manifest mismatch refusal | NOT_RUN |
| SI-T04–05 | Typed Boolean/component grammar; no candidate path, import, code or budget setting | NOT_RUN, H1/H2 scope only |
| SI-T06–07 | Existing native obligations/checker; changed actual acquisition calls | NOT_RUN |
| SI-T08 | H3/H4 source generation | NOT_SUPPORTED, isolation unavailable |
| SI-T09 | Retained failure and rejected NO_CHANGE with same inputs | NOT_RUN |
| SI-T15,18–19 | Existing native bundle replay, exact native return semantics, altered-file/digest refusal | NOT_RUN; no neural checkpoint support |
| SI-T16–17,26 | Crash-safe system activation, expected-parent promotion, rollback and independent benefit evaluation | NOT_IMPLEMENTED; no promotion API exposed |
| SI-T10–14,20–24 | Growth, native policy, matched experiments and paid-job enforcement | NOT_RUN / separate future admission |
| SI-T25 | Existing native atlas export is read-only | Reused interface; new path NOT_RUN |

The existing CAS adapter has pending amendments that Claude A1 must verify.
Its current source is called directly here, not replaced by a stub; acceptance
of the joint slice remains open until source-bound AWS checks and independent
public review return. `RETAINED_RESEARCH_ONLY` never means `PROMOTED`.
