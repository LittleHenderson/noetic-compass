# CHAPTER 20
## CCB-SELF — The Self-Programming Board
*The only board with no target port — and the one fault that makes it fail anyway*

Tie a transistor's base to its emitter and the device turns off.

Not "runs weakly." Off. The base-emitter junction needs a forward voltage across it before any current crosses, and a wire between the two terminals guarantees there is none. The collector supply can be as large as you like. Nothing moves. The part is undamaged, correctly specified, and completely inert, because the terminal that was supposed to hold a *reference* has been shorted to the terminal that was supposed to carry the *result*.

You have watched a person do this. On a Sunday evening, in a genuinely clear moment, someone decides that from now on they are a person who practises every morning. They mean it entirely. Nine days later it is gone, and the conclusion they draw is that they did not want it enough — that the fault was in the drive rail.

The drive rail was fine. They shorted the bias to the effect. The reference against which the new composition was to be measured was *the very composition being built*, so the moment performance dipped, the reference dipped with it, the junction unbiased itself, and the stage went to cutoff. This is not a metaphor about willpower. It is the topology of the circuit they built, and it is the single most common fault on this board.

CCB-SELF is the closed-loop board: the operator and the target are the same `^5`. That gives it the one property no other board in this catalogue has — there is no consent barrier, because there is no second party. It also gives it the fault above, which every other board avoids for free simply by having two people in it. This chapter is about building the decoupling that gets that property back.

---

### Requirements and Safety Invariants

Per Chapter 12.2, the must-not list comes first. These are structural, and each one is enforced by a named component later in the listing.

