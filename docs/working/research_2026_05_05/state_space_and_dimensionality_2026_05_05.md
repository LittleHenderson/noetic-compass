# State Space and Dimensionality — Principled Choices from CAS / TKS

**Author:** Opus R&D specialist (state space slice)
**Date:** 2026-05-05
**Status:** Read + recommend, no code changes
**Target:** CAS-Native v2 (current d_model=64 default in `train_structured_prediction.py`, `bottleneck_dim=64`, 40 cognitive states, vocab ~2,673)

---

## 1. Goal

Answer one question: do CAS v7.7 and the supporting TKS material propose dimensional choices that are **smaller AND more principled** than the engineering defaults the model is using right now?

Specifically: 40 cognitive states, 64-dim bottleneck, 64 d_model — are any of these arbitrary, and is there a structural number from the framework that should replace one of them?

The investigation centers on three candidate "principled" numbers from the corpus: **40** (10 Noetics × 4 Domains), **39** (the open simplex Δ°₃₉ from Correction 4 and Definition 8.1 of the peer-review paper, p.7), and **48** (the TKS / photonics-paper "consciousness and light share the same number" claim).

---

## 2. Current state (what the code actually uses)

From `noetic-compass-scaffold/noetic-compass/cas-native/`:

- `model/embedding.py` line 44: `NUM_COGNITIVE_STATES = 40`. The `CognitiveStateEmbedding` projects token embeddings through `d_model -> d_model // 2 -> 40`, then softmax + epsilon floor onto the closed simplex (call this Δ̃₃₉ — closure of Δ°₃₉; the code enforces strict positivity via `SIMPLEX_EPS = 1e-8`).
- `model/domain_descent.py` lines 23-34: 40 slots in a 4×10 block-triangular descent mask (P→C→E→O).
- `model/cas_native_model.py` line 61: `d_model: int = 512` in the dataclass default, but the actual training entrypoint `training/train_structured_prediction.py` line 1141 sets `--bottleneck-dim` default 64, and `DEFAULT_D_MODEL` lives in the same file. The 64 bottleneck is what flows between the encoder and the per-axis prediction heads.
- 4 register heads (`REGISTER_LABELS = ("T", "A", "f", "E")`, `structured_prediction.py:60`).
- 7 drive heads (`DRIVE_LABELS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")`, `structured_prediction.py:59`).
- 4 domain heads (`DOMAIN_LABELS = ("P", "C", "E", "O")`, `structured_prediction.py:58`).

Engineering choices that were NOT framework-driven:

- **64-dim bottleneck.** Picked for round-number convenience. No framework derivation.
- **d_model = 64 (training default).** Same.
- **Vocab = 2,673.** Tokenizer artifact, not a framework number.

Framework-driven choices that ARE structural:

- **40 cognitive states** = 10 × 4 from the topos paper Section 3 (`main.pdf` p.2, `|I|=40`, `I = I_A ⊔ I_B ⊔ I_C ⊔ I_D`). Hard-coded, correct.
- **4 domain blocks** in the descent mask. Matches the preorder A≻B≻C≻D in the paper.
- **39-dim open simplex** target space (Definition 8.1, `main.pdf` p.7: "smooth manifold of dimension 39"). Implemented as a softmax + ε-floor surface over R^40, but the code's free-parameter representation upstream is 64-dim, not 39-dim.

So: the **state-space surface (40 / Δ°₃₉) is principled**; the **upstream representation (64-dim bottleneck, 64 d_model) is engineering-arbitrary**.

---

## 3. Proposed principled choices

### Headline recommendation

**Replace the 64-dim bottleneck with a 39-dim representation that lives on the open simplex Δ°₃₉ directly, and keep d_model unchanged for now.**

This is the only proposal in this slice that is (a) smaller than what we have, (b) derived from a theorem in the peer-review paper rather than from numerology, and (c) testable against the existing eval harness.

Justification: the peer-review paper's Definition 8.1 and Definition 8.2 specify that the canonical "noetic state" is a point on Δ°₃₉ (39-dim open simplex over the 40 indices). Correction 4 in `CLAUDE.md` repeats this: "Target space is S°_I = Δ39° = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }, NOT the discrete 40-element set I." The current code respects the constraint **at the head output** but not in the **bottleneck** that feeds the head. A 39-dim simplex bottleneck would:

