# CAS_ORDERED_ENCODER_DIAGNOSTIC_001 launch binding

Status: source prepared; 38 pure launcher tests passed. The real launcher config
also passed the probe's validator. No provider call, reservation, CUDA work,
checkpoint loading, or training occurred during launcher preparation.

This profile measures numeric encoders. It does not establish learned reasoning
accuracy or completion of the cognitive-machine vision. Historical profiles and
their implementation remain unchanged.

## Frozen execution scope

- One job on one AWS `g7.2xlarge` in `us-west-2`.
- Reservation ceiling `$7.00`; automatic retries `0`.
- Training `false`; optimizer updates `0`; checkpoints `0`.
- Probe seed `20260916`; actual inner subprocess timeout `1200` seconds.
- Existing lifecycle bootstrap and instance limits remain `3600` and `7200`
  seconds. They include setup/collection/teardown and are not the diagnostic's
  computation allowance.
- Worker: `ordered_encoder_worker.py`.
- Entrypoint: `cas_meta2.graph_teaching.ordered_encoder_probe.run`.
- Job pattern: `cas-meta2-orderedencoder-YYYYMMDDHHMMSS-xxxxxxxx` (eight hex digits).

The adapter reuses the proven contrast worker scaffold, shared source-member
resolver, shared evidence transport, and candidate provider lifecycle. It binds
its own dispatch, schemas, terminal-failure status, evidence contract, and zero-
update manifest budget. The two existing hash-pinned wheels support the reused
environment/import path; no checkpoint or retained training artifact is packaged.

The request is inert. The authority binds its exact source/archive/manifest,
owner-record bytes, input inventory, execution design, evidence contract, and
nested worker configuration. Top-level and nested bounds cannot disagree.
The owner record must use `cas-ordered-encoder-owner/1`, identify this candidate,
preserve a nonempty exact owner quote, and state all `BOUNDS` fields. The existing
lifecycle also enforces one use of this owner record and rejects an already
reserved job before spending.

Required delivery comprises `results/result.json`, its SHA-256 sidecar,
`results/artifacts/manifest.json`, `encoder_probe.json`, and `measurements.json`.
The collector retains the predeclared contract independently of worker output.
Verified collection precedes evidence deletion. Failure evidence is preserved.

## Canonical campaign ledger

The new checkout contains a historical ledger copy. It must not become a second
spending ledger. Both the CLI and `execute()` require an explicit ledger path;
the provider and lifecycle must resolve to that same existing file inside the
CNCM homebase. The CLI has no default ledger for execution.

The coordinator's active ledger is:

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json`

Before execution, the coordinator must read its current revision and record its
path and exact before/after identities. After the lifecycle finishes, the
coordinator can copy the verified updated ledger/history into the new checkout
for publication. This adapter creates no cap change, amendment, or refund.

## Executable sequence

Run from the new checkout's `research/CAS_META_2_COMPOSITION` directory.

1. Freeze and commit the probe, encoder, launcher, and tests before packaging.
   The package builder rejects working packaging code or input bytes that differ
   from the specified Git commit. Use a fresh package directory each time.

```powershell
python -B -m aws.ordered_encoder_launch
$sourceSha = (git rev-parse HEAD).Trim()
python -B -c "from aws.ordered_encoder_launch import build_ordered_package; import sys; print(build_ordered_package(sys.argv[1],source_sha=sys.argv[2]))" records/ordered_encoder_001/package_001 $sourceSha
```

2. Rehearse the generated archive and verify every member against its manifest.
   Prepare a new exact owner record, inert request, and authority from the package
   receipt. Use `worker_config(job, source_sha=source_sha)` for the authority's
   nested config; the provider adds only the real bucket. Bind `frozen_inputs_hash()`,
   `digest(canonical(DESIGN))`, and `contract_digest(evidence_contract())`.
   Request/authority schema constants and all required fields are enforced by
   `validate_request()` and `validate_authority()`.

3. Only after coordinator review and the existing owner authorization are bound,
   execute with the explicit canonical ledger. Set these paths to the reviewed
   files; the command hashes their actual bytes.

```powershell
$request = 'records/ordered_encoder_001/launch_request.json'
$authority = 'records/ordered_encoder_001/launch_authority.json'
$owner = 'records/ordered_encoder_001/OWNER_AUTHORIZATION.json'
$ledger = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json'
$requestHash = (Get-FileHash -LiteralPath $request -Algorithm SHA256).Hash.ToLowerInvariant()
$authorityHash = (Get-FileHash -LiteralPath $authority -Algorithm SHA256).Hash.ToLowerInvariant()
python -B -m aws.ordered_encoder_launch --execute --request $request --request-sha256 $requestHash --authority $authority --authority-sha256 $authorityHash --owner-authorization $owner --ledger-path $ledger --receipt-dir records/ordered_encoder_001/job_001
```

No launch was performed while preparing this binding. Source freeze, package
rehearsal, exact authority files, and current canonical-ledger review remain the
coordinator's prelaunch work.
