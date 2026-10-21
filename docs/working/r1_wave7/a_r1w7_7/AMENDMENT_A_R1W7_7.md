# AMENDMENT A-R1W7-7 — the custodian's MULTI_QTY rule (HELM-R1 wave 7; 2026-10-21)

**Owner's word (typed in the operator session, 2026-10-21):** "Yes to D6, the custodian MULTI_QTY rule, as amendment
A-R1W7-7." (Same message: "Merge PR #433 into the thread branch. Build D1 to D5 with tests, FIX FIRST, at 0 USD.")

## 1. What changes (plain English)

The real-recipe exam (X7_REAL) takes recipes from old books. The frozen key (RB-W1T's `xreal.keys.key_r`, vendored byte
for byte) treats every book line as one ingredient line, named by its first head word. A book line that holds TWO amounts
("6 cloves, 12 peppercorns" — the author's own example, in the shape of the c54 items) therefore becomes ONE lesson about
the first ingredient; the second amount is tail text the key ignores, the exam never makes that ingredient run out and
never doubles it, and nothing in the lessons can teach its requirement. The wide reader reads two ingredients, is never
taught the second, and asks — an honest ask that the K4 rule counts as unexplained (job c54, SPEC 7.108: 2 of 2 asks;
`K4_ITEM_DIAGNOSIS_C54.md`). No general reader rule can answer it without breaking ordinary lists.

Under this amendment the custodian's key marks such a recipe **not representable**: after the frozen key is computed,
every raw line that carries a SECOND amount after a separator (a quantity start of the frozen grammar,
`xreal.grammar.qty_starts`, after the leading amount, with ", " / "and" / "or" / ";" between them; parentheses removed
first; one amount such as "1-1/2" or "one and a half" is never two; a line the survey already refuses for its form keeps
its own reason) adds `line<i>:MULTI_QTY`
to `representable.why_not`, and `representable.representable` becomes False. The item then scores `NOT_SCORED` (an
undetermined key), exactly as recipes with a range, an approximate amount, an odd form or a unit outside the top-20
table already do (PREREGISTRATION representability rule). Nothing else in the key changes: answer, yield, lessons,
heads, limiting index are untouched. The frozen key package `HELM_RBW1T_20261019` is NOT edited; the rule sits in the
wave-7 package (`r1w7/multi_qty_w7.py`) and is applied once, in `custody_w7.make_all`, to the real keys.

## 2. Files

| File | Role |
|---|---|
| `r1w7/multi_qty_w7.py` | the rule (`multi_qty_lines`, `apply`); stdlib only; takes the grammar module as an argument |
| `tests_r1w7/test_multi_qty_w7.py` | six tests on the author's own lines with the frozen grammar via `common_w7.setup(helm=False)` |
| `r1w7/custody_w7.py` | one import (`from r1w7 import multi_qty_w7 as MQ`) and one hook: `"keys": [MQ.apply(K.key_item(it), it["raw_lines"], ns.XG) for it in real_items]` |
| `apply_amendment_7.py` | applies the three changes to a package source tree; refuses on a missing or doubled anchor; prints the sha256 of each file |

## 3. What does not change

The frozen key, grammar and survey classifier (vendored, freeze-checked at setup). The exam frame, the draw, the seed
rule, the exclusion lists, the dialogue and noise exams, the arms, the instrument rows, the hard gates, the marks and the
status words. The K4 rule. HELM itself (this is an instrument change). Sealed data from c51–c54 is never re-read.

## 4. Effect on c54, for the record only (MEASURED, no re-reading of sealed data for a claim)

By program over the c54 unit files (`K4_ITEM_DIAGNOSIS_C54.md` §3): exactly 2 of 128 lesson lists carry one more amount
piece than the key has lines — the two unexplained asks — and no answered item does. Under this rule those two items would
have been `NOT_SCORED`; c54's recorded word stays `CHAT_WAVE_NO_GAIN` (the preregistration forbids re-reading sealed data
with a repaired reader). A fresh draw (package v7, job c55) is the only way to a new word.

## 5. Claim status

An instrument amendment; `PROPOSED` until the forked session seals it into v7 and the custodian draws under it. No HELM
claim moves. Cost 0 USD.
