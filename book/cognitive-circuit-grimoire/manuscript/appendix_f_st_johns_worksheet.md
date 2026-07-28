# APPENDIX F
## St. John's Equation Worksheet
*A printable bench sheet for one operation, one admissible confirmation, and one decision*

This form implements Chapters 5 and 23. It is an instrument sheet, not a
prediction certificate. The quantities below compare operations made under the
same declared conventions. They do not establish that a confirmation was
caused by an operation, that a target will arrive on a schedule, or that the
scale factor `τ = 1/3` is a physical constant.

Print one copy per operation. Write the timing convention and horizon before
the operation begins. Do not erase a `NO-READ`; it is a result.

---

### F.1 Page-One Conventions

Complete this page once for a campaign. Copy its revision identifier onto every
operation sheet.

| Field | Entry |
|---|---|
| Campaign / board | ______________________________________________ |
| Target stated in one sentence | ______________________________________________ |
| Target state literal | ______________________________________________ |
| Timing-convention revision | __________ |
| `t_op` begins at | ☐ procedure begins  ☐ gnosis / working state establishes |
| `t_op` ends at | ______________________________________________ |
| `t_conf` begins at | **the end of the operation** |
| Clock grid | **5 minutes** |
| Confirmation rule | **first admissible confirmation only** |
| Rolling median `t_conf` from last 10 comparable operations | __________ min |
| Computed horizon `3 × median` | __________ min |
| Declared horizon `t_H = max(1,440 min, 3 × median)` | __________ min |
| Minimum separation before another operation on this target | __________ |
| One-week control-count dates | __________ through __________ |
| Unprompted matching events during control week | __________ |
| Operator signature / date | ______________________________________________ |

**Boundary rule.** An event at or beyond `t_H` is `NO-READ`, not a slow
confirmation. A later, stronger event remains descriptive evidence and never
replaces the first admissible event in the ratio.

---

### F.2 Pre-Operation Gate

| Check | Reading | Pass condition | Result |
|---|---:|---|---|
| A0 authentication | witness load ______ / object premium ______ | Chapter 21 thresholds | ☐ PASS ☐ RE-WORD |
| Drive gate | `I_attention =` ______ | above the declared cutoff | ☐ PASS ☐ HOLD |
| Wisdom gate | schematic, parameters, test points present | all present | ☐ PASS ☐ HOLD |
| Power gate | time, place, tools, consent present | all present | ☐ PASS ☐ HOLD |
| Safety board | TP1 ______ / TP2 ______ / TP3 ______ / TP4 ______ | Chapter 24 bands | ☐ PASS ☐ BLOCK |

If any row reads `RE-WORD`, `HOLD`, or `BLOCK`, stop. Do not manufacture clock
readings for an operation that did not clear its gate.

---

### F.3 Operation Record

| Field | Entry |
|---|---|
| Operation number | __________ |
| Date / start time / time zone | ______________________________________________ |
| Board revision / parameter-change revision | ______________________________ |
| Exact target used | ______________________________________________ |
| Start event observed | ______________________________________________ |
| End event observed | ______________________________________________ |
| Raw `t_op` | __________ min |
| Quantized `t_op` (nearest 5 min) | __________ min |
| `^1` Mind degree | ☐ 1°  ☐ 2°  ☐ 3° / `NO_COMPUTE` |
| `^7` Rhythm degree | ☐ 1°  ☐ 2°  ☐ 3° |
| Confounds declared before reading | ______________________________________________ |

If `^1` Mind is 3°, keep the row and mark it `NO_COMPUTE`. The row describes
the operator's condition; it does not measure the board.

---

### F.4 Confirmation Intake

| Field | Entry |
|---|---|
| First candidate event | ______________________________________________ |
| Event time / time zone | ______________________________________________ |
| Raw elapsed time from **operation end** | __________ min |
| Inside the predeclared horizon? | ☐ YES  ☐ NO |
| First admissible event for this operation? | ☐ YES  ☐ NO |
| Attributable to only this open operation? | ☐ YES  ☐ AMBIGUOUS |
| Quantized `t_conf` (nearest 5 min) | __________ min |
| `^4` Vibration degree | ☐ 1°  ☐ 2°  ☐ 3° |
| Intake verdict | ☐ READ  ☐ `NO-READ`  ☐ AMBIGUOUS  ☐ CONFOUNDED |

