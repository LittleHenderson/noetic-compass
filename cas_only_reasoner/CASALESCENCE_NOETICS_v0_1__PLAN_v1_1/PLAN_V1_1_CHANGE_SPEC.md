# Plan v1.1 change specification (operator, 2026-10-07)

Status: PROPOSED. This folder is a byte copy of `CASALESCENCE_NOETICS_v0_1` (see `PROJECT_COPY_RECORD.json`). The v1.0 folder and its seal file are never edited. Every v1.1 change is made HERE and recorded in `PLAN_V1_1_CHANGES.json`.

## 0. Why (the counts, from the sealed v1.0 practice evidence)

Practice set, 12 settings (all 4 reserve settings used): 48 role-step candidates after Steps 2-3; 30 after the key check (both solvers must pick the key with the passage); 16 after the no-passage check (both solvers right without the passage); 16 selected. Floor 36. Plain-fact 86 / 85 / 44 / 20 selected, floor 20 (met).

Read-only diagnosis of the 18 key-check failures: 3 = the writer's key is wrong and a solver is right (all three BRING: TAKE_AWAY keyed the noticed thing, MEET_AGAIN keyed the remembered thing); 13 = key defensible but two or more options fit (7 of 11 PARTS candidates: WHAT_LEFT left two parts undone, NOT_BELONG had a second non-part among the wrong options; HABIT/LAND near-synonym option sets); 1 = solver error on a sound question; 1 = the question omitted its own condition. Every one of the 11 solver flags sat on a question read as ambiguous or defective.

Of the 14 guessable items: 5 = the key is the only option of its kind (an action among nouns, a memory among objects); 5 = valence written into the option words ("rough scratchy", "coarse", "heavy awkward", "calm"); 2 = the question repeats the answer's words; 2 = off-topic distractors (one leaked from another passage).

Supply: of 123 open (passage, form) pairs, 28 got no question from the writer, 42 lost every question at Steps 2-3, 53 had a passing question; the one-candidate-per-pair spare rule gave 48 candidates. Even 100% survival of 48 candidates could not have reached 36 after the per-passage cap. So v1.1 must raise supply AND question quality.

Two loosened key rules were counted and REJECTED: "keep when one solver picks the key and the other flags" would add 3 tasks, all flawed; "writer plus one solver" would add 6, four flawed and one with a wrong key. The key check and the no-passage check stay exactly as in v1.0. The floors stay 36 / 20. The reserve targets stay 45 / 25.

## 1. The changes (exhaustive)

### C1. Question brief (constants `briefs.question_brief`; plan 8.1 and 7.1/7.3 wording)

Add, in the "Forms 1 and 2" block, after the TAKE_AWAY line:
- "In TAKE_AWAY the right option is the thing that was brought to mind, never the noticed thing itself. In MEET_AGAIN the right option is a new thing of the same kind as the noticed thing (a sound like that sound, a smell like that smell), never the remembered thing."

Add, in the "Forms 9 and 10" block, after the NOT_BELONG line:
- "In WHAT_LEFT the question names every part that was dealt with, and exactly one named part is left. In NOT_BELONG the five wrong options are five of the named parts, and the right option is a thing that is not one of the named parts."

Add to "Rules for every FAMILY 1 question" (after the existing "Every wrong option is a thing or an action named in the passage" rule):
- "Every wrong option is the same kind of thing as the right option: an action with actions, a named part with named parts, a thing brought to mind with things brought to mind, a situation with situations."
- "Name things by their plain nouns. No option carries a word that says whether a thing is pleasant or unpleasant, liked or disliked, easy or hard, calm or alarming, rough or smooth, heavy or light."
- "No two options name the same thing, or nearly the same thing."
- "The question sentence must not repeat the words of the right option, and must not repeat the words of the passage sentence that holds the right option."

Nothing is removed from the brief. The forbidden-word lists do not change.

### C2. Program-enforced Step 2 rules (constants `question_rules`; tool `tools/ob_check_questions.py`; FILE_FORMATS 5.1 drop reasons; plan Step 2 drop list)

Three new drop rules for role-step questions, each with its own reason code, all using the looser word test of `tools/verdict.py` (`lenient_span` / "share at least half the content words of the shorter text"), the same frozen function the anchor and option checks already use:

