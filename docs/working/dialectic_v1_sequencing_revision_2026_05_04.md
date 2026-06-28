# Dialectic v1 Sequencing Revision (2026-05-04)

Status: planning revision. READ-ONLY. No code modified.

Pointers:
- Original proposal memory: `project_three_instance_dialectic_proposal_2026_05_04.md`.
- Scaffold report: `docs/working/dialectic_scaffolding_report_2026_05_04.md`.
- Scaffold module: `noetic-compass-scaffold/noetic-compass/cas-native/dialectic/`
  (`__init__.py`, `instance.py`, `rotator.py`, `attractor.py`, `selector.py`,
  `orchestrator.py`, `tests/test_smoke.py`, `README.md` — 1995 LOC, 5/5
  smoke tests green).
- Lever 3 retrain runbook (the v1 prereq): `docs/working/combined_retrain_runbook_2026_05_04.md`,
  `docs/working/lever3_script_completion_2026_05_04.md`.
- Compiler: `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`.
- Predictor: `noetic-compass-scaffold/noetic-compass/cas-native/inference/predict_cas.py`.
- Logits-mask precedent:
  `noetic-compass-scaffold/noetic-compass/cas-native/inference/constrained_sampling.py`.

---

## 1. The revised sequencing

**Old plan.** The original three-instance rotating-axis dialectic
proposal scoped the prototype to **Year 2 / Paper E or F territory**.
The reasoning was load-bearing and correct at the time: a multi-instance
dialog stacked on a 47%-aggregate-paraphrase predictor is noise, not
structural search. The scaffold ships today as plumbing only —
`README.md` says it explicitly: *"Multi-instance dialog on a 47% base is
noise. The scaffolding is here to lock the INTERFACE so the real
components drop in without restructuring."*

**New plan.** v1 retrain prereqs are landing **tonight**. The Lever 3
paired-free-form generator is wired (`generate_lever3_paired_freeform.py`,
574 lines, dry-run validated), the retrain run is scheduled to land at
~3 AM PDT on 2026-05-05, and the projected free-form coverage is
60-70%. The scaffold's interface bet pays off now: every "Stubbed
(Lever 3)" cell in the scaffold report's STUBBED-vs-REAL table either
becomes a small targeted patch or graduates to a v0.5 follow-on.

The rotating-axis prototype moves from **Year 2** to **2-3 days of
focused work after v1 lands and validates**. Concretely: first end-to-end
dialectic demo on the v1 checkpoint by **2026-05-08**, four days from
today.

The shift is justified by three things, only one of which was visible in
the original Year 2 framing:

1. **The compiler grammar gap is smaller than the scaffold report
   claims.** Verified empirically against
   `api/notation/compile_expression`:
   `^3^P|⟨A,f,T⟩` compiles `valid=True`, `^3^P|<A,f,T>` (ASCII) compiles
   `valid=True`, `^3^P|A + ^3^P|f` compiles `valid=True`,
   `^8^E_{F6} = Ω` compiles `valid=True`. Only `meta: ^8^E_{F6} = Ω` fails
   (`parsing@4: unexpected token ':'`). The set-spec form is already
   admitted by the lexer (`UNICODE_LANGLE = "⟨"` is recognized; the
   ASCII-bracket form parses through the angle-bracket fallback in the
   tuple/phi rules). The scaffold note `"set_spec |<...> form not yet in
   compiler grammar"` in `attractor._score_admissibility` is stale.
2. **The predictor exposes per-head logits dictionaries by
   construction.** `predict_cas._decode_outputs` consumes
   `outputs["noetic_logits"][0].argmax()` — the per-head logits already
   exist in the forward pass and are simply argmaxed on the way out.
   Exposing a `forward_logits` method that returns the full
   `outputs` dict is a 5-line addition.
3. **The constrained-sampling pattern in
   `cas_native.inference.constrained_sampling` is the directly reusable
   logits-bias mechanism.** It implements logit masks and biases for
   structured-token decoding; per-axis priming is a strict subset of
   that pattern (one-hot or distance-weighted bias on a single head's
   logits).

What stays Year 2: a learned query→rotation classifier, a learned
attractor quality scorer, and multi-turn integration with Phase 2 DST.
Those are not gated on the same tight loop and don't pay off until the
v1 predictor is operating in conversational mode.

---

## 2. What "real implementation" means (vs. scaffold)

The scaffold is plumbing. Three things are stubbed:

### 2.1 Logits-level axis priming

**Status today.** `instance.py:CASInstance.predict` records the
`AxisPriming` envelope in the prediction trace
(`InstancePrediction.priming_applied`) and adds a `priming-stubbed:` note
to `notes`. The model returns the same prediction regardless of priming.
Two-instance dialog therefore **degenerates to fallback** (instances
agree, integration is a no-op), which is why every smoke-test attractor
in the scaffold report shows `kind=fallback`.

