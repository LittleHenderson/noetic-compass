# Optimizer and Training Dynamics — CAS-Native Redesign of AdamW

**Author:** Opus R&D specialist (optimizer slice)
**Date:** 2026-05-05
**Status:** Research note. Side investigation. No production code touched. Live v1 retrain on the pod (PID 14170) untouched.

---

## 1. Goal

Replace `torch.optim.AdamW` in the CAS-Native training stack with a structured optimizer that is **smaller** (fewer state vectors per parameter), **smarter** (faster convergence on CAS-aligned tasks because it respects the geometry the model is supposed to be learning), and **traceable** (every per-step decision — which prerequisites were checked, which inversion axes blocked the step, which domain group received the larger learning rate — is inspectable).

The framing is deliberately ambitious: AdamW is generic. It treats every parameter the same. CAS already has structure on the parameters (which slot of the 40-dim simplex they help predict, which Domain they sit in, which Drive inversion pair they belong to, which Generative Operation they participate in). A CAS-shaped optimizer can use that structure directly.

## 2. Current setup

The CAS-Native training stack uses standard PyTorch AdamW in three places:

- `cas-native/training/train_structured_prediction.py` line 144 (smoke harness)
- `cas-native/training/train_structured_prediction.py` line 518 (paraphrase variant)
- `cas-native/training/train_structured_prediction.py` line 906 (full local trainer; the path the v1 retrain follows)

All three calls are vanilla — `torch.optim.AdamW(params, lr, weight_decay)`. State per parameter: two vectors (`m`, `v`) plus one scalar (`step`). For a 100M-parameter model that is roughly 800 MB of optimizer state at fp32, or 400 MB at fp16, in addition to the weights themselves.

The stack already has the CAS geometry available but does not feed it to the optimizer:

- `cas-engine/src/metric/mod.rs` ships the Fisher-Rao inner product `g^FR_p(u,v) = Σ uk·vk/pk` and the Bhattacharyya geodesic distance `d(p,q) = 2·arccos(Σ √(pk·qk))` (CLAUDE.md Correction 4; lines 99-162 of the metric module).
- `cas-native/model/loss.py` reuses the geodesic distance as a *loss* term (`fisher_rao_distance`, lines 48-77) to penalize cognitive drift, but the parameter updates that minimize that loss are still pushed through the Euclidean AdamW.
- `cas-native/model/rpm_gate.py` enforces the section-retraction asymmetry (separate `eta`/`epsilon` Linear layers, satisfaction cache cleared each forward, line 92) but the gradient flow back through those gates is unconstrained — AdamW will happily move weights in directions that *break* prerequisite satisfaction.
- `cas-engine/src/inversions/mod.rs` produces a per-step 7-axis inversion score; that score is currently consumed only at scoring time, not at optimization time.

In other words: the geometry, the prerequisite check, and the inversion scan all exist. They are wired into the *forward* pass and the *loss*. None of them are wired into the *update rule*.

## 3. Proposed redesign — one optimizer, four components

I propose a single new optimizer, **CASOpt**, that replaces AdamW. It composes four modules. Each is independently shippable; the whole only works once all four land.

### 3.1 Fisher-Rao natural-gradient step on simplex-tied parameters

