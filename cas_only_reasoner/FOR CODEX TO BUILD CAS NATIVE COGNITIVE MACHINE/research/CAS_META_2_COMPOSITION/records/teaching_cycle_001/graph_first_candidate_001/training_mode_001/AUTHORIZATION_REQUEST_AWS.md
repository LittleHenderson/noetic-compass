# Targeted ^6 specialist — replacement authorization request (NOT REGISTERED, NOT RESERVED)

Status: **AWAITING_OWNER_APPROVAL.** Per the owner's directive, attempt 005 is
NOT registered and NOT reserved; no job id has been minted. The complete
non-neural preparation path has been demonstrated from the exported package
before any further paid attempt.

## Connected preparation path — demonstrated from the exported package

The probe `tools/graph_training_preparation_probe.py` extracted
`package_005/source.zip` and ran, with imports from the extracted package
ONLY, the exact sequence:

```
permitted training/practice graph records
    -> adapter.public_records (frozen public records; validator inside)
    -> cas_meta2.codec.validate_public (frozen public validator)
    -> features_v2.LosslessPublicTokenizer.fit_train (tokenizer fitting)
    -> tokenizer.encode_public (actual encoded output)
```

Results (evidence `preparation_evidence_001/preparation_evidence.json`, sha256
`df9fd0c7fb3367f51acff67210157dad820bfe022c8c1423d349d00d7dae8616`):

- 60 records encoded: 10 per operation × 2 framing conditions, all three ops.
- Correct-position distribution across records: `{0: 23, 1: 21, 2: 16}` —
  the private target is NOT identifiable by slot.
- Target independence: with the public exercise fixed, swapping the private
  target leaves the encoded input identical (the encoder never consults the
  answer).
- Graph facts needed to solve the question remain in the model's input (the
  problem text carries the full graph rendering).
- Choice meanings (three-slot interface preserves the lessons): LIST_PARTS =
  one COMPLETE sorted list of direct constituents; FIND_SHARED_PART = ONE
  shared constituent or 'none'; REACHED_VIA = the COMPLETE reach label.
- Padding: literal `none_of_the_above`, position varies with the shuffle, and
  it never collides with lesson options.
- Boundary: `aws_calls: 0`, `model_execution: false`,
  `protected_splits_read: false`, no neural module created.

Locking tests (suite 66 passed in the graph packages): correct-position
variance, encoded-input invariance to the private target, padding, frozen
contract satisfaction, graph-facts-in-input.

## Package identities for the replacement (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `32d19fa2aaa058e624a31f230f95e7193dd7ab71` |
| archive_sha256 | `863cc79c650515be80e3b09c40c5bc43ddee61d92f08a677e116dfa2a506efd4` |
| manifest_sha256 | `dac94d10ac5447a36f57bc7c03c55d8ef30b1e3fc43d1e7c9281e0f3452647ca` |
| package | `training_mode_001/package_005/` (357,790 bytes, 30 members) |
| launcher | `aws/graph_training_launch.py` (ClientError wiring; enable export PROVEN in the child process; 600 s termination wait) |

Job id: **to be minted in the signed record at approval** — per the owner's
directive, nothing is registered yet.

## Preserved limits and protections (unchanged)

Per condition: 64 optimizer steps, 600.0 wall seconds, lr 0.003; totals 128
steps / 1200 s in ONE job; conditions `prompt_framing_only`; train 48 +
practice 16 whole-part records; validation/test sealed with predictions
recorded before answers; one `$4.00` reservation, no refund, no retries;
error capture; shutdown protection; verified cleanup; containment report
naming any parameter change outside `operation:^6`; the first scheduled
training update's early record will confirm encoding → forward → loss →
backward → permitted update, counted inside the existing allowance.

Ledger (exact, current): revision 27, `$158.00` reserved / `$242.00`
unreserved; a `$4.00` replacement would leave `$162.00` / `$238.00`.

## Next GPU execution requires owner approval

No automatic reservation or launch. On approval, the signed record will mint
the job, bind these identities and the preparation evidence, and one launch
will occur.
