# Diagram-Loop Lever Proposal — Graph-Encoder Self-Reference

Status: proposal — not yet implemented.
Anchored to: commit `3232f05` (clean-eval rescore of d99810a).
**Dependency:** validate PR #4 (linear self-reference loop) on retrain first; this proposal builds on its outcome.

## TL;DR

Where PR #4 closes the self-reference loop with the **linear** CAS expression as a `[PRIOR]` token block, this proposal closes the loop with the **actual typed graph** the compiler produces from that expression. The linear form already encodes most of the diagram's information as a sequence; the graph form encodes the topology directly via a graph encoder fused with the existing text encoder. This is architecturally cleaner — the model sees structural relationships (co-presence, integration, RPM dependency) as *edges*, not as *operator tokens it has to parse*. It is also a meaningfully bigger build than PR #4, which is why PR #4 ships first.

## 1. The two loops, distinguished

PR #4 — the **linear loop**:

```
[PRIOR] (^4^E_{F2}|E × ^4^E_{F2}|f × ^4^E_{F2}|A) = ^4^E|Ω_attunement
[QUERY] As a CAS notation check, translate this slot list...
```

The model sees a string. The structured-token tokenizer parses each token with CAS-axis features attached. But the *topology* (that the three operands of `×` are co-present register-instances of the same state, that they integrate into a single emergent Ω) is conveyed only through token order and the `×` / `=` operator tokens. The model has to learn the structural relations from the linear sequence.

This proposal — the **diagram loop**:

The compiler (`api/notation/compiler.py`) parses the same expression into a typed graph:

```
NoeticCluster
├── StateInstance{noetic=4, domain=E, drive=F2, register=E}  ──┐
├── StateInstance{noetic=4, domain=E, drive=F2, register=f}  ──┤── IntegrationEdge(×)
├── StateInstance{noetic=4, domain=E, drive=F2, register=A}  ──┘
└── EmergentResult{omega_label=attunement, noetic=4, domain=E}
```

(Per the diagram export feature shipped 2026-04-26 — `NoeticCluster`, `StateSet`, `RelationCluster`, `Tuple`, `Coordinate`, `Product`, `CoverOf`, `PartitionOf`.)

A new **graph encoder** consumes this typed graph directly. The graph encoding is fused with the text-encoder output via cross-attention. Predictions are made from the joint representation.

## 2. Architectural finding (why this is structurally cleaner)

In the linear loop, the model has to **re-derive the structure** from the token sequence on every forward pass. That's fine for short expressions; it's wasted capacity for compound ones (e.g., a v76_production recipe with 5 prerequisite states + a leakage term + a target). Token-order parsing is fragile and surface-form-sensitive — exactly the property we're trying to fight.

In the diagram loop, the structure is **input directly as adjacency**. The model doesn't have to learn to parse `×`-as-integration from token co-occurrence; it sees an `IntegrationEdge` between three nodes. The token-order surface fragility that motivates the whole self-reference idea doesn't even apply to the graph encoder.

This matters because:
- The boolean heads (turn_type, authority, has_omega, etc.) are already 96-100% paraphrase-consistent — the model doesn't need help on those.
- The content heads (noetic 71.5%, domain 77.4%, drive 79.4%, registers 79.1%) are exactly the heads that need richer structural signal.
- The graph form gives the content heads what they need: explicit structural context for "what kind of state this is in relation to its neighbors."

## 3. Loss / data finding (the input gap PR #4 doesn't close)

PR #4's `[PRIOR]` block puts the canonical prediction in the input but doesn't change the input *modality*. The signal arrives through the same structured-token pipe that already exists. If that pipe was the bottleneck, more of it doesn't help.

The diagram loop adds a second input modality. The training data shape changes:

```
{
  "user_prompt": "...",
  "cas_expression": "(^4^E_{F2}|E × ^4^E_{F2}|f × ^4^E_{F2}|A) = ^4^E|Ω_attunement",
  "prior_cas_state": "...",          # PR #4's linear form
  "prior_diagram": {                  # NEW: typed-graph form
    "nodes": [...],
    "edges": [...],
    "node_features": {...}
  }
}
```

The compiler already produces these typed graphs as part of validation. The data is essentially free; the model side is the work.

## 4. Proposed lever — Graph Encoder with Cross-Attention Fusion

### 4.1 Architecture

