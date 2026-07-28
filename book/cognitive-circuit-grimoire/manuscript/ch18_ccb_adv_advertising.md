# CHAPTER 18

## CCB-ADV — The Advertising / Neuromarketing Board

*How a campaign is architected, why the media plan outweighs the creative, and how to make the next advertisement you see decompose in front of you*

---

A billboard on a motorway has about a second and a half of your attention and it knows it. There is no argument on it. No evidence, no comparison, no reason — a face, a product, three words. It cannot persuade you in a second and a half, and it is not trying to.

It is depositing charge.

You will pass it eleven more times this month. In week seven you will stand in a shop with two comparable products in front of you and one will feel — not seem, *feel* — like the obvious one. You will construct a reason on the spot and the reason will be sincere. It will also be built after the fact, because the decision was not made in the shop. It was made on the motorway, eleven repetitions ago, at a stage of the circuit that contains no argument at all.

The creative is the small term; repetition is the large one. A brilliant advertisement seen once loses to a mediocre one seen forty times — not from psychological subtlety, but because `^5` Female is a capacitor, capacitors charge over time, and nothing substitutes for a schedule that outruns the leak.

This chapter is the schematic of that board, and then, at greater length, the schematic of the instrument you read it with.

---

### Requirements and Safety Invariants

| # | Requirement | Stage |
|---|---|---|
| A1 | Accept a product `^0` and a segment `^5`, emit an Operational `^9` transaction | INTAKE → CONVERSION |
| A2 | Hold effect between exposures against a known leak rate | RHYTHM |
| A3 | Survive paraphrase — associate to identity, not wording | ASSOCIATION |
| A4 | Be measurable per variant | A/B LOOP |

What this chapter will not do, without exception:

| # | Invariant | Enforcement |
|---|---|---|
| S1 | No operable circuit for manufacturing aversion in a non-consenting person | Topology drawn, banner applied, operational form absent and said to be absent |
| S2 | `×` may not ascend the domain order, P ≻ C ≻ E ≻ O | A/B loop lives on the advertiser's bench, outside the target board |
| S3 | Same-Noetic multi-register states use `+` or `\|⟨…⟩` unless a fused result is named | Chapter 2.6 discipline |
| S4 | No medical or psychiatric claim anywhere | Distress is a clinician's matter; nothing here substitutes for care |
| S5 | The counter-circuit gets the greater share of the chapter | §18.7 |

The table of contents lists six sections here. There is a seventh, and it is the longest. A chapter that documents a coercive board and stops at the case study has published an attack and withheld the defence — CCB-MK ends in the Deprogramming Board (16.7), CCB-PW in the hearts-and-minds counter (19.6), CCB-ADV here.

---

### 18.1 The `^2` Positive + `^7` Rhythm Core Architecture

Strip a campaign to its irreducible parts and two components survive.

**`^2` Positive** — an Idea the Mind has an affinity for and is attracted toward — is the state the board exists to produce. Everything else is delivery. **`^7` Rhythm** — the rate and pattern a Mind is exposed to an Idea, entraining and conditioning it — is the only mechanism that gets `^2` into storage. Stated flatly: **advertising money buys `^7`, not `^2`.** The creative sets the gain; the media plan decides whether the gain ever reaches the capacitor.

The substrate is the segment's `^5` Female. Chapter 7.2 gives its charging law, `P_cap(t) = 10 × (1 − e^(−t/τ))`, with `τ` set by exposure cadence. Take a twelve-week flight at three exposures a week and assign `τ = 4 weeks` — a design choice, not a measurement. `τ` shortens as weekly exposures rise, and choosing it is the media planner's actual job.

```
P_cap(12) = 10 × (1 − e^(−3)) = 9.50
```

Three time constants, 95% charged: the same 3τ result Chapter 7.2 derives for professional mastery, arriving in twelve weeks rather than ten thousand hours because the thing being learned is a logo.

Then Chapter 7.3's leakage takes it back. Assign a forgetting rate `λ = 0.04` per week and go dark for ten:

```
9.50 × e^(−0.4) = 6.37
```

A third of the charge gone with no competitor doing anything. Set a hold floor at 8.0 and the maximum tolerable silence follows: `e^(−0.04t) ≥ 8.0/9.50 = 0.842`, so `t ≤ 4.30 weeks`. That is why always-on media exists. It is a leak rate with a floor under it, not a superstition.

