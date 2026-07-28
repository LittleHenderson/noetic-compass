# CHAPTER 22
## The Quantitative Table — Measuring Your Operations
*Three readings, one honest scale, and the exact limit of what a trend across them is allowed to mean*

An operator hands you a notebook. Forty operations, eighteen months, every page in the same green ink. Every `^1` Mind reading is 1° or 2°. Every confirmation is graded 1°. There is not one NO-READ row in it, not one struck-through line, not one entry marked CONFOUNDED.

You have not been handed a log. You have been handed a diary, and its author cannot tell the difference — which is the problem, because a diary and a log look identical on the page and answer different questions. The diary answers *what was that like*. The log answers *did the thing I changed on the fourteenth do anything by the twenty-first*, and it can only answer that if it contains rows the author did not enjoy writing.

Chapter 5.5 named the three readings that can be taken at a bench with nothing but a wristwatch and an honest answer: `^1` Mind, `^4` Vibration, `^7` Rhythm. Chapter 5.6 put them on a board. This chapter builds the instrument that takes them, states what each number is worth, and — the part that matters most — states plainly what none of them is.

**They are structured self-report on a scale defined in this book.** They are useful for comparing one operator against their own earlier readings under known conditions. They have not been validated against any external criterion, there is no published norm to place you on, and nothing in this chapter licenses a comparison between two operators or a claim about anyone's mind but your own. The scale is a ruler you cut yourself. It measures change on your own bench and nothing beyond it, and that is worth having as long as you never claim more.

---

### Requirements and Safety Invariants

Chapter 12.2 requires the "must not" list before the functional one.

| # | Functional requirement | Realized by |
|---|---|---|
| R1 | Take three readings per operation on fixed, pre-declared scales | Gnosis sampler, rhythm clock, vibration grader |
| R2 | Capture each reading before hindsight can reach it | Two latency holds (§22.1, §22.2) |
| R3 | Admit exactly one confirmation per operation | First-only limiter (§22.2) |
| R4 | Emit NO-READ rather than a fabricated row | Horizon fuse → MUX |
| R5 | Refuse to trend across non-comparable operations | Confound gate, three-row filter |

| # | Safety invariant (MUST NOT) | Enforcement |
|---|---|---|
| S1 | Present a reading as externally validated, or compare two operators | Scope fuse, `action=permanent_block` |
| S2 | Revise a grade after the outcome is known | Write-once fuse on the row |
| S3 | Admit a later, better confirmation into the ratio | `Limiter< max=1.0 >` on arrivals |
| S4 | Compute a trend across a cycle with two changes in it | `CONFOUNDED` exit on the confound gate |
| S5 | Let the log ascend a domain — readings are `^C`, the row is `^O` | Descent diode; feedback only via Chapter 24.5 |
| S6 | Substitute this instrument for clinical judgment | Stated in §22.5; no component can enforce it |

S6 has no component behind it and never will. If your readings are tracking something that frightens you — sleep going, mood going, the practice becoming the only thing that holds — that is a matter for a clinician, and this book has nothing to offer it. Nothing here replaces care. Close the log and make the appointment.

[[FIGURE 22-A: Block diagram — CCB-QT left to right. GNOSIS SAMPLER (2-min hold, three bins) and RHYTHM CLOCK (declared boundary, three bins) feed a ROW ASSEMBLER from above; CONFIRMATION INTAKE (^8 arrival → ^9 recall) → FIRST-ONLY LIMITER → HORIZON FUSE (downward branch to a NO-READ terminal) → VIBRATION GRADER (30-min hold, three bins) feeds it from below. ROW ASSEMBLER → CONFOUND GATE (side exit marked CONFOUNDED) → WRITE-ONCE LATCH → descent diode → LOG ROW. A three-row trend filter hangs beneath the latch with an ABORT-REVIEW monitor on its output. TP1–TP4 flags at the gnosis hold, the clock output, the limiter, and the trend filter.]]

---

### 22.1 `^1` Mind Measurement — The 3 Degrees of Gnosis

`^1` Mind is *various degrees of awareness that processes, stores, outputs, and intakes Ideas*. At the bench you are reading one thing only: how much of that awareness stayed on the formed Idea, and how much went elsewhere.

