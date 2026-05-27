# Original Stage 7 / Stage 9 Text-Baseline Diagnostics - 2026-05-27

## Status

The original Pythia-era fixtures pass the stricter modern text-baseline
diagnostic. The leakage found in `tks40_balanced_v0_20260526.json` is **not**
inherent to the original Stage 7 / Stage 9 methodology.

The result is good news:

- Original Stage 9 40E text-only baseline: `49.24%`
- Original Stage 7 Foundation-28 text-only baseline: `54.08%`
- Both are below the pre-registered `<= 60%` ceiling.
- Both have `0` train/test group overlap.

## Why This Was Run

The guarded TKS40 v0 20B readout produced a strong hidden-state number
(`97.50%`) but also a `100.00%` text-only baseline. That blocked the specific
"CAS beats text" claim for that v0 TKS40 library.

The open question was whether the original Pythia-era Stage 9 and Stage 7
fixtures had the same problem under the stricter modern diagnostic. They do
not.

## Commands

Regenerate the historical Stage 9 pilot scenarios from commit `be9b4a3`:

```powershell
python live-trace-worker\scripts\export_original_stage9_scenarios.py `
  --output C:\tmp\stage9_original_40e_scenarios_export_20260527.json `
  --commit be9b4a3 `
  --mode pilot
```

Run the modern text diagnostic on original Stage 9 40E:

```powershell
python live-trace-worker\scripts\diagnose_tks40_text_baseline.py `
  --scenario C:\tmp\stage9_original_40e_scenarios_export_20260527.json `
  --output docs\working\stage9_original_40e_text_baseline_diagnostic_20260527.json `
  --label-key element `
  --axis-name original_stage9_40e `
  --group-key metadata.counterfactual_pair_id `
  --split-key metadata.split `
  --test-split test `
  --top-k 12 `
  --samples-per-label 3
```

Run the modern text diagnostic on original Stage 7 Foundation-28:

```powershell
python live-trace-worker\scripts\diagnose_tks40_text_baseline.py `
  --scenario live-trace-worker\scenarios\stage7_foundation_rolebound_pilot_20260526.json `
  --output docs\working\stage7_original_foundation28_text_baseline_diagnostic_20260527.json `
  --label-key foundation `
  --axis-name original_stage7_foundation28 `
  --group-key metadata.counterfactual_pair_id `
  --split-key metadata.split `
  --test-split test `
  --top-k 12 `
  --samples-per-label 3
```

## Results

| Fixture | Axis | Rows | Classes | Train | Test | Group Overlap | Text Accuracy | Macro-F1 | Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Original Stage 9 | 40 Elements | `8,320` | `40` | `3,840` | `4,480` | `0` | `49.24%` | `47.76%` | pass |
| Original Stage 7 | Foundation-28 | `4,368` | `28` | `2,016` | `2,352` | `0` | `54.08%` | `53.22%` | pass |
| New TKS40 v0 compact-gloss set | 40 Elements | `400` | `40` | `320` | `80` | `0` | `100.00%` | `100.00%` | blocked |

## Interpretation

The original fixture design is materially harder for text-only classifiers than
the compact TKS40 v0 scenario set.

The key design difference is the original role-bound counterfactual structure:

1. Each prompt contains two candidate roles in the same sentence.
2. The `Focus: A/B` marker selects which role is being labeled.
3. Train and test use explicit split metadata.
4. Test rows include additional paraphrase families.
5. The classifier cannot win by mapping one compact source-gloss phrase to one
   label as easily as it can in the v0 TKS40 builder.

## Claim Discipline

Allowed:

- The original Stage 9 40E fixture remains a meaningful text-baseline adversary
  under the modern diagnostic.
- The original Stage 7 Foundation-28 fixture remains a meaningful text-baseline
  adversary under the modern diagnostic.
- The modern `tks40_balanced_v0_20260526.json` library is the one that is
  blocked for CAS-beats-text claims.

Not allowed:

- Do not use the v0 compact-gloss TKS40 set as a headline "CAS beats text"
  result.
- Do not say every TKS40-style prompt set is clean by default. The original
  fixture structure is clean here; compact gloss injection is not.

## Next Move

For TKS40 large-model replication, reuse the original Stage 9 fixture design
instead of rebuilding blindly:

1. Regenerate/export the original Stage 9 role-bound scenario library.
2. Capture GPT-NeoX-20B activations on that exact fixture.
3. Re-run the balanced-logistic hidden-state readout.
4. Compare hidden readout against the now-confirmed `49.24%` modern text
   baseline.
5. Only then decide whether TKS40 needs a new v1 rewrite.

For Foundation-28, the `S7-F28-BALANCED-BRIDGE` path remains in the strong
reading: the original Foundation-28 text baseline is below the `<= 60%` ceiling.
