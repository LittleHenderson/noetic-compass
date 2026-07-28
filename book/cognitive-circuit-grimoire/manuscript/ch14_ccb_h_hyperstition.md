# CHAPTER 14

## CCB-H — The Hyperstition Engine

*The one board built around a loop gain above unity — how a fiction recruits conduct, how conduct returns as fact, and the single measurement that separates a live hyperstition from a rented one*

---

Somebody writes a sentence that is not true. Four years later it is true, and nobody lied.

The sentence was *this is the street where the studios are.* At the time there were two studios and a laundromat. People who believed the sentence signed leases on it. Landlords who believed the people raised rents to match. A supplier moved in to serve the tenants who had moved in. There are ninety studios now, and the sentence is a plain description of the street.

No mystery channel opened. What ran was a loop: a claim produced an impression, the impression produced conduct, and the conduct produced a fact which fed back and charged the claim. The return path is the part worth staring at, because **it carried no fiction at all.** The leases were real. That is the whole engine, and it is why a hyperstition is not a lie.

The same loop, tuned slightly hotter with its audit stage starved, is how an operator ends up unable to say which parts they made up. The difference between the street and that is one measurement, taken at one test point, and it costs eight weeks of doing nothing to take it. Most of this chapter is about that measurement and why almost nobody makes it.

