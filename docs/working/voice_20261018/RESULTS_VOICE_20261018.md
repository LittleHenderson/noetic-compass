# Fix F results: HELM's everyday-English writer (2026-10-18)

Run on the laptop, stdlib Python only, one small process, 0 USD. Free RAM before the work: 848 MB; after: 676 MB.
Python: `C:\Python314\python.exe -X utf8 -B`. Branch `claude/voice-20261018`, cut from `origin/claude/project-thread-pmbzd6` at `3332ae36`.

Claim status: **ENGINEERED-NOT-VALIDATED**. The automatic checks below are real, run on 50 frozen situations. No person has rated anything yet. "Sounds like a person" is **open** until the owner (or other judges) fill `RATING_SHEET.md`.

## What was built

| file | what it is |
|---|---|
| `helm_voice.py` | The writer. Receipt in, 1-3 sentences of plain English out. Deterministic. No second model. |
| `phrasebook.json` | 113 phrasings over 10 situations (8 to 18 each), each tagged with a Register, plus 60 dialogue-act tails (3 question-back and 3 offer per situation) and 2 plain fallback templates per situation. |
| `test_helm_voice.py` | 21 unit tests. |
| `fluency_test_50.py` | The automatic fluency harness: 50 frozen situations, old renderer vs new writer. |
| `helm_chat.py` (edited) | Recipe turns now speak through the writer. The user's own amounts are kept. The old adapter text is still shown in the diagnostic mode. |
| `docs/working/voice_20261018/` | Phrase miner + its output, phrasebook builder, 50 situations, harness output, rating sheet, rating key, this file. |

**How it works, in plain words.**
- The brain's receipt names one of 10 situations: success, blocked by a missing ingredient, can't determine, don't know, needs one amount, refused, learned something, repaired something, never taught, faded.
- The writer picks one sentence from the phrasebook for that situation and tone.
  - The first pick is fixed by the receipt's hash.
  - If that sentence was used in the last 3 turns of the same kind, a seeded alternative is drawn (up to 8). This is the rb_c4 restart-fallback rule. The seed is saved in the trace.
- A guard then reads the sentence back.
  - It pulls out the numbers, ingredient names and outcome words, and compares them with the receipt.
  - A sentence that fails is refused, and the plain template is used instead.
- Tone is chosen from the user's words:
  - warm (f) by default;
  - analytical (A) when they ask for detail;
  - hands-on (E) for "step by step";
  - big-picture (T) for "overall".
- A reply can end as a plain statement, a question back, or an offer.
- The writer reuses the user's own words when the receipt confirms them. Example: "you said you had 5 lbs of flour".
  - It only quotes them if the brain's number is the same.
  - It also notices repeats: "Flour is the bottleneck again", "Still no water".

**Where the phrasings came from.**
- 26 of 113 are seeded from a cited source: the roadmap §2.6 right-hand column (10), the 15 HOW_IT_TALKS examples (12), the CCE fixed forms (7), and the SDG corpus (3).
- The other 87 were written fresh.
- The SDG corpus was streamed, not loaded. All 5,268 rows were read: `wave3_step2_5_english_descriptions_20260508T203848Z` + `...20260509T002355Z` + `...20260509T002541Z`; hashes are in `SDG_PHRASE_MINING.json`.
- **Honest limit on the SDG source.** Those rows describe CAS expressions. They contain no everyday wording for a limiting ingredient, a missing ingredient or a yield number. What they do have is the connecting language for "these inputs make that outcome": "To produce …" in 380 rows, "together these produce" in 164, "these inputs together yield" in 88, "combine … with" in 86.
- Those frames seed 3 success phrasings. They cite 7 seed_ids: seed_recipe_00060, 00081, 00150, 00163, 00229, 00441, 00459.

## Tests run (all on the laptop)

| suite | result |
|---|---|
| `python -X utf8 -B test_helm_voice.py` | **Ran 21 tests, OK** |
| `python -X utf8 -B test_helm_chat_nuance.py` (existing; recipe turn now goes through the writer) | **ALL HELM CONVERSATIONAL NUANCE TESTS PASSED** (21 [PASS] lines) |
| `python -X utf8 -B -m pytest -q test_helm_end_to_end_loop.py` (existing; old adapter untouched) | **11 passed** |

One unit test plays every phrasing and every tail through the guard with sample receipts. All pass. All plain templates also pass.

## The 50-situation automatic results

- Situations file: `FLUENCY_50_SITUATIONS.json` (sha256 `2ed221df1a3810ba785ba4c41ef428b678aa1f36c033d2576e63ee955034cf0d`), played as one conversation.
- Phrasebook: sha256 `f92d5e19e4cf3083…` (full hash in `FLUENCY_50_OUTPUT.json`).
- Full per-situation output: `FLUENCY_50_OUTPUT.json`.

