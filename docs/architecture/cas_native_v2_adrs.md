# CAS-Native v2 — Architectural Decision Records

**Session:** CAS-Native v2 specification, 2026-04-22
**Scope:** Six architectural decisions governing CAS-Native v2 redesign against CAS v7.7 framework (Clarifications 1–10).
**Preceding work:**
- CAS v7.7 framework lock (commits `b5c5694` through `1eb62c6`, 2026-04-21)
- CAS-Native v7.4 weight audit, 2026-04-22 (no production weights — architectural scaffolding only)
- Framework-fidelity verification gate against Clarification 8 (in-session)

**Framework references cited throughout:**
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarifications 1, 8, 9, 10
- `CLAUDE.md` (repo-root v7.7 authoritative)
- `ip/CAS_NATIVE_ARCHITECTURE_PROVISIONAL_DISCLOSURE.md` (provisional disclosure, 2026-04-12)

**Related rollout plans:**
- `docs/working/cas_v7_5_rollout_plan.md`
- `docs/working/cas_v7_6_rollout_plan.md`
- `docs/working/cas_v7_7_rollout_plan.md`

---

# ADR-01: FiLM Modulation for Phenomenological Register Integration

## Status
Accepted — 2026-04-22 (CAS-Native v2 specification session)

## Context

CAS v7.5 (Clarification 8) introduces the Phenomenological Register as a second orthogonal axis to the Noetic Topos. Each of the 40 Cognitive States (10 Noetics × 4 Domains) and each of the 7 Core Drives can operate in any of four Registers: `|T` (Transcendent), `|A` (Analytical), `|f` (Affective, lowercase authoritative), `|E` (Embodied). Register involution pairs: `|T ↔ |E`, `|A ↔ |f`.

The neural architecture question: **how is the Register axis represented in CAS-Native v2 parameters and computations?**

The v7.4 scaffolding implements only the 40-state bank (`CognitiveStateEmbedding`, 10 Noetics × 4 Domains) with no register representation. v2 must extend this.

Five implementation architectures were considered: expanded 160-slot bank, orthogonal register embedding, factorized bilinear combination, FiLM modulation, complex-valued phase encoding.

Constraints informing the decision:
- Framework-fidelity to Clarification 8's characterization of Register
- Parameter budget (target: v2 additions < 1% of a 50M-parameter demonstration model)
- Device-space / load-time / runtime compatibility with edge deployment
- Quantization tractability for int8 / int4 deployment
- Involution pair structural expression in parameters

## Decision

**FiLM (Feature-wise Linear Modulation)** — Perez et al. 2018 — for register integration.

Mathematical form:

```
state_output[R] = γ[R] ⊙ state + β[R]
```

Where:
- `state` is the 40-slot base cognitive state vector (dim `d = 128`)
- `γ[R]`, `β[R]` are per-register learned modulation parameters (each dim `d`)
- `⊙` is element-wise (Hadamard) product
- `R ∈ {T, A, f, E}`
- Register-unspecified (v7.4 backward-compatible) = identity modulation: `γ = 1`, `β = 0`

**Parameter budget:** 4 registers × 2 × 128 = **1,024 parameters** for FiLM modulation.

**Register embedding dimension:** `d = 128`, matching the 40-state bank dimension.

**Involution pair constraint: SOFT (via loss function), NOT hard architectural enforcement.**

All four register FiLM parameter pairs `(γ, β)` are learned independently. The training loss includes a regularizer:

```
L_involution = λ × (
    ‖γ_T ⊙ γ_E − 1‖² +
    ‖β_T + β_E‖² +
    ‖γ_A ⊙ γ_f − 1‖² +
    ‖β_A + β_f‖²
)
```

The constraint encodes: involution partners are multiplicative inverses in γ (`γ_T ⊙ γ_E = 1`) and additive inverses in β (`β_T + β_E = 0`). Applying register `|T` then register `|E` returns to the unmodulated state, structurally matching the involution relation.

`λ` is a hyperparameter. Starting value `λ = 0.1`; tunable based on training dynamics.

## Alternatives Considered

### Option A — Expanded 160-slot bank (10 × 4 × 4 embedding table)

Replace the 40-state bank with a 160-slot table indexed by (Noetic, Domain, Register).

Parameter cost at d=128: 160 × 128 = 20,480 (20× larger than FiLM).

**Rejected because:**
- 4× memory footprint vs v7.4 baseline
- No structural encoding of register as modulation — register-specific entries can diverge arbitrarily in training, losing the framework's "same state, different operational character" semantic
- Multiplicative parameter scaling with any future axis addition (v7.8 adding any new axis ×4)
- Involution pair structure not architecturally expressible (just tied embeddings, same option available to FiLM with less parameter cost)

### Option B — Orthogonal register embedding (40 state bank + 4 register embedding table)

Separate 40-state bank (10 × 4) and 4-slot register table. Composed at inference via addition or concatenation.

Parameter cost (embedding tables only): 40 × 128 + 4 × 128 = 5,632.

**Rejected because:**
- Downstream parameter inflation: concatenation doubles input dim of next layer, multiplying that layer's parameters by 2. Addition loses the multiplicative interaction that gives modulation its expressive character.
- Less natural fit with the differential-geometry analogy (Clarification 8 §1 line 263) — orthogonal augmentation is not a coordinate transformation of the base state
- Defensible as second-best framework fidelity — explicitly acknowledged below — but no parameter-efficiency advantage over FiLM

This is the honest second-choice architecture. Revisit if FiLM exhibits training pathology.

### Option C — Factorized with low-rank bilinear interaction

Decompose into 10-dim Noetic embedding + 4-dim Domain embedding + 4-dim Register embedding, combined via learned bilinear layer.

Parameter cost: ~262K (dominated by bilinear combination layer).

**Rejected because:**
- Parameter count inflation (250× vs FiLM) without commensurate expressive gain
- Training complexity: bilinear layers are gradient-sensitive, require careful initialization
- Least interpretable of the options — composition is a black-box bilinear layer

### Option E — Complex-valued embedding with phase rotation

Represent cognitive states as complex vectors of dim `d/2`; encode register as phase rotation (`|T` = 0°, `|A` = 90°, `|f` = 180°, `|E` = 270°). Involution pairs naturally emerge as 180° phase shifts.

Parameter cost: similar to FiLM.

**Rejected because:**
- Infrastructure risk: PyTorch `torch.complex64`/`complex128` support exists but is less mature than real-valued tensor support
- 2× compute overhead from complex arithmetic (though GPU-compatible)
- Downstream layers (attention, FFN) don't naturally extend to complex arithmetic in a principled way — either requires research-grade extensions or projection back to real (losing the complex structure benefit)
- Beautiful but speculative; premature for v2

## Consequences

### Parameter budget impact
- v2 additions for register axis: **1,024 parameters**
- For a 50M demonstration model: <0.01% overhead
- Fits int8 quantization without architectural gymnastics

### Runtime cost
- FiLM forward pass: one element-wise multiply + one element-wise add per register application
- Device-friendly: fast on all modern GPU/CPU/TPU/edge accelerators

### Load time
- 1,024 parameters = ~4 KB at fp32, ~1 KB at int8
- Negligible load-time delta

### Training implications
- FiLM training is well-understood (Perez et al. 2018, StyleGAN variants, many production systems)
- Soft involution constraint requires hyperparameter `λ` tuning; start at 0.1
- Register-neutral (v7.4) backward compatibility: identity modulation means model can process register-unspecified inputs without any additional machinery

### Extensibility
- If CAS v7.8 or later adds new register values (currently not anticipated — the 4-register axis is cross-validated against TKS 4-Worlds and theoretically closed), extension is additive: new `(γ, β)` pair per added register, no architectural change.
- Involution pair structure is enforced by loss, not by architecture. This preserves capacity for empirical signal to refine the involution relation if framework-level adjustment is needed.

### IP implications
- FiLM itself is not CAS-Native's novelty (Perez et al. 2018 prior art)
- CAS-Native's novelty is using FiLM specifically for Phenomenological Register modulation over the 40-state bank, with involution-constrained learning
- The combined architecture (40-state bank + register FiLM + cross-register binding + production semantics) is the continuation-in-part territory relative to the 2026-04-12 provisional disclosure

## Framework Fidelity Notes

### What Clarification 8 commits to (verbatim)

Clarification 8 §1 line 261:
> "specifying the operational character of the cognitive operation without changing what the operation IS"

Clarification 8 §1 line 263:
> "Register is a specification of operational character layered on top of the existing primitives, analogous to how coordinate system choice in differential geometry does not modify the underlying manifold structure"

### How FiLM maps to these commitments

