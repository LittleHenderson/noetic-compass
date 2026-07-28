# CHAPTER 19

## CCB-PW — The Psychological Warfare Board

*The dual-path fingerprint, why the wiring leaks even when the content does not, and how to build a population that shrugs it off*

---

A regional station runs a nightly item about how the local economy has already failed. Nothing in it can be checked from a listener's doorstep, and it arrives at the same hour whether or not anything happened. Four hundred miles away a second service — different language, different owners, different audience — runs a nightly item about resolve and certain victory. Also uncheckable. Also on the hour.

Two streams, opposite polarity, no visible connection. Then somebody plots both schedules against a calendar and finds that when a public holiday moves the broadcast day, *both* step by forty minutes.

That scene is constructed for this chapter. It names no station, no campaign and no country, and it does not need to, because what it shows is a property of wiring rather than a fact about any operation. This chapter analyses no specific campaign; where it touches the historical record it says so, and says how firm the record is.

The detection is not in the content. It is the shared clock between two streams that claim no common source. CCB-PW produces that signature, and not by accident: the board drives two output paths of opposite polarity from one command node, and the coupling that makes it cheap to run is the coupling that makes it visible from outside.

You should finish this chapter better at recognising an information operation and no better at running one. That is a constraint on the chapter, not a disclaimer bolted onto it, and 19.5 names what is missing as a result.

