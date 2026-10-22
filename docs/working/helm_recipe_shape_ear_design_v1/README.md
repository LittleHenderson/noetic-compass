# Recipe-shape proposer ear — design packet v1 (2026-10-20 PDT)

Status: **DESIGN ONLY. 0 USD. Nothing built, nothing trained, nothing run. No claim.**
Status 2026-10-20 (after the packet): **Q7 BUILT, ENGINEERED-NOT-VALIDATED.** The two deterministic steps Q7 proposed are built behind one switch, `WIDE_UNITS_NOTE` (default OFF; `helm_brain_wide.units_note_on`): 6 widened units with exact programmed factors and NOTE lines; tests `test_helm_units_note.py` (14); census 1 re-run ON refuses 3,654 of 86,291 lines (was 10,069), see `census/CENSUS_REPORT_GAP_LINES.md` section "Re-census after stage 1c". The ear itself: still nothing built, nothing trained, nothing run, no claim.
Owner word: "Yes, write both design packets at 0 USD: the recipe-shape proposer ear and the Eye pairing over the
28 cells with receipt tags first. Design only, no run." (2026-10-20, in reply to two wonders of the same day:
"WHAT IF WE TRAINED TRANFORMS ON ENTIRE CAS EXPRESSIONS AND OR RECIPES INCLUDED".)

## What this packet is, in plain words

HELM's brain is now the wide recipe brain (owner ruling 2026-10-20, spec sheet §7.56; §7.89, §7.96). It learns the
amount of each ingredient one unit of a dish needs, but only from a batch someone watched run out. It never invents an
amount. Its weak spot is the door: the deterministic English reader understands a closed set of sentence shapes, and
everything else becomes a question. The small translator model, the "ear" (CTT, 9,585,566 parameters), was built to
widen that door for stock sentences and earned no word (§7.90, §7.95).

This packet designs the ear's next job: **proposing the SHAPE of a recipe sentence, never its numbers.** Shape means:
which dish is being talked about, which ingredients are named, which line is a stock line and which is a witnessed
batch, which ingredient ran out, which face or purpose words are attached. The brain keeps every number, every unit
conversion, every receipt and every refusal exactly as today. The ear can only cause a sentence to be read that
today would be a question, and only after a read-back the user confirms.

## Files

| File | What |
|---|---|
| `README.md` | this page |
| `DESIGN.md` | the design: what the ear proposes, what the brain checks, the hard boundary, the data, the size |
| `TEST_PLAN.md` | the frozen test it must pass before any sealed package: arms, marks, hard gates, status words, mechanism-free baseline |
| `OPEN_QUESTIONS.md` | the picks the owner must make before anything is sealed (none needed before this packet) |

## What this packet does not do

- It does not authorise training. The owner's GPU lift of 2026-10-19 named the CTT packet; a recipe-shape ear needs its
  own owner word, package hash and cap.
- It does not change any claim status. The ear stays `ENGINEERED-NOT-VALIDATED`; the wide brain's two sentences stand.
- It does not let any model write a number, a name or a fact.

## Sources read for this design

`Documents\Codex\2026-10-19\cas_token_transformer_design_v1\ARCHITECTURE.md` (the ear, directions A and B, the hard
boundary); spec sheet §7.82, §7.90, §7.92, §7.95 (the ear's record), §7.83, §7.89, §7.93, §7.96 (the wide brain),
§10.1 (settled negatives: SDG-rendered text as a reading corpus); `helm_brain_wide.py` header (what grows and only
when; refusals; receipt and memory check); `helm_wide_turn.py` v5 (reader, relative amounts, `AMOUNT_RELATIVE`);
`DIAGNOSIS_K4.md` (the "half as much soda" defect); `recipe_shape_survey_v1\SURVEY.md` (1 of 13,686 real recipes fit
the licensed brain); owner rulings 2026-10-19 (separation: "separate the cas transformer from the brain") and
2026-10-20 ("YES TO WIDE BRAIN").
