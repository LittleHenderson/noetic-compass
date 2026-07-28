# CHAPTER 11

## Special-Purpose Components

*The five parts that do not amplify — they decide, they clock, they select, they compare, and they match*

---

Open a quartz wristwatch and find the smallest part in it: a metal can the size of a grain of rice, with two wires. Inside is a sliver of quartz trimmed until it vibrates 32,768 times a second. That number is not round by accident. It is 2^15 — halve it fifteen times with fifteen flip-flops and you get one pulse per second, forever, with nothing to accumulate error.

The crystal has no gain. It amplifies nothing. It produces a rhythm stable enough that everything downstream can be built on the assumption the rhythm is right.

Chapters 6 through 10 gave you the parts that carry the signal — resistor, capacitor, diode, inductor, and the Cognitive Junction Transistor. Every one answers *how much gets through*. None of this chapter's five answer that question. A fuse answers *whether, ever again*. An oscillator answers *at what rate and in what pattern*. A filter answers *which rates survive*. An op-amp answers *which of two things is larger*. A transformer answers *at what working point*.

These five fail quietly, because a part with no gain gives no symptom when it is wrong. A fuse that cannot blow looks exactly like a fuse. You find these defects by reading parameters against each other, not by watching output.

[[FIGURE 11-A: Symbol plate — F1 fuse (rectangle with diagonal element, terminals "path in"/"path out", box for threshold and action); OSC1 (square wave in a circle, annotated period/duty/sustain); FLT1 drawn three times, as lowpass, highpass and notch blocks with response glyphs inset; U1 op-amp triangle, + and − inputs, one output, shared bias terminal at the base; T1 transformer, two coils across a double core, labelled n.]]

---

### 11.1 Fuses — Permanent Path Blocking

A fuse is the only component in this book whose entire specification describes how it fails. It conducts, then at one specified point stops, and never conducts again.

```cas
fuse f1: Fuse< path=carried, threshold=0.90, action=permanent_block >;
```

**`path`** — what the fuse sits in series with. It senses activation on that path and opens it.

**`threshold`** — the activation at which it opens, on [0, 1]. The default here is **0.90**, for the reason a mains fuse is rated well above normal load. At **0.50** it trips on ordinary variance: any path with healthy dynamic range crosses its own midpoint routinely, so a 0.50 fuse makes a working board single-use for nothing. At **0.99** it is decorative, because well-designed paths rarely reach a percent from unity. Nuisance tripping and never tripping are both fuse failures.

> **Bench Note — a fuse above the path's ceiling is a part guaranteed to do nothing.**
> Every path has a ceiling: a CJT plateaus at its `sat`, a capacitor at full charge, a rail at its supply. Put `threshold` above that ceiling and the fuse can never trip, and nothing in the listing complains. Chapter 24 makes the trap concrete: 24.2 specifies a refusal CJT saturating at **sat = 0.85**, 24.3 an enforcement fuse at **threshold = 0.90**. Place that fuse across that CJT and it is dead metal — the node plateaus five hundredths below the threshold, forever. So it must not go there. It belongs in series with the enforcement path downstream, whose ceiling is higher than 0.90; check that placement on any CSB you are handed, including the one in this book. Read `threshold` and `sat` together or read neither. The compiler takes your word about what you are guarding.

**`action`** — what "open" means. Six legal values, not interchangeable. `permanent_block` cuts the path for the life of the board, no reset — what enforcement requires (Chapter 24.3). `permanent_until_manual_reset` is a breaker: cut until a human clears it. `block_until_decomposed` cuts until `^6` Male decomposition has run on what tripped it. `defer_decision` holds pending a later read — timing, not safety. `open_feedback` cuts the O→P loop instead of the signal path, freezing a drifting constitution — the slew fuse on CCB-SELF's evidence return (Chapter 20.5). `warn` logs and passes.

`warn` is the one to watch: a board with it on the enforcement path validates clean, reads as a safety board, and has no latch.

**Once blown, blown.** This is the component form of Chapter 21.5's section-retraction result: the chain runs one way, and going back does not restore what you had. That is the whole value — a refusal that can be retried into an acceptance was never a refusal — and the whole cost, because a fuse blown by a false positive stays blown. Saturation and a fuse are two locks: saturation latches the **decision** and releases when the cause drops; the fuse latches the **path** and never releases.

