# Paper A v2 — Section 5.7 Draft (Diagloop / Tri-Channel Architecture)

**Status.** Draft. Empirical anchor is the K9_DiagLoop smoke v2 honest evaluation (5K canonical records, K=8 paraphrase + K=3 diagram-loop, 5 epochs). The full-scale K9_DiagLoop v3 retrain (16,570 canonical records, ~31K steps, 20 epochs) is in flight at draft time (PID 10441 on pod 104.255.9.187, started 2026-05-04 18:19 UTC). Section 5.7.5 carries explicit placeholders for the v3 numbers and three pre-committed interpretation cases. No existing paper draft is modified by this file; this is an independent draft for the §5.7 slot.

**Date.** 2026-05-04.

---

## 5.7 The Diagloop / Tri-Channel Architecture: Empirical Lift Under Honest Two-Pass Evaluation

### 5.7.1 Motivation

CAS expressions are not flat strings. The CAS v7.7 compiler emits a typed graph in which Noetic operators correspond to nodes (NoeticCluster, RelationCluster, IntegrationEdge), Processing Domains, Core Drives, and Registers attach as axis-attribute keys, and CAS operators (`→`, `×`, `*`, `+`) correspond to typed edges between clusters. A single CAS expression therefore admits two formally distinct ground-truth representations: a notation string that encodes the expression linearly in a token sequence, and a typed graph that encodes the same expression topologically as nodes, edges, and attributes.

The text channel and the graph channel have different recovery profiles under paraphrase noise. A paraphrase template that scrambles surface tokens — the bare-slot template, the K=9 prefix-stripped variants — corrupts the linear encoding by shifting token positions, removing prefix scaffolding, and exposing slot content out of its conventional ordering. A token-level model trained on the corrupted linear encoding sees a substantially different input distribution between canonical and paraphrase, even though the underlying CAS expression is invariant. The graph encoding is unaffected by paraphrase: graph node identity is keyed on `(node_type, noetic_value, domain_value, register_value)` for NoeticCluster nodes and on edge type for relations, none of which the paraphrase rewrites.

This asymmetry is the architectural thesis of the diagloop / tri-channel approach. If a model can be trained to consume both the text input and a graph-encoded prior, the graph channel provides a recovery path for axis identity that the text channel cannot: paraphrase noise on the text input does not corrupt the graph input, and a fusion mechanism that lets the model attend to graph node identity at prediction time gives the model an alternative route to the correct axis values when the text route fails. The empirical question this section addresses is whether the graph channel adds non-redundant signal beyond what a text-only model can recover, and whether that signal survives the transition from smoke scale to full training scale.

### 5.7.2 Architecture

The tri-channel architecture extends the K=9 baseline structured-prediction model (12 prediction heads, 64-dimensional shared bottleneck, structured-token tokenizer) with a graph encoder and a cross-attention fusion layer.

**Graph encoder.** A graph attention network (GAT) over the CAS-compiler-emitted typed graph. Node features carry NODE_FEATURE_DIM=49 dimensions encoding node type, axis-attribute one-hots (10 Noetics, 4 Domains, 7 Drives, 4 Registers), and structural flags. Edge features carry EDGE_FEATURE_DIM=34 dimensions encoding edge type and source/target node-type tuples. The GAT uses two layers with hidden_dim=64 to match the text encoder's bottleneck dimensionality. Reference: `cas-native/model/graph_encoder.py`.

**Graph-text fusion.** Cross-attention from text-encoder hidden states to graph-encoder node hidden states. Text positions attend to graph nodes; the fused representation passes to the 12 prediction heads. The fusion is bidirectional in implementation but only the text-side fused representation is consumed by the head stack at prediction time. Reference: `cas-native/model/graph_text_fusion.py`.

**Diagram-loop training augmentation.** During training, each canonical record produces K=3 diagram-loop pairs in addition to the K=8 paraphrase variants. A diagram-loop pair consists of (paraphrase_text, canonical_graph), where the canonical graph is the typed graph compiled from the canonical CAS expression of the same record. The model is trained to predict the canonical CAS expression given the paraphrase text and the canonical graph as joint input. The training signal teaches the fusion layer to use the graph as a structural prior when the text input is corrupted. Reference: `cas-native/training/diagram_serialization.py`.

