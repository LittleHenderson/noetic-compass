# Matched teaching study

Status at **2026-09-17 07:33:48 UTC: first GPU instance running; 0/6 completed arms**.

The study compares component-first teaching with mixing the same component/whole lessons. It holds the learner, initial state per seed, information and counted work fixed. This measures one teaching-order contrast, not general CAS architecture superiority.

- Three paired model seeds: 20260917, 20260918, 20260919.
- Full main course per arm: eight kinds, 1,152 presentations, 160 updates.
- Speed/transfer: 59 development questions at updates 0, 40, 80, 120, 160.
- Retention: 96 no-support probes before/after 16 other-question teaching updates.
- Validation: two independent last-main-update replays; 178 total actual updates.
- Six sequential jobs, $7 reservation each, $42 maximum, no automatic retries.

Worker source: `e6bdf30524c0cea3da05e8c39899ca6fc059553d`.
Frozen admission publication: `44553c76`.
Study record: `admission_001/study.json`, SHA-256 `154dee19e678aa3520b47528100642d73303c836230abcb7db6bc02d242a5099`.
Archive SHA-256: `2feff28c52fbbe5a230d4f1f32c936c9d9434bc514d5cf92d998fc917cbc72fc`.
Pure tests: **166 passed**. These tests are preparation evidence, not learning results.

First job: `cas-meta2-tmat-20260917072721-e6bdf305-a-20260917`.
Instance: `i-0dcbfc8321769d483`, observed `running`.
The supervisor is `execute_study.py`; it stops on a failed/incomplete arm or cleanup failure. The frozen schedules and endpoints do not change after scores arrive. `live_readonly_monitor.py` records scoped provider observations without mutations.

Campaign ledger after first reservation: revision 79, $466 reserved, $4,534 unreserved of $5,000. The actual hourly compute quote is $2.52; reservations are bounds, not invoices.

The initial automatic approval rejection concerned private-package destination trust. `destination_verification_001.json` binds the user's supplied handoff account statement to live AWS STS and prior-bucket ownership checks. The resubmitted identical bounded launch was accepted; the block is resolved. No new budget reservation or provider launch occurred during the rejected invocation.

Earlier completed-course results and the negative three-seed recurrence result remain preserved. No matched learning advantage is established yet.
