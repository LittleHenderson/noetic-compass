# Content-Axis Invariance Lever Proposal

Status: proposal — not yet implemented.
Anchored to: commit `3232f05` (clean-eval rescore of checkpoint `d99810a`).
Run: `cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/`.

## TL;DR

The four content heads (Noetic, Domain, Drive, Register) collapse under paraphrase even though the boolean/categorical heads do not. The model has the right answer in canonical form and **loses it under paraphrase 95-98% of the time** — pure invariance failure, not a knowledge gap. Current training pipeline contains paraphrase records but never aligns them with their canonical counterpart in the loss. Proposal: add a content-head paraphrase-invariance auxiliary loss (KL between canonical and paraphrase content-head softmax distributions), weighted per head by inverse-current-consistency, applied only to content heads.

---

## 1. The diagnosis (what's actually broken)

### 1.1 Asymmetry: the model knows the answer

For each pair `(canonical_pred, paraphrase_pred)` where the two disagree, the table below counts how often each side matches the ground truth:

| Head | Disagreements (of 3000) | Canonical right | Paraphrase right | Both wrong, different | Asymmetry (% canon right) |
|---|---:|---:|---:|---:|---:|
| noetic | 854 | 822 | 11 | 21 | **96.3%** |
| domain | 677 | 667 | 4 | 6 | **98.5%** |
| drive | 618 | 600 | 9 | 9 | **97.1%** |
| registers | 627 | 599 | 8 | 20 | **95.5%** |

Read the bold column: when canonical and paraphrase disagree, the canonical is right ~95-98% of the time. The model HAS the right content prediction; the paraphrase pushes the content-head logits across decision boundaries. This is invariance failure, not a knowledge gap.

### 1.2 Bucket concentration

Disagreements concentrate on `v75_register` and `v74_baseline` (and `meta_logic` for noetic):

| Head | v75_register | v74_baseline | meta_logic | v76_production | v77_omega | v77_rule_four |
|---|---:|---:|---:|---:|---:|---:|
| noetic | 334 | 307 | 164 | 40 | 5 | 4 |
| domain | 303 | 260 | 59 | 28 | 24 | 3 |
| drive | 250 | 203 | 63 | 12 | 71 | 19 |
| registers | 255 | 293 | 62 | 0 | 5 | 12 |

