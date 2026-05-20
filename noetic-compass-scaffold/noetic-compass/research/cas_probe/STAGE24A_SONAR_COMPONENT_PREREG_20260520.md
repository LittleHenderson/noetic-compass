# Stage 24A CAS Sonar + Component Attribution Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Scope

Stage 24A is a bounded research escalation for CAS Harness. It tests
token-level CAS signatures first, then a component-level attribution pilot.
It does not authorize SAE training, exact-neuron claims, or product-language
changes before results exist.

## Required Inputs

| Input | Value |
|---|---|
| `model` | `EleutherAI/pythia-160m` |
| `fixture` | `stage7_foundation_pilot_20260517.jsonl` |
| `activations` | `stage7_foundation_pilot_activations_20260517.npz` |
| `probe_report` | `stage7_foundation_pilot_probe_report_20260517.json` |
| `ablation_report` | `stage7_foundation_layer6_ablation_report_20260517.json` |
| `locked_readout` | `{'name': 'focus_token', 'key': 'X_focus', 'layer': 6}` |
| `foundation_classes` | `28` |
| `random_controls_required` | `True` |

## Tracks

### `sonar_token_signatures`

- Subject: `cas_harness_pythia160m_foundation_subspace`
- Status: `next_to_build`
- Primary artifact: `STAGE24A_SONAR_TOKEN_SIGNATURES_20260520`
- Question: Do Stage 7 Foundation probe directions induce class-specific vocabulary signatures through the model's unembedding/token space?

Method:
- Recover the locked Stage 7 Foundation probe raw-space class directions.
- Project each Foundation class direction through Pythia-160M output embeddings.
- Report top positive and negative tokens per Foundation, Drive, and Register.
- Compare within-drive/same-register similarity against hard-partner and random controls.
- Check involution/contrast pairs for token-signature opposition where applicable.

PASS gate:
- Top-token signatures are stable under bootstrap or split-resample controls.
- Same-Drive or same-Register classes are more similar than hard-partner controls.
- Random same-rank directions do not reproduce the observed class-specific structure.

NULL gate:
- Class signatures are no more stable than random directions.
- Within-axis similarity does not beat hard-partner or random controls.
- Top tokens are dominated by tokenizer artifacts or corpus leakage terms.

Claim if PASS: CAS Harness maps bounded CAS readout directions to model-native token signatures.

Claim if NULL: Stage 7 readout remains valid, but token-level vocabulary signatures are not established.

Forbidden claims:
- Do not claim the model would necessarily generate the top sonar tokens.
- Do not claim token signatures are neuron-level causal circuits.
- Do not claim universal sonar transfer before cross-model runs.

### `component_attribution_pilot`

- Subject: `pythia160m_attention_heads_and_mlp_intermediates`
- Status: `design_locked_gpu_optional`
- Primary artifact: `STAGE24A_COMPONENT_ATTRIBUTION_PILOT_20260520`
- Question: Can CAS Harness localize Foundation readout signal from the residual subspace down to specific transformer components?

Method:
- Hook attention-head outputs and MLP intermediate activations on the locked Stage 7 fixture.
- Rank components by projection/alignment to the Stage 7 Foundation subspace.
- Ablate top-ranked components and matched random controls.
- Measure Foundation probe accuracy drop, per-class disruption, and specificity.
- Cross-reference high-ranking components with sonar token signatures when available.

PASS gate:
- Top-ranked component ablation degrades Foundation readout more than matched random controls.
- Disruption is class-specific rather than a global activation-damage artifact.
- At least one component family clears a pre-registered effect floor.

NULL gate:
- Top-ranked components do not beat matched random controls.
- Ablation damage is nonspecific or equivalent across classes.
- Signal appears too distributed for component-level localization without SAE methods.

Claim if PASS: CAS Harness can localize bounded CAS readout signal to transformer components with causal evidence.

Claim if NULL: Component-level localization is not established; SAE/path-patching becomes the next research route.

Forbidden claims:
- Do not claim exact monosemantic neurons from component-level evidence.
- Do not claim full generation control from readout-component disruption.
- Do not claim SAE-level feature localization unless SAEs are trained and tested.

## Claim Boundary

- Licensed if pass: Stage 24A can support token-level CAS sonar and bounded component-level causal localization claims, depending on which track passes.
- Not yet claimed: Exact neuron-level or SAE-disentangled feature causality remains untested until a separate SAE/path-patching stage runs.
- Product relevance: Stage 24A strengthens CAS Harness evidence depth; it is not a blocker for Evidence Packet or Verification Stack productization.

## SAE Follow-Up

- Status: `deferred_not_launch_blocker`
- Trigger: Run if component attribution is distributed/polysemantic or if exact feature-level causal localization becomes the explicit research goal.
- Authorized by Stage 24A: `False`

## Validation

- valid
