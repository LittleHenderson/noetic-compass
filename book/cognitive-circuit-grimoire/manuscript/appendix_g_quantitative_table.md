# Appendix G — The Quantitative Table Template

Three blank forms, meant to be photocopied. Punch the left margin and file by
operation number rather than by date — one operation can run four months, and its
sheets belong together.

An operation you did not log did not produce data. It produced an impression, and
an impression is not something you can read three weeks later and disagree with.

---

### I.1 Which form, when

| Form | Opened | Written in | Answers |
|---|---|---|---|
| **1 — Operation Log** | Before the first session; one sheet per operation | Once at setup, then one row per session | What did I build, and what did it read? |
| **2 — Confirmation Log** | With Form 1 | One block per confirmation | How far did the signal actually get? |
| **3 — Parameter-Change Log** | With Form 1 | One block per change; verdict later | Which change caused which result? |

Form 3 governs the other two. Any reading taken after an unlogged change is
uninterpretable, and the honest thing to do with an uninterpretable reading is
strike it.

---

### I.2 Page geometry

- 58 monospace columns — about 9 pt in a 6×9 text block. Nothing here is wider,
  so nothing reflows on a photocopier set to 100 percent.
- Form 1 is one page per operation. Forms 2 and 3 repeat their block; run them
  onto as many sheets as the operation needs.
- Ink, not pencil. Corrections are struck through and initialled, never erased.
  The crossed-out number is often the interesting one.

---

### I.3 Form 1 — Operation Log

```
┌────────────────────────────────────────────────────────┐
│ OPERATION LOG                        sheet ___ of ___  │
├────────────────────────────────────────────────────────┤
│ Op # ______   Operator ______________________________  │
│ Board CCB-________  CCDL rev ______  Opened __/__/__   │
│                                                        │
│ Prime desire (A0-authenticated, present tense)         │
│ ______________________________________________________ │
│ ______________________________________________________ │
│                                                        │
│ Target:  self ____    consenting other ____            │
│ (there is no third box; Chapter 26.2)                  │
├────────────────────────────────────────────────────────┤
│ PARAMETERS AS SET                                      │
│ Dial(^2) ____  Dial(^3) ____  divergence ____  (<=4)   │
│ Dial(^5) ____  Dial(^6) ____  divergence ____  (<=4)   │
│ Dial(^8) ____  Dial(^9) ____  divergence ____  (<=4)   │
│ k ______   beta ______   sat ______                    │
│ r_pi ______  g_m ______   region  act / sat / cutoff   │
│ R_op:  R_cap ____ R_policy ____ R_ctx ____ R_res ____  │
├────────────────────────────────────────────────────────┤
│ RPM GATE (Ch 21)     pass/fail + the deciding number   │
│ A0 ____  ___________________________________________   │
│ D  ____  I_attention ________ vs cutoff ________       │
│ W  ____  ___________________________________________   │
│ P  ____  ___________________________________________   │
│ CSB  ____  refusal level ______   fuse intact ____     │
├────────────────────────────────────────────────────────┤
│ SESSIONS                                               │
│ S# │  Date  │t_op│^1│ TP1 │ TP2 │ TP3 │ TP4 │ Note     │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
├────────────────────────────────────────────────────────┤
│ ST. JOHN'S (first confirmation only)                   │
│ t_op ______  t_conf ______   eta = ____ / ____         │
│ eta x 1/3 = ____ / ____    a ______    b ______        │
│ A = b ______   n_ops = a ______   T = a x t_op ______  │
├────────────────────────────────────────────────────────┤
│ CLOSED __/__/__   outcome:  manifest / abandoned /     │
│                   fuse blown / superseded by op ______ │
└────────────────────────────────────────────────────────┘
```

**Field notes.**

