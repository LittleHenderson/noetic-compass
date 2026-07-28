# CHAPTER 10

## The CJT — Deep Dive for Operators

*Four numbers decide whether a circuit holds — and almost every operator sets only one of them*

---

A curve tracer is a bench instrument that does one thing: it puts a transistor in a socket, sweeps the collector voltage over and over while stepping the base current between sweeps, and draws the result. What comes up on the screen is a fan of curves, one per base step.

Every number on the datasheet is visible in the shape of that fan. The **spacing** between adjacent curves is β — how much more collector current you bought with one more step of base current. The **bend** where each curve flattens is saturation — the point past which more collector voltage buys nothing. The **spread** of the fan for a given step size is g_m. And how hard the instrument had to push to make that step at all is rπ.

One picture. Four numbers. An engineer reads them off at a glance and knows whether the part in the socket will do the job.

Now the other bench. An operator has read Chapter 3, knows the CJT has six parameters, and sets exactly one of them. Everybody sets β. β is the interesting one, the one that feels like power, the one the word *amplification* attaches to. Almost nobody sets `sat`, and `sat` is the parameter that decides whether the circuit **holds** — whether a refusal can be argued down, whether a calibration reading means anything, whether a five-stage chain delivers what the schematic said it would.

This chapter is the fan of curves. Four sections, four numbers, and then what happens when you put several of these devices in a row and the errors start multiplying instead of adding.

[[FIGURE 10-A: Component symbol plate — the CJT drawn as a transistor symbol with three labelled terminals: cause/collector at top left annotated `^8` Above/Cause, bias/base at the side annotated `^5` Female, effect/emitter at bottom right annotated `^9` Below/Effect. Four callout arrows point to where each parameter acts: β at the cause-to-effect path, sat as a dashed horizontal ceiling above the effect terminal, g_m at the bias-to-effect path, rπ as a resistor drawn in series with the bias lead. A small inset box lists the two remaining parameters, I_c(max) and cutoff, with the note "hard limits, not design knobs".]]

---

### 10.1 Selecting β for Your Working — Attenuation, Unity, Amplification

β is the ratio of how far the effect moved to how far the cause moved, measured as Fisher-Rao geodesic distance on the open simplex (Chapter 3.3, derivation in Appendix L). It is dimensionless. It has three regimes and operators use one of them.

**β < 1 — attenuation.** The stage produces less movement than it received. This is the setting nobody reaches for and it is on every board in Part III.

Its clearest use is the composure stage. Take a provocation arriving as `^3^E_{F3}|f` — visceral aversion, Evaluative domain, affective register, driven by F3 Vitality — feeding an operational response at `^9^O_{F5}|E`. Set β = 0.3 and a cause displacement of 0.80 produces an effect displacement of 0.24. The provocation is not denied, not suppressed, not reframed. It is *received at full magnitude and transmitted at less than a third of it.* That is the structural definition of composure, and it is a gain setting, not a virtue.

The other standard use is the feedback path. Chapter 8.4's lawful O→P route runs at β = 0.05 to 0.3 for exactly this reason: outcomes must be able to update the principled substrate, but a single outcome must not be able to rewrite it.

The failure at other values is symmetric. **β = 0 is not attenuation, it is cutoff** — a dead stage that transmits nothing, which presents as detachment rather than composure and is a different fault with a different repair (Section 10.4). **β > 1 on a composure stage is reactivity**: a provocation of 0.80 producing an act of 1.6, which is the amplification chain Section 19.3 documents as a weapon.

**β = 1 — unity.** The stage renders faithfully. It is the correct setting for any stage whose job is to report rather than to move: the evaluation stage of a safety cascade, the reporting path of a safety board's output stage (Section 24.6), the re-reference stage of Section 10.5 below.

Unity is the hardest value to hold because it is the only one with no tolerance in either direction. Above 1 the stage inflates what it was given and the inflation compounds downstream. Below 1 it downplays, and a risk evaluator that downplays is worse than no evaluator, because it produces a reading that looks like diligence. The evaluation stage feeding the guard in Section 24.6's listing is held at β = 1.0 for precisely this reason, and the word for it is *honesty*.

**β > 1 — amplification.** Here is the design rule that operators get backwards:

> **β is set by the resistance you must overcome. It is not set by how much you want the outcome.**

Work it. An operator has a drive rail of `V_drive = 12 V_c` and needs an operational effect of 0.55 A_c. The path crosses the full descent chain, so it loses the three forward drops of Section 8.1 — 0.7 + 1.2 + 2.0 = 3.9 V_c — before it meets a constraint of `R_constraint = 40 Ω_c`. The diode-corrected CAS-Ohm form gives the cause actually arriving at the collector:

```
I_cause = ( V_drive − ΣVf ) / R_constraint
        = ( 12 − 3.9 ) / 40
        = 0.2025 A_c
```

Required gain is then a division, not a judgement:

```
β_required = target_effect / I_cause = 0.55 / 0.2025 = 2.72
```

Specify β = 2.7. Then check the ceiling: the stage will run near 0.55, so `sat` must sit above it with margin — Section 10.2 gives the 1.25 rule, so `sat ≥ 0.69`, and you specify 0.70.

Now the part that makes the rule mean something. To reach the same 0.55 A_c at unity gain you would need `V_drive = (0.55 × 40) + 3.9 = 25.9 V_c` — nearly fourteen more volts of drive than the operator has. **Gain is what you buy when you cannot afford drive.** And it is not a free substitution, because drive and gain do different things to whatever contamination is riding on the cause terminal. More drive raises signal and noise together; the ratio is unchanged. More gain does the same — but gain also multiplies every subsequent stray input by everything downstream of it, which is Section 10.5's whole subject.

