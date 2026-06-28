# Prediction Heads and Loss — CAS-Native Redesign Research Note

**Date:** 2026-05-05
**Author:** Opus R&D specialist (slice 4 of 5 — heads + loss)
**Scope:** SIDE PROJECT. No live training touched. No production code modified. Pure
research note evaluating whether CAS / TKS conceptual machinery can REPLACE the
current 12-independent-linear-head + summed-cross-entropy stack with something
smaller, more interpretable, and architecturally honest.

> **Status disclaimer.** Every quantitative claim below is a back-of-envelope
> estimate derived from inspecting the existing source files, not a measurement
> from a training run. Falsification work is sketched in §6.

---

## 1. Goal

Make the prediction-head + loss layer of the CAS-Native classifier consistent
with CAS itself. The current stack treats Noetic, Domain, Drive, Register, and
eight structural flags as 12 statistically independent classification problems
that happen to share a 64-dim bottleneck. The framework says they are not
independent. They share an admissibility structure, an involution structure, a
domain-precedence structure, and a state-vector geometry (the open simplex
under the Fisher-Rao metric, per `CLAUDE.md` Correction 4). The redesign
should make the loss landscape match the framework's geometry instead of
fighting it.

Concretely:

- One head, not 12, that emits a single structured CAS expression whose 12
  fields are read off as derived projections.
- A loss that knows the difference between "wrong but valid" and "structurally
  invalid" (admissibility), between "wrong" and "inverted" (Inversion Scan),
  and between probability vectors close in Euclidean distance vs. close in
  Fisher-Rao distance on the open simplex.
- Every loss term must be inspectable and nameable per the user's
  object-traceability rule. If admissibility loss fires, the trace records
  which (operator, source, target) triple was inadmissible.

---

## 2. Current state (what's there today)

The relevant files:

- `noetic-compass-scaffold/noetic-compass/cas-native/model/structured_prediction.py`
  — the 12-head classifier (`StructuredPredictionHead`). Backbone is
  `Linear(d_model, 64) -> GELU -> LayerNorm`. Twelve `Linear(64, num_classes)`
  heads on top: `turn_type` (11), `expression_family` (6), `transition_kind`
  (13), `noetic` (10), `domain` (4), `drive` (7), `register` (4 multi-label),
  `register_mode` (5), `meta_relation` (9 multi-label), `authority` (3),
  `omega` (2), `meta_logic` (2). Loss is a plain sum of independent
  `cross_entropy` calls plus two `binary_cross_entropy_with_logits` for the
  multi-label heads. There is no admissibility check, no inversion penalty,
  no Fisher-Rao term, no RPM gate.
- `cas-native/model/loss.py` — `CognitiveMetricLoss` already implements
  Fisher-Rao geodesic distance, an operator-balance penalty for involution
  pair gaps, a domain-coherence penalty (DCI), an RPM-satisfaction term, and
  an inversion-sum term. It is wired against the LM head and the 40-dim
  simplex `cognitive_state`, **not** against the 12-head structured
  predictor. The two loss surfaces do not talk.
- `cas-native/model/expression_proposer.py` — `ExpressionProposerHead` (ADR-07)
  already emits a *structured* proposal (noetic / domain / per-operand
  registers / operand count / named-emergent flag) from a 32-dim bottleneck
  with five parallel heads (~5K params at d_model=128). It is the closest
  existing module to the redesign target.
- `cas-native/model/topos_reasoner.py` — `CognitiveToposReasoner`. Per its
  own docstring, "neural proxy for 3-valued assessment, not a literal
  implementation of a topos' internal logic." Outputs `(B, 7, 3)` truth
  values for seven topos propositions.
- `cas-native/model/lacunarity_head.py` — metacognitive head reporting
  per-slot gap probability and per-domain confidence. Not on the loss path
  in the structured predictor.
- `api/notation/inversion.py` — full 7-axis Inversion Scan implementation
  (N, W, F, P shipped; E, S, A deferred). Operates on compiled expression
  source strings via regex round-trip through the compiler. **Pure Python,
  not differentiable.**

Total params at d_model=512, bottleneck=64: ~37K. The 12 outputs are
mutually structure-blind: nothing penalizes a
`(noetic=^3, domain=O, transition_kind=cluster_update)` tuple the compiler
would reject. `HONEST_STATUS.md` records 93.2% canonical exact on the 1K
eval; per `project_paraphrase_failure_modes_diagnoses.md` when canonical
and paraphrase disagree the canonical is right 95-98% — structural
invariance failure, not knowledge gap.

---