[[FIGURE 11-B: Fuse characteristic — x-axis path activation 0 to 1, y-axis conductance 0 or 1, a step falling to zero at 0.90 with a one-way arrow on it. Overlaid: a shaded band 0 to 0.85 labelled "guarded path's sat ceiling", the 0.90 marker outside it marked "can never trip", a marker at 0.80 inside it marked "reachable".]]

---

### 11.2 Oscillators — Generating Cognitive Rhythms (^7)

`^7` **Rhythm** is *the rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.* The definition names two quantities: **rate** is the period, **pattern** is the duty cycle. An oscillator sets both.

```cas
osc clock: Oscillator< signal=claim, source=cadence, period=7.0, duty=0.15,
                       sustain=90.0 >;                       // days
```

It adds no energy. It converts a *sustained* drive into a *periodic* one, and it is worth a component because of Chapter 7.3: the `^5` Female capacitor leaks. One overwhelming impression does not hold; a smaller one redeposited before the last drains will.

That is a charge pump, and it has arithmetic. Let each exposure deposit `q` into a capacitor with leakage time constant `τ_leak`, on the 0–10 scale of Chapter 7.2:

```
Q_max = q / (1 − e^(−T/τ_leak))       Q_min = Q_max × e^(−T/τ_leak)
ripple = q                             (always — the ripple IS one pulse)
```

Take `τ_leak = 30 days`, `q = 0.8`, and vary the period.

| `T` (days) | `Q_max` | `Q_min` | ripple / `Q_max` | Character |
|---|---|---|---|---|
| 1 | 24.4 → clips at 10 | 10 | 0% | Pinned; every pulse after the first fortnight is spent for nothing |
| 7 | 3.84 | 3.04 | 21% | Design point |
| 10 | 2.82 | 2.02 | 28% | Ripple limit |
| 30 | 1.27 | 0.47 | 63% | Impression, gone, impression, gone — no plateau forms |

Thirty times the frequency buys a *pinned* substrate, not a proportionally larger one: the ceiling arrives before the arithmetic does. The last row is the commoner failure, experienced as starting over each time.

**Design rule: `T ≤ τ_leak / 3`.** That holds ripple under about thirty percent, where the plateau reads as a level rather than separate events. Above `τ_leak` there is no plateau; far below `τ_leak / 10` you pay for pulses landing on a full capacitor.

**Duty cycle** is the half operators skip. Design band: **0.10 to 0.25**. The gap is not wasted — it is where the mind runs its own `^6` Male decomposition, which makes the resulting `^5` composition the mind's own rather than a recording. At **duty ≥ 0.6** you have a DC level rather than a rhythm, and `^4` Vibration per exposure falls, because `^4` is *the degree to which an Idea resonates with the Mind, its impression*, and impression requires contrast. That is why over-frequency is a real advertising failure, not merely a budget one.

> **Bench Note — the objective is to make the oscillator unnecessary.**
> `sustain` is not "how long the campaign runs." It is how long you drive the pattern externally before the substrate supplies its own clock. Once entrained — entrainment is written into the canonical `^7` definition, not added by us — the `^8` Above/Cause cue fires at the expected time whether or not you present anything: associative triggering doing exactly what `^8` does, one Idea bringing another to Mind. Set `sustain ≥ 3 × τ_leak`, then run the test: **stop the external clock and see whether the cadence continues.** If it does, switch `source` to `internal`. If not, you rented a rhythm rather than building one.

[[FIGURE 11-C: Two stacked panels, shared time axis in days. Upper: pulse train, period 7 days, duty 0.15, both dimensioned. Lower: charge as a sawtooth climbing to a plateau between 3.04 and 3.84, exponential envelope drawn in, the 90-day mark labelled "stop the clock here", plus a ghosted T = 30-day sawtooth at 63% ripple with no plateau.]]

---

### 11.3 Filters — Lowpass (τ dampening), Highpass, Notch

A filter passes some rates of change and destroys the rest. Define every filter by what it destroys; define it by what it passes and you will install one that quietly deletes the thing you needed.

**Lowpass.** One parameter: τ, the dividing line between a trend and a spike.

```cas
filter lp: LowPass< in=carried, out=trend, tau=21.0 >;   // days
```