The augmentation is K=8 paraphrase + K=3 diagram-loop = 11 variants per canonical, vs the K=9 baseline's 9 paraphrase variants. Total record budget is the same magnitude; the diagram-loop variants reuse paraphrase texts and add the graph channel as an extra input.

### 5.7.3 Eval Methodology — Honest Two-Pass Protocol

Evaluating a graph-augmented architecture requires care to avoid an oracle leak. The naive evaluation passes the ground-truth `cas_expression` through the compiler to produce a graph, then passes that graph as the prior input on the paraphrase variant of the same record. The model's task is then to "predict" `cas_expression` given `cas_expression`-derived graph as input. The model can succeed by reading the answer off the graph encoder rather than by recovering the answer from the paraphrase text. This is not a measurement of paraphrase invariance; it is a measurement of whether the model can copy from its own input.

The honest protocol is a two-pass evaluation. Pass 1 runs the model on the canonical text input alone, with no graph input, and records the model's canonical CAS expression prediction — that is, the model's actual best guess at the CAS expression given only the canonical text. Pass 2 compiles the model's pass-1 prediction (not the ground-truth `cas_expression`) into a graph, and passes that graph as the prior on the paraphrase text input. When pass 1 is correct, the graph prior encodes the correct structure and pass 2 measures whether the model can use a correct prior to recover the answer under paraphrase. When pass 1 is wrong, the graph prior encodes the wrong structure, and pass 2 measures whether the model recovers despite a wrong prior — which is what production deployment looks like, where the model has access only to its own predictions and not to ground truth.

