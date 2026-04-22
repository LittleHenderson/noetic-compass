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
