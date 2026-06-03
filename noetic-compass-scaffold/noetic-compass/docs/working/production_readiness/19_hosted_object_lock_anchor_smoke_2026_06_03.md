# Hosted Object-Lock Anchor Smoke - 2026-06-03

**Status: VERIFIED for hosted throwaway deploy smoke.** This is not the final Pythia-160M packet
anchor. It proves the hosted Object-Lock wiring around S3 is real before anchoring the real packet.

## What was run

Command:

```powershell
python scripts\verify_evidence_anchor_deployed.py --base-url https://noetic-compass-api.onrender.com --require-anchor-mode s3 --require-object-lock
```

The verifier:

1. fetched a JWT from `/auth/token`;
2. created a throwaway distributed audit for `deploy-check/open-weight-ledger-watch-20b`;
3. reused the hosted registered workers `probe-worker-01` and `probe-worker-02`;
4. submitted two verifier fragment receipts;
5. merged a throwaway Evidence Packet;
6. verified the packet anchor via `/evidence/{trace_id}` and `/evidence/{trace_id}/verify`;
7. failed unless anchor mode was `s3` and Object Lock retention was active.

## Result

PASS.

Trace ID:

```text
cas-dist-ecb55108b0a964da-distributed-merge
```

Audit ID:

```text
cas-dist-ecb55108b0a964da
```

Hosted verifier output:

```text
[01] Create a distributed audit
     OK - created cas-dist-ecb55108b0a964da with 2 planned worker(s)
[02] Dispatch and prepare fleet
     OK - fleet prepared
[03] Lease every job and submit verifier fragment receipts
     OK - 2 receipt(s) accepted
[04] Merge packet and run verifier
     OK - merged packet cas-dist-ecb55108b0a964da-distributed-merge; verifier ACCEPT
[05] Fetch Evidence Packet and verify anchor
     OK - anchor status=anchored mode=s3 uri=s3://cas-harness-runpod-92754088/cas-harness/evidence-anchors/cas-dist-ecb55108b0a964da-distributed-merge/bc9bec027c1d528aff55d97382fa6b12e36ca41e8ded90a78c70d8b3ae4b2179.json

PASS: deployed Evidence Packet anchor smoke passed.
Trace ID: cas-dist-ecb55108b0a964da-distributed-merge
```

## Anchor receipt

From hosted `GET /evidence/cas-dist-ecb55108b0a964da-distributed-merge`:

```json
{
  "status": "anchored",
  "mode": "s3",
  "anchor_uri": "s3://cas-harness-runpod-92754088/cas-harness/evidence-anchors/cas-dist-ecb55108b0a964da-distributed-merge/bc9bec027c1d528aff55d97382fa6b12e36ca41e8ded90a78c70d8b3ae4b2179.json",
  "bucket": "cas-harness-runpod-92754088",
  "key": "cas-harness/evidence-anchors/cas-dist-ecb55108b0a964da-distributed-merge/bc9bec027c1d528aff55d97382fa6b12e36ca41e8ded90a78c70d8b3ae4b2179.json",
  "object_lock_mode": "GOVERNANCE",
  "object_lock_retain_until": "2026-07-03T14:56:13.157525+00:00",
  "retention_days": 30
}
```

From hosted `POST /evidence/cas-dist-ecb55108b0a964da-distributed-merge/verify`:

```text
overall: all_match
merged_packet_external_anchor: match=true
notes: S3 anchor object was re-read, its manifest commits to this packet hash and hash-log entry,
and Object Lock GOVERNANCE retention is active until 2026-07-03T14:56:13+00:00
```

## What this proves

- Hosted Render has `CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3` effectively active.
- The hosted service is writing to bucket `cas-harness-runpod-92754088`.
- The hosted service is using an S3 prefix under `cas-harness/evidence-anchors`.
- The hosted service can write the anchor manifest.
- The hosted service can re-read the anchor manifest.
- The hosted service can stamp Object Lock `GOVERNANCE` retention.
- The IAM credentials include the needed Object Lock retention permission, not just basic `PutObject`.

## What this does not prove

- This is not the final Pythia-160M packet anchor.
- This is not a customer production `ACCEPT`.
- This does not close matched controls for the live path.
- This does not prove every future packet family is discoverable by the static registry.

The next WORM step is the real packet anchor:

```text
POST /evidence/pythia-160m-stage9-40e-readout-20260531/anchor?require_object_lock=true
```

That should be run only when the intended packet/regeneration diff is settled.
