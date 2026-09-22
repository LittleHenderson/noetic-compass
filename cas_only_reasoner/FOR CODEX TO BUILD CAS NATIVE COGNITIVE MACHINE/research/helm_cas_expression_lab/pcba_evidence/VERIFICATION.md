# PCBA verification — 2026-09-21

Base commit: 04547c55fece9428d52ef973922b28ed9fec2e65.
Branch: codex/helm-pcba-board-reader-20260921.
All implementation writes are inside the authorized CNCM homebase worktree.
Original book, compiler, cas-forex sources and protected CAS_RRK sibling were
read-only. No model, GPU workload, service deployment or production activation
was run.

## Results

- 289 PCBA pytest cases passed: reader, isolated adapter, independently authored
  book/adversarial cases, checker and CLI. Of these, 93 are adapter checks.
- Independent generated boundary review: 2,764 cases; zero crashes, zero
  unexpected passes among cases explicitly labeled for rejection, and zero
  inconsistent JSON reports. Mutation cases without a rejection label prove
  robustness/report consistency, not semantic correctness.
- Full lab run on Python 3.12: 622 passed, 6 failed, 9 errors in 153.41 seconds.
  The six failures were pre-existing exporter tests needing jsonschema; the
  nine setup errors were pre-existing Q4 tests needing cryptography. Neither
  package is installed in that Python environment.
- Both affected files were rerun on the existing Python 3.14 environment:
  66 passed in 35.15 seconds. This covers all 15 initial dependency failures,
  with 51 overlapping successes. Thus 637 distinct lab cases passed across
  the two environments; there was no single all-green full-suite invocation.
- Four CLI examples produce the expected JSON results and exit codes listed in
  SOURCE_AND_EXAMPLE_MANIFEST.json. Named feedback exits 0; unverified/failed
  book examples exit 2. All say execution NOT_IMPLEMENTED and Helm NOT_TRAINED.
- The main compiler retains its existing LF SHA-256
  61ed5a45970459e49a6948282ce4060e7c3d3d3f7042078228bc97ff252b2527.

## Exact test commands

Run from research/helm_cas_expression_lab in this worktree. The temporary root
was created first, inside the authorized homebase and outside the Git worktree.
TEMP and TMP were set to that root for subprocess tests.

~~~powershell
$testRoot = "C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_test_runs\pcba_20260921"
$env:TEMP = $testRoot
$env:TMP = $testRoot

& "C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe" -m pytest -q -p no:cacheprovider test_pcba_reader.py test_pcba_component_adapter.py test_pcba_book_cases.py test_pcba_check.py --basetemp "$testRoot\integrated2"

& "C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe" -m pytest -q -p no:cacheprovider . --basetemp "$testRoot\full_lab"

& C:\Python314\python.exe -m pytest -q -p no:cacheprovider test_q3_load_and_export.py test_q4_followup.py --basetemp "$testRoot\legacy_dependency_recheck" --junitxml pcba_evidence/legacy_dependency_recheck.xml
~~~

PCBA environment: Python 3.12.10, Pydantic 2.13.3, pytest 9.0.2.
The adapter's source_files() receipts bind the reused four source files to raw
SHA-256 values and retain their original paths. They are now portable pinned
snapshots. The book manifest uses LF-normalized SHA-256.

## Independent review and recovered issues

Independent book tests and source review found defects while the checker was
being built: floating-point threshold rounding, large integer report overflow,
cap alias rejection, bare-domain terminal rejection, blanket upward-CJT
rejection, and treating unresolved inline bias identity as unequal.
All have regressions. Passive influence and coupled-loop uncertainty were then
added so an individual-path product cannot imply full-network stability.

review_result.json is the actual generated 2,764-case receipt.
review_pcba_boundary.py is the exact generating harness, retaining the local
worktree path it used. Its recorded source hashes remained unchanged during
that run and match the tested implementation. It uses no neural model.

The independent reviewer also ran an intermediate 287-case suite successfully.
The final 289-case suite adds coupled-loop and book-source identity regressions;
the older 287 count is not the final test total.

## Initial invocations and limits

The first reader/adapter invocation passed 209 tests but could not create the
default pytest temp directory for one fixture. Rerunning with an explicit
authorized basetemp passed all 210 cases then present.

An initial independent fuzz invocation used a Python environment without
Pydantic. It tested rejection paths only and is not counted as supported
component evidence. The complete reported fuzz run used the verified Python
3.12 executable and a genuinely passing baseline.

The broad-suite missing-dependency failures above were resolved by using the
already-installed appropriate interpreter, without changing old tests or
installing packages. The explicit 64 KiB reader bound, graph budget, exact
numeric proof budget and unsupported-language boundaries remain intentional.
These tests prove this static subset only. Operator selection/admissibility,
all combined transfer semantics, temporal execution and learned Helm use
remain unverified or unimplemented as described in PCBA_STATUS_20260921.md.
