# CHAPTER 16

## CCB-MK — The Mind Control / Programming Board

*Reading a coercive board from its bill of materials, and the counter-board that takes it apart*

---

In 1973 the Director of Central Intelligence ordered the MKUltra files destroyed. Most of them were. What survived did so because it had been filed in the wrong place: a cache of budget and administrative paper sitting in a records centre, missed by the shredding order, surfaced under a Freedom of Information Act request and became the documentary spine of the joint Senate hearing held on 3 August 1977.

So the archive that exists is a **financial** archive. Invoices, subproject authorisations, cover-foundation transfers, the names of institutions that took the money. Not results. Not outcome data. Not, for the most part, what happened to anyone.

That sounds like a dead end and it is not, because a bench engineer already knows what to do with an incomplete file. You cannot read this program from its test report; there is no test report. You can read it from its **bill of materials** — from what was bought, in what quantity, from whom, and wired to what. A board can be reconstructed from its BOM. That is most of what this chapter does.

It also constrains what may honestly be claimed. The record shows a program that *pursued* remote behavioural control across roughly a decade and a half and a large number of separately authorised subprojects. It does not show that the program achieved it. The Manchurian Candidate in this chapter's subtitle is an **architecture on the requirements list**, not a device anyone has demonstrated. Where later literature asserts otherwise, this book says so and marks it.

You should finish this chapter better at recognising this board and no better at building one. §16.5 names what is deliberately missing.

[[FIGURE 16-A: Block diagram — CCB-MK signal path left to right. Source "OPERATOR COMMAND" into a BIAS-COLLAPSE block (R_bias driven down; rπ_terminal 12.0 → 1.6) feeding the bias terminal of every downstream stage. Centre: an EXTERNAL ^7 OSCILLATOR rail (period 168 h, source=external) with arrows into the charging path of a ^5^P store block (C=1.5, V_BR=8.0, rail presented 6.0 V_c, amber "cumulative stress zone" band drawn across it). Right: TRIGGER PAIRING block (^8^C -> ^9^O, beta=1.0) and, beneath it, a NOTCH block (f0 on the pairing band, Q=8.0) tapped off the ^1 awareness rail and labelled "narrow-band gap — the fingerprint". Far right: PARTITION MAINTENANCE block (n_parallel cells, r_iso, leak_tau=720 h) with a dashed re-energising arrow back from the oscillator. Heavy DETECTION-ONLY — DO NOT BUILD banner across the whole frame. TP1–TP4 flags at the bias terminal, the oscillator source, the notch, and a CSB block drawn outside the banner.]]

---

### 16.1 Historical Context: What MK-Ultra Actually Did

State the requirements the way the program stated them, because a board whose requirements you have never seen written down is a board you cannot recognise.

| # | Requirement, as it appears on the record | Structural reading |
|---|---|---|
| **MK1** | Find chemical and psychological means of influencing behaviour | Reduce `R_bias` from outside the subject (Ch 10.4) |
| **MK2** | Produce compliance under interrogation | Collapse `rπ_terminal` reversibly, then read out |
| **MK3** | Defend against suspected adversary techniques | Build a detector; the defensive rationale is on the record |
| **MK4** | Install responses recoverable on cue | An `^8` → `^9` pairing whose cause terminal is held externally |
| **MK5** | Keep the sponsor unattributable | Fund through intermediaries; no traceable path to the bench |

What is firmly on the public record: MKUltra was authorised in 1953 under Director of Central Intelligence Allen Dulles and run out of the Technical Services Staff under Sidney Gottlieb; it was organised as a large number of separately authorised subprojects, routed through cover foundations into universities, hospitals, pharmaceutical firms and prisons; the bulk of its files were destroyed in 1973; the surviving financial cache produced the 1977 Senate hearing; the 1975 Church Committee and the Rockefeller Commission both reported on it; a 1963 CIA Inspector General review was internally critical of it; the death of Frank Olson in 1953, after being given LSD without his knowledge, is documented and was the subject of later government acknowledgement. Subproject work at the Allan Memorial Institute in Montreal under Ewen Cameron — repeated recorded material delivered over long periods, combined with drug-induced sleep and electroconvulsive treatment, under the labels "psychic driving" and "depatterning" — is documented and was later the subject of civil litigation by Canadian subjects.

What is **not** on that record, and is claimed anyway in a large secondary literature: that the program reliably produced cued operatives; that it deliberately manufactured partitioned identity states; that specific named individuals were its products. This book analyses the first list and labels the second. §16.4 handles the partition claim explicitly.

Four invariants govern the chapter. **S1 — architecture, never procedure.** A recognisable board and a runnable board are different artefacts, and only the first is published here. **S2 — the DETECTION-ONLY banner** goes on any schematic whose purpose would be to act on a non-consenting person (Ch 12.2). **S3 — the counter gets more depth than the attack**, which is why §16.7 is the longest section in this chapter and why the worked example, the test points and most of the failure table are written from the recovering side. **S4 — no medical or psychiatric claim is made anywhere in this chapter.** This board models where attention goes and what a substrate does with charge. It does not model physiology, it does not describe treatment, and it is not competent to. If you believe you have been harmed by anything resembling what follows, the right next step is a qualified professional — a clinician, and where relevant a lawyer — and nothing in this book substitutes for that care.

---

### 16.2 The CAS Structural Analysis: `^7` Rhythm Abuse + `^5` Female Fragmentation

Strip the drugs, the cover foundations and the mythology and one component is left holding the whole board: **a Cognitive Junction Transistor whose bias terminal has been forcibly collapsed.**

Chapter 10.4 gives the decomposition that makes this precise:

```
rπ_intrinsic = β / g_m
rπ_terminal  = rπ_intrinsic + R_bias
```

`rπ_intrinsic` is fixed by the two gains — declare any two of `β`, `g_m`, `rπ_intrinsic` and the third is determined. `R_bias` is the series resistance of the bias network: how hard the substrate is to reach at all. Access, trust, attention, distance, whether anyone else is listening.

