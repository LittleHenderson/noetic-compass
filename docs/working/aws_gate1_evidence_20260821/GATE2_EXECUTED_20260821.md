# GATE 2 — EXECUTED AND VERIFIED — 2026-08-21

**Owner said `go`. Change set `live-activation-v3-verified` executed. Stack reached `UPDATE_COMPLETE` with `ActivationMode = LIVE`.**

---

## The action-time pre-flight — and the check that refused first

All seven checks had to pass on observed state. **The first run REFUSED** on check 7:

```
7. canary freeze    : current=False
PRE-FLIGHT FAILED -- NOT EXECUTING
```

That was a **defect in the pre-flight itself, not in the freeze.** The check ran the freeze probe under the AWS venv, which has no `numpy`; the subprocess crashed, produced no output, and the harness read the empty output as "stale". It failed in the safe direction, but it was **measuring nothing**.

Fixed so that a check which *cannot run* is reported distinctly from a check that ran and said no — never silently as either. Re-verified directly: the live source manifest equals the preregistration pin, `BD4CCE31A351D05AE58F32C4F033B03B6C2F5CFF68AE234030E26CB5B4BB2A31`.

Second run, all seven green:

| # | check | observed |
|---|---|---|
| 1 | quota / capacity | limit `1000`, headroom `900`, LIVE reserves `8` |
| 2 | change set | `CREATE_COMPLETE` / `AVAILABLE`, 21 changes |
| 3 | destructive ops | replacements `0`, removals `0` |
| 4 | stack state | `CREATE_COMPLETE` |
| 5 | parameter verifier | `PASS` (against the real binding document) |
| 6 | hash links | artifact `66,154` B, binding `3,935` B, timing `967` B — all match |
| 7 | canary freeze | current at HEAD |

## Execution

```
[   0s] UPDATE_IN_PROGRESS
[  60s] UPDATE_COMPLETE
```

`ActivationMode = LIVE`, `CoreLockSha256 = f1b659a779e8b016456b519daaeaf7ea1c24823a4e0008f857fb2655361bc2c0`, `RuntimeZipSha256 = e59a73e1519154e0ad3d424c2975a282896b93675df6915ed923933831dea10a`, `RecoveryEnabled = TRUE`.

## Post-execution verification

**All nine functions LIVE, one code revision, `5Zpz4VGRVOCt`:**

- `ACTIVATION_MODE = LIVE` on all nine.
- **Reserved concurrency total = `8`** — exactly the predicted figure, and the reason the quota mattered. (`starter` reserves none by design.)
- `DEPLOYMENT_BINDING_SHA256 = a54c1810…` on **9/9**.
- `BINDING_OBJECT_SHA256 = e40f3401…` on **9/9**.

**A correction worth recording: the "unreviewable" hash turned out to be reviewable after all — just not through CloudFormation.** It is `NoEcho` in the console, in `describe_change_set`, and redacted in CloudTrail, but it is plainly readable via `lambda:GetFunctionConfiguration` once deployed. The earlier claim that *no* verification path existed was true only of the pre-deployment surfaces. **Post-deployment there is a direct one, and it should be added to the review procedure.**

## The LIVE runtime, observed passively

The `rate(1 minute)` recovery timer now fires under LIVE. Observed without invoking anything: **10 invocations, 10 errors** in ten minutes, each `GUARDIAN_RECOVERY_FAIL_CLOSED:ACTIVATIONERROR`.

**That string is useless for diagnosis — audit Finding 4 confirmed in the wild.** It cannot distinguish "your binding hash is wrong" from "the provider secret is a refusal payload". So the question was settled by replay rather than assumption: the deployed environment was run through the guardian's **own** gate functions.

| gate | computed | expected | result |
|---|---|---|---|
| binding-object hash | `e40f3401…` | `e40f3401…` | **PASS** |
| local material binding | `a54c1810…` | `a54c1810…` | **PASS** |

**Both binding gates pass.** The failure is therefore downstream — the deliberate preprod provider-secret refusal payload — which is the **designed** outcome for this activation. The audit's predicted catastrophe (all nine Lambdas dying at `LOCAL_MATERIAL_BINDING_DIGEST_MISMATCH`) **did not occur, because the hashes were corrected before execution.**

## Claim states

- **Real:** the stack is LIVE; nine functions carry the correct bindings; reserved concurrency is 8; both binding gates pass against the deployed environment; the recovery loop fails closed.
- **Open:** the full activation path beyond the secret boundary is untested — it cannot be tested until a real provider credential exists.
- **Not established:** that the guardian can create, observe, or stop a real pod. Nothing beyond the secret refusal has executed.

## Standing

**Gate 1 complete. Gate 2 COMPLETE. Gate 3 complete.** Gate 4 not started.

Before any Gate 4 launch: **A40 stock and price must be checked in the RunPod console** — the credential available here reaches `/pods` only (catalog `400`, GraphQL `403`). Both protected pods remain `EXITED` and untouched.

**Still true: no pod has been created, no GPU exists, and the A40/Pythia experiment remains `NOT RUN`.** Gate 2 activated the guardian's control plane; it proves plumbing, not science.