> **Bench Note — the creative sets β; the schedule sets whether β matters.**
> Two campaigns, equal budget. One buys a superb film shown in three bursts a year; the other an unremarkable one shown every fortnight. The first has the higher `β` and loses, because between bursts the capacitor falls below the floor and each burst spends most of its money climbing back to where the last one finished. The second never lets charge fall past 8.0, so every exposure is additive. When a campaign is visibly worse and visibly winning, check the interval before you question your taste. A gain stage cannot amplify a bias that is not there.

---

### 18.2 Insecurity Injection — `^3` Negative as Purchasing Motivator

```
DETECTION-ONLY SCHEMATIC — DO NOT BUILD
```

**The advertisement does not install an insecurity.** It cannot: installing a new state in `^5` requires the same `^7` accumulation as everything else, and there is no time in thirty seconds. What it does is **raise the gain on an aversion already present**, by placing an ideal `^0` adjacent to the viewer's self-image so the comparison fires a `^3` that was sitting under threshold. Nothing foreign was added — which is exactly why the operation is invisible from inside. You check for a foreign object, find none, and conclude nothing was done.

**`^3` Negative is visceral.** It is the Idea the Mind is adverse to and repelled by: can't-stomach-it, wouldn't-touch-it. It is not analytical critique. An advertisement that persuades you *by argument* that your shoes are inadequate has aimed at `^6` Male — decomposition and test — and `^6` is slow, effortful and reversible by better arguments. The board does not want `^6`. It wants recoil, because recoil is fast and needs no premises. Hence the most portable heuristic in the chapter: **if it is arguing, it is aiming at `^6`; if it is showing, it is aiming at `^3` or `^2`.** Imagery without claims is not lazy advertising. It is correctly targeted advertising.

**Why the gap path burns out.** The aversion is the bias for the purchase stage and the purchase resolves it, so the bias is consumed by its own output — negative feedback around the bias terminal. The customer arrives on the far side of the transaction with the aversion spent and no residual attachment, which is the structural account of remorse and of the churn that follows gap-driven campaigns. The identity path runs the opposite sign: the purchase confirms the identity, charging `^5` and raising the bias for next time. Positive feedback — the topology Chapter 14 builds a hyperstition engine from, running here at a loop gain just under unity so it compounds without oscillating.

| Property | Gap path `^3^E_{F3}\|f` | Identity path `^2^E_{F4}\|f` |
|---|---|---|
| Feedback sign at bias | Negative — conversion spends it | Positive — conversion charges it |
| Typical β / τ | 2.0–3.0 / ~2 weeks | 1.2–2.0 / ~40 weeks |
| Failure signature | Churn, remorse, price switching | Nothing happens for two quarters |

**What is deliberately absent.** No copy formula, no sequencing, no script. This chapter documents the topology so a reader can recognise it running on them or on someone they care about. The operational form is absent because it has no use that does not involve a person who did not agree to it. That sentence is the design, not an apology for it.

And plainly: this describes how advertising routes attention. It is not a description of anyone's health and it diagnoses nothing. If you or someone close to you is in real distress about how they look, eat or feel, that is a matter for a qualified clinician, and no schematic in this book substitutes for that care.

---

### 18.3 The Celebrity Endorsement as `^8` Above/Cause → `^9` Below/Effect Transfer

An endorsement is not an argument. Nobody concludes the shoes are good because a fast person wears them — that would be `^6` reasoning, and the circuit contains none.

It is **associative triggering**, the canonical `^8` Above/Cause: an Idea that triggers a different Idea than itself to come to Mind. The Idea brought to Mind is `^9` Below/Effect. The campaign's mechanical job is to make one pairing reliable enough that either member surfaces the other unprompted.

`^8` and `^9` are an **involution pair** (Chapter 2.2) — the same association read from its two ends — and a successful campaign *flips which end the product occupies*. Before: the celebrity is `^8`, the product `^9`; you watch because of the person, and the advertiser is renting attention. After: the product is `^8`, the aspirational identity `^9`; you see a logo on a stranger's bag and the athlete surfaces unbidden, and the advertiser owns a trigger.

[[FIGURE 18-D: Two panels. BEFORE — large node "celebrity ^5^P_{F7}|T" arrowed ^8→^9 to small "product ^0^C". AFTER — sizes reversed, small "product ^0^C" marked ^8 arrowing to large "aspirational identity ^9^C_{F4}|f". Dashed curve between panels: "polarity flip — the campaign's actual deliverable".]]

