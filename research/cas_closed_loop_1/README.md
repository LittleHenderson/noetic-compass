# CAS-CLOSED-LOOP-1 prospective recovery

This isolated adapter uses the existing native CompoundMachine, coordinator,
exact compiler Ohm calculation, PCBA reader/checker, work catalog and RPA replay.
It does not change active Helm/Q4 sources, run a model, or launch cloud work.

The prospective 2026-09-25 correctness amendment is described in
`HARNESS_SPEC.md` and `CHANGELOG.md`. Its new regression cases require the fresh
Codex-owned AWS Lane-A validation. Historical evidence remains byte-for-byte
unchanged and does not establish acceptance of this amended source.
`HISTORICAL_PRODUCER.json` and preserved producer snapshots support that
historical check. The fresh prospective source/package freeze binds the amended
code; its AWS acceptance remains pending.

The live repository lacks historical objects
`348638c9d9b6069eebab7853db6b98bfef453092` and
`2636bbb6e0f41a37ba2c20df08cdf51185718617`. This is prospective implementation,
not a claim to have recovered their history. `SOURCE_BINDINGS.json` pins the
available native dependency commit and each allowed file's exact bytes.

Inside the admitted AWS Lane-A worker, from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python research/cas_closed_loop_1/bootstrap_runtime.py
python research/cas_closed_loop_1/run_closed_loop.py check
python research/cas_closed_loop_1/check_artifacts.py
python -m pytest -q -p no:cacheprovider research/cas_closed_loop_1/test_native_step_adapter.py research/cas_closed_loop_1/test_closed_loop.py
python research/cas_closed_loop_1/run_closed_loop.py demo --output research/cas_closed_loop_1/demo/new-run
```

Use a new output directory each time. Retain the printed `bundle_digest`
separately. A fresh process can independently reconstruct and check the journal:

```powershell
python research/cas_closed_loop_1/run_closed_loop.py replay --directory research/cas_closed_loop_1/demo/new-run --expected-bundle-digest <retained-bundle-digest>
```

The digest must come from the caller's retained receipt, not from an untrusted
journal. A content digest detects changes; it is not a signature or external
attestation. The replay validates native semantics, event coverage, original
input substitution and event-bound primitive counts. The native RPA JSON view
is a read-only projection of the same verified journal; it has no resume rights.

The public task is `a*(b*x+c)+d=e`. The only original inputs are
`a=2,b=3,c=5,d=7,e=35`. An empty method registry blocks the caller, native RPM
opens two acquisition frames, finite construction and qualification install
procedure memory, and native checked returns resume that exact caller. Only the
existing coordinator changes native state. The independent Effect check uses
the original task inputs. Later reuse changes `e` to `41` and checks the changed
answer; invalidating a primitive blocks dispatch again.

Three statically checked PCBA boards map only to an explicit native operation
allowlist. Unsupported boards, passive transfers, feedback, and arbitrary
component execution are refused. This is not general CCDL/circuit execution.

`I_predicted` is the existing exact compiler's declared V/R design calculation.
The one-call grant floors that request and caps it after the permission mask.
`I_executed` meters entry into native `advance`; primitive instructions and
original/linear checks come separately from native event-bound executor reports.
Reservations, host entries, measured primitives, wall time and wrapper overhead
are separate channels. Missing counters and unrecorded fault work stay unknown.
ASOM and calibrated residuals remain unavailable.

This demonstrates checked procedure acquisition and reuse on a known engineering
task. It does not demonstrate model prediction, neural learning, a general task
benefit, a CAS-specific comparative advantage, production readiness or a release.
`pilot` refuses execution under the current no-model/no-cloud instruction.

The root agent is the sole writer. A bounded read-only agent reviewed specific
correctness questions; messages to DeepSeek are confined to the owner's bus.

## Lease `CAS-CORRECTION-20260927-01` (Claude, 2026-09-27)

Changes under the lease are listed in `DECISIONS.md` and dated amendments in `HARNESS_SPEC.md` and `CONTRACTS.json`.
The four frozen test files now collect 62 cases; the new `test_return_addresses.py` collects 11 (ten return-address
addendum rows plus one wiring case, see `RETURN_ADDRESS_TEST_MAP.json`). No total is hardcoded; a new freeze declares
what the corrected source collects. To run the addendum cases after `bootstrap_runtime.py`:

```powershell
python -m pytest -q -p no:cacheprovider research/cas_closed_loop_1/test_return_addresses.py
```

Notes preserving history: `SOURCE_BINDINGS.json` is byte-frozen because its digest is the admission identity of the
retained evidence bundle; its `missing_from_live_repository` entry describes Codex's local partial clone at recovery
time, and both objects (`348638c9`, `2636bbb6`) are present on `origin`. Historical `evidence/events.jsonl` row 0
carries a pre-amendment `return_identity` shape at `frames == []`; those bytes are preserved, not accepted, and the
amended no-frame rule applies to new receipts only. Claude's local runs are engineering checks; acceptance remains the
AWS worker sequence on a re-cut freeze run by Codex under an owner decision.
