# Graph-first ^6 training — AWS attempt 006: preserved error #5 (device placement) — CUDA confirmed live

Status: AWS_GRAPH_TRAINING_FAILED. Fully clean lifecycle. The candidate module
was CONSTRUCTED, the lesson REACHED it, and the forward executed — the
preserved error is a real torch execution error (CPU/CUDA device mismatch),
which also CONFIRMS CUDA is live on the instance. `$4.00` reserved; job
closed; no retry.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909052323-cb2ebc76` |
| request sha256 | `873eb5b9f713b650761b418e662efc0caa58ccf1b53554b4beecf60d5bc37aca` |
| authority sha256 | `2dd048fe9a5e5d1912bcfa940ffa36308446315c1639cdb4195249d136d2cd9b` |
| owner record sha256 | `2d1dfe230757c42c0506ae762d70facdcf27cc5158da414eb8d028cc64445384` |
| reservation | `4.00` USD, ledger 28 → 29 (`166.00` reserved, `234.00` unreserved) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909052323-cb2ebc76/`

## Preserved original error (verbatim tail)

```text
File ".../real_framework.py", line 161, in forward
    value = self.module(self._problem_vectors[position].unsqueeze(0))[0]
  ...
File ".../cas_cjt/neural.py", line 125, in forward
    parts = torch.cat((torch.tanh(self.left(value)), ...), dim=-1)
RuntimeError: Expected all tensors to be on the same device,
             but got mat2 is on cuda:0, different from other tensors on cpu
```

Root cause: the frozen encoder projection was created on the default CPU
device while the candidate module lives on `cuda:0`. Fixed: the projection is
now built ON the module's device (attempt-006 evidence proves CUDA is live:
the module's weights are on `cuda:0` and the forward ran until the device
mismatch).

## New package (package members changed)

| Field | Value |
|---|---|
| source_sha | `7d9d43ee591e13127e59cbaf3b2f545bfca9073f` |
| archive_sha256 | `60b75b727f44ae2b6f71c4fe9043e353af99436d3b2c4dcbe57a75be0040e069` |
| manifest_sha256 | `5999b053deb6a0dcb807485b276db1ed8f2f628746c2126ea1f25d94440cd570` |
| package | `training_mode_001/package_007/` |

## Policy status

- Zero automatic retries; `$4.00` stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