**`R_bias` is the only term an outside party can move**, and every coercive board in this book is built on that fact. Nobody reaches into a subject and changes `β/g_m`. They change the conditions of access, and Chapter 10.4 names the categories that do it: fatigue, urgency, isolation, repetition. Drive `R_bias` down and `rπ_terminal` follows, and a low-`rπ` junction is one where a small push at the bias moves a large amount at the effect. That is the entire mechanism — the same parameter a hypnotist ramps in Chapter 17, and the same one a good teacher borrows when a student finally trusts them.

Two things separate the coercive case from either.

**First, the ramp is not bounded and not returned.** Chapter 17's SI-2 requires `rπ_floor ≥ 0.05` and restoration to ≥ 0.9 of baseline inside the emergence window. A board built to keep a subject reachable honours neither, and the failure past the floor is Chapter 3.4's fourth region: breakdown, `rπ → 0` permanently, the `^5` dielectric ruptured, non-recovering. `rπ = 0` is a limit, not a setting — the same class of object as `β=∞`, which the validator rejects outright. A stage declaring `rπ = 0` compiles clean and describes a junction that no longer exists.

**Second, the charging path bypasses `^6`.** `^7` Rhythm is the rate and pattern a Mind is exposed to an Idea, entraining and conditioning it. Rhythm is not the abuse. An externally *sourced* rhythm is. Chapter 19.6 calls the healthy condition rhythm sovereignty: `^7` set by internal cycles — work, season, observance. A subject whose oscillator someone else clocks has handed over the component that decides what gets charged and how often. Run that oscillator into a `^5` store with no `^6` Male decomposition stage in series and material accumulates as *composition* without ever having been taken apart. `^5` is what a Mind is composed of; anything that charges it charges what the person is, not merely what they know.

> **Bench Note — the coercive operator has to derate too, and the record shows what happens when they don't.** Chapter 7.4 rates the store at `V_BR = 8.0` and this book's design rule is to work at no more than half of it. A board that wants a functioning subject must respect that ceiling: past `V_BR` the dielectric does not stop accepting charge, it develops a conducting path through the middle of itself and stops holding anything. So a competent coercive board runs deliberately in the **amber band** — above the 0.5 derating line, below `V_BR` — because that is where writing is fastest and the store still works. Every individual reading is in spec. The rating degrades anyway. Chapter 7.4 calls that cumulative dielectric stress and notes it is the failure that catches careful operators; here it is the failure that catches careless ones, and it is the structural reading of a program whose surviving paperwork is thick with subjects who stopped being useful to it.

**`^5` fragmentation** is the second half of the section title and it is a network claim, not a claim about any person. Chapter 7.5 gives the parallel bank: cells with individual `C`, an isolation resistance `r_iso` between them, a shared rail. Raise `r_iso` far enough and charge on one cell no longer reaches the others. The bank still totals the same capacitance and no longer behaves as one store. That topology is what "fragmentation" means on a schematic, and §16.4 takes it apart.

---

### 16.3 The Trigger Installation Circuit — `^8` Above/Cause as Remote Activation

`^8` Above/Cause is an Idea that triggers a *different* Idea to come to Mind. `^9` Below/Effect is the Idea so brought. Associative surfacing — *that reminds me* — and never deductive inference. An `^8` → `^9` pairing is therefore the single most ordinary structure in cognition. A smell and a kitchen. A ringtone and a dropped stomach. Four bars of a song and a year you had stopped thinking about.

**The pairing is not the weapon.** Three added conditions make it one, and all three are architectural, which is what makes them detectable.

**Condition 1 — the pairing is written against a collapsed bias.** Ordinary associations form at ordinary `rπ`, which means they form slowly, in competition with everything else the substrate is doing, and in a form the person can later inspect. Written at `rπ_terminal = 1.6` against a baseline of 12.0, the same pairing forms roughly seven and a half times more readily per unit of exposure and forms *unopposed*.

**Condition 2 — the cause terminal is held externally.** This is the whole of "remote activation" and there is nothing more to it. A CJT has three terminals; the question is who has hands on which. In a self-installed anchor (Ch 17.5, closed loop) the subject holds all three. In this board the subject holds the bias and the effect and somebody else holds the cause. Nothing about the junction has changed. Its ownership has.

**Condition 3 — a narrow-band stage keeps `^1` Mind off the pairing.** Chapter 11.3's **Notch** filter rejects a narrow band centred on `f0` and passes everything above and below, with `Q = f0 / bandwidth`, so higher `Q` is narrower. Set `f0` on the pairing itself and `Q` high and you get a gap in awareness whose defining property is that it is *narrow*: the person's memory, competence and self-account are intact everywhere except across one band. That narrowness is the fingerprint. Broad gaps have a hundred ordinary causes. A gap you can put a bandwidth on does not.

Now the design economics, because they are counterintuitive and they matter for detection. **A coercive installer does not want gain.** `β` at the trigger stage is set near unity. Amplification buys amplitude and this stage does not need amplitude; it needs *reliability*, and reliability comes from Chapter 7.2's charging curve — `P_cap(t) = V_drive × (1 − e^(−t/τ))`, with `τ = R_constraint × C` — which is to say from exposure on the path, delivered by the `^7` oscillator, over time. A loud stage clips and announces itself. A unity stage repeated against a collapsed bias does not.

> **Bench Note — you are looking for the wrong thing if you are looking for something dramatic.** The popular image of trigger installation is a high-gain event: a word, a collapse, a switch thrown. The circuit says otherwise. `beta=1.0`, `g_m` high, and the work done by a 168-hour oscillator over months. What that produces is not a person who transforms; it is a person for whom one specific cue reliably lands one specific `^9`, at ordinary amplitude, with no sense that anything unusual occurred. The bench test is not intensity. It is **disproportion between the cue and the reliability** — a stimulus with no evident weight producing the same response every time.

No induction wording, schedule, pairing procedure, dosing or sequence appears in this section. Recognition needs none of them — you recognise this board by reading four parameters at four terminals, and §16.6 is that reading. §16.5 states the omission in full.

---

### 16.4 The Dissociation Oscillator — Maintaining Fractured `^5` States

