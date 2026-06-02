# Doc 15 — Hosted ledger enable: runbook + watch (2026-06-02)

**Status: PREPARED, not VERIFIED.** Everything below is ready to run against hosted
production (Render). It has **not** been executed there yet, because doing so needs a
deploy decision only the repo owner can make (see "The one blocker" below). Do **not**
read this doc as evidence the hosted ledger is enabled — that evidence will be a future
doc 16, written only after a real hosted watch passes.

Doc 14 is the precedent: it VERIFIED steps 1–3 (shadow posture, zero divergence) under a
real local HTTP server. This doc carries the same watch to the hosted service and is honest
about the two things hosted adds — a deploy gate, and free-tier ephemerality.

## The one blocker (needs the owner, not me)

Render service `noetic-compass-api` deploys the **`master`** branch (`autoDeployTrigger:
commit`). **All** of the state-ledger code — the `LedgerMirror`, the bootstrap, the
`/api/state-ledger/status` route, the verifier — lives on branch
**`codex/cas-harness-live-run`**, which is **37 commits ahead of `origin/master`**. None of
it is on `master`. So the hosted service is **not** running this code yet, and cannot be
until one of these happens:

- **(A) Merge `codex/cas-harness-live-run` → `master` and push.** Render auto-deploys
  `master` on commit. This is the clean path. It also carries the `render.yaml` flag block
  (below) into the deployed blueprint.
- **(B) Point the Render service at the branch temporarily** (dashboard → service →
  Settings → Branch, or `branch:` in `render.yaml`), deploy, watch, then revert.

Both are owner decisions. **I am not performing the merge or the branch switch
autonomously** — it is an irreversible push to the production branch and is explicitly the
owner's call. This runbook is staged so that the moment the owner says "go," the watch is a
single command.

### Env-var caveat (verify, don't assume)

`render.yaml` on this branch already declares the enable flags:

```yaml
- key: NC_STATE_LEDGER_ENABLED
  value: "true"
- key: NC_STATE_LEDGER_READ_AUTHORITY
  value: "false"          # steps 1-3 only; step 4 flips this
- key: NC_STATE_LEDGER_PATH
  value: "/tmp/state_ledger.db"
```

If the Render service is **blueprint-synced**, merging path (A) applies these on the next
deploy. If the service was created from the dashboard and is **not** blueprint-synced, these
keys must be set in the dashboard by hand. **Check which mode the service is in before
relying on the file** — don't assume the blueprint wins. The honesty rule: the watch reads
`GET /api/state-ledger/status` first and refuses to proceed unless the posture is actually
enabled, so a missed env var fails loud at step 2, it does not silently pass.

## Free-tier ephemerality (what hosted does NOT add)

Render `plan: free` gives an **ephemeral** filesystem: `/tmp` is wiped on every deploy and
every cold-start. So `/tmp/state_ledger.db` is a **fresh SqliteStateStore on each boot**.
That is fine for this watch and dishonest to oversell:

- **Fine for the divergence watch.** Divergence is dict-vs-ledger *within one running
  process*. A fresh ledger that dual-writes and shadow-compares cleanly across a lifecycle
  proves exactly what doc 14 proved — read fidelity and dual-write landing — regardless of
  whether the file survives a restart.
- **Not durability / host-loss survival.** A wiped-on-deploy file is the opposite of
  durable. Multi-host Postgres durability was verified separately (commit `c32f639`); this
  hosted free-tier watch does **not** re-prove it and must not be cited as durability
  evidence.

## Posture 1 — shadow watch (steps 1–3, `READ_AUTHORITY=false`)

This is the hosted mirror of doc 14. Run it **first**, and keep it clean before going near
step 4.

```
C:/Python314/python.exe scripts/verify_state_ledger_enabled.py \
  --base-url https://noetic-compass-api.onrender.com \
  --require-posture shadow \
  --min-reads 1 --rounds 3 \
  --out-dir .tmp/ledger_enable/hosted_shadow
```