| check (same code for both) | OLD | NEW | good or bad |
|---|---|---|---|
| CAS tokens + jargon words, total | 109 | **0** | good: the old one spoke CAS (entropy, valve aperture, receipt, 40-digit, Ω_) in 19 of 50 replies |
| replies containing any CAS token | 19 | **0** | good |
| back-to-back identical replies | 9 | **0** | good |
| sentences said more than once (anywhere in the 50) | 18 sentences, 77 extra times | 3 sentences, 4 extra times | good; the 3 are full-sentence reuses 10+ turns apart |
| facts preserved (key facts said, no invented number, no invented name, no false "exactly") | 22 / 50 | **50 / 50** | good |
| facts preserved, only the 34 situations the old one has a form for | 22 / 34 | **34 / 34** | good |
| facts preserved if the old "40-digit" boilerplate is forgiven | 32 / 50 | 50 / 50 | the fair comparison; old still says "exactly 18.003" (true value 18.0029…) and "exactly 3.333" (true value 10/3) |
| outcome words right (says "can make" for a success, "missing" for a block, and so on) | 34 / 50 | **50 / 50** | good |
| reading grade, mean (Flesch-Kincaid, simple syllable count) | 6.25 | **3.06** | good: easier to read |
| reading grade, median | 7.17 | 2.8 | good |
| words per sentence, mean | 12.7 | 10.49 | good |
| words per sentence, variance | 47.57 | 14.31 | **not better.** The old number is high because long jargon lines sit next to short ones. The new one is more even. More rhythm variety is still to do. |
| replies of 1-3 sentences | 35 / 50 | **50 / 50** | good |

What the old renderer could not say at all:
- learned (4 situations), repaired without a yield (2), never taught (4), faded (4).
- For these it answered with its generic "I can't answer that question…" sentence. That is why it fails facts there.
- Repaired with a yield (2) got the old success sentence, which names Flour by default.

New writer internals on the 50:
- guard PASS 50 / 50;
- plain template needed 0 times;
- seeded fallback fired 17 times;
- 45 different phrasings used;
- registers: f 46, A 1, E 2, T 1. Only 4 users asked for detail, steps or the big picture.
- acts: statement 17, question 18, offer 15;
- the user's own words quoted back 9 times.

## Before and after (exact outputs)

Situation 1. User: "We have 5 lbs of flour, some sugar and butter. How many loaves can we bake?"
- OLD: "All set! Based on your ingredients, we can produce exactly 8.452 units. Your bottleneck (limiting ingredient) is Flour with 5 on hand, which sets the ceiling for this batch. (Verified with exact 40-digit Decimal precision; novelty entropy: 0.12, valve aperture: 0.5) [receipt: 9f1c2a7b3d4e5f60]"
- NEW: "Going by the 5 lbs of flour you mentioned, you can make about 8.45 loaves. That's the part that runs out first. I can check other ingredient amounts too, if that helps."

Situation 15. User: "How much baking soda goes in the quick bread?" (receipt: FADED, baking soda)
- OLD: "I can't answer that question because it doesn't match any verified facts or physical recipes in my system. What specific materials, tools, or goals would you like to work with?"
- NEW: "I learned baking soda before, but it's slipped, and I'd want a refresher. If you remind me, I'll go over it again."

Situation 5 (the same "no water" receipt, second time in a row):
- OLD: the same two sentences again.
- NEW: "Still no water, so I'm holding off again. I can tell you how much water the recipe calls for, if you want."

## Rough edges and what was not done

- **Not done: human judging.** `RATING_SHEET.md` is ready. It is blind A/B: the order of old and new is shuffled with seed 20261018, and the key is in `RATING_KEY.json`. It asks the three 1-5 questions.
- **Countable nouns stay singular.** The writer says "Do you have any more egg around?" and "Once you have egg". A plural rule is not built.
- **Some gap and faded lines read stiffly** when the item is a long phrase. Example: "How much yeast rye bread needs used to be solid for me…".
- **The chat hook covers recipe turns only.** These are the brain's receipts: success, missing-ingredient halt, brain refusal, clarify.
  - The other chat paths keep their existing hand-written replies, because their tests pin exact words. Those paths are greetings, feelings, jokes, the general-knowledge refusal and the agentic plans.
  - Learned, repaired, faded and never-taught receipts do not reach the chat yet: the live loop does not produce them. The writer and the harness handle them.
- **The live loop still fills unknown amounts with 10.** "5 lbs of flour" is read by the loop as 10 Flour; removing that is Fix C. Because of the guard, the writer will not say "you said 5 lbs" when the brain used 10. It just says what the receipt says.
- **The outcome-word guard is a word list.** It is checked against every phrasing in the book, but a new phrasing needs the self-test (`test_every_phrasing_and_tail_passes_the_guard_when_eligible`) to pass before use.
