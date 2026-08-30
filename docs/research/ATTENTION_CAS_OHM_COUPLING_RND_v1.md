# R&D Report: the Attention × CAS-Simplex × CAS-Ohm Coupling Architecture

## Designation: STATIC COUPLING BASELINE v1 (owner decision, 2026-08-30)

Status: **R&D ANALYSIS — documentation only.** No model, no GPU, no neural run, no claim
promotion. The architecture under review keeps its own declared status: PROPOSED, not
established. This report exists so the owner can decide what to build.

> **Scope note (append-only, 2026-08-30).** The owner designated this report the
> **Static Coupling Baseline v1**. Its architectural scope — Bias treated as static — is
> superseded by `RECURSIVE_CJT_BIAS_CONTROLLER_v0_1.md` (RPM-gated, ASOM-regulated,
> CAS-Ohm-routed recursive Bias). Nothing in this report is erased: it remains the clean
> static control the recursive design must beat. Four owner calibrations on this
> report's conclusions are recorded and accepted:
> 1. The `I_total := 1` verdict (§5.2) governs the fixed dense-forward-pass experiment
>    ONLY. It is not a permanent ban: in an adaptive architecture, compute genuinely
>    varies (active experts, RPM branches, reasoning ticks, retrievals, tool calls), and
>    total flow gets a measured referent (`B_t`) — see the recursive spec, Ch. 7.
> 2. The construction-gold restriction on `p_i` (§5.1) binds the FIRST claim-bearing
>    experiment, not all future ones. A later activation-decoded `p_i` is admissible
>    only after beating surface, matched-semantic, shuffled, and random controls.
> 3. The 28-cell Worlds↔Registers unification (§4) is held as a declared, frozen,
>    VERSIONED translation key — not asserted as ontological identity. The genuine
>    naming hazard (Drives×Domains vs Drives×Registers) stands as found.
> 4. The 15-agent process (§10) is internal review, not external scientific
>    verification. Model agreement changes audit priority only; it creates no authority.

How this was produced: a 15-agent workflow (run `wf_c7e419cf-c50`, 2026-08-30) — two
independent math verifiers (one instructed to refute), three literature lanes with live
web search, two source-consistency auditors (canon + settled experimental record), one
adversarial critic, one experiment designer, plus six independent verification agents who
re-checked every novelty verdict and citation. **All six verification checks upheld.**
Every math claim was computed with numpy/scipy, not eyeballed. The owner-restricted
Codex folder was never opened.

---

## 1. Bottom line

**The mathematics is sound — no equation in the proposal is wrong.** The architecture's
two big structural instincts (typed simplex semantics; magnitude×composition cones and
factorized products instead of one flat simplex) are the field-standard-correct choices
with clear prior art. **The core coupling `q = αᵀP` is published prior art** (three
independent instances). What is genuinely new as far as an aggressive search found: the
three-factor joint flow matrix with a typed cognitive-state axis, the hull-reachability
test used as an explicit *control signal* that opens a prerequisite goal, and the
Fisher-Rao structural memory key. **Three imports are broken and must be repaired before
any build:** (1) `I_total = V/R` is not licensed by the project's own CAS-Ohm sources and
is *unfalsifiable* in a standard forward pass; (2) the claimed 28-cell "source conflict"
is not real — but a different, genuine naming hazard exists; (3) the E/F controls are
insufficient to license the phrase "CAS-specific" under the project's own frozen law.
The proposal is worth one cheap, pre-registerable experiment (~30–50 A10G GPU-hours,
tens of dollars); the protocol is in §8.

---

## 2. Mathematics — every equation verified ✅ (with load-bearing caveats)

Verified by two independent agents running numpy/scipy (scripts `verify_math.py`,
`refuter_checks.py`, `critic_checks.py` in the session scratchpad; identities hold to
≤1e-12):