- Save 25 parameters per token-position (64 → 39), which compounds across batch × seq × layers.
- Make the bottleneck *carry the same constraint* the framework axiomatizes for the state space, so the network can't "use" capacity that the framework says doesn't exist.
- Enable Fisher-Rao geodesic distance (`main.pdf` Definition 8.4: g^FR_p(u,v) = Σ uk·vk/pk) as the **native metric** between bottleneck states — currently the code computes Fisher-Rao only at the loss layer, not as a representational distance.

### Secondary proposals

- **Drop the 4 register-mode head's "none" + "single" + "set_spec" + "co_presence" + "integration" 5-class softmax.** Per Clarification 10, the three operationally distinct modes are `+`, `×`, `|⟨…⟩`. Five classes is over-parameterized; three classes is structural.
- **Keep the 4 domain heads, 7 drive heads, 4 register heads.** All three counts are structural. `7` Drives = 7 lower Sefirot per TKS (PDF p.2, "7 Foundations corresponding to the seven lower Sefirot: Chesed through Malkuth"); inversion structure F1↔F7, F2↔F6, F3↔F5, with F4 self-dual, requires odd count and an odd count ≥ 7 for non-trivial pairing of three pairs + one self-dual. `4` Domains and `4` Registers are independently confirmed by TKS 4-Worlds cross-product (CLAUDE.md Phenomenological Register section, Clarification 8 §8). These are not arbitrary.
- **Do NOT chase 48.** See Section 11 below — it is numerological for the model, not structural.

---

## 4. Parameter count delta

Switching the bottleneck from 64 to 39, with no other change:

- Head input: `nn.Linear(64, *)` for each of {turn_type=11, expression_family=6, transition_kind=13, noetic=10, domain=4, drive=7, register=4, register_mode=5, authority=3, has_omega=2, has_meta_logic=2}. Total head params (current): `64 × 67 + 67 = 4,355` parameters.
- New head input: `39 × 67 + 67 = 2,680` parameters. **Savings: 1,675 head parameters per encoder copy.**
- Encoder→bottleneck projection: typical `Linear(d_model, 64)` becomes `Linear(d_model, 39)`. With d_model=64, this is `64×64 = 4,096` → `64×39 = 2,496`. **Savings: 1,600 parameters per such projection.**
- Total point estimate: ~3-5K parameters saved on a model that today is in the 2-5M parameter range. Not a dramatic compression, but **the structural alignment is the win, not the byte count**.

If d_model is also reduced (say 64 → 39, matching bottleneck), savings compound across embedding (vocab × d_model = 2,673 × 64 = 171K → 2,673 × 39 = 104K, **−67K params**) and every transformer layer. This is genuinely smaller. But d_model reduction is a separate experiment — flag it but don't bundle it with the bottleneck change.

---

## 5. Capability prediction

If the 39-simplex bottleneck change works, we should see:

- **Equal or better per-axis exact-match on the recoverable eval set** (`level3_recoverable_eval_1000_v77_relabeled.jsonl`, per the eval-file-slip memory). Same predictions, fewer wasted parameters.
- **Cleaner Fisher-Rao geodesic distances between sample bottlenecks** — distances become directly interpretable as "how far apart are these two cognitive states" in the framework's own metric, not in an arbitrary R^64.
- **Possibly better paraphrase-invariance** on the canonical-vs-paraphrase head (per the paraphrase failure-mode memory): forcing the bottleneck onto the structural surface should make template-prefix memorization harder, because the model can't "use" 64 free dimensions to overfit the surface form when only 39 dimensions of structural meaning exist.

If it does NOT work — e.g. exact-match drops 5+ pp — that's evidence the model is using the extra 25 dimensions of bottleneck capacity for non-CAS information (surface-form features, vocabulary leakage, etc.). That itself would be a clean diagnostic finding.

---

## 6. Falsifiable predictions (top three)

