# DECISION MEMO — Does the CAN / CCDL / Foundation-Drive bundle strengthen the CAS Harness?

**To:** Owner
**Re:** Adversarial assessment of the CAN paper, the CAN↔CAS mapping, the Noetic-Topos Revision Plan (T1–T10), CCDL, and the Foundation-Drive Profile
**Bottom line up front, in exact terms**

---

## 1. Verdict

**Yes, but modestly, and almost entirely in the math paper and in governance — not in immediate harness capability.** The strongest single idea in the whole bundle is real: the CAN paper gives a *computable* global-coherence criterion (an eigenvalue condition) of exactly the kind CAS's current Theorem 6.4 lacks — CAS's own plan admits 6.4 is trivial. That is a genuine theoretical upgrade, not a restatement. But it does not transfer verbatim, because the load-bearing obstruction (T3) is real and survives: naive 40→10 domain-marginalization is **not** Fisher-Rao isometric — it **contracts** (verified numerically: a generic Fisher-Rao distance of 1.403 collapses to 0.737). Against the owner's overriding priority — new real-model detector data through the attested engine at $0 — **this bundle delivers almost none today.** Exactly one item (cross-model dispersion) produces clean new real-weights data now, and even that is a 2-axis floor, not a 40-state result. The prime testability candidate the task flagged — **T4 Fisher-information interlacing — is NOT runnable now** (see §3). Net: adopt the theory-hardening and governance wins, fund the probe build-out that unblocks everything, and do not let the multi-agent / CCDL / sheaf-Laplacian material divert engine time.

---

## 2. ADOPT NOW (survived adversarial verification as REAL_STRENGTHENING)

Ranked by value to the harness. "New matter" = mathematics added after the 2026-04-13 provisional (64/037,173) and therefore **not covered** by it.