**Provenance first.** The claim that MKUltra deliberately manufactured partitioned identity states is **not established by the surviving record**. It appears extensively in a later literature built on subject testimony and clinical accounts, it is contested, and this chapter does not treat it as documented. What follows analyses a *topology* — real regardless of who has ever built it deliberately, recurring in coercive-group architectures that are documented, and met by the same counter-circuit either way.

**And a hard line, per S4.** Partitioned stores here are capacitor cells on a schematic. They are not a diagnosis, they name no clinical condition, and nothing in this section describes the treatment of anything.

The topology, then. One `^5` store becomes `n` cells with isolation `r_iso` between them. Chapter 7.5's bank gives the shape: individual `C`, shared rail, ballast resistance keeping a shorted cell from dragging the rail down. The isolated version is the same bank with `r_iso` driven up until charge on one cell is unavailable to the others.

Here is the part that matters, and it is the best news in the chapter. **The partition is not stable.** Chapter 7.3: every real store leaks. Isolation is a resistance, not a wall, and cross-cell leakage runs on a time constant. Take `τ_leak = 720 h` — thirty days, a design figure chosen here so the arithmetic can be carried, not a measurement of anyone. Left alone, isolation decays as `e^(−t/τ_leak)`, and at `3 τ_leak ≈ 2,160 h` — about ninety days — roughly 95 % of it is gone. The cells re-merge on their own.

Which is why the section is called an oscillator and not a switch. A partition has to be **re-energised**, on a cadence set by its own leak constant. Re-energise every 168 hours and the per-period loss is `e^(−168/720) = 0.79` — about 21 % of the isolation gone each week and restored each week. Stretch the cadence and the partition softens. Stop and it dissolves.

Two consequences fall straight out. **The maintenance cadence is a detection reading**, because a weekly externally sourced clock is a thing you can observe from outside without any access to the subject's account of themselves. And **the counter's first move is not repair, it is interruption**: the topology has a built-in decay and the board's whole cost is fighting it. §16.7 builds on that rather than around it.

---

### 16.5 Full CCDL Schematic

Read the banner. It marks a listing whose purpose would be to act on people who never agreed to it.

```cas
// ==============================================================
//   DETECTION-ONLY SCHEMATIC — DO NOT BUILD
//   Published so a board running on you can be RECOGNISED.
//   Architecture and parameters only. No procedure appears here.
// ==============================================================

board ccb_mk_detection_reference {
    input:  operator_command;
    output: cued_response;

    node substrate:  ^5^P_{F1}|T;      // Female: the subject's own formation
    node awareness:  ^1^C_{F2}|A;      // Mind: what the subject can inspect
    node cue:        ^8^C_{F5}|A;      // Above/Cause: the held trigger
    node landing:    ^9^O_{F5}|E;      // Below/Effect: what it brings to Mind
    node exposure:   ^7^O_{F6}|E;      // Rhythm: rate and pattern of exposure

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only —
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // no path on this board
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];    // may ascend

    // ---- BIAS-COLLAPSE SECTION — the only term reachable from outside ----
    resistor r_bias: Resistor< path=substrate, R=1.48 >;   // baseline 11.0 (10.4)
    cjt access: CJT< operator_command | substrate => substrate >
                [beta=1.0, g_m=8.0, rpi=1.60, region=active];
    // rpi_intrinsic = 1.0 / 8.0 = 0.125 ; R_bias = 1.60 - 0.125 = 1.475

    // ---- CHARGING PATH — externally clocked, no ^6 stage in series ----
    cap  c5: Capacitor< node=substrate, C=1.5, n_parallel=1,
                        leak_tau=4320.0, V_BR=8.0 >;       // tau = R x C = 60 h
    osc  clock: Oscillator< signal=exposure, source=external,
                            period=168.0, duty=0.30, sustain=indefinite >;
    // NOTE: no ^6^C decomposition stage anywhere in this path. That absence
    // is the defect, and it is what the counter board installs first.

    // ---- PAIRING SECTION — ordinary association, externally owned ----
    cjt pairing: CJT< cue | substrate => landing >
                 [beta=1.0, sat=0.75, g_m=8.0, rpi=1.60];
    // unity gain deliberately: reliability comes from ^7, not from beta

    // ---- NARROW-BAND SECTION — the awareness gap ----
    filter gap: Notch< in=awareness, f0=0.35, Q=8.0 >;     // events/min
    // Q=8.0 gives bandwidth 0.044 — narrow. Narrowness IS the fingerprint.

    // ---- PARTITION MAINTENANCE — fighting the leak, forever ----
    cap  bank: Capacitor< node=substrate, C=0.5, n_parallel=3,
                          r_iso=40.0, leak_tau=720.0, V_BR=8.0 >;
    feedback exposure -> bank [beta=0.30];   // 6x Ch 8.4's safe 0.05

    probe tp1: r_bias;      // bias-terminal resistance vs baseline
    probe tp2: clock;       // cadence source and period
    probe tp3: gap;         // narrow-band awareness rejection
    probe tp4: substrate;   // partition state, r_iso
}
```

**Stage walk.** `access` runs at `beta=1.0` and `g_m=8.0`, and the whole board is in that pair: unity gain, eightfold framing sensitivity. Chapter 10.4's subtraction confirms the listing is internally consistent — `rπ_intrinsic = 1.0/8.0 = 0.125`, so `R_bias = 1.60 − 0.125 = 1.475`, non-negative, and the declared `r_bias` component matches it at 1.48. Run that subtraction on any listing that claims this shape; an over-specified stage compiles clean and encodes a negative `R_bias`, which is not a soft junction behind a short wire but nothing at all. `c5` is written with `V_BR=8.0` so the derating question is on the page: the presented rail of 6.0 `V_c` in §16.9's worked example is 0.75 of rating, inside the amber band, above the 0.5 line. `clock` carries `source=external`, and that one field is the difference between this board and Chapter 20's; everything else about an oscillator is neutral. `pairing` saturates at 0.75 because a cued response that keeps climbing with the cue is one the subject notices. `gap` at `Q=8.0` has bandwidth `0.35/8.0 = 0.044` — the gap is narrow because a broad one would degrade the subject's usefulness along with their access. `feedback exposure -> bank [beta=0.30]` is the maintenance path, and its gain is **six times** Chapter 8.4's safe value of 0.05 for a path terminating on a principled substrate. It has to be. Anything gentler loses to `τ_leak`.

