
## 19. Amendment A-R1W7-7 (the custodian's MULTI_QTY rule; owner's word 2026-10-21 "Yes to D6, the custodian MULTI_QTY rule, as amendment A-R1W7-7"; written in the reader-gap session, applied to this package BEFORE the v7 reseal; package copy with the hook diff and the measured effect; 2026-10-21)

**Owner's word (typed in the operator session, 2026-10-21):** "Yes to D6, the custodian MULTI_QTY rule, as amendment
A-R1W7-7." (Same message: "Merge PR #433 into the thread branch. Build D1 to D5 with tests, FIX FIRST, at 0 USD.")

### 19.1 What changes (plain English)

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
its own reason) adds `line<i>:MULTI_QTY` to `representable.why_not`, and `representable.representable` becomes False. The
item then scores `NOT_SCORED` (an undetermined key), exactly as recipes with a range, an approximate amount, an odd form or
a unit outside the top-20 table already do (section 4 representability rule). Nothing else in the key changes: answer,
yield, lessons, heads, limiting index are untouched. The frozen key package `HELM_RBW1T_20261019` is NOT edited; the rule
sits in this package (`r1w7/multi_qty_w7.py`) and is applied once, in `custody_w7.make_all`, to the real keys.

### 19.2 Files in this package

| File | Role |
|---|---|
| `r1w7/multi_qty_w7.py` (sha256 `04d2df7e7cd75a3449611e159eea06649f5f5e56364f96bde5172e3ce066449b`) | the rule (`multi_qty_lines`, `apply`); stdlib only; takes the grammar module as an argument |
| `tests_r1w7/test_multi_qty_w7.py` (sha256 `3c58d323be3c9018335b370d49c47405d0aeb9279847f9fecd8ede81b280c179`) | seven tests on the author's own lines with the frozen grammar via `common_w7.setup(helm=False)` |
| `r1w7/custody_w7.py` | one import and one hook (the diff below) |

Applied to this package's source tree by `apply_amendment_7.py` (sha256 `c022b29ad3f75bf9a4c899bc6c65b59995546eb066c4361febc5e1a439aaa1d4`,
repo copy `docs/working/r1_wave7/a_r1w7_7/`) before the freeze; the tool refuses on a missing or doubled anchor and prints
the sha256 of each file it wrote. The whole diff of `r1w7/custody_w7.py` against the v6 extract:

    35a36
    > from r1w7 import multi_qty_w7 as MQ      # noqa: E402  A-R1W7-7 (SPEC 7.109 D6)
    116c117
    <     out["real"] = {"items": real_items, "keys": [K.key_item(it) for it in real_items], "skips": drawn["skips"],
    ---
    >     out["real"] = {"items": real_items, "keys": [MQ.apply(K.key_item(it), it["raw_lines"], ns.XG) for it in real_items], "skips": drawn["skips"],

### 19.3 What does not change

The frozen key, grammar and survey classifier (vendored, freeze-checked at setup). The exam frame, the draw, the seed
rule, the exclusion lists, the dialogue and noise exams, the arms, the instrument rows, the hard gates, the marks and the
status words. The K4 rule and the reader's own rules (`score_w7.py`, `merge_r1w7.py`: untouched; the ask prefix rule is
RB-W1T's `is_asking`, under which every `CLARIFY_*` status counts as an ask, so the reader-gap cut's new wide statuses
`CLARIFY_WIDE_PURPOSE_ABSENT`, `CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT`, `CLARIFY_WIDE_FACE_UNREAD`, `_NEGATED`,
`_WHICH_INGREDIENT`, `_REFUSED`, `_UNKNOWN` are asks without any reader change). HELM itself (this is an instrument change).
Sealed data from c51–c54 is never re-read.

### 19.4 Effect on c54, for the record only (MEASURED, no re-reading of sealed data for a claim)

By program over the c54 unit files (`K4_ITEM_DIAGNOSIS_C54.md` section 3): exactly 2 of 128 lesson lists carry one more
amount piece than the key has lines — the two unexplained asks — and no answered item does. Under this rule those two
items would have been `NOT_SCORED`; c54's recorded word stays `CHAT_WAVE_NO_GAIN` (line 4 forbids re-reading sealed data
with a repaired reader). A fresh draw (this package, v7) is the only way to a new word.

### 19.5 Effect size, MEASURED on this package's practice draw (128 items; the same ids as RB-W1T's practice draw v2; counts only; practice data, never an exam)

Measured by program on 2026-10-21 by running this package's own `custody_w7.py practice` (the amended tree) and comparing
its keys with the v6 practice keys (`compare_practice_keys.py` beside the zip): inputs byte-identical (REAL, CONV, NOISE,
the CONV keys, the pools); every key field other than `representable` identical on all 128 items; **6 of 128 items are
tagged, one line each (`line0`, `line2`, `line3`, `line4`, `line5`, `line7` of their books), all six representable and
ANSWER-keyed under the frozen key, so they become `NOT_SCORED`**: representable 120 → 114, representable-and-answer 106 →
100 (5 percent of the 120; 4.7 percent of 128). No untagged item changes. Ids: `RW:pg:63007@34737`, `RW:wb:425075:4511682`,
`RW:wb:202496:4494726`, `RW:wb:457675:4587499`, `RW:pg:65706@19804`, `RW:pg:65507@35986` (practice pool ids, already excluded
from every exam draw). The broad wording of the design packet ("more than one quantity span") would have tagged 20 of 128
(52 lines, 45 of them parenthesised equivalents such as "2 cups (250 g) flour"); the rule as written does not. The K1 bar
scales with the representable-and-answer count (section 5), so a practice reading under this rule compares a smaller
denominator; every such move is reported in `PRACTICE_READINGS_V7.json`.

### 19.6 Claim status

An instrument amendment; `PROPOSED` until the custodian draws under it. No HELM claim moves. Cost 0 USD.