A disturbance of duration `d` arrives attenuated to `1 − e^(−d/τ)` of its amplitude. At the τ = 21-day default of Chapter 8.4: **1 day survives at 4.6%, 3 days at 13.3%, 21 days at 63.2%, 63 days (3τ) at 95.0%.**

**What it kills** is the single dramatic event — the point, and why the O→P feedback of Chapter 8.4 is filtered before it reaches the constitution. **What it also kills** is a *genuine* permanent change. That last figure is a bill, not a bonus: an operator on a 21-day filter is two months behind a real change in their circumstances. Chapter 24.5 scales τ by experience, floor one week.

**Highpass.** The exact complement — it passes rapid change and destroys the baseline.

```
highpass(x) = x − lowpass(x)
```

So you can build one from the lowpass you already have. It gives a detector that responds to *change* while blind to *level* — and Chapter 9.3's coupling result, `V₂ = M × (di₁/dt)`, is a highpass in closed form. A coupled mind responds to the rate a conviction is moving, not to how deeply it is held, which is why the convert transmits and the thirty-year holder does not.

**What a highpass kills is your sense of level.** Monitor only through one and every change registers while nothing says whether the current state is acceptable. Hard rule: **never place a highpass on the O→P feedback path.** It passes precisely the spike the lowpass was installed to destroy, while looking in the listing like a filter.

**Notch.** Rejects a narrow band centred on `f0`, passing everything above and below. `Q = f0 / bandwidth`, so higher Q is narrower.

```cas
filter nf: Notch< in=audit, f0=0.35, Q=4.0 >;   // events/min — in-session only
```

Worked: bandwidth = 0.35 / 4 = 0.0875 events/min, so the rejected band runs 0.306 to 0.394 events/min — recurrences spaced roughly 2.5 to 3.3 minutes apart. Everything slower and faster passes untouched. This is the component behind Chapter 17.5's self-hypnosis variant and 17.6's indirect suggestion as filter bypass: it suppresses a `^6` Male self-audit *at the rate at which it interrupts a session*, without removing `^6` from the repertoire at any other rate. That distinction is the entire safety case for the part.

> **Bench Note — Q is a safety parameter, and there are places a notch may not go.**
> **Design floor: Q ≥ 3.0.** At Q = 0.5 the rejected band around `f0 = 0.35` runs from 0 to 0.7 events/min — not a notch, but most of the operator's `^6` decomposition removed under a label reading "narrow." Second, non-negotiable: **never notch a `^3^P` guard.** Redundant principled aversion is written `^3^P|A + ^3^P|f + ^3^P|T`, or `^3^P|⟨A,f,T⟩` when no interaction is claimed, because those are separately-defeasible guards rather than one fused state — a notch taking out one register leaves the others standing, which is the only reason the `+` form is worth its cost. A notch aimed at the whole guard set is a consent architecture with its own refusal removed; Chapter 16.6 analyses it so you can detect it. Third: a notch is for *in-session* suppression on a consenting, self-directed board. Anything you want gone permanently is a fuse — prohibited on `^6`.

[[FIGURE 11-D: Three response curves on one log-frequency axis (slow trends left, fast transients right), amplitude 0 to 1. Lowpass rolling off above 1/τ, 21-day corner marked, 4.6% / 63.2% / 95.0% annotated; highpass as its mirror image, marked "blind to level by design"; notch as a narrow well at f0 = 0.35 with the Q = 4.0 bandwidth of 0.0875 dimensioned, plus a ghosted wide well for Q = 0.5 marked "not a notch".]]

---

### 11.4 Op-Amps — Differential Cognitive Amplification

An operational amplifier has two inputs and one output, and amplifies only the *difference* between them.

```
V_out = A_d × (V₊ − V₋) + A_cm × (V₊ + V₋) / 2
```

The first term is what you want. The second is the leak, and the figure of merit is **CMRR** — `A_d / A_cm` — how much better the part amplifies the difference than whatever the two inputs share.

```cas
opamp cmp: OpAmp< non_inverting=recoil, inverting=draw, output=verdict,
                  open_loop_gain=1000.0 >;
```