| Degree | Behavioural description | State |
|---|---|---|
| **1°** | Complete absorption; the Idea is the only content present | `^1^C_{F2}\|T` |
| **2°** | Wanders and returns; intermittently clear | `^1^C_{F2}\|A` |
| **3°** | Frequent wandering; the image will not hold | `^1^C_{F2}\|A` |

Grade against the middle column, not against how the operation felt. "It felt powerful" is not on the scale. *Did the image hold, and did it return* is.

The register carries real information here and is not decoration. At 1° the awareness is not tracking itself — purpose-oriented, integrative, `|T`. At 2° and 3° it is checking the clock and narrating, which is `|A`. The Noetic never changes: it is `^1` Mind at all three degrees. Only the operational character changes, exactly as Chapter 2.5 defines register.

Now the honest part. This reading is taken by the same awareness whose depth is being reported, and no logbook design fixes that. An operator absorbed at 1° was by definition not monitoring their absorption; an operator who can describe their absorption in detail has told you it was 2°. Three defences exist and all three are procedural:

1. **Grade within two minutes of the operation ending, before any other line on the sheet is written.** The hold is set at two minutes because that is roughly how long a fresh impression survives before it starts being reconstructed into a story. At thirty minutes you are grading a memory of an impression.
2. **Grade against behaviour, never against feeling.**
3. **Never decide on `^1` alone.** It is the noisiest of the three columns. It earns its place by moving *with* `^4` Vibration across many rows, and a co-movement across ten rows is much harder for hindsight to manufacture than a single grade.

> **Bench Note — a 3° operation is a measurement of the operator, not of the board.** Chapter 5's TP2 is blunt about this: at 3°, do not compute `A`. The reading is admissible as a row — log it — but it is not admissible as evidence about the circuit, because the circuit was never properly driven. Operators hate this rule, because a 3° operation still cost them twenty minutes and they want a number for it. The number they would get would be a number about their sleep, their week, and the room. Fix the operating conditions and re-run. The row you strike is worth more than the number you would have kept.

---

### 22.2 `^4` Vibration Measurement — Confirmation Speed and Intensity

`^4` Vibration is *the degree to which an Idea resonates with the Mind, its impression*. A confirmation is the `^8` → `^9` pair of Chapter 5.6 and nothing more exotic: an event arrives and triggers a *different* Idea — the desire — into Mind. Associative surfacing. Not inference, not evidence, not a message.

Two quantities come off it, and they are different in kind.

**Speed** is `t_conf`, clocked from the *end* of the operation to the first confirmation, in minutes. It is a wristwatch reading and it is the one that enters St. John's Equation.

**Intensity** is the graded impression. The bins are 30 minutes and 2 hours, and both edges are design choices with stated failures. The 1° bin is kept short so that it sits well inside any plausible base rate — push it out to two hours and every operator grades every operation 1° and the column stops discriminating. The 3° bin is kept wide so a genuinely slow circuit still registers as something rather than nothing.

| Degree | Delay | Impression |
|---|---|---|
| **1°** | < 30 min | startling, undeniable; demands attention |
| **2°** | 30 min – 2 h | clear, but you can talk yourself out of it |
| **3°** | > 2 h | subtle, ambiguous; "was that a confirmation?" |

Three rules govern the column, listed in the order operators break them.

**Only the first confirmation enters the ratio.** Later ones stay on the sheet as `^4` evidence and never re-enter. An operator who admits a stronger confirmation that arrived four hours later has improved their number by choosing their data, and the improvement is entirely artefact. The instrument enforces this with a limiter that admits one arrival and drops the rest.

**Grade within thirty minutes of noticing, in ink, and never revise.** A 3° confirmation graded a week later, once the desire has actually manifested, grades 1° every time. This is not dishonesty. It is ordinary hindsight, it is unavoidable once the outcome is known, and the only defence against it is a clock.

**A confirmation is not a manifestation.** It says the signal reached the Ether. It says nothing about whether the signal reached the target with enough amplitude to clear `R_constraint` — Chapter 13's delivered-current band, where confirmations arrive reliably and nothing else does. Reading confirmations as arrivals is the error that costs more than all the others combined.

