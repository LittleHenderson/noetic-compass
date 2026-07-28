# CHAPTER 12

## How to Read a CCB Schematic

*The drawing conventions, the design order, the invariant list, and the four probes — everything the next eight chapters assume you already know*

---

Pin the same one-page drawing above two benches.

The first operator looks at it for a long time and calls it impressive. They can name most of the parts. Asked what the board will do, they describe the intention printed in the title block.

The second operator reads it in about ninety seconds and hands it back with three sentences. The guard stage is biased off a rail that will sit below its own firing floor for the first two years, so it will never fire and nothing on the board will say so. The gain stage is set high enough that it is pinned against its ceiling at any realistic input, so it reports a flat line and looks like stability. And the two diode drops in the signal path total 3.2, which means that below a drive of 3.2 this board produces nothing at all — not a little, none — so half the reports of "it stopped working" will be a drive problem misdiagnosed as a gain problem.

Nothing separates those two operators except a reading order. The second one checked the bias rail against every cutoff on the board, checked each gain against its ceiling, and summed the forward drops in the path. Three passes, ninety seconds, before considering what the board was *for*.

This chapter is that reading order. It is the difference between the eight board chapters that follow being drawings you can work from and pictures you can admire.

---

### 12.1 The CCB Design Process — Requirements → Block Diagram → Schematic → BOM → Test

Five steps, in this order, every board. The order is not a style preference. Each step produces the input the next one consumes, and skipping one does not save time — it moves the cost to bring-up, where it is paid at interest.

**Step 1 — Requirements.** A numbered table of what the board shall do, written before any component is chosen, each row naming a stage. The test of the table is whether you can point at any component on the finished board and name the row that demanded it; a part that serves no row is a part you added because it looked right, and it should come off. Requirements are written second, not first — 12.2 is what gets written first, and it is written first for a reason.

**Step 2 — Block diagram.** Function-level boxes, signal left to right, no component values anywhere. This is the step operators skip, and the one that catches architectural errors while they are still free: it is where you see that your guard sits downstream of your amplifier, or that your feedback path terminates on the signal path instead of a bias terminal. Both are fatal, and both are invisible in a schematic dense enough to hide them.