## 3. Proposed redesign

### 3.1 Single Topos-Reasoner head, 12 fields as projections

Replace the 12 parallel linears with ONE structured-expression head emitting
a distribution over the **5 Generative Operations** (×, ÷, ∘, +, −, per
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 §6) plus typed
operand slots (Noetic, Domain, Drive, Register) plus an emergent-result
flag for v7.7 cross-register integration.

```
Z = Backbone(pooled_hidden)                       # (B, bottleneck)
op_logits      = W_op      @ Z                    # (B, 5)    × ÷ ∘ + −
operand_logits = W_operand @ Z                    # (B, M, 25)  10+4+7+4
omega_logits   = W_omega   @ Z                    # (B, 2)
```

Derive every legacy field deterministically: `noetic` / `domain` / `drive`
are slot-mass argmaxes; `registers` (multi-label) is the union over operand
register slots; `register_mode` is a rule on (op, operand-count, omega) per
v7.7 Clarification 10 §3 (`+` → co_presence, `×` with omega → integration,
etc.); `transition_kind` / `turn_type` / `expression_family` /
`meta_relation` / `authority` / `meta_logic` are small auxiliary heads on
the same `Z`.

**Why smaller and smarter.** Smaller because the 12 output distributions are
conditionally independent given `Z` plus a fixed rule set — they don't need
to be learned as 12 distributions. Smarter because operands are typed (a
Noetic slot cannot emit a Drive label), shrinking the "wrong but plausible"
space from `Cartesian-product-of-12-marginals` to "wrong within a type."
This is the CAS-native analog of CRF-style structured prediction with type
constraints replacing arbitrary feature templates.

### 3.2 Admissibility-penalized loss (Correction 1)

Per `CLAUDE.md` Correction 1 and `api/notation/compiler.py` (`_is_admissible`),
every operator carries an admissibility relation D_k ⊆ I × I. Currently the
compiler validates AT INFERENCE; training never sees a penalty for emitting
an inadmissible structure.

Add an admissibility term:

```
L_admit = mean over batch of:
            sum over ordered operand pairs (i, j):
                P(operator) * P(operand_i = a) * P(operand_j = b)
                * (1 - is_admissible(operator, a, b))
```

This is the expected violation under the soft prediction distribution. When
the model puts mass on an inadmissible (operator, a, b) triple it pays a
cost. The admissibility table is finite and small (10 operators × 40 states
× 40 states = 16K booleans), pre-computable from the compiler at training
init, stored as a buffer, and indexed in O(1).

**Traceability hook.** When `L_admit > 0` for an example, the trace records
the top-k inadmissible triples by expected violation mass. The user asked
for "if admissibility loss fires, you can name which prerequisite was
violated" — this gives a per-example inadmissibility ledger.

### 3.3 Inversion-Scan penalty in loss (training-time regularizer)

The 7-axis Inversion Scan in `api/notation/inversion.py` is currently text-
level and not differentiable. The redesign uses a **probabilistic
shadow-Inversion Scan** that operates on the soft prediction directly, no
text round-trip.

For each axis with implemented semantics (N, W, F today; E, S, A deferred):

- **N axis.** Penalize involution-pair imbalance on the noetic operand
  distribution. The existing `compute_operator_balance_loss` in
  `cas-native/model/loss.py` already implements this for the 40-dim
  cognitive state. Reuse the same form on the operand-noetic logits:
  `relu(|p(^2) − p(^3)| − threshold) + relu(|p(^5) − p(^6)| − threshold)
  + relu(|p(^8) − p(^9)| − threshold)`.
- **W axis.** Penalize domain-precedence violations. The CAS rule is
  `P ≻ C ≻ E ≻ O`. For pairs of operands `(i, j)` where the predicted
  transition_kind is causal, penalize expected probability mass on
  `(domain_i lower-precedence than domain_j)`.
- **F axis.** Drive-pair imbalance, mirror of N axis on the drive
  distribution: F1↔F7, F2↔F6, F3↔F5; F4 self-dual.
- **E, S, A.** Deferred until the engine implements them. For now log
  zero contribution to keep the slot in the loss dict for parity.

Total: `L_inversion = λ_N * L_N + λ_W * L_W + λ_F * L_F`.

**Traceability hook.** Each axis fires independently, so a single example's
trace shows which axis (or compound combination) penalized it. This is the
training-time analog of Mode 7 Network Attribution
(`project_exposure_button_traceability.md`).

### 3.4 Fisher-Rao geodesic loss on the 40-state simplex (Correction 4)

