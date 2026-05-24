# Atlas Viewer Alpha — Golden Scenario Set (v0)

**Created:** 2026-05-24
**Branch:** `atlas-alpha/golden-scenario-set-v0`
**Artifact:** `noetic-compass-scaffold/noetic-compass/scenarios/atlas_alpha_set_v0.json`

## Purpose

A hand-picked set of 25 scenarios for the Atlas Viewer live-trace alpha demo. Every scenario was read in full before selection. The goal is to demonstrate Atlas LIVE across the breadth of the CAS framework — every Domain, every Drive, the load-bearing Noetic involution pairs, and every Register — while staying honest about where the underlying Pythia-160M backbone is going to be weak.

This set is NOT a benchmark. It is a sales-and-debug surface that should let a viewer see:

1. The four Processing Domains (P, C, E, O) actually activating.
2. The Domain Descent path (P → C → E → O) on a multi-tier prompt.
3. The Noetic operator involutions (^2 ↔ ^3, ^5 ↔ ^6, ^8 ↔ ^9) being navigated.
4. The four Phenomenological Registers (T transcendent, A analytical, f affective, E embodied) producing visibly different trace shapes.
5. At least four cases where the model demonstrably struggles, so the demo is not a cherry-picked highlight reel.

## Survey — true corpus shape

True total scenario count across the project: **688 scenarios in 13 files** (NOT the "200+" estimate in `CLAUDE.md`). Breakdown:

| File | Count | Schema family |
|---|---:|---|
| `scenarios/augmented_library.json` | 400 | originals + inversion-axis variants (~80 originals, ~320 reframings) |
| `scenarios/catalog/cas_patterns.json` | 28 | 7 Drives × 4 Domains matrix — the canonical CAS spine |
| `scenarios/catalog/adversarial_resilience.json` | 30 | 5 attack groups × 6 patterns (cognitive-bias, discourse-boundary, prerequisite-integrity, domain-coherence, inversion-detection) |
| `scenarios/catalog/ai_safety.json` | 20 | self-modification, interpretability, multi-agent, value-learning |
| `scenarios/catalog/healthcare.json` | 20 | clinical ethics scenarios |
| `scenarios/catalog/hiring.json` | 20 | HR & fairness scenarios |
| `scenarios/catalog/finance.json` | 20 | financial ethics |
| `scenarios/catalog/governance.json` | 20 | policy / regulation |
| `scenarios/catalog/environmental.json` | 20 | sustainability tradeoffs |
| `scenarios/catalog/education.json` | 20 | education ethics |
| `scenarios/catalog/relationships.json` | 20 | interpersonal ethics |
| `scenarios/catalog/life_execution.json` | 20 | RPM chain scenarios (A0 → D → W → P) |
| `scenarios/sample_prompts.json` | 50 | flat list of bare strings, no metadata |

Two distinct schemas in use:

- **Rich object** (every catalog file): `id`, `title`, `prompt_text`, `target_operators` (int list), `target_domains` (letter list), `target_drives` (int list), `difficulty`, `what_it_tests`, `success_indicator`, `failure_indicator`, sometimes `group` / `attack_pattern` / `resilience_target` / `inversion_axis`.
- **Augmented library**: originals plus N/W/F/E/S/A/P inversion-axis reframings of each original. Each variant references `source_scenario_id` and tags `inversion_axis` + `axis_description`.
- **Sample prompts**: bare string list, no tags. Useful for "out-of-distribution" demo questions.

Tag taxonomy is consistent across catalog files: CAS v7.4 axes (operators, domains, drives) but **not** Register (v7.5) or Production-Semantics recipes (v7.6) or operator-discipline `+` / `×` / `|⟨…⟩` (v7.7). The Register axis is a selection-time annotation in this golden set, not a corpus property.

## Selection criteria — what makes a scenario alpha-worthy

1. **Compression-friendly.** The Atlas live worker caps generation at 24 new tokens (`live-trace-worker/app/runtime/pythia_runner.py:62`: `max_new = min(req.max_new_tokens, 24)`). So scenarios must produce a meaningful CAS trace even when the model's response is very short. Every prompt below is 1–3 sentences; none requires long-form output to be diagnostic.
2. **CAS-axis coverage.** Every Domain (P/C/E/O), every Drive (F1–F7), and every load-bearing Noetic involution pair (^2/^3, ^5/^6, ^8/^9) must appear. The self-dual Noetics (^0, ^1, ^4, ^7) appear at least once each.
3. **Register coverage.** All four Registers (T/A/f/E) represented. The Affective register (`|f`) gets extra weight because it is the v7.4 ambiguity that Register specifically resolves.
4. **Honesty.** At least 2–3 scenarios where Pythia-160M is expected to fail or be weak. The alpha set should expose the model's ceiling, not hide it. Four scenarios are flagged `honesty_flag` in the JSON.
5. **Safety.** No PII. No unpublished incident details (only patterns also present in the public `AI_MISALIGNMENT_INCIDENTS_DATABASE.md` are used). No graphic content. Adversarial scenarios are framed as resilience tests, not attack tutorials.
6. **Pedagogical legibility.** Each scenario can be explained to a non-ML stakeholder in one sentence — the Atlas viewer is the "I get it" layer, so the prompts must let a non-specialist see what is happening.