**Real implementation.** Modify the per-head logits before argmax. The
lightest-touch real priming is an additive bias on the logits row
corresponding to the primed Noetic / Drive / Domain / Register, with
strength controlled by a `bias` field on `AxisPriming` (already
defined). The argmax is then taken on the modified logits, producing
**different per-head outputs under inverted primings** when the prior
distribution is not too sharp.

This is not the most expressive intervention possible — temperature
modulation, top-p restriction, or full prior renormalization would all
be reasonable upgrades — but additive logit bias is what the
constrained-sampling module already does, and it is the minimum viable
priming.

### 2.2 Real CAS-compiler-based admissibility

**Status today.** `attractor._score_admissibility` calls
`compile_expression` and checks `artifact.valid`. The known failure
modes per the scaffold report are: (a) `meta:` prefix is renderer-only,
not compiler-grammar; (b) `|<...>` set-spec form is "not yet in compiler
grammar."

**Empirical verification (2026-05-04, this revision).** Only (a) is
real. The set-spec form is already admitted; the scaffold's note is
out of date. The `meta:` prefix is the single grammar gap, and it is
trivially handled by stripping the prefix before passing to the
compiler — either at the renderer (emit a compiler-stripped variant
alongside the human-readable string) or at the scaffold's
admissibility scorer (regex-strip `^meta:\s*` before
`compile_expression`). One-line patch in either location.

**Real implementation.** Add the strip in
`attractor._score_admissibility`:

- Before the existing `compile_expression(candidate)` call, normalize
  `candidate` by stripping a leading `meta:\s*`.
- Optionally: also strip authority annotations `[blocked]` /
  `[admitted]` if those ever leak into the rendered string.
- Tighten the scaffold's stale set-spec note (delete it).

Once this is in, admissibility scores stop being uniformly 0.0 on
meta-logic attractors, the composite scoring becomes meaningful, and
`select_top_attractors` actually has signal to choose between
candidates.

### 2.3 Adaptive (learned) query→rotation classifier

**Status today.** `rotator.select_rotations` is rule-based: it inspects
the `rewrite_shim` axis-detection signal and prioritizes the matching
rotation library.

**Defer to v0.5.** Rule-based selection is not the bottleneck for the
prototype. The bottleneck is whether priming is real. If priming is
real and the rule-based selector still produces structurally distinct
attractors on enough rotations, the v0 prototype is healthy. If
priming is real but rule-based selection is funneling everything to one
library, that diagnosis is itself a finding, and we move to a learned
classifier in the v0.5 cycle (~1-2 weeks after v0).

The learned classifier is gated on the v0 priming patch landing because
the training data (`(query, best_rotation)` pairs from a brute-force
all-rotations sweep) cannot be generated until rotations actually
produce different attractors.

---

## 3. Three deliverables for the real prototype

| # | What | Time | Files |
|---|------|------|-------|
| **D1** | Logits-level priming: real per-head logit bias from `AxisPriming` | 1-2 days | `cas-native/dialectic/instance.py` (modify body of `CASInstance.predict`); `cas-native/inference/predict_cas.py` (extend `Predictor` with `forward_logits` returning the full `outputs` dict; thread an optional `priming` argument that applies an additive bias before the argmaxes); cross-reference `cas-native/inference/constrained_sampling.py` for the bias pattern |
| **D2** | Compiler-admissibility patch: strip `meta:` prefix and any authority-annotation noise; delete stale set-spec note | 0.5 day | `cas-native/dialectic/attractor.py` (modify `_score_admissibility` to normalize candidate before `compile_expression`); optional: `cas-native/inference/cas_renderer.py` (emit a `_compiler_stripped` variant on the prediction dict so all downstream consumers are consistent) |
| **D3** | End-to-end smoke on v1 checkpoint: orchestrator vs. v1 predictor on 20 representative prompts (mix of `v74_baseline`, `v75_register`, `v76_production`, `v77_omega`, `v77_rule_four`, `meta_logic` buckets); structurally-distinct-attractor verdict | 0.5 day | `cas-native/dialectic/tests/test_v1_integration.py` (new); fixture pulls 20 prompts from the v77-relabeled eval (`level3_recoverable_eval_1000_v77_relabeled.jsonl`) — note the `_v77_relabeled` suffix per the eval-file-slip memory |

**Total: 2.5-3.5 days of focused work, parallelizable on D1 and D2.**

D2 is dramatically smaller than the scaffold report's 2-3 day estimate
because the scaffold report assumed grammar work that the compiler has
already shipped. The real D2 is a one-line strip plus stale-note
cleanup.

D1 is the only deliverable that touches the predictor surface, and it
remains the load-bearing one — if priming doesn't actually modify
predictions, none of the rest of the architecture matters.

