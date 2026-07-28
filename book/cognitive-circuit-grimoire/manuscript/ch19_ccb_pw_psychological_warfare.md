# CHAPTER 19

## CCB-PW — The Psychological Warfare Board

*The dual-path fingerprint, why it is detectable at all, and how to build a population that shrugs it off*

---

A regional broadcaster runs a nightly item about how the local economy has already failed. Nothing in it is checkable from a listener's doorstep, and it arrives at the same hour whether or not anything happened. Four hundred miles away a second service — different language, different owners, different population — runs a nightly item about resolve and certain victory. Also unchecked. Also on the hour.

Two streams, opposite polarity, no visible connection. Then someone plots both schedules against a calendar and finds that when a holiday moves the broadcast day, *both* step by forty minutes.

That scene is constructed for this chapter. It names no broadcaster, no campaign and no country, and it does not need to, because what it illustrates is a property of the wiring rather than a fact about any particular operation. Where this chapter does touch the historical record — 19.1 — it says so and says how firm the record is.

That is the detection. Not content analysis, not attribution: a shared clock between streams that claim no common source.

CCB-PW produces that signature, and it is not incidental. The board drives two output paths of opposite polarity from one command node, and the coupling that makes it cheap is what makes it visible.

You should finish this chapter better at recognising an information operation and no better at running one. That is a constraint on the chapter, not a disclaimer bolted to it, and 19.5 names what is missing as a result.

