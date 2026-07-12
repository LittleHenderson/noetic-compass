# Can CAS PCBA (CJT + RPM) Improve CAS Harness? — Decision Report

**Date:** 2026-06-30 · **Framework:** CAS v7.7 / CAS PCBA (CJT/CCDL/CCB) · **Confidential**
**Method:** multi-agent workflow `wf_0e1aa032-fc8` — 5 parallel readers (PCBA book theory, existing cas-forex CJT/PCBA/CCB code, Harness ablation internals, the prior W0 empirical result, RPM/diode section-retraction), then per-binding design → 3-lens adversarial verification (empirical-falsifiability / overclaim-honest-NULL / metrology-feasibility), synthesized in the foreground after the background run stalled.
**Claim-status words preserved exactly:** LICENSED / NOT LICENSED / OPEN / GREY / NULL / FALSIFY / ACCEPT / FLAG_FOR_HUMAN_REVIEW / BLOCKED_SURFACE_LEAKAGE / ENGINEERED-NOT-VALIDATED / prototype.

---

## 1. Executive verdict

**Yes — CAS PCBA helps CAS Harness, but as pre-registered test *design and grammar*, not as validated capability.** The verification panel was unanimous and decisive: **all 13 adversarial verdicts across all 5 bindings returned `NEEDS_EMPIRICAL_BRIDGE`** — not one binding is `LOAD_BEARING` (validated), and not one is `REFUTED`/`ASPIRATIONAL_METAPHOR` (useless). They are genuinely falsifiable hypotheses with a real reuse path into existing harness code — and every one is unbuilt or unrun, and the single prior empirical attempt at this exact shape **FAILED**.

**The single biggest concrete win (lowest-risk, highest-leverage):** adopt the **existing, tested `cas-forex` CJT/PCBA grammar + typed schema as the Harness's spec layer** — so CJT hypotheses are written in a checked grammar (`CJT< cause | bias => effect >`) with a **no-ACCEPT claim-ceiling type** that enforces the honest-NULL discipline at the type level, instead of being rebuilt. This is buildable now, needs no GPU, and adds nothing the harness must walk back.

**The scientific win** the CJT contributes: it converts open-ended "go find circuits" into a **named, pre-registered causal hypothesis with a built-in knockout (cutoff) test** that maps directly onto the harness's existing subspace-ablation operation; RPM/diode adds a *directional* (asymmetric) test sharper than correlation. **The catch** the original LLM conversation did not have: the prior empirical run is the controlling datum, and it returned **`BLOCKED_SURFACE_LEAKAGE`**.

---

## 2. Per-binding ruling (all NEEDS_EMPIRICAL_BRIDGE; tiered by readiness)

| # | Binding | Ruling | Closest-prior empirical state | Strongest surviving objection |
|---|---------|--------|-------------------------------|-------------------------------|
| 1 | **cjt-as-ablation** (CJT cutoff = ablate BIAS subspace, watch a held-fixed EFFECT readout collapse) | NEEDS_EMPIRICAL_BRIDGE — *closest to shippable* | FAIL (W0 BLOCKED_SURFACE_LEAKAGE); a later counterbalanced bank cleared the surface *screen* but the hidden-state ablation was never run on it | The existing runner **retrains** the readout after ablation (recoverability, not knockout); `shippable_now:true` is overstated — needs a ~30 LOC fixed-probe variant |
| 2 | **rpm-diode-asymmetric-gate** (suppress W collapses P; suppress P spares W) | NEEDS_EMPIRICAL_BRIDGE — *sharpest claim, most confounds* | Never run (no cross-label executor exists anywhere in the project) | Even a clean two-leg PASS is **confounded by subspace subsumption** (P ⊂ span(W)) and **probe-strength asymmetry** — neither ruled out by the proposed guard |
| 3 | **cascade-search-order** (cutoff at stage k names the next stage to probe) | NEEDS_EMPIRICAL_BRIDGE | Directedness empirically unestablished | Sits on top of #1 and #2; the directed "walk-down" is an architecture diagram until the asymmetric edge (#2) is demonstrated |
| 4 | **ccb-csb-reusable-fixture** (a fixed CJT/RPM probe battery = an instrument) | NEEDS_EMPIRICAL_BRIDGE | Its load-bearing node is the same shape as the prior FAIL | The surface-leakage screen + bank builder live on a *different branch*; "robust" = robust-as-design, never robust-as-result |
| 5 | **eta1-eta2-first-node** (two-bridge detector as one CJT) | NEEDS_EMPIRICAL_BRIDGE — *NOT the easiest first node, despite the original recommendation* | Qwen p=9e-5 separation exists but is a **behavioral-divergence detector, NOT a hijack detector** | **Axis substitution**: the existing PASS is RISK-vs-CONTROL at the *prompt* stage (W0, zero generated tokens); the hijack-vs-refusal axis it claims is *post-generation* and needs η₂ emitted-text capture that does not exist |

