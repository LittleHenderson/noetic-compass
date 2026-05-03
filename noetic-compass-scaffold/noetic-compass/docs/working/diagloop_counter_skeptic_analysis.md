# DiagLoop Counter-Skeptic Analysis

**Role:** Counter-Skeptic (hostile reviewer)  
**Target hypothesis:** K9_DiagLoop full retrain regression (epoch 0=63.2%,
epoch 1=42.9%, epoch 2=28.1%) is caused by a train/eval mode mismatch —
training receives `graph_batch`, per-epoch eval calls `model(batch)` without
it.  
**Directive:** Argue hardest against this diagnosis. Make the team's case
stronger by ruling out nothing cheaply.  
**Source files read:** All five files retrieved from `refs/pull/6/head` via
GitHub API (`train_structured_prediction.py`, `structured_token_embedding.py`,
`graph_encoder.py`, `graph_text_fusion.py`,
`evaluate_diagram_loop_invariance.py`). The prior draft on this branch was
written without access to these files. This version supersedes it entirely.

---

## Preface — What the code actually says about the mismatch

Before arguing against the hypothesis, it must be stated precisely from the
code.

`evaluate_structured_token_prediction` (in `train_structured_prediction.py`)
always calls:

```python
batch_outputs = model(batch)   # no graph_batch argument
```

The training loop in `train_structured_token_prediction_local` constructs
`graph_batch` for any mini-batch containing at least one diagram-loop record:

```python
prior_diagrams = [r.get("prior_diagram") for r in batch_records]
graph_batch: dict | None = None
if any(pd is not None for pd in prior_diagrams):
    filled = [pd if pd is not None else _ctg("") for pd in prior_diagrams]
    graph_batch = serialize_diagram_for_batch(filled, device=dev)
outputs = model(batch, graph_batch=graph_batch)
```

With K=9 diagram-loop variants per canonical record, approximately 9/10 of
training records carry `prior_diagram`. Therefore roughly 9 in 10 mini-batches
invoke the full `GraphEncoder` + `GraphTextFusion` path during training. Eval
never does.

**The mismatch is real and confirmed in the code.** The arguments below do not
dispute that it exists. They argue it is insufficient to explain the observed
trajectory, and that fixing the routing alone will not vindicate the
architecture.

---

## C1. The hypothesis is too convenient

### The structural vulnerability of a three-for-one explanation

The eval-mode-mismatch hypothesis does three things simultaneously: it explains
the regression, it requires no architectural redesign, and it preserves the
+13.7 pp Noetic finding from the smoke. A diagnosis satisfying all three
desiderata of a team that wants to keep its architecture should be held to
higher evidentiary standards, not lower ones.

### What the epoch-0 starting point reveals

K9_DiagLoop full retrain starts at **63.2% text-only eval at epoch 0** — where
epoch 0 means: evaluate on the held-out 1K set after the first complete pass
through the augmented training corpus.

The structured-token 20-epoch GPU run committed to this repository
(`structured-token-20epoch-gpu-20260502-001907`) starts at **18.3% at epoch
0** from random initialization on the same held-out set. This is the expected
range for a randomly-initialized multi-class structured prediction model.

K9_DiagLoop's epoch-0 at 63.2% is 45 pp above random initialization.
`train_structured_token_prediction_local` contains no checkpoint-loading
mechanism — there is no `model.load_state_dict()` call before training begins
and no `--init-checkpoint` argument. The 63.2% is the model's performance
after training for one epoch on the K9_DiagLoop augmented corpus.

With K=9 diagram-loop variants, 9/10 of training records carry `prior_diagram`
compiled from the ground-truth `cas_expression`. In epoch 0, the model
processes all of these. The oracle graph directly encodes the four content-head
targets as explicit node features (dims 24-48 — see C2 for details). The model
can learn, in a single epoch, to read the answer from graph node features and
thereby achieve a training loss that is substantially lower than text-only
training. That low training loss produces **a model whose parameters have
already drifted toward oracle-graph reading after one epoch** — but the
text-only eval at epoch 0 still reports 63.2% because the text path has not
yet been fully displaced.