- `QUESTION_REPEATS_KEY`: drop when the question sentence and the right option match by the looser test. Constants key `question_rules.question_must_not_match_right_option: true` with a `_rule` text.
- `OPTIONS_MATCH_EACH_OTHER`: drop when any two of the six options match each other by the looser test. Constants key `question_rules.no_two_options_match: true` with a `_rule` text. (Plain-fact questions: apply the same rule to their four options.)
- `WRONG_OPTION_NOT_FROM_PASSAGE`: for the forms listed in `question_rules.wrong_options_must_match_passage_forms` only, drop when any WRONG option does not match the passage by the looser test (at least half of the option's content words occur in the passage). Forms: `GOES_FOR`, `KEEPS_AWAY`, `WHAT_STUCK`, `WHAT_SLID_OFF`, `WHAT_LEFT`, `NOT_BELONG`, `LONG_BREAK`, `NEW_STARTER`, `TAKE_AWAY`. Not applied to `MEET_AGAIN`, `SWAP_PERSON`, `WHERE_HELPS` (their options are new things or new situations by design) and not to plain-fact questions. The right option is not tested by this rule.

Order inside Step 2: after the existing form checks, before the anchor check. Each is counted in `dropped_by_reason` like the existing codes.

### C3. Three passes and the widened candidate rule (constants `outside_services.gemini_question_writer.passes`, `pass_meaning`, `seeds.writer_batch_order_p3`, `question_rules.spare_rule`; tools `ob_write_questions.py`, `ob_check_questions.py`, `ob_select.py`; FILE_FORMATS 4, 5.4, 7; plan Step 1 "Spare pass", the sentence after Step 3, Steps 4-6)

- Passes are `p1`, `p2`, `p3`. `pass_meaning.p3` = "third pass: same brief, different seeded batch order". New seed `writer_batch_order_p3 = 20261018` (the next unused value in the seeds block). The writer tool accepts `--pass p3` and reads its seed by the existing name rule. File names follow the existing pattern with `p3`.
- Candidate rule (replaces the v1.0 spare rule): every question of every pass that passes Steps 2 and 3 is a candidate. A (passage, form) pair may have up to three candidates, one per pass. `checks/candidates_<set>.json` lists them all; each candidate row carries `pass` (`p1`, `p2` or `p3`). The `counts` block reports `candidates_per_pass`.
- Steps 4 and 5 run on every candidate (no change to the solver tool's logic: items are per question id; the key-check keep rule and the no-passage drop rule are unchanged).
- Step 6 (selection): per (passage, form), the survivors are reduced to ONE question before the pair rule: the surviving candidate of the lowest pass (p1 before p2 before p3). Then the v1.0 pair rule, length backstop and letters apply unchanged. The selection file records, per passage and form, which pass supplied the task (`pass_used`). The survival rows count per passage and form as before ("a later pass stands in where an earlier one was dropped").
- Rationale for lowest-pass-first: the writer never learns which pass was kept; the choice is a fixed rule, not a choice after seeing the solvers.

### C4. Everything else is unchanged

Key check rule, no-passage rule, selection pair rule, length backstop, letters, reserve rule and targets (45 / 25), launch floors (36 / 20 / 100 / 100), all seals, all briefs other than the question brief, all job programs, the self-test expectations.

### C5. Costs (plan 19.2 and section 22 question 13; FILE_FORMATS section 0 unchanged limits)

Gemini: one more writer pass per set (practice about 22 calls at 12 settings, final about 59). DeepSeek: up to three candidates per pair instead of one; practice at most about 3 x 48 x 2 = 288 items (REAL v1.0 practice: 268 calls, 41,185 input and 1,609 output tokens); the v1.0 token limits (2,430,240 / 1,156,520) are far from reached and do not change. Claude solver: the same, as sub-agent sheets.

## 2. Version and files

- Plan file: `08_OPTION_B_PLAN_v1_1.md` (a copy of v1.0 with the edits above and a new section 28 "Version 1.1: changes after the practice stop of 2026-10-07", holding the counts of part 0 and a table of every edit with its section). `plan_version` = "1.1"; constants `schema` = "casalescence/optionb-plan-constants/v1.1"; `plan_file` = "08_OPTION_B_PLAN_v1_1.md". The v1.0 plan file stays in this folder, unedited, for the record.
- `optionb/FILE_FORMATS.md` is edited in place in THIS folder only (it is a byte copy); its header says "version 1.1" and names the changed sections.
- Tools edited in this folder only: `tools/ob_write_questions.py`, `tools/ob_check_questions.py`, `tools/ob_select.py`. Each keeps its exit-code rule and its dry mode. `tools/ob_seal.py` is checked (not edited unless necessary) for: step 3A listing the `p3` files; the survival rows it reads from `select/selection_practice.json`.
- `PLAN_V1_1_CHANGES.json`: one row per changed file with old sha256 (from `PROJECT_COPY_RECORD.json`), new sha256, and what changed.

## 3. Custody and review

The writer still sees only the brief and the fenced passages. The solvers still see only passage, question and options. No person edits a question or a key. The operator runs programs. A separate reviewer sub-agent reads the whole v1.1 package (plan diff, constants diff, formats diff, tool diffs) before anything runs; its record is `PLAN_V1_1_REVIEW.json` beside the plan. A BLOCKER or MAJOR holds the run.