Auth: on Render `NC_JWT_SECRET` is **server-generated** (`generateValue: true`) and not
known to the operator, so the watch mints its own demo JWT via `POST /auth/token` (its
default). You do **not** pass `--bearer-token` for hosted. The server verifies the token it
just signed.

Pass criteria (the script enforces all of them and exits non-zero otherwise):

- `posture == enabled_shadow_dict_authoritative` at step 2 (gate `ledger-enabled`).
- The full audit lifecycle runs `200 OK` end to end: create → dispatch → register → prepare
  → lease/receipt → merge `COMPLETE`. No real model inference — a synthetic open-weight 20B
  descriptor drives pure lifecycle traffic.
- `reads_compared` grows by ≥ `--min-reads` under our traffic (gate `reads-grew`).
- `divergences_found == 0` and `last_divergence == null` (gate `zero-divergence`).

First request after an idle free dyno cold-starts slowly; `--health-timeout` defaults to
120 s to absorb that.

## Posture 2 — read-authority watch (step 4, `READ_AUTHORITY=true`)

**Gated behind a clean Posture-1 run.** Flip `NC_STATE_LEDGER_READ_AUTHORITY=true` (redeploy),
then:

```
C:/Python314/python.exe scripts/verify_state_ledger_enabled.py \
  --base-url https://noetic-compass-api.onrender.com \
  --require-posture read-authority \
  --min-reads 1 --rounds 3 \
  --out-dir .tmp/ledger_enable/hosted_readauth
```

Pass criteria mirror Posture 1, with one critical substitution the next section explains:
posture must be `enabled_ledger_read_authoritative`, and the odometer that must grow is
**`reads_served`**, not `reads_compared`.

## The honesty asymmetry (read this before trusting step 4's green)

Directive for step 4 literally asked to watch `reads_compared > 0`. **That is structurally
impossible under read-authority, and discovering why is the load-bearing finding here.**

- `reads_compared` increments **only inside `shadow_compare`**, which only runs while the
  **dicts are authoritative** (Phases 1–2). The live read sites call `shadow_compare` to
  cross-check the ledger against the dict that just served the read.
- The moment read-authority flips, those same read sites call `read_payload` /
  `read_all_payloads` and **serve from the ledger directly — no dict to compare against**.
  So `shadow_compare` stops firing and `reads_compared` **freezes**. Watching it would make
  a *correctly working* read-authority deployment look dead.
- The honest Phase-3 denominator is a **separate odometer, `reads_served`**, added for
  exactly this: it ticks once per authoritative ledger read (`read_payload` +1,
  `read_all_payloads` +1 per call, not per row; a propagating `StateStoreError` does **not**
  tick — a read the ledger couldn't answer is not a serve). Under read-authority,
  `reads_compared` freezes and `reads_served` climbs. The verifier already picks the
  posture-appropriate odometer automatically.

**What each watch actually proves (they are not equal):**

| Watch | Zero divergence means | Read fidelity re-proven? |
|---|---|---|
| Shadow (Posture 1) | every ledger read **matched** the dict that served it | **Yes** — direct |
| Read-authority (Posture 2) | dual-writes didn't fail; dicts remain a valid rollback target | **No** — `shadow_compare` isn't running |

This is **why step 4 stays gated behind a clean shadow run.** Read-authority's green is a
weaker guarantee: it confirms the ledger is the sole read authority and dual-writes are
clean, but it does **not** independently re-prove that ledger reads equal dict reads —
because nothing is comparing them anymore. The shadow watch is the only place read fidelity
is proven, so it must be clean and sustained *before* the dicts stop serving. The ordering
in the directives is correct; this finding reinforces it rather than changing it.

## Next gates (not done here)

1. **Run Posture 1 hosted** once the owner clears the deploy blocker → write doc 16 with the
   verbatim before/after status and `result.json`.
2. **Run Posture 2 hosted** only after Posture 1 is clean and sustained.
3. **Phase 4 (dict deletion) stays HELD** until read-authority is proven *and* the
   `_FRAGMENT_REFS` replay guard is re-pointed off the in-RAM set (doc 13). Neither is done.