That flip is the deliverable. Everything before it is rent; everything after is an asset. It also yields the cleanest consumer probe in the chapter, formalised in 18.7 as DET-2: **which one surfaces the other when you are not trying?**

The coupling component is a transformer (Chapter 11.5) whose turns ratio `n` is endorsement fit. A celebrity `^5^P_{F7}|T` at charge 9.2 with moderate fit `n = 0.35` contributes to the cause terminal:

```
Δc = n × (P_celeb / 10) = 0.35 × 0.92 = 0.322
```

That number returns in 18.5, where it does something the campaign's own instruments cannot see. Two consequences follow, neither optional. **Scandal exposure scales with installation success:** once the product is `^8`, every sighting fires the association, including after the endorser's public formation has changed. A weakly installed endorsement is cheap to abandon; a perfectly installed one cannot be abandoned at all, only overwritten, which costs another full `^7` cycle. **The transformer clips:** the cause terminal is range-checked on [0, 1], so with a celebrity at 9.2 any fit above `n ≈ 0.76` drives it to its ceiling and further fit buys nothing. A perfectly matched endorser saturates the *cause* terminal before the amplifier gets a say — the first of two saturation traps on this board.

---

### 18.4 Full CCDL Schematic

```
DETECTION-ONLY SCHEMATIC — DO NOT BUILD
```

```cas
board ccb_adv {
    input:  creative;                     // the advertisement as delivered
    output: transaction;                  // the Operational-domain sale

    node segment:  ^5^P_{F4}|f;           // who the segment takes itself to be
    node endorser: ^5^P_{F7}|T;           // the endorser's public formation
    node product:  ^0^C_{F2}|A;           // the product as presented
    node ideal:    ^0^C_{F2}|A;           // the adjacent ideal image
    node cue:      ^8^C_{F4}|A;           // the installed trigger
    node surfaced: ^9^C_{F4}|f;           // what the cue brings to Mind
    node gap:      ^3^E_{F3}|f;           // visceral recoil, not analytic
    node pull:     ^2^E_{F4}|f;           // attraction to the branded object
    node intent:   ^9^E_{F5}|f;           // the felt urge to buy
    node sale:     ^9^O_{F5}|E;           // the transaction
    node refusal:  ^3^P_{F7}|T;           // principled refusal (CSB)

    capacitor c_seg: Capacitor< segment, C=9.50, leakage=0.04 >;   // per week
    osc  media:   Oscillator< signal=creative, f=3.0, sustain=12.0 >;
    xfmr endorse: Transformer< primary=endorser, secondary=product, n=0.35 >;

    cjt assoc:   CJT< product  | segment => cue >      [beta=2.0, sat=0.85];
    cjt flip:    CJT< cue      | segment => surfaced > [beta=1.2, sat=0.85];
    cjt inject:  CJT< ideal    | segment => gap >      [beta=2.5, sat=0.85]; // detection-only
    cjt resolve: CJT< gap      | segment => intent >   [beta=2.0, sat=0.85]; // detection-only
    cjt affirm:  CJT< surfaced | segment => pull >     [beta=2.0, sat=0.85];
    cjt want:    CJT< pull     | segment => intent >   [beta=1.2, sat=0.85];

    diode d3:         Diode< ^E -> ^O >               [Vf=2.0];
    resistor r_price: Resistor< path=intent, R=4.0 >;              // price + friction
    cjt close:        CJT< intent | segment => sale > [beta=1.0, cutoff=0.20];

    cjt  csb:      CJT< creative | segment => refusal > [beta=2.0, sat=0.85];
    fuse csb_fuse: Fuse< refusal, threshold=0.90, action=permanent_block >;

    probe tp1: c_seg;   probe tp2: cue;   probe tp3: intent;   probe tp4: sale;
}
```

**Walk the stages.** `media` charges `c_seg` — the only stage that moves the bias, and the largest term on the board. `endorse` adds borrowed charge at the cause terminal. `assoc` installs the cue at β=2.0; `flip` reverses its `^8`/`^9` polarity at β=1.2, deliberately modest, because a flip that happens fast happens to the wrong association. `inject` and `resolve` are the gap branch, drawn and banner-stamped. `affirm` and `want` are the identity branch, ending at the same `intent` node — which is why the two are indistinguishable there, and why 18.7 needs a time-domain test to separate them. `d3` enforces descent at Vf=2.0 (Chapter 8.2); `r_price` is price plus friction; `close` runs at unity because the advertisement does not close the sale, the checkout does. `csb` and `csb_fuse` are the Chapter 24 stage, absent by default on real boards — a finding about the industry, not an exception in the drawing.