D3 is the single PASS/HALF-PASS/FAIL gate (Section 4 below).

---

## 4. Pre-committed pass/fail

The prototype is intentionally cheap to build and intentionally easy to
falsify. The pass/fail gate is fixed before D3 runs:

- **PASS — ≥3 of 4 axis rotations produce structurally distinct
  integrated attractors** on the 20-prompt test set. Distinctness is
  measured on the integrated CAS expression: same Noetic AND same
  domain AND same drive AND same register-mode = identical; any axis
  difference = distinct. The test asserts that for each rotation, A's
  prediction and B's prediction differ on at least one axis on at
  least 50% of the prompts where the relevant rotation is selected.
- **HALF-PASS — 2 of 4** axis rotations meet the distinctness bar.
  Diagnosis: priming is partially effective (e.g., works on Noetic
  argmax but the prior is too sharp on Drive). Path forward: temperature
  modulation upgrade in D1.5 (~1 day).
- **FAIL — ≤1 of 4** axis rotations meet the distinctness bar.
  Diagnosis: additive bias is not a strong enough lever; the predictor
  is too confident on its argmax for the bias magnitudes available.
  Path forward: deeper architectural intervention — full prior
  renormalization on the head, or a constrained-sampling variant that
  forces the argmax to flip. This is the only branch that bumps the
  prototype back into multi-week territory; we identify it on day 3,
  not month 12.

This pass/fail is committed before D3 runs. No moving the goalposts.

---

## 5. The first demoable use case

What does a user see? The dialectic surfaces as a **trace that explains
the final answer**, not as the user-facing dialog itself. The trace is
optional, off-by-default, and renders only when the user asks "show
your work" or when CAS-Native runs in diagnostic mode.

```
USER: I keep practicing the same scale every day, but it feels off.

DIALECTIC TRACE:
  Round 1 — Noetic involution (^7 vs ^3):
    Instance A (^7-primed): "^7^O_{F6}|E — embodied rhythm,
                              structure-driven"
    Instance B (^3-primed): "^3^E_{F2}|f — felt aversion,
                              wisdom-driven"
    Integrated: ^7^O|E + ^3^E|f
                (co-presence, NOT cross-register integration; ≠ Ω)
  Round 2 — Drive inversion (F2 vs F5):
    Instance A (F2-primed): "^9^E_{F2}|f — knowledge-recall failure"
    Instance B (F5-primed): "^9^E_{F5}|f — agency-block failure"
    Integrated: 2 plausible Ω candidates
  Round 3 — selected by attractor scorer:
    Selected: Round 1's co-presence
              (highest substance + relevance to query)

CAS-NATIVE: Reading this as `^7^O_{F6}|E + ^3^E|f` — the rhythm is
            intact, but felt aversion has surfaced on top of it. The
            repetition itself is no longer producing the resonance it
            once did. Want to look at why?
```

Three observations on this rendering:

- The integrated expression honors **CAS v7.7 Clarification 10**
  operator discipline: `+` for co-presence (manifestations remain
  distinct), not `×` (which would require an explicit named emergent
  result `Ω`). The scaffold's `attractor.integrate_predictions` already
  encodes this discipline; D1 + D2 are what make it visible in
  user-facing output.
- The rotation trace is the load-bearing differentiator vs. existing
  multi-agent debate systems (Du et al. 2023, etc.). Other systems run
  unstructured-text debate; the dialectic runs **structured axis
  oppositions and integrates via CAS notation**.
- The user-facing reply is a single coherent sentence. The trace is
  optional. The product surface is not "show me four agents arguing";
  the product surface is **"give me a structurally honest read of my
  cognitive state, with the dialog visible if I ask."**

---

## 6. Sequencing relative to other v1 follow-ons

Tonight's parallel agents (per session 53 changelog):

- **Mode 7 network tracer (design + scaffold)** — complementary. The
  dialectic's `rotation_trace` is exactly the kind of attention-network
  surface Mode 7 traces. The two artifacts share infrastructure: each
  per-rotation `InstancePrediction` carries a per-head logits snapshot
  (after D1) that Mode 7 can ingest as one of its trace inputs.
- **Idea Atlas (design + scaffold)** — complementary. The dialectic's
  attractor scoring rubric (`substance / relevance / admissibility /
  invariant_balance`) is a candidate signal for what's "lit up" in the
  atlas at a given moment. The atlas's spatial layout could in turn
  inform the dialectic's `_score_relevance` heuristic (move from
  rewrite_shim axis match to a learned spatial-proximity score in
  v0.5).
- **Open-domain Q&A (design only)** — orthogonal. Q&A needs a
  generative head (Phase 2 NL Generation Head per
  `project_version_b_conversational_plan`); the dialectic needs the
  predictor only. They don't compete for engineering hours through
  the v0 dialectic build.

