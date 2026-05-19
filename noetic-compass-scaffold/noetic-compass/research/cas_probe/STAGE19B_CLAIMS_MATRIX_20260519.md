# Stage 19B Claims Matrix - Cross-Architecture Foundation Verification Stack

**Report status:** `NULL`

**Practical verdict:** `DIAGNOSTIC_ONLY_CROSS_ARCH`

Stage 19B tested the runtime-safe CAS Verification Stack on the locked Stage 15
OLMo and Stage 16 Qwen Foundation fixtures. The stack used only non-oracle
runtime signals for acceptance:

- 28-way Foundation majority across `focus_token`, `final_token`, and
  `mean_over_seq_len`
- Drive/Register recomposition as a factor-consistency gate
- non-oracle Foundation trace stability

Gold labels were used only after acceptance to score accuracy.

## Provenance

| Item | Value |
|---|---|
| Branch | `experiment/cas-probe-pythia` |
| Initial pre-registration commit | `ab6278c` |
| v2 bounded factor-scan commit | `87e6842` |
| Fixed-layer indexing bugfix commit | `ee19d62` |
| Pre-registration | `STAGE19B_CROSS_ARCH_FOUNDATION_VERIFICATION_STACK_GATES_20260519.md` |
| Runner | `run_stage19b_cross_arch_foundation_verification_stack.py` |
| Result JSON | `stage19b_cross_arch_foundation_verification_stack_20260519.json` |
| Result report | `STAGE19B_CROSS_ARCH_FOUNDATION_VERIFICATION_STACK_20260519.md` |

## Result

| Model | Per-model status | Best single Foundation | Stack accepted accuracy | Coverage | Silent error | Suppressed |
|---|---|---:|---:|---:|---:|---:|
| OLMo-1B | `DIAGNOSTIC_ONLY` | `0.9060` | `0.9816` | `0.7173` | `0.0184` | `0.2827` |
| Qwen2.5-1.5B | `DIAGNOSTIC_ONLY` | `0.8537` | `0.9949` | `0.7457` | `0.0051` | `0.2543` |

The result did not reach the pre-registered `PASS_BOUNDED` tier because both
models fell below `0.800` coverage. The report status is therefore `NULL` under
the pre-registered overall pass rule.

The diagnostic result is still meaningful: accepted examples are much cleaner
than the best single Foundation readout on both non-Pythia models.

## Component Ladder

| Model | Ensemble-only acc / cov | Factor-consistent acc / cov | Final stack acc / cov |
|---|---:|---:|---:|
| OLMo-1B | `0.8975 / 0.9039` | `0.9422 / 0.8240` | `0.9816 / 0.7173` |
| Qwen2.5-1.5B | `0.9281 / 0.8988` | `0.9661 / 0.8274` | `0.9949 / 0.7457` |

The ladder is coherent: each added gate increases accepted accuracy and reduces
coverage. This supports the stack as a high-precision diagnostic verifier, not
yet a high-coverage runtime license.

## Supported Claims

| Claim | Status | Evidence |
|---|---|---|
| Verification Stack transfers as a high-precision diagnostic to OLMo/Qwen | Supported | OLMo accepted accuracy `98.16%`; Qwen accepted accuracy `99.49%` |
| Factor consistency improves accepted Foundation quality | Supported | OLMo `89.75% -> 94.22%`; Qwen `92.81% -> 96.61%` |
| Trace stability further improves accepted Foundation quality | Supported | OLMo `94.22% -> 98.16%`; Qwen `96.61% -> 99.49%` |
| Runtime acceptance is non-oracle | Supported | Gold labels used only after acceptance for scoring |
| OLMo/Qwen Stack is high-coverage product-ready | Not supported | Coverage `71.73%` and `74.57%`, below `80%` bounded gate |
| Register is beyond-text evidence here | Not claimed | Register is only an internal consistency signal |
| Exact neurons or weights caused the answer | Not claimed | Stage 19B uses probes, factor gates, and trace states |
| Visible generation steering | Not tested | Out of scope |

## Defensible Wording

Use:

> Stage 19B replicated the CAS Verification Stack on OLMo-1B and
> Qwen2.5-1.5B as a high-precision diagnostic verifier. It accepted 71.7-74.6%
> of examples at 98.2-99.5% accuracy using only non-oracle runtime signals, but
> missed the pre-registered high-coverage product gate.

Do not use:

> Stage 19B proves the Stack is production-ready across architectures.

Do not use:

> CAS Harness gets 99% on all examples.

