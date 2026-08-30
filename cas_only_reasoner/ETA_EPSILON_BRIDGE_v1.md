# The η–ε Bridge — Formal, Empirical, and Proposed

Filed 2026-08-29. Corrected after external technical review. This
document keeps three layers strictly separate and never lets one
borrow authority from another:

- **PART I — FORMAL.** What the Noetic Topos / v7.4 documents actually
  prove. Verified verbatim against source files.
- **PART II — EMPIRICAL.** What the CAS Harness η→ε bridge actually
  is and measures. Verified against the spec sheet. It is **not** the
  formal section-retraction; the types do not match.
- **PART III — PROPOSED (UNTESTED).** A weight-learning use of the
  bridge + CAS-Ohm. Every claim here is a hypothesis with a
  falsifier. Nothing in Part III is demonstrated.

Governed by `CORRECTION_RECORD_v1.md` §8: no claim here may be
re-inflated without new runnable evidence.

---

## PART I — THE FORMAL BRIDGE (verified from source)

### I.1 The section-retraction pair

From `docs/whitepapers/monograph/noetic_topos2/chapters/ch05_legacy_collapse.tex`,
verbatim:

$$\eta_X : X \to R(X), \qquad \varepsilon_X : R(X) \to X, \qquad \varepsilon_X \circ \eta_X = \mathrm{id}_X.$$

- **η_X is a SECTION** (a split monomorphism): the embedding of an
  ideal state `X` into its realized/potentialized form `R(X)`.
- **ε_X is a RETRACTION** (a split epimorphism): realization of
  prerequisites, `R(X)` back down to `X`.
- **ε is NOT a counit.** The source states expressly *"Section-
  retraction, not adjunction."* Calling ε a "counit" imports an
  adjunction the document denies. (Correction to the prior
  explanation: ε is a **retraction / split epimorphism**, not a
  counit.)

### I.2 The exact composite — correct order

$$X \xrightarrow{\ \eta\ } R(X) \xrightarrow{\ \varepsilon\ } X, \qquad \varepsilon \circ \eta = \mathrm{id}_X.$$

**Embed first (η), then retract (ε): you recover the original `X`.**
(Correction: the prior summary line "realize-then-recover is exact"
stated this backwards. The exact composite applies η *first*. The
correct English is: *embed, then realize — identity.*)

### I.3 The asymmetry — the other composite is not the identity

From the same chapter, verbatim remark:

$$\eta \circ \varepsilon \ \neq\ \mathrm{id}_{R(X)}.$$

> "re-embedding after realization may lose information, and
> prerequisite [satisfaction is one-directional]."

$$R(X) \xrightarrow{\ \varepsilon\ } X \xrightarrow{\ \eta\ } R(X) \ \neq\ \mathrm{id}.$$

**Retract first, then re-embed: realization detail can be lost.** The
collapse argument uses ONLY `ε∘η = id_X` and never assumes
`η∘ε = id`, invertibility, or any adjunction triangle.

### I.4 The idempotent projection (was omitted before — it belongs)

Because `ε∘η = id_X`, the other composite

$$P := \eta \circ \varepsilon : R(X) \to R(X)$$

is **idempotent**:

$$P^2 = (\eta\varepsilon)(\eta\varepsilon) = \eta(\varepsilon\eta)\varepsilon = \eta\,\mathrm{id}_X\,\varepsilon = \eta\varepsilon = P.$$

So `P` is a **projection** onto the part of `R(X)` representable
canonically through `X`; `X` is a retract of `R(X)`. This is the
structurally useful object for later use, and it was missing from the
earlier explanation.

### I.5 The monad unit is a SEPARATE construction

v7.4 presents the RPM as a **monad** with unit `return : X → R(X)`
and the left/right unit (monad) laws (`_tmp_TKS_v7_4_FULL_CORRECTED.txt`,
"the unit lifts a value into a successful RPM computation"). A
section-retraction is **not, by itself, a monad**. The prior
explanation casually identified the monad `return` with the section
η; that identification is **not established** here — it needs a typed
bridge between the RPM monad and the potentialization endofunctor
that carries the section-retraction. Until such a bridge is written,
treat them as two different `R` constructions that share notation.
(Caveat: the claim that the project's own audit explicitly separates
them is carried from the external review; the underlying category
theory — section-retraction ≠ monad — is independently true.)

### I.6 The collapse — and what it does NOT do

`ch05` Lemma (verbatim): if `ε : E → X` is a split epimorphism with
section `η` (`ε∘η = id_X`) and `ε ∈ S` for a sieve `S`, then `S = m_X`
(the maximal sieve), because `ε∘η = id_X ∈ S`. Declaring `{ε_X}`
covering therefore collapses the covering sieve to maximal — the
"legacy RPM collapse."

**This is a sieve argument. It yields no weight-update equation.** Any
weight machinery in Part III comes from a readout Jacobian and its
inverse, not from this collapse.

---

## PART II — THE EMPIRICAL HARNESS BRIDGE (verified; NOT the formal pair)

