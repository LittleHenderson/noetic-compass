# Targeted ^6 specialist — replacement authorization request (NOT REGISTERED, NOT RESERVED)

Status: **AWAITING_OWNER_APPROVAL.** Attempt 006 is preserved as a
device-mismatch failure inside the real ^6 forward path — NOT a completed
forward pass and NOT a learning result. A complete device-placement review of
the corrected package has been completed; no launch and no reservation.

## Device-placement review (static, no execution)

The existing review tool was extended and run against `package_007/source.zip`
(evidence `training_mode_001/compat_review_002/compat_review.json`, sha256
`f8e35cbc23585364ad9763be1003d01861c4f8755b1a1f51a420b9ee14a0f996`).
All checks pass:

| Placement site | Result |
|---|---|
| frozen encoder projection | built `device=device`; same seed + generator preserved (no silent regeneration) |
| cached problem/option vectors | derived from the on-device projection via `torch.stack` (device follows inputs) |
| module parameters | `module.to(device)` before anything else |
| optimizer | `AdamW` constructed AFTER the module move (per the PyTorch guidance) |
| training targets | both `torch.tensor` call sites carry `device=self.device` (2/2) |
| readout | dot products on same-device vectors |
| prediction path | uses the same trained forward; argmax `.item()` |
| checkpoint | `detach().cpu()` for digesting (correct, stays off-GPU) |
| construction order | framework (module) built before the learner |

`unplaced_tensor_sites: []`. Frozen numerical values and the permitted
learning scope (`operation:^6`) are unchanged. The graph curriculum, targets,
scoring, and budgets are unchanged.

Remaining GPU-only uncertainty (explicit): actual forward numerics, finite
loss values, and gradient flow — verifiable only on the authorized run.

## Package identities for the replacement (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `7d9d43ee591e13127e59cbaf3b2f545bfca9073f` |
| archive_sha256 | `60b75b727f44ae2b6f71c4fe9043e353af99436d3b2c4dcbe57a75be0040e069` |
| manifest_sha256 | `5999b053deb6a0dcb807485b276db1ed8f2f628746c2126ea1f25d94440cd570` |
| package | `training_mode_001/package_007/` |
| launcher | `aws/graph_training_launch.py` (ClientError wiring; enable export proven; 600 s termination wait) |

Job id: to be minted in the signed record at approval. Preserved limits:
64 steps / 600 s per condition (totals 128 / 1200), one job, one `$4.00`
reservation, no retries, sealed splits, error capture, verified cleanup,
containment report. The next job must record the first scheduled
forward → three scores → finite loss → backward → permitted update inside the
existing allowance; if it succeeds, the registered lessons continue; if it
fails, the original error is preserved and the job stops under the existing
policy. Ledger (exact): revision 29, `$166.00` reserved / `$234.00`
unreserved; a `$4.00` replacement would leave `$170.00` / `$230.00`.
No automatic reservation or launch.
