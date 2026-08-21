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

## CORRECTION — I was wrong twice about the schema

**What I asserted:** *"the schema has no way to express that a value is a proxy"*, and that any caveat would have to "travel separately from the artifact". **Both are wrong.**

The schema has exactly one mechanism for this, and it is the field designed for it: **`source_evidence_manifest_sha256`**. The runtime checks only that the value is a well-formed SHA-256 — it **never fetches or inspects the manifest** (`guardian_runtime.py:2842-2844`). So the manifest's content and shape are entirely ours to define, and **the document commits to it cryptographically**.

That is a materially different situation from the one I described. The caveat does **not** travel separately: it is bound into the document by hash, and a reviewer following the chain cannot reach the numbers without passing it.

**What remains true, and is the real limit:** the runtime never reads the manifest, so the declaration is **committed but not machine-enforced**. A human must read it. That is weaker than a validator refusing a substituted value, and stronger than a note in a separate file.

---

## The draft document — built, NOT emitted, NOT uploaded, NOT bound

To make the decision concrete rather than abstract, the document that *would* result has been constructed and is shown here. **It has not been written to disk, uploaded to any bucket, or attached to any stack parameter.**

| field | value |
|---|---|
| `observed_recovery_gap_milliseconds` | **125424** — directly measured |
| `observed_worker_startup_milliseconds` | **190** — directly measured |
| `observed_provider_stop_execution_milliseconds` | **908** — **SUBSTITUTED** |
| `tested_consecutive_missed_ticks` | **1** — directly measured |
| `measurement_count` | **18** |
| `source_evidence_manifest_sha256` | `ae3909a3b950901e01cf48434646b749bf0d02b2462dfeedff9e6dcc5d6e8f79` |

The document's own SHA-256, which is what would go into `TimingValidationEvidenceSha256`, is:

```
0440cf8ecd73a928ce452fb1bec2cb7065ea3f15a0d13ff0a7ff80928deb575e
```

**The committed manifest's first key is deliberately unmissable:** `DECLARATION_THIS_DOCUMENT_CONTAINS_A_SUBSTITUTED_VALUE`. It names the field, gives the value, states exactly what was measured, states exactly what was **not** measured, explains why substitution was forced, records the probe's safety properties, lists all five samples, and says the worst case was used. It also carries the three discarded procedure artifacts, so the failures travel with the successes.

## The decision, stated plainly

Emitting this document is what would authorise `LIVE`. **That is why it has not been emitted.** The choice is between:

- **Emit it.** The substitution is cryptographically committed and impossible to miss for anyone who reads the manifest — but a reader of the document *alone* sees a field named `observed_provider_stop_execution_milliseconds` containing a transport measurement, and the runtime will not stop them.
- **Do not emit it.** Wait for Gate 4, where a real STOP against a real pod becomes possible — accepting that Gate 4 sits behind Gate 2, which sits behind this document.

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
