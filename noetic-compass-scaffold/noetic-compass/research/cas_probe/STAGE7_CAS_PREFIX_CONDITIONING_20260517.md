# Stage 7 CAS-Prefix Conditioning Probe

**Status:** `CAS_PREFIX_CONDITIONING_NOT_EFFECTIVE_IN_THIS_ASSAY`

## Read

This tests the missing in-between mechanism: use CAS as a readable prefix/context around Pythia's generation point instead of editing hidden states directly. Raw CAS symbols and human-readable CAS glosses are scored separately.

## Results

| Condition | Accuracy | Mean Margin | Mean Delta vs None | Sign p |
|---|---:|---:|---:|---:|
| none | 0.446 | -0.2054 | 0.0000 | 1.0000 |
| raw_correct | 0.446 | -0.1607 | 0.0446 | 0.9999 |
| raw_partner | 0.446 | -0.1786 | 0.0268 | 0.9999 |
| gloss_correct | 0.446 | -0.2232 | -0.0179 | 1.0000 |
| gloss_partner | 0.446 | -0.2321 | -0.0268 | 1.0000 |
| gloss_random_wrong | 0.446 | -0.1786 | 0.0268 | 1.0000 |

## Implication

This assay did not show reliable CAS-prefix conditioning. The next route would need training/fine-tuning, not just wrapping prompts. Raw CAS-symbol prefixes did not provide a strong route by themselves.
