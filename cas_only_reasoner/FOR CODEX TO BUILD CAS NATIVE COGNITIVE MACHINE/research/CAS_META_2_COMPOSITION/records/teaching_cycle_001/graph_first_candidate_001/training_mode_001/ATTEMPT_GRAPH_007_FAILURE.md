# Graph-first ^6 training — AWS attempt 007: preserved error #6 (CUDA generator for CUDA tensors)

Status: AWS_GRAPH_TRAINING_FAILED. Fully clean lifecycle. The encoder was
being built on the GPU device when PyTorch refused a CPU generator for a CUDA
tensor. Preserved verbatim. `$4.00` reserved; job closed; no retry.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909054806-78ffe06a` |
| request sha256 | `24a59f0203b706f265253893024f2257fd1c2b7499b71353e0ad5401832f5a71` |
| authority sha256 | `59d2562fd96b08273c8a7ae122a8eb619843045e71d4a23b6ede73f2f796451f` |
| owner record sha256 | `150fc7e0bed53e8845f2e9e15c100ffbc11b665f16a14a487be4bc3a3cde832b` |
| reservation | `4.00` USD, ledger 29 → 30 (`170.00` reserved, `230.00` unreserved) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909054806-78ffe06a/`

## Preserved original error (verbatim tail)

```text
File ".../real_framework.py", line 103, in build_encoder
    projection = torch.randn((len(vocabulary), d_model), generator=generator,
RuntimeError: Expected a 'cuda' device type for generator but found 'cpu'
```

Root cause: `torch.randn(..., device=cuda)` requires the generator itself to
be a CUDA generator. Fixed: `torch.Generator(device=device).manual_seed(seed)`.
The seed is preserved, so the frozen projection's values are unchanged in
intent; regression test and the compat reviewer now check
`torch.Generator(device=device)`.

## New package (package member changed)

| Field | Value |
|---|---|
| source_sha | `71d8e71ab274699cad5e2e083afc30dd39ffca41` |
| archive_sha256 | `7005cb88183176ce5f62a9fa669e5dd957a45776ee66365003986f77f85503c0` |
| manifest_sha256 | `72e18766a1bdca30634087e212375108b5d34dc06c9db81fe76232d5b464d29e` |
| package | `training_mode_001/package_008/` |

## Policy status

- Zero automatic retries; `$4.00` stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