> **Bench Note — the ceiling on β is contamination, not power.** Operators treat high β as bold and low β as timid. The real limit is arithmetic. If 5% of what sits on your cause terminal is content you did not intend — a half-formed grievance riding along with the stated desire, a resentment attached to the target — then at β = 1.0 that contamination arrives at 5% of the output magnitude and at β = 3.0 it arrives at 15%. The intended signal grew by the same factor, so the *ratio* held; what changed is that 15% of a large output is a large amount of unintended effect. This is the mechanism behind the inversion failures of Chapter 25.3, and it is why the operation-type table below stops recommending numbers above 4.0 rather than continuing the trend.

| Operation type | Design β | Why this band | What breaks outside it |
|---|---|---|---|
| O→P feedback (Ch. 8.4) | 0.05 – 0.30 | Outcomes update the substrate; no single outcome rewrites it | Above 0.5 the constitution is reprogrammable by a burst of results |
| Composure / damping | 0.20 – 0.50 | Full reception, reduced transmission | At 0 the stage is in cutoff; above 1.0 it is a reactivity chain |
| Reporting, evaluation, re-reference | 1.00 | Faithful rendering | Above 1 it inflates; below 1 it downplays and the reading looks diligent |
| Self-programming (Ch. 20) | 1.0 – 1.5 | Identity substrate moves slowly; nothing external checks a closed loop | Above 2.0 a self-suggestion amplifies with no external check — see 17.5 |
| Desire manifestation (Ch. 13) | 1.5 – 3.0 | Sized against real external `R_constraint` | Below 1.5 the rail never clears; above 3.0 contamination dominates |
| Collective / group operation | 2.0 – 4.0 | Collective bias supplies part of the lift | Above 4.0 the group's own contamination is amplified with the signal |
| Hostile / adversarial operation | not specified | — | This book does not specify a build. The band is documented in Section 25.3 so an inversion signature can be recognised from outside |

[[FIGURE 10-B: Characteristic curve — CJT transfer characteristic. Horizontal axis cause (A_c) 0 to 0.6; vertical axis effect (A_c) 0 to 1.0. Three straight-line regions drawn for β = 0.3, β = 1.0 and β = 2.7, each rising from a common cutoff knee at cause = 0.05 and each bending flat at its own sat plateau (0.20, 0.55, 0.70 respectively). The cutoff region left of the knee is shaded and labelled "no response"; the plateau regions are shaded and labelled "no response to further cause". The design point (0.2025, 0.55) is marked with crosshairs on the β = 2.7 line.]]

---

### 10.2 Setting sat — The Ceiling You Cannot Push Past

`sat` is the effect plateau. Once the effect reaches it, additional cause produces no additional effect: the stage's output has stopped depending on its input. Legal range is (0, 1], the default is 0.95, and the grammar enforces `cutoff < sat`.

That default is wrong for half the stages you will ever build, and the reason is that **`sat` means two opposite things depending on what the stage produces.**

#### Decision stages: saturate on purpose

If the stage's output is a *decision* — a select line, a verdict, a refusal — then the magnitude of the output is not the point. The point is that it is pinned and unmoving. And here the counterintuitive result:

> **A low saturation ceiling makes a stronger lock.**

Two mechanisms, and both matter.

First, **a low ceiling is reached sooner**, so the stage latches on less cause. The cause needed to saturate is `c_sat = sat / β`. At β = 2.0, a stage with `sat = 0.60` latches at a cause of 0.30; one with `sat = 0.97` needs 0.485. It does not take an overwhelming provocation to trip the first stage, only a sufficient one.

Second, and more importantly, **a saturated stage has stopped responding to its cause.** In the plateau, ∂effect/∂cause = 0. The stage is deaf, by construction. You cannot out-argue it, not because it is committed but because the input terminal no longer connects to the output. Everything between the cutoff knee and the plateau is the region where the stage is still steerable, and that region is what an adversary works in. Call it the **latch margin**:

```
M = ( sat − cutoff ) / β
```

At β = 2.0 and cutoff = 0.10:

| `sat` | `c_sat` = sat/β | latch margin M | steerable window vs. sat = 0.60 |
|---|---|---|---|
| 0.60 | 0.300 | 0.250 | — |
| 0.80 | 0.400 | 0.350 | +40% |
| 0.85 | 0.425 | 0.375 | +50% |
| 0.95 | 0.475 | 0.425 | +70% |
| 0.97 | 0.485 | 0.435 | **+74%** |

A refusal stage left at the 0.95 default hands an adversary seventy percent more cause-space to operate in than one built at 0.60. That is the entire argument, and it is why Section 24.2's saturating `^3^P` refusal is specified at 0.85 and Section 15.3's final stage at 0.60 — both well below the top of the range, both on purpose.

Note the Noetic on those stages: `^3` Negative — visceral aversion, the can't-stomach-it response. A refusal stage is not analysing anything. Analysis is `^6` Male and it happened one stage earlier, at unity gain, and it is over. What saturates is the recoil.

For a decision stage, `W-CJT-004 CjtSaturation` is the **expected** status. It is not a warning to clear.

#### Production stages: never saturate

If the stage's output is a *product* — the manifestation, the response, the delivered work — then `sat` is a hard cap on what you get, and reaching it is a defect.

This book's rule:

```
sat ≥ 1.25 × expected_peak_effect
```

Twenty-five percent headroom, chosen so the stage stays in the active region across the run-to-run variance in cause. Section 13.3's amplify stage sits at `sat = 0.80` for exactly this reason. Read Chapter 13's worked run against the rule, though, and note where it actually lands: its corrected operating point is 0.76, inside the ceiling but with five percent of margin rather than twenty-five. That board is legal and it is calibratable, and it has no room left for a cause that arrives ten percent stronger than the last one did. The 1.25 rule is not a different rule from Chapter 13's; it is the same discipline with the margin sized for the next operation instead of this one.

