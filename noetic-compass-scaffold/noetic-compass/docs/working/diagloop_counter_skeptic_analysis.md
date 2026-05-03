# DiagLoop Counter-Skeptic Analysis

**Role:** Counter-Skeptic (hostile reviewer)  
**Target hypothesis:** K9_DiagLoop full retrain regression (epoch 0=63.2%, epoch 1=42.9%, epoch 2=28.1%) is caused by a train/eval mode mismatch — training receives `graph_batch`, per-epoch eval calls `model(batch)` without it.  
**Directive:** Argue hardest against this diagnosis. Make the team's case stronger by ruling out nothing cheaply.

---

## STOP — Threshold finding before any section

Before any analysis of the five angles, the investigation must reckon with one fact: **three of the five files this team was told to read do not exist in this repository.**

```
docs/working/diagram_loop_lever_proposal.md  → NOT FOUND
cas-native/model/graph_encoder.py            → NOT FOUND
cas-native/model/graph_text_fusion.py        → NOT FOUND
cas-native/training/evaluate_diagram_loop_invariance.py → NOT FOUND
```

Checked via `find /home/user -name "graph_encoder*" -o -name "graph_text_fusion*" -o -name "evaluate_diagram*" 2>/dev/null` and `find /home/user -name "diagram_loop*" 2>/dev/null`. Both returned empty.

The file that **does** exist — `cas-native/training/train_structured_prediction.py` — contains the model classes the team is calling "the baseline." The current `StructuredTokenStructuredPredictor.forward` (line 122–128 of `structured_token_embedding.py`) accepts only `batch: StructuredTokenBatch`. There is no `graph_batch` parameter in the published code. The training loop (line 925) and the eval loop (line 443) both call `model(batch)` identically.

This means: **the eval-mode-mismatch hypothesis is a claim about code that is not in the repository.** PR #6 either introduced the graph path in files that have not been committed to the scaffold, or the PR has been reverted. The team cannot verify the mechanism, the oracle, the fusion architecture, or the eval script from the sources actually available.

Everything in the five sections below takes the trajectory data as given (63.2% → 42.9% → 28.1%; smoke peak 48.4% → 30.7%; smoke graph-path 65.5% vs text-only 30.7%) and argues from first principles and the code that does exist. The threshold finding stands independently: before any fix lands, the team must locate and read the actual PR #6 diff.

---

## C1. The hypothesis is too convenient

### The core tension

The +13.7 pp Noetic gain is the result the team most wants to preserve. The eval-mode-mismatch hypothesis is the most architecturally benign explanation for the regression: it requires no structural changes to the diagram-loop design, just a one-line fix in the eval harness. The team converges on this hypothesis the way a team always converges on the hypothesis that lets them keep the architecture intact.

Here is what motivated reasoning looks like from the outside: the team finds a mechanism that (a) explains the observed regression, (b) is fixable without redesign, and (c) preserves the exciting upstream finding. All three conditions being met simultaneously should raise skepticism, not confidence.

### What the eval-mode-mismatch hypothesis cannot explain about epoch 0

The trajectory begins at **63.2% at epoch 0**. Epoch 0 is the first evaluation pass — immediately after random weight initialization, before any gradient updates on the full training corpus.

Compare with the actual structured-token 20-epoch GPU run (`structured-token-20epoch-gpu-20260502-001907`, committed to this repo): epoch 0 accuracy is **18.3%** (`183/1000`). This is the expected behavior from random initialization on a multi-class structured prediction problem. The model's initial predictions are near-chance.

K9_DiagLoop epoch 0 at 63.2% is nearly 45 pp above random initialization. This is inconsistent with the K9_DiagLoop model being trained from scratch. **63.2% at epoch 0 implies the model was initialized from a pre-trained text-only checkpoint.** If that checkpoint is the K9 baseline (or the structured-token 85.3% run), then the "regression" may not be a regression from random init but a degradation of a fine-tuned model under a new training regime.

