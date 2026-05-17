# Stage 7.CPL3 CAS-Prefix Generation

**Status:** `PROBE_PREFIX_GENERATION_HEURISTIC_NOT_CLEAN`

## Read

This tests whether the full eta-to-epsilon CAS Harness loop shows up in visible short generations. It uses a simple target-vs-partner Drive keyword heuristic plus a sample-read audit.

## Results

| Condition | Target Win Rate | Mean Lexical Margin | Delta vs None | Positive Delta Count | Sign p |
|---|---:|---:|---:|---:|---:|
| none | 0.018 | 0.036 | 0.000 | 0 / 56 | 1.0000 |
| gold_readable | 0.125 | 0.125 | 0.089 | 7 / 56 | 1.0000 |
| probe_readable | 0.125 | 0.107 | 0.071 | 7 / 56 | 1.0000 |
| partner_readable | 0.054 | -0.125 | -0.161 | 3 / 56 | 1.0000 |
| probe_raw | 0.018 | 0.000 | -0.036 | 1 / 56 | 1.0000 |

## Key Comparisons

- `probe_readable_delta_vs_none`: 0.0714
- `probe_readable_margin_minus_partner_readable`: 0.2321
- `probe_readable_target_win_minus_partner_readable`: 0.0714
- `gold_readable_delta_vs_none`: 0.0893
- `probe_raw_delta_vs_none`: -0.0357

## Implication

The likelihood bridge is stronger than the short-generation heuristic. Generated text is too noisy or the heuristic is too weak for a clean generation-control claim from this run.
