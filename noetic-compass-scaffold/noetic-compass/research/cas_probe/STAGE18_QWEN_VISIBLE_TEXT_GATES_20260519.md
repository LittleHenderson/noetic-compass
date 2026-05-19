# Stage 18 Qwen Visible Text-Quality Gates

**Status:** pre-registered before any Stage 18 visible-generation run.

**Branch:** `experiment/cas-probe-pythia`

**Authorization:** user authorized the next Stage 18 visible text-quality gate after Stage 17 locked the evidence boundary.

## Scope

Stage 18 tests whether the Stage 16 Qwen eta-to-epsilon bridge is visible in
generated text, not only in likelihood scores.

Authorized:

- Model: `Qwen/Qwen2.5-1.5B`.
- Dataset: frozen Stage 7 original-TKS 28-Foundation fixture,
  `stage7_foundation_pilot_20260517.jsonl`.
- Activations: reuse Stage 16 activation artifact
  `stage16_qwen15b_activations_20260519.npz`.
- Probe: reuse the Stage 16 probe family and validation-selected layer rule.
- Selected layer: validation-selected Stage 16 layer `11`.
- Generated-text rows: the same 112 same-register Drive-cycle row shape used
  in CPL2, `16` rows per Drive.
- Conditions:
  - `none`
  - `probe_readable`
  - `partner_readable`
  - `gold_readable` as ceiling/reference only
  - `probe_raw` as raw-symbol control
- Decoding: greedy, deterministic, `max_new_tokens=48`.
- Judge: text-only Drive classifier trained on the frozen Stage 7 fixture,
  selected by validation accuracy before judging generated text.

Not authorized in this stage:

- Hidden-state steering.
- Sampling-temperature fishing.
- Human/LLM judge with flexible rubric.
- Changing the selected Qwen layer after looking at generated text.
- Raw CAS-symbol success claims.
- Open-ended generation-control claims.
- New model family or 7B scale-up.

Hard cap: 1 GPU-hour on A6000.

## Prompt Shape

The model-facing base prompt is fixed:

```text
{optional_prefix}{english}
Write one clear sentence about what the focused role represents:
```

The generated continuation is judged without the prefix text.

## Primary Visible-Text Gate

The primary axis is Drive, not full Foundation. Prior visible-generation tests
showed that full Foundation-level text judging is too noisy. Drive-level
alignment is the appropriate first visible-text target because CPL2 is also
mostly a Drive likelihood assay.

Primary metric:

> The text-only Drive judge's target-vs-partner probability margin for
> `probe_readable` continuations, compared with `partner_readable`
> continuations on the same rows.

### PASS_CLEAN

All must pass:

- Drive judge test accuracy on frozen Stage 7 test split `>= 0.65`.
- `probe_readable_mean_margin - partner_readable_mean_margin >= +0.10`.
- `probe_readable_mean_margin - none_mean_margin >= +0.05`.
- Paired Wilcoxon on per-row
  `(probe_readable_margin - partner_readable_margin) > 0` gives `p < 0.05`.
- At least `65/112` rows have `probe_readable_margin > partner_readable_margin`.
- Raw-symbol control does not exceed readable effect:
  `probe_raw_mean_margin - none_mean_margin < +0.05`.

Interpretation:

> Stage 18 closes a bounded visible-text tier for Qwen: generated continuations
> under probe-readable CAS realization are judged more target-Drive-aligned
> than wrong-partner continuations.

### NULL

Any one of these is enough for NULL:

- Drive judge test accuracy `< 0.60`.
- `probe_readable_mean_margin - partner_readable_mean_margin < +0.03`.
- fewer than `56/112` rows have
  `probe_readable_margin > partner_readable_margin`.

Interpretation:

> CPL2 likelihood remains the load-bearing eta-to-epsilon result; visible
> generated text is not established by Stage 18.

### GREY

Anything between PASS_CLEAN and NULL.

Interpretation:

> Visible text is suggestive but not clean. Do not use public visible-generation
> claims without a stronger judge or larger pre-registered pack.

## Required Artifacts

Commit:

- `STAGE18_QWEN_VISIBLE_TEXT_GATES_20260519.md`
- `run_stage18_qwen_visible_text_judge.py`
- `STAGE18_QWEN_VISIBLE_TEXT_REPORT_20260519.json`
- `STAGE18_QWEN_VISIBLE_TEXT_REPORT_20260519.md`
- `STAGE18_QWEN_VISIBLE_TEXT_SAMPLE_PACK_20260519.md`
- `STAGE18_QWEN_VISIBLE_TEXT_CLAIMS_20260519.md`
- README Stage 18 entry
- Claude audit handoff in `docs/working/agent_exchange/inbox_claude.md`

Do not commit:

- Any new activation `.npz` binary.
- Any generated cache directory.

## Audit Questions

1. Were gates committed before the run?
2. Was the Qwen layer fixed from Stage 16 before generation?
3. Was decoding deterministic and fixed?
4. Did the text judge get selected by validation before judging generated text?
5. Did raw-symbol control remain below readable-prefix effect?
6. Does wording stay at visible text-quality shift, not open-ended control?
