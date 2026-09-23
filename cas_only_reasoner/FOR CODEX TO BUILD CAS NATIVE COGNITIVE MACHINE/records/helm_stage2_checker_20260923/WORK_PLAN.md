# D-1 additive checker build

Codex owns checker_v2.py, answers_v2.py, slots_v2.py, builder tests and records.
Claude owns independent acceptance and sealed evaluation design. The copied
D-1 approval is Claude's transcription, not a signature witnessed by Codex.
Current user instructions authorize continuation and AWS execution.

Start: d206b42aa1b68d24f65ab01ec58cc82aad432859. Preserve that branch/checkpoint.
Use the already isolated Codex working folder; Claude's folder stays read-only.
No learned-model execution, training, GPU, or sealed final-test access in this job.
The five frozen files, historical predictions, grader, compiler, PCBA, Ohm and
atlas remain unchanged. New checker bound: 6; accepted-answer cap: 64.
All old supported slot plans delegate to the original compiler byte-for-byte.
The complete-assignment decoder is retained; new syntax contains 6!+1 candidates.
New target/check digests necessarily differ because the checker profile differs.

AWS selection: one temporary t3.large in us-west-2, 2 vCPUs, 8 GiB RAM,
12 GiB encrypted disposable gp3 disk, CPU credits standard (no surplus charges),
one CPU test process at a time, 4 GiB worker memory limit, 7,200-second instance
lifetime, automatic terminate on shutdown, and explicit cleanup after receipts.
No local tests or local model execution. No automatic instance or job retry.
EC2 API quoted Linux on-demand rate $0.0832/hour; at most $0.1664 instance time
for two hours, plus small disk/IP/data charges. Operational job budget: $1 USD;
this is a conservative estimate, not an AWS billing-enforced dollar cap.
Use a 1,800-second cap for builder unit tests and a 3,600-second cap for streamed
historical compatibility; performance benchmark limit 600 seconds.
Preserve partial results and failures; never report incomplete counts as acceptance.
Benchmark is on AWS per owner's latest instruction, not a local CPU measurement.
No full course reconstruction or retained all-packets cache: stream existing records.

D-1 does not change the public learner's frozen slot import. Larger learned
inference remains a separately selected integration, not proved by checker tests.
