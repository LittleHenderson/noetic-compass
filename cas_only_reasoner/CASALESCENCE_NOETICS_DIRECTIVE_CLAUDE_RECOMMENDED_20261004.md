# DIRECTIVE (Claude's recommended version): CASALESCENCE FOR ALL TEN NOETICS

Status: a recommendation for the owner. It authorizes nothing and spends nothing until the owner approves it and a costed plan.
Queue it after the current accepted milestone. Preserve current runs, saved models and results. Do not interrupt an active experiment or launch duplicate work.

## Goal

Extend the reader from Cause and Effect to all ten Noetics, using the canonical definitions word for word. Find out two things, in this order of proof:

1. Can the reader say which thing occupies each Noetic in unfamiliar situations with no wording clues?
2. Does that reading help a second model answer better, without breaking answers it already got right?

## 0. Carried forward. Do not run again.

- **Cause and Effect, clearly described: won.** 15 of 16 (Cause 7/8, Effect 8/8). This is done. Reuse the saved reader from the archive (`experiment/small_frozen/eta.json`, archive sha256 `dfd6ff53b40ea450a7894610f99a002ff3cb9bca8446794e4bbfddb3a4c3019b`). Do not refit it.
- **Help to model B: returned no answer.** All nine groups scored 0 of 8 because the scorer rejected B's answer format (124 of 144 answers were fenced). It is recorded as `VACUOUS`. It is not a loss and not a win.
- **Old dead ends stay closed** (spec sheet 7.1, 7.2, 7.6, 7.7, 10.1): no whole-passage sorting into 40 cells, no patching a rejected case bank, no reuse of cases written by the same hands that wrote the definitions.

## 1. Definitions: use these words exactly

