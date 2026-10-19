# Fix H — everyday English IN (2026-10-18)

Plain sentences about stock and recipes no longer get "say it another way". A deterministic reader restates them
in the checked form the loop already verifies, and the turn then runs exactly like a checked-form turn.

Laptop only, stdlib Python, 0 USD. Platform of every number below: **Windows 11, Python 3.14.0** (not run on Linux).

Claim status: **ENGINEERED-NOT-VALIDATED.** The reader handles a closed set of sentence shapes about the brain's
8 ingredients and 4 recipes. It is not a general English reader. Nothing here was rated by people. The brain's own
license (c34 `R1_BEATS_GB3`) stays **synthetic worlds only**.

## What changed, per file

| File | Change |
|---|---|
| `helm_english_in.py` (new) | The reader. `read(text, ingredients, products, last_topic, known_units)` returns `CONTENT`, `WITNESS`, `CLARIFY` or `NOT_MINE`. Every `CONTENT` / `WITNESS` reading is rendered with `language_v3/cce.py` and parsed back; it is used only if `parse(render(C)) == C`. Number, hedge and "no/not/without" words are the frozen ALIAS-WIDE lists (`ALIAS_WIDE_LEXICON_v0_1.json`, sha256 `d199611397d4d8ff5c215095d3424327917e4da9fcd5676e52cdd8c047a8b2e0`; `lexicon_v2` keeps these three lists unchanged, checked by a test). Ingredient and product words: the brain's 8 + 4 names plus a labeled plural table (`EVERYDAY_NAMES`, OUR_CONVENTION). |
| `helm_end_to_end_loop.py` | `_not_checked_turn` asks the reader first. `CONTENT` -> the reader's checked-form sentence goes through the same `verify_cce_round_trip` and the same `_checked_turn` (gate, brain, store, receipts). `WITNESS` -> `witness_batch`. `CLARIFY` -> status `CLARIFY_ENGLISH_<code>`, zero writes. New trace station `English in`. Also: a stated absence is now recorded in the store and never glued back from an older stored amount (see "A bug this exposed"). Messages are honest when stock was saved in the same turn as a "can't tell yet". The trace function writes a NEW file; the fix-C trace is untouched. |
| `helm_chat.py` | Stock/recipe English goes to `loop.process_turn` (one path). The side parser (old Step 7a, `extract_ingredient_quantities` + `update_inventory`) and the old Step 9 are gone. The chat's inventory is a mirror of the loop's verified stock. The loop writes into the conversation memory's own cube store, so a pantry question reads exactly what the loop saved. Every everyday reply goes through `helm_voice`. |
| `helm_memory.py` | `AnaphoraResolver` no longer adds "add 10 water"-style amounts to the inventory behind the loop's back (a second side parser). The mention is kept as an entity only. |
| `helm_voice.py` | `say_reader_question` (the reader's questions, 22 codes, 2 wordings each), `say_stock_noted` ("Got it: I've recorded 12 cups of flour on hand."), both through a guard: no CAS words, and every number and food name must come from the user's words or the reader's slots. `MOOD_FACT_CLASH_CHECK` (below). `receipt_from_loop_result` maps `CLARIFY_ENGLISH_*`, the new "there's no X on hand" line, the yield's unit ("6 loaves" when the batch was taught in loaves) and the learned requirement ("one bread needs 2 flour"). |
| `test_helm_english_in.py` (new) | 31 tests. |
| `test_helm_end_to_end_loop.py`, `test_helm_voice.py` | 3 tests updated, each because it pinned the old stopgap behaviour (listed below). |

## What English now works end to end

| You say | What happens |
|---|---|
| "We have 50 flour, 30 sugar and 20 butter" | 3 stocks. Checked form `There is 20 of Ω_Butter. There is 30 of Ω_Sugar. There is 50 of Ω_Flour.` |
| "there's 12 cups of flour" | stock 12, unit words "12 cups of flour" kept in the receipt; nothing converted |
| "we have 2 dozen eggs" / "we have three eggs" | 2 (unit "dozen", never turned into 24) / 3 |
| "we're out of water", "no water", "we ran out of water", "the water is all gone", "there is 0 water" | `There is no Ω_Water.` |
| "can we bake bread?", "how much bread can we make?", "how many loaves can we make?", "what about bread?" | `Topic: Ω_Bread.` |
| "bake a batch" | the product the conversation is already on; if there is none, "Which one do you want me to work out: bread, frosting, starter, or meringue?" |
| "we made 5 loaves from 10 flour and 8 water and ran out of flour" | a witnessed batch -> `witness_batch` -> the brain's own writer |
| "We have 12 cups of flour and no water. Can we bake bread?" | all three in one turn |

Chat transcript (everyday mode, deterministic; recorded 2026-10-18):

```
You: We have 50 Flour, 30 Sugar, and 20 Butter.
HELM: Got it: I've recorded 50 flour, 30 sugar, and 20 butter on hand.
You: We made 5 loaves from 10 flour and 8 water and ran out of flour.
HELM: Got it, now I know one bread needs 2 flour. Did I get that right?
You: we baked 2 loaves with 10 flour and 2 water; the water ran out first
HELM: I learned something new: one bread needs 1 water. Tell me if there's more to it.
You: We have 12 cups of flour and no water.
HELM: Noted and recorded: 12 cups of flour and no water.
You: Perfect! Can we bake bread?
HELM: We're out of water, so I held off on the batch rather than guess. I can tell you how much water the recipe calls for, if you want. You said 'perfect', but there's no water on hand that I know of. Did you mean that? Nothing was saved.
You: Now we have 9 cups of water. How much bread can we make?
HELM: Got it: I've recorded 9 cups of water on hand. Going by the 12 cups of flour you mentioned, you can make exactly 6 loaves. That's the part that runs out first.
You: Bake a batch.
HELM: Same story with the flour: it runs out first, and it caps you at exactly 6 loaves. Is that enough for what you need?
```

## What still gets a question back (never a guess)

| Code | Example | HELM says |
|---|---|---|
| `UNKNOWN_INGREDIENT` | "We have 20 chocolate and 3 flour" | "I don't know an ingredient called chocolate. I only keep track of flour, water, sugar, butter, milk, eggs, yeast, and salt." |
| `UNKNOWN_PRODUCT` | "Can we bake a cake?" | "Cake isn't something I have a recipe for. I can work out bread, frosting, starter, and meringue." |
| `NO_NUMBER` | "we have some milk" / "we have eggs" | "How much milk do we have? ..." / "How many eggs are there?" |
| `APPROXIMATE` | "We have about 4 eggs" | "I need an exact number, not about 4 eggs. How many eggs are there?" |
| `WHAT_IF` | "Can we bake bread with 20 flour?" | "Is 20 flour what we have right now? If it is, say \"we have 20 flour\" and I'll work from it." |
| `RELATIVE_AMOUNT` | "Add 10 water and bake" | "Is that 10 water all together, or on top of what we had? I'd rather ask than guess." |
| `UNIT_MISMATCH` | "We have 2 pounds of flour." after cups | "You switched flour from cups to pounds. I don't convert units, so which should I go with?" |
| `CONVERSION_REFUSED` | "convert 2 pounds of flour to cups" | "I don't convert between cups and pounds. That would be a guess on my part. ..." |
| others | `NEGATED_AMOUNT`, `WHAT_IF_ABSENT`, `PRODUCT_AS_STOCK`, `NO_INGREDIENT_NAMED`, `CONTRADICTION`, `MULTIPLE_PRODUCTS`, `WHICH_PRODUCT`, `STATED_RECIPE`, `BATCH_NEEDS_RAN_OUT`, `BATCH_TWO_RAN_OUT`, `BATCH_NEEDS_MADE`, `BATCH_NEEDS_PRODUCT`, `BATCH_NEEDS_STOCK`, `ROUND_TRIP_FAILED` | one plain question each (`helm_voice.READER_QUESTIONS`) |

Every one of these writes nothing (`cubes_written == []`, tested).

Text the reader does not claim ("Write code for a beehive counter", "I'm feeling tired", "What do we have in stock?",
"I love bread") goes to the old paths unchanged.

## MOOD_FACT_CLASH_CHECK — `ENGINEERED-NOT-VALIDATED`, reported only

HELM does **not** understand sarcasm. This is one written rule. When the user's words carry one of 10 positive mood
words (great, perfect, love it, wonderful, awesome, fantastic, excellent, amazing, brilliant, lovely; not counted when
negated, "not great") AND the brain's receipt is a refusal, a missing ingredient or an "I can't tell", the voice adds
one question: "You said 'perfect', but there's no water on hand that I know of. Did you mean that?" It never changes
the facts: the test checks the reply without the mood word is an exact prefix of the reply with it.

## Tests (recorded output: `docs/working/traces/TEST_OUTPUT_ENGLISH_IN_20261018.txt`)

| Suite | Result |
|---|---|
| `test_helm_english_in.py` (new) | **Ran 31, OK** — reader per sentence type (9), refusals (5), no new facts (2), round trip (3, incl. the lexicon_v2 agreement check, which ran and passed), loop integration (6), chat end to end (2), mood clash (4) |
| `test_helm_end_to_end_loop.py` | **Ran 18, OK** (test_14 and test_18 updated) |
| `test_helm_voice.py` | **Ran 22, OK** (test_chat_speaks_recipe_receipts_through_the_voice updated) |
| `test_helm_chat_nuance.py` (pytest) | **5 passed** — no assertion changed |
| language_v3 `run_suites.py` | lm_t1 **26**, lm_t1b **11**, lm_t1c **5**, lm_t1v3 **26** — ALL SUITES OK |
| language_v3 `test_lexicon_v2` | **Ran 19, OK** |
| `repair_performer/test_all.py` | **RESULT: ALL PASS** |
| `tks_meta_valve_controller.py` self-test | **3 written-rule cases PASS** |
| `fluency_test_50.py` rerun | outputs **byte-identical** (git diff empty) |
| pyflakes 3.4.0 | new and rewritten files clean; `helm_chat.py` 4 and `helm_memory.py` 5 warnings, all present on base `077c0353` (helm_chat had 5 there) |

**Tests updated, and why (each pinned the old stopgap, not a wanted behaviour):**
- `test_14_unparseable_english_clarifies_with_zero_writes`: it required "How much bread could we bake with whatever
  is around?" and "We have 50 Flour and 30 Sugar." to be refused. They are now read (that is fix H). Unclaimed
  English still gets `CLARIFY_NOT_CCE` with zero writes; the two sentences are now checked as read.
- `test_18_live_trace`: tick 5 is now `UNDETERMINED_CLARIFY` (read as bread, water unknown) instead of
  `CLARIFY_NOT_CCE`; two ticks were added; the `English in` station is required.
- `test_chat_speaks_recipe_receipts_through_the_voice`: it pinned "free English is refused" and "the stock sentence is
  spoken outside the voice" (1 voice trace). Its own comment said it waited for the English-in path.
- `test_helm_chat_nuance.py`: **no assertion changed**. Sequence B turn 1 still sees "recorded" and `inventory["Flour"]
  == 50`, now from the loop's verified stock; the pantry probe now reads cubes the loop wrote.

## The live trace (new file beside the old one)

- New: `docs/working/traces/HELM_LIVE_TRACE_ENGLISH_IN_20261018.jsonl` — 136 lines, sha256
  `678c907611fbcf64924bd22524e6ff5a9e517f2a4316885865a4fe97f6062b87` (also in the `.sha256` file beside it).
  Made by `C:\Python314\python.exe -X utf8 -B helm_end_to_end_loop.py`.
- Old (fix C), untouched: `HELM_LIVE_TRACE_20261018.jsonl`, sha256
  `4f94ccee22ea9829072ebfd59fe7690f56d3f28f49527cf2f39b140283fe6fba` (re-checked after the run).

| tick | in | result |
|---|---|---|
| 1-4, 6-10 | as in the fix-C trace | same statuses as before |
| 5 | "How much bread could we bake with whatever is around?" | was `CLARIFY_NOT_CCE`; now read as `Topic: Ω_Bread.` -> `UNDETERMINED_CLARIFY` (water unknown), 0 writes |
| 11 | third session, same store and brain: "We have 12 cups of flour and no water. Can we bake bread?" | `UNDETERMINED_CLARIFY`, gap "the stock of Ω_Water" (same as checked-form tick 4); the store's older 9 water is NOT glued back because the user said it is gone |
| 12 | "Now we've got 9 cups of water — how much bread can we make?" | `SUCCESS_EVALUATED`, 6 Bread, Flour runs out first; brain receipt `48ee0b4bac4d2567`, **identical** to checked-form tick 7 |

## A bug this exposed (fixed)

Before: "There is no Ω_Water." only removed water from the session's working stock. The repair child then fetched an
older stored water amount from the cube store and glued it back, so HELM computed bread with water the user had just
said was gone. Now the absence goes through the gate and a round trip, is written to the store (and read back), and
the child refuses to glue a said-gone ingredient. Test: `test_said_gone_is_never_glued_back_from_the_store`.

## Limits, plainly

- **Closed shapes only.** It reads the sentence types above. Other phrasings of the same idea may get `NOT_MINE`
  (old CLARIFY) — e.g. "we're out of chocolate" alone is not claimed (no known word).
- **Units are compared, never converted.** A unit word is checked against the unit that ingredient was given in
  before. A plain number ("50 flour") and a unit ("12 cups") are NOT compared: a plain number carries no unit to
  disagree with. So a batch taught in plain numbers and stock given in cups are put on one scale without a question.
  That is an open gap, stated here, not a hidden conversion.
- **All or nothing.** If any part of a turn needs a question, nothing in that turn is saved ("We have 6 eggs. Bake a
  batch." with no product on the table asks which product and does not save the eggs).
- **"bake a batch"** means bread only when bread is already the subject. The first time, HELM asks which one.
  (The order's example mapped it straight to bread; that would be a guess.)
- The pantry listing still prints brain names ("12 Flour"), not the user's words. Countable nouns in the old
  phrasebook lines stay singular (fix F's known rough edge).
- People have not rated any of this.
