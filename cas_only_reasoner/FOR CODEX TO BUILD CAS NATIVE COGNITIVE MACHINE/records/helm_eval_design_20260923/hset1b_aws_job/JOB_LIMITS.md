# AWS job: HSET-1B build, Stage 1 reach cells at 6 and 7 nodes

**Authority.**
- The owner's decision, in chat, 2026-09-23: "GO WITH YOUR RECOMMENDATION 6 AND 7 NODE" (recorded in
  `_handoffs/HELM_NEXT_PHASE_20260923/OWNER_DECISIONS_TAKEOVER_20260923.md`).
- "build the Stage 1 cells on aws".
- The AWS order.
- These limits are exactly the HSET-1A build job's (`../hset1a_aws_job/JOB_LIMITS.md`). Nothing is expanded.

**Runner.** Claude, the sealed-test custodian.

| Limit | Value |
|---|---|
| Machine | ONE `c7i.2xlarge`: 8 vCPU, 16 GiB, CPU only, us-west-2, on-demand, $0.357/hour |
| Timers | in-machine 120 minutes (power-off at 123); client deadline 130 minutes |
| Worst-case cost | **$0.79**. **Ceiling $1.50** |
| Credentials on the machine | none. Presigned links only |
| Work | non-neural only. No model, no GPU, no training |
| First stage | the builder end to end at tiny size, with a throwaway all-zero salt |
| Automatic retries | none. The launcher refuses to run twice |

**Custody.**
- The new salt, sha256 `b3cf84e2...c70d7f1e`, lives only in `D:/tksCAS-archive/hset1b_sealed_20260923/`.
- The sealed file `HSET1B_SEALED_TEST_NEW_67.json` returns only to a new run folder there.
- The bundle, which holds the salt, and the sealed tarball stay in the private S3 bucket under
  `helm-integration/hset1b-build-*`, as with HSET-1A. Claude deletes no data.