FiLM is a smooth invertible affine map parameterized by the register choice. The base state vector is preserved; only its operational character is transformed by the modulation. This mechanistically implements "without changing what the operation IS" — the unmodulated state remains recoverable by applying the identity FiLM (and by applying the involution partner's modulation to the register-modulated state, the state returns to unmodulated form via the involution constraint).

The differential-geometry analogy (coordinate-choice to manifold) maps cleanly to FiLM: the manifold point (cognitive state) is invariant; different coordinate systems (registers) give different numerical descriptions (modulated feature values) of the same point; the transformation between descriptions (involution pairs) is a diffeomorphism.

### Honest acknowledgment of spec openness

**Clarification 8 does NOT explicitly commit to modulation over orthogonal augmentation.** The word "modulation" does not appear in Clarification 8. The coordinate-choice-to-manifold analogy provides weak guidance toward modulation/transformation-style implementations over orthogonal-augmentation-style implementations, but the analogy is not dispositive.

Earlier in this specification session, a claim was made that Clarification 8 mandates FiLM. That claim overreached. The correct position:

1. FiLM has a **stronger framework-fidelity argument** than orthogonal embedding — it more naturally implements the coordinate-transformation analogy (diffeomorphism reading) — but is not **required** by Clarification 8.
2. Orthogonal embedding (Option B) satisfies Clarification 8's explicit commitments (non-alteration of base 40-state structure, axioms unchanged, Universal Applicability preserved). It is **not prohibited**.
3. The choice between them is legitimately an architectural trade-off, not a framework-compliance gate.

This ADR chooses FiLM on a combination of:
- Best fit with the differential-geometry analogy (weak framework-fidelity lean)
- Smallest parameter footprint of the framework-plausible options
- Natural involution-structure interpretation (constraint as inverse transformation, mechanistically meaningful)
- Device / quantization / load-time profile

The framing is "best fit with Clarification 8 spirit." Not "mandated by spec."

## Implementation Notes

### New class: `CognitiveStateEmbeddingWithRegister`

Extends the existing `CognitiveStateEmbedding` additively:

```
cas-native/model/embedding.py:
  class CognitiveStateEmbedding:  # EXISTING, preserved
    def __init__(self, d_model=128, num_states=40): ...

  class CognitiveStateEmbeddingWithRegister(CognitiveStateEmbedding):  # NEW
    def __init__(self, d_model=128, num_states=40, num_registers=4):
      super().__init__(d_model, num_states)
      self.register_gamma = nn.Parameter(torch.ones(num_registers, d_model))
      self.register_beta = nn.Parameter(torch.zeros(num_registers, d_model))
      # Identity initialization: γ=1, β=0 → register-neutral at start of training.

    def apply_register(self, state, register_idx):
      # register_idx ∈ {0,1,2,3} for T/A/f/E, or None for register-neutral.
      if register_idx is None:
        return state
      return self.register_gamma[register_idx] * state + self.register_beta[register_idx]
```

### Loss function extension

In `cas-native/model/loss.py`, extend `CognitiveMetricLoss` with an `involution_loss` method computing `L_involution` as specified in the Decision section. Add `lambda_involution` (default 0.1) to the loss configuration.

### Integration point

Register application lives between embedding lookup and downstream attention/FFN layers. One FiLM application per state per layer where register matters. A register-neutral forward pass skips the FiLM call entirely (no computation cost, no parameter touch).

### Testing

Unit tests for `CognitiveStateEmbeddingWithRegister`:
- Register-neutral input produces unchanged state (identity FiLM verified)
- Involution pair test at initialization: `apply_register(apply_register(state, T), E) ≈ state` with tolerance (at init with γ=1, β=0, exactly true; during training, within tolerance driven by `λ`)
- Gradient flow: register parameters receive gradient when register is applied

---

# ADR-02: Metric-Learning Binding for Emergent Register Mechanism

## Status
Accepted — 2026-04-22 (CAS-Native v2 specification session)

## Context

CAS v7.7 Clarification 10 admits same-Noetic cross-register integration under Rule 4: expressions of the form `(^n|R₁ × ^n|R₂ × ...) = ^n|Ω_name` are admissible only when the emergent result is explicitly named. Rule 4 is architecturally load-bearing — it distinguishes redundant co-presence (`+`) from unified emergent integration (`×` with named result) from static architecture specification (`|⟨…⟩`).

The neural architecture question: **how does CAS-Native v2 produce and recognize named emergent registers (Ω_*)?**

The current v7.4 scaffolding has no mechanism for cross-register integration or emergent register output. The Rust engine (post-Wave-3, commit `b5c5694`) has `RegisterSet`, `NamedEmergentRegister`, and `validate_same_noetic_cross_product` validator — these govern admissibility but do not produce emergent states.

Four implementation architectures were considered: dedicated composition head, vocabulary extension, runtime symbolic composition, k fixed integration heads. Plus one novel approach (metric-learning binding into continuous emergent-register space) not in the original alternatives list.

Constraints informing the decision:
- Parameter budget scaling with registry size (the Clarification 10 Ω_* registry is open-ended; Appendix I admits Ω_presence and Ω_refusal currently with anticipated growth)
- Extensibility: can new Ω_* be added without retraining?
- Novel Ω_* discovery: can the architecture identify candidate emergent states not yet in the registry?
- Framework fidelity to Clarification 10 semantics (cross-register integration produces a distinct state, not a detection pattern)
- Integration with the Rust engine as ground truth for Rule 4 validation

## Decision

**Metric-learning binding into emergent-register-space (ER-space).**

Architecture:

1. **Prerequisite gate** (zero new parameters): pure arithmetic on register activations. Detects same-Noetic same-Domain multi-register activation above a threshold. If fewer than 2 registers co-active above threshold at a (Noetic, Domain) position, the binding layer is not invoked.

2. **Binding layer** (Hadamard-product fold + single linear projection): the register-modulated state instances at the gated position are folded by element-wise product across the register axis, then projected through one linear layer `W : ℝᵈ → ℝᵈ` into ER-space. Parameters: `d²` = 16,384 (the projection weight matrix; no bias). Element-wise Hadamard product preserves bilinear-style interaction between register instances at `O(d)` composition cost; the learned projection shapes ER-space geometry. A full `nn.Bilinear(d, d, d)` would be `d³ ≈ 2.1M` parameters and is deliberately avoided — the Hadamard-plus-projection formulation achieves the binding semantics at `d²` cost.

3. **Ω_\* registry as lookup embeddings**: each admitted Ω_* in the registry (per Appendix I of `FULL_MANUSCRIPT.md`) is represented as a point in ER-space. Lookup table dimensions: `registry_capacity × d`. v1 registry capacity: 20 (current admitted = 2: Ω_presence, Ω_refusal; capacity headroom for near-term growth).

4. **Activation via similarity**: cosine similarity (or a learned metric) between the binding layer output and each registered Ω_* embedding. The closest registered Ω_* above a similarity threshold is reported as active. Continuous similarity scores are emitted per Ω_*, giving graded activation.

5. **Novel emergent detection**: binding outputs that are far from all registered Ω_* embeddings (below all similarity thresholds) are flagged as **candidate emergents** — potential new entries for Appendix I registry review under the Clarification 10 admission process.

**Parameter cost:**
- Binding layer: `d² = 16,384`
- Registry (capacity 20, d=128): `20 × 128 = 2,560`
- Total ADR-02 parameters: **~18,944**

Growth profile:
- v1 (k=2 admitted, capacity 20): 18,944 parameters
- k=20 (registry at designed capacity): 18,944 parameters (no allocation change; unused slots carry random-init embeddings)
- k=100 (registry expanded to 100 entries): `16,384 (binding) + 100 × 128 (registry) = 29,184` parameters

## Alternatives Considered

### Option A — Dedicated RegisterCompositionHead

One attention head specialized for cross-register integration patterns, producing a single output.

**Rejected because:**
- Single-head architecture cannot distinguish multiple admitted Ω_* (collapses all emergents to one output distribution)
- Extensibility: adding Ω_* requires retraining the head
- Loses the per-Ω_* identity semantics Clarification 10 requires

### Option B — Vocabulary extension (Ω_* as output tokens)

Add Ω_* labels to the model's output vocabulary. Model learns which register combinations produce which Ω_* from training data. No new architectural component.

**Rejected because:**
- Rule 4 enforcement becomes external (post-hoc validator only); architecture does not guarantee prerequisite
- Implicit learning of integration structure risks framework drift
- Ω_* vocabulary must be closed at training time (no hot-swap new emergents)
- No introspection path to identify which states integrated

### Option C — Runtime symbolic composition

Detect same-Noetic different-register active simultaneously; Rule 4 validated by Rust engine; emergent register computed via learned composition function only when validation passes.

**Rejected because:**
- Multi-stage runtime (detection → validation → composition) introduces latency
- Python/Rust boundary crossing on every inference = PyO3 overhead per forward pass
- Not end-to-end differentiable — gradient flow through symbolic validation step requires REINFORCE-style approximation

### Option D — k fixed integration heads (one head per admitted Ω_*)

One specialized detection head per registered Ω_*. Head `i` fires when its target pattern is present at its prerequisite.

**Rejected because:**
- Parameter count scales with registry size: `k × d² = 327,680` at k=20, `1,638,400` at k=100. Against ADR-02's metric-learning binding (18,944 at k≤20; 29,184 at k=100) that is ~17× larger at k=20 and ~56× larger at k=100 — an order of magnitude worse on parameter economy, growing with registry size
- Fixed vocabulary — adding Ω_* requires retraining
- Heads learn a DETECTION pattern, but Clarification 10's Ω_presence isn't a detection target — it's an emergent state in its own right
- No novel Ω_* discovery capability — model is blind to patterns outside its fixed head set

This was the strongest candidate before metric-learning binding was considered. Parameter economy and extensibility arguments decided against it.

## Consequences

### Parameter budget impact
- v1 (k=2 admitted): 18,944 parameters
- ~17× smaller than k-heads approach at k=20 (18,944 vs 327,680)
- ~56× smaller at k=100 (29,184 vs 1,638,400)

### Extensibility at inference time
- New Ω_* added by inserting its embedding into the registry lookup table (one row of 128 fp32 = 512 bytes)
- Model similarity comparison naturally includes the new row
- No retraining required
- Aligns with Clarification 10's open-ended Ω_* admission process (Appendix I registry)

### Novel Ω_* discovery
- Binding layer outputs that are far from all registered Ω_* are candidate emergents
- This is a feature: CAS-Native can propose new Ω_* for registry review under the six-stage admission process (Appendix I)
- Feedback loop: empirical candidate discovery → human review via triple-gate analysis → registry admission → new Ω_* becomes part of the model's recognized vocabulary

### Runtime cost
- Binding layer: one bilinear operation per prerequisite-gated position (fast on GPU)
- Similarity computation: `k × d` per emergent check (trivial)
- Overall: O(d²) per cross-register integration event, compared to O(k × d²) for k-heads approach

### Training implications
- Binding layer requires training signal for where in ER-space to place outputs
- Rust engine serves as oracle during training: when model produces an output, Rust validates Rule 4 compliance and returns the target Ω_* identity. Loss pulls binding output toward the corresponding registry embedding.
- Novel binding outputs (candidate emergents) during training are logged but not penalized — they become empirical candidates for registry growth.

### Framework fidelity alignment
- Clarification 10's admission process (pedagogical trial → evidence accumulation → triple-gate analysis → authoritative admission) matches metric-learning binding's extensibility naturally. The registry grows; the architecture does not change.

## Framework Fidelity Notes

Clarification 10 does not specify implementation architecture for Ω_* production. It specifies:

1. **Rule 4 admissibility** (Clarification 10 Section 4): same-Noetic multi-register `×` requires explicit emergent result or fusion semantics.
2. **Registry admission process** (Appendix I of `FULL_MANUSCRIPT.md`, admitted 2026-04-21, commit `1eb62c6`): six-stage workflow from structural identification to authoritative admission.
3. **Three-way operator distinction** (Clarification 10 Section 2): `|⟨…⟩`, `+`, `×` with named result.

Metric-learning binding satisfies all three:
- Rule 4 enforced architecturally by prerequisite gate (same-Noetic same-Domain multi-register activation required before binding layer fires)
- Registry admission matches metric-learning extensibility (new admitted Ω_* = new registry row)
- Three-way distinction enforced upstream (by compiler and parser); CAS-Native only engages the `×` branch when it applies

This is a pure engineering decision. No framework-fidelity claim is made beyond "matches Clarification 10's admission-process semantics naturally."

## Implementation Notes

### New class: `EmergentRegisterBindingHead`

```
cas-native/model/emergent_register.py (new file):
  class EmergentRegisterBindingHead(nn.Module):
    def __init__(self, d_model=128, registry_capacity=20):
      super().__init__()
      # Hadamard-product fold + single linear projection — d² params.
      # A full nn.Bilinear(d, d, d) would be d³ ≈ 2.1M params; avoided.
      self.binding_projection = nn.Linear(d_model, d_model, bias=False)
      self.registry = nn.Parameter(torch.randn(registry_capacity, d_model))
      self.registry_names = []  # List[str], e.g., ["Ω_presence", "Ω_refusal"]
      self.active_registry_size = 2  # Grows as Ω_* admitted.
      self.similarity_threshold = 0.7  # Tunable.

    def forward(self, register_modulated_states, prereq_mask):
      # register_modulated_states: shape (..., num_registers, d_model)
      # prereq_mask: True where same-Noetic same-Domain multi-register is active.
      # Fold across register axis by element-wise product, then project.
      folded = register_modulated_states.prod(dim=-2)  # (..., d_model)
      bound = self.binding_projection(folded)          # (..., d_model) — ER-space output
      # Mask out positions that did not pass the prerequisite gate.
      bound = bound * prereq_mask.unsqueeze(-1)
      # Similarity to every registered Ω_* — returns per-Ω_* score + novelty flag.
      # Returns: {registry_name: similarity_score, ...}, candidate_output (if novel).
      ...
```

### Rust engine integration

The `NamedEmergentRegister` type lives in `cas-engine/src/ontology/register_set.rs` (Wave 3 commit `b5c5694`); the Rule 4 validator `validate_same_noetic_cross_product` lives in `cas-engine/src/validation/rule_four.rs`. The training-time oracle invokes the validator via PyO3 to verify Rule 4 and return the registry-matching Ω_* identity.

### Registry synchronization

Registry entries in `FULL_MANUSCRIPT.md` Appendix I must be kept in sync with the model's `registry_names`. On new Ω_* admission:
1. Human review via triple-gate analysis (per Appendix I)
2. New entry in Appendix I
3. New row allocated in model's `registry` tensor (random init; training signal from Rust oracle)

### Testing

Unit tests for `EmergentRegisterBindingHead`:
- Prerequisite gate: outputs zero when fewer than 2 registers active at any (Noetic, Domain)
- Registered Ω_* recognition: synthetic inputs corresponding to known Ω_presence / Ω_refusal patterns produce high similarity to correct registry entries
- Novel candidate detection: synthetic inputs far from registry produce low similarity across all entries and are flagged as candidates
- Registry growth: adding a registry row does not perturb existing recognition behavior

---

# ADR-03: Ω_* Output Head Design (Derivative of ADR-02)

## Status
Accepted — 2026-04-22 (CAS-Native v2 specification session)

## Context

Given ADR-02's choice of metric-learning binding, the Ω_* "output head" is defined by the binding architecture. This ADR documents the output-head-specific design decisions flowing from ADR-02.

## Decision

**Activation format: continuous strength per Ω_\*.**

The model emits a similarity score per registered Ω_* (cosine similarity or learned metric distance). This provides graded activation reflecting the empirical reality of emergent states — Ω_presence is not binary present/absent but varies in strength across cognitive contexts.

**Vocabulary policy: fixed at training time for v1, hot-swappable at inference time.**

- Training: registry size fixed at 20 slots (capacity for growth beyond currently-admitted 2: Ω_presence, Ω_refusal). All 20 slots participate in loss and gradient updates.
- Inference: new Ω_* admitted post-training can be added to the registry lookup table without retraining. Model similarity comparison naturally includes the new row.
- Growth beyond 20: reallocate registry tensor (one-time cost); revisit if registry exceeds 20 entries.

**Rule 4 enforcement: two-layered.**

- **Architectural prerequisite gate** (from ADR-02): binding layer only fires when same-Noetic same-Domain multi-register activation is present. Structurally enforces the precondition for licensed `×`.
- **Rust post-hoc validation**: at inference time, model outputs flagged with Ω_* attribution are validated against Rust engine's `validate_same_noetic_cross_product`. Mismatch between model claim and Rust validation is logged as a training signal (via ADR-06's batch validation path).