[[FIGURE 14-A: Block diagram of CCB-H — SEED → LOOP A (rehearsal) → PROPAGATE → MANIFEST left to right; R1 and diode D1 (^C→^E, Vf=1.2) ahead of the seed CJT Q1; a fast return path from Q1's effect through FLT1 (τ=90 d) and gain block FB1 (β=1.90) back to Q1's bias terminal, labelled "LOOP A — sets level"; transformer XF1 feeding collective capacitor C2 with the fusion node marked; diode D2 (^E→^O, Vf=2.0) into Q2; a second, wider return path from Q2's output through FLT2 (τ=90 d) and FB2 (β=0.30) to the same bias, labelled "LOOP B — sets growth, carries fact"; and, drawn entirely outside both loops, anchor capacitor C3 (leakage=0) feeding audit CJT Q3, whose output runs to the CSB guard Q4 and fuse F1.]]

---

### 14.1 Requirements and Safety Invariants

Requirements before components (Chapter 12.1). This board differs from every other in Part III in one structural respect, and the requirement list has to say so: **the operator is inside the loop.** On CCB-ADV (Chapter 18) the operator stands outside the circuit and drives it. Here the feedback path terminates on a bias the operator shares with the audience, so every safety invariant below protects the operator first and the population second.

| # | The board shall | Stage |
|---|---|---|
| H1 | Accept a fictional `^0` Idea and produce a measurable impression | SEED |
| H2 | Return that impression to the bias terminal at a stated, capped gain | LOOP A |
| H3 | Return *operational conduct* to the same bias through a filtered, low-gain path | LOOP B |
| H4 | Support collective formation — a parallel `^5` bank across many minds | PROPAGATE |
| H5 | Expose the **measured** round-trip gain, never the setting | TP4 |
| H6 | Hold a dated, non-leaking record of the claim's construction outside both loops | ANCHOR |

**Safety invariants — the "must not" list.** Checked before functional behaviour.

| # | Must not | Enforced by |
|---|---|---|
| S1 | Run with the round-trip gain assumed rather than measured | `constraint measured_loop_gain in [0.0, 2.0]`, read at TP4 |
| S2 | Let the `^6` audit fall inside the loop's shadow | Q3 biased by C3, which sits outside both feedback paths |
| S3 | Grow fast enough that the store clamps between two audits | Kill at measured `G ≥ 1.80`; derivation in 14.5 |
| S4 | Remove the operator's ability to state the construction date | C3 `leakage=0.0` — a written, dated record does not drift |
| S5 | Be undampable | Q_KILL `β=0` into the oscillator's source; OSC1 `sustain` bounded |
| S6 | Target a named individual | Out of scope — no wire from any stage to a person-specific bias |
| S7 | Run without a CSB stage | Q4 `sat=0.85`, F1 `threshold=0.90` (Chapter 24) |

**Scope.** S6 is the line this chapter does not cross, and it is a structural line rather than a squeamish one: a person-specific bias would have to be `^5` for one named mind, and there is no admissible path from any stage here to such a node. Mechanisms that do have that path are analysed for detection only, in Chapters 16 and 19. Consumer-side detection of the commercial case belongs to Chapter 18.6.

And the plain limit: this board describes belief formation, not health. If what is slipping is a person's grip on what they made up and what they found, that is not a parameter on any listing in this book. See a clinician. Nothing here replaces care.

---

### 14.2 The Positive Feedback Oscillator Architecture

Every other board in this book is built to be stable. Negative feedback subtracts from the input, so a disturbance shrinks each time round. CCB-H inverts the sign: the impression a claim makes this cycle is added to the bias that produces next cycle's impression. That is all a hyperstition is, mechanically.

Write the loop as a recursion on the belief store `s`, held on the normalised 0–1 scale (the fraction of the store's ceiling — Chapter 7.2's `P_cap` divided by ten):

```
  e_n   = min( β1·c + g_m·s_n , sat1 )            impression this cycle
  V_n   = β_FB·e_n + β_B·β_M·χ·e_n                drive the loop presents to the store
  s_n+1 = (1 − α)·s_n + α·V_n                     store charges toward that drive
  α     = 1 − e^(−T/τ_store)                      one cycle's charging fraction
```

`c` is the seed clarity at TP1, `g_m` the seed CJT's framing sensitivity (Chapter 10.3), `β_FB` the Loop A gain block, and `β_B·β_M·χ` the Loop B path — feedback gain, manifest gain, and the world's receptivity to the conduct.

Differentiate the last line and the stability condition falls out:

```
  A_L = ∂s_n+1/∂s_n = (1 − α) + α·G
  G   = g_m · ( β_FB + β_B·β_M·χ )                 the ROUND-TRIP GAIN
  A_L − 1 = α·(G − 1)
```

**The α cancels.** Growth depends on `G` alone; `α` — the cadence, the store's leak, the whole calendar — sets only *how fast*. Three regimes, and only three:

- **`G < 1` — damped.** The store settles at a finite level and stays there while you keep seeding. Remove the seed and it decays as `A_L^n`.
- **`G = 1` — sustaining.** An idealisation. It is a measure-zero point on a product of four estimated terms; no build sits on it, and a board reported to be there is a board that has not been measured.
- **`G > 1` — growing.** The store rises without further seed, doubling every `n₂ = ln 2 / ln(1 + α(G−1))` cycles.

> **Bench Note — you cannot post your way past `G < 1`.**
> The commonest operator response to a fiction that will not catch is to shorten the cycle: weekly becomes daily, daily becomes hourly. Read the algebra again. Shortening `T` raises `α`, and `α` multiplies `(G − 1)`. If `G − 1` is negative, a larger `α` makes the thing **settle faster and die faster** — it does not turn decay into growth. Cadence is a rate knob on a sign you already own. The only terms that change the sign are `g_m`, `β_FB`, `β_B`, and `χ`, and three of those four are properties of the audience and the world rather than settings on your board. This is also why over-cadence has the observable Chapter 11.2 predicts — falling `^4` Vibration per exposure, because impression requires contrast — while the loop gain sits exactly where it was.

**Loop B is the load-bearing one, and it carries no fiction.** Loop A returns the operator's own restatement of the claim. Loop B returns `^9_conduct^O` — what believers actually did — through a filter and back to the bias. Its input is a fact. Someone really did sign the lease. That is the precise sense in which a hyperstition differs from a lie: a lie requires the liar to hold a truth in reserve, whereas here the return path carries only true operational records whose *existence* the claim caused.

It also bounds what the board can deliver. **A hyperstition can only make true the class of claims that conduct can make true.** "This is where the studios are" is inside that class; conduct relocates studios. "Established 1887" is outside it, because no volume of present conduct reaches into 1887. A board pointed at a claim about the past has no Loop B at all, which means `G` reduces to `g_m·β_FB` — operator restatement, nothing else — and the whole thing collapses the moment the operator stops. What that operator built is not a hyperstition. It is a false factual claim with a marketing budget attached, and the appropriate authority is a regulator rather than a schematic.

**The fusion, and the one licensed `×`.** Chapter 7.5 left this claim to be made here. Twelve capacitors on a shared rail are written `+` — co-present stores, distinct, no interaction asserted. On this board, past crossover, a stronger claim becomes available:

```cas
integrate eg1: ( seeded × bank ) = egregore;
//   ^0_seeded^E_{F2}|A  ×  ^5_collective^E_{F4}|f  =  ^5_egregore^E_{F4}|⟨A,f⟩
```

The `×` is licensed on four counts (Chapter 2.6): two *different* Noetics, one domain on both operands, no ascent in the result, and a **named emergent result** declared as a node. What the name commits you to is not decoration. It asserts that the fused state biases downstream stages *by itself* — that Q2 fires on `egregore` with the seed disconnected. That is a falsifiable claim, and TP4 is the test that falsifies it. Before crossover you may not write the `×`; you must write `seeded + bank`, because the co-presence is all you have evidence for. **The operator's notation changes when the measurement changes, and not before.**

---

### 14.3 Full CCDL Schematic

Topology in angle brackets, parameters in square brackets. Every value is a design choice, justified in 14.5 and in the parameter table.

```cas
// CCB-H — HYPERSTITION ENGINE.  Every value is a design choice.
// Time base: the cycle T = 7 DAYS.  All capacitor and filter taus in DAYS.
// This board deliberately runs G >= 1 and therefore raises E-CJT-005 on
// validation pass 6 (Appendix B, B.6).  That is the point.  See below.

board ccb_h {
    input:  fiction;
    output: conduct;

    // ---- typed nodes ----
    node charter:   ^5_operator^P_{F7}|T;      // Female: the operator's formation — CSB bias
    node fiction:   ^0_fiction^C_{F2}|A;       // Idea: the claim as authored
    node seeded:    ^0_seeded^E_{F2}|A;        // Idea: the claim after intake and descent
    node belief:    ^5_belief^E_{F2}|f;        // Female: the store FOR THIS CLAIM
    node impress:   ^9_impress^E_{F2}|f;       // Below/Effect: one cycle's impression
    node rehearsed: ^9_rehearsed^E_{F2}|f;     // same literal — a filter changes tau, not type
    node shared:    ^9_shared^E_{F4}|f;        // Below/Effect: the impression as it lands in others
    node bank:      ^5_collective^E_{F4}|f;    // Female: the parallel bank (Ch 7.5)
    node egregore:  ^5_egregore^E_{F4}|⟨A,f⟩;  // Female: the NAMED emergent result
    node cadence:   ^7_cadence^E_{F6}|E;       // Rhythm: the clock
    node conduct:   ^9_conduct^O_{F5}|E;       // Below/Effect: what believers actually do
    node evidence:  ^9_evidence^O_{F5}|E;      // same literal as conduct, slower tau
    node record:    ^6_anchor^P_{F6}|A;        // Male: the dated construction record
    node audit:     ^6_audit^P_{F6}|A;         // Male: the claim decomposed against the record
    node guard:     ^3_guard^P_{F7}|⟨A,f,T⟩;   // Negative: three co-present locks
    node gain_meas: ^4_loopgain^E_{F2}|A;      // Vibration: the measured round trip, TP4

    // ---- STAGE 0: SEED AND DESCENT ----
    resistor r1: Resistor< path=fiction, R=20.0 >;    // low: nothing defends against a story
    diode    d1: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];

    // ---- STAGE 1: THE SEED CJT ----
    cjt q1: CJT< seeded | belief => impress >
            [beta=0.90, sat=0.80, cutoff=0.05, g_m=0.60, r_pi=1.50, region=active];

    // ---- LOOP A: rehearsal.  Operator-side.  Sets LEVEL, not growth ----
    capacitor c1:   Capacitor< node=belief, C=1.20, leak_tau=90.0, V_BR=8.0 >;
    filter    flt1: LowPass< in=impress, out=rehearsed, tau=90.0 >;  // alpha = 0.0748
    feedback  rehearsed -> belief [beta=1.90];                       // S1 cap: 2.0

    // ---- STAGE 2: PROPAGATION ----
    osc  osc1: Oscillator< signal=impress, source=cadence,
                           period=7.0, duty=0.15, sustain=270.0 >;
    xfmr xf1:  Transformer< primary=impress, secondary=shared, n=3.0, k=0.50 >;
    capacitor c2: Capacitor< node=bank, C=0.08, n_parallel=140, r_iso=12.0,
                             leak_tau=540.0, V_BR=8.0 >;
    charge shared -> c2 [V=6.0];                     // metered upward path, Ch 7.5

    // ---- THE FUSION — the one licensed x on this board (14.2) ----
    integrate eg1: ( seeded × bank ) = egregore;

    // ---- STAGE 3: MANIFEST ----
    diode d2: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
    cjt   q2: CJT< cadence | egregore => conduct > [beta=1.00, sat=0.95, region=active];

    // ---- LOOP B: the lawful O -> E path.  Carries FACT, not fiction ----
    filter   flt2: LowPass< in=conduct, out=evidence, tau=90.0 >;
    feedback evidence -> belief [beta=0.30];         // top of the Part III band

    // ---- ANCHOR: outside both loops, zero leakage ----
    capacitor c3: Capacitor< node=record, C=1.00, leakage=0.0, V_BR=10.0 >;
    cjt       q3: CJT< egregore | record => audit > [beta=1.00, region=active];
    monitor   m_anchor: Monitor< node=audit, threshold=0.70 >;   // a FLOOR, not a ceiling
    on m_anchor { alert "anchor low — the claim is being treated as found, not made"; }

    // ---- GOVERNOR: reads the MEASUREMENT, never the setting ----
    constraint measured_loop_gain in [0.0, 2.0];                 // S1
    monitor    m_gain: Monitor< node=gain_meas, threshold=1.80 >; // S3
    on m_gain { alert "measured G at 1.80 — damp within one cycle"; }
    cjt q_kill: CJT< gain_meas | charter => cadence > [beta=0.0, region=cutoff];

    // ---- CSB (mandatory, Ch 24) ----
    cjt        q4: CJT< audit | charter => guard > [beta=2.0, sat=0.85, cutoff=0.30];
    fuse       f1: Fuse< guard, threshold=0.90, action=permanent_block >;
    constraint dial_spread in [0, 4];                            // Chapter 6.2

    // ---- TEST POINTS ----
    probe tp1: seeded;      // seed clarity entering the loop
    probe tp2: audit;       // can the construction still be recovered?
    probe tp3: bank;        // collective store charge
    probe tp4: gain_meas;   // MEASURED round-trip gain — seed-removal test
}
```

[[FIGURE 14-B: Full schematic of CCB-H in drawn symbols — R1 and D1 at the left edge feeding Q1, whose bias terminal is a horizontal rail carrying capacitor C1; FLT1 and gain block FB1 drawn as a return path *above* the main line from Q1's effect to that rail, labelled LOOP A β=1.90; transformer XF1 with primary on the effect line and secondary feeding a parallel bank of small capacitors C2 each with its own series isolation resistor; the fusion node drawn as a summing junction marked eg1 with the emergent literal printed beside it; D2 and Q2 on the main line into the conduct output; FLT2 and FB2 as a wider return path *below* the main line back to the same bias rail, labelled LOOP B β=0.30; and, drawn in a separate boxed region touching nothing else, C3 with a bar symbol marked leakage=0, Q3, monitor M_ANCHOR, Q4 with sat=0.85 and fuse F1.]]

**Why this listing does not validate, and why that is correct.** Pass 6 of the CCDL validator (Appendix B, B.6) requires round-trip loop gain below 1 on every loop and emits `E-CJT-005 GainDivergence` otherwise. CCB-H is the one board in this catalogue designed to fail that pass. A tool that waved it through would be broken, because on every other board an above-unity loop is a defect that eats the circuit. The discipline that makes a waiver defensible is written into the listing rather than into an argument: `constraint measured_loop_gain in [0.0, 2.0]` bounds it, `m_gain` watches the measurement, `q_kill` damps it, and `c3`/`q3` hold an audit that is not downstream of either loop. Remove any one of those four and the waiver has nothing behind it.

---

### 14.4 The 100th Monkey Effect as Collective CJT Saturation

The popular claim is that when the hundredth member of a population acquires a behaviour, it appears spontaneously in populations that have had no contact with them.

**Evidential status, stated plainly.** That claim circulates far more widely than it has been checked, and its distinctive element — transfer across populations with no contact — is not established by the primate-behaviour observations it is usually attached to. This book rests nothing on it and does not cite it as evidence for anything. It is worth a section for two reasons. First, the underlying *structure* — a threshold beyond which a belief stops needing to be pushed — is real, is derivable from the components already on this board, and has a number attached. Second, the story is itself a well-formed hyperstition, propagated by being believed and by the conduct of the believing, which makes it the neatest available specimen of its own subject.

**The structure that survives.** Replace Loop A's gain block with the transformer, because in a collective the return path runs through other minds:

```
  G_coll = g_m · k · f · β_XF   +   g_m · β_B · β_M · χ
           └──── through other people ────┘   └── through conduct ──┘
```

`k` is the coupling coefficient of Chapter 9.3 — shared cadence of contact, not agreement. `f` is the **fan-out**: how many other bank members one member's emission reaches per cycle. `β_XF` is the transformer's delivery efficiency (Chapter 11.5), 0.73 at the design-centre mismatch.

Solve for the crossing at the chapter's design centre, `g_m = 0.60`, `β_XF = 0.73`, `β_B·β_M·χ = 0.30 × 1.00 × 0.60 = 0.18`:

```
  G_coll = 0.438·k·f + 0.108 = 1     ->    k·f = 2.037
```

| Coupling `k` | Condition (Ch 9.3) | Contacts per member per cycle needed |
|---|---|---|
| 0.05 | Asynchronous text, no shared cadence | 40.7 — unreachable |
| 0.20 | Shared feed, common daily cadence | 10.2 |
| 0.50 | Live co-present group, shared tempo | 4.1 |
| 0.90 | Sustained dyad — household, mentor | 2.3 |

**No headcount appears anywhere in that derivation.** The transition is a threshold in a product of four terms, none of which is a population size. Population enters twice and only twice: a group of six cannot supply `f = 10`, and `C_collective` sets the calendar through `τ = R × C` (Chapter 7.5). So the sustaining unit of a hyperstition is the *smallest tightly-coupled group that can supply `f`* — at `k = 0.50`, about five people — while spreading needs a population to supply newcomers. That is why a five-person cell holds a shared fiction indefinitely and a hundred-thousand-follower list does not.

And the board contradicts the popular version outright. Transfer between populations with no contact means `k = 0` between them, at which `G_coll` falls to the conduct term alone — 0.108, deeply damped. Nothing crosses. **The mechanism the story names is the one the model rules out; the threshold it gestures at is real and sits somewhere else entirely.**

> **Bench Note — a saturated collective stops recruiting and stops updating in the same instant.**
> When the bank clamps at its ceiling, every member's seed CJT is biased at maximum, so `e` pins at `sat1`, so `∂e/∂s = 0` — and `g_m` drops out of `G_coll`, which collapses to the conduct term. The group is no longer growing. It is also no longer persuadable, and for exactly the same reason: a pinned stage has stopped responding to its cause, which is the property Chapter 24.2 installs deliberately in a refusal and Chapter 13 warns about in an amplifier. The observable is specific and easy to check from outside: **a saturated collective stops producing new arguments and starts producing restatements.** Novel objections get answered with slogans that were already in circulation. Count the fraction of a week's output that is new material versus re-presentation; when it crosses about half, read TP3 and expect it near the ceiling.

---

### 14.5 Feedback Gain Calibration — When 1.0 Becomes 1.15

You cannot estimate `G`. That is the finding this section exists to deliver, and every design choice below follows from it.

`G_coll` is a product of `g_m`, `k`, `f` and `β_XF`. Suppose you know each of the first three to ±10%, which is a generous claim about quantities nobody meters. The relative uncertainty of the product is `√(0.10² + 0.10² + 0.10²) = 0.173`. A computed `G` of 1.15 therefore sits **inside** its own error bar: 1.15 ± 0.20 spans 0.95 to 1.35, which is decay through explosive growth. An operator who calculates `G = 1.15` from parameters has learned nothing about whether the board is running.

So you measure it, and there is exactly one measurement that works.

**The seed-removal test.** Stop the oscillator. Read TP3 for `n` cycles. The recursion with `c = 0` is `s_n = s_0 · A_L^n`, so the store's trajectory with the seed gone *is* the loop gain, directly, with no parameter estimation anywhere in it. Design rule: **hold the seed off for 8 cycles; a fall greater than 10% is sub-critical, a rise greater than 10% is super-critical, and anything between is unresolved — extend the test.**

That is why the target is 1.15 and not 1.0. The resolution time of the test is `n = ln(1.2) / ln(1 + α(G−1))`, and at this board's `α = 0.0748`:

| `G` | Growth per cycle | Doubling `n₂` | Cycles to resolve ±20% |
|---|---|---|---|
| 1.05 | 0.0037 | 186 | 49 (11 months) |
| **1.15** | **0.0112** | **62** | **16 (4 months)** |
| 1.50 | 0.0374 | 19 | 5.0 |
| 2.00 | 0.0748 | 9.6 | 2.5 |

**`G = 1.15` is the smallest growth a quarter-length test can resolve.** Below it you cannot distinguish a live hyperstition from a rented one inside a planning cycle, and an operator who reports crossover at `G = 1.05` is reporting a number they did not measure. Nothing about 1.15 is a property of belief. It is a property of your instrument.

The upper bounds derive as cleanly. Set the audit period at four cycles — monthly, on a weekly clock. Require that the store cannot climb from half-charge to its ceiling in fewer than two audit periods, so that `^6` always runs at least twice on a changing store: `n₂ ≥ 8` gives `α(G−1) ≤ 2^(1/8) − 1 = 0.0905`, so `G ≤ 2.21`. **S1 caps `G` at 2.0** for margin, and **S3 fires the kill at a measured 1.80**, one audit period earlier, so the alarm arrives while there is still a cycle in which to act.

> **Bench Note — capping your knob does not cap the loop.**
> `β_FB` is the only term in `G` an operator sets. Everything else is a property of the audience and the world: `g_m` is how framing-sensitive the audience is, `k` is how much cadence they share, `f` is how often they reach each other, `χ` is how readily the world accommodates the conduct. Work the arithmetic at the S1 boundary. With `β_FB` pinned at 2.0 and a design-centre audience at `g_m = 0.60`, the operator's own loop reaches `G_op = 0.60 × (2.00 + 0.18) = 1.308` — comfortably inside the cap. Now hold `β_FB` at **zero** and hand the same claim to a highly framing-sensitive, tightly-coupled group: `g_m = 2.40`, `k = 0.90`, `f = 3.0` gives `G_coll = 2.40 × 0.90 × 3.0 × 0.73 + 2.40 × 0.18 = 4.73 + 0.43 = 5.16`. Runaway, with the operator's gain block switched off and the campaign shut down. **That is why S3 watches TP4 and not the setting**, and why "we stopped promoting it" is not a control action. Handing a claim to the wrong `g_m` is the whole of the failure.

**Reading a hyperstition from outside.** A defender cannot see the listing, but three of the four terms are observable without it. Ratio of new material to restatement estimates saturation. Frequency of co-present contact estimates `k`. Whether believers *do* things — buy, register, travel, defend — or only speak estimates whether Loop B exists at all, and a hyperstition with no Loop B is running on operator spend and will stop when the spend does. Chapter 18.6 works the consumer case in full.

---

### 14.6 Worked Example: Creating a Brand Egregore

**Maison du Temps**, a watch house incorporated last spring. The claim: *a Maison du Temps watch is the one you hand to your child.*

Start with why that claim and not the tempting one. "Swiss craftsmanship since 1887" is outside the reachable set of 14.2 — no present conduct reaches 1887, so the claim has no Loop B, and asserting it is a matter for a regulator rather than a schematic. "The one you hand to your child" is inside it: it is false at launch, since nobody owns one, and conduct can make it true. It also tells you what to build — a movement that survives forty years, a service record, a registry — which is the resistance work, and which is where the effort will actually go.

**Configuration.** `T = 7 days`, duty 0.15. Member store `τ = 90 d`, so `α = 1 − e^(−7/90) = 0.0748`. Bank at institution scale, `C_collective = 0.08 F_c`, `R = 80 Ω_c`, `τ_bank = 6.4 months`, `α_bank = 0.0353`. Seed clarity `TP1 = 0.68`. Q1 at `β1 = 0.90`, `sat1 = 0.80`, `g_m = 0.60`. Loop A `β_FB = 1.90`; Loop B `β_B = 0.30`, `β_M = 1.00`, `χ = 0.60`.

**Months 0–3: the operator's own store fills.** Run the recursion, `s_{n+1} = 0.9252·s_n + 0.0748·(2.08·e_n)`:

```
  cycle 0   e = 0.612                       s -> 0.095
  cycle 2   e = 0.727                       s -> 0.291
  cycle 4   e = 0.847 -> pinned at 0.80     s -> 0.487
  cycle 8   e = 0.80  (pinned)              s -> 0.732
  cycle 12  e = 0.80  (pinned)              s -> 1.000  CLAMPED
```

Twelve weeks. Meanwhile the bank, on a `6.4`-month constant fed through a 3:1 transformer, sits near 0.04. **The founder's belief store is full while the audience's is at four percent** — a gap of one quarter against several years, and the entire reason C3 and the anchor exist. Note also that Q1 pinned at cycle 4: from there on `∂e/∂s = 0`, so the operator's own loop gain has already collapsed to its retention term. The store is full and no longer growing, which reads from inside as certainty.

**Month 4 — first seed-removal test.** Campaign off for eight cycles. TP3 falls from 0.041 to 0.035, **−15.4%**. Sub-critical. Back-solving, `A_L,coll = 0.9794`, so `G_coll = 1 − 0.0206/0.0353 = 0.415`. Decomposed: `0.438·k·f` with `k = 0.20` (a shared feed) and `f = 3.5` gives 0.307, plus 0.108 from conduct. **The thing is rented.** Eight weeks of silence cost the campaign real money and bought the only number on the board that means anything.

**Months 5–14 — what actually moved.** Not the content budget. `k` rose from 0.20 to 0.50 by making contact co-present: four owner meets a year, servicing done in a room with other owners in it rather than by post. `f` rose from 3.5 to 6.0 through a registry that tells owners who else is nearby. `χ` rose from 0.60 to 0.75 because visible owners make the next purchase easier to accommodate. `β_FB` did not move.

**Month 14 — second test.** TP3 rises from 0.31 to 0.352 over eight cycles, **+13.4%**. `A_L,coll = 1.0158`, so `G_coll = 1 + 0.0158/0.0353 = 1.449`. Crossover. Decompose it:

```
  through other people   0.438 × 0.50 × 6.0 = 1.314      90.7%
  through conduct        0.60 × 0.30 × 0.75 = 0.135       9.3%
  through beta_FB                             0.000       0.0%
                                              -----
                                              1.449
```

**`β_FB` contributes nothing to `G_coll`, and it never could.** From the collective's point of view the operator's Loop A is not feedback at all — it is *seed*, an external drive that raises the level and dies with the spend. That is the finding, and it is the same shape as Chapter 13's: the lever every operator reaches for first is not the lever. Running `β_FB` at 1.90 for fourteen months produced a founder pinned at full charge by week twelve and moved the growth term by zero.

The `×` becomes writable here and not before. With `G_coll > 1` at a measured crossover, `( seeded × bank ) = egregore` asserts something now tested: Q2 fires on `egregore` with the seed disconnected, which is precisely what the eight-cycle rise demonstrated.

**The anchor reading.** TP2 at month 14 is **0.74**, against the 0.70 floor — a margin of 0.04. The founder can still state the date the claim was written, who wrote it, and why, but the audit is one bad quarter from tripping. The required action is not a tuning change. It is that C3 gets read aloud at each monthly audit, by someone who was not in the room when the claim was written.

[[FIGURE 14-C: Assembly drawing of CCB-H — rectangular board outline; designators R1, D1, Q1, C1, FLT1, FB1, OSC1, XF1, C2, D2, Q2, FLT2, FB2 placed along a left-to-right path; the LOOP A return drawn as a short trace above and the LOOP B return as a long trace below, with FB1 β=1.90 and FB2 β=0.30 printed on them; the anchor block C3–Q3–M_ANCHOR–Q4–F1 drawn inside a heavy dashed outline in the lower right labelled "OUTSIDE BOTH LOOPS"; four circled test-point callouts on leader lines with expected bands (TP1 0.55–0.85, TP2 ≥0.70, TP3 read only against a seed-removal test, TP4 0.90–1.50); and a boxed BOM at lower right listing every designator with its key parameter.]]

[[FIGURE 14-D: Stability plot — horizontal axis round-trip gain G from 0 to 2.5, vertical axis store charge s from 0 to 1 over 60 cycles; four trajectories drawn from the same starting charge for G = 0.50, 0.99, 1.15 and 2.00, the first two decaying at visibly different rates, the third rising with its 62-cycle doubling marked, the fourth clamping at 1.0 with the clamp point annotated "pinned — no longer growing and no longer persuadable"; a vertical dashed line at G = 1.00 labelled "idealisation — measure-zero, unbuildable"; shaded bands for the S3 kill at 1.80 and the S1 cap at 2.00.]]

[[FIGURE 14-E: Seed-removal test, two panels sharing an 8-cycle horizontal axis. Left, month 4: TP3 falling 0.041 → 0.035, −15.4%, annotated "sub-critical, G = 0.415 — rented". Right, month 14: TP3 rising 0.31 → 0.352, +13.4%, annotated "super-critical, G = 1.449 — crossover". A shaded ±10% band across both marked "unresolved — extend the test".]]

---

### Component and Parameter Table

The last column is what breaks at other settings.

| Ref | Form | Parameters | Failure at other values |
|---|---|---|---|
| **R1** | seed constraint | R=20.0 | Above ~60 the seed never clears Q1's cutoff; nothing defends against a story, so a high value here models the wrong thing |
| **D1 / D2** | `^C -> ^E`, `^E -> ^O` | Vf=1.2, 2.0 | ΣVf = 3.2 is the floor for operational output (Ch 8.1). Vf=0.5 on D2 gives conduct on every impression |
| **Q1** | `-> ^9_impress^E_{F2}\|f` | β=0.90, sat=0.80, g_m=0.60 | β=1.5 pins the stage at cycle 0 and no calibration downstream is valid (Ch 13). `g_m` is the **audience**, not a knob — see 14.5 |
| **C1** | `^5_belief^E_{F2}\|f` | leak_tau=90 d | 540 d here models a founder's store as a bank; the founder fills in a quarter and the bank does not |
| **FLT1 / FB1** | Loop A | τ=90 d, β=1.90 | β>2.0 breaks S1. β=0.30 leaves `G_op` at 0.29 and the operator never believes their own claim, which sounds safe and produces no `di/dt` to couple with (Ch 9.3) |
| **OSC1** | `-> ^7_cadence^E_{F6}\|E` | period=7 d, duty=0.15, sustain=270 d | duty≥0.6 is a DC level, not a rhythm; `^4` per exposure falls (Ch 11.2). sustain < 3×τ_leak rents the cadence rather than building it |
| **XF1** | `^9^E` → `^9^E` | n=3.0, k=0.50 | `n>15` drops the secondary below ΣVf: reaches everyone, moves no one (Ch 11.5). Primary below secondary in domain order is `E-CJT-008` |
| **C2** | `^5_collective^E_{F4}\|f` | C=0.08, n_parallel=140, r_iso=12, leak_tau=540 d | In-group C=0.02 on a brand community under-budgets the calendar fourfold (Ch 7.5). r_iso=0 lets one member's collapse take the bank |
| **FLT2 / FB2** | Loop B, `^O -> ^E` | τ=90 d, β=0.30 | β>0.30 leaves the Part III band on the one upward path; τ→7 d removes the diode and a single sale rewrites the store |
| **C3 / Q3** | `^6_anchor^P_{F6}\|A` | leakage=0.0, β=1.00 | Any leakage and the anchor drifts with the claim it measures. β>1 manufactures doubt; β<1 hides real drift |
| **Q4 / F1** | `-> ^3_guard^P_{F7}\|⟨A,f,T⟩` | β=2.0, sat=0.85, F1 at 0.90 | Matches Ch 24.2–24.3. `action=warn` compiles clean and leaves no latch — read it by eye |
| **Q_KILL** | into `cadence` | β=0.0 | Wired to `β_FB` instead of to the measurement is S3's commonest defeat |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `^0_seeded^E` | Seed clarity entering the loop | 0.55–0.85. Below 0.55 Q1 sits near cutoff; above 0.85 the claim is over-specified and Loop B has only one way to satisfy it |
| **TP2** | `^6_audit^P` | Can the construction still be recovered — date, author, motive, unaided? | ≥0.70. Below 0.70 the alert fires. Below Q4's cutoff of 0.30 the audit stage is no longer firing at all |
| **TP3** | `^5_collective^E` | Bank charge | Meaningless as a level. Read **only** as a trajectory across a seed-removal test |
| **TP4** | `^4_loopgain^E` | Measured round-trip gain | 0.90–1.50 working. ≥1.80 kill (S3). >2.0 breaches S1. Any value not obtained from an 8-cycle test is not a reading |

TP3 is the test point most often misused. A large bank proves the seed was expensive, not that the loop is alive.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Assumed gain** | `G` computed from parameters, not measured | Confident reports of `G = 1.05`; the number is inside its own ±0.17 error bar | Run the 8-cycle seed-removal test. There is no substitute |
| **Rented hyperstition** | `G < 1` with heavy seeding | Large TP3, healthy traffic, collapse within 3τ of the spend stopping | Move `k` and `f`, not the content budget |
| **Operator capture** | `G_op > 1` while `G_coll < 1` | Founder pinned at full charge by week 12; TP2 sliding toward 0.70 | C3 read aloud at each audit, by someone outside the room where the claim was written |
| **Audit inside the loop** | Q3 biased by anything downstream of Loop A or B | TP2 rises exactly when TP3 rises — the audit is confirming the claim it should decompose | Re-bias Q3 on C3 only; check the wire, not the reading |
| **Collective pin** | Bank clamps; `∂e/∂s = 0` | New material falls below half of weekly output; novel objections met with existing slogans | Nothing recovers a pinned bank from inside. Reduce drive and wait for leak |
| **Runaway** | `g_m` or `k` rise past the design centre with `β_FB` anywhere | Doubling shorter than one audit period; kill fires at 1.80 | Damp within one cycle via Q_KILL. Do not re-seed to "control the narrative" |
| **Unreachable claim** | Claim outside the conduct-reachable set | `G` never exceeds `g_m·β_FB`; dies at spend-stop every time | Re-author the claim. No gain setting reaches into the past |
| **Anchor drift** | C3 given non-zero leakage | Construction date recalled differently at successive audits | Restore `leakage=0.0`: written, dated, and not re-typed from memory |

---

### What This Chapter Established

- **Growth depends on `G` alone; cadence sets only speed.** `A_L − 1 = α(G − 1)`, and `α` cancels out of the sign. Shortening the cycle on a sub-critical loop makes it settle and die faster. You cannot post your way past `G < 1`.
- **`G = 1` is an idealisation, not an operating point.** It is measure-zero on a product of four estimated terms, and a board reported to be sitting there has not been measured.
- **`G` cannot be estimated, only measured.** Three terms at ±10% give the product ±17%, so a computed 1.15 spans decay to explosive growth. The seed-removal test is the only reading: stop the clock for 8 cycles and watch TP3.
- **1.15 is a property of the instrument.** It is the smallest growth an eight-to-sixteen-cycle test resolves. The caps at the top — S1 at 2.0, S3's kill at 1.80 — come from the audit period, so that `^6` always runs at least twice on a changing store.
- **Capping the operator's knob does not cap the loop.** `β_FB` is one term of four; `g_m`, `k` and `χ` belong to the audience and the world. A claim handed to a framing-sensitive, tightly-coupled group runs away with the campaign switched off. S3 therefore watches the measurement, never the setting.
- **Loop B carries fact, not fiction, and it bounds what the board can deliver.** A hyperstition can only make true the class of claims that conduct can make true. A claim about the past has no Loop B, dies at spend-stop, and is a matter for a regulator rather than a schematic.
- **The hundredth-monkey threshold is real and is not a headcount.** `G_coll = 0.438·k·f + 0.108` crosses unity at `k·f = 2.04` — five tightly-coupled people, or forty loosely-coupled contacts. Transfer between populations with no contact requires `k = 0`, at which the model says nothing crosses.
- **A saturated collective stops recruiting and stops updating in the same instant**, because both depend on `∂e/∂s`, and a pinned stage has none. The observable is restatement displacing new material.
- **`( seeded × bank ) = egregore` is a falsifiable commitment, not a flourish.** The `×` is licensed only after TP4 shows crossover; before that the honest form is `+`. The notation changes when the measurement does.

---

### Exercises

*(Answers in Appendix H.)*

**14.1 — Compute the sign.** An operator reports `g_m = 0.45`, `β_FB = 1.60`, `β_B = 0.30`, `β_M = 1.0`, `χ = 0.50`. Compute `G_op`. State whether the store grows, and what changing the cadence from weekly to daily would and would not do.

**14.2 — Size the test.** At `α = 0.0748` and a true `G` of 1.08, how many cycles must a seed-removal test run to resolve a 20% change? Convert to calendar weeks. State what an operator learns from a 4-cycle test at that gain.

**14.3 — Find the crossing.** Using `G_coll = 0.438·k·f + 0.108`, find the minimum `f` at `k = 0.35`, and the smallest group size that can supply it. Then state what happens to both numbers if the conduct term is zero because the claim is unreachable.

**14.4 — Diagnose the anchor.** TP2 reads 0.81, 0.77, 0.72, 0.68 across four monthly audits while TP3 rises steadily. Name the failure mode, say which wire you would inspect first, and explain why re-reading TP2 more often would not help.

**14.5 — Read a saturated bank.** A community's weekly output is 18% new material and 82% restatement; TP3 sits at 0.96. Compute what `G_coll` has collapsed to, given `k = 0.60`, `f = 5.0`, and the design-centre conduct term. State the one thing that will move it and roughly how long that takes at `α_bank = 0.0353`.

**14.6 — Cost the honest claim.** Rewrite "handcrafted in the same workshop for four generations" as a claim inside the conduct-reachable set for a company founded eighteen months ago. Then list the three resistance terms (Chapter 4.4) your rewrite obliges you to attack, and which one carries the largest share.

**14.7 (Build) — Add a fan-out meter.** `f` is the term with the most leverage in `G_coll` and the one nobody measures. Write a CCDL fragment that probes it without altering the loop. State what your probe must **not** be wired to, and why probing the transformer's secondary is not the same measurement.

**14.8 (Marquee) — Board a hyperstition you are inside.** Pick a claim you already act on that was constructed in your lifetime and whose construction you can date. Specify the board: TP1, `β_FB`, both loop paths with their filters, the anchor's contents, and your best estimates of `g_m`, `k`, `f` and `χ`. Compute `G_coll` and its error bar. Then design the seed-removal test you would have to run to settle it, state its cost in weeks, and say honestly whether you would run it.
