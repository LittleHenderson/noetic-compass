# RunPod pre-create guardian — offline design

Status: `DESIGN_ONLY / OFFLINE_ONLY / NOT_DEPLOYED / NO EXECUTION AUTHORITY`

This design addresses one narrow failure: the create-capable launcher sends
`POST /v1/pods`, RunPod creates a billed Pod, and the launcher crashes before it
persists the returned Pod ID.  The current ID-bound stop supervisor cannot stop
an ID that it never received.

## Separation of authority

The future deployment has two principals:

1. The launcher can send exactly one pre-hashed create request.  It cannot
   declare the guardian armed.
2. The independently running guardian can inventory Pods, GET one Pod, and STOP
   one Pod.  It cannot create or DELETE a Pod and contains no model path.

The offline reference implementation is
`tools/runpod_open_weight_canary_v2/precreate_guardian_offline.py`.  It accepts
only an injected provider adapter.  It has no HTTP, GitHub, credential,
subprocess, create, DELETE, or model implementation.

The current transaction producer's `PrecreateGuardian.arm_precreate()` hook is
the intended integration point, but its present
`cas_runpod_precreate_guardian_receipt.v1` validation does not yet admit this
design's account inventory, GitHub run/repository/attempt, or provider-endpoint
bindings.  Its later `bind_exact_pod()` call happens only after the HTTP 201 was
successfully parsed and therefore cannot cover a crash before that point.  Do
not substitute its local `build_guardian_receipt()` helper for an independently
running guardian.  Integration requires an explicit producer schema change;
this offline tranche intentionally does not edit that concurrently changing
file.

## Required protocol

1. The launcher generates an exact name whose final 32 lowercase hexadecimal
   characters contain 128 random bits.  It serializes the exact create-request
   bytes once and computes their SHA-256.
2. Before any create POST, it dispatches an independent guardian workflow.  The
   arm input binds the exact name, exact request SHA-256, source commit, OCI
   digest, creation-window start/end, hard-stop deadline, GitHub repository/run
   ID/run attempt/SHA, and exact provider create endpoint.
3. The guardian performs an account-wide inventory.  It refuses to arm if the
   exact name already exists.  Its create-new canonical arm receipt records the
   full ID/name projection and its hash.  The offline reference can construct
   that receipt for state-machine tests, but it **cannot authorize a live POST**:
   a deployed service must separately prove that an independently supervised
   polling lease is already live before releasing the receipt to the launcher.
4. The launcher must receive and verify that exact durable arm receipt before
   POST.  It must POST the same bytes whose SHA was armed.  A timeout or missing,
   stale, mismatched, or non-durable acknowledgement means **no POST**.
5. The guardian continues without depending on the launcher.  It binds an ID
   only when the exact name has one inventory match, the ID was absent from the
   pre-arm inventory, the ID is not protected, and provider `createdAt` lies in
   the bound creation window.  Provider `lastStartedAt` may supply the same
   bound birth/start evidence when `createdAt` is unavailable; when both are
   present, both must lie in-window.  Zero matches means keep polling.  Multiple
   matches, a protected ID, an old ID, a missing timestamp, or an out-of-window
   timestamp means no blind STOP.
6. After binding, the immutable ID is authoritative for recovery.  Later name
   edits cannot defeat containment.  The effective deadline is the earlier of
   the armed maximum and 1,800 seconds after the earliest admitted provider
   birth/start timestamp.  The armed maximum itself cannot exceed 1,800 seconds
   after the creation-window start.  The guardian begins bounded STOP attempts
   at the effective deadline minus 90 seconds, requires a successful STOP no
   later than that deadline, and polls the same ID until `EXITED` or
   `TERMINATED`.  It never DELETEs the Pod.
7. A no-target result is
   `UNRESOLVED_NO_UNIQUE_TARGET_BY_DEADLINE`, not evidence that no Pod exists and
   not evidence of cost containment.

## What this closes

Conditionally, this closes the launcher crash window only after an external
supervisor proves that the independent guardian is durably armed **and already
polling**.  A same-process callback cannot supply that proof and the offline
helper deliberately rejects any attempt to use it as live launch authority.
Once the external condition is real, loss of the launcher's process and HTTP
201 body no longer loses the only route to the new Pod ID.  The guardian can
recover that ID from the account inventory and STOP it by the effective
deadline.

The operational metaphor is a coat check.  The launcher may lose the numbered
ticket (the HTTP 201 ID), but the guardian already recorded that no coat had the
new 128-bit name, watches for exactly one new coat with that name, and then uses
its sewn-in immutable ID to retrieve it.

## Residual authenticity and operational gaps

This does **not** make the experiment launch-ready:

- A self-hashed GitHub receipt is not a RunPod signature.  GitHub OIDC-backed
  signing or external append-only anchoring is still absent.
- Name plus `createdAt` is correlation, not cryptographic proof that the armed
  request bytes created the observed Pod.  The real HTTP request/201 bytes and
  headers still need atomic durable capture by the transaction producer.
- The reference code cannot prove that the launcher POSTed the armed bytes.  A
  reviewed launcher/guardian handshake and exact-byte transport binding remain
  required.
- The reference code cannot prove process or workflow liveness.  Its combined
  same-process convenience entry point always rejects; production needs a
  durable lease/heartbeat observed from outside the guardian process before
  the launcher is allowed to POST.
- The offline reference does not atomically consume a globally unique
  authorization ID.  That one-use consume must live in the independent durable
  guardian, not in a caller-selected local state directory.
- RunPod inventory may be delayed, incomplete, or unavailable.  If the Pod is
  not visible before the deadline, STOP-by-deadline cannot be guaranteed.
- A caller could rename the Pod before first discovery; immutable-ID recovery
  starts only after the first exact-name binding.
- GitHub queue delay, runner loss, secret loss, API outage/rate limiting, clock
  error, and STOP failure can still defeat containment.  A deployment needs
  monitored liveness, alerting, bounded retries, and ideally a second
  independently hosted stop path.
- Provider `createdAt`, inventory objects, STOP responses, and terminal states
  are provider-reported observations, not billing settlement.
- The hard-coded protected-ID set must be source-reviewed and current before
  deployment.
- The offline tests use fake adapters.  They prove state-machine behavior only;
  they do not prove RunPod field semantics, GitHub delivery, permissions,
  persistence, latency, or real STOP behavior.

Therefore this tranche can be classified only as
`ENGINEERED / OFFLINE-TESTED / NOT DEPLOYED`.  A live create remains `NO-GO`
until a reviewed transaction producer, durable independent workflow, real
provider contract test, authenticated/anchored receipts, and owner authorization
for another Pod all exist.
