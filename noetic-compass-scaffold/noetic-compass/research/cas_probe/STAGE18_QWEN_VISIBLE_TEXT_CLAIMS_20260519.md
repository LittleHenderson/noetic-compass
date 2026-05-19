# Stage 18 Qwen Visible Text Claims

**Status:** `NULL_STAGE18_QWEN_VISIBLE_TEXT_SHIFT_NOT_ESTABLISHED`

Stage 18 does not establish visible-text shift; CPL2 remains load-bearing.

## Gate Result

| Metric | Result | Gate |
|---|---:|---:|
| Drive judge test accuracy | `0.6679` | `>= 0.65` |
| Probe-readable minus partner-readable margin | `-0.1414` | `>= +0.10` |
| Probe-readable delta vs none | `+0.0178` | `>= +0.05` |
| Probe > partner rows | `12/112` | `>= 65/112` |
| Probe > partner Wilcoxon p | `0.999759` | `< 0.05` |
| Probe raw delta vs none | `-0.1116` | `< +0.05` |

The judge itself cleared the minimum reliability gate, but the generated text
did not move in the intended direction under `probe_readable`. The
`partner_readable` condition was stronger than `probe_readable`, so the visible
text tier is not established.

## Supported Wording

> CAS Harness readable realization can be tested in visible generated text. Stage 18 reports whether Qwen continuations under probe-readable context are judged more target-Drive-aligned than wrong-partner context.

## Rejected Wording

- Do not say CAS directly controls Qwen generation.
- Do not say raw CAS symbols work.
- Do not say this identifies exact causal neurons.
- Do not say this proves all open-ended generated language can be steered.
