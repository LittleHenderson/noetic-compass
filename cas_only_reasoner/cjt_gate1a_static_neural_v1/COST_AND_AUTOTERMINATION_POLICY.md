# Cost ceiling and auto-termination policy — CANDIDATE (owner confirms the number)

## Cost estimate (g5.xlarge ≈ $1.01/hr on-demand, us-east-1)

| Step | Estimate |
|---|---|
| Dataset regen + checker + SCMPE table (CPU-side of the GPU box) | < 0.2 h |
| Activation extraction, 4 layers × (6k train + 1k val) passages, fp16 cache | ~1.0 h |
| Layer selection (4 × S0 head runs) | ~0.5 h |
| 25 head-training jobs from cache (24 arm-runs + the mandated S0/seed-11 duplicate) | ~2.6 h |
| Protected extraction + single evaluation pass + status emission | ~0.5 h |
| **Total estimate** | **~4.7 GPU-hours ≈ $5** |

## Frozen policy (candidate values; owner signs the ceiling)

- **Campaign hard ceiling: USD 120** (≈ 24× the estimate — covers retries, spot
  interruptions, and the SageMaker-fallback premium). When cumulative billed cost
  reaches the ceiling, everything terminates and the campaign status becomes
  `GATE1B_INCOMPLETE_COST_CEILING`; partial results are never promoted.
- **Per-job wall-clock cap: 2 hours** — exceeded → the job self-terminates and
  records `JOB_TIMEOUT`.
- **Idle auto-stop: 15 minutes** — the instance stops itself when no registered job
  step is running.
- **No retry shopping:** a failed run may be retried at most ONCE with the SAME
  seed and configuration (infrastructure failure only, recorded); a second failure
  ends that run as `RUN_FAILED` in the receipt.
- **Cost accounting:** every job appends its cost line to the execution receipt;
  the final receipt totals must reconcile with the AWS billing export before any
  status is treated as final.

## Owner decision required

Confirm or adjust: the USD 120 ceiling, the 2-hour per-job cap, region us-east-1,
and the EC2-vs-SageMaker path (quota check). These land in the signed
phase-approval record.
