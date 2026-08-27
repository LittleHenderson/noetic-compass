# CCB-R1 M1 parser diagnosis and live confirmation

**Date:** 2026-08-27

**Scope:** M1 only; this is not a full Stage 5 rerun.

**Source:** `3102994b0a5c06665abcf3bec877d59f4f6f1fcb`

**Disposition:** parser defect fixed; M1 remains **NOT CLEARED**.

## Root cause

`operator_scoring` used a loose `leads to` search over all response prose. It
therefore treated a valid derived conclusion such as `Therefore, AA leads to
CC.` and a negated mention such as `no statement says AA leads to CC` as if the
model had cited a new premise. `domain_coherence` correctly observed that the
derived/query link was not a literal premise, raised `W`, and withheld the
answer. The second instrumented pass consequently produced 72 `W` withholds
among 76 items that reached the base call.

That false positive masked a companion parsing defect. The generic parser takes
the first verdict word, so prose containing `no direct statement ...` followed
by a final `UNKNOWN` was internally scored as `NO`.

The fix is deliberately limited to response parsing:

- claimed premise steps must be exact whole lines of the form
  `AA leads to BB.`;
- the wrapped verdict must appear on the final non-empty line as `YES`, `NO`,
  `UNKNOWN`, or legacy `Answer: ...`;
- the bare-arm parser is unchanged;
- the wrapper still does not search a graph, compute transitive closure, or use
  the hidden answer.

Offline verification at the source commit passed `26/26` focused wrapper tests,
`265/265` full CCB-R1 tests, and `git diff --check`.

## Live confirmation

Same provider/model and same generated items were used in both arms:
`deepseek/deepseek-chat`, temperature `0`, `max_tokens=1024`, seed `20260830`,
50 answerable plus 50 unanswerable items. The run was sequential and produced
zero stderr bytes.

| Measurement | Instrumented pass 2 | Fixed pass |
|---|---:|---:|
| Wrapped correct | 48/100 | **87/100** |
| Wrapped answerable correct | 1/50 | **37/50** |
| Wrapped unanswerable correct | 47/50 | **50/50** |
| Bare correct | 69/100 | 68/100 |
| `inversion:W` withholds | 72 | **0** |
| RPM-gate withholds | 24 | 22 |

The fixed run's current-runner accuracy difference is **+19 pp** with paired
95% CI **[+8, +30] pp**. The registered threshold is judged on the lower bound,
so this is **NOT CLEARED**.

## Metric-contract blocker

The merged margin document defines M1 on **abstention among unanswerable
items**, but `run_comparison.py` currently judges **accuracy over the complete
balanced set**. Those are different estimands.

Descriptively, the fixed run's unanswerable abstention rates are 100% wrapped
versus 78% bare: **+22 pp [+10, +34]**, paired 95% CI. It still cannot adjudicate
the documented criterion:

1. the lower bound does not clear +20 pp; and
2. the balanced `n=100` set contains only 50 unanswerable pairs, below the
   registered `n >= 100` floor.

The next registered M1 design must name the primary unanswerable abstention
margin, include at least 100 unanswerable pairs, and pre-register a separate
answerable-usefulness guard so an always-`UNKNOWN` wrapper cannot pass. The
existing full kill-criteria draft supplies a prospective default of **0.90**;
K0.1 and the executable report do not currently bind it. With a balanced design,
the corrected minimum is therefore 100 unanswerable pairs plus 100 answerable
controls (`n=200` total). Earlier negative results remain historical evidence
and are not overwritten.

## Artifact identities

- Fixed output:
  `.tmp/audit_ccb_r1/instrumented5_out.txt`, SHA-256
  `7FEDB3A0E3EDA49EDBF11B1B7FB88F4E43F49521C51847FE19BC8A8B725F7726`
- Instrumented pass 2 output:
  `.tmp/audit_ccb_r1/instrumented2_out.txt`, SHA-256
  `1EA6CE59A2B07D1C76C1F813959949F84A486E4E59A3B4909993EAD51E7DD267`
- Structured summary: `ccb_r1_m1_parser_diagnosis_2026_08_27.json`