**SI1 — The reference node shall never be written by a single cycle.** Enforced by the reference time constant (`τ_ref ≥ 3 × τ_work`), the feedback low-pass (§8.4's τ ≥ 3 weeks), and the slew fuse `F1`.

**SI2 — Applied suggestion amplitude shall never exceed half the dielectric field limit.** Enforced by the limiter `LIM1`. Chapter 7.4's breakdown mode is not recoverable by trying harder.

**SI3 — A missed cycle shall never increase the next cycle's amplitude.** The oscillator's amplitude is fixed; only its phase is recoverable. Compounding a missed dose raises `di/dt` past the budget Chapter 9 sets.

**SI4 — No stage shall route a miss into a principled verdict on the operator.** Enforced by the self-compassion gate `Q2`, which is this board's mandatory CSB stage (Chapter 24). A board without it is not a shorter board; it is a different board with a shame oscillator in it.

**SI5 — The board has no external terminal.** Consent is structural here, not procedural. If you find yourself wiring an output of CCB-SELF into another person's `^5`, you have left this chapter and entered Chapter 17 or Chapter 15, and their rules apply.

**SI6 — This board routes attention. It does not model physiology.** Nothing in it is medical or psychiatric. If something you are trying to change is causing you real distress, that is a matter for a clinician, and no circuit here substitutes for that care.

Only then the functional requirements. The board shall: (1) move the operator's own `^5` composition in a stated direction at a rate the operator sets; (2) survive missed cycles without losing accumulated charge; (3) keep the `^6` Male audit available as *measurement* while keeping it off the signal path; and (4) shut its own drive off when the target composition is reached, rather than running forever into a full capacitor.

---

### 20.1 The Self as Both Operator and Target

Every other board in the catalogue has two capacitors. CCB-HYP has an operator `^5` and a subject `^5`; CCB-ADV has a campaign `^5` and a market `^5`. The bias terminal is fed from one and the effect terminal lands in the other, and the separation is free — it comes from there being two people.

CCB-SELF has one capacitor. Feed it naively and you get the cold open: bias tied to effect, junction unbiased, stage in cutoff.

The fix is not to find a second person. It is to **split the single `^5` into two nodes separated in time.**

- `ref_composition` — `^5^P_{F7}|T`. The composition you are building toward, held at the Principled domain, transcendent register. Slow. This is the same node Chapter 8.4 calls the constitution and Chapter 7.1 calls the accumulated-formation capacitor. It is the *bias*.
- `work_composition` — `^5^C_{F5}|⟨A,E⟩`. The composition as it is currently performing, held at the Cognitive domain, present in the analytical and embodied registers. Fast. This is the *effect*.

The register-set `|⟨A,E⟩` is a specification, not an operational claim: the working composition is instantiated in both registers, and nothing here asserts they fuse. Writing `(^5^C|A × ^5^C|E)` would be invalid under v7.7 — same Noetic, multiple registers, `×`, and no named emergent result.

Separation in time is what makes the two nodes genuinely two. The design rule:

```
τ_ref ≥ 3 × τ_work
```

Below 3× the nodes track each other closely enough that the loop closes and you are back in the cold open. At the design point of this chapter — an identity-level reference (`τ_ref = 85 days`) against a complex-behavioural working node (`τ_work = 22 days`) — the ratio is 3.86, a 29% margin. Set the reference to something evaluative and fast, like "am I any good at this today?" (τ ≈ 1 day), and the ratio is 0.045. That is the shame topology: the identity node chasing the daily performance, rewritten by every bad session.

> **Bench Note — how to tell a dead stage from a starved one.** They look identical from the output: nothing comes out. On the bench you separate them with a single measurement — a meter across base and emitter. A silicon junction that is conducting sits near its forward drop, the `Vf` threshold of Chapter 8.2; one that is *shorted* reads a hard zero and does not move when you raise the collector supply; one that is merely *under-driven* reads below the threshold and climbs as you raise the drive. Only the third responds to more drive. The cognitive instrument that does the same job is TP4 read against TP2. If the reference moves on the same day a cycle is missed, `V_BE` is zero, the stage is unbiased rather than weakly biased, and additional resolve will produce exactly nothing. If the reference holds steady while the working node sags, the stage is starved and raising the drive is the correct response. One symptom, two faults, opposite interventions — which is why the bring-up order in the Test Points section reads TP4 first.

[[FIGURE 20-A: Two panels. Left, "external board": two ^5 capacitors, operator feeding a CJT bias terminal, target receiving the effect, separation labelled "free — two people". Right, "self board": one ^5 split into a slow upper node (^5^P, τ_ref = 85 d) biasing the CJT and a fast lower node (^5^C, τ_work = 22 d) receiving it, plus a dashed fault inset showing base wired directly to emitter, annotated "V_BE = 0 — cutoff".]]

---

### 20.2 The Closed-Loop CJT Architecture

Eight stages, left to right, with one lawful ascent underneath.

**S0 REFERENCE** — `C1`, the slow `^5^P` capacitor. Bias source. Never an output.
**S1 INTAKE** — `R1` and the limiter `LIM1`. The `^0` Idea being asserted, amplitude-capped.
**S2 NOTCH** — `N1`. Takes the `^6` Male audit off the rail without silencing it.
**S3 MAIN CJT** — `Q1`. Cause = the assertion, bias = the reference, effect = the working composition.
**S4 OSCILLATOR + GATE** — `OSC1` with the hysteretic gate `G1`. Generates the `^7` Rhythm and shuts itself off.
**S5 ENACTMENT** — `Q3`, with the confirmation sampler `S2`. The `^9^O` behaviour and its log — the only node on the board that is not self-report.
**S6 EVIDENCE FEEDBACK** — `LP1` and the slew fuse `F1`, into the bias terminal. The board's one O→P ascent.
**S7 CSB — SELF-COMPASSION GATE** — `Q2`. Mandatory.
**S8 AUDIT INSTRUMENT** — `S1`. The `^6` probe, sampled and bounded.

S2 and S8 are one component split in two: the same `^6` instrument, notched out of the rail at S2 and re-attached on a schedule at S8.

The `^6` Male audit — *is this working? am I doing it right? this feels ridiculous* — is analytical decomposition of the operation. It is emphatically **not** `^3` Negative; nobody recoils from a practice session, they take it apart and test it. The distinction matters because the two faults have different repairs. `^6^C_{F6}|A` interference is fixed by the notch: move the instrument off the signal path. A genuine `^3^E_{F3}|f` — visceral, can't-stomach-it aversion to the session itself — is not an interference problem at all; it is a rate problem, and the repair is Chapter 9's: lower the amplitude, lengthen the taper, reduce `di/dt`.

And the reason the audit must come off the rail is not that doubt is bad. It is that **an instrument in the signal path is a load.**

> **Bench Note — a voltmeter with low input impedance changes the circuit it measures.** This is why probes are specified in megohms. A `^6` audit running continuously during the operation has, in these terms, low input impedance: it draws current out of the very path it is trying to read, so the measurement is both wrong and expensive. Run it instead at a fixed cadence — `S1` samples weekly, in a bounded ten-minute window, written down — and it becomes high-impedance: it reads the node without loading it. This is also why `rπ = 8.0 Ω_c` on `Q1`. High input resistance at the bias terminal means the working stage barely draws on the reference. Drop `rπ` to 0.5 and every mediocre session pulls charge directly out of the identity node, which is the structural description of "one bad practice and I decided I was not really a musician."

[[FIGURE 20-B: Block diagram, left to right, stages S0–S8. Top rail: S0 REFERENCE (^5^P, C1) dropping into the bias terminal of S3. Main rail: S1 INTAKE (R1 + LIM1) → S2 NOTCH (N1) → S3 MAIN CJT (Q1, β=1.5, sat=0.60, rπ=8.0) → S4 OSC1 with Schmitt gate G1 → S5 ENACTMENT (^9^O). Below the rail, a return from S5 through S6 (LP1 τ=21 d, then fuse F1) rising to S0's bias terminal, drawn outside the rail and labelled "the one lawful O→P". Right: S7 compassion gate as a separate block fed from a miss event; S8 as a dashed high-impedance probe touching the S2 node.]]

---

### 20.3 The Autosuggestion Capacitor — `^5` Self-Charging

Chapter 7.2 gives the charging curve, `P_cap(t) = 10 × (1 − e^(−t/τ))`, on the 0–10 composition scale. Self-charging adds two loss terms that decide almost everything about the schedule.

**Leakage (Chapter 7.3).** Unfed composition decays: `P(t) = P₀ · e^(−t/τ_leak)`. Take `τ_leak = 30 days`, the design choice in this chapter for a composition with fewer than about a hundred logged enactments behind it. A session delivers `ΔP_session = 0.35` points. For an interval `T` short against `τ_leak`, the level where charge in balances charge out is

```
P_eq  =  ΔP_session × τ_leak / T
```

| Cadence | `T` (days) | `P_eq` (of 10) |
|---|---|---|
| Daily | 1.0 | 10.5 → clips at 10.0 |
| Six days a week | 1.17 | 9.0 |
| Five days a week | 1.40 | 7.5 |
| Alternate days | 2.0 | 5.25 |
| Weekly | 7.0 | 1.5 |

> **Bench Note — the weekly session does not equilibrate at one-seventh.** Read the table again. Daily and weekly are the same session, the same operator, the same intent — and they land at 10.0 and 1.5. The reason is that leakage is proportional to the level already stored, so the weekly regime spends its entire delivery replacing what drained, and settles where the two rates happen to meet. This is the honest answer to "can I just do it on Sundays." Not "slower." *A different equilibrium, and a low one.* Invert the formula for a target of 8.0 and the maximum mean interval is `T = 0.35 × 30 / 8 = 1.31 days` — about 5.3 sessions a week, which is why the design point is six and why one missed day a week is inside budget and two is not.

**Dielectric field limit (Chapter 7.4).** The second loss term is not a loss at all; it is a failure. A capacitor breaks down when the field across the dielectric exceeds its strength, and field is voltage divided by thickness. Here:

```
E  =  V_sugg / d_evidence        design limit:  E ≤ 0.5 · E_break,  E_break = 1.0
```

`V_sugg` is how far above the observed composition your assertion sits, in composition points. `d_evidence` is the thickness of accumulated `^9^O` enactment underneath it — this book's design convention is one unit per ten logged enactments. Work the arc:

| Day (at six sessions/week) | Enactments | `d_evidence` | Max safe `V_sugg` |
|---|---|---|---|
| 1 | 1 | 0.1 | 0.05 |
| 30 | 26 | 2.6 | 1.3 |
| 66 | 57 | 5.7 | 2.85 |
| 254 | 218 | 21.8 | 10.9 (unbounded on a 0–10 scale) |

On day one the only assertion inside margin is essentially *I practised today*. At day 30 you have room for *I am becoming someone who practises*. At day 254 the evidence is thick enough that the identity claim carries any voltage the scale can supply. This is the structural account of why "I am a millionaire," said by someone with forty pounds and no logged enactments, does nothing useful: `V_sugg ≈ 8`, `d_evidence ≈ 0.1`, `E = 80` — eighty times breakdown. The capacitor does not fail to charge. It *punctures*, and a punctured dielectric conducts: the over-claim discharges the adjacent true claims, which is why the observable symptom is the practitioner losing confidence in things they previously did believe about themselves. The repair is to drop `V_sugg` to half of `d_evidence` and rebuild thickness. There is no version of trying harder that raises `E_break`.

Identity work is this same circuit with the reference at the Principled domain and the schedule in months. Reclaiming a disowned trait — the `^3` you have been attributing outward, recognised and re-composed into `^5` — runs at `β = 1.0`, no amplification, for exactly the field reason above: the point is accurate recognition, and the evidence thickness under a newly recognised trait is by definition near zero. The dedicated shadow-integration circuit, which adds the involution guard this board does not carry, is Chapter 25.4; CCB-SELF supplies only the capacitor it charges into.

[[FIGURE 20-C: Two stacked plots on a shared day axis, 0 to 260. Upper: charging curves for work_composition (τ=22 d) and ref_composition (τ=85 d), with markers at day 66 (9.50 / 5.40) and day 254 (9.50). Lower: field stress E = V_sugg/d_evidence against the same axis, with the 0.5 design limit dashed, a shaded puncture region above E = 1.0, and an off-scale arrow at day 1 labelled "E = 80".]]

---

### 20.4 The Habit Oscillator — `^7` Rhythm with Auto-Gating

Chapter 11.2 gives the oscillator. An ungated one fires the `^8^O` cue on schedule forever, which is wrong in both directions: it keeps spending drive into a capacitor that is already full, and it has no way to notice when the capacitor has drained.

The gate `G1` is a Schmitt trigger — an op-amp with positive feedback around it (Chapter 11.4) — sensing the working composition:

```
enable when  P_work < 8.0        disable when  P_work > 9.0
```

Hysteresis band: 1.0 composition point. It is not decoration. Work the numbers on the design case, `τ_work = 22 days`:

```
P = 8.0   at   t = 22 · ln 5   = 35.4 days
P = 9.0   at   t = 22 · ln 10  = 50.7 days
```

So the band spans days 35 to 51 — just over fifteen days in which the oscillator keeps running while the habit is already mostly formed. Now remove the hysteresis and use a single threshold at 8.5. The gate opens at day 41.7. Leakage at that level is `8.5 / 30 = 0.28` points per day, so the level falls back under the threshold within a day and the gate re-closes. Then the next session pushes it back over and it opens again. You have built a comparator without hysteresis, and it chatters — with a period of about one day, which the operator experiences as *I have got this / no I have not*, every day, indefinitely.

> **Bench Note — hysteresis converts chatter into a maintenance schedule.** With the band in place the gate opens at `P = 9.0` and the level decays as `9.0 · e^(−t/30)`, reaching 8.0 at `t = 30 · ln(9/8) = 3.5 days`. That is not a failure; that is the designed top-up cadence, and it falls out of the two thresholds and `τ_leak` without anyone choosing it. Note also what happens as the composition ages: `τ_leak` lengthens with evidence thickness — this book's design figure is roughly 90 days past five hundred enactments — and the same arithmetic gives `90 · ln(9/8) = 10.6 days`. Long-established practices tolerate ten-day gaps for a computable reason, and new ones do not.

Two further rules on the gate, each with a named failure.

**Gate on the slow node, never the fast one.** `G1` senses `work_composition`, which moves on 22 days. Sense an affective node instead — *do I feel like it today*, `^2^E|f`, bandwidth of hours — and the gate chatters at the bandwidth of mood. The symptom is a practice that runs in bursts synchronised to nothing.

**Fixed amplitude, recoverable phase.** SI3. Miss a cycle and you resume at the next scheduled phase at the same 0.35 amplitude. You do not run a double session to catch up. Doubling raises both `di/dt` (Chapter 9: the kick is a pure inverse in taper time, and it works the same on the way up) and `V_sugg` against an unchanged `d_evidence`, so the make-up session is simultaneously the highest-recoil and highest-field event in the schedule. It is the single most reliable way to end a streak that was otherwise healthy.

Breaking a habit runs on this same stage and nothing else changes. You do not delete an oscillator — the `^8^O_{F6}|E` cue is a fixture of your day and will fire whether you have a routine attached to it or not. You re-point it: keep the cue, keep the period, keep the amplitude, and swap the `^9^O` the cue lands on. Chapter 9.2's three conditions on a flyback path apply without modification, and the first is the one operators skip: the substitute must already be conducting *before* the old path opens.

**On dependency — a structural description, and where this chapter stops.** Read structurally, a dependency has a signature distinct from an ordinary habit on all three of the parameters this chapter has been setting. `β` on the enactment stage runs far above the unity of `Q3`, so a small `^8` trigger produces a large `^9`. `rπ` at the bias terminal has collapsed toward zero, which is the parameter description of the terminal that is supposed to hold a reference no longer holding one. And the oscillator's period is no longer set by `OSC1` — it is set by the substrate, which means the auto-gate `G1` has nothing to gate, because the enable line is not connected to anything the operator controls. That is a complete structural description, and it is deliberately where the account ends.

This book does not give a protocol for it, and the reason is not squeamishness: the operational version would be a procedure, and dependency is not a routing problem. The model in this chapter describes where attention goes. It does not describe physiology, tolerance, or withdrawal, and it is not competent to. **Dependency is a clinical matter.** If that is what you are looking at — in yourself or in someone else — the right next step is a clinician, and nothing in this chapter, this board, or this book substitutes for that care.

[[FIGURE 20-D: Oscillator-and-gate detail. Upper trace: P_work over days 0–70 along 10(1−e^(−t/22)), horizontal lines at 8.0 and 9.0, band between them shaded and annotated "days 35.4 – 50.7". Lower trace: the gate enable as a square wave — solid, with hysteresis, one clean transition at day 50.7 and a re-enable 3.5 days later; dashed, without hysteresis, chattering at one-day period from day 41.7. Inset: G1 as an op-amp with a positive-feedback resistor pair, terminals labelled sense / enable.]]

---

### 20.5 Full CCDL Schematic

```cas
board ccb_self {                        // CCB-SELF — closed loop; operator is target
    input:  intent;                     // the ^0 the operator asserts this cycle
    output: enacted;                    // the ^9 the cycle produces
    // the ^8 cue is generated on-board by OSC1 — SI5: there is no external terminal

    // ---- S0  REFERENCE: the slow ^5. Bias source, never an output. ----
    node ref_composition: ^5^P_{F7}|T;              // Female: composition built toward
    capacitor c1: Capacitor< node=ref_composition, tau=85.0,
                             leak_tau=180.0, e_break=1.0 >;         // tau in days

    // ---- S1  INTAKE: the asserted ^0, amplitude-limited ----
    node intent: ^0^C_{F7}|A;                       // Idea: today's assertion
    resistor r1:   Resistor< path=intent, R=30.0 >;
    limiter  lim1: Limiter< path=intent, max=1.3 >;   // E = 1.3/2.6 = 0.50 at d=2.6
                                                      // reschedule monthly against TP3

    // ---- S2  NOTCH: the ^6 audit off the rail, not silenced ----
    node audit: ^6^C_{F6}|A;                        // Male: decomposition and test
    notch n1: Notch< in=audit, band=in_session >;

    // ---- S3  MAIN CJT: biased from the reference, not from the output ----
    node work_composition: ^5^C_{F5}|⟨A,E⟩;         // Female: as currently performing
    capacitor c2: Capacitor< node=work_composition, tau=22.0,
                             leak_tau=30.0, e_break=1.0 >;
    cjt q1: CJT< intent | ref_composition => work_composition >
            [β=1.5, sat=0.60, rπ=8.0, region=active];

    // ---- S4  OSCILLATOR + HYSTERETIC GATE ----
    node cadence: ^7^C_{F6}|A;                      // Rhythm: the entraining cadence
    node cue:     ^8^O_{F6}|E;                      // Above/Cause: time and place fire it
    schmitt g1: Schmitt< sense=work_composition, on_below=8.0, off_above=9.0 >;
    osc  osc1:  Oscillator< signal=cue, source=cadence, period=1.0,
                            amplitude=0.35, gate=g1 >;              // period in days

    // ---- S5  ENACTMENT: the only node that is not self-report ----
    node enacted:    ^9^O_{F5}|E;                   // Below/Effect: the behaviour performed
    node impression: ^4^E_{F3}|f;                   // Vibration: what the cycle left behind
    cjt    q3: CJT< cue | work_composition => enacted > [β=1.0, region=active];
    sample s2: Sample< node=impression, period=1.0, window=1440.0 >;  // days, minutes

    // ---- S6  EVIDENCE FEEDBACK: the one lawful O -> P ascent (see 8.4) ----
    filter lp1: LowPass< in=enacted, out=evidence_trend, tau=21.0 >;   // three weeks
    fuse   f1:  Fuse< ref_composition, threshold=0.12, action=open_feedback >;
    feedback evidence_trend -> ref_composition [β=0.05];   // arrives at the BIAS terminal

    // ---- S7  CSB STAGE: the self-compassion gate. Mandatory. ----
    node miss_trigger: ^8^C_{F5}|f;                 // Above/Cause: a miss and its associations
    node compassion:   ^3^P_{F7}|⟨A,f,T⟩;           // Negative: recoil from self-condemnation
    node acceptance:   ^2^E_{F4}|f;                 // Positive: affinity for the self that missed
    cjt q2: CJT< miss_trigger | compassion => acceptance > [β=1.5, sat=0.70];

    // ---- S8  INSTRUMENT: the ^6 audit, sampled and bounded ----
    sample s1: Sample< node=audit, period=7.0, window=10.0 >;  // days, minutes

    // ---- TEST POINTS ----
    probe tp1: work_composition;    // P_cap against 10*(1 - e^(-t/22))
    probe tp2: enacted;             // cycles completed / cycles scheduled
    probe tp3: lim1;                // field stress E = V_sugg / d_evidence
    probe tp4: ref_composition;     // reference slew, points per day
}
```

**The stage walk.**

**S0.** `C1` is the same `^5^P_{F7}|T` capacitor Chapter 8.4 calls the constitution. CCB-SELF writes to the node every other board reads as bias, which is why SI1 and the slew fuse exist and why this board is not optional reading for anyone running the others. Its `leak_tau = 180 days` is long for a stated reason: the identity reference is backed by a lifetime of prior enactment, not by this operation's log, and by the §20.4 rule that leak lengthens with evidence thickness it sits well past the 90-day figure. Set it to 30 and the reference drains between operations, `P_eq` on the reference collapses, and the ratio rule of §20.1 cannot hold no matter what `τ_ref` says.

**S1.** `R1 = 30 Ω_c` is moderate intake resistance — enough to let the assertion in without flooding. `LIM1` is a diode clamp (Chapter 8), and it is the one parameter on this board that is *rescheduled during the operation*: as `d_evidence` grows, the ceiling rises. Every other value here is fixed at design time.

**S2.** The notch rejects the audit in-band — during the session — and passes it everywhere else. It does not remove the `^6`; it moves it to S8.

**S3.** `C2` is the working capacitor, and it is a separate part from `C1` for the whole reason §20.1 exists: two nodes, two time constants, one `^5`. `τ = 22 d` is this chapter's design figure for a complex behavioural composition, and `leak_tau = 30 d` is what every cadence number in §20.3 is computed from — assume 60 and the weekly schedule looks survivable, which it is not. `Q1` sits between them. `β = 1.5` is moderate: above about 4 the assertion outruns the evidence and `E` clears the limiter faster than the limiter can be rescheduled; below 1 each session yields less composition change than it cost, and the operator correctly concludes it is not working. `sat = 0.60` caps what one cycle may contribute; `rπ = 8.0 Ω_c` keeps the stage from loading the reference.

**S4.** As §20.4. Note `period=1.0` day, not "daily" — the parameter is a number because §20.3's leakage arithmetic needs one.

**S5.** `Q3` runs at unity. The enactment should render what the working composition actually supports, neither inflated nor hedged; a gain above 1 here is the stage that produces a performance the practitioner cannot repeat tomorrow. `impression` is the `^4` Vibration return that Chapter 22.2 grades, and `S2` is the instrument that catches it: one sampling window per cycle, a full day wide, because §20.6's `t_conf` is measured from the end of the session and the return in that worked case arrives three hours later. Narrow the window to the session itself and you record `t_conf` as never — which reads as `η → 0`, and St. John's then asks for a gain the limiter will not grant.

**S6.** `τ = 21.0 days` and `β = 0.05` are inherited from Chapter 8.4, not chosen freshly. The path terminates at `ref_composition`, a bias terminal — never at the signal path, which would make it the oscillator Chapter 14 builds on purpose. `F1` enforces the ceiling: a capacitor with `τ_ref = 85` days rises at most `10/85 = 0.118` points per day, so anything above 0.12 means something is writing to the reference directly rather than through the filter, and the fuse opens the feedback.

**S7.** The compassion bias is `^3^P_{F7}|⟨A,f,T⟩` — principled `^3` Negative, present in three registers, no fusion claimed. Check it against the anti-drift rule: this is visceral recoil *from self-condemnation*, the can't-stomach-it response to treating one missed morning as a verdict on a life. It is not an argument against self-condemnation; that would be `^6`, and it arrives later and works less well. The cause is `^8^C_{F5}|f`: a miss triggering its associations — *that reminds me of every other thing I quit*. Associative surfacing, canonical `^8`, not deduction. Domain descends `^C → ^E`.

> **Bench Note — the compassion gate is a decoupling capacitor, not a kindness.** It is easy to read S7 as the soft stage bolted onto an engineering chapter. It is the opposite: it is the component that holds `τ_ref` long. Without it, a missed cycle propagates from `^9^O` straight into the Principled reference, the reference starts moving at the working node's speed, `τ_ref/τ_work` collapses toward 1, and the board is back in the §20.1 fault — this time with an amplifier in it. S6's low-pass prevents the spike from *reaching* the reference; S7 handles the spike that reaches awareness anyway. Two mechanisms, one function, exactly as Chapter 24 pairs a saturating stage with a fuse. Remove either and the failure is not that the operator feels worse. It is that the reference node stops being a reference.

**S8.** Weekly, ten minutes, written down. High-impedance measurement.

[[FIGURE 20-E: Full schematic with reference designators. C1 (^5^P, 85 d) top left into Q1's base; R1 in series with LIM1 (a back-to-back diode clamp) into Q1's collector; N1 tapping the intake node with a dashed line to a floating ^6 symbol. Q1 (β=1.5, sat=0.60, rπ=8.0) emitter into C2 (^5^C, 22 d). G1, an op-amp with positive feedback, senses C2 and enables OSC1; OSC1 into Q3 (unity) producing ^9^O at the right terminal. Return path below the rail: ^9^O → LP1 (τ=21 d) → F1 (0.12 pts/day) → C1's bias terminal. Lower-right boxed subcircuit: Q2, cause ^8^C, bias ^3^P, effect ^2^E, β=1.5, sat=0.70, labelled "CSB — mandatory". TP1–TP4 flags at C2, the ^9^O terminal, LIM1, and C1.]]

---

### 20.6 The 10,000 Hour Protocol — Operationalizing St. John's for Self-Mastery

Chapter 5 derives the constant: `τ = t_practice / t_total = 1/3`, with 10,000 active hours inside roughly 30,000 elapsed. On this board that becomes a third capacitor, charging on practice hours rather than days, with `τ_mastery = 3,333 h` so that `3τ = 10,000 h`.

| Practice hours | `P_mastery` (of 10) | Fraction of the 10,000 |
|---|---|---|
| 1,000 | 2.59 | 10% |
| 3,333 (1τ) | 6.32 | 33% |
| 6,666 (2τ) | 8.65 | 67% |
| 10,000 (3τ) | 9.50 | 100% |

Read the middle two rows against each other. **The first third of the hours buys 6.3 points; the remaining two thirds buy 3.2.** That is the exponential, and it is the honest structural reason competent practitioners plateau in feel while continuing to improve in fact — the curve is flattening, not the practitioner.

The elapsed-time arithmetic is worth doing plainly, because this is where the 10,000-hour figure usually gets quoted without a schedule attached. At one hour a day, 10,000 hours is 27.4 years. At three hours a day, 9.1 years. At six hours a day, five days a week, 6.4 years. Chapter 5's 3½-year Adept arc corresponds to about 7.8 hours a day, every day — a full-time apprenticeship, which is what it was.

**Applying St. John's per session.** Take a 60-minute practice session. The confirmation — Chapter 5's `^4` Vibration return — arrives 180 minutes later, when the passage plays itself back unbidden while you are doing something else.

```
η       = t_op / t_conf = 60/180 = 1/3
result  = 1/3 × 1/3     = 1/9        →  a = 1, b = 9
β_next  = 9      n_ops = 1      T_manifest = 1 × 60 min
```

> **Bench Note — on this board, `β_next` is a count, not an amplitude.** Chapter 5 reads `β_next = 9` as an instruction to make the next operation nine times stronger. On CCB-SELF you may not obey that: `LIM1` forbids it, because a ninefold assertion against an unchanged `d_evidence` puts `E` far past breakdown, and the result is Chapter 7.4, not mastery. So convert amplitude into count. Nine times the activation, delivered at the fixed 0.35 amplitude, is nine cycles: `n_ops` absorbs the multiple that `β_next` was asking for, and `T_manifest = n_ops × t_op` becomes 9 × 60 = 540 minutes — nine hours of practice at the current setting. Note that 540 minutes is the same figure Chapter 5's Corvette worked example arrives at from the other direction. That conversion is the whole difference between a practice regime and a burnout, and it is available only because this board has an oscillator. A one-shot board like CCB-D has no count to spend into.

Skill acquisition is where the one legitimate `×` on this board appears. Accumulated composition and entraining cadence, integrated, produce a state neither supplies alone:

```
(^5^C_{F5}|A × ^7^C_{F6}|A) = ^5^C|Ω_fluency
```

`Ω_fluency` is defined here as the state in which performance no longer requires deliberate assembly — the composition and the cadence have fused, so the parts are not retrieved and combined, they arrive together. The `×` is licensed because the operands are different Noetics, the domain does not ascend (`^C × ^C`), and the emergent result is explicitly named and defined. Written as `+` it would claim only that composition and rhythm are co-present, which is true at hour 100 and misses what has happened by hour 3,000.

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement. The
reference designator is the CCDL identifier in §20.5, uppercased.

| Ref | Component | CAS state / form | Value | Why that value, and what breaks at others |
|---|---|---|---|---|
| `C1` | Capacitor | `^5^P_{F7}\|T` | τ=85 d, leak=180 d | The slow reference. `τ_ref/τ_work` = 3.86; below 3 the nodes lock and a bad day rewrites the identity. leak=180 d because the identity node is backed by a lifetime of enactment; at leak=30 d it drains between operations |
| `C2` | Capacitor | `^5^C_{F5}\|⟨A,E⟩` | τ=22 d, leak=30 d | Complex-behavioural. Every cadence figure in §20.3 is computed from leak=30 d; assume 60 and the weekly schedule looks survivable when it actually settles at `P_eq` = 1.5 |
| `R1` | Resistor | on `^0^C_{F7}\|A` | 30 Ω_c | Lets the assertion in without flooding the intake |
| `LIM1` | Limiter | diode clamp on intent | max=1.3 | Holds `E ≤ 0.5`. Above `E` = 1.0 the dielectric conducts and adjacent true claims discharge |
| `N1` | Notch | reject `^6^C_{F6}\|A` | band=in_session | Audit off the rail. Leave it in and the operation is measured continuously and never accumulates |
| `Q1` | CJT | `^0^C → ^5^C`, bias `^5^P` | β=1.5 | Above 4, `E` clears the limiter; below 1 the session costs more than it yields |
| `Q1` | — | — | sat=0.60 | No single cycle restructures composition. At 1.0 you get the weekend-breakthrough topology: full charge, no thickness, gone in weeks |
| `Q1` | — | — | rπ=8.0 Ω_c | Stage does not load the reference. At 0.5 one poor session depletes the identity node |
| `G1` | Schmitt | senses `C2` | 8.0 / 9.0 | A 1.0-point band turns chatter into a 3.5-day top-up. At zero band the gate chatters daily |
| `OSC1` | Oscillator | `^7^C_{F6}\|A` → `^8^O_{F6}\|E` | 1.0 d, 0.35 pts | `ΔP_session` from one bounded session. Raise it without evidence and `E` rises with it |
| `Q3` | CJT | `^8^O → ^9^O` | β=1.0 | Unity. Above 1 it renders a performance the practitioner cannot repeat tomorrow |
| `LP1` | LowPass | in `^9^O` | τ=21 d | Chapter 8.4's floor. At hours you have removed the diode chain, not filtered it |
| — | Feedback | trend → `C1` bias | β=0.05 | Chapter 8.4's ceiling. At 0.5, three weeks of bad days rewrite the constitution |
| `F1` | Fuse | on `C1` slew | 0.12 pts/day | `10/85 = 0.118`, the maximum lawful slew. Higher leaves SI1 unenforced; lower blows on normal charging |
| `Q2` | CJT | `^8^C → ^2^E`, bias `^3^P` | β=1.5, sat=0.70 | CSB stage. Removing it puts a shame oscillator where the safety element should be |
| `S1` | Sample | on `^6^C` | 7 d / 10 min | High-impedance instrument. Continuous sampling is a low-impedance load |
| `S2` | Sample | on `^4^E_{F3}\|f` | 1 d / 1,440 min | Catches the `^4` confirmation return so §20.6 has a `t_conf`. Window narrower than a day records `t_conf` as never, and St. John's then asks for a gain `LIM1` will refuse |
| Dials | — | involution pairs | `^2`=6 `^3`=5 · `^5`=7 `^6`=5 · `^8`=5 `^9`=6 | All within the 4-point divergence limit. Beyond it, inversion — Chapter 25, §25.2 |

---

### Worked Example — The Morning Hour

An operator wants a daily hour at the piano, and behind it the identity *I am someone who practises*. Three capacitors, three timescales, one board.

**Set-up.** Habit layer: complex behavioural, `τ_work = 22 d`, `3τ = 66 d`. Identity layer: `τ_ref = 85 d`, `3τ = 254 d`. Ratio check: `85/22 = 3.86 ≥ 3` — passes with 29% margin. Mastery layer: `τ_mastery = 3,333 h`.

**Cadence.** Target `P_work = 8.0`. From §20.3, `T_max = 0.35 × 30 / 8 = 1.31 days` — six sessions a week, `P_eq = 9.0`. Five a week lands at 7.5 and misses the target; this is a two-decimal difference in the schedule and a whole grade in the outcome.

**Day 1.** `d_evidence = 0.1`. `LIM1` permits `V_sugg = 0.05`. The only assertion inside margin is *I practised today*. The operator who instead asserts *I am a pianist* is running `E ≈ 60` and will be less sure of themselves in a month than they were at the start.

**Day 30.** 26 enactments, `d = 2.6`, `LIM1` rescheduled to 1.3. `P_work = 10(1 − e^(−30/22)) = 7.44`. Gate `G1` still enabled — the threshold is 8.0, reached at day 35.4. TP2 should read ≥ 0.85 cycles completed over cycles scheduled; at six a week it reads 0.857.

**Day 66.** `P_work = 9.50`. The gate opened at day 50.7 and has been top-ping up every 3.5 days since. The habit is automatic. And `P_ref = 10(1 − e^(−66/85)) = 5.40` — the identity node is at barely half.

That last pair of numbers is the result to carry out of this chapter. **The behaviour arrives at day 66; the composition that makes it feel like yours arrives at day 254.** An operator who reads the 66-day figure and expects to *feel* like a different person at day 66 is probing the wrong capacitor, concludes the operation failed, and stops — 26 days after the habit became automatic and 188 days before the identity finished charging. There is no fix for this in the circuit. The fix is reading TP1 and TP4 as two different instruments, which is what they are.

**Mastery layer.** One hour a day, six days a week, is 313 h/year. `P_mastery` at 1,000 hours — a little over three years — is 2.59. At 3,333 hours, 6.32, arriving somewhere in year eleven. Stated plainly rather than encouragingly: at this cadence the mastery capacitor is a decade-scale component, and the honest lever is hours per day, not intensity per hour, because intensity per hour is capped by `LIM1` and hours per day is not.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Bias–effect short** | Reference and working node are one node; `V_BE = 0` | Total collapse within days of a clear decision; operator blames motivation | Split the node; verify `τ_ref/τ_work ≥ 3` at TP4 before anything else |
| **Reference chasing** | `τ_ref` set by an evaluative node (τ ≈ 1 d) | TP4 moves the day TP2 records a miss | Re-site the reference at `^P`; confirm `F1` intact; confirm S7 present |
| **Dielectric puncture** | `V_sugg` far above `d_evidence` | Practitioner loses confidence in previously settled beliefs, not just the new one | Drop `V_sugg` to `0.5 × d_evidence`; rebuild thickness. Trying harder raises `E` |
| **Sub-cadence stall** | Interval above `T_max`; `P_eq` below target | Months of genuine effort, level parked at 1.5–5 | Raise cadence, or raise `ΔP_session`, or lower the target. Two of the three are usually available |
| **Gate chatter** | Hysteresis removed, or gate sensing an affective node | Daily on/off cycling; bursts synchronised to nothing | Restore the 1.0-point band; move the sense line to the slow node |
| **Make-up doubling** | SI3 violated after a missed cycle | The streak ends on the catch-up session, not the missed one | Fixed amplitude, recoverable phase. Resume at nominal |
| **Audit loading** | `^6` left in the signal path | The operation is measured continuously and never accumulates | Notch in-band; move the audit to `S1`, weekly, bounded, written |
| **Compassion gate absent** | S7 removed as sentimental | One miss produces a principled verdict; abandonment follows within days | Reinstall. It is a decoupling capacitor; the board oscillates without it |
| **Wrong instrument read** | TP1 read where TP4 was meant | "It worked but I don't feel different" at day 66 | Read both. They are 188 days apart by design |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `work_composition` | `P_cap` on the 0–10 scale | Tracks `10(1 − e^(−t/22))`: 6.32 at day 22, 9.50 at day 66. Flat with TP2 healthy means `Q1` is in cutoff — check the bias, not the drive |
| **TP2** | `enacted` | Cycles completed / cycles scheduled | ≥ 0.85 for a target of 8.0. The only non-self-report node on the board; if TP1 and TP2 disagree, TP2 is right |
| **TP3** | `LIM1` | Field stress `E = V_sugg / d_evidence` | ≤ 0.50. Above 1.0 is puncture and the damage shows up first in *adjacent* claims, not the asserted one |
| **TP4** | `ref_composition` | Reference slew, points per day | ≤ 0.12, and **uncorrelated with a single TP2 miss.** Correlation here is the safety failure: the decoupling has gone and the board is a shame oscillator |

Read them TP4, TP3, TP2, TP1 — confirm the reference is decoupled, confirm the field is in margin, confirm the cycles actually ran, then read the charge. That order is the bring-up procedure, and it puts the two silent failures first.

[[FIGURE 20-F: Assembly drawing. Board outline with titleblock "CCB-SELF · closed loop · rev A". Placement: C1 large and shaded upper left; C2 centre; R1 and LIM1 along the left edge; N1 above the intake trace; Q1 centre with terminals stencilled cause / bias / effect; G1 and OSC1 right of C2; Q3 at the right edge feeding the ^9^O output pad. The S6 return trace runs the bottom edge through LP1 and F1 to C1's bias pad, drawn in heavier weight and labelled "O→P — bias terminal only". Q2 sits in its own hatched block lower right, stencilled "CSB — DO NOT DEPOPULATE". Test-point callout flags with leader lines: TP1 at C2, TP2 at the ^9^O pad, TP3 at LIM1, TP4 at C1. BOM box lower left: C1 ^5^P τ=85 d leak=180 d · C2 ^5^C τ=22 d leak=30 d · R1 30 Ω_c · LIM1 max=1.3 · N1 in_session · Q1 β=1.5 sat=0.60 rπ=8.0 · G1 8.0/9.0 · OSC1 1.0 d 0.35 · Q3 β=1.0 · LP1 τ=21 d · F1 0.12 pts/day · Q2 β=1.5 sat=0.70 · S1 7 d / 10 min · S2 1 d / 1,440 min.]]

---

### What This Chapter Established

- **The self-programming fault is topological, not motivational.** Bias tied to effect is a junction with `V_BE = 0`, and a transistor in that condition is off — undamaged, correctly specified, inert.
- **One `^5` is made into two by separating them in time.** `τ_ref ≥ 3 × τ_work` is the design rule; below it the reference chases the output and every bad day is an identity verdict.
- **Leakage sets the schedule, and it is not linear in cadence.** `P_eq = ΔP_session × τ_leak / T`. The same session run daily and weekly equilibrates at 10.0 and 1.5.
- **Suggestion amplitude is limited by evidence thickness, not by conviction.** `E = V_sugg / d_evidence ≤ 0.5`. Puncture discharges adjacent true claims, which is why over-claiming leaves an operator less certain than before.
- **The `^6` Male audit is an instrument, and an instrument in the signal path is a load.** Notch it in-band, sample it weekly and bounded. It is `^6`, not `^3`; a genuine `^3^E|f` recoil is a rate problem and belongs to Chapter 9.
- **Hysteresis on the auto-gate converts chatter into a maintenance schedule** — a 1.0-point band and `τ_leak = 30 d` give a 3.5-day top-up interval that nobody had to choose.
- **The self-compassion gate is a decoupling capacitor.** It holds `τ_ref` long. Without it the board has a shame oscillator where its safety stage should be.
- **On this board St. John's `β_next` is spent as a count, not an amplitude,** because `LIM1` forbids the amplitude. Nine times the activation is nine cycles.
- **The behaviour and the identity arrive 188 days apart** — day 66 and day 254 at the design point — and reading the wrong capacitor at day 66 is the most common reason a working operation gets abandoned.

---

### Exercises

*(Answers in Appendix H.)*

**20.1** An operator sets a reference at `^2^E_{F3}|f` — "do I feel like someone who does this?" — with an effective τ of 1.5 days, against a working node at `τ_work = 22 d`. Compute the ratio, state whether it passes, and describe in two sentences what TP4 will show on the first missed cycle.

**20.2** A session delivers `ΔP_session = 0.50` into a composition with `τ_leak = 24 days`. Compute `P_eq` for daily, alternate-day, and twice-weekly cadence, and give the maximum mean interval that reaches `P_target = 7.0`.

**20.3** On day 1 an operator asserts a composition 6.0 points above their observed level, with two logged enactments. Compute `d_evidence`, `E`, and the multiple of `E_break`. Then compute how many logged enactments are needed before that same assertion sits inside the 0.5 design limit, and say how long that takes at six sessions a week.

**20.4** Explain why the in-session interference *"this is pointless, I should be doing something useful"* is classified `^6^C_{F6}|A` and not `^3^E_{F3}|f`. Reference the canonical definition of `^3` Negative, then state the different repair each one calls for and which chapter supplies it.

**20.5** A gate is built with a single threshold at `P = 8.5` on a node with `τ_work = 18 d` and `τ_leak = 25 d`. Compute the day the gate first opens, the leakage rate at that level, and the resulting chatter period. Then add a 1.0-point hysteresis band (8.0 / 9.0), recompute both transition days and the top-up interval, and state what the operator experiences in each case.

**20.6 (Design)** Build a CCB-SELF for a simple behavioural target: `τ_work = 10 d`, `τ_leak = 20 d`, identity reference at `τ_ref = 40 d`, `ΔP_session = 0.30`, target `P_work = 8.5`. Produce (a) the ratio check and whether it passes; (b) the maximum mean interval and the weekly cadence it implies — then state whether the target is reachable at one session per day, and if not, which of the three available levers you would move and why; (c) the `F1` slew threshold, derived; (d) a CCDL fragment declaring `C1`, `C2`, `Q1`, `G1`, `OSC1`, `LP1`, `F1`, and four probes. It must compile — check the feedback's τ and β against Chapter 8.4 before you submit it.

**20.7 (Marquee)** An operator completes 66 days at six sessions a week. TP1 reads 9.50, TP2 reads 0.86, TP3 reads 0.41. TP4 reads 5.40 and has been rising smoothly at 0.05 points per day. The operator reports that the practice is effortless and that they still do not feel like a musician, and proposes to raise `β` on `Q1` from 1.5 to 5.0 to "make it land."

a) State which test point they are misreading and what the correct reading of it is.
b) Compute `E` after the proposed change, assuming `V_sugg` scales with `β` and `d_evidence` is unchanged at 5.7, and name the failure mode they would enter.
c) Give the correct intervention, with the number that justifies it, and state the one thing this circuit model cannot tell them about their situation.
