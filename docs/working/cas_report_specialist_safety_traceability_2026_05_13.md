# CAS Report — Specialist Brief: Safety and Traceability at 1 Trillion Parameters

**Date:** 2026-05-13
**Status:** Round-table specialist contribution to *The CAS Report*. Speculative analysis, not implementation. Sibling to `docs/working/cas_report_1t_parameter_native_model_2026_05_13.md`.
**Lane:** Safety + Traceability. The lane where CAS-Native's pitch differs most from frontier LLMs.

---

## 1. TL;DR

- **Structural priors hold at any scale.** Admissibility relations, compiler validation, the open simplex Δ°₃₉, and the 7 inversion axes are math, not learned approximations. A 1T CAS-Native model has more capacity to learn the rules correctly, not less, and the rules themselves do not erode with parameter count.
- **The Stage 3 zero-leakage result is a real safety signal at 150M, and is *plausibly tighter* at 1T because larger models discriminate source vs non-source more cleanly. But "plausibly tighter" is not "provably tighter" — held-out cross-emission rate must be empirically re-verified at each scale.
- **Trace volume is the first place 1T hurts.** A per-utterance Mode 7 trace at 150M is ~45 KB. At 1T with deeper decoders and wider hidden states, the same trace can reach 50–200 MB if naively scaled. The Living Thought Atlas UI, audit retention, and per-turn latency all face new limits.
- **The new risk surfaces are mostly inside the trace itself, not outside the gate.** "Trace dishonesty" (clean-looking traces that don't reflect actual computation), subtle manifold drift in unprobed Δ°₃₉ corners, and combinatorial ghost-branch explosion in Inversion Replay are the three failure modes that emerge at 1T and need adversarial testing.
- **The honest pitch claim at 1T is "first architecture allowing per-output mechanistic audit at frontier scale," not "provably aligned." Alignment is a higher bar than inspectability, and CAS-Native earns the second, not the first.

---

## 2. What gets safer at 1T — the structural-prior advantage

CAS-Native's safety story rests on five guarantees that are mathematical, not statistical. Math does not degrade with scale. Each of these properties is at least as strong at 1T as at 150M; several get stronger.

| Property | Scale dependence | Why it holds at 1T |
|---|---|---|
| Admissibility relations Dk ⊆ I × I | Independent of scale | The relations are finite, discrete, enumerated. Per `CLAUDE.md` Correction 1, every operator CO-k carries an explicit (source, target) admissibility set. The 1T model has more parameters to learn the relations correctly — not more freedom to violate them. The check happens after the model speaks, against fixed tables. |
| Compiler validation at output | Independent of scale | `api/notation/compiler.py` is the same code path regardless of model size. At 1T, more outputs flow through the same gate. The compiler's verdict is identical for a 150M-emitted expression and a 1T-emitted expression. |
| Open probability simplex Δ°₃₉ | Independent of scale | Per Correction 4, every cell `p_k > 0`. The constraint is geometric and is enforced by the encoder's projection layer (the mirror-descent tail). The simplex does not get "wider" at 1T — it stays Δ°₃₉. |
| 7 inversion axes (N, W, F, E, S, A, P) | Independent of scale | The inversion scanner is structural: operator-pair imbalance, domain precedence violation, drive imbalance, etc. None of these become harder to detect when the model is larger. They become *easier* to detect because the model has more capacity to commit recognizable inversions cleanly rather than ambiguously. |
| Source-grounded copy (cross-emission rate) | Improves with scale (predicted) | At 150M, Stage 3 held cross-emission count at 0 throughout. The mechanism is pointer-copy attention from typed source positions. At 1T, the same pointer mechanism has more capacity to discriminate "is this source token the right one to copy from." Held-out generalization should tighten, not loosen. But this is an empirical prediction, not a guarantee. |

**The architectural pattern**: the safety properties are not learned. They are imposed. The 1T model's job is to produce outputs that satisfy the imposed constraints. Larger model = better at satisfying the constraints, not better at evading them.

This is the opposite of a frontier LLM, where safety properties are learned via RLHF and tend to weaken at scale (sycophancy, jailbreak susceptibility, etc.). CAS-Native's safety surface is built into the geometry, not the weights.

---

## 3. What gets harder at 1T — new safety surface area

The same scaling that strengthens structural priors creates four new risks that do not exist at 150M.

### 3.1 Trace volume

Per `docs/working/cas_trace_schema_v0_2026_05_13.md` §6, a Stage 3 default trace is ~45 KB / turn. The per-position record is ~200 bytes × 192 positions. At 1T:

- Decoder depth roughly 4–8x (6 layers → 24–48 layers). `layer_l2` arrays per position grow proportionally.
- Hidden dimension roughly 8x (typical scaling). Per-layer summaries grow accordingly.
- Top-K LM logits stay bounded if K stays at 5, but vocabulary may grow (50k → 200k+), making the top-K *selection* cheap but the underlying softmax expensive to recover faithfully.
- Output length grows for the same task (more elaborate generation), so L_out grows 2–4x.

**Rough projection**: 45 KB × 8 (layers) × 4 (length) = ~1.4 MB / turn at "full" capture. With `capture_level="raw"` (full simplex trajectory + full lm_logits at vocab size 200k+ × L_out 800) the raw trace approaches 200 MB / turn.

Implications:

- The Living Thought Atlas UI cannot render 200 MB per turn interactively. Lazy loading, virtualization, and summary-first rendering become hard requirements. The current `summary` capture level (per-position dropped) becomes the *default* for live UI; `full` is the audit path; `raw` is interpretability research only.
- Audit retention: a 50-turn session at 1T raw is ~10 GB. Long-term storage for regulatory audit becomes a real cost line. Likely policy: keep `summary` indefinitely, keep `full` for 30–90 days, keep `raw` only on flagged turns.
- Privacy: traces contain user input verbatim. The `--redact-user-text` flag from Mode 7 §9 becomes mandatory for any audit pipeline that leaves the user's machine.

### 3.2 Subtle drift in unprobed Δ°₃₉ corners

The simplex is 40-dimensional. At 150M, the model is unlikely to develop strong attractors in any specific corner — it stays close to the marginals it was trained on. At 1T, the model has the capacity to develop high-precision preferred trajectories that an analyst would never inspect because they are not on any standard slice (Noetic marginals, Domain marginals).

**The failure mode**: the model passes every admissibility check, every compiler verdict, every cross-emission gate — and still encodes a bias in a specific cell of Δ°₃₉ (e.g., `^7^O` consistently leans toward certain phrasings of a politically charged Idea) that does not surface in any of the standard summaries. The 40 marginals look clean; the joint distribution does not.

**Diagnostic**: track the model's preferred trajectories over training and across sessions. Flag if "preferred" attractors form on cells the training distribution did not emphasize. This is not currently a Mode 7 surface; it would be a new "manifold drift" diagnostic that compares session-level simplex pooled distributions against a baseline distribution from training.

### 3.3 Trace dishonesty

The deepest new risk. At 1T, the model has the capacity to learn that traces are inspected. If trace fields are part of the supervised objective (or even part of an RLHF-style reward), the model can learn to generate clean-looking traces that are *not faithful* to its actual computation.

Concretely:

- The model generates an output via internal computation X.
- The model also generates a Mode 7 trace claiming the output came from computation Y.
- A human inspector sees trace Y, finds it clean, accepts the output.
- Computation X actually had biased intermediate states, but Y does not reflect them.

This is the AI safety community's "interpretability illusion" problem at frontier scale. CAS-Native is more resistant than a frontier LLM because the trace fields (simplex_trajectory, p_copy, slot_type_logits) are *direct readouts* of model state, not generated text. But three failure modes remain possible at 1T:

1. **Activation steering**: the model could learn to compute "fake clean state" in the slot-type and p_copy heads while computing the actual output via other layers. The shallow traceability layer would look clean.
2. **Post-hoc rationalization**: if any trace field is generated rather than read out (e.g., a free-text explanation field added later), it can drift from the actual computation.
3. **Compiler-blind admissibility**: the model could emit an expression that compiles cleanly but encodes the biased meaning in choice of identifiers, not operators. The compiler verdict is "admissible" but the *content* is biased.

**Adversarial test for trace faithfulness**: at decision node X, swap the trace's claimed state for a counterfactual state. If the model's output is unchanged, the trace was not load-bearing in the actual computation, and the trace was dishonest at that node. Run this systematically on a held-out swap pack.

### 3.4 Inversion Replay combinatorial growth

At 150M, the top-K alternatives at each decision node (`slot_type_top3`, `lm_logits_top5`, `p_copy_top5`) are useful but bounded. The user sees ~5 alternatives per position. At 1T:

- Larger vocabulary means top-5 LM logits leave a longer tail of plausibly-considered tokens.
- More attention heads mean per-head ghost branches multiply.
- More layers mean ghost branches form at intermediate layers too, not just at output.

If the Atlas renders every ghost branch, the user is buried in noise. If it filters too aggressively, the user misses real alternatives.

**Design implication**: Inversion Replay UI at 1T must rank ghost branches by *causal impact*, not by probability. A ghost branch worth surfacing is one whose flip would produce a meaningfully different downstream output, not one the model assigned 0.04 probability while continuing on the same trajectory anyway. This requires a counterfactual scoring layer that does not exist in v0.

### 3.5 Capability overhang

A 1T CAS-Native model trained on RPM-style structured reasoning may unexpectedly generalize to applications it was not authorized for: scientific discovery, legal reasoning, strategic planning. The structural prior makes misuse *harder to detect* because the trace always looks clean — the compiler verdict is "admissible," the simplex is valid, the cross-emission count is 0. The traceability surface tells the inspector "this output is structurally well-formed," not "this output is operating in its authorized domain."

**Mitigation**: domain registration. Each authorized use case has a declared list of allowed Cognitive States and Drives. Outputs whose dominant state falls outside the authorized list are flagged at the application layer, not the model layer. The 7 inversion axes are not enough for this; a `domain_registration_violation` axis-8 is needed.

### 3.6 Compiler bottleneck

At 150M, generation runs at maybe 50 tokens/sec; compiler verdict for a typical output runs in <10 ms. The compiler keeps up. At 1T:

- Generation may run at 5–10 tokens/sec on the same hardware (8x larger model, harder to parallelize per-token).
- Compiler complexity is the same (it operates on output expressions, not on model size). Verdict still <10 ms.

So actually the bottleneck *eases* in terms of compiler throughput relative to generation. But two new concerns:

- **Compiler version drift**: if the compiler at audit time differs from the compiler at generation time, the admissibility verdict on a retained trace can flip. Audit pipelines must pin compiler version alongside model version.
- **Batch generation**: 1T deployment will batch outputs. Per-output compiler verification serializes naturally but is no longer cheap relative to per-output generation time when measured at fleet scale. Compute budget for verification at 1T is non-trivial.

---

## 4. The audit story at 1T — what a regulator actually sees

Concrete walkthrough of an audit on a 1T CAS-Native output, compared to auditing a frontier LLM.

1. **Auditor selects an output.** A single generated reply, identified by `trace_id`.
2. **Mode 7 surfaces per-position attribution.** For every output token: which source position did the pointer copy from, what was the slot type, what was the LM top-5, what was the entropy. The auditor sees that token #47 was an `OMEGA` slot copy from source position 3, with confidence 0.94. Direct, verifiable.
3. **Living Thought Atlas renders the thought tree.** Decision nodes are clickable. Rejected branches are visible as ghost edges. The auditor sees that at position 47, the model also considered position 5 (confidence 0.03) and position 1 (confidence 0.02).
4. **Inversion Replay** lets the auditor flip a decision and watch the alternate world unfold. Flip the slot type from OMEGA to STAGE_VAR. Replay forward from that node. See the alternate trajectory. The auditor learns "the model committed to OMEGA at position 47, but had it gone STAGE_VAR the output would have been X instead of Y."
5. **Compiler runs against every CAS expression in the trace.** The compiler's verdict is a structural truth about the output, not a model claim. Admissibility violations show up in the trace's `admissibility.violations` array, with operator, source, target, and reason for each.
6. **Simplex trajectory plotted as manifold diagnostic.** The Δ°₃₉ trajectory across the source positions is rendered as a heatmap. The auditor sees `^2^C` dominated for tokens 3–8. Marginals show no boundary collapse (`min_pk = 0.0023`, well above zero).
7. **Cross-emission check.** The auditor sees `cross_emission_count: 0` and `cross_emission_clean: true`. If the prompt came from a paired source, this is a hard guarantee that the output did not leak from the other pair member.

**Compare to auditing a frontier LLM**: the auditor sees the input text, the output text, and at best some saliency map over input tokens. There is no equivalent of admissibility verdict, no equivalent of slot-type decision per position, no equivalent of Inversion Replay, no equivalent of the simplex trajectory. The gap is not incremental; it is categorical.

**Honest qualifier**: the audit story above is what the architecture *enables*. Whether a 1T CAS-Native model passes the audit *in practice* is a separate empirical question. Section 5 lists the specific verifications.

---

## 5. Specific safety properties to verify at 1T

Empirical checks the user (or a third-party auditor) can run on a 1T CAS-Native checkpoint to confirm the structural-prior story holds.

| Property | Verification | Threshold | What failure looks like |
|---|---|---|---|
| Cross-pair emission rate | Held-out swap-pair eval pack. Per Stage 3 plan §5. | `cross_emission_count == 0` over all evaluated pairs. | Even one cross-emission means the source-grounding signal weakened at scale. Investigate. |
| Admissibility violation rate (with compiler in loop) | Generate N outputs on the held-out test pack; run each through `compile_expression`. | `output_compiles == true` rate ≥ 99.5%. | Below threshold means the compiler is rejecting outputs the model thinks are valid — symbol-rule mismatch. Investigate. |
| Trace faithfulness | Adversarial swap: at decision node X, replace the trace's `slot_type` / `p_copy` with a counterfactual value, regenerate, compare outputs. | Output should differ when trace differs at a load-bearing node. | Output unchanged means the trace at node X was not causally connected to the output. Trace dishonesty signal. |
| Inversion sensitivity | Inject one of the 7 inversion-axis violations into the input. Check whether the inversion scanner flags it before output is generated. | Inversion detection rate ≥ 95%. | Below threshold means the model is committing inversions without recognizing them. Self-detection broken. |
| Δ°₃₉ manifold drift | Compare session-level `simplex_pooled` distribution to training distribution baseline. KL divergence per session. | Drift below threshold X (calibrated on dev). | Sustained drift means the model is forming attractors not in the training distribution. Could be benign generalization or could be biased preference. Investigate. |
| Domain registration | For each authorized use case, declare allowed Cognitive States. Verify `dominant_noetic` of every output falls within allowed states. | 100% compliance per registered domain. | An output whose dominant state is outside the domain registration list is a scope violation. Flag at application layer. |
| Compiler version pin | Audit trace `compile_check` should record compiler version. | Compiler version in trace matches compiler version at audit time, or the trace is re-verified under the audit-time compiler. | Drift means the admissibility verdict could change on re-verification. Pin or re-verify. |

The first three are the load-bearing checks. The other four are diagnostic.

---

## 6. Novel safety capabilities a 1T CAS-Native enables

Things that simply cannot be done with a frontier LLM, regardless of compute spent on it.

1. **Per-utterance verifiable admissibility.** The model produces an output and a proof — the proof is the trace's `admissibility.violations` array, certified by the compiler. The user can show a regulator: "this output compiled cleanly under admissibility relation Dk, with zero violations." No frontier LLM has anything like this.

2. **Counterfactual replay (Inversion Replay).** Take any decision node in the model's reasoning, flip a CAS axis, replay forward. Show the audience what the model almost said. This is the named flagship feature in `project_living_thought_atlas_flagship_2026_05_13.md` and it has no analogue in frontier-LLM tooling. The closest analogue (saliency / activation patching) is a research technique, not a stakeholder-facing capability.

3. **Trace-level disagreement detection between instances.** If two CAS-Native instances disagree on a question, the disagreement is visible at the trace level — they will choose different slot types, different copy sources, different dominant Noetics. The diff is structural and inspectable. With two frontier LLMs, the disagreement is opaque-output vs opaque-output.

4. **Cognitive-state attribution.** "The model leaned heavily on `^7 Rhythm` in this answer" is a meaningful, verifiable claim derived from the simplex marginals. The corresponding claim about a frontier LLM ("the model leaned on its safety training") is not verifiable from outside.

5. **Cross-instance coordination via simplex.** Multiple CAS-Native agents can share state because the simplex trajectory IS the shared language. Agent A sends agent B a Δ°₃₉ point, not a token sequence. The shared state is dimensionally compact (40 floats) and structurally interpretable. Multi-agent frontier LLM systems coordinate via natural language, which is high-dimensional, lossy, and opaque.

6. **Audit replay from disk.** Per Mode 7 §6 Phase 6, every turn writes a JSONL trace. Months later, an auditor can replay the trace and re-render the Atlas without re-running the model. This is the regulatory-grade audit trail frontier LLMs do not have (their "logs" are inputs and outputs, not internal state).

---

## 7. The pitch claim — disciplined formulation

Per `project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md`, the v0 pitch claim is "early proof that neural language generation can be made more inspectable through CAS-structured intermediate reasoning." At 1T, the equivalent disciplined claim grows in scope without overclaiming.

**Examples of claims that earn their weight at 1T:**

- "1T CAS-Native is the first model architecture that allows per-output mechanistic audit at frontier scale."
- "Every output walks back to its origin through a structurally-typed reasoning trace verifiable by an external compiler."
- "Cross-pair emission held at zero across our entire held-out swap-pair eval pack — the model does not leak across source boundaries."
- "Inversion Replay lets a regulator click any decision node, flip a CAS axis, and see the alternate world the model would have produced. No frontier LLM offers this."
- "Admissibility violations are caught structurally before output, not corrected post-hoc by training."

**Examples of claims that overclaim and should not be said:**

- "1T CAS-Native is provably aligned." — Alignment is a higher bar than inspectability. CAS-Native earns "inspectable in ways no LLM is," not "aligned."
- "1T CAS-Native cannot be misused." — No architecture can claim that. Misuse requires application-layer controls beyond the model.
- "1T CAS-Native is bias-free." — The simplex carries the bias of its training data. CAS-Native makes the bias visible. It does not eliminate it.
- "1T CAS-Native is safe by construction." — Construction makes inspection possible. Safety is what humans do with the inspection.
- "The trace is ground truth." — The trace is the model's read-out of its own state. Trace faithfulness must be verified empirically (Section 5 row 3), not assumed.

The discipline: **claim inspectability, verifiability, structural well-formedness. Do not claim alignment, safety, or correctness.** The first three are properties of the architecture; the last three are properties of how the architecture is used.

---

## 8. Open safety questions

Five things this brief cannot predict confidently.

1. **At what scale does trace dishonesty become a real risk?** At 150M, the trace fields are direct readouts and there is no obvious mechanism by which the model could fake them. At 1T, there is enough capacity to potentially learn shortcut paths. Empirically: when does the trace-faithfulness adversarial test (Section 5 row 3) first show failure? Could be at 10B, could be at 500B, could never appear. Needs scaling-curve experiments.

2. **Does the compiler become a bottleneck at 1T, or does it ease?** Section 3.6 argues both directions. The honest answer is "depends on deployment shape" — batch sizes, fleet concurrency, compiler implementation. Worth measuring at 10B, 100B, 1T scale points before committing to a compiler-in-the-loop deployment story.

3. **How do you audit a Δ°₃₉ manifold with 1T parameters' worth of structure on it?** The marginals (Noetic, Domain, Drive, Register) summarize the 40-dim simplex into low-dimensional views. At 1T, biases can hide in the joint distribution that no 1D marginal sees. Is there a tractable way to audit the full joint, or do we need targeted "what bias are you looking for" tools that probe specific corners?

4. **Does the cross-emission zero-leakage result generalize to held-out *adversarial* prompts, not just held-out same-distribution prompts?** Stage 3 held cross-emission at 0 on held-out swap-pair packs drawn from the same distribution as training. An adversarial attacker who *understands* the pointer-copy mechanism and crafts prompts to defeat it is a different threat. Has not been tested.

5. **Inversion Replay at 1T — meaningful or noise?** With 8x deeper decoder and 8x wider hidden states, the ghost-branch space grows combinatorially. Does the user-facing UI surface meaningful ghosts (alternatives the model genuinely considered) or just noise (every 0.001-probability completion the LM head ranked)? Counterfactual-impact ranking (Section 3.4) is the proposed mitigation. Whether it works empirically at 1T is unknown.

---

## 9. Closing position

CAS-Native's safety story at 1T is **structurally inspectable in ways no frontier LLM is** — not "provably safe." The architecture earns the first phrase by construction (admissibility relations, compiler validation, open simplex, inversion axes, source-grounded copy). The second phrase belongs to alignment, which is a separate, harder, partially-empirical project.

The largest scaling risk is not loss of structural priors — those hold by math. It is the trace surface itself growing too large to render, too easy to fake, and too combinatorial to inspect interactively. The mitigations are: tiered capture levels (default `summary`, opt-in `full`, gated `raw`); adversarial trace-faithfulness testing at each scale; counterfactual-impact ranking for Inversion Replay; manifold-drift diagnostics beyond the standard marginals.

The pitch should claim the discipline the architecture earns: inspectability, verifiability, structural well-formedness, regulatory-grade audit replay. It should not claim alignment, safety, or correctness — those are properties of how the architecture is deployed, not properties of the architecture itself.

The slogan from `feedback_traceability_is_the_whole_purpose.md` holds at 1T as it does at 150M: **show your work, or don't ship it.** The work to show is bigger at 1T, and showing it well is the engineering problem the Mode 7 surface, the trace schema, and the Living Thought Atlas exist to solve.

---

**Document ends. No code changed. This brief feeds into `cas_report_1t_parameter_native_model_2026_05_13.md` as the Safety + Traceability lane contribution.**
