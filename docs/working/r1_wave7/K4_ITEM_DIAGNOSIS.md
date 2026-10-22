# K4 item diagnosis — c52's one unexplained ask (HELM-R1 wave 7 v4, job c52; laptop, 0 USD; 2026-10-20)

Plain English. The exam text is sealed: this note names the item by its id and describes its shape in the author's own
words. No recipe line, dialogue line or pantry line from the exam is quoted here.

## 1. What the reader said

`R1_W7_READING.json` (sha256 `bcb2f372a4c9c1600d86ce17c96fe15fec6a0969324c33f9250706f6fd38dd8b`), mark `K4_HONEST`:
`unexplained_asks_strict` 1, `unexplained_asks_w6_rule_reported` 1, `not_routed_scored_turns` 0, `unsettled_ask_fired` 0,
deviation `D-W7-9`, value FALSE. The reader's summary rows do not name the item.

The rule (read from the sealed v4 package, `r1w7/score_w7.py` -> wave 6's `r1w6/score_w6.py` -> RB-W1T's
`rbw1t/keys_rbw1t.py`, function `unexplained_ask`): an ask is UNEXPLAINED when all four hold at once —
(a) the item's key is `ANSWER`; (b) every lesson line scored `LEARNED` (admitted, bound to its own line, exact amount);
(c) the stock turn's status is `STOCK_RECORDED`; (d) the question turn's status is not an answering status (`ASKS`).
So an ask is "explained" whenever at least one lesson was refused or asked about, or the stock was not recorded. The
wave-6 rule (`unexplained_asks`) additionally forgives an ask whose question turn fired `CLARIFY_WIDE_UNSETTLED_SAME_NAME`
on a head-artifact item (D-W6-12); that did not fire here, so both counts read 1.

## 2. The item