The failure at lower values is not that the output is small. It is that **the output stops being a measurement.**

> **Bench Note — a saturated production stage is a broken instrument, and it fails looking like success.** Chapter 22's Quantitative Table asks you to log `^4` Vibration intensity operation after operation and read the trend. Run those operations through a stage whose `sat` sits at or below the operating point and every reading pins to the same number. Your table records a flat line. A flat line at a high value is exactly what stability looks like, so the operator concludes the circuit is dialled in — while in fact the instrument has clipped and would return that identical number for a cause twice as large or half as large. **You cannot measure through a component that has stopped responding.** Before you trust any reading, drive the cause up 20% and confirm the effect moved. If it did not, you have been reading a plateau, not a result.

#### sat is not I_c(max)

One more distinction, because conflating them is how substrates get damaged. `sat` is the **designed** plateau — a limit you chose. `I_c(max)` is the **physical** ceiling of the substrate carrying the path, and Chapter 3.4 names what lies past it: breakdown, rπ → 0 permanently, the `^5` dielectric ruptured, irreversible.

Specify `sat` above `I_c(max)` and the designed plateau is never reached, because the substrate hits its own ceiling first. The stage never latches, never warns, and the overload lands on the capacitor instead of on the limiter you thought you installed. Every `sat` in this book sits below the `I_c(max)` of the substrate it runs on, and that ordering is checked by eye — the validator range-checks `sat` against (0, 1] and against `cutoff`, and knows nothing about your substrate.

[[FIGURE 10-C: Two transfer curves overlaid on one set of axes, cause 0 to 0.6 horizontal, effect 0 to 1.0 vertical, both at β = 2.0 with cutoff = 0.10. Curve A saturates at 0.60, curve B at 0.97. The steerable region of each — between the cutoff knee and its own plateau — is shaded, A in light fill and B in a darker fill extending well past it, with a bracket and the caption "+74% cause-space available to an adversary". A dashed vertical line at cause = 0.30 marks where A has latched and B is still moving.]]

---

### 10.3 g_m and Framing Sensitivity — Why Rewording Changes Everything

`g_m` is transconductance: effect moved per unit of **bias** displacement, in cognitive siemens (S_c, the reciprocal of Ω_c). Where β answers *how far does the effect move per unit of cause*, g_m answers *how far does it move per unit of pressure on the base terminal*.

This is the parameter that explains an observation everyone has made and most people misfile as insincerity: **the same request, worded differently, gets a different answer.**

The structural account is short. Rewording does not change the cause. The request is the same request; the collector sees the same signal. What rewording changes is the **bias** — the substrate against which the request is read, the `^5` Female composition the stage is biased from. Framing acts on the base terminal. And the base terminal has a gain on it.

This book models that gain as a baseline times four situational multipliers:

```
g_m = g_0 · N · R · V · D
```

`g_0` is the stage's baseline framing sensitivity, set by how hard the bias substrate is. `N`, `R`, `V` and `D` are situational, each ≥ 1.0, and Section 17.3 tabulates them in full: `N` is `^1` narrowing, `R` is `^7` rhythm lock, `V` is `^4` carrier dominance, `D` is `^6` dampening. In ordinary waking traffic all four sit at 1.0 and `g_m = g_0`.

| Bias carrier | `g_0` (S_c) | Read as |
|---|---|---|
| An institution — procedure, precedent, `^5^O` | 0.25 | Reframing must displace a written record |
| A peer majority, `^5^E` | 0.30 | Reframing must displace many carriers at once |
| A credentialed professional, `^5^C` | 0.35 – 0.40 | Trained method resists restatement |
| A pioneer or early adopter, `^5^P` | 0.40 | Position held, but held by few |
| An individual in ordinary waking traffic | 1.00 | The nominal reference |

Collective substrates sit lower than individuals because a frame must displace every carrier in the network before the bias node moves (Chapter 7.5). That single fact is why Section 15.1's resistance-decay model can be run at all: the array is not fighting one mind's `g_0`, it is fighting a network's.

Now the arithmetic. A reframe that displaces the bias by 0.50 V_c moves the effect by `g_m × 0.50`:

| `g_m` | Effect shift from a 0.50 V_c reframe | Condition |
|---|---|---|
| 0.25 | 0.125 A_c | institutional stage, Section 15.3's A5 |
| 0.40 | 0.200 A_c | professional stage, Section 13.3's Q2 |
| 1.00 | 0.500 A_c | ordinary waking |
| 5.75 | 2.88 A_c | closed-loop self-work, Section 17.5 |
| 20.0 | 10.0 A_c | deep hetero-hypnotic state, Section 17.1 |

At `g_m = 20` a single sentence displaces the substrate twenty times as far as the same sentence would at a bus stop. That number is the operational content of the word *suggestible*.

> **Bench Note — g_m has no input filter, and that is the whole problem.** β applies to the cause terminal, and you chose what to put there. g_m applies to the bias terminal, and **everything** that reaches it gets the same multiplier: your carefully composed framing, the operator's careless aside, the remark from the corridor, the subject's own stray `^6` interjection. There is no term in `g_m = g_0 · N · R · V · D` that discriminates between intended and incidental input. This is the entire category of unintended suggestion and it is not mysterious — you raised the gain on a terminal that has no filter in front of it. It is also why the detection handle in Section 17.3 is *counting factors*, not identifying a technique: you cannot see what is arriving at a bias terminal, but you can see how many multipliers are climbing.