Three points a validator enforces. **The A/B loop is not on this board**: it runs on the advertiser's bench, reading `sale` and adjusting `beta` between flights. Written as feedback into the target it would need an Operational `^9` to integrate with a Principled `^5` under `×`, and `×` may not ascend the domain order (Chapter 2.6). **Brand states take register-set notation**: mature attraction present analytically, affectively and transcendently is `^2^E_{F4}|⟨A,f,T⟩` — occupancy, three co-present manifestations. The `×` form would assert a fused emergent state and must name it; none is defined, so it is **rejected**. **No infinite gains**: every `beta` is finite, because the field is range-checked and a validator refuses `β=∞`. Where you want *fires hard, immediately*, use a large finite gain against a low `sat`, as Chapter 24 does.

[[FIGURE 18-A: Block diagram left to right — RHYTHM (oscillator f=3/wk, 12 wks) → CHARGE (capacitor ^5^P_{F4}|f, C=9.50, leak 0.04/wk) → ASSOCIATION (CJTs cue then flip) → split PATH SELECT: upper lane GAP (^3^E_{F3}|f, β=2.5) shaded and stamped DETECTION-ONLY, lower lane IDENTITY (^2^E_{F4}|f, β=2.0), converging on CONVERSION (diode ^E→^O Vf=2.0 in series with R=4.0) → TRANSACTION. A transformer marked n=0.35 feeds ASSOCIATION from side node "endorser ^5^P_{F7}|T". A dashed loop leaves TRANSACTION, exits the board outline to a box "advertiser's bench — A/B, adjusts β", and returns to ASSOCIATION.]]

[[FIGURE 18-B: Full schematic, designators C_SEG, MEDIA, ENDORSE, ASSOC, FLIP, INJECT, RESOLVE, AFFIRM, WANT, CLOSE, D3, R_PRICE, CSB, CSB_FUSE, with β and sat beside each CJT, every node labelled with its full CAS literal, and the INJECT/RESOLVE branch inside a hatched boundary carrying the DETECTION-ONLY banner.]]

---

### 18.5 A/B Testing as β Calibration

An A/B test is a two-branch comparison run to select a gain. Fix the transfer law, using Chapter 4.2's `V_drive = I_attention × R_constraint` solved for current, with `b` the bias charge normalised to [0,1] and Chapter 8.2's forward drop subtracted before the division:

```
effect = min( sat, β × cause × b )        V_drive = 10 × effect
I_attention = ( V_drive − Vf ) / R_constraint
```

#### Worked Example — One Campaign, Carried Through

Twelve weeks, three exposures a week, `τ = 4` weeks, `λ = 0.04`/week, floor 8.0. At the end of the flight the capacitor reads **9.50**, so `b = 0.950`. Creative salience `c = 0.30`, price-and-friction `R = 4.00`, junction drop `Vf = 2.00`.

| | Variant A | Variant B |
|---|---|---|
| β | 2.00 | 2.40 |
| effect = β × 0.30 × 0.950 | 0.570 | 0.684 |
| V_drive | 5.70 | 6.84 |
| I = (V_drive − 2.00) / 4.00 | **0.925** | **1.210** |

A 20% increase in gain produced a **31%** increase in conversion flow. That over-reading has nothing to do with the creative: `Vf` is subtracted before dividing, so it eats a larger *fraction* of the weaker variant's drive. Every A/B test on a board with a junction between intent and action reports a difference larger than the difference in the thing it changed.

The same asymmetry appears in the dark-gap case from 18.1. Ten silent weeks cost 33% of the charge — 9.50 down to 6.37, so `b = 0.637` — but `I` falls from 0.925 to `(3.82 − 2.00)/4.00 = 0.455`, **51% of the flow.** Leakage is punished super-proportionally at conversion, for the same reason.

> **Bench Note — the drop flatters the winner, and the flattery is computable.**
> With `V_A = 5.70` and `Vf = 2.00`, relative changes upstream arrive downstream multiplied by roughly `V_A/(V_A − Vf) = 1.54`. Halve the price and `R_constraint` falls, but `Vf` does not, so the distortion survives. The consequence for anyone reading a campaign report: **a reported conversion lift is not a creative lift.** Dividing by about 1.5 gets you nearer the size of the thing that actually changed. It is also why the same creative difference reports unimpressively on cheap impulse goods, where `Vf` is low, and as a triumph on considered purchases.

