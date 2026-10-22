# DESIGN — reader v7.3 and amendment A-R1W7-11 (K4 leaves out an honest ask on a two-amount line) — FINAL

Date 2026-10-21 PDT. Worktree `C:\tmp\helm-ctt2r-c49-read`, branch `claude/helm-reader-v73-a11-20261021`, cut from thread
head `cc5ae88c`. Laptop, 0 USD, no network, no AWS. **Design only: nothing here is built, sealed or approved.** After the
build, reader v7.3 and A-R1W7-11 would be `ENGINEERED-NOT-VALIDATED`; the chat on any exam stays `NOT LICENSED`.

Owner's words (verbatim, 2026-10-21): "IF HELM ANSWERED HONESTLY AND CORRECTLY THEN YES  "Exempt from K4 only"; "merge
450"; "build v7.3" each tested through the real scoring program → a new sealed package → a fresh exam only on a line you
type." ("merge 450" is done: thread head `cc5ae88c` is the PR #450 merge.) "build v7.3" is read as spec §7.119's
"Proposed next FIX FIRST" (a) and (b); section 2 builds both as written, plus one guard (R2g) that only adds asks and is
named as a departure in section 7.

This version folds in an independent critic's 17 findings (section 8 says, item by item, what was checked and what changed).

## 0. Said plainly

- Job c56 (spec §7.119) missed two marks. **K3** fell on one wrong lesson. **K4** fell on one ask the frozen rule calls unexplained.
- Wrong lesson: a book line ends in a dangling "or". HELM's reader keeps "or" inside the name. The "ran out" phrase then
  matches only the next line, so the brain stores the wrong line's amount.
- Ask: a book line holds two amounts. The lessons never teach the second ingredient, so HELM asks. That ask is honest, but
  the frozen rule counts it.
- **Reader v7.3** has four rules. **R1:** "or" at the end of a line is never part of a name. **R1a:** a batch or a stock
  list that holds such a line asks "which one did you use?" and saves nothing. **R2:** when no line has the exact name
  and the phrase fits two or more lines, HELM does not pick one; it asks. **R2g:** when the phrase is an exact name but
  another line is that same name followed by a joining word ("tomatoes" beside "tomatoes in juice"), HELM asks which line.
- **A-R1W7-11** is the owner's "Exempt from K4 only", for a fresh draw only. An ask on a two-amount line leaves K4's count
  only when a program can check, from what the host already records, five things: the key is an answer key with the
  two-amount tag; the frozen rule counts the ask; the brain's own gate asked on the wide path; HELM's own sentence names
  exactly the ingredients its book holds untaught; and each of those names is the second ingredient written on a tagged
  line. These checks are necessary, not sufficient (limits in 3.2). A wrong number stays WRONG. Nothing leaves the
  question score. Nothing from c51–c56 is re-scored.
- It also corrects a false sentence in section 19.1 (A-R1W7-7): the frozen code never scored a tagged item `NOT_SCORED`.

## 1. Facts this design rests on (read in the code; probes are feasibility checks, not results)