Found by program over the unit outputs in `run_c52_r1w7v4_20261020\deliverable_unpacked_a1\...\r1w7_out\units\`:
the only REAL record whose lesson turns all read `WITNESS_ADMITTED`, whose stock turn read `STOCK_RECORDED`, and whose
question turn read an asking status.

| Fact | Value |
|---|---|
| Item id | `RW:pg:17438@21087` (X7_REAL, 4 lesson lines) |
| Arms showing the ask | `CHAT_ON` and `LOOP_ON` (and `CHAT_ON_REPLAY` / `CHAT_DIAG`, which equal `CHAT_ON`); the same statuses turn by turn in both |
| Lesson turns | 4 of 4 `WITNESS_ADMITTED`, path `wide`, reason `ADMITTED`; the licensed path's own status on each was `CLARIFY_ENGLISH_UNKNOWN_INGREDIENT`, so the wide reader took every turn |
| Stock turn | `STOCK_RECORDED`, path `wide` (licensed path `CLARIFY_ENGLISH_UNKNOWN_INGREDIENT`) |
| Question turn | `UNDETERMINED_CLARIFY` (inner status the same), `value` null, `limiting` null, `writes` 0, `routed` true (chat) |
| Wide audit of the lessons | `coefficients` 4, `support_slots` 5, `within_support` true, `ok` true — the brain's support set for the dish holds FIVE names while the recipe has FOUR ingredient lines |
| What the chat said (shape, not the words) | after each lesson it acknowledged the amount it learned and listed the ingredients it still needed a batch for; that list always carried one name that is not an ingredient (the condition word); at the question it said it could not answer yet because it still needed a batch where that non-ingredient "ran out first", and that it did not guess |
| What the loop said | the same sentences (the chat's voice adapter changes nothing on this item) |

## 3. The shape of the recipe, in my own words

Each lesson sentence (a batch the person made) and the stock sentence list the ingredient amounts, and one of the
ingredient lines carries a TEMPERATURE as a note right after it: an amount followed by the words for "degrees
Fahrenheit", set off by commas, with no "of <ingredient>" after it. The recipe has four ingredient lines; the key
(X-REAL's `key_r`, which the custodian computed from the raw lines) counts four lessons and treats the temperature as part
of the line it follows. Every one of the four real lessons was learned exactly, and the stock was recorded for all four.

## 4. The code path that produced the ask (HELM cut `dfc7158d`, the v4 `helm_now/`)

1. `helm_wide_turn.read_wide` matches the batch sentence (`WITNESS_RX`) and hands the ingredient list to `parse_lines`.
2. `parse_lines` -> `split_lines` cuts the list at separators; for each piece after a separator it asks `starts_line`
   whether the piece begins a NEW ingredient line. `starts_line` says yes to any piece that begins with an amount
   (`W.match_amount`), so the temperature piece ("<number> degrees Fahrenheit") became a line of its own.
3. `parse_line` on that piece: amount = the number; the word after it is not a unit (`W.unit_of` None) and not in
   `OTHER_UNIT_WORDS`; `bind_name` of the rest gives a name made of the condition words ("degrees fahrenheit").
4. The batch now has five names. `helm_brain_wide` admits the batch (`WITNESS_ADMITTED`) with a five-name support set and
   learns the coefficient of the ingredient that ran out; the condition "ingredient" gets a slot and never runs out.
5. The stock sentence goes the same way (`STOCK_RX` -> `parse_lines`), so the stock also carries the fifth name, and
   `take_over` accepts it (every name is "known" to the book), `STOCK_RECORDED`.
6. At the question, `_wide_question` finds the dish still has an unlearned name (`unlearned(product)` is not empty: the
   condition slot) and answers `UNDETERMINED_CLARIFY` ("I still need one batch where <condition> ran out first").

Reproduced on the laptop from the unit's recorded turns (`scratchpad\repro_k4_item.py`, which reads the turns by
program and prints statuses only): on the v4 cut, reader shapes show five bound names on every lesson and stock turn
(four ingredients + the condition name); loop driven directly: 4 x `WITNESS_ADMITTED`, `STOCK_RECORDED`,
`UNDETERMINED_CLARIFY`; chat (`HELMConversationalSession.handle_turn`, everyday mode): intents all
`RECIPE_FOUNDATION_LOOP`, gate codes PROCEED x4, GATE_PASS, REPAIR, the last reply the "can't say yet" ask.

On the fixed cut (`f45a8570`): four bound names on every turn; loop 4 x `WITNESS_ADMITTED`, `STOCK_RECORDED`,
`SUCCESS_EVALUATED` with value `1/2` and the limiting ingredient the fourth line's; chat gate codes PROCEED x4, GATE_PASS,
PROCEED, no "can't say". (The key's own answer is not read here; the reader will score it on a fresh draw. By hand from
the recorded amounts: three of the four ingredient ratios are 3/4, 4 and 3/2; the fourth is 1/2, the smallest — the
fixed answer matches the arithmetic.)

## 5. Why the reader counts it unexplained under D-W7-9

Key `ANSWER` (the reader scored it among the 94 representable ANSWER-keyed items), all 4 lessons `LEARNED` (admitted,
each bound to its own line, amounts exact), stock `STOCK_RECORDED`, question `UNDETERMINED_CLARIFY` = `ASKS`. Nothing the
rule forgives happened: no lesson was refused, no stock was refused, `CLARIFY_WIDE_UNSETTLED_SAME_NAME` did not fire. The
ask is a brain-side reading fault (the wide reader invented an ingredient), exactly what K4 exists to catch.

## 6. Every other ask on X7_REAL, by reason code (counts only)

`CHAT_ON`: 23 asking question turns over the 128 items; the reader counts 17 of them on ANSWER-keyed items (the other 6
sit on items whose key is not ANSWER and are `NOT_SCORED`; this note cannot say which 6 without opening the key file,
which it never does).

| Question-turn status | Lesson state before it | Stock turn | Count | Explained? |
|---|---|---|---|---|
| `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` | no lesson admitted (every lesson `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`) | `CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` | 16 | yes (lessons not learned) |
| `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` | no lesson admitted | `CLARIFY_ENGLISH_NO_INGREDIENT_NAMED` | 2 | yes |
| `UNDETERMINED_CLARIFY` | one lesson refused `TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH`, the rest admitted | `STOCK_RECORDED` | 2 | yes (one lesson not learned) |
| `UNDETERMINED_CLARIFY` | one lesson `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`, the rest admitted | `STOCK_RECORDED` | 1 | yes |
| `UNDETERMINED_CLARIFY` | no lesson admitted (`CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` x6) | `CLARIFY_ENGLISH_NO_INGREDIENT_NAMED` | 1 | yes |
| `UNDETERMINED_CLARIFY` | all 4 lessons admitted | `STOCK_RECORDED` | **1** | **NO — the item above** |

`LOOP_ON`: 26 asking question turns (reader: 19 asks on ANSWER-keyed items, 1 unexplained): `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`
22 (16 after `UNKNOWN_INGREDIENT` lessons, 2 after `NO_INGREDIENT_NAMED`, 4 after `CLARIFY_FACE_FACE_UNREAD` on the stock
turn — a loop-only status; the chat's routing takes those turns differently), `UNDETERMINED_CLARIFY` 4 (1 all-admitted
= the same item; 2 with one lesson refused; 1 with no lesson admitted).

`CHAT_OFF` (yardstick, licensed brain alone): 128 asking turns — `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` 113,
`UNDETERMINED_CLARIFY` 11, `NOT_ROUTED_TO_LOOP:GENERAL_KNOWLEDGE_INQUIRY` 4 (the reading's 4 unrouted).

So the 16 explained asks all come from recipes the wide reader could not bind at all (18 items where no lesson was
admitted) or where one lesson was refused (3 items). The fix below touches none of those paths: it only stops an amount
of a condition from becoming an ingredient. The 18 "no lesson admitted" items are a different, wider gap (lines the wide
reader refuses: ranges, approximate amounts, units with no exact size, names it cannot bind) and are negatives kept.

## 7. The two operator facts recorded with this diagnosis (c52 operator side)

1. The one unexplained ask has the same count in `LOOP_ON` (1) and the same item; the chat window is not the cause. The
   fix is in the wide reader (`helm_wide_turn.py`), not in `helm_chat.py`.
2. c52's 20 undetermined CONV items are the same S1 / S2 / S6 / S7 / R4 families as c51 and practice (a stock sentence
   carrying a face or purpose clause; the R4 past-tense lesson paraphrase), unchanged by v4 since v4 touched no HELM file.
   They are negatives kept; the fix here is NOT widened to them (the root cause — a condition amount read as an
   ingredient — does not cover them).

## 8. The fix (general rule, no special case) — commit `f45a85706a9d8b9177e4b7279453d1538c12045d`, PR #425

`helm_wide_turn.py`: `CONDITION_NOUNS` (temperature, time, head-count and percentage nouns; the wide reader's own copy of
the family in `helm_english_in.IGNORED_COUNT_NOUNS`) and `condition_fragment(piece)` (an amount followed by such a noun;
a bare `F` / `C` only when nothing follows it, so "2 c flour" stays two cups of flour). `starts_line` returns False for a
condition piece (it is a note of the line before it, like "a little salt"); `split_lines` holds a leading condition piece
for the first ingredient line; `parse_line` asks `NO_NAME` when a whole line is only a condition. `READER_VERSION` string
left as is (`test_helm_cas_address` pins the OFF-path trace bytes). `helm_brain_canonical.py` untouched.

Test `test_helm_wide_alongside.G_ConditionPiecesAreNotIngredients` (3 tests; the author's own muffin recipe in the same
shape, never the exam line): 3 of 3 fail on the thread head `1d2b390f`, 3 of 3 pass on the fix.

One limit found while writing the test, kept as a negative: the same stock sentence with plain unit words ("cups") and the
temperature in the middle is claimed first by the LICENSED English reader, whose stock-frame rule asks
`CLARIFY_ENGLISH_NO_STOCK_FRAME` for the amount after the temperature; that status is not one the wide path may take over,
so such a stock turn is not recorded. The exam item's sentences use unit words the licensed reader does not bind
("-fuls"), so the wide path took them. This is the licensed reader's own rule (helm_english_in v1.2), not the cause of the
c52 ask, and it is not changed here.
