# Bound v6 results summary

`summary.py` creates `summary.json` and `RESULTS.md` only after the completed
byte review, stored audit, and first-transition report have been supplied with
their exact external SHA-256 hashes. It also requires the actual downloaded
packet hash, frozen source SHA/archive hash, and job ID. It checks all 72 task /
360 arm mappings and recounts the groups. It never loads a model or calls AWS.

The report includes actual assembled split/depth counts, full native task
correctness before/after by depth and condition, validation-selected checkpoint
hashes and epochs, validation action curves, input/child-site diagnostics,
recorded first-divergence categories, and recorded GPU/compute intervals.
Validation action scores are never labeled native task correctness.

The 24 matched test triplets are not described as 72 independent structures.
The old literal 256 prototype graphs must have zero overlap with every current
split. No separate familiar-known-program test target is invented. The earlier
24/24 familiar fit and CAS 0/72 composition failure remain separate, linked to
their pinned historical receipts. No automatic acceptance or CAS-advantage claim
is emitted.

Budget-ledger and launcher receipts are optional, but each requires its own exact
external digest when supplied. Reservations, cost estimates, and unavailable
invoice data are separate fields. Missing evidence is unavailable, not zero.
Ledger arithmetic is recounted; this does not replace the launcher's full budget
authority/history validation. A recorded termination flag is not a fresh provider
observation.

## Checks already run

```powershell
C:/Python314/python.exe -B records/contrast_results_summary_v6_001/run_checks.py --output records/contrast_results_summary_v6_001/checks_002
```

Result: `PURE_SUMMARY_CHECKS_PASSED`, 15 pure unittest methods; all script bytes
unchanged during the run. Raw output and exact command are retained in
`checks_002/`. Receipt SHA-256:
`3e953ca3a08614eb3bdbec974403f0e4866bb009cf90ea480754c513f5d5e90b`.
The tests use invented identifiers and synthetic records. They do not read the
current packet, generate registered tasks, or demonstrate learning.

The first wrapper attempt could not start its child process because Windows
rejected the long adapter directory as the process working directory
(`NotADirectoryError: [WinError 267]`). No test ran in that attempt. The wrapper
now uses the shorter META2 working directory. `checks_001/` preserves the first
successful 15-method run; `checks_002/` includes the final exclusion-union count
check. No failed campaign run or actual result was erased.

## Run only after all three current reviews finish

Run from META2 and replace each placeholder with the actual file hash:

```powershell
C:/Python314/python.exe -B records/contrast_results_summary_v6_001/summary.py --review records/contrast_packet_review_v6_001/receipt.json --review-sha256 <REVIEW_SHA256> --audit records/contrast_stored_audit_v6_001/run_001/stored_audit_receipt.json --audit-sha256 <AUDIT_SHA256> --diagnostics records/contrast_first_transition_v6_001/receipt.json --diagnostics-sha256 <DIAGNOSTICS_SHA256> --packet records/aws_contrast_v6_001/cloud_artifacts.zip --packet-sha256 <PACKET_SHA256> --source-sha acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0 --source-sha256 3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1 --job cas-meta2-20260906064703-c0d74ffa --output records/contrast_results_summary_v6_001/run_001 --ledger records/budget/campaign_ledger.json --ledger-sha256 <LEDGER_SHA256> --launch records/aws_contrast_v6_001/launch_receipt.json --launch-sha256 <LAUNCH_SHA256>
```

Output must be a new directory under this summary directory. The script checks
all external input hashes again before writing. The JSON keeps every per-depth
validation action curve and every group/arm diagnostic count; the Markdown is
the shorter presentation. This is a report of previously checked evidence, not
another independent neural or stored-execution rerun.
