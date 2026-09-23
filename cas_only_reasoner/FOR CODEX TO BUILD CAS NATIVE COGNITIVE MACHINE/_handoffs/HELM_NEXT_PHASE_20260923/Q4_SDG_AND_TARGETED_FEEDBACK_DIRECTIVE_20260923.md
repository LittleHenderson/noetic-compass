# Q4: CAS SDG lessons and targeted error feedback

**For:** Little Henderson and the continuing Claude session  
**Date:** 2026-09-23  
**Status:** Development directive proposed in response to the owner's question: “Or raise the penalty? Could CAS SDG help with this GRU Q4?”

No training, inference, GPU job, repository change or cloud launch was performed while preparing this directive. The inspected historical source is `d4c3fc7643201a83693ea9073c14ab42ecc5a570` in `LittleHenderson/noetic-compass`. Reconcile newer work before implementing this proposal.

## 1. Decision

Investigate better CAS-specific lessons and more informative error feedback before assuming Q4 needs a larger network.

Keep the width-64 GRU as the first experimental model. First compare existing lessons with a deliberately constructed CAS SDG curriculum, using the same loss function. Then, if the error trace supports it, compare that curriculum with and without modest extra weight on structural decisions. Change the architecture only in a separate comparison if these steps and the information-use probes justify it.

This order changes the priority of the earlier architecture-oriented recovery proposal. Input attention remains a candidate, not a prerequisite and not a promised cure.

Q4 is a separate reconstruction model. Its improvements do not automatically upgrade Helm 2.0, certify Helm 3.0, or establish general CAS reasoning.

## 2. Grounded starting point

The actual original run used Q3 v0.7 family G, a pool of 2,048 examples and 128 single-example updates. The worker shuffled the row indices once and selected one row at each update. It therefore presented 128 row positions once, not 128 full passes through the dataset. Its sixteen development predictions were all the same wrong two-leaf PLUS tree.

Existing review diagnostics report that the same code memorized eight training rows after repeated practice, while a different 2,000-update job over 256 rows still produced no exact reconstruction. Reuse these records. They do not isolate a single cause or prove that more practice cannot work.

The source shows:

- Training already penalizes incorrect next-token predictions with cross-entropy.
- AdamW performs the weight updates, and gradient clipping limits their input magnitude.
- The encoder gives the decoder one final hidden vector. The decoder does not consult source-position representations while producing the tree.
- The output grammar supports StateLiteral and ordered PLUS/TIMES BinaryExpr trees. It is not a general CAS, English, PCBA or refusal decoder.
- EOS is permitted only after a complete generated tree. A short wrong tree can result from selecting STATE where BINARY was needed. Do not assume early EOS is the defect.
- The existing Q3 adapter already uses SDG expression strings for family R. Family G generates nested trees separately because the older SDG pool was reported to have narrow structural coverage. The original Q4 worker selects G, not the full SDG corpus.

These are specific implementation observations. The cause of the failed reconstruction remains open.

## 3. First return: identify the error to teach

Reuse the original checkpoint and existing probes where applicable. Under the current execution authorization, inspect a small public diagnostic panel and record:

1. The exact input, true target, generated output and first wrong decision.
2. Whether the first error is a leaf-versus-branch choice, PLUS-versus-TIMES, Noetic, Domain, Drive, Register, missing subtree, or extra subtree.
3. Next-token accuracy with correct previous tokens, separately from complete generation using the model's own previous tokens.
4. Whether changing one input field changes its encoded representation and the probability assigned to the correct output field.
5. Whether replacing the input summary with a different example's summary changes those probabilities. Compare with same-example replacement, hold the tested prefix fixed, and prefer substitutions with similar length and shape.
6. Actual encoder and decoder gradients and weight changes, unless the existing retained evidence already answers the relevant question.

A similar final vector is not proof that information is absent. Identical chosen outputs are not proof that the output probabilities are identical. If the model behaves differently with correct previous tokens, investigate that training/generation difference rather than blaming capacity alone.

Do not repeat unrelated compiler, PCBA or Helm audits as prerequisites.

## 4. Build a Q4-specific SDG adapter, not a corpus dump

Reuse the expression generation, compiler reference and strict file separation already present in the project. Inspect current versions first. Proposed new adapter files may be named `q4_sdg_curriculum.py` and `test_q4_sdg_curriculum.py`; these names are proposals, not claims that such files exist.

Keep the original Q3 v0.7 files unchanged. New lesson sets need new identities, counts, fingerprints and declared splits. Preserve Noetics as `^0` through `^9` and the current agreed axis namespaces. Do not invent Noetic nicknames, domain/register conversions, or book meanings.

The adapter must:

- Produce visible expression text in the current supported grammar.
- Produce the corresponding exact ordered reference tree using the pinned compiler and verified output codec.
- Check the generated tree against the compiler tree, rather than trusting generation alone.
- Keep expected trees, answer tokens, changed-field labels and error explanations out of the learner's prediction-time input.
- Retain those extra teaching labels in a supervised target sidecar for loss calculation and diagnosis.
- Reject unsupported output nodes explicitly. Do not silently remove PCBA syntax, nested sets, governing operators or metadata to make them fit.
- Keep malformed-expression lessons in a separate future refusal task until a refusal output contract exists.

