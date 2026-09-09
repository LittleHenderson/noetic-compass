# Targeted ^6 specialist — replacement authorization request (NOT REGISTERED, NOT RESERVED)

Status: **AWAITING_OWNER_APPROVAL.** Per the owner's directive, attempt 006 is
NOT registered and NOT reserved. A bounded source-level compatibility review
of the exported package against the exact frozen wheels has been completed
before any further paid attempt.

## Compatibility review (static, no execution)

`tools/graph_training_wheel_compat_review.py` inspected `package_006/source.zip`
and its embedded frozen wheels with the ast module — no code executed, no
neural module created, no tensors, no AWS calls. Evidence:
`training_mode_001/compat_review_001/compat_review.json`, sha256
`e5ba4d6865da7511739d7532f0d49bf7b08d93ddd498ebd2e20cadbbf1114c16`.

All checks pass:

| Connection | Result |
|---|---|
| `CASformerConfig` export | present in `casformer/__init__.py`; class defined in `casformer/core.py` |
| Constructor fields | all 8 used fields declared: `d_model`, `num_heads`, `num_relations`, `num_layers`, `dropout`, `attention_dropout`, `initial_cutoff`, `initial_saturation` (missing: none) |
| `RegisteredOperationBank` / `DECOMPOSE` / `OPERATION_REGISTRATIONS` | all present in `cas_cjt/neural.py`; `DECOMPOSE = '^6'`; the module dict is keyed by `DECOMPOSE` |
| `make_operation_contract` | present; plasticity expression is `"operation:{operation_id}"` → the real role `operation:^6` matches the trainer's target |
| `gpu_adapter._cuda` | returns `(torch, device)` as the caller expects |

## Effective configuration (recorded, with provenance)

```text
d_model = 64, num_heads = 2, num_relations = 4, num_layers = 1,
dropout = 0.0, attention_dropout = 0.0,
initial_cutoff = 0.01, initial_saturation = 100.0
```

All values are NEWLY SPECIFIED for this candidate (the attempt-005 fix
replaced the default constructor). They match the repo integration-test
construction pattern; they are NOT an optimization claim for learning.

## Remaining GPU-only uncertainties (explicit)

- torch.cuda availability and the `_DecomposeTransform` forward numerics.
- `DifferentialConductanceLinear` parameter names/shapes (runtime-determined;
  the first scheduled update's containment report must confirm only
  `operation:^6` parameters changed).
- Actual loss values and gradient flow.

## Package identities for the replacement (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `88f36b2f603db4d5fff20a2f6380242f8ea15619` |
| archive_sha256 | `d57ee62838c36b09cb75b171bbd9a017a40f2f8c6d981027a4dc45856f02d209` |
| manifest_sha256 | `71ef77e5451621e4d2001e95824c34898ede214c6ef3e592017aa095d824dcb9` |
| package | `training_mode_001/package_006/` |
| launcher | `aws/graph_training_launch.py` (ClientError wiring; enable export proven in the child process; 600 s termination wait) |

Job id: to be minted in the signed record at approval. Preserved limits:
64 steps / 600 s per condition (totals 128 / 1200), one job, one `$4.00`
reservation, no retries, sealed splits, error capture, verified cleanup,
containment report. The first scheduled update must record
constructed → forward → three scores → finite loss → backward → permitted
update, inside the registered allowance. Ledger (exact): revision 28,
`$162.00` reserved / `$238.00` unreserved; a `$4.00` replacement would leave
`$166.00` / `$234.00`. No automatic reservation or launch.