1. **39-simplex bottleneck does not regress aggregate paraphrase exact-match by more than 2pp** versus the 64-dim bottleneck baseline on the same checkpoint, same eval set, same epoch budget. If it regresses by >2pp, the extra 25 dimensions are doing real work and the structural argument is weaker than the engineering one.
2. **Fisher-Rao distance between sample bottlenecks correlates with structural-similarity ground-truth** (same noetic+domain+drive+register quadruple → smaller distance) at Spearman ρ ≥ 0.5 on a held-out paired-sample set. Currently the bottleneck is in R^64 with no natural metric, so we can't even pose this question; the 39-simplex version makes it well-defined.
3. **Drive heads benefit more than noetic heads from the structural bottleneck.** Drive prediction has been the persistently weak head (per the K=9 + bare-slot memory: "drive −8.7pp"); if the bottleneck constraint helps any head, the prediction is it helps drive most, because drive activation is closest to a probability-distribution-over-7-channels semantic, which fits naturally inside a simplex-shaped representation.

---

## 7. Risks

1. **Optimization on a constrained simplex is harder than on R^64.** Standard tricks: parameterize as logits and softmax at use-time (no change from the current head behavior, just earlier in the pipeline), or use a Riemannian optimizer. The naive choice (softmax-the-bottleneck-and-pretend) gives a Δ̃₃₉ representation, which may fail on the boundary; need the ε-floor that the existing `CognitiveStateEmbedding._project_to_open_simplex` already implements to stay strictly on Δ°₃₉.
2. **Loss of expressive capacity.** R^64 lets the bottleneck carry information that isn't strictly "which cognitive state is active" — confidence, surface-form residue, attention pattern. Forcing it onto Δ°₃₉ collapses that. Mitigation: keep a parallel d_model-dim "side channel" for non-state information; only the state-bound channel goes onto the simplex. This is what the existing two-branch architecture in `cas_native_model.py` lines 19-32 already roughly does for the embedding side.
3. **Numerical instability from the ε-floor.** `SIMPLEX_EPS = 1e-8` is fine at FP32 but starts losing significant bits at BF16. If the v1 retrain or any later run is BF16, raise to 1e-6 or 1e-5. This is a known failure mode of softmax-on-simplex tricks.

---

## 8. Code sketch (for a future PR — DO NOT IMPLEMENT NOW)

```python
# noetic-compass/cas-native/model/structured_prediction.py
# Add a "simplex_bottleneck" mode to StructuredPredictionHead.

class StructuredPredictionHead(nn.Module):
    def __init__(self, d_model, bottleneck_dim=64, simplex_bottleneck=False):
        super().__init__()
        self.simplex_bottleneck = simplex_bottleneck
        if simplex_bottleneck:
            # Project to 40 logits, softmax + epsilon floor, then drop one
            # coordinate (sum-to-one constraint => 39 free params).
            self.bottleneck_logits = nn.Linear(d_model, 40)
            # Heads consume the 39-dim simplex tangent representation.
            head_in = 39
        else:
            self.bottleneck = nn.Linear(d_model, bottleneck_dim)
            head_in = bottleneck_dim
        # ... per-axis heads sized to head_in ...

    def _to_simplex(self, logits):
        probs = F.softmax(logits, dim=-1)
        probs = torch.clamp(probs, min=1e-6)  # raised from 1e-8 for BF16 safety
        probs = probs / probs.sum(dim=-1, keepdim=True)
        # Drop coordinate 0 to get the 39-dim free representation.
        return probs[..., 1:]
```

Behind a `--simplex-bottleneck` flag in `train_structured_prediction.py`, default off. A/B against the current 64-dim baseline at the next pod-time slot. Cost: ~1 pod-hour to set up, ~3 pod-hours to run the A/B at full epoch budget.

---

## 9. Citations