This is the pattern the topological-memorization hypothesis explains better. If the K9_DiagLoop run starts from a strong text-only checkpoint (e.g., 85.3% accuracy) and then fine-tunes with graph-augmented supervision, the model's early-epoch performance (63.2%) represents partial degradation of the pre-trained representations as the graph-conditioning signal starts to override the learned text associations. By epoch 1 (42.9%) and epoch 2 (28.1%) the pre-trained text knowledge is being systematically overwritten by graph-topology-dependent representations that don't generalize at eval time.

**The eval-mode-mismatch hypothesis predicts monotonic degradation from epoch 0 onward**, starting from the checkpoint's initial performance level. The topological-memorization hypothesis predicts the same shape but also predicts that the eval-mode-mismatch fix (passing null/zeros as graph_batch during eval) would only partially recover performance — because the text representations themselves have been corrupted by fine-tuning against graph-dependent targets.

### The asymmetry the team should explain

If eval-mode-mismatch is the sole cause, fixing it should restore the full baseline accuracy. If the fix restores only partial accuracy (e.g., recovers to 70-75% rather than the original 85%+), that is evidence of dual causation and the team should not conclude the architecture is sound.

---

## C2. The +34.8 pp lift could be measurement artifact

### The oracle problem

The smoke run reports text-only eval at **30.7%** and graph-path eval at **65.5%**, a 34.8 pp lift. The team treats 65.5% as the "true performance" of the diagram-loop architecture. This requires that the graph provided at eval time is a realistic production-grade prior — one the model would actually have access to at inference time.

The file the team needed to verify this — `evaluate_diagram_loop_invariance.py` — **does not exist in this repository.** The exact mechanism by which `--with-graph-path` constructs `prior_diagram` cannot be audited.

The oracle risk is concrete. The eval records in `level3_recoverable_eval_1000.jsonl` contain a `cas_expression` field. The compiler (`api/notation/compiler.py`, the `diagram()` method at line 1274, and `build_diagram()` at line 5543) can compile any `cas_expression` into a graph with nodes, edges, and layout hints. If `evaluate_diagram_loop_invariance.py` calls `artifact.diagram()` on the eval record's ground-truth `cas_expression` and passes the result as `prior_diagram`, then:

- The graph is derived from the label.
- The model is given the answer as a structural prior.
- The eval is measuring how well the model can decode its own input when given the answer, not how well it generalizes.

The 34.8 pp lift would then be the model exploiting an oracle, not genuine generalization.

### Why 65.5% makes the oracle hypothesis more plausible, not less

If the graph prior were genuinely helpful but not oracle-quality (e.g., derived from heuristics or from prior-turn CAS expressions), we would expect the graph-path eval to be at or above the text-only 20-epoch baseline of 85.3%. Instead it scores 65.5% — a full 20 pp *below* the text-only best. An architecture that degrades best-case performance by 20 pp while claiming a 34.8 pp lift over its own broken eval is incoherent unless:

1. The "text-only 30.7%" reflects a genuinely broken eval (consistent with eval-mode-mismatch), and
2. The "65.5% with graph" is a partially-oracle measurement that inflates the architecture's real contribution.

Both can be true simultaneously, and neither requires the +13.7 pp Noetic finding to survive a clean retrain. The team should not treat any measurement from the smoke's `--with-graph-path` path as valid until `evaluate_diagram_loop_invariance.py` is recovered, read, and audited for oracle leakage.

### The Noetic-specific measurement

The +13.7 pp Noetic claim is doubly fragile: it depends on the graph-path eval being valid (C2 undermines this) AND on the graph path not being oracle-derived. The Noetic head is the axis most likely to be recoverable from graph structure because CAS expression graphs have Noetic operators as node labels. A graph oracle would give the model near-perfect Noetic accuracy without any genuine learning.

---

## C3. Cross-attention can collapse without graph_batch even when graph_encoder is None

### The layer norm contamination problem

The graph_text_fusion.py file does not exist in this repository, so the fusion architecture cannot be read directly. However, the pattern of cross-attention layer design in models with optional conditioning inputs is well-characterized, and the general principle applies regardless of the specific implementation.

When a cross-attention module has its own Layer Normalization layers (as is standard in Transformer cross-attention blocks), those LayerNorm parameters learn the input statistics of the activations they normalize. During training, the cross-attention receives `(query=text_hidden, key=graph_nodes, value=graph_node_values)`. The query projection and the query-side LayerNorm learn the statistical distribution of `text_hidden` conditioned on the presence of `graph_nodes`.