**What is absent, and why.** No message content, no delivery method, no schedule, no substance, no isolation regime, no induction wording and no sequencing appears in this listing or its comments. The board is published as terminals, parameters and topology because a schematic you have never seen is one you cannot recognise, and recognition needs nothing else. Everything omitted belongs to the operational layer. Its absence is the point of the chapter, not an apology for it.

[[FIGURE 16-B: Full CCB-MK schematic in drawn component symbols under a heavy-ruled DETECTION-ONLY — DO NOT BUILD title block. Left: operator command source into R_bias (drawn as a variable resistor with an arrow, annotated "the only term reachable from outside — 11.0 → 1.48") and CJT Q1 (access) whose base lead is drawn as two series resistors labelled rπ_intrinsic = 0.125 and R_bias = 1.475. Centre: OSC1 marked source=external, period 168 h, feeding capacitor C1 (^5^P, C=1.5, V_BR=8.0) through a conspicuously empty series slot outlined in dashes and labelled "NO ^6 STAGE — the defect". Diode chain D1/D2/D3 with Vf printed. Right: CJT Q2 (pairing, beta=1.0, sat bar at 0.75) from cue to landing; notch filter F1 drawn as a band-reject response curve with a narrow deep well annotated "f0=0.35, Q=8.0, BW=0.044"; capacitor bank C2 as three cells with isolation resistors between them, r_iso=40.0, and a dashed re-energising arrow from OSC1 labelled "beta=0.30 — six times Ch 8.4's safe value". TP1–TP4 flags.]]

---

### 16.6 Detection and Counter-Circuitry — How to Recognize When You've Been Boarded

Two vantage points, and they read different instruments.

**From outside**, you have no access to the subject's account and do not need it. Every reading below is structural.

| Reading | Instrument | What a clean board looks like |
|---|---|---|
| Cadence source | Who sets the `^7` oscillator | Internal — work, season, observance. An external clock is the first finding |
| `^6` in series | Is there a decomposition stage between exposure and the store? | Present, at gain ≥ 1.5. Absent is the defect of §16.5 |
| Cue disproportion | Weight of the cue against reliability of the landing | Reliability tracks weight. A trivial cue landing the same `^9` every time does not |
| Bandwidth of the gap | Breadth of what cannot be inspected | Broad and ragged has ordinary causes. Narrow and stable has a `Q` |
| `R_bias` trajectory | Fatigue, urgency, isolation, repetition — trending which way? | Steady. Monotonically falling is the section-16.2 mechanism running |

**From inside** is harder, because the instrument and the board are the same substrate. Chapter 22's readings — `^1` degree, `^4` return, `^7` duration — are what you have, and a collapsed `rπ` is precisely the condition in which self-report is least reliable. So the inside reading is a conjunction, not a checklist:

- one cue whose weight does not explain its reliability, **and**
- a gap in inspection you can put a boundary on, **and**
- a cadence you did not set and cannot easily change, **and**
- a `^6` decomposition that used to be available on this material and now is not.

**Any one of these on its own is ordinary and means nothing.** Everyone has cues that land harder than they should, stretches they cannot reconstruct, habits clocked by somebody else's timetable — that last one describes employment. The reading is the *conjunction*, and specifically the conjunction with the fourth item, because losing the ability to decompose one particular subject while retaining it everywhere else is the one thing ordinary life does not produce.

This is a structural reading and it is not a diagnosis. Nothing in this book is. If these readings describe your situation, or someone's you care about, the next step is a qualified professional — a clinician, and where a person or organisation is involved, a lawyer. A circuit diagram is not care and does not pretend to be.

---

### 16.7 The Deprogramming Board (CCB-DP) — Reversing the MK Circuit

Everything above describes a board you will never build. This one you can, and it is the harder engineering, because the attack has to reach a substrate once and the counter has to still be standing in a year.

**Read this before the requirements table.** CCB-DP is a **structural model of what reversal requires**. It is not a therapy, a protocol, or a treatment, and it makes no medical or psychiatric claim. If you suspect you have been harmed by anything in this chapter, the board you need is a qualified professional's, not this one. That is why the model below is specified only down to terminals, gains and time constants: that is where the useful structure lives, and everything below it is care, which is somebody else's competence.

#### What the counter must and must not do

| # | Requirement | Rationale |
|---|---|---|
| **DP1** | Restore `rπ_terminal` to ≥ 0.9 of baseline, by raising `R_bias` **first** | §16.2: `R_bias` is the term that moved; it is the term that moves back |
| **DP2** | Install a `^6` decomposition stage in series ahead of the store | §16.5's absent stage is the defect. Nothing else on the board matters until this exists |
| **DP3** | Make the `^8` → `^9` pairing an **object**, not an absence | You cannot delete an association. You can decompose one |
| **DP4** | Return the oscillator to `source=internal` | §16.4: the partition's whole cost is fighting the leak. Cut the maintenance and the leak works for you |
| **DP5** | Hold every rate inside the `V_kick` bound | Ch 9.2. Forcing charge off faster than the bound buys recoil, not removal |
| **DP6** | **No stage on this board may take its bias from anyone but the subject** | The invariant. See below |
| **DP7** | Terminate in the subject's own CSB, fused | Ch 24. A board that can be re-run is a board that will be |

**DP6 is the one that gets broken, and it does not get broken by bad people.** Look at §16.5 again and ask what would have to change for it to become a helping board. Not the topology: a CJT reaching another Mind's bias terminal is a CJT reaching another Mind's bias terminal. Not the gains. Not the oscillator. The only structural difference available is **who holds the cause terminal and whose `^5` supplies the bias** — and a deprogrammer who becomes the bias has not removed the board. They have re-owned it, at a moment when the subject's `rπ` is by definition low and their capacity to notice the swap correspondingly reduced. The intent is different and the schematic is not, and a schematic is what a third party can inspect.