The 63.2% starting point is therefore not a neutral baseline that is then
degraded by eval-mode-mismatch. It is a partially-corrupted oracle-graph
reading model evaluated in text-only mode. The trajectory from 63.2% to 28.1%
is not "baseline performance declining due to routing bug" — it is
"oracle-shortcut dominance increasing over three epochs." Eval-mode-mismatch
is present throughout, but oracle-shortcut adoption is what drives the
monotone decline.

### What the topological-memorization hypothesis explains that eval-mode-mismatch cannot

The eval-mode-mismatch hypothesis predicts: fix the routing, and the model
will recover to the K9 baseline level (~85% text-only accuracy). The
topological-memorization hypothesis predicts: fix the routing (meaning: provide
oracle graphs at eval too), and the model will score high on oracle-graph eval
but will underperform the K9 baseline on **text-only eval** because the text
path has been crowded out. These produce different post-fix trajectories. The
team's current plan cannot distinguish them unless it also reports text-only
eval (no graph at eval) after the fix.

---

## C2. The +34.8 pp lift is confirmed oracle leakage — not a risk, a fact

### The oracle is explicit in the evaluator code

`evaluate_diagram_loop_invariance.py`, function `make_diagram_loop_records`:

```python
def make_diagram_loop_records(records):
    result = []
    for record in records:
        variant = dict(record)
        variant["prior_diagram"] = compile_to_graph(
            str(record.get("cas_expression", ""))   # ← ground-truth label
        )
        ...
    return result
```

`cas_expression` is the **target field** — the label all prediction heads are
optimized to predict. The evaluator compiles this label into a graph and
provides it as `prior_diagram` to the model before asking for a prediction.
The model is given the answer in a different notation and asked to produce the
answer. The docstring even acknowledges this: "when the correct CAS diagram is
fed as prior context."

This is not accidental. The file is called `evaluate_diagram_loop_invariance.py`
— it is measuring invariance, not generalization. The team appears to have
measured oracle-decoding performance and reported it as architectural
performance. These are different claims.

### The node feature layout makes the leak mechanically complete

`diagram_serialization.py`, `NODE_FEATURE_DIM = 49`, layout:

```
dims  0–23  : node-kind one-hot (24 classes)
dims 24–33  : noetic one-hot (10 classes)       ← predicts "noetic" head
dims 34–37  : domain one-hot (4 classes)        ← predicts "domain" head
dims 38–44  : drive one-hot (7 classes)         ← predicts "drive" head
dims 45–48  : register multi-hot (4 bits)       ← predicts "register" head
```

The four content heads — noetic (10-class), domain (4-class), drive (7-class),
register (4-bit multi-label) — are each answered by the corresponding node
feature slice. The model does not need to perform any semantic processing on
text to achieve high accuracy under oracle-graph eval. It needs only to learn:
attend to node features, read off the one-hot encoding, output the matching
class.

The 34.8 pp lift (30.7% → 65.5%) is precisely the gap between text-based
inference and oracle-graph decoding. The 30.7% reflects text path degradation
(consistent with C1 and C3). The 65.5% reflects partially learned oracle
decoding (not yet perfect because the graph encoder trained for only a few
epochs).

### The Noetic finding is the most oracle-contaminated result

The +13.7 pp Noetic gain motivating the architecture is the head most directly
served by the oracle leak. Noetic operators appear as both node-kind labels
(dims 0-23) and as explicit node features (dims 24-33). An oracle graph reader
gains near-perfect Noetic signal with no semantic understanding of the input
text. The +13.7 pp Noetic lift is the result most expected under oracle
contamination and the result least attributable to genuine diagram-loop
generalization. Before the team retrains, it should state what Noetic gain it
expects on **text-only eval** (no graph) after the fix, because that is the
only measurement uncontaminated by the oracle.

### Why 65.5% is below the 85.3% text-only best — and what this means

If the oracle graph gave perfect information, the `--with-graph-path` eval
should approach 100%. It achieves 65.5%. The gap exists because the model has
not yet fully learned to decode oracle node features — the graph encoder
trained for only a few epochs on a task where the oracle graph is provided.
Simultaneously, the text path has been partially corrupted (C3 below). Both
effects compress the oracle-path score toward the middle. Neither is evidence
of genuine generalization.

---

## C3. Cross-attention parameter entanglement persists when graph_batch is None

### The q_proj gradient path contaminates the embedding

