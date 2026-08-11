# Attempt 3 off-pod recovery verification

Controlling status:

RFC3161_ANCHOR_VERIFIED / SUPERSEDED_PRE_EXECUTION_BYTECODE_GUARD_DEFECT / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED

The final read-only remote audit was captured at
2026-07-22T22:37:24.252993955Z and rechecked after recovery at
2026-07-22T22:48:22.264526424Z. The wrapper, model, and CUDA were not run.
No POST capture or receiver evidence was created or inferred.

## Remote continuity and execution absence

- Hostname: d808fa853c3b.
- Boot-ID SHA-256:
  8d6f65214f4ce130d8d342532a65ee41b4a8555fcd102502f6acb3840bbce7aa.
- Machine-ID SHA-256:
  aed9946c7ac389c687b73bd918790d99da1303140bc502277f8d7c016975a486.
- GPU: NVIDIA A40,
  GPU-5a2301c0-941c-a946-0ea2-f90016d4750f, 46068 MiB,
  driver 580.126.09, zero memory use, zero utilization.
- Official output, runlog, and environment_post each contained zero entries.
- No process matched the official runner, seccomp wrapper, or Attempt 3 run ID.
- Repository HEAD was
  a8969eb71c6d3e5c43d7ee2b7c7d4aa90dd70fc0, tree
  cce2d477bb0f423ee6a2669ee680eaac7b999322, with empty porcelain status.
- The dependency root contained exactly 15 regular files, three directories
  including the root, no symbolic links, no special entries, and no
  __pycache__ or .pyc residue.
- All 21 remote control files were present locally and matched SHA-256
  exactly.

## Exact archive recovery

The archives directory contains three byte-identical remote/local tar files:

| Archive | Bytes | SHA-256 |
|---|---:|---|
| official_attempt.tar | 327055360 | 84b2fd846d371ccbb6a7c020f778615a66862f8c65c5dabe27fb969e3a406a9f |
| dependency_bundle.tar | 706560 | ed16af7ae5a1ac8d61c6d3e83cf946a8cb3669c10f0f679fb2351965d5922bb8 |
| model_snapshot.tar | 377128960 | 10c55e36459311f24ac0e6d69793f5873b460fbf4da9c78ba0b202afa4ad35f6 |

Tar was used because the frozen repository contains eleven pre-existing
symbolic links. It preserves their entries without dereferencing them during
recovery.

## Normalized materialized comparison

Each archive was materialized under
C:\tmp\ATTEMPT_03_REMOTE_RECOVERY_MATERIALIZED_A8969EB7 for verification.
Relative paths used forward slashes and bytewise ordinal ordering.

| Root | Regular files | Directories | Links | Normalized SHA-256 | Differences |
|---|---:|---:|---:|---|---:|
| official attempt | 2704 | 324 | 11 | b584762d20ac5733963fc4bc119b8d08e430b0b59ef63a215b41f0f7f0ebf7c7 | 0 |
| dependency bundle | 15 | 3 | 0 | 0e37049e61b7d4abbc00957b3da2e2c9449d8a857615b372133825a8520d346c | 0 |
| model snapshot | 5 | 1 | 0 | a309e3a52fede6c07c5d87417923d79648d18cd099696b70e524f4ee061b62a6 | 0 |

The eleven symbolic-link path/target mappings also matched after normalizing
only Windows path separators.

The corrected non-self-referential remote record list binds 22 files; all 22
are present locally and match. The earlier
records_sha256_before_recovery.txt is intentionally preserved, but its own
self-entry cannot match because the output file was open when hashed. The
replacement records_sha256_final_remote.txt excludes itself and has zero
mismatches.

## Evidence boundary and next action

This is recovery proof, not model-execution proof. Attempt 3 remains
NO_SCIENTIFIC_CONCLUSION, verdict NONE, and NOT_LICENSED. The research pod was
not stopped during this task. Production pod hilj2rzs54gi06 was not touched.

Attempt 3 cannot be executed honestly: the anchored wrapper omits Python -B
from its execve child, so imports can add bytecode files after the dependency
root is verified. The next valid action is a versioned wrapper/runner fix,
tests proving bytecode suppression, a corrected frozen commit, and a fresh
Attempt 4 PRE/protocol/RFC3161 ceremony.