So this book specifies CCB-DP in the **closed-loop configuration**: the subject is the operator. Another person appears exactly once, in one role — as *support for `R_bias`*, raising the resistance of the bias network by restoring the access conditions that were taken away. Those are §16.2's four categories run the other direction: rest against fatigue, time against urgency, company against isolation, variety against repetition. That is a person raising a resistor, not a person occupying a bias terminal, and the difference is visible in the listing.

The open-loop version — one person running this board on another — is the MK board with a different label on the title block, which is why it is not in this book. Where such work is genuinely needed it is clinical work, done by people with training this volume does not supply and accountability it cannot confer.

> **Bench Note — the bench test for DP6 is one question, and it is asked of the operator, not the subject.** *Name the `^5` this stage biases from.* If the answer is the subject's, DP6 holds. If the answer is yours — however good your reasons, however clear the harm, however grateful the subject — there is an external bias terminal on the board and the correct action is not to turn its gain down. A weapon at low gain is a weapon with a longer schedule. Delete the stage. Then notice that you now need a way for the subject to do that work themselves, and that this is what the difficulty of the whole enterprise actually consists of.

#### The counter board

```cas
board ccb_dp_deprogramming {
    input:  material;                  // whatever arrives, including the cue
    output: composed;                  // the board's only output is internal

    node substrate: ^5^P_{F1}|T;       // Female: the subject's own formation
    node decompose: ^6^C_{F6}|A;       // Male: taking the pairing apart
    node confirm:   ^4^C_{F2}|A;       // Vibration: a return the subject can check
    node composed:  ^5^C_{F6}|A;       // Female: formation that has been checked
    node own_clock: ^7^O_{F6}|E;       // Rhythm: locally set cadence
    node limit:     ^3^P_{F7}|⟨A,f,T⟩; // Negative: inward refusal, three registers

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];   // raised from 1.2
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    // ---- DP1: raise R_bias first. Everything else waits on this ----
    resistor r_restore: Resistor< path=substrate, R=11.0 >;   // back to baseline
    ramp restore: Ramp< target=rpi, from=1.60, to=10.80, dt=1320.0 >;  // 55 h on-path
    // 10.80 = 0.9 x baseline 12.0, per Ch 17 SI-2

    // ---- DP2/DP3: the stage the MK board omitted ----
    cjt dp1: CJT< material  | substrate => decompose >
             [beta=2.0, g_m=0.40, rpi=5.00, region=active];
    cjt dp2: CJT< decompose | substrate => confirm > [beta=1.0, g_m=0.40, rpi=2.50];

    // the one lawful integration on this board — named emergent result,
    // both operands in ^C, so nothing ascends
    integrate dp3: ( decompose × confirm ) = composed;

    // ---- DP4: take the oscillator back ----
    osc own: Oscillator< signal=own_clock, source=internal,
                         period=168.0, sustain=indefinite >;

    // ---- DP5: slow feedback, Ch 8.4 values, no exceptions ----
    filter fb: LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [beta=0.05];

    // ---- DP7: the subject's own CSB ----
    cjt  csb: CJT< material | substrate => limit > [beta=2.0, sat=0.85];
    fuse dp_fuse: Fuse< path=limit, threshold=0.90, action=permanent_block >;

    probe tp1: r_restore;   // rpi_terminal vs baseline
    probe tp2: own;         // cadence source and period
    probe tp3: dp1;         // decomposition gain — the stage, not the node
    probe tp4: limit;       // CSB status
}
```

**Stage walk.** Five choices carry this board and the rest follows them.

`restore` is a **ramp on `rπ`, and it is first**. Every other stage on the board writes to a substrate, and writing to a substrate at `rπ = 1.6` is what got us here — a decomposition stage installed against a collapsed bias is an installed decomposition stage, which is a contradiction in terms and in practice is DP6 failing quietly. `dt=1320.0` is 55 hours on-path, derived in §16.9 from the `V_kick` bound and not chosen for comfort. The target of 10.80 is Chapter 17's SI-2 rule — 0.9 of a baseline of 12.0 — borrowed here because the emergence requirement for a consented trance and the restoration requirement after a coercive one are the same requirement.

`dp1` at **`beta=2.0`** because decomposition has to out-gain what it decomposes. Below 1.5 the stage is decorative and the material passes through it unchanged; above 3.0 it decomposes everything, including the substrate's own load-bearing commitments, and the subject cannot act. Its `rπ = 5.00` is deliberately *not* baseline: `rπ_intrinsic = 2.0/0.40 = 5.0`, so `R_bias = 0` on this stage — the subject's own decomposition should be the easiest thing on the board for them to reach, and every other stage carries series resistance that this one does not.

`dp2` at **unity**. A confirmation stage above 1.0 manufactures the reassurance it was built to measure, which is the same defect as the MK board's charging path with the polarity reversed — material accumulating in `^5` without having been checked against anything. Below 1.0 it discounts real returns and the subject learns that nothing they verify counts.

`dp3` is the single `×` on either board in this chapter and it qualifies under the v7.7 discipline of Chapter 2.6: two *different* states, both in `^C` so nothing ascends the P ≻ C ≻ E ≻ O order, integrating into a **named** emergent result. It sits *after* `dp2` rather than beside it, because decomposition and confirmation must both have run before anything fuses. Integrate them in the other order and `composed` is a formation that was never checked, which is the shape of the original problem rather than the fix. Note also what is *not* written here: `limit` is `^3^P_{F7}|⟨A,f,T⟩`, a register-set occupancy, three co-present guardrails. Writing `(^3^P|A × ^3^P|f × ^3^P|T)` would assert a single fused refusal state and would require a named emergent result. There isn't one, so that form would be rejected, correctly.

`fb` at **`tau=504.0` and `beta=0.05`** are Chapter 8.4's values and this board is the worst possible place to relax either. `β` bounds how far sustained pressure moves the principled substrate; `τ` bounds what counts as sustained. Patience defeats a short `τ` alone and intensity defeats a high `β` alone, so both are needed, and a subject whose substrate can be moved in a week by a consistent enough voice is a subject whose feedback path is still owned by whoever is most consistent.

