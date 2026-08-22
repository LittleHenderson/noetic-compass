# CAPABILITY ROADMAP — CAS & the CAS Harness (from the CAN / Noetic-Topos corpus)

## 1. What this corpus unlocks

The CAN sheaf paper and its CAS mapping hand us two things the harness did not have before: (a) a **completion path for the 40/10/4 granularity ladder** — the Domain-4 rung is already validated on real pythia-160m weights, and the corpus's Fisher-information interlacing plan (T4) tells us exactly why the Operator-10 and Element-40 rungs are the next builds; and (b) a **computable coherence number** — CAN's connection Laplacian `L=BB^T` (kernel dimension = how many independent global sections exist) gives CAS the global-coherence quantity the NCCS composite never had, and CAN's "counterfactual global section" (infer the beliefs that make observed behavior optimal) is term-for-term the noeticcompass.com assessment problem, which means we can assess **closed API models from outputs alone**. The honest obstruction is preserved throughout: naive 40→10 marginalization contracts under Fisher-Rao (the T3 negative), so every coherence/interlacing capability must use an isometric SEP map that *beats* that recorded contraction rather than ignore it. All the Laplacian/SEP/interlacing math post-dates the 2026-04-13 provisional (64/037,173) and is flagged new-matter.

---

## 2. BUILD NOW — $0, real model data, through the attested engine (OWNER PRIORITY)

Ranked by value × feasibility. All run on local CPU, all produce new real-model data, none introduce new math.

**1. Operator-10 Rung — the d=10 Noetic detector (effort M).** *Lead item.* Completes the middle rung of the ladder. Highest leverage because the 40E capture npz **already stores `labels_operator` (0..9)** next to `labels_domain` — the d=10 rung is an unused label column, not a new capture campaign. Build: clone the d=40 subspace-ablation readout contract into a 10-class LogisticRegression keyed on `labels_operator`, chance = 0.10, evaluate per layer with `GroupShuffleSplit` grouped on topic (held-out-topic), gate on a ≥1000-run label-shuffle null AND a char-ngram surface baseline. **Yields:** a layers×F1 curve, the emergence layer, and a ^0..^9 confusion matrix — VALIDATED rung or an honest per-operator NULL (self-duals ^0/^1/^4/^7 may under-separate; report per-operator, not a blanket pass).

**2. CAS Cognition Tomography (depth-resolved CAS-MRI) (effort S).** Cheapest new capability. Re-run the three *already-frozen* detectors (^2/^3 valence, ^8/^9 cause-effect, P/C/E/O Domain) at **every** layer of the residual stream instead of the single validated layer, with a per-cell shuffle null. **Yields:** the first layers×3-axes heatmap showing where each CAS axis emerges, peaks, and decays in a real model. Regression guard built in: the Domain axis must reproduce the recorded layer-2 peak or the run halts.

**3. Framing-Cue-Controlled Axis Hardening (effort M).** The cheapest way to learn which of the three "perfect" results are structural and which ride on giveaway words — the exact failure that already forced a W0 detector withdrawal. Author matched minimal-pair + paraphrase stimuli, freeze each validated detector, score on the controlled set without refitting, and certify HARDENED only if controlled F1 stays above the char-ngram surface baseline (computed on the *same* controlled set). **Yields:** a three-row certified/flagged table that makes every downstream claim defensible. A collapse on a flagship axis is a load-bearing negative to record, not bury.

**4. Domain/Operator Causal Ablation — correlational → causal (effort M).** Upgrades "the model represents the structure" to "the structure is load-bearing." Project the identified subspace out of the residual stream *during generation* and measure the shift in `pre_selection_logits` against a **norm-matched random-direction control**, with **restoration** (re-adding the direction) as the receipt. **Yields:** target-vs-control divergence, a per-prompt permutation p-value, and a restoration-recovery fraction — CONFIRMED-CAUSAL or an honest NOT-DISTINGUISHED-FROM-CONTROL (plausible on a 160m model).

