# HELM-R1 wave 6 (c48): why mark K4 was missed (diagnosis, 2026-10-20)

Status: post-run diagnosis on a SPENT exam. Nothing here changes the c48 reading. The status word stays
`WIDE_WAVE_NO_GAIN`. The fix below is `ENGINEERED-NOT-VALIDATED`: it is NOT re-tested on any sealed exam.

## Said plainly first

- The one unexplained ask came from ONE recipe: a cake whose last line reads "1 teaspoon of cream tartar, and half
  as much soda".
- The wide reader read "half as much soda" as a new, separate ingredient named **"as much soda"**, with an amount of
  **1/2 and no unit**. That ingredient does not exist. The recipe has five real lines.
- That made-up ingredient never "ran out" in any teaching batch, so the brain never learned its requirement.
  At the question, the gate saw one unlearned requirement and the wide path asked instead of answering.
- The rule UNSETTLED_ASK is not involved. The same ask happens with it off.
- **Verdict: an engineering defect in the reader** (a relative amount read as an absolute amount of a made-up
  ingredient). It is not a true design limit. A fix is built (reader v5) and tested on our own practice recipes only.

## Exam files opened (X6 is spent; opened for this diagnosis only)

The operator opened, after scoring, these files in `x6_custody\exam\` (sha256):

| File | sha256 |
|---|---|
| `KEYS_REAL_X6.json` | `312fb3505eafc89fa791cab2de7a801e1fbd956514ed29a2db4ed7b051f321e6` |
| `INPUTS_REAL_X6.json` | `7017fabe3ff1730e8005648e9e30254c556d40490cf8c61beea3928a20bd9ea8` |

No other exam file was opened or parsed. No fix was tuned or checked on X6. Host records read:
`deliverable_unpacked_a1\results\r1w6_host_run\out\r1w6_out\W6_X6_REAL\FULLP_WIDE.json` and `FULLP_WIDE_NOASK.json`.

## How the item was found

Script `diagnosis_k4/find_k4.py` (output `find_k4_output.txt`) re-ran the frozen scoring rule `rbw1t.keys_rbw1t.unexplained_ask` (the same function
`r1w6/score_w6.py` calls) over every X6_REAL key against the host records. Exactly one item matched, in both arms:

- **Recipe id:** `RW:pg:42450@476327` (cell `C46:MIXED`, product "cake", 5 lessons, 5 key lines).
- **Turn:** turn 7 of 7, "How much cake can we make?" Status `UNDETERMINED_CLARIFY` (FULL+WIDE and FULL+WIDE_NOASK).
- **Key:** `ANSWER`, yield `1/3`, limiting line 1 (butter). All 5 lessons scored `LEARNED`; the stock turn was
  `STOCK_RECORDED`. So by the frozen rule it was an ask on a fully learned, answerable recipe.
- HELM's own words at turn 7: "I still need one batch where as much soda ran out first while everything else was
  left over. I didn't guess."

## Replay on the laptop (sealed v2 code)

`diagnosis_k4/replay_k4.py` (output `replay_k4_output.txt`) fed the 7 turns through the fresh extract
`reading_pkg\HELM_R1_W6_20261019\helm_now\` with `HELM_WIDE_BRAIN=1`. File hashes:
`helm_wide_turn.py` `ce843711c9a88348cb5778170324b45f823e9bc95cd7e9e699c1916fedb7aaa0`, `helm_brain_wide.py`
`a0c60162f01a610ab6156e0806be41435bc40a9c7cbbed956b085610ca2969f4` (both equal to the source-cut commit
`221cab70` and to `claude/project-thread-pmbzd6` at `93379316`). The replay matched the host record exactly:

- turns 1-5 `WITNESS_ADMITTED`; turn 6 `STOCK_RECORDED` with six stock lines, the sixth
  `'as much soda': ['1/2', '']`;
- turn 7 `UNDETERMINED_CLARIFY`, brain gate `G1`, `unlearned ['as much soda']`;
- support `['sugar', 'butter', 'flour', 'milk', 'cream tartar', 'as much soda']` (the host's `wide_audit` also shows
  6 support slots, 5 coefficients).

## The code path (sealed v2 lines)

1. `helm_wide_turn.py:233` `split_lines`: `if not out or starts_line(seg):` asks whether the piece
   "half as much soda" begins a new line.
2. `helm_wide_turn.py:209` `starts_line`: `got = W.match_amount(s, 0)` finds an amount at the start of the piece.
3. `helm_brain_wide.py:119` (`AMOUNT_RX`, alternative `half`) and `:129` (`_word_amount`: `half` -> 1/2) read the
   word "half" as the amount 1/2. So the piece starts a new line.
4. `helm_wide_turn.py:146` / `:175` `parse_line`: amount 1/2, no unit word, then `name = bind_name(rest)` binds
   the rest, "as much soda", as an ingredient name.
5. Every lesson and the stock turn carry this sixth line; it never runs out, so its requirement stays unlearned.
6. `helm_wide_turn.py:871` `unlearned = brain.unlearned(product)` -> `['as much soda']`; the RPM gate does not
   proceed (`:885`), and `:888` returns `UNDETERMINED_CLARIFY`.

The same family has a second, quieter flaw in v4: "twice as much X", "as much X" and "the same amount of X" do not
start with an amount word, so `starts_line` returned False and they were kept as a NOTE and silently ignored.

## Defect or design limit?

**Engineering defect.** The reader invented an ingredient name and an amount (1/2, no unit) that the person never
said. That breaks the reader's own rule ("Never invents an amount"). It can also go the other way: if the made-up
"as much soda" had been taught as running out, the brain would have learned a wrong number.

What is a design limit, and stays one: the wide brain answers only from exact requirements. It never uses "at most"
bounds from batches where an ingredient was left over. The fix does not need that, and does not add it.

## The fix (reader v5, `helm_wide_turn.py`)

- A relative amount ("half as much X", "1/2 as much X", "twice as much X", "as much X", "the same amount of X",
  "a third as much X", "three times as many X", ...) now belongs to the line right before it.
- The two are kept as ONE bundled line: "1 teaspoon cream tartar, and half as much soda" -> ingredient
  `cream tartar and half as much soda`, amount 1 teaspoon.
- Why this is exact, not a guess: the bundle always holds its parts in the stated proportion r. A batch where either
  part ran out first teaches max(a_Y, a_X / r) per unit, in Y's unit. Stock of the same bundle then gives
  Y_stock / that, which is exactly the smaller of the two parts' limits.
- Safety: stock that names the parts any other way (Y alone, X on its own line, another proportion) is a different
  line, so HELM asks. A relative amount with nothing before it, "... as much X as Y", two relative amounts on one
  line, a line relative to itself, or a proportion outside a small fixed table -> one question (`AMOUNT_RELATIVE`),
  nothing saved.
- Regression tests: `test_helm_wide_alongside.py` class `D_RelativeAmountIsOneBundledLine`, 5 tests, built on our
  own practice recipes (scones; biscuits where the second part of the bundle runs out and limits). No X6 item used.

## What a re-run needs

A new seal (v3) with a FRESH custodian draw, a new owner word, and a cap of 1 USD. X6 must not be used again.