Beyond the horizon — `t_H = 3 × median(t_conf over the last ten operations)`, floored at 24 hours (§23.1) — there is no reading at all. The entry is **NO-READ**, and NO-READ is a result: it is the row that tells you whether your confirmation rate exceeds your own base rate.

---

### 22.3 `^7` Rhythm Measurement — Clocking the Operation

`^7` Rhythm is *the rate and pattern a Mind is exposed to an Idea, entraining it*. At the bench it reads as one number: `t_op`, the duration of the operation, start to finish, off a wristwatch. The state is `^7^C_{F6}|E` — Structure, embodied register, because it is a clocked bodily act and reads as one.

| Degree | Duration | Why this edge |
|---|---|---|
| **1°** | > 30 min | Full establishment |
| **2°** | 10 – 30 min | The working band |
| **3°** | < 10 min | Below ten minutes gnosis has not had time to establish |

The 10- and 30-minute edges sit at the two places operators actually break. Below ten, `^1` Mind almost never reaches 2°. Above thirty, `^1` Mind almost always falls — the operator tires and the image goes. Widen the bins and you merge a failed operation with a held one, which is the one thing the column exists to prevent.

The whole column depends on a convention that costs nothing to set and everything to skip. `t_op` has two defensible start points: the moment you begin the procedure, and the moment concentration actually establishes. For most operators they differ by five to ten minutes. **Either is fine. Mixing them across a log makes every comparison in it a comparison between two different measurements**, which is to say worthless. Write your convention on page one in ink before the first entry, and do not revise it because a later operation would read better under the other one. The instrument holds the convention in a write-once latch for exactly this reason.

---

### 22.4 The Table Sheet — Tracking Across Multiple Operations

One row per operation, every operation, including the ones that did not read. The printable forms are Appendix G — Form 1 the operation log, Form 2 the confirmation log, Form 3 the parameter-change log — and Form 3 governs the other two.

Eight fields carry the chapter: `Op #`, `t_op`, `t_conf`, `^1`, `^4`, `^7`, a flag column, and `A = 3 t_conf / t_op` from Chapter 13.5.

The three degrees also give a bookkeeping figure worth writing down. Define the **coupling sum** `S = m + v`, where `m` is the `^1` degree and `v` the `^4` degree, each 1 to 3. `S` runs 2 to 6, and lower is stronger. It is a sum and not a product, and the reason is not aesthetic: these are **ordinal bins**. 1°, 2° and 3° state an order and nothing else — the gap between 1° and 2° is not claimed equal to the gap between 2° and 3°, and multiplying ordinals asserts a ratio scale the bins do not have. A sum is already generous. Treat `S` as a bookkeeping index for ordering rows in one log, never as a magnitude.

> **Bench Note — the notation says the same thing the arithmetic does.** The three readings are `^1^C_{F2}|A + ^4^C_{F2}|f + ^7^C_{F6}|E` — the `+` of co-presence (Chapter 2.6). Three distinct measurements, present together, remaining distinct. It is emphatically **not** `×`. A `×` would assert that the three fuse into a single emergent state, and under v7.7 discipline that requires a named emergent result, which this book does not define. There is no "operation quality" state in the topos and `S` is not one. That is why `S` is a bookkeeping sum rather than a state literal, and why it never appears in a CCDL listing. The operator discipline and the measurement discipline are the same discipline here, which is a good sign that both are right.

Three flags do most of the work. **NO-READ**: no confirmation inside the horizon; `^1` and `^7` still logged, `^4` absent, `S` not computed. **CONFOUNDED**: two or more things changed in the cycle, including things you did not choose — illness, upheaval, a week of bad sleep. Nothing may be concluded from a confounded row, *including the parts you liked*. **Struck**: a corrected value, struck through and initialled, both readable. The crossed-out number is often the interesting one.

---

### 22.5 Interpreting Trends — When to Adjust, When to Abort

A single row diagnoses nothing. **Three comparable rows are the minimum**, where comparable means: same board, same declared conventions, one parameter changed at most between any two of them, and no CONFOUNDED flag in the sequence. Three is a design choice — it is the fewest rows in which a direction can be distinguished from a pair of readings, and one bad clock cannot redirect a campaign that needs three rows to turn. Two rows is a line through two points, which is not a trend; it is arithmetic.

