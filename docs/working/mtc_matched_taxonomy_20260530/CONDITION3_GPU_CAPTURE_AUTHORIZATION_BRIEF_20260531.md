# Condition-3 GPU comparative-capture — authorization brief (2026-05-31)

**Status: AWAITING EXPLICIT AUTHORIZATION. No GPU launched. No dollars spent.**
Per project rule, this run is gated on `AUTHORIZED: yes` in `decisions.md` **and** a
chat "go". This brief gives the exact commands, cost, runtime, and abort conditions.

---

## What the capture is

A two-step pipeline. **Only Step 1 costs GPU money.**

| Step | Where | Cost | What it does |
|---|---|---|---|
| 1. Activation extraction | GPU pod (RunPod) | **paid** | Run GPT-NeoX-20B forward over the 1440 Condition-3 prompts, dump per-layer last-token hidden vectors → one `.npz`. |
| 2. Matched-taxonomy comparator | CPU (local or pod) | **$0** | sklearn logistic probes on the saved `.npz`: CAS element vs Control B (NC40) vs Control C (NC28) vs lexical-kmeans vs scrambled null. Reads hidden−text lift per label set. |

The science question (prereg `cas_harness_matched_taxonomy_control_prereg_20260530.md`):
*on the SAME 20B hidden states, is the CAS 40-element partition more linearly
recoverable than coherent same-size non-CAS opponents?*

---

## TWO $0 pre-steps are REQUIRED before the paid run (honest blocker)

The existing harness does **not** ingest the Condition-3 fixture as-is. Both fixes are
local, free, and must land before spending a GPU dollar:

1. **Fixture → capture-schema adapter.** `capture_open_weight_probe_dataset.py` loads
   prompts via `load_labeled_scenarios`, which reads `prompt`/`text` + `id`/`scenario_id`
   + `expected_cas_axes`/`target_*` label fields. The Condition-3 fixture uses
   `english` / `sample_id` / `element_label`. **As-is the loader silently skips all 1440
   rows** ("No labeled scenarios found"). Need a ~20-line emitter that rewrites the
   fixture into `{id: sample_id, prompt: english, expected_cas_axes:{element:…}, split,
   control_semantic:{topic_40,frame_40,topic_7,function_4}}`.

2. **Comparator Control-C extension.** `run_mtc_dual_labeled_comparator.py` currently
   probes only Control B (`topic_40|frame_40`). Add the Control C arm
   (`topic_7|function_4`) **restricted to the 1008 sample_ids in
   `control_c_nc28_balanced_view_20260531.json`**, and point its `load()` at the
   Condition-3 control fields. ~30 lines.

I can build both on authorization (they're CPU/$0 and independently testable before any
GPU spend), or you can have them reviewed first. Until they exist, the GPU command below
will produce an empty/garbage dataset.

---

## Exact commands (valid once the two pre-steps land)

### Step 1 — GPU activation extraction (the paid step)

```bash
# on the RunPod pod, repo synced, HF cache warm or model on a network volume
python noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/capture_open_weight_probe_dataset.py \
  --model-id EleutherAI/gpt-neox-20b \
  --scenario-path docs/working/mtc_matched_taxonomy_20260530/mtc_condition3_capture_view_20260531.jsonl \
  --output docs/working/mtc_matched_taxonomy_20260530/condition3_gptneox20b_activations_20260531.npz \
  --torch-dtype float16 \
  --device-map auto \
  --max-length 192
```

- Captures last-token MLP output for **all 44 layers** (default `--layer-start 0`,
  `--layer-end = num_layers-1`). Hidden size 6144 → `features` shape ≈ (1440, 44, 6144)
  fp16 ≈ **0.78 GB raw** (compressed npz ~0.5–0.7 GB to download).
- `mtc_condition3_capture_view_20260531.jsonl` is the output of pre-step 1.

### Step 2 — CPU comparator ($0, runs on pod CPU or locally)

```bash
python noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/run_mtc_dual_labeled_comparator.py \
  --npz docs/working/mtc_matched_taxonomy_20260530/condition3_gptneox20b_activations_20260531.npz \
  --fixture docs/working/mtc_matched_taxonomy_20260530/mtc_condition3_topical_scenarios_20260531.jsonl \
  --control-c-view docs/working/mtc_matched_taxonomy_20260530/control_c_nc28_balanced_view_20260531.json \
  --out docs/working/mtc_matched_taxonomy_20260530/condition3_mtc_comparator_result_20260531.json
```

