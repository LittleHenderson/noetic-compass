# CAS Harness MTC 20B Capture Runbook - 2026-05-30

## Status

The Stage MTC pilot fixtures are ready for GPT-NeoX-20B activation capture after the text-baseline gate.

Current pilot gate:

| Axis | Rows | CAS text-only baseline | Non-CAS text-only baseline | Status |
|---|---:|---:|---:|---|
| 40E | 1,000 | 32.00% | 6.00% | Ready for pilot capture |
| F28 | 700 | 10.00% | 0.00% | Ready for pilot capture |

This is a pilot capture gate only. It does not prove CAS specificity.

## Files Synced To Current RunPod

Remote pod:

```text
root@213.181.104.235 -p 18795
```

Remote script directory:

```text
/workspace/cas-harness-large-eval/live-trace-worker/scripts/
```

Synced scripts:

- `capture_open_weight_probe_dataset.py`
- `probe_dataset_common.py`
- `run_open_weight_probe_shard.py`

Remote scenario directory:

```text
/workspace/cas-harness-large-eval/scenarios/
```

Synced fixtures:

- `mtc_dual_labeled_40e_pilot_20260530.json`
- `mtc_dual_labeled_f28_pilot_20260530.json`
- `mtc_dual_labeled_40e_pilot_assignments_20260530.json`
- `mtc_dual_labeled_f28_pilot_assignments_20260530.json`

Remote verification already passed:

```text
mtc_dual_labeled_40e_pilot_20260530.json 1000 ['domain', 'element', 'operator']
mtc_dual_labeled_f28_pilot_20260530.json 700 ['drive', 'foundation', 'register']
```

## Do Not Start While Grok Download Is Active

The current 8x H200 pod is still downloading the final Grok-1 BF16 shards. Do not run GPT-NeoX-20B capture until the Grok download completes or is intentionally paused. Running both at once risks disk/network contention and another incomplete shard.

## Capture Commands

Run on the pod after the Grok download completes.

If this run is being treated as claim-bearing instead of exploratory pilot capture, first WORM-anchor the pre-registration, fixture JSONs, assignment JSONs, and text-baseline diagnostics. If it is exploratory pilot capture, record that scope explicitly in the resulting report.

```bash
cd /workspace/cas-harness-large-eval/live-trace-worker

mkdir -p /workspace/cas-harness-large-eval/datasets /workspace/hf-cache /workspace/tmp

export HF_HOME="/workspace/hf-cache"
export HF_HUB_CACHE="/workspace/hf-cache/hub"
export XDG_CACHE_HOME="/workspace/.cache"
export TMPDIR="/workspace/tmp"

python3 scripts/capture_open_weight_probe_dataset.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path /workspace/cas-harness-large-eval/scenarios/mtc_dual_labeled_40e_pilot_20260530.json \
  --output /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.npz \
  --metadata-output /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.metadata.json \
  --layer-start 0 \
  --layer-end 43 \
  --max-scenarios 0 \
  --max-length 768 \
  --torch-dtype float16 \
  --device-map auto

python3 scripts/capture_open_weight_probe_dataset.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path /workspace/cas-harness-large-eval/scenarios/mtc_dual_labeled_f28_pilot_20260530.json \
  --output /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_f28_pilot_20260530_layers_0_43.npz \
  --metadata-output /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_f28_pilot_20260530_layers_0_43.metadata.json \
  --layer-start 0 \
  --layer-end 43 \
  --max-scenarios 0 \
  --max-length 768 \
  --torch-dtype float16 \
  --device-map auto
```

Use `--max-length 768`, not the old `192`, because the marker-balanced prompts put row-specific instructions near the end.

## Expected Outputs

40E:

```text
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.npz
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.metadata.json
```

Expected shape: `[1000, 44, 6144]`.

F28:

```text
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_f28_pilot_20260530_layers_0_43.npz
/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_f28_pilot_20260530_layers_0_43.metadata.json
```

Expected shape: `[700, 44, 6144]`.

## Post-Capture Checks

```bash
ls -lh /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_*_pilot_20260530_layers_0_43*
sha256sum /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_*_pilot_20260530_layers_0_43*
```

