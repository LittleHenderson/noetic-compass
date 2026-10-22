
## Amendment A-CUBE-TRAIN-1 (2026-10-22 PDT) — say-back rows, the exact labelling rule, the bands; written before any training code

Status: appended below `PREREGISTRATION_CUBE_TRAIN.precode.md` (`6e1afceb…`), which is not edited. Where they disagree, this governs. Owner's word for this step (2026-10-22): "Yes: build the training rows and the CTT adapter test-first (0 USD), then the AI-written lines, then seal the training package."

**A1. Say-back rows (missing from §4.1).** In each round HELM writes a plain say-back line and the proposers RE-READ it (A-TEACH2-2 B4); a CTT never trained on say-back lines could never agree twice. So **6,000** of the 40,000 SDG cube rows are say-back rows: the input is `helm_cube_osc.say_back(reading)` of a truth reading, the target is that same reading. DEV-SDG gets 300 say-back rows inside its 2,000.

**A2. The labelling rule (the generator's truth, written exactly).** For a line about fact F of a world:
- `thing` = F's unit (the yard or line name), lower case; `value` = F's value as the line states it (the count word, or the person or place name, lower case); `replaces` = the old count word on a correction line, else none.
- `slot` = the content words (the cut's `content_words`) of F's canonical template statement, minus `thing`, `value`, `replaces` and A-TEACH2-2 B2's discourse list, **kept only where the word also occurs in the line**; the row is dropped if the slot is empty, or if F has a month and the month is not in the line (the cube's branch target), or if any target word does not occur in the line (the copy rule).
- A first statement that a later correction fixes is labelled with the value it states (the old one); the correction line carries the new value and `replaces` the old.
- "I don't remember …" lines and small talk are labelled `NONE`.
- TRAP lines (SDG): the canonical statement with one decoy, three frozen frames — a leading "Not that it matters much, but …"; for counts a trailing ", up from <another number word> the month before."; a trailing ", while <another unit> was quiet in <another month>." The label is F's truth.
- FACT lines (SDG): the canonical statement with one of TEACH-1's practice prefixes (`PRACTICE_PREFIX`, and "As I said before, " for a restatement).

**A3. The bands (fixed now, above every band in use).** TRAIN worlds: seeds `2,050,000,000 + i`; DEV worlds: `2,051,000,000 + i`; the `LLM_WRITTEN` stratum's facts come from TRAIN worlds, its DEV lines from DEV worlds. TEACH-2's bands are taken at its seal above `2,052,000,000`. Training data is not secret, so the bands are fixed in advance; the house-rule seed (sha256 of `CUBE TRAIN at 3 USD` + ":" + the sealed zip's sha256) draws the 20,000 kept CAS-record rows and the batch order.

**A4. Where the code lives.** The row builder and its tests: `docs/working/helm_cube_oscillation_v1/cube_train/` (exam side, not inside HELM). The adapter (`reading_from_ctt`, `CTTProposer`) inside `helm_cube_osc.py`, standard library only; it refuses a malformed output, an output holding any word not in the line, an empty slot, or a thing or value that is not a word of the line.
