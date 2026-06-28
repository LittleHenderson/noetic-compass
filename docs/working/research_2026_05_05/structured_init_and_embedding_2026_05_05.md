# Structured Init + Embedding Redesign for CAS-Native — Research Note

**Author:** Opus R&D Specialist (slice: structured weight init + embedding layer)
**Date:** 2026-05-05
**Status:** Speculative research note. Side project. **No production code touched, no commits.** The v1 retrain on the pod (PID 14170) is untouched.
**Reading time:** ~12 min.

---

## 1. Goal

The CAS-Native model today spends a lot of parameters and a lot of training steps learning things the framework already knows for free. Two specific places:

- **Random weight init.** Every weight starts as a small random number (PyTorch default Kaiming/uniform). The model has no prior structure encoded — Domain precedence (P ≻ C ≻ E ≻ O), Noetic involution pairs (^2↔^3, ^5↔^6, ^8↔^9), Drive inversion pairs (F1↔F7 etc.), the open-simplex constraint — must all be discovered from gradient noise even though they are already authoritatively specified in `CLAUDE.md` (the four Critical Mathematical Corrections) and the Noetic Topos paper.
- **Standard embedding layer.** `StructuredTokenEmbedding` (`cas-native/model/structured_token_embedding.py:22-98`) is a `vocab_size × d_model` lookup. With `vocab_size ≈ 32 000` and `d_model = 512` (`cas_native_model.py:62-64`), the surface embedding alone is 16.4 M parameters. Each token's position in this 512-dim space starts as Gaussian noise, including the 14 reserved CAS notation tokens (`Λ Ω Θ → · NoeticCluster ...` per `HONEST_STATUS.md:86`) whose exact role in the framework is fully specified.

The question: can the CAS / TKS conceptual machinery REPLACE these with structured equivalents that are smaller AND smarter — and, per the user's standing rule (`memory: feedback_traceability_is_the_whole_purpose`), more traceable?

The hypothesis is yes — at least for the CAS-notation portion of the vocab and for select layers downstream of the embedding. This note proposes three concrete redesigns plus one speculative dimensional alternative, each with parameter counts, falsifiable predictions, and a code sketch.

---

## 2. Current architecture (concrete)

### Surface embedding

```
cas-native/model/structured_token_embedding.py:52-56
    self.surface_embedding = nn.Embedding(
        vocab_size,           # ~32_000
        d_model,              # 512
        padding_idx=padding_idx,
    )
```

Parameter count: **32 000 × 512 = 16 384 000**, drawn from `N(0, 1)` by default (PyTorch `nn.Embedding` is `kaiming_uniform_`-style). All tokens — `<pad>`, `<bos>`, every BPE wordpiece, AND every CAS literal like `^3`, `^P`, `Θ`, `→` — get the same random init.

### Side channels (CAS signature is explicit but its projection is random)

```
cas-native/model/structured_token_embedding.py:57-65
    signature_dim = NOETIC_AXIS_LEN(10) + DOMAIN_AXIS_LEN(4)
                  + DRIVE_AXIS_LEN(7)   + REGISTER_AXIS_LEN(4) = 25
    self.signature_projection = Linear(25, h) -> GELU -> LN -> Linear(h, 512)
    self.confidence_projection = Linear(1, 512)
    self.source_embedding      = Embedding(5, 512)
    self.span_projection       = Linear(2, 512)
    self.fusion_gate           = Linear(1024, 512)
```

So the CAS axis identity is already a structured 25-vector per token (from `structured_token.py:35-38`), but it gets mashed through a random-init MLP into the same 512-dim free space as surface words. The framework's structure is in the *input features* but is *not* preserved in the embedded representation.

### Cognitive state head

```
cas-native/model/embedding.py:50-97 (CognitiveStateEmbedding)
    Linear(512, 256) -> GELU -> Linear(256, 40) -> softmax + eps + renormalize
```

This already projects onto Δ°₃₉ (Correction 4). But the projection itself is random-init: the model has to learn from scratch which 512-dim direction means "principled positive." The 40 output dimensions are *named* (P0..O9) but the matrix that produces them is *anonymous*.

### Domain descent

`domain_descent.py:27-36` builds a hard-coded P→C→E→O mask at runtime, but the Q/K/V projections that operate against that mask are random init.

### Register FiLM