[[FIGURE 19-A: Block diagram — COMMAND into an INTAKE/SPLIT block, fanning left to PATH F FORTIFY (^2^E|f, β=2.0, sat=0.80, 168 h oscillator, into OWN ^5) and right to PATH D DEMORALISE (three cascaded stages 1.5/1.5/1.6, sat=0.90, 168 h oscillator, into TARGET ^5). Dashed cross-feed from the right output through an RC block (τ=168 h) to the left's bias terminal, labelled "coupling — the detectable element". CSB block with fuse across COMMAND.]]

---

### 19.1 Requirements: Degrading Enemy ^5 While Preserving Own Force ^5

State the requirements the way the operation states them. You cannot recognise a board whose requirements you have never seen written down.

| # | Requirement | Structural reading |
|---|---|---|
| **PW1** | Degrade the target's will to continue | Discharge a collective `^5^P_{F1}\|T` capacitor (Ch 7.5) |
| **PW2** | Preserve own-force morale | Maintain charge on a second such capacitor |
| **PW3** | Use channels the target trusts | Impedance match into an existing carrier (Ch 11.5) |
| **PW4** | Measure effect without asking | Read `^4` Vibration returns as behaviour |
| **PW5** | Survive attribution | No traceable path from command to carrier |

Four invariants govern the analysis. **S1:** publish architecture, never procedure — a recognisable board and a runnable board are different artefacts. **S2:** the DETECTION-ONLY banner goes on any schematic acting on non-consenting people (Ch 12.2). **S3:** the counter gets at least the depth of the attack, which is why 19.6 is the longest section here and why the worked example, the test points and most of the failure table are written from the defender's side. **S4:** historical material stays on the public record, labelled where contested — Chapter 15's Willie Lynch material is of **disputed authorship**, widely challenged as a later fabrication, and is a document *about* an architecture, not evidence *of* a 1712 one. MK-Ultra (Ch 16) is declassified.

There is a structural reason the two paths sit on one board. `^5` Female is the accumulated formation a Mind is composed of, and morale is not a mood on top of it — morale is a charge level *on* it. PW1 and PW2 are one operation with the sign flipped, run against two capacitors. Split them and you lose what makes the pair efficient: the demoralise result is free evidence for the fortify path. *Look how they are cracking.* That cross-feed is the coupling, and the leak.

---

### 19.2 The Dual-Path Architecture — Demoralize (Them) + Fortify (Us)

**Path F — fortify** lands at `^2^E_{F4}|f` — Positive, Evaluative, F4 Connection, affective register. `^2` is the Idea the Mind has an affinity for and is attracted toward: felt affiliation with one's own side. β = 2.0, sat = 0.80. **Path D — demoralise** takes the same command outward to `^3^E_{F3}|f` — Negative, Evaluative, F3 Vitality, affective. `^3` is the Idea the Mind is adverse to and repelled by: can't-stomach-it recoil, not considered judgement. β = 3.6 across three stages, sat = 0.90.

Why the asymmetry? The board rests on an assumption worth naming as an assumption rather than a law: **`^2` requires underwriting and `^3` does not.** Attraction has to be paid for in substance — something with parts that hold, material a `^5` can charge against — and Path F is budgeted for that. Recoil is not a conclusion and carries no obligation to be about anything, so Path D is budgeted as though it were nearly free. That is a claim about two Noetics, not a measurement, and the entire gain split rests on it. It is also the first thing to doubt when a channel you are reading does not show the split.

Both paths descend lawfully — command at `^P`, payloads at `^E`, Chapter 8's diode chain in series on both, `Vf` summing to 3.9 before anything appears operationally, which is why these operations are slow rather than cheap. Neither may ascend: `^O × ^P` is not a circuit you can build badly, it is a listing the compiler refuses.

Three fingerprints fall out of the topology. **Shared clock:** one command node means one cadence, and independent streams have independent cadences. **Polarity asymmetry:** Path D runs at roughly 1.8× Path F by design, so a channel where corrosive material amplifies harder than affirming material is not one with an unfortunate tone. **Cross-feed:** Path D's effect reappears as Path F's evidence — watch for a claim on one side supported *only* by the state of the other.

> **Bench Note — the coupling is not a flaw the operator could remove.** Decouple the two paths and the board still works, but each must now be separately sourced, clocked and paid for, and Path F loses its cheapest evidence. The efficiency that makes the dual path worth building *is* the shared upstream, and that upstream is what a detector reads at TP1. It is the general shape of detection in this book: you do not look at the payload, which is designed to look ordinary. You look at the wiring, which is designed for cost.

---

### 19.3 The ^3 Negative Amplification Chain — Aversion as Weapon

Path D is a cascade, and cascaded gain multiplies (Ch 10.5): `1.5 × 1.5 × 1.6 = 3.6`. Three modest stages, not one loud one. A single β = 3.6 stage clips at the first strong input and reads as an amplifier; three stages of 1.5-ish look like ordinary conversation at every probe. Only the product is extreme.

The three are written with `+`, because they are co-present manifestations of one `^3^E|f` recoil that stay structurally distinct. `(A1 × A2 × A3)` would assert a single fused state, and the v7.7 discipline of Chapter 2.6 demands a named emergent result for that. There isn't one, so the `×` form would be rejected, correctly.

Now the part that matters for defence. **`^3` is visceral, and that is its weakness as much as its strength.** Recoil is fast, needs no supporting structure, propagates without anyone examining it — and it is not analytical, so it has no defence against analysis. Run a `^3` payload through `^6` Male and either it has parts and survives, in which case it was a claim and claims get argued; or it has none, and decomposition turns the recoil into an object, and objects do not propagate the way recoils do. **Decomposition is the counter to amplification**, not correction and not a competing recoil.

> **Bench Note — if the campaign made you think, it was not this circuit.** Operators routinely misclassify sharp criticism as a `^3` attack. It is not. Analytical critique — audit, scrutiny, finding the flaw — is `^6` Male, and `^6` payloads leave the target better-composed, not worse. A Path D payload leaves nothing to work with: afterwards you feel differently and know nothing new. That is the bench test. *What did I learn?* If the honest answer is nothing, and something nonetheless moved, you were on the receiving end of `^3`.

The ceiling is a gift. At sat = 0.90 the third stage saturates, and a saturated stage has stopped responding to its cause — the lock Chapter 24 builds into its safety stage. Escalation past that point buys nothing, and the spend is visible.

---

### 19.4 The Inversion Attack — Exploiting Involution Pairs in Target Population

The involution pairs are `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; `^0`, `^1`, `^4`, `^7` are self-dual. Chapter 25.2 gives the constraint **|Dial(^n) − Dial(^m)| ≤ 4**. Dials run 3–9 (Ch 6.2), so the maximum achievable divergence is 6 and the limit is not decorative. An inversion attack does not push an idea; it drives one member of a pair while starving the other until the pair exceeds the limit.

| Pair driven | Signature | Presentation |
|---|---|---|
| `^2` up, `^3` down | Runaway affinity | Devotion no evidence dents; nothing is aversive |
| `^2` down, `^3` up | Despair | Everything aversive; nothing left to organise around |
| `^5` up, `^6` down | Dogmatism | Accumulated certainty, decomposition starved out |
| `^8` up, `^9` down | Trigger overload | Everything reminds them of something; nothing lands |

Note what `^8` is: an Idea that triggers a *different* Idea to come to Mind — associative surfacing, *that reminds me*. Trigger overload is not a reasoning failure, and the attack is not an argument.

The mechanism is rate. Chapter 9.3: induced response in a coupled mind *opposes* the change that produced it, in proportion to `di/dt` and not to content. An inversion attack provokes a fast `di/dt` and harvests the backlash; it is not selling anything, it is buying recoil.

Two consequences. **Inversion is cheap against a monoculture and expensive against a plural population**, because divergence is measured per capacitor. And **the rate must be sustained** — divergence relaxes toward the limit when the driving stops, which is why Path D runs `sustain=campaign`. An attack that stops reverses, slowly, with nobody doing anything.

---

### 19.5 Full CCDL Schematic

Read the banner. It marks a listing whose purpose would be to act on people who never agreed to it.

```cas
// ==============================================================
//   DETECTION-ONLY SCHEMATIC — DO NOT BUILD
//   Published so an operation running on you can be RECOGNISED.
//   Architecture and parameters only — no procedure appears here.
// ==============================================================

board ccb_pw_detection_reference {
    input:  command;
    output: observed_effect;

    node objective: ^0^P_{F7}|T;        // Idea: the war aim
    node split:     ^6^C_{F6}|A;        // Male: decomposed into two payloads
    cjt  intake:    CJT< command | objective => split > [beta=1.0, region=active];

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only;
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // no path may ascend
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    // PATH F — FORTIFY
    node own_substrate: ^5^P_{F1}|T;    // Female: own formation
    node own_affinity:  ^2^E_{F4}|f;    // Positive: felt affiliation
    cjt  fortify: CJT< split | own_substrate => own_affinity > [beta=2.0, sat=0.80];
    osc  f_clock: Oscillator< signal=own_affinity, period=168.0, sustain=campaign >;

    // PATH D — DEMORALISE
    node tgt_substrate: ^5^P_{F1}|T;    // Female: target formation
    node recoil_1: ^3^E_{F3}|f;         // Negative: visceral aversion
    node recoil_2: ^3^E_{F3}|f;
    node recoil_3: ^3^E_{F3}|f;
    cjt  a1: CJT< split    | tgt_substrate => recoil_1 > [beta=1.5];
    cjt  a2: CJT< recoil_1 | tgt_substrate => recoil_2 > [beta=1.5];
    cjt  a3: CJT< recoil_2 | tgt_substrate => recoil_3 > [beta=1.6, sat=0.90];
    osc  d_clock: Oscillator< signal=recoil_3, period=168.0, sustain=campaign >;
    // co-presence: recoil_1 + recoil_2 + recoil_3, NOT (r1 × r2 × r3)

    // CROSS-FEED — the coupling and the leak
    filter xfeed: LowPass< in=recoil_3, out=morale_evidence, tau=168.0 >;
    feedback morale_evidence -> own_substrate [beta=0.30];

    // INVERSION STAGE
    node fault_line: ^6^C_{F6}|A;       // Male: existing internal divisions
    node suspicion:  ^3^E_{F4}|f;       // Negative: recoil at own allies
    cjt  inv: CJT< fault_line | tgt_substrate => suspicion > [beta=2.5];

    // DENIABILITY — impedance match only
    xfmr deny: Transformer< primary=^0^P_{F7}|T, secondary=^0^C_{F2}|A, n=1.0 >;

    // CSB — the operator's own limit
    node limit_decision: ^3^P_{F7}|⟨A,f,T⟩;   // three co-present guardrails
    cjt  csb: CJT< split | own_substrate => limit_decision > [beta=2.0, sat=0.85];
    fuse csb_fuse: Fuse< limit_decision, threshold=0.90, action=permanent_block >;

    probe tp1: split;            // shared-source coupling
    probe tp2: recoil_3;         // chain gain, saturation
    probe tp3: fault_line;       // decomposition available
    probe tp4: limit_decision;   // CSB status
}
```

**Stage walk.** `intake` runs at unity because a fan-out with gain would make the two paths' levels track the command instead of their own design. `fortify` saturates at 0.80 deliberately — an over-fortified own-force `^5` becomes 19.4's dogmatism signature aimed at itself. `xfeed` is the coupling, and its gain of **0.30 is six times what Chapter 8.4 calls safe** for a path terminating on a `^P` bias: the defect that makes this board self-inverting over a long campaign. `deny` is a 1:1 transformer, `n=1.0`, and adds no gain — its only job is impedance matching (Ch 11.5). `csb` and `csb_fuse` are Chapter 24's refusal architecture.

**What is absent, and why.** No message construction, channel selection, schedule, targeting criteria, or procedure appears here. Those are the operational layer, and they are what turns an architecture into a weapon aimed at people who did not agree to it. The architecture is published because a board whose schematic you have never seen is one you cannot recognise; the procedure is withheld because recognition needs none of it. The incompleteness is deliberate.

[[FIGURE 19-B: Full CCB-PW schematic in component symbols under a heavy DETECTION-ONLY — DO NOT BUILD banner across the frame. Command source, intake CJT, D1/D2/D3 with Vf printed; Path F upper; Path D lower as three cascaded CJTs, the third with a saturation bar at 0.90; cross-feed dashed through an RC block to the fortify CJT's bias terminal, annotated "β=0.30 — six times the Ch 8.4 safe value"; inversion CJT off Path D; 1:1 transformer at the output; CSB CJT and fuse. TP1–TP4 flags.]]

---

### 19.6 The "Hearts and Minds" Counter-Circuit — When PsyWar Must Become PsyHeal

Everything above describes a board you will never build. This one you can, and it is the harder engineering, because an attack has to reach a population once and a counter has to still be standing in a year.

#### What the counter must and must not do

| # | Requirement | Rationale |
|---|---|---|
| **HM1** | Raise `R_collective` against externally-clocked input, **not** all input | A population that rejects everything has been closed — the attacker's second-best outcome |
| **HM2** | Restore `^6` decomposition as a public habit | 19.3: it is the counter to amplification |
| **HM3** | Restore a local, checkable `^4` return | So confirmation measures reality, not the campaign |
| **HM4** | Bring every involution pair inside 4 points | 19.4 |
| **HM5** | Work **without** identifying the attacker | Attribution is slow; the counter must run during the operation |
| **HM6** | Carry **no** outward `^3^E\|f` stage at any gain | Otherwise you have built a second CCB-PW |

HM6 is the one that gets violated, because the natural response to an information operation is a counter-operation, and that is a Path D pointed the other way. Two things use `^3` and are not the same component: `^3^P|T` is an inward-facing principled refusal, the limit an operator places on themselves (Ch 24); `^3^E|f` projected outward is a weapon. The counter carries the first and not the second, at any gain, however deserved the target. Make it inspectable: **decomposition dominance** means `β_6 ≥ 1.5` and no outward `^3^E|f` stage.

The violation does not arrive as a decision to build a weapon. It arrives as a domain slide. Someone holds `^3^P|T`, a principled refusal of what the operation is doing, and then needs the population to *feel* it — so they reach for the domain and the register in which people feel things. `^P` becomes `^E`; `|T` becomes `|f`. The literal on the page has moved by two characters and is now the node CCB-PW drives at `recoil_1`. Nobody wrote a Path D. Somebody wrote a `^3^E|f` node, put a gain on it, and kept their reasons. The reasons are not the component. Read the literal.

The bench test is one question put to whoever is running the counter: **name the `^5` this stage acts on.** If the answer is ours, the stage is inward and HM6 holds. If the answer is theirs, there is an outward stage on the board whatever the surrounding argument says about proportionality — and the correct action is the one in the failure-mode table. Delete it. Not turn it down. A weapon at low gain is a weapon with a longer schedule, and 19.4's point about sustain applies to your board exactly as it applies to theirs.

#### What an inoculated ^5 looks like structurally

Not "a well-informed population" — that describes contents, and contents are what an operation supplies. Inoculation is a property of *wiring*, with six features.

| Feature | Condition | What it defeats |
|---|---|---|
| Plural `^5` | `n ≥ 5` independently-charged capacitors (Ch 7.5) — family, trade, locality, faith, craft | At `n = 1`: one dielectric to breach, one dial pair to move |
| Live `^6` beside every `^5` | `\|Dial(^5) − Dial(^6)\| ≤ 4` | Dogmatism. Taking your own commitments apart is not being less committed |
| Non-zero `Vf` at D2 | `^C -> ^E` drop ≥ 1.2 (Ch 8) | Disagreement reading as attack — Path D's delivery route |
| Local, verifiable `^4` | Claims checkable against the population's own doorstep | A return path measuring the campaign, not reality |
| Rhythm sovereignty | `^7` set by internal cycles — work, season, observance | Entrainment on command; an externally clocked population has handed over its oscillator |
| Slow O→P feedback | `β ≤ 0.05` **and** `τ ≥ 3 weeks` (Ch 8.4) | Gain bounds how far pressure moves the substrate, `τ` what counts as sustained. Patience defeats `τ` alone, intensity `β` alone |

Fund the third row first if you can fund only one. The D2 drop is the ability to consider a claim without immediately feeling something about it — the first thing any environment that rewards immediate reaction destroys.

#### The counter board

```cas
board ccb_hm_hearts_and_minds {
    input:  incoming;
    output: composed;                   // the board's only output is internal

    node substrate: ^5^P_{F1}|T;        // plural, not one capacitor
    cap  c5: Capacitor< substrate, C=2.0, n_parallel=5, leakage=0.02 >;   // per week

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

    // the one lawful integration — named emergent result
    integrate hm3: ( decompose × confirm ) = composed;

    osc    local: Oscillator< signal=own_clock, period=168.0, source=internal >;
    filter fb:    LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [beta=0.05];

    cjt  csb: CJT< incoming | substrate => limit > [beta=2.0, sat=0.85];
    fuse hm_fuse: Fuse< limit, threshold=0.90, action=permanent_block >;

    probe tp1: own_clock;   // cadence source
    probe tp2: hm1;         // decomposition gain
    probe tp3: composed;    // fraction surviving decomposition
    probe tp4: limit;       // CSB status
}
```

Four choices carry this board. **`hm1` at β = 2.0**, because decomposition must out-gain the recoil it decomposes; below 1.5 the board is decorative, above 3.0 it decomposes everything and the population cannot act. **`hm2` at unity**, because above 1.0 it manufactures the reassurance it was meant to measure — Path F rebuilt inside the counter. **`d_ce` at Vf = 1.6** rather than Chapter 8's 1.2, the only parameter tuned against Path D; the cost is that a high D2 drop makes a population slower to feel a real emergency. **`fb` at τ = 504 h, β = 0.05**, from Chapter 8.4, because an operation that can move the substrate in a week owns the feedback path.

**Stage walk — the parts those four do not cover.** `c5` is the board's premise expressed as a component: `C=2.0` per cell at `n_parallel=5`, so ten units of composition sit across five independently-charged cells instead of ten in one. `leakage=0.02` per week is not a defect to be engineered out; a formation that leaks nothing is one no new experience can revise, which is the dogmatism row of the previous table arriving through a different door. `d_pc` and `d_eo` keep Chapter 8's stock 0.7 and 2.0 untouched on purpose — `d_ce` is the only diode this board is entitled to tune, because it is the only one Path D depends on, and a board that retunes every diode it can reach has stopped being a counter and started being a redesign of the population. `local` sources its cadence internally, which is the entire content of `source=internal` and the one line here that cannot be bought: an oscillator somebody else clocks is not a component you own. `hm3` sits *after* `hm2` rather than beside it, because decomposition and confirmation must both have run before anything fuses — integrate them in the other order and `composed` is a formation that was never checked against anything, which is the shape of the problem, not the fix. `csb` and `hm_fuse` are Chapter 24's stage unchanged: `sat=0.85` so the operator's own refusal plateaus and stops being arguable, `threshold=0.90` so that once it trips there is no route back through this board. Note that `csb` takes its bias from `substrate` and not from `limit`. A refusal that biases itself has nothing to check against and will hold at whatever level it happened to reach, which is indistinguishable from conviction and is not the same thing.

The probes are placed on stages rather than on nodes wherever a node can lie. `tp2` reads `hm1`, not `decompose`, because the reading that matters is the gain: a decomposition node can look busy while the stage feeding it runs at 0.6 and the population is decomposing a tenth of what arrives.

> **Bench Note — the counter board has no outward stage, and that is the guarantee.** Run your eye down the listing for a CJT whose effect terminal leaves the board aimed at anybody. There is none. `hm1` and `hm2` terminate inside the substrate that owns them; `hm3` fuses two internal nodes; `csb` produces an inward refusal. Every stage on CCB-HM acts on the `^5` it belongs to. That is what makes HM6 an architectural property rather than a promise: an outward `^3^E|f` payload has no terminal to attach to and would require declaring a new stage, and a new stage is visible in the listing to anyone who reads it. Compare CCB-PW, where the two outward CJTs are the first things on the board. If you find yourself adding one here, the listing has already told you what you built.

The single `×` on either board is `hm3`, and it qualifies under Chapter 2.6: two *different* states, both in `^C` so nothing ascends, integrating into a named emergent result. Everything else uses `+` or a register set, because nothing else has a named result to point at. Neither board specifies `β=∞`: infinite gain is the idealisation for a hard switch, a validator rejects non-finite input, and above about β = 10 the saturation ceiling shapes the output anyway. Where Chapter 24 writes `β=∞`, build 10.

#### What the counter cannot do

Three limits, stated because a defensive board that oversells itself is worse than no board at all.

**It does not attribute.** TP1 reads coupling, and coupling says only that two streams share an upstream. It does not say whose. HM5 makes that a design requirement rather than a shortfall — the counter has to run while attribution is still open, which for most operations is the whole of the operation. A detector that waits for a name has stopped being a detector and become a commentator.

**It cannot manufacture plurality inside a campaign.** `n_parallel` is the one parameter here with no short path. Five independently-charged capacitors are five real formations — a trade, a locality, an observance, a craft, a household — and they charge at the pace of `^7`, in years. The failure-mode table calls monoculture not fixable during an attack, and that is not pessimism about the repair; it is Chapter 9.2's `τ = L/R` applied to a substrate nobody has been charging. The counter for a monoculture is the counter that was built a decade earlier.

**It is blind to an operation that runs on the population's own clock.** Every fingerprint in 19.2 comes from the shared upstream. An operator willing to pay for separately sourced, separately clocked and separately funded paths surrenders exactly the efficiency the dual path exists for — and takes TP1 away in the same move. That operation costs several times as much and is correspondingly rarer, but a detector that only knows how to read cadence will report it clean. TP2 and TP3 still hold, because chain gain and decomposition survival are properties of the payload rather than of the wiring. This is why the test-point set is four readings and not one.

[[FIGURE 19-C: Full CCB-HM schematic in component symbols, no banner — this board is buildable. hm1 (β=2.0) into ^6^C decomposition and hm2 (unity) into ^4^C confirmation, both feeding a shaded block labelled "( decompose × confirm ) = composed"; five parallel capacitors labelled n_parallel = 5 as the ^5^P substrate; the D2's Vf=1.6 circled, annotated "raised from 1.2"; internal oscillator; RC feedback τ=504 h, β=0.05 ending at the capacitor bank's bias terminal, not the signal path; CSB CJT and fuse. TP1–TP4 flags.]]

---

### Parameter and BOM Table

Every value is a **design choice made in this book**, not a measurement of any population.

| Ref | Parameters | Failure at other values |
|---|---|---|
| `intake` (PW) | β=1.0 | β>1: path levels track the command, not the design |
| `fortify` (PW) | β=2.0, sat=0.80 | sat=1.0: own-force `^5` inverts into dogmatism |
| `a1`–`a3` (PW) | β=1.5/1.5/1.6, sat=0.90 | One β=3.6 stage clips early, reads as an amplifier |
| `xfeed` (PW) | τ=168 h, β=0.30 | 6× Ch 8.4's safe value — the self-inversion defect |
| `inv` (PW) | β=2.5 | Below 2.0: divergence relaxes faster than it is driven |
| `deny` (PW) | n=1.0 | `n` ≠ 1 adds gain and becomes detectable |
| `csb` (both) | β=2.0, sat=0.85, fuse 0.90 | sat=1.0: never plateaus, argued down |
| `c5` (HM) | C=2.0, n_parallel=5, leakage=0.02/wk | n_parallel=1: one dielectric, one pair to diverge. leakage=0: a formation no experience revises |
| `hm1` (HM) | β=2.0 | <1.5 decorative; >3.0 paralysis by analysis |
| `hm2` (HM) | β=1.0 | >1.0 manufactures reassurance; <1.0 discounts returns |
| `d_ce` (HM) | Vf=1.6 | 0.3: disagreement reads as attack. 3.0: no emergency |
| `fb` (HM) | τ=504 h, β=0.05 | Short τ: reprogrammable in a week. β=0: unfalsifiable |

---

### Worked Example — Four Weeks of Readings

**The numbers below are constructed for this example.** They are not measurements of any campaign, population or event; they exist so the arithmetic can be carried end to end.

A detector watches two streams for four weeks. Stream A is corrosive, aimed at population X; Stream B affirming, aimed at Y. Both seed at 0.12 in week 1. Outputs: A 0.43, 0.68, 0.85, 0.90; B 0.24, 0.33, 0.41, 0.47.

**TP2 — chain gain.** `β_A = 0.43 / 0.12 = 3.6`; `β_B = 0.24 / 0.12 = 2.0`; asymmetry `1.8`, matching 19.2's design figure exactly. By week 4 A has pinned at 0.90: **Path D has saturated.** Further spend buys nothing, and the spend continues.

**TP1 — coupling.** Chapter 9.3: `M = k√(L₁L₂)`. X's shared civic formation is `^P`-domain, so `k_d = 4.0` on 2,000 hours of exposure gives `L_A = 8,000 h·Ω_c`; Y is less concentrated at `L_B = 2,000`. Observed coupling `k = 0.62`, so `M = 2,480 h·Ω_c`. Independent streams sit at `k ≤ 0.20` — Chapter 9.3's shared-feed row — giving `M = 800`. The observed value is **three times** the honest-independence ceiling: the fingerprint, needing no attribution and no content analysis.

**TP4 — divergence in X.** Baseline `Dial(^2)=6, Dial(^3)=4` → 2, inside the limit. Week 4: `Dial(^2)=3, Dial(^3)=8` → **5**, and `Dial(^5)=8, Dial(^6)=3` → **5**. Two pairs over limit at once — axis N on both, a **compound** inversion on axis P: despair from the first pair, dogmatism from the second. Charge follows Chapter 7.2 at `τ = 3 weeks`: `P_cap(4 wk) = 10 × (1 − e^(−4/3)) = 7.4`.

**Repair time.** Rebuilding `^6` capacity is hours-on-path against inertia. With `L = 8,000 h·Ω_c` and `R = 50 Ω_c`: `τ = 160 h`, `3τ = 480 h` — at roughly 10 hours a week of deliberative contact, about **48 weeks**. Four weeks to charge, forty-eight to discharge, twelve to one, and it falls out of the mechanisms: `^3` needs no supporting structure and therefore no hours; `^6` is nothing but hours against `L`. That is the argument for inoculating before anyone needs it.

Do not try to shorten it. Chapter 9.2: `V_kick = L × di/dt`. Force the charge from 0.60 to zero in 24 h and `V_kick = 8,000 × 0.025 = 200 V_c` against a 24 V_c rail — **8.3× rail** — the recoil landing back on `^3^E_{F3}|f`. Ramp it over 480 h and `V_kick = 10 V_c`, well under rail. That is why aggressive mass correction produces entrenchment: not because the correction was wrong, but because the rate was.

> **A plain safety line, not decoration.** This chapter models how attention routes through populations. It makes no medical or psychiatric claims and describes no treatment. The 19.4 signature names — runaway affinity, despair, dogmatism, trigger overload — label circuit states on a divergence table; none of them is a diagnosis, and none should be read as one about a person. If you or someone near you is in real distress, that is a matter for a clinician, and nothing here substitutes for that care.

[[FIGURE 19-D: Assembly drawing of CCB-HM — board outline, silkscreen designators as in the schematic (C5 as five capacitor cans, HM1/HM2 as CJT footprints, D1/D2/D3 down the left edge, FB as an RC block, CSB and fuse boxed, marked SAFETY SECTION). Four test-point pads with callout leaders: TP1 cadence source, TP2 decomposition gain, TP3 survival fraction, TP4 CSB status. BOM box lower right giving Ref / Component / Parameters / Role for c5, hm1, hm2, local, d_pc, d_ce, d_eo, fb, csb, hm_fuse — hm3 is an integration statement, not a part, and is footnoted rather than listed. Corner note: "CCB-PW is detection-only and is not laid out."]]

---

### Test Points

Specified for the **detector**, the reader's role here. Two of the four sit on nodes CCB-PW models and the detector infers from outside; two sit on the counter board the detector actually owns. The column says which.

| TP | Node (board) | Reads | Expected |
|---|---|---|---|
| **TP1** | `own_clock` (HM), read against `split` (PW) | Coupling `k` between nominally independent streams | ≤ 0.20 for genuine independence; ≥ 0.50 is a shared clock. 0.62 in the example |
| **TP2** | `recoil_3` (PW), inferred from output level | `^3` chain gain, and whether it has pinned | ≈ 1 in ordinary discourse; ≥ 3 with a ceiling is an amplification chain |
| **TP3** | `composed` (HM) | Fraction of incoming surviving decomposition | High is good — claims are arriving. Near zero: no parts, so `^3`, not `^6` |
| **TP4** | `limit` (HM); `limit_decision` is its PW counterpart | Max involution divergence across the pairs | ≤ 4. Above 4 on one pair: inversion in progress; on two: compound |

TP1 and TP2 are structural: takeable without knowing what the material says. That is what makes them available to a detector who has no access to the attacking board and never will.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Counter becomes weapon** | Outward `^3^E\|f` stage added "temporarily" | Two operations running, one of them yours | Delete it. HM6 is not a preference |
| **Operator self-inversion** | `xfeed` β=0.30 against Ch 8.4's 0.05 | `^5`/`^6` divergence passes 4; the operator believes their own Path F | Not repairable from inside — the CSB fuse stops it |
| **Correction backlash** | Charge forced off `^3` faster than 3τ | Entrenchment; the corrected population holds harder | Ramp — `V_kick` is a pure inverse in `dt` (Ch 9.2) |
| **Closed population** | `hm1` past 3.0, or `R_collective` raised against all input | Nothing gets in, including true things | Lower `hm1` to 2.0. HM1 is a filter, not a wall |
| **Monoculture `^5`** | `n_parallel = 1` | One inversion attack moves the whole population | Not fixable during an attack — a decade-scale job |

---

### What This Chapter Established

- **The dual-path architecture is one board, not two.** Opposite polarity into two `^5` capacitors from one command node, and the cross-feed that makes it efficient is what makes it detectable.
- **Three fingerprints fall out of the topology**: a shared clock, a polarity asymmetry near 1.8×, and a claim on one side supported only by the state of the other. Gain is split across three ~1.5 stages; only the product is extreme.
- **`^3` is visceral and therefore has no defence against `^6`.** Decomposition — not correction, not counter-argument, not a competing recoil — is the structural counter to amplification.
- **Inversion attacks buy recoil with rate, not content** — cheap against a monoculture, expensive against a plural one, and they reverse when the driving stops. The **inoculated `^5` is a wiring property, not a contents property**: plural capacitors, `^6` paired inside 4 points, non-zero D2 drop, local `^4`, sovereign `^7`, slow O→P feedback.
- **Charge and discharge run on different clocks** — four weeks to charge `^3`, roughly forty-eight to rebuild `^6`: the argument for building resilience early.
- **HM6 is the invariant that gets broken.** A counter-circuit with an outward `^3^E|f` stage at any gain is a second CCB-PW, and the population is running two.
- **Detection is bounded, and the bound is nameable.** All three fingerprints read the shared upstream, so an operator who pays to decouple the paths defeats TP1 entirely — which is why the counter carries four readings and not one, and why an architecture published without its procedure still buys the reader everything recognition requires and nothing an operation does.

---

### Exercises

*(Answers in Appendix H.)*

**19.1 — Read the coupling.** Two streams have `L₁ = 6,000` and `L₂ = 1,500 h·Ω_c`. Compute `M` at the honest-independence ceiling `k = 0.20` and at an observed `k = 0.55`. State the ratio and what it does and does not entitle you to conclude.

**19.2 — Classify the payload.** Three items land the same day: one leaves you angry with nothing new; one leaves three checkable claims; one leaves you unable to name what it said but certain how you feel. Classify each as `^3` or `^6`, give the bench test, and say which is *not* evidence of an operation.

**19.3 — Size the chain.** A detector measures input 0.15 and output 0.62 across a three-stage chain of equal gain. Compute the per-stage β and explain why the operation chose three stages.

**19.4 — Diagnose the divergence.** A population reads `Dial(^2)=4, Dial(^3)=9, Dial(^5)=9, Dial(^6)=4, Dial(^8)=6, Dial(^9)=5`. Compute all three divergences, name every signature present, classify the inversion by axis, say which dial you would move first, and explain why raising `^2` is wrong.

**19.5 — Reject the listing.** An earlier draft contained `Diode< ^C -> ^P >`, commented "only principled signals fortify." State why the compiler refuses it, name the invariant it violates, and rewrite the intended relationship as a valid CCDL fragment specifying and justifying two parameters.

**19.6 (Marquee) — Specify a counter board for a monoculture.** A population of about 400,000 with `n_parallel = 1`, an externally sourced `^7`, and a D2 drop of 0.4, four weeks into a Path D campaign. Specify the full CCB-HM parameter set, departing from this chapter's defaults where you can justify it; for each departure name the failure mode you buy protection against and the capability you give up. Then say which of HM1–HM6 you cannot satisfy in four weeks, and what you would tell the people who asked for a four-week answer.