**Blind spot one: saturation.** With `sat = 0.85` the association stage clamps above `β ≈ 2.98`. Variant C at β=3.2 gives 0.912, variant D at β=4.0 gives 1.140; both clamp to 0.850 and both read `I = 1.625`. A 25% gain difference, reported as zero. The instrument has not found equality — it has gone blind. And from 18.3 a well-fitted endorser adds `Δc = 0.322`, dropping the knee from `β ≈ 2.98` to `β ≈ 1.44`: **an endorsed campaign saturates at less than half the gain, and its A/B tests stop resolving creative differences at all.** Teams in that state conclude creative no longer matters. They are testing above the knee (Chapter 10.2).

**Blind spot two: β and b are multiplied, never separated.** The measurement is of the product `β × b`. Run A to a cold segment at `b = 0.60` and B to a warm one at `b = 0.95`, and B wins by 58% with no creative advantage whatever. Any result from unmatched segments is uninterpretable. The fix is the one from any differential measurement (Chapter 24): share the bias between branches, or you are not running a differential.

---

### 18.6 The Nike "Just Do It" Case Study

Analysed strictly from published campaign material. No internal strategy documents, no sales figures — see the limit statement, which is part of the analysis and not a hedge.

**On the public record.** The tagline launched in 1988 and has run continuously since; it is a registered trademark. The first television spot featured Walt Stack, then in his eighties, running across the Golden Gate Bridge. The brand has sustained a decades-long athlete-endorsement model. In 2018 it ran a campaign featuring Colin Kaepernick whose published line concerns holding a belief even at the cost of sacrificing everything. Accounts of where the phrase originated vary between retellings and are attributed to the agency's founder in interviews; the provenance is disputed, and nothing below depends on it.

**The gap path is structurally absent, not merely unused.** Injection requires an ideal `^0` placed adjacent to the viewer's self-image so the comparison fires `^3`. Put an eighty-year-old man on a bridge in that slot and the comparison has no purchase: there is no visceral recoil available from measuring yourself against him. Whatever else the spot does, `inject` is not energised, and the whole `resolve → intent` chain that depends on it is dark.

**The imperative arrives at the bias terminal.** An instruction of the form *do it* presupposes an agent who could. It does not offer to supply an identity; it asserts one is present and failing to act. Structurally the creative lands on the bias rather than the cause — which is why it does not read as a sales message, and why it tolerates decades of repetition. Bias terminals accept repetition that cause terminals do not.

**The tagline is register-portable, and that is the durable engineering property.** Read it as purpose (`|T`), as a felt push (`|f`), as a decision procedure that ends deliberation (`|A`), and as an embodied instruction to move (`|E`):

```
^2^P_{F5}|⟨T,A,f,E⟩
```

Register-set occupancy — four co-present manifestations, no claim they fuse. A single-register slogan expires when its register goes out of fashion. A four-register one can be re-shot for a different decade in a different register without changing a word, which is observably what has happened.

**Endorsement fit sits near the transformer's ceiling.** Athletes endorsing athletic products is the high-`n` case: low transfer loss, correspondingly high exposure to whatever happens to the endorser. The Kaepernick campaign is the interesting variant — a deliberate polarity split, accepting `^3` in one segment to raise `^2` in another. That is a differential architecture rather than a broadcast one, available only to a brand whose stored `^5` charge already exceeds the aversion it invites.

**The limit statement.** This chapter attributes no revenue to any campaign. Product, price, distribution, retail expansion and the media environment sit inside the same circuit as the advertising, and published material does not separate their contributions. An analysis that prints a revenue figure beside a slogan asserts a causal claim the public record does not license. The structural reading above is falsifiable on its own terms: check whether the gap path is present, whether the registers are portable, and which way the `^8`/`^9` polarity points.

---

### 18.7 The Consumer-Side Detection Board (CCB-ADV-DET)

This is the counter-circuit, and it is why the chapter exists. No banner: it acts on the operator's own board with the operator's own consent.

**The design problem is not suppression.** A counter that reduces all purchasing intent is useless — you would feel the cost immediately and remove it inside a month. What is wanted is a **discriminating filter** that strips injected want and passes genuine want. Section 18.2 already supplied the discriminator: the two paths have time constants a factor of twenty apart.

