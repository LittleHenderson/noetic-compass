# Stage 17 Consolidated Claims Matrix

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

## Formal Verdict

`CAS_HARNESS_CROSS_ARCHITECTURE_LIKELIHOOD_CONDITIONING_SUPPORTED`

The consolidated Stage 7-16 record supports a bounded CAS Harness claim:

> Across Pythia, OLMo, and Qwen, CAS Harness can recover a 28-Foundation
> signal from hidden activations and realize that signal as readable context
> that shifts semantic likelihood under pre-registered CPL2-style gates.

It does not support stronger black-box claims such as exact causal-neuron
identification, raw CAS-symbol understanding, or open-ended generation control.

## Supported Claims

| Claim | Evidence | Allowed wording |
|---|---|---|
| Open-model hidden activations can contain CAS-readable structure. | Stage 7 Foundations, Stage 9 40 Elements, Stage 11 expression shapes, Stage 12 formula families. | "CAS can recover bounded CAS labels from open-model hidden activations." |
| The 28-Foundation readout is not just a text classifier on the Stage 7 fixture. | Stage 7 activation acc `0.7857` vs text `0.4966`, McNemar p `2.66e-95`; metadata baseline also beaten. | "The activation readout materially beats text and metadata baselines." |
| The Stage 7 Foundation subspace is causal for the trained CAS readout. | Targeted removal drops `0.7857 -> 0.0357` exact chance; random removals null. | "The trained subspace is load-bearing for the CAS readout." |
| The original TKS 40 Elements are strongly readable in Pythia-160M. | Stage 9 full 40-way acc `0.8980`, +39.7 pp over text, ablation to exact chance. | "The 40-Element structure is strongly readable and readout-causal in Pythia-160M." |
| Expression grammar shape is readable beyond text and metadata. | Stage 11 acc `0.9300`, text `0.6443`, metadata `0.6667`, ablation to chance. | "CAS expression-shape information is readable and readout-causal." |
| Compiler-backed formula families are readable beyond text and metadata. | Stage 12 acc `0.8995`, text `0.6393`, metadata `0.6667`, ablation to chance. | "Compiler-validated formula-family labels are readable from hidden states." |
| CAS can expose blind spots as unstable readout evidence. | Stage 13 traces: `77.7%` stable-like, `22.3%` problem-like; Stage 13.1 confirms balance and thresholds. | "CAS can flag weak, drifting, or conflicted readout paths." |
| CAS can inspect bounded weight geometry. | Stage 14.1 output logit-lens energy `2.83x` random, p `0.0099`. | "The CAS subspace is above random on some output-weight geometry checks." |
| Eta-to-epsilon conditioning transfers across Pythia scale. | Pythia-160M, 1B, 2.8B all pass readable-prefix likelihood bridge. | "The read-realize-condition bridge replicates across three Pythia scales." |
| Eta-to-epsilon conditioning transfers across architecture families. | OLMo-1B and Qwen2.5-1.5B pass after Pythia. | "The bridge replicated across Pythia, OLMo, and Qwen." |
| Multi-harness composition is the next hidden-content audit architecture. | The current single-axis harness loop passes; Stage 13 already shows multi-layer tracing; the spec now generalizes eta-1 into a multi-axis tensor. | "Multi-harness composition should make hidden-content gaps more decomposable; it is the next engineering architecture, not a completed experiment." |

## Bounded Or Grey Claims

| Claim | Status | Evidence | Required wording |
|---|---|---|---|
| Five isolated CAS operators are recoverable. | Grey, ceiling-limited | Stage 10 activation `0.9918`, text `0.9557`, lift only +3.61 pp; ablation to chance. | "Operators are highly readable and readout-causal, but the isolated task is too easy for text." |
| Register is a clean independent factor in Stage 7. | Bounded | Register readout is real and ablates to chance, but text baseline exceeds activation. | "Register is visible but text-explained in the Stage 7 fixture." |
| Weight geometry explains generation control. | Bounded | Stage 14.1 supports output-alignment inspection only. | "Weight geometry is a technical appendix, not a steering proof." |
| Blind-spot labels prove the model cannot represent a class. | Bounded | Stage 13.1 shows some weaknesses are readout-path-specific. | "Blind spots mean weak or unstable evidence under a given readout path." |

## Rejected Or Not-Yet-Supported Claims

