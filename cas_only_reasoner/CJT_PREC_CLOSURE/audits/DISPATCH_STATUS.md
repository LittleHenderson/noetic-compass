# SECOND MATH AUDITOR — DISPATCH BLOCKED (2026-09-02)

Owner instruction: *"get a second math auditor on the generic theorem."*

**The package is written, committed and ready. The dispatch FAILED on every eligible family,
and every failure is a BILLING OR ACCESS problem on the owner's accounts — none of it is
fixable from here.**

## Eligibility, enforced in code not assumed

| family | key | eligible? | why |
|---|---|---|---|
| Anthropic / Claude | — | **NO** | built the artifacts under audit |
| Zhipu / **GLM** | `ZHIPU_API_KEY` | **NO — RECUSED** | **authored the proof sketch under audit**; the dispatcher refuses this key by name |
| DeepSeek | `DEEPSEEK_API_KEY` | yes | distinct family, strong at mathematics |
| Google / Gemini | `GEMINI_API_KEY` | yes | distinct family |
| Alibaba / Qwen | `DASHSCOPE_API_KEY` | yes | distinct family, held as tie-breaker |

## What every eligible endpoint actually returned

```
DeepSeek        402  "Insufficient Balance"
                     -> account has no credit

Gemini 2.5-pro  429  "You exceeded your current quota, please check your plan
                      and billing details"
Gemini flash    403  "Your project has been denied access. Please contact support."
                     -> out of quota on pro AND denied on the flash tier

Qwen (intl)     400  "Arrearage ... please make sure your account is in good standing"
                     -> overdue payment
Qwen (cn)       401  "Incorrect API key provided"
                     -> the key is for the international endpoint, which is in arrears
```

**Three independent families, three billing walls. GLM is the only funded account and it is
the one that is recused.**

## What is NOT being done instead

**No same-family substitute is being passed off as the audit.** Claude agents can and did hunt
counterexamples, and that work is real — but it **cannot discharge this requirement**, because
the requirement exists precisely to get a party that did not build or author the thing. Running
more Claude agents and calling the result an independent audit would be the same class of error
as the fabricated control this project already caught.

## What the owner needs to do — any ONE of these unblocks it

1. **Top up DeepSeek.** Cheapest option; `deepseek-reasoner` is a strong mathematical model and
   the audit is a single long prompt (well under `$1`).
2. **Fix the Google project** — resolve the quota/billing on `GEMINI_API_KEY`, or supply a key
   from a project with `gemini-2.5-pro` access.
3. **Settle the Alibaba arrears** on `DASHSCOPE_API_KEY`.
4. **Use a human mathematician.** The package is written to be read by one — it states the
   object, both quantifier versions, the disproof of the universal claim, the numerical evidence
   for the generic one, and six gaps we found in our own sketch.

Once any of these is done, run:

```bash
python cas_only_reasoner/CJT_PREC_CLOSURE/dispatch_theorem_audit.py
```

It writes `audits/<family>_audit.md` and extracts the verdict line. Keys are read from
`~/.cas_llm_keys.env` and are never printed or written to any output file.

## Standing

```
Generic non-absorption theorem   NOT AUDITED -- unchanged
CJT-PREC-0                       REMAINS PARKED
GPU / neural training            NOT AUTHORIZED
Cost of this attempt             $0 (every call was rejected before billing)
```