Read two things down the column, in this order.

**`A` first**, because it is smooth in the clocks. `A = 3 t_conf / t_op` moves continuously with a timing error, where the reduced denominator `b` swings wildly (Chapter 13.5). The step ratio is `ρ = A_next / A_current` (§23.2). Falling `A` with `ρ ≤ 0.6` is a converging campaign. Flat `A` across three comparable rows means nothing you are changing is reaching the delivered current.

**`S` second**, as a cross-check. When `A` and `S` move together, the reading is coherent. When they disagree, the disagreement is itself the finding, and there are exactly two informative cases:

| Pattern | Reading | Action |
|---|---|---|
| `A` falls, `S` flat | The bins are coarser than the ratio; real change inside one bin | Trust `A`. Record `S`. Continue |
| `A` flat, `S` falls | Operating conditions improved; the circuit did not | Stop tuning the board. `R_op` is the problem |
| Both fall | Converging | Continue; one lever at a time |
| Both rise for two consecutive comparable rows | Diverging | **Abort.** Return to A0 (Chapter 21.1) |
| `A` flat, `S` rises | The operator is degrading while the board holds | Rest. Re-read §22.1's bench note |

**When to adjust.** One lever, one cycle, with a prediction written before the operation: a named test point and a direction. *TP3 comes off the ceiling* is a prediction. *It should improve things* is not. Verdict only after one operation and its first confirmation.

**When to abort.** Three conditions, any one sufficient. Both columns rising across two consecutive comparable rows. `A` flat across three comparable rows while `ρ` sits near 1.0 — this signal arrives *before* `A` reaches the re-spec boundary of 9, which is the whole point of watching a trend rather than a row. Or `^1` Mind falling to 3° for three consecutive operations at constant `t_op`, which is not a circuit reading at all: it says the operator cannot currently run the board, and the response is rest and a decomposition (§23.3), not a fourth attempt.

And the condition that is not on any table: if the log itself has become the thing that is not right — if you are casting to make the readings move, or the readings are the only evidence your week produced — stop and speak to a clinician. That is not a failure of the instrument. It is outside what any instrument in this book is for.

---

### Full CCDL Listing — CCB-QT

```cas
board ccb_qt {                            // CCB-QT — the acquisition bench
    input:  operation;                    // the operation as run
    output: log_row;                      // one admissible row, or NO-READ

    node practice_rail: ^5^P_{F7}|T;      // Female: accumulated practice — bias only

    // ---- S1  GNOSIS SAMPLER ----
    node gnosis: ^1^C_{F2}|A;             // Mind: awareness on the formed Idea
    hold h_mind: Hold< signal=gnosis, duration=2.0 >;          // min, before hindsight
    monitor m_mind: Monitor< signal=h_mind, limit=[1.0, 2.0],
                             action_on_violation=NO_COMPUTE >; // 3° -> no A

    // ---- S2  RHYTHM CLOCK ----
    node clocked_op: ^7^C_{F6}|E;         // Rhythm: the operation, start to finish
    fuse f_conv: Fuse< path=clocked_op, threshold=1.0,
                       action=permanent_block >;               // convention write-once

    // ---- S3  CONFIRMATION INTAKE ----
    node arrival:  ^8^C_{F2}|E;           // Above/Cause: the event that arrives
    node recalled: ^9^C_{F2}|A;           // Below/Effect: the desire brought back
    limiter l_first: Limiter< signal=arrival, max=1.0 >;       // first only
    fuse f_horizon: Fuse< path=recalled, threshold=1440.0,
                          action=no_read >;                    // 24 h floor

    // ---- S4  VIBRATION GRADER ----
    node impression: ^4^C_{F2}|f;         // Vibration: the impression it made
    hold h_vib: Hold< signal=impression, duration=30.0 >;      // min from noticing

    // ---- S5  ROW ASSEMBLER ----
    node row:     ^6^E_{F6}|A;            // Male: the readings composed into a row
    node no_read: ^0^O_{F6}|A;            // Idea: the logged absence of a reading
    mux out: MUX< inputs=[ row, no_read ], select=f_horizon >;

    // ---- S6  CONFOUND GATE and WRITE-ONCE ----
    node changes: ^6^O_{F6}|A;            // Male: what was altered this cycle
    monitor m_confound: Monitor< signal=changes, threshold=1.0,
                                 action_on_violation=CONFOUNDED >;
    fuse f_write: Fuse< path=out, threshold=1.0, action=permanent_block >;
    fuse f_scope: Fuse< path=out, threshold=1.0, action=permanent_block >;  // S1

    // ---- S7  TREND and DESCENT ----
    filter f_trend: Filter< in=out, out=trend, type=lowpass, tau=3.0 >;     // ops
    monitor m_abort: Monitor< signal=trend, threshold=0.6,
                              action_on_violation=ABORT_REVIEW >;
    diode d_out: Diode< ^E -> ^O >;       // the row descends into the ledger

    probe tp1: h_mind;        probe tp2: clocked_op;
    probe tp3: l_first;       probe tp4: f_trend;
}
```