**Conservative defaults flagged explicitly:**

- Similarity threshold `0.7` (ADR-02 code sketch) is a placeholder default. **No empirical basis yet** — the threshold should be tuned against first-training-run validation data. Too low risks promoting noisy binding outputs to false Ω_* matches; too high risks rejecting genuine Ω_* activations. Tuning priority is flagged in the Follow-ups section.

## Alternatives Considered

### Binary activation (present/absent)
**Rejected:** loses graded semantic. Clarification 10 Section 5 describes emergent registers as varying in strength across architectures and conditions — binary collapses this.

### Full distribution over vocabulary (softmax)
**Rejected:** forces exclusive Ω_* attribution when empirically multiple emergents may be co-active (rare but possible). Independent per-Ω_* similarity scores preserve this.

### Open-vocabulary at training time (registry never fixed)
**Rejected:** training requires a fixed output space for gradient flow. Fixed training-time vocabulary + inference-time hot-swap is the established pattern (matches how word embedding models handle rare-word additions without retraining).

## Consequences

### Parameter budget
Already counted in ADR-02: 2,560 parameters for registry (20 × 128).

### Training signal
Each of the 20 registry slots receives gradient when training examples include the corresponding Ω_*. Unused slots (v1 has 18 unused at k=2) still participate in similarity computation but receive minimal gradient; they drift toward noise unless regularized.

