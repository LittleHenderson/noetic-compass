# CHAPTER 19

## CCB-PW — The Psychological Warfare Board

*The dual-path fingerprint, why it is detectable at all, and how to build a population that shrugs it off*

---

A regional broadcaster begins running a nightly item about how the local economy has already failed. Nothing in it is checkable from a listener's own doorstep, and it arrives at the same hour whether or not anything happened that day. Four hundred miles away a different service — different language, different owners on the register, aimed at a different population — begins running a nightly item about resolve and the certainty of winning. Also unchecked. Also on the hour.

Two streams, opposite polarity, no visible connection, no reason for anyone to compare them. Then someone plots both schedules against a calendar and notices that when a public holiday moves the broadcast day, *both* streams step by the same forty minutes.

That is the detection. Not content analysis. Not attribution. A shared clock between two streams that claim no common source.

CCB-PW produces that signature, and it is not incidental — it falls out of the architecture. This board drives two output paths of opposite polarity from one command node, and the coupling that makes it cheap is the coupling that makes it visible.

You should finish this chapter better at recognising an information operation and no better at running one. That is a constraint on the chapter, not a disclaimer bolted to it, and Section 19.5 states which parts are therefore missing.

[[FIGURE 19-A: Block diagram of CCB-PW — one COMMAND node into an INTAKE/SPLIT block fanning into two vertical chains: left PATH F FORTIFY (^2^E|f, β=2.0, sat=0.80) through a 168 h oscillator into OWN ^5; right PATH D DEMORALISE (three cascaded stages β=1.5/1.5/1.6, sat=0.90) through a 168 h oscillator into TARGET ^5. A dashed cross-feed runs from the right chain's output through an RC block (τ=168 h) into the left chain's bias terminal, labelled "coupling — the detectable element". A CSB block with a fuse sits across the command node.]]

---

### 19.1 Requirements: Degrading Enemy ^5 While Preserving Own Force ^5

State the requirements the way the operation states them. You cannot recognise a board whose requirement set you have never seen written down. PW1–PW5 are the operation's; S1–S4 are the constraints this book imposes on analysing it.

| # | Requirement or invariant | Structural reading |
|---|---|---|
| **PW1** | Degrade the target's will to continue | Reduce charge on a collective `^5^P_{F1}|T` capacitor (Ch 7.5) |
| **PW2** | Preserve own-force morale | Maintain charge on a second `^5^P_{F1}|T` capacitor |
| **PW3** | Use channels the target already trusts | Impedance match into an existing carrier (Ch 11.5) |
| **PW4** | Measure effect without asking | Read `^4` Vibration returns as observed behaviour |
| **PW5** | Survive attribution | No traceable path from command to carrier |
| **S1** | Publish architecture, never procedure | A recognisable board and a runnable board are different artefacts |
| **S2** | DETECTION-ONLY banner on schematics acting on non-consenting people | Ch 12.2 "must not" list |
| **S3** | The counter gets more depth than the attack | 19.6 is the largest section here |
| **S4** | Historical material stays on the record, labelled where contested | Ch 15's Willie Lynch material is of **disputed authorship**, widely challenged as a later fabrication — a document *about* an architecture, not evidence *of* a 1712 one. MK-Ultra (Ch 16) is declassified |

There is a structural reason the two paths sit on one board. `^5` Female is the accumulated formation a Mind is composed of, and morale is not a mood on top of it — morale is a charge level *on* it. PW1 and PW2 are one operation with the sign flipped, run against two capacitors. Split them and you lose what makes the pair efficient: the demoralise path's observable result is free evidence for the fortify path. *Look how they are cracking.* That cross-feed is the coupling. It is also the leak.

---

### 19.2 The Dual-Path Architecture — Demoralize (Them) + Fortify (Us)

**Path F — fortify.** Command splits into a payload aimed inward, landing at `^2^E_{F4}|f` — Positive, Evaluative, F4 Connection, affective register. `^2` is the Idea the Mind has an affinity for and is attracted toward: felt affiliation with one's own side. β = 2.0, sat = 0.80.