**Lens reconciliation:** where the three lenses disagreed on `survives_surface_leakage_discipline`, the more conservative reading governs — the empirical-falsifiability and overclaim lenses repeatedly flagged that the *surface screen passing in design* is not the *hidden capture passing on data*, and on the cascade/CSB bindings one verifier checked git and found the surface-clean **hidden** sweep has never beaten the +0.15 margin (the layer-sweep JSON in the "v1 PASS" commit is byte-identical to the stale FAIL sweep). So: surface screen honored as a mandatory pre-flight ✓; hidden-state pass ✗ (never achieved).

---

## 3. The concrete first node — corrected

The original conversation recommended shipping the **η₁/η₂ detector** first. **The panel disagrees, with evidence:** η₁/η₂ needs the *hardest* prerequisites — η₂ emitted-text hidden-state capture (generated tokens, which W0 lacks), a *behavioral* hijack-vs-refusal axis, and a Qwen typed probe that doesn't exist — and its only prior result conflates hijack with refusal. It is the **last** node to ship, not the first.

**The genuinely-closest first node is `cjt-as-ablation` (the CJT cutoff *necessity* test)**, specced as:

- **Cause terminal (C, ^8 Above/Cause):** the incoming prompt content, captured as W0 residual-stream hidden states; probed as a separate `labels_cause` readout (not the ablation target).
- **Bias terminal (B, ^5 Female):** the accumulated safety/policy substrate, recovered as the SVD subspace of a trained bias probe's coefficients (`_coef_subspace_basis`). **This subspace is the ablation target.**
- **Effect terminal (E, ^9 Below/Effect):** the compliance/refusal state, read by a **held-FIXED** effect probe — *do not retrain after ablation*.
- **Exact ablation:** reuse `run_stage9_40e_subspace_ablation.py`'s `_project_ablate_with_scaler` to remove the bias subspace, then score the **fixed** effect probe; compare against the existing random same-rank orthonormal null (the harness's validated falsification baseline, 0.068 pp).
- **PASS:** (i) clean effect-probe hidden BA ≥ 0.75 **and hidden-minus-char/length margin ≥ 0.15** on a surface-clean bank that has cleared `screen_cjt_bias_vibration_surface_leakage.py` at `max_baseline_ba ≤ 0.60` *before any GPU capture*; (ii) post-ablation effect collapse exceeds the random null by ≥ 5 pp guard. **FALSIFY** if any leg fails — explicitly including the exact prior failure mode (hidden-minus-char **+0.042 < 0.15** → `BLOCKED_SURFACE_LEAKAGE`).
- **Verdict ceiling:** `FLAG_FOR_HUMAN_REVIEW` (the `CjtClaimCeiling` enum has **no ACCEPT** value; `merge_stage9_40e_evidence_packet.py` hard-codes FLAG).
- **What a PASS licenses (and only this):** *"on one open-weight model, removing the bias-direction subspace causally collapses the effect readout toward chance beyond a random same-rank null and beyond surface baselines — the effect readout is NECESSARILY dependent on the bias subspace."* It does **NOT** license a directional/one-way claim, "CAS Harness detects/prevents/removes prompt injection internally," or "CJT/PCBA proves causal control" (all NOT LICENSED).

**Two pieces of code stand between this and a run:** (a) a **fixed-probe (no-retrain) cross-ablation variant** (~30 LOC over existing helpers — the stock runner *retrains*, answering "is the subspace recoverable?" not "does removing bias destroy effect?"), and (b) a **multi-label `.npz` loader** (the stock runner carries one fused `operator|domain` label; CJT needs separate cause/bias/effect labelings).

---

## 4. Reuse map — the highest-leverage, lowest-risk win