If many `token_counts` equal `768`, the prompts are still being truncated and the capture must be rerun with a larger `--max-length`.

## Next After Capture

Run `run_matched_taxonomy_control.py` separately for 40E and F28 using:

- the captured `.npz`
- its `.metadata.json`
- the corresponding assignment JSON as `--manifest`

Then merge the reports into an Evidence Packet and WORM-anchor the packet before using any claim externally.

## Matched-Taxonomy Comparator Step (executed 2026-05-31)

This is the specificity lane. It asks, on the SAME 20B hidden states, whether
the CAS 40-Element partition is more linearly recoverable than a matched
alternative taxonomy and a scrambled null.

### Environment prep on pod

`scikit-learn` is NOT preinstalled on the H200 pod image. Install it first:

```bash
pip install -q scikit-learn   # pulls sklearn 1.8.x
```

sklearn 1.8 removed two kwargs the older runner passed:
- `LogisticRegression(multi_class=...)` — removed; multinomial is the default
  for `solver='lbfgs'`. Drop the kwarg.
- `n_jobs=-1` on `LogisticRegression` — now a no-op that only emits a
  `FutureWarning`. Harmless; ignore the warning spam in the log.

### Official runner invocation (claim-bearing)

```bash
cd /workspace/cas-harness-large-eval/live-trace-worker
nohup python3 -u scripts/run_matched_taxonomy_control.py \
  --dataset  /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.npz \
  --metadata /workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.metadata.json \
  --manifest /workspace/cas-harness-large-eval/scenarios/mtc_dual_labeled_40e_pilot_assignments_20260530.json \
  --output   /workspace/mtc_matched_taxonomy_40e_report_20260530.json \
  --axis 40e --layers all \
  > /workspace/mtc_official_40e.log 2>&1 &
```

Use `python3 -u` — without it, stdout is block-buffered to the log file and the
run looks silent for its entire duration.

Defaults match the headline probe and the prereg gates:
- probe `StandardScaler + LogisticRegression(C=0.1, class_weight='balanced', lbfgs)`
- text baseline `CountVectorizer(1-2gram, max_features=2^14) + LogisticRegression(C=1.0)`
- Gate 1 (`cas_hidden_readout_lift_over_text`): CAS hidden best-layer acc − CAS
  text acc must be ≥ `--cas-lift-threshold-pp` (default 20.0).
- Gate 2 (`cas_beats_coherent_matched_readout`): CAS hidden acc − each coherent
  control hidden acc must be ≥ `--matched-margin-pp` (default 5.0), on acc OR macro-F1.
- Gate 3 (`cas_flat_lacunarity_2x_cleaner`): CAS flat-lacunarity ≤ ½ best control.
- The runner auto-adds the preregistered scrambled-CAS taxonomy (first shuffled seed).

The 40E manifest carries one coherent matched control, `NC40_TOPIC_FRAME_V1`
(topic_40 × frame_40, 40 classes). The probe sweeps all 44 layers per taxonomy.

### Reading the verdict

The decision lives under `report["decision"]` / the `rules` block:
- Gate 1 FAIL ⇒ CAS is not recoverable above its own text baseline on this
  fixture. STOP — matched-taxonomy comparison is not interpretable. This is a
  fixture/configuration null, NOT a global CAS null (per the MTC 20B pilot
  results doc).
- Gate 1 PASS + Gate 2 PASS ⇒ CAS beats the matched alternative on the same
  hidden states — specificity evidence ON THIS FIXTURE only.

Honest caveat to attach to ANY result here: the dual_labeled CAS text baseline
is ~32% (non-trivial), so part of the CAS signal is text-visible. And this is
the dual_labeled pilot fixture, NOT the lost v1 fixture that produced the
95.625% headline. Read CAS-minus-control deltas, not absolute CAS accuracy.

### Quick directional alternative

`live-trace-worker/scripts/run_mtc_dual_labeled_comparator.py` is a lighter
ad-hoc comparator (cas_element / matched_control_tf / lexical_kmeans40 /
scrambled_cas, each at its own best layer). It is NOT prereg-aligned and not
claim-bearing — use only for a fast read; the official runner above is the
artifact to WORM-anchor.
