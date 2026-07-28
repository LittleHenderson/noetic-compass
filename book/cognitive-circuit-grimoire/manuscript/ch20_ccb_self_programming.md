# CHAPTER 20
## CCB-SELF — The Self-Programming Board
*The only board with no target port — and the one fault that makes it fail anyway*

Tie a transistor's base to its emitter and the device turns off.

Not "runs weakly." Off. The junction needs a forward voltage across it before any current crosses, and a wire between the two terminals guarantees there is none. Raise the collector supply as far as you like. Nothing moves. The part is undamaged, correctly specified, and completely inert — because the terminal that was supposed to hold a *reference* has been shorted to the terminal that carries the *result*.

You have watched a person do this. On a Sunday evening, in a genuinely clear moment, someone decides that from now on they are a person who practises every morning. They mean it. Nine days later it is gone, and the conclusion they draw is that they did not want it enough — that the fault was in the drive rail.

The drive rail was fine. They shorted the bias to the effect. The reference against which the new composition was to be measured *was the composition being built*, so the moment performance dipped the reference dipped with it, the junction unbiased itself, and the stage went to cutoff. That is not a metaphor about willpower. It is the topology of the circuit they built, and it is the most common fault on this board.

CCB-SELF is the closed-loop board: operator and target are the same `^5`. That gives it the one property no other board here has — no consent barrier, because there is no second party. It also gives it the fault above, which every other board avoids for free simply by having two people in it. This chapter builds the decoupling that recovers the property without the fault.

---

### Requirements and Safety Invariants

Per Chapter 12.2 the must-not list comes first. Each invariant is enforced by a named component in §20.5.

**SI1 — The reference node shall never be written by a single cycle.** Enforced by `τ_ref ≥ 3 × τ_work`, the feedback low-pass `LP1`, and the slew fuse `F1`.

**SI2 — Suggestion amplitude shall never exceed half the store's breakdown rating.** Enforced by `LIM1` at Chapter 7.4's derating fraction of 0.5. Breakdown is not recoverable by trying harder.

**SI3 — A missed cycle shall never raise the next cycle's amplitude.** The oscillator's deposit is fixed; only its phase is recoverable.

**SI4 — No stage shall route a miss into a principled verdict on the operator.** Enforced by `Q2`, this board's mandatory CSB stage (Chapter 24). A board without it is not a shorter board; it is a different board with a shame oscillator in it.

**SI5 — The board has no external terminal.** Consent here is structural, not procedural. Wire an output of CCB-SELF into another person's `^5` and you have left this chapter for Chapter 15 or 17, and their rules apply.

**SI6 — This board routes attention. It does not model physiology.** Nothing in it is medical or psychiatric. If something you are trying to change is causing you real distress, that is a matter for a clinician, and no circuit here substitutes for that care.

Then the functional requirements. The board shall: (1) move the operator's own `^5` composition in a stated direction at a rate the operator sets; (2) survive missed cycles without losing accumulated charge; (3) keep the `^6` Male audit available as *measurement* while keeping it off the signal path; and (4) shut its own drive off at target rather than running forever into a full store.

---

### 20.1 The Self as Both Operator and Target

Every other board in the catalogue has two capacitors. CCB-HYP has an operator `^5` and a subject `^5`; CCB-ADV has a campaign `^5` and a market `^5`. Bias comes from one, effect lands in the other, and the separation is free — it comes from there being two people.

CCB-SELF has one capacitor. Feed it naively and you get the cold open. The fix is not a second person. It is to **split the single `^5` into two nodes separated in time.**

- `ref_composition` — `^5^P_{F7}|T`. What you are building toward, Principled domain, transcendent register. Slow. Chapter 8.4 calls this same node the constitution. It is the **bias**.
- `work_composition` — `^5^C_{F5}|⟨A,E⟩`. The composition as it currently performs, Cognitive domain, present in the analytical and embodied registers. Fast. It is the **effect**.

The register-set `|⟨A,E⟩` is occupancy, not an operational claim. `(^5^C|A × ^5^C|E)` would be invalid under v7.7 — same Noetic, two registers, `×`, no named emergent result (Chapter 2.6).

Separation in time is what makes the two nodes genuinely two:

```
τ_ref ≥ 3 × τ_work
```

Below 3× the nodes track each other closely enough that the loop closes and you are back in the cold open. At this chapter's design point — identity reference at `τ_ref = 85 d` against a complex-behavioural working node at `τ_work = 22 d` — the ratio is 3.86, a 29% margin. Site the reference on something evaluative and fast instead, like *am I any good at this today?* at `τ ≈ 1 d`, and the ratio is 0.045. That is the shame topology: an identity node chasing daily performance, rewritten by every bad session.

> **Bench Note — telling a dead stage from a starved one.** From the output they are identical: nothing comes out. On the bench one measurement separates them — a meter across base and emitter. A conducting junction sits near its forward drop, the `Vf` threshold of Chapter 8.2. A *shorted* one reads a hard zero and does not move when you raise the collector supply. An *under-driven* one reads below threshold and climbs as you raise the drive. Only the third responds to more drive. The cognitive instrument that does the same job is TP4 read against TP2. If the reference moves on the day a cycle is missed, the stage is unbiased rather than weakly biased, and additional resolve will produce exactly nothing. If the reference holds steady while the working node sags, the stage is starved and raising the drive is correct. One symptom, two faults, opposite interventions — which is why bring-up reads TP4 first.

