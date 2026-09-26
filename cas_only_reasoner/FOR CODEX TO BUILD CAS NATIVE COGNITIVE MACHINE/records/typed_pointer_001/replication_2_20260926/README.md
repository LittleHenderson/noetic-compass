# HELM two-seed replication

This campaign repeats the completed 20-pass experiment for seeds 20260917 then 20260919. Each model starts fresh. The primary comparison is each seed's own hard-development pass-20 score minus its pass-10 score. Seed 20260918 remains the exploratory reference.

PLAN.json freezes both seeds; OWNER_DIRECTIVE.txt preserves the exact directive. Training/scoring source and reference package stay unchanged. The external admission context selects the two authorized seeds. The packaged contract's legacy run_model_seed label remains 20260918; its existing make_config and worker use design.model_seed parsed from each job. Focused checks must prove this distinction and reject mismatches.

The separate campaign cap is USD 45: USD 20 per seed and USD 5 shared. Planned bounds total USD 41, including USD 1 shared. Evidence storage is priced for 90 days; private archives remain retained afterward, with continuing cost disclosed in PLAN.json. Historical reservations are neither reused nor refunded. PROVIDER_CURRENT.json records current AWS Pricing API quotes. See https://aws.amazon.com/s3/pricing/ for storage, request and transfer pricing categories.

Both plans must be committed before training. The second seed runs after successful evidence collection and compute cleanup of the first even if its score regresses. Operational failure stops sequencing without retry. The five-minute monitor is read-only; the separate frozen Codex launch operator executes jobs.

The first CPU validation failed on an in-memory tuple/list comparison in the new adapter. Canonical serialized design bytes agree. The corrected adapter compares canonical bytes, matching the existing authority gate. The failed job and USD 0.25 reservation remain recorded. One new corrected validation is bounded to USD 0.25; revised total USD 41.25 within USD 45, with USD 3.75 headroom. No training job has started.