[[FIGURE 12-A: Block diagram of CCB-0, the trainer board — five labelled boxes left to right on one horizontal signal path (BIAS RAIL feeding upward from below, then AUDIT, GUARD, AMPLIFY, DELIVER); a bias rail drawn as a horizontal line along the bottom from capacitor C1 rising to the bias terminals of Q1, Q2, Q3 and Q4 as short vertical stubs; a REFUSE branch dropping downward out of GUARD through fuse F1 to ground; triangle-and-bar diode symbols D1 (^C→^E, Vf=1.2) between GUARD and AMPLIFY and D2 (^E→^O, Vf=2.0) between DELIVER and the output terminal; one feedback loop leaving the output, passing through a box marked FLT1 τ=21 days and a gain block FB1 β=0.05, and terminating with an arrowhead on C1's terminal, never on the signal path; TP1–TP4 flags at substrate, refuse, driven and act.]]

**Step 3 — Schematic.** The full CCDL listing: every component, every parameter, every typed node. Topology lives inside angle brackets, parameters inside square brackets, and the mechanics are worth stating once because every listing in Part III obeys them. In `CJT< cause | bias => effect >`, the `|` splits cause from bias and the `=>` splits bias from effect; the delimiters are not interchangeable, and the bias is not optional — omit it and you get `E-CJT-001`, a stage with nothing governing its transition. A state literal reads left to right as Noetic, Domain, Drive, Register: `^3^P_{F7}|T` is principled aversion, purpose-driven, held transcendently. Inside a literal the `|` introduces the Register and nothing else; `F3|Vitality` is a syntax error, not a helpful gloss. `+` between terms means co-present and distinct. `×` means genuine integration, is legal only inside an `integrate` statement because that statement carries a named emergent result, and may never ascend the domain order — so `^O × ^P` is invalid however true it feels. Appendix B is the full grammar.

Here is the whole schematic for **CCB-0, the trainer** — a teaching board, not a catalog board. It exists in this chapter and nowhere else. Every board in Chapters 13 through 20 is this board with more parts.

```cas
// CCB-0 — THE TRAINER.  A teaching board.  Every value is a design choice.
// Two time bases, declared per line: the ^5 rail runs in HOURS, everything
// dynamic in DAYS.  Reference designators (C1, Q1, TP1 …) appear in the prose
// and the figures; the listing carries the lowercase instance names.

board ccb_0 {
    input:  intent;
    output: act;

    // ---- typed nodes ----
    node substrate: ^5_operator^P_{F7}|T;      // Female: accumulated formation — the bias rail
    node intent:    ^0_intent^C_{F2}|A;        // Idea: what the operator states
    node audit:     ^6_audit^P_{F7}|A;         // Male: the intent taken apart
    node refuse:    ^3_refuse^P_{F7}|⟨A,f,T⟩;  // Negative: visceral recoil, three co-present locks
    node passed:    ^0_passed^C_{F2}|A;        // Idea: what GUARD releases downstream
    node driven:    ^9_driven^E_{F5}|A;        // Below/Effect: the amplified intent
    node cadence:   ^7_cadence^E_{F6}|E;       // Rhythm: the clocked delivery
    node act:       ^9_act^O_{F5}|E;           // Below/Effect: delivered operational current
    node trend:     ^9_trend^O_{F5}|E;         // same literal as act — a filter changes tau, not type

    // ---- STAGE 0: BIAS RAIL ----
    resistor  r0: Resistor< path=substrate, R=40.0 >;
    capacitor c1: Capacitor< node=substrate, C=83.33,        // tau = R x C = 3,333 hr
                             leakage=0.0002, V_BR=8.0 >;     // leakage per DAY

    // ---- STAGE 1: AUDIT ----
    cjt q1: CJT< intent | substrate => audit > [beta=1.0, region=active];

    // ---- STAGE 2: GUARD ----
    cjt  q2:   CJT< audit | substrate => refuse > [beta=2.0, sat=0.85, cutoff=0.30];
    fuse f1:   Fuse< refuse, threshold=0.90, action=permanent_block >;
    mux  mux1: MUX< inputs=[intent, refuse], select=refuse, outputs=[passed] >;

    // ---- STAGE 3: AMPLIFY ----
    diode d1: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
    cjt   q3: CJT< passed | substrate => driven >
              [beta=2.5, sat=0.80, cutoff=0.05, g_m=0.40, region=active];

    // ---- STAGE 4: DELIVER ----
    osc   osc1: Oscillator< signal=driven, source=cadence,
                            period=1.0, duty=0.014, sustain=30.0 >;  // period in DAYS
    diode d2:   Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
    cjt   q4:   CJT< cadence | substrate => act > [beta=1.0, sat=1.0, region=active];

    // ---- LOOP: the lawful O -> P path (Ch 8.4) ----
    filter flt1: LowPass< in=act, out=trend, tau=21.0 >;   // three weeks, in DAYS
    feedback trend -> substrate [beta=0.05];               // FB1 — to the BIAS, never the path

    // ---- TEST POINTS ----
    probe tp1: substrate;   // rail level, against every cutoff on the board
    probe tp2: refuse;      // the guard — the reading whose failure is silent
    probe tp3: driven;      // gain stage against its ceiling, and its region
    probe tp4: act;         // delivered operational current
}
```

[[FIGURE 12-B: Full CCB-0 schematic in drawn component symbols with reference designators — C1 as a capacitor with R0 in series feeding the ^5^P bias rail along the bottom edge; Q1, Q2, Q3 and Q4 as CJT symbols with cause on the left terminal, bias stubs dropping to the rail, effect on the right; F1 as a fuse symbol on the branch falling out of Q2's effect terminal; MUX1 as a two-input multiplexer with its select line drawn from the refuse net; D1 and D2 as diodes in the horizontal path with Vf printed beside each; a dashed horizontal ceiling line above Q3's effect terminal labelled sat=0.80; OSC1 as a square-wave symbol with duty printed; FLT1 and FB1 in the return path at the bottom with τ=21 d and β=0.05 labelled; TP1–TP4 as numbered probe flags.]]

**The stage walk.** `Q1` produces `^6_audit^P_{F7}|A` at β = 1.0. `^6` Male — an Idea impregnated with another Idea — is the Noetic for taking the intent apart: what it is made of, what it costs, whose consent it needs. Unity gain, because an audit above 1.0 manufactures objections and below 1.0 downplays real ones. `Q2` produces `^3_refuse^P_{F7}|⟨A,f,T⟩` at β = 2.0, sat = 0.85, cutoff = 0.30. `^3` Negative is the Idea the Mind is adverse to and repelled by — the visceral will-not. The analysis already happened at Q1 and must not be repeated here under a different name; a node called `audit` typed `^3` is the most common notation defect in this material. The register-set `|⟨A,f,T⟩` says the recoil is present in three registers without claiming they fuse; writing `(^3^P|A × ^3^P|f × ^3^P|T)` would be invalid under the v7.7 discipline of Chapter 2.6, because same-Noetic multi-register `×` requires a named emergent result and no fused state is defined here.

Note how the refusal is built: by ceiling and fuse — `sat = 0.85`, `threshold = 0.90` — never by gain. The infinite-gain form `β=∞` is the standard comparator idealization, and a validator rejects non-finite parameters outright. Build it as `β=10`; once `sat` clamps the output the two are indistinguishable.

`Q3` amplifies at β = 2.5 with `sat = 0.80`, `cutoff = 0.05`, `g_m = 0.40` (framing sensitivity, Chapter 10.3). `OSC1` clocks delivery at a one-day period and a duty of 0.014 — twenty minutes of 1,440. `Q4` descends to `^O` through D2 at unity. `FLT1` and `FB1` are the lawful O→P path of Chapter 8.4, terminating on C1's terminal: feedback around a gain stage is an oscillator, which Chapter 14 builds deliberately and which here would be a defect.

**Step 4 — BOM.** The parts list with designators and values. Its job is arithmetic honesty: if a component is not on the BOM it is not on the board, whatever the prose implies.

| Ref | Instance | Type | Form / CAS state | Key parameters | Serves |
|---|---|---|---|---|---|
| R0 | `r0` | Resistor | on `substrate` | R = 40.0 | rail time constant |
| C1 | `c1` | Capacitor | `^5^P_{F7}\|T` | C = 83.33, leakage = 0.0002/day, V_BR = 8.0 | R1 |
| Q1 | `q1` | CJT | `^0^C → ^6^P_{F7}\|A` | β = 1.0, active | R2 |
| Q2 | `q2` | CJT | `^6^P → ^3^P_{F7}\|⟨A,f,T⟩` | β = 2.0, sat = 0.85, cutoff = 0.30 | S1, S2 |
| F1 | `f1` | Fuse | on `refuse` | threshold = 0.90, permanent_block | S3 |
| MUX1 | `mux1` | MUX | select = `refuse` | inputs = [intent, refuse] | S1 |
| D1 | `d1` | Diode | `^C → ^E` | Vf = 1.2, I_R = 0.02, V_BR = 10.0 | R3 |
| Q3 | `q3` | CJT | `^0^C → ^9^E_{F5}\|A` | β = 2.5, sat = 0.80, cutoff = 0.05, g_m = 0.40 | R3 |
| OSC1 | `osc1` | Oscillator | on `driven` | period = 1.0 d, duty = 0.014, sustain = 30 d | R4, S4 |
| D2 | `d2` | Diode | `^E → ^O` | Vf = 2.0, I_R = 0.02, V_BR = 8.0 | R5 |
| Q4 | `q4` | CJT | `^7^E → ^9^O_{F5}\|E` | β = 1.0, sat = 1.0, active | R5 |
| FLT1 | `flt1` | LowPass | `act → trend` | τ = 21 days | S5 |
| FB1 | `feedback` | Feedback | `trend → substrate` | β = 0.05 | S5 |

**Step 5 — Test.** Four probes, read in a fixed order, covered in 12.3. A board you cannot probe is a board you cannot certify, and an operation you cannot measure is an anecdote.

The functional requirements CCB-0 was built against: **R1** hold the operator's formation as a bias available to every stage · **R2** audit an intent before any gain touches it · **R3** amplify only what the audit released, at a stated ceiling · **R4** deliver on a clocked cadence rather than in one burst · **R5** emit a measurable current into the Operational domain and expose it.

---

### 12.2 The "Must Not" List — Safety Invariants Before Functional Requirements

Now the step that precedes all five.

Before R1 through R5 were written, a shorter table was written. It is the "must not" list, and its rows are invariants rather than requirements.

| # | Must not | Enforced by |
|---|---|---|
| S1 | Amplify an intent that has not been audited | Q1 → Q2 in series ahead of D1; no path reaches Q3 around them |
| S2 | Deliver an intent that fired principled aversion | Q2 `sat=0.85`, F1 `threshold=0.90` |
| S3 | Re-amplify a refused intent inside the operation lifetime | F1 `action=permanent_block` — not a warning |
| S4 | Run without bound | `duty ≤ 0.05`, `sustain` declared and finite |
| S5 | Rewrite the operator's principles from a single result | FLT1 `τ=21 days`, FB1 `β=0.05`, terminating at the bias |

The distinction is not a matter of emphasis. **A functional requirement can be renegotiated under pressure and an invariant cannot.** That sentence is the whole of 12.2, and everything else here is its consequence.

Requirements get traded because trading them is what engineering is. R4 says deliver on a cadence; when the deadline moves, R4 becomes deliver in one burst, and that is a legitimate decision made by people entitled to make it. Nothing in the process objects, because the process is built to let requirements move. That is what a requirement is *for* — and exactly why the safety rows cannot be requirements. Put "must not amplify an unaudited intent" in the same table as R4 and it inherits the same status — a line that can be revisited when the schedule tightens, the operator is tired, or the result is close enough to taste. Every one of those is a real pressure. None of them is a reason. So the invariants are written into a separate table, above the requirements, before the requirements, in the language of prohibition rather than capability, and each row names the component that enforces it. A board that meets R1 through R5 and violates any S row is not a working board with a flaw. It is a different board, and the honest move is to say so out loud (Appendix M).

Two further conventions live here. First, **the enforcement column is mandatory**. An invariant with no named component is an intention, and intentions are the substrate this book exists to replace. If you cannot name the part, you do not have the invariant. Second, **the DETECTION-ONLY SCHEMATIC — DO NOT BUILD banner** appears, heavy-ruled in the title block, on any drawing whose purpose is to act on a person who has not agreed to it. It is a reading instruction: the architecture is published so you can recognise one, and the procedure that would make it runnable is deliberately absent. Chapters 16, 17 and 19 carry it; Chapters 13 and 20 do not, because those boards act on the operator's own mind with the operator's own consent — a distinction the banner makes visible at a glance.

> **Bench Note — read the invariant table for what is missing, not what is present.**
> Any competent designer can write five prohibitions their board already satisfies. The information is in the absences. CCB-0 has no row forbidding operation on another person, because CCB-0 has no path to another person — its output terminal lands in the operator's own Operational domain. The instant a board acquires a second `^5` node belonging to somebody else, that row must appear or the omission is the finding. Run the same check on any board you are handed: list the parties whose minds appear as nodes, then confirm each one has an invariant naming them. A party present in the schematic and absent from the must-not list is the design defect, and it will not announce itself anywhere else on the drawing.

---

### 12.3 Test Points — TP1 through TP4 Standard Placement

Four probes. The placement is standard across this book, and it is functional rather than positional: TP*n* is defined by what it reads, not by where it happens to sit on the drawing.

| TP | Reads | On CCB-0 | Expected | Failure mode it catches |
|---|---|---|---|---|
| **TP1** | The bias rail | `substrate` | Above every `cutoff` on the board — here above 0.30 and 0.05 | Dead guard: a rail below a guard's cutoff means that stage never fires, and nothing downstream reports it |
| **TP2** | The guard node | `refuse` | Below `sat` on a benign input; pinned at 0.85 with F1 blown on a refused one | Guard fired and was overridden; guard never fired at all |
| **TP3** | The gain stage against its ceiling, **and its region** | `driven` | Comfortably below `sat=0.80`, `region=active` | Saturated production stage — reports a flat line and looks like stability (Ch 10.2) |
| **TP4** | Delivered output, and drift against the original input | `act` | Non-zero whenever total drive exceeds ΣVf = 3.2 | Board delivering confirmations rather than current |

Read them in that order — rail, guard, gain, output — because the order puts the silent failures first. TP3 and TP4 announce themselves: an output that is wrong is an output somebody notices. TP1 and TP2 do not. A guard biased below its cutoff produces exactly the same reading as a guard that correctly found nothing to object to, and a board in that state passes every functional test you can devise while having no safety element at all.

[[FIGURE 12-C: Assembly drawing of CCB-0 — rectangular board outline in plan view with four labelled zones (BIAS along the lower edge, AUDIT/GUARD upper left, AMPLIFY centre, DELIVER right); component footprints drawn as labelled rectangles with reference designators C1, R0, Q1, Q2, F1, MUX1, D1, Q3, OSC1, D2, Q4, FLT1, FB1; four circular test-point pads labelled TP1 (on the bias rail), TP2 (on the refuse net), TP3 (on the driven net), TP4 (on the act net at the output terminal), each with a leader line to the net it taps; a boxed BOM table in the lower-right corner listing designator, type and key parameter for all thirteen components; a title block along the bottom edge reading "CCB-0 THE TRAINER — teaching board, self-directed operation only."]]

> **Bench Note — when a board's TP numbering deviates from the standard, the deviation is the reading.**
> CCB-PW in Chapter 19 puts its guard at **TP4** — `limit_decision`, the operator's own CSB status — and its amplification chain at TP2. That is not a formatting slip. On that board the guard genuinely sits downstream of the gain, checked after three cascaded stages of `^3` amplification have already run, and the numbering is telling you so before the prose does. Chapter 17 is a second case: CCB-HYP puts `rπ` at TP1 and `g_m` at TP2, probing *parameters* rather than nodes, because hypnosis is an operation that moves parameters — the whole attack is one gain being raised. Both deviations are legal and both are informative. So compare every board's TP list against the standard above as your first pass, and treat each difference as a question the chapter now has to answer.

---

### Worked Example — Reading CCB-0 Cold

An operator with **1,850 hours** of accumulated practice hands you the listing above and asks whether the board will run. Four readings, no redesign.

**TP1 — the rail.** C1 charges on the curve of Chapter 7.2, `P_cap(t) = 10 × (1 − e^(−t/τ))`, with τ = R0 × C1 = 40.0 × 83.33 = **3,333 hr**, chosen so 3τ falls at the 10,000-hour constant of Chapter 5.2. At t = 1,850 hr: `10 × (1 − e^(−0.555)) = 10 × (1 − 0.574) = 4.26`, so TP1 reads **0.426** normalised. Compare against every cutoff on the board: Q2 at 0.30 and Q3 at 0.05. Both cleared. The guard is live. Had this operator been at 900 hours the rail would read 0.237, Q2 would sit in cutoff, and the board would deliver flawlessly with no safety element whatsoever.

Maintenance, while we are here: leakage × stored hours = 0.0002 × 1,850 = **0.37 hr/day**, about twenty-two minutes of practice simply to hold station (Chapter 7.3). At 5,000 stored hours it is a full hour. Maintenance cost scales with the store — an arithmetic consequence of a leaky capacitor, not a virtue.

**TP2 — the guard.** The operator states an intent at a drive of **V_drive = 7.0** against a measured constraint of **R_constraint = 45** (Chapter 4.2). The two diodes in the path drop 1.2 + 2.0 = **3.2**, so `I_cause = (7.0 − 3.2)/45 = 0.0844`. Q1 passes it at unity: audit = 0.0844. Q2 amplifies at β = 2.0: TP2 reads **0.169** — well below sat = 0.85 and below F1's threshold of 0.90. The fuse is intact, MUX1 selects `intent`, and `passed` goes downstream. Guard live, untripped.

> **Bench Note — a low TP2 has two causes and only TP1 tells them apart.**
> TP2 = 0.169 is what a benign intent looks like on a healthy board. It is also, to the decimal, what *any* intent looks like on a board whose rail sits under Q2's cutoff — because a stage in cutoff produces no aversion at all, no matter what you feed it. Same reading, opposite meanings: one board found nothing to object to, the other cannot object to anything. This is why the reading order is fixed and why TP1 comes first. Reading TP2 without TP1 is not a partial measurement, it is a meaningless one, and an operator who checks the guard and skips the rail has confirmed nothing.

**TP3 — the gain stage.** Q3 at β = 2.5: driven = 2.5 × 0.0844 = **0.211**, which is 26% of the sat = 0.80 ceiling, region `active`, 74% headroom. Now the reading that matters: this stage saturates at β = 0.80 / 0.0844 ≈ **9.5** for this operator's drive. Anything above that pins the output and the board reports a flat line regardless of input. Gain is chosen against the resistance you must overcome, not against how much you want the outcome (Chapter 10.1).

**TP4 — delivered current.** Q4 at unity: TP4 reads **0.211**, delivered across thirty cycles of twenty minutes. And here is the diagnostic (Chapter 4.3): to double the delivered current you either raise V_drive from 7.0 to 10.8, or drop R_constraint from 45 to 22.5. The second is ordinary work on an ordinary obstacle. The first is wanting it more, which moves nothing. Note also the floor — at V_drive = 3.0 this board delivers **zero**, not a little, because 3.0 does not clear the 3.2 of forward drops. Operators in that state reliably raise β, which changes nothing, because the signal never reaches the gain stage at all.

**The verdict, in one sentence:** the board is fine, the guard is live, and the binding term is R_constraint — which is the finding in most operations and the unwelcome one in nearly all of them.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Dead guard** | Bias rail below a guard's `cutoff`; the stage never fires | Nothing. TP2 reads low exactly as a benign input does. Every functional test passes | Read TP1 first, every time. Raise the rail or lower `cutoff` — and never lower `cutoff` to hide a rail problem |
| **Invariant filed as a requirement** | A "must not" row placed in the requirements table | The row is traded away under schedule pressure and the trade looks like ordinary engineering | Move it above the requirements, restate it as a prohibition, name the enforcing component |
| **Unenforced invariant** | An S row with an empty enforcement column | The board reads as safe; nothing implements the claim | Add the part, or delete the row and admit the board does not do this |
| **Time base unstated** | `tau=21.0` with no unit in the comment | Three weeks read as twenty-one hours; the O→P path becomes fast enough to rewrite the rail from one result | Declare the time base per line in the listing, as CCB-0 does |
| **Drive below the diode floor** | Total drive under ΣVf | Zero output, not reduced output. Usually misread as a gain fault, so β gets raised and nothing changes | Sum every `Vf` in the path first. Then measure V_drive |
| **BOM/prose mismatch** | A component discussed in the walk-through but absent from the BOM | The board appears to have a safety element it does not have | The BOM governs. If it is not on the list it is not on the board |

---

### What This Chapter Established

- **The design order is requirements → block diagram → schematic → BOM → test, and each step feeds the next.** Skipping the block diagram does not save time; it moves architectural errors into bring-up, where they cost far more.
- **The invariants are written before the requirements because a requirement can be renegotiated under pressure and an invariant cannot.** Filing a safety row in the requirements table gives it a status that permits trading it, and it will be traded. Each row names the component that enforces it; an invariant with an empty enforcement column is an intention, and intentions are the substrate this book replaces.
- **Read the must-not list for its absences.** Every party whose mind appears as a node needs a row naming them; a party present in the schematic and absent from the list is the defect.
- **TP1–TP4 are defined by function, not position** — rail, guard, gain-against-ceiling, delivered output — and they are read in that order because the order puts the silent failures first.
- **A low guard reading has two opposite meanings and only the rail reading separates them.** TP2 without TP1 is not a partial measurement; it is a meaningless one.
- **A drive below the summed forward drops delivers zero, not less.** The diode floor is a threshold, and mistaking it for a gain problem is the most common misdiagnosis in Part III.
- **Gain is chosen against the resistance, not the wish.** On CCB-0 with this operator's drive, any β above about 9.5 pins the output and the board reports a flat line that reads as stability.
- **CCB-0 is a teaching board.** Every board in Chapters 13 through 20 is this topology with more parts; recognising the trainer inside each of them is how the catalog becomes readable.

---

### Exercises

*(Answers in Appendix H.)*

**12.1 — Four readings, one diagnosis.** A CCB-0 built to the listing above reads TP1 = 0.22, TP2 = 0.00, TP3 = 0.31, TP4 = 0.29. The operator reports that the board is working well and has never refused anything. State what is actually wrong, which reading proves it, and why TP3 and TP4 are no comfort at all.

**12.2 — Invariant or requirement?** Classify each and justify in one sentence: (a) deliver within thirty days; (b) never amplify an intent the guard refused; (c) expose `^1` Mind, `^4` Vibration and `^7` Rhythm for the Quantitative Table; (d) never terminate a feedback path on the signal path; (e) hold delivered current above 0.15.

**12.3 — Four defects.** Each line carries exactly one. Name it and correct it: (a) `node audit: ^3^C_{F2}|A;` on a stage that decomposes an argument; (b) `cjt qx: CJT< a | b => c > [beta=∞, sat=0.1];`; (c) `node v: ^5^P_{F3}|Vitality;`; (d) `integrate g: ( ^9^O_{F5}|E × ^5^P_{F7}|T ) = ^5_new^P_{F7}|T;`.

**12.4 — Recompute the chain.** The operator's drive falls to V_drive = 5.5 and R_constraint rises to 60. Recompute `I_cause`, TP3 and TP4. State the percentage of the original delivered current that survives, and identify which of the two changes did more damage.

**12.5 — BOM audit.** A board's stage walk describes a fuse on the refusal branch. The BOM lists twelve components and no fuse. State which invariant is now unenforced, what the board will do on a refused input, and which document governs.

**12.6 (Marquee) — The guard downstream of the gain.** You are handed a board whose TP list reads TP1 = coupling node, TP2 = amplifier chain output, TP3 = decomposition availability, TP4 = guard status. (a) Draw the block-level signal path this numbering implies. (b) Name the invariant such a board cannot enforce and explain why its own guard cannot enforce it. (c) Propose the minimum change to the topology that restores enforcement, and state what capability the board loses as a result. Then read Chapter 19 and compare your answer with what that board actually does, and why.