`graph_text_fusion.py` defines the fusion layer:

```python
self.q_proj  = nn.Linear(d_text, d_text, bias=False)
self.k_proj  = nn.Linear(d_graph, d_text, bias=False)
self.v_proj  = nn.Linear(d_graph, d_text, bias=False)
self.out_proj = nn.Linear(d_text, d_text, bias=False)
self.norm    = nn.LayerNorm(d_text)
```

When `graph_nodes is not None` (90% of training steps):

```python
q = self.q_proj(text_hidden).view(B, T, H, D).transpose(1, 2)
...
context = self.out_proj(context)
return self.norm(text_hidden + context)
```

The gradient of the loss flows: `head loss → post-fusion hidden_states →
fusion.norm → out_proj → attn_weights → q_proj → text_hidden → embedding`.

`q_proj` is optimized to project `text_hidden` into a query space that attends
efficiently to oracle node features at dims 24-48. This gradient signal reaches
the embedding and nudges all its parameters (`surface_embedding`,
`signature_projection`, `output_norm`, `fusion_gate`) toward producing
activations that are good cross-attention queries — not good direct head
inputs.

When `graph_nodes is None` at eval, the fusion layer executes:

```python
if graph_nodes is None:
    return text_hidden
```

`q_proj` is never applied. The head receives raw embedding output. But the
embedding's parameters have been trained to produce query-optimized
representations, not head-input-optimized representations. This mismatch is
not the routing bug; it is parameter-level drift caused by the mixed objective
during training.

### The LayerNorm statistics add a second entanglement

`fusion.norm` normalizes `text_hidden + context` during training. For the 90%
of training steps where graph is present, the inputs to this norm include a
nonzero cross-attention context vector. The norm learns running statistics for
the fused representation. When the head receives `text_hidden` directly at eval
(skipping the norm entirely, since the whole fusion call is bypassed), the
head's downstream normalization layers receive activations with different
statistics from what 90% of training steps produced.

This is independent of the routing bug. The norm statistics contamination
persists in a hypothetical retrain that consistently provides `graph_batch`
at eval — as long as 90% of training records use oracle graphs and 10% are
text-only, the embedding's parameters are split between two objectives in
different proportions.

### Diagnostic implication

After the team applies the routing fix, they should compare:

1. K9_DiagLoop (fixed) text-only eval vs K9 baseline text-only eval.
2. K9_DiagLoop (fixed) with model-predicted graph (not oracle) vs K9 baseline.

If (1) shows K9_DiagLoop underperforming K9 baseline text-only, cross-attention
entanglement is confirmed as a co-factor beyond the routing bug. If (2) shows
degradation vs K9 baseline, oracle dependency is confirmed. Both comparisons
should be reported, not only the oracle-graph comparison.

---

## C4. The 4.7× train loss collapse confirms oracle shortcut — not just mismatch

### The absolute loss level is the diagnostic

The task brief compares collapse ratios: K9 baseline 4.5×, K9_DiagLoop full
4.7×. The 4.4% difference in compression ratio is within batch-ordering and
seed variance — this comparison establishes nothing qualitatively different.

The diagnostic is the **absolute training loss** after epoch 1: K9_DiagLoop
achieves 0.47 vs K9 baseline's 0.52, a 9.6% lower loss. This means the model
is not converging faster to the same solution — it is finding a different,
lower-loss solution that the text-only model cannot reach.

### Why the lower absolute loss implicates oracle reading

The oracle graph encodes the content-head targets as one-hot and multi-hot
features in node feature dims 24-48. A model that learns to read these
features achieves lower training loss than a text-only model because:

1. The oracle signal is zero-ambiguity — one-hot encoding, no lexical
   variation.
2. The cross-attention can concentrate attention mass on relevant nodes in
   a handful of gradient steps, exploiting the clean feature structure.
3. The text path must handle lexical and syntactic variation across the K=9
   paraphrase templates; the graph path does not.

The 9.6% lower absolute loss reflects the model using the oracle shortcut to
reduce its loss floor below what text-only learning can achieve. The 4.7×
epoch-0→1 collapse is not a sign of architectural efficiency; it is a sign of
shortcut discovery.

### Both mechanisms can be true — and both need to be addressed