The cognitive content is one sentence: **a comparison is only trustworthy if the two things compared are biased identically.** Wire `^2` Positive — the Idea the Mind has an affinity for and is attracted toward — to one input and `^3` Negative — the Idea the Mind is adverse to and repelled by — to the other, give both the *same* `^5^P` accumulated formation as bias, and the output is the divergence between drawn-toward and repelled-by. `^2` and `^3` are an involution pair, which is what makes them a differential pair rather than two arbitrary probes.

Matching is stricter than it looks. The two input literals must differ in **the Noetic digit and nothing else** — same Domain, same Drive, same Register — because every axis they do not share is a difference the subtraction cannot distinguish from the finding. Compare `^2^P_{F7}|f` against `^3^P_{F7}|f` and the output is one quantity read from two sides. Compare `^2^E_{F4}|f` against `^3^P_{F7}|f` and you have subtracted an evaluative pull under one Drive from a principled recoil under another; the difference is large, stable, and about the wiring.

Say the honest difference on a proposal is **0.02**, and the framing around it — flattery, urgency, polish, verbosity — adds **3.0** to *both* inputs equally.

| CMRR | `A_d` | `A_cm` | Differential term | Common-mode term | The verdict is about |
|---|---|---|---|---|---|
| 1000 | 1000 | 1.0 | 20.0 | 3.0 | the proposal (7:1) |
| 100 | 1000 | 10 | 20.0 | 30.0 | roughly half framing |
| 10 | 1000 | 100 | 20.0 | 300.0 | the framing (1:15) |

Nothing about the proposal changed across those rows, and neither did the gain. Only the *matching* changed — and at CMRR = 10 the board reports a verdict fifteen parts presentation to one part substance, with a large number and full confidence.

> **Bench Note — high gain is not the safety property. Matched bias is.**
> Operators reach for `open_loop_gain` when a comparison feels weak, and it is the wrong knob: gain multiplies both terms together and cannot improve the ratio between them. What sets CMRR is whether the two inputs genuinely share one bias. Bias attraction against one `^5` substrate and aversion against another — different standards for two options, the ordinary human condition and not an exotic fault — and you have an **input offset**: the comparator reports a difference where there is none. It presents as a stable, invisible preference defended on the merits, because from inside the board an offset is indistinguishable from a finding.

**On `β=∞`.** The ideal comparator has unbounded open-loop gain, and the symbol names the intended behaviour — switch fully, immediately, no partial output — in one character. It is an idealisation, and the validator rejects non-finite input, correctly: a build must commit to a number. Above roughly 1000 the behaviour is indistinguishable from the limit, because the output clips at the drive rail long before the gain runs out. Write `β=∞` in an argument if you mean the limit; write `open_loop_gain=1000.0` in a listing. That clipping is a design fact in its own right: **a comparison can only report as much difference as the rail permits.**

[[FIGURE 11-E: Op-amp differential stage — triangle U1, ^3^P_{F7}|f recoil on the non-inverting input, ^2^P_{F7}|f draw on the inverting input, the two literals stacked so the reader sees only the Noetic digit differs; one ^5^P_{F7}|T bias node feeding BOTH input stages from a single highlighted net, callout "one constitution — this is the CMRR"; a +3.0 common-mode arrow into both inputs with a subtraction glyph showing it cancel; rail clip levels dashed.]]

---

### 11.5 Transformers — Impedance Matching Between Minds

A transformer adds no power. It trades voltage for current at a fixed ratio and hands the same power out the far side.

```
V₂ = V₁ / n        I₂ = I₁ × n        Z_reflected = Z_load × n²
```

That answers a question every operator eventually asks: *why does the same argument land on one audience and slide off another?* Not because one is smarter. Because a claim, like a source, has an **impedance** — a working point in volts and amps — and so does an audience; a mismatched source delivers a fraction of the power it has. Power into a load, with `r = Z_load / Z_source`, relative to the matched case:

```
efficiency = 4r / (1 + r)²
```

| `r` | Efficiency | What it looks like |
|---|---|---|
| 0.01 | 3.9% | A principled argument delivered unchanged to a lay audience |
| 0.32 / 3.16 | 73% | Acceptable mismatch, either direction |
| 1.00 | 100% | Matched |
| 100 | 3.9% | A popular framing delivered to a room of specialists |

**Design rule: keep `r` within a factor of about 3 either way** and you stay above 70%. Outside 10 you are below a third; outside 100, under four percent.