Only a `READ` proceeds to F.5. Preserve every other verdict in the campaign
ledger with arithmetic cells blank.

---

### F.5 Arithmetic

Use the quantized readings.

```text
t_op                         = __________ min
t_conf                       = __________ min

η = t_op / t_conf            = __________
τ                             = 1/3
result = η × τ               = __________
reduced result = a/b         = __________ / __________
A = 1/result
  = b/a
  = 3/η
  = 3 × t_conf / t_op        = __________

previous comparable A        = __________
ρ = A_current / A_previous   = __________
```

**Pair-admissibility check:** if `a > 3` after quantization, record `(a, b)` as
an arithmetic artifact and make no decision from `a` or `b`. Decide from `A`.

**Do not write `β = A`.** `A` is a ratio on delivered current. It can be paid
by target clarity, divider transmission, residual resistance, amplifier gain
within its legal range, or changes to `R_op`. A non-finite `A` is not a very
large amplifier setting; it is `NO-READ`.

---

### F.6 Band Decision

| `A` | Equivalent `η` | Instrument reading | Required action |
|---:|---:|---|---|
| `A ≤ 1` | `η ≥ 3` | sufficient | **ACT** — stop calibrating and take the practical action |
| `1 < A < 3` | `1 < η < 3` | close | **CLOSE** — finish resistance work; leave the amplifier alone |
| `3 ≤ A < 9` | `1/3 < η ≤ 1` | under-driven | **DRIVE** — change one lever, then re-read |
| `A ≥ 9` | `η ≤ 1/3` | weak coupling | **RE-SPEC** — decompose or reroute before another operation |

Selected band: ☐ ACT  ☐ CLOSE  ☐ DRIVE  ☐ RE-SPEC

Single next action authorised by this row:

____________________________________________________________________________

Single parameter or condition allowed to change before the next comparable
operation:

____________________________________________________________________________

Everything deliberately held constant:

____________________________________________________________________________

---

### F.7 Campaign Ledger

Use one row per attempted operation, including refused and unreadable rows.

**Timing ledger:**

| Op | Date | Board rev | `t_op` | `t_conf` |
|---:|---|---|---:|---:|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |

**Readings for the same operation numbers:**

| Op | `^1` | `^4` | `^7` | `η` | `(a,b)` | `A` | `ρ` | Verdict / band |
|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |
| 4 | | | | | | | | |
| 5 | | | | | | | | |
| 6 | | | | | | | | |
| 7 | | | | | | | | |
| 8 | | | | | | | | |

Trend is not accepted before three comparable `A` readings.

| Campaign check | Reading | Action |
|---|---:|---|
| Median `ρ` over the last three comparable rows | __________ | `≤ 0.6`: converging; `≥ 1.0`: stop |
| Operations currently inside an open horizon | __________ | More than one on the same target: mark later evidence AMBIGUOUS |
| Current concurrency derating `1 − k(N − 1)` | __________ | `≤ 0`: shed operations before proceeding |
| Last `NO-READ` row | __________ | None in a long ledger: re-audit the horizon |
| Last parameter change and its isolated effect | __________ | More than one change: result not attributable |

---

### F.8 Close-Out

| Close-out question | Entry |
|---|---|
| Did the practical action occur? | ☐ YES ☐ NO ☐ NOT YET DUE |
| Was any arrival estimate recorded? | __________ |
| Was it represented as a prediction? | ☐ NO required |
| Did evidence contradict the target or the board model? | ______________________________________________ |
| What will falsify the current interpretation? | ______________________________________________ |
| Operator signature / date | ______________________________________________ |
| Independent reviewer, if required | ______________________________________________ |

Keep the completed sheet with the exact board revision it measured. A row
separated from its timing convention, horizon, and parameter revision is not a
measurement you can compare.
