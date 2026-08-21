# Preregistration — guardian LIVE timing evidence (Gate 1, item 1)

**Written before any measurement run, and no evidence document has been produced.**

**Precision added 2026-08-21:** the harness has since been run against **real** AWS logs and took real observations there (§6). It produced **no evidence document**, because it refused — correctly — on insufficient data. So "nothing has been measured" is now too loose: **real numbers were observed; no evidence exists**, and those are different claims.

This document fixes what will be measured, the exact bar each measurement must clear, and the decision rule — in advance, so the run cannot be read backwards into a pass. The bars are not copied from prose. They are read out of `infra/runpod_guardian_live_candidate/src/guardian_runtime.py`, and `measure_guardian_timing_evidence.verify_contract_against_runtime()` fails closed if that module and the harness ever disagree.

Status: `PREREGISTERED / NOT RUN`. There is no result here, of either sign.

---

## 1. Why this exists

`RUNBOOK.md` §6 will not let the guardian go LIVE without empirical timing evidence from a **version- and hash-locked preproduction deployment**. It says plainly: if the bounds are not observed, LIVE is `NO_GO`, and the hash must never be invented or self-attested.

The guardian enforces that in code, not on trust. `_verify_timing_evidence` re-serializes the document, compares it byte-for-byte, checks every field against a fixed set, binds it to the stack identity, and requires that its SHA-256 equals the `TimingValidationEvidenceSha256` stack parameter. **A hand-written or optimistic document does not start the guardian; it fails activation.**

## 2. What will be measured

Three observations, each with a hard ceiling taken from `_verify_timing_evidence`:

| Measurement | Field | Ceiling | Source of the ceiling |
|---|---|---|---|
| Largest observed gap between consecutive scheduled recovery ticks | `observed_recovery_gap_milliseconds` | **180,000 ms** | `observed_acceptance_bounds` |
| Cold-start worker startup | `observed_worker_startup_milliseconds` | **8,000 ms** | `observed_acceptance_bounds` |
| Provider STOP execution on the exact-ID transport path | `observed_provider_stop_execution_milliseconds` | **8,000 ms** | `observed_acceptance_bounds` |

Plus four fixed model values the runtime requires verbatim — `measurement_kind` `EMPIRICAL_NON_GUARANTEE`, `scheduled_recovery_cadence_seconds` **60**, `recovery_retry_maximum_attempts` **2**, `recovery_event_maximum_age_seconds` **60** — and two counted values: `tested_consecutive_missed_ticks` (**≥ 1**) and `measurement_count` (**≥ 1**).

The abstract model is `5 + 60 + 8 + 8 + 5 = 86` seconds against a **300-second** STOP lead, with STOP beginning by minute **25** of the **30-minute** hard wall.

## 3. Decision rule — fixed now

- **Every** ceiling must hold. One millisecond over any bound is `NO_GO`. The harness has no override flag and will not grow one.
- At least **one** consecutive missed-tick scenario must actually be observed. A run with zero missed ticks has not tested the thing §6 asks about, and is `NO_GO` — **not** a pass with a caveat.
- Fewer than **two** recovery ticks cannot produce a gap measurement. The harness fails closed rather than reporting a flattering `0`.
- Durations round **up**. A measurement is never reported as faster than it was.
- Booleans are rejected where integers are required, matching the runtime's `type(x) is not int` check.
- If any check fails, **no document is emitted at all.** There is no partial artifact to quote later.

## 4. Procedure

1. Deploy a preproduction stack at the **same artifact version and hashes** as the intended LIVE stack. It must be its own stack — never the production one, and never a stack whose `ActivationMode` has been softened to make measurement easier.
2. Run the recovery schedule long enough to collect `measurement_count` ticks.
3. Induce **at least one** consecutive missed-tick window on the preproduction stack only. This is an operator action on preproduction; the harness never mutates a schedule.
4. Exercise the exact-ID STOP transport path against the preproduction provider surface.
5. Run `measure_guardian_timing_evidence.py`. Collection is read-only: `logs:FilterLogEvents` and `cloudformation:DescribeStacks`.
6. Two reviewers compare the emitted document against live read-only AWS descriptions, per §5.
7. Upload the document to the private versioned Object-Lock bucket, capture the exact S3 version ID and SHA-256, and set `TimingValidationEvidenceSha256` to the printed hash — **the printed one, never a retyped one.**

## 5. What a pass licenses, and what it does not

