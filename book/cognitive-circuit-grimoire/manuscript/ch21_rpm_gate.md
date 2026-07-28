# CHAPTER 21
## The RPM Prerequisite Gate
*The interlock that runs before the cast — four checks, four numbers, and the one operation you cannot reverse*

Fourteen operations. Two hundred and eighty logged minutes. One desire. Not a single confirmation graded better than 3°, which Chapter 5.5 calls subtle, ambiguous, weak.

The instinct is to reach for the amplifier — raise β, hold gnosis longer, tighten the sigil. All three are wrong, and the log says so on line one: the desire as worded was never the desire. Every number after it measured delivery of a target nobody wanted. The amplifier worked perfectly. It amplified the wrong thing fourteen times.

**CCB-RPM** is the interlock that catches that on day one. It casts nothing, amplifies nothing, and emits one output — `ARM` or `HOLD`, with the deciding number attached. It runs the chain `A0 → D → W → P → outcome` as four gates in series, each with a threshold you check by hand.

It costs forty minutes of paper and zero casts. It is the cheapest board in this book and the most often skipped, because skipping it feels like starting. And it is the only board whose skipping cannot be repaired afterward — Section 21.5, the part with real mathematics under it.

---

### Requirements and Safety Invariants

Chapter 12.2 requires the "must not" list before the functional one.

| # | Functional requirement | Realized by |
|---|---|---|
| R1 | Authenticate the desire as the operator's own before anything else runs | A0 differential pair + fuse F1 (§21.1) |
| R2 | Return a *number* for drive sufficiency, not an impression | CAS-Ohm D-gate, monitor M2 (§21.2) |
| R3 | Verify the schematic is possessed, not intended | Six-input AND, no partial credit (§21.3) |
| R4 | Verify the schedule can actually be held | Budget monitor at half the available minutes (§21.4) |
| R5 | Emit `ARM` or `HOLD` with the deciding number | MUX + ledger, TP4 |

| # | Safety invariant (MUST NOT) | Enforcement |
|---|---|---|
| S1 | Arm on a summed score — the four gates are not fungible | `AND`, never a weighted sum |
| S2 | Amplify anything | Every verdict CJT at β = 1.0; `E-CJT-005` on any loop |
| S3 | Let an Operational outcome edit the Principled substrate directly | Diode `d_out`; filtered τ = 21 d feedback at β = 0.15 (Ch. 8.4) |
| S4 | Present the scan as an undo | No inverse component exists, in the listing or the language (§21.5) |
| S5 | Arm while the operator's CSB is unarmed | No `ARM` on a blown involution monitor (Ch. 24, Ch. 6.2) |

[[FIGURE 21-A: Block diagram — CCB-RPM left to right: STATED DESIRE → A0 AUTHENTICATION (decomposition block feeding three pull probes into two differentials, "witness load" and "object premium"; fuse F1 branching down to a RE-WORD terminal) → D-GATE (drive rail, three-diode descent chain, four-resistor constraint stack, ammeter reading I_attention, monitor M2 branching down to HOLD) → W-GATE as a six-input AND → P-GATE as a four-input AND → ARM/HOLD MUX → diode D_out descending into the cast. Beneath, a τ = 21-day lowpass runs from the ARM node back to the practice rail. TP1–TP4 flags at witness load, I_attention, the readiness AND, the MUX output.]]

---

### 21.1 A0 (Pure Desire) Authentication — Is This Really What You Want?

A0 is the only gate that asks about the operator rather than the circuit, and it has one question in two halves: *is the pull mine, and is it toward the thing I named?*

Both halves are answered by subtraction. The operator writes three readings on a 0–1 scale, all typed `^2^E_{F5}|f` — Positive, Evaluative domain, Agency, affective register:

| Reading | What you rate |
|---|---|
| `pull_open` | The desire exactly as worded |
| `pull_private` | Same desire, all witnesses removed — nobody ever knows, asks, or sees |
| `pull_condition` | The condition the target stands for, delivered by another route, *without* the target |

These are self-ratings in a log, not measurements of anything. What makes them usable is that the gate acts on *differences*, so a consistent personal bias subtracts out — the common-mode argument the CSB's differential pair runs on (Ch. 24).

```
witness_load   = pull_open − pull_private     trip at ≥ 0.30
object_premium = pull_open − pull_condition   hold at ≥ 0.20
```