Work the match. A claim held at `^9^P_{F7}|T` — Principled domain, transcendent register, high potential and very few carriers — has `Z_source = 400 Ω_c`; a general audience path at `^9^E_{F4}|f` has `Z_load = 4 Ω_c`. Delivered raw, `r = 0.01` and **3.9%** arrives. The matching ratio is `n = √(Z_source / Z_load) = 10`. Insert a 10:1 step-down, `Z_reflected = 4 × 100 = 400 Ω_c` — matched — and delivery goes to 100%. **Twenty-five times the delivered power, with no change to the content of the claim.**

Two costs, both load-bearing.

**A transformer passes no DC.** It transmits only change, for the reason Chapter 9.3 gives: coupling is `V₂ = M × di₁/dt`. A steady, deeply-held claim at a constant level transfers *nothing*, however well matched. It requires the oscillator of Section 11.2 upstream.

**Step-down lowers the claim's voltage, and there is a floor.** Chapter 8.1 established a total forward drop of **ΣVf = 3.9** down the descent chain, below which no operational output appears. Take a claim at `V₁ = 60 V_c`: at `n = 10`, `V₂ = 6.0 V_c` and clears by 2.1; at `n = 15`, `V₂ = 4.0 V_c` and barely clears; at `n = 20`, `V₂ = 3.0 V_c` and the message **reaches everyone and moves no one**. `n_max = V₁ / ΣVf = 15.4`. That is the popularizer's dilemma exactly, and the fix is not more simplification — it is more `V₁`, or fewer junctions between the audience and the deed.

> **Bench Note — the primary may not sit below the secondary in the domain order.**
> `Transformer< primary=^9^P_{F7}|T, secondary=^9^E_{F4}|f, n=10.0 >` is a descent: Principled primary, Evaluative secondary, P ≻ C ≻ E ≻ O. Reverse it and you have written an ascent, invalid for the reason `^O × ^P` is invalid — a lower domain may not drive a higher one, and the bias-domain coherence pass rejects it. The seductive use of a transformer is the illegal one: matching an operational fact *up* into a principled commitment, the counterfeit ascent of Chapter 8.3 wearing a component symbol. The lawful version is Chapter 18.3's endorsement circuit.

[[FIGURE 11-F: Two panels. Left: efficiency curve 4r/(1+r)², r on a log axis 0.001 to 1000, peak at r = 1 marked 100%, ±factor-3 band shaded "≥70%", r = 0.01 and 100 marked 3.9%. Right: transformer T1, primary ^9^P_{F7}|T at 60 V_c and Z = 400 Ω_c, secondary ^9^E_{F4}|f at Z = 4 Ω_c, n = 10 dimensioned; a bar chart of V₂ at n = 10, 15, 20 with a dashed ΣVf = 3.9 line marked "no operational output below".]]

---

### The Bench Harness

All five parts on one board, so the test points have somewhere to attach.

```cas
board special_bench {                    // Ch. 11 — the five parts on one board
    input:  claim;
    output: carried;

    node substrate: ^5^P_{F7}|T;   // Female: accumulated formation, shared bias
    node cadence:   ^7^C_{F6}|A;   // Rhythm: presentation schedule
    node draw:      ^2^P_{F7}|f;   // Positive: drawn toward the claim
    node recoil:    ^3^P_{F7}|f;   // Negative: visceral aversion
                                   // matched pair — same domain, same drive, same register
    node audit:     ^6^C_{F6}|A;   // Male: decomposition
    node verdict:   ^9^E_{F6}|A;   // Below/Effect: comparison result
    node carried:   ^9^O_{F4}|E;   // Below/Effect: the claim as enacted
    node trend:     ^9^O_{F4}|E;   // same literal — a filter changes tau, not type

    osc    clock: Oscillator< signal=claim, source=cadence, period=7.0, duty=0.15,
                              sustain=90.0 >;
    opamp  cmp:   OpAmp< non_inverting=recoil, inverting=draw, output=verdict,
                         open_loop_gain=1000.0 >;
    filter nf:    Notch< in=audit, f0=0.35, Q=4.0 >;          // in-session only
    xfmr   match: Transformer< primary=^9^P_{F7}|T, secondary=^9^E_{F4}|f, n=10.0 >;
    filter lp:    LowPass< in=carried, out=trend, tau=21.0 >; // days
    fuse   cap:   Fuse< path=carried, threshold=0.90, action=permanent_block >;

    feedback trend -> substrate [β=0.05];

    probe tp1: clock;     probe tp2: verdict;
    probe tp3: trend;     probe tp4: cap;
}
```

