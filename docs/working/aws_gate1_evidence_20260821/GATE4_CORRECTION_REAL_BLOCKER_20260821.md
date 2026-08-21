# GATE 4 — CORRECTION — the blocker is ONE GitHub secret, not a private VPC

**This page corrects `GATE4_STRUCTURAL_BLOCKER_20260821.md`, written earlier today. That page's conclusion was WRONG. It is retained, not deleted, because a wrong call that was caught is part of the record.**

---

## What I got wrong

I found that the canary hard-requires a pre-create guardian arm receipt (true), then found `infra/runpod_precreate_guardian_aws/template.yaml` marked `NOT_A_DEPLOYMENT_CANDIDATE` needing a private VPC and three HTTP-filtering proxies (also true), and concluded Gate 4 needed that stack built (**wrong**).

**That AWS template is a reference design for a future, more elaborate guardian. It is not the implementation the canary uses.** Its own docstring said so and I read past it:

> "A **future independent GitHub workflow** must supply an adapter that can only inventory Pods, GET one Pod, and STOP one Pod."

The implementation the canary actually uses already exists, in two pieces that are both inside the canary's own hash-locked source manifest.

## The real implementation — verified present

**1. The state machine — `tools/runpod_open_weight_canary_v2/precreate_guardian_offline.py` (826 lines).**
`arm_guardian()` at line 454 emits a receipt with `"schema_version": ARM_SCHEMA` at line 498, where `ARM_SCHEMA = "cas_runpod_precreate_guardian_arm.v1"` — **exactly the schema the canary demands** at `run_open_weight_trajectory_canary_v2.py:808`. It also carries `PROTECTED_POD_IDS` and a `MAX_POD_RUN_SECONDS = 1_800` (30-minute) bound.

**2. The independent stop adapter — `tools/runpod_open_weight_canary_v2/github_stop_supervisor.py`, driven by `.github/workflows/runpod-canary-stop-supervisor.yml`.**
This is a real stop implementation, not a stub: `_post_stop_once` issues `POST /pods/{pod_id}/stop`, wrapped by `_stop_with_retries` and `_wait_for_terminal`, with `_require_bound_target` and `_validate_deadline_bound` binding it to one exact pod and one exact deadline.

**Crucially it runs on GitHub's infrastructure, not this laptop** — which is precisely the independent stop authority the gate exists to guarantee. If this machine loses power, GitHub still stops the pod.

## Verified on the GitHub side

| check | result |
|---|---|
| repo remote | `https://github.com/LittleHenderson/noetic-compass.git` |
| workflow file present on `master` | **yes**, `4085` B |
| workflow registered and runnable | **yes** — "RunPod canary stop supervisor", `active`, id `338579878` |
| `gh` authenticated | yes, account `LittleHenderson`, scopes `gist, read:org, repo` |
| **required secret `RUNPOD_CANARY_V2_API_KEY`** | **MISSING** — the repo has only `RENDER_API_KEY` |

## THE ACTUAL BLOCKER

**One GitHub repository secret is missing: `RUNPOD_CANARY_V2_API_KEY`.**

The workflow references it in three places (lines 70, 93, 108) as `RUNPOD_API_KEY: ${{ secrets.RUNPOD_CANARY_V2_API_KEY }}`. Without it the supervisor authenticates as nothing and cannot stop anything, so arming would be theatre.

**This must be done by the owner, not by me.** Placing a credential is exactly the class of action I do not perform — I never handle API keys into external systems. The owner adds it directly in GitHub, where the value never passes through this session.

Repository → **Settings → Secrets and variables → Actions → New repository secret**
- **Name:** `RUNPOD_CANARY_V2_API_KEY`
- **Value:** the RunPod API key (the same one in `~/.runpod/config.toml`)

**Scope note worth checking while doing it:** the key currently on this machine reaches `rest.runpod.io/v1/pods` but is refused (`403`) by the GraphQL catalog. Pod stop is a `/v1/pods/{id}/stop` REST call, so the existing key *should* suffice — but if a wider-scoped key is preferred, use that instead.

## Then Gate 4 proceeds, in this order

1. Owner adds the secret (above). **← the only blocked item**
2. Arm the GitHub supervisor and the local watchdog; capture the arm receipt from `arm_guardian()`.
3. Apply the execution binding: `execution_authority = GO_FOR_ONE_ENGINEERING_CANARY_ONLY`, `provider_launcher_live_status = LIVE_GUARDIAN_FROZEN` (the canary computes this expected pair at `run_open_weight_trajectory_canary_v2.py:811-816`), plus the frozen commit and launcher hashes and a recomputed self-hash.
4. Re-run the full suites so the negative tests prove the latches now pass for the right reasons.
5. Fresh inventory + A40 stock/price re-check at launch time.
6. One create attempt. 30-minute hard bound. `$0.44/hr`, expected spend `$0.22`.

## Corrected standing

**Gate 4 is NOT structurally blocked.** Stock and price passed. Every component of the guardian exists and is hash-locked. The gap is one repository secret that only the owner can place.

Both protected pods remain `EXITED` and untouched. No pod created. No GPU exists. The A40/Pythia experiment remains **`NOT RUN`**.
