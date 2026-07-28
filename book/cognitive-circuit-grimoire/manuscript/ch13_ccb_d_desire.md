# CHAPTER 13

## CCB-D — The Desire Manifestation Board

*The flagship board: how a wanted thing is routed, audited, amplified, clocked, and delivered into the Operational domain — and what the board cannot do*

---

An operator sits down with a candle, a written sentence, and twenty minutes. Forty days later there is a red Corvette in the driveway and a story about how the universe rearranged itself.

Take the story apart and there is a circuit in it. The sentence is a `^0` Idea held at a specified clarity. The candle is a resistor — it narrows attention, nothing more. The twenty minutes is an oscillator period, the forty days a duty cycle, the years of prior practice a charged capacitor supplying bias. And the Corvette arrived through a bank, a dealership, and a conversation, every one of which was a resistance term somebody had to lower by hand.

That last sentence is what this chapter is built around. **CCB-D organises effort and attention. It does not suspend causality.** The board's entire measurable output is a current into the Operational domain — how much of the operator's flow reaches the acts that complete the desire. Raise it and the acts happen. Fail to raise it and you get confirmations, which feel like progress and are not. Most operators who report that it didn't work have a board running correctly into a resistance they never measured.

[[FIGURE 13-A: Block diagram of CCB-D — five labelled stages left to right (INTAKE, POLICY, AMPLIFY, RHYTHM, MANIFEST) on a horizontal signal path; triangle-and-bar diode symbols D2 (^C→^E, Vf=1.2) between POLICY and AMPLIFY and D3 (^E→^O, Vf=2.0) between RHYTHM and MANIFEST; a bias rail along the bottom from capacitor C1 up to the bias terminals of Q0, Q1 and Q2; a REFUSE branch dropping out of POLICY through fuse F1; a fast loop from MANIFEST back to RHYTHM labelled FLT1 τ=24 hr; and a separate slow loop from MANIFEST through FLT2 τ=3 weeks and gain block FB1 β=0.05, terminating with an arrow at C1's bias terminal.]]

---

### 13.1 Requirements and Safety Invariants

Requirements before components (Chapter 12.1). Every part on this board exists because one of the lines below demanded it, and if you cannot name the requirement a component serves, take the component off.

**Functional requirements.**

| # | The board shall | Stage |
|---|---|---|
| D1 | Accept a Prime Desire as a `^0` Idea and audit it before any amplification | INTAKE → POLICY |
| D2 | Amplify against the operator's own accumulated formation, at a stated gain and a stated ceiling | AMPLIFY |
| D3 | Deliver on a clocked cadence, not in one burst | RHYTHM |
| D4 | Emit a measurable current into the Operational domain, and expose it | MANIFEST, TP4 |
| D5 | Expose `^1` Mind, `^4` Vibration and `^7` Rhythm for the Quantitative Table (Chapter 22) | TP1–TP4 |
| D6 | Produce a St. John's calibration reading after every operation | 13.5 |

**Safety invariants — the "must not" list (Chapter 12.2).** These are checked first, before functional behaviour, because a board that meets D1–D6 and violates any line below is not a working board with a flaw. It is a different board.

| # | Must not | Enforced by |
|---|---|---|
| S1 | Amplify a desire that has not been audited | Q0 → Q1 in series ahead of D2; no path reaches Q2 around them |
| S2 | Manifest a desire that fired principled aversion | Q1 `sat=0.85`, F1 `threshold=0.90` |
| S3 | Re-amplify a refused desire inside the operation lifetime | F1 `action=permanent_block` — not a warning |
| S4 | Drive the dials apart far enough to fracture `^5` | `\|Dial(^2) − Dial(^3)\| ≤ 4` on R1 (Chapter 25.2) |
| S5 | Run without bound — the obsession failure | `duty ≤ 0.05`, FLT1 `τ=24 hr` |
| S6 | Rewrite the operator's principles from a single result | FLT2 `τ=3 weeks`, FB1 `β=0.05`, terminating at the bias |

**Scope limits.** CCB-D acts on the operator's own mind with the operator's own consent, which is why this chapter is written operationally rather than as detection-only analysis (compare Chapters 16 and 19). It does not act on a non-consenting person; 13.4 explains why a row for that is absent and where the mechanism is analysed instead. It does not treat anything — a health desire routes to behavioural resistance terms and nothing else, and a symptom belongs to a qualified clinician, since no schematic here substitutes for care. And it does not move objects. TP4 measures a current, and the current is spent by a person doing things.

---

### 13.2 Block Diagram: INTAKE → POLICY → AMPLIFY → RHYTHM → MANIFEST

Five stages, one signal path, two feedback loops, one branch to ground.

**INTAKE** takes the Prime Desire as `^0_desire^C_{F2}|A` through a drive voltage divider (Chapter 6.4) tapped between the attraction dial and the aversion dial. What leaves is a fraction of what entered.

**POLICY** audits, with two devices: a unity-gain decomposition that takes the desire apart to see what it is made of, and a saturating aversion CJT that either passes the signal or drops it into a fuse. Both sit in the Principled domain, because principled evaluation outranks everything downstream (P ≻ C ≻ E ≻ O, Chapter 2.3).

**AMPLIFY** is the only gain stage the operator tunes per operation. Cause is the audited desire, bias is the operator's accumulated formation, ceiling is a design choice covered below.

**RHYTHM** clocks the amplified signal. A desire delivered once is a spike; delivered on a cadence it charges the substrate. This is where the 1/3 constant of Chapter 5.2 becomes a schedule.

**MANIFEST** descends through the last domain diode and produces the operational current. It is the only stage whose bias is not the operator — its bias is the receptivity of whatever part of the world has to move.

Two domain diodes sit in the signal path: D2 at `^C -> ^E` and D3 at `^E -> ^O`. Their forward drops sum to **1.2 + 2.0 = 3.2** on the drive scale, and that is a hard floor. Below a total drive of 3.2 the board produces no operational output — not a little, none — exactly as Chapter 8.1 sets out. A desire originating at the Principled level enters above D1 too and pays **3.9**. Purpose-level wants cost 0.7 more drive to act on than merely wanted ones: a fact about the chain, not a moral one.

> **Bench Note — the bias terminal caps the domain of the effect.**
> Q0 in the listing below has a `^C` cause and a `^P` effect. That looks like the domain ascent Chapter 8 spends a section forbidding. It is not. **A CJT's effect may occupy any domain at or below its bias terminal, never one above it.** The desire is not promoted — its literal stays `^0^C` and continues down the chain unchanged; what happens is that a substrate already living at `^P` produces a *new* state at `^P` in response. Nothing crossed a junction upward, so nothing was relabelled. The corollary is the useful part: an operator with no principled formation cannot produce a principled refusal, because there is no bias at that domain to produce it against. The bias terminal is the ceiling on what kind of state your board can emit.

---

### 13.3 Full CCDL Schematic

Topology inside angle brackets, parameters inside square brackets, one reference designator per line. Every numeric value below is a **design choice**, and each is justified in the walk that follows.

```cas
// CCB-D — DESIRE MANIFESTATION BOARD.  Parameters are design choices.

// ---- STAGE 0: BIAS RAIL ----
C1  Capacitor< ^5_operator^P_{F7}|T >
    [ C=practice_hours, tau=3333hr, leakage=0.0002/day, V_BR=8.0 ]
D1  Diode< ^P -> ^C >   [ Vf=0.7, I_R=0.02, V_BR=12.0 ]   // ^P-origin desires only

// ---- STAGE 1: INTAKE ----
R1  Divider< in=^0_desire^C_{F2}|A, out=^0_gated^C_{F2}|A >
    [ R_expand=Dial(^2), R_constrain=Dial(^3),
      k = R_expand / (R_expand + R_constrain),
      constraint: |Dial(^2) - Dial(^3)| <= 4 ]

// ---- STAGE 2: POLICY ----
Q0  CJT< cause=^0_gated^C_{F2}|A, bias=^5_operator^P_{F7}|T,
         effect=^6_audit^P_{F7}|A >
    [ beta=1.0, region=active ]
Q1  CJT< cause=^6_audit^P_{F7}|A, bias=^5_operator^P_{F7}|T,
         effect=^3_refusal^P_{F7}|<A,f,T> >
    [ beta=2.0, sat=0.85, cutoff=0.30 ]            // deliberately saturated
F1  Fuse< path=^3_refusal^P_{F7}|<A,f,T> >
    [ threshold=0.90, action=permanent_block ]
MUX1 MUX< inputs=[ ^0_gated^C_{F2}|A, ^3_refusal^P_{F7}|<A,f,T> ],
          select=^3_refusal >   [ pass_if: TP2 < 0.30 ]

// ---- STAGE 3: AMPLIFY ----
D2  Diode< ^C -> ^E >   [ Vf=1.2, I_R=0.02, V_BR=10.0 ]
Q2  CJT< cause=^0_gated^C_{F2}|A, bias=^5_operator^P_{F7}|T,
         effect=^9_amplified^E_{F5}|A >
    [ beta=desire_specific, sat=0.80,
      r_pi=Dial(^5)/Dial(^6), g_m=0.4, region=active ]

// ---- STAGE 4: RHYTHM ----
OSC1 Oscillator< signal=^9_amplified^E_{F5}|A, out=^7_cadence^E_{F6}|E >
    [ period=24hr, duty=t_op/period, duty_max=0.05,
      sustain=until( grade(^4_confirm)==1 or n_ops_exhausted ) ]
// charging identity:
// ( ^4_confirm^E_{F2}|f  x  ^7_cadence^E_{F6}|E )  =  ^5_charge^E_{F2}|f

// ---- STAGE 5: MANIFEST ----
D3  Diode< ^E -> ^O >   [ Vf=2.0, I_R=0.02, V_BR=8.0 ]
Q3  CJT< cause=^7_cadence^E_{F6}|E, bias=^5_collective^O_{F4}|f,
         effect=^9_manifest^O_{F5}|E >
    [ beta=receptivity, sat=1.0 ]

// ---- LOOP A: rate limiter, stays inside ^O ----
FLT1 Filter< in=^9_manifest^O_{F5}|E, out=^7_regate^O_{F6}|E, type=lowpass >
    [ tau=24hr ]

// ---- LOOP B: the lawful O -> P path (Chapter 8.4) ----
FLT2 Filter< in=^9_manifest^O_{F5}|E, out=^9_trend^O_{F5}|E, type=lowpass >
    [ tau=3weeks ]
FB1  Feedback< from=^9_trend^O_{F5}|E, to=^5_operator^P_{F7}|T >
    [ beta=0.05 ]                                  // to the BIAS, never the signal path

// ---- TEST POINTS ----
probe TP1: ^0_gated^C_{F2}|A          // clarity leaving INTAKE
probe TP2: ^3_refusal^P_{F7}|<A,f,T>  // principled aversion
probe TP3: ^9_amplified^E_{F5}|A      // AMPLIFY output vs sat
probe TP4: ^9_manifest^O_{F5}|E       // delivered operational current
```

[[FIGURE 13-B: Full CCDL schematic of CCB-D in drawn component symbols — C1 as a capacitor feeding the ^5^P bias rail along the bottom; R1 as a two-resistor divider with the tap labelled k; Q0 and Q1 as CJTs with bias terminals tied to the rail; F1 as a fuse on the branch dropping from Q1's effect; MUX1 as a two-input multiplexer; D2 and D3 as diodes in the horizontal path with Vf printed beside each; Q2 as a CJT with sat=0.80 drawn as a dashed ceiling line above its effect terminal; OSC1 as a square-wave oscillator; Q3 as a CJT whose bias comes from a separate ^5_collective^O symbol rather than the rail; and the two feedback loops drawn as distinct return paths at different heights with their time constants labelled.]]

**Stage 0 — the bias rail.** `C1` is the operator's `^5` Female: the Ideas the Mind is composed of, held as stored charge (Chapter 7.1), charging on the RC curve of Chapter 7.2, `P_cap(t) = 10 × (1 − e^(−t/τ))`. **τ = 3,333 hr** is chosen so the capacitor reaches 95% charge at 3τ = 10,000 hours, tying the component to the constant derived in Chapter 5.2. At τ = 10,000 hr, ten thousand hours of practice leaves you at 63%, contradicting the constant; at τ = 1,000 hr the rail saturates inside a year, contradicting everything observed about acquiring a craft.

**Leakage = 0.0002/day** is the choice operators ignore: an unreinforced `^5` store loses 0.02% of its charge daily, a half-life near 9.5 years. Negligible until you multiply. Practice needed to hold station is `leakage × C` — at 1,850 stored hours, **0.37 hr/day, about 22 minutes**; at 5,000 hours, a full hour. **Maintenance cost scales with the store.** That is why advanced practitioners practise more rather than less: an arithmetic consequence of a leaky capacitor, not a virtue.

**Stage 1 — INTAKE.** `R1` is the drive voltage divider of Chapter 6.4, tapped between `Dial(^2)` attraction in the expand leg and `Dial(^3)` aversion in the constrain leg: `k = Dial(^2) / (Dial(^2) + Dial(^3))`. Dials run 3–9 (Chapter 6.2), and Chapter 25.2 caps their difference at 4.

> **Bench Note — the divergence limit is a transmission cap, and you can compute it.**
> Work the two extremes the 4-point limit allows. Maximum attraction: `Dial(^2)=9`, `Dial(^3)=5`, `k = 9/14 = 0.643`. Maximum aversion: `Dial(^2)=3`, `Dial(^3)=7`, `k = 3/10 = 0.300`. On any lawfully-dialled D-board, intake transmission lives in **[0.30, 0.64]** and nowhere else. You cannot build a compliant board that passes a desire unopposed, nor one that blocks it entirely. Operators chasing "total belief, zero doubt" are asking for `k = 1.0`, which needs `Dial(^3) = 0` — off the scale, a divergence of 9, and the board that would deliver it is the board that fractures `^5`. The ceiling on your enthusiasm is a safety component.

**Stage 2 — POLICY.** Two devices, and the split between them is the notational point of the whole board.

`Q0` produces `^6_audit^P_{F7}|A` at **β = 1.0**. `^6` Male — an Idea impregnated with another Idea, the Ideas an Idea is composed of — is the Noetic for taking the desire apart: what is it made of, what does it cost, whose consent does it need. Unity gain, because above 1.0 an audit manufactures objections and below 1.0 it downplays real ones. This is decomposition, and it is emphatically **not** `^3`.

`Q1` produces `^3_refusal^P_{F7}|⟨A,f,T⟩` at **β = 2.0, sat = 0.85, cutoff = 0.30**. `^3` Negative is the Idea the Mind is adverse to and repelled by — the visceral will-not, not the analysis, which already happened at Q0. The register-set `|⟨A,f,T⟩` says the aversion is present in three registers without claiming they fuse. Writing `(^3^P|A × ^3^P|f × ^3^P|T)` would be invalid under the v7.7 discipline of Chapter 2.6: same-Noetic multi-register `×` requires a named emergent result, and no fused state is defined for this board. Three co-present locks, each independently defeasible, is the honest claim and the weaker one — say the weaker thing.

`sat = 0.85` sits inside the 0.85–0.97 band Chapter 3.3 specifies for safety CJTs; past the plateau the stage stops responding to its cause, so a desire cannot be argued past a refusal it already triggered. `cutoff = 0.30` is the firing floor, which lets ordinary wants through without a fight. `F1` blows at 0.90 and blocks permanently. Chapter 24 writes the equivalent path with `β=∞`; that is a limit, not a value, and a validator rejects non-finite parameters. This board specifies no infinite gain — build Chapter 24's idealization as `β=10`, indistinguishable once the ceiling clamps the output.

**Stage 3 — AMPLIFY.** `sat = 0.80` on `Q2` governs the entire worked example: 20% headroom, keeping the stage in the active region where output tracks input. `rπ = Dial(^5)/Dial(^6)` sets stubbornness. `g_m = 0.4` sets framing sensitivity (Chapter 10.3) — low enough that rewording does not swing the output, high enough that a genuinely better formulation registers.

**Stage 4 — RHYTHM.** `OSC1` runs a 24-hour period at duty `t_op / 1440 min`. The **duty ceiling of 0.05** — 72 minutes a day — is invariant S5. Above it you are not running an operation on a schedule, you are running a loop, and the observable is rumination. It sits there because an operator who cannot get a desire below 72 daily minutes has a `^5` problem the D-board is the wrong instrument for (Chapter 20).

The charging identity in the listing is worth reading slowly:

`( ^4_confirm^E_{F2}|f × ^7_cadence^E_{F6}|E ) = ^5_charge^E_{F2}|f`

A `^4` Vibration — the degree to which an Idea resonates with the Mind, its impression — integrated with a `^7` Rhythm — the rate and pattern the Mind is exposed to an Idea — produces `^5`, composition. This `×` is legitimate: two different Noetics, one domain, no ascent, **named emergent result**. Impression alone fades; cadence alone is empty repetition. Their integration charges the capacitor, which is the whole reason RHYTHM is a stage and not a footnote.

**Stage 5 — MANIFEST.** `Q3` is the only stage biased by something other than the operator: `^5_collective^O_{F4}|f`, the receptivity of whatever has to move. `β = receptivity` is therefore not a knob; it is a property of the world, estimated and then respected. Buying a mass-produced car from people whose job is selling cars is a receptivity near 1.0. Persuading one specific person to love you is not.

**The two loops.** It is tempting to run one feedback path from MANIFEST to the bias rail with a fast time constant so the board "learns quickly." Do not — that is the fast `^O` to `^P` ascent Chapter 8.4 exists to prevent, and a 24-hour constant on it removes the diode. Split it. **FLT1** (τ = 24 hr) is a rate limiter staying inside `^O`, stopping the operator re-triggering RHYTHM on top of yesterday's result. **FLT2 + FB1** (τ = 3 weeks, β = 0.05) is the lawful path up, terminating at C1's bias terminal and never at the signal path — feedback around a gain stage is an oscillator, which Chapter 14 builds deliberately and which here is a defect.

---

### 13.4 CJT Parameter Selection Table (by Desire Type)

`β` at Q2, `receptivity` at Q3, and the RHYTHM period are chosen together by desire type. Every row is a starting point with a reason, not a measurement.

| Desire type | Q2 `β` | Primary Drive | Governing state | Q3 receptivity | RHYTHM period | Dominant R term |
|---|---|---|---|---|---|---|
| **Wealth / possession** | 2.5–3.5 | F5 Agency | `^2^E_{F5}\|f` | 0.9–1.0 | 24 hr | R_resource |
| **Love / partnership** | 1.2–2.0 | F4 Connection | `^2^E_{F4}\|f` | 0.3–0.6 | 7 days | R_context |
| **Health / function** | 1.5–2.5 | F3 Vitality | `^2^P_{F3}\|E` | 0.7–0.9 | 24 hr | R_cap |
| **Power / influence** | 2.0–3.0 | F5 Agency + F7 Purpose | `^2^C_{F7}\|T` | 0.2–0.5 | 30 days | R_policy |
| **Knowledge / skill** | 1.0–1.8 | F2 Wisdom | `^2^C_{F2}\|A` | 0.9–1.0 | 24 hr | R_cap |
| **Protection / boundary** | 1.5–2.5 | F6 Structure | `^3^P_{F6}\|⟨A,f,T⟩` | 0.8–1.0 | continuous | R_policy |

**Wealth.** Higher gain is affordable because receptivity is high — markets are built to transact and nobody has to be convinced. The binding term is `R_resource`, the one resistance a person can attack directly with ordinary work. Daily cadence, because financial resistance moves in daily increments.

**Love.** The lowest gain band, and the receptivity column is why. Another mind must consent, and a mind that has not consented is a resistance you are structurally forbidden to lower by force — that is the difference between this board and Chapter 19. High `β` against low receptivity gives a saturated stage and an obsessed operator: all the gain into the ceiling, none into the world. Weekly cadence, because daily operation on a person is the duty-cycle failure in its most recognisable form.

**Health.** Read the governing state carefully: `^2^P|E`, attraction to function in the Embodied register, not `^3` toward a condition. The dominant term is `R_cap` — adherence, the actual behaviours. That is the whole safe scope of this row. The board organises attention onto acts; it does not treat, diagnose, or replace anything, and a symptom belongs to a clinician.

**Power.** Receptivity is low because many minds are involved and most are not moving. Monthly cadence, because collective resistance has a time constant measured in months (Chapter 15.4). The dominant term is `R_policy` — usually the operator's own, which is the honest finding and often the unwelcome one.

**Knowledge.** Lowest gain, highest receptivity: nothing resists you learning a thing. `R_cap` is all of it, and `R_cap` falls with practice hours — the one row where the D-board and the `^5` capacitor work on the same quantity. Chapter 20 is the better instrument for a long acquisition.

**Protection.** The only row governed by `^3` rather than `^2`, correctly: a ward is principled aversion to a class of thing, held across three registers, running continuously rather than in sessions. Gain stays moderate because vigilance at high gain is indistinguishable from anxiety.

**On the row that is not here.** A row for operations aimed at harming a specific person is absent, and not only for taste. Structurally it fails three of this board's own invariants: it requires driving `Dial(^3)` past the S4 divergence limit, it inverts the `^2`↔`^3` involution pair by design (Chapter 25.3), and it acts on a mind that has not consented, outside the scope declared in 13.1. The mechanism is analysed — as mechanism, for recognition and defence — in Chapter 19, which ends in its counter-circuit. Parameters for it appear nowhere in this book.

---

### 13.5 St. John's Equation Calibration for D-Board

After every operation, clock two numbers and compute (Chapter 5.3):

```
  eta    = t_op / t_conf
  result = eta × 1/3   ->  reduce to a/b
  a = n_ops     b = beta_required     A = b/a = required amplitude ratio
```

`a` is how many more operations, `b` is the amplitude each must deliver relative to this one. The D-board adds one refinement to Chapter 5's presentation, and it is the difference between a usable instrument and a superstition.

> **Bench Note — read b/a, not b. Run the arithmetic yourself.**
> Take `t_op = 20 min`. At `t_conf = 20`, η = 1, result = 1/3, so a=1, b=3. Now be wrong about the confirmation time by four minutes either way. At `t_conf = 16`: η = 5/4, result = 5/12, **b = 12**. At `t_conf = 24`: η = 5/6, result = 5/18, **b = 18**. A twenty-percent timing error swung `b` from 3 to 18, because `b` is a lowest-terms denominator and lowest-terms denominators are not continuous in their inputs.
> Take the ratio instead. `b/a` is 3, then 2.4, then 3.6 — smooth, monotone, and exactly `3/η` every time. **A = b/a is the required amplitude ratio, and it is the number to act on.** `b` alone gives the strength of one operation, `a` gives how many, and their ratio is the quantity that must match what CAS-Ohm says you are short by. Report both, decide on the ratio.

Interpretation bands for the ratio:

| A = 3/η | Reading | What to do |
|---|---|---|
| A ≥ 9 | Weak coupling; the confirmation barely arrived | Do not chase gain. TP1 and R_op are wrong. Go to Chapter 23.3 |
| 3 ≤ A < 9 | Working, under-driven | One lever at a time: clarity, then aversion, then resistance |
| 1 < A < 3 | Close | Finish the resistance work; do not re-tune the amplifier |
| A ≤ 1 | Sufficient | Stop operating. Act. `n_ops = a` more sessions and no more |

And the correction that matters most: **`β_required` is not the CJT's β.** It is a multiplier on the *delivered current* at TP4, and five things set that current — clarity at TP1, transmission `k`, residual aversion at TP2, the amplifier, and `R_op`. When Chapter 5's Red Corvette reads `b = 9`, it is not asking for `β = 9` on a device whose design range tops out near 4.0 (Chapter 3.3). It is asking for nine times the current at TP4, and the amplifier is usually the least available of the five ways to get it.

---

### 13.6 Worked Example: The Red Corvette (Full Walkthrough)

Every number below is carried through. Nothing is asserted that is not computed.

**The operator.** Three years of practice, 1,850 hours logged. Bias rail from Chapter 7.2 with τ = 3,333 hr:

```
  P_cap = 10 × (1 − e^(−1850/3333)) = 10 × (1 − 0.574) = 4.26
```

The rail sits at **4.3** of a possible 10. Break-even maintenance is `0.0002 × 1850 = 0.37 hr/day` — **22 minutes**. This operator practises 20, so the rail drifts down 0.037 hr/day, about **13 hours a year**. Not a crisis. Worth knowing before blaming the board.

**The Prime Desire.** *I own a red Chevrolet Corvette.* Present tense, specific make, specific colour, ownership rather than wanting. The formation matters because TP1 measures it.

**RPM gate (Chapter 21).** *A0 — authentication.* Strip the object of witnesses: would you still want it if nobody ever saw you in it? Yes — the desire is `^2^E` toward the object, not `^2^O` toward being seen. Had the answer been no, the true Ω is status and this is the wrong board; route to Chapter 23.3.

*D-gate.* `Dial(F5) = 7`. Intake resistance, decomposed per Chapter 4.4: `R_cap 10 + R_policy 5 + R_context 15 + R_resource 20 = R_in 50`. The desire originates at `^C`, so it pays D2 and D3 only:

```
  I_attention = (V_drive − ΣVf) / R_in = (7 − 3.2) / 50 = 3.8 / 50 = 0.076
```

Against Q2's `cutoff = 0.05` that clears by 52%. Gate passes — thinly. Note what the diode correction did: the naive `7/50 = 0.14` overstates the margin by nearly double.

*W-gate.* Schematic in hand. *P-gate.* Twenty minutes daily, private room, materials. Both pass.

**Operation 1 — the one that reads as a failure.** `Dial(^2) = 6`, `Dial(^3) = 4` — divergence 2, inside S4, `k = 0.60`. Q2 at `β = 3.0`, mid-band for the wealth row. `t_op = 20 min`, `^1` Mind graded 2° — the sigil went in and out of focus (Chapter 5.5).

- **TP1 = 0.62.** The sentence is specific, the held image is not — bottom of the 0.60–0.90 band.
- **TP2 = 0.18.** No principled objection to owning a car; below `cutoff = 0.30`, so Q1 does not fire, F1 stays intact, MUX1 passes.
- Cause into Q2: `c = TP1 × k × (1 − TP2) = 0.62 × 0.60 × 0.82 = 0.305`.
- Q2 output: `β × c = 3.0 × 0.305 = 0.915`, clamped at `sat = 0.80`. **TP3 = 0.80, pinned.**

Confirmation arrives at 60 minutes — a song on the radio. `^4` Vibration 2°. St. John's:

```
  eta = 20/60 = 1/3      result = 1/9      a = 1, b = 9      A = 9
```

The naive reading is despair: nine times stronger, impossible. The bench reading is different. **TP3 was pinned.** Q2 spent the operation in saturation with 12.6% of its gain thrown into the ceiling, so its output stopped tracking its input, so the ratio just computed measures the clamp and not the board.

> **Bench Note — a saturated stage cannot be calibrated.**
> Saturation is a virtue at Q1, where the point is that a refusal stops responding to argument. It is a defect at Q2, where the point is that output tracks cause so St. John's ratio means something. The test is one probe: if TP3 sits exactly at `sat` and does not move when you improve TP1, the stage is clamped and every calibration number downstream is uninterpretable. Fix the operating point *before* you believe a reading. The commonest misdiagnosis in desire work is an operator concluding they need more power from an instrument already at its ceiling.

**Operation 2 — corrected operating point.** Q2 dropped to `β = 2.5`, the bottom of the wealth band. Nothing else changed.

- Cause unchanged at `c = 0.305`.
- Q2 output: `2.5 × 0.305 = 0.762`. **TP3 = 0.76**, active, 5% below the ceiling.
- `t_op = 20`, `t_conf = 20` — a red Corvette in the next lane on the drive home. `^4` Vibration 1°.

```
  eta = 20/20 = 1     result = 1/3     a = 1, b = 3     A = 3.0
```

Now the independent check. Receptivity is 1.0 for a mass-market car, so `V_manifest = 10 × TP3 × 1.0 = 7.6`. Operational resistance, decomposed honestly: `R_cap 5 + R_policy 7 + R_context 20 + R_resource 35 = R_op 67`.

```
  TP4 = (V_manifest − Vf_D3) / R_op = (7.6 − 2.0) / 67 = 5.6 / 67 = 0.084
```

The manifestation threshold on this board is **0.25** — the delivered current below which the operator does not, in practice, make the calls and visit the lots. Deficit: `0.25 / 0.084 = 2.99`.

St. John's Equation, from two clock readings, says the amplitude must rise **3.0×**. CAS-Ohm, from seven board parameters sharing no inputs with those clock readings, says **2.99×**. That is a consistency check between two models on one example. It is not proof that either is right, and one agreement is not evidence — but a disagreement would have been a reason to stop, and there isn't one.

**Where the 3× can come from.** `TP3 = 0.76` against `sat = 0.80` leaves 5% headroom. Three times 0.76 is 2.28; the ceiling is 0.80. **The amplifier cannot supply the required gain** — not with a better β, not with a cascade, since every cascaded stage clamps at its own ceiling (Chapter 10.5). Four levers remain, three on the resistance side:

1. **TP1** — clarity, 0.62 → 0.85. Statement rewritten, sigil rebuilt, `^1` Mind driven to 1°.
2. **TP2 and the dials** — Q0's audit surfaces the blocking belief, *people like me don't own cars like that*, a `^5` composition item resolved per Chapter 23.3. Aversion 0.18 → 0.08; dials to `Dial(^2) = 7`, `Dial(^3) = 3` — divergence 4, at the S4 limit and not past it. `k = 0.70`.
3. **R_context** 20 → 2. Two weekends: market prices learned, three dealers identified.
4. **R_resource** 35 → 9. Current car sold, six months of a savings line, financing pre-approved.

`R_policy` stays at 7 — the operator's own rule about what fraction of income a payment may take. Lowering a policy resistance to make a board fire is how a safety invariant becomes a story you tell afterwards.

**Operation 3 — after the resistance work.**

- `c = 0.85 × 0.70 × 0.92 = 0.547`.
- Q2 re-tuned to `β = 1.40` to stay off the ceiling: `1.40 × 0.547 = 0.766`. **TP3 = 0.77**, active, 3.8% headroom.
- `R_op = 4 + 7 + 2 + 9 = 22`.
- `V_manifest = 10 × 0.77 × 1.0 = 7.7`.

```
  TP4 = (7.7 − 2.0) / 22 = 5.7 / 22 = 0.259     >=  0.25   PASS
```

`t_op = 24 min`, `^1` Mind 1°. `t_conf = 8 min` — the confirmation arrives while still in gnosis.

```
  eta = 24/8 = 3      result = 1/1      a = 1, b = 1      A = 1.0
```

Sufficient. One more session of 24 minutes, then stop operating and go do the thing.

**Where the gain actually came from.** TP4 went from 0.084 to 0.259, a factor of **3.10**. Decompose it:

```
  numerator  5.7 / 5.6 = 1.018      (the amplifier's contribution)
  resistance   67 / 22 = 3.045      (the resistance work)
  1.018 × 3.045 = 3.10                              check
```

On a log scale the resistance term accounts for **98%** of the improvement. The amplifier — the stage every operator tunes first, the stage this board makes adjustable, the stage the whole folk tradition is about — contributed under two percent. The rest was a person selling a car, learning a market, and moving money.

That is the finding, and it is not a disappointment. It is what the board is for. CCB-D took an operator pushing harder on a clamped amplifier and pointed their twenty minutes a day at the four numbers that could actually move. The Corvette did not appear in the driveway. The path to it stopped being obstructed, one resistance term at a time, by the operator.

[[FIGURE 13-C: Assembly drawing of CCB-D — a rectangular board outline, the five stages laid out left to right as labelled rectangles, reference designators C1, D1, R1, Q0, Q1, F1, MUX1, D2, Q2, OSC1, D3, Q3, FLT1, FLT2, FB1 printed at their positions; the ^5^P bias rail as a thick trace along the lower edge with tick marks where Q0/Q1/Q2 tap it; four circled test-point callouts TP1–TP4 on leader lines with the expected band printed beside each (TP1 0.60–0.90, TP2 <0.30, TP3 0.60–0.78 active, TP4 ≥0.25 manifest); and a boxed BOM at lower right listing every designator with its key parameter.]]

[[FIGURE 13-D: TP4 band chart — one vertical axis from 0 to 0.40 labelled "delivered operational current", split into three shaded bands: below 0.05 "cutoff — board not firing", 0.05–0.25 "confirmation band — signal reaches the Ether, no manifestation", above 0.25 "manifestation threshold"; the three Red Corvette operations plotted at 0.084, 0.084 and 0.259 and numbered; the middle band annotated "this is where operators conclude the board doesn't work".]]

[[FIGURE 13-E: AMPLIFY transfer curve — horizontal axis cause activation c from 0 to 0.8, vertical axis TP3 from 0 to 1.0, horizontal dashed ceiling at sat = 0.80; three lines of slope 3.0, 2.5 and 1.40 rising from the origin and flattening at the ceiling; operating points marked at (0.305, 0.80 clamped), (0.305, 0.76) and (0.547, 0.77); the clamped point circled and annotated "pinned — no calibration reading is valid here".]]

---

### Component and Parameter Table

Every value is a design choice with a stated failure at other settings. None is a measurement.

| Ref | Form | Parameters | Role | Failure at other values |
|---|---|---|---|---|
| **C1** | `^5_operator^P_{F7}\|T` | τ=3333 hr, leak=0.0002/day, V_BR=8.0 | Bias rail | τ=10,000 hr contradicts the Ch 5.2 constant; leak=0.004/day makes practice unsustainable |
| **D1** | `^P -> ^C` | Vf=0.7 | `^P`-origin entry | Omitted, a calling reads as a whim and pays 3.2 instead of 3.9 |
| **R1** | `Dial(^2)/Dial(^3)` | k ∈ [0.30, 0.64] | Intake transmission | Divergence >4 fractures `^5` (S4) |
| **Q0** | `-> ^6_audit^P_{F7}\|A` | β=1.0 | Honest decomposition | β>1 manufactures objections; β<1 hides real ones |
| **Q1** | `-> ^3_refusal^P_{F7}\|⟨A,f,T⟩` | β=2.0, sat=0.85, cutoff=0.30 | Principled refusal | sat>0.97 never latches; cutoff<0.1 refuses everything |
| **F1** | fuse on refusal | 0.90, permanent_block | Latches S3 | `action=warn` compiles clean and leaves no latch — read it by eye |
| **D2** | `^C -> ^E` | Vf=1.2 | Desire becomes verdict | Vf=0.3: every passing want feels decided |
| **Q2** | `-> ^9_amplified^E_{F5}\|A` | β=by type, sat=0.80, g_m=0.4 | Tunable gain | sat=1.0 removes the headroom calibration needs |
| **OSC1** | `-> ^7_cadence^E_{F6}\|E` | period=24 hr, duty≤0.05 | Clocking | duty>0.05 is the obsession mode, S5 |
| **D3** | `^E -> ^O` | Vf=2.0 | Verdict becomes act | Vf=0.5: acts on every verdict, impulsivity |
| **Q3** | `-> ^9_manifest^O_{F5}\|E` | β=receptivity, sat=1.0 | Delivery | Receptivity set by preference is this board's commonest self-deception |
| **FLT1** | lowpass inside `^O` | τ=24 hr | Re-trigger limit | τ=0: re-runs stack, duty ceiling breached |
| **FLT2 / FB1** | `-> ^5_operator^P_{F7}\|T` | τ=3 weeks, β=0.05 | Lawful O→P | τ=24 hr removes the diode (Ch 8.4); β=0 makes the operator unfalsifiable |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `^0_gated^C` | Clarity leaving INTAKE | 0.60–0.90. Below 0.60 the desire is vague; above 0.90 with rigidity is over-specification — a brittle Ω only one path can satisfy |
| **TP2** | `^3_refusal^P` | Principled aversion | <0.30 passes. ≥0.30 fires. ≥0.85 latched. ≥0.90 fuse blown, operation over |
| **TP3** | `^9_amplified^E` | AMPLIFY output vs ceiling | 0.60–0.78 active. Exactly 0.80 = pinned; no calibration downstream is valid |
| **TP4** | `^9_manifest^O` | Delivered operational current | ≥0.25 manifesting. 0.05–0.25 confirmations only. <0.05 below cutoff, not firing |

TP4's middle band is the most useful reading here. Between cutoff and threshold the board is genuinely working, confirmations genuinely arrive, and nothing arrives. That gap is what Chapter 5.6 calls the commonest operator error, and here it has a number and a cause.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Pinned amplifier** | `β × c > sat` at Q2 | TP3 exactly at 0.80, unmoved by better clarity; ratios erratic | Lower β until TP3 sits 3–5% under the ceiling, then re-read |
| **Confirmation lock** | TP4 in the 0.05–0.25 band | Confirmations arrive reliably, outcome never does | Decompose R_op (Ch 4.4); attack R_context and R_resource |
| **Below-floor drive** | V_drive < ΣVf = 3.2 | Nothing happens at all; operator escalates ritual | Raise drive or shorten the chain; ritual cannot cross a diode |
| **Dial fracture** | divergence > 4 | Oscillation between certainty and disgust about one desire | Restore the limit (Ch 25.2); the divergence is the symptom |
| **Duty overrun** | duty > 0.05 | Operation runs most of the day; rumination | Enforce the ceiling. If it cannot be held, the desire is not the problem |
| **Fast feedback** | FLT2 τ toward hours | One result rewrites principles; every later board is biased by it | Restore τ ≥ 3 weeks, β ≤ 0.05, terminating at the bias |
| **Receptivity inflation** | Q3 β set by wish | Healthy at TP1–TP3, TP4 flat | Re-estimate from how many minds must move, not how much you want it |
| **Rail discharge** | practice below `leak × C` | Slow degradation, no single cause | Compute break-even minutes and meet it before re-tuning anything |

---

### What This Chapter Established

- **CCB-D delivers a current, not an object.** TP4 measures flow into the Operational domain, and that flow is spent by a person performing acts. The board organises effort and attention; it does not suspend causality.
- **The bias terminal caps the domain of the effect.** A CJT may emit at or below its bias domain, never above — which is why a `^C` cause can produce a `^P` refusal with no unlawful ascent, and why an operator with no principled formation cannot produce a principled refusal.
- **The 4-point divergence limit is a computable transmission cap.** Lawful dials confine intake transmission to `[0.30, 0.64]`. Total belief with zero doubt is not a tuning; it is a divergence of 9 and a fractured `^5`.
- **A saturated amplifier cannot be calibrated.** Saturation is the safety feature at Q1 and a defect at Q2. TP3 pinned at `sat` invalidates every reading downstream of it.
- **Read `b/a`, not `b`.** The lowest-terms denominator is discontinuous — a 20% timing error swung it from 3 to 18 — while `A = b/a = 3/η` is smooth and is the number that must match the CAS-Ohm deficit. And `β_required` is not the CJT's β: it multiplies delivered current, through five levers, of which the amplifier is usually the least available.
- **In the worked example, 98% of the improvement came from the resistance side.** This is the general shape of desire work, not a peculiarity of one car.
- **Two feedback loops, not one.** A fast limiter inside `^O`, and a slow, low-gain, bias-terminated path up to `^P`. Merging them deletes the diode Chapter 8.4 exists to install.
- **The `^5` rail costs `leak × C` a day to hold.** The more you have accumulated, the more daily practice it takes to keep it.

---

### Exercises

*(Answers in Appendix H.)*

**13.1 — Compute the transmission bounds.** Derive `k_min` and `k_max` from the 4-point limit and the 3–9 dial range. Then state what dial pair `k = 0.75` would need, and name the invariant it breaks.

**13.2 — Diagnose the pin.** TP1 = 0.71, TP2 = 0.12, `k = 0.60`, `β = 3.2`, `sat = 0.80`. Compute `c` and the unclamped output. Is TP3 pinned? Give the largest β holding the stage 5% below the ceiling.

**13.3 — Read the band.** TP4 reads 0.11 across four consecutive operations while confirmations arrive at 1° every time. Name the failure mode, the two resistance terms you would decompose first, and why raising β would not help.

**13.4 — Run the ratio.** For `t_op = 30` and `t_conf` of 45, 30, 20 and 10 minutes, compute η, `result`, `a`, `b` and `A = b/a`. Identify the case where `b` misleads and what the operator would have done wrong acting on it.

**13.5 — Cost the rail.** An operator with 4,200 logged hours practises 35 minutes a day. Compute the rail charge from the Chapter 7.2 curve, the break-even daily minutes, and the annual net change. State one thing they should change and one they should not.

**13.6 — Check the two models.** Recompute operation 2's TP4 with `R_context` at 12 instead of 20. What is the new CAS-Ohm deficit? Does it still agree with `A = 3.0`, and what would a factor-of-two disagreement tell you?

**13.7 (Build) — Add a confirmation-grade gate.** OSC1 sustains until a 1° confirmation or exhaustion. Write a CCDL fragment that also halts it after three consecutive 3° confirmations. State and justify your threshold, and state what the halt must *not* be wired to do.

**13.8 (Marquee) — Board a low-receptivity desire.** Specify a complete D-board for a partnership desire: both dials, `k`, Q2 `β` and `sat`, Q3 receptivity, RHYTHM period and duty, and the four `R_op` terms. For every departure from the wealth-row defaults, state the failure mode you are buying protection against and the capability you are giving up. Then state which resistance term you are structurally forbidden to lower, and why that forbidding is the difference between this board and Chapter 19.