Cross-entropy on the 40-state distribution is Euclidean-flavored: it
penalizes log-prob of the true class only. The state space is the open
probability simplex with the Fisher-Rao metric
`d(p, q) = 2 * arccos(Σ √(p_k q_k))` (Correction 4 in `CLAUDE.md`). The
Fisher-Rao distance is *the* canonical Riemannian distance on the simplex
and the existing `fisher_rao_distance` in `cas-native/model/loss.py` already
computes it correctly with float64 stabilization.

Replace the noetic + domain CE with a single Fisher-Rao term against a
target one-hot smoothed onto the open simplex (smoothing required because
Fisher-Rao is undefined at the boundary):

```
target_smooth = (1 - eps) * one_hot + eps / 40
L_geodesic    = fisher_rao_distance(p_state, target_smooth).mean()
```

Where `p_state` is the 40-dim joint distribution implied by the structured
proposer (outer product of noetic and domain, projected to the simplex).
Gradient of arccos is well-behaved away from p = q (clamping the
Bhattacharyya coefficient at 1 − 1e-7 in `loss.py` already handles this).

The win is principled gradient direction: at high confidence, CE is nearly
flat in a way Fisher-Rao is not, so geodesic loss keeps the model honest at
the easy end of the distribution where confidence calibration matters.

### 3.5 RPM-gated loss (Correction 2)

Per Correction 2, the RPM chain is section-retraction, one-directional. If
a prediction's prerequisites are not satisfied, the prediction should not
update weights toward itself — it should update the prerequisites first.
`cas-native/model/rpm_gate.py` already produces a satisfaction score per
gate (A0 → D → W → P).

RPM-mask the loss:

```
sat = min(sat_A0, sat_D, sat_W, sat_P)            # weakest link
L_supervised = sat * L_geodesic + (1 - sat) * L_rpm_repair
```

`L_rpm_repair` is the per-gate satisfaction loss already in
`compute_rpm_satisfaction_loss`. When RPM is broken, gradient flows into
fixing prerequisites; when RPM is satisfied, gradient flows into the
prediction itself. This matches the framework: prerequisite satisfaction
is one-directional and must be repaired before downstream targets become
reachable.

### 3.6 Joint structured product loss

The default loss above ties heads via the structured proposal, but the four
v7.5 axes (Noetic × Domain × Drive × Register) are not literally
independent. Replace the four independent CEs with a CRF-style log-partition
over the joint, restricted to the admissibility table. 16K admitted triples
is small enough to enumerate; cost is one tensor contraction per batch,
strictly tighter than four marginal CEs on correlated targets. Land this
last, after §3.1–§3.5 are validated.

---

## 4. Param count

Order-of-magnitude estimates only. d_model = 512, bottleneck = 64.

| Component | Current | Proposed | Δ |
|---|---|---|---|
| Backbone | 512×64 + 64 = 32,832 | 512×64 + 64 = 32,832 | 0 |
| Twelve linears (current) | ~4,800 | — | −4,800 |
| Single Topos head (5 op + 4 operand × 25 slot + 2 omega) | — | 64 × (5 + 100 + 2) + 107 = 6,955 | +6,955 |
| Derived projections (rule-based, no params) | — | 0 | 0 |
| Auxiliary classifier heads (turn_type, expression_family, transition_kind, meta_relation, authority, meta_logic) | included above | 64 × (11+6+13+9+3+2) + 44 = 2,860 | +2,860 |
| **Total head + backbone** | **~37,632** | **~42,647** | **+5,015 (~13%)** |

The redesign *grows* the head by ~5K params. The win is structural, not
parameter count: the proposed head produces *jointly consistent* output
where the current head produces *12 marginally consistent* outputs. That
trade — slightly larger but architecturally honest — is the right one given
the user's "CAS gets the glory" rule.

If parameter count is non-negotiable, the auxiliary classifier heads can be
replaced with rule-based projections from the structured operands (the
`register_mode` example in §3.1 shows the pattern), recovering ~2.9K params
and putting the redesign within ~2K of the original count.

The loss redesign adds zero parameters (admissibility table is a fixed
buffer; Fisher-Rao and RPM use existing code paths).

---

## 5. Capability gain

The hypotheses (each is falsifiable per §6):

1. **Structural-error rate drops sharply.** "Wrong but invalid" outputs
   (noetic/domain combinations the compiler rejects) should approach zero,
   because the admissibility loss penalizes them directly during training.
   Current K=9 checkpoint emits inadmissible structure on roughly 7% of
   held-out eval (HONEST_STATUS); target is <1%.
