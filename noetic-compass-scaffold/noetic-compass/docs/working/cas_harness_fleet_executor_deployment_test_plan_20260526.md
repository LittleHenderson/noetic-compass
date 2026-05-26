# CAS Harness Fleet Executor Deployment Test Plan

Date: 2026-05-26

## Goal

After PR #97 merges and Render redeploys, prove the deployed API enforces the fleet executor contract for large open-weight audits.

The test must prove the negative case too: a 300B run is not valid just because a scale plan exists. It must require worker registration, job leases, heartbeats, Evidence Packet fragment receipts, and a blocked merge until every assigned job returns evidence.

## Phase 1: Confirm PR And Deploy State

1. Confirm PR #97 is merged to `master`.
2. Wait for the `noetic-compass-api` Render service to redeploy from `master`.
3. Confirm the deployed API is reachable:

```powershell
curl.exe -sS https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

This live health check is not the fleet test, but it confirms the API service is awake.

## Phase 2: Run Fleet Contract Verification

From the repo root:

```powershell
cd C:\tmp\cas-harness-enterprise-scale\noetic-compass-scaffold\noetic-compass
python scripts\verify_cas_harness_fleet_deployed.py --base-url https://noetic-compass-api.onrender.com
```

The script should verify:

- create 300B distributed session with `minimum_worker_count`
- dispatch assignments
- prepare fleet jobs
- unregistered worker cannot lease
- registered worker can lease only its assigned job
- receipt requires Evidence Packet fragment
- partial fleet merge remains blocked
- no `ACCEPT` is produced before verifier review

## Phase 3: Failure Conditions

Stop and fix before demo if any of these happen:

- 300B run completes from a plan alone
- unregistered worker leases a job
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