`register_film.py:96-368` (RegisterLatent) is the one place where structured init is already used: `W_gamma_*` and `W_beta_*` are zero-initialized so step-0 register FiLM is identity. This is a precedent for what the rest of this note proposes generalizing.

**Bottom line.** Structure is everywhere in the spec. In the model, structure is a runtime mask, a named output dimension, and one zero-init layer. Everything else starts as noise.

---

## 3. Proposed redesigns

### Proposal A — CAS-state-anchored initialization (keep architecture, change init)

The cheapest, lowest-risk move. Don't change the architecture; change how each weight matrix is initialized so the framework's structural invariants hold at step 0 instead of having to be learned.

**A.1 Cognitive-state head: domain-block init.**
The final `Linear(256, 40)` of `CognitiveStateEmbedding` produces logits over the 40 named states P0..O9. Initialize its bias as a domain-precedence prior:

```
b[P0..P9]   =  +α      (Principled most-active-by-default; α ≈ 0.5)
b[C0..C9]   =  +α/3
b[E0..E9]   =  -α/3
b[O0..O9]   =  -α
```

After softmax this gives a non-uniform prior that already respects P ≻ C ≻ E ≻ O. Random init starts at uniform 1/40; this starts at the spec's prior. Cost: 0 extra parameters.

**A.2 Involution-pair weight tying.**
The 10 Noetics form three involution pairs: ^2↔^3, ^5↔^6, ^8↔^9, with ^0, ^1, ^4, ^7 self-dual (`CLAUDE.md` Structural Invariants). For any matrix `W` whose output rows index Noetics, initialize so paired rows are negatives of each other:

```
W[3, :] = -W[2, :]   at init
W[6, :] = -W[5, :]
W[9, :] = -W[8, :]
W[0/1/4/7, :] = symmetric init
```

This encodes "Negative is the inverse direction of Positive in feature space." It's a *prior*, not a constraint — gradients can drift the rows apart later. Same trick applies to Drive inversion pairs (F1↔F7, F2↔F6, F3↔F5, F4 self-dual; `CLAUDE.md`).

**A.3 Domain-precedence-respecting Q/K init in `DomainDescentAttention`.**
The mask in `domain_descent.py:27-36` already enforces precedence at runtime. The Q/K projections (`q_proj`, `k_proj`) can be initialized with a small bias toward attending up the precedence ladder, e.g. by giving the first 10 (P) rows a slightly larger init scale than the last 10 (O). Speculative magnitude: 1.5× / 1.0× / 0.7× / 0.5× across P/C/E/O. The mask still does the hard-stop work; this just biases magnitudes inside the allowed region.

**Parameter delta:** zero (init is free). All numbers above are step-0 only; gradients are unconstrained.

---

### Proposal B — Simplex-valued embeddings (replace `nn.Embedding`)

Today the embedding is `R^512` and a separate head projects later down to Δ°₃₉. Proposal B inverts the order: each token's embedding **lives directly on Δ°₃₉**, and downstream layers consume that simplex distribution as their input.

Concretely, replace `nn.Embedding(vocab_size, d_model)` with a parameter table of unconstrained `R^40` logits per token:

```
self.simplex_logits = nn.Parameter(torch.zeros(vocab_size, 40))

def embed(token_ids):
    logits = self.simplex_logits[token_ids]        # (B, S, 40)
    return softmax(logits) + eps  -> renormalize    # on Δ°_39
```

**Parameter count:**
- Current: `32 000 × 512 = 16.4 M`.
- Proposal B (40-dim only): `32 000 × 40 = 1.28 M`. **~12.8× smaller.**

If downstream layers still want `d_model = 512`, you re-expand once via a single shared `Linear(40, 512)` for `40 × 512 + 512 = 20 992` extra params. Total: `1.28 M + 0.02 M ≈ 1.30 M`. Still ~12.6× smaller.

**Why this is "smarter," not just smaller.**
- Every token is described by *named* coordinates: dim 5 of token X's embedding *literally is* "how much P5 (Principled Female) does this token activate." That ARRAY is its trace (per `memory: feedback_object_traceability_required`).
- Constraint is enforced structurally (softmax + eps), not learned. The Correction 4 invariant — pk > 0, Σpk = 1 — never has to be discovered.
- Inversion-pair priors (A.2) become trivial to express: at init, paired tokens like `^2`'s reserved CAS literal and `^3`'s reserved CAS literal can be initialized with mass on opposite halves of the simplex. Citation: `CLAUDE.md` Structural Invariants, Correction 4.

