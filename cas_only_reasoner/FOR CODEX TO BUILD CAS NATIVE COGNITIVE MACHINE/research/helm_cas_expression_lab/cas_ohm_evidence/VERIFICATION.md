# CAS-Ohm verification — 2026-09-21

These checks establish software behavior for declared numbers and static
fixtures. No model, sensor, circuit runtime, live atlas, provider job, training,
inference, deployment or scientific acceptance ran.

## Evidence

- **compiler_tests.xml**: **771 passed** across compiler, help, legacy
  behavior and Ohm arithmetic, including the final runtime/concurrency fixes.
- **lab312_tests.xml**: 638 passed, including all 64 prepared-connection
  tests, all 289 PCBA checks, historical-loader isolation, nesting parity
  and a fresh Q3 build. Runtime: Python 3.12.10 / Pydantic 2.13.3.
- **lab314_tests.xml**: all 66 tests in the two dependency-specific lab files
  passed. Runtime: Python 3.14. The union is **704 distinct lab tests**.
- **implementation_receipt.json**: exact two-file implementation identity,
  source/offline/ZIP byte equality, source-reference hashes, historical pin,
  demonstration counts and capability boundaries.
- **compiler_examples.json** and the five **.cas** inputs: actual valid
  calculations 12/4=3, 12/6=2, 3*4=12, 12/3=4; invalid division by zero.
- **offline_cli.json**: actual subprocess output, errors and exit codes.
- **pcba_resistor.json**, **synthetic_demo.json**, **cas_rpa_projection.json**:
  prepared interfaces exercised with declared examples, without live bindings.

The full lab was checked before the final compiler review corrections.
The affected compiler checks above and all **83** connection/historical/nesting
checks were rerun afterward; **lab_final_tests.xml** records that rerun.
Those 83 overlap the full lab and are not added again. The union is **1,475
distinct tests** (771 compiler + 704 lab). No failing run is included in this
passing-test count.

## Reproduce

Use a temporary directory under this task's writable homebase and outside the
Git checkout, setting both TEMP and TMP. Disable the pytest cache when saving
receipts. Do not run neural code for these checks.

From **noetic-compass-scaffold/noetic-compass**:

~~~powershell
& 'C:\Python314\python.exe' -m pytest -q --noconftest -p no:cacheprovider tests/test_cas_ohm_numeric.py tests/test_notation_compiler.py tests/test_notation_compiler_continuation.py tests/test_notation_compiler_nesting_and_defects.py tests/test_notation_compiler_ohm.py tests/test_offline_help_text_canon.py
~~~

The working directory matters: the legacy showcase test reads
**docs/CAS_SHOWCASE_APP.cas** relative to it. The standalone compiler does not
require the API app's conftest/server dependencies.

From **research/helm_cas_expression_lab**:

~~~powershell
& 'C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe' -m pytest -q -p no:cacheprovider . --ignore=test_q3_load_and_export.py --ignore=test_q4_followup.py
& 'C:\Python314\python.exe' -m pytest -q -p no:cacheprovider test_q3_load_and_export.py test_q4_followup.py
& 'C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe' -m pytest -q -p no:cacheprovider test_cas_ohm_connections.py test_historical_compiler.py test_compiler_nesting_facts.py
& 'C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe' cas_ohm_evidence/run_demonstrations.py
~~~

The numeric module and compiler use the standard library. The two Python
environments cover different existing dependencies: Python 3.12 has Pydantic;
Python 3.14 has jsonschema and cryptography. No missing-dependency failure is
reported as a product pass.

From the repository root, rebuild the offline folder and ZIP first if the
compiler/helper changes:

~~~powershell
& 'C:\Python314\python.exe' offline-cas/build_offline_package.py
~~~

For the recorded runs, pytest also receives an explicit **--basetemp** under
the task's **_test_runs/cas_ohm_20260921/** directory and **--junitxml** pointing
to the corresponding evidence file.

## Historical preservation

The Q3 v0.7 row/report files reproduce their committed hashes through the
pinned pre-Ohm compiler. The generator now reports the historical snapshot as
its resolution location; it does not falsely report loading the active source.
Existing dataset files, manifests, export pins, frozen contracts and Rust
engine remain unchanged. This does not authorize an in-place dataset rebuild.

The loader rechecks the snapshot hash on every call, including cached calls.
A missing or modified snapshot fails instead of using a nearby current
compiler. The nesting suite compares historical and active results for its
covered legacy examples; it is not a proof of every possible CAS program.

## Findings fixed and failed invocations

Independent review found and regression-tested these concrete defects during
development: Decimal output inherited host settings; direct dataclass
construction could misstate input provenance; large exact integer records
could inherit the host's integer-string digit limit; prepared projection
replay had the same limit; JSON preflight failed to count object keys.
The final compiler review also found generic PLUS/MINUS access through
**any** bindings and concurrent initial helper-load collisions. The corrections
retain named Ohm arithmetic and synchronized helper initialization.

Initial local test commands exposed setup problems: PowerShell passed a file
wildcard literally to pytest; inherited API conftest imported an unavailable
middleware dependency; running at repository root gave a missing relative
showcase fixture (660 passed, 1 failed). Explicit files, **--noconftest**, and
the scaffold working directory resolved those invocations.

An initial historical nesting diagram test relied on the old Q3 loader's
global sys.path side effect; it now imports the active compiler independently.
The first demonstration verifier assumed an extra top-level directory in the
ZIP. Inspection showed ZIP paths start at **api/**; correcting the verifier
made exact member parity pass. No runtime implementation was changed to
accommodate that verifier mistake.

Network-restricted GitHub metadata calls failed locally and succeeded through
the approved network tool route. The signed-in user is LittleHenderson and
the destination LittleHenderson/noetic-compass is private with ADMIN access.
No credentials were printed or added to artifacts.

## Limits kept open

No automatic calibration, measured-current collection, causal interpretation
of effective constraint, series/parallel inference, board execution, learned
Helm result, full atlas integration, or live control is established here.
Legacy canonical ambiguities and set-identity limits remain documented in
COMPILER_CURRENT_STATUS_20260921.md. Existing source defects described in
SOURCE_REVIEW.md are comparison findings; those unrelated implementations
were not silently rewritten.
