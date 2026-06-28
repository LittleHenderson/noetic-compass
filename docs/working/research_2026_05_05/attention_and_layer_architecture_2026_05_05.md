# Attention and Layer Architecture — Can CAS / TKS replace the standard transformer block?

**Author:** R&D specialist (attention + layer slice), 2026-05-05
**Status:** Research note. No production code touched. Pure paper exercise to feed into the Version B build.
**Hard rules followed:** No foreign pretrained weights anywhere. Every proposed module surfaces its intermediate state through the existing `outputs` dict pattern. All claims cited to file:line, CLAUDE.md section, or PDF page.

---

## 1. Goal

CAS-Native today uses an ordinary transformer block (attention + FFN) with CAS modules glued on. The question: **can CAS/TKS replace that block with something smaller, smarter, and fully traceable?** Smaller = fewer params per layer or fewer effective layers per input. Smarter = meaningful inductive bias. Traceable = every intermediate readable in the forward pass, same contract as today's `outputs` dict (`cas_native_model.py:618-643`).

---

## 2. Current architecture — what is wired today

The CASTransformerLayer (`cas_native_model.py:97-196`) is the standard block plus CAS overlays:

```
x_in
  --> norm1 --> DomainDescentAttention(x, cognitive_state) --> domain_out      (line 167-172)
  --> norm2 --> FractalAttentionHead(x)                     --> fractal_out    (line 173-177)
  blend: gate * domain_out + (1 - gate) * fractal_out       (line 179-181)
  residual add
  --> norm3 --> PrerequisiteGateLayer (4 SoftGates a0/D/W/P) (line 186)
  residual add
  --> norm4 --> FFN (Linear -> GELU -> Linear)              (line 137-143)
  residual add
```

So per layer we run **two attention modules** (domain-descent and fractal) plus a 4-stage RPM gate plus a standard FFN. Bigger than a standard block, not smaller — CAS overlays run in parallel to standard machinery rather than replacing it.

Module status:

| Module | Wired? | What it does | Source |
|---|---|---|---|
| `DomainDescentAttention` | yes | Aggregates tokens into 40 cognitive-state slots, applies P→C→E→O lower-triangular mask over slot-to-slot attention, projects back to tokens. Adds learned O→P feedback. | `domain_descent.py:39-225` |
| `FractalAttentionHead` | yes (blended) | Standard QKV attention but the queries are passed through a Hutchinson IFS operator at multiple depths, and the depth outputs are mixed by a learned softmax. | `fractal_attention.py:78-211` |
| `PrerequisiteGateLayer` | yes (every layer) | 4 sequential soft gates (A0 → Drive → Wisdom → Proficiency). Returns per-gate satisfaction tensors. eta and epsilon are separate learned linears (section-retraction approximation). | `rpm_gate.py:49-122` |
| `RegisterLatent` / `RegisterFiLM` | partial | Modulates the 40-dim simplex AND the d_model hidden state via a shared per-register latent. Currently only applied to the cognitive-state projection inside `_compute_cognitive_state`, NOT to layer hidden states. | `register_film.py:96-374`; usage at `cas_native_model.py:444-526` |
| `CognitiveToposReasoner` | yes (output head only) | 7 propositions × 3 truth values (true/false/undetermined). Pools, projects to `num_propositions * d_model`, classifies. Pure output head — no role inside the stack. | `topos_reasoner.py:40-114` |
| `LacunarityGate` | yes (after final norm) | Softmax-renormalize the 40-state vector when activation concentrates too tightly. | `lacunarity_gate.py` |
| `GenerativeHead` (composition) | scaffolded, not in forward path | Implements the (i+j) mod 10 monoid table for operator composition. | `composition.py:23-145` |
| `RecursiveRPMGate` | scaffolded, not wired | Adds CO-1/4/7 exposure loop, CO-5 receptor, CO-6 decomposer, CO-8/9 causal resolver. | `rpm_gate.py:142-340` |