**Risk.** A 40-dim simplex may be too narrow as a *full* representation — surface words like "anyway" or "the" don't have a natural CAS state distribution. Mitigations: (1) keep two parallel embedding streams, structured 40-dim for the CAS-notation slice of vocab, unconstrained for the natural-language slice; or (2) augment Δ°₃₉ with a small "residual" `R^k` (k ≈ 24) channel that captures non-CAS surface meaning — total `32 000 × (40 + 24) = 2.05 M`, still ~8× smaller.

---

### Proposal C — Reserved-token anchoring (subset of A; the cheapest concrete win)

The 14 reserved CAS tokens (`HONEST_STATUS.md:86`: `Λ Ω Θ → · NoeticCluster StateSet RelationCluster CoverOf PartitionOf Product ∪ ∩ ∖`) plus the 8 reserved-vocab tokens (`vocabulary.py:37-46`: `<pad> <bos> <eos> <unk> <mask> <cas_literal> <lexicon_hit> <fallback_neutral>`) plus the operator literals (`^0..^9`, `^P/^C/^E/^O`, `F1..F7`, `|T/|A/|f/|E`) currently get random init like every other token. They shouldn't.

For each reserved token, write down a fixed structural target vector at init. Examples (under Proposal B's 40-dim simplex view):

| Token | Init target on Δ°₃₉ |
|---|---|
| `^3` (CAS literal) | mass 0.97 spread evenly on `{P3, C3, E3, O3}` (the four ^3 states), 0.03/36 on the rest to keep open simplex |
| `^P` (domain) | mass 0.97 spread on `{P0..P9}`, 0.03 on rest |
| `Θ` (recipe operator, v7.6) | uniform on the simplex (operator, not a state); near uniform with small lift on `{P0, C0, E0, O0}` (the ^0 Idea row, the operator-target slot) |
| `→` (recipe arrow) | uniform on simplex |
| `Λ` (leakage marker) | uniform on `{^3 row}` (lacunarity / wrong-product side) — **speculative** placement |
| `<pad>` | uniform (no signal) |

These are *initial conditions*. Gradients can move them. But the network starts knowing what the framework already specifies. Cost: zero new parameters, ~50 lines of init code, plus a unit test that walks the table.

The 14 reserved-CAS-token slice is small in count but huge in structural load: every CAS notation expression in the SDG corpus passes through these tokens. Anchoring them is high leverage per parameter touched.

**Citation chain:** `HONEST_STATUS.md:86` for the vocab14 list, `vocabulary.py:37-55` for the additional reserved vocabulary IDs, `register_film.py:96-203` for the precedent of zero-init structural anchoring (RegisterLatent's W_gamma/W_beta zero-init).

---

### Proposal D — 48-dim alternative to the 40-state space (speculative)

The "When Light and Consciousness Share the Same Number" paper (PDF pp. 1-6) makes a structural claim: TKS architecture is fundamentally **48-dimensional**, decomposed as **40 Elements + 7 Foundations + 1 A0 (Pure Desire / Keter)**. The Forbes 2025 quantum-photonics result lands on the same 48 via su(7) (48 = 7² − 1). The author honestly notes (PDF p. 4) that the 48s arise from different mathematical objects — TKS's 48 is an additive composite, su(7)'s 48 is a single irreducible Lie algebra — but the structural archetype "≈10 operators acting across ≈4 hierarchical levels with 7 motivational foundations and 1 source" is preserved.

Where this matters for the model: the current state space is the 40 Cognitive States (10 × 4). The 7 Drives (F1..F7) are tracked separately (e.g., as the 7-dim drive axis in `signature_dim`, `structured_token.py:37`) and the A0 Pure Desire is the head of the RPM chain (`CLAUDE.md`: `A0 → Dn → Wn → Pn → Outcome`). They are not in the same vector space.

**Speculative redesign D.** Replace Δ°₃₉ with a **Δ°₄₇** open simplex over the full 48-dim TKS architecture: `[P0..O9, F1..F7, A0]`. This unifies state and drive in a single distribution, and adds A0 as an explicit "pure capacity" dimension at the head of the RPM chain.

**Parameter count under Proposal B + D:** `32 000 × 48 = 1.54 M` (vs current 16.4 M; ~10.6× smaller; ~20% larger than B alone).

**What it might unlock.**
- RPM chain integrity becomes a property of the same vector that holds Cognitive State. A0 mass directly indexes "is the prerequisite chain even started?" — `CLAUDE.md` Correction 2.
- Drive inversion pairs (F1↔F7, F2↔F6, F3↔F5) live in the same simplex as Noetic involution pairs, making cross-axis inversion analysis a single matrix operation rather than two pipelines.
- The 48-dim alignment with the OAM photonics result is decorative for now — *do not* ship marketing copy claiming a quantum connection (per `CLAUDE.md` Authoritative Noetic Definitions and the PDF's own honest framing). The structural prediction is internal: a 48-dim state space with the additive decomposition (40, 7, 1) is more expressive than 40-dim alone, and it lines up with the existing RPM chain `A0 → Dn → Wn → Pn`.

**Risks.** The Noetic Topos paper formally fixes |I| = 40 (`peer_review/journal_submission/main.pdf` p. 2: "We fix a finite index set I with |I| = 40, together with a partition I = I_A ⊔ I_B ⊔ I_C ⊔ I_D"). The Fisher-Rao metric, the Grothendieck topology, and the sheaf topos Sh(Noetica, J_noe) are all defined on this 40-element site. Moving to 48 would require either (i) embedding the 40-state simplex inside a 48-dim simplex (the 7+1 extra dims as auxiliary, simplex constraint preserved) or (ii) a parallel formal write-up justifying |I| = 48. Option (i) is implementable today; option (ii) is a multi-month formal effort.

**Recommendation:** treat D as a research probe, not a near-term build. Implement only after Proposal B is empirically validated.

---

## 4. Parameter count comparison (concrete)

Defaults: `vocab_size = 32 000`, `d_model = 512`.

| Component | Today | Prop A (init only) | Prop B (40-dim) | Prop B + C | Prop B + D (48-dim) |
|---|---:|---:|---:|---:|---:|
| Surface embedding | 16 384 000 | 16 384 000 | 1 280 000 | 1 280 000 | 1 536 000 |
| 40→512 re-expand (shared) | — | — | 20 992 | 20 992 | 25 088 (48→512) |
| Cognitive-state head | 131 968 | 131 968 | (folded in) | (folded in) | (folded in) |
| Reserved-token anchor table | — | — | — | 0 (init only) | 0 (init only) |
| **Embedding-stack total** | **~16.5 M** | **~16.5 M** | **~1.30 M** | **~1.30 M** | **~1.56 M** |
| **Reduction vs today** | — | 0% | **~92%** | **~92%** | **~91%** |

Caveat: total model parameter count includes the 6-layer transformer stack which dominates (~30 M+ at `d_model = 512`). The embedding redesign reduces *embedding-layer* parameters by ~92%, which is roughly a **15 M parameter savings** out of a typical ~50 M model — meaningful but not the bulk of the model. The bigger win is qualitative: traceability, structural priors, and faster convergence.

---

## 5. Capability claims (what structured init unlocks)

Each claim is paired with the citation supporting it:

1. **Zero-shot Noetic involution.** With Proposal A.2 (paired rows initialized as negatives), at step 0 the model already produces inverse-direction logits for `^3` queries vs `^2` queries on the cognitive-state head. Random init has no such property. Citation: `CLAUDE.md` Structural Invariants ("Involution pairs: CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9").

2. **Faster convergence on small data.** Structured init narrows the prior over which the optimizer must search. This is most valuable when training data is scarce — exactly the regime CAS-Native operates in (162K records, `HONEST_STATUS.md:23`). Speculative magnitude: ~30-50% fewer steps to reach the same canonical-exact rate. Falsifiable (see §6).

3. **Interpretable latent space (the trace).** Under Proposal B, every embedded token IS a 40- (or 48-) dim CAS distribution. Reading the model's mind on token X reduces to printing `simplex_logits[X].softmax()` — no probe, no SAE, no attribution machinery. This is the load-bearing user requirement: `memory: feedback_traceability_is_the_whole_purpose` ("every model output must walk back to its origin").

4. **Open-simplex constraint enforced structurally.** No need for a regularizer or projection step deep in training; Correction 4 holds at every step from step 0 by construction. Citation: `CLAUDE.md` Correction 4; `embedding.py:70-86` for the current softmax+eps+renormalize pattern.

5. **Reserved CAS tokens are no longer black boxes.** Under Proposal C, every reserved token's role in the framework is encoded at init in the same notation a human reads. `Θ` IS the recipe operator (v7.6); after init, the model treats it as such on the very first step. Citation: `CLAUDE.md` Production Semantics — CAS v7.6 extension; `HONEST_STATUS.md:86`.

---

## 6. Falsifiable predictions

Each prediction is a concrete experiment that distinguishes structured init from the random-init baseline. None requires the live pod or production retrain.

**P1 (cheap, ~1 hour CPU).** Take a fresh untrained `CognitiveStateEmbedding`. Apply Proposal A.1 (domain-block bias init). On a randomly drawn test batch:
- Random init prediction: P(Pi) ≈ P(Cj) ≈ P(Ek) ≈ P(Ol) ≈ 1/40 = 0.025 each.
- A.1 prediction: mean P(P-row) > mean P(C-row) > mean P(E-row) > mean P(O-row), with the gap matching α ≈ 0.5.
- **Falsifies if** the gap is < 0.005 (within softmax noise of uniform).

**P2 (medium, ~half-day GPU).** Train two 1-epoch runs on the existing 5K Lever-3 paired corpus (`HONEST_STATUS.md:85`):
- Run 1 (control): current `StructuredTokenEmbedding`, random init.
- Run 2: same model, but with Proposal A (init only, no architecture change).
- **Predict:** Run 2 reaches >50% canonical-exact in epoch 1 vs Run 1's <30%. **Falsifies if** the gap is < 5pp.

**P3 (medium, ~1 day GPU).** Same setup as P2 but with Proposal B (simplex embeddings + 40→512 re-expand) replacing the current 16.4M embedding.
- **Predict:** Proposal B reaches within 5pp of Run 1's full canonical-exact rate, despite using ~12× fewer embedding parameters. **Falsifies if** the gap is > 10pp.

**P4 (small, ~2 hours).** Inversion-pair geometry test. After 100 training steps under Proposal A.2:
- For each involution pair (e.g., ^2 vs ^3), compute cosine similarity between the corresponding output rows of the cognitive-state head.
- **Predict:** cos(W[2,:], W[3,:]) < −0.7 under A.2; cos(W[2,:], W[3,:]) ∈ [−0.2, +0.2] under random init. **Falsifies if** the structured gap < 0.3.

**P5 (interpretability, no training).** Under Proposal C, walk the 14 reserved-token anchor table and verify each anchor lands on the correct subset of the 40-state simplex (e.g., `^P` token's mass concentrates on P0..P9 within the eps tolerance of `embedding.py:47`). This is a unit-test-level prediction — falsified if any anchor deviates from spec by more than 2 percentage points of mass per non-target dim.

---

## 7. Risks and open questions

**Risk 1 — Structured priors can hurt if the training data violates the prior.** If the SDG corpus has a domain skew (e.g., more O than P examples), an init that pushes mass toward P will need extra steps to undo before it can reach the data distribution. Mitigation: estimate corpus domain ratios first, set α adaptively. Speculative magnitude of risk: low; the SDG is built to the spec, not against it.

**Risk 2 — 40-dim is narrow for natural-language tokens.** Most BPE wordpieces have no natural CAS-state interpretation. Proposal B in its pure form may underfit the surface-vocab slice. Mitigations listed in §3 (residual k-dim channel; two-stream embedding). Open question: what's the right k? Speculative starting point k = 24 (so total 64 dims, matching the existing shared 64-dim bottleneck noted in `memory: project_deepseek_revised_diagnosis_2026_05_03`).

**Risk 3 — Patent scope.** The user's filings (USPTO #64/037,173 per `CLAUDE.md`) cover the 40-state matrix. Proposal D's 48-dim variant should not ship publicly without IP attorney review. Citation: `CAS_FOUNDATIONAL_CLARIFICATIONS.md` §12 (legal framing), `cas_v7_7_rollout_plan.md` IP attorney flag.

**Risk 4 — The Noetic Topos paper formally fixes |I| = 40.** Any 48-dim move requires either an embedding-inside-48 trick (state simplex remains 40, 8 extra dims auxiliary) or a formal extension of the topos paper. Citation: `peer_review/journal_submission/main.pdf` p. 2 Definition 3.1.

**Open Question 1.** Should reserved-token anchors be **frozen** (`requires_grad=False`) or **soft** (gradient-trainable from the anchor)? Frozen guarantees traceability forever; soft allows the model to refine the anchors with experience. The `RegisterLatent` precedent (`register_film.py:209-216`) uses a freeze-then-unfreeze warmup mechanism — same pattern would work here.

**Open Question 2.** For the 48-dim variant: where does A0 go in the simplex ordering? At index 47 (last), index 0 (head, before P0), or as a separate norm-1 channel? `CLAUDE.md` lists the RPM chain as `A0 → Dn → Wn → Pn → Outcome` which suggests A0 is structurally *before* P0 — i.e., index 0. Speculative.

**Open Question 3.** Does the reserved-token-anchor approach break down for compositional CAS tokens like `^3^P` (which is a compound, not a primitive)? The current vocabulary handles compounds as multi-token sequences (`vocabulary.py:64-77` uses source-aware keys). The anchor table only needs entries for *primitive* CAS literals (`^0..^9`, `^P/^C/^E/^O`, `F1..F7`, `|T/|A/|f/|E`, plus `Λ Ω Θ → · NoeticCluster StateSet RelationCluster CoverOf PartitionOf Product ∪ ∩ ∖`); compounds emerge from composition during training.

---

## 8. Code sketch — Proposal B + C (the most promising)

This is pseudocode-level Python in CAS-Native style. ~70 lines. Drop-in replacement for `StructuredTokenEmbedding`'s `surface_embedding` field.

```python
# cas-native/model/simplex_embedding.py  (new file, NOT yet written)

import torch
import torch.nn as nn
import torch.nn.functional as F

NUM_STATES = 40
SIMPLEX_EPS = 1e-8

# The 40 named state indices: P0..P9 = 0..9, C0..C9 = 10..19,
# E0..E9 = 20..29, O0..O9 = 30..39. Matches embedding.py NUM_COGNITIVE_STATES.

# Reserved-token anchor table. Each entry is (token_id, target_state_indices).
# Mass alpha goes uniformly across target indices, (1-alpha) spread on rest.
# All numbers traceable to CLAUDE.md Structural Invariants.
RESERVED_ANCHORS = {
    # Noetic primitives — mass on all 4 domain instances of that Noetic
    "^0": [0, 10, 20, 30],   "^1": [1, 11, 21, 31],
    "^2": [2, 12, 22, 32],   "^3": [3, 13, 23, 33],
    "^4": [4, 14, 24, 34],   "^5": [5, 15, 25, 35],
    "^6": [6, 16, 26, 36],   "^7": [7, 17, 27, 37],
    "^8": [8, 18, 28, 38],   "^9": [9, 19, 29, 39],
    # Domain primitives — mass on full 10-Noetic row of that domain
    "^P": list(range(0, 10)),
    "^C": list(range(10, 20)),
    "^E": list(range(20, 30)),
    "^O": list(range(30, 40)),
    # Operators get uniform anchor (no state preference at init)
    "Theta": list(range(40)),  "Lambda": list(range(40)),
    "Omega": list(range(40)),  "arrow": list(range(40)),
}

def build_anchor_logits(target_indices, alpha=0.97, num_states=NUM_STATES):
    """Return logits whose softmax puts mass alpha on target_indices."""
    p = torch.full((num_states,), (1 - alpha) / (num_states - len(target_indices)))
    p[target_indices] = alpha / len(target_indices)
    # Convert probabilities back to logits (log + small jitter for stability)
    return torch.log(p + SIMPLEX_EPS)

class SimplexEmbedding(nn.Module):
    """
    Token embedding directly on the open probability simplex Δ°_39.
    Each token is a (num_states,) logit vector; .forward returns probabilities.

    Object traceability: simplex_logits[token_id].softmax() IS the trace.
    """
    def __init__(self, vocab_size, num_states=NUM_STATES,
                 vocab_to_anchor=None, alpha=0.97):
        super().__init__()
        self.vocab_size = vocab_size
        self.num_states = num_states

        # Random init for non-reserved tokens; structured init for reserved.
        logits = torch.randn(vocab_size, num_states) * 0.02
        if vocab_to_anchor is not None:
            for tok_id, anchor_name in vocab_to_anchor.items():
                if anchor_name in RESERVED_ANCHORS:
                    logits[tok_id] = build_anchor_logits(
                        RESERVED_ANCHORS[anchor_name], alpha=alpha
                    )
        self.simplex_logits = nn.Parameter(logits)

    def forward(self, token_ids):
        # (B, S) -> (B, S, num_states) on Δ°_39
        raw = self.simplex_logits[token_ids]
        probs = F.softmax(raw, dim=-1) + SIMPLEX_EPS
        return probs / probs.sum(dim=-1, keepdim=True)


class SimplexToHidden(nn.Module):
    """Re-expand simplex embedding to d_model for downstream transformer."""
    def __init__(self, num_states=NUM_STATES, d_model=512):
        super().__init__()
        self.proj = nn.Linear(num_states, d_model)

    def forward(self, simplex_emb):
        return self.proj(simplex_emb)
```

**Wiring.** Replace the `self.surface_embedding = nn.Embedding(...)` line in `structured_token_embedding.py:52-56` with:
```python
self.surface_embedding = SimplexEmbedding(vocab_size, NUM_STATES, vocab_to_anchor=...)
self.simplex_to_hidden = SimplexToHidden(NUM_STATES, d_model)
# in forward:
simplex_emb = self.surface_embedding(input_ids)        # (B, S, 40)
surface = self.simplex_to_hidden(simplex_emb)          # (B, S, d_model)
# (rest of forward unchanged)
```

The `vocab_to_anchor` map is built once at vocabulary construction, walking `RESERVED_TOKENS` (`vocabulary.py:37-46`) plus the Wave-1 reserved CAS tokens.

---

## 9. Citations

- `CLAUDE.md` — Four Critical Mathematical Corrections (Corrections 1, 2, 3, 4); 10 Noetics list; Structural Invariants block (Involution pairs, Domain precedence, 7 Drives, 7 Inversion Axes, 22 Capability Pathways including A0); Phenomenological Register section (4 registers T/A/f/E); Production Semantics block (Θ, Ω, Λ).
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — Clarification 1 (10 authoritative Noetics); Clarification 8 (Register axis, identity-init precedent); Clarification 9 §2 (recipe operator Θ definition); §12 patent legal framing.
- `peer_review/journal_submission/main.pdf` — p. 1 abstract (Δ°₃₉ + Fisher-Rao layer); p. 2 Definition 3.1 (|I| = 40 with partition I_A ⊔ I_B ⊔ I_C ⊔ I_D and preorder A ≽ B ≽ C ≽ D = P ≽ C ≽ E ≽ O); Definition 2.1-2.3 (sieve, Grothendieck topology, sheaf).
- `When Light and Consciousness Share the Same Number...pdf` — pp. 1-3 (48 = 40 Elements + 7 Foundations + 1 A0); p. 4 ("decomposition of 48 is fundamentally different"; honest delimitation); p. 5 (Frame 1/2/3 interpretive options).
- `noetic-compass-scaffold/noetic-compass/cas-native/model/structured_token_embedding.py:22-98` — current `StructuredTokenEmbedding`.
- `noetic-compass-scaffold/noetic-compass/cas-native/model/embedding.py:50-97` — current `CognitiveStateEmbedding`.
- `noetic-compass-scaffold/noetic-compass/cas-native/model/embedding.py:70-86` — open-simplex projection (softmax + eps + renormalize).
- `noetic-compass-scaffold/noetic-compass/cas-native/model/domain_descent.py:27-36` — current domain-precedence mask.
- `noetic-compass-scaffold/noetic-compass/cas-native/model/register_film.py:96-203, 209-216` — RegisterLatent zero-init structural anchoring + freeze/unfreeze precedent.
- `noetic-compass-scaffold/noetic-compass/cas-native/model/cas_native_model.py:62-64` — default `d_model=512`, `vocab_size=32000`.
- `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/vocabulary.py:37-55` — 8 reserved vocabulary tokens.
- `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/structured_token.py:35-38` — axis lengths (Noetic 10, Domain 4, Drive 7, Register 4 → signature_dim 25).
- `noetic-compass-scaffold/noetic-compass/cas-native/training/structured_token_adapter.py:40-49` — `SIGNATURE_FEATURE_DIM` and `NUM_TOKEN_SOURCES`.
- `noetic-compass-scaffold/noetic-compass/HONEST_STATUS.md:23` — corpus size 162K; `:86` — vocab14 reserved CAS tokens list.
- Memory references (user-ratified directives): `feedback_traceability_is_the_whole_purpose`; `feedback_no_foreign_architecture_cas_only`; `feedback_object_traceability_required`.

---

**Word count:** ~2 700 words (within the 1 500-3 000 target).