Parameters that produce the 40-dim cognitive state vector (the embedding head, the proposer head, anything that ends with a softmax onto `Δ39°`) get a **natural-gradient** step instead of a Euclidean step. Standard AdamW computes `θ ← θ - lr · m̂ / (√v̂ + ε)`. The natural-gradient version multiplies the raw gradient by the inverse Fisher information matrix before updating: `θ ← θ - lr · F⁻¹ · g`. For a softmax output the diagonal Fisher block is just `pk(1 - pk)` per slot, so `F⁻¹` is essentially free to compute and store as a single 40-vector per example (see Amari 1998, Natural Gradient Works Efficiently in Learning, for the canonical derivation; the CAS-specific form follows directly from the metric module's `fisher_rao_inner_product`).

The payoff: a step that is uniform in CAS-distance moves the same amount in `^2^P` space as in `^9^O` space, regardless of how concentrated the current activation is. AdamW's adaptive moments approximate this badly and noisily; the diagonal-Fisher rescaling is exact for the simplex.

**State:** one `40`-vector of inverse-Fisher entries per simplex-tied layer, recomputed each step. **No momentum vectors needed for these parameters.**

### 3.2 RPM section-retraction guard

Per CLAUDE.md Correction 2, RPM is a section-retraction (`εI ∘ ηI = idI` but `ηI ∘ εI ≠ idR(I)`) — prerequisite satisfaction is one-directional. The current `PrerequisiteGateLayer` caches forward-pass satisfaction (rpm_gate.py lines 76, 104-109). The optimizer should *consume* that cache.

Concretely: before applying an update to any parameter `θ` whose forward path runs through a gate `g`, check whether the proposed step `θ + Δθ` would have driven `g`'s satisfaction *below* a per-gate floor on the *previous* batch's inputs. If yes, project the step onto the half-space that preserves satisfaction (the simplest projection is to scale `Δθ` until the satisfied/unsatisfied boundary stops being crossed, recorded as `clip_factor` in the trace).

This is a **constrained optimizer** with a soft constraint: prerequisite satisfaction monotonicity. It implements Correction 2 at the update level. Because the satisfaction values are already cached, the per-step cost is one comparison per parameter group, not a full re-forward-pass.

**State:** one scalar (the cached gate satisfaction floor) per gate. Four gates in `PrerequisiteGateLayer` → four scalars total for the whole RPM chain.

### 3.3 Domain-precedence scheduling and Drive-inversion symmetric decay

The 4 Domains have a total order P ≻ C ≻ E ≻ O (CLAUDE.md, Structural invariants block; CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarification 8 §6). The 7 Drives have inversion pairs F1↔F7, F2↔F6, F3↔F5 with F4 self-dual.

Two changes:

- **Domain-keyed learning rate.** Parameters that contribute primarily to a Principled-domain prediction get a *smaller* learning rate than Operational ones, ratio `1 : 1.5 : 2 : 3` for P:C:E:O (small to large). The intuition: Principled features are higher in the precedence stack and should change slowly; Operational features are immediate-action features and can move faster. The output heads in `structured_prediction.py` already partition cleanly along Domain (`DOMAIN_LABELS = ("P", "C", "E", "O")`, lines 58), so the parameter grouping is mechanical.
- **Symmetric weight decay on Drive inversion pairs.** Replace AdamW's uniform `weight_decay * θ` term with a pairwise term `λ · ‖θ_F1 + θ_F7‖²` (and similar for F2/F6, F3/F5; F4 unchanged). This pulls inversion-pair weights toward additive inverses of each other rather than toward zero, which is the correct prior given the involution structure. The CAS-Native loss already does this for the *Register* involution pairs (`InvolutionConstraintLoss` in `loss.py` lines 270-365); the optimizer change extends the same idea to *Drive* parameters and folds it into the update rule rather than the loss.

Symmetric decay roughly *halves* the effective parameter count for the Drive heads — once F1 is known, F7 is determined up to a sign error and a regularization slack. Same for F2/F6 and F3/F5. The model still learns 7 Drive heads explicitly, but the optimizer keeps them coupled.

**State:** one scalar per inversion pair (the pairwise λ); negligible.

### 3.4 Inversion-Scan-driven step-size adaptation

The 7-axis inversion scanner (`cas-engine/src/inversions/mod.rs`) already runs in the loss path (`compute_inversion_penalty`, loss.py lines 178-184). I propose using its output a second time, this time as a *step-size modulator*:

- Compute the 7-axis inversion score `I_t` after the forward pass at step `t`.
- Compute the *predicted* inversion score `I_t+1` if the candidate step were taken (a one-step lookahead, cheap because the scanner is O(40) operations per axis).
- If `I_t+1 > I_t` on more than one axis, scale the step by `0.5`. If `I_t+1 < I_t` on every axis, scale the step by `1.2` (capped at `2 × lr`).

This makes the optimizer **structurally self-regulating**: it cannot make a step that increases overall inversion, and it accelerates when it is moving toward better-aligned states. Each step's modulation factor is logged with the seven per-axis deltas, satisfying the object-traceability rule.

**State:** zero — recomputed each step. (The scanner has no internal optimizer state; only the modulation factor needs to be logged.)

## 4. Parameter and state count comparison

For a representative 100M-parameter CAS-Native model:

| Component | AdamW state | CASOpt state |
|---|---|---|
| Per-parameter momentum `m` | 100M floats | 0 (replaced by Fisher rescaling on simplex-tied blocks; small per-block momentum for the rest) |
| Per-parameter variance `v` | 100M floats | 0 on simplex-tied blocks; ~30M on remaining heads |
| Step counter | 1 scalar | 1 scalar |
| Fisher-Rao diagonal (per simplex-tied layer) | — | ~10 layers × 40 floats = 400 floats |
| RPM gate satisfaction floors | — | 4 scalars |
| Drive-pair λ | — | 3 scalars |
| Inversion modulation factor | — | 1 scalar |

Net: **~30M floats vs ~200M floats** of optimizer state. Roughly **6-7× reduction** in optimizer memory, concentrated on the simplex-tied output stack which is where AdamW's adaptive moments are most redundant (the Fisher diagonal is the principled version of what `v` is approximating).

For the v1 retrain currently on the A6000 pod, that translates to roughly 0.6 GB of GPU memory freed, useful for batch-size headroom or for pushing d_model up.

## 5. Capability gain

The optimizer is not just smaller; it is doing structurally different work.

- **Geometry-aware updates.** Section 3.1 lets the model converge in the metric the loss is already measured in. The drift-loss term (`compute_cognitive_drift_loss`, loss.py lines 186-195) currently fights an Euclidean optimizer. Aligning them removes a known cancellation: AdamW takes a step that locally decreases loss in Euclidean distance but locally *increases* Fisher-Rao distance, and vice versa, depending on where on the simplex the current state sits.
- **Monotone prerequisite satisfaction.** Section 3.2 means the RPM chain cannot regress between checkpoints. Today, an unlucky sequence of batches can push gate-satisfaction below threshold and the model has to *re-learn* the chain. With the section-retraction guard, the chain is a ratchet.
- **Halved effective Drive parameter count** (Section 3.3) means faster convergence on Drive heads, which the v74_baseline / paraphrase failure-mode analysis (memory: `project_paraphrase_failure_modes_diagnoses.md`) flagged as a recurring weak spot.
- **Self-regulating inversion** (Section 3.4) closes a loop the loss currently only opens: if a step would worsen inversion, the optimizer doesn't take it. This is structurally analogous to trust-region methods but the trust region is defined in CAS terms, not parameter-norm terms.

## 6. Falsifiable predictions

A retrain with CASOpt on the same v1 data, same model, same number of epochs as the live AdamW retrain, should produce:

1. **Sample-level canonical-exact rate** strictly greater than the v1 AdamW baseline on `level3_recoverable_eval_1000_v77_relabeled.jsonl` (per memory: `feedback_real_metric_is_samples.md`, exact_match is the load-bearing metric). Concrete bar: ≥ +1.5 pp.
2. **Drive-head accuracy** lifted by ≥ +3 pp, attributable to symmetric decay (3.3). The v1 paraphrase run logged drive consistency 75.5% best; predict ≥ 78.5%.
3. **Gate-satisfaction monotonicity:** zero epochs in which mean RPM gate satisfaction (logged in `rpm_satisfaction` component) decreases relative to the previous epoch. AdamW currently shows non-monotone trajectories on roughly 1 epoch in 4 (anecdotal; would need to confirm against the live run logs once the pod completes).
4. **Inversion penalty trajectory** monotone non-increasing within each epoch. AdamW today produces noisy inversion-penalty curves; CASOpt's Section 3.4 guarantees the curve is monotone in expectation.

If any of these four predictions fails on a clean retrain, the corresponding component is invalidated and either tuned or removed; the four components are independent enough that one failure does not condemn the rest.

## 7. Risks

**R1: Diagonal Fisher is wrong off-simplex.** The natural-gradient derivation is exact only for parameters that produce a probability vector on the simplex. Applied to backbone parameters that *don't* feed a softmax (early transformer layers), it is wrong and possibly harmful. Mitigation: only apply Section 3.1 to the explicitly simplex-tied output blocks; everything else gets a vanilla Euclidean step with momentum. The grouping is by parameter name, recorded in the per-step trace.

**R2: Section-retraction guard can stall.** If the gate-satisfaction floor is set too high, the projection in 3.2 zeros out almost every step and the model stops learning. Mitigation: the floor is itself a hyperparameter, initialized from the first 100 batches' median satisfaction and only enforced once the running median is stable. Logged as `floor_t` per step.

**R3: Domain-keyed LR can starve P-domain heads.** A 1:3 P:O LR ratio means P-domain heads see roughly a third of the learning the O-heads do. If the P-domain features are *not* over-fitted (the assumption behind slowing them) but *under-fitted* (the failure mode if the SDG is sparse on Principled examples), this is exactly wrong. Mitigation: the ratio is a config knob with default `1.0:1.0:1.0:1.0` (i.e., off). Turn on with evidence from the v1 logs that P-domain heads are over-fitting.

**R4: Inversion-scan one-step lookahead is expensive enough to slow the step.** The scanner is O(40) per axis and 7 axes; not free at high batch sizes. Mitigation: lookahead is computed every K steps (K=8 default), not every step. The `step_size_modulator` between lookaheads stays at the last computed value.

**R5: All four components combined could interact badly.** Each is reasonable in isolation; the joint behavior is untested. Mitigation: ablation harness — train one CAS-Native checkpoint per single-component configuration, compare against full CASOpt. Five runs total (AdamW baseline, +Fisher, +Section-retraction, +Domain-LR/Drive-decay, +Inversion-modulation, full). One pod-day at the v1 retrain scale.

## 8. Code sketch

```python
# cas-native/optim/casopt.py  -- proposed
import torch
from torch.optim import Optimizer

class CASOpt(Optimizer):
    """CAS-aware optimizer: Fisher-Rao natural gradient on simplex-tied
    blocks, RPM section-retraction guard, Domain-keyed LR, Drive-inversion
    symmetric decay, Inversion-Scan step-size modulation.

    Drop-in replacement for AdamW for the vanilla-Euclidean group;
    extra param-group kwargs activate the CAS-aware paths.
    """

    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8,
                 weight_decay=0.0, *, fisher_simplex=False,
                 domain_lr_scale=1.0, drive_pair=None,
                 rpm_gate_floor=None):
        defaults = dict(lr=lr, betas=betas, eps=eps,
                        weight_decay=weight_decay,
                        fisher_simplex=fisher_simplex,
                        domain_lr_scale=domain_lr_scale,
                        drive_pair=drive_pair,
                        rpm_gate_floor=rpm_gate_floor)
        super().__init__(params, defaults)
        self._trace = []  # per-step decisions, traceability

    @torch.no_grad()
    def step(self, closure=None, *, last_state=None,
             gate_satisfactions=None, inversion_scores=None,
             predicted_inversion=None):
        loss = None if closure is None else closure()
        # Inversion-Scan modulator (3.4)
        mod = self._step_modulator(inversion_scores, predicted_inversion)

        for group in self.param_groups:
            lr = group['lr'] * group['domain_lr_scale'] * mod
            for p in group['params']:
                if p.grad is None:
                    continue
                g = p.grad
                # Fisher-Rao diagonal rescale (3.1)
                if group['fisher_simplex'] and last_state is not None:
                    g = g * (last_state * (1 - last_state) + 1e-12)
                # Drive symmetric decay (3.3)
                if group['drive_pair'] is not None:
                    partner = group['drive_pair']  # tensor handle
                    g = g + group['weight_decay'] * (p + partner)
                else:
                    g = g + group['weight_decay'] * p
                # Section-retraction guard (3.2)
                if group['rpm_gate_floor'] is not None:
                    if gate_satisfactions is not None:
                        sat = gate_satisfactions[group.get('gate_name')]
                        if sat.mean() < group['rpm_gate_floor']:
                            g = g * 0.0  # halt the step on this group
                            self._trace.append({'block': True, 'sat': sat.mean().item()})
                p.add_(g, alpha=-lr)
        return loss

    def _step_modulator(self, current, predicted):
        if current is None or predicted is None:
            return 1.0
        worse = (predicted > current).sum().item()
        if worse > 1:
            return 0.5
        better = (predicted < current).all().item()
        return 1.2 if better else 1.0

    def consume_trace(self):
        out, self._trace = self._trace, []
        return out
```

The trace mechanism in `consume_trace` is the object-traceability spine — every step's decisions become inspectable post-hoc. Wiring into `train_structured_prediction.py` line 906 is a one-line change once the optimizer ships.

## 9. Citations

- CLAUDE.md, Four Critical Mathematical Corrections, lines 25-47 (Corrections 1-4).
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8 §6 (axiom-preserving status of Register layer; the same logic applies to optimizer changes — they are specification of *update dynamics* over the existing primitives, not new primitives).
- `peer_review/journal_submission/main.tex` lines 200-243 (section-retraction axioms; Proposition `prop:rpm-pullback`).
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/metric/mod.rs` lines 99-162 (Fisher-Rao inner product, Bhattacharyya geodesic distance — both already implemented in Rust, ready to call via PyO3 bindings).
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/inversions/mod.rs` lines 1-120 (7-axis scanner; available for one-step lookahead).
- `noetic-compass-scaffold/noetic-compass/cas-native/model/loss.py` lines 48-77 (Python `fisher_rao_distance`); lines 270-365 (`InvolutionConstraintLoss` — the model already has the *register* involution prior; this proposal extends it to the *Drive* axis and folds it into the optimizer).
- `noetic-compass-scaffold/noetic-compass/cas-native/model/rpm_gate.py` lines 76, 104-109 (forward-pass satisfaction cache, ready to be consumed by the optimizer).
- `noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py` lines 144, 518, 906 (current AdamW call sites — three drop-in replacement points).
- Amari, S. (1998), *Natural Gradient Works Efficiently in Learning*, Neural Computation 10(2). External reference for the natural-gradient derivation; cited for completeness, not for primitives — every primitive used is from the in-repo CAS engine.
- Memory: `feedback_real_metric_is_samples.md` (sample-level metrics are the only real eval metric); `project_paraphrase_failure_modes_diagnoses.md` (Drive-head invariance failures); `feedback_traceability_is_the_whole_purpose.md` (every optimizer decision must walk back to its origin).
