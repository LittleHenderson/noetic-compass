# The STOP measurement — options revised after tracing the actual code path

**This supersedes the A/B/C framing in `BOOTSTRAP_CIRCULARITY.md`.** That framing was written from the activation rules alone. Tracing the provider path end to end changes two things materially, and one of them invalidates the option I recommended.

---

## What the STOP transport actually requires

`_provider_proxy_handler` refuses before any network work unless **all** of these hold:

1. `_activation_gate` passes — which needs `ACTIVATION_MODE=LIVE` **and** a non-placeholder `DEPLOYMENT_BINDING_SHA256`.
2. `provider_account_id` in the request equals the `PROVIDER_ACCOUNT_ID` environment value — preproduction currently has `UNBOUND`.
3. `_real_proxy_transport` obtains the provider secret from Secrets Manager — preproduction currently has a placeholder ARN.

The transport target is fixed in code: `rest.runpod.io:443`, path root `/v1/pods`.

## Consequence 1 — Option B is now impossible, and my own fix is what closed it

Option B was: emit a **provisional** timing document, use it to activate preproduction `LIVE`, measure the real STOP there, then emit the final document.

That provisional document would need *some* value for `observed_provider_stop_execution_milliseconds`. There is none to put in it. And as of today the harness **refuses any document containing a zero for that field**, on the grounds that zero is the absence of a measurement rather than a measurement.

So Option B cannot start without either fabricating a number or removing the very guard added hours earlier. **Neither is acceptable, so Option B is withdrawn.** It was my recommendation, and it was wrong.

## Consequence 2 — Option B also required spreading the RunPod credential

Even setting the above aside, a real STOP from preproduction needs the **real RunPod API key** placed in the preproduction account's Secrets Manager, plus a real `ProviderAccountId`. That is a second copy of a production credential in a second account, created to run a test. It should not be done casually, and it was not visible in the original framing.

---

## The revised option — A′, and it is better than the old A

**Time the transport, unauthenticated, from a preproduction Lambda with matching region and runtime.**

Issue a request to `https://rest.runpod.io/v1/pods` and time DNS resolution, TLS handshake, and the HTTP round trip to first byte. The provider answers `401`. That response is the measurement.

Why this is materially better than the old Option A:

- **No credential is needed or used.** Nothing is copied anywhere. The RunPod key stays exactly where it is.
- **It cannot stop anything.** There is no pod ID, no authentication, and no mutation. A `401` has no side effect.
- **It measures the part that actually varies.** DNS, TLS and round trip to the exact host and port the guardian uses are the dominant and variable cost. What it omits — the guardian's own dispatch after the gate — is small, in-process, and already visible in the recovery Lambda's measured durations.
- **It is honest about what it is.** It is a transport measurement, not the guardian executing STOP, and it must be labelled that way wherever the number appears.

**What it is not:** it is not the guardian performing a real STOP against a real pod. That remains unobtainable until Gate 4 exists, because a real STOP needs a real pod to stop. **The circularity is genuinely deeper than first recorded: the fully authentic measurement sits behind Gate 4, which itself sits behind Gate 2.**

## Options as they now stand

| | What it is | Credential needed | Can it stop anything | Status |
|---|---|---|---|---|
| **A′** | Unauthenticated transport timing to `rest.runpod.io:443` from preproduction | **None** | **No** | **Available — recommended** |
| ~~B~~ | Provisional document → preproduction `LIVE` → real STOP | Real RunPod key, copied | Yes | **WITHDRAWN — needs a fabricated number the harness now refuses** |
| **C** | Accept three of four; production stays `NO_GO` | None | No | Available |

**A′ still requires owner authorisation**, because it is an outbound network call to the provider's host. It is the smallest such call that can exist: unauthenticated, side-effect-free, and incapable of touching a pod.

## If A′ is chosen, what must be said about the result

- The number is a **transport-path measurement**, never "the guardian's STOP time".
- The document must record that the guardian's own STOP dispatch was **not** included.
- It does **not** discharge the RUNBOOK's requirement for the full exact-ID STOP transport path under a real authorisation. That remains open, behind Gate 4.
- A pass on A′ licenses exactly one sentence: *the transport leg to the provider host completed within the bound, measured from a matching runtime and region.*

## Standing

Gate 1 item 1 remains **`OPEN / NOT RUN`**. Three of four values are measured and in bounds. Nothing here is execution authority, no GPU is authorised, and the A40/Pythia experiment remains **`NOT RUN`** — it has neither passed nor failed.
