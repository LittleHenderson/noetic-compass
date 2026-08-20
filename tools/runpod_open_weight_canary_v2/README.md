# RunPod open-weight canary v2: probe, pinned runtime, and watchdog

Status: `PREPARED / NOT LAUNCHED / NO PROVIDER MUTATION`.

This directory is isolated from every historical Gate 5, Jacobian, whitebox,
and production-pod wrapper. Nothing in this directory creates a Pod. The armed
watchdog is lifecycle-capable only after it is given one exact newly created
Pod identity; it rejects both protected Pod IDs.

## Frozen target runtime

- Image tag: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`
- Linux/amd64 OCI manifest digest:
  `sha256:4d1721e62b56d345c83b4fd6090664be6daf9312caab5b2e76f23d8231941851`
- OCI index digest:
  `sha256:0a360022e8de4375af99430f84e8b38951acc397252163a37ceac7204d01be35`
- Base Python: `3.12.3`; PyTorch runtime: `2.8.0+cu128`; CUDA: `12.8`.
- Hash-locked dependency file:
  `C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820\tools\runpod_open_weight_canary_v2\requirements-canary-py312-cu128.lock.txt`
- Dependency-lock SHA-256:
  `9E990C06B907FE117E67D6BB4CCD8B5AF09FFD9E8B1D98D893A727102C33CB9A`.

The exact target container still needs an in-container, no-model preflight.
No real model execution is authorized if its Python, CUDA, package, tokenizer,
or Pythia meta-architecture checks differ from the preregistration.

## Read-only provider probe

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820\tools\runpod_open_weight_canary_v2\probe_readonly.ps1"
```

The probe reads `C:\Users\wakil\.runpod\config.toml` in memory. It never
prints the API key or API URL. It makes only these operations:

1. `GET https://rest.runpod.io/v1/pods?includeMachine=true&includeNetworkVolume=true`.
2. `GET https://rest.runpod.io/v1/networkvolumes`.
3. Authenticated GraphQL query `ReadOnlyAccountState`, containing only
   `myself.clientBalance` and `myself.currentSpendPerHr`.
4. Unauthenticated GraphQL query `ReadOnlyA40State`, containing only
   `gpuTypes(id: "NVIDIA A40")` discovery fields.

It emits a sanitized JSON observation. It never returns Pod environment
variables, public IP addresses, account email, user ID, or credentials.

Current observation at `2026-08-20T10:18:30.5627917Z`:

- Balance: `16.6409483689` credits.
- Current spend: `0.013` credits/hour.
- Running Pods: `0`.
- Exited Pods: `1`.
- The sole returned Pod is excluded H200 `q2oqlooejhin7s`, status `EXITED`,
  with excluded network volume `hfelwlp1va` (130 GB). Do not mutate either.
- Excluded production Pod `hilj2rzs54gi06` is not returned by the current
  account inventory. Absence is not proof of historical deletion.
- `NVIDIA A40`: 48 GB, secure-cloud type metadata is present and community
  cloud is false, but the current one-GPU stock and uninterruptible-price fields
  are both `null`. The probe therefore reports
  `PRICE_OR_STOCK_UNAVAILABLE_FAIL_CLOSED`; this is not launchable evidence.

At approximately `2026-08-20T10:13Z`, an earlier identical public discovery
query briefly returned stock `Low` and `0.35` credits/hour. At approximately
`10:17Z`, and again at the current observation above, the same fields returned
`null`. This change is why a future launch must require a fresh, non-null rate
and stock observation and must freeze a price ceiling; the earlier price is
historical discovery only.

These facts are point-in-time provider observations and must be re-read before
any future launch.

## Two independent stop supervisors

Example only, using a future newly created Pod identity:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820\tools\runpod_open_weight_canary_v2\watchdog_unarmed.ps1" `
  -PodId '<future-new-pod-id>' `
  -PodName 'cas-open-weight-canary-v2-<future-run-id>' `
  -RunCreatedAtUtc '<future-create-receipt-UTC>'