For this experiment, use expression text to tree reconstruction. Do not silently switch to English-to-CAS translation. The historical SDG mainly creates CAS first and then associated language. Compiler acceptance of an expression does not establish that an English interpretation is semantically correct.

Providing reference targets during supervised training is legitimate. Providing the completed reference tree to the prediction path would bypass the learning question.

## 5. The proposed lessons

### A. Preserve one state accurately

Cover Noetics, Domains, Drives and Registers, including supported optional fields. Include pairs differing in exactly one field, for example:

```text
^8^C_{F2}|A
^8^C_{F2}|E
```

The target difference is the Register, not the whole expression. Balance coverage deliberately and log it. Do not force every possible combination into a tiny initial sample and then present each only once.

### B. Preserve two ordered parts and their operator

Use both PLUS and TIMES, unequal leaves, and exchanged left/right positions. A reconstruction target retains left and right even when an operation's evaluated value would not change after an exchange.

The objective is to read the supplied tree, not replace it with an algebraically equivalent one.

### C. Preserve grouping

Construct pairs containing the same states and same operators but different nesting:

```text
(^1^C + (^2^C + ^3^C))
((^1^C + ^2^C) + ^3^C)
```

These have the same symbol inventory but different ordered tree structures. Derive and check both targets. Such pairs test a distinction that an order-blind symbol counter cannot recover.

Change grouping, operator identity and leaf values in separate controlled families before combining all three. Include both shallow and deeper examples instead of training only easy examples until they are memorized.

### D. Correct recurring mistake types

Use errors from training or a designated feedback-development panel to select new public examples of the same mistake type. For example, repeated loss of the right nested branch should trigger new right-nested examples with different leaf values and some left-nested controls.

Retain earlier skills in the mixture. Avoid an endless loop of presenting the same failed sixteen questions. Keep protected final questions and their answers out of this feedback process.

Do not enforce a rule that different inputs must always produce different answers across CAS generally. Use this distinction only where the exact reconstruction contract establishes different targets.

### Curriculum caution

An easy-to-hard schedule is a testable design, not a guaranteed benefit. Declare the mixture or promotion rule before observing prospective results. Preserve some shorter cases while increasing depth, and include controlled exposure to harder cases rather than assuming an easy-only phase will transfer.

The relevant outside precedent, *Learning to Execute* by Zaremba and Sutskever, used a different recurrent model and task. It found curriculum design mattered and that a naive curriculum was insufficient. It motivates testing this proposal; it does not predict Q4's result.

## 6. What “raise the penalty” should mean

### Do not start with a global multiplier

Multiplying the entire loss by a constant adds no information about which decision is wrong. For ordinary gradient descent it rescales the gradient. AdamW's normalization and existing clipping mean it is not generally a proportionately stronger update. Finite precision, epsilon, existing optimizer state and clipping can change the details.

Similarly, appending a plain numerical surcharge after comparing a generated tree with the reference does not create a useful gradient through the discrete generation step. A sequence-level training method would need an explicit estimator; do not mistake a printed score for a learning signal.

Do not disable clipping to make the penalty stronger. Do not globally suppress PLUS or the known wrong tree; both can be legitimate targets for other inputs.

### First targeted candidate: structural-position weighting

If the first-error report shows leaf-versus-branch decisions are a major problem, compare ordinary cross-entropy with an explicit weighted version:

```text
Per-token weight = 2 at STATE/BINARY decision positions.
Per-token weight = 1 at all other target positions.
Loss = sum(weight * token_cross_entropy) / sum(weight).
```

The factor 2 is a proposed modest experimental setting, not a proven optimum or a canonical CAS number. Freeze it before the comparison. Weight the decision position whether its correct answer is STATE or BINARY. This discourages both lost branches and invented branches; it does not reward trees merely for being larger.

Keep the existing full-vocabulary training loss behavior otherwise unchanged for this first comparison. Changing training masks at the same time would be another intervention.

Use `cross_entropy(..., reduction="none")` to obtain token losses before applying explicit position weights. Check equal weights reproduce the original reduction. Verify the weighted loss changes relevant gradients, not just the displayed number. Normalize intentionally and retain ordinary unweighted loss for comparison between jobs.

If metadata, not structure, is the measured weakness, choose a separately specified field-weight experiment. Do not turn up every field at once. Adding whole-tree exact failure as a diagnostic is useful, but it is not a replacement for a trainable per-decision objective.

A small verified-wrong-example or ranking objective can be considered later. It must be conditioned on the actual input and must not penalize an answer that is correct for that input. It is not required for the first experiment.

## 7. Comparison sequence

Prepare these named conditions, but initially execute only the applicable matched pair:

