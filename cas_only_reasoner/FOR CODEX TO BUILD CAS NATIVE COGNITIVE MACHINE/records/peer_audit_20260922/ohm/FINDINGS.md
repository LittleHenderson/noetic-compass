# Independent CAS-Ohm audit — frozen peer branch

The claimed fixes reproduce, but the module still emits invalid numbers and misleading result labels. The existing suite passes **51/51**. Eight independent contract probes produce **7 failures and 1 error**. These are symbolic, fabricated audit inputs; no model, inference, training, GPU or cloud workload ran.

Scope is exactly `626cc84b574e60217a103b72d2f09388d7aa5e34`, under `noetic-compass-scaffold/noetic-compass/api/cas_ohm/`. This is the peer agent's module, not the different compiler helper on Codex's `eb998556` branch. Production sources were not changed. The active `helm3-lab` worktree was not changed.

The frozen `quantifiers.py` is 40,676 bytes, raw and LF SHA256 `039fdb9b124b83a5a9ef312c6d6c3a8c806fd6b5b85e3b7960e83d6f45666284`. The reproduction script records every original source/test hash, exact commits, interpreter, original stdout/stderr and all 50 adversarial calls in [results.json](results.json).

## Remaining defects

Line references below are in the frozen `quantifiers.py`. These defects are observed, not speculative. The suggested corrections are review recommendations, not changes made by this audit.

**Attribution:** all 50 adversarial observations are identical at the pre-fix `078d00ed` and frozen peer revision. That pre-fix module is byte-identical (Git blob `2c98a77378ef4abe31449c55fc0f904227e4bbd3`) to its introduction at `3ea9dbe67a09a4e71c38b8d2a7330229a3a0aff9`, dated 2026-08-18. The findings below are inherited defects left unresolved by the September hardening, not regressions introduced by `86ba3d75` or `a4b2e0d7`. The audit record retains the pre-fix outcome beside each probe to make that attribution checkable.

| ID | Priority | Finding and exact observation | Source / evidence |
|---|---|---|---|
| OHM-A1 | P1 | `delta_current(100,0,tolerance=nan)` emits value `100.0`, sign `WITHIN_TOLERANCE`, tolerance `nan`. Invalid observations and predictions also yield this sign. Validate both operands, tolerance and subtraction result before classifying. The NaN prediction case was already disclosed in correction 7; the bad-tolerance route remains an additional unreported entry point. | lines 386–394; probes `NAN_TOLERANCE_FALSE_ALIGNMENT`, `NAN_OBSERVATION_FALSE_ALIGNMENT`, `INF_MINUS_INF_FALSE_ALIGNMENT` |
| OHM-A2 | P2 | Finite inputs still create non-finite outputs: `i_pred(1e308,1e-308) -> inf`; `r_hidden(1e308,0.1,2)` emits uncensored `r_apparent=inf, magnitude=inf`; `delta_current(1e308,-1e308)` emits `inf/OVERSHOOT`. Operand guards alone do not protect the calculation result. The existing total-sum overflow test does not cover division/subtraction. | lines 317, 387, 572–577; `FINITE_*` probes |
| OHM-A3 | P2 | `r_hidden(8,0,2,i_obs_interval=(1,2))` raises untyped `ZeroDivisionError`; `i_obs_interval=(3,1)` is accepted as usable; a point outside the interval is also accepted. The interval path checks neither ordered endpoints nor consistency with the point, and bypasses the point zero guard. A NaN epsilon also bypasses the zero guard. Reject inconsistent interval/point metadata before division. A valid tiny positive point with a tight positive interval still works and should remain supported. | lines 521–572; `INTERVAL_ZERO_POINT_DIVISION`, `REVERSED_INTERVAL_ACCEPTED`, `INTERVAL_EXCLUDES_POINT_ACCEPTED`, `NAN_EPS_ZERO_DIVISION`; positive control `INTERVAL_VALID_TINY_POINT` |
| OHM-A4 | P2 | `admissible_trend` accepts reversed intervals and emits `RISING`; NaN intervals/points/thresholds emit `NO_TREND`; an empty axis emits `RISING`; `uncertainty_rule='made-up-rule'` is returned while the implementation actually runs the same interval comparison. The returned tag is presented as admissible despite absent/invalid evidence or a rule it never executed. Validate declarations and bind the rule label to implemented behavior. | lines 720–747; `TREND_NAN_*`, `TREND_REVERSED_INTERVAL_ACCEPTED`, `TREND_UNSUPPORTED_RULE_ACCEPTED`, `TREND_EMPTY_AXIS_ACCEPTED` |
| OHM-A5 | P2 | The trend function says comparisons use EXACT values, but converts them all to float. Valid separated intervals around 1.00000000000000000001 and 1.00000000000000000004, with minimum effect 1e-21, collapse to 1.0 and emit `NO_TREND` instead of `RISING`. Preserve the declared Decimal precision. | lines 707 and 735–745; `TREND_FLOAT_LOSS`; exact full inputs in both executable probes |
| OHM-A6 | P2 | `maturity_q4(Decimal('2.49999999999999999999999999999999999999999999999999999'))` returns band `Q1` but stores `i_q_exact='2.5'`. Replaying that recorded “exact” value produces `Q2`. `normalize()` rounds under the global 50-digit context. Retain the actual classified value without context rounding. | lines 76, 649, 664; `MATURITY_EXACT_CUT_BELOW`, `MATURITY_EXACT_CUT_AT` |
| OHM-A7 | P2 | Other numeric boundaries are still open: `r_cap(10,1,inf) -> inf`; `maturity_q4(-1)` and negative infinity get Q1; positive infinity gets Q4. These do not satisfy the documented finite/non-negative quantity domain. NaN maturity instead raises a raw Decimal `InvalidOperation`. Refuse invalid domain values consistently before banding or inversion. | lines 293–300 and 605–649; `RCAP_INFINITY_BOUND`, `MATURITY_NEGATIVE`, `MATURITY_INFINITY`, `MATURITY_NAN` |