[[FIGURE 22-B: Full schematic with reference designators. Upper rail: gnosis node into H1 (Hold, 2.0) into M1 (Monitor, NO_COMPUTE exit drawn as a downward stub). Second rail: clocked_op into F1 (write-once convention fuse). Lower rail: arrival into L1 (Limiter, max 1.0) into F2 (horizon fuse, downward NO-READ branch) into H2 (Hold, 30.0). All three rails converge on the row assembler and MUX1, whose select line is drawn from F2. MUX1 into M2 (confound gate, side exit CONFOUNDED), into F3 (write-once) with F4 (scope fuse) tapped in parallel and labelled "S1 — self-report only". F3 into FLT1 (lowpass, tau = 3 ops) with M3 (abort monitor) on its output, and into D1 (E to O diode) to the log_row terminal. TP1–TP4 flags at H1, clocked_op, L1, FLT1.]]

**S1 — Gnosis sampler.** `Hold` captures the grade and freezes it; `duration=2.0` is the two-minute latency of §22.1. `m_mind` is the enforcement of Chapter 5's TP2: a 3° reading exits `NO_COMPUTE`, which logs the row and withholds `A`.

**S2 — Rhythm clock.** The convention fuse is a genuine `Fuse` with a finite threshold and `action=permanent_block`, not an infinite-gain comparator. It is tempting to write `β=∞` on any latch that must never yield; that is an idealization a validator rejects, exactly as Chapter 24 notes on the CSB's red path, and here there is no need for it — a fuse latches by construction.

**S3 — Confirmation intake.** `^8` triggers, `^9` surfaces; both are modelled at `^C` so that no unlawful `^O → ^C` ascent enters the listing (§23.1 does the same). The limiter is S3 in hardware: one arrival admitted, the rest logged as evidence and dropped from the ratio. The horizon fuse carries the 24-hour floor as a literal; a running bench recomputes 3× the rolling median and holds the floor underneath.

**S4–S5.** The grader's thirty-minute hold is the anti-hindsight latch. The MUX selects on the horizon fuse: intact routes the assembled row, blown routes the `no_read` terminal, which is a declared node rather than a dangling name — an absence you can probe is worth more than an absence you infer. The row itself is `^6` Male, the readings decomposed and composed into a structure. It is not `^3` and not `^8`: assembling a row is compositional work, not aversion and not associative triggering.

**S6–S7.** The confound gate permits one change per cycle; two exits `CONFOUNDED`. The scope fuse is the only component here with no signal-processing function: it exists so that S1 has an enforcement column, and it blows the moment a row is used to support a claim about anyone but this operator. The trend filter's `tau=3.0` is three operations, the minimum from §22.5; the abort monitor watches `ρ` against 0.6. `d_out` is the lawful descent, and the only path back up is Chapter 24.5's ethical-drift filter, which takes this log as its literal input.

---

### Parameter and BOM Table

Every value is a design choice made in this book. None is a measurement.

