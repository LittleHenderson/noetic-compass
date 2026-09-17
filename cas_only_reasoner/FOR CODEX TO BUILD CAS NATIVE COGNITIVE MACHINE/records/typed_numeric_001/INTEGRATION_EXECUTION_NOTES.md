# Full-course integration execution notes

The root agent ran the worker and launcher pure suites together on 2026-09-17:
`python -B -m pytest tests/test_typed_course_worker.py research/CAS_META_2_COMPOSITION/tests/test_typed_course_launch.py -q -p no:cacheprovider`.
The observed terminal result was **67 passed in 5.81s**, exit 0. These are pure
checks; they do not establish numerical execution. The earlier worker-only run
was interrupted after 23 passing tests while it materialized 564 packets before
the Windows guard. The owner moved that materialization after the guard and
reported 26 passing worker checks. That interrupted run had no reported assertion
failure and is not counted as a passed suite.

The source-only staged whitespace check passed. The earlier component commit's
whole-tree check encountered CRLF/trailing whitespace in immutable raw test logs;
those logs were retained byte for byte rather than normalized.

Committed execution source: `857367899983783c8f048df195338c71bdcb8aa5`.
Archive SHA-256: `5d23043ce2d1f437715065a50318252771b23f7670124f61e36127a576f49403`.
The exact archive rehearsal passed with 231 manifest members unchanged. It
exercised the real Windows refusal before CUDA; it was not a numerical run.

The first launch CLI invocation rejected a relative receipt path with
`EVIDENCE_PATH_PARENT_COMPONENT` at evidence-directory preparation, before
reservation or launch. The path was corrected to an absolute path for the same
job. This was not a second paid worker attempt.

Job: `cas-meta2-typedcourse-20260917020901-85736789`.
The launch receipt observed instance `i-0b7a980f8110e686a`.
Reservation revision 77 records $7 for this job, $452 campaign total reserved,
and $4,548 unreserved. No automatic refund is assumed.

The reservation's inherited descriptive `plan.frozen_budget` and `task_scope`
still describe an older curriculum experiment. They must not be used as this
run's teaching protocol. The source-bound authority, worker config and package
bind the actual 160 main updates plus two replay updates. The reservation's
physical one-instance, $7 and 7,200-second bounds remain the intended bounds.
This mismatch is preserved; this note does not alter the original receipt.

The source commit was pushed to the private `codex/cncm-vision-next` branch.
This note alone makes no claim about completion, learning gains or cleanup.
