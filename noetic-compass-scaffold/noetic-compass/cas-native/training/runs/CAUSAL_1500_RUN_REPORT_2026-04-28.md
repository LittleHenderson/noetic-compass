# CAS-Native Causal 1500-Step Run Report

Date: 2026-04-28
Run: `v2-first-full-20260428-220635`
Commit base: `88fe382`

## Configuration

- Target mode: `cas_expression`
- Causal LM: `true`
- Dataset: Level 2 10K symbolic corpus
- Batch size: `32`
- Requested steps: `1500`
- Production warmup: `100`
- Eval/checkpoint interval: `250`
- Tokenizer hash: `2339a510d298afed`
- CAS expression UNK rate: `0.0`

## Training Outcome

- Status: `COMPLETED`
- Final step: `1500/1500`
- Wall-clock: `51.8 min`
- Peak GPU memory: `12.52 GB`
- NaN/OOM: none

| Step | Total | LM | Production | Proposer | Null-space |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 21.7378 | 7.3168 | n/a | 6.2687 | 503.4359 |
| 250 | 334.8873 | 3.7537 | 319.8706 | 5.9273 | 501.7390 |
| 500 | 59.5437 | 3.7191 | 45.1823 | 4.9994 | 497.8177 |
| 750 | 12.4690 | 2.8335 | 0.3289 | 2.7770 | 488.8848 |
| 1000 | 10.4174 | 1.5374 | 0.0014 | 2.1574 | 475.1470 |
| 1250 | 9.8809 | 1.1389 | 0.0093 | 2.0194 | 468.8568 |
| 1499 | 9.8612 | 1.1336 | 0.0501 | 2.0593 | 467.7266 |

## Qualitative Sampling

Standard sampling:

- Run: `qualitative-1500step-20260428-220635`
- Temperature/top-p: `0.7 / 0.9`
- Valid fragments: `30/30`
- Structured-valid CAS: `3/30`
- Structured examples all came from `v74_baseline`.

Low-temperature sampling:

- Run: `qualitative-1500step-lowtemp-20260428-220635`
- Temperature/top-p: `0.35 / 0.8`
- Valid fragments: `30/30`
- Structured-valid CAS: `5/30`
- Structured examples: `4/5` in `v74_baseline`, `1/5` in `v75_register`.

Representative structured outputs:

- `^0_{F6}|E + ^0^O_{F4}|T`
- `^7_{F1}|E + ^3^E_{F1}|A`
- `^1_{F6}|A + ^0^E_{F4}`
- `^3_{F3}|A + ^3^E_{F6}|T`
- `^7_{F1}|E + ^4^O_{F1}|f`

## Interpretation

This run crosses the first structured-generation threshold. The 100-step run produced `0/30` structured-valid outputs. The 500-step run showed token-family emergence but no reliable structured-valid threshold crossing. The 1500-step run produces repeatable structured-valid CAS under both standard and low-temperature sampling.

The emergence is still shallow. Valid structured outputs are concentrated in baseline/register-like expressions. Rule-Four, omega, production, and meta-logic forms remain malformed under free sampling. More training may help, but the next product-grade improvement is likely constrained decoding or expression-proposer-assisted rendering rather than only more steps.

## Artifact Policy

Committed artifacts should include metrics, logs, tokenizer, sample JSONL, bucket summaries, and this report. Checkpoints remain local-only because `final.pt` is approximately `450 MB`.
