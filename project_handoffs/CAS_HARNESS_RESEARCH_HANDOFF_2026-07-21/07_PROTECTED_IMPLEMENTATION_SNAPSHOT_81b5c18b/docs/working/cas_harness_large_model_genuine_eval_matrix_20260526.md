# CAS Harness Large-Model Genuine Eval Matrix

Date: 2026-05-26

Purpose: produce real, non-demo CAS Harness evaluations on open-weight models
at approximately 20B, 100B, and 300B scale. This is the evidence ladder for
the claim that CAS Harness generalizes beyond small research models.

## Hard Rule

Do not call CAS Harness universal from screenshots, replay fixtures, dry-run
fleet receipts, or planner output.

The claim only starts to become defensible when the same CAS testing protocol
runs on real open weights across model size and architecture, and returns:

- model identity and weight/tokenizer hash
- assigned worker receipts
- CAS readout result
- causal ablation/intervention result
- matched-control result
- output-effect result
- verifier accept/suppress/flag result with confidence and coverage
- Evidence Packet for every audited run

## Candidate Model Ladder

| Tier | Primary model | Why this model | Architecture value | Source |
| --- | --- | --- | --- | --- |
| 20B | `EleutherAI/gpt-neox-20b` | Stable dense 20B open-weight baseline; Apache 2.0; same broad lineage as Pythia but much larger. | Dense GPT-NeoX transformer, good 20B scale bridge from Pythia. | https://huggingface.co/EleutherAI/gpt-neox-20b |
| 100B-class | `openai/gpt-oss-120b` | OpenAI open-weight 120B model family; strong current 100B-class target. | Sparse/MoE open-weight reasoning model; different lab and architecture from EleutherAI. | https://openai.com/open-models/ |
| 300B-class | `xai-org/grok-1` | Exact 300B-class target: 314B parameter MoE open release. | Large MoE, very different scale/runtime/architecture. | https://github.com/xai-org/grok-1 |
| 300B-class alternate | `Qwen/Qwen3-235B-A22B` | Modern Apache-2.0 235B MoE; useful if Grok-1 runtime blocks on JAX/hardware. | Modern MoE with 22B active parameters; strong architecture-diversity check. | https://huggingface.co/Qwen/Qwen3-235B-A22B |

## Why These Are Not Equivalent

Passing Pythia, OLMo, and Qwen small/medium runs proves CAS is not a one-off
toy. It does not prove CAS works at 20B, 100B, or 300B. Large-model proof
requires the same tests on real weights at larger scale.

The ladder is designed to test three things separately:

1. **Scale:** does CAS still read and intervene as parameter count grows?
2. **Architecture:** does it survive dense transformer vs MoE routing?
3. **Vendor/lab family:** does it hold outside one model lineage?

## Required Baselines

Each run must include controls. A raw CAS score alone is not enough.

1. **Text-only baseline**
   - Uses the same prompt/output text, but no hidden states.
   - Purpose: prove CAS is reading internal model structure, not just English wording.

2. **Shuffled-label baseline**
   - CAS labels are randomly permuted before probing.
   - Purpose: prove the labels are not succeeding by dataset leakage.

3. **Random same-size ablation**
   - Removes the same number/rank of neurons or directions as the CAS cover, but randomly.
   - Purpose: prove the targeted CAS cover matters more than random damage.

4. **Wrong-drive ablation**
   - Removes a calibrated cover for the wrong CAS drive.
   - Purpose: prove the effect is drive-specific, not just "any CAS-looking removal."

5. **Raw-symbol output control**
   - Tests whether raw CAS notation alone moves likelihood.
   - Purpose: prove the result is not caused by injecting CAS-looking tokens.

## Pass Criteria

These are pre-registered thresholds for calling a large-model run supportive.
They can be tightened later, but they should not be loosened after seeing the
results.

| Test | Passing evidence |
| --- | --- |
| Model identity | Exact model id, revision, tokenizer id, and weight hash recorded. |
| CAS readout | CAS hidden-state probe beats the text-only baseline by at least 15 percentage points, or beats it with `p < 0.01` on the locked scenario set. |
| Causal removal | Targeted CAS ablation/intervention causes a larger readout or output collapse than random same-size and wrong-drive controls. |
| Output effect | CAS-conditioned intervention shifts likelihood/verdict in the predicted direction and beats raw-symbol control. |
| Verifier | Accepted rows show high accepted accuracy, and coverage is reported separately. |
| Evidence Packet | Every reported result has an Evidence Packet or worker fragment bound to the audit id. |
| Fleet integrity | Large runs must have assigned workers and completed receipts before merge. |

## Claim Levels

| Result pattern | Allowed claim |
| --- | --- |
| 20B only passes | CAS scales beyond small models on one dense 20B open-weight target. |
| 20B + 100B pass | CAS shows cross-scale evidence from 20B to 100B-class open weights. |
| 20B + 100B + one 300B-class pass | CAS has genuine large-scale replication evidence across model size and architecture. |
| All three pass with controls | CAS Harness has strong evidence for broad open-weight generalization. |
| Any tier fails | Report the failure. Do not bury it. The failure tells us where CAS needs an adapter or where the claim boundary is. |

Do not say "CAS is universal" until the 300B-class run has real Evidence
Packets and at least one architecture-diverse replication passes.

## Execution Order

1. Merge and deploy PR #97: distributed control-plane + hardened receipt gate.
2. Merge PR #98: worker daemon bridge.
3. Attach the 20B target first.
   - Start with `EleutherAI/gpt-neox-20b`.
   - Run the 25 golden scenarios, then the full scenario set.
   - Confirm Evidence Packet fragments are produced by the worker daemon.
4. Attach the 100B-class target.
   - Start with `openai/gpt-oss-120b` if weights/runtime are available.
   - Run the same locked scenario set and controls.
5. Attach the 300B-class target.
   - Primary: `xai-org/grok-1`.
   - Alternate: `Qwen/Qwen3-235B-A22B` if Grok runtime blocks.
6. Generate one comparative report:
   - per-model readout delta vs baseline
   - ablation/intervention collapse vs controls
   - output-effect delta vs raw-symbol control
   - accepted accuracy and coverage
   - fragment receipt count
   - Evidence Packet hashes

## Hardware Reality

These evals are not just API calls.

- 20B can likely run on a single strong GPU depending on precision.
- 100B-class likely needs an H100/A100-class setup, quantization, tensor
  parallelism, or multiple workers.
- 300B-class requires a real worker fleet and enough aggregate memory for
  the weights plus activation/probe overhead. A 314B bf16 model is already
  roughly 628GB of weights before runtime overhead.

If the infrastructure cannot load the weights, the run fails. Do not replace
it with a planner result or a dry-run receipt.

## Meeting Language

Use this:

> We have already validated CAS Harness on smaller open-weight models. The
> next research gate is a pre-registered large-model ladder: 20B dense,
> 100B-class MoE, and 300B-class MoE. We will only count a result if it runs
> on real open weights and returns Evidence Packets with readout, ablation,
> matched controls, output-effect checks, and verifier metrics.

Do not use this yet:

> CAS is universal.

Use this only after the ladder passes:

> CAS Harness has strong open-weight replication evidence across model size
> and architecture.
