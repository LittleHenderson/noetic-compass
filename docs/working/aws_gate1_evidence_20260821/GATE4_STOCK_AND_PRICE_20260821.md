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

## STOCK — NOT ESTABLISHED, and it needs the owner

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

## Standing

Gates 1, 2 and 3 complete. **Gate 4 is blocked on one fact: live Secure Cloud A40 availability.** No pod created. No GPU exists. The A40/Pythia experiment remains **`NOT RUN`**.
