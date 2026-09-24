# Switch-ON smoke (enabled-path check): run log

Runner: the Claude coordinator (temporary takeover). Label: `CLAUDE_BUILT_CLAUDE_CHECKED`.
Launched ONLY the smoke, directly with the launcher and the argv frozen in `smoke/smoke.json`. The seeds await the
owner's approval of a named plan (`OWNER_DIRECTION_20260924.md`), so `run_on_study.py` was not used, because it
would go on to the seeds.

## Attempt 1 (2026-09-24, job `cas-meta2-tpntr-20260924021244-70490111-m-20260917`): FAILED before launch, AWS capacity

**What happened:**
- Source `70490111`. Smoke admission and package committed in `45d6bea9` (`smoke.json` sha256 `d29d8753...`).
- The launcher passed preflight, booked the $15.00 ledger reservation, and created its evidence bucket, IAM role,
  instance profile and security group.
- `RunInstances` then failed with `InsufficientInstanceCapacity`: "We currently do not have sufficient g7.2xlarge
  capacity in the Availability Zone you requested (us-west-2a) ... You can currently get g7.2xlarge capacity by not
  specifying an Availability Zone in your request or choosing us-west-2b, us-west-2c, us-west-2d."
- Launcher exit 1. `result.json` status `AWS_CANDIDATE_FAILED`, execution `FAILED`, cleanup `INCOMPLETE`
  (`INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT`).

**Cleanup, checked by the coordinator directly in AWS:**
- no instance of this job in any state; no volume created since 02:00Z;
- the security group, IAM role and instance profile are gone;
- only the evidence bucket remains (4 objects: `input/config.json`, `input/source.zip`,
  `reservation/ledger_snapshot.json`, `reservation/reservation_receipt.json`). The launcher keeps it by design
  (`DELETION_DENIED`, retained pending collection).

**Money:** compute $0.00 (no instance ran). The $15.00 ledger reservation stays booked, because the ledger never
refunds automatically. Of the owner's $60.00 reservation limit, $45.00 is left.

**Why the launcher did not try another zone.** It uses the fixed preference `AZ_PREFERENCE = ("us-west-2a",
"us-west-2b", "us-west-2c")` (`aws/graph_training_curriculum_launch.py:157`) and makes one attempt in the first zone.
That order was itself an owner-authorised placement amendment of 2026-09-11, made after the same error in us-west-2d.

**Next.** Claude does not change the launcher's zone choice on its own authority. The owner is asked to choose:
- retry later in us-west-2a; or
- authorise a placement-only amendment (try us-west-2b and us-west-2c when us-west-2a reports no capacity, inside one
  job, before any instance exists).

Either way a retry is a new, recorded attempt with a new admission and a new $15.00 reservation. There are no
automatic retries.

## Attempt 2 (2026-09-24): preparation

**Owner approval to launch.** The owner's words: "YES to launching the side-by-side training of the repaired Helm.
You approved up to $60." The plan and its rules are in `PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md` section 0, on
`research/helm-integration-20260923` at `197caa32`.

**Attempt 1's records are renamed, not changed.** Every byte is kept:
- `smoke/` is now `smoke_attempt1/`;
- `receipt_analogy_on_smoke_20260917/` is now `receipt_analogy_on_smoke_20260917_attempt1/`.

The absolute paths written inside `smoke_attempt1/smoke.json` still name the old folders. That file is history and
is not edited.

**Attempt 2 is a new, recorded job.** It has a new stamp, a new admission and a new $15.00 ledger booking. It is not
an automatic retry. It uses the same reviewed code, and the zone preference is unchanged (us-west-2a first).
