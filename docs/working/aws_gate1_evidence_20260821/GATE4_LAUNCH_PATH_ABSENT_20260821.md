# GATE 4 — the pod-launch path does not exist in this repository — 2026-08-21

**I was wrong twice today about how far Gate 4 was. This page states the verified position and both errors.**

## What I got wrong

**Error 1 (too pessimistic).** I claimed Gate 4 needed the AWS VPC guardian stack built — a private VPC and three HTTP-filtering proxies. Wrong: that template is a reference design for a future elaborate guardian, not the implementation in use. Corrected in `GATE4_CORRECTION_REAL_BLOCKER_20260821.md`.

**Error 2 (too optimistic).** In that same correction I claimed the *only* blocker was the missing GitHub secret. Also wrong. The secret was **a** blocker — the stop supervisor genuinely needs it — but not **the** blocker.

The pattern in both: I inferred the remaining distance from one artifact instead of tracing the whole launch path to its entry point.

## The verified position

**No code in this repository can create a Pod.** This is documented, deliberate, and enforced.

`tools/runpod_open_weight_canary_v2/README.md`:

> line 20: *"Nothing in this directory creates a Pod."*
> line 157: *"**No production pre-create guardian currently exists in this repository.** For that reason the launcher's `--mode live` path is structurally `LIVE_NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE`: it returns before reading a [credential]…"*

Enforced at `create_provider_launch_receipt.py:1711-1714`:

```python
if args.mode == "live":
    # This check intentionally precedes credential reads, authorization
    # consumption, transport construction, filesystem writes, and network.
    print("LIVE_NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE")
    return 4
```

**Unconditional.** No flag, no binding, no environment, and no amount of authorization changes it. It is the first statement in `main()`, before any credential is read.

Three independent searches confirm there is no alternative entry point:

| search | result |
|---|---|
| anything calling the launcher library's live path | **none** — the only references are the canary *hashing the file* as frozen source |
| a workflow that arms the **pre-create** guardian | **none** — the single workflow is `runpod-canary-stop-supervisor.yml`, which runs *after* a pod exists and takes `pod_id` as input |
| any live transport for `precreate_guardian_offline.py` | **none** — nothing imports or drives it outside tests |

`precreate_guardian_offline.py` states the same thing in its own docstring: it *"deliberately contains no HTTP, GitHub, subprocess, model, create, delete, or credential implementation. A **future** independent GitHub workflow must supply an adapter."*

## What Gate 4 actually needs

A **production pre-create guardian**: an independently-running adapter that can only

1. inventory Pods,
2. GET one Pod by exact id,
3. STOP one Pod,

which arms **before** the create request is sent, so a Pod created but never acknowledged can still be found by its exact high-entropy name and stopped. Plus a live launch driver that uses it.

This is scoped, tractable work — the state machine (`precreate_guardian_offline.py`, 826 lines) and the stop transport (`github_stop_supervisor.py`) both already exist and are hash-locked. What is missing is the **arm-time adapter and the workflow that runs it**. It is **not** the private VPC and three proxies from Error 1.

## What genuinely advanced today

Real, verified progress — this is not a wasted session:

- **Gate 1, 2, 3 complete.** Preprod control plane `LIVE`, both binding gates verified against the deployed environment.
- **Gate 4 step 1 PASSED** — Secure Cloud A40 confirmed available, `$0.44/hr`, `High`, `9 max`.
- **The GitHub secret is placed** — `RUNPOD_CANARY_V2_API_KEY`, set `2026-08-21T16:41:33Z`. The stop supervisor can now authenticate.
- **The execution binding is APPLIED** — `GO_FOR_ONE_ENGINEERING_CANARY_ONLY`, `LIVE_GUARDIAN_FROZEN`, source commit `7c338f6d…`, launcher hash `936E7C7B…`. Suites **576 passed / 0 failed**.
- **Four defects found and fixed**, each of which would have cost real money or evidence: the model that could never load, the create-path IAM gap, the unprotected evidence pod, and the guardian core-lock drift.

## Standing

**Gate 4 cannot complete until the pre-create guardian adapter is built.** That is the honest position, verified from the code and the project's own README rather than inferred.

No pod created. No GPU exists. The A40/Pythia experiment remains **`NOT RUN`** — neither passed nor failed.

---

## PROGRESS 2026-08-21 — the pre-create guardian now exists in three parts

Built after the finding above, in order of increasing capability, and stopping short of the one piece that can spend money.

| piece | commit | can it create or spend? |
|---|---|---|
| `precreate_guardian_runpod_adapter.py` — live RunPod transport | `0725f944` | **No.** Only `list_pods` / `get_pod` / `stop_pod` exist |
| `run_precreate_guardian.py` — arm + supervise driver | `7f56a377` | **No.** Reaches only the bounded adapter |
| `.github/workflows/runpod-canary-precreate-guardian.yml` | `a0c867d0` | **No.** Contains no launcher call and no `--mode live` |

The adapter was **exercised against the real RunPod API** (read-only): it listed both real pods, bound an exact id, refused all three protected pods, and handled a bogus id cleanly. Fakes alone would not have proved that — the canary defect is the reason.

