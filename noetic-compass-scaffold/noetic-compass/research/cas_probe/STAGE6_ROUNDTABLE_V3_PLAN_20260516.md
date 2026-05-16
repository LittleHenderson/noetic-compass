# Stage 6 Roundtable Plan - V3 Role-Bound Noetic Probe

**Status:** Research plan, not yet implemented.  
**Date:** 2026-05-16  
**Branch:** `experiment/cas-probe-pythia`  
**Purpose:** Convert the Stage 5.4 result into the strongest next experiment for testing whether CAS noetic structure is present in open-model activations beyond plain text shortcuts.

## Current Evidence

Stage 5.4 repaired the targeted `^6` Male failure:

- Male diagnostic: `7/30 -> 29/30`
- Nested-composition Male: `0/10 -> 10/10`
- No-alias Male: `0/10 -> 9/10`

But global transfer is still mixed:

- Stage 5.2 paraphrase fixture: `29/60 -> 38/60`
- TF-IDF on the same fixture: `35/60`
- Paired v2 probe vs TF-IDF: `p=0.607`

The correct interpretation is:

> Targeted semantic repair works, but current evidence does not yet prove a reliable activation advantage over strong text-only baselines.

## Roundtable Verdict

The strongest next step is **not** another append-only alias repair.

The strongest next step is:

> Build a role-bound counterfactual noetic fixture where the same sentence contains both sides of a noetic contrast, and only a neutral focus marker selects the target label.

This attacks the main weakness directly. If the same words support both labels, a bag-of-words classifier should lose its advantage. A useful probe must track the role the text asks it to inspect.

## Core Experiment

Name: `stage6_role_bound_noetic_counterfactual`

Example structure:

```text
A brings B to mind. Focus: A -> ^8 Above/Cause
A brings B to mind. Focus: B -> ^9 Below/Effect
```

```text
A draws the mind toward it; B pushes the mind away. Focus: A -> ^2 Positive
A draws the mind toward it; B pushes the mind away. Focus: B -> ^3 Negative
```

```text
Mind M is shaped by ideas X/Y/Z; idea I is built from parts X/Y/Z. Focus: M -> ^5 Female
Mind M is shaped by ideas X/Y/Z; idea I is built from parts X/Y/Z. Focus: I -> ^6 Male
```

Matched `^4/^7` examples must place impression strength and repeated exposure in the same row, with the focus selecting which aspect is labeled.

## Ontology Rules

Use these as the v3 label contract.

| Pair | Distinction |
|---|---|
| `^5` vs `^6` | Mind/person/agent composed by received ideas vs an idea/claim/plan composed of inner ideas |
| `^8` vs `^9` | Source cue that brings another idea forward vs resulting thought/content that appears |
| `^2` vs `^3` | Movement toward, affinity, inclusion vs movement away, aversion, exclusion |
| `^4` vs `^7` | Salience or impression strength vs repeated cadence, interval, or exposure pattern |
| `^0` vs `^1` | Object/content under consideration vs active awareness/processing of content |

Each row needs a `mapping_note` that states the focused role. The model input must not include the note.

## Dataset Shape

Recommended dataset: `v3_hard_contrast_noetic`

- Total: `3,000` rows
- Train: `1,200` rows, `120` per noetic
- Val: `400` rows, `40` per noetic
- Locked test: `1,400` rows, `140` per noetic
- Structure: `60` contrast bundles x `10` noetics x `4` core paraphrases = `2,400` rows
- Additional locked-test challenge: `600` rows using held-out paraphrase families

Split by `contrast_bundle_id`, `lexical_pack_id`, and `template_id`. Never split by individual row.

No scenario, noun pack, template skeleton, or paraphrase family may cross from train into locked test.

## Record Schema

```json
{
  "sample_id": "v3_train_bundle014_debugging_02",
  "dataset_version": "v3_hard_contrast_noetic",
  "split": "train",
  "contrast_bundle_id": "bundle014_debugging_warning",
  "lexical_pack_id": "debugging_warning_assertion_patch",
  "template_id": "role_inverse_minimal_v01",
  "paraphrase_family": "role_inverse_minimal",
  "surface_style": "system_process",
  "english": "...",
  "noetic_label": 8,
  "noetic_name": "Above/Cause",
  "cas_expression": "^8",
  "focus_span": "A",
  "contrast_partner_label": 9,
  "hard_contrast_labels": [8, 9],
  "mapping_note": "A is the source cue, not the resulting thought.",
  "anti_leak_flags": {
    "contains_cas_notation": false,
    "contains_label_name": false,
    "counterbalanced_keyword_pack": true
  },
  "source_strategy": "hand_authored_then_model_paraphrased",
  "review_status": "double_annotated_agree",
  "confidence": "high"
}
```

Only `english` is used as model input.

## Paraphrase Families

Core families:

- `role_inverse_minimal`: same nouns, same sentence, different focus role.
- `no_alias_plain`: ontology-correct wording without known label aliases.
- `concrete_human`: human-scale examples using repeated entities.
- `system_process`: technical/process examples to avoid human-story overfit.