| Ref | Component | Setting | Why | Failure at other values |
|---|---|---|---|---|
| H1 | Hold, `^1` grade | 2 min | Roughly how long a fresh impression survives | 30 min: the grade is a reconstruction, and reconstructions trend upward |
| M1 | Gnosis monitor | admit 1°–2° | Chapter 5's TP2: 3° measures the operator | Admitted: operator noise enters the circuit record as circuit data |
| — | `^1` bins | behavioural | Held / returned / would not hold | Feeling-based: every operation grades 1° after a good week |
| F1 | Convention fuse | write-once | `t_op` boundaries must match across the log | Revisable: every comparison is between two different measurements |
| — | `^7` bins | 10 / 30 min | The two points operators break | Wider: a failed operation and a held one land in one bin |
| L1 | First-only limiter | max = 1 | The ratio needs one arrival, not the best one | Best-of: `A` improves with nothing changed |
| F2 | Horizon fuse | 3 × median, floor 24 h | Passes slow circuits, excludes base rate | Short: live circuits declared dead. Long: everything "confirms" |
| H2 | Hold, `^4` grade | 30 min from noticing | Before hindsight reaches the grade | Later: no operation is ever graded 3° again |
| — | `^4` bins | 30 min / 2 h | 1° bin inside plausible base rate | 1° edge at 2 h: the column stops discriminating |
| M2 | Confound gate | 1 change / cycle | Attribution needs a single lever | 2 changes: a better number, bought, with no account of what bought it |
| F3 | Write-once latch | `permanent_block` | Grades must not move after the outcome | Revisable: the log becomes a record of the outcome, not of the operations |
| F4 | Scope fuse | `permanent_block` | Invariant S1 | Absent: a self-report scale gets quoted as a finding |
| FLT1 | Trend filter | τ = 3 operations | Fewest rows that can show a direction | 1 op: one bad clock redirects a campaign. 10: the abort arrives too late |
| M3 | Abort monitor | `ρ` ≤ 0.6 | Reaches DRIVE in one step from 9 (§23.2) | 1.0: divergence reads as steady |
| — | `S` | ordinal sum, 2–6 | Bins are ordinal; a product asserts a ratio scale | Multiplied or averaged: a coarse index quoted to two decimals |

[[FIGURE 22-C: Assembly drawing — CCB-QT board outline with the three intake rails entering the left edge stacked vertically (gnosis, clock, confirmation), converging at MUX1 mid-board, then M2, F3/F4, FLT1 with M3, and D1 at the right edge to log_row. The practice rail drawn as a thick trace along the lower edge. Circled test-point callouts TP1–TP4 on leader lines with expected readings beside each (TP1 1° or 2°, latency < 2 min; TP2 boundary matches page one; TP3 exactly one arrival admitted; TP4 ρ ≤ 0.6). Boxed BOM at lower right listing H1, M1, F1, L1, F2, H2, M2, F3, F4, FLT1, M3, D1 with settings. Corner panel reproducing the three degree ladders side by side.]]

---

### Worked Example — Campaign Q-3

Self-directed board (CCB-SELF), one desire, six operations across nineteen days. Convention declared on page one: `t_op` starts when the operator sits down and begins the procedure. Clocks logged raw; `A` computed on the 5-minute grid of §23.1.

| Op | `t_op` | `t_conf` | `^1` | `^4` | `^7` | `S` | `A` | Flag |
|---|---|---|---|---|---|---|---|---|
| 1 | 15 | 150 | 3° | 3° | 2° | 6 | — | `NO_COMPUTE` |
| 2 | 25 | 100 | 2° | 2° | 2° | 4 | 12.0 | — |
| 3 | 25 | 60 | 2° | 2° | 2° | 4 | 7.2 | — |
| 4 | 25 | — | 2° | — | 2° | — | — | NO-READ |
| 5 | 30 | 45 | 1° | 2° | 2° | 3 | 4.5 | `CONFOUNDED` |
| 6 | 30 | 40 | 1° | 2° | 2° | 3 | 4.0 | — |

**Operation 1.** `^1` = 3°, so M1 exits `NO_COMPUTE` and no `A` is written — correctly, because at fifteen minutes the gnosis never established. The row is logged in full. One change follows, CH-001: `t_op` 15 → 25 min, prediction *TP1 moves to 2° by operation 2*.

**Operation 2.** `A = 3 × 100 / 25 = 12.0` — RE-SPEC band (§13.5). `S` = 4. CH-001 verdict: KEEP, prediction met.