**Witness load ≥ 0.30 blows fuse F1.** A pull that drops by a third when the audience goes is substantially `^2^O_{F4}|f` — attraction toward being seen — wearing the target's clothes. Chapter 13.6 runs this probe on the Red Corvette and passes it: the operator wants the car with nobody watching, so the desire is `^2^E` toward the object, not `^2^O` toward the witnesses. Threshold 0.30 is a design choice — a third of the pull is where the audience, not the object, is setting the amplitude. At 0.50 the fuse passes desires that are almost entirely audience; at 0.10 it blocks nearly everything and the operator quietly stops logging honestly, which is worse.

**Object premium below 0.20 trips M1 as `PROXY_TARGET`.** If the bare condition pulls nearly as hard as the named target, the target is a proxy and the condition is the prime desire. 0.20 is the smallest gap that survives self-rating noise; below it the readings are indistinguishable and the honest verdict is *undecided*, reported as a hold.

The repair for both is `^6^C_{F6}|A` — Male, Cognitive, analytical: take the wording apart and see what it is made of. Note the Noetic. Decomposition is `^6`; it is not `^3`, even though what you are often hunting is a `^3`, a visceral recoil across the path. Finding it is `^6` work. Chapter 2.2 names this the commonest drift in the book, and it costs — an operator who thinks aversion-hunting is itself `^3` goes looking for something to recoil from and reliably finds it.