Locked-test-only families:

- `compressed_minimal`: short direct rows.
- `long_embedded_clause`: label-bearing relation is not first.
- `counter_alias_hard_negative`: label-associated words appear under the wrong label.

Example hard negative:

```text
The reviewer favors rejecting the proposal. Focus: favoring the rejection.
```

This is `^2` Positive because the attitude is toward the rejection, even though the object is rejection.

## Anti-Leak Rules

Hard fail any row with:

- CAS notation, `^0`-style strings, `CAS`, `noetic`, `operator`, or label IDs.
- Explicit label names in model input.
- Exact normalized text overlap with v1/v2 training or Stage 5 fixtures.
- Near duplicate to train/dev: char 5-gram Jaccard `>= 0.85` or TF-IDF cosine `>= 0.90`.
- Template leakage across splits.
- Metadata-only baseline materially above chance.

Quarantine/manual review:

- char 5-gram Jaccard `0.75-0.85`
- TF-IDF cosine `0.80-0.90`

High-signal unigrams/bigrams must either appear in at least three labels or be removed/counterbalanced.

## Activation Readouts

Train probes on three readouts:

1. Primary: residual stream at the neutral focus token.
2. Secondary: final token after the focus clause.
3. Legacy: current mean-over-sequence pooling.

For Pythia-160M:

- Primary causal layer: layer `4`
- Historical comparison layer: layer `3`
- Shortcut check: layer `0` / embedding

For a second open model, scan all layers but select layer on validation only.

## Probe Setup

Train:

- 10-way noetic probe.
- Pairwise contrast probes for `^0/^1`, `^2/^3`, `^4/^7`, `^5/^6`, `^8/^9`.
- Surface-residualized probe: regress activations on TF-IDF/char-ngram features on train, subtract that predicted surface component, then train the same probe.

The residualized probe is a shortcut test. It asks whether the activation signal survives after shallow text form is accounted for.

## Baselines

Use the best validation-selected text-only model among:

- Majority class
- Stratified dummy over 10,000 seeds
- CountVectorizer + LogisticRegression
- TF-IDF + LogisticRegression
- Char TF-IDF + LogisticRegression
- Alias-rule baseline
- Metadata-only baseline

Also include:

- Shuffled-label control through the full training pipeline.
- Layer 0 embedding shortcut check.

## Statistical Gates

A v3 "reliably above text" claim requires all of:

- Probe accuracy minus best text baseline `>= 0.05` on locked test.
- Exact two-sided McNemar/binomial paired test: `p < 0.05`.
- Cluster bootstrap 95 percent CI lower bound for accuracy lift `> 0`.
- Macro-F1 lift over best text `>= 0.03`, bootstrap lower bound `> 0`.
- No noetic class below `0.50`; at least 8/10 classes at or above `0.60`.
- Shuffled-label control at chance-ish: `<= 0.15` accuracy for 10-way noetic.

If accuracy clears but McNemar does not, verdict remains:

> Labels recoverable mostly from text.

## Causal Tests

Only run causal claims after the locked probe test passes.

Use forced-choice semantic logit tests instead of free continuation token match.

Interventions:

1. True-direction ablation: removing the true pairwise direction should reduce the correct-vs-contrast logit margin more than random/off-class controls.
2. Signed steering: adding/subtracting the pair direction should monotonically shift the semantic margin toward the corresponding noetic.
3. Counterfactual activation patching: patch the focus-token residual from the `Focus: A` twin into the `Focus: B` twin and measure whether probe prediction and semantic logit margin shift.

Controls:

- 100 random orthogonal directions matched by layer, norm, rank, and target position.
- Shuffled-label probes.
- Template/style probe ablations.
- Off-class noetic ablations.
- Same ablation at layer 0 and a late non-selected layer.
- Non-focus token position controls.

Pass only if true-direction effects exceed random-null p95 with permutation `p < 0.01`, and steering/patching changes are semantically directional.

## Claim Language

Allowed after dataset-only pass:

> The Pythia probe shows statistically reliable lift over strong text-only baselines on this locked v3 noetic fixture.

Allowed after causal pass:

> Pythia contains a role-bound, causally usable internal signal aligned with CAS noetic distinctions under counterfactual controls.

Not allowed yet:

- Pythia encodes CAS.
- We can inspect the model's reasoning.
- Glass House is confirmed.
- The probe proves hidden thoughts.

## Immediate Build Order

1. Write v3 schema + validator.
2. Author 10 pilot contrast bundles by hand.
3. Generate the 10-label semantic card for each bundle.
4. Produce paraphrases from semantic cards, not CAS notation.
5. Run forbidden-token, duplicate, near-duplicate, MI, length-parity, and split-isolation checks.
6. Run a small pilot with v2 probe and text baselines to validate the test mechanics.
7. If clean, scale to 60 bundles and freeze locked-test SHA before v3 probe training.

## Bottom Line

V2 proved targeted repair is possible. V3 must prove whether that repair generalizes beyond wording. The cleanest way to do that is not more aliases. It is same-words, different-focus, role-bound counterfactual testing.
