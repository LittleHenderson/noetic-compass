# DIRECTIVE (Claude's recommended version, revision 2): CASALESCENCE FOR ALL TEN NOETICS

Revision 2 folds in the review of revision 1: the new reading ability is named as new work; the earlier result is stated exactly; pass rules need useful accuracy, not only a win over weak comparisons; the agreement rule is split in two; the text-reader conclusion is narrowed; the non-CAS comparison must be fair.

Status: a recommendation for the owner. It authorizes nothing and spends nothing until the owner approves it and a costed plan.
Queue it after the current accepted milestone. Preserve current runs, saved models and results. Do not interrupt an active experiment or launch duplicate work.

## Goal

Extend the reader from Cause and Effect to all ten Noetics, using the canonical definitions word for word. Role recognition and useful help are two separate achievements. Measure and report them separately. Find out two things, in this order of proof:

1. Can the reader say which thing occupies each Noetic in unfamiliar situations with no wording clues?
2. Does that reading help a second model answer better, without breaking answers it already got right?

## 0. Carried forward. Do not run again.

- **Cause and Effect, clearly described: won.** 15 of 16 (Cause 7/8, Effect 8/8). This is done. Reuse the saved reader from the archive (`experiment/small_frozen/eta.json`, archive sha256 `dfd6ff53b40ea450a7894610f99a002ff3cb9bca8446794e4bbfddb3a4c3019b`). Do not refit it.
- **Help to model B: the program's result is `INCONCLUSIVE`.** All nine groups scored 0 of 8 on both task sets. Of the 144 answers, 124 were fenced JSON and were scored as malformed, 19 were plain JSON and scored wrong, and 1 was cut off. Whether the answers inside the fences were right is unknown. So formatting is not the only cause: some answers were wrong. A fixed scorer may show differences between groups or may not. It is not a loss for CAS and not a win.
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
- **`^0` Idea stays in the representation.** Under its definition every thing is an Idea, so "is an Idea present" is not scored. What is scored is which Ideas the reader finds and how they relate: each thing the reader points to is an Idea, and the other Noetics describe its relations.
- Allowed answers also include **ambiguous**, **not enough information**, and **none of these**. Never force a label.

## 2b. This needs a new reader. Build and test it as new work.

The saved reader does one small job: for a focus the prompt describes, it picks Cause or Effect from one reading point. It cannot find the things in a passage, and it cannot give several Noetics to each. Adding eight more output labels does not create that ability.

The new reader must:

- read at every word position of the passage, not at one point;
- find each thing that occupies a role and point to its exact words;
- give one thing several Noetics when that is true, and link it to the Mind or Idea it is relative to;
- be able to answer ambiguous, not enough information, or none.

This changes what is captured from model A, so it needs a new reviewed package version with its own software tests, built and tuned on development cases only. The saved Cause/Effect reader stays as the baseline and is not altered.

## 3. Order of work

**Step 1 — Fix the yardstick (cheap, first).**
Write the scoring rules before any paid call: plain JSON, fenced JSON, missing fields, invalid answers. Prove the scorer on known right and wrong examples. Report formatting failures separately from wrong answers. Pick tasks where model B alone is right between 30% and 70% of the time on practice cases, so a gain or a loss can show.

**Step 2 — Can people agree on the labels? (no cloud cost).**
For each of the ten Noetics, two independent labelers from different model families label unfamiliar, unmarked passages using only the definitions above. Neither sees the other's labels. The owner spot-checks a sample of disagreements. Do this in two sizes:

- **First look:** 10 to 20 passages per Noetic. Its only purpose is to find problems in the labeling guide. It is not a verdict.
- **Verdict:** a fresh, larger set (proposed: at least 50 passages per Noetic; the plan fixes the number and justifies it).