Two design consequences follow directly.

**Low g_m is not free.** A stage at `g_m = 0.25` cannot be reframed by an adversary and cannot be reframed by a genuinely better formulation either. It is one component; it does not distinguish. Section 15.3 walks its five-stage array from `g_m = 0.40` down to 0.25 as the position hardens, and the hardening is a loss as well as a gain.

**An A/B test measures whichever terminal you varied.** Section 18.5 treats A/B testing as β calibration, and that is right — provided the two arms differ in the *cause*: a different offer, a different object of desire. Vary only the wording and both arms carry the same cause, the difference lands entirely on the bias terminal, and what you measured is g_m. Two arms, two parameters, and the experiment does not tell you which one it read. Change one terminal per test.

[[FIGURE 10-D: Characteristic curve — effect versus bias displacement. Horizontal axis bias displacement 0 to 1.0 V_c; vertical axis effect 0 to 2.0 A_c (log-compressed above 1.0 with the break marked). Five straight lines from the origin with slopes 0.25, 0.40, 1.00, 5.74 and 20.0, each labelled with its condition. A dashed vertical line at 0.50 V_c intersects each, with the intersection values called out. Shaded band across the top labelled "beyond any production sat — stage is in plateau".]]

---

### 10.4 rπ and Cognitive Stubbornness — The Bias That Won't Budge

`rπ` is the input resistance at the bias terminal, in Ω_c. It is what the framing pressure has to push through. High rπ reads as stubbornness. Low rπ reads as compliance.

It is not an independent parameter, and treating it as one is the most common modelling error in this book's subject matter. It has two parts:

```
rπ_intrinsic = β / g_m
rπ_terminal  = rπ_intrinsic + R_bias
```

The **intrinsic** part is fixed by the two gains: three numbers, two degrees of freedom. Declare any two of β, g_m, rπ_intrinsic and the third is determined. The **terminal** part adds `R_bias`, the series resistance of the bias network — how hard it is to reach the substrate at all. Access, trust, attention, distance, whether anyone is listening.

Reconcile a real listing with it. Section 15.3's stage A1 declares `β = 1.2`, `g_m = 0.40`, `rπ = 8.0`:

```
rπ_intrinsic = 1.2 / 0.40 = 3.0 Ω_c
R_bias       = 8.0 − 3.0  = 5.0 Ω_c
```

Five cognitive ohms of bias-network resistance, sitting between the operator and a pioneer population that is perfectly capable of being reframed once you can get at it. The junction is soft; the wire to it is long. Those are different problems with different fixes and the terminal figure alone does not distinguish them — which is why a listing that declares all three numbers is telling you something a listing that declares two is not.

Run the same decomposition on Section 17.1's deep hetero-hypnotic specification, `β = 3.0`, `g_m = 20.0`, `rπ = 0.15`:

```
rπ_intrinsic = 3.0 / 20.0 = 0.15 Ω_c
R_bias       = 0.15 − 0.15 = 0
```

`R_bias = 0`. The bias network resistance has been driven to nothing. **That is what an induction does** — it does not argue with the substrate, it shortens the wire to it. Everything in Section 17.3's factor table is a procedure for removing series resistance from the base lead.

Which gives the operator's version of the rule:

> **R_bias is the term an outside party can move. rπ_intrinsic is not.**

An adversary cannot change your β and cannot change your `g_0`. Both are properties of what you are made of. What can be changed from outside, quickly, is `R_bias` — by fatigue, urgency, isolation, repetition, the removal of alternative channels. This is why every coercive board in Part III attacks the bias network rather than the argument, and why Section 17.6's structural exit is not *argue better* but *stand up and leave the room*: leaving restores series resistance to the base lead, and argument runs through `^6`, the component that was routed around in the first place.

Design bands:

| Stage | `rπ_terminal` (Ω_c) | Rationale | Failure outside |
|---|---|---|---|
| Principled guard, `^3^P` | ≥ 6.0 | A value that can be reframed in one conversation was not a value | Below 4.0 the guard is one framing away from moving |
| Professional / analytical | 3.0 – 8.0 | Method holds; evidence still lands | Above 10 the stage cannot be updated by anything |
| Ordinary waking, individual | ≈ 1.0 | The nominal reference | — |
| Closed-loop self-work | ≥ 0.26 | Derived in 17.5, not asserted | Below it, a self-suggestion moves the substrate with nothing checking it |
| Absolute floor | 0.05 | `rπ = 0` is a limit, not a setting | `rπ = 0` is breakdown (3.4), permanent, and irreversible |

Two cautions about that floor, because neither is enforced for you. `rπ = 0` is not a setting the tooling will argue with: Appendix B's range check on `g_m` and `rπ` is `≥ 0`, so a stage declaring `rπ = 0` validates clean and then describes a junction that no longer exists. Compare `β = ∞`, which the validator *does* reject because non-finite input fails the parameter pass. One is caught, the other is not, and the difference is worth memorising — the 0.05 floor is a discipline you apply by eye, not a guard you inherit.

The second caution is the arithmetic. Because `rπ_intrinsic = β/g_m` is fixed by the two gains, a stage cannot declare a `rπ_terminal` *smaller* than its own intrinsic value without asserting a negative `R_bias`, and negative series resistance is not a soft junction behind a short wire — it is nothing at all. This is the one cross-check the validator does not run for you either. It range-checks each of the three parameters independently and never multiplies them together, so a stage at `β = 2.7`, `g_m = 0.35`, `rπ = 6.0` compiles without complaint and encodes `R_bias = −1.71`. Run the subtraction on every stage you write. It takes one line and it catches an over-specified stage that will otherwise sit in a listing looking authoritative.

