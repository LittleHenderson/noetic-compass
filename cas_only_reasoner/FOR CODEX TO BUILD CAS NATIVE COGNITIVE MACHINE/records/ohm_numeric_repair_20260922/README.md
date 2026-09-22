# Bounded diagnostic numeric repair — new evidence, 2026-09-22

Invalid input handling is repaired in the older `api/cas_ohm/quantifiers.py`.
These are newly executed symbolic unit tests against pinned historical source
and the repaired source. They are not recovered historical runs, measurements,
Helm answers, calibration evidence or training authorization.

Base: `eb9985566bd11a89f485d627186ef0efa7177f02`.
Carried hardening: `86ba3d75431c56147f229f24794805a3d8504f76` and
`a4b2e0d7c6726968903b99c714b7b5a6b15d401f`.
The final repaired source is bound by SHA-256 in `RECEIPTS.json` and
`ACCEPTANCE_MANIFEST.json`, so these records also work after cherry-pick.

| Selected test group | Test functions | Test cases | Meaning |
|---|---:|---:|---|
| Existing at base | 39 | 39 | Original function bodies preserved |
| Existing only on peer branch, imported here | 12 | 12 | Claude's exact added guards preserved |
| Newly authored in this repair | 19 | 152 | Numeric boundaries and valid controls |
| Final selected total | 70 | 203 | Two files, all passing |

The integration baseline gains 31 functions / 164 cases, of which only
19 functions / 152 cases are newly authored. Parameterized cases are different
input-specific executions; they are not 152 independent requirements.
The two selected files are `api/cas_ohm/test_quantifiers.py` and
`api/cas_ohm/test_numeric_boundaries.py`. No diagnostic-package test file is
unloaded. The repository-wide filename census finds 1,052 other `test_*.py`
files, all listed as unloaded in `RECEIPTS.json`; this census is not code
coverage and does not imply every such file is runnable in this environment.

The 19 new functions cover invalid number admission at prediction, score,
capability, resistance and residual boundaries; conversion and arithmetic
overflow; invalid thresholds; unusable observation censoring; malformed
intervals; zero observed flow; signed residuals; valid tiny positive intervals;
maturity domains and replay; exact trend comparison; invalid trend evidence;
ambient Decimal context; conversion underflow; exact threshold retention; and validation before rational allocation. Multiple functions/cases can
overlap these contracts. No independent requirements-coverage percentage is
claimed.

| New replay against source | Passed | Failed | Errors | Cases |
|---|---:|---:|---:|---:|
| Base `eb998556` | 86 | 117 | 0 | 203 |
| Peer hardening `a4b2e0d7` | 111 | 92 | 0 | 203 |
| Repaired source | 203 | 0 | 0 | 203 |

All 117 failed base cases and all 92 failed peer cases have an exact matching
case ID that passes in the final run. The existing 51 peer cases pass under
both peer and repaired source. The base passes 44 of those 51; seven carried
peer guards expose the earlier finite-number defects. All failures and raw
outputs are retained, not replaced with a passing subset.

The public package probe imports `api.cas_ohm`, checks all 11 existing function
signatures and all prior public exports, then exercises prediction, signed
residual, observed-zero censoring, invalid-tolerance refusal and the existing
uncalibrated eligibility gate. Its standalone assertions are not added to the
203 pytest case total. Its input data are fabricated.

Every acceptance artifact has a relative repository path, byte count and raw
SHA-256 in `ACCEPTANCE_MANIFEST.json`. `RECEIPTS.json` additionally records each
run's exact command, source fingerprint, test fingerprints, Python version,
UTC execution times and case-by-case results. Scratch paths identify where the
test ran; scratch copies were removed after completion. Raw receipt hashes
refer to committed XML/log bytes with Git text normalization disabled.

Reproduce from the repository root with Python 3.14 and pytest installed:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
C:\Python314\python.exe -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/ohm_numeric_repair_20260922/run_repair_receipts.py'
C:\Python314\python.exe -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/ohm_numeric_repair_20260922/probe_public_entrypoints.py'
```

The runner deliberately records failures against old source and exits zero only
if the final repaired run passes. Repeating it creates new receipts with new
times; retain the committed originals when investigating this acceptance.
To verify existing evidence without rerunning tests:

```powershell
C:\Python314\python.exe -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/ohm_numeric_repair_20260922/verify_acceptance.py'
```

The first local draft run passed 199 cases with an unknown `asyncio_mode`
configuration warning. The retained run disables unrelated configuration and
plugins and has no such warning. JUnit emitted empty class names in the retained
runs; an initial metadata grouping error was corrected from disjoint test-name
inventories. The raw XML/logs were not edited to make that correction. After the exact-threshold metadata and allocation-order guards were added, the full three-source replay was rerun for the final 203-case scope. Preliminary 199/201-case runs are not the acceptance record.

Limits: `NUMERIC_POLICY.md` versions the changed rejection, formatting and
threshold behavior. This repair does not unify the compiler and diagnostic
contracts, validate canonical semantics, enforce every calibration condition
inside each convenience function, turn `CjtQRecord` into a validating record,
or close every eligibility/type-check gap. Signed activation projections remain
different from the compiler's nonnegative declared quantities. No compiler,
atlas, pinned implementation or historical evidence was changed. Static tracked
import searches found the diagnostic package initializer and tests, but no
confirmed application/runtime caller; presence alone is not a deployment claim.
The shared exact core remains a proposal for separately typed adapters.