2. **Paraphrase-invariance improves.** Per the diagnoses memory, when
   canonical and paraphrase disagree the canonical is right 95-98% — pure
   invariance failure. The Inversion-Scan penalty during training should
   pull paraphrase predictions toward the same operator-balance profile,
   reducing template-prefix memorization.
3. **Calibration improves on the open simplex.** Fisher-Rao geodesic loss
   gives correct gradient at high confidence where CE is flat, so the
   distribution between near-tied 1st and 2nd choices should compress.
4. **Mode 7 trace becomes load-bearing.** Every loss term is named, so
   the per-example trace can attribute "this example was penalized
   primarily on N axis Inversion + admissibility violation" — addressing
   the user's traceability rule end-to-end on the loss path.

---

## 6. Falsifiable predictions

These should be cheap to test on a small synthetic eval (no full retrain
needed for the first three):

- **A.** Inject 10K synthetically inadmissible (operator, source, target)
  triples into the eval. Current model: high non-zero rate of inadmissible
  predictions. Redesigned head with admissibility loss: predicted rate of
  inadmissible outputs ≤ 1% after 1K training steps on the same corpus.
  *Falsified if* admissibility-rate ≥ 5%.
- **B.** Take 1K paraphrase pairs from the existing eval. Measure operator-
  balance gap (|p(^2) − p(^3)|, etc.) for canonical vs. paraphrase. Current
  model: gap correlates with paraphrase miss. Redesigned model: gap
  uncorrelated (Pearson |r| < 0.1). *Falsified if* the correlation is
  unchanged.
- **C.** Train two checkpoints to identical lm_loss, one with CE on the
  noetic head, one with Fisher-Rao on the joint state. Measure expected
  calibration error (ECE) at high-confidence decile. Hypothesis: Fisher-Rao
  ECE strictly lower. *Falsified if* ECE within 1 standard error.
- **D.** RPM-gated loss should not regress lm_loss on examples with
  satisfied prerequisites (sat ≈ 1). *Falsified if* lm_loss regresses by
  more than noise on satisfied-RPM examples.

A-D are all sample-level metrics, consistent with
`feedback_real_metric_is_samples.md`.

---

## 7. Risks

The top three:

1. **Admissibility table coverage gap.** The compiler's admissibility
   relation today covers state literals (`^N^D` pairs). It does NOT cover
   v7.6 production-semantics recipes or v7.7 register-multiplicity rules
   uniformly across all five generative operations. If the table is
   incomplete, the loss penalizes some real signal as inadmissible. Mitigation:
   gate the admissibility loss on the operations the compiler validates
   today (state, register_state, rule_four), zero-mass it on production /
   omega / meta_logic until the table extends. This matches the existing
   `_v77_relabeled` boundary.
2. **Fisher-Rao gradient pathology near boundary.** The open simplex excludes
   p_k = 0. The current `fisher_rao_distance` already clamps at 1e-12, but
   smoothing one-hot targets onto the simplex (eps / 40) introduces a
   target-mass-dependent bias. If eps is too small, gradient is near-zero
   and the model coasts; if too large, the loss landscape flattens. Likely
   eps ≈ 0.01 (1% mass on non-true classes) but this needs sweep.
3. **Joint structured loss (§3.6) is the most expensive change.** A CRF-
   style log-partition over the admissibility table is O(|admitted-triples|)
   per example. 16K is fine; v7.7 register-multiplicity expansion could
   blow that up to ~100K. Mitigation: keep §3.6 as last to land, gate
   behind a flag, and benchmark wall-clock on the existing eval before
   committing.

A fourth, lower-priority risk: the redesigned head is additive to the
existing model (see §9 below) but the 12-head decoder is wired into eval
harnesses, predict_cas, the chat REPL, the trace package, and the belief
substrate. Any change to the public output schema breaks all of them. The
redesign therefore must preserve the 12-key dict at the surface — it just
derives the 12 keys from the structured proposal instead of producing them
independently.

---

## 8. Code sketch

Pseudocode only. No production file is touched.