Source: `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, Clarification 1 (commit `1c8531ea`, file sha256 `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880`), verbatim from the Tootra Math Handbook. Cite the file and commit in every record.

- `^0` **Idea** — All things in and outside the Mind.
- `^1` **Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- `^2` **Positive** — An Idea the Mind has an affinity for and is attracted toward.
- `^3` **Negative** — An Idea the Mind is adverse to and repelled by.
- `^4` **Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- `^5` **Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- `^6` **Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- `^7` **Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- `^8` **Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- `^9` **Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

Rules:

- Never reword, shorten or "modernize" a definition. Never use everyday or gender meanings.
- Use the checks already in Clarification 6: `^3` is felt aversion, not analysis; `^8` is triggering, not reasoning.
- Label the Noetic only. Worlds/Domains, Drives and Registers are not labeled in this study. Say so in every record.
- Write `^8`, `^9`. The pilot wrote `^8|C`; in CAS notation the bar marks a Register, so that label was malformed. Fix it before any new case is written.

## 2. What a label is

A label says which exact words in the passage occupy a Noetic, and relative to which Mind or Idea. Example shape: "`^8`: *the smell of rain*, for the Mind *Ada*; `^9`: *her grandmother's porch*."

- Several Noetics may be present in one passage.
- Allowed answers also include **ambiguous**, **not enough information**, and **none of these**. Never force a label.

## 3. Order of work

**Step 1 — Fix the yardstick (cheap, first).**
Write the scoring rules before any paid call: plain JSON, fenced JSON, missing fields, invalid answers. Prove the scorer on known right and wrong examples. Report formatting failures separately from wrong answers. Pick tasks where model B alone is right between 30% and 70% of the time on practice cases, so a gain or a loss can show.

**Step 2 — Can people agree on the labels? (no cloud cost).**
For each of the ten Noetics, two independent labelers from different model families label unfamiliar, unmarked passages using only the definitions above. Neither sees the other's labels. The owner spot-checks a sample of disagreements. A Noetic enters the study only if the two labelers agree on at least 8 of 10 cases after allowing for chance agreement (Cohen's kappa of 0.6 or more). A Noetic that fails is reported as "not labelable under this method" and parked. It is not forced and not counted as a failure of CAS.

**Step 3 — Finish the unmeasured half for Cause and Effect.**
Using the saved reader, run the help-to-B comparison once with the fixed yardstick. This is not a repeat of the reading. It is the first real answer to "does the reading help at all", and it tests the Stage C machinery on the two Noetics we can already read.

**Stage A — clearly described roles, the other eight.**
Each alone and in combinations with the others, including `^8`/`^9`. This is preparation: it shows the machinery and labels work. It is not a result to claim.

**Stage B — unfamiliar, unmarked roles. This is the decisive stage.**
No Noetic names, numbers or giveaway wording. Different situations from training. The reader must name the Noetic and point to the words that occupy it. Include close alternatives, several roles at once, and unclear cases.

**Stage C — help to model B.**
Only for Noetics that passed Stage B. Measure whether B's answers improve and whether previously right answers become wrong.

**Replication.** A fresh set of cases, run independently, before anything is said outside the project.

Keep the Qwen2.5 pair for the first study. Propose other pairs separately.

## 4. Fair comparisons

Reader, Stages A and B. Compare the internal reader with:

- a **strong text reader** given the full prompt (the same information the internal reader has);
- a **letter-pattern rule** on the raw text (character n-grams), plus a word-level one;
- a reader trained on **deliberately mixed-up labels**;
- the **answer-only reader**, as a secondary comparison;
- for any claim that the result is special to CAS: a **same-size set of non-CAS roles**, labeled the same way on the same cases. It must do worse.

Model B, Step 3 and Stage C. Compare: no guidance; CAS guidance; mixed-up CAS guidance; ordinary helpful guidance; neutral filler of the same length. Same length, same allowed effort, same answer format, same scorer. Never put the answer in the guidance.

## 5. Pass rules, written before any run

- **Stage B passes for a Noetic** only if the internal reader beats both the letter-pattern rule and the mixed-up-label reader on the sealed final test, by a margin fixed in the plan.
- **If the strong text reader ties or beats the internal reader**, say so plainly: the role is readable from the text and the internal reading adds nothing. Then use the simpler reader.
- **Stage C passes** only if CAS guidance beats the strongest ordinary-help group, not just "no guidance", and does not lose on the previously-right tasks.
- **Sizes.** The plan must show its own calculation. As a guide: at least 40 final-test cases per Noetic for reading, and roughly 150 to 250 matched final-test tasks to detect a 10-point gain for B. Anything smaller is labeled exploratory.
- **A missed requirement is a failure of that stage.** No retry on the same test cases, no changed threshold, no dropped cases. A new attempt needs new cases and a newly reviewed version.

## 6. Shortcut prevention

- Split practice, development and final cases by situation family and wording pattern. Keep related pairs in one group.
- Case writers never see the reader or its outputs. Label reviewers are independent of the writers.
- The final cases and answers are sealed by hash and held away from anyone tuning the reader. Layers, prompts and settings are chosen on development cases only.
- Nothing about the test changes after results are seen.
- Include tasks B already gets right, to check nothing is broken.

## 7. Who does what

No single agent designs, runs and grades. Name, before work starts: the builder, the two label teams, the plan reviewer, and the operator who runs AWS. Every status comes from a program's output, not from prose. The owner approves each paid stage.

## 8. Running it

- Use AWS for all model work. Reuse the corrected launcher (`D:\tksCAS-runs\controller_cas_small_op11_claude_c1`, `C1_AMENDMENT.md`).
- One job at a time on the shared storage slot, with bus notices before and after.
- Arm the independent cleanup check at launch, so it runs within minutes of shutdown even if a session is cut off.
- Present a costed plan per stage and reconcile the budget first. This directive assumes no unused funds and authorizes no spending.

## 9. Deliver evidence that can be inspected

Definition and source inventory; label-agreement report with every disagreement; frozen study plan; case-split record; checked scorer examples; every individual prediction; comparison tables with counts and uncertainty; which Noetics get confused with which; roles missed and roles falsely added; how accurately the reader points to the right words; where B improved and where it got worse; instructions to reproduce. Add each result to the spec sheet and changelog in the same commit, negatives included.

## Work tree

Fix the yardstick → label agreement → finish Cause/Effect help-to-B → clearly described roles (other eight) → unfamiliar unmarked roles → help and no-harm comparison → independent replication

Alternative paths: repair unreliable labels before expanding; use the simple reader if it does equally well; other model pairs only after the first study can be read.

Report agent models and reasoning settings, start and finish times in Pacific time, and what is active, waiting or parked. Mark verified wins 🏆, failures 👎 and genuinely new approval requests 🔴 A.N.

## Decisions for the owner

1. **`^0` Idea.** Its definition covers all things, so "Idea" is true of everything and cannot be scored as right or wrong. Recommended: record it as always present and do not score it as a class. If you want it scored, say what should count as *not* an Idea.
2. **Step 3.** Recommended as written: finish Cause/Effect help-to-B early, because it is cheap and tells us whether guidance helps at all. If you say no, it waits until after Stage B.
3. **Builder and labelers.** Name who builds (Codex, or Claude with sub-agents). At least one label team must not be Claude, so the two teams are truly independent.
4. **Budget ceiling for this study.** Not priced yet. A plan with a dollar figure per stage comes to you before any launch.