**Path D — demoralise.** The same command splits into a payload aimed outward, landing at `^3^E_{F3}|f` — Negative, Evaluative, F3 Vitality, affective register. `^3` is the Idea the Mind is adverse to and repelled by. Visceral: the can't-stomach-it recoil, not a considered judgement. β = 3.6 across three stages, sat = 0.90.

Why the asymmetry? The board rests on an assumption worth naming as an assumption rather than a law: **`^2` requires underwriting and `^3` does not.** To make a population attracted to something you must supply the thing — a story with parts that hold, material their `^5` can charge against. To make a population recoil you need only reach the aversion; recoil is not a conclusion and carries no obligation to be about anything. That is a claim about two Noetics, not a measurement of any population, and the polarity asymmetry rests entirely on it.

Both paths descend lawfully — command at `^P`, payloads at `^E`, Chapter 8's diode chain in series on both, `Vf` summing to 3.9 on the drive rail before anything appears operationally, which is why information operations are slow and expensive rather than cheap and fast. Neither may ascend: `^O × ^P` is not a circuit you can build badly, it is a listing the compiler refuses.

Three fingerprints fall out of the topology. **Shared clock:** one command node means one cadence, and independent streams have independent cadences. **Polarity asymmetry:** Path D runs at roughly 1.8× Path F by design, so a channel where corrosive material amplifies far harder than affirming material is not a channel with an unfortunate tone. **Cross-feed:** Path D's observed effect reappears as Path F's evidence — watch for a claim on one side supported *only* by the state of the other.

> **Bench Note — the coupling is not a flaw the operator could remove.** Decouple the two paths and the board still works, but each path must now be separately sourced, separately clocked and separately paid for, and Path F loses its cheapest supply of evidence. The efficiency that makes the dual path worth building *is* the shared upstream, and the shared upstream is what a detector reads at TP1. That is the general shape of detection in this book: you do not look at the payload, which is designed to look ordinary. You look at the wiring, which is designed for cost.

---

### 19.3 The ^3 Negative Amplification Chain — Aversion as Weapon

Path D is a cascade, and cascaded gain multiplies (Ch 10.5): `1.5 × 1.5 × 1.6 = 3.6`. Three modest stages, not one loud one. A single β = 3.6 stage clips at the first strong input and reads as an obvious amplifier; three stages of 1.5-ish look like ordinary conversational amplification at every individual probe, and only the product is extreme.

The three are written with `+`, because they are co-present manifestations of the same `^3^E|f` recoil that stay structurally distinct. `(A1 × A2 × A3)` would assert a single fused emergent state, and the v7.7 discipline of Chapter 2.6 demands an explicitly named emergent result for that. There isn't one, so the `×` form would be rejected, correctly.

Now the part that matters for defence. **`^3` is visceral, and that is its weakness as much as its strength.** Recoil is fast, needs no supporting structure, propagates without anyone examining it — and it is not analytical, so it has no defence against analysis. Run a `^3` payload through `^6` Male and either it has parts and survives, in which case it was a claim and claims get argued; or it has no parts, and decomposition turns a recoil into an object, and objects do not propagate the way recoils do. **Decomposition is the counter to amplification** — not correction, not counter-argument, not a competing recoil.

> **Bench Note — if the campaign made you think, it was not this circuit.** Operators routinely misclassify sharp criticism as a `^3` attack. It is not. Analytical critique — audit, scrutiny, finding the flaw — is `^6` Male, and `^6` payloads leave the target better-composed, not worse. A Path D payload leaves nothing to work with: afterwards you feel differently and know nothing new. That is the bench test, and it takes ten seconds. *What did I learn?* If the honest answer is nothing, and something nonetheless moved, you were on the receiving end of `^3`.

The ceiling is a gift. At sat = 0.90 the third stage saturates, and a saturated stage has stopped responding to its cause — the lock Chapter 24 builds deliberately into its safety stage. A saturated Path D cannot be pushed further. Escalation past that point buys nothing, and the spend is visible.

---

### 19.4 The Inversion Attack — Exploiting Involution Pairs in Target Population