Recommended order:

1. **2026-05-05 ~03:00 PDT** — v1 retrain validates. Free-form
   coverage check (target ≥60%) is the gate; if it doesn't clear,
   dialectic prototype slips to wait for v2.
2. **2026-05-05 to 2026-05-06** — Mode 7 + Idea Atlas + open-domain QA
   design specs land. These are design-side; they don't block D1/D2.
3. **2026-05-06 to 2026-05-07** — Dialectic D1 + D2 (parallel). D1 on
   the predictor side, D2 on the scaffold side. They touch disjoint
   files.
4. **2026-05-08** — Dialectic D3 (v1 integration smoke test). Pass/fail
   gate runs.
5. **2026-05-08 EOD** — First dialectic demo on v1 checkpoint, with the
   trace rendering above. Demoable to user, not yet shippable to
   customers.

Total elapsed: 4 days from this revision; 3 days of dialectic work
inside that window.

---

## 7. Long-term vs. near-term framing

The user's clarification is correct: **Year 2 was overly conservative**
for the prototype. The Year 2 framing assumed both (a) the predictor
would not be at usable structural-output accuracy until well into
training Phase 2 of the conversational plan, and (b) the compiler
grammar would need real extension work. Neither is true today: (a) is
being addressed by the Lever 3 retrain landing tonight, and (b) is
already shipped (only the `meta:` prefix-strip remains, which is a
one-line scaffold patch).

**Real near-term (this week).**

- v0 prototype shipping: 2026-05-08.
- 20-prompt v1-checkpoint smoke verdict: PASS / HALF-PASS / FAIL with
  the gate pre-committed in Section 4.
- Trace rendering visible on at least one demoable interaction.

**Real Year 2 territory (still Year 2, no change).**

- **Learned query→rotation classifier.** Replaces the rule-based
  `select_rotations`. Gated on D1 producing varying predictions per
  priming, plus a brute-force all-rotations dataset on a substantial
  eval slice. Estimate: 3-5 days of work, but **scheduled** for after
  the v0 prototype demos and validates.
- **Real attractor quality scoring.** The four sub-scorers in
  `attractor.py` (`_score_substance`, `_score_relevance`,
  `_score_admissibility`, `_score_invariant_balance`) are
  heuristic-with-real-bones today. A learned scorer trained on
  user-rated attractor quality would replace the heuristics. Gated on
  collecting user-rated data, which requires shipping v0 first.
- **Multi-instance × multi-turn integration.** When Phase 2 DST goes
  live (per `phase2_dst_spec_2026_05_04.md`), the dialectic extends
  from single-turn rotation to multi-turn rotation across a coherent
  dialog. This is genuine Year 2 work and not in scope for the v0
  prototype.
- **Replacing the rule-based selector with the rule-based selector +
  learned veto stage.** Already noted in the scaffold report as a
  useful intermediate; deferred until the v0 prototype's rotation
  selection emerges as a measurable bottleneck.

The Year 2 plan was not wrong; it was sized to the wrong baseline. Now
that the baseline is moving, the prototype rides the predictor uplift
into near-term shippable territory, and the genuinely hard pieces
(learned classifier, learned scorer, multi-turn) stay correctly placed
where the underlying system is mature enough to support them.

---

## Appendix: residual risks

- **Risk: priming is too weak.** Additive logit bias against a sharply
  peaked prior produces no behavior change. Mitigation: D1 includes a
  bias-magnitude sweep (e.g., `noetic_bias_strength ∈ {1.0, 2.0, 5.0,
  10.0}`) on the smoke test; if no value flips the argmax on a
  representative prompt, escalate to temperature modulation in D1.5.
- **Risk: v1 retrain underperforms.** If free-form coverage lands below
  ~50%, multi-instance dialog remains noise per the original Year 2
  diagnosis. Mitigation: the gate at step 1 of the sequencing in
  Section 6 is a hard stop; if v1 doesn't clear, the dialectic
  prototype slips to v2 without re-doing D1/D2 work — both deliverables
  are predictor-version-agnostic.
- **Risk: structurally-distinct-attractor verdict is gameable.** The
  distinctness criterion (any-axis difference = distinct) is permissive.
  If D3 reports PASS but the user-facing dialog still feels redundant,
  we tighten the criterion to require admissible + structurally-balanced
  distinct attractors. This is a v0.5 refinement, not a v0 blocker.
- **Risk: the `meta:` prefix-strip changes downstream behavior.** Some
  scoring or rendering code may assume the prefix is present.
  Mitigation: D2 grep verifies that all consumers either strip
  themselves or accept stripped input. The single source of truth is
  the rendered prediction dict; the strip is an admissibility-time
  normalization, not a renderer change.

---

End of revision document.