Adopt the dependency-light `cas-forex` CJT core as the Harness's **spec/grammar layer** (it has 59 passing tests and is pure pydantic+stdlib once lifted out of its `cas_forex.*` couplings):

| Module | What it gives the Harness |
|---|---|
| `cas-forex/cas_forex/cjt_syntax.py` | The `CJT< cause \| bias => effect >` grammar + parse/roundtrip — write CJT hypotheses in a *checked* language |
| `cas-forex/cas_forex/schemas/cjt.py` | `CjtObservation`/`CjtCircuitDiagnostic` typed targets + **`CjtClaimCeiling` (no ACCEPT value)** + model-validators that **raise** if `can_unlock_live_trading`/`can_create_broker_accept` is set — honest-NULL discipline enforced by the type system |
| `cas-forex/cas_forex/cjt_analysis.py` | `classify_region` (executable CUTOFF/ACTIVE/SATURATION/BREAKDOWN) + `large_signal_beta` (logged-only; `CjtAnalysis.validated` hard-coded **False**) |
| `cas-forex/cas_forex/cjt_differential.py` | Fisher-Rao geodesic `d(p,q)=2·arccos(Σ√(pₖqₖ))` (CLAUDE.md Correction 4) |
| `cas-forex/cas_forex/ccb_designs.py` + `crc_linter.py` | The fixed CSB (=CCB-1) battery + a static design-rule pre-filter for the fixture track |

The harness's **own** ablation/bridge primitives are the execution layer: `run_stage9_40e_subspace_ablation.py` (`_coef_subspace_basis`, `_project_ablate_with_scaler`, `_random_orthonormal_basis`, `_group_split`, guard), `discover_stage9_40e_neuron_covers.py` (matched random/wrong-class controls), `merge_stage9_40e_evidence_packet.py` (FLAG-ceilinged packet), and the pipeline scripts `screen_cjt_bias_vibration_surface_leakage.py` / `build_cjt_bias_vibration_bank.py` / `evaluate_cjt_bias_vibration_diagnostic.py` / `capture_enabled_predicate_w0_all_layers.py` (currently on branch `codex/cas-harness-public-beta-candidate` — **branch reconciliation is a prerequisite**).

> Note: `cas-forex` CJT is a **symbolic circuit layer over forex/CAS**, not a hidden-state probe — its β/region values are design constructs, not model measurements. It is the attach point for the **grammar/diagnostic/Evidence-Packet-explanation** track, **NOT** the causal-ablation track. Don't conflate the two.

---

## 5. The three honest limits (all confirmed in-record)

1. **Open-weight only.** Every hidden-state test needs `.npz` residual-stream capture (`features[N,L,H]`). Nothing transfers to closed-API models (Claude/GPT/Gemini) — there, only the text-surface shadow screen applies. (Spec sheet §9.1; pre-reg §8.)
2. **Each binding is a per-model hypothesis that can return FALSIFY — and one already did.** The CJT-shaped W0 bias/vibration test on **Qwen2.5-1.5B-Instruct (2026-06-18)** returned **FAIL / `BLOCKED_SURFACE_LEAKAGE`**: best hidden layer BA up to 1.0, but **char baseline 0.9583 ≥ hidden at every one of 28 layers, hidden-minus-char only +0.042, 0/28 layers passed.** The expanded injection gate also FAILED (hidden 0.745 < 0.75 required; margin 0.094 < 0.15 required). This is the model citizen — the discipline that lets the harness return FALSIFY is exactly what makes the bindings worth adopting *and* what blocks them today. **Substrate trap:** Pythia-160M has a trained probe (91.6%) but is **non-injectable** (0% compliance); Qwen2.5-1.5B is injectable (~45%) but has **no typed probe yet** (Gate A ≥85% held-out unmet).
3. **β-metrology is unsolved — and the book agrees.** Every β/sat/cutoff value in the CAS PCBA book is "a number you choose… not a measurement pulled from a running model" (Bench Notes); `cjt_differential` consumes simplex vectors and `CjtAnalysis.validated` is hard-coded **False**; `classify_region` consumes scalar `[0,1]` activations, not probe accuracies. **Ship the binary cutoff (null-beating margin); never ship β as a measured gain.**

