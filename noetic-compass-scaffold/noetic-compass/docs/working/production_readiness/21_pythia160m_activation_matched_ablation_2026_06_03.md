# Pythia-160M Activation Matched-Ablation Evidence - 2026-06-03

**Status: VERIFIED for stored-activation matched ablation.** This reused the
archived Pythia-160M activation dataset and did not rerun the Pythia model.

This closes one missing computation from the historical Stage 9 40E run: a
matched activation-level ablation over the stored hidden states. It does **not**
turn the packet into `ACCEPT`, because the final Stage 9 40E `ACCEPT` gate also
requires explicit matched-taxonomy / uniqueness proof.

## Inputs

Canonical archived run:

```text
D:\tksCAS-archive\pythia160m_gate1_reproduction_20260531
```

Stored activation dataset:

```text
D:\tksCAS-archive\pythia160m_gate1_reproduction_20260531\pythia160m_stage9_40e.npz
```

The dataset was read as stored activations:

```text
features: (8320, 12, 768), float16
layers: (12,)
labels_element: (8320,)
```

The original eval and cover reports were adapted into the generic ablation
runner's expected schema:

```text
docs\working\pythia160m_gate1\eval_adapter.json
docs\working\pythia160m_gate1\cover_adapter.json
```

## Command

The full run used the existing activation-level ablation runner:

```text
python live-trace-worker\scripts\ablate_probe_dataset.py --dataset "D:\tksCAS-archive\pythia160m_gate1_reproduction_20260531\pythia160m_stage9_40e.npz" --eval-report ".tmp\pythia160m_matched_ablation\eval_adapter.json" --cover-map ".tmp\pythia160m_matched_ablation\cover_adapter.json" --output-report ".tmp\pythia160m_matched_ablation\pythia160m_activation_cover_ablation_report.json" --random-trials 20 --seed 42
```

The report was then copied into the repo and archive:

```text
docs\working\pythia160m_gate1\pythia160m_activation_cover_ablation_report.json
D:\tksCAS-archive\pythia160m_activation_cover_ablation_20260603
```

## Result

Report schema:

```text
cas_harness_activation_cover_ablation_report.v1
```

Ablation mode:

```text
activation_level_train_mean_replacement
```

Evaluated axis:

```text
element
```

Best layer:

```text
3
```

Heldout examples:

```text
1680
```

Key within-report metrics:

```text
clean accuracy: 0.376786
label-specific cover accuracy: 0.322024
label-specific drop from clean: 0.054762
wrong-cover control drop from clean: 0.003572
label random same-size controls: 20 trials, max drop 0.005953
union cover accuracy: 0.268452
union cover drop from clean: 0.108334
union random same-size controls: 20 trials, max drop 0.0
```

Report summary:

```text
candidate cover is stronger than matched controls at activation level
label_drop_exceeds_random_max: true
label_drop_minus_random_mean: 0.053661
union_drop_exceeds_random_max: true
union_drop_minus_random_mean: 0.114524
union_drop_minus_wrong_drop: 0.104762
```

## Artifact Hashes

```text
pythia160m_activation_cover_ablation_report.json
SHA256 8093B49935FB37C7498956DE4960308D4126C1A3AEC428D602FC75678DE4860F

eval_adapter.json
SHA256 0408AD1F3084C92C8ED57F7FC25B7405ED6CA56440F989A7FA437BD9BAC7629A

cover_adapter.json
SHA256 8BE1396AE4A44C27B05846AF54F9A28147B8743CA8125B4C9CDF6122446C234A
```

Archive copy:

```text
D:\tksCAS-archive\pythia160m_activation_cover_ablation_20260603
```

## What This Proves

- The historical Pythia-160M run does not need to be rerun to test this gate.
- The archived hidden-state activations were sufficient to run matched
  activation-level ablation.
- The candidate neuron cover reduced heldout accuracy more than wrong-cover and
  same-size random controls within this ablation runner.

## What This Does Not Prove

- This does not make the packet `ACCEPT`.
- This does not replace the WORM-retained production verdict:
  `FLAG_FOR_HUMAN_REVIEW`.
- This does not prove matched-taxonomy / uniqueness.
- This does not prove customer production readiness.
- The clean accuracy in this ablation report is the ablation runner's internal
  refit/split metric. It should not be compared directly to the original
  91.72% Stage 9 40E probe-eval accuracy. The meaningful comparison here is
  within this report: candidate-cover drop versus matched random and wrong-cover
  controls.