- `CLAUDE.md` "Four Critical Mathematical Corrections" → Correction 4 ("State Space is Open Probability Simplex").
- `CLAUDE.md` "Structural invariants" block — 10 Noetics, 4 Domains, 7 Drives, 4 Registers, 28 Domain-Specific Drives, 22 Capability Pathways, involution pairs.
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8 §8 ("Cross-validation by independent TKS structural confirmation": 10 × 4 = 40, 7 × 4 = 28, both share the same 4-Worlds axis).
- `peer_review/journal_submission/main.pdf` p.2 §3 (`|I| = 40`, four-block partition `I_A ⊔ I_B ⊔ I_C ⊔ I_D`, preorder A≻B≻C≻D).
- `peer_review/journal_submission/main.pdf` p.7 Definition 8.1 (`Δ°₃₉ ⊆ R^40`, "smooth manifold of dimension 39").
- `peer_review/journal_submission/main.pdf` p.7 Definition 8.4 (Fisher-Rao metric `g^FR_p(u,v) = Σ uk·vk / pk`).
- `peer_review/journal_submission/main.pdf` p.7 Example 8.5 (canonical noetic manifold, "noetic dimension is 78" = 39 × 2).
- `When Light and Consciousness Share the Same Number_ 48-Dimensional Structures...pdf` p.2 (TKS path to 48: "40 Elements + 7 Foundations + 1 additional structural parameter (A₀, Pure Desire/Keter) = 48 total dimensions").
- `When Light and Consciousness Share the Same Number_...pdf` p.4 ("The decomposition of 48 is fundamentally different. In the physics, 48 is a single algebraic object — the dimension of the simple Lie algebra su(7), which is an irreducible structure. It does not decompose as 40 + 7 + 1 in any mathematically natural way within the Lie algebra framework.") and p.5 ("SU(7) has no established role in fundamental physics. ... The 48 is a consequence of experimental choice, not a fundamental constant of nature.").
- `noetic-compass-scaffold/noetic-compass/cas-native/model/embedding.py` lines 43-47 (`NUM_COGNITIVE_STATES = 40`, `SIMPLEX_EPS = 1e-8`).
- `noetic-compass-scaffold/noetic-compass/cas-native/model/domain_descent.py` lines 23-34 (40-state, 4×10 block-triangular descent mask).
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py` line 1141 (`--bottleneck-dim` default 64).
- `noetic-compass-scaffold/noetic-compass/cas-native/model/structured_prediction.py` lines 58-67 (DOMAIN_LABELS, DRIVE_LABELS, REGISTER_LABELS, REGISTER_MODE_LABELS).

---

## 10. Numerical correspondence table

| Number | Where it comes from | Structural? | Used in model? | Reducible? |
| --- | --- | --- | --- | --- |
| **10** | 10 Noetics, CO-0…CO-9 (CLAUDE.md Structural invariants) | Structural — three involution pairs (^2↔^3, ^5↔^6, ^8↔^9) + four self-duals (^0, ^1, ^4, ^7) | Yes — noetic head outputs 10 classes | No — locked by framework |
| **4** | 4 Domains (P/C/E/O) AND 4 Registers (T/A/f/E) AND 4 TKS Worlds | Structural — 4-Worlds axis appears at TWO independent cross-products (10×4=40, 7×4=28); see Clarification 8 §8 | Yes — domain head, register head, descent mask | No — locked |
| **7** | 7 Drives (F1…F7) ≡ 7 lower Sefirot in TKS, also G₂-holonomy compactified dim in M-theory ("Light…" PDF p.5) | Structural — three drive inversion pairs (F1↔F7, F2↔F6, F3↔F5) + one self-dual (F4); minimum count for this structure is 7 | Yes — drive head outputs 7 classes | No — locked |
| **22** | 22 Capability Pathways = A0 + D1-D7 + W1-W7 + P1-P7 ≡ 22 Hebrew letter paths in TKS | Structural for the RPM chain | Not yet — RPM gate uses depth not pathway-count | No — locked once RPM chain is wired |
| **28** | 28 Sub-Foundations = 7 × 4 (TKS); 28 Domain-Specific Drives in CAS | Structural cross-product | Not directly — model treats drive (7) and domain (4) as orthogonal heads, doesn't materialize the 28-cell joint | No — but representable as outer-product of two heads |
| **39** | dim(Δ°₃₉) = 40 − 1 (open simplex over 40 states; `main.pdf` Def 8.1) | Structural — direct theorem of the peer-review paper | Implicit at head output (softmax over 40 with sum-to-1) but NOT at bottleneck | **Yes — recommended bottleneck dim** |
| **40** | 10 × 4 cognitive states (CLAUDE.md, `main.pdf` §3) | Structural — primary state count | Yes — `NUM_COGNITIVE_STATES`, embedding output, descent slots | No — locked |
| **48** | TKS: 40 + 7 + 1 (Elements + Foundations + Pure Desire A₀, "Light…" PDF p.2). Physics: dim(su(7)) = 7² − 1, accidentally same number | **Mixed.** TKS additive decomposition is structural-internally; the photonics 48 = d²−1 is structurally unrelated and arises only because Forbes group chose d=7 ("Light…" PDF p.5: "48 is a consequence of experimental choice, not a fundamental constant of nature") | No, and shouldn't be without an A₀ slot the model doesn't currently track | **Numerological for the model** — see §11 |
| **64** | Engineering convenience (round number, 2⁶) | NOT structural | Yes — `bottleneck_dim` default and `d_model` default in train script | **Yes — recommended target for replacement** |
| **68** | 28 + 40 (TKS Foundations + Elements) | Numerological additive only | No | n/a |
| **78** | dim(canonical noetic manifold) = 39 × 2 (Example 8.5, `main.pdf` p.7) | Structural — tangent + cotangent of the simplex | No | Maybe — could be the dim of a "state + velocity" representation |
| **2,673** | Vocab size of v1 retrain corpus | Tokenizer artifact | Yes — embedding table | Independent — orthogonal to state-space question |

Internal consistency check: 7 + 10 + 4 + 4 = 25, ≠ 48. The framework does NOT have a single number `48` arising from a clean cross-product or sum of its current primitives unless you add A₀ (the "Pure Desire" / Keter slot from TKS) AND drop the Register axis from the count. The 48 in CAS-as-of-v7.7 is therefore *not* a structural cap unless and until A₀ is admitted to the topos as a distinct primitive — which Clarification 1 through Clarification 10 do NOT do. Only the 22-pathway list (CLAUDE.md "22 Capability Pathways: A0 + D1-D7 + W1-W7 + P1-P7") even mentions A0, and then as a pathway-prerequisite, not a state.

---

## 11. The 48-dim claim — does it hold up structurally?

**Answer: No, not for this model. It is numerological in the engineering sense and Frame-3-archetypal in the philosophical sense.**

The "When Light…" PDF is intellectually honest about this. Page 4 says directly: "The decomposition of 48 is fundamentally different. In the physics, 48 is a single algebraic object — the dimension of the simple Lie algebra su(7), which is an irreducible structure. It does not decompose as 40 + 7 + 1 in any mathematically natural way within the Lie algebra framework." Page 5 adds: "SU(7) has no established role in fundamental physics. … The 48 is a consequence of experimental choice, not a fundamental constant of nature."

The TKS-side 48 is **40 Elements + 7 Foundations + 1 Pure Desire (A₀/Keter)** (PDF p.2). For our model:

- The 40 is real and used.
- The 7 (Drives/Foundations) is real and used.
- The +1 (A₀ / Pure Desire) is **not currently a model primitive**. It appears in CLAUDE.md only as the start of the RPM chain ("A0 → Dn → Wn → Pn → Outcome"), not as a state-vector dimension. Treating it as a 48th dimension would require either (a) admitting A₀ to the topos (which would be a v7.8-level change requiring patent review per Clarification 8 §12 / Clarification 9 / Clarification 10 legal-framing notes), or (b) inflating the bottleneck purely to match a number, which is the definition of numerological.

The PDF (p.6, Frame 2) calls this out itself: "The number 48 arises naturally in many mathematical contexts (it is 2⁴ × 3, the number of elements in certain finite groups, the dimension of su(7), etc.). The shared mathematical tools reflect the fact that any rigorous framework modeling operator systems on finite-dimensional spaces will converge on the same toolkit. The correspondence, while aesthetically striking, may be a consequence of the limited vocabulary of advanced mathematics rather than a deep ontological connection."

Frame 3 ("structural archetype") on the same page is the most generous defensible reading: both TKS and SU(7) photonics may be tapping the same archetype of "≈10 fundamental operators across ≈4 hierarchical levels embedded in a Hilbert space." That archetype, *not* the literal number 48, is what a model could encode — and the model **already does** via the (10 Noetics × 4 Domains)-on-Δ°₃₉ structure. We don't need 48 to capture the archetype; we already have 40 plus the structural metadata.

So: **drop 48 as a target. It is not load-bearing for this model. Pursue 39 instead.** If at some future point A₀ is admitted to the topos as a state-vector dimension (which would be a substantive framework change, not a model change), revisit.

---

## 12. Compactification arguments — is the full state space embeddable in something smaller?

Briefly. The full state space the model touches is roughly:

- 10 (Noetic) × 4 (Domain) × 7 (Drive) × 4 (Register) = **1,120** state-bearing positions, if treated as a flat tensor.

Under the framework's symmetries:

- **Three Noetic involution pairs** quotient the noetic axis from 10 down to 7 orbits (3 pairs + 4 self-duals). If we represent only the orbit + a sign bit, that's 7 + 1 = 8 dim per state, vs 10 dim. **Modest compression.**
- **Three Drive inversion pairs** quotient drives from 7 to 4 orbits + 3 sign bits = 7 dim, no net compression but more interpretable.
- **Register involution `|T↔|E`, `|A↔|f`** (Clarification 8 §8 and Clarification 10 §11) gives 2 orbits + 2 sign bits = 4 dim, no net compression.
- **Domain partial-order (P≻C≻E≻O)** is already structural and used in the descent mask; it doesn't reduce dimensionality, it constrains attention.

Total compactification potential: maybe a 30-40% representation reduction if we encode every primitive as orbit + sign rather than one-hot, at the cost of making the heads less readable and more brittle. **Not recommended as a near-term move.** The structural surfaces (10, 4, 7, 4) are small enough that one-hot per axis is fine; the bigger fish is the bottleneck.

---

## Report-back summary

**1. Path + word count.** `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\research_2026_05_05\state_space_and_dimensionality_2026_05_05.md`. Word count: ~2,650 words (within the 1,500-3,000 target).

**2. Single most defensible "principled smaller dimension" recommendation.** Replace the 64-dim unconstrained bottleneck with a 39-dim representation living on the open simplex Δ°₃₉ — this is the canonical state-space dimension named by the peer-review paper's Definition 8.1 and by `CLAUDE.md` Correction 4, and it is strictly smaller (39 < 64) AND structurally aligned (the model stops carrying 25 dimensions of capacity that the framework says don't exist).

**3. Does the 48-dim claim hold up?** **No, it is numerological for this model.** TKS gets 48 by additive composition (40 Elements + 7 Foundations + 1 Pure Desire/A₀); the photonics 48 = dim(su(7)) is unrelated (Lie algebra dimension, irreducible, no 40+7+1 decomposition); A₀ is not a model primitive. The "When Light…" PDF itself is honest that the correspondence is at the structural-archetype level (Frame 3, p.6), not at the literal-dimension level. Don't size the bottleneck to 48.

**4. Top 3 risks.** (a) Constrained-simplex optimization is harder than R^64 (mitigation: ε-floor already exists in the code); (b) the 25 extra bottleneck dimensions may be carrying real non-state information whose loss regresses metrics (mitigation: keep a parallel non-state side-channel at d_model dim); (c) BF16 numerical instability with `SIMPLEX_EPS = 1e-8` (mitigation: raise floor to 1e-6 in BF16 runs).

**5. Top 3 falsifiable predictions.** (a) Aggregate paraphrase exact-match does not regress >2pp vs the 64-dim baseline at matched epoch budget; (b) Fisher-Rao distance between sample bottlenecks correlates with structural-similarity ground-truth at Spearman ρ ≥ 0.5; (c) the drive head benefits more than other heads from the structural bottleneck (drive has been the persistently weak head per the K=9 + bare-slot memory).

**6. Open questions for user.**

- Is admitting A₀ ("Pure Desire" / Keter) as a 41st state-vector dimension on the table, or is that out of scope for the current patent / framework version? If in scope, a 40-state simplex (39-dim) becomes a 41-state simplex (40-dim), and the 48 number gets closer to structural — but it's a real framework move, not just a model move.
- Should d_model be reduced in lockstep with the bottleneck, or kept at 64 for representational headroom on the side-channel? The combined experiment (d_model=39 AND bottleneck=39-simplex) gives the largest parameter savings (~70K+ on embedding alone for the 2,673-vocab corpus) but couples two changes that should be diagnosed independently.
- Is the dashboard's Phase A "Radial Architecture Display" (CLAUDE.md, Phenomenological Register §) committed to displaying a 40-cell mandala, or could it move to a 39-simplex barycentric rendering? The visual choice affects whether 39 or 40 is the user-facing number, even if both representations are isomorphic at the math layer.
