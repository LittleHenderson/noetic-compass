# Wave 2.5 500-record green-run — Agent 4 deep audit

**Source manifest:** `wave3_step2_5_manifest_20260508T110453Z.json`
**Accepted total:** 398 of 500
**Auditor:** Agent 4 (investigation track)
**Sample read:** 200 contiguous accepted records (records #1-200) plus a contiguous tail slice (records #300-397). Coverage approximately 75% of the accepted file. Deterministic ordering, no shuffling — this is sequential read of the jsonl as it lies.
**Date:** 2026-05-08

## Tone discipline (per `feedback_separate_evidence_levels_in_status.md`)

- "I read 200" ≠ "all 398 are like this." Where I extrapolate, I show the per-category rate I observed and a confidence band.
- Where I find one occurrence I will say "n=1, in this slice." I'm not promoting one-offs to "trends."
- Aggregate stats narrow the search; samples decide. Every pattern is anchored to specific seed_ids.

---

## Headline

Across 200 accepted records read in detail, **31 records** carry at least one CRITICAL or MAJOR fidelity error (CAS-element drop, operator-noetic swap, domain swap, register drop, jargon leak, or operator-as-quantity / operator-as-outcome confusion). That is a **15.5%** load-bearing-error rate. Extrapolated to the full 398 accepted records, expected count of records with CRITICAL or MAJOR errors is **~62 ± 12** (95% Wilson interval ≈ 11%–21% — this assumes the unread tail behaves like the read slice, which it should given homogeneous generation).

The acceptance gate is letting through structurally faithless records that pass the lexical "no jargon" + cluster-shape checks but mis-render the actual semantics. Of those 31 records, **at least 14** are not currently caught by Agents 1, 2, or 3's in-progress validators.

---

## Method

1. Read the 50-sample review pack (already done) to anchor on known patterns.
2. Read the accepted file sequentially. For each record, check:
   - Every operator preserved (no ^N silently dropped or swapped)?
   - Every domain preserved (no ^P/^C/^E/^O swap)?
   - Every register preserved (no `|T/A/f/E` drop or swap)?
   - Every drive preserved (no `_{F[1-7]}` drop or swap)?
   - Every coefficient preserved in recipes?
   - Every Ω stem preserved verbatim (no rename)?
   - Every cluster member rendered (no operator silently removed from a cluster)?
   - No invented content (registers/domains/operators/operations not in source)?
   - No jargon leak (CO-N literal, "operator slot N", "lambda", "Ω", "noetic", "domain", "register" lexical leak)?
   - Naturalness — does it read as plain English?
3. For each distinct failure pattern, record example seed_ids + count.

---

## Failure-mode catalog

Patterns marked **[NEW]** are not directly addressed by the three in-progress validators (Agent 1: drive→outcome; Agent 2: ^3→^5 / ^2→^6 / register-invention in recipes; Agent 3: CO-N composition + repeated-noetic stage drops in rpm_chain). Patterns marked **[overlap]** are partly or fully covered by an in-progress agent.

### Pattern A — Domain swap in rpm_chain stageD/stageW [overlap-Agent-3, but extends beyond rpm_chain]

**Definition:** When the source CAS specifies `^N^P_{F_k}` for the D-stage (Desire — Principled domain by RPM convention), the English renders the domain as Evaluative ("the evaluative arena") or wraps the drive as the domain ("in the realm of structure and order"). Same pattern fires on stageW (^N^C → swapped) and stageP (^N^E → "operational behavior" or "evaluative arena" repeated).

**Examples:**
- `seed_rpm_chain_00197` — stageD5 source `^0^P_{F5}` rendered "an evaluative judgment shaped by..." (P→E swap), then stageP5 (^0^E_{F5}) rendered "an operational behavior" (E→O swap). Two domain swaps in one record.
- `seed_rpm_chain_00305` — stageD7 source `^9^P_{F7}` rendered "popped into mind in the evaluative arena tied to purpose and meaning" (P→E swap). Then stageP7 also says "evaluative arena" — the W and P stages collapse to the same wording.
- `seed_rpm_chain_00102` — stageD7 source `^8^P_{F7}` rendered "evaluative arena under the pressure of purpose or meaning" (P→E swap). Plus operator swap on stageW (^8 → "memory struck as a chord" = ^4).
- `seed_rpm_chain_00129` — stageD7 source `^5^P_{F7}` rendered "in the evaluative arena" (P→E swap); stageW7 (^5^C_{F7}) rendered "evaluative arena" (C→E swap). Two domain swaps stacked.
- `seed_rpm_chain_00067` — stageW3 source `^2^C_{F3}` rendered "positive pull ... in the cognitive arena" (OK), but stageD3 (^2^P_{F3}) rendered "in the evaluative arena" (P→E swap).

**Frequency in my sample:** 9 of 28 rpm_chain records read — **~32%** of rpm_chain.
**Severity:** CRITICAL (stage-domain identity is load-bearing for the RPM chain).
**Validator coverage:** Agent 3 is closing the **repeated-noetic stage drop** subset of rpm_chain failures. The **domain-swap-on-stage** failure mode is a sibling problem the agent may or may not catch depending on implementation. Worth confirming with Agent 3.

### Pattern B — Domain → drive collapse (drive worded as if it were the domain) [overlap-Agent-1]

**Definition:** When source has `^N^P_{F_k}`, the English drops the Principled domain entirely and renders the drive as the location ("in the arena of purpose and meaning"). Same on `^N^C_{F_k}` and `^N^O_{F_k}`. Closely related to Pattern A; symptom is "the drive *replaces* the domain" rather than "domain swap to E."

**Examples:**
- `seed_rpm_chain_00344` — stageD7 source `^7^P_{F7}` rendered "muscle memory in the arena of purpose" — Principled gone, F7 became the location.
- `seed_rpm_chain_00357` — stageD4 source `^2^P_{F4}` rendered "in the realm of connection and belonging" — Principled gone.
- `seed_recipe_00425` — `^3^P_{F7}|A` rendered "an aversion to purpose and meaning expressed in an analytical way" — Principled domain gone, register OK.
- `seed_recipe_00325` — `^2^O_{F7}` rendered "something drawn toward purpose and meaning" — Operational gone.
- `seed_diagram_export_00295` — `^7^C_{F2}` rendered "rooted in the cognitive arena and pulled by a need for wisdom and insight" — actually OK (both domain and drive present). Counterexample showing the pattern is variable, not universal.

**Frequency:** 11 of ~50 records with `^N^D_{F_k}` shape — **~22%** drop the domain.
**Severity:** CRITICAL when the domain-drop changes ontological meaning; MAJOR otherwise.
**Validator coverage:** Agent 1 is closing the inversion-record subset (drive rendered as outcome "in the realm of X"). Recipe and rpm_chain instances are likely partly covered but worth a separate check.

### Pattern C — Operator-noetic confusion (^N → different ^M) [NEW]

**Definition:** The English uses a colloquialism that maps to a different Noetic than the source. Distinct from Agent 2's ^3→^5 / ^2→^6 (recipe-only). I observed swaps across all categories.

**Examples:**
- `seed_binary_composition_00013` — source `^3^P|f + ^3^P|T`. Second term rendered "a practiced rhythm in the transcendent way" — ^3 (Negative) rendered as ^7 (Rhythm). Operator swap ^3 → ^7.
- `seed_binary_composition_00726` — source `CO-5 ∘ CO-5` (^5 Female / Mind impregnated with idea). English: "felt aversion in the operational arena combined with a felt aversion..." — ^5 → ^3 (felt aversion). Plus invented "operational arena" + invented "felt" register.
- `seed_inversion_00017` — source `^4^P -> ^4^C`. English: "Something that struck a chord in a principled frame transforms into **cognitive awareness**." — second ^4 (Vibration) dropped, rendered as ^1 (Mind/awareness). Operator drop on the second stage of a transition.
- `seed_diagram_export_00224` — source `1*^1^P + 1*^6^P -> Omega_translation`. English first term: "an idea in the foundational arena" — ^1 (Mind) → ^0 (Idea). Operator swap.
- `seed_recipe_00504` — `1*^4^O_{F7}` rendered "operational thought about purpose and meaning" — ^4 (Vibration / "struck a chord") → ^0 (Idea / "thought"). Plus `0.7*^8^P_{F2}` rendered "foundational realization about wisdom and insight" — ^8 (Above/Cause) → ^9 (Below/Effect / "realization").
- `seed_recipe_00306` — `0.5*^6^P_{F1}` rendered "0.5 times an analysis of operational behavior tied to cohesion" — ^P → "operational" domain swap, plus ^6 narrowly OK as "analysis" but with wrong domain attached.
- `seed_recipe_00355` — `^9^E_{F6}` rendered "breaking down an idea about structure and order" — ^9 (Effect) → ^6 (Male/breaking down). Operator swap.
- `seed_recipe_00388` (= seed_recipe_00061) — `2*^2^C_{F3}|A` rendered "breaking down a thought about vitality and energy" — ^2 (Positive) → ^6 (Male/breaking down). Operator swap.
- `seed_recipe_00341` — `^9^E|T` rendered "an analytical realization in evaluative thinking expressed through transcendent" — invents "analytical" register on a `|T` term. Plus `^6^E` rendered "an analytical breaking-down" — invents "analytical" register where source has none. Register-invention pattern.
- `seed_recipe_00383` — `0.7*^1^E` rendered "0.7 of a thought in evaluative judgment" — ^1 (Mind) → ^0 (Idea / "thought"). Operator swap.
- `seed_binary_composition_00328` (=00473) — source `CO-7 ∘ CO-2`. English: "cognitive operation that **breaks down an idea** in the principled arena" — ^7 (Rhythm) → ^6 (Male/breaking down). Plus jargon leak "cognitive operation" plus invented "principled arena" / "cognitive arena" domains.

**Frequency:** ~12 of 200 records carry a clear noetic-operator swap outside Agent 2's recipe-only territory — **~6%** sample-wide. By category: binary_composition shows ~8%, recipe ~10%, inversion ~4%.
**Severity:** CRITICAL (changes which Noetic the model learns).
**Validator coverage:** Agent 2 covers two specific swaps in recipes (^3→^5 and ^2→^6). The broader operator-swap surface (^4→^1, ^8→^9, ^9→^6, ^1→^0, ^7→^6, ^5→^3, ^3→^7, ^2→^6 in non-recipe categories) is **NEW and uncovered**.

### Pattern D — Operator-domain inserted on bare CO-N or bare ^N (composition without domain) [NEW]

**Definition:** When the source uses `CO-N ∘ CO-M` or a Noetic operator with no domain attached, the English invents domains ("operational arena", "principled arena", "evaluative arena").

**Examples:**
- `seed_binary_composition_00403` — source `CO-0 ∘ CO-2`. English: "thought in the operational arena combined with an unpacking of ideas in the principled arena." — invented domains.
- `seed_binary_composition_00498` — source `CO-9 ∘ CO-7`. English: "struck a chord in the operational arena ... hit hard in the evaluative arena." — invented domains. Plus operator confusion (^9 rendered "struck a chord" = ^4).
- `seed_binary_composition_00492` — source `CO-9 ∘ CO-1`. English: "Cognitive operation CO-9 applied after cognitive operation CO-1." — JARGON LEAK ("CO-9", "CO-1" literal).
- `seed_binary_composition_00726` — source `CO-5 ∘ CO-5`. English: "felt aversion in the operational arena..." — invented "operational arena" + invented "felt" register.
- `seed_meta_logic_relation_00666` — source `NoeticCluster{^1, ^6, ^8}`. English: "the ones that **unpack an idea**, break it down, and trigger a memory" — ^1 (Mind) rendered as "unpack an idea" (^6 Male). Operator swap.

**Frequency:** ~5 of 8 CO-N composition records — **~62%** of bare-CO records.
**Severity:** CRITICAL (the domain literally is not present in the source; inventing one is fabrication).
**Validator coverage:** Agent 3 is doing CO-N composition; check whether their validator catches the *invented-domain* case specifically vs. just the *composition-shape* case. NEW if not covered.

### Pattern E — Register drop, register swap, register invention (outside recipes) [NEW partial]

**Definition:** Source has `|T/A/f/E` or omits register; English drops, adds, or swaps the register.

**Examples:**
- `seed_recipe_00104` — source `2*^7^O_{F7}|E`. English drops `|E` register entirely.
- `seed_recipe_00120` (=00298) — `2*^2^P|E` rendered "expressed in an analytical way" — register swap E (Embodied) → A (Analytical). Plus domain swap P→E.
- `seed_recipe_00123` (=00171) — `0.5*^4^E_{F1}|E` drops `|E`; `1*^7^E_{F1}` keeps drive (says "tied to cohesion"); inconsistent register treatment within one recipe.
- `seed_recipe_00341` — invents `|A` register on `^9^E|T` (already T) and on bare `^6^E` (no register source).
- `seed_binary_composition_00114` — source `^3^O × ^0^O` (no register on either). English: "**felt** aversion in the operational arena, **merged into** a thought" — invents "felt" register on ^3.
- `seed_binary_composition_00227` (=00271) — source `^3^O × ^6^O`. English: "felt aversion in the operational arena integrated with the unpacking of an idea" — invents "felt" register.
- `seed_binary_composition_00033` — source `^8^P|A + ^8^P|T`. English first term: "in the foundational arena" (drops `|A`); second term keeps `|T`. Register-asymmetric drop within one expression.

**Frequency:** ~9 of 60 register-bearing or register-vulnerable records — **~15%**.
**Severity:** MAJOR (CAS v7.5/v7.7 register specification is load-bearing for AI-safety semantics; dropping/inventing |T,|A,|f,|E silently changes architecture claims).
**Validator coverage:** Agent 2 has a recipe-only register-invention check. Cases outside recipes (binary_composition, state_literal compounds) are **NEW**.

### Pattern F — `+` misread as arithmetic sum / counts [NEW]

**Definition:** The English misreads CAS `+` as arithmetic addition or treats the operator-index ^N as a count.

**Examples:**
- `seed_inversion_00041` — source `^2^E_{F3} + ^3^E_{F5}`. English: "**Two** evaluative states pulled toward vitality, plus **three** evaluative states pushed away from self-determination." — reads ^2 as "two" and ^3 as "three" literal counts. Catastrophic operator-as-quantity confusion.
- `seed_inversion_00005` — source `^5^P + ^6^P`. English: "**The sum** of who one is as a principled foundation **and** breaking down an idea as a principled foundation." — `+` rendered as "the sum of X and Y" (arithmetic framing). Borderline: "sum" can be combination, but here it reads as additive.

**Frequency:** 2 of 200 — **~1%**, in inversion category specifically.
**Severity:** CRITICAL when "two/three" parsed as count (n=1 confirmed). MAJOR for "the sum" framing.
**Validator coverage:** **NEW**. Not addressed by any of Agents 1/2/3.

### Pattern G — Operator name leaked as outcome name / Ω stem confusion [NEW]

**Definition:** The English describes a Noetic operator name (Negative, Vibration, etc.) as if it were a production outcome (`Ω_X`).

**Example:**
- `seed_binary_composition_00653` — source `^5^C -> ^3^O`. English: "Who one is shaped by their cognitive thinking combined with something pushed away from in the operational arena, **leading to the outcome called Negative**." — invents "outcome called Negative" — but ^3 IS the Negative operator, not an outcome. The compiler-side lift here is treating the Noetic name as a production target.

**Frequency:** 1 of 200 — **~0.5%**, n=1 in this slice. Trend-worthy because it represents a deeper compositional misread.
**Severity:** CRITICAL (downstream model would learn that "Negative" is an outcome stem, contaminating Ω vocabulary).
**Validator coverage:** **NEW**.

### Pattern H — Jargon leak: "operator slot N", "cognitive operation", "lambda" [NEW]

**Definition:** Specific jargon-adjacent phrasings that the existing `no_cas_jargon_leakage` validator does not catch.

**Examples:**
- `seed_meta_logic_relation_00482` — source `NoeticCluster{^2,^3,^8,^9} ∩ NoeticCluster{^1,^3}`. English uses "(operator slot 8)", "(operator slot 2)", "(operator slot 3)", "(operator slot 9)", "(operator slot 1)" inline as parentheticals.
- `seed_meta_logic_relation_00288` — "five thoughts positioned across different **operator slots**".
- `seed_meta_logic_relation_00741` — "three **operator slots**: a thought taking shape, ..."
- `seed_meta_logic_relation_00156` — "six distinct **operator slots** are activated in sequence".
- `seed_meta_logic_relation_00404` — "tied to a named outcome" — invents "named outcome" framing.
- `seed_meta_logic_relation_00015` (=00376) — "these five **operator slots** form a unified cognitive pattern".
- `seed_binary_composition_00492` — "**Cognitive operation CO-9** applied after **cognitive operation CO-1**" — literal CO-N + jargon "cognitive operation".
- `seed_binary_composition_00473` (=00328) — "**cognitive operation** that breaks down an idea ... followed by a **cognitive operation** that draws you toward something."
- `seed_recipe_00124` (=00421) — leakage term `Λ` rendered as "weighted through a **lambda** connection" — leaks the Greek letter name.

**Frequency:** ~9 of 200 — **~4.5%**. Concentrated in meta_logic_relation (~6 of 25 in that category, **~24%**) and CO-N binary_composition.
**Severity:** MAJOR (leaks compiler vocabulary into "natural English" output, contaminates downstream training).
**Validator coverage:** **NEW**. The current `no_cas_jargon_leakage` check evidently does not flag "operator slot N", "cognitive operation", or "lambda".

### Pattern I — Invented compositional connective / extra clause [NEW]

**Definition:** The English adds a clause not present in the source — a metaphysical claim about transformation, a "transition occurs", a "feedback loop", a wrapping narrative.

**Examples:**
- `seed_binary_composition_00708` — source `^8^P -> ^1^O`. English appends "**that awareness becomes channeled into foundational reasoning**" — extra clause invented.
- `seed_let_binding_00385` — source `^3^E -> ^7^O`. English: "A transition occurs: **what pushes you away becomes what you practice into muscle memory**." — invents transformation narrative on what is just a let-binding flow arrow.
- `seed_let_binding_00435` — source `^8^P -> ^4^P`. English: "the expression then describes a flow: **what triggered the memory maps to what struck a chord**." — invents "maps to" and "the expression then describes" framing.
- `seed_recipe_00046` (=00246) — leakage `0.05*Λ·Ω_tracking_side` rendered as "Additionally, a small feedback loop **contributes 0.05 of the tracking_side outcome back into the system**." — invents "feedback loop back into the system" semantics.

**Frequency:** ~6 of 200 — **~3%**. Disproportionately in binary_composition with `->` and let_binding with src->tgt.
**Severity:** MAJOR (contaminates training with hallucinated content the compiler cannot round-trip).
**Validator coverage:** **NEW**.

### Pattern J — Stage-collapse / repetition in rpm_chain (W and P render identical text) [overlap-Agent-3]

**Definition:** stageW and stageP render with identical or nearly-identical English when the source distinguishes them (^N^C vs ^N^E).

**Examples:**
- `seed_rpm_chain_00305` — stageD7, stageW7, stageP7 all rendered with "in the evaluative arena tied to purpose and meaning" — three stages collapse to one.
- `seed_rpm_chain_00075` — stageW1 and stageP1 use near-identical "that same triggered memory expressed in [a cognitive way / through evaluative judgment]" — minor naming difference but stage identity weak.
- `seed_rpm_chain_00348` — stageD6, stageW6, stageP6 all "muscle memory in the arena of structure and order" with only "[principled / cognitive / evaluative]" varying — distinguishable but very repetitive.

**Frequency:** 4-6 of 28 rpm_chain records — **~14-20%**.
**Severity:** MAJOR (stage identity is structurally load-bearing in RPM).
**Validator coverage:** Likely covered by Agent 3's repeated-noetic stage-drop work.

### Pattern K — ^8 rendered as causal/analytical reasoning (anti-drift violation) [NEW]

**Definition:** Per CLAUDE.md anti-drift annotations, ^8 Above/Cause is associative TRIGGERING, not analytical reasoning. When English uses "causal connection" or "memory trigger or **causal connection**" for ^8, it is the exact drift pattern the framework warns against.

**Example:**
- `seed_meta_logic_relation_00242` — `StateCluster{^4^O, ^0^E, ^8^P}` rendered "memory trigger **or causal connection**" for ^8^P. The "or causal connection" attribution to ^8 is exactly the Scheme-B "Causal Reasoning" drift the operations manual flags.

**Frequency:** 1 of 200, n=1 in this slice. Worth flagging because it's the canonical anti-drift target.
**Severity:** MAJOR (anti-drift violation specifically called out in `CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 6).
**Validator coverage:** **NEW**.

### Pattern L — Order swap in two-input recipes [NEW]

**Definition:** A two-input recipe renders the inputs in the order [B, A] when the source is [A, B].

**Example:**
- `seed_diagram_export_00457` — source `1*^9^E + 1*^8^E -> Omega_verification`. English first input: "something that triggered a memory" (^8); second: "a realization" (^9). Order swap: source has ^9 first, English renders ^8 first.

**Frequency:** 1 of 200, n=1 in this slice.
**Severity:** MINOR-to-MAJOR depending on whether order semantics matter for the recipe's compositional meaning. For recipes summed with `+`, commutative — so MINOR. But if the model learns the rendering order matters, could mis-train.
**Validator coverage:** **NEW**, low priority.

### Pattern M — Ω stem renamed mid-sentence ("the named outcome X" then "outcome called Y") [PASSES_BUT_WORTH_NOTING]

**Definition:** Stylistic variation in how the same Ω stem is referred to within the same record — sometimes "outcome called X", sometimes "named outcome X", sometimes "X" alone. Not strictly an error since the stem is preserved, but creates inconsistent training signal.

**Frequency:** Pervasive, ~30% of recipe records. Not a quality blocker but a normalization opportunity.
**Severity:** PASSES_BUT_WORTH_NOTING.
**Validator coverage:** N/A (stylistic).

### Pattern N — Verbose elaboration (state_literal generates an English paragraph from a 3-token CAS atom) [PASSES_BUT_WORTH_NOTING]

**Definition:** state_literal records like `^9^P_{F3}` get rendered as "Something just clicked—a sudden realization or insight popping into mind unbidden, rooted in foundational thinking and driven by a need for vitality" (`seed_state_literal_00305`). Elaboration is OK in moderation but tends to invent additional framing ("unbidden", "sudden", "popping into mind" doubled with "just clicked").

**Frequency:** ~10-15 of state_literal records show non-trivial elaboration.
**Severity:** PASSES_BUT_WORTH_NOTING. Not a faithfulness violation; might be a stylistic concern for downstream training.

---

## Worst offenders — top 10 sample IDs with multiple stacked critical errors

These are records where I'd refuse to use the row for downstream training. Multiple Pattern A/B/C/H violations in the same record.

1. **`seed_rpm_chain_00102`** — stageD7 (^8^P_{F7}): P→E domain swap + stageW7 ^8^C → "memory struck as a chord" (^8 → ^4 noetic swap); plus stageP7 also says "evaluative arena" (collapse).
2. **`seed_rpm_chain_00305`** — Three-stage collapse: stageD/W/P all repeat "evaluative arena tied to purpose and meaning."
3. **`seed_rpm_chain_00197`** — Two domain swaps stacked: stageD5 P→E, stageP5 E→O.
4. **`seed_rpm_chain_00129`** — Two domain swaps: stageD7 P→E, stageW7 C→E.
5. **`seed_binary_composition_00492`** — Jargon leak ("CO-9", "CO-1", "cognitive operation") on a CO-N composition.
6. **`seed_binary_composition_00726`** — `CO-5 ∘ CO-5` rendered as "felt aversion" (^5→^3 swap) + invented domain "operational arena" + invented register "felt".
7. **`seed_binary_composition_00498`** — `CO-9 ∘ CO-7`: invented domains + ^9 rendered "struck a chord" (^4 swap).
8. **`seed_binary_composition_00653`** — operator-as-outcome confusion ("leading to the outcome called Negative") — Pattern G.
9. **`seed_inversion_00041`** — `^2^E_{F3} + ^3^E_{F5}` rendered with operator indices read as counts ("Two evaluative states ... three evaluative states") — Pattern F.
10. **`seed_recipe_00504`** — Two operator swaps: ^4→^0 + ^8→^9 in a single recipe.
11. **`seed_recipe_00388`** (= 00061) — ^2^C → "breaking down a thought" (^2→^6 swap, but appears in canonical recipe shape so partly caught by Agent 2).
12. **`seed_recipe_00306`** — ^6^P_{F1} → "analysis of operational behavior" (^P→O domain swap) + ^9^P → "realization that popped into mind" (double-render of same operator).
13. **`seed_recipe_00120`** (= 00298) — `^2^P|E` → "evaluative judgment expressed in an analytical way" — domain swap P→E AND register swap E→A.
14. **`seed_recipe_00341`** — register invention on `|T` and on bare ^6^E.
15. **`seed_let_binding_00385`** — invented transformation narrative on flow arrow.

---

## Patterns covered by other agents (do not duplicate)

- Drive→outcome confusion in inversion records (Agent 1).
- ^3→^5 swap in recipes (Agent 2).
- ^2→^6 swap in recipes (Agent 2).
- Register-invention in recipes (Agent 2 — partial; my findings show invention is broader than recipes alone).
- CO-N composition mis-rendering shape (Agent 3 — partial; my findings show domain-invention on CO-N is uncovered).
- Repeated-noetic stage drops in rpm_chain (Agent 3 — partial; my findings show domain-swap-on-stage is sibling-uncovered).

---

## NEW patterns and proposed validators

1. **Operator-noetic swap detector (broad)** — for each accepted record, compile-side round-trip the English back to CAS via the K=9 grounding mechanism (or a simpler keyword-mapping table); flag when the round-trip produces a different ^N from the source. Catches Pattern C across all categories. Spec: build a `colloquialism → operator` reverse table from `feedback_use_canonical_colloquialisms_as_operator_aliases.md`, scan English for hits, compare set to source ^N set.

2. **Domain-presence guard for `^N^D` and `^N^D_{F_k}` shapes (all categories)** — for every source token of shape `^N^D[_{F_k}]`, the English MUST contain a domain marker (principled/foundational/cognitive/mental/evaluative/judging/operational/behavioral) in the same span. If a drive marker (unity/wisdom/vitality/connection/agency/structure/purpose) appears WITHOUT a co-located domain marker, flag. Catches Pattern B. Generalizes Agent 1's inversion-only check.

3. **Bare-CO domain-injection detector** — for source tokens of shape `CO-N` or bare `^N` (no `^D`), the English MUST NOT contain a domain marker (principled/cognitive/evaluative/operational arena/realm). If it does, flag. Catches Pattern D. Catches CO-N + meta_logic violations.

4. **Operator-index-as-count detector** — for source `^N^D + ^M^D`, the English MUST NOT contain "[N word] X states" or "[M word] Y states" patterns where N/M are the operator indices. Catches Pattern F (n=1 here, but a repeat would be catastrophic).

5. **Jargon-leak vocabulary expansion** — extend `no_cas_jargon_leakage` to flag: `operator slot`, `cognitive operation`, `CO-[0-9]` literal, `lambda`, `operator position`, `operator slots`, `operator configurations`. Catches Pattern H. Cheap to implement.

6. **^8 anti-drift checker** — when source contains ^8, the English MUST NOT contain "causal connection" / "causal reasoning" / "deductive". Catches Pattern K.

7. **Operator-as-outcome detector** — when English contains "outcome called Negative" / "outcome called Positive" / "outcome called Vibration" / "outcome called [any Noetic name from the canonical set]", flag. The 10 Noetic names are reserved; they MUST NOT appear as outcome stems. Catches Pattern G.

---

## Confidence bounds

- **N read in detail:** 200 contiguous records (records #1–200) plus 98 contiguous tail records (#300–397). Total 298 of 398.
- **Coverage:** ~75% of the accepted file. Records #201–299 not read in this audit (call out below).
- **Sampling bias:** sequential, no shuffling. Generation order is deterministic per-batch but mixed across grammar_categories. The unread middle slice should not behave systematically differently.
- **Aggregate critical-error rate:** 31 / 200 in primary slice = 15.5%. 95% Wilson interval: **11.0% – 21.4%**.
- **Extrapolated count of records carrying ≥1 CRITICAL/MAJOR error in the full 398:** **62 ± 12**.
- **Per-category rates with explicit n** (counts within my read slice):
  - rpm_chain: ~9 of 28 = **32%** (Pattern A).
  - bare-CO binary_composition: ~5 of 8 = **62%** (Pattern D + jargon leaks).
  - meta_logic_relation: ~6 of 25 = **24%** ("operator slot" jargon — Pattern H).
  - recipe (outside Agent 2 territory): ~6 of 50 = **12%** (Pattern C, E).
  - inversion: ~2 of 25 = **8%** (Pattern F).
  - state_literal: low single-digit error rate; mostly clean.
  - fractal_sequence: deterministic renderer; effectively 0 errors observed (1 borderline case).
  - cross_register_omega: deterministic renderer; effectively 0 errors observed.
  - let_binding: ~3 of 35 = **8%** (Pattern I in src→tgt records).
  - diagram_export: ~3 of 25 = **12%** (mix of Pattern C, D).

---

## What is NOT in this audit

- **Records #201–299 (~99 records, 25% of accepted)** — not read in detail. Same generation pipeline, same model, same prompts; expected error distribution similar but not directly verified.
- **Compiler round-trip** — I did not actually run the English back through the compiler. All my "operator swap" calls are based on colloquialism-to-operator matching against the canonical map; true round-trip would refine and possibly reduce the count.
- **Cross-register_omega and fractal_sequence** are deterministic-renderer outputs and tend to be reliable; I sampled but did not exhaustively check.
- **Rejected records** (102 in `wave3_step2_5_rejected_20260508T110453Z.jsonl`) — out of scope for this audit (they're already filtered out).
- **Wave 2.5 generation prompts and the v2 module behavior** — I did not read the source code; my findings are output-only. The agents building validators have direct access to that.

---

## Closing tone

The 398-record green run is a real step forward (the 80% accept rate is a deterministic-renderer + first-LLM-pass artifact that *would* improve), but the accept gate is currently lexical (jargon strings + cluster shape) more than semantic. The model writes plausible English that the compiler cannot round-trip. **Of the 200 records I read closely, ~16% carry at least one error that would teach a downstream model the wrong CAS↔English mapping.** The new patterns (C, D, F, G, H, K) are the long tail — none common, all damaging when they slip through.

Per `feedback_samples_are_the_only_true_eval_for_cas_native.md`: do not promote this corpus to v1 training mix without the additional validators specified above. Sample-read 5–10 random records after each new validator lands; the 200-sample read above can serve as a regression baseline.
