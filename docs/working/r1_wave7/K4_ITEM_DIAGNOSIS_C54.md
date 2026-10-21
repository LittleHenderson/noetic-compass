# K4 item diagnosis — c54's two unexplained asks, and c52's one (HELM-R1 wave 7; laptop, 0 USD; 2026-10-21)

Plain English. The exam text is sealed: every fact below was read by a program from the unit files and the sealed v6
package; the items are named by id and described by shape. No recipe line, pantry line, dialogue line or ingredient
name from the exam is quoted here.

Claim states used: **MEASURED** = a program read it from a frozen file; **PROPOSED** = a change nobody has approved;
**OPEN** = not settled. Nothing here moves any claim; c54 stays `PASS` / `CHAT_WAVE_NO_GAIN`, `NOT LICENSED`.

## 1. What the reader said (MEASURED)

`run_c54_r1w7v6_20261021/R1_W7_READING.json` (sha256 `9bf8a2b687054f9d1a59a1b14a91ed61bb88a69be4ed24d71407b6c3b34ecd23`),
mark `K4_HONEST`: `unexplained_asks_strict` 2, `unexplained_asks_w6_rule_reported` 2, unrouted scored turns 0,
`unsettled_ask_fired` 0 → FALSE. The same 2 in `LOOP_ON`, `CHAT_DIAG` and `CHAT_ON_REPLAY`. The summary rows do not name
the items.

The rule (`deps/HELM_RBW1T_20261019/rbw1t/keys_rbw1t.py`, `unexplained_ask`, line 133): an ask is UNEXPLAINED when all
four hold — the key is `ANSWER`; every lesson scored `LEARNED`; the stock turn read `STOCK_RECORDED`; the question turn
read an asking status. Nothing forgiving fired (no refused lesson, no refused stock, no same-name unsettled ask).

## 2. The items (MEASURED, found by program)

Finder: every X7_REAL record whose lesson turns all read `WITNESS_ADMITTED`, whose stock turn read `STOCK_RECORDED`, and
whose question turn read an asking status. Unit files: c54 `W7_X7_REAL_CHAT_ON.json` sha256 `d3577f70…`, `W7_X7_REAL_LOOP_ON.json`
`48567018…`; c52 `W7_X7_REAL_CHAT_ON.json` `a09b3eb4…`.

| | c54 item A | c54 item B | c52 item (for comparison) |
|---|---|---|---|
| Id | `RW:pg:52800@102023` | `RW:pg:38193@150079` | `RW:pg:17438@21087` |
| Key lessons / turns | 3 / 5 | 6 / 8 | 4 / 6 |
| Lesson turns | 3 × `WITNESS_ADMITTED`, path wide, reason `ADMITTED` (licensed first: `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`) | 6 × the same | 4 × the same (licensed first: `UNKNOWN_INGREDIENT`) |
| Stock turn | `STOCK_RECORDED`, path wide | same | same |
| Question turn | `UNDETERMINED_CLARIFY`, value null, writes 0, routed | same | same |
| Wide audit | coefficients 3, support slots **4** | coefficients 6, support slots **7** | coefficients 4, support slots 5 |
| Same in `LOOP_ON` | yes, turn by turn | yes | yes |
| Names the sealed v6 reader binds on every lesson and on the stock | 4, every one with an exact amount | 7, every one with an exact amount | 4 + the condition name |
| Of those, ran out across the lessons | 3 | 6 | 4 |
| Never ran out | **1** (a one-word name, plain count, no unit) | **1** (a one-word name, a fraction amount, no unit) | the condition name |
| The chat's last reply | names that one; says it cannot say yet; says it does not guess (three booleans, measured) | same | same |

So on both c54 items the brain holds one more ingredient than the key has lessons, and that ingredient never ran out,
so its requirement was never taught, so the brain asks. That is exactly the c52 mechanism at the brain — but the extra
name is NOT a condition (temperature, time, head count). It carries a real amount. It came from somewhere else.

## 3. Where the extra name comes from (MEASURED)

The lesson sentence lists the batch's ingredients. The custodian's generator (`deps/HELM_RBW1T_20261019/vendor/xreal_v2/xreal/mapping.py`,
`join_lines`) joins the KEY LINES with ", " and " and " (the last). So the list should hold exactly as many amount-bearing
pieces as the key has lines. Counting pieces split at ", " and " and ":