This matches the bucket-level paraphrase residual finding (sibling PR #2). Both diagnoses point at `v74_baseline` and `v75_register` as the buckets where the surface signal is weakest.

### 1.3 Drift patterns

Top canonical → paraphrase confusions per head:

- **noetic:** `0→5 (65)`, `6→5 (59)`, `7→0 (55)` — paraphrase predictions collapse toward `^5` (Female / accumulated experience) and `^0` (Idea), the most common Noetics in training.
- **domain:** `C→P (142)`, `O→C (96)`, `E→P (84)` — drift up the precedence hierarchy (`P ≻ C ≻ E ≻ O`), toward the "default" domain.
- **drive:** `F1→F5 (125)`, `F1→F6 (81)`, `F3→F5 (77)` — drift across drive inversion pairs.
- **registers:** `()→('E',) (195)`, `()→('A',) (161)`, `('E',)→('A','E') (57)` — model invents registers under paraphrase when canonical has none.

These are systematic prior-collapse patterns. Under paraphrase noise, the content heads fall back on training-distribution priors instead of the per-record signal.

---

## 2. Architectural finding (why the boolean/content split exists)

`cas-native/model/structured_prediction.py:111-145`. All 12 heads share a single 64-dim bottleneck:

```python
self.backbone = nn.Sequential(
    nn.Linear(d_model, bottleneck_dim),  # 128 -> 64
    nn.GELU(),
    nn.LayerNorm(bottleneck_dim),
)
# All 12 heads (boolean and content) project from the same 64-dim z.
```

The boolean heads sit at ~96-100% paraphrase consistency on this same `z`. So the bottleneck representation IS mostly invariant under paraphrase — this is not a "the encoder maps paraphrases to different z" problem.

The split is downstream of `z`: content heads (Noetic 10-way, Drive 7-way, Register multi-label, Domain 4-way) need finer-grained linear discrimination than boolean heads (2-3 way). The same noise in `z` that boolean heads tolerate pushes content-head logits across decision boundaries.

That makes the right intervention point the content-head logits, not the encoder.

---

## 3. Loss finding (why the existing K=3 augmentation isn't enough)

`cas-native/model/structured_prediction.py:240-275`. `structured_prediction_loss`:

```python
loss = sum_h F.cross_entropy(outputs[h_logits], targets[h])
       + lambda_register * BCE(register_logits, registers_target)
       + lambda_meta_relation * BCE(meta_relation_logits, meta_relations_target)
```

All heads weighted equally. No invariance term. No paraphrase-pair awareness.

`cas-native/training/train_structured_prediction.py:732-742` (paraphrase augmentation entry point):

```python
if paraphrase_augment_train > 0:
    train_records = expand_with_paraphrases(
        train_records, variants_per_record=paraphrase_augment_train
    )
```

`expand_with_paraphrases` adds paraphrases as **independent records** in the training pool. They are shuffled together with canonicals and the loss treats each as a standalone supervised target. The structural relationship "this paraphrase is a surface variant of THAT canonical" is **never expressed in the batch shape and never expressed in the loss**.

So with `--paraphrase-augment-train 3`, the model sees 4× the supervised signal per record but with NO invariance constraint. It can — and does — produce different content-head distributions on the canonical vs the paraphrase, because nothing in the loss penalizes that.

---

## 4. Proposed lever — Content-Head Paraphrase Invariance Auxiliary Loss

One added loss term, applied **only to the four content heads**, on **canonical-paraphrase pairs** that already exist in the training pipeline.

### 4.1 Loss formula

For a batch with paired canonical record `c` and its paraphrase variants `p_1, ..., p_K`:

```
L_total = L_supervised(c, p_1, ..., p_K)             # existing per-record CE/BCE, unchanged
        + λ_inv * L_inv

L_inv = (1 / K) * sum_{k=1..K} sum_{h ∈ CONTENT_HEADS} w_h * KL(P_h(c) || P_h(p_k))

CONTENT_HEADS = {noetic, domain, drive, registers}

P_h(x) = softmax(content_head_h(z_x))   for noetic, domain, drive
P_h(x) = sigmoid(register_logits(z_x))  for registers (per-label Bernoulli, use binary KL)
```

KL not L2: KL is scale-invariant on probability outputs; L2 on logits creates a magnitude pull that's independent of how confident the model is.

### 4.2 Per-head weighting (inverse current consistency)

Weight content heads by how much help they need:

| Head | Current consistency | w_h |
|---|---:|---:|
| noetic | 71.5% | 4.0 |
| domain | 77.4% | 3.0 |
| registers | 79.1% | 2.5 |
| drive | 79.4% | 2.5 |

(Heuristic: w_h = 1 / (1 - consistency_h), normalized so the worst head dominates.)

### 4.3 Why content-only

Boolean heads sit at 96-100% consistency. Adding invariance pressure on them costs gradient capacity for no benefit and risks underfitting the genuine canonical → paraphrase variation that should be allowed (e.g., the model SHOULD adapt confidence for ambiguous prompts).

### 4.4 Hyperparameters

- `λ_inv ∈ {0.05, 0.1, 0.3, 1.0}` — sweep, start at 0.1.
- Per-head weights as above; expose as a CLI override.
- Apply only when `paraphrase_augment_train > 0` (otherwise the term is zero by construction).

---

## 5. Implementation diff

Three file changes, additive only.

### 5.1 `cas-native/model/structured_prediction.py`

Add `content_axis_invariance_loss()` next to `structured_prediction_loss()`:

```python
CONTENT_HEAD_KEYS = ("noetic_logits", "domain_logits", "drive_logits", "register_logits")

DEFAULT_CONTENT_WEIGHTS = {
    "noetic_logits":   4.0,
    "domain_logits":   3.0,
    "drive_logits":    2.5,
    "register_logits": 2.5,
}

def content_axis_invariance_loss(
    canonical_outputs: dict[str, torch.Tensor],   # logits at canonical z
    paraphrase_outputs: dict[str, torch.Tensor],  # logits at paraphrase z (same batch order)
    *,
    weights: dict[str, float] | None = None,
) -> torch.Tensor:
    """KL(canonical || paraphrase) on content heads only."""
    weights = weights or DEFAULT_CONTENT_WEIGHTS
    loss = torch.tensor(0.0, device=next(iter(canonical_outputs.values())).device)
    for key in CONTENT_HEAD_KEYS:
        if key not in canonical_outputs or key not in paraphrase_outputs:
            continue
        if key == "register_logits":
            # multi-label: sum of per-label binary KL
            p_c = torch.sigmoid(canonical_outputs[key])
            p_p = torch.sigmoid(paraphrase_outputs[key])
            kl = (p_c * (torch.log(p_c.clamp_min(1e-8)) - torch.log(p_p.clamp_min(1e-8)))
                  + (1 - p_c) * (torch.log((1 - p_c).clamp_min(1e-8)) - torch.log((1 - p_p).clamp_min(1e-8)))).sum(dim=-1).mean()
        else:
            log_p_c = F.log_softmax(canonical_outputs[key], dim=-1)
            p_c = log_p_c.exp()
            log_p_p = F.log_softmax(paraphrase_outputs[key], dim=-1)
            kl = (p_c * (log_p_c - log_p_p)).sum(dim=-1).mean()
        loss = loss + weights[key] * kl
    return loss
```

### 5.2 `cas-native/training/train_structured_prediction.py`

The current loop iterates `train_records` (canonicals + their paraphrase expansions, mixed). The change:
- Build a `pair_index: dict[base_id, list[paraphrase_record_idx]]` once at training start, so each batch can be augmented with the canonical-paraphrase pair structure.
- For each batch, compute the existing supervised loss as today.
- Additionally, sample `B_pair` canonical records that have at least one paraphrase variant in the train pool, forward both, and compute `content_axis_invariance_loss` between them.
- Add `--paraphrase-invariance-weight` CLI flag (default 0.0; setting >0 activates this lever).

Pseudocode for the addition to the training step:
```python
sup_loss = structured_prediction_loss(outputs, targets)
inv_loss = torch.tensor(0.0, device=dev)
if args.paraphrase_invariance_weight > 0 and pair_indices:
    canon_batch, para_batch = sample_canonical_paraphrase_pairs(...)
    canon_out = model(canon_batch)
    para_out  = model(para_batch)
    inv_loss = content_axis_invariance_loss(canon_out, para_out)
loss = sup_loss + args.paraphrase_invariance_weight * inv_loss
loss.backward()
```

This adds one extra forward pass per training step proportional to `B_pair`. Cost estimate: with `B_pair = 32` (small fraction of `--batch-size 128`), training step time grows by ~25%. Still cheap on the A6000.

### 5.3 `cas-native/training/structured_prediction_ingest.py`

Add a helper `build_canonical_paraphrase_pair_index(records)` that:
- Reads `record["base_id"]` (already populated by `expand_with_paraphrases`)
- Returns a dict mapping each canonical base_id to a list of paraphrase record indices in the train pool.
- Also returns the indices of canonicals that have at least one paraphrase variant.

This is pure index bookkeeping — no record mutation.

---

## 6. A/B test plan

Holding everything else constant against `d99810a` (commit `3232f05`):

1. **Baseline**: rerun the same hparams as `runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045` — same training corpus, same `--paraphrase-augment-train 3`, same seed (42), same 20 epochs.
2. **Treatment**: add `--paraphrase-invariance-weight 0.1`. No other change.
3. Compare on the relabeled held-out eval (`level3_recoverable_eval_1000_v77_relabeled.jsonl`) and the same paraphrase-eval harness.

### 6.1 Expected effect (priors, not promises)

| Metric | Baseline | Treatment (expected) |
|---|---:|---:|
| Canonical all-heads exact | 93.2% | 92.5%–94.0% (regularization may help; risk of slight decrease) |
| Paraphrase all-heads exact | 46.9% | **52%–56%** |
| noetic consistency | 71.5% | **80%–85%** |
| domain consistency | 77.4% | 84%–87% |
| drive consistency | 79.4% | 84%–87% |
| register consistency | 79.1% | 83%–86% |
| Boolean head consistency | 96-100% | unchanged |

The treatment closes the bigger half of the boolean/content gap — not the entire gap (some content variation IS legitimate, e.g., when paraphrase is genuinely ambiguous).

### 6.2 Sweep

If the `λ_inv = 0.1` run is a clear win, sweep `λ_inv ∈ {0.05, 0.1, 0.3, 1.0}` to identify the knee. If it's flat or negative, reconsider — the failure mode might not be invariance-loss-shaped (see §8 alternatives).

---

## 7. Why this lever, not the alternatives

### 7.1 vs Contrastive paraphrase batch construction

Contrastive objectives (e.g., InfoNCE) require negative samples and a temperature term. They're more powerful but more brittle to tune. KL between canonical and paraphrase distributions is a strict subset of contrastive learning — a positive-only invariance pressure. Cleaner first lever.

### 7.2 vs Token-level provenance signal

`cas-native/model/structured_token_embedding.py:62-66` ALREADY has `source_embedding` distinguishing LEXICON / CAS_NOTATION / LEARNED / FALLBACK token sources. The provenance signal is in the embedding stream. The boolean head at ~100% suggests the model is using it where it can. Adding more provenance plumbing doesn't address the head-level decision boundary problem.

### 7.3 vs Increasing K (more paraphrases per canonical)

PR #2 (sibling proposal) recommends raising `--paraphrase-augment-train 3 → 9` and adding a bare-slot template. That addresses the bucket-level coverage gap. This proposal is complementary: even at K=9 with no invariance constraint, the model could still produce inconsistent content predictions across surface forms. Both levers should compose.

If only one can be tried first, do PR #2's first (cheaper, more direct), then this one on top.

---

## 8. Risks and fallbacks

- **Risk: λ_inv too high → underfit.** Mitigation: small starting value, sweep, monitor canonical exact (must not drop more than 1 pp).
- **Risk: invariance forces uniform distributions for genuinely ambiguous paraphrases.** Mitigation: KL not L2 (KL has natural floor when the supervised loss already matches); also content-head-only.
- **Risk: extra forward pass costs more than the lift is worth.** Mitigation: B_pair is tunable; can also gate the inv loss to fire every Nth step.
- **Fallback if this lever flat-lines:** the failure mode is more architectural — content heads on a 64-dim bottleneck may genuinely lack capacity. Next lever would be widening the content-head sub-bottlenecks (separate `nn.Sequential` per content head with extra width) or adding a second projection layer between `z` and the content heads.

---

## 9. Composability with sibling proposal (PR #2)

PR #2 (`paraphrase residual proposal: v74_baseline + meta_logic`) addresses the **bucket-level coverage gap** by raising K and adding a bare-slot training template.

This proposal addresses the **per-head invariance gap** with a loss-level intervention.

The two are orthogonal and should compose:
- PR #2 changes WHICH paraphrases the model sees (more variants, more bare-slot framing).
- This proposal changes HOW the model is rewarded for handling them (explicit invariance pressure on content heads).

Recommended ordering: implement PR #2 first; if v74_baseline + meta_logic paraphrase scores rise, evaluate the per-head consistency on the new checkpoint; if Noetic / Domain / Drive / Register heads still sit below 90%, layer this lever on top.

---

## 10. Open questions for the reviewer

1. Per-head weights `w_noetic = 4.0` etc. — agree with inverse-consistency heuristic, or prefer flat weighting and let `λ_inv` carry the signal?
2. KL direction: `KL(canon || para)` (treat canon as anchor) or symmetric Jensen-Shannon? Prior runs in similar lit prefer the asymmetric form when one side is the "trusted" prediction.
3. Pair-batch size `B_pair`: bound by training-step budget, or scale with `--batch-size`?
4. Activation criterion: only fire `L_inv` after epoch N (e.g., N=2) so the supervised loss has time to ground the heads first?