The fuse here is a **runaway cap**, not a refusal enforcer: if the claim as enacted reaches 0.90, the path is cut permanently. `carried` is an unsaturated output node, so 0.90 is reachable and the part can do its job. An enforcement fuse of the Chapter 24.3 kind belongs in series with the enforcement path instead, so that tripping *delivers* the block — and its threshold must clear the ceiling of whatever node it sits on, which is the check §11.1 asked you to run.

---

### Component and Parameter Table

Every value is a **design choice** made in this book, not a measurement.

| Ref | Parameter | Design range | Failure at other values |
|---|---|---|---|
| **F1** | `threshold`, `action` | 0.85–0.95, default 0.90; `permanent_block` | 0.50: nuisance trips. Above the guarded `sat`: never trips. `warn`: no latch |
| **OSC1** | `period`, `duty`, `sustain` | `T ≤ τ_leak/3`; 0.10–0.25; ≥ 3 × τ_leak | `T ≥ τ_leak`: 63% ripple, no plateau. duty ≥0.6: a DC level. Short sustain: drains at budget stop |
| **FLT1** | lowpass `tau` | 21 days (adept) to 6 months (novice), floor 1 week | Hours: the filter is gone, and the ascent block with it |
| **FLT2/3** | highpass; notch `Q` | `x − lowpass(x)`, rate detection only; Q ≥ 3.0 | Highpass on the O→P path: passes the spike the lowpass killed. Q = 0.5: most of `^6` gone, labelled "narrow" |
| **U1** | CMRR, `open_loop_gain`, input match | ≥ 1000 on a guard path; gain 100–1000, finite; inputs identical on Domain, Drive and Register | CMRR 10: 15 parts framing to 1 substance. `β=∞` rejected; past ~1000 the rail clips first. Mismatched axes: a permanent offset read as a finding |
| **T1** | `n`, direction | `r` within ×3 of 1, `n ≤ V₁/3.9`; primary at or above secondary | `r = 0.01`: 3.9% delivered. Past `n_max`: nobody acts. Ascent: counterfeit promotion |

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Unreachable fuse** | `threshold` above the guarded path's ceiling | Never trips, on any input | Read `threshold` against `sat`; move it downstream or lower it |
| **Fuse in the wrong terminal** | On the refusal, not the enforcement path | It cuts the refusal — the board fails open while logging a success | Place it in series with what must stop, not with what detects |
| **Under-clocked oscillator** | `T ≥ τ_leak` | No plateau; the operator starts from zero each cycle | Drop `T` to `τ_leak / 3` before adding drive |
| **Rented rhythm** | `sustain` short, source never internal | Pattern collapses the week external clocking stops | Extend to ≥ 3 × τ_leak; run TP1 first |
| **Highpass on the feedback path** | Complement installed where the lowpass belonged | Constitution tracks single dramatic events | Restore the lowpass; the O→P path takes trends only |
| **Wide notch** | `Q` below 3.0 | Decomposition absent outside the band; the operator cannot say what they stopped checking | Raise Q, or remove it — a wide notch is not a narrow one with tolerance |
| **Input offset** | Op-amp inputs on different `^5` substrates, or input literals differing on any axis but the Noetic digit | A confident preference defended on the merits, impossible to source | One bias net to both inputs; match Domain, Drive and Register; verify at TP2 |
| **CMRR collapse** | Gain raised to "sharpen" a weak comparison | Larger output, worse discrimination | The wrong knob. Re-match the bias |
| **Over-matched claim** | `n` past `n_max`, or no modulation | Universal reach, zero operational output; or a perfect match transferring nothing | Raise `V₁`, shorten the descent chain, put the oscillator upstream |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `clock` | Period, duty, whether `source` is still external | `T ≤ τ_leak/3`, duty 0.10–0.25. The real reading is taken with the clock **stopped**: cadence continues = entrained, cadence stops = rented |
| **TP2** | `verdict` | Differential output, `recoil − draw` | Near zero on a neutral input. Non-zero there is an **input offset** — either the inputs are not on one bias net, or the two literals differ on an axis other than the Noetic digit |
| **TP3** | `trend` | What survived the 21-day lowpass | ≤ 5% of a 1-day disturbance; ≥ 95% of a 63-day one. A trend tracking yesterday means τ is set in hours |
| **TP4** | `cap` | Fuse state and headroom | Intact, `threshold` verifiably **below** the ceiling of `carried`. Never tripping is not proof it works |

