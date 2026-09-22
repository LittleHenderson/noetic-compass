# Three PCBA-book issues for an owner decision

Prepared 2026-09-22 by an independent verifier (label `book`). Nothing in the book was edited.

- Book read at commit `65ad300835c06f9feff154170cb8b103d5d13ffa` (`65ad3008`), with `git show` only.
- The book text at `65ad3008` is the same as the peer-audit snapshot `626cc84b` and the canon pin `d50abbbc`. (`git diff --stat 626cc84b 65ad3008 -- book/CAS_PCBA_Engineer ':!*.pdf' ':!*.png'` prints nothing.)
- Every quote and number below comes from `book_decision_probe.py` (next to this file). It writes `book_decision_probe.json` and `truth_tables.md`.
- Reproduce: `C:/Python314/python.exe -B book_decision_probe.py` (exit 0). Standard library only. No model, no GPU, no network.

What kind of evidence this is:
- **Real:** the quotes. They are the exact bytes of the book at `65ad3008`.
- **Calculated:** the truth tables and gain numbers. They are exact arithmetic (Python `fractions.Fraction`). They are not measurements.
- **Not measured:** no circuit in this book has ever been run for these checks. Nothing here is an observation.
- **Open:** all three issues need an owner choice. This file does not make that choice.

---

## Issue 1 — What happens to a CJT in breakdown?

Plain meaning: the book gives two different rules for what a CJT's output does when it is overloaded ("breakdown"). CJT means Cognitive Junction Transistor.

- **Rule A — the flip is automatic.** In breakdown, the output Noetic always changes to its involution partner (`^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`).
- **Rule B — the flip is conditional.** A flip happens only when an explicit rule is declared.

### The conditional rule (2 lines, both in Appendix B, both added by OD-A commit `0fc6bb30`)

- `Appendix_B_Component_Datasheets.md:59`: `| **Breakdown** | overload past safe limits | engineered failure behavior; an involution flip occurs only when that explicit rule is declared |`
- `Appendix_B_Component_Datasheets.md:79`: `| Breakdown rule invoked | declared overload rule changes the output, possibly by a licensed involution | (design: clamp before breakdown) |`

Before OD-A, line 59 said: `| **Breakdown** | overload past safe limits | effect flips to its involution pair (`^2`→`^3`) — the controlled state inverts |`.
So OD-A created this contradiction. Before OD-A, the book agreed with itself (Rule A everywhere).

### The automatic rule (the three lines you named)

- `Appendix_A_Notation_Quick_Reference.md:40`: `Under CJT **breakdown**, output flips to its involution pair; self-duals have nowhere to flip (stable anchors).`
- `Appendix_A_Notation_Quick_Reference.md:121`: `Regions: **Cutoff** (no effect) · **Active** (Δeffect ≈ β·Δcause) · **Saturation** (maxed) · **Breakdown** (flips to involution pair). Named form: ...`
- `Appendix_C_CCDL_Language_Reference.md:549`: `- **Breakdown** — gross overload; the effect flips to the involution pair (`^2`→`^3`, `^8`→`^9`), a bug unless deliberately designed with protection.`

### Every other passage that states Rule A without a condition (whole-book search)

There are 26 places in total (the three above included). Each says the flip simply happens:

Appendix A:40, A:121 · Appendix C:549, C:765 · Appendix D:545 · Appendix E:74 · Appendix F:172 · Glossary (Appendix G):47–50, G:238 · Chapter 2:56, 2:220 · Chapter 3:101, 3:103, 3:188, 3:199 · Chapter 4:161, 4:176 · Chapter 5:171 · Chapter 6:195 · Chapter 9:5, 9:203, 9:215 · Chapter 14:216 · Chapter 21:296 · Chapter 22:19 · STYLE_GUIDE:125–126 (the style guide is not in the printed book's build list).

Softer passages that fit either rule: Glossary G:324–325 ("can invert"), G:397–398 (self-duals cannot flip), Appendix C:1041, Appendix D:764, Chapter 5:177, Chapter 11:21, Chapter 14:285, Chapter 22:361.

The peer audit (BOOK-AUDIT-1) cited 6 of these 26 passages: A:40, A:121, C:549, Ch 3:101, Ch 3:103 and G:47–48. Its finding is correct. Its list is only part of the full set.

### Two more facts the owner should know

1. **You cannot declare the rule in CCDL.** Rule B depends on an "explicit rule" being declared. But no CCDL syntax for this exists in the book. The CJT parameter table (Appendix C:526–533) has only `β`, `sat`, `cutoff`, `region`, `gm` and `rπ`. The reserved-key list (Appendix C:185) has no rule key either. So under Rule B as written, the flip can never be triggered.

   > **Precision note added by Claude after spot-checking, 2026-09-22.** The reserved-key list at Appendix C:185
   > *does* contain a key named `breakdown`, but it is the Zener's numeric threshold (`Zener< state, breakdown=… >`,
   > range [0,1], Appendix C:410), not a rule that declares a flip. A CJT can also declare `region=breakdown`
   > (Appendix C:511, :531), which names the *intended operating region* and says nothing about whether the output
   > flips. So the conclusion stands — nothing in CCDL declares Rule B's "explicit rule" — but "no rule key" should be
   > read as "no key that declares a flip rule".