| Claim | Verdict |
|---|---|
| `q = αᵀP` stays in the closed simplex Δ³⁹ | CORRECT (exact convex-combination closure) |
| Open-simplex membership (all `q_k > 0`) | CORRECT **iff every stored `p_i` is strictly positive** — openness is inherited from the profiles, not from α. Enforce `p_ik > 0` (ε-floor), per CLAUDE.md Correction 4. |
| Three marginals of `F_ik = I·α_i·p_ik` | CORRECT to machine precision |
| Convex-hull reachability (outside hull ⇒ unreachable by any α) | CORRECT — LP infeasibility certificate computed for a counter-target; inside-target recovered exactly |
| Controller `α* = argmin d_FR(αᵀP, q*)` | CORRECT_WITH_CAVEAT — equivalent to **maximizing the Bhattacharyya coefficient, which is concave in α** (0/5000 midpoint violations): a clean convex program. But `α*` is non-unique when profiles are affinely dependent (the optimal *mixture* is unique); and FR gradients blow up near simplex vertices — metric norm `2.39e7` at ε=1e-6 vs `1.02e3` at uniform. Near-one-hot construction-gold profiles live exactly there; the smoothing ε is an undeclared free parameter that must be frozen. |
| Cone `d = m_D·π_D` | CORRECT for `d ≥ 0`, unique for `d ≠ 0`, degenerate at 0. Requires nonnegative drive activations. |
| `P(F,W) = P(F)P(W|F)` | CORRECT — but it is a lossless reparameterization (27 = 28−1 free parameters), not an independence assumption; it constrains nothing. |
| `p_E = p_C·K_B` | CORRECT (row-stochastic closure); open-simplex needs strictly positive `K_B`. |
| `10·4·7·4 = 1120`; factorized ≈ 49 vs flat 1119 free parameters | CORRECT — a ~23× parameter reduction; matches `cas_reasoner.txt` line 8873's own 1,120 count. |
| `Δ³` notation for 4 registers / 4 ASOM regions | CORRECT under the Δⁿ⁻¹ convention. |

**Two mathematical deflations that matter:**