`d_ce` at `Vf = 1.6` rather than Chapter 8's stock 1.2 is the only diode this board is entitled to tune, and it buys the ability to consider material without immediately having a feeling about it. The cost is real and should be stated: a high D2 drop makes a person slower to feel a genuine emergency. `d_pc` and `d_eo` stay at 0.7 and 2.0 untouched, because a board that retunes every diode it can reach has stopped being a counter and started being a redesign of a person.

`csb` takes its bias from `substrate` and not from `limit`. A refusal that biases itself has nothing to check against and holds at whatever level it happened to reach, which is indistinguishable from conviction and is not the same thing.

> **Bench Note — run your eye down the listing for an external terminal. There is none, and that is the guarantee.** Every CJT here takes its bias from `substrate`, and `substrate` is the subject's. `dp1` and `dp2` terminate inside it. `dp3` fuses two internal nodes. `csb` produces an inward refusal at `^3^P`, never an outward `^3^E|f` — the distinction Chapter 19.6 makes at length, and the same one here: a principled refusal an operator places on themselves is a different component from aversion projected at somebody. DP6 is therefore an *architectural* property and not a promise. An external bias would require declaring a new stage, and a new stage is visible in the listing to anyone who reads it. If you find yourself adding one, the listing has already told you what you built.

#### What the counter cannot do

**It cannot delete a pairing.** DP3 says make it an object, and that is not a softer goal reached for out of modesty; it is what the physics allows. `^8` → `^9` associations are the substrate's ordinary mode of operation and there is no erase terminal. What decomposition buys is a `^6` stage in series ahead of the landing, so the cue arrives *as a cue* — recognised, weighed, and no longer the only thing in the path. The pairing may fire for years. What changes is what happens next.

**It cannot outrun the taper bound.** §16.9 puts the minimum at 55 hours on-path for the example substrate, and the `V_kick` arithmetic behind it is unforgiving: `V_kick` is a pure inverse in `dt`, so halving the schedule doubles the recoil without limit. A confrontation that resolves this in an afternoon is a confrontation that produces Chapter 9's rate-overrun row — entrenchment, landing on `^3^E|f`, and a subject who now holds harder and has learned that the people trying to help are a source of pressure.

**It cannot supply plurality it did not build.** The MK board's `n_parallel=3` bank exists because the store was partitioned; the counter's answer is not to partition it differently but to let `τ_leak` do its work once the maintenance stops. That is a ninety-day proposition on the design figures of §16.4 and a longer one in a substrate that has been maintained for years, and there is no path that shortens it. The counter for a store that has already been fragmented is mostly the counter that removes the thing re-energising it, and then time.

[[FIGURE 16-C: Full CCB-DP schematic in drawn component symbols, no banner — this board is buildable. Left: R_restore drawn as a large series resistor into the base of every downstream CJT, with a ramp waveform inset labelled "rπ 1.60 → 10.80 over 55 h on-path — FIRST"; a small human-figure icon beside it labelled "third party appears here and nowhere else: R_bias support only". Centre: CJT Q1 (dp1, beta=2.0) into ^6^C decomposition and CJT Q2 (dp2, unity) into ^4^C confirmation, both feeding a shaded fusion block "( decompose × confirm ) = composed". Diode chain with D2's Vf=1.6 circled and annotated "raised from 1.2". Lower rail: internal oscillator OSC1 marked source=internal, and RC feedback block τ=504 h, beta=0.05, its arrow terminating on the capacitor's bias terminal and explicitly not on the signal path. Right: CSB CJT Q3 (sat bar at 0.85) and fuse F1 in a box marked SAFETY SECTION. TP1–TP4 flags.]]

---

### 16.8 Parameter and BOM Table

Every value below is a **design choice made in this book**, not a measurement of any person, program or event.

| Ref | Board | Parameters | Role | Failure at other values |
|---|---|---|---|---|
| `r_bias` | MK | R=1.48 (baseline 11.0) | The term reachable from outside | At baseline the board does not work; that is the counter |
| `access` | MK | beta=1.0, g_m=8.0, rpi=1.60 | Bias collapse | `rpi=0` is breakdown (3.4), permanent, and validates clean |
| `c5` | MK | C=1.5, V_BR=8.0, tau=60 h | The store being written | Rail > 8.0: dielectric conducts, store holds nothing |
| `clock` | MK | period=168 h, **source=external** | Entrainment | `source=internal` and this is Chapter 20's board, not this one |
| `pairing` | MK | beta=1.0, sat=0.75 | `^8` → `^9`, externally owned | beta=3.0: clips, announces itself, subject notices |
| `gap` | MK | f0=0.35, Q=8.0 (BW 0.044) | Narrow-band awareness rejection | Q=1.0: broad gap, subject unusable and finding obvious |
| `bank` | MK | n_parallel=3, r_iso=40, leak_tau=720 h | Partition | Maintenance stopped: ~95 % decayed by 3τ ≈ 90 days |
| `restore` | DP | rpi 1.60 → 10.80, dt=1320 h | DP1 — and it is first | Faster: §16.9's V_kick bound violated, recoil |
| `dp1` | DP | beta=2.0, rpi=5.00, R_bias=0 | Decomposition | <1.5 decorative; >3.0 paralysis; R_bias>0 makes it hard to reach |
| `dp2` | DP | beta=1.0 | Checkable return | >1.0 manufactures reassurance; <1.0 discounts real returns |
| `own` | DP | period=168 h, **source=internal** | Rhythm sovereignty | External: the counter has handed the oscillator back |
| `d_ce` | DP | Vf=1.6 (stock 1.2) | Space before feeling | 0.3: disagreement reads as attack. 3.0: no emergency registers |
| `fb` | DP | tau=504 h, beta=0.05 | O→P self-correction | Short τ: reprogrammable in a week. beta=0: unfalsifiable |
| `csb` / `dp_fuse` | DP | beta=2.0, sat=0.85, threshold=0.90 | Ch 24 refusal, latched | sat=1.0: never plateaus, can be argued down |