| Condition | Lessons | Feedback | Purpose |
| --- | --- | --- | --- |
| A | Existing family-G sampling | Original cross-entropy | Contemporary control with a meaningful declared practice budget. |
| B | New Q4-specific SDG lesson package | Original cross-entropy | Tests the lesson-package change with the same network. |
| C | Exactly B's lessons and order | Targeted position weights | Tests whether the selected penalty change adds benefit. |

Run A versus B first. Run B versus C only when the diagnostic evidence and resource scope justify that next comparison. To isolate curriculum order from the examples themselves later, compare the same generated corpus in shuffled and curriculum order.

Use matching initial tensors and recorded seeds where possible, the same optimizer configuration, the same limits and example-presentation count. Record source-byte and target-token counts, lengths, actual runtime and resource use because equal update counts are not equal compute. Account for any checkpoint restoration of optimizer and random state. Do not compare a fully trained new job only with the historical 128-update smoke and attribute the entire gain to SDG.

Do not claim a universal benefit from one run. Confirm a promising result with predefined additional starts and fresh protected examples before making a stronger claim.

## 8. What counts as improvement

Report exact full-tree reconstruction first. Also report structural accuracy, ordered leaf correctness, per-field errors, first wrong decision, generated length/depth, output diversity, and correct-prefix versus free-generation behavior.

Separate four panels:

- The actual teaching examples.
- New content using familiar structural patterns.
- New ordered tree structures at matched sizes.
- Longer or deeper expressions than those taught.

Preserve both bare-shape and operator-labelled-shape definitions. Keep all declared holdout shape families out of generated training. Assign near-duplicate lesson groups before splitting, or explicitly disclose paired exposure as a separate test design.

The repeatedly examined old sixteen are now a development diagnostic. Do not make them the sole evidence for reusable learning. New evaluation thresholds and model-selection rules must be fixed before the prospective results, without retroactively changing the original smoke's status.

More varied wrong trees, a lower loss, or a higher syntax-validity rate alone is not success. A perfect deterministic parser remains a useful reference and product baseline; it is not the learned model's output.

## 9. When to change the architecture

If adequate declared practice and the targeted lesson/feedback comparisons still fail to fit small teaching sets or use input distinctions, act on the failure trace.

A smaller intervention is to supply the same final summary at every decoding step. A larger one is to retain the encoder's per-position learned representations and allow the decoder to consult them. The latter changes the one-vector compression contract and must have a separate model identity.

Do not feed a compiler-produced completed tree through that new memory path and claim neural reconstruction. Do not replace all learned behavior with a parser and present its perfect score as Q4 improvement.

Neither a width increase nor attention is proved necessary by 0/16 alone.

## 10. Roles, execution and records

Claude may continue the selected Q4 implementation while Codex is unavailable, after recording temporary ownership and checking current branch activity. Keep a separate review context and final-answer custody wherever available. Do not duplicate an already-owned experiment or assume old task ownership is still current.

Use a separate worktree. Preserve the working compiler, CAS-Ohm, PCBA checker, atlas, Helm weights and original Q3/Q4 receipts. Pin new source and data before execution. Save failures as well as successes. Reload a successful checkpoint in a fresh process under the declared numerical policy.

The latest supplied project handoff directs new sustained checks to AWS because local memory is exhausted. Use the current applicable standing research authorization with an explicit instance/device, one runner, job cap, wall-time, update budget, monetary limit and cleanup plan. Do not infer a price or unlimited spending from this directive. Ask only for genuinely missing scope, not permissions already granted.

CAS-RPA may display the real input, target, prediction, first error, new lesson family and later result. Such a display is inspection, not learned control. CAS-Ohm is not required for this repair; do not relabel the optimizer's error value as measured CAS attention, Drive or constraint without a separately established measurement contract.

## Sources used

Project code, all at `d4c3fc7643201a83693ea9073c14ab42ecc5a570`, under `research/helm_cas_expression_lab/` in the CNCM homebase:

- `q3_behaviour_records.py`: existing R/SDG and G/grammar distinction, strict splits and supervised target boundaries. Git blob `ef6253e62f5ef8c399978cfa4478d55c077ab40e`.
- `q4_smoke_job.py`: G-only job, actual single-example loop, cross-entropy, AdamW and clipping. Git blob `2e0c787775442d34fef18f6741e3175df7d4548d`.
- `learner_q4_neural.py`: final-hidden-state handoff and separate supervised/free-generation paths. Git blob `ad9d1a03618c9ffceac676fde247b52b2ba0f4e4`.
- `learner_q4_decoder.py`: grammar, fields, ordered reconstruction and EOS restriction. Git blob `f1fa10e3c0598fb20f8826498001cf8d959edfde`.

Project reports: `records/q4_authorized_20260922/README.md`; `records/helm_why_review_20260922/README.md`; 2026-09-23 implementation/coordination handoffs; `records/helm_stage2_checker_20260923/` for the later AWS instruction, not for Q4 model acceptance.

Outside primary references: PyTorch official CrossEntropyLoss, AdamW and gradient-clipping documentation/source; Zaremba and Sutskever, *Learning to Execute*, arXiv:1410.4615. These explain general mechanisms and motivate proposed tests. They are not evidence that a proposed Q4 fix has succeeded.
