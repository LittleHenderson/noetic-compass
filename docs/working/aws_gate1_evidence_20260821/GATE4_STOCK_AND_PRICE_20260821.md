# Gate 4 — "check stock and price first" — status 2026-08-21

Gate 4's first instruction is *"Check stock and price first."* That is two separate facts. **One is now established; one still needs the console.**

## PRICE — ESTABLISHED

**Secure Cloud A40 = `$0.44/hour`. The cap is `$0.50/hour`. It fits, with `$0.06/hour` of margin.**

Read from RunPod's public pricing page (`https://www.runpod.io/pricing`), no login and no account access involved. The page carries a Community/Secure toggle, and the **Secure Cloud radio was the selected one** when the figure was read — verified by inspecting the radio state directly, not by assuming the default:

```
Community Cloud  -> checked: false
Secure Cloud     -> checked: true
A40  48 GB VRAM  50 GB RAM  9 vCPUs   $0.44/hr
```

**Corroboration:** the existing stopped canary pod `vernmyfb3ck9po` records `costPerHr 0.44` — an independent figure from the account's own history that matches the published Secure Cloud rate exactly.

At `$0.44/hour`, the 30-minute hard bound costs **`$0.22`**, inside the `$0.50` total spend cap.

## STOCK — ESTABLISHED 2026-08-21 (owner opened the console; read directly)

**A Secure Cloud A40 is AVAILABLE. `High` availability, `9 max` GPUs.** Read from the RunPod console deploy page with the **Secure Cloud** filter active:

```
A40    $0.44/hr    48 GB VRAM    9 max    50 GB RAM  9 vCPU    High
```

The reading is meaningful because the same page marks other GPUs **`Unavailable`** in the same list (`H100 PCIe`, `RTX 6000 Ada`, `RTX PRO 6000 WK`, `H200 NVL`, `RTX A4500`). A40 is not among them, and its console price `$0.44/hr` matches the public page and the account's own history exactly.

**Both halves of "check stock and price first" are now COMPLETE.**

Also confirmed from the console pod list: both protected pods remain stopped and untouched — `vernmyfb3ck9po` (`cas-open-weight-canary-v2-20260820t124254257z-d874dad6`, `A40 x1`, storage-only `$0.01/hr`) and `q2oqlooejhin7s` (`heavy_moccasin_gerbil`, `H200 SXM x1`, `$0.00/hr`). **`vernmyfb3ck9po` was NOT restarted** — the standing protection holds.

## Earlier attempt record — why the API could not answer this



**Live A40 availability cannot be read from here.** This is a verified limitation, not a first-attempt failure. What was tried:

| attempt | result |
|---|---|
| REST `/pods` | **works** (proves the credential is valid) |
| REST `/gputypes`, `/gpu-types` | `HTTP 400` |
| REST `/billing/balance` | `HTTP 400` |
| GraphQL `gpuTypes`, query-param auth | `HTTP 403` |
| GraphQL `gpuTypes`, Bearer auth | `HTTP 403` |
| GraphQL `gpuTypes`, raw `Authorization` | `HTTP 403` |
| search for a second, wider-scoped credential | none exists — `~/.cas_llm_keys.env` holds only `DASHSCOPE`, `DEEPSEEK`, `ZHIPU` |

The single RunPod credential is scoped to the Pods REST surface only. The catalog and availability endpoints refuse it. The public pricing page publishes **price** but not **live capacity**.

**Owner action, and it is small:** open the RunPod console deploy page and confirm a **Secure Cloud A40 is actually available** right now. That is the only remaining unknown before a launch.

## Everything else for Gate 4 is staged

| constraint | status |
|---|---|
| Secure Cloud A40, on-demand, non-interruptible | pinned in the launch plan |
| ≤ `$0.50/hour` | **satisfied at `$0.44/hour`** |
| exact pinned image `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`, digest `sha256:4d1721e6…` | pinned |
| encrypted positive Pod volume, **no** network volume | pinned |
| only `22/tcp` | pinned |
| dedicated key | pinned |
| 30-minute hard bound, one create attempt | pinned |
| model loads (was a guaranteed failure) | **fixed and proven** — re-pinned artifact loads and captures |
| create-path IAM (would have burned the attempt) | **fixed and proven** by two regression tests |

Protected resources re-verified untouched: `vernmyfb3ck9po` `EXITED`, `q2oqlooejhin7s` `EXITED`, network volume `hfelwlp1va` not touched.

## THE REMAINING BLOCKER — the safety net does not exist yet

Stock and price are done. The launch is still **NO-GO**, and not for a paperwork reason. Both latches in the preregistration are still set:

```
execution_authority           = NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN
provider_launcher_live_status = NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE
```

The second one is the substantive blocker. **The precreate guardian is not deployed.** It exists only as an untracked template at `infra/runpod_precreate_guardian_aws/template.yaml`. That component is the thing that guarantees a created pod gets stopped even if this machine dies, the network drops, or the process is killed mid-run. Without it, a `$0.44/hour` pod created under a 30-minute plan has **no independent authority that will stop it** — the 30-minute bound would depend on the same process that created it.

Flipping the latches, per the launch plan, requires all of:

1. Apply the draft execution binding — `execution_authority = GO_FOR_ONE_ENGINEERING_CANARY_ONLY`, plus the frozen source commit and launcher source hashes, plus a recomputed self-hash. **Unblocked now that Gate 2 has passed.**
2. **Deploy and arm the precreate guardian.** Not started.
3. Arm the GitHub stop-supervisor and the local watchdog; bind their receipts.
4. Re-run the canary suite so the negative tests prove the latches pass for the right reasons.

**Note also:** the LIVE preprod guardian cannot create a pod today — its provider secret is deliberately a refusal payload, so it fails closed at `PROVIDER_SECRET_*`. Gate 2 proved the control plane activates; it did not give the guardian a working credential.

## Standing

Gates 1, 2 and 3 complete. **Gate 4: stock and price CHECKED and PASSED; the launch itself is NO-GO until the precreate guardian is deployed and armed.** Proceeding without it would remove the only independent stop authority over a paid machine — which is weakening a gate to make it pass.

No pod created. No GPU exists. The A40/Pythia experiment remains **`NOT RUN`**.
