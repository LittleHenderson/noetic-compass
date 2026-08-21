# A bootstrap circularity in Gate 1 item 1 — found 2026-08-21, before the account was created

**The second account is necessary but NOT sufficient.** One of the three required timing measurements cannot be taken by any deployment that is not already `LIVE`, and `LIVE` cannot be reached without that measurement. Creating the account will unblock two thirds of item 1 and then stop.

This was found while preparing the preproduction deploy parameters, deliberately before the account exists, so the wall is visible now rather than after the work.

---

## The loop, in four verified facts

**1. `LIVE` requires a non-zero timing hash.** `template.yaml` asserts it under `LiveMode`:

```
Assert: !Not [!Equals [!Ref TimingValidationEvidenceSha256, '000…000']]
AssertDescription: LIVE requires reviewed empirical recovery/startup/STOP evidence;
                   AWS scheduling is not a hard guarantee.
```

**2. That hash covers a document that must contain a STOP number.** `_verify_timing_evidence` requires the exact 18-field set, including `observed_provider_stop_execution_milliseconds`, bounded at **8,000 ms**. A document missing it is `TIMING_EVIDENCE_SCHEMA_INVALID`.

**3. Under `INERT`, the provider STOP path is never reached.** `_activation_gate` opens with:

```python
if environment.get("ACTIVATION_MODE") != "LIVE":
    raise ActivationError("DEPLOYMENT_IS_INERT")
```

and it is called from **every** handler that could touch the provider — `_provider_proxy_handler()`, `_handler()`, `starter_handler()`, `recovery_handler()` (lines 2123, 3262, 3362, 3425). The refusal happens before any transport work.

**4. Therefore:** `LIVE` needs the STOP number → the STOP number needs the provider path → the provider path needs `LIVE`.

## What the second account still buys — this is not wasted work

Two of the three measurements **do not** need `LIVE` and can be taken in an `INERT` preproduction stack with `RecoveryScheduleState: ENABLED`. The template's `LIVE` assertions are conditional on `LiveMode`, so `INERT` + `ENABLED` is a permitted combination:

| Measurement | Needs `LIVE`? | Obtainable in `INERT` preprod |
|---|---|---|
| `observed_recovery_gap_milliseconds` | **No** | **Yes** — EventBridge still fires, the Lambda still runs and fails closed, so tick timestamps are real |
| `observed_worker_startup_milliseconds` | **No** | **Yes** — cold-start init is real regardless of the refusal |
| `observed_provider_stop_execution_milliseconds` | **Yes** | **No** — refused before transport |
| `tested_consecutive_missed_ticks` | **No** | **Yes** — the induction tool works against a real schedule |

So the account gets us **three of the four counted values** and leaves exactly one.

## What must NOT be done

- **Do not invent, estimate, or carry over a STOP number.** `RUNBOOK.md` §6 says the hash must never be invented or self-attested, and the harness refuses to emit a document with a missing measurement. A plausible figure here would corrupt the one artifact whose entire purpose is to be trustworthy.
- **Do not patch the runtime to let `INERT` reach the provider.** `guardian_runtime.py` is hash-locked. Editing it breaks `core-lock.json`, the deployment binding, and the freeze in one move — and it would remove the very gate that makes `INERT` mean something.
- **Do not lower the 8,000 ms bound or drop the field.** That is weakening a gate to make it pass.

## Options for the owner and reviewer — a decision, not an agent's call

**Option A — measure the STOP transport separately, and label it.** Time the real HTTPS STOP call to the provider from a Lambda in preproduction with the same region, runtime, and cold-start profile, outside the guardian. Honest and obtainable, but it is a **proxy** for the guardian's own path and must be declared as one wherever the number appears. It is not the guardian executing STOP.

**Option B — two-stage bootstrap.** Use an Option A figure to produce a **preproduction-only** timing document, activate preproduction `LIVE` on it, exercise the **real** guardian STOP path there, then emit the final document from that real measurement. Only the second document ever binds production. This yields a genuine end-to-end number, at the cost of one deliberate provisional activation **in preproduction only** — which a reviewer must sign off, because activating on a provisional document is exactly the kind of step that must never become routine.

**Option C — accept the ceiling.** Item 1 closes for two of three measurements and stops. Production `LIVE` stays `NO_GO`. Honest, and it costs nothing further.

**Recommendation: Option B, with the provisional document clearly marked, never uploaded to production's bucket, and destroyed once the real document exists.** It is the only route that ends with a real guardian STOP measurement. Option A alone leaves a proxy number binding production, which is weaker than it looks.

## Status

Gate 1 item 1 remains **`OPEN / NOT RUN`**. Nothing here changes that, and nothing here is execution authority. The A40/Pythia experiment remains **`NOT RUN`** — it has neither passed nor failed.