**Operation 3.** `A = 3 × 60 / 25 = 7.2` — DRIVE. `ρ = 7.2 / 12.0 = 0.60`, exactly at the abort monitor's limit and on the right side of it. Note that `S` did not move: 4 both times. This is the coarse-bins case from §22.5 — a 40% fall in `A` happened entirely inside the 2°/2° cell. Trust `A`, record `S`.

**Operation 4.** Horizon: `3 × median(150, 100, 60) = 300` min, but the 24-hour floor governs at this point in the log, so `t_H = 1440`. Nothing arrives. **NO-READ**, `^1` and `^7` logged, `^4` absent, `S` not computed. This is the row that tells the operator their confirmation rate is not simply their base rate.

**Operation 5.** `t_op` raised to 30 *and* the symbol changed, on a week of bad sleep. `S` = 3 and `A` = 4.5 — the best reading in the log, and worthless. M2 exits `CONFOUNDED`; nothing may be concluded, including the parts the operator liked.

**Operation 6.** One change only, CH-003: revert the symbol, hold `t_op` at 30. `A = 3 × 40 / 30 = 4.0`, `S` = 3, `ρ = 4.0 / 7.2 = 0.56` against the comparable predecessor. Converging.

**The readout.** Comparable rows are 2, 3 and 6 — three, the minimum. `A` runs 12.0 → 7.2 → 4.0 with `ρ` = 0.60 and 0.56, both inside 0.6. `S` runs 4 → 4 → 3. Both columns fall, they do not disagree, and the campaign continues with one lever at a time. **Six operations, three usable rows.** That ratio is not a sign of a bad log. It is what an honest one looks like, and the notebook in the cold open — forty rows, forty usable — is the one to distrust.

[[FIGURE 22-D: Two-panel trend chart for campaign Q-3. Upper panel: A against operation number, points at 12.0, 7.2, 4.0 for ops 2, 3, 6 joined by a line, with ops 1, 4, 5 shown as open markers on a "not comparable" baseline and labelled NO_COMPUTE, NO-READ, CONFOUNDED. Horizontal band shading behind the axis labelled ACT / CLOSE / DRIVE / RE-SPEC at A = 1, 3, 9. Lower panel, sharing the axis: S plotted 4, 4, 3 as a step line on an inverted ordinal axis 6 at the bottom to 2 at the top, with the flat 4→4 segment annotated "40% change in A, none in S — the bins are coarser than the ratio".]]

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `h_mind` | `^1` degree and its capture latency | 1° or 2°, captured under 2 min. A 3° reading is admissible as a row and inadmissible as evidence — do not compute `A` |
| **TP2** | `clocked_op` | `t_op` against the boundary written on page one | Same rule as every prior entry. A different rule makes the row incomparable, not merely different |
| **TP3** | `l_first` | Arrivals admitted | Exactly one, inside the horizon, graded within 30 min. Two admitted means the ratio has been chosen rather than measured |
| **TP4** | `f_trend` | `ρ` across three comparable rows | ≤ 0.6 per step. Flat near 1.0 across three rows is the abort signal, and it arrives before `A` reaches 9 |

Read them in order. TP1 and TP2 decide whether the row is admissible at all; TP3 decides whether there is a `^4` reading; TP4 is the only one that speaks about the campaign. Three of the four can send you home without a number, and that ratio is deliberate.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Retrospective grading** | Grades written after the outcome is known | No operation in the log was ever graded 3° | H1 and H2 latencies; ink; never revise |
| **Best-of admission** | A later, stronger confirmation entered | `A` improving while nothing about the operation changed | L1 at `max=1`; Form 2's first-confirmation field |
| **Boundary drift** | `t_op` start defined differently across entries | Two operations that felt identical reading five minutes apart | F1 write-once; the convention on page one |
| **Window creep** | Horizon widened until something lands | Every operation confirms; no NO-READ rows anywhere | Fix `t_H` before the cast; run a one-week control count |
| **Multi-lever cycle** | Two or more changes between readings | A better number with no account of which change bought it | M2 `CONFOUNDED`; claim nothing from the row |
| **Ordinal inflation** | `S` averaged, multiplied, or quoted to decimals | "Mean coupling 3.67 this month" | `S` orders rows in one log; it has no magnitude |
| **Scale export** | Readings compared between operators, or quoted as a finding | A degree used as evidence about someone else's mind | F4 scope fuse; invariant S1 |
| **Instrument substitution** | The log used to track distress | Readings watched more closely than sleep | §22.5. See a clinician; nothing here replaces care |