Writing the driver tests surfaced **three real safety rules**, each of which refused an unrealistic fixture. All three are features; the fixtures were corrected, never the rules:

1. the arm is bound to the exact create bytes, which must actually **name** the guarded Pod;
2. `GITHUB_SHA` must **equal** the guarded source commit, so a run cannot arm for one commit while executing another;
3. `armed <= window_start < window_end < deadline` — the guardian must arm **before** the creation window opens, so nothing can be created during a period nothing was watching.

## NEW BLOCKER FOUND — the workflow is not dispatchable yet

**`workflow_dispatch` workflows are only dispatchable from the repository's default branch.** Verified:

| | |
|---|---|
| default branch | `master` |
| current branch | `codex/cas-interpretability-successor-v2` |
| new guardian workflow on `master` | **404 — absent** |
| stop supervisor on `master` | present, and it *is* listed as dispatchable |

So the pre-create guardian workflow **cannot be triggered** until it reaches `master`. This would have surfaced at launch time, with a paid machine waiting on a guardian that could not be armed.

**Merging to the default branch is the owner's call**, not an autonomous action.

## Remaining for Gate 4

1. Get the guardian workflow onto `master` so it becomes dispatchable. **Owner decision.**
2. Write the **live launch driver** — the only remaining piece that creates spending capability, deliberately not written without an explicit go.

**No pod created. No GPU exists. Experiment `NOT RUN`.**

---

## ITEM 1 COMPLETE — the guardian workflow is dispatchable — 2026-08-21

Owner said "1 then 2". Item 1 is done.

`master` is a **protected branch**: a direct write was correctly refused with *"Changes must be made through a pull request. 3 of 3 required status checks are expected."* So it went through review properly.

**The full branch was not merged, and should not have been:** `codex/cas-interpretability-successor-v2` is **637 commits ahead, 258 behind, 3,691 files changed**. Merging that into a protected default branch to unblock a dispatch would be reckless. Instead the change was scoped to exactly what dispatchability requires — **one file, +160 lines, 0 deletions** — which works because the job checks out `inputs.source_commit` and verifies the guardian sources against pinned hashes *at that ref*.

PR **#214**: all **10 checks passed**, `mergeStateStatus=CLEAN`, squash-merged `2026-08-21T18:12:34Z`, branch deleted.

**Verified after:** `RunPod canary pre-create guardian` is now registered and `active` (id `339592969`), beside `RunPod canary stop supervisor` (id `338579878`). The blocker is gone.

## ITEM 2 — a genuine architectural gap, found by tracing the contract

Before writing the live launch driver I read what the launcher actually demands of a guardian receipt (`_validate_guardian_receipt`, `create_provider_launch_receipt.py:1031`) and compared it — mechanically — against what `arm_guardian()` actually produces.

**They are incompatible.**

| | |
|---|---|
| guardian produces | **23** keys (`cas_runpod_precreate_guardian_arm.v1`) |
| launcher requires | **22** keys, exact-match (`set(value) != required` → raise) |
| overlap | only **11** |

**Required but never produced:** `authorization_id`, `authorization_consumption_key`, `consumed_at_utc`, `guardian_consumption_generation`, `guardian_id`, `guardian_receipt_sha256`, `intent_sha256`, `maximum_hard_stop_deadline_utc`, `provider_endpoint`, `request_body_sha256`, `source_commit_sha256`.

**Produced but not required:** `delete_attempted`, `exact_create_request_sha256`, `github_repository`, `github_run_attempt`, `github_run_id`, `github_sha`, `guardian_source_sha256`, `hard_stop_deadline_utc`, `protected_pod_ids`, `provider_create_endpoint`, `receipt_sha256`, `source_commit_sha`.

This is **not** a naming mismatch that a field-rename would fix. The launcher expects a guardian built around concepts the offline state machine does not have at all:

- **`authorization_id` + `authorization_consumption_key`** — the guardian must *consume a one-time authorization*, keyed as `sha256(authorization_id + "\n" + request_body_sha256)`.
- **`guardian_id` + `guardian_consumption_generation`** — a persistent guardian identity and a *generation counter*, i.e. durable state across runs.
- **`intent_sha256`** — a binding to the launcher's own intent document, which the offline guardian never sees.
- **`consumed_at_utc`** — a consumption event distinct from the arm.

In short: the launcher was written against a **stateful, authorization-consuming guardian with a durable generation counter**. What exists is a **stateless arm-and-supervise state machine**. They are two different designs that were never wired together.

**Consequence:** the live launch driver is not a thin adapter over existing parts. It requires either extending the offline guardian to consume authorizations and maintain durable generation state, or writing a second guardian implementing the launcher's `PrecreateGuardian` protocol. Both are real design work involving durable state, and both touch the one component that can spend money.

**This was found by tracing the contract rather than assuming it — the discipline that the two earlier errors on this page cost me.** Had the driver been written on the assumption that the arm receipt would simply be accepted, it would have failed at `PRECREATE_GUARDIAN_RECEIPT_KEYSET_MISMATCH` — quite possibly with a paid machine already running.

**No pod created. No GPU exists. Experiment `NOT RUN`.**
