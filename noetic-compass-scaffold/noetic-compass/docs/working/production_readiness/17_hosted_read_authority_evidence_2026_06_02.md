# Doc 17 - Hosted state-ledger read-authority evidence (2026-06-02)

**Status:** hosted production/Render read-authority verification is **VERIFIED under
real HTTP service traffic**.

This is step 4 of the state-ledger rollout. The hosted service was moved from shadow
mode (`enabled_shadow_dict_authoritative`) to read-authority mode
(`enabled_ledger_read_authoritative`) after the hosted shadow proof in doc 16 passed.

## Release action

- `NC_STATE_LEDGER_READ_AUTHORITY` was changed from `"false"` to `"true"` in both
  `render.yaml` and `infra/render.yaml`.
- The change was committed as `f1e572e`:
  `infra: enable hosted state-ledger read authority`.
- `master` was pushed to GitHub: `02b6f9c..f1e572e`.
- After waiting for Render rollout, the hosted verifier passed in read-authority mode.

## Hosted verifier command

```powershell
python scripts\verify_state_ledger_enabled.py `
  --base-url https://noetic-compass-api.onrender.com `
  --require-posture read-authority
```

## Observed result

The verifier reported:

```text
posture=enabled_ledger_read_authoritative
reads_served=0->92
reads_compared=0
divergences_found=0
last_divergence=None
audit_id=cas-dist-bb51e79a414a9e62
workers=2
receipts=2
merge status=COMPLETE
gate=ready_for_verifier
pass=true
```

Verbatim status snapshots:

```json
{"posture":"enabled_ledger_read_authoritative","audit_count":0,"fleet_counts":{"workers":0,"fleet_runs":0,"fragment_refs":0},"divergence_tally":{"reads_compared":0,"reads_served":0,"divergences_found":0,"last_divergence":null}}
```

```json
{"posture":"enabled_ledger_read_authoritative","audit_count":0,"fleet_counts":{"workers":0,"fleet_runs":0,"fragment_refs":0},"divergence_tally":{"reads_compared":0,"reads_served":92,"divergences_found":0,"last_divergence":null}}
```

## What this proves

- The hosted service booted in the expected posture:
  `enabled_ledger_read_authoritative`.
- A real hosted distributed audit lifecycle completed through the HTTP API while public
  get/list reads were served from the ledger.
- The read-authority odometer `reads_served` moved from 0 to 92 under hosted traffic.
- `divergences_found` stayed 0 and `last_divergence` stayed `null`.
- Fleet merge still reached `COMPLETE` / `ready_for_verifier`.

## Why `reads_compared` stayed 0

This is expected. `reads_compared` is the shadow-mode counter. It only moves when the
dicts serve reads and the ledger is checked behind them. In read-authority posture, the
ledger serves reads directly, so the live odometer is `reads_served`.

## What this does not prove

- **Not Phase 4.** `_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, and
  `_FRAGMENT_REFS` were not deleted.
- **Not host-loss durability.** Render free plan storage is ephemeral; this proves
  hosted read-authority correctness for one uptime, not persistence across host loss.
- **Not full production launch.** WORM, live worker route, external CRM sync,
  billing/accounts, compliance, and UI claim ladder work remain open.

## Next gate

Phase 4 remains held. Before deleting process-global dictionaries, the `_FRAGMENT_REFS`
replay guard must be re-pointed off the in-RAM set and doc 13's grep-clean plan must be
executed deliberately. This document does not authorize deletion.
