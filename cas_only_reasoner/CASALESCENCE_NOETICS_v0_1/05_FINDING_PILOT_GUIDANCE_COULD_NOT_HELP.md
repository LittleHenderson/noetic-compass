# 05 — Finding: in the pilot, the CAS guidance could not have helped model B, by design

Found 2026-10-04 about 23:20 PDT, by reading the accepted pilot package (`casalescence_small_v0_2`, manifest `df821cf46c2c977781bade4bce677fe2d7cd29a75f039755930e653a9df811e8`). No code was run. This is a reading of the source and data, not a new measurement.

## The finding

In the pilot's benefit tasks, whether the prompt was marked Cause or Effect had nothing to do with the right answer. So telling model B "this one is Cause" or "this one is Effect" gave it nothing it could use to answer.

## The evidence

1. **The answer never looks at the focus.** `src/task_contract.py`, function `solve` (lines 220 to 237): the answer is computed from `task["problem"]` only. The `focus` text is checked for type and length and then ignored.
2. **The eight benefit tasks are four identical problems, each asked twice.** Same records, same swaps, same question; only the focus sentence differs. From `data/public.json` and `data/labels.json`:

   | Task | Label | Problem (hash of the problem data) |
   |---|---|---|
   | `…2745` | `^8|C` | `253dc7e09a` |
   | `…2746` | `^9|C` | `253dc7e09a` |
   | `…2747` | `^8|C` | `99adaaeba2` |
   | `…2748` | `^9|C` | `99adaaeba2` |
   | `…2749` | `^8|C` | `7f68cefbac` |
   | `…274a` | `^9|C` | `7f68cefbac` |
   | `…274b` | `^9|C` | `20e38e2f82` |
   | `…274c` | `^8|C` | `20e38e2f82` |

   Each pair has the same right answer.
3. **The labels file says so itself:** every row carries `"objective_answer_is_class": false`.
4. **The package's own protocol says so:** "Paired variants change the marked focus while preserving the objective answer. The task helper computes an ordinary quantity, actor or word list; the CAS class is not that answer." It calls the setup "limited conditioning". The catalog review recorded `CLASS_IS_NOT_OBJECTIVE_ANSWER`.
5. **The CAS guidance was one of two fixed sentences.** `render_class` (line 332) returns one stored text per class and takes no task data.
6. **Model B already saw the focus sentence** in its own prompt (the review's limits list says "B already sees focus cue").

This matches what the run showed: under the CAS prefix, B's visible answer did not change on any of the 8 benefit items.

## What this does and does not mean

- It does **not** mean CAS guidance cannot help a second model. That was not tested.
- It does **not** change the recorded result: reader screen passed 15/16; benefit comparison `INCONCLUSIVE` in the program's words, `VACUOUS` in the spec sheet.
- It **does** mean the code-fence scoring problem was not the only reason for the empty result. With a perfect scorer, the most likely outcome of that design was still "no difference", because the guidance carried no information about the answer.
- It **does** mean the reviewed design separated "is the class the answer" from "does the class matter to the answer" and only checked the first. Keeping the answer out of the guidance is right. Making the guidance irrelevant to the answer goes too far.

## My error

In directive revision 1 and revision 2, I recommended finishing the Cause/Effect help-to-B check early, with a fixed scorer and fresh cases of the same kind, because it was "cheap and tells us whether guidance helps at all". I had not checked that the label mattered to the answer. Run that way, it would have cost about 7 USD and told us nothing. The plan's stages P3 and P4 are on hold for this reason.

## What a valid help-to-B test needs

Tasks where knowing which thing occupies which role is a needed step toward the answer, without being the answer. Example of the shape: a passage in which a smell brings a place to someone's Mind, and a question such as "What is most likely to come to her Mind the next time she meets that smell?" The role reading (`^8`: the smell; `^9`: the place) is what the solver needs; the answer is still for B to produce.

Two consequences:

1. **The saved Cause/Effect reader cannot supply that.** It tells two focus sentences apart on marked prompts. It does not find things in a passage. A valid help-to-B test therefore waits for the new reader (directive section 2b), or uses role readings from the label teams as a stand-in to test the idea before the reader exists.
2. **The fair rival gets stronger.** Ordinary helpful guidance (model A saying in plain words who was reminded of what) carries the same information. CAS guidance must be compared with that, as the directive already requires.

## Options for the owner

| Option | What happens | Cost | What it tells us |
|---|---|---|---|
| A | Skip the early Cause/Effect check. Go on with label agreement, then the new reader, then a help-to-B test on role-relevant tasks. | none now | nothing, until the reader is built |
| B (recommended) | Label agreement continues at no cost. Then, before the new reader is built, test the idea with "perfect" role readings: give B the label teams' agreed roles as guidance on role-relevant tasks, against ordinary help and no help. | one small GPU job, about 2 to 5 USD | whether correct role information helps B at all. If it does not help even when perfect, the reader is not worth building for this purpose. |
| C | Rerun the old design with only the scorer fixed. | about 7 USD | almost nothing; not recommended |

I recommend B. It is the cheapest way to answer "is this worth building", and it follows the same logic as the label-agreement check: test the weakest link before the expensive one. It needs a short reviewed task set first, and a priced plan for your approval.