2. **No code picks a side.** `quantifiers.py` has only the name `BREAKDOWN = "BREAKDOWN"` (line 104 at `65ad3008`, line 107 at `9e2e3a8a`). `compiler.py` never mentions breakdown.

Also, the committed EPUB at `65ad3008` was last committed on 2026-08-09 (`cc07e9e8`), before OD-A (2026-09-21). It still contains the old Rule A wording (`the controlled state inverts`: 1 hit; `only when that explicit rule is declared`: 0 hits).

### A concrete example where the two rules give different outputs

Take Chapter 4's own first circuit (Chapter 4:29): `CJT< ^8^C_{F2}|A | ^5^E_{F4}|f => ^9^C_{F6}|A > [β=2.4]`

Drive it into breakdown and declare no involution rule. (Declaring one is impossible anyway, as shown above.)

| Reading | What probe `tp1` reads on the effect |
|---|---|
| Rule A (Ch 4:176 names this exact case: "`^9`→`^8`") | `^8^C_{F6}\|A` — the Noetic flipped |
| Rule B (Appendix B:59) | `^9^C_{F6}\|A` — no flip; the "engineered failure behavior" is not specified |

Assumption, stated plainly: no passage says what happens to Domain, Drive or Register in a flip. The table keeps them unchanged.

Under Rule A, Chapter 4:161's test ("If you instead see ... an involution flip, the transistor has gone into breakdown") detects breakdown. Under Rule B, the same test cannot detect it.

Full matrix (from the probe): the two rules disagree for any effect Noetic `^2 ^3 ^5 ^6 ^8 ^9` when no rule is declared. They agree for the self-duals `^0 ^1 ^4 ^7`, and whenever a rule is declared.

### Choices open to the owner (none has been made)

- (a) Keep Rule A. Put Appendix B:59/79 back to the automatic flip.
- (b) Adopt Rule B. Then rewrite the 26 passages, add CCDL syntax for declaring the rule, and say what "engineered failure behavior" produces when no rule is declared.
- (c) Keep both, with a written precedence rule. For example: "Appendix B governs, and every other passage describes the default rule `X`."

---

## Issue 2 — How many inputs do XOR and XNOR take, and what do they compute?

Plain meaning: one part of the book lets XOR and XNOR take any number of inputs from 2 up. Other parts say exactly 2. With 3 or more inputs, "XOR" can mean several different things.

### The conflicting passages

- `Appendix_C_CCDL_Language_Reference.md:447`: `Gates act on engineered Boolean firing flags obtained by thresholding continuous CAS activations. `NOT` takes one input; the rest take two or more. AND detects a both-active condition. XOR is true for exactly one active input. XNOR is true when its inputs agree, including the both-inactive case.`
- `Chapter_10_Special_Purpose_Components.md:115`: ``| `XOR< s₁, s₂ >` | 2 firing flags | fires iff exactly one fires |``
- `Chapter_10_Special_Purpose_Components.md:116`: ``| `XNOR< s₁, s₂ >` | 2 firing flags | fires iff the inputs agree, including both-inactive |``
- `Appendix_B_Component_Datasheets.md:389`: ``| `XOR< s₁, s₂ >` | 2 | fires iff exactly one fires | exclusivity detector — one route, never both |``
- `Appendix_B_Component_Datasheets.md:390`: ``| `XNOR< s₁, s₂ >` | 2 | fires iff inputs agree | equivalence detector; both-active **and** both-inactive count |``

Other XOR/XNOR passages found: Chapter 10:87 ("takes one or more binary inputs"), 10:96 ("true if inputs *differ*"), 10:97 ("true if inputs agree"), 10:99, 10:106, 10:118, 10:324, 10:356 · Appendix B:367, 377, 392, 394, 401 · Appendix C:179, 183, 444, 452, 453 · Appendix A:137 · Appendix E:337 ("XOR fires only when its inputs differ") · STYLE_GUIDE:145.