Report two measures, calculated separately, for each Noetic: (a) plain agreement, the share of cases where both teams gave the same label and pointed to the same words; and (b) agreement after removing what chance alone would give (Cohen's kappa). Proposed bars: (a) at least 80% and (b) at least 0.6. Both must be met. Show the counts and the uncertainty range, not only the percentages.

A Noetic that misses either bar is reported as "not labelable under this method" and parked. It is not forced and not counted as a failure of CAS.

**Step 3 — Finish the unmeasured half for Cause and Effect.**
After the scorer is checked, run the help-to-B comparison once, on fresh cases, using the saved reader as it is. This is not a repeat of the reading. It is the first real answer to "does the reading help at all", and it tests the Stage C machinery on the two Noetics we can already read. Its cases are the clearly described kind, so keep this result separate from the later unmarked-role study and never merge the two.

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
- for any claim that the result is special to CAS: a **fair non-CAS set of roles** on the same cases. Fair means all of these: it is a meaningful, established way to describe the same situations; it has a similar number of roles; it is relevant to the same tasks; it is labeled by the same independent process and reaches similar label agreement; and it is not a renaming of the CAS labels (a renaming ties by construction, spec sheet 7.19). The set is reviewed and frozen before any run. Beating arbitrary or badly chosen labels proves little and may not be claimed.

Model B, Step 3 and Stage C. Compare: no guidance; CAS guidance; mixed-up CAS guidance; ordinary helpful guidance; neutral filler of the same length. Same length, same allowed effort, same answer format, same scorer. Never put the answer in the guidance.

## 5. Pass rules, written before any run

- **Stage B passes for a Noetic** only if both of these hold on the sealed final test:
  1. *It beats the weak comparisons:* the letter-pattern rule and the mixed-up-label reader, by a margin fixed in the plan.
  2. *It is useful in its own right.* The plan fixes, before any run, three floors: a minimum share of true roles found and named correctly; a maximum share of roles the reader adds that are not there; and a minimum share of correct roles where it points to the right words. Proposed starting values: at least 70% found, at most 20% falsely added, at least 70% pointed correctly. No floor may be set above what the two label teams themselves reached.
- **Report missed roles and falsely added roles separately**, per Noetic.
- **If the strong text reader ties or beats the internal reader**, the conclusion is exactly this: "We have not demonstrated an advantage from reading inside the model on this test." It does not mean internal reading can never add value. For the help-to-B stage, the simpler reader may then be used, and the question of an internal advantage stays open.
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

No single agent designs, runs and grades. Name, before work starts: the builder, the two label teams, the plan reviewer, and the operator who runs AWS. Different model families help, but separation of access is what counts: label teams cannot see each other's judgments; builders and tuners cannot see final cases or final answers; reviewers cannot edit what they review. Record who could open which file. Every status comes from a program's output, not from prose. The owner approves each paid stage.

## 8. Running it

- Use AWS for all model work. Reuse the corrected launcher (`D:\tksCAS-runs\controller_cas_small_op11_claude_c1`, `C1_AMENDMENT.md`).
- One job at a time on the shared storage slot, with bus notices before and after.
- Arm the independent cleanup check at launch, so it runs within minutes of shutdown even if a session is cut off.
- Price the small preliminary stages first (scorer check, label agreement, the early Cause/Effect help-to-B check). Expand only when their results justify it, with a new costed plan each time. Reconcile the budget before each launch. This directive assumes no unused funds and authorizes no spending.

## 9. Deliver evidence that can be inspected

Definition and source inventory; label-agreement report with every disagreement; frozen study plan; case-split record; checked scorer examples; every individual prediction; comparison tables with counts and uncertainty; which Noetics get confused with which; roles missed and roles falsely added; how accurately the reader points to the right words; where B improved and where it got worse; instructions to reproduce. Add each result to the spec sheet and changelog in the same commit, negatives included.

## Work tree

Fix the yardstick → label agreement → finish Cause/Effect help-to-B → build and test the new reader → clearly described roles (other eight) → unfamiliar unmarked roles → help and no-harm comparison → independent replication

Alternative paths: repair unreliable labels before expanding; use the simple reader if it does equally well; other model pairs only after the first study can be read.

Report agent models and reasoning settings, start and finish times in Pacific time, and what is active, waiting or parked. Mark verified wins 🏆, failures 👎 and genuinely new approval requests 🔴 A.N.

## Decisions for the owner

Settled in this revision unless you say otherwise:

- **`^0` Idea:** kept in the representation; presence is not scored; finding the Ideas and their relations is.
- **Early Cause/Effect help-to-B check:** yes, after the scorer check, on fresh cases, with the saved reader as baseline, reported separately.

Still yours to decide:

1. **Who builds, who labels, who reviews.** Name them. At least one label team must not be Claude, and the teams must not be able to see each other's judgments.
2. **Budget for the preliminary stages.** A priced plan for the scorer check, the label-agreement check and the early help-to-B check comes to you first. Nothing launches before you approve it.