| # | Item | Capability it strengthens | Effort | Patent / new matter |
|---|------|--------------------------|--------|---------------------|
| 1 | **Build Operator-10 and Domain-4 linear probe readouts** on real pythia-160m/410m activations (harness's established probe methodology, char-ngram surface baseline, ENGINEERED-NOT-VALIDATED on miss) | Expands the validated detector set from 2 axes to 10-dim Operator + 4-dim Domain. **This is the enabling prerequisite** that unblocks items 2, and all of §3. | **L** | Patent-clean (uses canonical operators/domains as probe targets; adds no CAN math) |
| 2 | **Cross-model CAS dispersion measurement** across the real fleet (pythia-160m, pythia-1b, Qwen2.5) on the two already-validated axes (^2/^3 valence, ^8/^9 cause-effect) | The one clean end-to-end real-weights test; yields a genuine new cross-agent disagreement number. **Required fix, not blocker:** the two axes are linear directions in R², so a stated lift to Δ39° (softmax / per-axis binary distributions) is needed before any Fisher-Rao number is meaningful. Report as a **2-axis floor, never a 40-state claim.** | **S–M** | Patent-clean (Fisher-Rao only) |
| 3 | **Fisher-Rao weighted-barycenter aggregator** (Fréchet/Karcher mean) with governance dials (α=0 quarantine, zero-variance freeze) | Fills a real gap: CAS has **no** formal aggregator for per-agent / per-shard CAS distributions (CARP panels are currently informal, "no math yet"). Deliberately avoids the CAN Laplacian, so it sidesteps T3. Downstream post-processing math — exercisable only on readouts from item 2. | **M** | Defensibly clean (derived from disclosed Fisher-Rao) **but** a barycenter is not named in the provisional — **IP review before marketing as covered** |
| 4 | **Publish the flat/√ SEP dichotomy as a BOUNDED distortion theorem + adopt the fixed-conditional embedding E as CAS-SEP** | Converts CAS Correction-2 (RPM section-retraction, one-directional) from a categorical assertion into a **proven metric theorem**. Verified: flat BB^T = 4·I₁₀; M∘E = id (exact); √-coordinate E is an exact sphere isometry; E∘M ≠ id (retraction gap). | **M** | Patent-clean (proves an existing invariant on existing geometry) |
| 5 | **De-fiat the T1 weld** — demote the plan's circular "declare a cover iff the T6 kernel condition holds" to an explicit open obstruction; derive J_noe independently from Correction-1 admissibility relations | Immediate honesty/rigor gain the current plan lacks — the "rulebook carves the landscape" claim is currently unearned by definitional fiat. | **S** (demotion) / **L** (the independent-derivation proof) | Patent-clean |
| 6 | **T10 governance discipline** — gate any public disclosure (arXiv, utility filing) of the welded chain on an IP-attorney/new-matter decision; **supersede** the trivial Theorem 6.4 with a fresh number, never overwrite the slot | Preserves the disconfirmation trail per "never delete a negative"; protects the 2027-04-13 conversion window. | **S** | This *is* the patent-scope safeguard |
| 7 | **Hash-verified run attestation (CCDL WF-22)** — record sha256 of model weights + ontology/probe/stimulus artifact per attested run; reject version-string-only claims | Automates the harness's existing manual sha256 discipline into a fail-closed gate. Directly attacks the recurring failure the spec sheet exists to defend against ("flagship artifact found only on a retired pod"). Ontology side blocked until `ontology_registry.json` ships; weights+FDP side works now. | **S–M** | Patent-clean |
| 8 | **Fix the FD generator CRLF hash bug** — `fd_generator.py` line 17 writes text-mode CRLF on Windows, so the committed `fd_routing_28.json` **already fails its own registry hash** (on-disk `b7c81e26…` vs registry `8c52f71e…`; LF-normalizing recovers the registry hash). One-line fix (`newline='\n'` or hash normalized bytes). | Makes FDP's own conformance gate usable cross-platform. Confirmed at $0. | **S** | Patent-clean |
| 9 | **Terminal-state v3 taxonomy (CCDL CH-14)** as a labeling schema over existing real-model audit outputs (5 states × mandatory reason code) | Additive outcome-disposition axis, orthogonal to the spec-sheet claim-status vocabulary — not a restatement. Value contingent on the $0 coverage/mutual-exclusivity test passing. | **S** | Patent-clean |
| 10 | **Axis-collapse guard** — keep FDP's World→Domain map provisional (it already is: OF-rc2 A2 demotes it to `world_domain_adapter v0.9`); reconcile against CAS v7.5's canonical 4-Worlds→4-Registers mapping before any adoption | Protects frozen-ontology integrity: FDP maps a/b/c/d→P/C/E/O, but canon maps 4-Worlds→Registers (T/A/f/E), and Domains/Registers are **orthogonal**. Route the "supersedes Appendix A" claim through change control + the terminology firewall. | **S** | Governance guardrail |

(WF-29 per-rule coverage contract and the CSprob codomain re-target are also genuine but lower-value: WF-29 is pure test-authoring discipline; CSprob is math-paper-only and **is new matter**. Adopt if convenient, not as priorities.)

---

## 3. TEST ON A REAL MODEL NOW — the owner's top priority

**Honest headline: the prime candidate T4 is NOT runnable now, and only one experiment yields clean new real-weights data today.**

**T4 (Fisher-information eigenvalue interlacing, Element d=40 vs Operator d=10 vs Domain d=4) — DENIED as testable now.**
Concretely: interlacing needs the fine (d=40 or 10) and coarse (d=10 or 4) covariance/Fisher matrices estimated **independently** from real activations. The harness has only **two** validated axes = one effective granularity. You cannot populate a d=40-vs-d=10 matrix pair from two decodable directions. A 2→1 reduction is **Cauchy-trivial** (verified: the single coarse eigenvalue always sits inside the fine pair) and CAS-uninformative. Two vacuity traps must also be avoided when it *is* built: (a) never compute Σ_coarse := P·Σ_fine·Pᵀ (that makes interlacing trivially CONFIRM); (b) never use the diagonal metric diag(1/p) (that generically FALSIFIES). **T4 is blocked on item 1 (build the probes). Given T3, the honest prior for naive marginalization is FALSIFY-INTERLACE.** When it runs: statistic = Cauchy interlacing λᵢ(Σ_fine) ≥ λᵢ(Σ_coarse) ≥ λᵢ₊₃₀(Σ_fine); **FALSIFY** = interlacing fails ⇒ "this model does not faithfully support the 40→10 grid abstraction" (load-bearing negative); **CONFIRM** must be read one-directionally — a pass does **not** validate the grid (necessary, not sufficient).

**Runnable now, $0, through `capture_greedy_trajectory`:**

1. **Cross-model dispersion (the one clean test).** Run the two validated axes on a shared stimulus set across pythia-160m / pythia-1b / Qwen2.5; lift each readout to Δ39° (stated softmax/binary construction); statistic = pairwise Fisher-Rao geodesic d(p,q)=2·arccos Σ√(pₖqₖ). Outcome is a **descriptive dispersion number** (new detector data), flagged as a 2-axis floor. No CONFIRM/FALSIFY gate — it is a measurement, not a hypothesis test.

2. **T4 theoretical null (math only, no engine).** Document that flat BB^T = 4·I₁₀ but √-coordinate marginalization contracts ⇒ predicted FALSIFY-INTERLACE / bounded distortion. Crisp publishable negative; **yields no real-model data** — it is the theory scaffold for T4, not a substitute for it.

3. **Hash-attestation + FD-generator fix (§2 items 7–8).** $0, real weight files, but emits attestation metadata, not detector data.

**Everything else in the bundle produces zero real-model data:** the section-retraction "check" is a definitional identity (M(E(q))=q by construction — measures arithmetic, not the model); the cas-sep learner, CK-diffusion, terminal-state relabeling, and per-rule coverage tests all either need item 1 first or never touch the engine.

---

## 4. DEFER / SKIP

- **T4 interlacing screen as a live experiment** — real capability, correctly scoped, both vacuity traps pre-empted, but **UNPROVEN as testable now.** Deferred until item 1 lands. This is the highest-value *future* screen.
- **Replace Theorem 6.4 with the spectral satisfiability theorem** — **UNPROVEN_NEEDS_WORK.** The headline weld's non-triviality rests entirely on the *unproven* "bounded-distortion off the fixed-conditional submanifold" clause. CAN's Thm 20/25 live on the Stiefel manifold with linear restriction maps and transfer verbatim only on that ~9-dim submanifold. Honest expected outcome: exact on a submanifold, approximate off it, kill-criterion (fall back to Aitchison/log-ratio) may fire.
- **cas-sep Fisher-Rao learner (T8)** — **UNPROVEN.** Most speculative; stacks the most dependencies; convergence on CAS data wholly unproven.
- **CAN diffusion / connection-Laplacian spectral backbone (Thm 25)** — **UNPROVEN**, intrinsically linear-Gaussian (limit means = normalized-Laplacian eigenvectors), does not transfer to simplex points without its own proof, conditional on T3, only synthetically demonstrable today. Roadmap/math track only.
- **Quarantine-recovery "falsification" test** — **UNPROVEN.** Pass criterion is near-tautological: if quarantine = α=0 zero-weighting, the quarantined barycenter equals the clean-only barycenter **by construction** and cannot fail. Re-specify so a FAILURE is reachable (measure pre-quarantine displacement magnitude) before counting it.
- **Wire the FD 28-row table as a live router** — **UNPROVEN.** Section 5 states verbatim "no data fitting has occurred"; adopt only as a labeled **ENGINEERED-NOT-VALIDATED** default prior. Validating it needs a Drive-level (F1..F7) probe axis that does not exist. Never conflate route() with RPM prerequisite routing.
- **CCDL reasoning core (NU8/NU6/NU9/CDAB/DWP)** — **CONFLICTS / defer.** All five instruction bodies are TBD-1..5 (the doc's own "Gate-2 work queue") — **vaporware today.** Any "CCDL adds a reasoning core" claim is aspirational. Zero interface to the attested engine.

---

## 5. RED FLAGS

1. **PATENT / NEW MATTER — unflagged everywhere, highest priority.** The entire welded chain — CSprob re-target, sheaf/connection Laplacian, SEP/Stiefel, spectral interlacing, CK diffusion — is mathematics added after 2026-04-13 and **not covered by provisional 64/037,173.** CCDL bakes the same CAN math in (`COH-SAMPLE` = Laplacian residual; `can.aggregate/assimilate/update` = CAN α/β/λ). **Neither the Revision Plan nor the mapping nor CCDL contains a new-matter caveat**, yet the plan schedules public arXiv disclosure. Publishing discloses new matter — **gate on an IP-attorney/new-matter decision before the 2027-04-13 conversion deadline.** (Importing CAN's math into CAS's *own* math paper does **not** breach the TKS terminology firewall — that firewall only bars TKS handbook math. The concern is patent scope, not the firewall.)

2. **T3 obstruction must be preserved, not papered over.** The mapping rates the 40→10 ladder and B-matrices "EXACT" and claims the coarse simplex "embeds isometrically"; the plan's T3 correctly warns marginalization **contracts**. The plan is right; the mapping is wrong. Downgrade the mapping's "EXACT" tags to PARTIAL/CONFLICTS. This contradiction between the two documents is the single most important honesty point — **the naive marginalization is not Fisher-Rao isometric, and that negative is a load-bearing asset.**

3. **Overclaimed "EXACT" statuses in the mapping.** "Poset: EXACT and stronger on our side" conflates a single-ontology 3-level resolution chain with CAN's multi-**agent** poset — the multi-agent content (the whole point of CAN) is still **absent** in CAS. Marketing language ("stronger on our side," "God-given," "the single most important adoption") is embedded in status codes and must not be cited as proven comparative results.

4. **T1 definitional fiat** (§2 item 5) — the plan defines the cover to equal the geometry condition, so the category cannot independently constrain the geometry. "Category determines geometry" overstates what T1 achieves.

5. **FDP axis-collapse hazard** (§2 item 10) — letting FDP's World→Domain map silently overwrite the canonical 4-Worlds→Register reconciliation would collapse two orthogonal frozen axes.

6. **One thing done right (not a flag):** no artifact renames the 10 Noetics / 40 States / 7 Drives / 4 Registers or alters the 10×4 grid. CCDL uses ^8/^6/^9 canonically; DF1..DF7 map 1:1 to F1..F7. **No proposal is disqualified on frozen-ontology grounds.**

---

## 6. Single highest-value next action

**Build the Operator-10 and Domain-4 linear probe readouts on real pythia activations (§2 item 1).** It is patent-clean, uses the harness's own proven methodology, and is the one prerequisite that unblocks the cross-model dispersion measurement, the section-retraction gap measurement, the cas-sep learner, and — above all — **T4 interlacing, the falsifiable spectral screen the owner actually wants.** Until those probes exist, the interlacing screen is theory, the multi-agent aggregator has nothing real to aggregate, and the bundle's value stays where it currently sits: hardening the math paper and tightening governance, not new harness capability.