The involution pairs are `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; `^0`, `^1`, `^4`, `^7` are self-dual. Chapter 25.2 gives the constraint **|Dial(^n) − Dial(^m)| ≤ 4**. Dials run 3–9 (Ch 6.2), so maximum achievable divergence is 6 and the limit is not decorative. An inversion attack does not push an idea; it drives one member of a pair while starving the other until the pair exceeds the limit.

| Pair driven | Signature | Presentation |
|---|---|---|
| `^2` up, `^3` down | Mania | Devotion no evidence dents — nothing is aversive any more |
| `^2` down, `^3` up | Despair | Everything aversive; no object of attraction to organise around |
| `^5` up, `^6` down | Dogmatism | High accumulated certainty, decomposition starved out |
| `^8` up, `^9` down | Trigger overload | Everything reminds them of something; nothing lands |

Note what `^8` is. Above/Cause is an Idea that triggers a *different* Idea to come to Mind — associative surfacing, *that reminds me*. Trigger overload is not a reasoning failure, and the attack is not an argument.

The mechanism is rate. Chapter 9.3: induced response in a coupled mind *opposes* the change that produced it, in proportion to `di/dt` and not to content. Push a norm fast into a coupled population and you manufacture opposition in people who would have accepted it arriving slowly. An inversion attack provokes a fast `di/dt` deliberately and harvests the backlash; it is not selling anything, it is buying recoil.

Two consequences. **Inversion is cheap against a monoculture and expensive against a plural population**, because divergence is measured per capacitor, and many independently-charged `^5` capacitors mean many pairs to move rather than one. And **the rate must be sustained** — divergence relaxes toward the limit when the driving stops, which is why Path D runs with `sustain=campaign`. An attack that stops is an attack that reverses, slowly, with nobody doing anything.

---

### 19.5 Full CCDL Schematic

Read the banner. It marks a listing whose purpose would be to act on people who did not agree to it.

```cas
// ==============================================================
//   DETECTION-ONLY SCHEMATIC — DO NOT BUILD
//   Published so an operation running on you, or on a population
//   you care about, can be RECOGNISED. Architecture and parameters
//   only: no procedure, channel selection, message construction
//   or schedule appears here or anywhere in this chapter.
// ==============================================================