**5. CAS Version-Drift Regression Report / Coherent-Subspace Drift Alarm (effort M).** A cognitive diff between two checkpoints of the *same* base (base vs fine-tune). Per validated axis: canonical subspace angle + Fisher-Rao displacement, gated by a base-vs-base seed-noise null, rendered red/amber/green. **Yields:** a per-axis drift card; the positive control (deliberately steer the valence axis via the drive-local eraser and watch that card flip red while others stay green) *is* the validation. Uses only validated axes — no new math.

**6. Live Cognitive-Coherence Meter (effort M).** Streams the three validated detectors per token off the live-trace worker (which now emits real traces) and reports a Fisher-Rao dispersion of consecutive states. **Yields:** continuous per-token real-model data on every generation — the demo-able "I get it" surface. Uses the existing metric only.

---

## 3. BUILD NEXT — engineering, no new math

Ranked. These make the BUILD-NOW data reproducible, spoof-proof, and cheap to launch.

**1. CCDL-RUN declarative run-spec compiler + HASH-GATE preflight (effort L).** A ~20-line typed file (`model_ref`, `layer_set`, `detector_ref`, `stimulus_bank_ref`, `null_spec`, `seed`) that lowers to the real engine calls, **refuses to run unless every input matches a declared sha256** (`REGISTRY_HASH_MISMATCH`), refuses to bind the known-fake public-worker path (`FAKE_PATH_REFUSED`, guards the recorded integration break), and emits a content-addressed event log. Biggest force multiplier: collapses the cost of launching every future real-model test. *Caveat: the engine callables may live in the off-repo successor lane — may need a cross-repo import shim.*

**2. GOLDEN-TRACE-CI determinism bench (effort M).** Freeze each validated detector's (program+seed+stimulus)→event-list as a golden file; CI replays and fails on any non-byte-identical trace. Ships one deliberately-broken fixture per detector that MUST mismatch. Pins recorded numbers (e.g. the subspace-ablation 78.571%→3.571%, p=0.03225806451612903) so no refactor silently regresses a proven result. *Caveat: byte-identical floats across BLAS backends is hard — canonicalize to fixed decimal above the noise floor.*

**3. VERDICT-ENVELOPE output schema (effort S).** Every detector returns one shared envelope with a top-level verdict (SEPARATED / NULL_AT_CHANCE / UNDERPOWERED / NOT_LICENSED / UNSTABLE) plus a **mandatory reason code**. Makes honest negatives structurally first-class — a NULL_AT_CHANCE carries its own evidence and cannot be silently paraphrased or upgraded. Enforces the spec-sheet rule at the type level.

**4. FD-PRIOR — Foundation-Drive routing table as a labeled prior (effort M, produces real data).** Load `fd_routing_28.json` (hash-gated) as a 28×7 prior over the 7 Drives; for a Foundation×World-tagged stimulus, project real activations onto drive directions and report measured-vs-predicted mixture + Fisher-Rao divergence vs a cell-shuffle null. Upgrades drive probing from open-ended to falsifiable. *Caveat: drive directions were validated as a likelihood shift, not an absolute mixture basis — this new use must itself be validated; 160m may be too small (a first NULL is acceptable).*

**5. Governance-Weighted NCCS Aggregation with a coherence gate (effort M).** Replaces flat averaging with explicit logged trust dials (alpha/beta/lambda) and **refuses to emit a single composite until the coherence gate confirms a global section** — otherwise returns DISPERSED + the tension report. Note: this layer is engineering, but its gate *depends on* the CAS-Laplacian, which is research/new-matter — flag the dependency.

---

## 4. RESEARCH TRACK — new math, each needs its own patent filing

Every item here is new matter not covered by provisional 64/037,173 (predates 2026-04-13). **Flag for a filing before any arXiv, disclosure, or utility-patent inclusion.** Ranked by value.

**A. Element-40 Rung + Fisher-Rao Interlacing Screen (T4) (effort L). Honest obstruction: T3.** Build the d=40 rung, then test whether coarsening 40→10→4 preserves distinctions via Cauchy eigenvalue interlacing. **The pass condition is beating the recorded T3 contraction, not ignoring it** — naive marginalization has large interlacing defect; a valid coarsening must clear it. Produces real data once the rung exists. This is the capability that makes the ladder a coherent whole rather than three unrelated probes.