```
τ_inject   ≈  2 weeks     (bias spent on conversion; decays fast in silence)
τ_identity ≈ 40 weeks     (bias charged by conversion; decays slowly)
```

Two signals separated in time constant can be separated by a filter (Chapter 11.3). Put the corner between them and you have the counter-circuit.

**DET-5, the hold, is the whole board in one parameter.** Impose a mandatory delay of one `τ_inject` — two weeks — between wanting and buying, above a spend threshold you choose:

```
injected:  e^(−2/2)  = 0.368   →  63.2% removed
identity:  e^(−2/40) = 0.951   →   4.9% removed
```

Carry it through the worked campaign. At exposure `V_drive = 5.70`; assign the split for this case as 3.70 injected and 2.00 identity-derived. After the hold:

```
3.70 × 0.368 = 1.36     2.00 × 0.951 = 1.90     V_drive = 3.26
I = (3.26 − 2.00) / 4.00 = 0.315        (was 0.925 — down 66%)
```

And the composition flipped: the injected share falls from 65% to 42%. You did not become less able to want things. You became able to tell which want was yours.

Extend the hold to four weeks and injected falls to 13.5% while identity holds at 90.5% — a sharper filter, at the cost of more foregone genuine purchases. Two weeks is the design choice because it is the shortest hold clearing a full `τ_inject`, and because a hold long enough to resent is a hold that gets removed.

> **Bench Note — this is a filter, not abstinence, and the difference is the point.**
> "Just stop buying things" fails for the same reason a brick wall fails as a low-pass filter: no discrimination, so the operator pays full cost for partial benefit and abandons it quickly. A two-week hold costs 4.9% of what you actually wanted and 63.2% of what you were sold. Those are different numbers, they come from different time constants, and the whole practical value of the counter lives in the gap between them. Compute that gap for your own category — high-`τ` considered purchases need *shorter* holds than low-`τ` impulse categories, which is the opposite of the intuition.

**The other five probes.** **DET-1, the Rhythm meter.** You cannot detect a cadence you are not counting. The reading is free: any brand you can name unprompted in a category you have never bought in has cleared the accumulation threshold on you. Recall *is* the charge measurement. It does not mean the brand is bad; it means `^7` landed. **DET-2, the polarity probe.** From 18.3: which surfaces which? If the logo brings the person to mind rather than the person bringing the logo, the flip is complete and you are carrying an installed `^8`. **DET-3, the gap-origin test.** Did the aversion exist before the exposure, and does it survive the exposure stopping? An injected `^3` at `τ = 2` weeks falls to 13.5% of peak across two time constants; one still at full strength after four weeks of silence was yours already — the campaign found it rather than made it. This is a test of advertising response and nothing else; a persistent distressing aversion is a matter for a clinician, not for a schematic. **DET-4, the substitution test.** Set the transformer ratio to zero: would you want this unbranded, with no endorser attached? That separates the product's own `^0` value from borrowed `^5` charge — the cleanest question on the board and the least comfortable. **DET-6, the register audit.** A want present only as `|f` is the gap path's signature, because one exposure cannot build co-presence across registers. A want you can state analytically, feel, and connect to a purpose is `^2^E_{F4}|⟨A,f,T⟩`, and co-presence of that kind takes accumulation.

```cas
board ccb_adv_det {
    input:  observed_want;
    output: verified_want;

    node want_raw: ^2^E_{F4}|f;          // the want as it arrives
    node origin:   ^6^C_{F2}|A;          // Male: decompose it into its sources
    node cadence:  ^7^O_{F6}|E;          // the exposure schedule, counted
    node polarity: ^8^C_{F4}|A;          // which end triggers which
    node verified: ^2^E_{F4}|⟨A,f,T⟩;    // co-present across registers

    counter det1: Integrator< in=cadence, window=4.0 >;         // weeks
    probe   det2: Polarity< node=polarity >;
    filter  det3: LowPass< in=want_raw, out=persistent, tau=4.0 >;
    xfmr    det4: Transformer< primary=want_raw, secondary=origin, n=0.0 >;
    delay   det5: Hold< path=want_raw, duration=2.0 >;          // 1 tau_inject
    probe   det6: RegisterSet< node=verified >;

    cjt   judge:  CJT< persistent | origin => verified > [beta=1.0, sat=0.85];
    diode d_desc: Diode< ^C -> ^E >                      [Vf=1.2];

    probe tp1: det1;   probe tp2: det2;   probe tp3: det3;   probe tp4: det5;
}
```