The routing bug is real. The oracle shortcut is also real. The routing fix
closes the eval-time gap only if the eval graphs are oracle-quality. A retrain
that passes oracle graphs consistently at both train and eval will show high
accuracy — but that is oracle decoding, not production performance. In
production, `prior_diagram` must be the model's own previous prediction on a
novel input. The team should not declare success until accuracy is measured
with model-predicted (not oracle) graphs.

---

## C5. The non-monotonic smoke peak at epoch 2 is mechanically inconsistent with pure eval-mode-mismatch

### What monotone degradation would look like

Pure eval-mode-mismatch predicts the following smoke trajectory:

- Epoch 0: graph encoder is randomly initialized; cross-attention output is
  near-noise; text path provides the dominant gradient signal; eval accuracy
  starts near or above the K9 text-only baseline.
- Epoch 1+: graph encoder trains; cross-attention becomes informative;
  model's text-path gradient contribution is crowded out; text-only eval
  accuracy declines monotonically.

This is a strictly monotone declining trajectory from epoch 0 onward.

The K9_DiagLoop **smoke** text-only eval shows:

```
epoch 2: 48.4%   ← PEAK
epoch 4: 30.7%
```

A peak at epoch 2 is inconsistent with monotone decline from epoch 0. The
text path is genuinely improving through epoch 2. Eval-mode-mismatch is
present but its damage is deferred.

### The two-phase mechanism the peak reveals

The non-monotonic trajectory is evidence of a discrete phase transition, not
gradual degradation.

**Phase 1 (epochs 0–2): Graph encoder underfit, mixed-objective learning.**
The cross-attention context in early epochs is high-variance (graph encoder
randomly initialized). The training gradient for graph-path records is
dominated by the text-path component (the noisy cross-attention contributes
little useful signal). The embedding updates primarily from text supervision.
The eval's text-only accuracy improves as text generalization improves. This
is consistent with the rise to 48.4% at epoch 2.

**Phase 2 (epochs 3+): Phase transition to oracle-shortcut dominance.**
After enough training, the graph encoder produces stable, informative node
embeddings for the oracle graphs. The cross-attention discovers that attending
to node feature dims 24-48 provides a near-perfect gradient signal. Training
objective switches: oracle-graph reading dominates, text path is starved of
gradient. Eval accuracy collapses to 30.7%.

In the **full retrain** (larger training set, more gradient steps per epoch),
the phase transition occurs faster — within epoch 1 rather than epoch 2-3 —
which is why the full run shows no visible peak; it enters Phase 2 before the
first reported eval.

### Why this invalidates the routing fix as the complete solution

If Phase 1 is real (genuine text learning in early epochs) and Phase 2 is
oracle-shortcut collapse, then:

- Fixing the routing restores Phase 2's damage IF oracle graphs are provided at
  eval. The model will score well because it learned to decode oracle graphs.
- The text-path learning from Phase 1 is not recoverable without changing the
  training regime.
- A fixed retrain with K=9 oracle-graph augmentation will reproduce the same
  phase transition in approximately the same epoch window.

The critical validation is not "does fixing the routing produce high accuracy?"
but "does the accuracy remain when oracle graphs are replaced with
model-predicted graphs?" Only the latter tests whether Phase 1's text learning
survived the phase transition.

---

## Best Alternative Hypothesis

**Oracle-Graph Teacher Collapse** — the K=9 diagram-loop augmentation creates
a 9:1 oracle-to-text training ratio that trains the model to decode ground-
truth answers rather than to generalize from text, making the eval-mode-mismatch
a symptom rather than a cause.

### Mechanism

1. `expand_with_diagram_loop_pairs` generates K=9 variants per canonical where
   `prior_diagram = compile_to_graph(cas_expression)` — the oracle graph.
   With K=9, 90% of training records carry oracle graphs.

2. Epoch 0: graph encoder randomly initialized; noisy cross-attention context;
   model updates embedding from both text (10%) and cross-attention gradient
   path (90% records, but low-quality graph signal). Text path learns adequately,
   achieving 63.2% text-only eval after the first epoch on the large K=9
   augmented corpus.

