# Gate 4 — launch plan and standing authorization — recorded 2026-08-21

## The authorization, verbatim

> "the paid A40 authorisation for Gate 4. is hereby granted"

Recorded as **standing spend authority for exactly one machine**. It does **not** reorder the gates: the owner's own gate list says each gate passes before the next, and Gate 2 is still open. This authority is **held, not exercised**, until Gate 2 passes.

## Scope of the authority — the standing launch limits, unchanged

Exactly **one** new RunPod Pod, and only with **all** of:

| Constraint | Value |
|---|---|
| Cloud / GPU | Secure-Cloud **A40**, on-demand, non-interruptible |
| Rate | **≤ $0.50/hour** — checked at launch time, not assumed |
| Image | exact pinned `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`, digest `sha256:4d1721e6…` |
| Volume | encrypted positive Pod volume, **no network volume** |
| Network | only `22/tcp` |
| Key | dedicated key |
| Wall | **30-minute hard bound**; spend cap `$0.50` total; **one** create attempt |

Protected resources stay protected: never touch Pod `q2oqlooejhin7s`, keep Pod `vernmyfb3ck9po` stopped, never touch volume `hfelwlp1va`.

## Model re-pin — the reason this plan is now launchable at all

Before 2026-08-21 this plan would have failed at model-load on the pod, **after** the single create attempt was spent: the pinned `model.safetensors` `29D2E457…` carries 184 tensors including 36 legacy buffers, the pinned `transformers 5.8.1` loads 148, and the byte-exact weight verifier demands set equality. The owner approved the re-pin; the **verifier was not weakened** and the model artifact moved instead. The model now **loads and captures through the real engine** on the plan's own frozen prompt. Full account: `MODEL_REPIN_RECORD_20260821.md`. Step 3 below therefore re-verifies against the NEW hashes (tree `BB65650E…`, source manifest `BD4CCE31…`).

## What still blocks the launch, and who owns it

1. **Gate 2 — AWS quota** `9b482ab5…` (`CASE_OPENED`, applied still `10`). Owner of the wait: AWS.
2. ~~The change-set review verdict.~~ **RESOLVED 2026-08-21: the owner said "review passed", verbatim, while this plan was being written.** The change set `live-activation-for-owner-review` is now REVIEWED. Per RUNBOOK §7, execution still requires the owner's **action-time confirmation immediately before** executing — review and execution confirmation are deliberately separate acts.
3. **The canary's own NO-GO latches**, which nothing here weakens: `execution_authority = NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN` and `provider_launcher_live_status = NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE`. They flip only via the draft below, applied **after** Gate 2, plus an armed precreate guardian.

## The DRAFT execution binding — staged, NOT applied

When Gate 2 passes, the preregistration gets exactly these three edits (plus its recomputed self-hash), and nothing else:

| Field | Draft value |
|---|---|
| `execution_authority` | `GO_FOR_ONE_ENGINEERING_CANARY_ONLY` |
| `required_source_commit_sha256` | the final frozen commit at application time — candidate now: **`8595f6adfca00a7c9f724aafad00ffabd32b5109`** (superseded candidate `09a30a8a1b917db1fa6a3a0409d0fa41670f7d9a`, invalidated by the owner-approved model re-pin; freeze re-verified current at this HEAD 2026-08-21; re-verify again at application) |
| `required_provider_launcher_source_sha256` | `C2081C74897D25147F29A57926863FBC5B827E516D3FC22D802051C664832F21` (computed from `create_provider_launch_receipt.py` today; re-verify at application) |

**Applying this draft is the formal grant of canary execution authority.** It is deliberately not applied now, because Gate 2 has not passed and the precreate guardian is not armed.

## The launch-time sequence, when everything above is green

Per the handoff's step 5 and RUNBOOK §7, in order, all on the same day as the launch:

1. Fresh account inventory (no unexpected pods), then **A40 stock and rate check** — abort if rate > `$0.50/hour` or Secure-Cloud A40 unavailable.
2. Precreate guardian **armed**, GitHub stop-supervisor **armed**, local watchdog **armed** — receipts bound.
3. Apply the draft execution binding; re-run the canary suite so the negative tests prove the latches now pass for the right reasons.
4. Owner's **action-time confirmation** (RUNBOOK §7 requires it immediately before execution — this authorization does not substitute for it on the guardian change set, and the same discipline applies here).
5. One-send production launcher. **One** create attempt. Any mismatch — inventory, price, capacity, image, storage, port, key, deadline, binding, recovery, secret, KMS, receipt — STOPs only the exact new Pod ID and never runs the model.
6. 30-minute hard wall; the canary's nine captures; export; STOP; sweep.

## Standing

Gates 1 and 3 complete; Gate 2 open on two items; Gate 4 **authorized but not started**; Gate 5 not started. Even a Gate 5 pass is `NOT_PACKET_ELIGIBLE`, `NOT_SCIENTIFIC_RESULT` — plumbing only. Production untouched; no GPU exists; the A40/Pythia experiment remains **`NOT RUN`**.
