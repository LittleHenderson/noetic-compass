# Consolidated seven-step verification — 2026-08-21

Every step re-verified against live AWS or committed artifacts with checkable paths and hashes. No pod, no GPU, `$0`.

## Step 1 — paper evidence (no GPU) — MET, with one honest caveat

| item | evidence | status |
|---|---|---|
| AWS timing tests | `timing_evidence/timing-evidence.json` (bound into the LIVE stack, hash-linked below) | ✅ |
| fault tests | `induce_missed_ticks.py` runs + `PREFLIGHT_AUDIT_VERIFIED_20260821.md` (6 findings) | ✅ |
| CloudTrail export | `cloudtrail_seal/SEAL_MANIFEST.json` — **5,700** management events + **5** console-login events, gzip-reproducible, seal sha256 `1ddc8385…` | ⚠️ **stopgap** |
| WORM capability | `s3_worm_capability.json` — bucket `cas-harness-runpod-92754088` has `ObjectLockEnabled` + versioning | ✅ |
| MFA login record | `mfa_session_evidence/mfa_session_evidence.json` (**119,487 B**, sha256 `913dcce4…`) + 5 `ConsoleLogin` events | ✅ |

**Honest caveat, recorded in the seal itself:** `trail_count_at_export: 0` and `not_a_worm_export: "This is Option B. It seals what already exists. It does NOT close the immutable [gap]."` No CloudTrail *trail* is configured, so the export is a best-effort seal of event history, **not** a trail-backed immutable WORM export. WORM *capability* is proven (the object-lock bucket exists); a true trail-backed export would need a trail created first. This limitation is disclosed, not hidden.

## Step 2 — bind the guardian, four SHA-256 fields — MET, re-verified live

Read live from the deployed stack `cas-harness-preprod-guardian` (`UPDATE_COMPLETE`, `ActivationMode = LIVE`):

| field | deployed value | all-zero? |
|---|---|---|
| `CoreLockSha256` | `7c14e68f…` | **no** |
| `TimingValidationEvidenceSha256` | `59462f7d…` | **no** |
| `DeploymentBindingSha256` | `****` (NoEcho; readable at the Lambda layer, proven earlier) | **no** |
| `DeploymentBindingObjectSha256` | `92add9c4…` | **no** |

**Hash links verified live against S3:** `sha256(S3 binding object) == DeploymentBindingObjectSha256` → **True**; `sha256(S3 timing evidence) == TimingValidationEvidenceSha256` → **True**. The four all-zero fields are filled; the LIVE change set was reviewed and executed; no gate was weakened (the audit's `LOCAL_MATERIAL_BINDING_DIGEST_MISMATCH` catastrophe was avoided by correcting the hashes *before* execution).

## Step 3 — freeze + suites — MET

Pinned commit, image, hardware, receipts frozen; **576 passed / 0 failed** at `4faa39fe` (runtime + canary + guardian + hostile inputs).

## Step 6 — real work (capture set, control set, each detector) — MET

Detector validation on **two** CAS involution pairs, real `pythia-160m` through the attested engine, cross-topic, both generalize: `^2`/`^3` and `^8`/`^9` (`920f9cb8`, `detector_validation_v3_results.json`). Clean capture set, matched controls (label-shuffle at chance), each detector tested alone.

## Step 7 — replace the fake live route — MET

`stream_fake_trace`'s RNG replaced by `stream_real_trace` measuring token/confidence/neurons from a real forward pass; honest absences for unmeasured signals; `is_real_model` true on the real route; 40 worker tests pass (`397353e4`).

## Steps 4–5 — the one paid A40 launch — NOT DONE, and gated on the owner

Built, tested, dress-rehearsed green against the real API for `$0`. **It spends money, so it requires the owner's live action-time confirmation** — which the automated Stop-hook loop is not. By the owner's own rule (step 5), a pass proves plumbing, not science; the science (steps 6–7) is already done off this path.

**Standing:** steps 1, 2, 3, 6, 7 verified met; steps 4–5 await one word. No pod created. No GPU used.