```python
# cas-native/model/topos_structured_head.py  (NEW, additive)

class ToposStructuredHead(nn.Module):
    def __init__(self, d_model, bottleneck=64, max_operands=4):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(d_model, bottleneck), nn.GELU(), nn.LayerNorm(bottleneck))
        self.op_head      = nn.Linear(bottleneck, 5)            # × ÷ ∘ + −
        self.operand_head = nn.Linear(bottleneck, max_operands * 25)  # 10+4+7+4
        self.omega_head   = nn.Linear(bottleneck, 2)
        self.aux = nn.ModuleDict({
            k: nn.Linear(bottleneck, n) for k, n in AUX_DIMS.items()
        })
        # Precompute admissibility once from compiler._is_admissible
        self.register_buffer("admit_table", build_admissibility_table())

    def forward(self, hidden, mask=None):
        z = self.backbone(_pool(hidden, mask))
        operands = self.operand_head(z).reshape(-1, MAX_OPERANDS, 25)
        return {
            "op_logits": self.op_head(z),
            "operand_logits": operands,           # slices: 0:10 N, 10:14 D, 14:21 F, 21:25 R
            "omega_logits": self.omega_head(z),
            **{k: h(z) for k, h in self.aux.items()},
            "_z": z,
        }


# cas-native/model/topos_structured_loss.py  (NEW, additive)

def topos_structured_loss(out, targets, *, lambdas):
    L_geo   = fisher_rao_on_joint_state(out, targets)            # §3.4
    L_admit = expected_admissibility_violation(out, admit_table) # §3.2
    L_inv_N = involution_imbalance(out["operand_logits"][..., :10])
    L_inv_F = involution_imbalance(out["operand_logits"][..., 14:21], DRIVE_PAIRS)
    L_inv_W = domain_precedence_violation(out)                   # §3.3
    L_aux   = sum(F.cross_entropy(out[k], targets[k]) for k in AUX_KEYS)

    sat = min_rpm_satisfaction(out)                              # §3.5
    L_total = (
        sat * (L_geo + L_admit + lambdas.aux * L_aux)
        + (1 - sat) * rpm_repair_loss(out)
        + lambdas.inv_N * L_inv_N + lambdas.inv_F * L_inv_F + lambdas.inv_W * L_inv_W
    )
    return L_total, {  # every term is a named scalar — traceability hook
        "geodesic": L_geo, "admit": L_admit, "inv_N": L_inv_N,
        "inv_F": L_inv_F, "inv_W": L_inv_W, "aux": L_aux, "rpm_sat": sat,
    }
```

---

## 9. Additive vs. replacement

**Additive.** Build `ToposStructuredHead` and `topos_structured_loss` as new
files alongside the existing `StructuredPredictionHead` and
`structured_prediction_loss`. Gate behind a `V2ComponentFlags` boolean
(`use_topos_structured_head`, default False) following the ADR-07 pattern.
When the flag is False, the model is byte-equivalent to the current K=9
checkpoint; when True, the new head is wired and the new loss runs.

The 12-key surface dict (`predict_cas.py`, chat REPL, belief store) is
preserved by `project_legacy_fields()`. No downstream consumer breaks.

This matches the user's parallel-don't-serialize rule
(`feedback_parallelize_sdg_with_training.md`): the v1 retrain on the pod
continues uninterrupted, and the redesign lands as a flagged option for the
next training cycle.

---

## 10. Citations

- `CLAUDE.md` — Corrections 1–4, 7 Inversion Axes, involution pairs.
- `docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 §6 — the 5
  Generative Operations (×, ÷, ∘, +, −).
- `docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10 §3 — operator
  discipline (`+` vs `×` vs `|⟨…⟩`).
- `docs\working\technical_feature_overview_extract.md` lines 83-87 — formal
  semantics of the 5 Generative Operations.
- `cas-native\model\structured_prediction.py` — current 12-head stack.
- `cas-native\model\loss.py` — `fisher_rao_distance`,
  `compute_operator_balance_loss`, `compute_domain_coherence_loss`,
  `compute_rpm_satisfaction_loss`, `compute_inversion_penalty` (reused).
- `cas-native\model\expression_proposer.py` — ADR-07 structured proposer
  (closest precedent for §3.1).
- `cas-native\model\topos_reasoner.py` — 3-valued proposition scorer; the
  redesign generalizes this pattern.
- `cas-native\model\rpm_gate.py` — RPM gate; satisfaction signal for §3.5.
- `api\notation\inversion.py` — 7-axis Inversion Scan; §3.3 is its
  probabilistic shadow over N/W/F (E/S/A deferred).
- `api\notation\compiler.py` `_is_admissible` (line 1588), v7.7 §4
  enforcement (line 2867) — source of the admissibility table in §3.2.
- `HONEST_STATUS.md` — 93.2% canonical-exact baseline; live pod retrain.
- Memory `feedback_real_metric_is_samples.md`,
  `feedback_object_traceability_required.md`,
  `project_paraphrase_failure_modes_diagnoses.md`,
  `feedback_no_foreign_architecture_cas_only.md`.
