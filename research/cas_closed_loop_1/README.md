# CAS-CLOSED-LOOP-1 prospective recovery

This isolated adapter uses the existing native CompoundMachine, coordinator,
exact compiler Ohm calculation, PCBA reader/checker, work catalog and RPA replay.
It does not change active Helm/Q4 sources, run a model, or launch cloud work.

The live repository lacks historical objects
`348638c9d9b6069eebab7853db6b98bfef453092` and
`2636bbb6e0f41a37ba2c20df08cdf51185718617`. This is prospective implementation,
not a claim to have recovered their history. `SOURCE_BINDINGS.json` pins the
available native dependency commit and each allowed file's exact bytes.

From the repository root:

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
