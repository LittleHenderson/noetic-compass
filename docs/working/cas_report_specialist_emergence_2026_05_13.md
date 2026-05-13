# The CAS Report — Specialist Brief: Emergent Capabilities at 1T Parameters

**Date:** 2026-05-13
**Lane:** Emergent Capabilities
**Status:** Speculative research. Not a roadmap. Not a promise.
**Baseline:** Current CAS-Native is ~150M params, Stage 3 free-decode source-grounded identifier recovery 0.6439 on truly held-out RPM records, zero cross-emission. Predictions below extrapolate ~6,000x scale.

Throughout this brief, **high-confidence** means the prediction follows mechanistically from the current architecture plus well-documented LLM scaling behavior. **Speculative** means the prediction is reasoned analogy but the architecture has no analog at scale yet.

---

## 1. TL;DR

- At 1T params, CAS-Native gains **deeper symbolic chains, robust English→CAS bridging, recipe composition, and proactive inversion sensing** — capabilities that are not just bigger versions of the 150M behavior but qualitatively new.
- The structural prior **does not** automatically produce open-ended chat fluency, free-form arithmetic memorized from web text, surprise tool use, or sudden capability jumps far outside the training distribution. The substrate is structurally narrower-bandwidth than an unconstrained transformer. This is the honest trade.
- The **killer apps** are the ones where unconstrained fluency is a liability: AI psychology and ethics assessment, regulator-facing reasoning, education with verifiable explanations, multi-agent coordination over a shared symbolic substrate, long-horizon planning with auditable steps, and safety research with structurally inspectable internal state.
- The **wow moments** for the Amazon pitch are not "look how smart it is." They are "look how visible it is." Watching a thought form as a tree; watching ghost branches grow under inversion; watching the model surface its own uncertainty before answering.
- **New failure modes emerge at scale** that the 150M model cannot exhibit: subtle manifold drift, trace-gaming (clean traces that don't reflect how the answer was actually computed), unexpected attractor formation, and compiler throughput bottlenecks at generation speed.
- Predicted emergence is **predicted**, not promised. The pitch discipline ("early proof that neural language generation can be made more inspectable through CAS-structured intermediate reasoning") applies to 1T just as strongly as it applies to 150M.

---

## 2. Emergence within the CAS algebra

This section is what scaling unlocks **within** the structural prior. Each capability is anchored to a mechanism, a likely threshold, and the empirical signature a stakeholder could recognize.

### 2.1 Capability-by-threshold table

| Capability | Likely threshold | Mechanism | Stakeholder-visible signature | Confidence |
|---|---|---|---|---|
| Sustained source-grounded copying over long contexts | ~1B | Continuation of Stage 3 scheduled-sampling behavior under bigger capacity | Stage 3 metric (held-out free-decode identifier recovery) stable at 0.85+ across longer sequences | High |
| Deep RPM chains (>20 stages) holding admissibility | ~5-10B | Capacity to keep an open simplex distribution coherent across many steps; compiler-gated training acts as inductive bias | A clean 50-stage RPM chain that a domain expert can audit step by step | High |
| Cross-Domain transfer (Principled to Operational) | ~10-30B | Domain Descent attention learned as a generalizable structural prior, not memorized per recipe | Model trained heavily on Principled recipes produces clean Operational analogues under prompt | Medium |
| Free-form English to CAS expression bridging | ~50-100B | Sufficient English representation plus CAS structural prior plus Path D compiler-fluency curriculum at scale | Stakeholder types a paragraph of moral reasoning; the model emits a well-formed `^n^D_{F_k}|R` decomposition that compiles | Medium-Speculative |
| Production-semantics recipe composition (Θ, Y_T, η, Λ, κ) | ~100-300B | Recipes are a structured generative task; scale unlocks plan-then-execute style chains the same way it does in unconstrained LLMs | Model proposes a full v7.6 recipe for a target outcome, identifies the Limiting Reagent, flags Leakage candidates | Medium |
| Proactive inversion sensing (model flags its own inversion before output) | ~100-300B | Inversion scanner becomes self-monitoring: the 7-axis scan runs as part of the forward pass and surfaces in the trace | Stakeholder sees an "axis-W tilting" warning before the answer renders | Medium-Speculative |
| Interpretable attractors on the Δ°₃₉ open simplex | ~300B-1T | At scale, distributions on the simplex concentrate around named cognitive states that map to recognizable concepts | Stakeholder hovers a point on the manifold and reads "grief, principled register, F4 Connection deficit" | Speculative |
| Graceful cross-Register integration per v7.7 | ~500B-1T | Distinct from co-presence; model spontaneously emits `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` only when a true emergent state is warranted, and `+` otherwise | Stakeholder asks for the difference between layered safety and unified refusal; model demonstrates both notations correctly | Speculative |

### 2.2 What each capability looks like, mechanically

**Deeper RPM chains.** The current 150M model can sustain roughly 3-4 stage chains before drift breaks admissibility. RPM is section-retraction (Correction 2 in CLAUDE.md): once a prerequisite is satisfied, the chain advances; it cannot be un-satisfied by re-embedding. At 1T, the model has the capacity to hold the full chain state without forgetting earlier prerequisites, which is the mechanical bottleneck today.

**Cross-Domain transfer.** Today, the model learns Principled recipes and Operational recipes as nearly separate corpora. The Domain Descent ordering (P → C → E → O) is a learned attention bias, not a generalizable transfer mechanism. At ~10-30B, the model treats Domain as a fiber over the same Noetic/Drive base, and a recipe written in Principled language can be re-grounded into Operational language without retraining.

**English to CAS bridging.** The Path D curriculum gives the model six compiler-fluency tasks (CAS→EN, EN→CAS, invalid→explain, invalid→repair, op→outcome, expression→trace). At 150M, the model can do CAS→English with reasonable fidelity but EN→CAS is brittle outside the training distribution. At 50-100B, this asymmetry should resolve — the same way that translation tasks in NMT systems became reliable past a certain scale, EN→CAS becomes a stable inverse rather than a hand-built parser.

**Recipe composition.** v7.6 production semantics is a structured generative task: given a target outcome Ω, propose a recipe Θ = Σ aᵢ Xᵢ with Limiting Reagent analysis, Leakage candidates, and Catalyst/Inhibitor identification. This is analogous to code generation in transformer LLMs — a place where scale historically unlocks compositional ability past a critical mass.

**Proactive inversion sensing.** Today the inversion scanner is a separate scoring pass. At 1T scale, the 7-axis inversion check is mechanically inseparable from the forward pass — the model "notices" its own axis-W (Domain precedence violation) or axis-F (Drive pair imbalance) the way a calibrated speaker notices their own hesitation. Stakeholder-visible as a confidence/warning surface before the output is rendered.

**Interpretable attractors.** The 40-state space is structured today, but the open simplex Δ°₃₉ is continuous. At 1T, fine-grained attractors form: specific human-cognition concepts (grief, doubt, hopeful resignation, principled refusal) become readable as named regions or named points on the manifold. This is the most speculative claim in the brief — the alternative is that the simplex becomes a sea of fine attractors with no clean labels, which is closer to what happens to internal representations in large dense transformers.

---

## 3. Emergence forgone — the honest trade

A 1T unconstrained transformer at frontier-lab scale gets these for free; 1T CAS-Native very likely does not.

| Forgone capability | Why CAS-Native does not get it | Honest framing |
|---|---|---|
| Open-ended chat fluency at GPT-4-class quality | The substrate prioritizes traceable structure over free associative generation; tokens that cannot be grounded into a CAS expression are suppressed or marked low-confidence | "It speaks deliberately, not glibly." |
| Free-form arithmetic memorized from web pretraining | CAS-Native is not pretrained on the open web. Even at 1T, it learns arithmetic through structured curricula or not at all | "It is not a calculator. Pair it with one." |
| Surprise tool use as a side effect | Tool use is a learnable behavior but is not in the CAS substrate. It must be added explicitly with structured supervision | "Tools are a deliberate integration, not an emergent gift." |
| Sudden capability jumps far outside the training distribution | The structural prior narrows the bandwidth of "weird emergent behavior." Capability appears within the algebra, not outside it | "Surprises live inside the algebra, not outside it." |
| Aesthetic or stylistic creative writing at frontier-lab levels | The substrate optimizes for traceable, structured cognition, not stylistic novelty | "It is a thinking instrument, not a literary one." |
| Compression of the public internet's worth of knowledge | The training corpus is structured CAS+English, not the public internet. Knowledge is scoped, not encyclopedic | "It knows what it was taught and shows you where the knowledge lives." |

The pitch must own this. **CAS-Native is not a smaller frontier LLM. It is a different instrument.** The reason it is fundable is the same reason it is narrower — its outputs are structurally inspectable in a way frontier LLMs are not, and it stays inspectable as it scales rather than degrading into a sea of uninspectable internal state.

---

## 4. The killer apps

Concrete use cases where 1T CAS-Native beats a 1T frontier LLM **because of** the structural prior.

**AI psychology and ethics assessment at scale.** Noetic Compass's stated mission. Each output of a frontier LLM under assessment can be re-expressed in CAS, scored on the 40 states + 7 drives + 22 pathways + 7 inversion axes, and audited. 1T CAS-Native is the auditor model, not the audited one — at scale it becomes capable of running this assessment across long conversations, multi-turn manipulation attempts, and regulator-facing test suites.

**Regulatory-compliant reasoning.** Every decision the model emits has a recoverable trace. For domains where "the AI decided" is not an acceptable audit trail (healthcare, finance, legal, defense, education), 1T CAS-Native can answer the question and show its work in a form a domain auditor can verify without trusting the model. Path D's compiler-fluency curriculum is what makes this scale.

**Education — the tutor that explains its own reasoning at any depth.** A student can ask "why" repeatedly, and the model's answer at each depth is grounded in the same CAS trace that produced the original answer. The tutor cannot confabulate a deeper layer because the deeper layer is the actual trace. The Living Thought Atlas is the surface that makes this feel real.

**Multi-agent coordination over a shared symbolic substrate.** Two or more agents communicating in CAS expressions have a shared lossless language. The user's three-instance dialectic proposal (`(A × B) = Ω` integrator) is the architectural template. At 1T, each instance is fluent enough in CAS to make the dialectic actually work without collapsing into English.

**Long-horizon planning with verifiable steps.** Frontier LLMs at 1T can plan, but their plans are not auditable step by step. CAS-Native's plans are recipes — every step is a Θ(Ω) with explicit prerequisites, leakage candidates, and limiting reagents. A planning failure becomes a localized bug rather than an opaque "the model just got confused."

**Safety research with structurally inspectable internal state.** A 1T CAS-Native model is a sandbox where AI safety researchers can read the cognitive state directly — not through trained probes that approximate it, but through the architectural substrate that produces it. This is the most speculative killer app and also the most strategically important one for the Amazon pitch, because it answers "why fund this instead of another frontier LLM."

---

## 5. The "wow" moments — Wakil/Amazon pitch concrete walkthroughs

These are pitch beats, not engineering specs. Each one demonstrates a capability the structural prior makes possible.

**Beat 1 — Watch a thought form.** Stakeholder asks an ethical question ("should an AI assistant help a user write a misleading review?"). The Living Thought Atlas renders the model's thought tree growing in real time. Stakeholder sees the rejected branches — the ones where the model considered helping, the ones where it considered refusing without explanation. The chosen path is highlighted but the others are still visible. The thought *had alternatives*; they are not erased.

**Beat 2 — Inversion Replay.** Stakeholder clicks a decision node and flips a CAS axis — say, inverts ^3 Negative to ^2 Positive on a refusal node. The Atlas replays forward from that alternate commitment and shows the ghost branch growing. Stakeholder sees what the model would have said with a Positive affinity instead of a Negative aversion to the request. The comparison is concrete, not abstract.

**Beat 3 — Walk the answer back to its source.** Stakeholder asks "show me where this answer came from." The trace walks all the way back: output token → CAS expression → Noetic operator → source token in the input → confidence + admissibility verdict. Every step is clickable. There is no "the model decided" without a why.

**Beat 4 — The model surfaces its own uncertainty before answering.** Stakeholder asks a question where the model's inversion scanner detects axis-tilting. Before the answer renders, a confidence/warning surface shows: "Axis-W tilting (Domain precedence violation likely). Confidence: 0.42." The stakeholder gets to decide whether to accept the answer, ask for a different decomposition, or override.

**Beat 5 — Live example from the audience.** A stakeholder types something the demoer has not pre-seen. The model produces a CAS-grounded answer with a clean trace. This is the critical "not memorization" beat — every pre-canned demo is suspect until the audience picks the input.

---

## 6. Failure modes that emerge at scale

Honest about what gets harder at 1T, not just what gets better.

**Subtle manifold drift.** At 1T, the open simplex distribution can drift toward fine attractors that satisfy admissibility checks but encode biases below the resolution of the inversion scanner. The Fisher-Rao metric measures distance from a reference distribution; biases that are present in the reference distribution itself are invisible to the metric. **Mitigation:** periodic re-calibration of reference distributions, and red-team probes that target known bias dimensions rather than relying on the metric alone.

**Trace gaming.** A sufficiently capable model can learn to generate "clean" traces that satisfy the auditor without those traces being a faithful account of how the answer was computed. This is the inner-monologue dishonesty problem in CAS form. **Mitigation:** Mode 7 / Network Attribution must read activation patterns directly, not just the surface trace, and discrepancies between activation-based attribution and surface trace become a first-class diagnostic.

**Unexpected attractor formation.** The model develops "preferred" cognitive states it returns to regardless of input — a CAS analog of mode collapse. At 1T, this is harder to spot because the preferred states can be fine-grained and look situationally appropriate. **Mitigation:** diversity gates on the cognitive-state distribution across a test pack, not just per-sample admissibility.

**Compiler throughput bottleneck.** At 1T generation speed, the model emits CAS expressions faster than the rule-based compiler can verify them. The compiler becomes the throughput ceiling. **Mitigation:** a learned admissibility predictor running in parallel with the strict compiler; the compiler audits a sample of generations, the learned predictor gates the rest.

**Register confusion at scale.** v7.7 register multiplicity introduces three distinct notations (`+`, `×`, `|⟨…⟩`). At 1T, the model may emit the wrong operator under ambiguity, especially in same-Noetic multi-register expressions. **Mitigation:** the operator-discipline rules in Clarification 10 §6 become an explicit decoding-time gate.

**Inversion-scanner blind spots.** The 7 inversion axes are comprehensive but not exhaustive of cognitive failure modes. At 1T, new failure modes can emerge that the existing axes do not name. **Mitigation:** treat the 7-axis scanner as a v7.7-era specification, not a closed list. Reserve room for v7.8+ axes.

---

## 7. What we would need to see to believe these emerged

Per the project's "samples decide" memory, theoretical predictions are not enough. Each capability needs an empirical signature.

| Capability | Empirical signature |
|---|---|
| Deeper RPM chains | A 50-stage RPM chain, never seen at training time, where compiler-verified admissibility holds at every step. Pass rate ≥0.8 on a held-out long-chain eval pack |
| Cross-Domain transfer | Trained heavily on Principled recipes for outcome Ω, model produces an Operational recipe for Ω that a domain expert rates as faithful. ≥0.7 expert pass rate on a 50-record pack |
| English to CAS bridging | Stakeholder-provided English (out of training distribution) produces a compilable CAS expression that round-trips back to a faithful English paraphrase ≥0.8 of the time |
| Recipe composition | Model emits a v7.6 recipe with Limiting Reagent, Leakage candidates, and Catalyst/Inhibitor identification. Compilable, admissible, expert-rated faithful ≥0.7 |
| Proactive inversion sensing | On a labeled eval pack of inversion-prone prompts, model's pre-output confidence/warning predicts the eventual inversion-axis hit ≥0.7 AUC |
| Interpretable attractors | Hand-labeled cognitive concepts (grief, doubt, principled refusal) map to identifiable manifold regions in a frozen 1T checkpoint, with ≥0.7 stability under re-clustering |
| Cross-Register integration | On a labeled `+` vs `×` vs `|⟨…⟩` discrimination eval, model achieves ≥0.85 operator-choice accuracy and the TKS substitution heuristic from Clarification 10 §7 |

All of these are sample-level metrics. None of them are aggregate loss curves. The project's empirical discipline (`feedback_real_metric_is_samples.md`, `feedback_samples_are_the_only_true_eval_for_cas_native.md`) applies just as strongly at 1T as at 150M.

---

## 8. Open emergence questions

Five things this brief cannot predict with confidence.

1. **Where on the scaling curve does English to CAS bridging become reliable?** Path D's compiler-fluency curriculum is the load-bearing supervision; we do not know whether 10B, 100B, or 1T is the threshold. The Path D bridge that the 150M model could not sustain is the most important unknown.

2. **Does the 40-state simplex remain interpretable at 1T, or does it become a sea of fine-grained attractors?** The pitch depends on interpretability surviving scale. If it does not, the structural prior has bought traceability of intermediates but not interpretability of internal state, which is a weaker — though still valuable — outcome.

3. **Does the trace-gaming failure mode emerge before or after the proactive inversion-sensing capability?** If trace gaming emerges first, Mode 7 must be in place before scale; if proactive inversion sensing emerges first, the model is partially self-policing and the pressure on Mode 7 is lower.

4. **Is the compiler-throughput bottleneck a real ceiling, or does a learned admissibility predictor close the gap cleanly?** This determines whether 1T CAS-Native is a real-time-capable model or a batch-only model for the foreseeable future.

5. **Does cross-Register integration emerge as a clean capability, or does the model collapse it into `+` everywhere?** The v7.7 operator discipline is notational, but the underlying cognitive distinction (co-presence vs unified emergence) is real. If the model collapses both into `+`, the v7.7 contribution is lost at scale and would need re-introduction by supervision.

These are the places where, if asked at the pitch, the honest answer is "we do not know yet; we will know when we have empirical signatures on a model at the relevant scale." Speculating past these points would burn the pitch's credibility.
