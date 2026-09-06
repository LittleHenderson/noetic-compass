# v6 recorded-result review

Prepared for source `acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0` and
job `cas-meta2-20260906064703-c0d74ffa` before its results were available.
The script has not yet passed against a completed v6 packet. `--help` only
checks that its command-line entry point loads.

The review checks the externally supplied result archive hash, frozen source
package, complete collection index, recorded CUDA gates, checkpoint bytes,
saved validation actions, selected checkpoint history, and native summary
counts. It does not load a checkpoint or import a neural framework.

The checker now also requires the exact GPU test names, modules, commands,
XML totals, and gate receipt copies. It checks all saved dataset file hashes,
rechecks the existing construction without generating tasks, and binds the
four sealed neural choices to the five native evaluation choices (including
the public-only rule control). Native case, reference, action, and verdict
copies must agree. The saved evaluator process exit and private-opening order
must match their receipts.

The final review receipt includes the source manifest, complete member
inventory, extraction metadata, and binding-check counts. Frozen source and
extracted bytes are rechecked before the receipt is written. This addition
does not change the frozen training code, runtime, launcher, or evaluator.

This is not an independent neural rerun or a stored-trace semantic audit.
Those evidence boundaries must remain separate. No result or candidate is
accepted merely because this script exists or its checks pass.

Use `review.py --sha256 <verified downloaded packet SHA-256>` after the
launcher has completed collection. It requires a new extraction directory
and refuses to overwrite an existing review receipt.

## Pure checker tests

`run_tests.py` passed 10 test methods and 48 subtests on
2026-09-06T07:00:45.557591+00:00, with zero failures, errors, or skips.
The raw output and source-bound receipt are `pure_test_output.txt` and
`pure_test_receipt.json`. All 538 frozen package files, including 316 protected
baseline files, matched before and after this test run.

These tests use in-memory synthetic GPU records and synthetic native result
copies, plus the already exposed seed-926603 development dataset. The test
process blocks neural/provider imports and current campaign packet reads.
It does not generate the registered seed-2026092601 dataset, run a model,
execute a native CJT, or show a learning result.

From the CAS_META_2_COMPOSITION directory, run
`C:/Python314/python.exe -B records/contrast_packet_review_v6_001/test_review.py`
to repeat the tests without overwriting the saved receipt. `run_tests.py`
requires new receipt/output paths and refuses to overwrite the original run.
