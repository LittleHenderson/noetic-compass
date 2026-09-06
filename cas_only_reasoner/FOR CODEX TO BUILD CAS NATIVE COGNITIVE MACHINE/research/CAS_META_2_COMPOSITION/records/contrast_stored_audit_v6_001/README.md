# Contrast v6 stored-trace audit adapter

This is a separate, offline audit adapter. It does not change the frozen experiment,
load a checkpoint, execute a neural model, or call AWS. The running experiment's
private tasks and result packet were not read while building or testing it.

## What the adapter checks

- Requires externally supplied exact source-commit, source-archive, downloaded
  packet, and completed byte-review receipt hashes. Checks the launcher and its
  helpers against the Git commit before importing them. Checks all packaged
  local source/input bytes before importing the frozen semantic replay engine.
- Independently streams the full ZIP inventory, verifies complete collection,
  compares it with the review receipt, and checks every extracted file before
  and after replay. Rejects links, unsafe paths, additions, missing files, and
  changed bytes. It never silently re-extracts the evidence.
- Uses only the pure primitives from `tools/audit_stored_packet_v3.py` and
  `cas_meta2/stored.py`, plus frozen admission and public-parser checks. It does
  not call an old v3 acceptance gate or manufacture old acceptance receipts.
- Validates every stored `native.db` trace against the published v0.2 schema.
  Also validates every `native_traces.json` export and compares it to its database,
  including diagnostic GPU-test exports. The schema bytes must match accepted
  baseline `0917267b1354e5d036263eaa6ba9a7197eafb776`.
- Independently derives 72 reference and 360 arm verdicts from stored execution.
  Keeps rejected choices in the denominator and requires zero native writes for
  rejected choices. A valid trace alone is not task correctness.
- Checks dataset hashes, four-arm neural prediction preservation, public task
  mappings, the frozen rule selector, case/arm copies, and native summaries.
  Recounts depth 3 (48 attempts), depth 4 (24 attempts), and each of the three
  conditions (24 attempts each). These are 24 matched triplets, not 72 independent
  task families. Files are under `cloud_job/campaign/native/evaluation/case_XXXX`.
  Depth comes from `provenance.depth`; condition comes from top-level
  `contrast_side`, while `provenance.evaluation_group` must be `test`.

## Executed checks

From the META2 directory, the retained check command was:

```powershell
C:/Python314/python.exe -B records/contrast_stored_audit_v6_001/run_checks.py --output records/contrast_stored_audit_v6_001/checks_001
```

Result: `PURE_CHECKS_PASSED`, 22 unittest test functions, no failures. The synthetic
tests do not use the registered seed or generate any CAS task graph. They check
orchestration and rejection behavior, not real model execution or learning.

The separate real source-only preflight verified 538 packaged inputs and 316
protected files. The source ZIP has 539 members including its launch manifest.
The published schema SHA-256 is
`35d304a3c51b0687a63c40c65c52a6cdf7eddcda8c2ee28e2234a0a4d1641969`.
No forbidden neural/provider package was imported. All bound source inputs and
the three checked adapter scripts were unchanged after the checks.

Raw output and exact subprocess commands are retained in `checks_001/`.
Its receipt SHA-256 is
`10a12d79fb3ddb4247b61cfa440c5299a480320a31e6a656fe332d18e5af6f77`.

## Actual packet audit, only after collection

Supply the actual downloaded packet digest and the actual completed review
receipt digest. Do not substitute placeholders in an executed command.

```powershell
C:/Python314/python.exe -B records/contrast_stored_audit_v6_001/audit.py --review records/contrast_packet_review_v6_001/receipt.json --review-sha256 <EXACT_REVIEW_SHA256> --source-archive records/aws_contrast_v6_source_001 --source-sha256 3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1 --source-sha acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0 --packet records/aws_contrast_v6_001/cloud_artifacts.zip --packet-sha256 <EXACT_DOWNLOADED_PACKET_SHA256> --job cas-meta2-20260906064703-c0d74ffa --extracted records/aws_contrast_v6_001_review_extracted --output records/contrast_stored_audit_v6_001/run_001
```

Only a new output directory below this adapter's directory is allowed. The actual
receipt is `run_001/stored_audit_receipt.json`, schema
`cas-meta2-contrast-stored-audit/6`. Success is
`STORED_CONTRAST_AUDIT_PASSED` with `completed: true` and `errors: []`.
Derived cases are in `outcomes.cases`; each includes `case_index`, `task_id`,
`reference`, and the five `arms`. Derived arm fields are task/procedure/binding/
dependency/output/trace correctness, native runs, reserved policy units, and
`model_rejection`. Group indices, counts and metrics are in `outcomes`.

This is stored documentary/source replay, not an independent neural rerun,
an earliest-neural-token diagnosis, a restart demonstration, a CAS-advantage
finding, or automatic learning acceptance. `learning_accepted` remains false.
The parent experiment's complete byte-review is required separately.
