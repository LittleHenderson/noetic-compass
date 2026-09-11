# SMOKE_RUN_CFC_001 — the whole worker body, local GPU, truncated schedule

**Not a measurement.** This exists because two paid attempts died on the instance in
code a local run would have caught. The pure-Python halves of the path were
rehearsed; the torch-touching half was not, although the standing order sanctions the
local GPU for smoke and development. This runs the **whole packaged worker body** so
that class of defect is found without a reservation.

## What was run

`tools/graph6_face_worker_smoke.py` unpacked
`candidate_package_001/source.zip` (archive sha256
`94047806420ff720749bf4a75a787d43a9a7b2e933ee9c3a268709b1c1ba1f8b`), installed the
frozen wheels from that same package, and executed `face_worker.run` on the local
NVIDIA RTX 4070 Laptop GPU with `torch 2.11.0+cu128` — the same torch version the
worker installs. Two conditions, **8 episodes each, one optimizer update each**, and
a 24-item sample of the panel.

Machine-readable output: `SMOKE_RUN_CFC_001.json`, sha256
`047dedd468816a55657dd63835d20fa8af6e4a609e07ee09066e0213f07dc155`.

## What it establishes

| step | outcome |
| --- | --- |
| encoder fit on the 2,518-record fitting corpus | ok — the call that killed attempt 001 |
| representation checks | changed role 0.1237, changed content 2.6674, changed cue 0.0576, same-token rewiring 0.1060 — **all non-zero** |
| gradient check | loss 1.184588 finite; scores finite; a target-dependent gradient on `left.weight`; the call that killed attempt 002 |
| batched teaching | 8 episodes per condition in **exactly one optimizer update** — batching verified on real tensors, not only with a stub |
| checkpoint round trip | written, read back and **verified** in both conditions |
| panel passes | before and after, no updates |
| delivery | `result.json` plus its sidecar (matching), `measurements.json` and the artifact manifest all written; envelope `REMOTE_FINISHED` |

## What none of its numbers are

- **No number here is a measurement.** Eight episodes and one update per condition on
  a laptop GPU say nothing about learning, and none of these figures may be reported
  as a result. The pilot needs the declared 4,608 decisions and 576 updates per
  condition on the AWS instance.
- The representation distances are a smoke-scale reading on five problems. They say
  the encoder does not collapse those inputs at this scale; the job's own checks, on
  the full corpus, are what the report will rest on.
- It ran the local development GPU, which the standing order permits for smoke and
  development only. It contacted no provider, created no reservation and uploaded
  nothing.

## What it does not cover

Linux behaviour, the A10G on the paid instance, the worker's own venv install and
S3 delivery, and the full 18,432-decision job. Those are what the authorised run is
for. What it does cover is every line of the worker body that touches a tensor
before, during and after teaching — which is exactly where the last two attempts
died.