| # | Fact | Where |
|---|---|---|
| F1 | `parse_line("1 can tomatoes or")` returns name `"tomatoes or"`: no step removes a final "or". `ALTERNATIVE_RX` needs an amount after "or"; the v6 alternative split needs a word after it. With a comma (`"1 can tomatoes, or"`) the "or" becomes a note; beside `"4 cups fresh tomatoes"` that pair already asks (`SAME_INGREDIENT_TWICE`, "fresh" is dropped), beside `"4 cups chopped tomatoes"` it is read as two needed lines. | `helm_wide_turn.py` 187, 274–372, 336–344, 458–483; re-checked on the v9 copy |
| F2 | `resolve_ran_out` order: exact → unit-stripped exact → starts-with (1 hit binds, 2+ unchanged) → ends-with (same) → own-words (1 hit binds). A single starts-with or ends-with hit binds before own-words is checked. An exact hit always binds. | 540–572; callers 680–683 (`own` map, v7.2) |
| F3 | The exam's lesson is `"We made 1 {N} from {L} and ran out of {H}."`, lines joined `", "` and `" and "`, the ran-out line at its amount and every other line doubled (only its leading amount); `{H}` = the frozen grammar's modifiers + head, which stops at STOP words ("or", "in", "with", …). So `"1 can tomatoes or"` and `"1 can tomatoes in juice"` both give `H = "tomatoes"`. | `rbw1t/common_rbw1t.py` `TEACH`; `exam_rbw1t.turns_for`; `xreal/mapping.join_lines`; `xreal/grammar.py` 48–49 (`STOP_WORDS`), 133–148 |
| F4 | `keys_rbw1t.score_question` returns `NOT_SCORED` only when `answer.key != "ANSWER"`; any status not in `ANSWERING = ("SUCCESS_EVALUATED",)` is `ASKS`. `unexplained_ask` = ANSWER key, every lesson `LEARNED`, stock `STOCK_RECORDED`, question `ASKS`. Neither reads `representable`. `score_lessons` walks the key's lines, so an empty record gives all `NOT_LEARNED`. | `keys_rbw1t.py` 98–135 |
| F5 | `score_w6.score_real` reads `representable` only for `rep_answer` / `fully_learned_rep` (K1). `unexplained_asks_strict` has no exemption; the D-W6-12 exemption touches only the reported `unexplained_asks`. | `score_w6.py` 29–77 |
| F6 | K4 today: `t.get("unexplained_asks_strict") == 0` on X7_REAL `CHAT_ON` (D-W7-9). `merge_r1w7.Run.arm_summary` calls `score_w7.score_real` for EVERY X7_REAL arm. | `merge_r1w7.py` 65–85, 336–340; `score_w7.py` 77–78 |
| F7 | A CHAT record holds `turns` (each with `kind`; a routed turn has `loop` = `chat_harness.loop_view(res)`, whose `loop_sentence` is the loop's `everyday_english_response`), `log`, `lesson_records`, `scored_turn` (its `inner_status` is a COPY of `status`), `wide_audit = [audit_brain(book, W)]` (`coefficients` = learned numbers, `support_slots` = ingredient names over all recipes, `ok`). A `LOOP_ON` record's turns are wave 3's (`reply_adapter` = the same loop sentence). | `chat_harness.py` 58–67 (64), 232–266 (239); `harness_w6.py` 170–191; `live_w3.py` 356–361; `arms_rbw1t.py` 131–146 |
| F8 | The wide question returns `UNDETERMINED_CLARIFY` exactly when the RPM gate does not PROCEED; the gate's unsatisfied list is absent stock plus unlearned requirements. `say_wide` then speaks one of two G1 sentences: if any support name has no stock, "I can't say how much {p} we can make yet, because I don't know how much …"; otherwise "I can't say yet how much {p} we can make. I still need {need}. I didn't guess.", where `need` names every unlearned requirement in first-batch order (one name: "one batch where X ran out first while everything else was left over"; two or more: "one batch for each of {say_and}: a batch where that one ran out first …"). `BRAIN_UNDETERMINED` comes only after the gate PROCEEDs. `_finish` copies the sentence into `everyday_english_response` unchanged. | `helm_wide_turn.py` 732–737, 751–789, 1299–1318, 1334–1336; `helm_brain_wide.py` 608–640; `helm_end_to_end_loop.py` 450–465 |
| F9 | `take_over` returns False for every CLARIFY reading that has no pending batch, so a wide reader's question is never spoken: the licensed path's status stands and nothing is written. | `helm_wide_turn.py` 921–943, 995–1004 |
| F10 | A key holds no raw lines (`keys_rbw1t.key_item` 38–54). The raw lines sit in `SAMPLE_REAL_X7.json`, which custody writes beside `KEYS_REAL_X7.json` in the same laptop-only exam folder that the reader already opens. | `custody_w7.py` 43, 119, 180–185; `merge_r1w7.py` 36–39 |
| F11 | Crash shapes: a chat crash record has `log []`, `lesson_records []`; a wave-6 crash record has NO `scored_turn` but keeps `log` and `lesson_records` (so the frozen rule CAN count it: lessons LEARNED, stock recorded, question status None = ASKS); an ALWAYS_ASK record carries `always_ask`. | `chat_harness.py` 268–276; `harness_w6.py` 170–191; `score_w6.py` 17–26 |
| F12 | The v9 cut and branch head `cc5ae88c` differ in 3 of 167 cut files: `helm_chat.py`, `helm_memory.py`, `test_helm_memory.py` (memory compaction, commits `0014ae32`, `9f0c359a`; compaction behind `HELM_MEMORY_COMPACT`, default OFF; "user_facts keeps the LAST 20"). A v10 cut from the head carries them into the chat arms. | hash compare against `contract/HELM_CUT_R1W7.json` |

**Probes (scratch only; feasibility, not results; every scratch copy checked byte-equal to the v9 sources first: 132 of
132 `helm_now` files, the RB-W1T tree 395 of 395, `multi_qty_w7.py`).** Scratch root
`C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\`:
- `v73_design_probe\` (first draft): R1+R2 only, host's 12 HELM unittest names `Ran 280 tests in 7.347s`, `OK (skipped=1)`.
- `v73_scratch\critic\` (the critic): `critic_probe.py` → `run\probe1.log`; re-run here by `v73_scratch\finalize\run\probe_rerun.log`,
  identical apart from header lines.
- `v73_scratch\finalize\` (this version): `scripts\final_patch.py` (R1, R1a, R2, R2g as in-process replacements),
  `scripts\honest_check_proto.py` (the section 3.2 test), `scripts\final_probe.py` → `run\final_probe2.log`,
  `scripts\final_tests.py` → `run\final_tests.log`: host's 12 names with the final rules **`Ran 280 tests in 6.816s`,
  `OK (skipped=1)`** (`READER_VERSION` unchanged, so the OFF-path pin test ran and held). `run\final_probe.log` is an earlier
  run whose R2g returned a marker string; it shows that marker reaching HELM's voice ("Tomato ∅ wasn't in that batch").

Authored items through HELM's loop (keys by the frozen `key_item` + A-R1W7-7's `apply`; chat-shaped records built as
`chat_harness.Dialogue.record` builds them; frozen `real_record_view`, `score_lessons`, `score_question`, `unexplained_ask`):

| Item (author's own raw lines) | Frozen key | v7.2 (as in v9) | v7.3 final rules |
|---|---|---|---|
| D1 `1 can tomatoes or` / `4 cups chopped tomatoes` / `2 onions` | UNDETERMINED, q 1, 4, 2 | lesson 0 binds `chopped tomato`, learns 8 (key 1): WRONG; then `TEACH_REFUSED_REFUSED_CONFLICT`, `TEACH_REFUSED_RECEIPT_FAILED` (c56's pattern) | lessons and stock `CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE`; question `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` (licensed); nothing learned |
| D2 `1 cup butter or` / `1 cup margarine` / `2 cups flour` | ANSWER 3/2 | RIGHT 3/2 (name `butter or`) | which-one asks; question ASKS with no lesson LEARNED (not an unexplained ask; a K1 cost) |
| D3 `1 can tomatoes or` / `4 cups fresh tomatoes` / `2 onions` | UNDETERMINED | lesson 0 binds `tomato` (the fresh line), learns 8: WRONG | which-one asks |
| D4 `2 cups flour` / `1 cup butter, or` / `1 cup margarine` | ANSWER 3/2 | RIGHT 3/2 | which-one asks |
| A1 `3 cups tomatoes with juice` / `1 cup chopped tomatoes` / `2 onions` | UNDETERMINED | lesson 0 binds `chopped tomato` (ends-with), learns 2 (key 3): WRONG | lesson 0 `TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH`; lessons 1–2 LEARNED |
| X1 `3 cups tomatoes with juice` / `1 can tomatoes or` / `2 onions` | UNDETERMINED | lessons 0–1 refused, lesson 2 LEARNED (the first draft's R1+R2 alone: lesson 0 WRONG, learns 2 vs key 3) | which-one asks |
| X2 `1 can tomatoes in juice` / `2 tomatoes` / `2 onions` | UNDETERMINED | lesson 0 binds `tomato` by exact name, learns 4 (key 1): WRONG (the same under the first draft) | lessons 0–1 `CLARIFY_WIDE_RAN_OUT_WHICH_LINE`; lesson 2 LEARNED |
| C1 `3 eggs, 1 beaten` / `2 cups flour` / `1 cup milk` | ANSWER 3/2, `line0:MULTI_QTY` | 3 LEARNED, `STOCK_RECORDED`, `UNDETERMINED_CLARIFY` naming `beaten` (a note read as an ingredient) | the same; A-R1W7-11: not exempted |
| C2 `1 cup sugar, 2 tablespoons reserved` / `2 cups flour` / `1 cup milk` | ANSWER 3/2, `line0:MULTI_QTY` | the same, naming `reserved` | the same; not exempted |
| C3 `2 cups flour, plus 2 tablespoons` / `1 pound beef, a lean cut` / `1 cup broth` | ANSWER 3/2, `line0:MULTI_QTY` | the same, naming `lean cut` (from UNTAGGED line 1) | the same; not exempted |
| C4 `1 onion, 2 tomatoes` / `1 cup rice` / `2 cups tomatoes with juice` | ANSWER 3/2, `line0:MULTI_QTY` | lesson 2 `TEACH_REFUSED_MEMORY_CHECK_REFUSED` | lesson 2 `CLARIFY_WIDE_RAN_OUT_WHICH_LINE` |
| M1 `2 cups barley` / `5 cloves, 10 juniper berries` / `1 cup broth` | ANSWER 3/2, `line1:MULTI_QTY` | 3 LEARNED; ask naming `juniper berry` | the same; **exempted** |
| P1 `2 cups rice` / `6 cloves and 12 peppercorns` / `1 cup stock` (c56's shape) | ANSWER 3/2, `line1:MULTI_QTY` | ask naming `peppercorn` | the same; **exempted** |

Totals: WRONG lessons v7.2 **4** (D1, D3, A1, X2), v7.3 final **0**; WRONG answers 0 and 0. Under the first draft's
check (d), C1, C2 and C3 were exempted; under section 3.2 only M1 and P1 are. A two-name case,
M2 `2 cups barley` / `6 cloves, 12 peppercorns and 2 allspice berries` / `1 cup broth`, is also exempted (names
`peppercorn`, `allspice berry`; `scripts\final_probe_m2.py` → `run\final_probe_m2.log`).

## 2. Part 1 — reader v7.3 (`helm_wide_turn.py`, `READER_VERSION = "helm_wide_turn reader RB-W1 v7.3 (2026-10-21)"`)

### 2.1 R1 — a dangling "or" is never part of a name

**Rule.** `DANGLING_OR_RX = re.compile(r"(?:^|[\s,;]+)or[\s,;]*$", re.IGNORECASE)`. In `parse_line`, after
`s = line.strip().strip(".").strip()`: if the pattern matches `s` and words stand before it, cut it (`s` becomes the words
before it, trailing `" ,;"` removed); if it matches `notes` (`"or"` alone, or notes ending in a dangling "or"), cut it from
`notes`. Either way the line carries `"dangling_or": True`. Everything after (amount, unit, `ALTERNATIVE_RX`, the v6
alternative split, `bind_name`) runs on the cut text. `name` and `own` never hold the dangling "or"; `said` keeps the words
as given (`"1 can tomatoes or"`). "or" inside a word ("liquor"), "or" with an amount after it (`"2 large or 4 small"`, v3's
`AMOUNT_HAS_TWO_PARTS`), "or" with a word after it (`"dry beans or whole peas"`, v6) and `"or more"` are untouched. No
`parse_line` dict gains a key unless the rule fired.

### 2.2 R1a — a batch or stock relying on the pair asks which one (§7.119 (a), as written)

**Rule.** In `parse_lines`, after every line has parsed and BEFORE the `SAME_INGREDIENT_TWICE` check: the first line with
`dangling_or` returns `([], _ask("ALTERNATIVE_WHICH_ONE", first=<its name>, second=<the next line's name, or None when it
is the last line>, words=<its said text>))`. So a witnessed batch (with or without a dish name) and a stock list holding
such a line are one question; nothing is saved and no pending batch is kept.

**The question is spoken.** `take_over` gains one clause, right after its existing cubes-written check: a CLARIFY reading whose code is in
`WHICH_ONE_CODES = ("ALTERNATIVE_WHICH_ONE", "RAN_OUT_WHICH_LINE")` is taken when the licensed path wrote nothing and its
status is in `WIDE_MAY_TAKE` (the rule that already governs a WITNESS reading). Without it (F9) the licensed status would
stand and the person would never hear the real reason. `wide_turn`, on such a reading, first calls
`_withdraw_mentioned_stock(loop, text, tick)` (v4's rule for a turn the wide path cannot use: HELM never answers from stock
the person just restated), then finishes with status `CLARIFY_WIDE_<code>` and `say_reader_question`:
- `ALTERNATIVE_WHICH_ONE`, partner known: `You wrote "{words}" and then {second}, so it reads as one or the other. Which one
  did you use? Tell me the batch again with just that one. Nothing was saved.`
- partner None: `You wrote "{words}" with nothing after the "or". Which one did you use? Tell me the batch again with just
  that one. Nothing was saved.`

**Why "both needed" is dropped.** The first draft kept both lines as requirements and never asked. That answers an
either/or recipe as if both were required (D2 answered 3/2 limited by margarine although butter could stand in): it matches
the frozen key, not the recipe, against the owner's "honestly and correctly". It also made X1 a WRONG lesson. The ask sits at
the batch and the stock, so it is K4-safe (an unexplained ask needs every lesson LEARNED and the stock recorded) and K3-safe
(nothing is learned). The cost falls on K1 only: a representable ANSWER key holding a dangling-"or" line can no longer be
fully learned. The one dangling-"or" item §7.119 names was a same-name UNDETERMINED key (outside K1); c56's K1 read 91 of 91
against a bar of 82. A fresh draw's exposure is counted in the v10 practice reading (section 6, reported only).

### 2.3 R2 — ambiguity is checked before any guess that is not an exact match (§7.119 (b))

**New `resolve_ran_out(name, batch, said=None)`** (steps 1–2 unchanged, steps 3–5 replaced):
1. `name in batch` → `name`.
2. strip leading unit / size words as today → `stripped`; `stripped in batch` → `stripped`.
3. `name2 = stripped or name`. `SW = {b : b.startswith(name2 + " ")}`; `EW = {b : b.endswith(" " + name2)}`;
   `OW = {b : _contains(_words(said.get(b, b)), _words(name2))}` when `said` (the `own` map) is given, else empty.
4. `U = SW ∪ EW ∪ OW`. `len(U) == 1` → that name. Otherwise (0, or 2 and more) → `name` unchanged; the brain then refuses
   (`REFUSED_RAN_OUT_NOT_IN_BATCH`) and HELM asks, exactly as v7.2 does for two hits inside one step.

**What changes against v7.2.** Starts-with no longer wins alone when ends-with or own-words also fits another line
(`"sugar"` with `sugar beet` / `brown sugar`: v7.2 → `sugar beet`; v7.3 → unchanged). Ends-with no longer wins alone when
own-words fits another line (c56's shape; A1). Own-words now uses the unit-stripped phrase (`name2`): `"cupfuls of
sifted"` with own words `"2 cups sifted cake flour"` → `cake flour` (v7.2: unchanged). On every existing test `name2 ==
name` or the result is the same.

### 2.4 R2g — an exact hit that the frozen key would also give to another line is asked (an addition; see section 7)

**Rule.** In `read_wide`, right after `ran_out = [resolve_ran_out(…)]` and BEFORE the `NO_PRODUCT` / pending step: for each
resolved name `n` that is a batch name, the rivals are the other batch names `b` with `_words(b)[:k] == _words(n)` and
`_words(b)[k]` in `STOP_WORDS` (`k = len(_words(n))`; `STOP_WORDS` is a copy, inside `helm_wide_turn.py`, of the frozen
`xreal.grammar.STOP_WORDS`: and, or, but, for, in, on, at, to, with, from, into, the, a, an, left, that, which, if, as, per,
each). Any rival → `clarify(_ask("RAN_OUT_WHICH_LINE", item=n, lines=[n] + rivals))`; nothing saved, no pending kept.
Voice: `You said {item} ran out, but that could be {lines joined with ", " and a final " or "}. Which one ran out first?
Tell me the batch again. Nothing was saved.` `resolve_ran_out` itself is not changed by R2g (its return is always a name,
so no marker string can reach the voice).

**Why.** By F3 the frozen grammar's name stops at a STOP word, so `"1 can tomatoes in juice"` and `"2 tomatoes"` are both
`"tomatoes"` to the exam; an exact bind to `tomato` is a guess. X2 showed it storing a wrong amount in v7.2 and in the
first draft. Exact matches with no such rival still bind: `"sugar"` beside `brown sugar`, `"stock"` beside `beef stock
cube`, `"tomato"` beside `tomato paste` (the next word is not a STOP word).

### 2.5 Statuses and files

Two new statuses, both beginning `CLARIFY` (asks under RB-W1T's `is_asking`): `CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE`,
`CLARIFY_WIDE_RAN_OUT_WHICH_LINE`. The reseal's ask-prefix check must list **13** wide statuses (v9: 11; 2 added) and must
also catch codes passed to `_ask` through a named constant. `helm_brain_wide.py`, `helm_faces_in.py`,
`helm_end_to_end_loop.py`, `helm_chat.py` are not changed by v7.3; the licensed path is untouched.

### 2.6 OFF-path pin

`test_helm_cas_address.PINNED_OFF_SHA256` (`79e4914a561851d2cd19d04902f38e869787e36db0e984302bbbc6c434fa698c`) is recomputed
only if the fixture trace changes. The finalize probe (all four rules, `READER_VERSION` unchanged) kept it. The
`READER_VERSION` string is in the trace (`english_in.reader` and the "English in (wide)" row), so the bump to v7.3 changes it.
On the REAL implementation (not the probe), the builder first diffs the canonical fixture records (`helm_test_pins.canon`)
of v7.2 and v7.3 by program; the only differing values allowed are the reader string. Then the new value is written with a
dated comment line, machine-neutral as §7.107 requires (`test_helm_pin_hygiene` must still pass).

## 3. Part 2 — amendment A-R1W7-11 (wave-7 package; a fresh draw only)

### 3.1 Scope

K4 only. The frozen strict count `unexplained_asks_strict` stays exactly as computed and is still reported. A new count
`unexplained_asks_strict_after_a11` = strict count minus the exempted asks; K4 reads it. The question score is untouched: a
tagged ANSWER key still scores RIGHT, WRONG or ASKS; WRONG still fails K3. K1, K3, NH-CHAT, P, N, every gate, instrument
row and the status-word order are untouched. c51–c56 are not re-scored and their unit files are not re-read.

### 3.2 The exact honesty test — an ask is exempted only if all five hold, checked in this order

For an X7_REAL item: key `k`, host record `r`, `n = n_lessons` (from the inputs), `raw` = the item's raw lines from
`SAMPLE_REAL_X7.json` (F10). Each check runs only if the one before it held; a check not reached is recorded as `None`.
Every field is read with `.get()` and type and length checks; the function never raises (an exception gives
`exempt: False` and records `error: <type name>`).

- **(a) tagged answer key:** `k["answer"]["key"] == "ANSWER"` and some entry of `k["representable"]["why_not"]` matches
  `^line(\d+):MULTI_QTY$`.
- **(b) the frozen rule counts it:** `keys_rbw1t.unexplained_ask(k, ls, v["stock_status"], qs)` is True, where
  `v = score_w6.real_record_view(r, n)`, `qs = keys_rbw1t.score_question(k, q.status, q.value, q.limiting, v["lessons"])`
  with `q = v["question"]`, `ls = keys_rbw1t.score_lessons(k, v["lessons"])` — the same calls, in the same order, as
  `score_w6.score_real`.
- **(c) the brain's gate asked on the wide path:** `r["scored_turn"]["status"] == "UNDETERMINED_CLARIFY"`,
  `len(r["log"]) == n + 2` and `r["log"][-1]["path"] == "wide"`. (`inner_status` is not used: on a CHAT record it is a copy
  of `status`, F7.)
- **(d) HELM's own sentence names exactly its untaught ingredients.** The question sentence is, on a CHAT record, the
  `loop.loop_sentence` of the LAST turn whose `kind` is `"turn"`; on a wave-3-shaped record (no `kind`), `turns[-1]
  ["reply_adapter"]`; else none. It must match one of (frozen, copied from F8's template):
  - `G1_ONE_RX = ^I can't say yet how much (?P<p>.+?) we can make\. I still need one batch where (?P<one>.+) ran out first while everything else was left over\. I didn't guess\.$`
  - `G1_MANY_RX = ^I can't say yet how much (?P<p>.+?) we can make\. I still need one batch for each of (?P<many>.+): a batch where that one ran out first while everything else was left over\. I didn't guess\.$`

  The names are `[one]`, or `many` split by `, and |, | and `. Then all of: no name is empty; `len(r["wide_audit"]) == 1`;
  `wide_audit[0]["ok"] is True`; `wide_audit[0]["coefficients"] == len(k["lessons"])`;
  `wide_audit[0]["support_slots"] - wide_audit[0]["coefficients"] == len(names)`; every `v["lessons"][j]["product"]` is the
  same name and equals `p`. The missing-stock sentence ("… because I don't know how much …"), any other sentence, or a split
  whose count does not equal the untaught count (a name holding ", " or " and " always adds pieces) → not exempted.
- **(e) each name is the second ingredient written on a tagged line.** For each tagged line `i` (with `raw[i]` present):
  remove parentheses with `multi_qty_w7.PAREN_RX`; take the frozen grammar's `qty_starts`; the lead amount ends at
  `qty_at(s, starts[0])["end"]`; every later start `p` with `p >= lead_end` and `multi_qty_w7.SEP_RX` matching between them
  is a second-amount tail; its head is `xreal.grammar.parse_line(s[p:].strip())["head"]` (lower case), and `lead_end` moves
  to the end of the amount at `p`. A head is dropped when it matches `^[a-z]+(?:ed|en)$`, when its `head_norm` is in the
  `head_norm` of `DENY = ("more", "less", "extra", "reserved", "divided", "separated", "beaten", "whites", "yolks", "them",
  "it", "each", "garnish", "serving", "dusting", "glazing", "brushing", "frying")`, when it or its `head_norm` is a unit word
  (`xreal.grammar.UNITS`, keys lower-cased, and their `head_norm`), or when its `head_norm` equals the `head_norm` of any key
  line's head. The allowed set is the `head_norm` of the heads left. Exempt only if every name `x` has
  `rbw1t.head_norm(rbw1t.last_word(x))` in the allowed set. No raw lines for the item → not exempted (`raw_lines_found:
  False`).

`exempt = a and b and c and d and e`.

**What the five checks show, and what they do not (necessary, not sufficient).** Together they show: the key is an answer
key with a two-amount line; every key line was learned at the key's amount and the stock was recorded; the brain's gate,
not a reader, asked; HELM's own words name every untaught requirement, and the number of names equals the number of
untaught slots in its one recipe; and each name has the head word of a second ingredient written on a tagged line, which
is not a unit, a note word, a participle or a key line. **Named limits:** (1) names are matched to tagged lines by head
word, not by line position (a phantom from an untagged line with the same head word as a tagged tail would pass); a
line-position check needs a recorder field (`rec["wide_support"] = {p: book.support_of(p) for p in book.recipes}` in
`chat_harness.Dialogue.record`), NOT part of A-R1W7-11 unless the owner asks; (2) the drop rules err toward not exempting:
an honest ask on a second ingredient named like a participle or a deny word ("flaxseed", "chicken", "yolks"), or whose
plural the frozen `head_norm` does not fold to HELM's name ("bay leaves" → `leave`, HELM `bay leaf`), stays counted,
costing K4, never K3; (3) the sentence regexes are tied to the v10 cut's `say_wide` text by a test (T2); a later
change to that text makes the test fail and, until fixed, exempts nothing; (4) the deny list is frozen here and
owner-reviewable (section 7).

### 3.3 Status sets, from the code

- Exempt (closed allow-list): **`UNDETERMINED_CLARIFY`** on path `"wide"` with the G1 untaught-requirement sentence.
- Never exempt: `BRAIN_UNDETERMINED` (the gate passed); the G1 missing-stock sentence; every `CLARIFY_WIDE_<code>` of the
  wide reader (including v7.3's `ALTERNATIVE_WHICH_ONE` and `RAN_OUT_WHICH_LINE`, `AMOUNT_IS_A_RANGE`, `AMOUNT_APPROXIMATE`,
  `NO_AMOUNT`, `NO_NAME`, `UNIT_NOT_IN_TABLE`, `AMOUNT_HAS_TWO_PARTS`, `SAME_INGREDIENT_TWICE`, `UNREAD_CLAUSE`,
  `NO_PRODUCT`, `ABSENT_STATED`, `AMOUNT_RELATIVE`); the face holds (`CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT`,
  `CLARIFY_WIDE_FACE_UNKNOWN_PRODUCT`, `CLARIFY_WIDE_FACE_UNKNOWN`, `CLARIFY_WIDE_PURPOSE_ABSENT`,
  `CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT`); `CLARIFY_WIDE_DISH_NAME_NOT_BOUND`, `CLARIFY_ROUND_TRIP_FAILED`,
  `UNDETERMINED_UNKNOWN_PRODUCT`, `WIDE_NOT_MINE`, `REFUSE_NOT_VERIFIED`, every licensed-path status (`CLARIFY_ENGLISH_*`,
  `UNDETERMINED_CLARIFY` with path `"licensed"`), `NOT_ROUTED_TO_LOOP:<intent>`, `CLARIFY_WIDE_UNSETTLED_SAME_NAME`,
  `CLARIFY_ALWAYS_ASK`, `CRASHED`, and any record with no `scored_turn`.

### 3.4 Counts and consistency

For EVERY key (tagged or not), (b) is also computed on its own, outside the 3.2 chain, for the recount only;
`a11_strict_recount` = the number of keys with (b) True. For each key with (a) True and (b) True, (c), (d), (e) are
evaluated as in 3.2. Outputs: `out["totals"]["a11_strict_recount"]`;
`out["totals"]["unexplained_asks_strict_after_a11"] = unexplained_asks_strict − len(exempted)`;
`out["totals"]["a11_consistent"] = (a11_strict_recount == unexplained_asks_strict) and set(exempted) ⊆ {ids with (b)}`
(so the after count is never below 0); `out["a11_exempted_ids"]` (sorted); `out["a11_checks"]` (one row per tagged ANSWER
key: `id`, `tagged_lines`, `a`–`e`, `exempt`, `unlearned`, `allowed_tail_heads`, `raw_lines_found`, `error` when any);
`per_item[i]["a11_exempt"]`.

### 3.5 Where the code goes (wave-7 package only; no frozen neighbour is edited)

- **New `r1w7/honest_ask_w7.py`** (stdlib + the namespace's frozen modules + `multi_qty_w7`'s `PAREN_RX` / `SEP_RX`):
  `AMENDMENT = "A-R1W7-11"`, `EXEMPT_STATUS`, `TAG_RX`, `G1_ONE_RX`, `G1_MANY_RX`, `NAME_SPLIT_RX`, `PARTICIPLE_RX`,
  `DENY`; `tagged_lines(key)`; `question_sentence(rec)`; `tail_heads(raw_line, G)`; `allowed_heads(key, raw, G)`;
  `honest_ask(ns, key, rec, n_lessons, raw_lines) -> dict`; `apply(ns, out, keys, inputs, doc, raw_by_id) -> out`.
- **`r1w7/score_w7.py`**: `from . import honest_ask_w7 as HA`; `score_real(ns, HV, keys, inputs, doc, plainness_scored,
  raw_by_id=None)`; right after line 78 (`out = ns.SC6.score_real(ns, keys, inputs, doc)`): `HA.apply(ns, out, keys, inputs,
  doc, raw_by_id)`. A caller that passes no raw lines gets no exemption.
- **`r1w7/merge_r1w7.py`**: `Run.__init__` reads `ex / "SAMPLE_REAL_X7.json"` when present → `self.raw_real = {id:
  raw_lines}` and `self.sample_real_sha256` (else `{}` and `None`; never raises); `arm_summary` passes
  `raw_by_id=self.raw_real`; K4 (lines 336–340): `"value": bool(t) and t.get("a11_consistent") is True and
  t.get("unexplained_asks_strict_after_a11") == 0`, keeping `"unexplained_asks_strict"` and adding
  `"unexplained_asks_strict_after_a11"`, `"a11_strict_recount"`, `"a11_exempted_ids"`, `"sample_real_sha256"`,
  `"a11_flag_for_human_review"` (each exempted item's `id`, `tagged_lines`, `unlearned`, `allowed_tail_heads`: reported as
  `FLAG_FOR_HUMAN_REVIEW`, not a gate) and `"amendment": "A-R1W7-11"`. `READER` becomes `"r1w7.merge_r1w7 v3 (2026-10-21,
  A-R1W7-11: K4 reads the strict count after the MULTI_QTY honest-ask exemption; reads SAMPLE_REAL_X7.json for the tagged
  lines)"`.