| | key lines | amount-bearing pieces | the key's own line parser (`xreal.grammar.parse_line`) on the extra pieces |
|---|---|---|---|
| item A | 3 | **4** | pieces 3 and 4 are each "amount + one word", plain counts (the survey classifier calls piece 3's word a unit of its top-20 table and piece 4 `count (no unit)`) |
| item B | 6 | **7** | piece 6 is six words with TWO amounts and an "or"; piece 7 is two words, a fraction glyph and a name, which `parse_line` does not parse as a line at all (`None`) |
| c52 item | 4 | 5 | the extra piece is a condition (`condition_fragment` True) — the §7.105 class, fixed in v5 |

The key's line count comes from the BOOK's line breaks: one book line = one lesson, named by the line's first head word;
whatever follows a comma or "and" inside that line is tail text the key ignores. The exam then (a) makes only that first
name run out in that line's lesson, and (b) doubles only the line's LEADING amount in the other lessons (`surplus_line`),
so the second amount is identical in every lesson. **Nothing in the lessons can teach the second ingredient's requirement.**

The wide reader's rule (v3, `split_lines` / `starts_line`): cut a list at a separator only where a new amount begins.
Two amounts of two things are two ingredients. The reader read the sentence as any cook would; the key read it as one line.

**Whole-exam check (c54 `CHAT_ON`, 128 items, by program):** lesson lists with one MORE amount-bearing piece than key
lines: **2** — both asked, both with every lesson admitted: the two items above. Equal counts: 97 answered, 15 asked with no
lesson admitted, 2 asked with one lesson refused. (12 items my piece counter counted one piece SHORT — an article amount
it does not count; all 12 were answered.) So on this draw the two-amount line accounts for exactly the two unexplained asks
and touches no answered item.

## 4. The class, and who should change (MEASURED facts; PROPOSED remedy)

- **Not the c52 class.** c52's extra name was a condition amount read as an ingredient (a reader fault, fixed in v5 by a
  general rule). c54's extra name is a second ingredient inside one book line, with its own amount.
- **HELM's ask is honest.** The brain was never taught that ingredient's requirement and said so, named it, and did not
  guess. A reader rule that glued a second amount onto the line before it would be a special case that breaks ordinary
  lists ("2 cups flour, 1 cup sugar" is two lines). No general HELM rule makes this item answerable from these lessons.
- **The instrument's representability rule is the general fix (PROPOSED, custodian side, A-R1W7-7).** `keys_rbw1t.representable`
  already refuses ranges, odd forms and units outside the top-20 table. Add: a raw line with more than one quantity span
  (`xreal.grammar.spans_in` gives them) is not representable (`why_not` entry `lineN:MULTI_QTY`). Such recipes then score
  `NOT_SCORED` (undetermined key), as the preregistration already does for the others. Applies to a FRESH draw only: the
  sealed c54 data may not be re-read with a repaired reader (preregistration rule); c54 stays `NO_GAIN`.
- **K4's rule is unchanged.** It did its job: it found a place where the key and the reader disagree.

## 5. Every ask on X7_REAL `CHAT_ON`, by cause (MEASURED, counts only)

19 asking question turns over 128 items (the reader counts 13 on ANSWER-keyed items; the other 6 sit on undetermined-key
items, which this note cannot name without the key file, which it never opens).

| Question status | Lessons | Stock turn | Count | Explained by the rule? |
|---|---|---|---|---|
| `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` | none admitted | `CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` | 10 | yes |
| `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` | none admitted | `CLARIFY_ENGLISH_NO_INGREDIENT_NAMED` | 3 | yes |
| `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` | none admitted | `CLARIFY_NOT_CCE` | 2 | yes |
| `UNDETERMINED_CLARIFY` | one refused (`TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH`), rest admitted | `STOCK_RECORDED` | 2 | yes |
| `UNDETERMINED_CLARIFY` | all admitted | `STOCK_RECORDED` | **2** | **NO — items A and B** |

**The 15 zero-lesson items (the next-biggest real-recipe gap, MEASURED):** the sealed wide reader on their 98 lesson turns:
`CLARIFY UNIT_NOT_IN_TABLE` 96, `CLARIFY NO_PRODUCT` 2. Licensed path on the same turns: `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`
83, `CLARIFY_NOT_CCE` 13, `CLARIFY_WIDE_NO_PRODUCT` 1, `CLARIFY_WIDE_DISH_NAME_NOT_BOUND` 1. So 15 of 128 real recipes
(every lesson refused) are lost to units outside the 20-unit table; stage 1c's widened table exists behind a switch that is
OFF and `ENGINEERED-NOT-VALIDATED`. That is a separate item in the design packet (G4), not touched by any proposal here.

## 6. Files

Read by program: `run_c54_r1w7v6_20261021/deliverable_unpacked_a1/.../r1w7_out/units/W7_X7_REAL_{CHAT_ON,LOOP_ON}.json`;
`run_c52_r1w7v4_20261020/.../W7_X7_REAL_CHAT_ON.json`; the sealed v6 package `build_v6/HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip`
(`387577de…`; `helm_now/helm_wide_turn.py` `ba9ecf6c…`) extracted to a scratch folder; `deps/HELM_RBW1T_20261019/rbw1t/keys_rbw1t.py`
and `vendor/xreal_v2/xreal/{mapping,grammar}.py` (code only). The custodian carrier was listed by name only; `out/exam/` and
the key files were never opened.