At eval time, when `graph_batch=None` and the cross-attention block is skipped, the subsequent layers (which include further LayerNorm layers further down the stack) are still present and their parameters were learned under the assumption that their inputs had passed through the cross-attention. If the cross-attention is simply bypassed (the text hidden states passed directly without modification), the skip-connection residual has different statistics than what the downstream LayerNorm layers expect.

### The shared query projection problem

More specifically: if `graph_text_fusion.py` uses a cross-attention where the query is projected from the text hidden states by a linear projection `W_q`, that projection is jointly trained with the cross-attention mechanism. The projection is optimizing to make the text features attend efficiently to graph nodes. After training, `W_q` has learned to project `text_hidden` into a query space that anticipates graph structure.

When this projection is applied at eval time (even if the cross-attention itself is skipped), the text hidden states passed to subsequent layers have already been transformed by a `W_q` that was trained for graph-conditional operation. The text path is no longer operating on the same hidden states it would produce without the fusion module present at all.

**This mechanism does not require the cross-attention to fire.** The contamination is in the projection layers and their effect on the downstream computation graph, not in the attention weights themselves.

### Why this matters for the diagnosis

If cross-attention parameter entanglement is a contributing factor, then fixing the eval-mode-mismatch (passing `graph_batch=None` consistently or bypassing fusion at eval) will not fully recover performance. The recovery ceiling will be the accuracy achievable by the text path through the fusion-module-contaminated projection layers — which will be lower than a text-only model trained without the fusion path at all.

The team should design the fix to test this: after patching the eval-mode mismatch, compare the recovered accuracy against a K9 baseline run without the diagram-loop PR applied. If the recovered accuracy is materially below the K9 baseline, cross-attention entanglement is a likely co-factor.

---

## C4. The 4.7× train loss collapse signature

### The numbers in context

The task states:
- K9 baseline: 2.33 → 0.52 (4.5×)
- K9_SC3 smoke: 4.28 → 1.38 (3.1×)
- K9_DiagLoop full: 2.19 → 0.47 (4.7×)

The claim is that 4.7× is "the fastest." But 4.5× vs 4.7× is a 4.4% difference in compression ratio between epoch 0 and epoch 1. Over a single epoch on a large training corpus, this is not statistically distinguishable from noise. The claim that K9_DiagLoop's collapse is qualitatively "faster" rests on a difference smaller than typical run-to-run variance from batch ordering and initialization randomness.

### What the collapse DOES tell us

However, the specific shape of the collapse is informative in a different way. The K9_DiagLoop full run starts at a lower training loss (2.19 vs 2.33 for K9 baseline) and achieves a lower training loss after epoch 1 (0.47 vs 0.52). This means the K9_DiagLoop model is NOT just finding the same minimum as K9 baseline — it is finding a different, lower-loss solution. Training loss 0.47 vs 0.52 is a 9.6% reduction.

If the diagram-loop were contributing only noise (because graph_encoder is randomly initialized at the start), the training loss should be higher than the baseline, not lower. Random graph features would add noise to the predictions and make optimization harder. The fact that training loss is lower suggests the model is genuinely using the graph information during training to achieve better prediction of training labels.

This confirms the eval-mode-mismatch hypothesis's premise: the model IS learning to use `graph_batch` during training, making the eval-mode-mismatch more damaging over time. But it simultaneously raises a harder question: if the model is using graph structure productively, what exactly is it learning?

### The shortcut hypothesis is independent

Even granting that the model uses graph information genuinely, the nature of that usage matters. The training corpus has a structural property: `cas_expression` labels determine graph topology deterministically (each expression compiles to a specific graph via `build_diagram()` at compiler.py:5543). This means graph topology and training label are in near-bijective correspondence. The model can achieve very low training loss by learning `graph_topology → label` — a topological lookup — rather than `text → label`.

The 4.7× loss collapse in one epoch is consistent with rapid topological memorization: the model discovers that attending to graph structure provides a near-perfect training signal and down-weights the text path. The text path is then undertrained relative to a text-only baseline.