Additional boundary observations, separated from valid typed-input defects:

- `check_eligibility(ACTIVE,True,True,None)` and an omitted/None outcome supplied explicitly both admit, as do string values `'false'` for the boolean approval fields. This is a fail-closed gap if unvalidated external records reach this Python API. Its type hints require booleans/enums; the audit does not claim a demonstrated external ingestion path.
- `delta_current` defaults its region to ACTIVE, while the Region documentation calls UNASSESSED the honest default. This primitive therefore assumes an active region when no caller declaration is supplied. No evidence packet gate is automatically invoked.
- A proper `CensoredResult` cannot silently become a numeric residual: passing it to `delta_current` raises `TypeError`. This control reproduces the intended structural separation.
- The error text at lines 217–220 still says “NaN compares False against every operator,” although the package corrects that wording elsewhere. `nan != 0` is true. The guard itself works.

## Original claims, checked separately

Every row was checked by `audit_ohm.py` against Git objects, not a floating worktree HEAD. Exact original outputs are retained in `results.json`.

| Claim | Verdict | What was observed |
|---|---|---|
| OHM-1 | REPRODUCES | Pre-fix calls return `nan, nan, 0.0, inf, inf`, exactly in the stated order. |
| OHM-2 | REPRODUCES | All five calls raise `ValueError` with “finite” at first-fix and frozen commits. |
| OHM-3 | REPRODUCES, bounded | Listed examples give `2.0, 2.0, 10.0, magnitude=2.0, r_apparent=4.0`; zero and negative resistance remain refused before/after. This verifies the listed examples, not a universal “nothing else changed” theorem. Source diff confines the first fix to guards/helper relocation. |
| OHM-4 | FALSE as written for current HEAD | Historical 39/39 and 48/48 reproduce. Old implementation plus the exact 86ba3d75 tests produces 42/48 with the stated six failures. Frozen current tests produce 51/51, or **44/51 with seven failures** against the old implementation. The instruction to copy “HEAD's tests” cannot reproduce 42/48 now. Pin the tests and implementation separately. |
| OHM-5 | REPRODUCES | Pre-fix `_as_resistance` tests only `rf <= 0`; the existing `_is_finite` helper is not called there. |
| OHM-6 | REPRODUCES | `asom(0.0,INTENDED) -> None`. Predictions 2.0, 0.0, NaN, infinity consumed by delta_current give WITHIN_TOLERANCE, OVERSHOOT, WITHIN_TOLERANCE, UNDERSHOOT. The correction is accurate; its NaN defect remains live. |
| OHM-7 | REPRODUCES only for this frozen peer tree | The frozen peer compiler has no `cas_ohm`, `delta_current`, `r_hidden`, `maturity_q4` or `i_pred` references, and this source module is not imported by it. This does not support a machine-wide current claim: the separate Codex compiler branch is outside this verdict. |
| OHM-8 | REPRODUCES within this module | Export list has I=V/R. R=V/I is exposed only as r_hidden.r_apparent, tagged APPARENT_SAME_SAMPLE. No exported V=I×R function exists here. |
| OHM-9 | REPRODUCES | At 86ba3d75 non-finite drives produce NaN/infinite RHidden magnitudes; at a4b2e0d7/frozen they raise ValueError containing “finite”. Suites are 48/48 then 51/51. |
| OHM-10 | REPRODUCES | Original test `test_r_hidden_censors_non_finite` already passes NaN and infinity as i_obs. The correction accurately restricts the original missing coverage to i_pred/r_total. |