A pass licenses exactly one sentence: **the observed timing on a hash-locked preproduction deployment fell inside the bounds §6 requires.**

It does **not** license any of the following, and none may be said:

- That the bounds are guaranteed. **EventBridge is best-effort.** Neither the one-minute schedule nor the largest observed gap is a service bound. The field is named `EMPIRICAL_NON_GUARANTEE` for that reason.
- That LIVE is authorized. LIVE additionally requires a reviewed CloudFormation change set, the deployment binding, and the remaining §6 service validations.
- That the retry envelope, cold secret retrieval, DNS, TLS, and proxy invocation fit the lead. Those are **separate** measurements this document does not cover.
- Anything whatsoever about the A40/Pythia experiment, which remains **`NOT RUN`** — it has neither passed nor failed.

## 6. Harness status

`tools/runpod_open_weight_canary_v2/measure_guardian_timing_evidence.py`, with `test_measure_guardian_timing_evidence.py`: **29 focused tests, 29 passing**. Full suite sweep after the Gate 3 re-pin: **488 passed, 0 failed** — canary 85, guardian + core + timing + precreate 355, C14 adapter incl. hostile 48. (An earlier revision of this line said **334**; that was the count before the canary suite was added to the sweep.)

The load-bearing test is `test_emitted_document_passes_the_real_runtime_validator`. It feeds the harness's own output into the runtime's `_verify_timing_evidence`, so the harness cannot drift into emitting a document only it would accept. Paired negative tests confirm the runtime **rejects** the same document under a wrong declared hash, and that one millisecond over any bound is refused while exactly on the bound is accepted.

**Operational note:** run the guardian suite with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`. `test_candidate_tree_contains_no_python_or_pytest_cache_artifacts` asserts the candidate tree is free of `__pycache__`, so a plain `pytest` invocation makes that test fail on its own bytecode. That is the test working, not a regression.

### Verified against REAL AWS data, 2026-08-21 — and it correctly refused

The harness had only ever run against a fake Logs client. It has now been pointed at the **real** guardian log groups in `us-west-2`, read-only.

**The collector works on real data.** It parsed **15** `REPORT` lines across all nine guardian Lambda log groups. That number is an **independent cross-check**: the `AWS/Lambda Invocations` metric over the trailing 24 h, read from a *different* API, is also **15.0**. Two APIs, one number.

| Lambda | invocations | max duration | cold-start init |
|---|---:|---:|---:|
| `control` | 3 | 17 ms | 247 ms |
| `observe` | 2 | 21 ms | 197 ms |
| `create` | 2 | 13 ms | 194 ms |
| `stop` | 2 | 4 ms | 196 ms |
| `observe-proxy` | 1 | 13 ms | 188 ms |
| `create-proxy` | 1 | 10 ms | 191 ms |
| `stop-proxy` | 1 | 14 ms | 202 ms |
| `starter` | 2 | 14 ms | 193 ms |
| `recovery` | 1 | 4 ms | **186 ms** |

Every cold start is between **186 ms** and **247 ms**, against the `observed_worker_startup_milliseconds` ceiling of **8,000 ms** — roughly a **32×** margin. **That is an observation, not evidence:** it is one cold start per function on a stack that has never run a scheduled recovery, and §6 asks for something quite different.

**The fail-closed path fired on real data, which is the part that mattered.** Two attempts were made against what actually exists:

1. Measure a recovery gap from the real timestamps → **REFUSED**: `RECOVERY_GAP_SAMPLE_INSUFFICIENT: at least two recovery ticks are required to measure a gap; got 1`.
2. Build an evidence document from everything available → **REFUSED**: `LIVE_NO_GO: section 6 requires at least one consecutive missed-tick scenario; observed 0`.

**No document was produced, and that is the correct outcome.** The refusals are now demonstrated on genuine AWS data rather than only on synthetic inputs — a fail-closed path that has only ever been exercised by its own unit tests is a promise, not a property.

**Status therefore moves from *tested against fakes* to *collection and refusal verified against real AWS data*, while item 1 itself stays `OPEN / NOT RUN`.** The gap is unchanged: the production stack has **one** recovery invocation and a `DISABLED` schedule, so the recovery-gap, missed-tick, and STOP-transport measurements cannot exist here. Those need the preproduction deployment — which **cannot be created in this account** (see `GATE_STATUS_2026_08_21.md`).

**The harness is built and tested. It has measured nothing.** Producing evidence requires a preproduction deployment, which is an owner decision with real cost, and has not been requested or made.