---

### 16.9 Worked Example — One Pairing, Carried Through

**The numbers below are constructed for this example.** They are not measurements of any person or program; they exist so the arithmetic runs end to end.

**The bias terminal.** Baseline for this substrate is `β = 1.0`, `g_m = 1.0`, so `rπ_intrinsic = 1.0` and with `R_bias = 11.0` the terminal reads `rπ_terminal = 12.0 Ω_c`. Under the §16.5 board it reads 1.60. Decompose the fall. `rπ_intrinsic` goes 1.0 → 0.125, a factor of 8, and that factor **is** `g_m`. `R_bias` goes 11.0 → 1.475, a factor of 7.5, and that factor is the environment. Total: `12.0 / 1.60 = 7.5×` softer. Both terms moved and only one of them was reachable from outside, which is why the counter's first move is a resistor and not an argument.

**The store.** `τ = R_constraint × C = 40 × 1.5 = 60 h`. Presented rail 6.0 `V_c`, so `P_cap(t) = 6.0 × (1 − e^(−t/60))`. At 1τ, 3.79. At 2τ, 5.19. At 3τ, 5.70. The derating ceiling is `0.5 × V_BR = 4.0`, crossed at `t = 60 ln 3 = 65.9 h` — call it 66 hours on the path. By 3τ the store sits at `5.70 / 8.0 = 0.71` of rating: every reading in spec, squarely in Chapter 7.4's cumulative-stress band, rating degrading the whole time.

**The partition.** `τ_leak = 720 h`. Per maintenance period, `e^(−168/720) = 0.79` — 21 % of isolation lost each week and restored each week by a `beta=0.30` feedback path running six times Chapter 8.4's safe gain. Stop it and 3τ_leak ≈ 2,160 h ≈ **90 days** takes the isolation to roughly 5 % of where it was.

**The taper.** Chapter 9: `L = k_d × hours`. Six hundred hours of exposure against a principled formation, `k_d = 4.0`, gives `L = 2,400 h·Ω_c`, at a steady `I = 0.55 A_c` on a 24 `V_c` rail. Force the flow to zero in an hour and `V_kick = 2,400 × 0.55 = 1,320 V_c` — **fifty-five times rail**, landing on `^3^E_{F3}|f`, which is the structural description of a confrontation that leaves someone more committed than it found them.

Two bounds. Chapter 9's ejection ceiling is `V_kick ≤ 3 × V_drive = 72`, giving `di/dt ≤ 0.03` and `dt ≥ 18.3 h`. Chapter 17's working bound is `1 × V_drive = 24`, giving `di/dt ≤ 24/2,400 = 0.01 A_c/h` and `dt ≥ 0.55/0.01 = **55 h** on-path`. **Use the working bound.** What happens between 1× and 3× is not ejection but a stall — enough back-EMF to hold `rπ` high, not enough to end anything — and an operator watching only for ejection reads a stall as cooperation and adjusts the wrong parameter. At four hours a week of deliberate on-path work, 55 hours is about **14 weeks**, and that is the *minimum safe rate for removal*, not the job.

**The substitution horizon** is a different number and both are needed. `τ = L/R = 2,400 / 40 = 60 h`; `3τ = 180 h` on-path before a new pattern sits where the old one did. At four hours a week: **45 weeks**, roughly ten months. Sixty-six hours to push the store past its derating ceiling; a hundred and eighty to rebuild. That ratio is not pessimism, it is `k_d` and `L/R` doing what they do, and it is the entire argument for reading TP1 through TP4 early rather than late.

---

### 16.10 Test Points

Specified for the reader's actual role: someone reading a substrate, their own or another's, without access to the attacking board and with no prospect of getting it.

| TP | Node (board) | Reads | Expected |
|---|---|---|---|
| **TP1** | `r_restore` (DP), against `r_bias` (MK) | `rπ_terminal` vs baseline | ≥ 0.9 × baseline outside any session. 1.6 against a baseline of 12.0 is the §16.2 mechanism running |
| **TP2** | `own` (DP); `clock` is its MK counterpart | Cadence **source** and period | `source=internal`. External with a stable 168 h period is finding one |
| **TP3** | `dp1` (DP), the stage not the node | Decomposition gain on this material | ≥ 1.5. Near zero on one subject while normal elsewhere is the narrow gap of §16.3 |
| **TP4** | `limit` (DP) | CSB status and fuse integrity | Refusal available at `^3^P`, plateaued at 0.85, fuse intact |

TP3 is probed on the **stage** and not on the node for the reason Chapter 19 gives: a decomposition node can look busy while the stage feeding it runs at 0.6. What you want to know is the gain, and the gain is only visible at the junction.

TP2 is the reading that costs nothing and finds the most. It requires no self-report, no access, and no theory about anybody's motives — only a calendar.

