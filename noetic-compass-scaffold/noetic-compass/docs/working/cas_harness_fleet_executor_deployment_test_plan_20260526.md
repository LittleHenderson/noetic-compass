# CAS Harness Fleet Executor Deployment Test Plan

Date: 2026-05-26

Purpose: verify that PR #97 is actually live after merge and that the deployed CAS Harness API enforces the worker-fleet gates required for 20B/100B/300B open-weight audits.

## Phase 1 - Verify PR #97 Is Merged

- Confirm PR #97 is merged into `master`.
- Confirm `master` contains the distributed audit runner and fleet executor changes.
- Hard failure: do not test production behavior from a branch, preview, or stale local checkout.

## Phase 2 - Wait For Render API Deploy

- Wait for the `noetic-compass-api` Render service to redeploy from `master`.
- Confirm the latest deploy finished successfully before running API checks.
- Hard failure: if Render is still building, failed, or serving an older commit, stop.

## Phase 3 - Run API Health Check

- Check the API base URL responds:
  - `https://noetic-compass-api.onrender.com/health`
- Check Atlas live real-mode status still reports real weights when applicable:
  - `https://noetic-compass-api.onrender.com/atlas/live/health/realmode`
- Hard failure: if health fails, real-mode reports fake mode unexpectedly, or the API returns stale route errors, stop.

## Phase 4 - Run Fleet Verification Script

Run the deployed fleet verification script against:

```text
https://noetic-compass-api.onrender.com
```

The script must verify:

- Create a 300B distributed audit session.
- Dispatch worker assignments.
- Prepare fleet jobs.
- Confirm an unregistered worker cannot lease a job.
- Register a worker.
- Lease a job with a registered worker.
- Submit a completed worker receipt with an `evidence_packet_fragment_ref`.
- Confirm merge blocks while any assigned job lacks a receipt.
- Confirm the run cannot emit `ACCEPT` from merge alone.

Hard failure: any 300B run that advances without worker registration, job leases, worker receipts, and Evidence Packet fragments is invalid.

## Phase 5 - Manual Audit Console Inspection

After UI wiring lands, inspect the Audit Console manually:

- Confirm the fleet panel shows worker registry status.
- Confirm leases, stale workers, receipts, merged packet state, and verifier gate are visible.
- Confirm users can tell the difference between a scale plan and a real fleet-backed audit.
- Confirm the UI does not imply a valid 300B audit before worker receipts and Evidence Packet fragments exist.

Hard failure: if the UI makes a plan look like a completed audit, stop and fix the wording/state gate.

## Non-Negotiable Validity Rule

A 300B CAS Harness run is not valid unless all of the following exist:

- Registered workers.
- Assigned leases.
- Fresh heartbeats.
- Completed worker receipts.
- Evidence Packet fragments from those workers.
- A merged Evidence Packet.
- A verifier decision layer over the merged evidence.

Until those exist, the only honest product state is pending, blocked, failed, or `FLAG_FOR_HUMAN_REVIEW`.
