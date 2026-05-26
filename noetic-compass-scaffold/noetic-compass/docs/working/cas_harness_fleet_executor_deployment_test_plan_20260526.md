# CAS Harness Fleet Executor Deployment Test Plan

Date: 2026-05-26

## Goal

After PR #97 merges and Render redeploys, prove the deployed API enforces the fleet executor contract for large open-weight audits.

The test must prove the negative case too: a 300B run is not valid just because a scale plan exists. It must require worker registration, job leases, heartbeats, Evidence Packet fragment receipts, and a blocked merge until every assigned job returns evidence.

## PR #97 Scope Boundary

PR #97 is an enterprise distributed audit control-plane and receipt-gate PR.

It proves that a large-audit run cannot move from plan to verifier-ready status without registered workers, owned leases, live heartbeats, and Evidence Packet fragment receipts. It does not prove arbitrary 20B, 100B, or 300B inference completion. It does not load or run real large-model weights by itself. It does not provision a production worker fleet.

It also does not merge the final `ACCEPT` / `SUPPRESS` verifier decision. The fleet merge may make a completed receipt set ready for verifier review, but only the verifier layer can emit a final verdict after it evaluates the merged Evidence Packet, confidence thresholds, controls, and policy profile.

## Post-Merge Runbook

1. Merge PR #97 to `master`.
2. Wait for the deployed API service to redeploy from `master`.
3. Acquire or mint a deployed API JWT for the verifier and set it in the verifier environment:

```powershell
$token = (curl.exe -sS -X POST https://noetic-compass-api.onrender.com/auth/token -H "Content-Type: application/json" -d "{\"username\":\"fleet-verifier\"}" | ConvertFrom-Json).token
$env:CAS_HARNESS_AUTH_TOKEN = $token
```

Verifier results are valid only when protected fleet endpoints are called with `Authorization: Bearer <token>`. If the verifier script or harness does not inject that token, stop and fix the verifier in a separate code PR before claiming deployed verification.

4. Run the deployed fleet control-plane verifier.
5. Provision real Probe Workers with access to the target model weights, compatible runtime hooks, and artifact storage.
6. Confirm workers can register, heartbeat, lease their assigned jobs, and return real Evidence Packet fragment receipts.
7. Only after the deployed verifier passes and the worker fleet is live, run 20B/100B/300B large-model audit tests.

## Phase 1: Confirm PR And Deploy State

1. Confirm PR #97 is merged to `master`.
2. Wait for the `noetic-compass-api` Render service to redeploy from `master`.
3. Confirm the deployed API is reachable:

```powershell
curl.exe -sS https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

This live health check is not the fleet test, but it confirms the API service is awake.

4. Confirm the verifier auth token is set before running protected fleet checks:

```powershell
if (-not $env:CAS_HARNESS_AUTH_TOKEN) { throw "CAS_HARNESS_AUTH_TOKEN is required for fleet verification" }
```

## Phase 2: Run Fleet Contract Verification

From the repo root:

```powershell
cd C:\tmp\cas-harness-enterprise-scale\noetic-compass-scaffold\noetic-compass
python scripts\verify_cas_harness_fleet_deployed.py --base-url https://noetic-compass-api.onrender.com
```

The verifier is a deployed control-plane check. It should verify:

- create 300B distributed session with `minimum_worker_count`
- dispatch assignments
- prepare fleet jobs
- unregistered worker cannot lease
- registered worker can lease only its assigned job
- receipt requires Evidence Packet fragment
- partial fleet merge remains blocked
- no `ACCEPT` is produced before verifier review

Passing this verifier means the deployed receipt gate is working. It does not mean a 300B model loaded, completed inference, or produced a final verifier verdict.

## Phase 3: Failure Conditions

Stop and fix before demo if any of these happen:

- 300B run completes from a plan alone
- 20B/100B/300B completion is claimed without real model weights and a registered worker fleet
- unregistered worker leases a job
- protected fleet endpoints succeed without verifier auth
- receipt is accepted without active lease token
- completed receipt is accepted without `evidence_packet_fragment_ref`
- merge succeeds with missing worker receipts
- API emits `ACCEPT` or numeric confidence from fleet merge alone

## Phase 4: UI Inspection

Once Audit Console wiring lands, inspect:

- fleet registry count
- leased jobs
- stale workers
- completed fragments
- merged packet status
- verifier gate status

The UI must make it obvious that the scale plan is not the audit. The audit only becomes verifier-ready after real fleet receipts exist.

## Large-Model Test Prerequisites

Do not start or announce 20B/100B/300B audit tests until all of these are true:

- PR #97 is merged and deployed.
- Verifier auth is configured and used for protected fleet calls.
- The deployed fleet verifier passes.
- Real Probe Workers are provisioned against actual supported model weights.
- Workers can register, heartbeat, lease jobs, and return Evidence Packet fragment receipts.
- The final verdict path is still clearly labeled as verifier-owned, not fleet-merge-owned.
