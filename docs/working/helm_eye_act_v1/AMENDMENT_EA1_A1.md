# EYE-ACT-1 amendment A1 — the stock source, made complete for live use (written 2026-10-21 PDT, after the pre-code
# hash 0d731774…, BEFORE any code and before any scored or practice number)

Why: reading the live loop after the freeze showed three ways the wide stock changes legitimately, and the frozen rule
(section 1.1: "the latest qualifying `stock_on_hand (wide)` record") names only the first:
1. a wide stock turn (`S6 next` status `STOCK_RECORDED`): the `S2 Bias ^5` record `stock_on_hand (wide)` at that tick
   holds the FULL held stock after the update;
2. a withdrawal (`S2 Bias ^5` record `stock_withdrawn (wide)`, `helm_wide_turn._withdraw_mentioned_stock`): named
   ingredients are dropped;
3. a licensed-path stock turn (`S6 next` status `INVENTORY_RECORDED`, `helm_wide_turn.STOCK_DONE`): the wide path
   copies `read_wide(user text)["stock"]` into the wide stock with no wide record of its own.
Under the frozen rule the Eye would "restore" away (2) and (3) in live use: harm the exam would not see (made-up words
always take path 1).

Change (instrument only; no arm, fault, mark, gate threshold or status word changes):
- The verified stock is a fold over the loop's own trace in tick order: (1) set to the record's stock; (2) drop the
  withdrawn names; (3) update with HELM's own reader `helm_wide_turn.read_wide` applied to that tick's `user` record
  text (the user's own words, re-read by HELM's own reader). Question-time `stock_on_hand (wide)` records stay excluded.
- A held stock entry that the fold does not explain at all (a name with no source) is `SOURCE_MISSING`: in every mode
  the Eye HOLDS questions on it and never removes it (removing could undo a change the Eye does not understand).
  A name the fold explains with a different amount is `STOCK_DIFFERS` and is restored as frozen.
- One test is added for each of (2) and (3) and for the hold-never-remove rule.

The exam is unchanged by this amendment (its worlds use path 1 only); predictions unchanged.