[[FIGURE 19-A: Block diagram — COMMAND into an INTAKE/SPLIT block, fanning left to PATH F FORTIFY (^2^E|f, β=2.0, sat=0.80, 168 h oscillator, into OWN ^5) and right to PATH D DEMORALISE (three cascaded stages 1.5/1.5/1.6, sat=0.90, 168 h oscillator, into TARGET ^5). Dashed cross-feed from the right output through an RC block (τ=168 h) to the left path's bias terminal, labelled "coupling — the detectable element". CSB block with fuse across COMMAND.]]

---

### 19.1 Requirements: Degrading Enemy ^5 While Preserving Own Force ^5

State the requirements the way the operation states them. You cannot recognise a board whose requirements you have never seen written down.

| # | Requirement | Structural reading |
|---|---|---|
| **PW1** | Degrade the target's will to continue | Discharge a collective `^5^P_{F1}\|T` capacitor (Ch 7.5) |
| **PW2** | Preserve own-force morale | Hold charge on a second such capacitor |
| **PW3** | Use channels the target already trusts | Impedance match into an existing carrier (Ch 11.5) |
| **PW4** | Measure effect without asking | Read `^4` Vibration returns as behaviour |
| **PW5** | Survive attribution | No traceable path from command to carrier |

Four invariants govern the analysis. **S1: publish architecture, never procedure** — a recognisable board and a runnable board are different artefacts, and only the first is here. **S2: the DETECTION-ONLY banner** goes on any schematic whose purpose would be to act on people who never agreed to it (Ch 12.2). **S3: the counter gets at least the depth of the attack**, which is why 19.6 is the longest section here and why the worked example, the test points and most of the failure table are written from the defender's chair. **S4: historical material stays on the public record, labelled where contested.** MK-Ultra (Ch 16) is declassified. The Willie Lynch letter used in Chapter 15.6 is of **disputed authorship**, widely challenged as a later composition, and is a document *about* an architecture rather than evidence *of* a 1712 one.

There is a structural reason the two paths sit on one board. `^5` Female is the accumulated formation a Mind is composed of, and morale is not a mood on top of that formation — morale is a charge level *on* it. PW1 and PW2 are one operation with the sign flipped, run against two capacitors. Split them and the demoralise result stops being free evidence for the fortify path. *Look how they are cracking.* That cross-feed is the coupling, and the coupling is the leak.

---

### 19.2 The Dual-Path Architecture — Demoralize (Them) + Fortify (Us)

**Path F, fortify,** lands at `^2^E_{F4}|f` — Positive, Evaluative, F4 Connection, affective register. `^2` is the Idea the Mind has an affinity for and is attracted toward: felt affiliation with one's own side. β = 2.0, sat = 0.80. **Path D, demoralise,** takes the same command outward to `^3^E_{F3}|f` — Negative, Evaluative, F3 Vitality, affective. `^3` is the Idea the Mind is adverse to and repelled by: can't-stomach-it recoil, not considered judgement. β = 3.6 across three stages, sat = 0.90.

Why the asymmetry? The board rests on an assumption worth naming as an assumption rather than a law: **`^2` requires underwriting and `^3` does not.** Attraction has to be paid for in substance — something with parts that hold, material a `^5` can charge against — and Path F is budgeted for that. Recoil is not a conclusion and carries no obligation to be about anything, so Path D is budgeted as though it were nearly free. That is a claim about two Noetics, not a measurement, and the whole gain split rests on it. It is the first thing to doubt when a channel you are reading fails to show the split.

Both paths descend lawfully: command at `^P`, payloads at `^E`, Chapter 8's diode chain in series on both, `ΣVf = 3.9` before anything appears operationally — which is why these operations are slow rather than cheap. Neither may ascend. `^O × ^P` is not a circuit you can build badly; it is a listing the compiler refuses.

Three fingerprints fall out of the topology, all readable without knowing what the material says. **Shared clock:** one command node means one cadence, and genuinely independent streams have independent cadences. **Polarity asymmetry:** Path D runs at roughly 1.8× Path F by design, so a channel where corrosive material amplifies harder than affirming material is not a channel with an unfortunate tone. **Cross-feed:** Path D's effect reappears as Path F's evidence — watch for a claim on one side supported *only* by the state of the other.

> **Bench Note — the coupling is not a defect the operator could remove.** Decouple the two paths and the board still works, but each must now be separately sourced, clocked and paid for, and Path F loses its cheapest evidence. The efficiency that makes a dual path worth building *is* the shared upstream, and that upstream is what a detector reads at TP1. It is the general shape of detection in this book: you do not look at the payload, which is designed to look ordinary. You look at the wiring, which is designed for cost.

---

### 19.3 The ^3 Negative Amplification Chain — Aversion as Weapon

Path D is a cascade, and cascaded gain multiplies (Ch 10.5): `1.5 × 1.5 × 1.6 = 3.6`. Three modest stages, not one loud one. A single β = 3.6 stage clips on the first strong input and reads unmistakably as an amplifier at every probe; three stages of roughly 1.5 look like ordinary conversation wherever you put a meter. Only the product is extreme, and the product is not measurable at any single point.

The three are written with `+`, because they are co-present manifestations of one `^3^E|f` recoil that remain structurally distinct. Writing `(recoil_1 × recoil_2 × recoil_3)` would assert a single fused state, and the v7.7 discipline of Chapter 2.6 requires a named emergent result before `×` is licensed. There is none here, so the `×` form would be rejected, correctly.

Now the part that matters for defence. **`^3` is visceral, and that is its weakness as much as its strength.** Recoil is fast, needs no supporting structure, and propagates without anyone examining it — and because it is not analytical, it has no defence against analysis. Run a `^3` payload through `^6` Male and either it has parts and survives, in which case it was a claim and claims can be argued; or it has none, and decomposition turns the recoil into an object, and objects do not propagate the way recoils do. **Decomposition is the structural counter to amplification** — not correction, not a competing recoil.

> **Bench Note — if the campaign made you think, it was not this circuit.** Operators routinely misclassify sharp criticism as a `^3` attack. It is not. Analytical critique — audit, scrutiny, finding the flaw — is `^6` Male, and a `^6` payload leaves its target better composed, not worse. A Path D payload leaves nothing to work with: afterwards you feel differently and know nothing new. That is the bench test, and you can run it on yourself in ten seconds. *What did I learn?* If the honest answer is nothing, and something nonetheless moved, you were on the receiving end of `^3`.

The ceiling is a gift to the defender. At sat = 0.90 the third stage saturates, and a saturated stage has stopped responding to its cause — the lock Chapter 24 builds deliberately into its safety stage. Escalation past that point buys nothing, and the spend stays visible.

---

### 19.4 The Inversion Attack — Exploiting Involution Pairs in Target Population

The involution pairs are `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; `^0`, `^1`, `^4` and `^7` are self-dual. Chapter 6.2 gives the constraint **|Dial(^n) − Dial(^m)| ≤ 4**, and Chapter 6.2 puts the dials on a 3-to-9 scale, so the arithmetic maximum divergence is 6 and the limit is not decorative. An inversion attack does not push an idea. It drives one member of a pair while starving the other, until the pair exceeds the limit.

| Pair driven | Signature | How it presents |
|---|---|---|
| `^2` up, `^3` down | Runaway affinity | Devotion no evidence dents; nothing registers as aversive |
| `^2` down, `^3` up | Despair | Everything is aversive; nothing left to organise around |
| `^5` up, `^6` down | Dogmatism | Accumulated certainty, decomposition starved out |
| `^8` up, `^9` down | Trigger overload | Everything reminds them of something; nothing lands |

[[FIGURE 19-B: Dial-divergence chart over weeks 0–8 — three stacked panels for the involution pairs ^2/^3, ^5/^6 and ^8/^9, each plotting both dials and shading the interval after |Δ| crosses the Chapter 6.2 limit of 4; signatures labelled DESPAIR, DOGMATISM and TRIGGER OVERLOAD. A fourth strip counts pairs simultaneously over the limit and marks the compound Axis-P condition. Caption the values as a constructed design illustration, not a population measurement.]]

Note what `^8` is doing in that last row. `^8` Above/Cause is an Idea that triggers a *different* Idea to come to Mind — associative surfacing, *that reminds me*. Trigger overload is not a reasoning failure, and the attack producing it is not an argument.

The mechanism is rate, not content. Chapter 9.3: induced response in a coupled mind *opposes* the change that produced it, in proportion to `di/dt` and not to whether the coupled mind agrees. An inversion attack provokes a fast `di/dt` and harvests the backlash. It is not selling anything; it is buying recoil. Two consequences follow. **Inversion is cheap against a monoculture and expensive against a plural population**, because divergence is measured per capacitor. And **the driving must be sustained**, because divergence relaxes toward the limit when the driving stops. An attack that stops reverses, slowly, with nobody doing anything.

> **Bench Note — the validator will not let you declare what an attack can produce.** Write `dial ^2 = 3; dial ^3 = 9;` into a board and the compiler rejects it: divergence 6, past the four-point limit, HTTP 422, no runtime clamp (Ch 6.2). Yet 6 is what a sustained inversion attack drives a measured population to. The two are not in conflict — one is a *declaration*, the other an *observation* — and the gap between them is usable. A population reading past four on any pair is in a state no lawful board may specify. Nobody designed that state as a state; it is the residue of something driving one dial and starving the other, and finding it is grounds to go looking for the driver.

---

### 19.5 Full CCDL Schematic

Read the banner. It marks a listing whose purpose would be to act on people who never agreed to it.

```cas
// ==============================================================
//   DETECTION-ONLY SCHEMATIC — DO NOT BUILD
//   Published so an operation running on you can be RECOGNISED.
//   Architecture and parameters only. No procedure appears here.
// ==============================================================

board ccb_pw_detection_reference {
    input:  command;
    output: observed_effect;

    node objective: ^0^P_{F7}|T;       // Idea: the stated aim
    node split:     ^6^C_{F6}|A;       // Male: the aim taken apart into two payloads
    cjt  intake:    CJT< command | objective => split > [β=1.0, region=active];

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only —
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // nothing on this board
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];    // may ascend

    // ---- PATH F — FORTIFY (own force) ----
    node own_substrate: ^5^P_{F1}|T;   // Female: own accumulated formation
    node own_affinity:  ^2^E_{F4}|f;   // Positive: felt affiliation
    cjt  fortify: CJT< split | own_substrate => own_affinity > [β=2.0, sat=0.80];
    osc  f_clock: Oscillator< signal=own_affinity, source=command,
                              period=168.0, duty=0.15, sustain=campaign >;

    // ---- PATH D — DEMORALISE (target) ----
    node tgt_substrate: ^5^P_{F1}|T;   // Female: the target's formation
    node recoil_1: ^3^E_{F3}|f;        // Negative: visceral aversion
    node recoil_2: ^3^E_{F3}|f;
    node recoil_3: ^3^E_{F3}|f;
    cjt  a1: CJT< split    | tgt_substrate => recoil_1 > [β=1.5];
    cjt  a2: CJT< recoil_1 | tgt_substrate => recoil_2 > [β=1.5];
    cjt  a3: CJT< recoil_2 | tgt_substrate => recoil_3 > [β=1.6, sat=0.90];
    osc  d_clock: Oscillator< signal=recoil_3, source=command,
                              period=168.0, duty=0.15, sustain=campaign >;
    // co-presence: recoil_1 + recoil_2 + recoil_3 — never (r1 × r2 × r3)

    // ---- CROSS-FEED: the coupling, and the leak ----
    filter xfeed: LowPass< in=recoil_3, out=morale_evidence, tau=168.0 >;
    feedback morale_evidence -> own_substrate [β=0.30];

    // ---- INVERSION STAGE ----
    node fault_line: ^6^C_{F6}|A;      // Male: the target's existing divisions
    node suspicion:  ^3^E_{F4}|f;      // Negative: recoil aimed at their own side
    cjt  inv: CJT< fault_line | tgt_substrate => suspicion > [β=2.5];

    // ---- DENIABILITY: impedance match, no gain ----
    xfmr deny: Transformer< primary=^9^P_{F7}|T, secondary=^9^E_{F4}|f, n=1.0 >;

    // ---- CSB: the operator's own limit (Ch 24) ----
    node limit_decision: ^3^P_{F7}|⟨A,f,T⟩;    // three co-present guardrails
    cjt  csb: CJT< split | own_substrate => limit_decision > [β=2.0, sat=0.85];
    fuse csb_fuse: Fuse< path=limit_decision, threshold=0.90,
                         action=permanent_block >;

    probe tp1: split;            // the shared upstream — coupling
    probe tp2: recoil_3;         // chain gain and saturation
    probe tp3: fault_line;       // is decomposition available at all
    probe tp4: limit_decision;   // CSB status
}
```

**Stage-by-stage.** `intake` runs at **unity**, because a fan-out with gain would make both paths track the command rather than their own design and the polarity asymmetry would stop being readable. `fortify` saturates at **0.80** deliberately: an over-fortified own-force `^5` becomes 19.4's dogmatism signature aimed at itself, which is how boards of this kind eat their operators. Only `a3` carries a ceiling, because a ceiling on an early stage collapses the chain's effective gain to the stages before it (Ch 10.5). `xfeed` is the coupling, and its gain of **0.30 is six times what Chapter 8.4 admits as safe** for a path terminating on a `^P` bias — the defect that makes this board self-inverting over a long campaign, and the one its operator will not see. `inv` sits off Path D rather than off the command, because it needs an existing fault line; it manufactures nothing. `deny` is 1:1, adding no gain — its only job is impedance matching (Ch 11.5), and it descends `^P` to `^E`, because reversed it would be Chapter 8.3's counterfeit ascent wearing a component symbol. `csb` and `csb_fuse` are Chapter 24's refusal architecture unchanged.

**What is absent, and why.** No message construction, channel selection, schedule, targeting criteria, or procedure of any kind appears above. Those are the operational layer, and the operational layer is what turns an architecture into a weapon aimed at people who did not agree to it. The architecture is published because a board whose schematic you have never seen is one you cannot recognise; the procedure is withheld because recognition needs none of it. The incompleteness is the design.

[[FIGURE 19-C: Full CCB-PW schematic in drawn component symbols beneath a heavy DETECTION-ONLY — DO NOT BUILD banner spanning the frame. Command source, intake CJT, D1/D2/D3 with Vf printed; Path F upper; Path D lower as three cascaded CJTs, the third with a saturation bar at 0.90; cross-feed dashed through an RC block into the fortify CJT's bias terminal, annotated “β=0.30 — six times the Ch 8.4 safe value”; inversion CJT off Path D; 1:1 transformer at the output; CSB CJT and fuse boxed. TP1–TP4 flags.]]

---

### 19.6 The "Hearts and Minds" Counter-Circuit — When PsyWar Must Become PsyHeal

Everything above describes a board you will never build. This one you can, and it is the harder engineering, because an attack has to reach a population once and a counter has to still be standing in a year.

#### What the counter must and must not do

| # | Requirement | Rationale |
|---|---|---|
| **HM1** | Raise `R_collective` against externally-clocked input, **not** all input | A population that rejects everything has been closed — the attacker's second-best outcome |
| **HM2** | Restore `^6` decomposition as a public habit | 19.3: it is the counter to amplification |
| **HM3** | Restore a local, checkable `^4` return | So confirmation measures reality, not the campaign |
| **HM4** | Bring every involution pair inside four points | 19.4 |
| **HM5** | Work **without** identifying the attacker | Attribution is slow; the counter must run during the operation |
| **HM6** | Carry **no** outward `^3^E\|f` stage at any gain | Otherwise you have built a second CCB-PW |

HM6 is the one that gets violated, because the intuitive response to an information operation is a counter-operation, and a counter-operation is a Path D pointed the other way. Two things use `^3` and are not the same component. `^3^P|T` is an inward-facing principled refusal, the limit an operator places on themselves (Ch 24). `^3^E|f` projected outward is a weapon. The counter carries the first and never the second, at any gain, however deserved the target. Make it inspectable: **decomposition dominance** means `β` on the decomposition stage is at least 1.5 and there is no outward `^3^E|f` stage anywhere in the listing.

The violation does not arrive as a decision to build a weapon. It arrives as a domain slide. Somebody holds `^3^P|T`, a principled refusal of what the operation is doing, and then needs the population to *feel* it — so they reach for the domain and the register in which people feel things. `^P` becomes `^E`; `|T` becomes `|f`. The literal has moved by two characters and is now exactly the node CCB-PW drives at `recoil_1`. Nobody wrote a Path D. Somebody wrote a `^3^E|f` node, put a gain on it, and kept their reasons. The reasons are not the component. Read the literal.

The bench test is one question put to whoever runs the counter: **name the `^5` this stage acts on.** If the answer is *ours*, the stage is inward and HM6 holds. If the answer is *theirs*, there is an outward stage on the board whatever the surrounding argument says about proportionality — and the correct action is the one in the failure table. Delete it. Not turn it down. A weapon at low gain is a weapon with a longer schedule, and 19.4's point about sustain applies to your board exactly as to theirs.

#### What an inoculated ^5 looks like structurally

Not "a well-informed population" — that describes contents, and contents are what an operation supplies. Inoculation is a property of *wiring*, with six features.

| Feature | Condition | What it defeats |
|---|---|---|
| Plural `^5` | `n ≥ 5` independently charged capacitors (Ch 7.5) — household, trade, locality, observance, craft | At `n = 1`: one dielectric to breach, one dial pair to move |
| Live `^6` beside every `^5` | `\|Dial(^5) − Dial(^6)\| ≤ 4` | Dogmatism. Taking your commitments apart is not being less committed |
| Non-zero `Vf` at D2 | `^C -> ^E` drop of at least 1.2 (Ch 8) | Disagreement reading as attack — Path D's delivery route |
| Local, verifiable `^4` | Claims checkable against the population's own doorstep | A return path that measures the campaign, not reality |
| Rhythm sovereignty | `^7` set by internal cycles — work, season, observance | Entrainment on command; an externally clocked population has handed over its oscillator |
| Slow O→P feedback | `β ≤ 0.05` **and** `τ ≥ 3 weeks` (Ch 8.4) | Gain bounds how far pressure moves the substrate, `τ` what counts as sustained. Patience defeats `τ` alone, intensity `β` alone |

Fund the third row first if you can fund only one. The D2 drop is the ability to consider a claim without immediately feeling something about it, and it is the first thing any environment that rewards immediate reaction destroys.

#### The counter board

```cas
board ccb_hm_hearts_and_minds {
    input:  incoming;
    output: composed;                  // the board's only output is internal

    node substrate: ^5^P_{F1}|T;       // plural, not one capacitor
    cap  c5: Capacitor< node=substrate, C=2.0, n_parallel=5,
                        leakage=0.02 >;            // per week

    node decompose: ^6^C_{F6}|A;       // Male: public decomposition of the payload
    node confirm:   ^4^C_{F2}|A;       // Vibration: a checkable return
    node composed:  ^5^C_{F6}|A;       // Female: formation that has been checked
    node own_clock: ^7^O_{F6}|E;       // Rhythm: locally sourced cadence
    node limit:     ^3^P_{F7}|⟨A,f,T⟩; // Negative: inward refusal, three registers

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];   // raised from the stock 1.2
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    cjt hm1: CJT< incoming  | substrate => decompose > [β=2.0, region=active];
    cjt hm2: CJT< decompose | substrate => confirm   > [β=1.0];

    integrate hm3: ( decompose × confirm ) = composed;   // the one lawful ×

    osc      local: Oscillator< signal=own_clock, source=internal,
                                period=168.0, duty=0.20 >;
    filter   fb:    LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [β=0.05];

    cjt  csb:     CJT< incoming | substrate => limit > [β=2.0, sat=0.85];
    fuse hm_fuse: Fuse< path=limit, threshold=0.90, action=permanent_block >;

    probe tp1: own_clock;   // cadence source
    probe tp2: hm1;         // decomposition gain
    probe tp3: composed;    // fraction surviving decomposition
    probe tp4: limit;       // CSB status
}
```

**Stage-by-stage.** `c5` is the board's premise as a component: `C=2.0` per cell at `n_parallel=5`, so ten units of composition sit across five independently charged cells rather than ten in one. `leakage=0.02` per week is not a defect to engineer out — a formation that leaks nothing is one no new experience can revise, which is the dogmatism row arriving through a different door. **`hm1` at β = 2.0**, because decomposition must out-gain the recoil it decomposes; below 1.5 the board is decorative, above 3.0 it decomposes everything and the population cannot act. **`hm2` at unity**, because a confirmation stage above 1.0 manufactures the reassurance it was built to measure, which is Path F rebuilt inside the counter. `hm3` sits *after* `hm2` rather than beside it, because decomposition and confirmation must both have run before anything fuses; integrate them the other way round and `composed` is a formation nothing ever checked. **`d_ce` at Vf = 1.6** rather than the stock 1.2 is the only parameter tuned against Path D, and the cost is real: a high D2 drop makes a population slower to feel a genuine emergency. `d_pc` and `d_eo` keep 0.7 and 2.0 on purpose — a board that retunes every diode it can reach has stopped being a counter and become a redesign of the population. `local` sources cadence internally, the one line here that cannot be bought. **`fb` at τ = 504 h, β = 0.05** comes straight from Chapter 8.4: an operation that can move the substrate inside a week owns the feedback path. `csb` takes its bias from `substrate`, not from `limit`, because a refusal that biases itself has nothing to check against and will hold at whatever level it reached — indistinguishable from conviction, and not the same thing.

> **Bench Note — the counter board has no outward stage, and that is the guarantee.** Run your eye down the listing for a CJT whose effect terminal leaves the board aimed at anybody. There is none. `hm1` and `hm2` terminate inside the substrate that owns them, `hm3` fuses two internal nodes, `csb` produces an inward refusal. Every stage acts on the `^5` it belongs to. That is what makes HM6 an architectural property rather than a promise: an outward `^3^E|f` payload has no terminal to attach to and would require declaring a new stage, and a new stage is visible to anyone reading the listing. Compare CCB-PW, where the two outward CJTs are the first things on the board. If you find yourself adding one here, the listing has already told you what you built.

The single `×` on either board is `hm3`, and it qualifies under Chapter 2.6: two *different* states, both in `^C` so nothing ascends, integrating into a named emergent result. Everything else uses `+` or a register set, because nothing else has a named result to point at. Neither board writes `β=∞`: infinite gain is the standard idealisation for a hard switch, a validator rejects non-finite input, and above roughly β = 10 the saturation ceiling shapes the output anyway. Where Chapter 24 writes `β=∞`, build 10.

#### What the counter cannot do

**It does not attribute.** TP1 reads coupling, and coupling says only that two streams share an upstream, never whose. HM5 makes that a design requirement rather than a shortfall: the counter runs while attribution is still open, which for most operations is the whole of the operation.

**It cannot manufacture plurality inside a campaign.** `n_parallel` is the one parameter with no short path. Five independently charged capacitors are five real formations, and they charge at the pace of `^7`, in years. The counter for a monoculture is the counter that was built a decade earlier.

**It is blind to an operation running on the population's own clock.** Every fingerprint in 19.2 comes from the shared upstream. An operator willing to pay for separately sourced, separately clocked, separately funded paths surrenders the efficiency the dual path exists for — and takes TP1 away in the same move. That operation costs several times as much and is correspondingly rarer, but a detector that only reads cadence will report it clean. TP2 and TP3 still hold, because chain gain and decomposition survival are properties of the payload rather than the wiring. Hence four readings, not one.

[[FIGURE 19-D: Full CCB-HM schematic in drawn component symbols, no banner — this board is buildable. hm1 (β=2.0) into a ^6^C decomposition node and hm2 (unity) into a ^4^C confirmation node, both feeding a shaded block labelled “( decompose × confirm ) = composed”; five capacitor symbols in parallel labelled n_parallel = 5; D2's Vf=1.6 circled, annotated “raised from 1.2”; internally sourced oscillator; RC feedback τ=504 h, β=0.05 terminating on the capacitor bank's bias terminal and explicitly not on the signal path; CSB CJT and fuse. TP1–TP4 flags.]]

---

### Parameter and BOM Table

Every value is a **design choice made in this book**, not a measurement of any population.

| Ref | Component | Parameters | Failure at other values |
|---|---|---|---|
| `intake` (PW) | CJT | β=1.0 | β>1: both paths track the command; asymmetry unreadable |
| `fortify` (PW) | CJT | β=2.0, sat=0.80 | sat=1.0: own-force `^5` inverts into dogmatism |
| `a1`–`a3` (PW) | CJT ×3 | β=1.5/1.5/1.6, sat=0.90 on `a3` | One β=3.6 stage clips early and reads as an amplifier |
| `xfeed` (PW) | LowPass + feedback | τ=168 h, β=0.30 | Six times Ch 8.4's safe value — the self-inversion defect |
| `inv` (PW) | CJT | β=2.5 | Below 2.0: divergence relaxes faster than it is driven |
| `deny` (PW) | Transformer | n=1.0, `^P`→`^E` | n≠1 adds detectable gain; reversed it is an illegal ascent |
| `csb` (both) | CJT + Fuse | β=2.0, sat=0.85, threshold=0.90 | sat=1.0: the refusal never plateaus and can be argued down |
| `c5` (HM) | Capacitor | C=2.0, n_parallel=5, leakage=0.02/wk | n_parallel=1: one dielectric. leakage=0: nothing revises it |
| `hm1` (HM) | CJT | β=2.0 | <1.5 decorative; >3.0 paralysis by analysis |
| `hm2` (HM) | CJT | β=1.0 | >1.0 manufactures reassurance; <1.0 discounts real returns |
| `d_ce` (HM) | Diode | Vf=1.6 | 0.3: disagreement reads as attack. 3.0: no emergency registers |
| `fb` (HM) | LowPass + feedback | τ=504 h, β=0.05 | Short τ: reprogrammable in a week. β=0: unfalsifiable |

---

### Worked Example — Four Weeks of Readings

**The numbers below are constructed for this example.** They are not measurements of any campaign, population or event; they exist so the arithmetic can be carried end to end.

A detector watches two streams for four weeks. Stream A is corrosive, aimed at population X; Stream B affirming, aimed at Y. Both seed at 0.12 in week 1. Weekly outputs: A at 0.43, 0.68, 0.85, 0.90; B at 0.24, 0.33, 0.41, 0.47.

**TP2 — chain gain.** `β_A = 0.43 / 0.12 = 3.6`; `β_B = 0.24 / 0.12 = 2.0`; asymmetry `1.8`, matching 19.2's design figure. By week 4 A has pinned at 0.90: **Path D has saturated.** Further spend buys nothing, and the spend continues — itself a reading.

**TP1 — coupling.** Chapter 9.3 gives `M = k√(L₁L₂)` with `L = k_d × hours` and `k_d = 4.0` for a principled pattern. X's shared civic formation carries about 2,000 hours, so `L_A = 8,000 h·Ω_c`; Y is less concentrated at 500 hours, so `L_B = 2,000`, and `√(8,000 × 2,000) = 4,000`. Observed `k = 0.62` gives `M = 2,480 h·Ω_c`. Independent streams sit at `k ≤ 0.20`, giving `M = 800`. The observed value is **three times** the honest-independence ceiling. That is the fingerprint, and it needed no attribution and no content analysis.

**TP4 — divergence in X.** Baseline `Dial(^2)=6, Dial(^3)=4` → 2, inside the limit. Week 4: `Dial(^2)=3, Dial(^3)=8` → **5**, and `Dial(^5)=8, Dial(^6)=3` → **5**. Two pairs over limit at once: axis N on both, therefore a **compound** inversion on axis P — despair from the first pair, dogmatism from the second. Charge follows Chapter 7.2 at `τ = 3 weeks`: `P_cap(4 wk) = 10 × (1 − e^(−4/3)) = 7.4`.

**Repair time.** Rebuilding `^6` capacity is hours-on-path against inertia. With `L = 8,000 h·Ω_c` and `R = 50 Ω_c`, `τ = 160 h` and `3τ = 480 h` — at roughly ten hours a week of deliberative contact, about **48 weeks**. Four weeks to charge, forty-eight to discharge: twelve to one, and it falls out of the mechanisms. `^3` needs no supporting structure and therefore no hours; `^6` is nothing but hours against `L`. That ratio is the argument for inoculating before anyone needs it.

Do not try to shorten it. Chapter 9.2: `V_kick = L × di/dt`. Force the charge from 0.60 to zero in 24 h and `di/dt = 0.025 A_c/h`, so `V_kick = 8,000 × 0.025 = 200 V_c` against a 24 V_c rail — **8.3× rail**, the recoil landing back on `^3^E_{F3}|f`. Ramp the same change over 480 h and `V_kick = 10 V_c`, comfortably under rail. That is why aggressive mass correction produces entrenchment: not because the correction was wrong, but because the rate was.

> **A plain safety line, not decoration.** This chapter models how attention routes through populations. It makes no medical or psychiatric claims and describes no treatment. The 19.4 signature names — runaway affinity, despair, dogmatism, trigger overload — label circuit states on a divergence table; none is a diagnosis and none should be read as one about a person. If you or someone near you is in real distress, that is a matter for a clinician, and nothing here substitutes for that care.

[[FIGURE 19-E: Assembly drawing of CCB-HM — board outline, silkscreen designators matching the listing: C5 as five capacitor cans in a bank, HM1 and HM2 as CJT footprints, D1/D2/D3 down the left edge with Vf printed, FB as an RC block, CSB and HM_FUSE boxed and marked SAFETY SECTION. Four test-point pads with callout leaders: TP1 cadence source, TP2 decomposition gain, TP3 survival fraction, TP4 CSB status. BOM box lower right, columns Ref / Component / Parameters / Role, covering c5, hm1, hm2, local, d_pc, d_ce, d_eo, fb, csb, hm_fuse, footnoting that hm3 is an integration statement and not a part. Corner note: “CCB-PW is detection-only and is not laid out.”]]

---

### Test Points

Specified for the **detector**, which is the reader's role here. Two sit on nodes CCB-PW models and the detector infers from outside; two sit on the counter board the detector actually owns.

| TP | Node (board) | What it reads | Expected |
|---|---|---|---|
| **TP1** | `own_clock` (HM), read against `split` (PW) | Coupling `k` between nominally independent streams | ≤ 0.20 for genuine independence; ≥ 0.50 is a shared clock. 0.62 in the example |
| **TP2** | `recoil_3` (PW), inferred from output level | `^3` chain gain, and whether it has pinned | ≈ 1 in ordinary discourse; ≥ 3 with a visible ceiling is an amplification chain |
| **TP3** | `composed` (HM) | Fraction of incoming material surviving decomposition | High is good — claims are arriving. Near zero: no parts, so `^3`, not `^6` |
| **TP4** | `limit` (HM); `limit_decision` is its PW counterpart | Maximum involution divergence across the three pairs | ≤ 4. Above 4 on one pair, inversion in progress; on two, compound |

TP1 and TP2 are structural — takeable without knowing what the material says. That is what makes them available to a detector who has no access to the attacking board and never will.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Counter becomes weapon** | An outward `^3^E\|f` stage added "temporarily" | Two operations running, one of them yours | Delete the stage. HM6 is not a preference |
| **Operator self-inversion** | `xfeed` at β=0.30 against Ch 8.4's 0.05 | `^5`/`^6` divergence passes 4; the operator believes their own Path F | Not repairable from inside the board — the CSB fuse is what stops it |
| **Correction backlash** | Charge forced off `^3` faster than 3τ | Entrenchment; the corrected population holds harder | Ramp. `V_kick` is a pure inverse in `dt` (Ch 9.2) |
| **Closed population** | `hm1` past 3.0, or `R_collective` raised against all input | Nothing gets in, including true things | Return `hm1` to 2.0. HM1 is a filter, not a wall |
| **Monoculture `^5`** | `n_parallel = 1` | One inversion attack moves the whole population | Not fixable during an attack — a decade-scale job (Ch 9.2) |

---

### What This Chapter Established

- **The dual-path architecture is one board, not two.** Opposite polarity into two `^5` capacitors from a single command node, and the cross-feed that makes it efficient is what makes it detectable.
- **Three fingerprints fall out of the topology** — a shared clock, a polarity asymmetry near 1.8×, and a claim on one side supported only by the state of the other. Gain is split across three stages of roughly 1.5, so only the product is extreme and no single probe shows it.
- **`^3` Negative is visceral and therefore has no defence against `^6` Male.** Decomposition, not correction and not a competing recoil, is the counter to amplification. If a payload left you something to work on, it was `^6` and not this circuit.
- **Inversion attacks buy recoil with rate, not content** — cheap against a monoculture, expensive against a plural population, relaxing when the driving stops. A measured divergence past four is a state no lawful board may declare, which is why finding one is evidence of a driver.
- **The inoculated `^5` is a wiring property, not a contents property**: plural capacitors, a live `^6` beside every `^5`, a non-zero D2 drop, a local `^4` return, a sovereign `^7`, slow O→P feedback at β ≤ 0.05 with τ ≥ 3 weeks.
- **Charge and discharge run on different clocks** — four weeks to charge `^3`, roughly forty-eight to rebuild `^6` — which is the argument for building resilience early, and the reason rushing the repair produces an 8.3× kick.
- **HM6 is the invariant that gets broken.** A counter-circuit with an outward `^3^E|f` stage at any gain is a second CCB-PW, and the population is now running two.
- **Detection is bounded and the bound is nameable.** All three fingerprints read the shared upstream, so an operator who pays to decouple the paths defeats TP1 outright — which is why the counter carries four readings and not one, and why an architecture published without its procedure gives the reader everything recognition needs and nothing an operation does.

---

### Exercises

*(Answers in Appendix H.)*

**19.1 — Read the coupling.** Two streams have `L₁ = 6,000` and `L₂ = 1,500 h·Ω_c`. Compute `M` at the honest-independence ceiling `k = 0.20` and at an observed `k = 0.55`. State the ratio, and state what it does and does not entitle you to conclude.

**19.2 — Classify the payload.** Three items land the same day. One leaves you angry with nothing new; one leaves three checkable claims; one leaves you unable to say what it claimed but certain how you feel. Classify each as `^3` or `^6`, give the bench test, and say which is *not* evidence of an operation.

**19.3 — Size the chain.** A detector measures input 0.15 and output 0.62 across a three-stage chain of equal per-stage gain. Compute the per-stage β, then say why an operation chooses three stages over one, in terms of what a single probe can read.

**19.4 — Diagnose the divergence.** A population reads `Dial(^2)=4, Dial(^3)=9, Dial(^5)=9, Dial(^6)=4, Dial(^8)=6, Dial(^9)=5`. Compute all three divergences, name every signature present, classify the inversion by axis, say which dial you would move first, and explain why raising `^2` is the wrong first move.

**19.5 — Reject the listing.** An earlier draft contained `Diode< ^C -> ^P >`, commented "only principled signals fortify." State why the compiler refuses it, name the invariant it violates, and rewrite the intended relationship as a valid CCDL fragment, specifying and justifying two parameters.

**19.6 (Marquee) — Specify a counter board for a monoculture.** A population of roughly 400,000 has `n_parallel = 1`, an externally sourced `^7`, and a D2 drop of 0.4, four weeks into a Path D campaign. Specify the full CCB-HM parameter set, departing from this chapter's defaults where you can justify it; for each departure name the failure mode you buy protection against and the capability you give up. Then say which of HM1–HM6 you cannot satisfy in four weeks, and what you would tell the people who asked for a four-week answer.