**Both mechanisms (eval-mode-mismatch AND topological memorization) can be true simultaneously.** The team's fix for eval-mode-mismatch does not test or address topological memorization. A retrain that passes `graph_batch` consistently at both train and eval — the fix the team is preparing — will still be subject to the topological memorization shortcut if the eval graphs are oracle-derived (C2).

---

## C5. The non-monotonic peak at epoch 2 (48.4% → 30.7%)

### The monotonicity prediction

The eval-mode-mismatch hypothesis, in its simplest form, predicts the following eval trajectory for the smoke run:

- Epoch 0: graph encoder randomly initialized; cross-attention outputs near-noise; text path operates largely unimpeded; eval accuracy close to the text-only K9 baseline
- Epoch 1: graph encoder has trained for one epoch; cross-attention weights are non-random; eval-mode-mismatch begins to damage text path; accuracy starts to fall
- Epoch 2, 3, 4: graph encoder increasingly converged; cross-attention damage increases; accuracy monotonically falls

This predicts a **monotonically declining trajectory from epoch 0 onward.** The smoke run does not show this. It shows:

- Epoch 0: text-only eval at some value (not reported in the brief)
- Epoch 2: peak at **48.4%**
- Epoch 4: floor at **30.7%**

A trajectory that peaks at epoch 2 and then falls violates the monotonic prediction. The peak means the model is genuinely improving on the text-only eval task through epoch 2, before some threshold event causes degradation.

### The correct two-phase interpretation

The non-monotonic trajectory is best explained by a two-phase model:

**Phase 1 (epochs 0–2): Genuine text-path learning**

In the first epochs of training, the graph encoder's representations are noisy but partially informative. The cross-attention mechanism uses both text and graph signals. Because the graph encoder output is noisy, the model learns to rely more heavily on the text path (the more reliable signal). The text path improves on the training data, which also improves performance on the held-out eval (even in text-only eval mode, because the text representations are genuinely better).

This explains the rise to 48.4% at epoch 2. The model is learning real text→CAS structure. The eval-mode-mismatch is present but its damage is limited because the cross-attention hasn't learned to depend on the graph encoder yet.

**Phase 2 (epochs 3–4): Cross-attention convergence and collapse**

After epoch 2, the graph encoder's representations have converged enough to provide a strong, consistent signal. The cross-attention mechanism discovers that graph_batch provides a better training gradient than the text path alone (due to topological bijection). The model shifts to relying on graph information, and the text path's gradient contributions are suppressed.

In training mode, this produces excellent training loss (confirming C4). In text-only eval mode, the cross-attention now expects graph features that aren't provided, and the text-path representations are undertrained for the eval distribution. Eval accuracy collapses to 30.7%.

### Why this dual-phase interpretation is a problem for the fix

If Phase 1 is real (genuine text learning) and Phase 2 is the collapse, then the team's fix (consistent graph_batch at eval) will restore Phase 2's damage but will not recover Phase 1's learning trajectory. The fixed model may plateau in the same range as Phase 1's peak (around 48–50%) rather than reaching the text-only 85.3% baseline.