| Field | What goes in it | What does not |
|---|---|---|
| Prime desire | The A0-authenticated desire (Chapter 21.1) | The desire you walked in with, if the audit changed it |
| Board / rev | The CCDL revision you actually fired | The one you meant to fire |
| Dials | Both members of every pair, plus the divergence — the limit is 4 points (Chapter 25.2) | One dial with its involution partner left blank |
| CJT | β, sat, rπ, g_m as set (Chapter 3.3) | β alone. sat is what pins your readings |
| Gates | Pass or fail per gate **and the number that decided it** (Chapters 21.2–21.4) | A tick |
| Sessions | Readings taken at TP1–TP4 (Chapter 12.3); `^1` Mind graded 3°/2°/1° (Chapter 5.5) | Readings reconstructed later from the outcome |
| A | The required multiple of delivered activation at TP4 (Chapter 13.5) | A β setting. They are different quantities |

**Worked example — one session row filled.** From the Red Corvette operation of
Chapter 13.6, first session:

```
│ 01 │03/14/26│ 20 │2°│0.62 │0.18 │0.80!│0.084│TP3 pin   │
```

The `!` is the operator's own flag: TP3 sat exactly at `sat = 0.80` and did not
move when the cause improved. Mark pinning in the row the moment you see it.
That one character is what makes the next form's entry obvious.

---

### I.4 Form 2 — Confirmation Log

```
┌────────────────────────────────────────────────────────┐
│ CONFIRMATION LOG            Op # ______   sheet ____   │
├────────────────────────────────────────────────────────┤
│ C-____   Date __/__/__   Time ____:____                │
│ t_conf ________ min from end of operation              │
│ Grade    1°    2°    3°          (Chapter 5.6)         │
│ First confirmation for this operation?    Y / N        │
│ What happened ________________________________________ │
│ ______________________________________________________ │
│ Could this be coincidence?    Y / N / unsure           │
│ Recorded within ______ min of noticing it              │
├────────────────────────────────────────────────────────┤
│ C-____   Date __/__/__   Time ____:____                │
│ t_conf ________ min from end of operation              │
│ Grade    1°    2°    3°          (Chapter 5.6)         │
│ First confirmation for this operation?    Y / N        │
│ What happened ________________________________________ │
│ ______________________________________________________ │
│ Could this be coincidence?    Y / N / unsure           │
│ Recorded within ______ min of noticing it              │
└────────────────────────────────────────────────────────┘
```

Rules, in the order they get broken:

1. **Only the first confirmation enters St. John's Equation.** `t_conf` runs from
   the end of the operation to the first confirmation, in minutes. Later ones
   stay on the sheet as `^4` Vibration evidence; they do not re-enter the ratio.
2. **Grade at the time, not afterwards.** A 3° confirmation graded a week later,
   once the outcome is known, grades 1°.
3. **The coincidence line is not humility, it is data.** Write what you actually
   thought at the moment. An operator whose logs never contain the word "unsure"
   has stopped logging and started narrating.
4. **A confirmation is not a manifestation.** It says the signal reached the
   Ether, not that it reached the target (Chapter 5.6).

**Worked example — one block filled.**

```
│ C-001   Date 03/14/26   Time 21:40                     │
│ t_conf 60 min from end of operation                    │
│ Grade    1°   (2°)   3°          (Chapter 5.6)         │
│ First confirmation for this operation?   (Y) / N       │
│ What happened  the song came on the radio, unbidden,   │
│ in the car, forty minutes into an errand               │
│ Could this be coincidence?   Y / N / (unsure)          │
│ Recorded within 15 min of noticing it                  │
```

η = 20 / 60 = 1/3; × 1/3 = 1/9; a = 1, b = 9. Carry that arithmetic onto Form 1
so the result and its inputs can never be separated later.

---

### I.5 Form 3 — Parameter-Change Log

The form that earns its page. An operator who moves two parameters and gets a
better reading has bought a better reading and learned nothing.

