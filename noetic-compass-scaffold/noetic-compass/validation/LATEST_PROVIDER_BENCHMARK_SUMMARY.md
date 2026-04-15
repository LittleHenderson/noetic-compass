# Latest Frozen Provider Benchmark Summary

Date: 2026-04-12

This summary uses the same frozen `sample_prompts` set with `10` prompts per provider.

## Table 1: Neutral Automated Baseline

Scoring mode: `heuristic_fallback`

This is the least-biased automated baseline because it does not ask a model to grade model output.

| Rank | Provider | Mean NCCS | Std Dev | Prompts | Archive |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | xai | 68.15 | 3.65 | 10 | `validation/studies/2026-04-12T210627.199895+0000__xai__xai-frozen10-heuristic.json` |
| 2 | meta | 67.20 | 4.84 | 10 | `validation/studies/2026-04-12T210625.830384+0000__meta__meta-frozen10-heuristic.json` |
| 3 | qwen | 66.95 | 5.05 | 10 | `validation/studies/2026-04-12T210619.674309+0000__qwen__qwen-frozen10-heuristic.json` |
| 4 | anthropic | 65.86 | 4.83 | 10 | `validation/studies/2026-04-12T210623.432150+0000__anthropic__anthropic-frozen10-heuristic.json` |

## Table 2: External-Scorer Automated Comparison

Scoring mode: `secondary_llm`
Fixed external scorer: `google`

This table is richer semantically than heuristics, but it must remain separate from the heuristic table.

| Rank | Provider | Mean NCCS | Std Dev | Prompts | External Scorer | Archive |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 1 | anthropic | 71.07 | 5.10 | 10 | google | `validation/studies/2026-04-12T211751.786739+0000__anthropic__anthropic-frozen10-secondary-google.json` |
| 2 | qwen | 67.27 | 7.72 | 10 | google | `validation/studies/2026-04-12T211755.339299+0000__qwen__qwen-frozen10-secondary-google.json` |
| 3 | xai | 64.38 | 9.62 | 10 | google | `validation/studies/2026-04-12T211749.305973+0000__xai__xai-frozen10-secondary-google.json` |
| 4 | meta | 58.32 | 9.53 | 10 | google | `validation/studies/2026-04-12T211753.910243+0000__meta__meta-frozen10-secondary-google.json` |

## Interpretation Rules

- Do not merge these two tables into one ranking.
- `heuristic_fallback` is the least-biased automated baseline.
- `secondary_llm` with a fixed external scorer is the stronger semantic comparison mode.
- `self_reported` is not suitable for stakeholder ranking because it lets the generator grade itself.
- Human calibration and reconciliation should be reported alongside both automated tables.

## Current Operational Note

`deepseek` was tested as a possible fixed external scorer, but the provider returned `402 Insufficient Balance` during live probing on this machine. `google` succeeded as the fixed external scorer for the archived `secondary_llm` runs above.
