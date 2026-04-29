# Slot-Aware Rerank Validation

Run: `slot-rerank-1500step-20260429-4e0d129`
Code commit: `4e0d129`
Checkpoint: `v2-first-full-20260428-220635/checkpoints/final.pt`
Dataset: `level2_full_10k.jsonl`
Mode: `--decode-mode rerank --candidate-source hybrid --family-filter prompt`

## Summary

Slot-aware filtering works on the cases it can explicitly read from the prompt. It preserves the prior syntax/family guarantees and improves typed-content selection for prompts that name concrete carriers, foundations, noetics, domains, or Omega targets.

| Metric | Result |
| --- | ---: |
| Samples | 30 |
| Whole compiler-valid | 30/30 |
| Structured CAS-valid | 30/30 |
| Prompt-family match | 30/30 |
| Required Omega-name anchors | 5/5 |
| Slot-match where applicable | 12/12 |
| Exact ground-truth match | 1/30 |

## Bucket Results

| Bucket | Structured | Family Match | Slot Match | Exact | Unique Outputs |
| --- | ---: | ---: | ---: | ---: | ---: |
| v74_baseline | 5/5 | 5/5 | n/a | 0/5 | 3/5 |
| v75_register | 5/5 | 5/5 | n/a | 0/5 | 4/5 |
| v77_rule_four | 5/5 | 5/5 | n/a | 0/5 | 1/5 |
| v77_omega | 5/5 | 5/5 | 5/5 | 1/5 | 4/5 |
| v76_production | 5/5 | 5/5 | 4/4 | 0/5 | 4/5 |
| meta_logic | 5/5 | 5/5 | 3/3 | 0/5 | 5/5 |

## Concrete Improvements

The previous family-rerank run proved the decoder could pick the right expression family. This slot-aware run shows it can also preserve explicit prompt anchors:

- `Omega_cadence`, `Omega_invocation`, `Omega_clarity`, and `Omega_refusal` prompts all generated expressions containing the requested `Omega_*` target.
- `Product(Foundations, Domains)` generated `Product(Domains, Foundations)`, preserving both requested carriers.
- `Foundation_1..Foundation_7 cover SubFoundations` generated `CoverOf(SubFoundations, ...)` containing all seven foundations.
- `NoeticCluster over noetics 8, 3` generated `NoeticCluster{^4, ^3, ^1, ^8, ^7}`, which preserves both requested noetics but still adds extra members.
- Production prompts naming principled/cognitive/evaluative/operational domains generated recipes containing those requested domain slots.

## Remaining Gap

Exact-match is still only `1/30`. That is expected after this patch because slot filtering checks containment, not equality. A candidate can satisfy the requested slots while still adding extra members or choosing a different but slot-compatible recipe.

The clearest example is:

```text
Prompt: Explain the typed NoeticCluster over noetics 8, 3.
Generated: NoeticCluster{^4, ^3, ^1, ^8, ^7}
```

This is slot-correct because it contains `^8` and `^3`, but it is not minimal or exact. The next improvement is not more unconstrained GPU training; it is stricter slot policies.

## Next Engineering Move

Add slot policy modes:

- `subset`: current behavior; requested slots must be present.
- `exact`: generated slot set must equal requested slot set when prompt wording implies a closed set, e.g. "over noetics 8, 3".
- `ordered`: generated carrier order must match prompt order when the expression family is ordered, e.g. `Product(Foundations, Domains)`.
- `soft`: keep the current filter but add a scoring penalty for extra slots.

The likely next patch should implement exact/minimal filtering for clusters and ordered carrier filtering for `Product(...)`. That should improve exact-match for meta-logic without needing another training run.

## Verification

Local:

```text
python -m py_compile constrained_sampling.py generate_samples.py test_constrained_sampling.py
python -m pytest test_constrained_sampling.py test_tokenizer.py -q
17 passed, 4 skipped
```

Pod:

```text
python cas-native/inference/generate_samples.py \
  --dataset /root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
  --checkpoint /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt \
  --out-dir /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/slot-rerank-1500step-20260429-4e0d129 \
  --decode-mode rerank \
  --candidate-source hybrid \
  --family-filter prompt \
  --rerank-max-candidates 2000 \
  --rerank-batch-size 64 \
  --samples-per-bucket 5
```