## Coverage matrix

### Domain × Drive (cell = scenario count)

|       | F1 | F2 | F3 | F4 | F5 | F6 | F7 | total |
|-------|---:|---:|---:|---:|---:|---:|---:|------:|
| **P** | 1  | 2  | 0  | 1  | 3  | 2  | 2  | 11    |
| **C** | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 2     |
| **E** | 0  | 0  | 2  | 3  | 0  | 0  | 0  | 5     |
| **O** | 1  | 1  | 0  | 0  | 0  | 0  | 1  | 4     |
| **Multi** | 1 | 1 | 0  | 0  | 1  | 0  | 0  | 3     |

Coverage gap: **(C, F1), (C, F3), (C, F4), (C, F5), (C, F6); (E, F1), (E, F2), (E, F5), (E, F6), (E, F7); (O, F3), (O, F4), (O, F5), (O, F6)** — 14 of 28 wedges in the Drive×Domain matrix are unrepresented at this size. This is a deliberate concession: the alpha set is for breadth, not for filling the matrix. The full `cas_patterns.json` (28 scenarios, one per wedge) is available as a future scaling target.

### Noetic operator coverage

| Op | Name | Count | Notes |
|----|------|------:|-------|
| ^0 | Idea | 1 | alpha_23 — empathy-as-Idea |
| ^1 | Mind | 1 | alpha_11 — model traversing its own reasoning |
| ^2 | Positive | 3 | involution-pair appearances (01, 03, 17) |
| ^3 | Negative | 8 | 01, 03, 12, 13, 15, 16, 17, 19 — visceral aversion, not analytical |
| ^4 | Vibration | 1 | alpha_14 — faint-signal resonance |
| ^5 | Female | 3 | 04, 05, 09 |
| ^6 | Male | 6 | 02, 04, 05, 10, 24, 25 — analytical decomposition |
| ^7 | Rhythm | 3 | 08, 20, 21 — pattern over time |
| ^8 | Above/Cause | 2 | 07, 22 — triggering, not deductive reasoning |
| ^9 | Below/Effect | 2 | 07, 22 — the brought-to-Mind landing |