**Two confounds the verifiers added that even a clean PASS would not escape** (these are the panel's sharpest contribution beyond the original conversation):
- **Subsumption (RPM):** W→P-collapse / P→W-survival is *also* produced by geometric nesting (if P ⊂ span(W)) — not prerequisite order. Requires a decodability-matched non-prerequisite control.
- **Probe-strength (RPM):** asymmetry could merely reflect W being more decodable than P. Requires rank/accuracy-matched probes.
- **Axis substitution (η₁/η₂):** the existing PASS is on the prompt-stage RISK-vs-CONTROL axis (W0, zero generated tokens); the claimed hijack-vs-refusal axis is post-generation and needs η₂ emitted-text capture that does not exist.

---

## 6. Build roadmap (ordered; each step gated)

**Now — no GPU, no overclaim risk:**
1. Lift the dependency-light `cas-forex` CJT core into the Harness as the **spec/grammar layer + no-ACCEPT `CjtClaimCeiling` type**.
2. Ship the **bounded shadow `cjt_pcba_diagnostics` sidecar** on the existing instruction-integrity "gluing" payload — `{cause_ref, bias_ref, effect_ref, region, board, test_point, claim_ceiling}`, `verdict_effect: none_shadow_only`, positives → `FLAG_FOR_HUMAN_REVIEW`. **Explanation layer only; no internal-detection claim.** (This is the only LICENSED-now deliverable.)
3. **Branch-reconcile** the four pipeline scripts onto the working branch.

**Next — the empirical bridge (in this exact order; each is a hard gate):**
4. Author a **surface-balanced v1 bank** and **PASS `screen_cjt_bias_vibration_surface_leakage.py` at ≤0.60 BEFORE any GPU capture.**
5. Train the **Qwen2.5-1.5B typed probe to Gate A ≥85%** held-out (Pythia is non-injectable; this is unavoidable).
6. **Actually clear hidden-minus-char ≥ 0.15 on a surface-clean *hidden* capture** — never achieved yet; this is the wall the prior attempt hit.
7. Build the **~30 LOC fixed-probe (no-retrain) cross-ablation executor** + multi-label loader.
8. Run the **`cjt-as-ablation` cutoff necessity test** (binding #1). PASS → FLAG_FOR_HUMAN_REVIEW; FALSIFY is a live outcome.

**Later — only after #1 passes:**
9. `rpm-diode-asymmetric-gate` (#2) **with** the subsumption + probe-strength controls.
10. `cascade-search-order` (#3), `ccb-csb` fixture battery (#4), then `eta1-eta2` (#5) once η₂ emitted-text capture exists.
11. **β-metrology — deferred indefinitely** (fragile; not licensed).

---

## 7. How this strengthens the claim ladder *without* overclaiming

Adopting CJT/RPM does **not** soften any caveat — it **adds named, pre-registered, falsifiable circuits**, which is *more* honest-NULL surface, not less: more specific things that can return FALSIFY/GREY, each tied to a concrete proof chip. Concretely:

- The CJT cutoff result populates the existing **`causal_proof`** chip; the RPM directional result populates **`causal_proof` + `control_proof`** — they slot into the six-chip Evidence Packet rather than inventing a new verdict surface.
- The **`CjtClaimCeiling` no-ACCEPT enum** is a *type-system* enforcement of the discipline that the harness today enforces only by convention (`merge_stage9_40e_evidence_packet.py` hard-coding FLAG) — strictly an upgrade to the honest-NULL machinery.
- The mandatory surface-leakage pre-flight makes the **char/length-surface discipline permanent and non-bypassable**, matching the standing rule that a W0 detector was once withdrawn when a char n-gram (0.925) beat the hidden signal.

**Bottom line:** CAS PCBA gives CAS Harness a *better way to ask falsifiable causal questions* (named cause|bias=>effect circuits, a directional diode test, a terminating search order, a reusable CSB instrument) and a *checked grammar + no-ACCEPT type* to ask them in. It does **not** give the harness any validated new capability today — every binding is `NEEDS_EMPIRICAL_BRIDGE`, the nearest prior run is a surface-leakage **FAIL**, and the genuinely-shippable-now deliverable is the grammar layer plus a bounded shadow explainer. Build the grammar layer and the fixed-probe cutoff test first; let it return PASS or FALSIFY honestly; one validated CJT cutoff binding is worth more to the harness than the whole asserted component library.