```

The command exits `3` after printing the plan. That nonzero exit is deliberate:
it prevents automation from mistaking an unarmed plan for a running watchdog.
The file contains no credential access or HTTP calls.

`watchdog_armed.ps1` is the local Windows lifecycle implementation for one
fresh Pod start. It binds the provider-reported `lastStartedAt`, performs one
exact-target GET before writing the create-once ARMED
receipt, polls only that ID, issues STOP at the 30-minute deadline, and requires
an EXITED observation. It also registers a same-user Task Scheduler fallback.
It never deletes a Pod. Evidence must be exported and independently verified
before a separate deletion decision.

The Windows watchdog is not sufficient by itself. Logout, sleep, power loss,
loss of local internet, task tampering, or an unavailable RunPod API can defeat
it. The model runner therefore also requires a fresh canonical arm receipt from
the independent GitHub-hosted supervisor:

- `.github/workflows/runpod-canary-stop-supervisor.yml`
- `tools/runpod_open_weight_canary_v2/github_stop_supervisor.py`
- `tools/runpod_open_weight_canary_v2/arm_github_supervisor.ps1`

The GitHub job first performs an authenticated provider GET for the exact new
Pod and uploads its point-in-time arm receipt. It is then intended to remain
active until the same hard deadline, retries STOP at or after that deadline,
verifies EXITED/TERMINATED, and uploads a terminal receipt. An `if: always()`
emergency step retries STOP if the normal step fails after a successful arm
check. The arm receipt does not prove that the GitHub job remains live later;
the run status must be re-read immediately before the model starts, and manual
workflow cancellation remains forbidden during the canary.
It rejects both protected Pod IDs and never deletes a Pod. The workflow must be
present on the repository's default branch, its exact source commit must be
checked out, and the temporary `RUNPOD_CANARY_V2_API_KEY` repository secret must
be removed after terminal evidence is exported.

Both supervisors must be armed immediately after a future create receipt and
before any model command. Their receipts must bind the same Pod ID, deadline,
and source commit. The runner rejects either missing, stale, noncanonical, or
cross-mismatched receipt. Do not test either supervisor with a protected Pod.

The OCI digest and creation time are preregistered/create-receipt inputs. The
RunPod REST GET independently exposes the image name and Pod lifecycle fields;
it does not independently prove the OCI digest supplied by the operator. Exact
image-digest verification must happen inside the pinned container and in the
separate provider-create receipt.

The armed implementation uses this lifecycle:

1. Re-read `GET /v1/pods/{podId}` and bind the one new Pod's observed ID, name,
   image tag, A40 count, rate, and storage topology. Cross-link the separately
   supplied creation time and OCI digest without calling them provider-observed.
2. Reject `q2oqlooejhin7s` and `hilj2rzs54gi06` before any provider mutation.
3. Require a Pod volume, not a network volume. RunPod documents network-volume
   Pods as terminate-only, which is incompatible with evidence-preserving STOP.
4. At or immediately after 30 minutes both independent supervisors may call
   `POST /v1/pods/{podId}/stop`; success is HTTP 200. Duplicate STOP attempts
   are accepted as cost-containment retries, not counted as model work.
5. Poll read-only `GET /v1/pods/{podId}` until `desiredStatus` is `EXITED`.
6. Export evidence and independently match its byte count and SHA-256 off-pod.
7. It deliberately does not call DELETE. After export verification, deletion
   is a separate operator action with a fresh exact-target re-read.
8. Retain the stop and provider-state receipts.

The final user-facing experiment outcome must not be declared until the canary
bundle and both terminal stop receipts have been exported and reconciled. The
current canary result file does not itself prove that either stop supervisor
later reached a terminal provider state. Remove the temporary GitHub repository
secret only after that reconciliation.

If export is not verified, the watchdog stops compute but must not automatically
delete the Pod volume. This avoids turning a compute-cost guard into evidence
destruction. A separate bounded recovery/cleanup decision is then required.

## Claim boundary

These tools establish provider inventory and a future lifecycle design only.
They do not authorize a Pod, spend, model execution, Evidence Packet, scientific
claim, Gate 5 closure, or Stage C activation.