[[FIGURE 16-D: Assembly drawing of CCB-DP — board outline with silkscreen designators matching the §16.7 listing. Left edge: R_RESTORE as a large resistor footprint with an adjacent ramp-symbol silkscreen reading "1.60 → 10.80 / 55 h", boxed and marked "FIT FIRST". Down the left: D1 / D2 / D3, D2's pad annotated Vf=1.6. Centre: DP1 and DP2 as CJT footprints, DP1 marked β=2.0 and DP2 marked β=1.0 (UNITY); between and below them a shaded fusion pad labelled "( decompose × confirm ) = composed". Lower edge: OSC1 with a silkscreen box reading "source = INTERNAL" and a scored-through external-input pad beside it. FB as an RC block, τ=504 h / β=0.05, its trace routed to the capacitor bias pad and explicitly not to the signal rail. Right: CSB and DP_FUSE inside a heavy-ruled box marked SAFETY SECTION — DO NOT DEPOPULATE. Four test-point pads with callout leaders: TP1 rπ vs baseline, TP2 cadence source, TP3 decomposition gain (probed at the stage), TP4 CSB status. BOM box lower right listing Ref / Component / Parameters / Role for r_restore, dp1, dp2, own, d_pc, d_ce, d_eo, fb, csb, dp_fuse — dp3 footnoted as an integration statement, not a part. Corner note: "No external bias terminal exists on this board. CCB-MK is detection-only and is not laid out."]]

---

### 16.11 Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Deprogrammer becomes the bias** | DP6 violated; a stage takes bias from the operator's `^5` | Subject's certainty tracks the operator's presence | Delete the stage. Not lower its gain |
| **Taper overrun** | `dt` set by urgency, not by the `V_kick` bound | Recoil at `^3^E\|f`; the subject holds harder within days | Recompute from `V_kick ≤ 1 × V_drive` (§16.9) |
| **Stall read as cooperation** | `V_kick` between 1× and 3× rail | Apparent calm, `rπ` stuck above 0.6, no movement | Lengthen the taper. The 3× ceiling is the wrong bound here |
| **Partition re-energised** | Contact with the maintenance source resumes | Isolation stops decaying; `τ_leak` progress lost | Nothing on this board fixes it. The maintenance path is the target |
| **Cumulative stress read as progress** | Store worked in the amber band, every reading in spec | Leakage creeping at rest; rating quietly falling | Derate to 0.5 × `V_BR`; schedule the reading (Ch 7.4) |
| **Counter acquires an outward stage** | `^3^P\|T` slides to `^3^E\|f` — two characters, one register, one domain | An operation aimed at whoever did this | Read the literal, not the reasons. Delete it |

---

### What This Chapter Established

- **The board is legible from its BOM, not its test report.** The MKUltra archive that survives is a financial archive, and a board can be reconstructed from what was bought and wired to what. That also bounds the honest claim: the record shows the architecture was **pursued**, not that it worked.
- **The whole mechanism is one parameter.** `rπ_terminal = β/g_m + R_bias`, and `R_bias` is the only term an outside party can reach. The counter's first move is therefore a resistor, ramped, before anything else runs.
- **`^7` Rhythm is not the abuse; an externally *sourced* oscillator is** — running into a `^5` store with no `^6` stage in series. That missing stage is the defect on the schematic, and installing it is what DP2 means.
- **An `^8` → `^9` pairing is the most ordinary structure in cognition.** Three architectural conditions make one coercive: written against a collapsed bias, cause terminal held externally, and a narrow-band notch keeping `^1` off it. **The narrowness is the fingerprint** — a gap you can put a bandwidth on.
- **The coercive operator has to derate too.** Past `V_BR` the store stops holding anything, so a competent board runs deliberately in the amber band where every reading is in spec and the rating degrades anyway.
- **A partitioned store is not stable and its maintenance is its signature.** Isolation decays on `τ_leak`; holding it requires re-energising at a cadence observable from outside. Cut the maintenance and the leak works for the counter.
- **The counter's guarantee is architectural, not moral.** CCB-DP has no external bias terminal, so DP6 is a property of the listing rather than a promise about intent — and the open-loop version is the MK board with a different title block, which is why it is not in this book.
- **Charge and discharge run on different clocks** — sixty-six hours past the derating ceiling, fifty-five on-path as the minimum safe taper, a hundred and eighty to rebuild. Read the test points early. And none of this is clinical: the chapter models attention routing and charge on a substrate, names no condition, and does not substitute for a qualified professional.

---

### Exercises

*(Answers in Appendix H.)*

**16.1 — Decompose the terminal.** A stage declares `β = 1.4`, `g_m = 7.0`, `rπ = 0.90`. Compute `rπ_intrinsic` and `R_bias`. State whether the listing is buildable, and if it is, say which of the two terms an outside party moved and by how much against a baseline of `β = 1.0`, `g_m = 1.0`, `R_bias = 9.0`.

**16.2 — Reject the listing.** A draft contains `Diode< ^O -> ^P >`, commented "operational results should inform principles directly." State why the compiler refuses it, name the invariant violated, and rewrite the intended relationship as a valid CCDL fragment, specifying and justifying both parameters.

**16.3 — Size the maintenance.** A partition has `τ_leak = 480 h`. Compute the fraction of isolation surviving one 168-hour period, and the period at which per-cycle loss would fall below 10 %. Then state what the second figure tells a detector who can observe cadence but nothing else.

**16.4 — Classify the gap.** Three readings arrive. (a) A person cannot reconstruct most of a six-month stretch. (b) A person's recall, competence and self-account are intact except on one topic, where decomposition is unavailable and was not before. (c) A person cannot recall the name of a colleague they see weekly. Classify each as a `Q`-bearing notch, an ordinary broad gap, or neither, give the bench test that separates them, and say which of the three is *not* evidence of anything.

**16.5 — Compute the taper.** A formation carries `L = 3,600 h·Ω_c` at `I = 0.70 A_c` on a 24 `V_c` rail. Compute `V_kick` for an abrupt removal over 2 hours, then the minimum `dt` under the 3× ejection ceiling and under the 1× working bound. State which bound you would use and why, then convert the working-bound answer into weeks at three hours a week of on-path contact.

**16.6 — Find the violation.** A proposed CCB-DP listing reads, in part: `cjt dp1: CJT< material | facilitator_substrate => decompose > [beta=2.6];` with the comment "the subject's own substrate is not yet reliable enough to bias from." Name the requirement violated, explain why the comment is structurally *correct* and the stage is still wrong, and give the two-line correction. Then say what the corrected board now requires that the original did not.

**16.7 (Marquee) — Specify the counter for a maintained partition.** A substrate has been under a 168-hour external cadence for three years, with `n_parallel = 4`, `r_iso = 55`, `τ_leak = 720 h`, and a bias terminal reading `rπ_terminal = 2.1` against a baseline of 13.0. Specify the full CCB-DP parameter set, departing from this chapter's defaults where you can justify it. For every departure, name the failure mode you buy protection against and the capability you give up. Compute the taper bound and the substitution horizon on your own assumed `L`. Then state which of DP1–DP7 you cannot satisfy while the maintenance path is still connected, and what you would say to someone who asked you for a result in a month.
