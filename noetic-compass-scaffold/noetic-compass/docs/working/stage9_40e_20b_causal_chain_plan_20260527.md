# Stage 9 40E 20B Causal Chain Plan

## Scope

Method label: `S9-40E-ORIGINAL-BASELINE-READOUT`

Current proof: GPT-NeoX-20B hidden readout reaches **95.625%** on Stage 9 40E, versus the confirmed text-only baseline at **49.241071%**. The measured lift is **+46.383929 percentage points**.

Bounded claim today: the 20B hidden states contain a recoverable 40E signal far above the confirmed text-only baseline, and the assembled Stage 9 validation packet returns packet-level verifier `ACCEPT` with confidence **0.95625**.

Not claimed yet: live customer-production verdicts, 100B/300B universality, complete neuron-by-neuron causal maps, or compact-gloss TKS40 v0 closure. Compact-gloss TKS40 v0 is blocked as a proof target because text-only hit **100%**.

## Chain

| Step | Gate | Pass Threshold | Fail Condition | What It Proves | Output |
| --- | --- | --- | --- | --- | --- |
| 1. Readout anchor | Reproduce `S9-40E-ORIGINAL-BASELINE-READOUT` on frozen GPT-NeoX-20B activations and the confirmed text-only baseline. | Hidden readout stays at or above **95.0%**, text-only stays at or below **50.5%**, and hidden-over-text lift stays at or above **40 pp**. | Hidden readout falls below threshold, text baseline rises enough to explain the result, or the split/method label is not reproducible. | 40E labels are linearly recoverable from hidden states beyond the confirmed surface-text baseline. | Readout metrics, split manifest, model/layer metadata, method label, seed/config hash. |
| 2. Subspace ablation | Remove the trained readout subspace from held-out activations and compare against dimension-matched random subspaces. | Targeted ablation drops hidden readout by at least **30 pp** or to **65% or lower**; matched random ablations move readout by **5 pp or less**; non-target sanity metrics do not globally collapse. | Targeted ablation does not selectively reduce the signal, or random ablations cause comparable damage. | The readout subspace is necessary for the measured hidden-state signal, not just a passive classifier artifact. | Ablation report with targeted, random, layer-matched, and no-op controls. |
| 3. Cover discovery | Find the smallest stable layer/head/neuron cover that carries the ablatable subspace. | A sparse cover explains at least **80%** of readout-subspace variance or preserves at least **90%** of full readout accuracy when retained; ablating the cover recovers at least **70%** of the full subspace-ablation drop; non-cover controls stay within **10 pp**. | No stable cover appears across seeds/splits, or the cover is so diffuse that it is not inspectable. | The signal has inspectable carriers rather than being only a whole-network aggregate. | Cover manifest with components, scores, stability checks, and retained/ablated metrics. |
| 4. Matched controls | Run label, lexical, position, layer, model, and ablation controls on the same evaluation harness. | Shuffled-label and random-subspace controls stay near chance or below **10%**; lexical/text-only controls stay near the confirmed **49.241071%** baseline and below **55%**; no matched control closes more than one quarter of the hidden-over-text gap. | A control reaches a hidden-readout-like score, a text-only variant solves the task, or controls expose leakage. Compact-gloss-style **100%** text-only results invalidate that target. | The result is not explained by label imbalance, lexical leakage, token position, or generic damage from intervention. | Control matrix with pass/fail rows and explicit invalid-target notes. |
| 5. Eta-to-epsilon bridge | Use the detected internal 40E state to condition external model likelihoods, then compare against neutral and wrong-class bridges. | Correct-class likelihood improves on at least **65%** of held-out examples; aggregate paired bootstrap confidence interval is strictly above zero; wrong-class and neutral bridges do not show the same lift. | Likelihood shifts are nonspecific, vanish under controls, or improve wrong classes equally. | The internal readout can be realized as external evidence that moves model likelihoods in the predicted direction. | Bridge report with per-item likelihood deltas, aggregate confidence interval, and control prefixes. |
| 6. Evidence Packet | Assemble the readout, ablation, cover, controls, bridge, caveats, hashes, and rerun commands into one auditable artifact. | Packet includes every upstream artifact, the current numbers (**95.625%** vs **49.241071%**), model/split/method hashes, pass/fail status, caveats, and an explicit packet verifier decision. | Any upstream gate is missing, unverifiable, or overstates what was proven. | The causal chain is reviewable as a durable audit record. It does not by itself prove safety or general truth. | `gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json` with verifier `ACCEPT`, confidence **0.95625**, and scope `stage9_40e_validation_packet`. |

## Release Discipline

Do not promote compact-gloss TKS40 v0. Do not claim 100B/300B universality from the 20B packet. Do not present the Stage 9 validation-packet `ACCEPT` as a live customer-production verdict. Every new model, prompt library, or fleet run needs its own Evidence Packet and verifier decision.

The intended product posture is: **"Turn your black box into a glass house."** The engineering bar is that every pane in that glass house has a named method, a baseline, a control, and a reproducible artifact.