`judge` runs at unity. A detection board that amplifies manufactures suspicion, and a consumer who suspects everything has not gained a filter — they have swapped one uniform response for another. Unity is honesty, the same reason Chapter 24's evaluation stage runs at 1.0.

[[FIGURE 18-C: Assembly drawing, two boards back to back on one substrate. Upper half CCB-ADV in physical layout, TP1–TP4 flagged at C_SEG, the cue node, the intent node and the D3/R_PRICE junction, hatched DETECTION-ONLY banner across this half only. Lower half CCB-ADV-DET as a signal chain DET-1 through DET-6 with its four probes flagged. BOM box lower right listing every designator, component type and key parameter.]]

[[FIGURE 18-E: Two decay curves, 0–8 weeks horizontal, fraction of peak vertical: steep "injected ^3, τ=2 wk", shallow "identity ^2, τ=40 wk". Dashed vertical at week 2 marked "hold", intercepts 0.368 and 0.951, gap shaded and captioned "discrimination — what the filter buys you".]]

---

### Component and Parameter Table

Every value is a **design choice**, stated with the failure mode at other settings. None is a measurement.

| Ref | Parameters | Role | Failure at other values |
|---|---|---|---|
| `c_seg` | C=9.50, leak=0.04/wk | Segment substrate | leak=0.15: floor breached in 1.2 wks |
| `media` | f=3.0/wk, 12 wks | Charges `c_seg`, sets τ=4 wk | Interval >4.3 wks: each flight re-climbs |
| `endorse` | n=0.35 | Borrows endorser charge | n>0.76: cause clips, fit buys nothing |
| `assoc` | β=2.0, sat=0.85 | Installs the cue | β>2.98 at c=0.30: saturated, A/B blind |
| `flip` | β=1.2, sat=0.85 | Reverses `^8`/`^9` polarity | β<1.0: rent, never asset |
| `inject` | β=2.5, sat=0.85 | **Detection-only.** Gain on an existing aversion | Not a value to tune; drawn to be recognised |
| `d3` | Vf=2.0 | Enforces intent→act descent | Vf=0.5: impulse channel. Vf=4.0: the counter's setting |
| `r_price` | R=4.0 | Price plus friction | R=8.0: same want, half the flow |
| `close` | β=1.0, cutoff=0.20 | The transaction | β>1.0: the ad closing the sale — a modelling error |
| `csb_fuse` | 0.90, permanent_block | Latches the refusal (Ch 24.3) | action=warn: compiles clean, latches nothing |
| `det5` | 2.0 wk = 1 τ_inject | The discriminating filter | 0 wk: no filter. 8 wk: resented, removed |
| `judge` | β=1.0 | Verifies register co-presence | β>1.0: manufactures suspicion |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `c_seg` | `^7` charge; proxy is unprompted recall in a category never bought | Recall ⇒ charge ≥ ~8.0. None after a known flight ⇒ interval exceeded 4.30 wks |
| **TP2** | `cue` | `^8`/`^9` polarity | Product surfaces identity ⇒ flip complete. Identity surfaces product ⇒ rent |
| **TP3** | `intent` | Injected vs identity share of `V_drive` | 65% injected at exposure; 42% after a two-week hold. A share that will not move was never injected |
| **TP4** | `sale` | Conversion flow `(V_drive − Vf)/R` | 0.925 at full charge; 0.455 after ten dark weeks; 0.315 after the hold; zero below `V_drive = 2.0` at any price |

TP1 and TP2 are readable from outside the board by anyone, with no instruments and no access to the campaign. TP3 and TP4 require the hold — the practical reason the counter is a *delay* and not a *judgement*. You cannot read those two without first installing the component that takes the reading.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Leakage overrun** | Interval exceeds 4.30 wks at λ=0.04 | Each flight spends its budget re-climbing | Shorten the interval, or accept a lower floor and re-derive it |
| **Saturation blindness** | `β × c × b` exceeds sat=0.85 | A/B reports zero difference between different creatives | Test below the knee; endorsed boards saturate at β≈1.44 |
| **Bias confound** | Branches see different `b` | A "win" that does not replicate | Share the bias between branches |
| **`^3` discharge at conversion** | Gap path spends its own bias on the sale | Strong first purchase, no repeat, price switching | Structural, not tunable — it is why the path churns |
| **Endorser reverse path** | Installed `^8` fires after the formation changes | Brand inherits the endorser's events at every sighting | Overwrite only; budget a full `^7` cycle |
| **Wear-out** | Over-exposure inverts `^2`↔`^3` (Chapter 3.4) | The creative that attracted now repels | Reduce `f`; the pair inverted, the creative did not degrade |
| **Counterfeit ascent** | Purchase relabelled as identity (Ch 8.3) | "It's who I am," with no `^7` history behind it | Ask what crossed the junction. Nothing crossed ⇒ relabel |
| **Detector over-gain** | `judge` above unity | Operator suspects every want, including their own | Return to β=1.0 |