```
┌────────────────────────────────────────────────────────┐
│ PARAMETER-CHANGE LOG        Op # ______   sheet ____   │
├────────────────────────────────────────────────────────┤
│ CH-____  Date __/__/__  Takes effect at session ____   │
│ Parameter ___________________  from ______ to ______   │
│ Why (one line) _______________________________________ │
│ Prediction: TP____ moves   up / down / off ceiling     │
│    to about ______ by session ______                   │
│ Anything else changed this cycle?    No / Yes >>       │
│    >> if Yes, write CONFOUNDED here _______________    │
│ Observed ______ at session ______ on __/__/__          │
│ Verdict     KEEP  /  REVERT  /  INCONCLUSIVE           │
├────────────────────────────────────────────────────────┤
│ CH-____  Date __/__/__  Takes effect at session ____   │
│ Parameter ___________________  from ______ to ______   │
│ Why (one line) _______________________________________ │
│ Prediction: TP____ moves   up / down / off ceiling     │
│    to about ______ by session ______                   │
│ Anything else changed this cycle?    No / Yes >>       │
│    >> if Yes, write CONFOUNDED here _______________    │
│ Observed ______ at session ______ on __/__/__          │
│ Verdict     KEEP  /  REVERT  /  INCONCLUSIVE           │
└────────────────────────────────────────────────────────┘
```

**The six rules.**

1. **One parameter per block.** Change two and the block is written off: mark it
   CONFOUNDED and claim nothing from it, including the parts you liked.
2. **Prediction before the operation, never after.** A named test point and a
   direction — *TP3 comes off the ceiling* — is a prediction. *It should improve
   things* is not.
3. **Verdict only after a full cycle**: one operation and its first confirmation.
   Anything sooner is a guess wearing a verdict's clothes.
4. **A revert is a change.** It gets its own block and its own prediction.
5. **Never overwrite a prediction that turned out wrong.** Strike it, initial it,
   leave both readable. Wrong predictions are how you learn the board.
6. **Your own condition is a parameter you did not set.** Sleep, illness,
   upheaval at work — these move the bias rail whether or not you consent. Note
   them; do not call a cycle clean when it was not.

**Worked example — one block filled.** The second operation of Chapter 13.6:

```
│ CH-002  Date 03/21/26  Takes effect at session 01      │
│ Parameter  Q2 beta            from  3.0  to  2.50      │
│ Why  TP3 pinned at sat=0.80; the reading is the clamp, │
│      not the board                                     │
│ Prediction: TP3 moves   up / down / (off ceiling)      │
│    to about 0.76 by session 01                         │
│ Anything else changed this cycle?   (No) / Yes >>      │
│ Observed 0.76 at session 01 on 03/21/26                │
│ Verdict    (KEEP)  /  REVERT  /  INCONCLUSIVE          │
```

That block is readable because nothing else moved. Contrast the third operation
in the same chapter, which moved four levers at once — clarity at TP1, both
dials, β, and the `R_op` terms — and delivered 3.10× at TP4. The log cannot
apportion that gain. The chapter apportions it arithmetically, decomposing the
product into its factors, and that works only because each factor is separately
computable. Where the arithmetic will not decompose, a four-lever change hands
you a number and no account of where it came from.

---

### I.6 Filling conventions

| Mark | Meaning |
|---|---|
| Blank cell | Not measured |
| `—` | Measured, and the reading was zero |
| `!` after a reading | Pinned or clamped; suspect everything downstream |
| `?` after a reading | Taken, but not trusted |
| Struck through, initialled | Corrected; both values stay readable |
| `CONFOUNDED` | Two or more changes in one cycle; nothing may be concluded |

---

### I.7 What the logs feed

- **Chapter 22.5**, trend reading, needs at least three operations at comparable
  settings before a movement in η means anything. Form 3 is the only record of
  which operations were comparable.
- **Chapter 24**'s safety review is read straight off these sheets. The question
  that matters most — any blown fuses, and why — is answerable only if the why
  was written down at the time it blew (Chapter 24.3).
- **Chapter 24.5**'s ethical-drift filter takes the operations log as its literal
  input: `Filter< input=^9_operations_log^O, type=lowpass, τ=ethical_drift_τ >`.
  The sheet is not paperwork about the circuit. It is the node the one lawful
  feedback path reads from, and an operator who keeps no sheet has left an input
  on their safety board unconnected.

Keep the sheets until one full ethical-drift τ has elapsed past the last entry
(Chapter 24.5). Then keep them anyway. The operator you will argue with in two
years is yourself, and these pages are the only witness either of you will have.