Read them TP2, TP1, TP3, TP4 — the comparison first, since nothing it reports counts until it is honest, then the clock, the filter, the fuse's headroom.

---

### What This Chapter Established

- **A fuse is specified entirely by its failure**, and its threshold is meaningless without the guarded path's ceiling beside it. `threshold` above `sat` is a part guaranteed to do nothing, and nothing in the listing complains.
- **Saturation and a fuse are two different locks.** Saturation latches the decision and releases when the cause falls; the fuse latches the path and never releases.
- **An oscillator converts sustained drive into periodic drive**, and exists because `^5` leaks. `T ≤ τ_leak / 3` holds ripple under 30%; at `T ≥ τ_leak` no plateau forms. Duty is the "pattern" half of `^7` Rhythm's canonical definition, and at duty ≥ 0.6 you have a DC level, with `^4` Vibration falling because impression requires contrast.
- **The objective is to make the oscillator unnecessary.** Run `sustain ≥ 3 × τ_leak`, then stop the clock — the test separating an entrained pattern from a rented one.
- **Every filter is defined by what it destroys.** A lowpass kills the spike *and* delays a genuine change by 3τ; a highpass kills your sense of level; a notch kills one recurrence rate and must never be aimed at a `^3^P` guard, at any Q.
- **Gain cannot fix a comparison — matched bias can**, and matching means the two input literals differ in the Noetic digit and nothing else. At CMRR = 10 a board reports a verdict fifteen parts framing to one part substance, confidently and with a large number.
- **A transformer changes nothing about an argument and everything about who can carry it.** Matching takes delivery from 3.9% to 100% at no cost to content — but it passes no DC, and step-down past `n_max = V₁ / ΣVf` produces a message everyone receives and no one can act on.

---

### Exercises

*(Answers in Appendix H.)*

**11.1** A board guards a path whose CJT is `[β=2.0, sat=0.78]` with `Fuse< path=that_node, threshold=0.90, action=permanent_block >`. State what this fuse does across every input, then give two corrections — one changing the fuse, one changing where it sits — and say which you would ship.

**11.2** A `^5` substrate has `τ_leak = 45 days`; each exposure deposits `q = 0.6`. Compute `Q_max`, `Q_min` and ripple for `T = 7`, `15` and `45 days`. Say which satisfies the design rule, and what the operator reports at `T = 45`.

**11.3** An operator wants to detect that their own principled commitments are *moving*, while staying indifferent to where they sit. Name the filter, write it in terms of the lowpass they already have, then name the one place on the board where installing it would be a serious defect — and what it would let through.

**11.4** A comparison stage runs `open_loop_gain = 1000` with `A_cm = 50`. The honest differential is 0.05; framing adds 4.0 to both inputs. Compute both output terms and their ratio, then what happens if the operator raises the gain to 4000, and why that was the wrong knob.

**11.5** A claim is held at `V₁ = 48 V_c` with `Z_source = 900 Ω_c`; the audience path has `Z_load = 9 Ω_c`. Compute (a) `r` and the efficiency with no transformer; (b) the matching `n`, confirming `Z_reflected`; (c) `V₂` at that `n` against `ΣVf = 3.9`; (d) `n_max` and the headroom left.

**11.6 (Marquee)** A campaign has run six months on a weekly cadence against a substrate with `τ_leak = 30 days`, and the plateau has stopped rising. The operator proposes doubling the budget: same period, `duty` raised from 0.15 to 0.70.

a) Compute `Q_max` and ripple at `q = 0.8`, and say why the plateau stopped rising.
b) Explain, in terms of `^4` Vibration and the canonical `^7` Rhythm definition, what raising duty to 0.70 will do.
c) Describe the TP1 stop-the-clock check, both outcomes, and what each means for the budget.
d) Write a CCDL fragment for the corrected oscillator plus a fuse capping runaway on the enacted path. State the ceiling you assume and why your threshold clears it.