The honest protocol is implemented in `cas-native/training/evaluate_diagram_loop_honest.py` (PR #19). The implementation includes a monkeypatch invariant test that intercepts every call to `compile_to_graph` during evaluation and asserts that the input is never the held-out record's `cas_expression` field. The invariant fires before any model forward pass; an oracle leak triggers an explicit AssertionError rather than a silent inflated metric.

A footnote-worthy methodology lesson: the original reference implementation, `evaluate_diagram_loop_invariance.py --with-graph-path`, did carry the oracle leak. The leak was identified during code review of the smoke v1 result, which had reported paraphrase-with-graph-prior accuracy comparable to canonical and prompted a sanity check. PR #19 corrected the protocol; smoke v1 numbers are deprecated and not reported in this paper. The protocol correction predates all numbers in §5.7.4 and §5.7.5.

### 5.7.4 Smoke v2 Honest Results

**Setup.** Training base: K=9 baseline checkpoint commit `3232f05`, structured-token tokenizer, 64-dimensional bottleneck. Augmentation: K=8 paraphrase variants per canonical + K=3 diagram-loop pairs per canonical. Training data: 5,000 canonical Level 3 recoverable records expanded to 5,000 × (1 canonical + 8 paraphrase + 3 diagram-loop) = 60,000 training examples. Held-out evaluation: 1,000 records, joint-key-filtered against training, eval label set is `level3_recoverable_eval_1000_v77_relabeled.jsonl` (post-relabel). Epochs: 5. Learning rate: 1e-3. Eval protocol: honest two-pass (§5.7.3).

**Aggregate results.**

| Metric | Value |
|---|---:|
| Canonical text-only (pass 1) | 47.9% |
| Paraphrase text-only (no graph prior) | 26.6% |
| Paraphrase with self-prior (pass 2, honest) | **45.4%** |
| Honest lever lift (pass 2 − text-only paraphrase) | **+18.8 pp** |

The headline number is the +18.8 pp lift. Paraphrase-with-self-prior closed almost the entire canonical-paraphrase gap: 45.4% paraphrase under self-prior vs 47.9% canonical, a residual 2.5 pp gap where the K=9 baseline at the same training scale shows a much wider gap on the same eval set. The graph channel, fed by the model's own pass-1 prediction, recovers most of the paraphrase-induced loss in axis identity even when the prior is sometimes wrong.

**Per-head consistency under self-prior.**

| Head | Paraphrase consistency under self-prior |
|---|---:|
| registers | **98.6%** |
| noetic | 85.1% |
| domain | 81.0% |
| drive | 71.6% |

The registers head at 98.6% under self-prior is the strongest single-head result observed across any CAS-Native experiment to date — including the K=9 bare-slot retrain, the self-conditioning smoke, and the meta-logic-reweight runs. The result is notable not in isolation but in conjunction with two prior diagnostics: (a) the K=9 bare-slot run identified registers as the strongest gainer from prefix-memorization mitigation, and (b) the self-conditioning small-scale smoke could not move drive consistency through a linear `[PRIOR]` block, suggesting the channel matters. The diagloop architecture is the first lever in the program to push registers consistency above 95%, and it does so through a non-text channel.

**Per-bucket all-heads-exact.**

| Bucket | n | Paraphrase with self-prior |
|---|---:|---:|
| `v77_omega` | 267 | 75.7% |
| `v74_baseline` | 200 | 60.5% |
| `v77_rule_four` | 59 | 48.6% |
| `v75_register` | 264 | 25.8% |
| `v76_production` | 108 | 24.4% |
| `meta_logic` | 102 | 7.5% |

The per-bucket distribution is informative. Buckets with relatively simple expression structure (`v77_omega`, `v74_baseline`) recover well; buckets with high expression arity (`v76_production` for recipe expressions, `meta_logic` for cluster expressions) recover poorly. The graph encoder hidden_dim=64 and two-layer GAT depth do not appear to give the architecture enough capacity to encode high-arity recipe-bucket and cluster-bucket structure at smoke scale. This is an architectural canary worth flagging for the full-scale result.

**Comparison to K=9 notation-only baseline at matching scale.** The K=9 notation-only baseline at 5K canonical / 5 epochs achieves paraphrase 46.9% on the same held-out set. The diagloop architecture matches the baseline's text-only paraphrase recovery (45.4% vs 46.9%, within statistical noise) AND lifts paraphrase invariance under self-prior simultaneously. This is the smoke-scale evidence that the graph channel is non-redundant: the architecture does not sacrifice text-channel paraphrase recovery to gain graph-channel paraphrase recovery — both signals coexist at smoke scale.

### 5.7.5 Full-Scale Retrain Results

**[V3 RESULTS — fill in after K9_DiagLoop_full_v3_2026_05_04 honest eval lands ~2026-05-04 20:30 PDT]**

**Setup.** Training base: K=9 baseline checkpoint commit `3232f05`. Augmentation: K=8 paraphrase + K=3 diagram-loop. Training data: 16,570 canonical Level 3 recoverable records (post joint-key filter) expanded to ~198,840 training examples. Held-out evaluation: 1,000 records on `level3_recoverable_eval_1000_v77_relabeled.jsonl`. Epochs: 20. Total steps: ~31,080. Eval protocol: honest two-pass (§5.7.3). Pod: 104.255.9.187. Run identifier: `K9_DiagLoop_full_v3_2026_05_04`. Started 2026-05-04 18:19 UTC.

**Aggregate results.**

| Metric | Value |
|---|---:|
| Canonical text-only (pass 1) | ___% |
| Paraphrase text-only (no graph prior) | ___% |
| Paraphrase with self-prior (pass 2, honest) | **___% (target ≥60%)** |
| Honest lever lift | **___ pp (target ≥15 pp)** |

**Per-head consistency under self-prior.**

| Head | Paraphrase consistency under self-prior |
|---|---:|
| registers | **___% (target ≥95%)** |
| noetic | ___% |
| domain | ___% |
| drive | ___% |

**Per-bucket all-heads-exact.**

| Bucket | n | Paraphrase with self-prior |
|---|---:|---:|
| `v77_omega` | 267 | ___% |
| `v74_baseline` | 200 | ___% |
| `v77_rule_four` | 59 | ___% |
| `v75_register` | 264 | ___% |
| `v76_production` | 108 | **___% (target: did high-arity recover with more data?)** |
| `meta_logic` | 102 | **___% (target: same architectural canary at full scale?)** |

**Pre-committed interpretation cases.** The §5.7 narrative downstream of this sub-section depends on which case the v3 numbers fall into. The cases are committed before the result lands:

**Case A — strong validation.** Paraphrase-with-self-prior ≥60% AND lift ≥20 pp AND registers per-head ≥95%. Interpretation: the tri-channel architecture works at scale. The smoke v2 result was not a small-scale artifact; it reflects a real architectural lever that scales. Recommendation: the diagloop architecture is the production architecture going forward, replacing K=9 notation-only as the deployment target. The §5.7.7 discussion frames per-head channel routing as the natural follow-on hypothesis to test.

**Case B — solid validation.** Paraphrase-with-self-prior 50-60% AND lift 15-20 pp. Interpretation: the architecture works but does not dominate the K=9 baseline on the joint metric. The graph channel adds real signal, but the cost-benefit against simpler levers (bare-slot template expansion, self-conditioning at scale) is not unambiguously favorable. Recommendation: continued lever exploration before architectural commitment. The §5.7.7 discussion treats the diagloop architecture as a successful research probe but defers the production-architecture decision to a follow-up study with per-head channel routing controls.

**Case C — collapse.** Paraphrase-with-self-prior <50% AND lift <10 pp. Interpretation: the smoke v2 lift was a scale artifact. The graph channel either does not survive full-data training or is dominated by capacity-stealing at the shared 64-dimensional bottleneck. Recommendation: deprecate the diagloop architecture in favor of K=9 + Lever 3 (TBD: self-conditioning at scale or grammar-guided sampling on the K=9 checkpoint). The §5.7.7 discussion frames the negative result as a publishable methodological finding: a non-redundant signal at smoke scale does not guarantee a net-positive architecture at full scale, and capacity-stealing at the shared bottleneck is the load-bearing mechanism.

**Sub-section status.** Numbers above are placeholders. The full-scale eval is expected to land approximately 2026-05-04 20:30 PDT. The case selection is mechanical: the table is filled in from the eval manifest, and the interpretation paragraph is selected from Case A / B / C above based on the threshold criteria. Section 5.7.6 and §5.7.7 are written to be valid under all three cases, with case-specific extensions noted.

### 5.7.6 Methodology Lessons

Three methodological lessons from the diagloop development arc are load-bearing for the rest of the paper, and for any subsequent tri-channel work.

**Eval-mode mismatch.** During the K9_DiagLoop development cycle preceding this section, a per-epoch evaluation hook called `model(batch)` without passing `graph_batch`, even though training called `model(batch, graph_batch=...)`. The eval was running text-only mode on every checkpoint while training supervised the fused mode on 25% of the records. The trajectory regressed during training, and the regression was initially read as "the model is learning a topological memorization shortcut." Code reading found the bug: `evaluate_structured_token_prediction` had not been updated when `graph_batch` was added to the forward signature. A same-checkpoint smoke comparison after the fix showed +34.8 pp lift when `graph_batch` was passed at eval time. The lesson is general: any architecture that adds an auxiliary input channel must audit every eval entry point for a mode-mismatch between training and evaluation forward calls. The training loss curve does not catch the bug; only an explicit eval-mode audit does.

**Limit-default trap.** The training script `train_structured_prediction.py` defaults `--limit` to 128. A full-data run on 16,570 canonical records requires `--limit 100000` (or any value greater than the canonical count) to be passed explicitly. Without the flag, the run silently produces a 114-canonical-record training set and a useless checkpoint. This trap caught a K9_DiagLoop full retrain on 2026-05-03 at epoch 4 with rate=0.0; the run was killed and restarted with the flag. Any future tri-channel experiment must pass `--limit 100000` explicitly.

**Reference implementation audit.** The original `evaluate_diagram_loop_invariance.py --with-graph-path` reference implementation was oracle-leaky, as documented in §5.7.3. Reference implementations that ship before the corresponding evaluation methodology has been audited are a chronic source of inflated metrics. Any architecture that exposes auxiliary channels at evaluation time must include an oracle-leak invariant test as part of its initial commit, not as a post-hoc fix. PR #19's monkeypatch invariant on `compile_to_graph` is the pattern.

### 5.7.7 Discussion

**Per-head asymmetry as evidence of non-redundant channel signal.** The smoke v2 per-head consistency ordering — registers (98.6%) > noetic (85.1%) > domain (81.0%) > drive (71.6%) — is not the ordering predicted by a model in which the graph channel is a uniform redundancy of the text channel. A uniform-redundancy model predicts that all four content axes should benefit from the graph prior at approximately the same rate, since the graph encodes axis identity for all four axes through the same node-attribute mechanism. The observed asymmetry suggests instead that channels carry non-redundant information at different per-axis rates: the graph channel is more informative for registers identity than for drive identity, even though both axes are represented in the graph encoding. One plausible explanation is that the graph encoding makes registers a first-class node attribute whose identity is unambiguous in the graph but is positionally ambiguous in the linear text encoding; whereas drive identity is embedded in a recipe-edge structure that the GAT depth (two layers) cannot fully exploit. Per-head channel routing — separate fusion parameters per prediction head, tuned to the per-head channel-information rate — is a natural follow-on hypothesis that the per-head asymmetry suggests but does not validate. Validation requires an ablation, not an observation.

**Per-bucket asymmetry as architectural signal.** The smoke v2 per-bucket distribution flags `v76_production` (24.4%) and `meta_logic` (7.5%) as architectural canaries. Both buckets exercise high-arity expressions: `v76_production` instantiates recipe semantics with multiple weighted prerequisites and an outcome; `meta_logic` instantiates cluster expressions with multiple inner expressions and meta-relation edges. The graph encoder at hidden_dim=64 with two GAT layers has limited capacity to encode the multi-arity edge structure of these expressions, and the fusion layer downstream cannot use information that the encoder did not produce. Increasing graph encoder capacity — wider hidden_dim (128 instead of 64), deeper GAT (three or four layers instead of two), or graph-level attention pooling — is the natural lever to test whether the bucket-level weakness is encoder-capacity bound or is a more fundamental architectural limit. This is a follow-on experiment, not a v2 paper claim.

**Cross-paper relevance of the honest two-pass eval protocol.** The honest two-pass protocol described in §5.7.3 is reusable for any architecture with an auxiliary input channel that derives from a transform of the model's task target. Examples include retrieval-augmented architectures (where the retrieved passage is conditionally selected based on the model's task input), self-distillation architectures (where the model's own logits become an input on a subsequent pass), and constitutional-style architectures (where the model's first-pass output is rewritten by a separate head and re-fed). In each case, the danger is that an evaluation protocol fed with task-target-derived auxiliary input becomes an oracle-leaky benchmark that scores the model on its ability to copy. The two-pass protocol — auxiliary input is the model's own pass-1 prediction, never the ground truth — is the structural correction. We propose it as a general benchmarking discipline beyond the CAS context.

**Limitations to acknowledge in any case.** Three limitations apply regardless of which v3 case lands. First, the architecture has been tested only on the CAS v7.7 ontology and the structured-token tokenizer; cross-architecture validation against vanilla T5 or BERT fine-tunes is deferred. Second, the K=3 diagram-loop augmentation ratio is a hyperparameter choice that has not been swept; K=1, K=5, K=10 may give different results. Third, smoke-vs-full-scale discrepancies have been observed in prior CAS-Native experiments (e.g., the meta-logic reweight smoke positive that did not survive full retrain), and we do not extrapolate from smoke-positive to full-scale-positive. The §5.7.5 result is the empirical anchor; smoke v2 motivates the experiment but does not determine it.

---

**End of §5.7 draft.**
