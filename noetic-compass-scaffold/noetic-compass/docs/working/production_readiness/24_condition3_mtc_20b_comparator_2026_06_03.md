# Condition-3 MTC 20B Comparator Evidence - 2026-06-03

**Status: COMPLETED with verdict `GREY`.** The GPT-NeoX-20B
Condition-3 matched-taxonomy comparator ran on the captured activation dataset
from the replacement H200 pod. It did not return `PASS`, `FALSIFY`, or
`BLOCKED`.

This is a 20B Stage X.1 comparator result only. It does not alter the
WORM-retained Pythia-160M packet, which remains `FLAG_FOR_HUMAN_REVIEW`.

## Verdict

```text
decision: GREY
status: completed
pass: false
grey: true
falsify: false
blocked: false
fail: false
rationale: CAS did not fully satisfy both readout and lacunarity gates; uniqueness remains open.
```

## Run Scope

```text
stage: Stage X.1
scope: 20B-only matched-taxonomy decision gate
model: EleutherAI/gpt-neox-20b
axis: 40e
seed: 20260530
split mode: auto
test size: 0.2
```

The cross-architecture extension remains conditional and was not executed.

## Input Dataset

```text
dataset: /workspace/condition3_gptneox20b_activations.npz
metadata: /workspace/condition3_gptneox20b_metadata.json
manifest: /workspace/condition3_mtc_row_level_manifest_20260603.json
samples: 1440
layers: 44
hidden dim: 6144
taxonomies evaluated: 4
```

The row-level manifest derives rival labels from `control_semantic`, not from
CAS labels.

## Comparator Command

```text
cd /workspace
python scripts/run_matched_taxonomy_control.py \
  --dataset /workspace/condition3_gptneox20b_activations.npz \
  --metadata /workspace/condition3_gptneox20b_metadata.json \
  --manifest /workspace/condition3_mtc_row_level_manifest_20260603.json \
  --output /workspace/condition3_mtc_20b_comparator_result_20260603.json \
  --axis 40e \
  --seed 20260530 \
  --test-size 0.2 \
  --split-mode auto \
  --progress
```

The comparator completed and wrote:

```text
/workspace/condition3_mtc_20b_comparator_result_20260603.json
```

## Rule Outcomes

```text
cas_hidden_readout_lift_over_text: passed
  CAS hidden accuracy: 0.5347222222222222
  CAS text accuracy:   0.09722222222222222
  observed lift:       43.75 pp
  required lift:       20.0 pp

cas_flat_lacunarity_2x_cleaner: passed
  CAS flat lacunarity:                  0.04394354424923896
  best coherent matched flat lacunarity: 0.1160894894797089

scrambled_cas_near_chance_no_clean_structure: passed
  scrambled CAS accuracy:        0.03819444444444445
  near-chance threshold:         0.07500000000000001
  max shuffled-label accuracy:   0.04513888888888889

coherent_matched_taxonomy_presence: present

cas_beats_coherent_matched_readout: failed
  required margin:       +5.0 pp
  observed accuracy margin vs NC40: -46.52777777777778 pp
  observed macro-F1 margin vs NC40: -47.37143534570005 pp
```

## Taxonomy Summary

```text
CAS 40E:
  best hidden layer: 12
  hidden accuracy:  0.5347222222222222
  hidden macro-F1:  0.5262856465429995
  text accuracy:    0.09722222222222222
  flat lacunarity:  0.04394354424923896

Condition-3 NC40 topic x frame:
  best hidden layer: 13
  hidden accuracy:  1.0
  hidden macro-F1:  1.0
  text accuracy:    1.0
  flat lacunarity:  0.1160894894797089

Condition-3 NC28 topic x function:
  best hidden layer: 20
  hidden accuracy:  1.0
  hidden macro-F1:  1.0
  text accuracy:    1.0
  flat lacunarity:  0.3287381546174172

Scrambled CAS seed 20260530:
  best hidden layer: 6
  hidden accuracy:  0.03819444444444445
  hidden macro-F1:  0.03875136194215141
  text accuracy:    0.010416666666666666
  flat lacunarity:  0.05558920546631349
```

## Archive

Local archive:

```text
D:\tksCAS-archive\condition3_mtc_comparator_20260603
```

Archived files:

```text
condition3_mtc_20b_comparator_result_20260603.json
condition3_mtc_20b_comparator_20260603.log
condition3_mtc_row_level_manifest_20260603.json
```

SHA-256:

```text
condition3_mtc_20b_comparator_result_20260603.json
860956BA3C0267AB2A3EE9A56643A0B115064F7AE4B9430F9040F88CC3DFC274

condition3_mtc_20b_comparator_20260603.log
8E2978606F66209BCA7E127D1809E39FB4DAFD37884BE4F5DD475E860970474A

condition3_mtc_row_level_manifest_20260603.json
B33A23F961579EE34088CD25E4D709237018979B05F1E006FBA0D20214EABC53
```

## Claim Boundary

This result keeps uniqueness open. It is not a 20B `PASS`, and it is not a
Pythia-160M uniqueness proof. It therefore does not permit the Pythia-160M
Stage 9 40E packet to move from `FLAG_FOR_HUMAN_REVIEW` to `ACCEPT`.