- Not touched: `multi_qty_w7.py` (the tag rule; it still sets `representable` False, so K1's denominator effect stays),
  `custody_w7.py`, `chat_harness.py`, `units_w7.py`, every file under `deps/`.

### 3.6 Text for the preregistration (append as section 23; sections 19–22 are not edited)

> **23. Amendment A-R1W7-11 (owner's word 2026-10-21: "Exempt from K4 only"; a fresh draw only).** K4 HONEST reads
> `unexplained_asks_strict_after_a11` = the frozen strict count minus the asks exempted here, and is false unless
> `a11_consistent` holds (a recount of the frozen rule equals the frozen strict count, and every exempted ask is one it
> counts). An ask is exempted only when, checked in order: (a) the key is ANSWER and carries a `line<i>:MULTI_QTY` tag;
> (b) RB-W1T's `unexplained_ask` counts it; (c) the question's status is `UNDETERMINED_CLARIFY` on the wide path; (d) the
> question's loop sentence is HELM's untaught-requirement sentence, its names count exactly the untaught slots of the one
> wide recipe whose learned coefficients equal the key's line count, and its dish is the lessons' dish; (e) each name's head
> word is the head of a second-amount tail on a tagged line (read from `SAMPLE_REAL_X7.json` with the frozen grammar), not a
> unit, a note word, a participle or a key line's head. These checks are necessary, not sufficient; their limits are listed
> in the design (DESIGN_V73_A11.md 3.2). Each exempted item is listed as `FLAG_FOR_HUMAN_REVIEW`. The strict count is still
> reported. The question score, K1, K3, NH-CHAT, P, N, every gate and instrument row are unchanged; a wrong number stays
> WRONG. No reading of c51–c56 is redone.
>
> **23.1 Correction to section 19.1.** Section 19.1 says a tagged item "then scores `NOT_SCORED` (an undetermined key),
> exactly as recipes with a range, an approximate amount, an odd form or a unit outside the top-20 table already do". That
> premise is false in the frozen code. `rbw1t.keys_rbw1t.score_question` returns `NOT_SCORED` only when the key's answer
> word is not ANSWER and never reads `representable`; `r1w6.score_w6.score_real` reads `representable` only for K1's bar
> (`rep_answer`, `fully_learned_rep`); `unexplained_ask` never reads it. So A-R1W7-7 as built changed only K1's
> denominator: a tagged ANSWER key, like every not-representable ANSWER key, kept its question score and stayed in K4's
> strict count. The "would have been `NOT_SCORED`" statements of 19.4 and 19.5 are `WITHDRAWN` as stated; those items
> stay scored for their question. The 19.5 counts themselves (6 of 128 tagged; representable 120 to 114) stand. The error
> is the builder's (spec §7.119). Readings c51–c56 stand as read.

### 3.7 What A-R1W7-11 does not do

It does not exempt any untagged item, any reader / clarify / routing ask, any `BRAIN_UNDETERMINED`, any missing-stock ask,
any ask where a lesson was not LEARNED (the frozen rule does not count those anyway), any licensed-path ask, or any ask whose
names are not tagged tails. It does not touch the reported wave-6-rule count (`unexplained_asks`, D-W6-12). It does not
change keys, the tag rule, the draw, custody or the arms.

## 4. Part 3 — test plan "through the real scoring program"

### T1 — HELM unit tests (`test_helm_reader_gap.py`, written first, run on v7.2 to fail)

Class **J `DanglingOrAsksWhichOne`** and class **K `AmbiguityBeforeAnyGuess`** (the author's own sentences, from F3's template):

| Test | Asserts | On v7.2 |
|---|---|---|
| J1 | `parse_line("1 can tomatoes or")`: name `tomato`, unit `can`, amount 1, `said` `1 can tomatoes or`, `own` `1 can tomatoes`, `dangling_or` True | FAILS |
| J2 | D1 lesson 0 `read_wide`: `CLARIFY`, code `ALTERNATIVE_WHICH_ONE`, slots `first` `tomato`, `second` `chopped tomato`, `words` `1 can tomatoes or`; no `witness`, no `pending` | FAILS |
| J3 | the same with `or;`, with the comma form `1 cup butter, or` (D4), with the pair second-to-last, with the pair LAST (`second` absent, the no-partner sentence), as a STOCK sentence, and as a batch with no dish name (no pending kept) | FAILS |
| J4 | D1's three lessons, stock and question through `HELMEndToEndLoop(wide_brain=True)`: every lesson and the stock `CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE`, path `wide`, 0 cubes written; the question asks; no wide recipe | FAILS |
| J5 | D3 the same (the which-one ask comes before `SAME_INGREDIENT_TWICE`) | FAILS |
| J6 | X1 through the loop: every lesson `CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE`; no lesson admitted (no WRONG possible) | FAILS |
| J7 (pin) | a plain `parse_line("2 cups flour")` dict has keys `amount, name, own, said, unit` only; a plain reading has no which-one code; `2 large or 4 small green peppers` still `AMOUNT_HAS_TWO_PARTS`; `1 cup coffee liquor` → `coffee liquor`; `1 cup dry beans or whole peas` → `dry bean` with the note kept | passes |
| J8 | a held wide stock amount named again in a which-one STOCK sentence is withdrawn; the next question asks (missing-stock sentence) | FAILS |
| J9 | the spoken sentence of J2 equals the 2.2 text exactly | FAILS |
| K1 | `resolve_ran_out("tomato", ["tomatoes with juice", "chopped tomato", "onion"], own)` → `tomato` (unchanged) | FAILS (`chopped tomato`) |
| K2 | `resolve_ran_out("sugar", ["sugar beet", "brown sugar"])` → `sugar` | FAILS (`sugar beet`) |
| K3 | A1 through the loop: lesson 0 `TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH`; `chopped tomato` learned 1 by lesson 1 only; no WRONG | FAILS |
| K4 (pin) | exact still binds: `("sugar", ["sugar", "brown sugar"])` → `sugar`; `("stock", ["stock", "beef stock cube"])` → `stock`; and through `read_wide` (no clarify) | passes |
| K5 | `resolve_ran_out("cupfuls of sifted", ["cake flour", "sugar"], {"cake flour": "2 cups sifted cake flour", "sugar": "1 cup sugar"})` → `cake flour` | FAILS (unchanged) |
| K6 | X2 lesson 0 `read_wide`: `CLARIFY`, code `RAN_OUT_WHICH_LINE`, slots `item` `tomato`, `lines` `["tomato", "tomatoes in juice"]`; the spoken sentence equals 2.4's text | FAILS |
| K7 | X2 through the loop: lessons 0–1 `CLARIFY_WIDE_RAN_OUT_WHICH_LINE`, 0 cubes; lesson 2 learns `onion` 2; no WRONG | FAILS |
| K8 (pin) | R2g does not fire beside `brown sugar`, `beef stock cube`, `tomato paste` | passes |

Fail-first run without git stash: copy the new test file into a fresh scratch copy of the v9 `helm_now/` (v7.2) and run it
there; expected `Ran 52 tests`, 14 not passing (J1–J6, J8, J9, K1, K2, K3, K5, K6, K7; each named, failure or error) and the
3 pins passing. Then on v7.3: the host's 12-name list `Ran 297 … OK (skipped=1)` from the kit's loader (`HELM_LOADER`),
with `HELM_SESSION_DIR` in scratch.

### T2 — A-R1W7-11 tests (`tests_r1w7/test_honest_ask_w7.py`, real frozen functions via `C.setup`)

Keys: `ns.rb.keys_rbw1t.key_item({"id", "raw_lines", "pantry_lines"})` then `multi_qty_w7.apply(key, raw, ns.XG)`, on the
author's raw lines (section 1 table; pantry from `exam_rbw1t.turns_for`). Records: authored in the CHAT record shape (F7),
with `turns[-1]` = `{"kind": "turn", "loop": {"loop_sentence": …, "status": …, "path": …}}`. Each test calls the frozen
`ns.SC6.score_real` and the hooked `score_w7.score_real(…, raw_by_id=…)` on the same inputs.

| Case | Record | Expected |
|---|---|---|
| honest ask M1 | 3 lessons LEARNED (q 2, 5, 1), `STOCK_RECORDED`, `UNDETERMINED_CLARIFY`, `log[-1].path` wide, sentence naming `juniper berry`, `wide_audit [{"ok": true, "coefficients": 3, "support_slots": 4}]`, products `stew` | frozen ASKS 1, strict 1; recount 1; after 0; exempted `[M1]`; `a11_consistent` True |
| honest ask P1 | the same shape, sentence naming `peppercorn` | exempted |
| phantom C1 / C2 | the same shape, sentence naming `beaten` / `reserved` | strict 1; after 1; (e) False |
| phantom C3 | the same shape, sentence naming `lean cut` (tail head `tablespoon` is a unit, dropped) | not exempted |
| missing-stock sentence | M1 with "… because I don't know how much broth we have. How much broth is there? I didn't guess." | not exempted, (d) False |
| two names | M1-shaped key whose tagged line holds two tails whose heads fold (e.g. `6 cloves, 12 peppercorns and 2 allspice berries`); sentence "one batch for each of peppercorn and allspice berry: …", `support_slots − coefficients == 2` | exempted; with a count of 3 → not exempted |
| wrong number | M1 with `SUCCESS_EVALUATED` value `1/2` | q WRONG; totals WRONG 1; strict 0; after 0; exempted `[]` |
| right number | M1 with `3/2`, limiting `clove` | RIGHT; nothing exempted |
| reader / clarify ask | M1 with `CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT`; again with `NOT_ROUTED_TO_LOOP:GENERAL_KNOWLEDGE_INQUIRY`, `BRAIN_UNDETERMINED`, `UNDETERMINED_UNKNOWN_PRODUCT`, `CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE` | strict 1 where the frozen rule counts it; after = strict; not exempted |
| untagged honest-looking ask | D2's key (untagged) + the honest-ask record shape | strict 1; after 1; (a) False |
| (c)/(d) fail, each alone | path `licensed`; `len(log) != n + 2`; `wide_audit` missing, two entries, a dict, or `ok` False; `coefficients == 2`; `support_slots == 3`; two lesson products; sentence dish ≠ lesson dish | not exempted |
| raw lines missing | `raw_by_id` None; item id absent from it | not exempted, `raw_lines_found` False |
| record shapes | ALWAYS_ASK record; chat crash record; wave-6 crash record (lessons LEARNED, stock recorded, no `scored_turn`); fields of the wrong type (`turns` a dict, `log` None) | exempt False, no exception; the wave-6 crash record has (b) True and (c) False |
| LOOP_ON shape | the honest record with wave-3 turns (`reply_adapter` holds the sentence) | exempted (reported only; K4 reads `CHAT_ON`) |
| template tie | `say_wide` of the package's `helm_now` (v10 cut) on G1 records with 1, 2 and 3 untaught names matches `G1_ONE_RX` / `G1_MANY_RX` and splits into exactly those names; the missing-stock record matches neither | passes |
| consistency | a mixed set of the above | recount = frozen strict; after = strict − exempted; exempted ⊆ (b) ids; never below 0 |

Reader level (the real `merge_r1w7.read` on the package's synthetic run). **First, before `honest_ask_w7.py` exists:** add
the plants below to a scratch copy of the v9 `tests_r1w7/fixture_run.py` (plants only; the fixture also writes a synthetic
`SAMPLE_REAL_X7.json`, which the v9 reader ignores) and run them with the UNMODIFIED v9 `merge_r1w7.read`; record that
`K4_A11` reads K4 missed with `unexplained_asks_strict` 1 (the failure this amendment addresses), and the others miss as
listed. **Then on v10:** plants applied to `CHAT_ON`, `CHAT_ON_REPLAY` and `CHAT_DIAG` alike (so HG2/HG7 do not move):
- `K4_A11` (key 0 tagged before the keys file is written; item 0's raw lines in the synthetic sample with a second-amount
  tail; record 0 the honest ask naming that tail's head) → `marks_missed == []`, K4 strict 1, after 0, exempted `["RW:f00"]`,
  one `a11_flag_for_human_review` row;
- `K4_A11_CLARIFY` (status `CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT`), `K4_A11_PHANTOM` (sentence names `beaten`),
  `K4_A11_NO_SAMPLE` (honest-ask shape, no sample file) → K4 missed, after 1;
- `K3_A11_WRONG` (tagged, value `1/3`) → K3 missed, word `CHAT_WAVE_HARMED`;
- the existing `K4` plant still reads strict 1 and K4 missed.
`tests_r1w7/run_tests.py` gains `"tests_r1w7.test_honest_ask_w7"`.

### T3 — end to end through the package's own unit runner and scorer (scratch copies only)

Under `...\scratchpad\v73_scratch\`, one process at a time:
- `pkg_v72\` = a fresh extract of `HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip` (sha256 `ad3fb98c…` checked first);
- `pkg_v73r\` (required) = another fresh extract with ONLY `helm_wide_turn.py` and `test_helm_reader_gap.py`
  (+ `test_helm_cas_address.py` if 2.6 changed the pin) swapped in from the branch head;
- `pkg_v73\` = another fresh extract with the branch head's differing cut files (v7.3 files and F12's three memory files),
  i.e. the cut v10 would seal.
In each copy the changed files' hashes are rewritten in `contract/HELM_CUT_R1W7.json` and the byte-equal
`helm_now/SOURCE_CUT.json` (commit field unchanged); every T3 output JSON carries `"helm_files_from": "branch head <sha>"`
and `"cut_commit_field_is_plumbing": true` (scratch, never sealed). The A-R1W7-11 files go into the scorer side of each copy.
Neighbours by `R1W7_W1_DIR`, `R1W7_W3_DIR`, `R1W7_W3B_DIR`, `R1W7_W6_DIR`, `R1W7_RBW1T_DIR` →
`C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\x7v9_custody\pkg\deps\<dir>` (freeze-checked by `setup`).

Inputs: `INPUTS_REAL_AUTHOR.json` (schema `helm.r1w7.real-inputs/1`; the 13 items of section 1 — D1, D2, D3, D4, A1, X1,
X2, C1, C2, C3, C4, M1, P1 — built by `exam_rbw1t.turns_for` with authored multipliers 3, 3/2, 5/2; ids `AUTHOR:D1` …) and
the matching raw lines as `raw_by_id`; keys as in T2. Per copy: `python -X utf8 -B -I <copy>\r1w7\units_w7.py chat --exam
X7_REAL --arm CHAT_ON --items … --items-sha256 … --scratch <fresh> --out …` and the same with `loop --arm LOOP_ON`.
Scoring: a driver (`t3_score_v73.py`, kept in this folder) calls the copy's `score_w7.score_real(ns, HV, keys, items, doc,
True, raw_by_id=…)` and, for per-lesson detail, the frozen `real_record_view` + `score_lessons`. Output: one JSON with the
three copies side by side (v7.2 / v7.3-reader-only / v7.3 + F12).

Expected (from section 1's loop probe; the chat may differ and is reported as found, never tuned):

| Item | `pkg_v72` | `pkg_v73r` and `pkg_v73` (both arms) |
|---|---|---|
| D1, D3 | lesson 0 WRONG; then NOT_LEARNED | NOT_LEARNED ×3 (which-one) |
| D2, D4 | RIGHT 3/2 | ASKS, lessons NOT_LEARNED (not unexplained) |
| A1 | lesson 0 WRONG | NOT_LEARNED, LEARNED, LEARNED |
| X1 | NOT_LEARNED, NOT_LEARNED, LEARNED | NOT_LEARNED ×3 |
| X2 | lesson 0 WRONG | NOT_LEARNED, NOT_LEARNED, LEARNED |
| C1, C2, C3 | ASKS, counted; not exempted | the same |
| C4 | lesson 2 NOT_LEARNED; not counted | the same |
| M1, P1 | ASKS, counted; exempted | the same |
| totals | strict 5, after-a11 3, exempted `[AUTHOR:M1, AUTHOR:P1]` | the same; `lessons_WRONG` 0, `WRONG` 0 |

Pass condition: on `pkg_v73r` and `pkg_v73`, `lessons_WRONG == 0` and `WRONG == 0` on `CHAT_ON` and `LOOP_ON`, exempted ids
exactly `[AUTHOR:M1, AUTHOR:P1]` on every copy and arm, and C1, C2, C3 never exempted. `pkg_v72` must show at least one
WRONG lesson among D1, D3, A1, X2 (else the test does not exercise the fault and is reported as such, not tuned).

## 5. Files

| File | Change |
|---|---|
| `helm_wide_turn.py` | R1 (`DANGLING_OR_RX`, `parse_line`), R1a (`parse_lines` step, `ALTERNATIVE_WHICH_ONE`), R2 (`resolve_ran_out`), R2g (`read_wide` step, `RAN_OUT_WHICH_LINE`, local `STOP_WORDS` copy), `WHICH_ONE_CODES`, `take_over` clause, `wide_turn` withdrawal on a which-one ask, two `say_reader_question` sentences, `READER_VERSION` v7.3, header note |
| `test_helm_reader_gap.py` | + classes J (9) and K (8): 35 → 52 tests |
| `test_helm_cas_address.py` | `PINNED_OFF_SHA256` recomputed after the reader-string-only diff (2.6) + dated comment |
| `docs/working/r1_wave7/v73_a11/` | this design and its `.sha256`; later `AMENDMENT_A_R1W7_11.md`, `honest_ask_w7.py`, `test_honest_ask_w7.py`, `apply_amendment_11.py` (applies to a fresh v9 extract; refuses on a missing or doubled anchor, as `apply_amendment_7.py`), `t3_score_v73.py` + its JSON output, copies of the probe scripts |
| package v10 (new `build_v10\`, from a fresh extract of the v9 zip; `build_v9\` never edited) | new `r1w7/honest_ask_w7.py`; `r1w7/score_w7.py` (import, keyword, one call); `r1w7/merge_r1w7.py` (`READER`, sample read, keyword, K4); new `tests_r1w7/test_honest_ask_w7.py`; `tests_r1w7/fixture_run.py` (5 plants + synthetic sample); `tests_r1w7/run_tests.py` (+1 name); `PREREGISTRATION_R1W7.md` (append §23); then the reseal's own amendment (A-R1W7-12: HELM cut = merged head carrying v7.3, ask-prefix check widened to 13 statuses, exclusion block `X7v9_c56`, fresh seed bands, labels, the line to sign) and `FROZEN`/`PACKAGE_FREEZE` |
| `docs/CAS_HARNESS_SPEC_SHEET.md`, `CHANGELOG.md` | a new dated section and change-log row in the same commit as each result |

**Does not change:** every frozen neighbour (`rbw1t` keys and scoring, `xreal`, `score_w6`, `harness_w6`, `arms_rbw1t`,
`custody_w6`); `multi_qty_w7.py`, `custody_w7.py`, `chat_harness.py`, `units_w7.py`, the CONV / NOISE scoring; every mark
other than K4, every gate and instrument row, the status-word order, arms, exam sizes; `helm_brain_wide.py`,
`helm_faces_in.py`, `helm_end_to_end_loop.py`, `helm_chat.py` (beyond F12's already-merged lines).

## 6. Order and stop rules

1. T1 written, shown failing on v7.2 (scratch: 14 named, 3 pins pass), then v7.3 built; 12-name list OK; pin per 2.6.
2. T2's reader-level plants run against the UNMODIFIED v9 merge and their misses recorded, BEFORE `honest_ask_w7.py` is
   written; then A-R1W7-11 built in `docs/working/…` and applied to a fresh v9 extract; T2 and the package's suites pass;
   the plants read as listed.
3. T3 on scratch copies. A WRONG lesson or WRONG answer under v7.3, an exemption of C1, C2 or C3, or a missing exemption of
   M1 or P1 is a STOP (no reseal), reported as found.
4. PR to the thread branch, with the spec section and change-log row in the same commit as each result; v10 reseal by the
   forked session's process; its practice run must read 0 WRONG. The practice reading also reports, not as gates: every
   a11-exempted item with its untaught names and tagged tails (`FLAG_FOR_HUMAN_REVIEW`), and the number of representable
   ANSWER keys holding a dangling-"or" raw line (R1a's K1 exposure).
5. A fresh exam only on a line the owner types. Nothing here approves one.

**Compute (owner's AWS order of 2026-09-23).** T1, T2 and T3 are light runs and stay on the laptop under this stated
exception: measured 280 HELM tests in 5.136–6.816 s in one process; free physical memory at the finalize runs 707,044 KB
(about 690 MB). Rule: run on the laptop only if at least 500 MB is free at the start; otherwise stop and report the blocker
(no silent fallback). The reseal's host runs and any exam stay on AWS as before.

## 7. Open questions for the owner (none blocks the build; each answer would come as a new amendment or version)

1. **R2g departs from the letter of §7.119 (b)**, which says "an exact match still binds". R2g makes HELM ask instead, only
   where the frozen key would give two lines the same name ("tomatoes" beside "tomatoes in juice"). If you strike it, an
   X2-shaped recipe can store a wrong amount (a K3 failure).
2. The A-R1W7-11 drop rules (participle pattern, deny list, unit words) err toward NOT exempting: an honest ask on a second
   ingredient such as "flaxseed", "chicken" or "yolks" stays counted (a K4 cost). Review the list?
3. Reader gaps left open, seen in this design's own probes: "3 eggs, 1 beaten", "2 tablespoons reserved" and ", a lean cut"
   each make HELM invent an ingredient and ask. v7.3 does not fix them and A-R1W7-11 does not exempt them, so such a recipe
   on a fresh draw fails K4 honestly. A reader rule for them would be a new version, only on your word.
4. R1a, R2 and R2g turn some right-by-luck answers into asks (D2 and D4 now ask "which one?"). That can cost K1, never K3.
   Accept that cost?

## 8. The critic's findings, item by item

| # | Severity | Checked against | Verdict and what changed |
|---|---|---|---|
| 1 | HIGH | critic's probe re-run here (identical); `helm_wide_turn` 418–442 (a line after a comma that starts with an amount is its own line) | Holds. C1/C2 were exempted by count-level (d). Folded: (e) line-level tail-head check with participle, deny, unit and key-head drops; C1, C2 in T2 and T3 as not exempted. Added what the critic left open: keys hold no raw lines (F10), so the reader reads `SAMPLE_REAL_X7.json`; with no raw lines nothing is exempted. |
| 2 | HIGH | probe log; `xreal.grammar.qty_at` (an article counts only before a unit word) | Holds. C3's phantom comes from an untagged line. Folded by (e): `lean cut` is not a tagged tail head; the critic's prototype kept `tablespoon` as allowed, so unit words are now dropped explicitly. C3 in T2/T3. |
| 3 | MEDIUM | `chat_harness.loop_view` 64; `say_wide` 764–777; `_finish` 453–454 | Holds. Folded: (d) reads the loop sentence; 3.2, 7 and §23 corrected. Refined: the sentence is read from the last turn of kind `"turn"` (not `turns[-1]`, which can be a noise turn), and from `reply_adapter` on wave-3-shaped records. |
| 4 | MEDIUM | `_wide_question` 1299–1318; `evaluate` 626–629 | Holds as a proof gap (no failing case shown). Closed: the missing-stock sentence is a different template; "proves" removed; checks called necessary, not sufficient. |
| 5 | HIGH | critic's probe re-run (first draft: X1 lesson 0 learns 2 vs key 3, WRONG) | Holds. Folded by building §7.119 (a) as written (R1a): X1 asks on every batch (section 1 table; T1 J6; T3). |
| 6 | HIGH | probe re-run; `resolve_ran_out` 546–547 | Holds (X2 WRONG in v7.2 and the first draft). Folded as R2g, but as a reader question with its own code, not "return the name unchanged": in the exact case the name IS a batch name, so returning it binds; the critic's own scripts returned a marker string, which reached HELM's voice (`run\final_probe.log`). T1 K6, K7, K8; T3. |
| 7 | HIGH | spec §7.119 "Proposed next FIX FIRST" (a), quoted in 2.2 | Holds. Folded: (a) built as written; "both needed" dropped; the old open question 2 removed. Added what the critic left open: `take_over` must take the which-one ask (F9), or the person never hears it. 13 wide statuses, 2 added (R2g's code is the second). |
| 8 | MEDIUM | the first draft's T1–T3 | Holds. Folded: X1, X2 in T1 and T3; C1, C2, C3, the missing-stock record and M1/P1 in T2; plant `K4_A11_PHANTOM`. |
| 9 | MEDIUM | the first draft's T2 | Holds. Folded: plants run on the UNMODIFIED v9 merge first (step 2 of section 6), then on v10. |
| 10 | MEDIUM | F11; finalize probe record cases | Holds, and is sharper than stated: a wave-6 crash record can satisfy (b) (lessons LEARNED, no `scored_turn`); the probe shows (b) True, (c) False, no exception. Folded: ordered short-circuit, `.get()`, never raises; T2 record-shape cases. |
| 11 | LOW | `chat_harness.py` 239 | Holds. The `inner_status` sub-check is dropped. |
| 12 | LOW | first draft 3.4 | Holds. Folded: (b) computed for every key; `a11_strict_recount`; exempted ⊆ counted. |
| 13 | LOW | first draft 2.1 | Holds. The unused `alternatives` mark is replaced by R1a's question, which carries the pair as its slots; T1 J3, J7, J9 test it; R2's stripped own-words path gets K5; the 2.6 canon diff runs on the real implementation. |
| 14 | LOW | first draft T3 | Holds. Folded: scratch labels in every T3 output; `pkg_v73r` required; three copies side by side. |
| 15 | LOW | first draft 0 and 3.2 | Holds. Folded: "proves" removed; named limits in 3.2; exempted items listed as `FLAG_FOR_HUMAN_REVIEW` in every reading (practice included), reported only. |
| 16 | LOW | owner's order, CLAUDE.md 2026-09-23 | Holds. Folded: section 6 states the light-run exception with measured numbers and a memory floor. |
| 17 | NONE | — | Confirmed. §23.1's `WITHDRAWN` stays scoped to the "would have been `NOT_SCORED`" sentences; the 19.5 counts stand; spec section and change-log row in the same commit (section 6, step 4). |

## 9. Frozen before code

This design is final. Its sha256 is written to `DESIGN_V73_A11.sha256` in this folder (one line: the hash, two spaces, the
file name), and from that moment this file does not change. The build follows this text. Anything the build finds that
this text did not foresee is recorded in the build report as a deviation, with its reason, and never by editing this file;
a change of rule needs a new design file with its own hash. No code, test, package or exam exists yet because of this file:
reader v7.3 and A-R1W7-11 are designed, not built; after the build they would be `ENGINEERED-NOT-VALIDATED`, and the chat on
any exam stays `NOT LICENSED`.
