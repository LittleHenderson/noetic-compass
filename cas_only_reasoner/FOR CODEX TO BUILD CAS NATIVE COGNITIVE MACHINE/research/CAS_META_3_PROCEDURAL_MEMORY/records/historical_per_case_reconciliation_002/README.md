# Historical META-3 assertion reconciliation

All 13 reported test IDs passed individually in a fresh run of the unchanged
historical pure validator at `63f5b4210cc4df179193a5b5e3489ff48d79b3dd`.
The full suite reported **531 passed, 1 warning**, with no failures, errors, or
skips. The warning is the intentional duplicate-ZIP fixture. This is a pure,
synthetic-packet test result, not neural inference or live provider evidence.

## Exact scope and evidence

- `receipt.json` records all 13 exact node IDs and their individual outcomes.
- `tests.xml` and `test_stdout.txt` preserve the new unmodified test results.
- `validation_receipt.json` binds source checks, three pinned META2 dependencies,
  all 316 protected files, the child command, import restrictions, and environment.
- `baseline_before.json` and `baseline_after.json` independently compare every
  manifest entry against binary Git objects and checkout bytes. Both report
  **316 present, zero Git mismatches, zero checkout mismatches**.
- Seven `inspection_*.json` files preserve the actual rejection receipts from
  this rerun. Their hashes are bound to the corresponding test in `receipt.json`.

The manifest itself is read from the exact commit using binary `git cat-file`,
not reconstructed from another working tree. Its SHA-256 is
`476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0`.

Audit receipt SHA-256:
`49d4f88227218680efb2623c3a222fd79d4fcc47245314476ce3fcb4ecd9c230`.

## Each reported case

Names below retain the exact test names. The receipt supplies each full node ID.

| Historical test | Fresh outcome | What was checked |
| --- | --- | --- |
| `test_import_is_pure_and_native_sources_are_literal_pinned` | Pass | Pure import, 316 protected bytes, literal native source pins |
| `test_fixed_expectation_is_independent_and_passes_unchanged_pure_native_admission` | Pass | Expected runs and return node under unchanged pure admission |
| `test_stage_parent_receipts_record_exit_before_a_reader_can_be_requested` | Pass | Mock parent process exit receipt and checked child source roots |
| `test_fresh_child_discovers_all_pinned_runtime_sources_without_neural_import` | Pass | Real fresh Python process discovers exact source files without importing neural libraries |
| `test_full_synthetic_byte_packet_preserves_all_bytes_and_sidecars` | Pass | Synthetic full packet, preserved bytes, audit input handoff |
| `test_partial_packet_never_supplies_completed_semantic_audit_inputs` | Pass | Partial packet does not supply completed audit inputs |
| `test_resealed_malformed_records_do_not_pass[gpu]` | Pass | `GPU_GATE_RECEIPT_NOT_FOUR_PASSED:policy` |
| `test_resealed_malformed_records_do_not_pass[runtime]` | Pass | `FIXED_GPU_IDENTITY_REQUIRED` |
| `test_resealed_malformed_records_do_not_pass[command]` | Pass | `FIXED_DEMO_COMMAND_REQUIRED` |
| `test_resealed_malformed_records_do_not_pass[source]` | Pass | `DEMO_SOURCE_BYTES_MISMATCH` |
| `test_resealed_malformed_records_do_not_pass[native]` | Pass | `MEMBER_DIGEST_BINDING_MISMATCH` for candidate/native.db |
| `test_resealed_malformed_records_do_not_pass[learning]` | Pass | `META3_DEMO_SCOPE_OR_COUNTS_MISMATCH` |
| `test_wrong_sidecar_hash_cannot_reach_semantic_audit` | Pass | `TRUSTED_DEMO_SIDECAR_BINDING_MISMATCH` |

For all six malformed-record cases, the saved inspection receipts say
`completed_run_evidence_verified=false` and `semantic_audit_inputs=null`.
The wrong-sidecar receipt has the same result and its explicit sidecar mismatch.
These are observations from the completed fixture and inspector, not deductions
from an upstream fixture exception.

## Source basis at the historical commit

Historical package root:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3-audit-63f5b421/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY`

- `tests/test_native_demo.py:68`, `:124`, `:303`, and `:326` contain the
  four native-demo tests above.
- `tests/test_packet_inspection.py:34` constructs the full synthetic fixture.
  Line 36 calls `source_identity()` before it builds the packet.
- `cas_meta3/native_demo.py:129` defines that identity check. Lines 140-143
  compare each protected file with the manifest and raise
  `PROTECTED_BASELINE_BYTES_CHANGED` on a mismatch.
- `tests/test_packet_inspection.py:179` builds the changed fixture; line 180
  actually inspects it; lines 181-182 assert rejection and absent audit inputs.
- The wrong-sidecar test builds its fixture at line 246, inspects the altered
  packet at line 256, and checks the explicit sidecar issue at lines 257-259.

## What is corrected, and what is still unknown

The user's two supplied tracebacks establish a fixture-construction failure
before the learning-record and sidecar rejection checks. The previously claimed
guard defects are withdrawn. The other eleven original failures lack individual
full tracebacks; **this report does not assign them the same historical cause**.
It checks their assertions individually in the new run.

No missing or mismatched protected file exists in the tested Git commit or this
checkout. Therefore the claim that the commit lacks those baseline bytes is not
supported by these checks. The auditor's exact mismatching path and byte hash
remain unavailable. This report does not invent that path or treat the current
pass as an explanation of their original checkout.

The binary-object inventory contains 128 LF-only UTF-8 text files.
Current system Git configuration reports `core.autocrlf=true`; effective Git
attributes are also captured and include explicit text/line-ending rules.
A line-ending difference is only a candidate to inspect in the auditor's actual
checkout, not an established cause.

The pure dependencies and native source pins already pass the frozen build-time
Git-object checks. A clone used for reproduction must contain the referenced
Git objects, including
`b5f1718e63a2b5cf72b4b606d513d0524b9226ac`; a shallow export without required
history is not the tested setup. No dependency, source, guard, accepted executor,
or model weight was modified to obtain this pass. A fresh virtual environment
or wheel installation was not part of this bounded historical audit.

## Reproduction and run identity

Use a new clean checkout at the exact source SHA with the repository's required
history and sibling research directories intact. Do not normalize protected
artifact bytes. The existing validator writes only under its records directory
and a retained homebase scratch directory.

The run used Python 3.14.0, pytest 9.0.2, and jsonschema 4.26.0. Torch 2.11.0
distribution metadata was present, but Torch and the other forbidden neural
libraries were blocked from import. No models or tensors were loaded.

The exact validator command and output paths are in `receipt.json`.
The wrapper `run.py` can be copied to a new records directory and run with:

```powershell
C:/Python314/python.exe -B <new-records-directory>/run.py --historical-root <clean-checkout-META3-directory>
```

The wrapper invokes the unmodified historical validator, independently hashes
the 316 Git objects and checkout files before and after, and copies its raw
test records and actual synthetic rejection receipts. Both output directories
must be new; existing evidence is not overwritten.

A first wrapper attempt stopped before tests because a 316-path
`git check-attr` command exceeded the Windows command-line limit
(`WinError 206`). The wrapper was corrected to pass paths through standard
input. No test or protected source was changed. The successful run above is
the first test execution of this new audit.

The earlier **CAS 0/72** held-out composition result and **24/24** familiar-program
fit result remain separate and unchanged. This historical package check changes
neither learning result.