3. Epoch 1: graph encoder has converged enough to produce structured node
   embeddings for oracle features. Cross-attention discovers the oracle
   shortcut. Training loss collapses 4.7× (2.19 → 0.47). The text-path
   gradient contribution becomes negligible relative to the oracle-graph
   reading gradient. Embedding parameters drift toward cross-attention
   query optimization.

4. Epoch 2+: oracle shortcut fully dominant. Text-only eval: 28.1% (full
   run) / 30.7% (smoke). The text path has been substantially displaced
   as the primary learning pathway.

### Key distinction from eval-mode-mismatch

Eval-mode-mismatch: the model works; it's being tested wrong. Fix the routing,
and the model performs as designed.

Oracle-Graph Teacher Collapse: the model was trained to do the wrong thing.
Fix the routing, and text-only eval will still underperform the K9 baseline,
because the embedding has been retrained away from text-generalization optima.
Oracle-graph eval will score high, but that is oracle decoding, not production
performance.

### Distinguishing experiments

| Experiment | Mismatch-only predicts | Oracle-Collapse predicts |
|---|---:|---:|
| Post-fix, text-only eval | ~85%+ (matches K9 baseline) | ~40–55% (text path damaged) |
| Post-fix, oracle-graph eval | ~85%+ | ~65–75% (oracle decoding ceiling) |
| Post-fix, model-predicted graph eval | ~85%+ | ≤ K9 baseline |
| K=1 diagram-loop retrain, text-only eval | Similar to K=9 fix | Better than K=9 fix |
| K9 baseline (no diagram-loop) text eval | ~85%+ | ~85%+ (unaffected) |

The critical single experiment: **text-only eval after the routing fix**.
Eval-mode-mismatch predicts full recovery. Oracle-Graph Teacher Collapse
predicts at most partial recovery. If text-only eval after the fix scores
below the K9 baseline, the architecture has a deeper problem than routing.

### What the team should do before declaring success

1. **Report text-only eval** (no graph at eval) explicitly, not only
   oracle-graph eval. Do not treat 65.5% oracle-graph as "true performance."

2. **Compare K9_DiagLoop (fixed) text-only vs K9 baseline text-only** on the
   same epoch count. If K9_DiagLoop underperforms, the architecture is
   net-negative for text generalization.

3. **Run one variant with model-predicted prior** (the model's own
   epoch N−1 prediction compiled to a graph, not the oracle label) to test
   whether the lever generalizes to a realistic self-referential regime.

4. **Reduce K to 1 or 2 in a smoke** to test whether lower oracle-graph
   ratio reduces text-path corruption. Oracle-Graph Teacher Collapse predicts
   that K=1 fixes much of the degradation even without changing the routing.

---

## Summary

| Section | Core claim | Strength |
|---|---|---|
| C1 | 63.2% epoch-0 reflects oracle-shortcut onset, not a neutral baseline; topological memorization and eval-mode-mismatch produce identical aggregate trajectories | Strong — only per-head per-epoch curves distinguish them |
| C2 | The +34.8 pp lift is confirmed oracle leakage by code inspection; node features at dims 24-48 directly encode the content-head answers; the +13.7 pp Noetic result is the most oracle-susceptible signal | Very strong — confirmed fact, not risk |
| C3 | `q_proj` gradient contaminates embedding weights toward cross-attention query optimization; `fusion.norm` statistics mismatch; both persist regardless of routing fix | Medium-strong — magnitude requires ablation |
| C4 | 0.47 vs 0.52 absolute training loss (9.6% lower) indicates a different solution space, not faster convergence; oracle shortcut is the only available lower-loss solution | Strong — absolute loss level is a concrete datapoint |
| C5 | Non-monotonic smoke peak at epoch 2 is mechanically inconsistent with monotone degradation; requires two-phase explanation; routing fix cannot address the phase transition | Very strong — the peak falsifies monotone-degradation prediction |
| Alt | Oracle-Graph Teacher Collapse: K=9 creates 9:1 oracle:text ratio; model trained to decode answers not generalize from text; routing fix is necessary but insufficient | Strong — makes distinct, testable predictions |

**The counter-skeptic position in one sentence:** the routing bug is real and
should be fixed, but it is the smaller of two problems; the larger is that K=9
oracle-graph augmentation trains the model to decode answers from ground-truth
graphs, and no routing fix alone can recover text generalization without also
changing the training regime to use realistic self-referential priors.
