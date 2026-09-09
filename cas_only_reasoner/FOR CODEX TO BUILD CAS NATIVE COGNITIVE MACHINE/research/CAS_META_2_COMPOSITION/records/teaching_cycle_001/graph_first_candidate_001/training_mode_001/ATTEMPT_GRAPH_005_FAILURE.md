# Graph-first ^6 training — AWS attempt 005: preserved error #4 (config import module)

Status: AWS_GRAPH_TRAINING_FAILED. Fully clean lifecycle (zero leftovers); the
worker passed the entire preparation path (records → public adapter → frozen
validator → tokenizer fit → encode) and failed only when constructing the
candidate neural module. The **original inner error was preserved verbatim**.
`$4.00` reserved; job closed; no retry.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909040850-e4a39dea` |
| request sha256 | `2edc441b00851c576bb1e70730d2532a25227cece3f172bef9afea7f1ca66538` |
| authority sha256 | `23741f79959ef62ad15de0441039c87503052ca41e9deeab3dbe1378158e5bac` |
| owner record sha256 | `0ab92492a67f9d6e0e5ed15928b819fb171ee2963f1c1d6ed6683fe86649e70d` |
| reservation | `4.00` USD, ledger 27 → 28 (`162.00` reserved, `238.00` unreserved) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909040850-e4a39dea/`

## Preserved original error (verbatim tail)

```text
File ".../real_framework.py", line 65, in build_graph_training_framework
    from cas_cjt.types import CASformerConfig
ImportError: cannot import name 'CASformerConfig' from 'cas_cjt.types'
ValueError: CAS_CJT_IMPORT_UNRESOLVED:cannot import name 'CASformerConfig' ...
```

Root cause: `CASformerConfig` is exported by the **casformer reference
wheel** (`casformer/__init__.py`), not by `cas_cjt.types`. The fix imports
`from casformer import CASformerConfig` and constructs the candidate config
with the same fields the repo's integration tests use (d_model = encoder
d_model, num_heads 2, num_relations 4, num_layers 1, zero dropout,
initial_cutoff 0.01, initial_saturation 100.0). Verified against the real
wheel bytes (regression test reads the frozen wheel).

## New package (package member changed)

| Field | Value |
|---|---|
| source_sha | `88f36b2f603db4d5fff20a2f6380242f8ea15619` |
| archive_sha256 | `d57ee62838c36b09cb75b171bbd9a017a40f2f8c6d981027a4dc45856f02d209` |
| manifest_sha256 | `71ef77e5451621e4d2001e95824c34898ede214c6ef3e592017aa095d824dcb9` |
| package | `training_mode_001/package_006/` |

## Policy status

- Zero automatic retries; `$4.00` stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
