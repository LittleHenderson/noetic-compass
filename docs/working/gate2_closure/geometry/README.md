# Track B — Model-Internal Grid Geometry

## Purpose

Test whether TKS definitions exhibit the 10×4 (Noetic × Domain) grid structure
in a language model's internal representations — WITHOUT any external test bank.

The "ground truth" is the 10×4 grid structure itself: a mathematical property.
No human-labeled test items needed.

## Theory

If TKS definitions genuinely capture compositional structure (the claim under
test), then embeddings of the 40 definition texts should naturally organize into
a grid where:

- Cells sharing the same Noetic (row) are similar
- Cells sharing the same Domain (column) are similar
- A held-out cell can be reconstructed from its row + column siblings
- Compact CAS definitions (concatenated, not composed) should show weaker structure

## Files

| File | Purpose |
|---|---|
| `grid_alignment.py` | Full analysis: encodes definitions, computes grid metrics, runs permutation tests |

## Usage

```bash
cd docs/working/gate2_closure/geometry

python grid_alignment.py \
  --tks-defs ../tks_owner_locked_definitions_20260603.json \
  --cas-defs ../item4_arms/arm_D_compact_cas.json \
  --model EleutherAI/pythia-160m \
  --layer 12 \
  --n-perm 1000 \
  --output grid_results.json
```

Or with pre-computed embeddings to skip model inference:

```bash
python grid_alignment.py \
  --tks-defs ../tks_owner_locked_definitions_20260603.json \
  --cas-defs ../item4_arms/arm_D_compact_cas.json \
  --embeddings /path/to/precomputed.npz \
  --output grid_results.json
```

## Metrics

| Metric | What it measures | Interpretation |
|---|---|---|
| Row coherence | Cosine similarity between same-Noetic vs different-Noetic cells | Higher = row structure present |
| Column coherence | Cosine similarity between same-Domain vs different-Domain cells | Higher = column structure present |
| Neighbor rank | Fraction of top-3 nearest neighbors that are grid siblings | > 0.308 (chance) = grid structure |
| CV reconstruction | Cosine between held-out cell and its row+col composition | > 0 = compositional structure |
| Combined grid score | Average of normalized component scores | > 0 = some grid structure |
| Permutation p | Likelihood of observing grid score under shuffled labels | < 0.05 = significant |

## Comparison

The primary comparison is TKS vs compact CAS:

- **TKS > CAS with CI excluding zero** → TKS definitions exhibit stronger compositional structure in model-internal geometry
- **No reliable difference** → both show similar structure (or neither does)
- **CAS > TKS** → unexpected result, would require explanation

## Interpretation Ceiling

A positive result licenses: "TKS definitions induce stronger 10×4 grid geometry
in this model's hidden states than concatenated CAS definitions."

It does NOT license: claims about human comprehension, cross-model universality,
or product readiness.

## Relationship to Gate 2 Item 4

Track B is orthogonal to the behavioral bank experiment:

- **Track B** tests whether definitions INTERNALLY exhibit grid structure
- **Gate 2 Item 4** tests whether definitions enable accurate classification of EXTERNAL items

Both contribute evidence to the same underlying claim, but through different
mechanisms. Track B cannot be killed by the shared-authorship confound because
it measures definition geometry, not classification accuracy against a test bank.

## Status

`SPECIFIED / SCRIPT WRITTEN / NOT YET EXECUTED`