| Claim | Status | Reason |
|---|---|---|
| CAS sees exact internal neurons that caused an answer. | Not supported | Current probes and traces are readout-level and subspace-level, not exact causal-neuron proofs. |
| CAS sees weights firing. | Rejected phrasing | Weights are static parameters. Activations change per input. |
| Pythia, OLMo, or Qwen internally run a CAS compiler. | Not supported | Compiler validation is external fixture provenance. |
| Raw CAS symbols alone condition host models. | Not supported | Raw controls are near null across the CPL2 line. |
| Hidden-state steering is solved. | Not supported | Stage 7 hidden-state ablation/additive generation routes failed random controls. |
| Open-ended visible generated-language control is solved. | Not supported | Visible text generation remains the Stage 18 gate. |
| The black-box problem is fully solved. | Not supported | CAS reduces opacity for tested structures; it does not expose every cause of every output. |
| Multi-harness composition has already detected intentional hiding. | Not yet supported | Current evidence proves the components and rationale, not a completed multi-axis hiding benchmark. |

## Claim Levels For Evidence Packets

| Level | Badge | Meaning | Example |
|---|---|---|---|
| 1 | Provenance | File, model, fixture, and hash can be verified. | model revision and fixture SHA match manifest |
| 2 | Readout | A trained probe recovers a CAS label from activations. | Stage 16 Qwen selected layer 11 test acc `0.8202` |
| 3 | Beyond text | Activation readout beats text/metadata baselines. | Stage 12 lift +26.0 pp over text |
| 4 | Readout causal | Removing the trained subspace collapses the CAS readout while random removals do not. | Stage 9 full 40-way ablation to exact chance |
| 5 | Diagnostic trace | Layer/readout traces flag stable, drifting, weak, or conflicted evidence. | Stage 13 problem-like traces |
| 6 | Weight geometry | CAS subspace aligns with static weight geometry above random. | Stage 14.1 output logit-lens p `0.0099` |
| 7 | Harness conditioning | Readable CAS realization shifts likelihood under controls. | Stage 16 Qwen CPL2 pass |
| 8 | Visible generation | Human/classifier-visible generated text shift. | Not yet closed |

## Cross-Architecture Claim Boundary

The strongest current external claim is:

> CAS Harness replicated a bounded likelihood-conditioning mechanism across
> Pythia, OLMo, and Qwen. The mechanism is read from hidden activations,
> realize as readable CAS context, then condition the host model through
> ordinary language attention.

Do not upgrade that to:

> CAS controls the model's thoughts.

Do not upgrade that to:

> CAS can prove the exact neurons that caused an answer.

Do not upgrade that to:

> CAS can force any generated output.

## Hidden-Content Detection Boundary

The current hidden-content comparison is:

- eta-1: internal CAS readout from hidden activations
- eta-2: emitted-text CAS readout from the answer

Single-probe eta-1 can detect a gap, but only along one axis at one selected
depth. Multi-harness composition upgrades eta-1 into a structured tensor across
CAS axes and layer bands. That makes hiding or suppression easier to localize:
the audit can compare Noetic, Foundation, Domain, Register, operator, formula,
and blind-spot traces instead of one label at a time.

Supported now:

> The component evidence for this architecture is present: multiple CAS axes
> are readable, some are readout-causal, multi-layer traces work, and the
> eta-to-epsilon bridge replicates across model families.

Not yet supported:

> A completed multi-harness hiding benchmark showing intentional concealment or
> systematic internal/external divergence across all axes.

## Developer Integration Boundary

The product surface should expose these fields:

- `trace_id`
- `model_name`
- `model_revision`
- `fixture_sha256`
- `activation_sha256`
- `selected_layer`
- `selected_readout`
- `probe_accuracy`
- `probe_confidence`
- `lacunarity`
- `blindspot_flags`
- `claim_level`
- `raw_control_result`
- `readable_prefix_result`
- `caveats`

The product surface should avoid these fields or labels:

- `exact_neurons_that_caused_answer`
- `weights_fired`
- `model_compiled_cas_internally`
- `guaranteed_truth`
- `full_black_box_solved`

## Next Stage Recommendation

Stage 18 should test visible text quality with a locked judge:

1. Generate continuations under `none`, `probe_readable`, and `partner_readable`.
2. Blind the condition labels.
3. Score target Foundation/Drive alignment with a classifier and/or human judge.
4. Require a pre-registered pass gate before public visible-generation claims.

No more GPU scale-up is needed before this evidence boundary is audited.