The last two fail silently. Every other row on this table announces itself in the log; those two look like diligence.

---

### What This Chapter Established

- **These are structured self-reports on a scale defined in this book, not validated instruments.** They order one operator's rows against each other under known conditions. They carry no external norm, do not compare two operators, and are evidence about no mind but the operator's own.
- **Three of ten Noetics take a bench reading without instrumentation** — `^1` Mind, `^4` Vibration, `^7` Rhythm. That is a fact about instrumentation, not about the topos: all 40 states carry an activation in principle (Appendix L), but these three answer *how much* without hardware.
- **Register carries information in the `^1` column.** The same `^1^C_{F2}` reads `|T` at 1° and `|A` at 2° and 3°. The Noetic never changes; the operational character does.
- **The three readings are `+`, not `×`.** Co-presence of three distinct measurements, no named emergent result, therefore no licensed fusion. `S` is a bookkeeping sum of ordinals, not a state, and never appears in a listing.
- **Hindsight is defeated by clocks, not by resolve.** Two minutes for `^1`, thirty from noticing for `^4`, ink, no revision. Every other defence has been tried by every operator who ever kept a log.
- **NO-READ and CONFOUNDED are results.** A log with neither has a window too wide or a discipline too loose, and is measuring the operator's patience.
- **Three comparable rows is the floor for a trend**, and comparable is a technical word: same board, same conventions, one lever, no confound flag.
- **`A` leads and `S` cross-checks.** When they disagree the disagreement is the finding — coarse bins when `A` moves alone, degrading operating conditions when `S` moves alone.
- **The abort signal arrives at the trend, not the row.** Flat `ρ` near 1.0 across three rows fires before `A` reaches the re-spec boundary of 9, which is the entire reason for watching a column instead of a number.

---

### Exercises

**22.1** An operation logs `t_op = 20`, `t_conf = 75`, `^1` = 2°, `^4` = 2°. Compute `^7`'s degree, `S`, and `A`. Which band? State which single figure you would act on and which you would only record.

**22.2** An operator's last six rows read `S` = 4, 4, 3, 3, 3, 3 and `A` = 9.0, 8.7, 9.1, 8.9, 9.0, 8.8. The only thing changed between rows was the amplifier β, raised each time. Diagnose using §22.5's table, name the failure mode, and state the first measurement you would demand.

**22.3** A colleague grades a confirmation 1° "because it was unmistakable" — six hours after the operation, and graded the following morning once the desire had manifested. Identify three separate rule violations, state which component of CCB-QT catches each, and give the grade the entry should have carried.

**22.4** Op 4 of campaign Q-3 is a NO-READ. Write the argument that the row should be deleted from the log, then rebut it in three sentences using §22.2 and the base-rate reasoning behind the horizon.

**22.5** `S` is defined as `m + v`. A reader proposes `S' = m × v` on the grounds that it "separates the good rows better." Give the measurement-theory objection in one sentence, then give the CAS notation objection in one sentence, and state which of the two you would put in a design review first and why.

**22.6 (Build)** Add a stage to CCB-QT that flags a row whose confirmation could be claimed by a second live operation — the attribution collision of §23.1. Write the CCDL fragment, name the component type, state where it sits in the signal path, and state what it must *not* do to the row it flags.

**22.7 (Marquee)** The scope fuse F4 has no signal-processing function; it enforces an invariant no measurement can check. Argue either that it belongs on the board or that it is decoration. If you argue it belongs, state what physical event blows it. If you argue it is decoration, name the mechanism that would enforce S1 instead, and say honestly whether that mechanism is a circuit or a person.

*(Answers in **Appendix H**, worked in full. Every parameter in this chapter is a design choice with a stated failure at other values; the scales are conventions defined in this book, not measurements of anything outside it.)*