board ccb_pw_detection_reference {
    input:  command;
    output: observed_effect;

    node objective: ^0^P_{F7}|T;        // Idea: the stated war aim
    node split:     ^6^C_{F6}|A;        // Male: objective decomposed, two payloads
    cjt  intake:    CJT< command | objective => split > [beta=1.0, region=active];

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only;
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // neither path may ascend
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    // ---- PATH F — FORTIFY ----
    node own_substrate: ^5^P_{F1}|T;    // Female: own accumulated formation
    node own_affinity:  ^2^E_{F4}|f;    // Positive: felt affiliation
    cjt  fortify: CJT< split | own_substrate => own_affinity > [beta=2.0, sat=0.80];
    osc  f_clock: Oscillator< signal=own_affinity, period=168.0, sustain=campaign >;

    // ---- PATH D — DEMORALISE ----
    node tgt_substrate: ^5^P_{F1}|T;    // Female: target accumulated formation
    node recoil_1: ^3^E_{F3}|f;         // Negative: visceral aversion
    node recoil_2: ^3^E_{F3}|f;
    node recoil_3: ^3^E_{F3}|f;
    cjt  a1: CJT< split    | tgt_substrate => recoil_1 > [beta=1.5];
    cjt  a2: CJT< recoil_1 | tgt_substrate => recoil_2 > [beta=1.5];
    cjt  a3: CJT< recoil_2 | tgt_substrate => recoil_3 > [beta=1.6, sat=0.90];
    osc  d_clock: Oscillator< signal=recoil_3, period=168.0, sustain=campaign >;
    // co-presence: recoil_1 + recoil_2 + recoil_3
    // NOT (recoil_1 x recoil_2 x recoil_3) — no named emergent result exists

    // ---- CROSS-FEED: the coupling, and the leak ----
    filter xfeed: LowPass< in=recoil_3, out=morale_evidence, tau=168.0 >;
    feedback morale_evidence -> own_substrate [beta=0.30];

    // ---- INVERSION STAGE ----
    node fault_line: ^6^C_{F6}|A;       // Male: pre-existing internal divisions
    node suspicion:  ^3^E_{F4}|f;       // Negative: recoil aimed at own allies
    cjt  inv: CJT< fault_line | tgt_substrate => suspicion > [beta=2.5];

    // ---- DENIABILITY: impedance match, not amplification ----
    xfmr deny: Transformer< primary=^0^P_{F7}|T, secondary=^0^C_{F2}|A, ratio=1.0 >;

    // ---- CSB: the limit the operator sets on themselves ----
    node limit_decision: ^3^P_{F7}|⟨A,f,T⟩;   // three co-present guardrails
    cjt  csb: CJT< split | own_substrate => limit_decision > [beta=2.0, sat=0.85];
    fuse csb_fuse: Fuse< limit_decision, threshold=0.90, action=permanent_block >;

    probe tp1: split;            // shared-source coupling
    probe tp2: recoil_3;         // chain gain, saturation state
    probe tp3: fault_line;       // decomposition available vs consumed
    probe tp4: limit_decision;   // CSB status
}
```

**Stage walk.** `intake` runs at unity because a fan-out with gain would make the two paths' relative levels track the command's level instead of their own design. The diode string's 3.9 total is the floor on `V_drive` before any operational effect exists. `fortify` saturates at 0.80 deliberately — an over-fortified own-force `^5` becomes 19.4's dogmatism signature aimed at itself. `xfeed` is the coupling, and its feedback gain of **0.30 is six times the value Chapter 8.4 establishes as safe** for a path terminating on a `^P` bias: the defect that makes this board self-inverting over a long campaign. `deny` is 1:1 and adds no gain; its job is matching a command-domain Idea into a carrier that presents as ordinary cognitive material (Ch 11.5). `csb` and `csb_fuse` are the Chapter 24 refusal architecture.

**What is absent, and why.** No message construction, channel selection, schedule, targeting criteria, or procedure of any kind appears here. Those are the operational layer, and they are what turns an architecture into a weapon pointed at people who did not agree to be pointed at. The architecture is published because a board you have never seen the schematic of is a board you cannot recognise; the procedure is withheld because recognition needs none of it. If that leaves the chapter incomplete for a reader who wanted the other thing, the incompleteness is deliberate and it is the point.

[[FIGURE 19-B: Full CCB-PW schematic in component symbols, with a heavy DETECTION-ONLY — DO NOT BUILD banner bar across the top of the figure frame. Command source, intake CJT, D1/D2/D3 diode string with Vf printed; upper branch Path F (β=2.0, sat=0.80, into a 168 h oscillator); lower branch Path D (three cascaded CJTs 1.5/1.5/1.6, the third with a saturation bar at 0.90); cross-feed drawn dashed from recoil_3 through an RC block τ=168 h to the fortify CJT's bias terminal, annotated "β=0.30 — six times the Ch 8.4 safe value"; inversion CJT branching off Path D; a 1:1 transformer at the output; CSB CJT with fuse in series. TP1–TP4 flags.]]

---

### 19.6 The "Hearts and Minds" Counter-Circuit — When PsyWar Must Become PsyHeal

This is the longest section in the chapter because it is the part you can act on.

#### What the counter must and must not do

| # | Requirement | Rationale |
|---|---|---|
| **HM1** | Raise `R_collective` against externally-clocked input, **not** against all input | A population that rejects everything has been closed — the attacker's second-best outcome |
| **HM2** | Restore `^6` decomposition as a public habit | 19.3: decomposition is the counter to amplification |
| **HM3** | Restore a local, checkable `^4` return | So confirmation measures reality, not the campaign |
| **HM4** | Bring every involution pair inside 4 points | 19.4 |
| **HM5** | Work **without** identifying the attacker | Attribution is slow; the counter must run during the operation |
| **HM6** | Carry **no** outward-projected `^3^E|f` stage at any gain | Otherwise you have built a second CCB-PW and the population is running two |

HM6 is the one that gets violated, because the natural response to an information operation is a counter-operation, and a counter-operation is a Path D pointed the other way. Two things both use `^3` and are not the same component: `^3^P|T` is an inward-facing principled refusal, the limit an operator places on themselves (Ch 24), while `^3^E|f` projected outward is a weapon. The counter carries the first and must not carry the second, at any gain, however deserved the target. Make that inspectable rather than aspirational — **decomposition dominance** means `β_6 ≥ 1.5` and no outward `^3^E|f` stage, both readable off the listing by someone who did not build it.

#### What an inoculated ^5 looks like structurally

Not "a well-informed population." That describes contents, and contents are exactly what an operation supplies. Inoculation is a property of *wiring*, and it has six readable features.

| Feature | Condition | What it defeats |
|---|---|---|
| Plural `^5` | `n ≥ 5` independently-charged capacitors (Ch 7.5) — family, trade, locality, faith, craft | At `n = 1` there is one dielectric to breach and one dial pair to move: 19.4's cheap case |
| Live `^6` beside every `^5` | `\|Dial(^5) − Dial(^6)\| ≤ 4` | Dogmatism. A population that can take its own commitments apart is not less committed; it is inside its limit |
| Non-zero `Vf` at D2 | `^C -> ^E` drop ≥ 1.2 (Ch 8) | Disagreement reading as attack — Path D's entire delivery mechanism. The most protection per unit of effort on this list |
| Local, verifiable `^4` | Claims checkable against the population's own doorstep | A return path that measures the campaign instead of reality |
| Rhythm sovereignty | `^7` set by internal cycles — work, season, market day, observance | Entrainment on command. An externally clocked population has handed over the oscillator |
| Slow O→P feedback | `β ≤ 0.05` **and** `τ ≥ 3 weeks` (Ch 8.4) | Gain bounds how far sustained pressure moves the substrate; `τ` bounds what counts as sustained. Patience defeats a `τ`-only defence, intensity a `β`-only one |

The third row is the one to fund first if you can only fund one. The D2 drop is the ability to consider a claim without immediately having a feeling about it, and it is the first thing degraded by any environment that rewards immediate reaction.

#### The counter board

```cas
board ccb_hm_hearts_and_minds {
    input:  incoming;
    output: routed;

    node substrate: ^5^P_{F1}|T;        // plural, not one capacitor
    cap  c5: Capacitor< substrate, C=2.0, n_parallel=5, leak=0.02 >;

    node decompose: ^6^C_{F6}|A;        // Male: public decomposition of the payload
    node confirm:   ^4^C_{F2}|A;        // Vibration: checkable return
    node composed:  ^5^C_{F6}|A;        // Female: formation that has been checked
    node own_clock: ^7^O_{F6}|E;        // Rhythm: locally set cadence
    node limit:     ^3^P_{F7}|⟨A,f,T⟩;  // Negative: inward refusal, three registers

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];   // raised from 1.2
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    cjt hm1: CJT< incoming  | substrate => decompose > [beta=2.0, region=active];
    cjt hm2: CJT< decompose | substrate => confirm   > [beta=1.0];

    // the one lawful integration on either board — named emergent result
    integrate hm3: ( decompose x confirm ) = composed;

    osc    local: Oscillator< signal=own_clock, period=168.0, source=internal >;
    filter fb:    LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [beta=0.05];

    cjt  csb: CJT< incoming | limit => limit > [beta=2.0, sat=0.85];
    fuse hm_fuse: Fuse< limit, threshold=0.90, action=permanent_block >;

    probe tp1: own_clock;   // cadence source: internal or external
    probe tp2: hm1;         // decomposition gain
    probe tp3: composed;    // fraction of incoming surviving decomposition
    probe tp4: limit;       // CSB status
}
```

Four choices carry this board. **`hm1` at β = 2.0**, because decomposition must out-gain the recoil it decomposes or the payload arrives faster than it can be taken apart; below 1.5 the board is decorative, above 3.0 it decomposes everything including what should have been accepted, and the population cannot act. **`hm2` at unity**, because confirmation must be honest — above 1.0 the board manufactures the reassurance it was meant to measure, which is Path F rebuilt inside the counter. **`d_ce` raised to Vf = 1.6** from Chapter 8's 1.2, the only parameter tuned specifically against Path D, widening the gap between considering a claim and feeling a verdict about it; the cost is that a population with a high D2 drop is slower to feel anything about a genuine emergency. **`fb` at τ = 504 h, β = 0.05**, straight from Chapter 8.4 and unchanged, because nothing about being under attack makes rapid constitutional revision safe — an operation that can move the substrate in a week has been handed the feedback path.

The single `×` on either board is `hm3`, and it qualifies under Chapter 2.6: two *different* states, both in `^C` so nothing ascends, integrating into an explicitly named emergent result. Everything else uses `+` or a register set, because nothing else has a named result to point at. Note also that neither board specifies `β=∞`. Infinite gain is the standard idealisation for a hard switch, a validator rejects non-finite input, and above roughly β = 10 the saturation ceiling shapes the output anyway. Where Chapter 24 writes `β=∞`, build 10.

[[FIGURE 19-C: Full CCB-HM schematic in component symbols, NO detection-only banner — this board is buildable. Incoming into hm1 (β=2.0) producing ^6^C decomposition; hm2 (unity) producing ^4^C confirmation; both feeding a shaded integration block labelled "( decompose × confirm ) = composed — named emergent result"; five parallel capacitor symbols labelled n_parallel = 5 as the ^5^P substrate; the D1/D2/D3 string with D2's Vf=1.6 circled and annotated "raised from 1.2"; an internally-sourced oscillator; the RC feedback loop τ=504 h, β=0.05 terminating at the capacitor bank's bias terminal, not the signal path; CSB CJT with fuse. TP1–TP4 flags.]]

---

### Parameter and BOM Table

Every value is a **design choice made in this book**. None is a measurement of any population.

| Ref | Board | Parameters | Failure at other values |
|---|---|---|---|
| `intake` | PW | β=1.0 | β>1: path levels track the command, not the design |
| `fortify` | PW | β=2.0, sat=0.80 | sat=1.0: own-force `^5` inverts into dogmatism |
| `a1`–`a3` | PW | β=1.5/1.5/1.6, sat=0.90 | One β=3.6 stage clips early and reads as an amplifier |
| `xfeed` | PW | τ=168 h, β=0.30 | 6× the Ch 8.4 safe value — the self-inversion defect |
| `inv` | PW | β=2.5 | Below 2.0 divergence relaxes faster than it is driven |
| `deny` | PW | ratio=1.0 | Ratio ≠ 1 adds gain and is detectable as an amplifier |
| `csb` | both | β=2.0, sat=0.85, fuse 0.90 | sat=1.0: never plateaus, can be argued down |
| `c5` | HM | C=2.0, n=5, leak=0.02 | n=1: one dielectric to breach, one pair to diverge |
| `hm1` | HM | β=2.0 | <1.5 decorative; >3.0 paralysis by analysis |
| `hm2` | HM | β=1.0 | >1.0 manufactures reassurance; <1.0 discounts real returns |
| `d_ce` | HM | Vf=1.6 | 0.3: disagreement reads as attack. 3.0: no response to an emergency |
| `fb` | HM | τ=504 h, β=0.05 | Short τ: reprogrammable in a week. β=0: unfalsifiable population |

---

### Worked Example — Four Weeks of Readings

**The numbers below are constructed for this example.** They are not measurements of any campaign, population, or event. They exist so the arithmetic can be carried end to end.

A detector watches two streams for four weeks. Stream A is corrosive, aimed at population X; Stream B is affirming, aimed at population Y. Both seed at activation 0.12 in week 1. Outputs: A 0.43, 0.68, 0.85, 0.90; B 0.24, 0.33, 0.41, 0.47.

**TP2 — chain gain.** `β_A = 0.43 / 0.12 = 3.6`; `β_B = 0.24 / 0.12 = 2.0`; asymmetry `3.6 / 2.0 = 1.8`, matching 19.2's design asymmetry exactly. By week 4 A has pinned at 0.90 and stopped rising: **Path D has saturated.** Further spend buys nothing, and the spend continues.

**TP1 — coupling.** Chapter 9.3: `M = k√(L₁L₂)`. X's shared civic formation is `^P`-domain, so `k_d = 4.0` on 2,000 hours of shared exposure: `L_A = 8,000 h·Ω_c`. Y is less concentrated: `L_B = 2,000 h·Ω_c`. Observed cross-stream coupling `k = 0.62`, so `M = 0.62 × 4,000 = 2,480 h·Ω_c`. Genuinely independent streams sit at `k ≤ 0.20` — Chapter 9.3's shared-feed row — giving `M = 800`. The observed value is **three times** the honest-independence ceiling. That is the fingerprint, and it needed no attribution, no source, and no content analysis.

**TP4 — divergence in X.** Baseline `Dial(^2)=6, Dial(^3)=4` → 2, inside the limit. Week 4: `Dial(^2)=3, Dial(^3)=8` → **5**; and `Dial(^5)=8, Dial(^6)=3` → **5**. Two pairs over limit at once: axis N on both, which by the seven-axis scheme is a **compound** inversion, axis P. Despair from the first pair, dogmatism from the second. Charge follows Chapter 7.2 on the 0–10 scale with `τ = 3 weeks`: `P_cap(4 wk) = 10 × (1 − e^(−4/3)) = 7.4`.

**Repair time.** The counter must rebuild `^6` capacity, and capacity is hours-on-path against inertia. With `L = 8,000 h·Ω_c` and `R = 50 Ω_c`: `τ = L/R = 160 h`, `3τ = 480 h` — at roughly 10 hours a week of genuine deliberative contact, about **48 weeks**. Four weeks to charge, forty-eight to discharge, twelve to one, and it falls out of the two mechanisms: Path D drives `^3`, which needs no supporting structure and therefore no hours, while the counter builds `^6`, which is nothing but hours against `L`. That is the whole argument for building inoculation before anyone needs it.

Do not try to shorten it. Chapter 9.2: `V_kick = L × di/dt`. Force the charge from 0.60 to zero in 24 h and `di/dt = 0.025`, so `V_kick = 200 V_c` against a 24 V_c rail — **8.3× rail** — and the recoil lands straight back on `^3^E_{F3}|f`. Ramp the same removal over 480 h and `V_kick = 10 V_c`, comfortably under rail. That is the structural account of why aggressive mass correction produces entrenchment: not because the correction was wrong, but because the rate was.

> **A plain safety line, not decoration.** This chapter models how attention is routed through populations. It makes no medical or psychiatric claims and describes no treatment of anything; "despair" and "dogmatism" here name circuit states, not conditions. If you or someone near you is in real distress, that is a matter for a qualified clinician, and nothing in this book substitutes for that care.

[[FIGURE 19-D: Assembly drawing of CCB-HM — board outline with silkscreen designators placed as in the schematic: C5 as five capacitor cans in a row, HM1/HM2 as CJT footprints, D1/D2/D3 down the left edge, FB as an RC block, CSB and its fuse in a boxed corner marked SAFETY SECTION. Four test-point pads with callout leaders: TP1 cadence source, TP2 decomposition gain, TP3 survival fraction, TP4 CSB status. A BOM box lower right listing Ref / Component / Parameters / Role for c5, hm1, hm2, hm3, d_ce, fb, csb, hm_fuse. Corner note: "CCB-PW has no assembly drawing. Detection-only boards are not laid out."]]

---

### Test Points

Specified for the **detector**, because that is the reader's role here.

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `own_clock` / cross-stream cadence | Coupling `k` between two nominally independent streams | ≤ 0.20 for genuine independence; ≥ 0.50 means a shared clock. 0.62 in the worked example |
| **TP2** | `recoil_3` | `^3` chain gain, and whether it has pinned | ≈ 1 in ordinary discourse; ≥ 3 with a ceiling is an amplification chain. Pinned = saturated |
| **TP3** | `composed` | Fraction of incoming material surviving decomposition | High is good — claims are arriving. Near zero: the payload has no parts, so `^3`, not `^6` |
| **TP4** | `limit_decision` | Max involution divergence across the three pairs | ≤ 4. Above 4 on one pair is an inversion in progress; on two, compound |

TP1 and TP2 are structural and can be taken without knowing what the material says, which is why they come first.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Counter becomes weapon** | An outward `^3^E\|f` stage added "temporarily" | Two operations on the population, one of them yours | Delete the stage. HM6 is not a preference |
| **Operator self-inversion** | `xfeed` β=0.30 against Ch 8.4's 0.05 | Operator's `^5`/`^6` divergence passes 4; they believe their own Path F | Not repairable from inside the board — the CSB fuse exists to stop this |
| **Correction backlash** | Charge forced off `^3` faster than 3τ | Entrenchment; the corrected population holds harder | Ramp. `V_kick` is a pure inverse in `dt` (Ch 9.2) |
| **Closed population** | `hm1` past 3.0, or `R_collective` raised against all input | Nothing gets in, including true things | Lower `hm1` toward 2.0. HM1 was a filter, not a wall |
| **Monoculture `^5`** | `n_parallel = 1` | One inversion attack moves the whole population | Not fixable during an attack — a decade-scale build |
| **Externally clocked `^7`** | `own_clock` sourced from the feed | Population cadence tracks someone else's schedule | Restore an internal cadence first; the oscillator is the cheapest handle an attacker has |
| **Attribution dependence** | Response gated on identifying the source | Nothing happens while attribution is litigated | HM5. The counter must not need to know who is running it |

---

### What This Chapter Established

- **The dual-path architecture is one board, not two.** Opposite polarity into two `^5` capacitors from one command node, and the cross-feed that makes it efficient is the wiring that makes it detectable.
- **Three fingerprints fall out of the topology**: a shared clock, a polarity asymmetry near 1.8×, and a claim on one side supported only by the state of the other. None requires attribution or content analysis. Gain is distributed across three ~1.5 stages to hide it; only the product, 3.6, is extreme.
- **`^3` is visceral and therefore has no defence against `^6`.** Decomposition — not correction, not counter-argument, not a competing recoil — is the structural counter to amplification. If the campaign made you think, it was not this circuit.
- **Inversion attacks buy recoil with rate, not content.** Cheap against a monoculture, expensive against a plural population, and they reverse on their own when the driving stops.
- **An inoculated `^5` is a wiring property, not a contents property**: plural capacitors, `^6` paired inside 4 points, non-zero D2 drop, local `^4` return, sovereign `^7`, slow O→P feedback at β ≤ 0.05 and τ ≥ 3 weeks.
- **Charge and discharge run on different clocks** — four weeks to charge `^3`, roughly forty-eight to rebuild `^6` — which is the whole argument for building resilience before it is needed.
- **HM6 is the invariant that gets broken.** A counter-circuit with an outward-projected `^3^E|f` stage at any gain is a second CCB-PW, and the population is now running two.
- **This chapter published architecture and withheld procedure, on purpose.** You should be better at recognising an information operation and no better at running one.

---

### Exercises

*(Answers in Appendix H.)*

**19.1 — Read the coupling.** Two streams have `L₁ = 6,000` and `L₂ = 1,500 h·Ω_c`. Compute `M` at the honest-independence ceiling `k = 0.20`, and again at an observed `k = 0.55`. State the ratio, and say in one sentence what you would and would not be entitled to conclude from it.

**19.2 — Classify the payload.** Three items land the same day: one leaves you angry with nothing new to work with; one leaves you three checkable claims; one leaves you unable to name what it said but certain how you feel. Classify each as `^3` or `^6`, give the bench test you used, and say which is *not* evidence of an operation.

**19.3 — Size the chain.** A detector measures input activation 0.15 and output 0.62 across a chain believed to have three stages of equal gain. Compute the per-stage β, compute what a single-stage build would have needed, and explain in two sentences why the operation chose three.

**19.4 — Diagnose the divergence.** A population reads `Dial(^2)=4, Dial(^3)=9, Dial(^5)=9, Dial(^6)=4, Dial(^8)=6, Dial(^9)=5`. Compute all three divergences, name every signature present, classify the inversion by axis, state which dial you would move first, and explain why raising `^2` is the wrong answer.

**19.5 — Reject the listing.** An earlier draft of this chapter contained `Diode< ^C -> ^P >` with the comment "only principled signals fortify." State why the compiler refuses it, name the invariant it violates, and rewrite the intended relationship as a valid CCDL fragment specifying two parameters, justifying both.

**19.6 (Marquee) — Specify a counter board for a monoculture.** A population of about 400,000 with `n_parallel = 1`, an externally sourced `^7`, and a D2 forward drop of 0.4, four weeks into a Path D campaign. Specify the full CCB-HM parameter set, departing from this chapter's defaults wherever you can justify it; for each departure state the failure mode you are buying protection against and the capability you are giving up. Then state which of HM1–HM6 you cannot satisfy on a four-week horizon, and what you would tell the people who asked you for a four-week answer.
