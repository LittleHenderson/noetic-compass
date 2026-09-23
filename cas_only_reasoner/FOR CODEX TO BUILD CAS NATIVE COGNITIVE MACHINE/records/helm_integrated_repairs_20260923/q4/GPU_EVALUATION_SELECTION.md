# Selected Q4 evaluation, 2026-09-23

The original saved Q4 model is CUDA-only. Preserve its source and device checks.
The current user authorization in `docs/OWNER_RUN_AUTHORIZATION_20260922.md`
and the current repair request apply to this diagnostic evaluation. The
coordinator explicitly selected this GPU job before execution; this amendment
replaces only the earlier design's CPU device choice. No owner identity,
signature, new training permission request, or independent acceptance is invented.

- Task: evaluate the original 128-update Q4 reconstruction checkpoint on three
  separately reported visible diagnostic panels: 16 consumed teaching rows,
  16 new-content expressions on familiar ordered operator/tree shapes, and
  16 existing development expressions with genuinely new shapes.
- Historical source: `d4c3fc7643201a83693ea9073c14ab42ecc5a570`.
- Weights SHA-256: `d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477`.
- Frozen canonical input-manifest SHA-256:
  `ffbed5ffa335608f0b5e9f5a30d94530e2a2e34c1b82c2f3681cceaa0c9a1061`.
- Device: `cuda:0`, RTX 4070 Laptop GPU,
  `GPU-7cfee18b-e83d-b6fb-a946-ae444b329fdd`.
- Limits: zero updates, no optimizer, at most 48 predictions, one job,
  two CPU threads, 120 seconds including admission, no automatic retry/resume,
  no CPU fallback, cloud access, or paid API.
- Admission: original shared-display policy, three samples at <=10% GPU load,
  >=4096 MiB free, <=75 C; require readable local process inventory with no
  matching learning job. Shared Q4 lock prevents overlapping Q4 launches.
- Stop: original monitor stops the owned child at >=80 C, unavailable telemetry,
  device identity change, or time limit. Other processes remain untouched.
- Source, input and checkpoint mismatches stop before model loading; source is
  frozen throughout the selected run. Keep any failed admission/run receipt.

This is not tuning, a hidden final evaluation, a historical Helm gate, or the
complete Helm 3.0 result. Claude retains independent checking/final evaluation;
no acknowledgment or approval from Claude is claimed.

The original worker logged update numbers but no per-row IDs. Exposure is
reconstructed from its pinned single-example seeded shuffle, the completed
128-update log and the saved checkpoint, with that limitation stated in the
manifest. New-content targets are declared aligned token/AST substitutions,
not newly compiled outputs or learned predictions. New structures are absent
from the complete 2048-row teaching pool both with and without binary operator
labels. Matched size/depth status is recorded per row.

Initial tests: 31 passed, one failed due to an incorrect expected shuffle
fixture. The implementation was unchanged; correcting the fixture gives
32 passed. Both receipts remain under `tests/`. This is narrow evaluator
validation, not a model capability claim.