Math reference points:
- Domain Descent mask: total order P ≻ C ≻ E ≻ O (CLAUDE.md §"Structural invariants"; built at `domain_descent.py:27-36`).
- RPM section-retraction (CLAUDE.md "CORRECTION 2"; eta/epsilon at `rpm_gate.py:67-73`).
- 5 Generative Operations: × (integration), ÷ (division), ∘ (fractal composition), + (co-presence), − (subtraction). `CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 §6 (lines 547-559); v7.7 operator discipline in CLAUDE.md.
- 40-state open simplex Δ₃₉° (CLAUDE.md "CORRECTION 4"; `embedding.py:70-86`).

---

## 3. Proposed redesigns

Five proposals, ablation-independent. Each lists what it replaces, the math sketch, traceability.

### Proposal A — Domain-Descent attention as the **default** attention pattern

**Replaces:** the standard all-to-all + parallel fractal blend.

The 40×40 descent mask is a lower-triangular block (P→P, C→P+C, E→P+C+E, O→all): 550 of 1600 entries valid, ~34% density. Today's slot pipeline pays full token-side density before/after. **Make domain-descent the only attention path; run token-to-token only along the descent chain.** Tokens get a soft assignment α(t) ∈ Δ₃ over {P,C,E,O} from the 40-state vector (sum over 10-noetic blocks):

```
A(t, t') = Σ_D α_D(t) · Σ_{D' ⊑ D} α_{D'}(t') · (QK^T)(t,t') / √d
descent_allowed(D, D') = 1 iff D' ⊑ D in P ≻ C ≻ E ≻ O.
```

~34% density vs. dense; drops the depth-3 fractal stack entirely. **Trace:** `domain_routing` (B,S,4), `descent_allowed` (S,S). Plain English: "for this token I attended to peers at my domain-tier or above."

### Proposal B — Hutchinson-attention on the slot bank (fractal merged with descent)

**Replaces:** parallel `DomainDescentAttention` + `FractalAttentionHead`.

Fractal attention today (`fractal_attention.py:78-211`) does QKV with queries passed through a depth-3 Hutchinson IFS in raw token space. That competes with domain-descent for the same role. IFS contractions converge by the contraction-mapping theorem on **bounded** state spaces; the 40-slot bank is bounded (Δ₃₉°). Token space is not. So move it to where it works:

1. Aggregate tokens → 40-slot bank (existing code).
2. Apply `H(s) = Σ_i w_i(s)` at slot level (`fractal_attention.py:18-47`).
3. Slot-to-slot attention with descent mask.
4. Scatter back to tokens.

Hutchinson maps now act on 40 vectors, not S tokens (typically 512+) — **>10× cheaper** per forward at equivalent map count. Expressivity argument: IFS density on compact attractors. **Trace:** `slot_fractal_depth_{0..D-1}` per slot; `depth_weights` softmax tells you which scale dominated.

### Proposal C — RPM gate as **dynamic-depth halt between layers**

**Replaces:** fixed n_layers loop running unconditionally.

`PrerequisiteGateLayer` already returns per-gate satisfaction (a0, drive, wisdom, proficiency); today aggregated into a logged scalar (`cas_native_model.py:608-616`). Reverse the role: **the RPM gate decides whether the next layer runs.** Per "CORRECTION 2," prerequisite satisfaction is one-directional — once eta is satisfied, applying more layers can only add noise.

Let `s_L = ¼(sat_a0 + sat_drive + sat_wisdom + sat_prof)`. With learnable τ, soft halt during training:

```
gate_L = σ(γ · (s_L − τ))                   # γ learnable sharpness
x_{L+1} = gate_L · x_L + (1 − gate_L) · TransformerLayer_{L+1}(x_L)
```

Hard halt at inference. If average halt at L_halt < n_layers, compute saved = `(n_layers − L_halt)/n_layers`. **Trace:** `halt_layer` per sample, `per_layer_rpm`. Plain English: "this input resolved at layer 3."

### Proposal D — Block alphabet of **5 Generative Operations**

**Replaces:** the (attention + FFN) block with a *named* operation per layer.

The 5 ops (×, ÷, ∘, +, −) get distinct module shapes:

| Op | Math primitive | Module | Use |
|---|---|---|---|
| `+` co-presence | additive slot aggregation | sum-pool over slots within domain | merge co-present manifestations without fusing |
| `×` integration | bilinear / outer-product fusion | `CompositionHead` (`composition.py:23-84`) | cross-operand integration → emergent state |
| `∘` fractal compose | iterated map (Hutchinson stack) | the Prop B block | sequential same-type composition / monoid product |
| `÷` division | masked re-softmax on simplex | conditional projection | marginalize a register/domain |
| `−` subtraction | residual suppression | `x_L − suppression(x_L)` | suppress a competing pattern |

A 6-layer stack is specified as `[+, ∘, ×, ÷, ×, −]`. Ordering becomes architecture, not buried hyperparameter. With 5 typed transforms shared across 6 layers vs. 6 independent FFN blocks: ~17% FFN reduction.

Admissibility (v7.7 Clarification 10): same-Noetic multi-register `×` invalid by default unless emergent result named. Layer-level discipline: `×` between layers must either fuse into a named emergent-state head, or downgrade to `+`. **Compile-time checkable** through the existing `api/notation/compiler.py` rather than a runtime knob.

**Trace:** `outputs["layer_types"]` — string list. Plain English: "layer 2 was fractal composition; layer 3 was integration into E_3."

### Proposal E — **Topos-reasoning layer** mid-stack

**Replaces:** one or more middle blocks.

`CognitiveToposReasoner` is currently output-only (`topos_reasoner.py:40-114`). Lift it into the stack: after k blocks, pool to `pooled_L ∈ R^{B×d}`, run the reasoner to get `T_L ∈ R^{B×7×3}`, project to small `cond_L` (zero-init linear, identity at step 0), modulate downstream:

```
x_{L+k} = LayerNorm(x_{L+k}) · (1 + cond_L) + bias(cond_L)
```

21 truth values condition the rest of the stack. Tiny bottleneck, but each value is *interpretable* (true/false/undetermined per named proposition). Cost: ~10K params at d=512. **Trace:** `outputs["mid_topos"]` — the 7×3 tensor at the lift point. Plain English: "by layer 3 the model decided this was a typed-subset claim, rest undetermined."

---

## 4. Parameter count comparison

Baseline `CASNativeConfig` defaults: d=512, n_layers=6, n_heads=8, vocab=32K.

Per-layer cost (current `CASTransformerLayer`):
- `DomainDescentAttention` (q/k/v/out/feedback) = 5d² = 1.31M
- `FractalAttentionHead` (q/k/v/out + 3 depth Hutchinson) ≈ 4d² + 3·4·(d/h)² ≈ 1.10M
- `PrerequisiteGateLayer` (4 SoftGate + eta + epsilon) = 6d² = 1.57M
- FFN (d→4d→d) = 4.20M
- LayerNorm ×4 ≈ 0.004M
- **Total per layer ≈ 8.18M; 6 layers ≈ 49.1M**

| Variant | Per-layer params | 6-layer stack | Δ vs baseline |
|---|---|---|---|
| **Baseline** (current `CASTransformerLayer`) | 8.18M | 49.1M | — |
| **Prop A only** (Domain-Descent default; drop fractal head) | 8.18M − 1.10M = 7.08M | 42.5M | **−13.4%** |
| **Prop B** (merged Hutchinson on slots) | 5.97M | 35.8M | **−27.0%** |
| **Prop C** (RPM dynamic depth, A+B baseline) | same params, ~25-40% inference compute saved | n/a (compute, not param) | **inference compute −25-40%** |
| **Prop D** (5-op alphabet, sharing across 6 layers) | typed FFN shared: avg 3.5M/layer | ~21M (FFN) + 8M (attn shared) = ~29M | **−40%** vs baseline FFN+attn |
| **Prop E** (topos lift, +21→d projection) | +0.01M one-time | +0.01M | negligible (interpretability gain only) |
| **Composite A+B+C+D** | ~5.0M effective | ~30M static, ~20M average inference | **~−40% static, ~−60% inference** |

Back-of-envelope; real numbers need an actual build. Savings come from removing redundancy (parallel domain+fractal, FFN-per-layer no-sharing, gates that don't actually gate) — not clever compression.

---

## 5. Capability claims

- **A:** structural cross-domain leakage prevention. Tokens cannot attend in violation of descent — they literally cannot do it. Today's overlay design lets the standard path do whatever it wants.
- **B:** stable multi-scale slot dynamics, guaranteed by IFS contraction-mapping on the bounded simplex (no such guarantee on raw token space).
- **C:** dynamic compute per input + a meaningful "this input was easy" signal. `outputs["halt_layer"]` is a free interpretability surface. "Easy questions stop at layer 2; jailbreak attempts run all 6 and trip more inversion flags."
- **D:** named-layer architecture with admissibility checks. The compiler in `api/notation/` validates layer sequences the same way it validates CAS expressions — architecture diff = compiler diff.
- **E:** mid-stack symbolic verdict. Model commits to a propositional stance halfway through; later layers condition on it. The one place 3-valued logic plays a computational role rather than just decorating the output.

---

## 6. Falsifiable predictions

Each is a few hours of A6000 time, not days.

- **P1 (Prop A):** Domain-descent-default loses < 2pp on 1K canonical eval but cuts W-axis (domain-precedence) inversion rate by > 50%.
- **P2 (Prop B):** Merged slot-Hutchinson + descent matches or beats current dual-path at 30% fewer params on canonical exact + meta_relations.
- **P3 (Prop C):** With dynamic halting, > 40% of 1K eval examples halt at layer ≤ 4 of 6; no canonical regression vs always-run.
- **P4 (Prop D):** 6-layer typed `[∘, +, ×, ÷, ×, −]` beats parity-param "all-generic" on meta-logic bucket (which already requires understanding × vs + per Clarification 10).
- **P5 (Prop E):** Mid-stack topos lift cuts inversion-axis P (compound) flag rate by > 30% on 1K eval, no canonical regression.

---

## 7. Risks and open questions

**Risks.**

1. **The current dual-attention might already be a learned identity.** If `fractal_gate` (`cas_native_model.py:127`) converged near 1.0 across layers, the fractal path is doing nothing and dropping it is free. Near 0.5, removing it costs capacity. **Measure before any retrain.**
2. **Prop C** trains poorly with sharp halt. Needs sharpness annealing + load-balancing loss to prevent halt-at-layer-1 collapse (PonderNet/ACT issue — solvable, not novel).
3. **Prop D** risks becoming relabeling — 5 differently-named MLPs that learn whatever. Pays off only if op type is *architecturally* enforced (`+` cannot have bilinear terms; `×` must produce explicit emergent-state output).
4. **Prop E** can hide capacity if the projection back is too low-rank. 21 values is a real bottleneck. Mitigation: conditioning signal, not residual replacement.
5. **No-foreign-weights rule** means every redesign is from-scratch retrain — no warm start.
6. **Trace size grows.** Every redesign adds keys to `outputs`. Need a trace-budget contract before production.

**Open questions for the user.**

1. Should Prop D's layer sequence be a CAS expression validated by `api/notation/compiler.py`, or a parallel discipline? Conflating two compilers vs. unifying them.
2. Prop C's τ — global scalar, per-layer learnable, or input-dependent? Input-dependent is most expressive but hardest to interpret.
3. Topos lift (E) at a **fixed** depth or **learned**? Fixed = traceable; learned = powerful but adds a discrete trace decision.
4. How aggressively to drop fractal-on-tokens (B)? If `fractal_gate` data shows real signal at certain layers, keep it there only.

---

## 8. Code sketch — most promising redesign (Prop B + Prop C combined)

Combined because they touch the same module and Prop C is essentially free riding on Prop B's slot bank. This is pseudocode, NOT production-ready:

```python
# noetic-compass-scaffold/noetic-compass/cas-native/model/cas_block_v2.py
# CAS-native block: slot-Hutchinson + descent + RPM-halt
# Replaces CASTransformerLayer (cas_native_model.py:97-196)

import torch, torch.nn as nn, torch.nn.functional as F
from .domain_descent import build_domain_descent_mask, NUM_COGNITIVE_STATES
from .fractal_attention import HutchinsonOperator
from .rpm_gate import SoftGate

class CASBlockV2(nn.Module):
    """Slot-Hutchinson + Domain-Descent + RPM halt gate.

    Replaces the parallel (DomainDescent || Fractal) + RPM + FFN block
    with a single slot-bank pipeline. Returns a halt scalar per sample
    that the outer model uses to decide whether to skip the next layer.
    """
    def __init__(self, d_model, n_heads, num_states=NUM_COGNITIVE_STATES,
                 num_ifs_maps=4, rpm_threshold=0.5):
        super().__init__()
        self.d_model, self.n_heads, self.num_states = d_model, n_heads, num_states
        self.head_dim = d_model // n_heads
        self.num_ifs_maps = num_ifs_maps

        # Token <-> slot routing
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # IFS contraction on slot space (Prop B)
        self.hutchinson = HutchinsonOperator(d_model, num_ifs_maps)

        # Descent mask buffer
        self.register_buffer("descent_mask", build_domain_descent_mask(num_states))

        # RPM halt gates (Prop C) — operate on slot-pooled state
        self.gate_a0 = SoftGate(d_model, rpm_threshold)
        self.gate_drive = SoftGate(d_model, rpm_threshold)
        self.gate_wisdom = SoftGate(d_model, rpm_threshold)
        self.gate_prof = SoftGate(d_model, rpm_threshold)
        # Section-retraction style eta/epsilon (CLAUDE.md CORRECTION 2)
        self.eta = nn.Linear(d_model, d_model)
        self.epsilon = nn.Linear(d_model, d_model)

        # Tiny FFN (kept; small)
        self.ffn = nn.Sequential(nn.Linear(d_model, 2*d_model), nn.GELU(),
                                 nn.Linear(2*d_model, d_model))
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)

    def forward(self, x, slot_weights, attention_mask=None):
        """
        x: (B, S, d_model)
        slot_weights: (B, S, 40) from cognitive embedding
        Returns: (x_out, halt_score, trace_dict)
        """
        B, S, D = x.shape
        # 1. Aggregate tokens into 40-slot bank
        h = self.norm1(x)
        slot_mass = slot_weights.sum(1).clamp_min(1e-8)         # (B, 40)
        slots = torch.einsum('bsd,bsk->bkd', h, slot_weights) / slot_mass.unsqueeze(-1)

        # 2. Hutchinson contraction in slot space (Prop B)
        slots_fr = self.hutchinson(slots.reshape(-1, D)).reshape(B, 40, D)

        # 3. Descent-masked slot-to-slot attention
        q = self.q_proj(slots_fr); k = self.k_proj(slots_fr); v = self.v_proj(slots_fr)
        attn = (q @ k.transpose(-1,-2)) / (D**0.5)
        attn = attn.masked_fill(~self.descent_mask.unsqueeze(0), -1e9)
        slot_out = self.out_proj(F.softmax(attn, dim=-1) @ v)

        # 4. Scatter back to tokens
        token_out = torch.einsum('bkd,bsk->bsd', slot_out, slot_weights)
        x = x + token_out

        # 5. RPM halt: compute satisfaction on slot-pooled state
        eta = self.eta(self.norm2(x.mean(dim=1)))                # (B, D)
        _, sat_a0 = self.gate_a0(eta)
        _, sat_d  = self.gate_drive(sat_a0 * eta)
        _, sat_w  = self.gate_wisdom(sat_d * eta)
        _, sat_p  = self.gate_prof(sat_w * eta)
        halt = (sat_a0.mean(-1) + sat_d.mean(-1)
                + sat_w.mean(-1) + sat_p.mean(-1)) / 4           # (B,)

        # 6. Small FFN, residual
        x = x + self.ffn(self.norm3(x))

        trace = {
            "halt_score": halt.detach(),
            "rpm": {"a0": sat_a0.detach(), "drive": sat_d.detach(),
                    "wisdom": sat_w.detach(), "prof": sat_p.detach()},
            "slot_states": slots_fr.detach(),
        }
        return x, halt, trace


# In CASNativeModel.forward, replace the layer loop with:
# halted = torch.zeros(B, dtype=torch.bool, device=x.device)
# for L, layer in enumerate(self.layers):
#     cog = self._compute_cognitive_state(x, register_activations)
#     x_new, halt, tr = layer(x, cog, attention_mask)
#     gate = torch.sigmoid(GAMMA * (halt - TAU)).view(B,1,1)   # soft halt
#     x = gate * x + (1 - gate) * x_new                         # halted samples freeze
#     halted = halted | (halt > TAU)
#     trace_per_layer.append(tr)
#     if halted.all() and not self.training:                    # early-exit at inference
#         break
```

This is implementable on the existing `CASNativeModel` skeleton with surgical edits to the layer loop and replacement of `CASTransformerLayer` by `CASBlockV2`. Embeddings, output heads, and inversion detector all stay the same. **No replacement of the model class** — just block surgery.

---

## 9. Citations

**CLAUDE.md (project bible):** §"Authoritative Noetic Definitions" (10 canonical Noetics); §"Structural invariants" (P≻C≻E≻O; descent vs feedback); §"CORRECTION 2" (RPM section-retraction, one-directional); §"CORRECTION 4" (open simplex Δ₃₉°, Fisher-Rao); §"Phenomenological Register axis v7.5" (T/A/f/E); §"Production Semantics v7.6" (Θ(Ω), limiting reagent); §"Register Multiplicity v7.7" (`+` vs `×` vs `|⟨…⟩`); §"Phase 4: CAS-Native AI" (Phase-4 deliverable list).

**Foundational clarifications:** `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 §6 lines 547-559 (5 Generative Operations); Clarification 10 §3-4 (operator discipline + admissibility).

**Code (all paths inside `noetic-compass-scaffold/noetic-compass/cas-native/model/`):**
- `cas_native_model.py:97-196` — `CASTransformerLayer`; `:228-643` — full `CASNativeModel.forward`; `:127` — `fractal_gate`; `:608-616` — RPM aggregation.
- `domain_descent.py:27-36` — descent mask; `:39-225` — slot attention.
- `fractal_attention.py:18-47` — IFS contraction; `:78-211` — fractal head.
- `rpm_gate.py:21-46` — SoftGate; `:49-122` — `PrerequisiteGateLayer`; `:244-340` — `RecursiveRPMGate` scaffold.
- `register_film.py:96-374` — `RegisterLatent` (ADR-08 Option E).
- `topos_reasoner.py:40-114` — output-head reasoner.
- `composition.py:23-84` — `CompositionHead` (monoid table); `:87-145` — `GenerativeHead`.
- `lacunarity_gate.py:17-80` — self-correction.
- `embedding.py:50-97` — open-simplex projection.

**Honest status:** `noetic-compass-scaffold/noetic-compass/HONEST_STATUS.md` lines 36-43 (Mode 7 trace wiring — proposals stay compatible); lines 53-65 (NL generation roadmap — this slice doesn't block it).

**Peer-review paper.** Did not deep-read `peer_review/journal_submission/main.pdf` in this slice. Math sketches use textbook IFS contraction-mapping theorem and the section-retraction statement from CLAUDE.md "CORRECTION 2." Before implementation, paper's exact formal statements for domain-descent / fractal / RPM / topos should be re-checked; minor index/name adjustments likely.