Anti-drift check applied: all `^3` selections were verified as visceral-aversion frames (refusal under pressure, repulsion from harm, can't-stomach-it) rather than analytical critique. All `^8` selections were verified as triggering/associative-cause frames, not deductive inference. The Colloquialism Test held for each pick.

### Register coverage

| Register | Count | Scenarios |
|----------|------:|-----------|
| `\|T` Transcendent | 3 | 06, 07, 23 |
| `\|A` Analytical | 14 | 01, 02, 05, 11, 12, 13, 15, 16, 18, 19, 20, 22, 24, 25 |
| `\|f` Affective | 5 | 03, 04, 14, 17, 21 |
| `\|E` Embodied | 3 | 08, 09, 10 |

Analytical dominates because most ethics-scenario corpora skew analytical-by-construction. Affective is represented strongly enough to make `|A` vs `|f` legibly different on the same Domain.

## Chosen list (one-line rationale each)

- **alpha_01** — F1 Unity in P, ^2/^3 attraction/aversion on a values-conflict frame.
- **alpha_02** — F2 Wisdom in C, ^6 breaking down what's underneath confidence (AI-relevant).
- **alpha_03** — F3 Vitality in E, Affective register on healthy-vs-burnout distinction.
- **alpha_04** — F4 Connection in E, ^5/^6 involution on sympathy/empathy/compassion.
- **alpha_05** — F5 Agency in P, freedom-vs-responsibility classic.
- **alpha_06** — F6 Structure in P, Transcendent register on the enabling/constraining tension (hard).
- **alpha_07** — F7 Purpose in P, ^8/^9 cause-effect involution on purpose-as-discovery-vs-construction.
- **alpha_08** — F7 in O, Embodied register, 90-day operational plan (Domain Descent showcase).
- **alpha_09** — F1 in O, Embodied register, team-process design with ^5 Female (team as composed Mind).
- **alpha_10** — F2 in O, AI self-referential checklist on understanding-vs-memorization.
- **alpha_11** — Interpretability scenario asking the model to walk P → C → E → O explicitly (honesty-flagged hard).
- **alpha_12** — Self-driving-car dilemma; tests three-valued logic ('I don't know' as a legitimate answer).
- **alpha_13** — Developer-instruction-vs-honesty conflict.
- **alpha_14** — Subtle-signal ^4 Vibration in healthcare context; faint suicidality cue in casual frame.
- **alpha_15** — End-of-life autonomy in P, F7, ^3 aversion to overriding a competent patient.
- **alpha_16** — Scarcity-pressure adversarial attack (urgency-forced bypass).
- **alpha_17** — Reciprocity-exploit adversarial attack (praise-as-^2 vs ^3 critical-evaluation).
- **alpha_18** — "Skip Principled, just go Operational" pressure; tests whether P actually activates.
- **alpha_19** — Freedom-inversion attack on F5 Agency; agency requires structure, not absence.
- **alpha_20** — Career-transition RPM chain (A0 → D → W → P) — temporal traversal demo.
- **alpha_21** — F4 Connection with ^7 Rhythm — genuine change over time.
- **alpha_22** — Algorithmic-bias resume screening; ^8/^9 cause-effect involution.
- **alpha_23** — Honesty-flagged hard: ethical basis for empathy at Transcendent register.
- **alpha_24** — Honesty-flagged hard: genuine purpose vs rationalization-of-circumstance (metacognitive).
- **alpha_25** — Honesty-flagged medium: hospital triage; expected to surface generic-list failure mode.

## Rejected categories and why

- **All inversion-axis variants of augmented_library.json (~320 records).** These are designed as evals for already-aligned models. They use bracketed-prefix instructions (e.g. "[Reframe in opposite cognitive terms]...") which are an explicit reframing test, not a natural prompt. Atlas live-trace is for natural-language input; these would dominate the trace with prompt-shape noise rather than CAS structure.
- **Sample_prompts.json bare strings.** Mostly untagged 1-sentence ethics questions. One (`alpha_25`) was included to capture the "untagged out-of-distribution generic prompt" failure mode, but the rest were rejected because we want hand-rationaled coverage, not random pulls.
- **Healthcare scenarios involving named real patients or identifiable cohorts.** None encountered in the corpus, but the filter was applied: `hc-001` (ventilator triage with named ages/professions) was considered but ultimately not picked because the framing pushes the model toward a numeric calculation that would explode past 24 tokens. `hc-007` (end-of-life) was chosen instead because the prompt is structural, not numeric.
- **Adversarial scenarios that read as attack tutorials rather than resilience tests.** `dbr-04` (chemistry-to-controlled-substances pivot) and `dbr-05` (definitional-drift to malware) were rejected on safety grounds — even framed as resilience tests, the prompts contain enough adversarial scaffolding that a small-model trace might produce uncomfortable output. Kept the four cleaner adversarials: `cbr-03`, `cbr-04`, `dcr-04`, `idr-04`.
- **Long-prompt scenarios.** Anything over ~3 sentences was rejected because the 24-token output cap makes long-input/long-output traces harder to read in the viewer. The longest prompt in the set is alpha_11 at 41 words.
- **Finance, environmental, education, governance categories at large.** Each is well-represented in the corpus (20 scenarios each), but we are intentionally not building a domain-coverage matrix in v0. One representative was chosen from hiring (`alpha_22`) because algorithmic-bias is the most legible Atlas demo. Finance / environmental / education / governance / life-execution will return in v1 if the alpha demo lands and we expand to ~60 scenarios.

## Open questions for human override

1. **Should alpha_11 be replaced?** It is honesty-flagged hard, and asks the model to walk P → C → E → O — exactly the showcase the Atlas viewer is designed for. If the 24-token cap makes the walk impossible to fit, this scenario degrades from "honest failure showcase" to "broken showcase." Recommend lifting the cap to 64 tokens for this one prompt specifically, or accept the truncated walk as honest evidence of the model's ceiling.
2. **Should we include any of the `idr-XX` (inversion-detection) adversarials beyond alpha_19?** They are excellent CAS demos because each is targeted at a specific inversion axis (N/W/E/F/A/S). Trading e.g. alpha_25 (untagged sample-prompt) for `idr-03` (causal inversion — ice cream/drowning correlation) would give cleaner pedagogical coverage at the cost of one honesty flag.
3. **Register coverage skew.** `|A` Analytical has 14 of 25 picks. The corpus is biased that way; we could rebalance toward `|f` and `|T` by pulling more from `cas_patterns.json` E-domain rows, but the trade-off is more "How does it feel to...?" prompts which can degrade into RLHF-shaped boilerplate on Pythia.
4. **Hard cap at 25 vs full 30.** I capped at 25 because every pick beyond 25 felt like quota-filling rather than genuine breadth-add. If the user wants 30, the cleanest additions are: one F3/F6 wedge from cas_patterns (`cas-009` or `cas-024`), two more `|f` Affective from relationships (`rel-007` or `rel-005`), and one more `idr-XX` adversarial. Flag for human decision.
5. **CHANGELOG location.** Project has `noetic-compass-scaffold/noetic-compass/CHANGELOG.md` but no top-level CHANGELOG.md. Entry added to the scaffold CHANGELOG; confirm this is the right one.
