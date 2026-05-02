# Lexicon Coverage Diagnostic

- Lexicon size: **191**
- Canonical eval: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\level2_scaffold\level3_recoverable_eval_1000.jsonl`
- Paraphrases per record: 3

## Canonical eval

- Records: 1,000
- Total tokens: 74,357
- Signal-bearing tokens (LEXICON+CAS_NOTATION): 9,891 (13.3%)

| Source | Tokens | Fraction |
|---|---:|---:|
| LEXICON | 2,609 | 3.51% |
| CAS_NOTATION | 7,282 | 9.79% |
| LEARNED | 0 | 0.00% |
| FALLBACK | 64,466 | 86.70% |

## Paraphrase eval

- Records: 3,000
- Total tokens: 221,272
- Signal-bearing tokens (LEXICON+CAS_NOTATION): 27,261 (12.3%)

| Source | Tokens | Fraction |
|---|---:|---:|
| LEXICON | 5,415 | 2.45% |
| CAS_NOTATION | 21,846 | 9.87% |
| LEARNED | 0 | 0.00% |
| FALLBACK | 194,011 | 87.68% |

## Headline delta

- Canonical signal fraction: **13.3%**
- Paraphrase signal fraction: **12.3%**
- Δ paraphrase − canonical: **-0.98 pp**

If the paraphrase signal fraction is meaningfully *below* canonical, the lexicon is the OOV bottleneck on paraphrase generalization. If they are close, the encoder — not the lexicon — is the next bottleneck.

## By bucket

| Bucket | Canonical signal % | Paraphrase signal % | Δ (pp) |
|---|---:|---:|---:|
| meta_logic | 9.6% | 8.3% | -1.26 |
| v74_baseline | 11.7% | 9.9% | -1.84 |
| v75_register | 13.4% | 12.0% | -1.47 |
| v76_production | 13.8% | 13.5% | -0.33 |
| v77_omega | 13.8% | 12.9% | -0.93 |
| v77_rule_four | 14.2% | 13.3% | -0.86 |
