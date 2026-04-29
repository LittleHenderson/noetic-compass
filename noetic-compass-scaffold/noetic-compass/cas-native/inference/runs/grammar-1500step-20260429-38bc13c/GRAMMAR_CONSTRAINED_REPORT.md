# Grammar-Constrained Decoding Validation

Date: 2026-04-29

Code commit: `38bc13c`

Checkpoint:
`cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt`

Dataset:
`cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl`

Command mode:
`generate_samples.py --decode-mode grammar --samples-per-bucket 5`

## Headline

Grammar-constrained decoding reached `30/30` whole-expression compiler-valid
and `30/30` structured-valid on the same six-bucket, 30-sample qualitative
suite.

This is a material change from the earlier runs:

| Run | Structured-valid |
| --- | ---: |
| Free sampling, standard temperature | 3/30 |
| Free sampling, low temperature | 5/30 |
| Bucket-prefix priming | 1/30 |
| Grammar-constrained decoding | 30/30 |

## Bucket Results

| Bucket | Whole-valid | Structured-valid |
| --- | ---: | ---: |
| `v74_baseline` | 5/5 | 5/5 |
| `v75_register` | 5/5 | 5/5 |
| `v77_rule_four` | 5/5 | 5/5 |
| `v77_omega` | 5/5 | 5/5 |
| `v76_production` | 5/5 | 5/5 |
| `meta_logic` | 5/5 | 5/5 |

Candidate bank sizes used by the constrained decoder:

| Bucket | Compiler-valid candidates |
| --- | ---: |
| `v74_baseline` | 851 |
| `v75_register` | 2,320 |
| `v77_rule_four` | 480 |
| `v77_omega` | 36 |
| `v76_production` | 5 |
| `meta_logic` | 14 |

## Interpretation

The experiment confirms the main diagnosis from the primed run: raw model
sampling had learned CAS vocabulary and local motifs, but not enough grammar
state control. Once illegal next tokens are masked before temperature/top-p,
the same checkpoint can produce fully compiler-valid expressions.

This does **not** yet prove semantic correctness. The constrained decoder is
currently a finite candidate trie. It guarantees syntax by letting the model
choose among compiler-valid candidates, but for smaller banks the output can be
generic or repetitive:

- `v76_production` has only 5 candidates, so repetitions are expected.
- `meta_logic` has only 14 candidates and often emits broad examples such as
  `^2 ∈ Noetics`.
- `v77_omega` has 36 candidates and repeated `Ω_landing` / `Ω_refusal`
  examples in this run.

So the system has crossed the syntax-validity barrier, not the
prompt-faithfulness barrier.

## Product Implication

This is the right architecture direction:

1. The model supplies logits/preferences.
2. The grammar layer prevents malformed CAS.
3. The compiler remains the terminal authority.

User-facing CAS generation should use constrained decoding or a later
constrained+reranked path. Raw free-form model output should remain diagnostic
only.

## Next Engineering Step

The next step is semantic reranking / conditioned candidate generation:

1. Expand candidate banks from dataset-grounded expression families rather than
   hand-authored small sets.
2. Score candidates by model log-probability plus prompt/bucket compatibility.
3. Add exact/semantic-match metrics against the held-out `cas_expression`.
4. Keep the 30/30 compiler-valid gate as a non-negotiable product gate.

Recommended next gate:

- `>=95%` whole compiler-valid remains required.
- Add a second metric: semantic family match or expression-shape match by
  bucket.
- Target `>=70%` bucket-shape match before exposing model-generated CAS as a
  product feature.