(`--control-c-view` is the new flag added in pre-step 2.)

---

## Cost estimate & runtime

GPT-NeoX-20B fp16 ≈ 40 GB weights → needs one **48–80 GB GPU** (A6000 48 GB, A40 48 GB,
A100 80 GB, or H100), or 2×24 GB via `device-map auto`.

| GPU (RunPod) | ~$/hr | model load | 1440 fwd passes (1/prompt, ≤192 tok) | est. wall clock | **est. cost** |
|---|---|---|---|---|---|
| A6000 48 GB | $0.5–0.8 | 3–6 min (warm cache) | ~15–30 min | ~30–45 min | **~$0.4–0.6** |
| A100 80 GB | $1.6–2.5 | 2–4 min | ~10–20 min | ~25–40 min | **~$1–2** |
| H100 80 GB | $2.5–4.0 | 2–4 min | ~8–15 min | ~20–30 min | **~$1.5–2.5** |

**First-time model pull adds ~40 GB download (~10–20 min)** unless GPT-NeoX-20B is
already on a network volume / HF cache (prior gpt_neox_20b stages suggest it may be).
Realistic all-in for one capture: **~$1–3 and well under an hour.** Step 2 is free
(a few minutes of CPU: 44 layers × 4 label sets of balanced logistic).

---

## Abort conditions (kill the pod, do not pay further)

- **Loader skip**: `[capture]` progress shows fewer than 1440 scenarios, or
  "No labeled scenarios found" → pre-step 1 adapter is wrong. Abort before the forward loop.
- **OOM / device-map spill to CPU**: capture rate falls below ~1 prompt/2s (CPU-offload
  thrash) → wrong GPU size. Abort, pick a bigger card.
- **Wrong model fingerprint**: metadata `model_info.num_hidden_layers != 44` or
  `hidden_size != 6144` → wrong checkpoint/revision. Abort.
- **Token blow-up**: many prompts hitting `token_count == 192` (truncation) → prompts
  longer than expected; Condition-3 prompts are short, so this signals a bad capture view. Abort.
- **NaN/inf in features** or all-zero layers → hook/dtype problem. Abort, do not run Step 2.
- **Wall clock > 90 min** with no completion → something is wrong; stop and diagnose.

Back up the `.npz` + metadata + the comparator result + commit hash to
`D:\tksCAS-archive\` **immediately** on a successful run (per standing rule), before
tearing down the pod.

---

## How to read the result (prereg decision thresholds)

From `cas_harness_matched_taxonomy_control_prereg_20260530.md`:

- **PASS** (comparative specificity licensed at 20B): CAS hidden readout ≥ **20 pp**
  above its own text baseline; CAS lift beats **every** coherent comparator (Control B
  NC40 **and** Control C NC28) by the pre-registered `delta_lift` margin (≥5 pp);
  scrambled stays near chance. (Lacunarity legs apply to the F28 nested arm.)
- **FAIL**: any coherent non-CAS matched taxonomy matches or beats CAS on lift, or the
  7×4 nested comparator lands within 1.5× of CAS on nested lacunarity.
- **BLOCKED** (not FAIL): execution can't fairly score — comparator can't be
  materialized, or the margin is unstable (`BLOCKED_MARGIN_UNSTABLE`). The threshold is
  **not** retuned after seeing the result.

The key honesty point the prereg already records: the Condition-3 CAS text baseline is
near-chance (Surface Gate 6.25%), so unlike the lost dual_labeled pilot, the
hidden−text **lift** here is a clean specificity signal rather than text leakage. This
is exactly why Condition-3 can earn a comparative PASS/FAIL that Condition-2 could not.

---

## One-line recommendation

Fixture is eligible (all 3 local gates GREEN; Control C now ELIGIBLE_SECONDARY). The
only thing between here and a claim-bearing comparative result is the **two $0 adapters**
above plus **one ~$1–3 GPU capture**. Recommend: authorize the two adapters now (free,
reviewable), hold the GPU launch for a separate explicit "go".
