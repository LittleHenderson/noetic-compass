# Native procedural-memory demo: verified, not learned

The AWS job completed successfully. Its source-bound packet inspection, unchanged stored semantic audit, and separate live cleanup verification all passed. This is one fixed procedure saved and reused through the native runtime—not learned retrieval, skill qualification, or package promotion.

- Job: `cas-meta3-20260905225148-462ab42e`.
- Source SHA: `8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7`.
- Source ZIP SHA256: `f79e40602b9b0d3729d0f2b49dcf654bd4d0bd738107c8af7e6b9096b846aa5c`.
- Returned packet SHA256: `1991e2d49e332f0c953088e5614b2d72ec17c4cb4ad09710fdc1755435bd8673` (1,299,987 bytes).
- GPU: NVIDIA RTX PRO 4500 Blackwell Server Edition, `g7.2xlarge`, CUDA 12.8, PyTorch `2.11.0+cu128`. Eight cloud GPU checks passed: four native-contract checks and four policy checks.

## What the evidence shows

The writer exited successfully before a separate reader process retrieved the saved B procedure. A fixed parent ran A, called that B procedure twice using the same A result, and returned the first B result's identity. The two calls had distinct execution identities; the stored package address was not used as a call identity. All three candidate outputs matched the separately executed reference.

The stored audit checked six native traces across three databases: three reference traces, three candidate traces, and a zero-trace fresh-reader identity probe. It checked the registry, process records, native call tree, source bytes, and first-child return. All 316 protected file hashes matched before and after the audit. All indexed evidence remained unchanged.

Exactly five negative checks were recorded and reproduced:

- `forged_package_digest` → `UNKNOWN_PACKAGE_DIGEST`.
- `wrong_compatibility` → `CALLER_COMPATIBILITY_MISMATCH`.
- `denied_child_scope` → `CALLER_CJT_SCOPE_DENIED`.
- `denied_parent_scope` → `DEMONSTRATION_PARENT_SCOPE_DENIED`.
- `wrong_package_schema` → `UNSUPPORTED_PACKAGE_KIND`.

These requests did not call the native candidate entrypoint or create its directory. The registry bytes stayed unchanged. The reference had already run. This does not claim a sixth cloud test for altered stored-package bytes.

## Receipts and reproduction

- [Source bundle and launch command](../aws_native_demo_source_001/PRELAUNCH.md).
- [Original launch receipt](launch_receipt.json): `AWS_JOB_FINISHED`, exit 0, cleanup errors empty.
- [Outer packet inspection](../aws_native_demo_001_inspection/inspection_receipt.json): `CAS_META_3_PACKET_FULL_EVIDENCE_VERIFIED`.
- [Unchanged stored semantic audit](../aws_native_demo_001_stored_audit_clean/stored_audit_receipt.json): `CAS_META_3_STORED_NATIVE_DEMO_AUDIT_PASSED`, completed, no errors; SHA256 `9af2bb1ed781c1e10550c21821cd4f01b9476494258b3379cdce2d39bf1e4fd7`.
- [Exact audit command and working directory](../aws_native_demo_001_stored_audit_clean/process_receipt.json): `C:/Python314/python.exe -B tools/audit_native_demo.py`, with the fixed source, job, two sidecar hashes, original extracted input roots, and fresh output directory recorded in full.
- [Source-alignment proof](../aws_native_demo_001_stored_audit_clean/alignment_receipt.json) and [workspace alignment history](../source_alignment_001/README.md).
- [Independent cleanup observation](../aws_native_demo_001_cleanup_verification/closure_observation_01.json): `CAS_META_3_NATIVE_DEMO_CLEANUP_INDEPENDENTLY_VERIFIED` at 2026-09-05 23:05:47 UTC.

The semantic audit ran unchanged in the isolated checkout at `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3_audit_8b5d8ac9`. Three metadata files there required only CRLF→LF normalization to match the Git blobs, source ZIP, and original protected manifest. No audit code or manifest was changed. Earlier failed audit receipts remain preserved. The successful audit finished at 23:09:56 UTC; the temporary active-checkout README alignment was restored afterward.

## Cleanup, budget, and limits

The exact instance was terminated; its security group, profile, worker/timer roles, and schedule were absent. Both job-tagged and instance-attached volume queries were empty. The launch receipt did not contain a historical volume ID; the cleanup record states this limit explicitly. Three private, AES256-encrypted result objects remain under the seven-day lifecycle, with provider expiration headers of 2026-09-13 00:00 UTC.

The unchanged shared ledger records **$32 reserved and $368 unreserved**, including this job's $7 reservation, against the total $400 cap. There was no refund or new ledger. The launcher's compute/EBS/IPv4 estimate was approximately $0.4252, excluding S3, transfer, and taxes; it is not an invoice.

`learning_performed=false` and `qualification_status=UNQUALIFIED` remain in force. Fresh-process retrieval is not suspended-caller restart. This result does not establish learned skill selection, general memory, model-version transitions, CAS-specific advantage, production readiness, or completion of the cognitive-machine vision. No local neural execution was used for the audits.