**Follow-up flagged:** add a regularization term pulling unused registry embeddings toward a "null" point in ER-space (so they don't accidentally match real patterns). Exact form tunable; placeholder: L2 penalty on unused-slot norm.

### Inference efficiency
Per-forward-pass Ω_* check: 20 × 128 = 2,560 floating-point operations for cosine similarity. Negligible on modern hardware.

### Registry synchronization
The model's `registry_names` list must be kept in sync with Appendix I. Configuration file `cas-native/config/omega_registry.yaml` (new) maintains the authoritative mapping from registry slot index to Ω_* name, matching Appendix I entries.

## Framework Fidelity Notes

Clarification 10 does not specify activation format, vocabulary growth policy, or enforcement layering. This ADR makes engineering choices compatible with Clarification 10's registry semantics.

The "hot-swappable at inference" design specifically honors Clarification 10 Appendix I's admission-process workflow: Ω_* can be admitted to the registry after the current model is trained, and the model must accommodate without full retraining. Metric-learning binding + lookup-table registry naturally provides this.

## Implementation Notes

Registry config file:

```yaml
# cas-native/config/omega_registry.yaml
version: 1
admitted:
  - slot: 0
    name: "Ω_presence"
    appendix_i_ref: "Entry 1"
  - slot: 1
    name: "Ω_refusal"
    appendix_i_ref: "Entry 2"
capacity: 20
reserved_slots_for_growth: 18
```

Loading logic reads this config at training/inference startup; registry tensor is initialized according to admitted entries; unused slots are randomly initialized.

---

# ADR-04: Hybrid Production Semantics (CAS v7.6)

## Status
Accepted — 2026-04-22 (CAS-Native v2 specification session)

## Context

CAS v7.6 Clarification 9 introduces Stoichiometric Production Semantics: recipes, yields, limiting reagents, leakage, catalysts, inhibitors. The Rust engine (post-Wave-3) implements these types — `Recipe`, `Yield`, `LimitingReagent`, `Leakage` — with exact symbolic computation.

The neural architecture question: **how does CAS-Native v2 reason about production semantics — symbolically, learned, or hybrid?**

Three baseline approaches plus one differentiable-approximation approach considered.

Constraints:
- Framework fidelity: production semantics is mathematical (`Y_T = min_i(x_i / a_i)`, limiting reagent = `argmin_i(x_i / a_i)`) — these have exact answers
- Gradient flow: model needs end-to-end training signal from yield accuracy back to recipe identification
- Inference correctness: production values reported must be mathematically correct, not approximate
- Rust engine already implements exact computation

## Decision

**Hybrid: learned identification + symbolic computation at inference; differentiable stoichiometry approximation for gradient flow at training.**

Same architecture, two execution modes.

### Recipe head (~10,000 parameters)

Outputs:
- **Prerequisite identification**: logits over the 40-state × 4-register × 7-drive space for each recipe prerequisite slot
- **Coefficients**: positive reals (softplus-activated) for `a_i` values
- **Leakage identification**: logits for `Λ` side-reactions, plus their magnitudes

### Inference path (hard symbolic)

Recipe head outputs → discretize prerequisite identifications (argmax) → pass to Rust engine → Rust computes:
- `Y_T = min_i(x_i / a_i)` (theoretical yield)
- `L = argmin_i(x_i / a_i)` (limiting reagent)
- `Y_A` (actual yield from observation)
- `η = Y_A / Y_T` (efficiency)
- `ε_i` (excess capacity per non-limiting prerequisite)

Exact math. Fast. Correct.

### Training path (soft differentiable)

Same recipe head outputs, but:
- Prerequisite identification: Gumbel-softmax relaxation (temperature annealed from high to low during training)
- Theoretical yield: soft-min via log-sum-exp approximation:
  ```
  Y_T_soft = -τ × log(Σ_i exp(-(x_i / a_i) / τ))
  ```
  with temperature `τ` annealed from high (smooth) to low (sharp min) during training
- Limiting reagent: soft-argmin using softmax attention over the **negated** ratios `-(x_i / a_i)` (equivalently: softmin over `(x_i / a_i)`). A plain softmax over unnegated ratios would produce soft-argmax and pick the *largest* ratio, which is the opposite of the limiting-reagent semantics.

Fully differentiable. Gradient flows: `yield error → prerequisite identification logits → embeddings`.

### Two-mode pattern

- **At training**: soft version computes loss, gradient propagates end-to-end through the differentiable stoichiometry
- **At inference**: hard version invokes Rust engine for exact math
- **Consistency guarantee**: as `τ → 0`, soft version converges to hard version; near end of training, the two agree

This is the Gumbel-softmax / straight-through estimator pattern applied to stoichiometric operators.

## Alternatives Considered

### Option A — Fully symbolic (model outputs only cognitive state activations, Rust computes everything)

**Rejected because:**
- Model has no end-to-end training signal for production semantics
- Recipe identification would have to be learned implicitly from downstream task loss — slow, noisy
- No way for the model to reason about production during generation

### Option B — Fully learned (model outputs recipe structures, yields, limiting reagents directly as learned)

**Rejected because:**
- No verification of mathematical correctness — model may learn incorrect production logic (e.g., violate `min` semantics)
- Duplicates the Rust engine's work with less rigor
- Inference-time yield values would be approximations, not exact

### Option D alone — Differentiable stoichiometry without symbolic inference path

**Rejected because:**
- Soft-min approximation introduces bounded error at inference time
- Rust engine already implements exact computation — not using it at inference is wasteful
- Downstream consumers (dashboard, peer-review paper, regulatory-facing reports) need exact values

## Consequences

### Parameter budget
Recipe head: ~10,000 parameters. Dominant cost is prerequisite identification projection (d × 40 × 4 × 7 ≈ 143,360 logits; achievable with low-rank projection at ~10K parameters).

### Runtime cost
- Inference: one Rust engine call per recipe analysis (PyO3 crossing, ADR-06 batch API)
- Training: log-sum-exp and Gumbel-softmax operations (standard PyTorch ops, GPU-efficient)

### Training stability
- Temperature annealing schedule for `τ` must be tuned; start linear from 10.0 → 0.1 over training
- Recipe head logits require standard classification-training hygiene (label smoothing, class-weight balancing if recipe distribution is skewed)

### Inference correctness
- All published yield values are exact symbolic computations from Rust
- Model's differentiable approximation is training-only, never reported

### Future research extension
- Fully differentiable production semantics (Option D alone) becomes a research paper extension — replacing the symbolic inference path with the differentiable version would allow gradient flow at inference for certain applications (model-predictive optimization over production targets). Out of scope for v2.

## Framework Fidelity Notes

Clarification 9 specifies the mathematical semantics of production operators (`min`, `argmin`, ratio, efficiency). It does not specify implementation architecture. The Rust engine implements the hard mathematics; this ADR specifies how the neural model interacts with that math.

The hybrid pattern is framework-faithful at inference (exact math per Clarification 9) and training-friendly (gradient flow via well-established differentiable approximations). Both modes converge as training progresses.

## Implementation Notes

### New class: `ProductionSemanticsHead`

```
cas-native/model/production_semantics.py (new file):
  class ProductionSemanticsHead(nn.Module):
    def __init__(self, d_model=128, max_prerequisites=8, num_cognitive_states=40):
      ...
    def forward(self, hidden_states, mode="inference"):
      prereq_logits = ...
      coefficients = ...
      leakage_logits = ...
      if mode == "training":
        return self._soft_compute_yield(prereq_logits, coefficients, tau=self.tau)
      else:  # inference
        return self._hard_compute_yield_via_rust(prereq_logits, coefficients)
```

### Rust engine integration

Per ADR-06's task queue, `cas-engine` will expose `compute_yield_batch` for batch inference (likely in `cas-engine/src/scoring/yield_calc.rs`, alongside the existing `theoretical_yield`, `limiting_reagent`, `excess_capacity`, and `efficiency` functions; `Recipe` and `Leakage` live at `cas-engine/src/ontology/recipe.rs`). Rust receives prerequisite identities + coefficients + observed quantities, returns `(Y_T, L, Y_A, η, ε_i)` tuple per batch element. Function is **pending implementation** — not yet present in the Rust codebase.

### Temperature scheduling

Training config:

```yaml
production_semantics:
  tau_initial: 10.0
  tau_final: 0.1
  tau_schedule: "linear"  # or "exponential", "cosine"
  tau_anneal_over_steps: 50000
```

### Testing

Unit tests for `ProductionSemanticsHead`:
- Training vs inference consistency: as `τ → 0`, soft-min agrees with hard-min
- Gradient flow: yield loss produces non-zero gradients on prerequisite identification logits
- Rust integration: hard path returns same values Rust computes for manually-specified recipes
- Limiting reagent correctness: argmin via soft-argmax at low temperature matches hard argmin

---

# ADR-05: Backward Compatibility — Clean Redesign

## Status
Accepted — 2026-04-22 (CAS-Native v2 specification session)

## Context

CAS-Native v7.4 weight audit completed 2026-04-22 (this session). Finding: **no production weights exist**. Architectural scaffolding only. Zero `.pt`, `.pth`, `.ckpt`, `.safetensors`, or `.bin` files in any `cas-native/` directory. No checkpoint directories. No training logs. Git history shows commits adding training infrastructure but no commits completing training runs.

The backward-compatibility question reduces from "how do we transfer trained weights?" to "what structural invariants must v2 preserve for IP continuity?"

## Decision

**Clean architectural redesign, preserving the 40-state bank STRUCTURE (not weights) for IP continuity.**

- `CognitiveStateEmbedding` class preserved as named architectural component — the 40-state Noetic × Domain bank remains recognizable in v2 source code and architectural documentation
- All new components (`CognitiveStateEmbeddingWithRegister`, `EmergentRegisterBindingHead`, `ProductionSemanticsHead`, extensions to existing components) start from random init
- First training run of v2 is also the project's first training run of any kind
- No transfer-learning complexity
- No freeze/unfreeze phases needed
- Standard fresh-training workflow

## Alternatives Considered

### Weight transfer learning (freeze-then-unfreeze)

This was my earlier recommendation. **Rejected because:** the weight audit invalidated its premise. There are no weights to transfer.

### Full ground-up rewrite abandoning existing class structure

**Rejected because:** IP continuity with the 2026-04-12 provisional disclosure requires the 40-state bank and domain-descent attention to remain recognizable architectural components. Fully renaming or restructuring these would weaken the continuation-in-part argument.

## Consequences

### Implementation simplification
ADR-05 simplifies significantly as a result of the weight audit. Standard training workflow applies. No multi-phase freeze/unfreeze schedule.

### Architectural freedom on Q1 and Q2
ADR-01 (FiLM) and ADR-02 (metric-learning binding) were partially chosen on framework-fidelity and parameter-economy grounds. Earlier analysis included "ease of transfer from v7.4 weights" as a tiebreaker. That tiebreaker is void. Both ADR-01 and ADR-02 decisions are unaffected by this reassessment — they remain correct on their framework-fidelity and parameter-budget arguments.

### IP implications

- 40-state bank structure preservation is load-bearing for `ip/CAS_NATIVE_ARCHITECTURE_PROVISIONAL_DISCLOSURE.md` (2026-04-12, 540 lines) continuation-in-part
- v2 additions (Register FiLM, cross-register metric-learning binding, Ω_* registry, production semantics, Rule 4 architectural enforcement) are new matter
- **IP attorney consultation required** before public disclosure of v2 architecture beyond this internal specification
- arXiv submission, peer-review paper describing v2 architecture, and utility patent filing ALL gate on IP attorney consultation
- Internal drafting and training may proceed in parallel with pending IP consultation — no material dependency

### Implication for synthetic data generator (next project phase per directive sequencing)

Since no v7.4 training baseline exists, the CAS Synthetic Data Generator (next scheduled work) must produce training data covering the **full v2 architecture from day one**. There is no "v7.4 data we extend later" fallback. This means the data generator must include:

- Cognitive state examples with register annotations (all four registers represented across all Noetic × Domain cells)
- Cross-register integration examples with Rule 4 compliance (both valid `×` with named emergent result, and invalid same-Noetic multi-register `×` requiring rewrite)
- Ω_* labeled examples for Ω_presence and Ω_refusal (initial registry)
- Production semantics examples with recipes, yields, limiting reagents, and leakage instances
- Inversion and lacunarity examples spanning the full 7-axis taxonomy

Data generator pipeline implications are flagged for the next ADR series when data generator architecture is specified.

## Framework Fidelity Notes

No framework fidelity concerns. This ADR is purely about engineering workflow and IP continuity. Framework adherence is handled by the other ADRs.

## Implementation Notes

### Class structure (preserved names, additive extensions)

```
cas-native/model/
├── embedding.py
│   ├── CognitiveStateEmbedding            (PRESERVED from v7.4)
│   └── CognitiveStateEmbeddingWithRegister (NEW, extends above)
├── domain_descent.py
│   └── DomainDescentAttention             (PRESERVED from v7.4)
├── rpm_gate.py
│   └── PrerequisiteGateLayer              (PRESERVED from v7.4)
├── fractal_attention.py
│   └── FractalAttentionHead               (PRESERVED from v7.4)
├── topos_reasoner.py
│   └── CognitiveToposReasoner             (PRESERVED from v7.4)
├── composition.py
│   └── GenerativeHead                     (PRESERVED from v7.4)
├── lacunarity_gate.py
│   └── LacunarityGate                     (PRESERVED from v7.4)
├── lacunarity_head.py
│   └── LacunarityHead                     (PRESERVED from v7.4)
├── emergent_register.py                   (NEW file)
│   └── EmergentRegisterBindingHead        (NEW, per ADR-02)
└── production_semantics.py                (NEW file)
    └── ProductionSemanticsHead            (NEW, per ADR-04)
```

### Training workflow

Standard single-phase training. No freeze/unfreeze choreography. Config file `cas-native/config/training_v2.yaml` (new) specifies hyperparameters, data paths, eval frequency, checkpoint schedule.

---

# ADR-06: Rust Engine Alignment

## Status
Accepted — 2026-04-22 (CAS-Native v2 specification session)

## Context

The Rust CAS engine (post-Wave-3, commits `b5c5694` and following) implements authoritative framework validation:
- `Register`, `RegisterSet`, `NamedEmergentRegister` types
- `validate_same_noetic_cross_product` (Rule 4)
- `Recipe`, `Yield`, `LimitingReagent`, `Leakage` (production semantics)
- PyO3 bindings

The Python CAS-Native model needs to interact with this engine across the PyO3 boundary. The architecture question: **how should that boundary be designed for training efficiency and inference correctness?**

Baseline concern: PyO3 call overhead is ~microseconds per call. Training with batch size 64 and per-sample validation = 64 crossings per batch — a measurable bottleneck that compounds over training runs.

## Decision

**Synchronous batch validation during training with structural-hash caching.**

### Architecture

1. **Validation timing**:
   - **Training**: synchronous per-batch validation. Provides supervision signal that cannot be deferred.
   - **Inference**: optional post-hoc validation. Default on for correctness-critical paths (production yield reporting); default off for latency-critical paths.

2. **Batch API**:
   - Rust engine exposes batch-validation functions: one PyO3 call per training batch, not per sample
   - Input: tensor of structural data (prerequisites, coefficients, emergent register claims)
   - Output: tensor of validation results (pass/fail, distance-to-valid metric where applicable)
   - Tasks added to Rust engine queue (tracked in `docs/working/cas_v7_7_rollout_plan.md`):
     - `validate_same_noetic_cross_product_batch`
     - `verify_named_emergent_register_batch`
     - `compute_yield_batch` (also serves ADR-04)

3. **Structural-hash caching**:
   - Validation results cached by structural hash of input pattern (same-Noetic, same-Domain-activations, same-register-combination = same validation result)
   - Cache lives Python-side; Rust unaware
   - Expected hit rate: 80-95% based on training data repetition patterns (recipe archetypes repeat often)
   - Cache eviction: LRU with configurable cap (default 10,000 entries)

4. **Continuous validation signal where possible**:
   - Rule 4 violation magnitude: distance-to-valid metric (how far off admissibility the expression is) enables gradient flow
   - Binary (pass/fail) only where distance-to-valid has no semantic meaning (e.g., registry-name matching is exact-string, not continuous)

5. **PyO3 boundary**:
   - Tight. Python owns model state (weights, activations, gradients).
   - Rust owns framework semantics (Rule 4 compliance, registry validation, recipe structural validation, yield computation).
   - Types crossing boundary: tensor-of-primitives (no Python objects into Rust; no Rust enums into Python training loop).

## Alternatives Considered

### Async validation (background validation with eventual supervision)

**Rejected because:**
- Training supervision requires gradient flow; async defeats this
- Adds complexity without throughput benefit when batch+cache already handles the overhead

### Per-sample synchronous validation (current baseline, no batching)

**Rejected because:**
- Training bottleneck at reasonable batch sizes
- 64× PyO3 crossings per batch is wasteful when batch-API is possible

### Validation only at inference (no training-time supervision)

**Rejected because:**
- Loses the Rust engine's value as training oracle
- Model has no gradient signal for Rule 4 compliance if validation happens only post-training

### Full Python reimplementation of validation logic (avoid PyO3 boundary entirely)

**Rejected because:**
- Duplicates Rust engine's work
- Risk of Python/Rust drift over framework versions
- Loses single-source-of-truth property

## Consequences

### Parameter budget
Zero new model parameters. This is an infrastructure ADR.

### Runtime cost
- Training: one PyO3 call per batch × (1 − cache_hit_rate). At 90% cache hit rate and batch size 64, this is one PyO3 call per 10 batches rather than 64 per batch — 640× reduction.
- Inference: one PyO3 call per production-yield report (acceptable latency).

### Training throughput
- Without batch API + caching: Rust boundary is the training bottleneck at reasonable batch sizes
- With optimizations: validation cost becomes per-batch-unique-structures cost, scaling with data diversity rather than batch count

### Rust engine tasks queued

Added to `docs/working/cas_v7_7_rollout_plan.md` as follow-up implementation work:
- **`validate_same_noetic_cross_product_batch`**: accept array of expressions, return array of validation results
- **`verify_named_emergent_register_batch`**: accept array of (name, register-set) tuples, return array of verification results
- **`compute_yield_batch`**: accept arrays of (prerequisites, coefficients, observed), return arrays of yield tuples
- **Structural-hash cache**: Python-side wrapper class, not Rust engine change

Estimated Rust engine work: 2-4 hours for batch API additions; Python-side cache: 1-2 hours.

### Correctness guarantees
- Rust remains authoritative for framework semantics — if Rust says invalid, it's invalid, regardless of what the Python cache said (cache is invalidated by Rust engine version change)
- Cache correctness: structural hash must include all semantically-relevant inputs; false cache hits would be incorrect validation

## Framework Fidelity Notes

No framework-fidelity decisions in this ADR. Pure infrastructure.

The Rust engine's authoritative role for framework semantics is preserved. Python cache is a performance optimization, not a semantic layer.

## Implementation Notes

### New Python module: `cas-native/validation/rust_bridge.py` (NEW directory + NEW file)

The `cas-native/validation/` directory does not yet exist — it is created as part of this ADR's implementation work.

```
class RustValidationBridge:
    def __init__(self, cache_capacity=10000):
      self.cache = LRUCache(capacity=cache_capacity)

    def validate_batch(self, expressions_tensor):
      # 1. Hash each expression.
      # 2. Cache-lookup; split into (cached_results, cache_misses_indices).
      # 3. One PyO3 call for cache misses: rust_engine.validate_same_noetic_cross_product_batch(...)
      # 4. Update cache with new results.
      # 5. Stitch cached + fresh results into output tensor.
      return validation_results_tensor
```

### Rust engine API additions

`cas-engine/src/validation/rule_four.rs` extends with:

```rust
pub fn validate_same_noetic_cross_product_batch(
    expressions: &[CognitiveStateWithRegister],
    named_emergent_results: &[Option<NamedEmergentRegister>],
) -> Vec<RuleFourResult> {
    expressions.iter()
        .zip(named_emergent_results.iter())
        .map(|(expr, result)| validate_same_noetic_cross_product(expr, result.clone()))
        .collect()
}
```

Similar patterns for `verify_named_emergent_register_batch` and `compute_yield_batch`.

PyO3 binding exposes the batch function. Python-side `RustValidationBridge` wraps the call.

### Testing

- Unit tests for `RustValidationBridge`:
  - Cache hit behavior (identical input produces identical result without PyO3 call)
  - Cache miss behavior (new input triggers PyO3 call, result cached)
  - Cache invalidation on Rust engine version change
- Integration tests:
  - Training throughput benchmark: measure PyO3 calls per batch with and without cache
  - Correctness regression: ensure cached results match fresh Rust computation

---

# Cross-Cutting Locked Decisions (Design Ledger)

Decisions that span multiple ADRs or are foundational to all six:

## Register embedding dimension
**`d = 128`**. Matches the 40-state bank dimension. Rationale: uniform dimension across components simplifies downstream layer shapes; 128 is a balance between capacity and footprint; larger dimensions (256, 512) available if training signals saturation at 128.

## Training data distribution
**Initial split: 60% cross-register integration examples, 40% production semantics examples.**

Rationale: cross-register integration is the most novel v2 component (Clarification 10 + metric-learning binding); production semantics is well-specified via Rust engine and needs less data-sample diversity for the head to learn. Rebalance based on evaluation metrics after first training run.

Data generator implications flagged for the CAS Synthetic Data Generator project phase (next).

## Naming convention

- **Preserve existing class names from v7.4**: `CognitiveStateEmbedding`, `FractalAttentionHead`, `DomainDescentAttention`, `PrerequisiteGateLayer`, `CognitiveToposReasoner`, `GenerativeHead`, `LacunarityGate`, `LacunarityHead`
- **Extensions use additive naming pattern**: `CognitiveStateEmbeddingWithRegister`, `EmergentRegisterBindingHead`, `ProductionSemanticsHead`, `RustValidationBridge`
- Rationale: preserves IP provisional disclosure continuity (names in the 2026-04-12 filing remain present in v2 source) and makes v7.4→v2 diff legible

## Hyperparameter defaults (summary)

| Parameter | Default | Source ADR |
|---|---|---|
| Register embedding dim (`d`) | 128 | ADR-01 |
| Involution constraint weight (`λ`) | 0.1 | ADR-01 |
| Registry capacity | 20 | ADR-02, ADR-03 |
| Similarity threshold (registered Ω_* match) | 0.7 | ADR-02 |
| Gumbel-softmax temperature (`τ`) initial | 10.0 | ADR-04 |
| Gumbel-softmax temperature final | 0.1 | ADR-04 |
| Cache capacity (Rust bridge) | 10,000 | ADR-06 |

All defaults are tunable. First training run provides empirical signal for re-tuning.

---

# Open Questions & Follow-ups

## Requiring Wakil judgment
- **Registry growth beyond 20 Ω_\***: reallocation strategy (one-time rebuild of registry tensor + fine-tune, vs. pre-allocate larger tensor at v1). Flagged for decision if registry admissions reach 15+.
- **Training data 60/40 split**: revisit after first evaluation pass.
- **IP attorney consultation timing**: coordinate before arXiv, paper, or patent filing.

## Technical follow-ups (queued, not blocking)
- Unused-registry-slot regularization (ADR-03 follow-up): specify exact regularization form
- Temperature annealing schedule for Gumbel-softmax (ADR-04): tune on first training run
- Rust engine batch API implementation (ADR-06): 2-4 hours of Rust work
- Python-side cache wrapper (ADR-06): 1-2 hours of Python work
- Testing suite for all new classes: ~1 day of test-writing work

## Research extensions (out of scope for v2)
- Fully differentiable production semantics at inference (ADR-04, extending Option D)
- Complex-valued register encoding (ADR-01, Option E)
- Continuation-in-part patent filing (ADR-05, pending IP attorney)

---

# Summary

Six ADRs lock the CAS-Native v2 architectural decisions:

| ADR | Decision | Parameters (v1) |
|---|---|---|
| ADR-01 | FiLM modulation for Register | 1,024 |
| ADR-02 | Metric-learning binding for Ω_* | 18,944 |
| ADR-03 | Continuous activation + hot-swap registry | (included in ADR-02) |
| ADR-04 | Hybrid production semantics (symbolic inference, differentiable training) | ~10,000 |
| ADR-05 | Clean redesign preserving 40-state structure | 0 (infrastructure) |
| ADR-06 | Batch validation + hash caching | 0 (infrastructure) |

**Total v2 additions: ~30,000 parameters.** For a 50M demonstration model, additions are <0.1% of total. Device-friendly, load-time-friendly, runtime-friendly, quantization-tractable.

Ready for implementation in subsequent work sessions. First implementation phase: background agents per the directive sequencing.

---

# ADR-07: Learned Expression Proposer Head

## Status
Accepted — 2026-04-22 (CAS-Native v2 Wave 8A)

## Context

Codex 5.4 verified in the Wave 7B panel review (and Claude Code confirmed) that the current `_compute_rule_four_loss` in `cas-native/training/trainer.py` is not gradient-bearing with respect to model weights. Two issues make the existing implementation a **metric**, not a **training signal**:

1. Expression operands are built from **ground-truth labels** (`register_labels_batch`), not from model outputs. The structural patterns fed to the Rust validator carry no graph linkage to any model parameters.
2. The Rust-returned per-sample distances are Python floats. The trainer wraps them in `torch.tensor(distances, ...)`, which has `requires_grad=False`. The resulting scalar enters `total_loss` but its backward pass touches no parameters.

Agent 34's own docstring at `trainer.py:795-803` acknowledges this: *"Full end-to-end gradient wiring awaits a learned 'expression proposer' head which is scheduled beyond Wave 7B."* ADR-07 closes that gap.

The Rust validator itself is non-differentiable. Any design must route gradients through a **differentiable proxy** for expression correctness; the Rust engine can remain as an inference-time / evaluation-time authority, but not as a training-time gradient source.

## Decision

Introduce `ExpressionProposerHead` (`cas-native/model/expression_proposer.py`): a learned head that consumes d_model-width hidden states from `CASNativeModel` and emits five parallel logit heads describing a CAS v7.7 structural expression. Train the proposer with a **score-based loss** (Option A — see Alternatives Considered) computed against label-derived targets; because the proposer logits are produced by a linear projection of hidden states, the loss is gradient-bearing through the entire upstream model.

### Head architecture

* Shared low-rank backbone: `d_model → bottleneck_dim (default 32) → GELU`.
* Five parallel heads:
  - `noetic_logits` — `(B, 10)` over the 10 Noetics (CO-0 … CO-9)
  - `domain_logits` — `(B, 4)` over P / C / E / O
  - `register_logits_per_operand` — `(B, max_operands=4, 4)` over T / A / f / E
  - `operand_count_logits` — `(B, 5)` over operand counts `{0, 1, 2, 3, 4}`
  - `named_emergent_logits` — `(B, 2)` binary "is an emergent result named"
* Training mode attaches a straight-through Gumbel-softmax sample on the per-operand register logits (`register_gumbel`) for forward-compat with a future Option-B upgrade; v1 loss does not consume it.
* Inference mode: argmax on every head → `ExpressionProposal` dataclass aligned with the Rust bridge's `StructuralPattern` shape.

### Parameter budget

At `d_model=128, bottleneck=32, max_operands=4`:

```
backbone:    128 * 32 + 32                  =  4,128
noetic:       32 * 10 + 10                  =    330
domain:       32 *  4 +  4                  =    132
register:     32 * (4 * 4) + (4 * 4)        =    528
op_count:     32 *  5 +  5                  =    165
named_emg:    32 *  2 +  2                  =     66
─────────────────────────────────────────────────────
TOTAL                                        ≈  5,349
```

At `d_model=512`: ≈ 17,637. At the upper `d_model=512, bottleneck=64, max_operands=5` sweep the figure approaches ≈ 50K — the upper bound quoted in the ADR-07 directive. The actual count is exposed by `ExpressionProposerHead.parameter_count`.

### Training loss (Option A, score-based)

`cas-native/model/loss.py` gains `ProposerRuleFourLoss` with five component terms:

* `L_noetic` — cross-entropy on `noetic_logits`
* `L_domain` — cross-entropy on `domain_logits`
* `L_register` — cross-entropy on `register_logits` masked by per-operand-slot presence
* `L_count` — smooth-L1 on the soft-argmax of `operand_count_logits` (smooth-L1 respects the ordinal axis; count-3 is closer to count-4 than to count-0)
* `L_named_emergent` — cross-entropy on `named_emergent_logits`

Aggregate: `L = w_n·L_noetic + w_d·L_domain + w_r·L_register + w_c·L_count + w_e·L_named_emergent`. Outer weight `lambda_proposer_rule_four` (default `0.5`) multiplies the aggregate in the trainer's loss sum.

### Trainer integration

* `_compute_proposer_rule_four_loss(hidden_states, register_labels_batch, omega_labels_batch)` builds per-example targets from the batch label streams, runs the proposer, and returns the weighted score loss.
* Aggregation sits in `_train_step` immediately after `rule_four_loss` addition, marked `# ADR-07 expression proposer loss aggregation`.
* Gumbel-softmax tau is reused from ADR-04's annealing schedule — the same `self.current_tau` the `DifferentiableStoichiometry` head consumes.

### Backward compatibility

A new flag `V2ComponentFlags.use_expression_proposer: bool` (default `False`) gates the head. When `False`:
* No proposer is instantiated; `state_dict` contains no proposer entries.
* Forward pass returns the identical dict (no `proposer_outputs` key).
* Loss aggregation adds nothing.
* Parameter count unchanged; byte-equivalent to the pre-ADR-07 Wave 7B state.

Default `False` at introduction is deliberate: the proposer is a significant architectural addition; opt-in preserves first-training-run stability while the other v2 components continue to stabilize.

## Alternatives Considered

### Option A — Score-based (chosen)

Proposer outputs are scored directly against label-derived target distributions using CE + smooth-L1. Gradient path: `hidden_states → proposer logits → loss → backward`.

Pros: simple, low variance, no Rust at training time, closes the wiring gap with minimum architectural surface, Rust remains authoritative at eval.

Cons: loses the Rust distance's structural severity weighting (2-register vs 3-register vs 4-register); relies on label-derived targets that the synthetic data generator must emit correctly.

### Option B — REINFORCE-lite with Gumbel-ST

Proposer outputs are discretized (straight-through Gumbel-softmax), fed to Rust via `rule_four_distance_batch`, and the resulting distance is used as a negative reward. The pathwise gradient is computed by multiplying the reward against proposer log-probabilities.

Pros: directly optimizes Rust-validated distance; structural severity weighting preserved.

Cons: higher variance; requires Rust at every training step (latency hit at ~10 ms/batch); variance reduction (baselines, control variates) adds complexity; marginally better only when label-derived CE targets and Rust distances disagree — and at v1 they largely agree.

Deferred to a future v2 of ADR-07 if empirical signal justifies it. The proposer head emits `register_gumbel` in training mode to preserve this upgrade path with no additional head surgery.

### Option C — Do nothing, accept Rule 4 as metric-only

Leave `_compute_rule_four_loss` as a non-gradient-bearing metric; rely on the other v2 losses (emergent binding, production, involution) to shape the architecture and evaluate Rule 4 compliance at validation time.

Rejected because: (1) Codex 5.4's panel finding explicitly flagged this as a gap requiring closure before first training run, (2) Agent 34's own docstring cites the learned proposer as the planned resolution, (3) leaving the loss inert while it appears in the aggregate creates misleading per-step metrics in W&B / checkpoint state.

## Consequences

* **Parameter budget** adds ~5K-18K parameters depending on `d_model` (<0.04% of a 50M-parameter demonstration model). Well within the ADR cross-cutting "v2 additions < 1%" constraint.
* **Gradient flow closes** — the first training run can see genuine Rule 4 signal backpropagating through the model. Empirical question: does the proposer's label-CE signal improve Rule 4 compliance at eval? Answer measured at first validation pass.
* **Forward contract extended** — when enabled, `CASNativeModel.forward` adds a `proposer_outputs` key. All existing consumers ignore unknown keys.
* **Config schema extended** — `V2ComponentFlags.use_expression_proposer` + eight `V2Hyperparameters.lambda_proposer_* / proposer_*` fields. YAML schema updated in `training_v2.yaml`.
* **Test surface** — ~25 new tests in `tests/test_expression_proposer.py` covering shape, gradient flow, Gumbel mode, backward compatibility, config integration, and the critical end-to-end "does proposer loss deliver gradient to model params" assertion.
* **Follow-ups flagged** — Synthetic data generator should begin emitting explicit `target_noetic` / `target_domain` fields on `omega_labels` entries; the v1 proposer loss falls back to the Rule-4 template (`^3^P|…`) when only register labels are present.

## Framework Fidelity Notes

No framework change. ADR-07 is implementation work closing a wiring gap in CAS-Native v2. The 40 Cognitive States, 7 Drives, 4 Registers, 5 Generative Operations — the primitives named in USPTO #64/037,173 and Clarifications 1-10 — remain unchanged. The proposer head consumes the v7.7 expression space (Noetic × Domain × Register × operand-count × named-emergent) and emits proposals within that space. IP attorney review flagged with `cas_v7_7_rollout_plan.md` as part of v7.7 rollout; ADR-07 adds no new primitives and does not alter v7.7's provisional patent posture.

Because this is a Wave 8A scaffold, the ADR carries a **partial framework fidelity** note: the proposer's training signal derives from labels, not from a CAS-algebraic reward. Once empirical signal justifies it, the Option-B upgrade path wires the Rust validator's distance directly into the gradient — at which point framework fidelity graduates to full. The v1 Option-A design closes the gradient-flow gap identified by the panel without claiming framework-level optimality.

## Implementation Notes

* New module: `cas-native/model/expression_proposer.py` with `ExpressionProposerHead`, `ExpressionProposal` dataclass, and public constants.
* New loss class: `ProposerRuleFourLoss` in `cas-native/model/loss.py`, alongside `InvolutionConstraintLoss` and `LacunarityRegularizationLoss`.
* Trainer integration: `_compute_proposer_rule_four_loss` method + aggregation term in `_train_step` with marker comment `# ADR-07 expression proposer loss aggregation`.
* Model integration: `CASNativeModel.forward` runs the proposer on the pre-final-norm hidden states `x` (same tensor feeding `lm_head` and `topos_reasoner`), so proposer gradients reach every transformer layer.
* Config: `V2ComponentFlags.use_expression_proposer` defaults `False`. `V2Hyperparameters` gains eight fields (five loss weights + two architecture knobs + the outer `lambda_proposer_rule_four`). YAML template `training_v2.yaml` updated.
* Test file: `cas-native/tests/test_expression_proposer.py`.

Integration points — summary table:

| Surface | Change |
|---|---|
| `model/expression_proposer.py` | NEW — `ExpressionProposerHead`, `ExpressionProposal` |
| `model/loss.py` | ADD `ProposerRuleFourLoss` |
| `model/cas_native_model.py` | ADD `expression_proposer_enabled` property + forward branch emitting `proposer_outputs` when enabled |
| `training/trainer.py` | ADD proposer init, `_compute_proposer_rule_four_loss`, aggregation term marked `# ADR-07 expression proposer loss aggregation` |
| `training/config.py` | ADD `use_expression_proposer` flag + 8 proposer hyperparameters + validate() hooks |
| `config/training_v2.yaml` | ADD proposer section |
| `tests/test_expression_proposer.py` | NEW — ~25 tests including the critical gradient-flow assertion |

Total v2 additions after ADR-07: ~30K (pre-existing) + ~5-18K (proposer) ≈ **35-48K parameters**. Still <0.1% of a 50M demonstration model. Device-friendly, load-time-friendly, runtime-friendly, quantization-tractable.

---

# ADR-08: Option E — Shared Register Latent with Dual Output Heads

## Status
Accepted — 2026-04-22 (CARP Round 3 panel consensus, 4-of-5)

## Context
Wave 7A landed two independently-learned FiLM modules on `CognitiveStateEmbeddingWithRegister`:
- `register_film`, 40-dim over the cognitive-state simplex surface (v7.5 path)
- `register_film_dmodel`, d_model-wide for downstream binding heads (v7.7 path, ADR-02)

Each module carried `(num_registers, width)` gamma and beta parameter tensors, learned independently. Nothing architecturally forced the two modules to represent the same register concept — the A-register's 40-dim gamma and the A-register's d_model gamma are independent parameter tensors with no structural coupling. Semantic drift was possible: the 40-dim module could learn to encode "A = analytical cognitive state" while the d_model module independently drifted to encode "A = something-else-under-d_model-width." The drift would be silent — emerging only as cross-surface inconsistency at inference.

The 5-model panel (Codex 5.4, Claude Code 4.7, Qwen 3.5, Gemini 3, DeepSeek-R1) debated four alternatives across three CARP rounds. Panel converged 4-of-5 on Option E (shared latent with dual heads) with all accepting-panelist modifications incorporated.

## Decision
Introduce `RegisterLatent` as the authoritative register parameterization. Single learnable per-register embedding `z_R` (latent dimension `r=16`). Four output heads project `z_R` into `(gamma_40, beta_40, gamma_d, beta_d)` via zero-initialized linear layers with tanh-saturated scaled readouts:

```
gamma_40 = 1 + s_40 * tanh(W_gamma_40 @ z_R)      (R, num_states)
beta_40  =       s_40 * tanh(W_beta_40  @ z_R)    (R, num_states)
gamma_d  = 1 + s_d  * tanh(W_gamma_d  @ z_R)      (R, d_model)
beta_d   =       s_d  * tanh(W_beta_d   @ z_R)    (R, d_model)
```

Scales `s_40 = 0.05`, `s_d = 0.02`, frozen for the first `scale_warmup_steps = 1000` training steps so the W heads adapt under fixed scalar magnitudes before the scalars themselves begin moving.

Involution enforcement is latent-level primarily (`z_T + z_E ≈ 0`, `z_A + z_f ≈ 0`) with a dimension-normalized output-surface regularizer layered on top as a belt-and-braces redundancy. Defaults: `lambda_latent = 0.01`, `lambda_out = 0.1`. When `z_T = -z_E` exactly and the W heads are linear, the output-surface involution follows by construction (tanh is odd, W is linear), so the output-surface term vanishes automatically as the latent-level term is satisfied — they are not orthogonal constraints.

`RegisterFiLM` is preserved in `register_film.py` as a legacy shim for tests and external call sites that construct it directly; the model/embedding/trainer forward path consumes `RegisterLatent` exclusively. `CognitiveStateEmbeddingWithRegister.register_film` and `register_film_dmodel` are now `_LatentFiLMView` proxies — read-through accessors that compute gamma/beta from the shared latent on each access. Legacy code reading `.gamma` and `.beta` continues to work; perturbation via `.gamma.add_` does NOT (the views are computed, not stored).

## Alternatives Considered

**Option A — Shared Projection.** Learn Module 1 (40-dim) directly; derive Module 2 (d_model) via a fixed projection (e.g. random linear or Fourier lift). Rejected because the projection choice is a design-by-guess problem with no principled answer at the framework level — the "correct" projection depends on the downstream d_model surface's role, which varies across binding heads, production semantics, and LM-head consumers.

**Option B — Consistency Loss.** Learn both modules independently, add a penalty for divergence between their per-register representations. Rejected under the panel's "brains first" priority: soft enforcement permits drift under strong task-gradient pressure; the panel favored structural enforcement — if the two modules are semantically coupled, the architecture should make drift impossible, not merely penalize it.

**Option C — Hypernetwork.** Deep generator maps register_id to all FiLM parameters. At general `k` (number of registers), C is the most expressive option; at `k = 4` (Clarification 8 register axis is closed at T/A/f/E), C's scalability advantage is moot and the parameter overhead is unjustified (deep hypernetwork >> simple linear heads over a 16-dim latent).

**Option D — Single d_model Module.** Eliminate the 40-dim module entirely; let all register modulation happen at d_model and propagate to the simplex via the projection. Rejected because it inverts framework alignment — the 40-dim cognitive-state simplex is the canonical target space (Clarification 8, ADR-01, CORRECTION 4), not an implementation derivative of d_model. Option D would subordinate the canonical space to the architectural convenience of the transformer's hidden-state width.

Option E preferred over Codex's full-hypernetwork variant of C because k=4 means the shared-latent-with-linear-heads form is sufficient and cheaper. Preferred over Claude Code's Option A variant because learned readout heads avoid the "which projection?" design problem — the heads learn whatever projection the task gradient requires, constrained only by the shared latent.

## Consequences

**Parameter budget (d=128, r=16):**
```
Register embeddings  : 4 * 16  =     64
W_gamma_40, W_beta_40: 2 * 16 * 40 = 1,280
W_gamma_d,  W_beta_d : 2 * 16 * 128 = 4,096
Scales (s_40, s_d)   :              2
                              Total = 5,442  (~ 5,440 target)
```

**At d=512:** `5,442 - 4,096 + (2 * 16 * 512) = 17,730`. Comparable to the Wave 7A two-module design (which had `4*2*40 + 4*2*512 = 4,416`) — slightly larger absolute count due to the shared latent + 4 W heads, but **semantically more tightly coupled** (one source of register identity instead of eight independent gamma/beta vectors).

**Structural alignment guarantee.** Register identity is a single `z_R`; both substrate expressions are projections of one semantic source. Semantic drift prevented by construction: a gradient that pushes the A-register's 40-dim gamma in one direction flows through `z_A` and symmetrically affects `gamma_d`, `beta_d` (and the other 40-dim head). The two FiLM surfaces cannot individually specialize to inconsistent interpretations of "A."

**v7.4 byte-equivalence preserved.** Zero-initialized W heads + `tanh(0) = 0` gives `gamma = 1`, `beta = 0` at every surface at step 0. The step-0 FiLM is the exact identity. When `V2ComponentFlags.use_register_film = False`, `CognitiveStateEmbeddingWithRegister` is never instantiated, and the model path is byte-for-byte identical to the v7.4 `CognitiveStateEmbedding` forward. Guarded by `test_v74_byte_equivalent_when_flags_off` (`test_option_e_alignment.py`) and `test_register_neutral_matches_base_embedding_exactly` (`test_register_integration.py`).

**Wave 8A agent compatibility preserved.** Agent 35's `ExpressionProposerHead` (operates on hidden states, not register params) unchanged. Agent 37's unified None/zero forward path (Decision G) preserved and guarded by bitwise-equality tests under Option E. Agent 38's null-space regularization (`OmegaRegistry` unused-slot pull) unchanged — operates on a separate emergent-register surface entirely.

**Legacy-test adaptation required.** Tests that mutated `emb.register_film.gamma.add_(...)` no longer produce mutation (the view is read-only); adapted to perturb `emb.register_latent.W_*.weight` instead. Scope: 4 assertions across `test_register_integration.py` and `test_forward_path.py`. `test_wrapped_parameter_count_includes_film` rewritten to count RegisterLatent's 5,442 instead of the legacy two-module 832.

## Framework Fidelity

Clarification 8 §1 line 263: "The Register axis does not introduce new primitives. The 40 Cognitive States remain unchanged. Register is a specification of operational character layered on top of the existing primitives."

**ADR-08 verdict.** `z_R` is a compact INTERNAL REPRESENTATION of the specification layer. It is not a CAS primitive; it does not modify the 40-state bank or add to the 10-Noetic / 4-Domain / 7-Drive / 4-Register framework vocabulary. It is the architecture-internal encoding of "which register is being specified" at parameter-storage level, analogous to a token embedding table in any NLP model (tokens are not primitives independent of the vocabulary just because they have learned embeddings).

The register axis remains T/A/f/E — four values, orthogonal to Noetic/Domain/Drive, closed set. The `z_R` table has four rows because the register axis has four values. No primitive introduced; no framework drift.

Framework fidelity satisfied. USPTO #64/037,173 provisional patent posture unchanged.

## Implementation Notes

**Scale-freeze mechanism.** Scales are `nn.Parameter` with `requires_grad=False` at construction. `RegisterLatent.set_scales_frozen(False)` flips the requires_grad and subsequently permits gradient accumulation. The optimizer (`Adam(model.parameters())`) already owns the scale parameters at construction time — Adam's internal momentum buffers lazily initialize when the first non-zero gradient arrives, so no `add_param_group` call is needed at the unfreeze boundary. This is simpler than the "add param group at unfreeze" alternative considered in the panel discussion; implementation-wise it is also more robust (no risk of the same parameter appearing in two param groups).

**Trainer scale-warmup wiring.** `CASTrainer._maybe_unfreeze_scales(current_step)` is called at the END of each `_train_step` with `current_step + 1` (so the step crossing the boundary applies the unfreeze effect on the FOLLOWING step's forward). Idempotent: once unfrozen, subsequent calls are no-ops via the `latent.scales_frozen` guard.

**Diagnostic metrics.** `CASTrainer._latent_film_metrics()` returns a `register_latent/*`-prefixed dict covering per-register `z_norm`, `gamma40_norm`, `beta40_norm`, `gammad_norm`, `betad_norm`, plus scalar `l_inv_output`, `l_inv_latent`, `scale_40_value`, `scale_d_value`, `scales_frozen`. Routed into the `_train_step` metrics dict for W&B / stdout surfacing.

**Test coverage.** 30 tests in `test_register_latent.py` (instantiation, zero-init, apply-register, scale freeze, involution symmetry, gradient flow, diagnostics). 15 tests in `test_option_e_alignment.py` (LatentInvolutionLoss correctness, byte-equivalence, Wave 8A agent integration, scale warmup, trainer diagnostics). 4 legacy tests adapted (`test_register_integration.py`, `test_forward_path.py`, `test_trainer_v2.py`, `test_loss_refinement.py`). Full suite: 388 passing (343 baseline + 45 new - 0 regressions), 3 pre-existing unchanged failures.

**Planned follow-up — ablation harness.** ADR-08 is admitted on CARP consensus plus step-0 byte-equivalence + unit-test coverage. A small-scale empirical ablation comparing Option E against the two-independent-FiLM Wave 7A baseline is scheduled as follow-up (not in scope for the landing commit):
- Training 10k steps on a ~100M-token synthetic register-labeled corpus, Option E vs Wave 7A, matched hyperparameters.
- Primary metrics: register prediction accuracy on held-out registers, cross-surface consistency (do the 40-dim and d_model FiLMs agree on register identity at similar-context inputs?), Rule 4 violation rate.
- Expected finding: Option E delivers equal or lower register-prediction error AND substantially higher cross-surface consistency than Wave 7A. If Option E underperforms on prediction accuracy at equal compute, that's a signal to relax the scale_warmup schedule or increase `latent_dim_r`. The ablation is instrumentation-only; landing commit does not gate on it.

## Integration Points — Summary Table

| Surface | Change |
|---|---|
| `model/register_film.py` | ADD `RegisterLatent`; preserve `RegisterFiLM` as legacy shim |
| `model/embedding.py` | REPLACE two-FiLM design with shared `register_latent`; expose `register_film` / `register_film_dmodel` as `_LatentFiLMView` proxies |
| `model/cas_native_model.py` | `_apply_register_film_to_logits` reads gamma/beta once from shared latent (was: twice through view properties in loop) |
| `model/loss.py` | ADD `LatentInvolutionLoss`; extend `InvolutionConstraintLoss._extract_gamma_beta` to accept `RegisterLatent` |
| `training/config.py` | ADD 6 Option E hyperparameters: `latent_dim_r`, `scale_40`, `scale_d`, `scale_warmup_steps`, `lambda_out`, `lambda_latent` |
| `training/trainer.py` | ADD `_latent_involution_loss`, `_maybe_unfreeze_scales`, `_latent_film_metrics`; rewire `_compute_involution_loss` |
| `config/training_v2.yaml` | DOCUMENT new hyperparameters with ADR-08 citation |
| `tests/test_register_latent.py` | NEW — 30 tests |
| `tests/test_option_e_alignment.py` | NEW — 15 tests |
| `tests/test_register_integration.py` | ADAPT 2 tests (perturb latent W heads, rewrite parameter-count assertion) |
| `tests/test_forward_path.py` | ADAPT 4 tests (perturbations via shared latent; non-trivial loss function) |
| `tests/test_trainer_v2.py` | ADAPT 1 test (init involution loss is small-positive, not zero) |
| `tests/test_loss_refinement.py` | ADAPT 1 test (zero-grad on latent, not view) |

Total Option E delta: ~600 LoC added, ~150 LoC modified, 45 new tests, 8 adapted tests. ADR-08 preserves the CAS framework vocabulary unchanged and improves architectural coupling between the two FiLM surfaces.

---

# ADR-09: CAS Memory Substrate (Future Architecture)

**Numbering note:** Originally drafted as ADR-08 in a parallel side conversation (Gemini + Codex Memory Substrate collaboration) that landed in `noetic-compass-scaffold/noetic-compass/docs/architecture/cas_native_v2_adrs.md`. In parallel, the panel's Option E implementation was committed as ADR-08 in this canonical file (commit `b7341e3`). Reconciled to ADR-09 here to resolve the collision and establish `docs/architecture/cas_native_v2_adrs.md` as the single canonical ADR location going forward.

## Status
Accepted as Future Work — 2026-04-22 (CAS-Native v2 Wave 8A)

## Context

Current AI memory systems (MemGPT, Letta, LangGraph) effectively solve the *mechanics* of memory (storage tiers, vector similarity, core/archival blocks). However, they lack a formal cognitive indexing ontology.

The CAS framework contains rich cognitive structures that could ground a fundamentally superior memory system. Specifically:
- **40 Cognitive States & Registers:** Allow memories to be indexed by the cognitive mode in which they were formed or apply.
- **Drives & Foundations:** Provide a natural schema for memory salience and weighting.
- **RPM & Production Semantics:** Naturally encode memories as relational graphs (prerequisites, catalysts, yields) rather than isolated text chunks.
- **Lacunarity:** Allows an agent to detect *missing* structural memories (e.g., high analytical knowledge but zero practical/embodied knowledge on a topic).

While the theoretical value is immense, building a full graph-based, CAS-annotated memory system is a massive undertaking. It requires a memory record schema, annotation pipeline, CAS-aware reranking algorithms, and evaluation benchmarks. Attempting to build this now would distract from the core goal of validating CAS-Native v2.

## Decision

Establish the **CAS Memory Substrate** as a formal architectural design for future implementation (v7.8+ or v8.0), but **strictly defer implementation** until CAS-Native v2 and the Synthetic Data Generator are stable.

1. **Overlay Architecture:** The substrate will *not* replace existing vector stores or databases. It will act as a cognitive schema that rides on top of them.
2. **V0 Memory Ledger:** A JSONL-compatible schema (`cas_memory_ledger_schema_v0.json`, located alongside this ADR at `docs/architecture/`) has been defined for early, file-backed experimentation.
3. **Auto-Tagging via Proposer:** The `ExpressionProposerHead` (ADR-07) will eventually be utilized in inference mode as the primary automated annotator, mapping agent thoughts/hidden states to structured CAS metadata.
4. **Relational Target (V1):** The ultimate architecture will rely on a Graph Database (e.g., Neo4j) augmented with vector embeddings to natively support RPM prerequisite traversal and Production Semantics linking.

## Consequences

- **Scope Containment:** Prevents feature creep. Current memory needs (project continuity) will continue to rely on standard tools (`CLAUDE.md`, ADRs, git).
- **Clear Roadmap:** We have a formally validated blueprint for how CAS translates to agent memory when the time is right.
- **Schema Validation:** The V0 JSON schema provides a concrete artifact that can be used to manually structure critical project insights today without building the full software pipeline.

## Companion artifacts (in `docs/architecture/`)

- `CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md` — full PDR and design document (~17 KB)
- `CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.pdf` — typeset copy of the PDR (~222 KB)
- `cas_memory_ledger_schema_v0.json` — V0 ledger schema referenced in Decision point 2 (~4.5 KB)