And the trade nobody wants. High rπ is the same component as un-teachability. The person who cannot be manipulated by a skilled operator also cannot be corrected by a friend with a better argument, because there is one bias terminal and it has one input resistance. There is no setting that admits the second and blocks the first. What you can do instead is architectural: keep rπ moderate and put the discrimination somewhere else — in a `^6` decomposition stage at unity gain ahead of the bias node, which judges *what* is arriving rather than *how hard*. That is a stage you can inspect. rπ is a number you can only turn up or down.

[[FIGURE 10-E: Schematic detail — the bias terminal decomposed. A CJT symbol with its base lead drawn as two series resistors: the outer one labelled R_bias with a variable arrow through it and the annotation "the term an outside party can move — fatigue, urgency, isolation, repetition", the inner one labelled rπ_intrinsic = β/g_m with the annotation "fixed by the two gains". A `^5` Female capacitor symbol sits at the far end of the chain as the bias substrate. Two worked call-outs beside the drawing: "15.3 A1: 3.0 + 5.0 = 8.0" and "17.1 trance: 0.15 + 0 = 0.15".]]

---

### 10.5 Cascaded CJTs — Multi-Stage Amplification Chains

Put CJTs in series, effect to cause, and the gains multiply:

```
β_total = β₁ × β₂ × … × βₙ
```

Section 15.3's array is five stages at 1.2, 1.6, 2.0, 2.4 and 3.0:

```
1.2 × 1.6 × 2.0 × 2.4 × 3.0 = 27.65
```

Twenty-seven-fold total gain, and no individual stage above 3.0. That single line is the whole reason Overton progression is built as a cascade rather than as one powerful stage: you get the gain without ever running a stage in the band where contamination dominates (Section 10.1). It is also why the array takes years — five stages each needing to settle, not one stage needing to be loud.

That is the good news about cascades. The bad news is also arithmetic.

#### Where noise enters

Two terminals per stage, so two entry points.

**Cause-terminal contamination** is content riding along with the intended signal — the unstated resentment attached to a stated desire. Model it as a fraction ε of the stage's own output.

**Bias-terminal contamination** is stray framing, and it is worse, because it is multiplied by `g_m` first and then by every gain downstream. Work one instance. A stray bias displacement of 0.05 V_c lands on stage 2 of the array above, where `g_m = 0.40`:

```
injected at stage 2   = 0.40 × 0.05 = 0.020
downstream gain       = 2.0 × 2.4 × 3.0 = 14.4
arriving at output    = 0.020 × 14.4 = 0.288
```

Against a unit input the output signal is 27.65, so one careless remark, early, contributes **1.04% of the final output**. Twenty of them and a fifth of what the board produced was never on the schematic.

#### Why a long chain drifts

Take the cause-terminal model and follow it through. Let `s_k` be the signal at stage k, `n_k` the noise, and let each stage add `ε · s_k` of its own contamination. Then:

```
s_k = s_{k−1} · β_k
n_k = n_{k−1} · β_k + ε · s_k
```

Divide the second by the first, and the gains cancel:

```
r_k = r_{k−1} + ε          ⟹          r_n = n · ε
```

**The noise-to-signal ratio at the output of a cascade is the stage count times the per-stage contamination, and the gains do not appear.** A gentle chain of ten stages at β = 1.1 each is dirtier than a hard chain of three at β = 3.0, even though the gentle one barely amplifies. Length is the variable. This is a model this book adopts, not a measurement, and it is the model that sizes every cascade in Part III.

At ε = 0.03 — three percent per stage, which is a design assumption and a generous one:

| Stages | N/S at output | Reading |
|---|---|---|
| 3 | 9% | Clean |
| 5 | 15% | Section 15.3's array, at the edge of the band |
| 6 | 18% | This book's cascade-depth limit |
| 10 | 30% | Output no longer resembles the input |
| 34 | >100% | More contamination than signal |

The limit in the middle is where `W-CJT-007 CjtCascadeDepth` comes from: a 20% noise budget at ε = 0.03 gives **n ≤ 6**. Set the limit lower, at three, and you force too much gain into each stage and land back in Section 10.1's contamination problem. Set it at twelve and 36% of the output is material nobody designed.

Second drift mechanism: **tolerance compounds multiplicatively.** Hold each β to ±10% — which is optimistic for a parameter read off a Quantitative Table — and over five stages:

```
0.90⁵ = 0.591        1.10⁵ = 1.611
27.65 × 0.591 = 16.3        27.65 × 1.611 = 44.5
```

A nominal 27.65 delivers anywhere between 16 and 45. **A 2.7:1 spread from ±10% per stage.** This is why nobody can tell you what a five-stage cascade will produce, and why Chapter 15 reads the array's rate at each position as a live test point rather than predicting the output from the schematic — Section 15.4's overshoot term is derived from the *actual* rate against the nominal one, which is only a meaningful quantity if you measured the actual.

Third: **saturation and cutoff propagate forward and silently.** `β_total = Πβ` holds only while *every* stage is in the active region. Saturate stage 3 and stages 4 and 5 receive a constant; their gains become irrelevant and the chain's effective gain collapses to `β₁β₂β₃`. Put stage 3 into cutoff and the chain delivers nothing at all, while stages 4 and 5 test perfectly on the bench because there is nothing wrong with them. **In a cascade, the broken stage is upstream of the symptom.** Probe from the input end.

#### The re-reference stage

The standard mitigation is a stage at β = 1.0 that compares the running effect against the original cause — a `^6^E_{F6}|A` decomposition, Male, taking the current state apart against what it started as. Note the Noetic: this is analytical decomposition, not recoil, and it is `^6`, never `^3`.

