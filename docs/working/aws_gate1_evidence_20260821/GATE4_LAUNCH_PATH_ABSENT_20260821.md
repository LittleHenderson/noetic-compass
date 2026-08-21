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