[[FIGURE 21-B: Decision map — horizontal axis witness load 0 to 0.6 with a dashed line at 0.30; vertical axis object premium 0 to 0.6 with a dashed line at 0.20. Four labelled quadrants: PASS (low load, high premium), PROXY TARGET, WITNESS-CARRIED, BOTH — RE-WORD. Plot the worked example's two passes at (0.38, 0.08) and (0.07, 0.42), joined by an arrow labelled "re-specification, no cast fired".]]

> **Bench Note — write all three numbers before you compute either difference.** Self-reports drift toward the answer the operator already wants. Rate open, then private, then condition, in ink, and only then subtract. Compute the witness load after two readings and the third gets bent to clear the threshold — not dishonestly, just helpfully, the way anyone filling in a form they want to pass bends it. This is the one place on the board where the procedure does more work than the arithmetic, and it is free.

A plain line about the operator, not the circuit: decomposition can surface something painful rather than a mis-worded target. This is a checklist on paper — it identifies nothing about a person and treats nothing. If what surfaces is distress, that is a matter for a clinician, and nothing here substitutes for that care.

---

### 21.2 D-Gate: V_drive Sufficiency Check

Pure arithmetic, and it is Chapter 4 applied unmodified.

```
I_attention  = ( V_drive − ΣVf ) / R_constraint            (Ch. 4.2)
R_constraint = R_cap + R_policy + R_context + R_resource   (Ch. 4.4)
```

`V_drive` sums the drive dials on the path, each an integer 3–9 (Ch. 6.2). `ΣVf` is the forward drop of the descent chain the operation must cross — D1 (P→C) 0.7, D2 (C→E) 1.2, D3 (E→O) 2.0 `V_c` (Ch. 8.2). A desire originating at `^C` and landing at `^O` pays 3.2 `V_c` before the constraint stack sees anything. The result is compared against the `cutoff` of the AMPLIFY stage that will actually fire:

| `I_attention / cutoff` | Verdict | Why |
|---|---|---|
| ≥ 2.0 | **PASS** | Two-fold margin absorbs an ordinary bad day without dropping the stage into cutoff |
| 1.0 – 2.0 | **MARGINAL** | It fires today. It will not fire reliably across a campaign |
| < 1.0 | **HOLD** | Below cutoff the stage never fires, and the chain reads as if nothing was attempted |

The Red Corvette reads `0.076` against `cutoff = 0.05` — 1.52×. Chapter 13.6 calls that passing thinly; on this board it is MARGINAL, and the response is not to abandon the operation but to spend one afternoon on `R_context` first.

Which is the gate's real output: not *no*, but *which term*. Chapter 4.4 ranks the four by repair cost — `R_context` first (minutes, one clarifying answer), `R_resource` second (days, a budget line), `R_cap` third (hundreds of hours, falling only as the `^5` capacitor charges), `R_policy` last and in writing, because a term that moves by decision gets moved by decision at exactly the moment the operator is least inclined to argue with themselves.

> **Bench Note — do the diode subtraction by hand once, then never skip it.** The naive Corvette reading is `7/50 = 0.14`, a 2.8× margin and a comfortable pass. Corrected: `(7 − 3.2)/50 = 0.076`, 1.52× and thin. The descent chain ate 46% of the rail before the constraint stack saw a volt, and `V/R` overstates by nearly double. Every crossing pays this, and the error grows with how far the desire must descend. Work one gate both ways with a pencil — that gap is the whole reason there is a diode chain drawn in this board.

---

### 21.3 W-Gate: Do You Have the Schematic?

A possession question, and possession is binary. Six items, all required:

| # | Item | Check | Notation |
|---|---|---|---|
| 1 | A formed `^0` Idea — specific, present tense, holdable as one scene | clarity ≥ 0.60 | `^0^C_{F2}\|A` |
| 2 | A CCDL schematic for this operation | in writing | `^6^C_{F6}\|A` |
| 3 | The correct board for this desire type | named, from Ch. 13–20 | `^1^C_{F2}\|A` |
| 4 | CJT parameters — β, sat, cutoff, rπ | numbers, not ranges | `^6^C_{F6}\|A` |
| 5 | A St. John's calibration sheet (App. F) | printed | `^4^E_{F2}\|A` |
| 6 | A Quantitative Table sheet (App. G) | printed | `^7^O_{F6}\|E` |

**It is an `AND`, not a sum, and that is invariant S1.** A weighted score lets an operator trade a vivid Idea against a missing board selection, and those are not exchangeable: five-sixths of a schematic is not a circuit running at 83%, it is an undefined circuit. The characteristic failure is exact — items 1, 2, 4, 5, 6 in hand and item 3 wrong, running a CCB-D against what is actually an identity problem, which Chapter 20 owns.

Item 1 is the only measured one, and 0.60 is borrowed, not invented: the bottom of the 0.60–0.90 clarity band Chapter 13.6 reads at TP1. Below it the Idea is a sentence rather than a scene, usually because the target is phrased as a *condition* — "I decide what work I take" — which nobody can hold as one image. The repair is to give the condition a scene: one Tuesday, one job declined, one accepted.

---

### 21.4 P-Gate: Can You Execute?

Drive without capacity is the failure this gate exists for.

| # | Check | Threshold | Notation |
|---|---|---|---|
| 1 | Gnosis reachable — `^1` Mind at 2° or deeper (Ch. 22.1) | reliably, not once | `^1^C_{F1}\|T` |
| 2 | Schedule load — planned minutes ÷ available minutes | ≤ 0.50 | `^7^C_{F6}\|A` |
| 3 | Access to the substrate the operation writes to | present | `^5^E_{F4}\|f` |
| 4 | Arrival aversion — recoil at the target actually arriving | ≤ 0.25 | `^3^E_{F7}\|f` |

**Check 2 is the one operators argue with.** A campaign must fit inside *half* the available operating minutes across `T_manifest`. Planned at full budget it fails on the first sick day — and a broken `^7` Rhythm does not merely pause a campaign, it lets the `^5` capacitor leak between casts (Ch. 7.3), so the operator restarts from a lower charge than they finished at. Half is the design choice; the failure at 0.9 is a campaign that reads as insufficient drive when what happened was a missed Tuesday.

**Check 4 is `^3` used correctly.** Not an analytical judgement that the outcome would be inconvenient — that is `^6` decomposition. The recoil: can't-stomach-it, when you picture the thing having arrived. The operator who wants the promotion and goes cold imagining its first week. Above 0.25 the operation opposes itself and casting harder amplifies both sides; the response is a self-directed sub-operation against the recoil (Ch. 20, Ch. 23.3) before the prime desire is cast at all.

---

### 21.5 Section-Retraction: Why You Can't Un-Cast

Write `R(I)` for the prerequisite space of a target state `I` — the A0/D/W/P configurations that would produce it. Two maps connect them:

- **`η_I : I → R(I)`** — *embed.* Take the target, descend into what it requires.
- **`ε_I : R(I) → I`** — *realize.* Take a satisfied configuration, collapse it into the state it produces.

The RPM chain is a **section-retraction pair**, not an adjunction, and the composites are not symmetric:

```
ε_I ∘ η_I  =  id_I       embed then realize — you land exactly where you started
η_I ∘ ε_I  ≠  id_R(I)    realize then re-embed — your configuration does not come back
```

[[FIGURE 21-C: Commutative diagram. Upper row: object I, arrow η to R(I), arrow ε back to I, with a curved composite beneath labelled "= id_I — scanning is free". Lower row: R(I), arrow ε to I, arrow η to a distinct shaded object R(I)′, with a crossed-out equals sign between R(I) and R(I)′ and an annotation listing the difference: "+ the cast happened; + the operator knows what it felt like; + the log has a row". Caption notes no arrow R(I)′ → R(I) exists.]]

**The left identity is what makes the gate cheap.** Descend into any prerequisite, find it lacking, come back up with the target unchanged and nothing consumed. That licenses running the whole gate, failing at A0, re-wording, and running it again from the top — which the worked example does. Scanning is lossless. There is no such thing as spending a desire by inspecting it, and the operator who won't run the gate because "looking too hard will kill it" is describing a property the mathematics does not have.

**The right non-identity is what you cannot get around.** Once the cast has fired, re-embedding the resulting state does not hand back the configuration you came from. No inverse arrow, therefore no `undo` component to draw — and **CCDL has no `undo` statement, which is a design claim, not an oversight** (App. B, §B.2.1: look for it; it is not there). Three consequences follow:

1. **An un-cast would be an unlawful ascent.** Reversing a cast requires the Operational outcome to reach back and rewrite the Principled prerequisite that authorized it: `^O × ^P`, invalid notation for the same reason it is invalid engineering (Ch. 8.3). The one lawful upward path here is the filtered O→P feedback, τ = 21 days at β = 0.15. It *updates* the substrate; it does not *restore* it.
2. **Infinite gain does not manufacture an inverse.** `β=∞` is the standard idealization for a hard switch, used in exactly that sense on the CSB's red path (Ch. 24) with the note that a validator rejects non-finite parameters and a real build writes a large finite number. Here the objection is deeper than range-checking: the reverse arrow does not exist *at any gain*, so no finite substitute exists either. A large β on a reverse path specifies a component that is not merely unbuildable but undefined.
3. **A second reading of a gate is not comparable to the first.** This is the checkable face of `η ∘ ε ≠ id`. After firing, the A0 readings cannot be re-taken clean, because one of the three ratings is now contaminated by knowing what the cast felt like. The prerequisite space you re-enter is a different space.

Now the discipline, because this result is over-read more often than it is used. **Section-retraction does not imply:**

- **That the outcome is guaranteed.** Irreversible is not effective. The gate authorizes; it delivers nothing. A cast that produced no confirmation at all still cannot be un-cast.
- **That consequences are permanent.** You may cast a counter-operation — a *new* target with its own full RPM gate, cost, and risk, not an inverse. What is unavailable is making the first cast not have happened.
- **That satisfied prerequisites stay satisfied.** They decay: charge leaks (Ch. 7.3), rails sag, schedules lapse.
- **Anything moral.** The asymmetry is structural. It says nothing about whether the cast should have been made, and a reader who hears a warning in it is hearing their own.

> **Bench Note — decay is not inversion, and confusing them produces a superstition.** A prerequisite can *become* unsatisfied by attrition: stop practising and the `^5` rail drops, stop clarifying and `R_context` climbs back. What cannot happen is a prerequisite being *un-satisfied by an operation designed to reverse it*. The signatures differ — attrition is slow, monotone, visible in the log as a drifting rail; reversal is unavailable at any speed. The operator who conflates them concludes that neglecting a working takes it back. It does not. It loses them the capacity to run the next one, while the first one stands.

---

### The Full CCDL Listing — CCB-RPM

```cas
board ccb_rpm {                          // CCB-RPM — the prerequisite gate
    input:  stated_desire;               // as the operator first words it
    output: authorization;               // ARM or HOLD — never a cast
    node practice_rail: ^5^P_{F7}|T;     // Female: accumulated practice — bias only

    // ---- S1  A0 AUTHENTICATION ----
    node stated: ^0_stated^C_{F2}|A;      node parts:           ^6^C_{F6}|A;
    node pull_open:      ^2^E_{F5}|f;     node pull_private:    ^2^E_{F5}|f;
    node pull_condition: ^2^E_{F5}|f;     node witness_load:    ^2^E_{F4}|f;
    node object_premium: ^4^E_{F5}|A;     node a0_ok:           ^2^E_{F7}|T;
    cjt q_dec:  CJT< stated | practice_rail => parts >          [β=1.0];
    cjt q_open: CJT< parts  | practice_rail => pull_open >      [β=1.0];
    cjt q_priv: CJT< parts  | practice_rail => pull_private >   [β=1.0];
    cjt q_cond: CJT< parts  | practice_rail => pull_condition > [β=1.0];
    diff d_witness: Differential< plus=pull_open, minus=pull_private,
                                  out=witness_load >;
    diff d_premium: Differential< plus=pull_open, minus=pull_condition,
                                  out=object_premium >;
    fuse    f_witness: Fuse< path=witness_load, threshold=0.30,
                             action=block_until_decomposed >;
    monitor m_proxy:   Monitor< signal=object_premium, limit=[0.20, 1.00],
                                action_on_violation=PROXY_TARGET >;
    cjt q_a0: CJT< witness_load | practice_rail => a0_ok > [β=1.0, cutoff=0.05];

    // ---- S2  D-GATE ----
    rail F5: Agency [v=7];                rail F2: Wisdom [v=6];
    node path_in: ^1^C_{F5}|A;            node d_ok: ^4^E_{F5}|A;
    diode d2: Diode< ^C -> ^E > [Vf=1.2]; diode d3: Diode< ^E -> ^O > [Vf=2.0];
    resistor r_cap:      Resistor< path=path_in, R=25 >;
    resistor r_policy:   Resistor< path=path_in, R=0  >;
    resistor r_context:  Resistor< path=path_in, R=30 >;
    resistor r_resource: Resistor< path=path_in, R=20 >;
    monitor m_drive: Monitor< signal=path_in, limit=[0.10, 1.00],
                              action_on_violation=D_GATE_HOLD >;
    cjt q_d: CJT< path_in | practice_rail => d_ok > [β=1.0, cutoff=0.05];

    // ---- S3  W-GATE ----
    node idea:    ^0^C_{F2}|A;   node w_sched: ^6^C_{F6}|A;
    node w_board: ^1^C_{F2}|A;   node w_param: ^6^C_{F6}|A;
    node w_calib: ^4^E_{F2}|A;   node w_sheet: ^7^O_{F6}|E;
    node w_ok:    ^6^E_{F6}|A;
    monitor m_idea: Monitor< signal=idea, limit=[0.60, 1.00],
                             action_on_violation=IDEA_UNFORMED >;
    gate g_w: AND< idea, w_sched, w_board, w_param, w_calib, w_sheet >;
    cjt q_w: CJT< g_w | practice_rail => w_ok > [β=1.0];

    // ---- S4  P-GATE ----
    node p_gnosis: ^1^C_{F1}|T;  node p_load:   ^7^C_{F6}|A;
    node p_access: ^5^E_{F4}|f;  node p_recoil: ^3^E_{F7}|f;
    node p_ok:     ^7^E_{F3}|E;
    monitor m_budget: Monitor< signal=p_load,   limit=[0.00, 0.50],
                               action_on_violation=OVERCOMMIT >;
    monitor m_absorb: Monitor< signal=p_recoil, limit=[0.00, 0.25],
                               action_on_violation=ARRIVAL_AVERSION >;
    gate g_p: AND< p_gnosis, p_load, p_access, p_recoil >;
    cjt q_p: CJT< g_p | practice_rail => p_ok > [β=1.0];

    // ---- S5  ARM / HOLD ----
    gate g_ready: AND< w_ok, p_ok >;      gate g_arm: AND< a0_ok, d_ok, g_ready >;
    node arm:  ^9^O_{F5}|E;               node hold: ^9^E_{F6}|A;
    diode d_out: Diode< ^E -> ^O > [Vf=2.0];
    mux out: MUX< inputs=[hold, arm], select=g_arm >;

    // ---- S6  LEDGER: the lawful ascent, and the only one ----
    filter f_log: LowPass< in=arm, out=trend, tau=21.0 >;   // days
    feedback trend -> practice_rail [β=0.15];

    probe tp1: witness_load;   probe tp2: path_in;
    probe tp3: g_ready;        probe tp4: out;
}
```

**S1.** All three pull probes and both differentials sit at `^E` deliberately. What the bench reads is the operator's *evaluation* of their own pull, not the world-level fact of who is watching, and modelling it at `^E` keeps an unlawful `^O → ^E` ascent out of the listing — the move Chapter 23's intake makes at `^C`. The bench samples; it does not drive. `block_until_decomposed` names the only lawful path past F1: re-word, then re-run from the top.

**S2.** The resistor values are this operator's, on this desire, today — inputs, not constants of the board. The diodes carry the descent drop explicitly rather than folding it into `R`, because an operator who cannot see the 3.2 `V_c` will not subtract it.

**S3–S4.** `AND` and only `AND` (S1). Two P-gate inputs are monitored ceilings rather than possessions — `p_load` and `p_recoil` enter as pass/fail from their monitors, which is why the monitors carry the numbers and the gate carries none.

**S5–S6.** `g_arm` is the last reversible point on the board; the diode past the MUX is the descent into the cast and has no counterpart pointing back. The ledger is the one lawful ascent — `arm` at `^O` reaching `practice_rail` at `^P` — legal only because it is filtered at τ = 21 days and held at β = 0.15, inside the 0.05–0.3 band Part III uses for every feedback path (Ch. 8.4).

[[FIGURE 21-D: Full schematic with reference designators. Left: stated_desire into Q1 fanning to Q2/Q3/Q4 (the three pull probes) into DIFF1 (witness load) and DIFF2 (object premium); F1 in series on DIFF1 with a downward RE-WORD branch; M1 on DIFF2. Centre: drive rail F5 = 7 and F2 = 6 stacked in series through D2 (Vf 1.2) and D3 (Vf 2.0) into the series stack R1–R4 (R_cap 25 / R_policy 0 / R_context 30 / R_resource 20), an ammeter reading I_attention, M2 branching down to HOLD. Right: G1 six-input AND with M3 on its first input; G2 four-input AND with M4 and M5; G3 readiness AND; G4 arm AND; MUX1 with hold and arm inputs; D_out descending to the cast terminal. Bottom edge: FLT1 lowpass τ = 21 d from arm back to the practice rail, marked β = 0.15 and "the only upward path". TP1–TP4 flags.]]

---

### Parameter and BOM Table

Every value is a design choice made in this book, not a measurement.

| Ref | Component | Setting | Why | Failure at other values |
|---|---|---|---|---|
| F1 | Witness fuse | 0.30, `block_until_decomposed` | A third of the pull is where the audience sets the amplitude | 0.50: audience-carried desires pass. 0.10: operator stops logging honestly |
| M1 | Proxy monitor | premium ≥ 0.20 | Smallest gap surviving self-rating noise | Lower: proxies read as prime. Higher: real targets held undecided |
| Q1–Q8 | Verdict CJTs | β = 1.0 | **A gate that amplifies is not a gate** (S2) | β > 1 manufactures readiness; β < 1 hides drive that is really there |
| — | CJT `cutoff` | 0.05 | Bottom of the 0.05–0.20 band (Ch. 3.3), matching Ch. 13's AMPLIFY floor | 0.20: modest but real drive reads as no drive |
| D2, D3, D_out | Descent diodes | Vf 1.2, 2.0 | Chapter 8.2 drops, carried explicitly | Folded into `R`: margin overstated ~2× |
| R1–R4 | Constraint stack | 25 / 0 / 30 / 20 `Ω_c` | This operator, this desire (Ch. 4.4 ranges) | Treated as board constants: the gate stops reading the operator |
| M2 | Drive monitor | `I` ≥ 0.10 = 2 × cutoff | One bad day must not drop the stage into cutoff | 1.0×: fires today, not across a campaign |
| G1 | W-gate | 6-input AND | Possession is binary (S1) | Summed: 5-of-6 arms with the board selection missing |
| M3 | Idea clarity | ≥ 0.60 | Bottom of Ch. 13.6's TP1 band | Lower: conditions pass as scenes, TP1 reads low all campaign |
| M4 | Budget monitor | load ≤ 0.50 | Half the minutes leaves room for a bad week | 0.90: one missed session reads as insufficient drive |
| M5 | Arrival aversion | ≤ 0.25 | Above it the operation opposes itself | Ignored: casting harder amplifies both sides |
| FLT1 | Ledger lowpass | τ = 21 d, β = 0.15 | The only lawful `^O → ^P` path (Ch. 8.4) | Short τ or high β: one operation rewrites the substrate |

[[FIGURE 21-E: Assembly drawing — CCB-RPM layout with test-point callouts and a BOM box. Intake pad at the left edge marked STATED DESIRE, cast terminal at the right; components in signal order across four labelled zones A0 / D / W / P, with MUX1 and D_out in a fifth narrow zone; FLT1 along the lower edge running right to left to the practice-rail pad. TP flags with leader lines: TP1 at DIFF1's output, TP2 at the ammeter, TP3 at G3, TP4 at MUX1. Boxed BOM lower right listing F1, M1–M5, Q1–Q8, D2/D3/D_out, R1–R4, G1–G4, MUX1, FLT1 with settings. Corner panel: the four thresholds — witness 0.30 · premium 0.20 · I/cutoff 2.0 · load 0.50.]]

---

### Worked Example — Operation R-1

**The operator.** Two years, 1,100 logged hours. Bias rail per Chapter 7.2, τ = 3,333 hr:

```
  P_cap = 10 × (1 − e^(−1100/3333)) = 10 × (1 − 0.719) = 2.81
```

The rail sits at **2.8** of 10 — thinner than the Corvette operator's 4.3 (Ch. 13.6). It matters only as bias, and it is one more reason every verdict CJT here runs at unity.

**Stated desire.** *I run my own studio.*

**A0, pass 1.** Three readings, written before any subtraction: `0.82`, `0.44`, `0.74` — the condition being recognized as the person whose judgement decides, delivered without a studio.

```
  witness_load   = 0.82 − 0.44 = 0.38   ≥ 0.30  →  F1 BLOWS
  object_premium = 0.82 − 0.74 = 0.08   < 0.20  →  M1: PROXY_TARGET
```

Both instruments fire and they agree: the pull is largely audience, and the object stands in for standing. Decomposition breaks the wording into three parts — the work, the authority over the work, the standing of having one — and the third carries most of the amplitude. The operator re-words to the second.

**A0, pass 2.** *I decide what work I take and when.* Fresh readings `0.78`, `0.71`, `0.36`: witness load **0.07**, premium **0.42**. Both pass. No cast has fired; under `ε ∘ η = id` the first pass cost nothing but the readings.

**D-gate.** `V_drive` = F5 at 7 plus F2 at 6 = **13 `V_c`**. Origin `^C`, landing `^O`, so `ΣVf = 1.2 + 2.0 = 3.2`. Stack: `R_cap 25` (can do the work, has never priced or scheduled it), `R_policy 0`, `R_context 30` (the target is undefined for any actual week), `R_resource 20` (the hours exist; the buffer to refuse a job does not) — `R_in = 75`.

```
  I_attention = (13 − 3.2) / 75 = 9.8 / 75 = 0.1307 A_c
  margin      = 0.1307 / 0.05  = 2.61×      →  PASS
```

Run it against the *original* target and the gates couple visibly: `R_cap` 45 (never run a business) and `R_resource` 35 (capital) give `R_in = 110`, `I = 0.089`, margin **1.78× — MARGINAL**. The re-specification did not merely find a truer target; it removed 35 `Ω_c` of constraint. **An A0 failure presents downstream as resistance, which is why A0 is first.** Then the cheap repair Chapter 4.4 ranks first — one afternoon defining the week takes `R_context` from 30 to 10: `I = 9.8/55 = 0.178`, margin **3.56×**.

**W-gate.** Items 2–6 in hand. Item 1 reads **0.55** — `IDEA_UNFORMED`, hold. The cause is structural: the new target is a condition, not a scene. The operator gives it one — a specific Tuesday, one job declined, one accepted — and re-reads **0.71**. Six of six.

**P-gate.** Gnosis 2° reliably (Ch. 22.1). Plan: 4 operations, `t_op` 20 min, 72-hour spacing (Ch. 23.2), 12 days.

```
  planned = 4 × 20 = 80 min      available = 20 min/day × 12 = 240 min
  load    = 80 / 240 = 0.33      ≤ 0.50   →  pass
```

Access present; arrival aversion **0.18** — mild unease at the first declined job, not recoil. Pass.

**Arm.** `g_arm` closes, TP4 goes to `ARM`, `d_out` conducts, the cast fires. Two full passes, roughly fifty minutes on paper, zero casts — and it caught a target that would otherwise have run this chapter's opening log.

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `witness_load` | `pull_open − pull_private` | < 0.30. Read it beside M1: both failing at once is a re-wording, not a re-tuning |
| **TP2** | `path_in` | `I_attention`, `A_c` | ≥ 0.10 (2 × cutoff). Between 0.05 and 0.10 is MARGINAL — fires today, not across a campaign |
| **TP3** | `g_ready` | W `AND` P | Closed, or the *named* open input. "Not ready" is not a reading; which of the ten items is missing, is |
| **TP4** | `out` | The authorization edge | `HOLD` with its deciding number, or `ARM`. **The last reversible point on the board** |

Read them in order: is the desire mine, is there current, do I hold the schematic and the schedule — and only then arm. TP4 is the only reading you cannot take twice.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Gate skipped as ceremony** | The scan is treated as delay | A long log on one target, every confirmation 3° or worse, amplifier raised repeatedly | Run A0 on the logged target; expect the wording to fail |
| **A0 read after the fact** | Third rating written once the differential is known | Witness load landing just under 0.30 suspiciously often | Three ratings in ink before any subtraction |
| **Naive D-gate** | `V/R` computed without `ΣVf` | Margin overstated ~2×; a stage in cutoff on a board that "passed" | Subtract the descent chain; recompute every gate that crossed domains |
| **W-gate summed** | Six items scored and averaged | 5-of-6 arms, and the missing item is usually the board selection | `AND`. No partial credit (S1) |
| **Schedule at full budget** | Load planned near 1.0 | Campaign stalls in week two, reads as insufficient drive | Load ≤ 0.50; re-plan `n_ops`, not β |
| **Recoil cast through** | Arrival aversion above 0.25, run anyway | Confirmations arrive and are not felt; the operator undoes the arrival | Self-directed sub-operation first (Ch. 20, Ch. 23.3) |
| **Scan mistaken for undo** | Operator fires, then re-runs the gate "to take it back" | A second A0 reading that will not settle; two incomparable pass-1 rows | §21.5. Re-running is a new authorization, never a reversal |
| **Ledger over-gained** | τ shortened or feedback β raised | The substrate moves after single operations; held thresholds drift | τ = 21 d, β ≤ 0.3. Never remove the filter |

---

### What This Chapter Established

- **A0 is answered by subtraction, not introspection.** Two differentials — witness load (trip ≥ 0.30) and object premium (hold ≥ 0.20) — turn "is this really what I want" into two numbers whose common-mode bias cancels. The repair is `^6` decomposition, never `^3`.
- **The D-gate is Chapter 4 with a threshold on it.** `I = (V_drive − ΣVf)/R` against the downstream `cutoff`, 2× margin required. The Red Corvette's 1.52× is MARGINAL here — and Chapter 13.6 already called it thin.
- **The descent chain is where the margin goes.** `7/50 = 0.14` and `(7−3.2)/50 = 0.076` describe one operation; the naive form overstates by nearly double, and the error grows with how far the desire must descend.
- **W and P are `AND` gates, and that is a safety invariant.** Five-sixths of a schematic is not a circuit at 83%; it is undefined. The characteristic arming failure is 5-of-6 with the board selection wrong.
- **The gates are not independent.** Re-specifying at A0 removed 35 `Ω_c` from the stack and moved the D-gate from 1.78× to 2.61×. An unauthenticated desire presents downstream as resistance.
- **Scanning is free: `ε ∘ η = id`.** Descend into a prerequisite, find it lacking, return with the target unchanged. Two full passes cost the worked example fifty minutes and no casts.
- **Firing is not reversible: `η ∘ ε ≠ id`.** No inverse arrow, so no `undo` component and none in CCDL. An un-cast needs an `^O × ^P` ascent, and `β=∞` on a reverse path does not help — the arrow is undefined, not merely large.
- **What irreversibility does not mean.** Not that the outcome is guaranteed, not that consequences are permanent, not that prerequisites cannot decay, and nothing moral. **Decay is not inversion** — attrition is slow and visible as a drifting rail; reversal is unavailable at any speed.

---

### Exercises

**21.1** An operator rates `pull_open = 0.70`, `pull_private = 0.66`, `pull_condition = 0.58`. Compute both A0 quantities, give each verdict, and say which single instrument decided the gate.

**21.2** A desire originates at `^P` and lands at `^O`. Drives are F7 at 8 and F6 at 5; the stack is `R_cap 15`, `R_policy 40`, `R_context 10`, `R_resource 5`; the AMPLIFY stage has `cutoff = 0.10`. Compute `ΣVf`, `I_attention`, and the margin. Verdict? Now name the term you would repair first, and why it is *not* the largest one.

**21.3** Recompute 21.2 naively as `V_drive / R`. Give the margin both ways and the percentage error, then say in one sentence why the error grows with the origin domain.

**21.4** An operator holds all six W-gate items but reads Idea clarity at 0.52, and proposes weighting the gate so six-of-six at 0.52 clears. Write the two-sentence reply, name the invariant, and describe the operation that arms as a result.

**21.5** A campaign plans 6 operations of 25 minutes over 18 days against 15 available minutes per day. Compute the load, give the P-gate verdict, and state two re-plans that clear it — one changing `n_ops`, one changing the horizon.

**21.6** An operator fires a cast, regrets it within the hour, and asks for an un-cast stage. Answer in three parts: (a) which arrow of the section-retraction pair they are asking you to build; (b) why `β=∞` on it does not produce that arrow; (c) what you would build instead, and how it differs from a reversal.

**21.7** Design exercise. Add a re-entry counter to CCB-RPM that flags a target re-worded more than three times without a cast. Write the CCDL fragment, name the failure mode it catches, and name the opposite failure mode you have just installed.

*(Answers in **Appendix H**, worked in full. Every parameter here is a design choice; the A0 and clarity readings are operator self-reports on a stated scale, and the chapter never treats them as measurements of anything else.)*
