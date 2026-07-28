# CHAPTER 13

## CCB-D — The Desire Manifestation Board

*The flagship board: how a wanted thing is routed, audited, amplified, clocked, and delivered into the Operational domain — and what the board cannot do*

---

An operator sits down with a candle, a written sentence, and twenty minutes. Forty days later there is a red Corvette in the driveway and a story about how the universe rearranged itself.

Take the story apart and there is a circuit in it. The sentence is a `^0` Idea held at a specified clarity. The candle is a resistor — it narrows attention, nothing more. The twenty minutes is an oscillator period, the forty days a duty cycle, the years of prior practice a charged capacitor supplying bias. And the Corvette arrived through a bank, a dealership, and a conversation, every one of which was a resistance term somebody had to lower by hand.

That last sentence is what this chapter is built around. **CCB-D organises effort and attention. It does not suspend causality.** The board's entire measurable output is a current into the Operational domain — how much of the operator's flow reaches the acts that complete the desire. Raise it and the acts happen. Fail to raise it and you get confirmations, which feel like progress and are not. Most operators who report that it didn't work have a board running correctly into a resistance they never measured.

[[FIGURE 13-A: Block diagram of CCB-D — five labelled stages left to right (INTAKE, POLICY, AMPLIFY, RHYTHM, MANIFEST) on one horizontal signal path; diode symbols D2 (^C→^E, Vf=1.2) between POLICY and AMPLIFY and D3 (^E→^O, Vf=2.0) between RHYTHM and MANIFEST; a bias rail along the bottom from capacitor C1 to the bias terminals of Q0, Q1 and Q2; a REFUSE branch dropping out of POLICY through fuse F1; a fast loop from MANIFEST back to RHYTHM labelled FLT1 τ=24 hr; a separate slow loop from MANIFEST through FLT2 τ=3 weeks and gain block FB1 β=0.05, arrowed into C1's bias terminal.]]

---

### 13.1 Requirements and Safety Invariants

Requirements before components (Chapter 12.1). If you cannot name the requirement a component serves, take it off.

| # | The board shall | Stage |
|---|---|---|
| D1 | Accept a Prime Desire as a `^0` Idea and audit it before amplifying | INTAKE → POLICY |
| D2 | Amplify against the operator's accumulated formation, at a stated gain and ceiling | AMPLIFY |
| D3 | Deliver on a clocked cadence, not in one burst | RHYTHM |
| D4 | Emit a measurable current into the Operational domain, and expose it | MANIFEST, TP4 |
| D5 | Expose `^1` Mind, `^4` Vibration and `^7` Rhythm for the Quantitative Table (Ch 22) | TP1–TP4 |
| D6 | Produce a St. John's calibration reading after every operation | 13.5 |

**Safety invariants — the "must not" list (Chapter 12.2).** Checked before functional behaviour, because a board that meets D1–D6 and violates any line below is not a working board with a flaw. It is a different board.

| # | Must not | Enforced by |
|---|---|---|
| S1 | Amplify a desire that has not been audited | Q0 → Q1 in series ahead of D2; no path reaches Q2 around them |
| S2 | Manifest a desire that fired principled aversion | Q1 `sat=0.85`, F1 `threshold=0.90` |
| S3 | Re-amplify a refused desire inside the operation lifetime | F1 `action=permanent_block` — not a warning |
| S4 | Drive the dials apart far enough to fracture `^5` | `\|Dial(^2) − Dial(^3)\| ≤ 4` on R1 (Chapter 6.2) |
| S5 | Run without bound — the obsession failure | `duty ≤ 0.05`, FLT1 `τ=24 hr` |
| S6 | Rewrite the operator's principles from a single result | FLT2 `τ=3 weeks`, FB1 `β=0.05`, terminating at the bias |

**Scope limits.** CCB-D acts on the operator's own mind with their own consent, which is why this chapter is written operationally rather than as detection-only analysis (compare Chapters 16 and 19). It does not act on a non-consenting person; 13.4 explains why a row for that is absent. It does not treat anything — a health desire routes to behavioural resistance terms and nothing else, and a symptom belongs to a qualified clinician, since no schematic here substitutes for care. And it does not move objects: TP4 measures a current, spent by a person doing things.

---

### 13.2 Block Diagram: INTAKE → POLICY → AMPLIFY → RHYTHM → MANIFEST

Five stages, one signal path, two feedback loops, one branch to ground.

**INTAKE** takes the Prime Desire as `^0^C_{F2}|A` through a drive voltage divider (Chapter 6.4) tapped between the attraction and aversion dials. What leaves is a fraction of what entered.

**POLICY** audits with two devices: a unity-gain decomposition that takes the desire apart, and a saturating aversion CJT that either passes the signal or drops it into a fuse. Both sit in the Principled domain, because principled evaluation outranks everything downstream (P ≻ C ≻ E ≻ O, Chapter 2.3).

**AMPLIFY** is the only gain stage tuned per operation. Cause is the audited desire, bias the operator's accumulated formation.

**RHYTHM** clocks the amplified signal. A desire delivered once is a spike; delivered on a cadence it charges the substrate.

**MANIFEST** descends through the last domain diode and produces the operational current. It is the only stage whose bias is not the operator, but the receptivity of whatever part of the world has to move.

Two domain diodes sit in the signal path: D2 at `^C -> ^E` and D3 at `^E -> ^O`. Their forward drops sum to **1.2 + 2.0 = 3.2** on the drive scale, a hard floor. Below a total drive of 3.2 the board produces no operational output — not a little, none — exactly as Chapter 8.1 sets out. A desire originating at the Principled level enters above D1 too and pays **3.9**: purpose-level wants cost 0.7 more drive to act on than merely wanted ones, a fact about the chain and not a moral one.

> **Bench Note — the bias terminal caps the domain of the effect.**
> Q0 below has a `^C` cause and a `^P` effect. That looks like the domain ascent Chapter 8 forbids. It is not. A CJT obeys two domain rules, and they point in opposite directions. **The bias must sit at or above the cause** (Chapter 3.2 — a lower-domain bias is `E-CJT-008`, the prompt-injection signature). **The effect may sit at or below the bias, never above it.** Q0 satisfies both: cause `^C`, bias `^P`, effect `^P`. The desire is not promoted — its literal stays `^0^C` the whole way down; a substrate already living at `^P` produces a *new* state at `^P` in response. Nothing crossed a junction upward, so nothing was relabelled. The corollary is the useful part: an operator with no principled formation cannot produce a principled refusal, because there is no bias at that domain to produce it against.

---

### 13.3 Full CCDL Schematic

Topology inside angle brackets, parameters inside square brackets. Every numeric value is a **design choice**, justified in the walk that follows.

```cas
// CCB-D — DESIRE MANIFESTATION BOARD.  Every value is a design choice.
// Time bases per line: the ^5 rail in HOURS, everything dynamic in DAYS.
// Instance labels read ^n_name^D_{Fk}|R — strip the label for the literal.

board ccb_d {
    input:  desire;
    output: manifest;

    // ---- typed nodes ----
    node substrate:   ^5_operator^P_{F7}|T;      // Female: accumulated formation, the bias rail
    node desire:      ^0_desire^C_{F2}|A;        // Idea: the Prime Desire as formed
    node attraction:  ^2^C_{F2}|f;               // Positive: the divider's expand leg
    node aversion:    ^3^C_{F2}|f;               // Negative: constrain leg, visceral not analytic
    node gated:       ^0_gated^C_{F2}|A;         // Idea: what survives INTAKE
    node audit:       ^6_audit^P_{F7}|A;         // Male: the desire taken apart
    node refusal:     ^3_refusal^P_{F7}|⟨A,f,T⟩; // Negative: three co-present locks
    node passed:      ^0_passed^C_{F2}|A;        // Idea: what POLICY releases
    node amplified:   ^9_amplified^E_{F5}|A;     // Below/Effect: the amplified want
    node confirm:     ^4_confirm^E_{F2}|f;       // Vibration: the confirmation's impression
    node cadence:     ^7_cadence^E_{F6}|E;       // Rhythm: the clocked delivery
    node charge:      ^5_charge^E_{F2}|f;        // Female: what the cadence deposits
    node receptivity: ^5_collective^E_{F4}|f;    // Female: disposition of the minds that must move
    node manifest:    ^9_manifest^O_{F5}|E;      // Below/Effect: delivered operational current
    node regate:      ^7_regate^O_{F6}|E;        // Rhythm: the rate limit, inside ^O
    node trend:       ^9_trend^O_{F5}|E;         // manifest's literal — a filter changes tau, not type

    // ---- STAGE 0: BIAS RAIL ----
    resistor  r0: Resistor< path=substrate, R=40.0 >;               // Ohm_c
    capacitor c1: Capacitor< node=substrate, C=83.33,               // tau = R x C = 3,333 hr
                             leakage=0.0002, V_BR=8.0 >;            // leakage per DAY
    diode     d1: Diode< ^P -> ^C > [Vf=0.7, I_R=0.02, V_BR=12.0];  // ^P-origin desires only

    // ---- STAGE 1: INTAKE ----
    dial       d_pos: ^2 [dial=6];
    dial       d_neg: ^3 [dial=4];
    constraint dial_spread in [0, 4];                     // S4 — Chapter 6.2
    resistor   r1a: Resistor< path=attraction, R=60.0 >;  // 10 x Dial(^2)
    resistor   r1b: Resistor< path=aversion,   R=40.0 >;  // 10 x Dial(^3)
    divider    r1:  Divider< source=desire, expand=attraction,
                             constrain=aversion, tap=gated >;   // k = 6/(6+4) = 0.600

    // ---- STAGE 2: POLICY ----
    cjt  q0:   CJT< gated | substrate => audit >   [beta=1.0, region=active];
    cjt  q1:   CJT< audit | substrate => refusal > [beta=2.0, sat=0.85, cutoff=0.30];
    fuse f1:   Fuse< refusal, threshold=0.90, action=permanent_block >;
    mux  mux1: MUX< inputs=[gated, refusal], select=refusal, outputs=[passed] >;
                                      // selects refusal once TP2 reaches q1's cutoff

    // ---- STAGE 3: AMPLIFY ----
    diode d2: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
    cjt   q2: CJT< passed | substrate => amplified >
              [beta=2.5, sat=0.80, cutoff=0.05, g_m=0.40, r_pi=1.50, region=active];
              // beta by desire type (13.4); 2.5 = wealth row.  r_pi = Dial(^5)/Dial(^6)

    // ---- STAGE 4: RHYTHM ----
    osc osc1: Oscillator< signal=amplified, source=cadence,
                          period=1.0, duty=0.014, sustain=40.0 >;
              // period in DAYS; duty = 20/1440 min; ceiling 0.05 = 72 min (S5)
              // sustain in DAYS — the window; n_ops from 13.5 sets it
    monitor m_conf: confirm;                     // ^4 grade, logged per operation (Ch 22)
    on m_conf { alert "1-degree confirmation — stop operating and act"; }
    integrate rh1: ( confirm × cadence ) = charge;   // ^4 x ^7 = ^5, named emergent result

    // ---- STAGE 5: MANIFEST ----
    diode d3: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
    cjt   q3: CJT< cadence | receptivity => manifest > [beta=1.0, sat=1.0, region=active];
              // beta = receptivity (13.4); 1.0 = mass-market car
              // the bias is ^E and never ^O — see the Stage 5 walk

    // ---- LOOP A: rate limiter, stays inside ^O ----
    filter flt1: LowPass< in=manifest, out=regate, tau=1.0 >;   // tau in DAYS

    // ---- LOOP B: the lawful O -> P path (Ch 8.4) ----
    filter flt2: LowPass< in=manifest, out=trend, tau=21.0 >;   // three weeks, in DAYS
    feedback trend -> substrate [beta=0.05];   // FB1 — to the BIAS, never the signal path

    // ---- TEST POINTS ----
    probe tp1: gated;       // clarity leaving INTAKE
    probe tp2: refusal;     // principled aversion
    probe tp3: amplified;   // AMPLIFY output vs sat
    probe tp4: manifest;    // delivered operational current
}
```

[[FIGURE 13-B: Full schematic of CCB-D in drawn component symbols — C1 as a capacitor feeding the ^5^P bias rail along the bottom; R1 as a two-resistor divider with the tap labelled k; Q0 and Q1 as CJTs with bias terminals tied to the rail; F1 as a fuse on the branch dropping from Q1's effect; MUX1 as a two-input multiplexer; D2 and D3 as diodes in the horizontal path with Vf beside each; Q2 with sat=0.80 drawn as a dashed ceiling above its effect terminal; OSC1 as a square-wave oscillator; Q3 biased from a separate ^5_collective^E symbol rather than the rail; the two feedback loops as return paths at different heights, time constants labelled.]]

**Stage 0 — the bias rail.** `C1` is the operator's `^5` Female — a Mind impregnated with an Idea, the Ideas a Mind is composed of — held as stored charge (Chapter 7.1) and charging on the curve of Chapter 7.2, `P_cap(t) = 10 × (1 − e^(−t/τ))`. **τ = 3,333 hr** is chosen so the rail reaches 95% at 3τ = 10,000 hours, tying the component to the constant of Chapter 5.2. At τ = 10,000 hr ten thousand hours of practice leaves you at 63%, contradicting the constant; at τ = 1,000 hr the rail saturates inside a year, contradicting everything observed about acquiring a craft.

**Leakage = 0.0002/day** is the parameter operators ignore: an unreinforced `^5` store loses 0.02% of its charge daily, a half-life near 9.5 years. Negligible until you multiply. Practice needed to hold station is `leakage × C` — **22 minutes a day at 1,850 stored hours**, a full hour at 5,000. Maintenance cost scales with the store, which is why advanced practitioners practise more rather than less: an arithmetic consequence of a leaky capacitor, not a virtue.

**Stage 1 — INTAKE.** `R1` is the drive voltage divider of Chapter 6.4, tapped between `Dial(^2)` in the expand leg and `Dial(^3)` in the constrain leg: `k = Dial(^2) / (Dial(^2) + Dial(^3))`. Dials run 3–9 (Chapter 6.2); Chapter 6.2 caps their difference at 4.

> **Bench Note — the divergence limit is a transmission cap, and turning attraction up can lower it.**
> `k` is set by the *ratio* of the dials, not their size, so enumerate the lawful pairs instead of reaching for the biggest number. `Dial(^2) = 9` drags `Dial(^3)` to at least 5 to stay inside the limit: `k = 9/14 = 0.643`. Back both off to (7,3) — divergence still exactly 4, still lawful — and `k = 0.700`. **The lower pair transmits more.** Maximum transmission sits at the bottom of the aversion range, not the top of the attraction range: 0.700 at (7,3), 0.667 at (8,4), 0.643 at (9,5). The floor is the mirror image, (3,7), `k = 0.300`. On any lawfully-dialled D-board intake transmission lives in **[0.30, 0.70]** and nowhere else. Operators chasing "total belief, zero doubt" are asking for `k = 1.0`, which needs `Dial(^3) = 0` — off the scale, a divergence of 9, and the board that delivers it is the board that fractures `^5`.

**Stage 2 — POLICY.** Two devices in series on separate Noetics: decomposition at `^6`, recoil at `^3`. Collapse them into one and you have written the drift this book exists to prevent.

`Q0` produces `^6_audit^P_{F7}|A` at **β = 1.0**. `^6` Male — an Idea impregnated with another Idea, the Ideas an Idea is composed of — is the Noetic for taking the desire apart: what it is made of, what it costs, whose consent it needs. Unity gain, because above 1.0 an audit manufactures objections and below 1.0 it downplays real ones. Decomposition, emphatically **not** `^3`.

`Q1` produces `^3_refusal^P_{F7}|⟨A,f,T⟩` at **β = 2.0, sat = 0.85, cutoff = 0.30**. `^3` Negative is the Idea the Mind is adverse to and repelled by — the visceral will-not, not the analysis, which already happened at Q0. The register-set says the aversion is present in three registers without claiming they fuse. `(^3^P|A × ^3^P|f × ^3^P|T)` would be invalid under the v7.7 discipline of Chapter 2.6: same-Noetic multi-register `×` requires a named emergent result, and no fused state is defined for this board. Three co-present locks, each independently defeasible, is the honest claim and the weaker one — say the weaker thing.

`sat = 0.85` sits inside the 0.85–0.97 band Chapter 3.3 specifies for safety CJTs; past the plateau the stage stops responding to its cause, so a desire cannot be argued past a refusal it already triggered. `cutoff = 0.30` lets ordinary wants through without a fight. `F1` blows at 0.90 and blocks permanently. Note that this refusal is specified by ceiling and fuse, never by gain: the infinite-gain form `β=∞` used for comparators in the companion volume is a limit, not a value, and a validator rejects non-finite parameters outright. Build such a stage as `β=10` — once `sat` clamps the output the two are indistinguishable.

**Stage 3 — AMPLIFY.** `sat = 0.80` on `Q2` governs the entire worked example: 20% headroom, keeping the stage in the active region where output tracks input. `cutoff = 0.05` is the floor of the 0.05–0.20 band of Chapter 3.3, deliberately at the bottom, because this is the stage the RPM D-gate is measured against (13.6) and a high floor reads modest but real drive as none — at `cutoff = 0.20` the Corvette operator's `I_attention = 0.076` fails the gate on a desire that in fact runs. `rπ = Dial(^5)/Dial(^6)` sets stubbornness; `g_m = 0.4` sets framing sensitivity (Chapter 10.3), low enough that rewording does not swing the output, high enough that a better formulation registers.

**Stage 4 — RHYTHM.** `OSC1` runs a 24-hour period at duty `t_op / 1440 min`. The **duty ceiling of 0.05** — 72 minutes a day — is invariant S5. Above it you are not running an operation on a schedule but a loop, and the observable is rumination. An operator who cannot get a desire below 72 daily minutes has a `^5` problem the D-board is the wrong instrument for (Chapter 20).

`( ^4_confirm^E_{F2}|f × ^7_cadence^E_{F6}|E ) = ^5_charge^E_{F2}|f`

A `^4` Vibration — the degree to which an Idea resonates with the Mind, its impression — integrated with a `^7` Rhythm — the rate and pattern a Mind is exposed to an Idea, entraining it — produces `^5`, composition. This `×` is legitimate: two different Noetics, one domain, no ascent, **named emergent result**. Impression alone fades; cadence alone is empty repetition. Their integration charges the capacitor, which is why RHYTHM is a stage and not a footnote.

**Stage 5 — MANIFEST.** `Q3` is the only stage biased by something other than the operator: `^5_collective^E_{F4}|f`, the accumulated composition of whatever minds have to move. `β = receptivity` is therefore not a knob but a property of the world, estimated and then respected. Buying a mass-produced car from people whose job is selling cars is a receptivity near 1.0. Persuading one specific person to love you is not.

Read the bias domain twice, because the obvious choice is wrong and the compiler catches it. Receptivity is about the world, the world is where acts land, so the hand reaches for `^5_collective^O` — and `cause=^7_cadence^E` against `bias=^5_collective^O` is refused: **`E-CJT-008 CjtCrossDomainBias`**, the bias sitting *below* its own cause. `Q3` satisfies both domain rules at `^E`: cause `^7^E`, bias `^5^E`, effect `^9^O`, with D3 doing the descent. It is also the truer literal — an `^O` collective store records what a population has already done, while what biases this stage is how disposed those minds are *before* they act. When a state refuses to wire, the usual reason is that it was describing the wrong thing.

**The two loops.** It is tempting to run one fast path from MANIFEST to the bias rail so the board "learns quickly." Do not — that is the fast `^O` to `^P` ascent Chapter 8.4 exists to prevent, and a 24-hour constant on it removes the diode. Split it. **FLT1** (τ = 24 hr) is a rate limiter staying inside `^O`, stopping the operator re-triggering RHYTHM on yesterday's result. **FLT2 + FB1** (τ = 3 weeks, β = 0.05) is the lawful path up, terminating at C1's bias terminal and never at the signal path — feedback around a gain stage is an oscillator, which Chapter 14 builds deliberately and which here is a defect.

---

### 13.4 CJT Parameter Selection Table (by Desire Type)

`β` at Q2, `receptivity` at Q3, and the RHYTHM period are chosen together by desire type. Every row is a starting point with a reason, never a measurement.

| Desire type | Q2 `β` | Governing state | Q3 receptivity | RHYTHM period | Dominant R term |
|---|---|---|---|---|---|
| **Wealth / possession** | 2.5–3.5 | `^2^E_{F5}\|f` | 0.9–1.0 | 24 hr | R_resource |
| **Love / partnership** | 1.2–2.0 | `^2^E_{F4}\|f` | 0.3–0.6 | 7 days | R_context |
| **Health / function** | 1.5–2.5 | `^2^P_{F3}\|E` | 0.7–0.9 | 24 hr | R_cap |
| **Power / influence** | 2.0–3.0 | `^2^C_{F7}\|T` | 0.2–0.5 | 30 days | R_policy |
| **Knowledge / skill** | 1.0–1.8 | `^2^C_{F2}\|A` | 0.9–1.0 | 24 hr | R_cap |
| **Protection / boundary** | 1.5–2.5 | `^3^P_{F6}\|⟨A,f,T⟩` | 0.8–1.0 | continuous | R_policy |

**Wealth.** High gain is affordable because receptivity is high — markets are built to transact and nobody has to be convinced. The binding term is `R_resource`, the one resistance a person attacks directly with ordinary work. Daily cadence, because financial resistance moves in daily increments.

**Love.** The lowest gain band, and the receptivity column is why. Another mind must consent, and a mind that has not consented is a resistance you are structurally forbidden to lower by force — the difference between this board and Chapter 19. High `β` against low receptivity gives a saturated stage and an obsessed operator: all the gain into the ceiling, none into the world. Weekly cadence, because daily operation on a person is the duty-cycle failure in its most recognisable form.

**Health.** Read the governing state carefully: `^2^P|E`, attraction to function in the Embodied register, not `^3` toward a condition. The dominant term is `R_cap` — adherence, the actual behaviours. That is the whole safe scope of this row: the board organises attention onto acts. It does not treat, diagnose, or replace anything, and a symptom belongs to a clinician.

**Power.** Receptivity is low because many minds are involved and most are not moving. Monthly cadence, because collective resistance has a time constant measured in months (Chapter 15.4). The dominant term is `R_policy` — usually the operator's own, which is the honest finding and often the unwelcome one.

**Knowledge.** Lowest gain, highest receptivity: nothing resists you learning a thing. `R_cap` is all of it, and it falls with practice hours — the one row where the D-board and the `^5` capacitor work on the same quantity. Chapter 20 is the better instrument for a long acquisition.

**Protection.** The only row governed by `^3` rather than `^2`, correctly: a ward is principled aversion to a class of thing, held across three registers, running continuously. Gain stays moderate because vigilance at high gain is indistinguishable from anxiety.

**On the row that is not here.** A row for operations aimed at harming a specific person is absent, and not only for taste. It fails three of this board's own invariants: it drives `Dial(^3)` past the S4 limit, it inverts the `^2`↔`^3` involution pair by design (Chapter 19.4), and it acts on a mind that has not consented, outside the scope declared in 13.1. The mechanism is analysed — as mechanism, for recognition and defence — in Chapter 19, which ends in its counter-circuit. Parameters for it appear nowhere in this book.

---

### 13.5 St. John's Equation Calibration for D-Board

After every operation, clock two numbers and compute (Chapter 5.3):

```
  eta    = t_op / t_conf
  result = eta × 1/3   ->  reduce to a/b
  a = n_ops     b = beta_next     A = b/a = required amplitude ratio
```

`a` is how many more operations, `b` the amplitude each must deliver relative to this one. Neither name is a CJT parameter.

> **Bench Note — `A = b/a` is the number, and the reason is arithmetic rather than doctrine.**
> Chapter 5.3 puts the swing on the bench: hold `t_op = 20 min`, be wrong about the confirmation by four minutes either way, and `b` reads 3, then 12, then 18. Here is *why*. `b` is a lowest-terms denominator, and reduction is not continuous in its inputs — 5/12 and 5/18 sit close either side of 1/3, but 12 and 18 sit nowhere near 3. The ratio cancels the reduction back out: `b/a` equals `3/η` identically, so the same three readings give **3.0, 2.4, 3.6** — smooth and monotone under a timing error. `A` is also the only St. John's output dimensionally comparable to a CAS-Ohm current ratio, which is what makes the independent check in 13.6 possible at all. Log `a` and `b` because the tradition does. Decide on `A`.

| A = 3/η | Reading | What to do |
|---|---|---|
| A ≥ 9 | Weak coupling; the confirmation barely arrived | Do not chase gain — TP1 and R_op are wrong. Chapter 23.3 |
| 3 ≤ A < 9 | Working, under-driven | One lever at a time: clarity, aversion, resistance |
| 1 < A < 3 | Close | Finish the resistance work; do not re-tune the amplifier |
| A ≤ 1 | Sufficient | Stop operating. `n_ops = a` more sessions, then act |

And the correction that matters most: **`β_next` is not the CJT's β.** It multiplies the *delivered current* at TP4, and five things set that current — clarity at TP1, transmission `k`, residual aversion at TP2, the amplifier, and `R_op`. When Chapter 5's Red Corvette reads `b = 9`, it is not asking for `β = 9` on a device whose design range tops out near 4.0. It is asking for nine times the current at TP4, and the amplifier is the least available of the five ways to get it.

---

### 13.6 Worked Example: The Red Corvette (Full Walkthrough)

Every number below is carried through; nothing is asserted that is not computed.

**The operator.** Three years of practice, 1,850 hours logged. Bias rail from Chapter 7.2 with τ = 3,333 hr:

```
  P_cap = 10 × (1 − e^(−1850/3333)) = 10 × (1 − 0.574) = 4.26
```

The rail sits at **4.3** of a possible 10. Break-even maintenance is `0.0002 × 1850 = 0.37 hr/day` — **22 minutes**. This operator practises 20, so the rail drifts down 0.037 hr/day, about **13 hours a year**. Worth knowing before blaming the board.

**The Prime Desire.** *I own a red Chevrolet Corvette.* Present tense, specific make and colour, ownership rather than wanting. The formation matters because TP1 measures it.

**RPM gate (Chapter 21).** *A0.* Strip the object of witnesses: would you still want it if nobody ever saw you in it? Yes — the desire is `^2^E` toward the object, not `^2^O` toward being seen. Had the answer been no, the true Ω is status and this is the wrong board (Chapter 23.3).

*D-gate.* `Dial(F5) = 7`. Intake resistance per Chapter 4.4: `R_cap 10 + R_policy 5 + R_context 15 + R_resource 20 = R_in 50`. The desire originates at `^C`, so it pays D2 and D3 only:

```
  I_attention = (V_drive − ΣVf) / R_in = (7 − 3.2) / 50 = 3.8 / 50 = 0.076
```

Against Q2's `cutoff = 0.05` that clears by 52%. Gate passes — thinly. Note what the diode correction did: the naive `7/50 = 0.14` overstates the margin by nearly double.

*W-gate.* Schematic in hand. *P-gate.* Twenty minutes daily, private room, materials. Pass.

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
> Saturation is a virtue at Q1, where a refusal must stop responding to argument. It is a defect at Q2, where output must track cause for St. John's ratio to mean anything. The test is one probe: if TP3 sits exactly at `sat` and does not move when you improve TP1, the stage is clamped and every calibration number downstream is uninterpretable. Fix the operating point *before* you believe a reading. The commonest misdiagnosis in desire work is an operator concluding they need more power from an instrument already at its ceiling.

**Operation 2 — corrected operating point.** Q2 dropped to `β = 2.5`, the bottom of the wealth band. Nothing else changes.

- Cause unchanged at `c = 0.305`.
- Q2 output: `2.5 × 0.305 = 0.762`. **TP3 = 0.76**, active, about 5% below the ceiling.
- `t_op = 20`, `t_conf = 20` — a red Corvette in the next lane on the way home. `^4` Vibration 1°.

```
  eta = 20/20 = 1     result = 1/3     a = 1, b = 3     A = 3.0
```

Now the independent check. Receptivity is 1.0 for a mass-market car, so `V_manifest = 10 × TP3 × 1.0 = 7.6`. Operational resistance, decomposed honestly: `R_cap 5 + R_policy 7 + R_context 20 + R_resource 35 = R_op 67`.

```
  TP4 = (V_manifest − Vf_D3) / R_op = (7.6 − 2.0) / 67 = 5.6 / 67 = 0.084
```

The manifestation threshold on this board is **0.25** — the current below which the operator does not, in practice, make the calls and visit the lots. Deficit: `0.25 / 0.084 = 2.99`.

St. John's Equation, from two clock readings, says the amplitude must rise **3.0×**. CAS-Ohm, from seven board parameters sharing no inputs with those readings, says **2.99×**. That is a consistency check between two models on one example — not proof that either is right, and one agreement is not evidence. But a disagreement would have been a reason to stop, and there isn't one.

**Where the 3× can come from.** `TP3 = 0.76` against `sat = 0.80` leaves 5% headroom. Three times 0.76 is 2.28; the ceiling is 0.80. **The amplifier cannot supply the required gain** — not with a better β, not with a cascade, since every cascaded stage clamps at its own ceiling (Chapter 10.5). Four levers remain, three on the resistance side:

1. **TP1** — clarity, 0.62 → 0.85. Statement rewritten, sigil rebuilt, `^1` Mind at 1°. The rebuild is also a capability gain, so `R_cap` falls 5 → 4: an operator who can hold the image can hold a conversation about the car.
2. **TP2 and the dials** — Q0's audit surfaces the blocking belief, *people like me don't own cars like that*, a `^5` composition item resolved per Chapter 23.3. Aversion 0.18 → 0.08; dials to (7,3) — divergence 4, at the S4 limit and not past it. `k = 0.70`.
3. **R_context** 20 → 2. Two weekends: market prices learned, three dealers identified.
4. **R_resource** 35 → 9. Car sold, six months of a savings line, financing pre-approved.

`R_policy` stays at 7 — the operator's own rule about what fraction of income a payment may take. Lowering a policy resistance to make a board fire is how a safety invariant becomes a story you tell afterwards.

**Operation 3 — after the resistance work.**

- `c = 0.85 × 0.70 × 0.92 = 0.547`.
- Q2 re-tuned to `β = 1.40` to stay off the ceiling: `1.40 × 0.547 = 0.766`. **TP3 = 0.77**, active, about 4% headroom.
- `R_op = 4 + 7 + 2 + 9 = 22`; `V_manifest = 10 × 0.77 × 1.0 = 7.7`.

```
  TP4 = (7.7 − 2.0) / 22 = 5.7 / 22 = 0.259     >=  0.25   PASS
```

`t_op = 24 min`, `^1` Mind 1°. `t_conf = 8 min` — the confirmation arrives while still in gnosis.

```
  eta = 24/8 = 3      result = 1/1      a = 1, b = 1      A = 1.0
```

Sufficient. One more 24-minute session, then stop operating and go do the thing.

**Where the gain actually came from.** TP4 went from 0.084 to 0.259, a factor of **3.10**:

```
  numerator  5.7 / 5.6 = 1.018      (the amplifier)
  resistance   67 / 22 = 3.045      (the resistance work)
  1.018 × 3.045 = 3.10                              check
```

On a log scale the resistance term accounts for **98%** of the improvement. The amplifier — the stage every operator tunes first, the one this board makes adjustable, the one the whole folk tradition is about — contributed under two percent. The rest was a person selling a car, learning a market, and moving money.

That is the finding, and it is not a disappointment. It is what the board is for. CCB-D took an operator pushing harder on a clamped amplifier and pointed their twenty minutes a day at the four numbers that could move. The Corvette did not appear in the driveway. The path to it stopped being obstructed, one resistance term at a time, by the operator.

[[FIGURE 13-C: Assembly drawing of CCB-D — rectangular board outline, five stages left to right as labelled rectangles, designators R0, C1, D1, R1, Q0, Q1, F1, MUX1, D2, Q2, OSC1, D3, Q3, FLT1, FLT2, FB1 at their positions; the ^5^P bias rail as a thick trace along the lower edge with tick marks where Q0/Q1/Q2 tap it; four circled test-point callouts TP1–TP4 on leader lines with expected bands beside each (TP1 0.60–0.90, TP2 <0.30, TP3 0.60–0.78, TP4 ≥0.25); a boxed BOM at lower right listing every designator with its key parameter.]]

[[FIGURE 13-D: TP4 band chart — one vertical axis from 0 to 0.40 labelled "delivered operational current", split into three shaded bands: below 0.05 "cutoff — board not firing", 0.05–0.25 "confirmation band: signal reaches the Ether, no manifestation", above 0.25 "manifestation threshold"; Red Corvette operations 2 and 3 plotted at 0.084 and 0.259; the middle band annotated "this is where operators conclude the board doesn't work".]]

[[FIGURE 13-E: AMPLIFY transfer curve — horizontal axis cause activation c from 0 to 0.8, vertical axis TP3 from 0 to 1.0, horizontal dashed ceiling at sat = 0.80; three lines of slope 3.0, 2.5 and 1.40 rising from the origin and flattening at the ceiling; operating points marked at (0.305, 0.80 clamped), (0.305, 0.76) and (0.547, 0.77); the clamped point circled and annotated “pinned — no calibration reading is valid here”.]]

---

### Component and Parameter Table

The last column is what breaks at other settings. **Ref** is the designator used in the prose and figures; the listing's instance name is the same letters in lower case. `C1` and `F1` are reserved tokens in CCDL (`C1` a state reference, `F1` a Drive), which is why the listing never uses the upper-case form as an identifier.

| Ref | Form | Parameters | Failure at other values |
|---|---|---|---|
| **C1** (with R0) | `^5_operator^P_{F7}\|T` bias rail | τ=3333 hr (R=40.0 × C=83.33), leak=0.0002/day, V_BR=8.0 | τ=10,000 hr contradicts the Ch 5.2 constant; leak=0.004/day makes practice unsustainable |
| **D1** | `^P -> ^C` | Vf=0.7 | Omitted, a calling reads as a whim and pays 3.2 instead of 3.9 |
| **R1** | `Dial(^2)/Dial(^3)` divider | k ∈ [0.30, 0.70] | Divergence >4 fractures `^5` (S4) |
| **Q0** | `-> ^6_audit^P_{F7}\|A` | β=1.0 | β>1 manufactures objections; β<1 hides real ones |
| **Q1** | `-> ^3_refusal^P_{F7}\|⟨A,f,T⟩` | β=2.0, sat=0.85, cutoff=0.30 | sat>0.97 never latches; cutoff<0.1 refuses everything |
| **F1** | fuse on refusal | 0.90, permanent_block | `action=warn` compiles clean and leaves no latch — read it by eye |
| **MUX1** | select on `refusal` | passes `gated` while TP2 is under Q1's cutoff | Selecting on a timer, a retry count, or operator patience makes the audit decorative. S1 hangs on this one wire |
| **D2** | `^C -> ^E` | Vf=1.2 | Vf=0.3: every passing want feels decided |
| **Q2** | `-> ^9_amplified^E_{F5}\|A` | `β=by type`, `sat=0.80`, `cutoff=0.05`, `g_m=0.4`, `rπ=Dial(^5)/Dial(^6)` | sat=1.0 removes the headroom calibration needs; cutoff=0.20 reads ordinary drive as none and fails the D-gate on desires that would have run |
| **OSC1** | `-> ^7_cadence^E_{F6}\|E` | period=24 hr, duty≤0.05 | duty>0.05 is the obsession mode, S5 |
| **D3** | `^E -> ^O` | Vf=2.0 | Vf=0.5: acts on every verdict, impulsivity |
| **Q3** | bias `^5_collective^E_{F4}\|f` → `^9_manifest^O_{F5}\|E` | β=receptivity, sat=1.0 | Bias written at `^O` sits below its own `^E` cause: `E-CJT-008`. Receptivity set by preference is this board's commonest self-deception |
| **FLT1** | lowpass inside `^O` | τ=24 hr | τ=0: re-runs stack, duty ceiling breached |
| **FLT2 / FB1** | `-> ^5_operator^P_{F7}\|T` | τ=3 weeks, β=0.05 | τ=24 hr removes the diode (Ch 8.4); β=0 makes the operator unfalsifiable |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `^0_gated^C` | Clarity leaving INTAKE | 0.60–0.90. Below 0.60 the desire is vague; above 0.90 with rigidity is over-specification — a brittle Ω only one path can satisfy |
| **TP2** | `^3_refusal^P` | Principled aversion | <0.30 passes. ≥0.30 fires. ≥0.85 latched. ≥0.90 fuse blown, operation over |
| **TP3** | `^9_amplified^E` | AMPLIFY output vs ceiling | 0.60–0.78 active. Exactly 0.80 = pinned; no calibration downstream is valid |
| **TP4** | `^9_manifest^O` | Delivered operational current | ≥0.25 manifesting. 0.05–0.25 confirmations only. <0.05 the chain never cleared Q2's cutoff; the board is not firing |

TP4's middle band is the most useful reading here. Between cutoff and threshold the board is genuinely working, confirmations genuinely arrive, and nothing arrives — the error Chapter 5.6 names, now with a number and a cause.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Pinned amplifier** | `β × c > sat` at Q2 | TP3 exactly at 0.80, unmoved by better clarity; ratios erratic | Lower β until TP3 sits 3–5% under the ceiling, then re-read |
| **Confirmation lock** | TP4 in 0.05–0.25 | Confirmations arrive reliably, outcome never does | Decompose R_op (Ch 4.4); attack R_context and R_resource |
| **Below-floor drive** | V_drive < ΣVf = 3.2 | Nothing happens; operator escalates ritual | Raise drive or shorten the chain; ritual cannot cross a diode |
| **Dial fracture** | divergence > 4 | Oscillation between certainty and disgust about one desire | Restore the Chapter 6.2 limit; the divergence is the symptom |
| **Duty overrun** | duty > 0.05 | Operation runs most of the day; rumination | Enforce the ceiling. If it cannot be held, the desire is not the problem |
| **Fast feedback** | FLT2 τ toward hours | One result rewrites principles; later boards inherit the bias | Restore τ ≥ 3 weeks, β ≤ 0.05, terminating at the bias |
| **Receptivity inflation** | Q3 β set by wish | Healthy at TP1–TP3, TP4 flat | Re-estimate from how many minds must move |
| **Rail discharge** | practice below `leak × C` | Slow degradation, no single cause | Meet break-even minutes before re-tuning anything |

---

### What This Chapter Established

- **CCB-D delivers a current, not an object.** TP4 measures flow into the Operational domain, spent by a person performing acts. The board organises effort and attention; it does not suspend causality.
- **The bias terminal is bounded on both sides, and the two rules point opposite ways.** A bias must sit at or above the cause it governs (`E-CJT-008` otherwise); an effect must sit at or below the bias that produced it. Together they explain why a `^C` cause can produce a `^P` refusal with no unlawful ascent, why an operator with no principled formation cannot produce one at all, and why receptivity biases MANIFEST at `^E` and not the `^O` a reader reaches for first.
- **The 4-point divergence limit is a computable transmission cap, and it is not monotone in the attraction dial.** Lawful dials confine intake transmission to `[0.30, 0.70]`, maximum at (7,3) — not (9,5), which transmits less. Total belief with zero doubt is a divergence of 9 and a fractured `^5`.
- **A saturated amplifier cannot be calibrated.** Saturation is the safety feature at Q1 and a defect at Q2. TP3 pinned at `sat` invalidates every reading downstream of it.
- **Read `b/a`, not `b`.** The lowest-terms denominator is discontinuous — a 20% timing error swung it from 3 to 18 — while `A = b/a = 3/η` is smooth and is the number that must match the CAS-Ohm deficit. And `β_next` is not the CJT's β: it multiplies delivered current through five levers, of which the amplifier is usually the least available.
- **In the worked example, 98% of the improvement came from the resistance side.** That is the general shape of desire work, not a peculiarity of one car.
- **Two feedback loops, not one.** A fast limiter inside `^O`, and a slow, low-gain, bias-terminated path up to `^P`. Merging them deletes the diode Chapter 8.4 exists to install.
- **The `^5` rail costs `leak × C` a day to hold.** The more you have accumulated, the more daily practice it takes to keep it.

---

### Exercises

*(Answers in Appendix H.)*

**13.1 — Compute the transmission bounds.** Derive `k_min` and `k_max` from the 4-point limit and the 3–9 dial range. State what dial pair `k = 0.75` would need, and name the invariant it breaks.

**13.2 — Diagnose the pin.** TP1 = 0.71, TP2 = 0.12, `k = 0.60`, `β = 3.2`, `sat = 0.80`. Compute `c` and the unclamped output. Is TP3 pinned? Give the largest β holding the stage 5% below the ceiling.

**13.3 — Read the band.** TP4 reads 0.11 across four consecutive operations while confirmations arrive at 1° every time. Name the failure mode, the two resistance terms you would decompose first, and why raising β would not help.

**13.4 — Run the ratio.** For `t_op = 30` and `t_conf` of 45, 30, 20 and 10 minutes, compute η, `result`, `a`, `b` and `A = b/a`. Identify the case where `b` misleads and what acting on it would cost.

**13.5 — Cost the rail.** An operator with 4,200 logged hours practises 35 minutes a day. Compute the rail charge from the Chapter 7.2 curve, the break-even daily minutes, and the annual net change. State one thing they should change and one they should not.

**13.6 (Build) — Add a confirmation-grade gate.** OSC1 sustains until a 1° confirmation or exhaustion. Write a CCDL fragment that also halts it after three consecutive 3° confirmations. Justify your threshold, and state what the halt must *not* be wired to do.

**13.7 (Marquee) — Board a low-receptivity desire.** Specify a complete D-board for a partnership desire: both dials, `k`, Q2 `β` and `sat`, Q3 receptivity, RHYTHM period and duty, and the four `R_op` terms. For every departure from the wealth-row defaults, state the failure mode you are buying protection against and the capability you give up. Then state which resistance term you are structurally forbidden to lower, and why that forbidding is the difference between this board and Chapter 19.
