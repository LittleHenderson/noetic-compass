# SMOKE_RUN_CFC_003 — all four conditions and the whole panel, local GPU

**Not a measurement.** This supersedes `SMOKE_RUN_CFC_002` (all four conditions, but
only the head of the panel, so the diagnostics went unexercised). Three paid attempts
have now died in code a local run would have caught, each time because the rehearsal
covered some paths and not all of them: the synthesised fitting corpus (attempt 001),
the un-indexed gradient check (attempt 002), and the mixed-order seed type
(attempt 003), which the smoke missed because it ran only the two CFC conditions.
This run closes all three gaps at once.

## What was run

`tools/graph6_face_worker_smoke.py` unpacked
`candidate_package_001/source.zip` (archive sha256
`9723735f3bb7ee26ae1bf1292b56f2245c9f48f03bb45d4a7627d19afb604dc8`), installed the
frozen wheels from that package, and executed `face_worker.run` on the local NVIDIA
RTX 4070 Laptop GPU with `torch 2.11.0+cu128` — the same torch version the worker
installs.

- **All four declared conditions**, never a sample: `cfc_stable_cues`,
  `cfc_neutral_cue`, `mixed_order_stable_cues`, `mixed_order_neutral_cue`.
- **A stratified panel**: 8 primary items plus **all 24 diagnostic items**, so the
  rename / reorder / rewire path is exercised rather than assumed.
- 8 episodes per condition, one optimizer update each.

Machine-readable output: `SMOKE_RUN_CFC_003.json`, sha256
`8a24671cf08eb0c18c38335ec37aa824434a4f8d0c0601e39c66e949bb3e703b` (the file is the
tool's stdout as saved, so its final line is the boundary statement).

## What it establishes

| step | outcome |
| --- | --- |
| encoder fit on the fitting corpus | ok |
| representation checks | changed role 0.1348, changed content 5.0303, changed cue 0.0490, same-token rewiring 0.0974 — all non-zero |
| gradient check | loss 1.09604 finite, target-dependent gradient on `left.weight` |
| all four conditions | `TEACHING_COMPLETE`, 8 episodes each, **exactly one optimizer update** each |
| checkpoints | four files, one per condition, each written, read back and **verified** |
| panel passes | before and after every condition, with the diagnostic items included |
| delivery | `result.json` + matching sidecar, `measurements.json`, artifact manifest; envelope `REMOTE_FINISHED` |
| comparison | computed across the four conditions and written into the envelope |

## What none of its numbers are

- **No number here is a measurement.** Eight episodes and one update per condition on
  a laptop GPU say nothing about learning. The pilot needs the declared 4,608
  decisions and 576 updates per condition on the AWS instance.
- The representation distances are smoke-scale readings; the two runs report
  different values because the stratified panel changes the fitted vocabulary. The
  job's own checks on the full corpus are what the report will rest on.
- It ran the local development GPU, which the standing order permits for smoke and
  development only. No provider, no reservation, no upload.

## What it still does not cover

Linux behaviour, the A10G on the paid instance, the worker's own venv install, S3
delivery, the full 576-update-per-condition schedule, and the wall-clock ceiling. The
first four are what the authorised run is for; the fifth is guarded by
`TEACHING_INCOMPLETE` and by `validate_bounds`, which refuses any design that does not
fit the reservation.
