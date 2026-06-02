# Doc 16 - Hosted state-ledger shadow enable evidence (2026-06-02)

**Status:** hosted production/Render shadow-mode verification is **VERIFIED under real
HTTP service traffic** after merging `codex/cas-harness-live-run` into `master`.

This is the hosted counterpart to doc 14. The code reached the Render-connected branch,
the hosted API exposed the state-ledger route, and the verifier drove a real distributed
audit lifecycle against `https://noetic-compass-api.onrender.com` while the state ledger
was enabled in shadow mode.

## Release action

- `master` was first fast-forwarded to `origin/master`.
- `codex/cas-harness-live-run` was then fast-forward merged into `master`.
- `master` was pushed to GitHub: `a9f519b..f32a650`.
- The first hosted verifier attempt still returned 404 for `/api/state-ledger/status`,
  meaning Render was still serving the old build.
- After waiting for rollout, the verifier passed against the hosted API.

## Hosted verifier command

```powershell
python scripts\verify_state_ledger_enabled.py `
  --base-url https://noetic-compass-api.onrender.com `
  --require-posture shadow
```

## Observed result

The verifier reported:

```text
posture=enabled_shadow_dict_authoritative
reads_compared=0->95
reads_served=0
divergences_found=0
last_divergence=None
audit_id=cas-dist-3a9e11fe091aa1f2
workers=2
receipts=2
merge status=COMPLETE
gate=ready_for_verifier
pass=true
```

Verbatim status snapshots:

```json
{"posture":"enabled_shadow_dict_authoritative","audit_count":0,"fleet_counts":{"workers":0,"fleet_runs":0,"fragment_refs":0},"divergence_tally":{"reads_compared":0,"reads_served":0,"divergences_found":0,"last_divergence":null}}
```

```json
{"posture":"enabled_shadow_dict_authoritative","audit_count":0,"fleet_counts":{"workers":0,"fleet_runs":0,"fragment_refs":0},"divergence_tally":{"reads_compared":95,"reads_served":0,"divergences_found":0,"last_divergence":null}}
```

## What this proves

- The state-ledger code is now on the Render-connected production branch.
- The hosted service exposes `GET /api/state-ledger/status`.
- The hosted service booted in the expected posture:
  `enabled_shadow_dict_authoritative`.
- A real hosted distributed audit lifecycle completed through the HTTP API.
- The dicts still served reads while the ledger shadow-compared them.
- The shadow watch accumulated 95 comparisons with zero divergence.

## What this does not prove

- **Not read-authority.** `NC_STATE_LEDGER_READ_AUTHORITY` stayed false. The next
  gate is a separate hosted run with `--require-posture read-authority`, watching
  `reads_served`, not `reads_compared`.
- **Not Phase 4.** `_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, and
  `_FRAGMENT_REFS` were not deleted.
- **Not host-loss durability.** Render free plan storage is ephemeral; this proves
  hosted shadow correctness for one uptime, not persistence across host loss.
- **Not full production launch.** WORM, live worker route, external CRM sync,
  billing/accounts, compliance, and UI claim ladder work remain open.

## Next gate

The next hosted ledger gate is:

```powershell
python scripts\verify_state_ledger_enabled.py `
  --base-url https://noetic-compass-api.onrender.com `
  --require-posture read-authority
```

That gate should only run after the owner explicitly chooses to flip
`NC_STATE_LEDGER_READ_AUTHORITY=true`. In read-authority posture the live odometer is
`reads_served`; `reads_compared` is expected to freeze because dict-vs-ledger shadow
comparison is no longer the serving mode.