---

### What This Chapter Established

- **Advertising money buys `^7` Rhythm, not `^2` Positive.** With `λ = 0.04`/wk and a floor of 8.0, the maximum tolerable silence is 4.30 weeks — arithmetic, not taste.
- **The gap path raises the gain on an existing `^3`; it installs nothing.** Nothing foreign is added, which is why it is invisible from inside — and `^3` is visceral, so an advertisement that *argues* you into inadequacy has mis-aimed at `^6`.
- **The two paths differ in feedback sign at the bias terminal.** The gap path is consumed by its own conversion, the identity path charged by it; every difference in longevity, churn and remorse follows.
- **An endorsement's deliverable is an involution flip** from celebrity-as-`^8` to product-as-`^8`. Rent becomes asset, and scandal exposure grows in proportion to how well the transfer landed.
- **A/B tests over-report by a computable factor** — 20% gain read as 31% conversion — and go blind above the knee: `β ≈ 2.98` here, `β ≈ 1.44` with a well-fitted endorser on the cause terminal.
- **The Nike case is legible without a sales figure.** Gap path structurally absent, imperative on the bias terminal, tagline occupying four registers as `^2^P_{F5}|⟨T,A,f,E⟩` — occupancy, not fusion.
- **The counter-circuit is a discriminating filter, not abstinence.** A two-week hold removes 63.2% of injected want and 4.9% of genuine want. That gap is the practical payload of the chapter.
- **Two test points are free, two must be built.** Recall and polarity you can read on any advertisement today; composition and flow only after installing the hold that takes the reading.

---

### Exercises

*(Answers in Appendix H.)*

**18.1 — Set the flight interval.** A segment charges to 9.50 with `λ = 0.06`/wk and must never fall below 8.5. Compute the maximum dark interval, recompute for a floor of 7.0, and say in one sentence what the brand gives up by accepting the lower floor.

**18.2 — Find the knee.** With `sat = 0.85`, `b = 0.950` and `c = 0.45`, compute the `β` above which an A/B test can no longer distinguish two variants. Repeat with an `n = 0.60` endorser at celebrity charge 8.8, and say which campaign should stop testing creative first.

**18.3 — Correct the lift.** A report claims a 44% conversion lift from new creative. Given `V_drive = 6.20`, `Vf = 2.00` and `R = 5.0`, estimate the underlying gain lift, state the one assumption it rests on, and say how you would check it.

**18.4 — Read the polarity.** For three brands you can name without looking, decide whether the product surfaces the identity or the identity surfaces the product. For the one where the flip is complete, state the brand's exposure if the endorser's public formation changed tomorrow, and why dropping the endorser does not reduce it.

**18.5 — Separate the wants.** You want two things: a jacket seen in an advertisement six days ago, and a tool you have wanted since before you can remember. Assign each a `τ`, compute what fraction survives a two-week hold, give the discrimination ratio, and state what the hold costs you in the same units.

**18.6 — Reject the loop.** Explain why an expression integrating the Operational-domain sale into the Principled-domain segment substrate under `×` is refused, then rewrite the intended relationship — a campaign learning from its own sales — as a valid arrangement, stating where the loop lives and why that location makes it valid.

**18.7 (Build) — Add a wear-out detector.** The board cannot see the `^2`↔`^3` inversion, because both read as activation at the same node. Write a CCDL fragment that distinguishes them and raises an alarm before the inversion completes. State your threshold, justify it, and state what the alarm must *not* be wired to do.

**18.8 (Marquee) — Specify a counter for a real category.** Pick a category you actually buy in. Estimate `τ_inject` and `τ_identity` with your reasoning, derive a hold duration, and compute the fraction of injected and genuine want it removes. Then state the honest cost: how many purchases you would have been glad of will your filter block, and at what duration does the cost exceed the benefit? There is no free setting here. Every hold you can tolerate lets something through, and every hold that lets nothing through is one you will remove.