More seriously: a fixed retrain where `graph_batch` is consistently provided at eval will succeed if the eval graphs are genuinely informative and non-oracle. But if the eval graphs are oracle-derived (C2), the fixed model will appear to achieve very high accuracy (perhaps 65%+ matching the smoke's oracle measurement) while actually being a lookup table on graph topology, not a generalizing text classifier.

The team cannot distinguish Phase 1/Phase 2 dynamics from pure eval-mode-mismatch using only the aggregate trajectory. Per-head accuracy curves across epochs would be diagnostic: if Noetic accuracy in particular rises in Phase 1 and collapses in Phase 2, that implicates topological memorization (Noetic operators are directly encoded in graph node labels). If all heads collapse uniformly, eval-mode-mismatch is more likely.

---

## Best Alternative Hypothesis: Pre-trained Checkpoint Degradation under Graph-Conditional Fine-Tuning

If the team had to identify the second-most-likely diagnosis after eval-mode-mismatch, the candidate is:

**K9_DiagLoop was initialized from the K9 structured-token 85.3% checkpoint, and the diagram-loop PR applied graph-conditional fine-tuning that systematically degraded the pre-trained text representations.**

### Evidence for this interpretation

1. **Epoch 0 accuracy at 63.2% is inconsistent with random initialization.** The actual structured-token run (committed to this repo) starts at 18.3% from random init. A 63.2% starting point implies a pre-trained initialization. 63.2% could represent partial degradation of an 85.3% checkpoint during the first data-loading and one-step evaluation.

2. **The trajectory shape (monotonic decline from epoch 0) is consistent with checkpoint degradation**, not with a model learning something new and then forgetting it. If the diagram-loop PR added the graph path to a randomly-initialized model, epoch 0 should start near-chance. If it was applied to the 85.3% checkpoint, epoch 0 should start near 85.3% and then fall as graph-conditional fine-tuning corrupts the representations — which is precisely what 63.2% → 42.9% → 28.1% shows.

3. **The 34.8 pp lift in the smoke** would then reflect the pre-trained model correctly encoding text → CAS before graph-conditional corruption has propagated deeply, plus oracle contribution from `prior_diagram`.

### What this predicts

If checkpoint degradation is the mechanism, then:
- The retrain from random init (the fix the team is preparing) will NOT reproduce the 63.2% epoch-0 starting point
- The retrain will show the normal 18.3% epoch-0 accuracy and rise from there
- If the fix is only eval-mode-mismatch, the retrain's final accuracy may be similar to the K9 baseline (85%+), not meaningfully higher
- The +13.7 pp Noetic gain may vanish entirely, because it was an artifact of the pre-trained checkpoint's text-path knowledge being evaluated before graph-conditional fine-tuning could fully corrupt it

### What the team should verify before retraining

1. **Confirm the initialization state of K9_DiagLoop**: was it trained from random init or from the K9 structured-token checkpoint? The run config (`manifest.json`) for K9_DiagLoop should show this.

2. **Compare epoch 0 accuracy**: if K9_DiagLoop's epoch 0 accuracy is 63.2% and the K9 baseline's epoch 0 is 18.3%, the checkpoint initialization hypothesis is confirmed and the fix must address both initialization and eval-mode-mismatch.

3. **Audit `evaluate_diagram_loop_invariance.py`**: this file must be found and read before any retrain is declared successful. The smoke's 65.5% is the only positive datapoint for the diagram-loop architecture, and it cannot be validated without this script.

4. **Run a text-only eval on the K9_DiagLoop checkpoint at epoch 0**: if the epoch-0 checkpoint achieves 63.2% text-only (no graph), the representations were pre-trained. If it achieves 18.3%, the model started from random init and the 63.2% figure requires another explanation.

---

## Summary for the team

The counter-skeptic position is not that the diagram-loop architecture is wrong. It is that the team has four independent unknowns they cannot resolve without the missing files:

| Unknown | File needed | Status |
|---|---|---|
| What does the graph path actually do? | `graph_encoder.py`, `graph_text_fusion.py` | **NOT IN REPO** |
| Is the +34.8 pp lift oracle-contaminated? | `evaluate_diagram_loop_invariance.py` | **NOT IN REPO** |
| What is the diagram-loop proposal's rationale? | `diagram_loop_lever_proposal.md` | **NOT IN REPO** |
| Was K9_DiagLoop initialized from a checkpoint? | K9_DiagLoop `manifest.json` | Not reviewed |

The eval-mode-mismatch hypothesis is plausible and likely a real contributor. But it is insufficient alone to explain the 63.2% epoch-0 starting accuracy, the non-monotonic smoke peak, and the +34.8 pp oracle-suspect lift. A retrain that fixes only eval-mode-mismatch but does not address initialization state and oracle leakage risk will produce a result the team cannot interpret cleanly.

The strongest single counter-argument is this: **if the epoch-0 accuracy of 63.2% is confirmed to come from a pre-trained checkpoint initialization, the regression is primarily a fine-tuning degradation problem, and fixing eval-mode-mismatch alone will not recover the architecture's claimed performance.**