### II.1 What the harness maps actually are

From `docs/CAS_HARNESS_SPEC_SHEET.md` line 199, verbatim: *"read a CAS
class out of the hidden states (η), rewrite that class as a readable
English prefix (ε), prepend it to the original prompt, re-run the
model, and measure how far the next-token log-likelihood moves."*

$$\eta_{\text{harness}} : \text{hidden activations} \to \text{CAS class} \quad(\textbf{readout})$$
$$\varepsilon_{\text{harness}} : \text{CAS class} \to \text{English prefix} \quad(\textbf{realizer})$$

### II.2 Why it is NOT a section-retraction

$$\varepsilon_{\text{harness}} \circ \eta_{\text{harness}} : \text{hidden activations} \to \text{prefix tokens} \ \neq\ \mathrm{id}_{\text{hidden}}.$$

The codomain is wrong: the composite lands in prefix-token space, not
back on the hidden-state space. It **cannot** be `id` on hidden
states. Worse, the naming **inverts** the formal convention: the
harness `η` is a *readout* (the formal ε's direction), the harness
`ε` is a *realization to prefixes* (not the formal η, and not back to
activations). So the shared symbols are a naming coincidence, not an
instantiation of Part I.

### II.3 The honest empirical loop is CYCLE-CONSISTENCY, not ε∘η=id

To close a real loop the model `F_θ` must appear:

$$z \xrightarrow{\text{realize}} u \xrightarrow{\ F_\theta\ } h' \xrightarrow{\text{probe}} z', \qquad \text{condition: } z' \approx z.$$

i.e. `Probe(F_θ(Realize(z))) ≈ z`. This is a **cycle-consistency
test**, and it is an *empirical, measurable* condition — not the
formal identity `ε∘η = id`. Reachability of every target CAS state
must be **measured**; prefix influence is not surjectivity.

### II.4 Verified status of the harness bridge

- Status (spec sheet §4.2 line 172): **`REAL` + `OPEN (missing
  pre-registered control)`**, claim ceiling **`PARTIAL`**.
- GPT-NeoX-20B 40E: probe-readable likelihood shift Δ **+1.412050**,
  probe-minus-partner margin **+2.881239**, probe/gold handoff
  **94.3%**.
- Raw-CAS-symbol prefix control **null at every scale** (−0.020 to
  +0.003) — the effect is not just "some prefix moves the logit."
- **The lossiness of the realizer (WELD v2) does NOT prove the formal
  asymmetry `η∘ε≠id`.** Generic projections are lossy; that the
  empirical realizer loses information is expected of any lossy map
  and is *not* evidence that the empirical maps instantiate the
  formal section-retraction. (Correction: the prior explanation drew
  this connection too tightly.)

---

## PART III — PROPOSED WEIGHT-LEARNING USE (UNTESTED HYPOTHESES)

Nothing below is demonstrated. Each block is a proposal with a
falsifier. This layer reinterprets `X` and `R(X)` for machine
learning — a NEW assignment of meaning, not the formal document's.

### III.1 The proposed orientation

- `X` := **CAS behavior space** (e.g. correct active/passive role
  binding; a direction on the 40-state simplex).
- `R(X)` := **neural realization space** (a LoRA adapter, a low-rank
  weight update, a steering vector).
- `η : X → R(X)` := **realization map** — desired CAS behavior →
  candidate weight update.
- `ε : R(X) → X` := **readout map** — resulting weights → the CAS
  behavior actually implemented.

Desired: `ε∘η ≈ id_X` (ask for a behavior, synthesize a realization,
read it back — the behavior returns). And `η∘ε ≠ id_{R(X)}` on
purpose: **many weight configurations implement nearly the same
behavior**, so a behavior does not determine unique weights. The goal
is therefore *"the smallest CAS-effective weight update that realizes
the target,"* not "the correct weights."

### III.2 The linear instantiation (this part is exact)

Frozen probe `ε(h) = A h`, `A ∈ ℝ^{k×d}` (use **39** independent
coordinates for the 40-simplex; the probabilities sum to 1). If `A`
has full row rank, the least-norm right inverse

$$\eta = A^\top (A A^\top)^{-1}, \qquad A\eta = I_k \ \Rightarrow\ \varepsilon\circ\eta = I_k \text{ exactly (linearized).}$$

`P = ηA` is the orthogonal projector onto `row(A)` (`P² = P`), so
`h = Ph + (I−P)h`: `Ph` is CAS-visible, `(I−P)h` is **not seen by the
probe and must not be discarded**.

### III.3 Activations → weights (local, first-order)

For trainable params `φ` (one LoRA adapter), readout coordinate
`ξ = ε(h_ℓ(φ,x))`, Jacobian `J_φ = ∂ξ/∂φ`, regularized pseudoinverse
`J_φ^†`:

$$\boxed{\ \Delta\phi_{\text{pred}} = J_\phi^{\dagger}\,\Delta\xi^{*}\ }$$

Apply `φ' = φ + αΔφ_pred`, measure `Δξ_obs`, bridge error
`e_bridge = ‖Δξ_obs − Δξ*‖` (or Fisher-Rao distance on the full
simplex). **Local, first-order, test-point / model / adapter
specific. Not a global inverse of the Transformer.**

### III.4 CAS-Ohm as dose→response (proposed; NOT in current source)

Direction comes from the gradient / §III.3. CAS-Ohm would predict
*magnitude*: dose `a = α‖Δφ_pred‖`, signed movement
`y = ⟨Δξ_obs, u*⟩`, `ŷ = a / r_eff`, residual `δy = y_obs − ŷ`. Only
admissible under a fixed model-specific profile with real units,
declared uncertainty, calibration on one split, evaluation on a
**disjoint** split — never `r = a/y` from a sample then "validated"
on the same sample.

**The two errors stay separate:** `e_bridge` (did we reach the target
CAS state?) vs `δy` (was the response the predicted size?). They can
disagree, and a CAS coordinate reached while the *task* still fails
means the CAS representation is insufficient — flow and produced
effect must not be collapsed.

### III.5 CAS-native importance (proposed) and selective plasticity

Fisher-Rao pulled back through the readout Jacobian:

$$F^{\text{CAS}}_g = J_g^\top\, G_{\text{FR}}(z)\, J_g, \qquad \Omega^{\text{CAS}}_g = \mathbb{E}_{x\in H}\big[\mathrm{tr}(J_g^\top G_{\text{FR}}(z) J_g)\big].$$

Split a later gradient `g` by the projector: `g_∥ = Pg` (CAS-visible),
`g_⊥ = (I−P)g`. Protect a mastered skill by raising resistance on
`g_∥`. Graduated states **PLASTIC / DAMPED / CONSOLIDATED / FROZEN /
REOPENED**, EWC-style soft penalty
`L = L_new + λ Σ_g Ω_g ‖θ_g − θ_g*‖²`.

**Consolidate only when ALL hold** (a small gradient alone is NOT
enough — a neuron may be dead, saturated, or bypassed): held-out
correctness, causal importance (ablate→degrade, restore→recover),
stability across seeds/batches, specificity, no protected regression,
declared confidence.

### III.6 Honest status of the CAS-Ohm dependency

- Current CNCM: CAS-Ohm is **optional instrumentation outside the
  reasoning loop; no board imports it; source synthetic; no live
  model measured.**
- Current paper: CAS-Ohm is **not a validated measure of attention or
  a causal law.**
- 40-simplex caveat: ordinary Fisher-Rao is **permutation-invariant**
  (all distinct pure states equidistant), so it does not by itself
  encode which CAS labels are semantically related. The matched-
  taxonomy control **has not passed**; CAS specificity is **open**.

### III.7 The one decisive first experiment + falsifiers

Small open-weight model, LoRA only, one narrow skill (active/passive
role binding — the known failure). Conditions: **A** plain LoRA · **B**
LoRA+EWC · **C** η–ε right-inverse update · **D** C + CAS-Ohm dose ·
**E** D with shuffled CAS labels · **F** same dims, random probe.

Pre-registered falsifiers (freeze before running):
- C not beating A → the right-inverse did not help.
- D not beating C → CAS-Ohm added nothing.
- E as good as D → CAS *semantics* add no value (only dimensionality).
- F as good as D → benefit is compression, not CAS.
- cycle-consistency improves but task accuracy does not → CAS
  coordinate insufficient for the skill.
- measurement overhead > compute saved → no wall-clock claim allowed.

**Plausible first win (not a promise):** a Transformer learns a
*sequence* of skills with fewer trainable parameters, less
forgetting, and less backward compute than ordinary fine-tuning —
which must still beat EWC/SI/OGD/LoRA baselines under matched
conditions. It will **not** make pretraining a general model "10× faster."

---

## The one-line reading of the asymmetry, corrected

$$\varepsilon\circ\eta = \mathrm{id}, \qquad \eta\circ\varepsilon \neq \mathrm{id}$$

means, for the proposed ML use: **a desired CAS behavior may have a
reproducible neural realization, while that behavior does not uniquely
determine the weights that realized it.** So ask the bridge for the
smallest CAS-effective update that realizes the target — never for
"the correct weights," which may not exist.

## Sources
`ch05_legacy_collapse.tex` (η/ε pair, not-an-adjunction, collapse) ·
`appD_glossary.tex` (§Section-retraction, §Unit) ·
`_tmp_TKS_v7_4_FULL_CORRECTED.txt` (monad `return`) ·
`docs/CAS_HARNESS_SPEC_SHEET.md` §4.2 (harness η/ε types + status +1.412) ·
`docs/working/gate5_weld/WELD_SPEC_V2.md` (realizer lossiness, J2 absent).
External literature (proposals): EWC (PNAS 2017), Synaptic
Intelligence, Orthogonal Gradient Descent, LoRA (arXiv 2106.09685),
FreezeOut (arXiv 1706.04983).