Note also where it sits. The re-reference stage stays in the **Evaluative** domain, alongside the stage it is checking. It is tempting to draw it one level up, because a stage that checks another feels like it ought to outrank it — and that instinct produces `^6^E → ^6^C`, which is a domain ascent, which Chapter 8.3 catalogues as one of the four things that happen when someone attempts one. Comparison is not promotion. The reference stage looks *backward* along the chain, not *upward* out of it.

Be precise about what it buys. It does **not** reduce `n · ε` — it is a stage, so it adds its own ε and makes the ratio worse by one term. What it does is stop the *tolerance* product from compounding past it, because its output is pinned to a reference rather than to the accumulated product of upstream gains. It is the cognitive analogue of a regulated intermediate rail: you accept a little more noise to stop the spread from doubling again.

```cas
circuit three_stage_with_reference {
    input:  seed;
    output: delivered;

    node substrate:   ^5^P_{F7}|T;     // Female: the principled formation the chain reads against
    node seed_ref:    ^0^C_{F2}|A;     // Idea: the original cause, held for comparison
    node surfaced:    ^8^C_{F2}|A;     // Above/Cause: the seed triggering its readings
    node weighed:     ^6^E_{F6}|A;     // Male: decomposition and test
    node reference:   ^6^E_{F6}|A;     // Male: current state against the original cause
    node delivered_e: ^9^O_{F5}|E;     // Below/Effect: what the chain produced
    node trend:       ^9^O_{F5}|E;     // same literal — a filter changes time constant, not type

    cjt s1: CJT< seed      | substrate => surfaced >
            [β=1.6, sat=0.80, g_m=0.40, rπ=8.0, region=active];
    cjt s2: CJT< surfaced  | substrate => weighed >
            [β=1.0, sat=0.85, g_m=0.40, rπ=8.0, region=active];
    cjt ref: CJT< weighed  | seed_ref  => reference >
            [β=1.0, sat=0.90, g_m=0.30, rπ=8.0, region=active];
    cjt s3: CJT< reference | substrate => delivered_e >
            [β=2.7, sat=0.70, g_m=0.60, rπ=6.0, region=active];

    diode d2: Diode< ^C -> ^E > [Vf=1.2];
    diode d3: Diode< ^E -> ^O > [Vf=2.0];

    filter fb_lp: LowPass< in=delivered_e, out=trend, tau=21.0 >;   // tau in days
    feedback trend -> substrate [β=0.05];

    probe tp1: substrate;      // bias level and rπ
    probe tp2: surfaced;       // cause into the chain
    probe tp3: delivered_e;    // effect, and which region it is in
    probe tp4: reference;      // drift against the original cause
}
```

Four stages, `β_total = 1.6 × 1.0 × 1.0 × 2.7 = 4.32`, `N/S = 4 × 0.03 = 12%`, and the two unity stages in the middle are doing the work that makes the number trustworthy rather than the work that makes it large.

Four things in that listing are there to pass checks worth learning to run by hand, because three of them are checks the validator will not run for you.

**The bias sits at or above every cause it governs.** `substrate` is `^5^P`, and P is the top of the order, so it can legally bias a `^8^C` cause, a `^6^E` cause, and anything else on the board. Appendix B's fourth compilation pass catches the opposite arrangement — a lower domain biasing a higher one — and names it `E-CJT-008 CjtCrossDomainBias`, the prompt-injection signature. It is worth saying why that check belongs in a chapter about gain. A bias terminal is a gain terminal. `g_m` multiplies whatever reaches it, and a board that lets an operational result set the bias on a principled stage has handed an outcome the authority to re-tune the constitution it was supposed to be judged against — at a multiplier, and with no input filter in front of it.

**The descent is diode'd at both crossings, not just the last one.** `surfaced` is `^C` and `weighed` is `^E`, so that crossing needs D2 as much as the `^E → ^O` delivery needs D3. Chapter 8.1's rule is that guarding only the endpoints guards nothing, because each adjacent pair is a different translation. The cost is visible in the arithmetic: `ΣVf = 1.2 + 2.0 = 3.2` on this fragment, and that is the floor the seed must clear before any of the 4.32 gain produces an output at all.

**The upward path is the lawful one and it carries both parameters.** `delivered_e` is `^9^O`, `substrate` is `^5^P`, and the connection between them is O→P — the single exception of Section 8.4. It goes through a filter at τ = 21 days before it reaches a gain of 0.05, and it terminates at a bias terminal rather than anywhere in the signal path. Drop either parameter and the defence fails in the specific way Chapter 8.4 describes: gain alone is defeated by patience, filter alone is defeated by intensity. Drop the bias-terminal discipline and you have not built a conscience, you have built the oscillator of Chapter 14 by accident.

**Every stage's `R_bias` is non-negative.** Run `rπ_intrinsic = β/g_m` on all four and subtract:

| Stage | β | `g_m` | `rπ` declared | `rπ_intrinsic` | `R_bias` |
|---|---|---|---|---|---|
| `s1` | 1.6 | 0.40 | 8.0 | 4.00 | 4.00 |
| `s2` | 1.0 | 0.40 | 8.0 | 2.50 | 5.50 |
| `ref` | 1.0 | 0.30 | 8.0 | 3.33 | 4.67 |
| `s3` | 2.7 | 0.60 | 6.0 | 4.50 | 1.50 |