Add three components to `cas-native/model/`:

1. **`graph_encoder.py`** — small graph attention network (GAT, 2-3 layers, hidden 64) that consumes a typed graph (node features = CAS-axis one-hots + node-type embedding; edge features = edge-type embedding for `co-presence` / `integration` / `rpm-dependency` / `cluster-membership` / etc.). Outputs a per-graph fixed-size representation (mean-pool over nodes).

2. **`graph_text_fusion.py`** — cross-attention layer. Text-encoder hidden states attend over graph-encoder node embeddings. Output: text hidden states enriched with graph context.

3. **Modify `structured_token_embedding.py` / `structured_prediction.py`** — accept an optional `graph_encoding` arg. When present, fuse via 4.1.2 before the prediction head.

### 4.2 Training shape

Two-pass training, same shape as PR #4:

1. Pass 1 (canonical): forward without `prior_diagram` → predict canonical CAS expression.
2. Pass 2 (paraphrase): compile pass-1's prediction into a graph → forward paraphrase prompt + `prior_diagram` → predict (should match canonical).

Loss: existing supervised loss + optional invariance regularizer (could compose with PR #3's KL-on-content-heads).

### 4.3 Inference shape

Optional at inference: when the user's query has prior context (e.g., a previous turn in a conversation), pass that prior as a diagram. When there's no prior, the diagram input is null and the model falls back to text-only.

## 5. Implementation diff (sketch)

| File | Action | Approximate cost |
|---|---|---:|
| `cas-native/model/graph_encoder.py` | NEW | ~200 lines |
| `cas-native/model/graph_text_fusion.py` | NEW | ~150 lines |
| `cas-native/model/structured_token_embedding.py` | MODIFY (optional graph input) | ~50 lines diff |
| `cas-native/training/diagram_serialization.py` | NEW (compiler graph → encoder input) | ~100 lines |
| `cas-native/training/diagram_loop_augmentation.py` | NEW (training-pair construction) | ~80 lines |
| `cas-native/training/train_structured_prediction.py` | MODIFY (`--diagram-loop-pairs K` flag, dual-pass loss) | ~80 lines diff |
| `cas-native/training/evaluate_diagram_loop_invariance.py` | NEW (eval harness) | ~300 lines |
| `cas-native/tests/` | NEW tests for each | ~400 lines |

Total: ~1300-1500 net lines. Roughly 2-3× PR #4's footprint. Estimated 3-6 weeks of focused dev to implement and validate.

## 6. A/B test plan

Holding everything else constant against the K=9 retrain (commit `fe7d389`):

1. **Baseline** — K=9 result (whatever it lands at when training completes).
2. **PR #4 retrain** — K=9 + `--self-conditioning-pairs N`. If lift is solid (paraphrase exact rises materially above 46.9%), validates the self-reference principle.
3. **Diagram-loop retrain (this proposal)** — K=9 + `--diagram-loop-pairs N`. Compare against #2.

Three outcomes worth distinguishing:
- **Diagram > Linear**: graph form provides structural signal the linear form can't, paper-worthy on its own.
- **Diagram ≈ Linear**: linear form was sufficient; ship PR #4, defer the graph encoder, redirect dev hours.
- **Diagram < Linear**: graph encoder is overfit to training graph distributions or fusion layer is wrong; investigate before retrying.

## 7. Why this lever, when

**Why a separate proposal from PR #4:** the implementation is large enough (1300-1500 lines, new model component) that bundling it with PR #4 would have made PR #4 unreviewable. The decoupling lets PR #4 ship and answer the cheap question first (does self-reference help at all?), and lets this proposal answer the harder question (does *graph-form* self-reference help more than linear?).

**When to build:** after K=9 + PR #4 retrain results land. Specifically:
- If PR #4's linear lever lifts paraphrase exact by ≥10 pp, build this. The principle is validated; we want to know the ceiling.
- If PR #4 lifts paraphrase exact by <5 pp, redirect — the issue is somewhere else (maybe content-axis architecture per PR #3) and this proposal is premature.
- If PR #4 lifts by 5-10 pp, judgment call. Probably worth building because this is the architecturally cleaner version regardless.

## 8. Composability with sibling proposals

| Sibling | Relationship |
|---|---|
| **PR #2 (bare-slot K=9)** | Composes. K=9 is data; this is architecture. K=9 retrain provides the ground from which to layer this lever. |
| **PR #3 (KL-on-content-heads)** | Composes. KL regularizer pushes content-head outputs toward consistency; graph encoder gives the model better input to *be* consistent on. They reinforce each other. |
| **PR #4 (linear self-reference loop)** | **Direct predecessor.** This proposal supersedes PR #4 only if the diagram form is empirically better; otherwise PR #4 stays as the production lever and this proposal is shelved. |

## 9. Risks and fallbacks

- **Risk: graph encoder is heavy for the gain.** If model size growth is significant and gain is marginal, the linear form (PR #4) is preferred. Mitigation: build the smallest viable graph encoder (2 GAT layers, hidden 64) and grow only if gain warrants.
- **Risk: training graphs come from the model's own predictions which may be wrong.** Same risk PR #4 has. The architecture should learn to weight `[PRIOR]` info partially when it conflicts with strong text signal. Mitigation: dropout the prior on a fraction of training samples so the model doesn't become prior-dependent.
- **Risk: paper-worthy contribution claim doesn't hold.** If the linear form already captures most of the diagram benefit, the graph encoder is a wash. Mitigation: this proposal explicitly defers to the linear-vs-graph A/B before claiming superiority.
- **Fallback if this lever flat-lines:** investigate at the architecture level — content heads may need separate sub-bottlenecks before the graph form can help (a deeper architectural change beyond this proposal).

## 10. Why this matters strategically

PR #4 is a working solution to the immediate problem (paraphrase invariance). This proposal is the **architecturally honest version** of the same idea. The "Attention is All You Need" tier framing the user has explored only really applies to the diagram-loop variant — the linear form is incremental, the graph form is an actual modality choice with a real research story attached. Specifically:

- The graph form gives a clean abstract for the architecture paper (Paper C in the four-paper sequencing): *"CAS Transformer: cross-modal text-and-graph encoder for ontology-constrained structured prediction with explicit self-reference."*
- The diagram-output-as-input loop is the proof-of-concept for the broader claim that CAS-Native AI is auditable by construction — every prediction emits a diagram that can be fed back as oversight signal.
- Validates that CAS-as-cognitive-trace isn't just architectural framing but a working substrate for self-monitoring and self-correction.

PR #4 doesn't carry this weight; it's a tactical fix. This proposal does, *if* the empirical envelope supports it.

## 11. Open questions for the reviewer

1. Graph encoder architecture: GAT vs Graph Transformer vs message-passing GNN? Default GAT for simplicity; want to revisit if results disappoint.
2. Edge-type vocabulary: should `co-presence` (PR #4-style `+`), `integration` (`×`), `RPM-dependency`, `cluster-membership`, `pullback` etc. each be distinct edge types, or fewer general types? Probably more types is better; needs to be confirmed against compiler-emitted graph cardinality on the training corpus.
3. Fusion direction: text attends over graph (proposed), or graph attends over text, or both directions? Text-attends-over-graph is the cheaper default; bidirectional would be a follow-up if needed.
4. Should `prior_diagram` always be the model's own prediction, or can it be ground-truth at training time only (with student-teacher schedule)? PR #4 uses model-prediction-only at training time too; this proposal mirrors that for consistency.
5. CPU-only inference for the eval harness, or allow CUDA? PR #4's eval is CPU-only by constraint; this proposal could match or relax depending on graph encoder size.

## 12. What this proposal does NOT include

- No retrain. Implementation + tests + PR only.
- No claim of empirical superiority over PR #4. Empirical claim is contingent on the A/B test landing.
- No commitment to building before PR #4's retrain validates the principle.
- No new Noetic / Domain / Drive / Register values. Cardinalities (10/4/7/4) remain canonical.
- No modification to existing tests or evals; this is purely additive.

## 13. Filing under the four-paper sequencing

This lever belongs to **Paper C** (the full CAS Transformer architecture paper). Specifically, it provides:

- The architectural insight ("graph-encoder fused with text-encoder for self-reference")
- The empirical envelope (linear-vs-graph A/B on the same task)
- The auditability claim grounded in a working mechanism (prediction → compile → diagram → re-encode → predict)

If the A/B lands cleanly in favor of the graph form, this is the headline result for Paper C. If not, the linear form (PR #4) carries the practical story and Paper C focuses elsewhere.