A third arity rule sits in the grammar itself: `arg_list ::= arg , { "," , arg }` (Appendix C:379, and again at C:890). The grammar accepts one or more arguments for every gate, even `XOR< a >`.

### Three readings of XOR (and XNOR) for 3 or more inputs

- XOR (i) **odd parity**: true when an odd number of inputs are active. (This is the usual digital-electronics meaning.)
- XOR (ii) **exactly one**: true when exactly one input is active. (This is the book's stated rule.)
- XOR (iii) **inputs differ** (not all equal): the wording of Chapter 10:96 and Appendix E:337.
- XNOR: the complement (logical NOT) of each: even parity, NOT exactly-one, and **all equal**. "All equal" is the book's "inputs agree" wording.

With 2 inputs, all three readings give the same answer (checked). So OD-A's two-input correction is unaffected.

#### 3 inputs

| inputs | k_active | XOR:odd_parity | XOR:exactly_one | XOR:not_all_equal | XNOR:even_parity | XNOR:NOT exactly_one | XNOR:all_equal |
|---|---|---|---|---|---|---|---|
| 000 | 0 | 0 | 0 | 0 | 1 | 1 | 1 |
| 001 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 010 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 011 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 100 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 101 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 110 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 111 | 3 | 1 | 0 | 0 | 0 | 1 | 1 |

#### 4 inputs

| inputs | k_active | XOR:odd_parity | XOR:exactly_one | XOR:not_all_equal | XNOR:even_parity | XNOR:NOT exactly_one | XNOR:all_equal |
|---|---|---|---|---|---|---|---|
| 0000 | 0 | 0 | 0 | 0 | 1 | 1 | 1 |
| 0001 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 0010 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 0011 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 0100 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 0101 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 0110 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 0111 | 3 | 1 | 0 | 1 | 0 | 1 | 0 |
| 1000 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| 1001 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 1010 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 1011 | 3 | 1 | 0 | 1 | 0 | 1 | 0 |
| 1100 | 2 | 0 | 0 | 1 | 1 | 1 | 0 |
| 1101 | 3 | 1 | 0 | 1 | 0 | 1 | 0 |
| 1110 | 3 | 1 | 0 | 1 | 0 | 1 | 0 |
| 1111 | 4 | 0 | 0 | 0 | 1 | 1 | 1 |

### Rows where the readings disagree

| Comparison | 3 inputs | 4 inputs |
|---|---|---|
| XOR odd-parity vs exactly-one | `111` | `0111 1011 1101 1110` |
| XNOR even-parity vs NOT-exactly-one (the complements) | `111` | `0111 1011 1101 1110` |
| XOR odd-parity vs not-all-equal | `011 101 110 111` | `0011 0101 0110 1001 1010 1100` |
| XOR exactly-one vs not-all-equal | `011 101 110` | `0011 0101 0110 0111 1001 1010 1011 1100 1101 1110` |
| XNOR even-parity vs all-equal | `011 101 110 111` | `0011 0101 0110 1001 1010 1100` |
| XNOR NOT-exactly-one vs all-equal | `011 101 110` | `0011 0101 0110 0111 1001 1010 1011 1100 1101 1110` |

**An extra problem inside the book's own pair.** The book defines XOR as "exactly one" and XNOR as "inputs agree" (all equal). With 3 or more inputs, these two are **not** each other's opposite. On these rows both output 0:
- 3 inputs: `011 101 110`
- 4 inputs: `0011 0101 0110 0111 1001 1010 1011 1100 1101 1110`

Usually XNOR means NOT XOR. So making the gates variadic (any number of inputs) without choosing a reading breaks that relationship.

### Choices open to the owner (none has been made)

- (a) Make XOR and XNOR **binary only** (exactly 2 inputs). Then change Appendix C:447 to "NOT takes one input; XOR and XNOR take exactly two; the rest take two or more". Also check the grammar at C:379 and C:890.
- (b) Make them **variadic** (any number of inputs), and name the truth function: odd parity, exactly one, or not-all-equal. Then state XNOR as its exact complement, or say plainly that it is not one.

---

## Issue 3 — The "exactly 3, observed" gain in Chapter 16

Plain meaning: Chapter 16 says the feedback circuit's gain "settles to" exactly 3 and calls that "observed". The chapter's own formula does not give 3 for this circuit. Nothing was ever measured.

### The passage and its example, verbatim

`Chapter_16_Feedback_Systems.md:211`:

> Walk it line by line. The forward CJT `c_fwd` has `β=12.0` — an aggressive, unstable-on-its-own expansion, our stand-in for the op-amp's runaway open-loop gain. Left alone it would blow every prompt out of proportion. The `feedback evaluate -> expand [β=0.333]` line is Black's inverted wire: it samples the evaluation node and routes one-third of it back to *oppose* the expansion's bias. By the closed-loop formula, the observed gain settles to `1/β = 3`, regardless of whether the forward `β` is 12 or 10 or drifting — the loop divides out the forward path's volatility. The two probes let you see the contrast: `tp_fwd` shows the hot raw expansion, `tp_out` shows the disciplined result after feedback. Gain of exactly 3, set by the feedback factor, immune to the forward path. This is the current-limited, self-stabilizing topology that the CSB's reasoning rail uses in Chapter 18.

The example (Chapter 16:180–209). The lines that matter:
- `:180` `## Worked Build 1: A Negative-Feedback Amplifier, Closed-Loop Gain = 3`
- `:182` `... set so the closed-loop gain lands at exactly 3.`
- `:184` `... In CAS feedback terms, the feedback factor is `β = Rg/(Rf+Rg) = 1/3`, and with large forward gain the closed-loop gain is `1/β = 3`. So we set the forward CJT's open-loop gain high and the feedback path's `β = 0.333`.`
- `:198` `    cjt c_fwd: CJT< prompt   | bias_principles => expand   > [β=12.0];`
- `:199` `    cjt c_eval: CJT< expand  | bias_principles => evaluate > [β=1.5];` (this is the displayed 1.5 stage)
- `:200` `    cjt c_out:  CJT< evaluate| bias_principles => respond  > [β=1.0];`
- `:203` `    // β = 1/3 → closed-loop gain = 1 + Rf/Rg = 3`
- `:204` `    feedback evaluate -> expand [β=0.333];`
- `:207` `    probe tp_out:  evaluate;   // watch the tempered, fed-back result`
- `:213` `> **Bench Note — keep the loop gain large.** ... Here forward `β=12` against a target of 3 — a loop gain of 4×, enough to make the forward path's drift negligible. ...`
- Formula at `:17`–`:23`: `A_closed = A / (1 + Aβ)`. Line 17 calls its value "the actual, real-world gain you observe".

The feedback samples `evaluate`. That means `c_eval` (β=1.5) sits **inside** the loop. So the listing's true forward gain is 12 × 1.5 = 18. If `c_fwd` drifts from 12 to 10, the forward gain becomes 15.

> **Note added by Claude, 2026-09-22.** Where the loop closes is itself a reading the book does not state in CCDL
> terms. Line :211 and the Bench Note at :213 treat the forward gain as `c_fwd` alone (12, or 10 when drifting); the
> verifier's reading treats it as `c_fwd × c_eval` (18, or 15). **Under every reading in the table below, the gain is
> not 3.** Choosing between A = 12 and A = 18 is part of the owner's choice, and the CALCULATED wording below uses
> A = 18; if the owner reads the loop as `c_fwd` alone, the calculated value is 3000/1249 ≈ 2.402 (β = 0.333) or
> 12/5 = 2.4 (β = 1/3).

### Exact numbers (formula `A/(1+Aβ)`, exact fractions)

| Case | β = 0.333 (as written) | β = 1/3 (as intended) |
|---|---|---|
| A = 12 (`c_fwd` alone, as the Bench Note reads it) | 3000/1249 = 2.401921537229784 | 12/5 = 2.4 |
| A = 10 (`c_fwd` drifted, alone) | 1000/433 = 2.3094688221709005 | 30/13 = 2.3076923076923075 |
| A = 18 (full chain as listed: 12 × 1.5) | 9000/3497 = 2.5736345438947668 | 18/7 = 2.5714285714285716 |
| A = 15 (full chain after drift: 10 × 1.5) | 3000/1199 = 2.5020850708924103 | 5/2 = 2.5 |
| Limit A → ∞ (= 1/β) | 1000/333 = 3.003003003003003 | 3 |

Loop gain Aβ: A=12 gives 999/250 = 3.996 or 4; A=18 gives 2997/500 = 5.994 or 6.

Drift (β = 1/3, A 12 → 10). The forward stage drops by 1/6. The closed-loop gain drops by 6/65, which is 1/26 of 2.4. Drift is reduced, not removed.
Full chain (β = 0.333, A 18 → 15). The gain drops by 300000/4192903, which is 100/3597 of the A=18 value.
Shortfall from 3: at A=12 with β=1/3 the gain is 1/5 (20%) below 3. At A=18 with β=0.333 it is 497/3497 below.

A non-standard reading, for completeness only: put `c_eval` *outside* the loop. That gives 1.5 × 3000/1249 = 4500/1249 = 3.602882305844676, or 18/5 = 3.6 with β = 1/3. That is not 3 either.

The peer audit's four decimals (2.401921537229784, 2.3094688221709005, 2.5736345438947668, 3.003003003003003) match these fractions exactly.

### When is "exactly 3" true?

- **Only in the limit A → ∞ with β = 1/3 exactly.** At β = 1/3 the gain is 3A/(3+A). That is below 3 for every finite A.
- There is one coincidence. With β = 0.333 as written, A = 3000 gives exactly 3000/1000 = 3. Above A = 3000 the gain rises past 3 toward 1000/333 (A = 3001 gives 3001000/1000333). This is a side effect of rounding β. It is not "set by β alone".
- None of A = 10, 12, 15 or 18 gives 3 under either β.
- To come within 1% of 3 with β = 1/3 needs A = 297 (the gain is then exactly 297/100).

### History: this is not a recent change

The whole Chapter 16 file has the same git blob `3c1b6226f00206de9f0688b3f3ce4196103e779a` at `c3855275`, at OD-A's parent `0fc6bb30~1`, at `0fc6bb30`, at `d50abbbc`, at `626cc84b` and at `65ad3008`.

Line 211's text (sha256 without newline `891360f650fd792d0117f88a6970c9f65fa45c511057d3801b61940209fa294b`) is unchanged since the first draft `341cba66` of 2026-06-18, where it was line 181. The last commit to touch the file was `57fcaac7` on 2026-07-25.

The committed EPUB also carries the sentence (`the observed gain settles to`: 1 hit).

The book's own exercise answer disagrees with line 211's claim. Appendix E:519 says that for gain 5 the forward β should be "much larger than 5 (a high gain, e.g. ≥ 50–100)". It says that otherwise "the actual gain sags below 5". Line 211's example uses a forward gain only 4× the target.

### Three replacement wordings for the two claim sentences in :211 (owner picks one; the matching lines :180, :182, :203 and :213 would follow)

**CALCULATED (finite formula, exact result)**

> By the closed-loop formula `A_closed = A/(1 + Aβ)`, this circuit's gain is a calculated design value, not a measurement. The feedback samples `evaluate`, so both `c_fwd` (β=12.0) and `c_eval` (β=1.5) sit inside the loop, and the forward gain is A = 12.0 × 1.5 = 18. With β = 0.333 the calculated closed-loop gain is 18/(1 + 18 × 0.333) = 9000/3497 ≈ 2.574. If `c_fwd` drifts from 12 to 10, A falls to 15 and the calculated gain falls to 3000/1199 ≈ 2.502. The loop shrinks the forward path's drift; it does not remove it. The two probes let you see the contrast: `tp_fwd` shows the hot raw expansion, `tp_out` shows the tempered result after feedback.

**LIMITING APPROXIMATION (assumptions stated, labelled approximate)**

> The closed-loop formula says that as the forward gain grows without limit, the closed-loop gain approaches `1/β`. With β exactly 1/3 that limit is 3. With β written as 0.333 it is 1000/333 ≈ 3.003. So "gain 3" is an approximation. It holds only when the loop gain `Aβ` is much larger than 1. This build does not meet that condition well. Its forward gain is 18 (`c_fwd` × `c_eval`), and the formula gives about 2.57, not 3. Getting within 1% of 3 needs a forward gain of about 300. Read 3 as the target the loop approaches, not as the gain this circuit delivers.

**OBSERVED (only with a measurement record — none exists)**

> *Not usable today.* No measurement record exists. A search of every branch finds no run log, probe reading or evidence packet for `nfb_amplifier_gain3`. The only other file that names it is the 2026-09-22 peer audit's `book_probe.json`, and that is a formula calculation. So the word "observed" must go. Template for use only after a real run: "On [date], run [record path; circuit version; input fixture], probe `tp_out` read a closed-loop gain of [value] with `tp_fwd` at [value]; see [record path]."

A related line, lower priority: Chapter 16:47 says "a gain of exactly 3, set in metal" for the ideal op-amp. That is the standard textbook ideal (infinite A). At a real A = 100000 with β = 1/3, the formula gives 300000/100003 = 2.999910002699919.