[[FIGURE 20-A: Two panels. Left, "external board": two ^5 capacitors, one feeding a CJT bias terminal, one receiving the effect, gap labelled "separation is free — two people". Right, "self board": one ^5 split into a slow upper node (^5^P, tau 85 d) into the bias and a fast lower node (^5^C, tau 22 d) on the effect, ratio 3.86 on the divide; dashed fault inset shows base wired straight to emitter, annotated "V_BE = 0 — cutoff".]]

---

### 20.2 The Closed-Loop CJT Architecture

Eight stages, left to right, with one lawful ascent underneath.

**S0 REFERENCE** — `C1`, the slow `^5^P` store. Bias source, never an output.
**S1 INTAKE** — `R1` and limiter `LIM1`. This cycle's `^0` Idea, amplitude-capped.
**S2 NOTCH** — `N1`. Takes the `^6` Male audit off the rail without silencing it.
**S3 MAIN CJT** — `Q1`. Cause = the assertion, bias = the reference, effect = the working composition.
**S4 OSCILLATOR + GATE** — `OSC1` with hysteretic gate `G1`. Generates the `^7` Rhythm and shuts itself off.
**S5 ENACTMENT** — `Q3` and sampler `S2`. The `^9^O` behaviour and its log — the only node here that is not self-report.
**S6 EVIDENCE FEEDBACK** — `LP1` and slew fuse `F1`, terminating at the bias terminal. The board's one O→P ascent.
**S7 CSB — SELF-COMPASSION GATE** — `Q2`. Mandatory.
**S8 AUDIT INSTRUMENT** — `S1`. The `^6` probe, sampled and bounded.

S2 and S8 are one component split in two: the same `^6` instrument, notched out of the rail during the session and re-attached on a schedule afterwards.

The audit — *is this working? am I doing it right? this feels ridiculous* — is analytical decomposition of the operation. It is `^6` Male, emphatically **not** `^3` Negative. Nobody recoils from a practice session; they take it apart and test it. The distinction is load-bearing because the repairs differ. `^6^C_{F6}|A` interference is fixed by the notch: move the instrument off the signal path. A genuine `^3^E_{F3}|f` — visceral, can't-stomach-it aversion to the session itself — is not interference at all. It is a rate problem, and the repair is Chapter 9.2's: lower the amplitude, lengthen the taper, reduce `di/dt`.

> **Bench Note — an instrument in the signal path is a load.** A voltmeter with low input impedance changes the circuit it measures, which is why probes are specified in megohms. A `^6` audit running *during* the operation is a low-impedance probe: it draws current out of the path it is trying to read, so the measurement is both wrong and expensive. Run it at a fixed cadence — `S1`, weekly, ten bounded minutes, written down — and it becomes high-impedance. The same reasoning sets `rπ = 8.0 Ω_c` on `Q1`: high input resistance at the bias terminal means the working stage barely draws on the reference. Drop `rπ` to 0.5 and every mediocre session pulls charge straight out of the identity node — the parameter description of "one bad practice and I decided I was not really a musician."