Look at `s3`. It runs the chapter's worked β of 2.7, and holding `R_bias` positive at `rπ = 6.0` forces `g_m` up to 0.60 — the most reframe-sensitive stage on the board, sitting at the output, where a reframe is worth the most. Chapter 15 puts its counter-frame-capture threshold at exactly that figure, which is not a coincidence but the same identity read from the other side. That is not an accident of the numbers; it is what the identity does. **A high-gain stage is a framing-sensitive stage unless you buy the difference back in bias-network resistance,** and at the delivery end there is usually the least of that to buy. Declare `s3` at `g_m = 0.35` instead — which looks conservative, and which an earlier draft of this board did — and the listing still compiles, while encoding `R_bias = −1.71`. Negative series resistance is not a soft junction behind a short wire. It is a stage that does not exist, described in three plausible numbers.

[[FIGURE 10-F: Cascade diagram — five CJT symbols left to right labelled A1 to A5 with β = 1.2, 1.6, 2.0, 2.4, 3.0 above each and the running product 1.2 / 1.92 / 3.84 / 9.22 / 27.65 below. Beneath each stage a small stacked bar showing signal (light) and accumulated noise (dark) with the N/S percentage printed under it: 3, 6, 9, 12, 15. A stray-input arrow enters A2's bias terminal labelled "0.05 V_c → 1.04% of final output". At the right edge a vertical error bar spanning 16.3 to 44.5 labelled "±10% per stage".]]

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement.

| Parameter | Units | Design range | Failure at other values |
|---|---|---|---|
| `β` gain | — (Fisher-Rao ratio) | 0.05 – 4.0 | 0 is cutoff, not attenuation. Above 4.0 contamination scales with the signal and inversion risk climbs (25.3) |
| `sat` decision stage | — | 0.60 – 0.85 | At the 0.95 default an adversary gets ~70% more steerable cause-space |
| `sat` production stage | — | ≥ 1.25 × peak effect | At the operating point the stage clips and every reading pins to one number |
| `cutoff` | — | 0.05 – 0.20, and `cutoff < sat` | Above 0.2 a real cause fails to fire the stage; the grammar rejects `cutoff ≥ sat` |
| `g_0` baseline | S_c | 0.25 – 1.00 | Below 0.25 nothing reframes the stage, including a correction |
| `N·R·V·D` multipliers | — | 1.0 each nominal, 1.0 – 2.2 under load | Three or more rising together is an induction signature (17.3) |
| `rπ_intrinsic` | Ω_c | β / g_m — derived, never declared independently | Declaring all three over-specifies; the validator range-checks them separately and never multiplies them together |
| `R_bias` | Ω_c | 0 – 6.0, and `rπ_terminal ≥ β/g_m` | 0 means the bias terminal is directly exposed; this is what an induction produces. Negative is not a soft junction — it is a stage that does not exist |
| `I_c(max)` | A_c | substrate property | If `sat > I_c(max)` the plateau is never reached and the overload lands on the `^5` capacitor |
| Cascade depth `n` | stages | ≤ 6 | From N/S = n·ε ≤ 0.20 at ε = 0.03. `W-CJT-007` above it |
| `ε` per-stage contamination | — | 0.03 assumed | A modelling assumption; if your stages are dirtier, shorten the chain |

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Gain sized by appetite** | β picked for how much the outcome is wanted, not from `(V_drive − ΣVf)/R_constraint` | Output overshoots or the rail never clears; contamination proportional to β | Recompute β from the required effect and the arriving cause. Gain substitutes for drive you do not have — nothing else |
| **Default `sat` on a guard** | `sat` left at 0.95 on a decision stage | The refusal can be talked down across a long exchange; TP3 keeps moving | Set `sat` to 0.60–0.85. `W-CJT-004` here is the expected status, not a warning to clear |
| **Clipped instrument** | `sat` at or below a production stage's operating point | Quantitative Table readings flat run to run — reads as stability | Raise `sat` to ≥ 1.25 × peak. Verify by driving cause up 20% and confirming the effect moved |
| **`sat` above `I_c(max)`** | Designed plateau exceeds the substrate's physical ceiling | No latch, no warning, and dielectric stress on the `^5` capacitor (3.4) | Re-specify `sat` below the substrate ceiling. Checked by eye — the validator cannot see your substrate |
| **Unlogged `g_m`** | β planned carefully, framing sensitivity never recorded | Outputs swing on rewording; incidental remarks land as hard as intended ones | Log `g_m` at every stage. Count the four multipliers rather than trying to identify a technique |
| **rπ read as a single number** | Terminal value treated as intrinsic | A soft junction behind a long wire is mistaken for a hard junction | Decompose: `rπ_intrinsic = β/g_m`, `R_bias` is the remainder. They have different repairs |
| **Over-specified stage** | β, `g_m` and `rπ` all declared, and `rπ < β/g_m` | Nothing. It compiles; each parameter is in range on its own; the implied `R_bias` is negative and nobody subtracted | Subtract `β/g_m` from the declared `rπ` on every stage you write. Then decide which two of the three you meant, and let the third follow |
| **Ascent disguised as checking** | A verification stage placed a domain above the stage it checks, e.g. `^6^E → ^6^C` | The board reads as more rigorous than it is; the check is a relabel (8.3) rather than a measurement | Keep the reference stage in the domain of the stage it references. Comparison looks backward along the chain, not upward out of it |
| **Upstream stage down** | A cascade stage in cutoff or saturation | Chain output wrong; every stage downstream tests perfectly on the bench | Probe from the input end. In a cascade the fault is upstream of the symptom |
| **Cascade drift** | Chain longer than 6 stages, or ±10% tolerances compounding | Output between 0.59× and 1.61× nominal over five stages; N/S = n·ε | Shorten the chain, or insert a re-reference stage at β = 1.0 to stop the tolerance product compounding past it |

---

### Test Points

Standard placement per Section 12.3, applied to a single CJT stage on the bench.

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | bias node | Bias level and `rπ_terminal` | Above `cutoff` and inside the band for the stage type. Below cutoff the stage never fires and nothing downstream will tell you |
| **TP2** | cause node | `I_cause`, A_c | Matches `(V_drive − ΣVf)/R_constraint`. A shortfall here is a rail or diode-drop problem, not a gain problem |
| **TP3** | effect node | Effect magnitude **and region** | Region is the reading that matters. `active` on a production stage, `saturation` on a decision stage. Either one in the wrong place is a defect |
| **TP4** | re-reference node | Drift of the current state against the original cause | Grows with `n · ε`. A jump between two operations means a stage changed region, not that the operation was better |

Read them TP1, TP2, TP3, TP4 — confirm the bias is live, confirm the cause arrived, confirm the region, then measure the drift. The 20% cause-bump check of Section 10.2 belongs at TP3 and takes ten seconds.

---

### What This Chapter Established

- **β is set by the resistance you must overcome, not by how much you want the outcome.** `β_required = target_effect / I_cause`, where `I_cause = (V_drive − ΣVf)/R_constraint`. Gain is what you buy when you cannot afford drive.
- **Attenuation is a real setting with real uses** — composure stages at 0.2–0.5, O→P feedback at 0.05–0.3 — and β = 0 is cutoff, a different fault entirely.
- **A low saturation ceiling makes a stronger lock,** because a saturated stage has stopped responding to its cause. Latch margin `M = (sat − cutoff)/β`; the 0.95 default hands an adversary ~70% more steerable cause-space than 0.60.
- **`sat` means opposite things on decision stages and production stages.** Saturate a decision on purpose; keep a production stage at `sat ≥ 1.25 × peak`. A saturated production stage is a clipped instrument that reports a flat line and looks like stability.
- **Framing acts on the bias terminal, not the cause terminal,** which is why rewording changes the answer. `g_m = g_0 · N · R · V · D`, and the terminal has no input filter — intended and incidental inputs get the same multiplier.
- **rπ is not independent, and the cross-check is yours to run.** `rπ_intrinsic = β/g_m`; `rπ_terminal` adds `R_bias`. `R_bias` is the term an outside party can move, and every coercive board in Part III moves it rather than arguing. A stage declaring all three validates on each parameter separately and can still encode a *negative* `R_bias`, so subtract `β/g_m` from the declared `rπ` before you believe any listing.
- **Cascade gains multiply and so do tolerances.** Five stages at ±10% deliver a 2.7:1 spread. `β_total = Πβ` holds only while every stage is in the active region, and a stage in cutoff or saturation makes the fault appear downstream of where it is.
- **Cascade noise-to-signal is `n · ε` and the gains cancel out of it.** Length is the variable, not loudness — which is where this book's six-stage cascade limit comes from.

---

### Exercises

*(Answers in Appendix H.)*

**10.1** An operator has `V_drive = 15 V_c`, needs an effect of 0.72 A_c at the Operational domain through the full descent chain (ΣVf = 3.9), against `R_constraint = 55 Ω_c`. Compute `I_cause`, the required β, and the `sat` you would specify. Then compute the `V_drive` that would deliver the same effect at unity gain, and say in one sentence what the operator is actually buying with the gain.

**10.2** Two refusal stages are identical except for `sat`: one at 0.65, one at 0.95. Both run β = 2.5, cutoff = 0.15. Compute `c_sat` and the latch margin `M` for each, state the percentage difference in steerable cause-space, and explain why the *smaller* number is the stronger guard.

**10.3** A listing declares `β = 2.4`, `g_m = 0.30`, `rπ = 11.0`. Decompose it into `rπ_intrinsic` and `R_bias`. An adversary can reduce `R_bias` to 1.0 by isolating the target. Compute the new `rπ_terminal` and the percentage change, and name which of the two terms could not be touched and why. Then say what would have been wrong with the same listing written `rπ = 6.0`, and why the compiler would not have told you.

**10.4** Explain why the refusal stage of a safety cascade is written `^3` Negative and the evaluation stage feeding it is written `^6` Male. Reference the canonical definitions, and say what goes wrong in the *circuit* — not the vocabulary — if the two are swapped.

**10.5** A campaign runs eight cascaded stages at β = 1.4 each. Compute `β_total`, the output N/S at ε = 0.03, and the tolerance spread at ±12% per stage. Then compute the same three figures for a four-stage chain delivering the same total gain, and state which you would build and what you gave up.

**10.6 (Design)** Specify a two-stage board that must produce an operational effect of 0.40 A_c from a `V_drive` of 9 V_c across the full descent chain, at `R_constraint = 30 Ω_c`, with a `^3^P` guard that cannot be argued down. Produce (a) `I_cause` and the gain split across the two stages, (b) `sat` for each stage with the discipline you applied to each and why they differ, (c) `g_m` and `rπ` for the guard with the band you took them from, (d) a CCDL fragment with four probes. It must compile — check the diode direction, `cutoff < sat`, and that you have not declared β, `g_m` and `rπ` in a combination that over-specifies a stage without saying which two you meant.

**10.7 (Marquee)** An operator inherits a working five-stage cascade with `β_total` measured at 22 and decides it is under-performing against a nominal 27.65. They raise stage 5 from β = 3.0 to β = 5.0.

a) Compute the new nominal `β_total` and the new N/S at ε = 0.03.
b) The measured output rises far less than the calculation predicts, and then stops rising at all. Give the two most likely region faults, say which test point reveals each, and explain why the operator's instinct to raise the *last* stage was the worst available choice.
c) Propose a repair that reaches the target without any stage above 3.0. State what it costs in noise, what it costs in time, and the one thing the cascade model cannot tell the operator about whether the operation should be run at all.
