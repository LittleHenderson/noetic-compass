# Option A′ — transport probe result, and why the number still cannot go in the document

**Measured 2026-08-21 from preproduction account `063693212118`, `us-west-2`.**

---

## The measurement

A Lambda matching the guardian's stop proxy exactly — `python3.12`, `arm64`, `128 MB`, `8 s` timeout, same region — issued five unauthenticated `GET` requests to `https://rest.runpod.io/v1/pods`.

| sample | DNS | TCP | TLS | to first byte | **total** | status |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 59 ms | 360 ms | 65 ms | 426 ms | **908 ms** | `401` |
| 2 | 1 ms | 230 ms | 58 ms | 352 ms | **639 ms** | `401` |
| 3 | 1 ms | 265 ms | 60 ms | 341 ms | **666 ms** | `401` |
| 4 | 1 ms | 221 ms | 64 ms | 405 ms | **689 ms** | `401` |
| 5 | 1 ms | 222 ms | 58 ms | 403 ms | **683 ms** | `401` |

**Worst case `908 ms` against an `8,000 ms` bound — an 8.8× margin.**

**Every sample returned `401`,** which is the safety property, not a footnote. The probe asserts the status is an auth challenge and returns `ok: false` otherwise. A `200` would have meant a credential reached it from somewhere; five `401`s prove none did.

**Safety, by construction rather than by care:** no `Authorization` header is built anywhere in the source, so no code path can leak one. No pod ID appears — `STOP` targets `/v1/pods/{id}`, and the probe touches only the collection root, so it cannot address a pod even accidentally. The method is `GET`. The execution role carries `AWSLambdaBasicExecutionRole` **only** — no Secrets Manager, no EC2, no S3.

---

## Why this number still cannot be written into the timing-evidence document

The field is named `observed_provider_stop_execution_milliseconds`. What was measured is DNS, TLS and an HTTP round trip — **not the guardian executing a STOP.**

The 18-field schema was checked for any way to mark a value as a substitute. There is none. `measurement_kind` is fixed at `EMPIRICAL_NON_GUARANTEE`, which describes the *class* of evidence — empirical rather than guaranteed — not whether a particular value is a stand-in. `source_evidence_manifest_sha256` points at raw data but asserts nothing about substitution.

**So writing `908` into that field would silently launder a transport measurement into an authentic-looking guardian STOP execution time.** The document would be valid, hashable, and wrong in the one way that matters: a reader could not tell.

**No document has been emitted.** That is the correct outcome, and it is the same principle that refused a zero earlier today: a number that did not come from the thing the field names does not belong in that field.

## The schema limitation is itself a finding

**The timing-evidence document has no way to record that a measurement is a proxy.** Every value in it reads as directly observed. That is fine while every value *is* directly observed, and becomes a defect the moment one is not — which is exactly the situation the bootstrap circularity forces.

Options, and this is an owner and reviewer decision:

- **Accept the proxy**, recording its nature **outside** the document — in this file, the tracker, and the spec sheet — and knowing the document itself cannot carry that caveat. Weaker than it looks, because the caveat travels separately from the artifact.
- **Extend the schema** so a value can be marked as substituted. This changes a hash-locked contract and the runtime that validates it, so it is a real change with real review cost, not a tweak.
- **Wait for Gate 4.** A genuine STOP needs a real pod to stop. That is behind Gate 4, which is behind Gate 2, which is behind this measurement — the circularity again.

## Standing

Three of four values are measured, real, and in bounds: recovery gap **`125,424 ms`**, worker startup **`190 ms`**, missed ticks **`1`**, over **`18`** samples. The fourth now has a **real transport measurement of `908 ms`** that is in bounds but **is not the thing the field names**.

Gate 1 item 1 remains **`OPEN / NOT RUN`**. No timing-evidence document exists. Nothing here is execution authority, no GPU is authorised, production remains `INERT` with ledger `0` and zero instances, and the A40/Pythia experiment remains **`NOT RUN`** — it has neither passed nor failed.

**Cleanup:** the probe Lambda `cas-harness-preprod-transport-probe` and role `cas-preprod-transport-probe-role` exist in preproduction only and can be deleted at any time; they hold no data and no permissions beyond logging.