[[FIGURE 20-B: Block diagram, left to right, S0–S8. Top rail: S0 REFERENCE (^5^P, C1) dropping into the bias terminal of S3. Main rail: S1 INTAKE (R1 + LIM1) → S2 NOTCH (N1) → S3 MAIN CJT (Q1, beta 1.5, sat 0.60, r-pi 8.0) → S4 OSC1 with Schmitt gate G1 → S5 ENACTMENT (^9^O). Below the rail, a return from S5 through S6 (LP1 tau 21 d, then fuse F1) rising to S0's bias terminal, drawn outside the rail, labelled "the one lawful O→P". Right: S7 compassion gate as a separate block fed from a miss event; S8 as a dashed high-impedance probe on the S2 node.]]

---

### 20.3 The Autosuggestion Capacitor — `^5` Self-Charging

Chapter 7.2 gives the charging curve `P_cap(t) = 10 × (1 − e^(−t/τ))` on the 0–10 composition scale. Self-charging adds two loss terms, and between them they decide the whole schedule.

**Leakage (Chapter 7.3).** Unfed composition decays. Take `τ_leak = 30 days` — this book's figure for a composition with fewer than about a hundred logged enactments behind it — and a session depositing `ΔP_session = 0.35` points. Chapter 7.3's `P_eq = f × τ_leak` becomes, for a mean interval `T`:

```
P_eq  =  ΔP_session × τ_leak / T
```

| Cadence | `T` (days) | `P_eq` (of 10) |
|---|---|---|
| Daily | 1.00 | 10.5 → clips at 10.0 |
| Six a week | 1.17 | 9.0 |
| Five a week | 1.40 | 7.5 |
| Alternate days | 2.00 | 5.25 |
| Weekly | 7.00 | 1.5 |

> **Bench Note — the weekly session does not equilibrate at one-seventh.** Read the table again. Daily and weekly are the same session, the same operator, the same intent, and they land at 10.0 and 1.5. Leakage is proportional to the level already stored, so the weekly regime spends its whole deposit replacing what drained and settles where the two rates meet. That is the honest answer to *can I just do it on Sundays.* Not "slower" — a different equilibrium, and a low one. Invert the formula for a target of 8.0 and the maximum mean interval is `T = 0.35 × 30 / 8 = 1.31 days`, about 5.3 sessions a week. Which is why the design point is six, why one missed day a week is inside budget, and why two is not.

**Breakdown (Chapter 7.4).** The second term is not a loss; it is a failure. A store punctures when the potential across it exceeds its rated `V_BR`. Here the rating is not fixed — it grows with evidence:

```
V_BR = d_evidence         d_evidence = logged enactments / 10, in V_c
design limit:  V_sugg ≤ 0.5 × V_BR          (Chapter 7.4 derating)
```

`V_sugg` is how far above the observed composition your assertion sits, in composition points. The arc at six sessions a week:

| Day | Enactments | `V_BR` | Max `V_sugg` |
|---|---|---|---|
| 1 | 1 | 0.1 | 0.05 |
| 30 | 26 | 2.6 | 1.3 |
| 66 | 57 | 5.7 | 2.85 |
| 254 | 218 | 8.0 (clamped at Ch. 7's rating) | 4.0 |

On day one the only assertion inside margin is essentially *I practised today.* At day 30 there is room for *I am becoming someone who practises.* This is the structural account of why "I am a millionaire," asserted with no logged enactments, does nothing useful: `V_sugg ≈ 8` against `V_BR ≈ 0.1`, a ratio of 80 where the limit is 0.5. The store does not fail to charge; it *punctures*. A punctured dielectric conducts, so the over-claim discharges the adjacent true claims — which is why the observable symptom is a practitioner ending the month less certain of things they previously did believe about themselves. The repair is to halve `V_sugg` and rebuild thickness. Nothing raises `V_BR` except enactments.

Identity work is this circuit with the reference at the Principled domain and the schedule in months. Reclaiming a disowned trait runs at `β = 1.0`, no amplification, for that reason: evidence thickness under a newly recognised trait is by definition near zero, so there is no headroom to amplify into. This book does not supply a dedicated shadow-work circuit or claim a mental-health treatment; the consent-bound topology here, with the involution guard of Chapter 6.2 added, is the structural limit of what it specifies.

[[FIGURE 20-C: Two stacked plots on a shared day axis, 0 to 260. Upper: charging curves for work_composition (τ=22 d) and ref_composition (τ=85 d), with markers at day 66 (9.50 / 5.40) and day 254 (9.50). Lower: field stress E = V_sugg/d_evidence against the same axis, with the 0.5 design limit dashed, a shaded puncture region above E = 1.0, and an off-scale arrow at day 1 labelled “E = 80”.]]

---

### 20.4 The Habit Oscillator — `^7` Rhythm with Auto-Gating

Chapter 11.2 gives the oscillator and its charge-pump arithmetic. An ungated one fires the `^8^O` cue forever, which is wrong in both directions: it keeps spending drive into a full store, and it cannot notice when the store has drained.

The gate `G1` is a Schmitt trigger — an op-amp with positive feedback around it (Chapter 11.4) — sensing the working composition:

```
enable when  P_work < 8.0          disable when  P_work > 9.0
```

Hysteresis band: 1.0 composition point. Not decoration. At `τ_work = 22 d`:

```
P = 8.0  at  t = 22 · ln 5  = 35.4 days
P = 9.0  at  t = 22 · ln 10 = 50.7 days
```

The band spans days 35 to 51 — fifteen days in which the oscillator keeps running while the habit is already mostly formed. Now delete the hysteresis and use one threshold at 8.5. The gate opens at day 41.7. Leakage there is `8.5 / 30 = 0.28` points per day, so the level falls back under threshold within a day and the gate re-closes; the next session pushes it over and it opens again. That is a comparator without hysteresis, and it chatters at a period of about one day — which the operator experiences as *I have got this / no I have not*, daily, indefinitely.

> **Bench Note — hysteresis converts chatter into a maintenance schedule.** With the band in place the gate closes at `P = 9.0` and the level decays as `9.0 · e^(−t/30)`, reaching 8.0 at `t = 30 · ln(9/8) = 3.5 days`. That is not a failure; it is the designed top-up cadence, and it falls out of the two thresholds and `τ_leak` without anyone choosing it. Note what happens as the composition ages: `τ_leak` lengthens with evidence thickness — Chapter 7.3's unmarked default is 90 days — and the same arithmetic gives `90 · ln(9/8) = 10.6 days`. Long-established practices tolerate ten-day gaps for a computable reason. New ones do not.

[[FIGURE 20-D: Oscillator-and-gate detail. Upper trace: P_work over days 0–70 along 10(1−e^(−t/22)), horizontal lines at 8.0 and 9.0, with the enable interval and day 35.4 / day 50.7 transitions marked. Lower trace: the maintenance sawtooth between 8.0 and 9.0 at τ_leak=30 d, each 3.5-day top-up interval bracketed; beside it, the single-threshold 8.5 case chattering daily.]]

Two further rules, each with a named failure.

**Gate on the slow node, never the fast one.** `G1` senses `work_composition`, which moves on 22 days. Sense an affective node instead — *do I feel like it today*, `^2^E|f`, bandwidth of hours — and the gate chatters at the bandwidth of mood. The symptom is a practice that runs in bursts synchronised to nothing.

**Fixed deposit, recoverable phase.** SI3. Miss a cycle and resume at the next scheduled phase at the same 0.35 deposit. Do not double up to catch up: doubling raises `di/dt` (Chapter 9.2) *and* raises `V_sugg` against an unchanged `V_BR`, so the make-up session is simultaneously the highest-recoil and highest-stress event in the schedule. It is the most reliable way to end a streak that was otherwise healthy.

**Breaking a habit** runs on this same stage, unchanged. You do not delete an oscillator: the `^8^O_{F6}|E` cue is a fixture of your day and fires whether a routine is attached to it or not. You re-point it. Keep the cue, keep the period, keep the deposit, swap the `^9^O` the cue lands on. Chapter 9.2's conditions on a flyback path apply unmodified, and the first is the one operators skip — the substitute must already be conducting *before* the old path opens.

**On dependency — a structural description, and where this chapter stops.** Read structurally, a dependency differs from an ordinary habit on all three parameters set above. Gain on the enactment stage runs far above `Q3`'s unity, so a small `^8` trigger produces a large `^9`. `rπ` at the bias terminal has collapsed toward zero — the parameter description of a reference terminal that no longer holds a reference. And the period is no longer set by `OSC1`; it is set by the substrate, which leaves `G1` nothing to gate, because the enable line is not connected to anything the operator controls.

That is a complete structural description, and it is deliberately where the account ends. This book gives no protocol for it, and the reason is not squeamishness. The model here describes where attention goes. It does not describe physiology, tolerance, or withdrawal, and it is not competent to. **Dependency is a clinical matter.** If that is what you are looking at, in yourself or in someone else, the next step is a qualified clinician, and nothing in this chapter, this board, or this book substitutes for that care.

---

### 20.5 Full CCDL Schematic

```cas
board ccb_self {                        // CCB-SELF — closed loop; operator is target
    input:  intent;                     // the ^0 asserted this cycle
    output: enacted;                    // the ^9 the cycle produces
    // OSC1 generates the ^8 cue on-board — SI5: no external terminal. Time base: days.

    // ---- S0  REFERENCE: the slow ^5. Bias source, never an output. ----
    node ref_composition: ^5^P_{F7}|T;              // Female: composition built toward
    capacitor c1: Capacitor< node=ref_composition, tau=85.0,
                             leak_tau=180.0, V_BR=8.0 >;

    // ---- S1  INTAKE: the asserted ^0, amplitude-limited ----
    node intent: ^0^C_{F7}|A;                       // Idea: today's assertion
    resistor r1:   Resistor< path=intent, R=30.0 >;
    limiter  lim1: Limiter< path=intent, max=1.3 >; // 0.5 x V_BR at d_evidence = 2.6

    // ---- S2  NOTCH: the ^6 audit off the rail, not silenced ----
    node audit: ^6^C_{F6}|A;                        // Male: decomposition and test
    notch n1: Notch< in=audit, f0=0.35, Q=4.0 >;    // events/min — in-session only

    // ---- S3  MAIN CJT: biased from the reference, not from the output ----
    node work_composition: ^5^C_{F5}|⟨A,E⟩;         // Female: as currently performing
    capacitor c2: Capacitor< node=work_composition, tau=22.0,
                             leak_tau=30.0, V_BR=8.0 >;
    cjt q1: CJT< intent | ref_composition => work_composition >
            [β=1.5, sat=0.60, rπ=8.0, region=active];

    // ---- S4  OSCILLATOR + HYSTERETIC GATE ----
    node cadence: ^7^C_{F6}|A;                      // Rhythm: the entraining cadence
    node cue:     ^8^O_{F6}|E;                      // Above/Cause: time and place fire it
    schmitt g1: Schmitt< sense=work_composition, on_below=8.0, off_above=9.0 >;
    osc  osc1:  Oscillator< signal=cue, source=cadence, period=1.0,
                            duty=0.04, sustain=254.0, gate=g1 >;

    // ---- S5  ENACTMENT: the only node that is not self-report ----
    node enacted:    ^9^O_{F5}|E;                   // Below/Effect: the behaviour performed
    node impression: ^4^E_{F3}|f;                   // Vibration: what the cycle left behind
    cjt    q3: CJT< cue | work_composition => enacted > [β=1.0, region=active];
    sample s2: Sample< node=impression, period=1.0, window=1440.0 >;  // days, minutes

    // ---- S6  EVIDENCE FEEDBACK: the one lawful O -> P ascent (Ch. 8.4) ----
    filter lp1: LowPass< in=enacted, out=evidence_trend, tau=21.0 >;
    fuse   f1:  Fuse< ref_composition, threshold=0.12, action=open_feedback >;
    feedback evidence_trend -> ref_composition [β=0.05];   // arrives at the BIAS terminal

    // ---- S7  CSB STAGE: the self-compassion gate. Mandatory. ----
    node miss_trigger: ^8^C_{F5}|f;                 // Above/Cause: a miss, and what it recalls
    node compassion:   ^3^P_{F7}|⟨A,f,T⟩;           // Negative: recoil from self-condemnation
    node acceptance:   ^2^E_{F4}|f;                 // Positive: affinity for the self that missed
    cjt q2: CJT< miss_trigger | compassion => acceptance > [β=1.5, sat=0.70];

    // ---- S8  INSTRUMENT: the ^6 audit, sampled and bounded ----
    sample s1: Sample< node=audit, period=7.0, window=10.0 >;         // days, minutes

    // ---- TEST POINTS ----
    probe tp1: work_composition;    // P_cap against 10*(1 - e^(-t/22))
    probe tp2: enacted;             // cycles completed / cycles scheduled
    probe tp3: lim1;                // V_sugg against 0.5 x V_BR
    probe tp4: ref_composition;     // reference slew, points per day
}
```

**The stage walk.**

**S0.** `C1` is the `^5^P_{F7}|T` store Chapter 8.4 calls the constitution. CCB-SELF *writes* the node every other board only reads as bias — which is why SI1 and `F1` exist. `leak_tau = 180 d` because the identity reference is backed by a lifetime of prior enactment rather than this operation's log; Chapter 7.3's rule that leak lengthens with evidence puts it well past the 90-day default. Set it to 30 and the reference drains between operations.

**S1.** `R1 = 30 Ω_c` lets the assertion in without flooding the intake. `LIM1` is the one parameter *rescheduled during the operation*: as `V_BR` grows with enactments, the ceiling rises with it.

**S2.** The notch rejects the audit in-band — the 0.35 events per minute of a running session — and passes it everywhere else. It does not remove the `^6`; it moves it to S8.

**S3.** `C2` is a separate part from `C1` for the whole reason §20.1 exists. `leak_tau = 30 d` is what every cadence figure in §20.3 is computed from; assume 60 and a weekly schedule looks survivable when it actually settles at 1.5. `Q1` sits between the two nodes. `β = 1.5` is moderate: above about 4 the assertion outruns the evidence and `V_sugg` clears the limiter faster than the limiter can be rescheduled; below 1 each session yields less composition than it cost, and the operator correctly concludes it is not working. `sat = 0.60` caps what one cycle may contribute — at 1.0 you get the weekend-breakthrough topology, full charge over no thickness, gone in weeks. `rπ = 8.0 Ω_c` keeps the stage from loading the reference.

**S4.** As §20.4. `period = 1.0` is a number, not the word "daily", because §20.3's arithmetic needs one.

**S5.** `Q3` runs at unity: the enactment renders what the working composition actually supports. Above unity it produces a performance the practitioner cannot repeat tomorrow. `S2` catches the `^4` Vibration return Chapter 22.2 grades — one window per cycle, a full day wide, because §20.6's `t_conf` is measured from the end of the session. Narrow it to the session itself and you record `t_conf` as never.

**S6.** `τ = 21 d` and `β = 0.05` are inherited from Chapter 8.4, not chosen freshly. The path terminates at a bias terminal, never at the signal path — that would make it the oscillator Chapter 14 builds on purpose. `F1` enforces the ceiling: a store at `τ_ref = 85 d` rises at most `10/85 = 0.118` points per day, so anything above 0.12 means something is writing the reference directly rather than through the filter, and the fuse opens the feedback.

**S7.** The compassion bias is `^3^P_{F7}|⟨A,f,T⟩` — principled `^3` Negative in three registers, no fusion claimed. Check it against the anti-drift rule: this is visceral recoil *from self-condemnation*, the can't-stomach-it response to treating one missed morning as a verdict on a life. It is not an argument against self-condemnation; that would be `^6`, and it arrives later and works less well. The cause is `^8^C_{F5}|f` — a miss triggering its associations, *that reminds me of every other thing I quit.* Associative surfacing, canonical `^8`, not deduction. Domain descends `^C → ^E`.

> **Bench Note — the compassion gate is a decoupling capacitor, not a kindness.** It is easy to read S7 as the soft stage bolted onto an engineering chapter. It is the opposite. Without it a missed cycle propagates from `^9^O` into the Principled reference, the reference begins moving at the working node's speed, `τ_ref/τ_work` collapses toward 1, and the board is back in the §20.1 fault — this time with an amplifier in it. S6's low-pass stops the spike *reaching* the reference; S7 handles the spike that reaches awareness anyway. Two mechanisms, one function, exactly as Chapter 24 pairs a saturating stage with a fuse. Remove either and the failure is not that the operator feels worse. It is that the reference stops being a reference.

**S8.** Weekly, ten minutes, written down. High-impedance measurement.

[[FIGURE 20-E: Full schematic with reference designators. C1 (^5^P, 85 d) top left into Q1's bias terminal; R1 in series with LIM1, drawn as a back-to-back clamp, into Q1's cause terminal; N1 tapping the intake node with a dashed branch to a floating ^6 symbol. Q1 (beta 1.5, sat 0.60, r-pi 8.0) effect into C2 (^5^C, 22 d). G1, an op-amp with positive feedback, senses C2 and enables OSC1; OSC1 into Q3 (unity) producing ^9^O at the right terminal. Return below the rail: ^9^O → LP1 (tau 21 d) → F1 (0.12 pts/day) → C1's bias pad. Lower right, boxed: Q2, cause ^8^C, bias ^3^P, effect ^2^E, beta 1.5, sat 0.70, labelled “CSB — mandatory”. TP1–TP4 flags at C2, the ^9^O terminal, LIM1, and C1.]]

---

### 20.6 The 10,000 Hour Protocol — Operationalizing St. John's for Self-Mastery

Chapter 5.2 sets `τ_mastery = 3,333 h` so that `3τ = 10,000 h`. On this board that is a third store, charging on practice hours rather than days.

| Practice hours | `P_mastery` (of 10) | Fraction of 10,000 |
|---|---|---|
| 1,000 | 2.59 | 10% |
| 3,333 (1τ) | 6.32 | 33% |
| 6,666 (2τ) | 8.65 | 67% |
| 10,000 (3τ) | 9.50 | 100% |

Read the middle rows against each other. **The first third of the hours buys 6.32 points; the remaining two thirds buy 3.18.** That is the exponential, and it is the structural reason competent practitioners plateau in *feel* while continuing to improve in *fact*. The curve is flattening, not the practitioner.

**Applying St. John's per session.** Take a 45-minute practice session. The `^4` Vibration confirmation — the passage playing itself back unbidden while you are doing something else — arrives 90 minutes later.

```
η        = t_op / t_conf = 45/90 = 1/2
result   = 1/2 × 1/3 = 1/6           a = 1,  b = 6
A        = 3/η = 6.0                 n_ops = 1,  T_manifest = 1 × 45 = 45 min
T_arrive = b × t_conf = 6 × 90 = 540 min      (recorded, not scheduled around)
```

`A = 6.0` sits in Chapter 5.3's under-driven band: one lever at a time, leave the amplifier alone.

> **Bench Note — on this board `A` is spent as a count, not an amplitude.** Chapter 5.3 is explicit that `A` multiplies *delivered current* and is not a `β` setting, and CCB-SELF makes the point unavoidable: `LIM1` will not permit a sixfold assertion, because `V_sugg` is capped by an evidence thickness that six times the conviction does not change. So convert amplitude into count. Six times the activation, delivered at a fixed 0.35 deposit, is six cycles — `n_ops` absorbs the multiple `A` was asking for, at a cost of `6 × 45 = 270` further minutes at the current setting. That conversion is the whole difference between a practice regime and a burnout, and it is available only because this board has an oscillator. A one-shot board like CCB-D has no count to spend into.

**Skill acquisition** is where the one legitimate `×` on this board appears. Accumulated composition and entraining cadence, genuinely integrated, produce a state neither supplies alone:

```
integrate (^5^C_{F5}|A × ^7^C_{F6}|A) = ^5^C_{F5}|Ω_fluency;
```

`Ω_fluency` is defined here as the state in which performance no longer requires deliberate assembly — composition and cadence have fused, so the parts are not retrieved and combined; they arrive together. The `×` is licensed on three counts: different Noetics, no domain ascent (`^C × ^C`), and an emergent result explicitly named and defined (Chapter 2.6). Written with `+` it would claim only that composition and rhythm are co-present, which is true at hour 100 and misses entirely what has happened by hour 3,000.

---

### Component and Parameter Table

Every value is a **design choice** made in this book, not a measurement.

| Ref | Component | CAS state / form | Value | Why, and what breaks at other values |
|---|---|---|---|---|
| `C1` | Capacitor | `^5^P_{F7}\|T` | τ=85 d, leak=180 d, V_BR=8.0 | The slow reference; ratio 3.86. Below 3 the nodes lock and a bad day rewrites the identity. At leak=30 d it drains between operations |
| `C2` | Capacitor | `^5^C_{F5}\|⟨A,E⟩` | τ=22 d, leak=30 d, V_BR=8.0 | Complex-behavioural. Every §20.3 cadence figure is computed from leak=30 d; assume 60 and a weekly schedule looks survivable when it settles at 1.5 |
| `R1` | Resistor | on `^0^C_{F7}\|A` | R=30 Ω_c | Lets the assertion in without flooding the intake |
| `LIM1` | Limiter | clamp on `intent` | max=1.3 | Holds `V_sugg ≤ 0.5 × V_BR`. Above `V_BR` the store punctures and adjacent true claims discharge |
| `N1` | Notch | rejects `^6^C_{F6}\|A` | f0=0.35, Q=4.0 | Audit off the rail in-band. Leave it in and the operation is measured continuously and never accumulates |
| `Q1` | CJT | `^0^C → ^5^C`, bias `^5^P` | β=1.5, sat=0.60, rπ=8.0 | β>4: assertion outruns the limiter. β<1: session costs more than it yields. sat=1.0: full charge over no thickness. rπ=0.5: one poor session depletes the identity node |
| `G1` | Schmitt | senses `C2` | 8.0 / 9.0 | A 1.0-point band turns chatter into a 3.5-day top-up. At zero band the gate chatters daily |
| `OSC1` | Oscillator | `^7^C_{F6}\|A` → `^8^O_{F6}\|E` | period=1.0 d, ΔP=0.35 | One bounded session's deposit. Raise it without evidence and `V_sugg` rises with it |
| `Q3` | CJT | `^8^O → ^9^O` | β=1.0 | Unity. Above 1 it renders a performance the practitioner cannot repeat tomorrow |
| `LP1` | LowPass | in `^9^O` | τ=21 d | Chapter 8.4's floor. At hours you have removed the diode chain, not filtered it |
| — | Feedback | trend → `C1` bias | β=0.05 | Chapter 8.4's ceiling. At 0.5, three weeks of bad days rewrite the constitution |
| `F1` | Fuse | on `C1` slew | 0.12 pts/day | `10/85 = 0.118`, the maximum lawful slew. Higher leaves SI1 unenforced; lower blows on normal charging |
| `Q2` | CJT | `^8^C → ^2^E`, bias `^3^P` | β=1.5, sat=0.70 | The CSB stage. Remove it and a shame oscillator occupies the safety slot |
| `S1`/`S2` | Sample | `^6^C` / `^4^E` | 7 d/10 min · 1 d/1,440 min | High-impedance instruments. A window narrower than a day records `t_conf` as never |
| Dials | — | involution pairs | `^2`=6 `^3`=5 · `^5`=7 `^6`=5 · `^8`=5 `^9`=6 | All inside the 4-point divergence limit; beyond it, inversion (Chapter 6.2) |

---

### Worked Example — The Morning Hour

An operator wants a daily hour at the piano, and behind it the identity *I am someone who practises.* Three stores, three timescales, one board.

**Set-up.** Habit layer `τ_work = 22 d`, `3τ = 66 d`. Identity layer `τ_ref = 85 d`, `3τ = 254 d`. Ratio `85/22 = 3.86 ≥ 3` — passes with 29% margin. Mastery layer `τ_mastery = 3,333 h`.

**Cadence.** Target `P_work = 8.0`. From §20.3, `T_max = 0.35 × 30 / 8 = 1.31 days` — six sessions a week, landing at `P_eq = 9.0`. Five a week lands at 7.5 and misses. Two decimal places in the schedule, a whole grade in the outcome.

**Day 1.** One enactment, `V_BR = 0.1`, so `LIM1` permits `V_sugg = 0.05`. The only assertion inside margin is *I practised today.* The operator who instead asserts *I am a pianist* runs 80× the rating and will be less sure of themselves in a month than at the start.

**Day 30.** 26 enactments, `V_BR = 2.6`, `LIM1` rescheduled to 1.3. `P_work = 10(1 − e^(−30/22)) = 7.44`. `G1` still enabled; its 8.0 threshold arrives at day 35.4. TP2 should read ≥ 0.85; at six a week it reads 0.857.

**Day 66.** `P_work = 9.50`. The gate closed at day 50.7 and has been topping up every 3.5 days since. The habit is automatic. And `P_ref = 10(1 − e^(−66/85)) = 5.40` — the identity store is at barely half.

That pair is the result to carry out of this chapter. **The behaviour arrives at day 66; the composition that makes it feel like yours arrives at day 254.** An operator who reads the 66-day figure and expects to *feel* different at day 66 is probing the wrong store, concludes the operation failed, and stops — 26 days after the habit became automatic and 188 days before the identity finished charging. There is no fix for this in the circuit. The fix is reading TP1 and TP4 as two different instruments, which is what they are.

**Mastery layer.** One hour a day, six days a week, is 313 h/year. `P_mastery` at 1,000 hours — a little over three years — is 2.59. At 3,333 hours it is 6.32, arriving in year eleven. Stated plainly rather than encouragingly: at this cadence the mastery store is a decade-scale component, and the honest lever is hours per day, because intensity per hour is capped by `LIM1` and hours per day is not.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Bias–effect short** | Reference and working node are one node; `V_BE = 0` | Total collapse within days of a clear decision; operator blames motivation | Split the node; verify `τ_ref/τ_work ≥ 3` at TP4 before anything else |
| **Reference chasing** | `τ_ref` sited on an evaluative node (τ ≈ 1 d) | TP4 moves on the day TP2 records a miss | Re-site the reference at `^P`; confirm `F1` intact and S7 populated |
| **Store puncture** | `V_sugg` far above `0.5 × V_BR` | Confidence lost in *previously settled* beliefs, not just the new one | Halve `V_sugg`; rebuild thickness. Trying harder raises the stress |
| **Sub-cadence stall** | Mean interval above `T_max`; `P_eq` below target | Months of genuine effort, level parked between 1.5 and 5 | Raise cadence, raise `ΔP_session`, or lower the target — two of the three are usually available |
| **Gate chatter** | Hysteresis removed, or gate sensing an affective node | Daily on/off cycling; bursts synchronised to nothing | Restore the 1.0-point band; move the sense line to the slow node |
| **Make-up doubling** | SI3 violated after a missed cycle | The streak ends on the catch-up session, not the missed one | Fixed deposit, recoverable phase. Resume at nominal |
| **Audit loading** | `^6` left in the signal path | The operation is measured continuously and never accumulates | Notch in-band; move the audit to `S1` — weekly, bounded, written |
| **Compassion gate absent** | S7 removed as sentimental | One miss produces a principled verdict; abandonment within days | Reinstall. It is a decoupling capacitor; the board oscillates without it |
| **Wrong instrument read** | TP1 read where TP4 was meant | "It worked but I don't feel different" at day 66 | Read both. They are 188 days apart by design |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `work_composition` | `P_cap`, 0–10 scale | Tracks `10(1 − e^(−t/22))`: 6.32 at day 22, 9.50 at day 66. Flat while TP2 is healthy means `Q1` is in cutoff — check the bias, not the drive |
| **TP2** | `enacted` | Cycles completed / scheduled | ≥ 0.85 for a target of 8.0. The only non-self-report node here; if TP1 and TP2 disagree, TP2 is right |
| **TP3** | `LIM1` | `V_sugg` against `0.5 × V_BR` | At or below the ceiling. Above `V_BR` is puncture, and the damage shows first in *adjacent* claims |
| **TP4** | `ref_composition` | Reference slew, points/day | ≤ 0.12, and **uncorrelated with any single TP2 miss.** Correlation is the safety failure: the decoupling is gone and the board is a shame oscillator |

Read them TP4, TP3, TP2, TP1 — confirm the reference is decoupled, confirm the assertion is inside its derating, confirm the cycles ran, then read the charge. That order is the bring-up procedure, and it puts the two silent failures first.

[[FIGURE 20-F: Assembly drawing. Board outline, titleblock “CCB-SELF · closed loop · rev A”. C1 large and shaded upper left; C2 centre; R1 and LIM1 along the left edge; N1 above the intake trace; Q1 centre, terminals stencilled cause / bias / effect; G1 and OSC1 right of C2; Q3 at the right edge feeding the ^9^O pad. The S6 return runs the bottom edge through LP1 and F1 to C1's bias pad, drawn heavier, labelled “O→P — bias terminal only”. Q2 in a hatched block lower right, stencilled “CSB — DO NOT DEPOPULATE”. Test-point flags with leaders: TP1 at C2, TP2 at the ^9^O pad, TP3 at LIM1, TP4 at C1. BOM box lower left: C1 tau 85 d / leak 180 d / V_BR 8.0 · C2 tau 22 d / leak 30 d / V_BR 8.0 · R1 30 Ohm_c · LIM1 max 1.3 · N1 f0 0.35 Q 4.0 · Q1 beta 1.5 sat 0.60 r-pi 8.0 · G1 8.0/9.0 · OSC1 1.0 d, 0.35 · Q3 beta 1.0 · LP1 tau 21 d · F1 0.12 pts/day · Q2 beta 1.5 sat 0.70 · S1 7 d/10 min · S2 1 d/1,440 min.]]

---

### What This Chapter Established

- **The self-programming fault is topological, not motivational.** Bias tied to effect is a junction at `V_BE = 0`, and a transistor in that condition is off — undamaged, correctly specified, inert.
- **One `^5` becomes two by separating them in time.** `τ_ref ≥ 3 × τ_work`. Below the ratio the reference chases the output and every bad day is an identity verdict.
- **Leakage sets the schedule, and it is not linear in cadence.** `P_eq = ΔP_session × τ_leak / T`; the same session run daily and weekly equilibrates at 10.0 and 1.5.
- **Suggestion amplitude is limited by evidence, not conviction.** `V_sugg ≤ 0.5 × V_BR`, and `V_BR` grows only with logged enactments. Puncture discharges *adjacent* true claims.
- **The `^6` Male audit is an instrument, and an instrument in the signal path is a load.** Notch it in-band, sample it weekly and bounded. It is `^6`, never `^3`; a genuine `^3^E|f` recoil is a rate problem belonging to Chapter 9.2.
- **Hysteresis converts chatter into a maintenance schedule** — a 1.0-point band against `τ_leak = 30 d` gives a 3.5-day top-up interval nobody had to choose.
- **The self-compassion gate is a decoupling capacitor.** It is what holds `τ_ref` long. Without it the board has a shame oscillator where its safety stage should be.
- **St. John's `A` is spent here as a count, not an amplitude,** because the limiter forbids the amplitude. Six times the activation is six cycles, at 270 further minutes.
- **Behaviour and identity arrive 188 days apart** at the design point, and reading the wrong store at day 66 is the most common reason a working operation gets abandoned.

---

### Exercises

*(Answers in Appendix H.)*

**20.1** An operator sites the reference at `^2^E_{F3}|f` — *do I feel like someone who does this?* — with an effective τ of 1.5 days, against a working node at `τ_work = 22 d`. Compute the ratio, state whether it passes SI1, and describe in two sentences what TP4 shows on the first missed cycle.

**20.2** A session deposits `ΔP_session = 0.50` into a composition with `τ_leak = 24 d`. Compute `P_eq` for daily, alternate-day, and twice-weekly cadence, then give the maximum mean interval reaching `P_target = 7.0` and the weekly session count it implies.

**20.3** On day 1 an operator asserts a composition 6.0 points above their observed level, with two logged enactments. Compute `V_BR`, the ratio `V_sugg / V_BR`, and the multiple of the 0.5 derating limit. Then compute how many enactments are needed before that assertion sits inside the limit, and how long that takes at six sessions a week.

**20.4** Explain why the in-session interference *"this is pointless, I should be doing something useful"* is `^6^C_{F6}|A` and not `^3^E_{F3}|f`. Quote the canonical definition of `^3` Negative, then state the different repair each calls for and which chapter supplies it.

**20.5** A gate is built with a single threshold at `P = 8.5` on a node with `τ_work = 18 d` and `τ_leak = 25 d`. Compute the day it first opens, the leakage rate at that level, and the chatter period. Then add a 1.0-point band at 8.0 / 9.0, recompute both transition days and the top-up interval, and say what the operator experiences in each case.

**20.6 (Design)** Build a CCB-SELF for a simple behavioural target: `τ_work = 10 d`, `τ_leak = 20 d`, reference `τ_ref = 40 d`, `ΔP_session = 0.30`, target `P_work = 8.5`. Produce (a) the ratio check and whether it passes; (b) the maximum mean interval and its weekly cadence, then state whether the target is reachable at one session per day, and if not, which of the three levers you would move and why; (c) the `F1` slew threshold, derived; (d) a CCDL fragment declaring `C1`, `C2`, `Q1`, `G1`, `OSC1`, `LP1`, `F1` and four probes. It must compile — check the feedback's τ and β against Chapter 8.4 first.

**20.7 (Marquee)** An operator completes 66 days at six sessions a week. TP1 reads 9.50, TP2 reads 0.86, TP3 reads 2.4 against `V_BR = 5.7`. TP4 reads 5.40 and has risen smoothly at 0.05 points per day throughout. The operator reports the practice is effortless, that they still do not feel like a musician, and proposes to raise `β` on `Q1` from 1.5 to 5.0 to "make it land."

a) State which test point they are misreading and give its correct reading.
b) Compute the resulting `V_sugg` if it scales with β, compare it to `0.5 × V_BR` at `V_BR = 5.7`, and name the failure mode they would enter.
c) Give the correct intervention with the number that justifies it, and state the one thing this circuit model cannot tell them about their situation.