**B. CAS-SEP granularity-map learner (effort L). Directly answers T3.** Learns the distortion-minimizing isometric (Stiefel) map between rungs from real activations, replacing naive averaging; reports achieved distortion against the recorded T3 number as pass/fail. The concrete tool that turns T4's ambition into a testable build.

**C. CAS-Laplacian Coherence Certificate — single-model, cross-model, and fleet (effort L–XL).** One 0–1 coherence number + named worst-seam from `dim ker(L)` and the spectral gap. Three scopes: intra-model (layers as nodes), cross-model (models as nodes — attacks the "CAS is just your rubric" objection with a computable objectivity number), and fleet (300B sharded audit governance). **Crux: seam maps must be isometric SEP fits — a sloppy projective seam manufactures false coherence, which is exactly where T3 bites.** Produces real data.

**D. Bounded-Distortion Reading Certificate — SEP error bar (effort M).** Stamps every harness reading with a proven distortion bound (SEP residual → epsilon); readings over threshold auto-flag FLAG_FOR_HUMAN_REVIEW. Converts every existing probe output from "wired" into "measurement with an error bar."

**E. Spectral Involution-Balance Certificate (effort M).** Replaces the hand-tuned involution-balance term in NCCS with a provable spectral quantity on the two already-validated involution axes (^2/^3, ^8/^9). Low-risk because it uses validated axes.

**F. Inverse CAS Assessment — Behavior-to-Architecture (effort L).** Solve for the latent CAS profile that best explains a model's outputs; **calibrate and validate the inverse on open-weight models where activations give ground truth**, then certify only the axes that land within a pre-registered Fisher-Rao tolerance (others reported NOT_LICENSED for behavior-only use). Produces real data in calibration. This is the flagship product engine (see §5).

**G. Stated-vs-Enacted Divergence — counterfactual global section (effort XL).** The gap between the state a model's outputs *imply* and the state its activations *show* — a grounded alignment/deception residual. Highest product relevance, highest effort; must return NO_GLOBAL_SECTION when no reconciling section exists rather than fabricate one.

---

## 5. THREE FLAGSHIP CAPABILITIES worth naming as products

1. **Inverse CAS Assessment (Behavior-to-Architecture)** — "Hand us only your model's outputs — no weights, no internals — and we return the cognitive architecture that explains them, validated against open-weight ground truth." The only assessment that works on closed API models, which is the only artifact enterprises can actually share. *(Research track, new matter.)*

2. **Cognitive Coherence Certificate** — "One spectral number, computed from your model's own activations, that says whether it holds one consistent cognitive architecture or several incompatible self-models." Turns 'coherence' from a marketing adjective into a signed, regulator-facing, falsifiable quantity (kernel dimension). *(Research track, new matter; single-model version pairs with the $0 Live Coherence Meter today.)*

3. **CAS Version-Drift Regression Report** — "A cognitive diff between two checkpoints that flags, per axis, whether fine-tuning silently blurred your valence axis or collapsed a Processing Domain." Buildable now on validated axes, no new math, a re-buy every release cycle. *(BUILD NOW.)*

---

## 6. Build this first: the Operator-10 Rung

**The single highest-value build is the Operator-10 (d=10 Noetic) detector.** It is the owner's stated top priority (real-model data at $0), it is only effort M, and its main input — the per-example `labels_operator` column — **already exists in the 40E capture npz**, so it is mostly an unused label waiting for a readout rather than a new capture campaign. It is also the structural keystone: it is the missing middle rung that turns the 40/10/4 ladder from 2-of-3 into a complete object, and it is the prerequisite that unlocks the entire Fisher-Rao interlacing screen (T4), the coherence certificates, and the SEP granularity learner. Everything in the research track waits on the ladder being complete; the ladder waits on this one rung; and this one rung is the cheapest real-model experiment on the board.