- **`F` is bookkeeping, not measurement.** The refuter constructed joint matrices with
  the same marginals as `F` but different interiors: the rank-1 factorization
  `F = I·α·p` is a conditional-independence *assumption* ("what is read FROM Idea i
  equals Idea i's static profile"), and `F` carries zero information beyond
  `(I, α, P)`. `F` becomes contentful only if an independent joint-flow measurement is
  specified. Until then it is a display format.
- **The reachability trigger is near-vacuous for generic targets.** The hull of n
  profiles has dimension ≤ n−1; for n ≤ 39 Ideas it is a measure-zero face of Δ³⁹, and
  in LP experiments **0/200 random targets were in-hull at every n tried (5…120)**. The
  test is meaningful only when targets are generated from within (or near) the span of
  available profiles, or when "reachable" is defined as within-ε projection distance —
  the argmin-projection form, not exact attainment, is the usable controller.

---

## 3. Novelty — what already exists, what is actually new

All citations below were independently re-verified by separate agents (6/6 upheld).

**Prior art exists (do not claim as new):**
- `q = αᵀP` — attention-weighted aggregation of per-item probability/concept vectors:
  Ilse, Tomczak & Welling, *Attention-based Deep MIL*, ICML 2018; See, Liu & Manning
  pointer-generator, ACL 2017; Concept Transformer, ICLR 2022. Concept-vector-per-item
  is Concept Bottleneck Models (Koh et al., ICML 2020; probabilistic variant Kim et al.,
  ICML 2023).
- The hull *fact* (attention outputs confined to the convex hull of values): Richter &
  Wattenhofer, arXiv:2005.09561 (2020); Frank-Wolfe attention analysis, arXiv:2508.09628.
- Flow-conserving attention attribution: Abnar & Zuidema, *Quantifying Attention Flow*,
  ACL 2020, and successors. Two-factor amount×content: Kobayashi et al., EMNLP 2020.
- Simplex-semantics typing: this is compositional data analysis doctrine — the R
  `compositions` package's mandatory scale classes (acomp/rcomp/aplus/rplus/ccomp) are
  exactly "same vector, declared type, different licensed operations."
- Magnitude×simplex cone for Drives: the CoDA "total + composition" standard
  (Pawlowsky-Glahn, Egozcue & Lovell, *Tools for compositional data with a total*, 2015).
- Selective plasticity: EWC (2017), Synaptic Intelligence (2017), PackNet (2018),
  Supermasks-in-Superposition (2020). CAS-conditioning is a variant, not a mechanism.
- Concept-coverage curriculum: Skill-It! (NeurIPS 2023 Spotlight).
- Bias-conditioned state-transition kernels: dialogue-act HMMs (Stolcke et al., 2000).
- Deficit-simplex bottleneck attribution: Liebig's law / Leontief min-form — and CAS
  v7.6's own `Y_T = min_i(x_i/a_i)` is already this.
- Factorized product over flat joint: DBNs (1989), factored MDPs, mean-field practice.

**Partly novel (ingredient prior art, combination not found):**
- The rank-1 three-factor `F = I·α·p` with a **typed cognitive-state form axis** and
  marginal consistency.
- Hull reachability used as an explicit **stop-adjusting-attention → open a
  missing-prerequisite goal** control signal wired to RPM (adjacent: control theory of
  prompting, arXiv:2310.04444; steering non-identifiability, arXiv:2602.06801).
- Dual-key retrieval with a **Fisher-Rao structural profile** as the second key (hybrid
  retrieval is standard; the FR-simplex structural key was not found anywhere).
- The 5-way pragmatic typing labels as a per-record schema field (CoDA has the
  discipline; nobody was found applying it to cognitive-state records).

**Honest summary:** the proposal is a competent *synthesis* wearing CAS types — its math
is elementary and its ingredients are established. Its value, if any, is in the typed
coupling and the diagnostics, which is exactly what the experiment in §8 tests.

---

## 4. Source-consistency vs canon — one claimed conflict is NOT real 🟥, one real hazard found 🟨

- 🟥 **The proposal's claimed 28-cell source conflict is wrong.** It says TKS's
  "7 Foundations × 4 Worlds = 28" and the harness's "7 Drives × 4 Registers = 28" are
  two DIFFERENT spaces that must not share a name. The authoritative translation key
  (`docs/reference/tks_28_foundations_translation_key.md` line 5) says the opposite,
  verbatim: "The 28 TKS Foundations arise from the cross-product 7 Foundations × 4
  Worlds. In CAS v7.5, the same structural cross-product is expressed as 7 Drives
  (F1–F7) × 4 Registers (T, A, f, E)" — with a position-by-position World↔Register
  table. They are the SAME space under the frozen key (canon: a=Spiritual…d=Physical).
- 🟨 **But a genuine naming hazard exists that the proposal missed:** the corpus has a
  *third* 28-grid — **28 Domain-Specific Drives = 7 Drives × 4 DOMAINS (P/C/E/O)** —
  which is orthogonal to Registers ("the Register axis is orthogonal to the Domain
  axis; they do not collapse", translation key line 52). The conflation has already
  happened once: `docs/working/cas68_recipe_audit_20260610.md` line 6 writes
  "28 Foundations (7 Drives × 4 Domains)" — mislabeled. Naming discipline IS warranted,
  between Drives×Domains and Drives×Registers.
- ✅ Multiple-drives-simultaneously-active: supported (v7.6 State Vector = unnormalized
  activation quantities), so the cone-not-simplex argument stands.
- ✅ Register mixture-vs-fusion warning correctly tracks Clarification 10's `+`/`×`
  discipline (same-Noetic multi-register `×` invalid by default).
- ✅ Domain precedence `P ≻ C ≻ E ≻ O` and descent quoted correctly; a bare occupancy
  simplex indeed cannot carry the order.
- 🟨 **CMB embellishment:** the 40-cell CAS-addressed memory bank IS in
  `cas_reasoner.txt` (lines 471, 1138, 1650), but "**retrieved through Fisher-Rao
  structural similarity**" is NOT — `grep -i fisher` over all 11,834 lines returns zero
  matches. That half of the proposal's citation is an addition, not a quote.

---

## 5. Settled-record consistency — the three hard constraints 🔒

1. **Claim A is DEAD and stays dead.** Spec sheet §8.1 (owner-retired 2026-08-18): flat
   40-cell decoding from hidden states collapses to chance under leakage control
   (`6.5% vs 2.5%`); a rival taxonomy is ~13× more recoverable (`0.8472 vs 0.0653`);
   involution ranks 14/14. **Consequence:** the architecture is consistent with the
   record ONLY while `p_i` comes from construction-gold traces/labels (the Claim-B
   measurement plane). Any implementation that decodes `p_i` from activations revives
   Claim A and contradicts the record unless re-proven under §7.2-grade matched
   controls. The critic's "biggest unstated dependency" verdict: every claimed
   advantage inherits the truth of Claim B for arbitrary content, and the spec sheet's
   current answer on CAS-specificity is GREY.
2. **`I_total = V/R` may not be imported as a licensed quantity.** The project's own
   sources refuse it three ways: spec sheet Capability 22 "NOT LICENSED — proposed
   instrument, never run against a model"; "Every worked number in that module is
   fabricated for exposition, and the module has zero callers"; the CAS-Ohm paper
   itself — "The borrowed shape licenses nothing by itself", `ŷ = a/r_eff` admissible
   only after registered calibration. **And it is unfalsifiable in a standard
   Transformer:** constant compute per token, softmax rows normalized — the critic
   computed that `F/ΣF` is bit-identical for `I_total = 3.7` and `I_total = 999`.
   Every simplex-level quantity is invariant to `I_total`; the "low total flow" fault
   branch can never fire from data without an external, declared proxy. The experiment
   protocol therefore sets `I_total := 1` and defers CAS-Ohm entirely.
3. **E/F controls cannot license "CAS-specific."** By the project's own frozen law
   (`labels/LABEL_CLAIM_BOUNDARY.md` §6): CAS must beat the lexical control AND the
   **matched-semantic** control. Shuffled (E) and random-matched (F) are noise
   controls — a D win over them is consistent with "any veridical side-channel about
   the data-generating process helps." A matched-semantic arm (a generic non-CAS
   taxonomy built from the same traces, SCMPE-style) is REQUIRED before the phrase
   "CAS-specific" is licensed.

Also confirmed consistent: the fault table's fourth row mirrors the CAS-Ohm guide
verbatim ("A correct I reading with a wrong effect points toward bias, gain, saturation,
or breakdown rather than a simple resistance problem"); the typed-unit discipline
matches the paper's Rule 2.2/2.3; the proposal's self-declared PROPOSED status satisfies
the correction-record reversal rule.

---

## 6. The seven claimed advantages — status table

| # | Advantage | Status after R&D |
|---|---|---|
| 1 | Precise fault localization (4-way) | 🟨 Coherent taxonomy, BUT: branch 1 unfalsifiable without an `I_total` referent; branches 2–3 need trusted `p_i` (a probe error of ε=0.15 manufactures a phantom composition fault L1=0.126 *larger* than a real one at 0.048 — fault classes collapse); the verdict also flips under Idea re-segmentation. Operable today only under construction-gold traces. |
| 2 | Reachability / "focus harder is impossible" | 🟨 Mathematically true, near-vacuous for generic targets (measure-zero hull, 0/200 in-hull at all n tried); usable as ε-projection distance, and only with a defined Idea segmentation. Partly novel as a control signal. |
| 3 | Interpretable routing to boards | 🟧 Untested; missing cheaper baselines that could kill it (learned gating, Shazeer 2017; **hash routing matches learned routing**, Roller 2021); "organ set" today is deterministic symbolic boards with cognitive characterizations formally withdrawn (CORRECTION_RECORD_v1). |
| 4 | Dual-key structural memory retrieval | 🟨 Partly novel (the FR structural key specifically); no record support or refutation; UNTESTED. |
| 5 | Curriculum balancing by CAS coverage | 🟨 Prior art mechanism (Skill-It!); CAS-grid variant untested. |
| 6 | Selective plasticity | 🟧 Prior-art mechanism (EWC/SI/PackNet/SupSup); structural threat: superposition (Elhage 2022) — disjoint dampable region↔parameter groups may not exist. Correctly self-labeled hypothesis; maps to Claim D of the standing preregistration. |
| 7 | Probabilistic CJTs `p_E = p_C·K_B` | 🟨 Sound Markov machinery, prior art (dialogue-act HMMs); keeps the guide's K/I/β/verifier separations correctly; identifiability of `K_B` from behavior untested. |

---

## 7. Surviving defects the proposal must repair

1. **"Idea" is operationally undefined** for real inputs — and the architecture is not
   segmentation-invariant: an information-preserving merge of two Ideas flipped a
   reachable target (d_FR = 0.0) to unreachable (d_FR = 0.7537), flipping the fault
   verdict from "routing" to "missing prerequisite" with no change in content.
2. **A single α does not exist in a Transformer** — L·H·T attention simplexes do; the
   proposal needs five defined operators (segmentation, head-agg, layer-agg,
   token→Idea pooling, normalization), and bare attention weights are known-misleading
   (Kobayashi EMNLP 2020: influence ≈ α·‖v‖; Jain & Wallace NAACL 2019).
3. **`p_i` at inference on real inputs** = the GREY frontier (see §5.1). Circularity
   risk: measuring and steering with the same unvalidated instrument.
4. **`I_total`** — see §5.2. Either declare a measurable external proxy (e.g., retrieval
   budget, tool-call budget, token budget) or drop the coordinate.
5. **Missing controls** — matched-capacity (G: constant uniform profiles through the
   identical architecture) and matched-semantic (generic taxonomy). Both added in §8.
6. **FR-vertex blowup** for near-one-hot profiles — freeze the ε-floor in advance.
7. **Two competing A–F tables** now exist for "the first experiment" (this proposal's
   vs `CAS_TRACE_GOLD_SPEC_v1.md` §7's). The owner must declare which governs and
   retire the other by name.

---

## 8. The runnable experiment (PROPOSED_UNTESTED — needs owner-signed phase-0)

Full protocol drafted by the experiment lane, conforming to the standing law
(construction-gold labels via `CAS_TRACE_GOLD_SPEC_v1.md`, owner-gated promotion,
GPU-first on AWS, deterministic claim promotion, ≥10 seeds, group bootstrap):

- **Task**: passages of 3–6 clause-level Ideas, each realized from a formal CAS trace
  (one op from ^2/^3/^6/^8), query targets one clause; answer deterministically
  computable from the trace. Shared vocabulary across classes, ≥8 template families per
  op, surface-matched minimal pairs; ~10,000 candidates → ~6,000–8,000 promoted items
  after ABSTAIN/round-trip attrition; splits grouped by template family with three
  protected splits read once.
- **Conditions** on frozen `Qwen2.5-0.5B-Instruct` (heads only train, parameter counts
  matched within 1%): A plain readout; B +attention pooler (α); C +profiles (uniform
  α); **D coupled** (the SAME α mixes content AND computes `q = αᵀP`, `F` features +
  FiLM gating, `I_total := 1`); E shuffled-CAS; F random-matched; **G matched-capacity
  (new)** — constant uniform profiles through D's exact architecture; **plus the
  required matched-semantic arm** (generic non-CAS taxonomy from the same traces)
  before any "CAS-specific" language.
- **Primary metric**: examples-to-threshold (θ=0.90 proposed) over a 6-point dataset
  ladder. **Hard gates**: G1 learnability; G2 D>B and D>C; G3 D>E and D>F **plus the
  matched-semantic win** (only this licenses "CAS-specific"); G4 D>G (else the win was
  capacity — REFUTED); G5 ≥50% of the advantage retained on protected splits.
  **Kill criteria** pre-registered; one protected read; no reruns; a killed study is
  reported killed.
- **Ablation signatures (the double dissociation)**: α-ablation must raise clause-
  SELECTION error without raising operation error; profile-ablation must raise
  OPERATION error without raising selection error. Same undifferentiated error under
  both = the fault-localization advantage is REFUTED.
- **Cost**: activation extraction <0.5 A10G-hour; ~420 head-training runs over cached
  activations; **30–50 A10G-hours total — tens of dollars**, one instance,
  auto-terminate, receipts.

---

## 9. Owner decisions required before anything is built

1. Which A–F condition table governs the first experiment (this proposal's + G +
   matched-semantic arm, or `CAS_TRACE_GOLD_SPEC_v1.md` §7's) — retire the other by name.
2. Accept or reject the `I_total := 1` deferral of CAS-Ohm (recommended: accept; the
   coordinate is currently unfalsifiable and unlicensed).
3. Approve the naming fix: the real hazard is Drives×DOMAINS vs Drives×REGISTERS, not
   the proposal's Worlds-vs-Registers pair (which the translation key already unifies).
4. Freeze the ε-floor for open-simplex profiles and the reachability tolerance.
5. The usual: sign the phase-0 record, pin the promotion key, approve rules — all
   already listed in the Phase 0C return.

## 10. Provenance

Workflow `wf_c7e419cf-c50`: 15 agents, 0 errors, ~1.40M subagent tokens, 155 tool
uses. Verification round: 6/6 novelty-and-citation checks independently upheld. Numeric
scripts: `verify_math.py`, `refuter_checks.py`, `critic_checks.py` (numpy 2.3.5, scipy
1.17.1), all CPU-deterministic. Sources read: `CLAUDE.md`,
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, `docs/reference/tks_28_foundations_translation_key.md`,
`docs/CAS_HARNESS_SPEC_SHEET.md` (§§7–8), `CORRECTION_RECORD_v1.md`, both CAS-Ohm PDFs
(in full), `cas_reasoner.txt` (grep + targeted reads), the Phase 0C label-authority
lane. The owner-restricted Codex folder was not opened by any agent.