## Test commands and failures

Run from this evidence directory:

```powershell
& 'C:\Python314\python.exe' -B .\audit_ohm.py
& 'C:\Python314\python.exe' -B .\contract_boundary_probes.py
```

The first command extracts original package/test bytes into a temporary directory under the outer CNCM homebase, invokes the original standalone runner, records its outputs, and removes only its own temporary directory. The six suite receipts are:

| Implementation pin | Test pin | Exact result | Exit |
|---|---|---|---|
| 078d00edc85fe97570b6aa3c4ea47b0ad2dad248 | same | PASSED 39/39 | 0 |
| 86ba3d75431c56147f229f24794805a3d8504f76 | same | PASSED 48/48 | 0 |
| a4b2e0d7c6726968903b99c714b7b5a6b15d401f | same | PASSED 51/51 | 0 |
| 626cc84b574e60217a103b72d2f09388d7aa5e34 | same | PASSED 51/51 | 0 |
| 078d00edc85fe97570b6aa3c4ea47b0ad2dad248 | 86ba3d75431c56147f229f24794805a3d8504f76 | PASSED 42/48 | 1 |
| 078d00edc85fe97570b6aa3c4ea47b0ad2dad248 | 626cc84b574e60217a103b72d2f09388d7aa5e34 | PASSED 44/51 | 1 |

The second command is the independent failing regression demonstration against the frozen module: **Ran 8 tests; FAILED (failures=7, errors=1), exit 1**. The error is the interval/zero-denominator `ZeroDivisionError`; the seven assertions are numeric overflow, invalid tolerance, malformed/unsupported trend declarations, lost trend precision, and rounded “exact” value. [boundary_failures.txt](boundary_failures.txt) preserves all names, tracebacks and literal results. These failures are not counted as passing engineering tests.

The original invocation used the filename `test_contract_boundaries.py`, which remains visible in the unchanged raw failure receipt. The script was subsequently renamed to `contract_boundary_probes.py` so routine recursive pytest discovery cannot collect these intentionally failing historical probes. Its bytes are unchanged (SHA256 `a6242fce13e6896512635b4ec05d4771ad6d733309c2eabc244cf5d67022105f`); it was not rerun for this packaging change.

## Calculated versus measured

The package/module docstrings repeatedly identify this as a working draft, proposed-not-validated instrument, say examples are fabricated and disclaim live model measurement. This audit found no actual measured Helm claim in these two source files.

The boundary is documentary rather than enforced per returned scalar: `i_pred(12,4)` returns the bare float 3.0; CjtQRecord accepts missing source/id/timestamp and can derive ALIGNED from caller-supplied axes with no observed result. That record is not proof of a measurement, calibration or prediction accuracy. A consumer that displays these outputs must retain source status and distinguish declared/calculated/observed records. This is an integration limitation; it is not evidence that the author actually ran or measured a model.

## Answers to the package's three questions

1. **The self-correction list is incomplete.** It accurately acknowledges the NaN residual symptom, but finite-operation overflow, malformed interval paths, trend admission/precision and loss of the recorded exact band value remain.
2. **The broader confidence is not justified by 51 passing tests.** Those tests verify the selected cases. The current-HEAD reproduction instruction is stale, and “hardened” does not mean all numeric boundaries are closed.
3. **Calculated values could lose their provenance when consumed as bare floats/optional trace records.** The module's prose labels them honestly; it does not enforce those labels on each result. No actual calculation-as-measurement publication was established in this scoped audit.
