# CHAPTER 23
## St. John's Equation — Advanced Calibration
*Reading a campaign instead of a cast — scheduling, interference, and what the equation does at its limits*

Two operators sit through the same operation and each writes down two numbers. The first records `t_op = 30` minutes and `t_conf = 90`, runs Chapter 5.3's arithmetic, and reads a required gain of **9**. The second caught the clock differently — 31 and 88 — because they disagreed by a breath about when the gnosis began and when the song on the radio registered.

The second operator's reading is **264**.

Neither made a mistake. Thirty-one is prime, 264 factors as 8 × 3 × 11, the fraction will not reduce, and the denominator Chapter 5 tells you to read as a required gain comes back thirty times larger for two minutes of honest disagreement about a wristwatch. That is a reduction problem, not a measurement problem, and Chapter 13.5 already fixed it for a single cast: act on the amplitude ratio `A = b/a = 3/η`, never on `b` alone. The two operators' ratios are 9.00 and 8.52.

Section 13.5 reads one cast. It does not run a **campaign** — a sequence of operations on one desire, scheduled against each other, competing with everything else you have live. Campaigns break in four places a single cast never reaches: at the limits of the equation, at the scheduling, at the interference between concurrent operations, and at the point where an operator with three live campaigns wonders why all three went cold in the same week. This chapter is the instrument board. It casts nothing. It reads the log.

---

### Requirements and Safety Invariants

Chapter 12.2 requires the "must not" list before the functional one.

| # | Functional requirement | Realized by |
|---|---|---|
| R1 | Turn two clock readings into an amplitude requirement | Quantizer → ratio → readout |
| R2 | Stay stable against clock jitter of a few minutes | Ratio `A` on a quantized grid (§23.1) |
| R3 | Declare NO-READ rather than invent a number | Horizon gate, band guard |
| R4 | Report whether a campaign converges | Ledger filter, ratio `ρ` |
| R5 | Derate when other operations are live | Interference model (§23.2) |

| # | Safety invariant (MUST NOT) | Enforcement |
|---|---|---|
| S1 | Report `A ≥ 9` as an amplifier instruction | Re-spec fuse, `block_until_decomposed` |
| S2 | Admit a confirmation arriving after the horizon | Horizon fuse, `action=no_read` |
| S3 | Accept a confirmation two live operations could claim | Entry marked `AMBIGUOUS` |
| S4 | Let a blown ledger reset by re-wording the target | Re-spec must change domain or object |
| S5 | Run without the operator's CSB armed (Chapter 24) | No ledger opens on a blown involution monitor |

[[FIGURE 23-A: Block diagram — CCB-CAL, left to right: LOG INTAKE (t_op, t_conf) → QUANTIZER (5-min grid) → HORIZON GATE with a downward branch to a NO-READ terminal → RATIO (fixed 3.0 divider, output A) → BAND GUARD with four exits ACT / CLOSE / DRIVE / RE-SPEC → CAMPAIGN LEDGER (rho trend). A 72-hour scheduling oscillator sits beneath the intake and feeds it. TP1–TP4 flagged at quantizer output, ratio input, ratio output, ledger output.]]

---

### 23.1 The 1/3 Constant — Deeper Derivation from Fibonacci and Pi

Section 5.2 sets `τ = 1/3` beside π ≈ 3.14159 — both non-terminating — as a mnemonic for domains left *open*. Be exact about what that is. φ and π are mathematical constants with proofs behind them. **There is no derivation that produces 1/3 from either, and this book does not offer one.** The only derivation of `τ` in these pages is Section 5.2's training arc: roughly 10,000 active hours inside a roughly 30,000-hour span, one part work to two parts gestation.

```
η = t_op / t_conf     result = η × τ = a/b     A = b/a = 3/η = 3 t_conf / t_op
```

`A` is fixed by two clock readings and by `τ`. Nothing else enters. **`τ` is a scale factor — a unit convention — expressing a cast's requirement against that same 1:3 split.** Change `τ` and every number in every log changes by the same factor, while every *comparison between operations* stays where it was. The equation's content is the ordering it puts on your operations, not the magnitude of any one reading. That is a structural analogy, not a measured law. Nothing here shows that time is quantized at thirds, and a reader who treats `A = 9` the way they treat a resistor's 470 Ω will over-trust two wristwatch readings and a convention.

#### Quantize before you reduce

`A` moves smoothly. The integer pair does not, because lowest-terms denominators are not continuous in their inputs — that is the whole content of the cold open, where 30/90 gave (1, 9) and 31/88 gave (31, 264).

Quantize both clocks onto a **5-minute grid** before reducing. Five minutes is a design choice: finer than the 30-minute bins Section 5.5 uses to grade `^4` Vibration, coarser than the moment an operator *notices* a confirmation, which is not a one-minute-accurate event. Too fine and the coprime explosion returns; at 30 minutes a 20-minute operation confirmed at 25 bins with one confirmed at 45, erasing the difference between an overdriving circuit and an ordinary one. **If `a > 3` after quantizing, discard the pair and act on `A`.**

> **Bench Note — check this one by hand before you trust the bench.** Take `t_op = 27`, `t_conf = 64`. Raw: `27/192` reduces to `9/64` — a = 9, b = 64. On the grid: `25/195` reduces to `5/39` — a = 5, b = 39. The two pairs share nothing at all. Now compute `A`: `3 × 64/27 = 7.11` and `3 × 65/25 = 7.80`. Both land in the same band and say the same thing. Do this arithmetic yourself once. Until you have watched `b` swing from 64 to 39 while `A` barely moves, you will keep reaching for the denominator, because Chapter 5 taught you to.

#### The bands, and the two limits

Chapter 13.5's bands fall out of `A = 3/η`, and their edges land on clean values of η.

| `A` | η | Reading | Action |
|---|---|---|---|
| `A ≤ 1` | η ≥ 3 | Sufficient | Stop calibrating. Act |
| `1 < A < 3` | 1 < η < 3 | Close | Finish the resistance work |
| `3 ≤ A < 9` | 1/3 < η ≤ 1 | Under-driven | One lever at a time |
| `A ≥ 9` | η ≤ 1/3 | Weak coupling | Re-specify (§23.3, §23.4) |

Chapter 5.4's Red Corvette sits at η = 1/3, `A` = 9 — exactly on the re-specification boundary. The canonical worked example in this book is a borderline cast, worth knowing before you copy its numbers.

**`t_conf → ∞`: the confirmation never comes.** `η → 0`, `A → ∞`, and the temptation is to write `β=∞` into the listing. That is an idealization the validator rejects — parameter fields are range-checked and refuse non-finite values — and where a real build would substitute a large finite gain, no finite substitute exists here, because the input is *missing* rather than large. The bench returns **NO-READ**, behind a horizon:

```
t_H = 3 × median(t_conf over the last 10 logged operations),   floor 24 h
```

Over a long enough window *everything* confirms: a loose desire matches some event in any given day, and an operator who holds the window open until something matches is measuring their own patience. The 3× multiple is wide enough that a genuinely slow circuit still reads, narrow enough that the median stays meaningful; the 24-hour floor covers the early log, where the median rests on too few entries. Too short and live circuits are declared dead; too long and the log fills with base rate.

**`t_conf → 0`: the confirmation arrives inside the operation.** `η → ∞`, `A → 0`, and the reduction degenerates. At `t_op = 30`, `t_conf = 4`: `η = 7.5`, `result = 5/2`, pair (5, 2) — "twice as strong, five more times," for a circuit that confirmed inside four minutes. The quantizer does not save that; only the band guard does. Above η = 3 the bench returns **OUT-OF-BAND-HIGH**, and the instruction is Section 13.6's: stop calibrating, take the practical action.

[[FIGURE 23-B: Characteristic curve — A against eta. Horizontal axis eta 0 to 4, log-spaced below 1; vertical axis A 0 to 20. Hyperbola A = 3/eta, band shading ACT / CLOSE / DRIVE / RE-SPEC (hatched), dashed verticals at eta = 1/3, 1, 3. Annotate the Red Corvette at (1/3, 9) and the derated concurrent cast of §23.2 at (0.30, 10).]]

---

### 23.2 Multi-Operation Compounding — When β_next > 10

The title states the condition as Chapter 5 states it, because that is how it arrives: an operator reads a denominator above 10 and asks what to do. On this bench it is `A ≥ 9` — the same complaint with a stable number attached.

A campaign is a sequence of operations on one target, each designed from the last one's reading, and demand compounds as `demand_{k+1} = demand_k × A_k`. **The compounding is multiplicative.** Two operations each reading `A = 3` demand nine times the original delivered current. Cascaded gains multiply (§10.5) and a campaign is a cascade in time, which is why a high reading is a stop rather than a challenge: it is the head of a geometric series.

**`A` is not a β setting.** Section 13.5 governs: `A` multiplies the *delivered current* at TP4, and five things set that current — clarity of the formed `^0` Idea, transmission through the dial divider, residual aversion, the amplifier, and `R_op`. The CJT's design range tops out near **4.0** (Chapter 3.3). So β across a campaign moves under a ceiling, not a formula: one increment per operation inside 0.5–4.0, with everything above taken from the other four levers or from recruitment. An operator who reads `A = 9` and writes `β = 9` has specified a device that does not exist.

```
φ_k = 1 / A_{k+1}   (delivery fraction)      ρ_k = A_{k+1} / A_k   (convergence ratio)
```

Design threshold: **`ρ ≤ 0.6` per operation.** From `A = 9` a campaign at 0.6 runs 9 → 5.4 → 3.2 → 1.9 → 1.2: inside DRIVE by the second step, near sufficiency by the fourth. At `ρ ≥ 1.0` it is diverging, and the action is to stop by operation three rather than cast harder. A flat `ρ` sustained is the "η flat" row of Section 22.5. Believe no trend before three operations — `A` is a quotient of two soft clock readings, and one of them has no error bars at all.

> **Bench Note — the flat ledger column is a tautology, so do not read it as evidence.** It is natural to keep an "absolute target" column, `T_k = G_k × A_k`, where `G_k` is cumulative realized gain. Work the algebra and `T_{k+1} = T_k` identically, for any campaign, converging or not — because `G` is itself defined from the `A`s. A column that cannot vary cannot inform. Operators build it, watch it hold at 9 for four operations, and conclude the campaign is on target. It would have held at 9 if every operation had been worthless.

#### Scheduling: one live operation per horizon

A confirmation you cannot attribute to a specific operation is not a measurement. **No new operation on a desire begins until the previous horizon has closed.** At a median `t_conf` of 45 minutes, `3 × 45 = 135` minutes falls under the 24-hour floor and the floor governs; the campaign below uses 72 hours, which also lets the `^5` capacitor recover between casts (§7.3). Fire inside the horizon and a confirmation has two candidate causes: mark it `AMBIGUOUS` and drop it from the median. An operator who wants a good number assigns every confirmation to the most recent cast, and the ledger then reports a convergence that never happened.

#### Interference between concurrent operations

Concurrent operations on *different* desires share one operator: one `^1` Mind budget, one `^5` substrate, one attention rail. Chapter 9.3's coupling model transfers directly and the coefficient keeps its name.

```
η_effective = η_isolated × ( 1 − k × (N − 1) )
```

| `k` | Condition | Observed when ignored |
|---|---|---|
| 0.05 | Different Drive, different domain, no shared symbol | Nothing. The intended posture |
| 0.15 | Same Drive, different target | Uniform mild slump in η across everything live |
| 0.35 | Same Drive, shared symbols — sigil letters, same person | Every campaign's `A` doubles in a week for no visible reason |
| 0.60 | Contradictory desires — one raises the other's `R_constraint` | Both ledgers diverge, `ρ > 1` on each at once |

Work it. Three live operations, all on F5 Agency, all sharing symbols: `N = 3`, `k = 0.35`, derating `1 − 0.35 × 2 = 0.30`. Take an operation reading `η = 1.0` in isolation — comfortably DRIVE at `A = 3`. Concurrently, `η_effective = 0.30`, so with `t_op = 30` the confirmation lands at `30 / 0.30 = 100` minutes, already on the grid:

```
η = 30 / 100 = 0.30        A = 3 × 100 / 30 = 10.0        →  RE-SPEC. The fuse blows.
```

**A comfortable operation became a re-specification reading and nothing was wrong with the operation.** The three campaigns were wrong with each other. This is the most under-diagnosed failure on the bench, because the operator inspects the cast — gnosis, sigil, wording — and the cast is fine.

Hence: keep `k(N − 1) ≤ 0.3`, holding derating at or above 0.7. At `k = 0.05` that permits seven concurrent operations; at `k = 0.35` it permits exactly one. **Run one live operation per Drive.** The derating is first-order and honest only while `k(N − 1) < 0.5`; past that it runs to zero and then negative, which is not a statement about anything. Beyond half derating the model's answer is not a number — it is *shed operations*.

[[FIGURE 23-C: Chart — interference derating. Horizontal axis N (live operations) 1 to 8; vertical axis 1 − k(N−1), 0 to 1. Four labelled lines, k = 0.05, 0.15, 0.35 and 0.60. Dashed line at 0.70 marked “design floor”; region below 0.50 shaded “model not valid — shed, do not compute”. Mark where each line crosses 0.70.]]

> **A plain line about the operator, not the circuit.** A ledger that will not converge, run against a desire that will not let go, is a recognizable and unpleasant place to be. Everything here is arithmetic on a log. None of it is a psychological or medical instrument, and it does not describe, diagnose, or treat distress or compulsion of any kind. If the operations have stopped being something you choose, that is a matter for a clinician, and nothing in this book substitutes for that care.

---

### 23.3 Sub-Desire Resolution — When the Prime Desire Is Blocked

`A ≥ 9` is almost never a statement about how much amplitude you need. It is a statement that the target you specified is not the target that is blocked. Section 21.1 authenticates A0 before an operation; this section is what you do when the bench tells you, three operations in, that the authentication was wrong.

The procedure is decomposition, and the Noetic matters. You take the stated desire apart and test its parts — `^6^C_{F6}|A`, Male, Cognitive domain, analytical register: what is this Idea made of. It is emphatically **not** `^3`. What you are usually *looking for* is a `^3`, a visceral aversion lying across the path, the can't-stomach-it recoil that keeps the cast from landing — but the finding of it is `^6` work. Confusing the two is the drift Chapter 2.2 warns about, and it costs: an operator who believes aversion-hunting is itself `^3` goes looking for something to recoil from and duly finds it.

The arithmetic is the point. A blocking sub-desire sits in the operator's own `^5`, so it is addressed with a self-directed board (Chapter 20) against much lower resistance. Lower `R` means higher η means lower `A`, and sub-desire operations routinely read in DRIVE while the prime desire reads past 9. Then the prime desire is re-read, not re-argued.

---

### 23.4 The Tree of Life Method — Redirecting Through Higher Probability Paths

The second answer to a blown re-spec fuse is to change the route rather than the target: cast for an intermediate outcome that is genuinely wanted, sits at lower resistance, and from which the prime target is reachable — then read the prime desire again from the new position.

**The hops obey the diode chain.** An intermediate sits at the target's domain or lower (§8.1). You may route an Operational target through an Evaluative or Operational intermediate. You may not route it through one requiring an ascent back to Principled mid-chain — `^O × ^P` is invalid notation for the same reason it is invalid engineering (§8.3). The one lawful ascent is the filtered O→P feedback path, on a time constant of weeks (§24.5), not inside a campaign.

**The method cannot promise a smaller total.** Demands cascade multiplicatively, so a two-hop route costs `A₁ × A₂`. Suppose a direct read of `A = 36`, an intermediate reading `A₁ = 4`, and the prime desire read again from the new position at `A₂ = 3`: the product is 12 against 36 direct. Worth having — but **the comparison is retrospective.** You did not compute 4 and 3 by factoring 36. You cast for the intermediate, read 4 from that operation's own log, arrived, cast again, read 3. The route might equally have read 8 and 6. What the method does promise is the thing that matters: **every stage sits inside the feasible band, which the direct path did not.**

---

### 23.5 Astrological Weighting — Planetary Dials for Timing

The tradition schedules operations against a planetary calendar and applies a timing multiplier spanning 0.5 at worst to 3.0 at best. **No celestial mechanism is asserted, no evidence for one is offered, and the multiplier is not claimed to be a measured quantity.** It is a dial. Its **default value is 1.0**, and any other value in your log is a statement about your practice, not about the sky.

What a fixed external calendar genuinely does — a real engineering function — is take the scheduling decision away from the operator. The moment you most want to cast is the moment your `^1` Mind reading is least trustworthy, because wanting to cast and being able to hold gnosis are different faculties and only one of them is impatient. An externally fixed schedule is a watchdog timer: it fires on its own clock regardless of how the operator feels. Any fixed calendar does this; the planetary one is merely unarguable, since you cannot negotiate with an ephemeris.

To treat the multiplier as measured rather than chosen, run the falsification: record the dial **before** the operation, never after; accumulate at least 20 operations; split into high-dial and low-dial windows; compare the **medians** of `A`, medians because `A` is a quotient with a long tail. If they do not separate, set the multiplier to 1.0, keep the calendar for its scheduling value, and log the null. Then name the confound, which is almost certainly present: an operator who believes the timing is favourable casts with more conviction, raising `^1` Mind, raising η, lowering `A` on its own. The dial and the operator's state are not separable in this design.

---

### The Full CCDL Listing — CCB-CAL

```cas
board ccb_cal {                           // CCB-CAL — the calibration bench
    input:  op_log;                       // one row per operation: two clocks, two degrees
    output: next_op_spec;

    node practice_rail: ^5^P_{F7}|T;      // Female: accumulated practice — bias, never driven

    // ---- S1  INTAKE ----
    node clocked_op: ^7^C_{F6}|E;         // Rhythm: the operation, start to finish
    node arrival:    ^8^C_{F2}|E;         // Above/Cause: the event that arrives after
    node recalled:   ^9^C_{F2}|A;         // Below/Effect: the desire brought back to Mind

    // ---- S2  QUANTIZER ----
    filter q_op:   Filter< in=clocked_op, out=t_op,   type=quantize, grid=5.0 >;
    filter q_conf: Filter< in=recalled,   out=t_conf, type=quantize, grid=5.0 >;

    // ---- S3  HORIZON GATE ----
    fuse f_horizon: Fuse< path=arrival, threshold=1440.0, action=no_read >;

    // ---- S4  RATIO ----
    node eta: ^6^E_{F2}|A;                          // Male: the reading decomposed
    resistor r_tau: Resistor< path=eta, R=3.0 >;    // tau = 1/3 as a fixed divider
    node requirement: ^4^E_{F5}|A;                  // Vibration: A = 3/eta

    // ---- S5  BAND GUARD ----
    monitor m_band: Monitor< signal=eta, limit=[0.333, 3.000],
                             action_on_violation=OUT_OF_BAND >;

    // ---- S6  CAMPAIGN LEDGER ----
    node convergence: ^4^E_{F5}|A;                  // rho = A_next / A_current
    filter f_ledger: Filter< in=convergence, out=trend, type=lowpass, tau=3.0 >;

    // ---- S7  RE-SPEC FUSE and lawful descent ----
    fuse f_respec: Fuse< path=requirement, threshold=9.0,
                         action=block_until_decomposed >;
    diode d_out: Diode< ^E -> ^O >;

    // ---- S8  SCHEDULE ----
    node cadence: ^7^O_{F6}|E;
    osc o_sched: Oscillator< signal=clocked_op, source=cadence, period=3.0,
                             amplitude=1.0, gate=m_band >;        // period in days

    probe tp1: q_conf;         probe tp2: eta;
    probe tp3: requirement;    probe tp4: f_ledger;
}
```

**S1 — intake.** `^8^C` and `^9^C` sit in one domain deliberately. The confirming event happens in the world, `^O`; what the bench reads is the *recall* it triggers, and modelling the trigger at `^C` keeps an unlawful `^O → ^C` ascent out of the listing. `^8` here is associative arrival — the thing that brings the desire back to Mind — not an inference.

**S2–S3 — quantizer and horizon.** Both clocks pass through identical grids, so no asymmetry enters the quotient. The horizon threshold carries the 24-hour floor as a literal; a running bench recomputes it as 3× the rolling median and holds the floor underneath. `action=no_read`, not a large number, because a confirmation past the horizon is base rate.

**S4–S5 — ratio and band guard.** Under CAS-Ohm (Chapter 4.2) flow through a fixed resistance is drive divided by resistance, so the constant is structurally a fixed divider in the readout path — a unit convention realized as a component, which is the honest way to draw it. `Monitor` is a two-threshold comparator: OUT-OF-BAND-LOW routes to the re-spec fuse, OUT-OF-BAND-HIGH terminates calibration.

**S6–S8 — ledger, fuse, schedule.** The lowpass over three operations is why one bad reading cannot redirect a campaign while a genuine trend still passes. `block_until_decomposed` names the only lawful path past the fuse — §23.3 or §23.4 — with invariant S4 stopping that becoming a loophole. `D1` enforces descent from the Evaluative readout into the Operational next-cast spec, and the oscillator is gated by the band guard, so the schedule stops firing the moment the reading leaves the readable window.

[[FIGURE 23-D: Full schematic with reference designators. Intake at left into FLT1/FLT2 (quantizers, grid 5.0); F1 horizon fuse with a downward NO-READ branch; R1, a fixed 3.0 ohm-c resistor labelled “tau = 1/3”; M1 band guard drawn as a two-threshold comparator with four exits; F2 re-spec fuse in series on the RE-SPEC exit, marked “A = 9, block_until_decomposed”; FLT3 lowpass (tau = 3 operations) to the ledger output; D1 domain diode E to O before next_op_spec; OSC1 along the bottom, gated from M1 and wired back to the intake. TP1–TP4 flags at q_conf, eta, requirement, f_ledger.]]

---

### Parameter and BOM Table

Every value is a design choice made in this book, not a measurement.

| Ref | Setting | Why | Failure at other values |
|---|---|---|---|
| FLT1/2 quantizer | grid = 5 min | Finer than `^4` bins, coarser than noticing | 1 min: coprime blow-up. 30 min: overdrive reads ordinary |
| F1 horizon fuse | 3 × median, floor 24 h | Passes slow circuits, excludes base rate | Short: live circuits declared dead. Long: all "confirms" |
| R1 fixed resistor | R = 3.0 Ω_c | Realizes `τ = 1/3` as a divider | Rescales every entry, changes no comparison |
| M1 band guard | η ∈ [0.333, 3.000] | Maps to `A` ∈ [1, 9], the readable window | No lower bound: re-spec reads as amplifier work |
| Amplifier ceiling | β ≤ 4.0, one step per op | Chapter 3.3 device range | `A` as β specifies a device that does not exist |
| F2 re-spec fuse | `A` = 9 | Head of a geometric series | Higher: unconvergeable campaigns stay open |
| FLT3 ledger lowpass | τ = 3 operations | Minimum for a believable trend | 1 op: one bad clock redirects the campaign |
| Convergence | `ρ` ≤ 0.6 | Reaches DRIVE in one step from 9 | `ρ` ≥ 1.0 sustained is divergence |
| Coupling `k` | 0.05 / 0.15 / 0.35 / 0.60 | Set by shared Drive and symbols (§9.3) | Ignored: campaigns collapse together |
| Concurrency | `k(N − 1)` ≤ 0.3 | Holds derating ≥ 0.7 | Past 0.5 the model is invalid — shed |
| OSC1 schedule | period = 72 h | One horizon plus `^5` recharge (§7.3) | Shorter: confirmations unattributable |
| Timing dial | 1.0 | No mechanism claimed (§23.5) | As measured: confounded with `^1` Mind |

[[FIGURE 23-E: Assembly drawing — CCB-CAL board layout with test-point callouts and a BOM box. Intake at the left edge, next_op_spec at the right; components in signal order FLT1/FLT2, F1, R1, M1, F2, FLT3, D1, with OSC1 along the lower edge feeding back to the intake. TP1–TP4 flags with leader lines. Boxed BOM lower right listing all nine designators with their settings. Corner panel reproduces the band strip ACT / CLOSE / DRIVE / RE-SPEC with eta edges 3, 1, 1/3.]]

---

### Worked Example — Campaign C-7, Career Change

Prime desire, present tense per §13.6: *"I hold a paid position doing X."* Board: CCB-D. Drive: F5 Agency with F2 Wisdom. Operations spaced 72 hours.

| Op | Board | `t_op` | `t_conf` | η | `η × 1/3` | `(a, b)` | `A` | `ρ` | Band |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CCB-D | 30 | 90 | 1/3 | 1/9 | (1, 9) | 9.0 | — | RE-SPEC |
| S1 | CCB-SELF | 20 | 20 | 1 | 1/3 | (1, 3) | 3.0 | — | DRIVE |
| 2 | CCB-D | 30 | 30 | 1 | 1/3 | (1, 3) | 3.0 | 0.33 | DRIVE |
| 3 | CCB-D | 30 | 10 | 3 | 1/1 | (1, 1) | 1.0 | 0.33 | ACT |
| 4 | CCB-D | 30 | 5 | 6 | 2 | — | 0.5 | — | OUT-OF-BAND |

**Operation 1.** `A = 3 × 90/30 = 9.0`. The fuse blows on the boundary. Decompose (§23.3) or re-route (§23.4); the operator decomposes because it is cheaper.

**Sub-operation S1.** A0 re-authentication with `^6^C_{F6}|A` decomposition surfaces a blocker in the operator's own `^5`: a visceral aversion to being visible and judged, `^3^E_{F4}|f`. Self-directed board, low resistance: `η = 1`, `A = 3.0`, cleared in one operation. Note what the bench did *not* do — it never named the blocker. It said the prime target's number was wrong for the target as stated.

**Operation 2.** Same cast, blocker cleared: `η = 1`, `A = 3.0`, `ρ = 3.0/9.0 = 0.33`. Delivery `φ = 1/3` — a third of the intended 9× landed, which is 3×: real, short of design. **The amplifier was never touched.** β stayed at its Chapter 13 setting; resistance fell.

**Operation 3.** `η = 3`, `result = 1/1`, `A = 1.0`, `ρ = 0.33` again, `φ = 1.0`. `A = 1` is terminal: present strength suffices.

**Operation 4.** Raw, `η = 7.5` and the pair is (5, 2) — "twice as strong, five more casts." Gridded, `η = 6` and `A = 0.5`. Both are off the instrument, the band guard fires, and the correct action is not a fifth operation. It is the practical act the campaign was always about: send the application, make the call, be in the room.

**Totals.** 140 minutes of operation across roughly twelve days. `A` runs 9 → 3 → 1, `ρ` flat at 0.33, terminal at operation three.

---

### Test Points

| TP | Node | Expected |
|---|---|---|
| **TP1** | `q_conf` | Quantized `t_conf` inside the horizon. A reading *at* `t_H` is a NO-READ, not a slow confirmation — they look identical and must not be logged the same way |
| **TP2** | `eta` | 0.333 – 3.000. Below, the re-spec fuse is next; above, stop calibrating |
| **TP3** | `requirement` | `A ≤ 1` act, `< 3` close, `< 9` drive, `≥ 9` blows F2. If `a > 3`, read TP3 alone |
| **TP4** | `f_ledger` | `ρ ≤ 0.6` per step across three operations. Flat near 1.0 is the abort signal, and it arrives before TP3 reaches 9 |

Read them in order: is the measurement admissible, is it in band, what is the requirement, what is the trend. TP4 warns you early. TP3 stops you.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Coprime blow-up** | Pair reduced unquantized | `b` in the hundreds with `a > 3` | Quantize to 5 min; act on `A` |
| **Horizon creep** | Window widened until something matches | Every operation "confirms"; median `t_conf` climbs | Fix `t_H` before the cast; log NO-READ |
| **Attribution collision** | Second operation fired inside the first's horizon | A confirmation two campaigns can claim | Mark `AMBIGUOUS`; keep 72-hour spacing |
| **Unmodelled concurrency** | Related operations live at once, `k` ignored | Every `A` doubling in a week; each cast inspects clean | Compute `k(N − 1)`; shed until ≤ 0.3 |
| **`A` written as β** | Requirement read as an amplifier setting | A listing specifying β = 9 on a 4.0 device | Section 13.5's five levers; recruit instead |
| **Tautological ledger** | Flat absolute-target column read as convergence | A column that never moves | Delete it. Track `ρ` only |
| **Ledger laundering** | Blown fuse routed around by re-wording the target | `A` "resets" while the desire did not change | S4: change domain or object, never wording |

---

### What This Chapter Established

- **`τ = 1/3` is a scale factor, not a derivation.** Nothing produces 1/3 from φ or π. Change `τ` and every comparison survives untouched — the equation carries an ordering, not a physical quantity.
- **The measurement was never the fragile part — the reduction was.** `A` moved 9.00 → 8.52 while the pair swung from (1, 9) to (31, 264). Quantize on a 5-minute grid; if `a > 3`, act on `A` alone.
- **Both limits run off the instrument.** As `t_conf → ∞` the bench returns NO-READ behind a horizon — `β=∞` is an idealization the validator rejects, and no finite substitute exists because the input is missing, not large. As `t_conf → 0` the reduction degenerates above η = 3 and the reading is OUT-OF-BAND-HIGH.
- **Campaign demand compounds multiplicatively**, so `A ≥ 9` is the head of a geometric series. `A` multiplies delivered current and is never a β setting: the device range ends at 4.0, β steps one increment per operation, and the rest comes from the other four levers or from recruitment.
- **The only campaign diagnostic is `ρ = A_next / A_current`**, threshold 0.6, believed only after three operations. The absolute-target column is an identity that holds for any campaign, converging or not.
- **Concurrent operations interfere through the shared substrate**, derating as `1 − k(N − 1)`. Three coupled operations turned a comfortable cast (`A = 3`) into a re-spec reading (`A = 10`) with nothing wrong with the cast. Hold `k(N − 1) ≤ 0.3`; past 0.5, shed rather than compute.
- **Re-routing lowers the maximum per-stage demand, not the total.** Hops cascade multiplicatively and obey the diode chain — descent only, `^O × ^P` invalid. The 12-against-36 comparison is retrospective; the promise is that every stage lands inside the feasible band.
- **The timing dial defaults to 1.0.** No celestial mechanism is asserted; a fixed calendar earns its place as a watchdog timer, and §23.5 gives the falsification and the confound you must name if you claim more.

---

### Exercises

**23.1** An operation logs `t_op = 45`, `t_conf = 240`. Compute η, the reduced pair `(a, b)`, and `A`. Which band? Which response would you take first, and why that one?

**23.2** Take `t_op = 27`, `t_conf = 64`. Compute the pair raw and on the 5-minute grid, then `A` both ways. State in one sentence what the comparison demonstrates about which quantity to act on.

**23.3** A campaign reads `A` = 12.0, 9.6, 7.7, 6.2 across four operations. Compute `ρ` at each step. Converging by the chapter's threshold? How many further operations at this `ρ` before it reaches ACT, and would you keep casting?

**23.4** An operator runs four live operations: two on F5 Agency sharing a sigil alphabet, one on F2 Wisdom with no shared symbols, one on F4 Connection targeting the same person as one of the F5 operations. Assign `k` to each pairing, compute `k(N − 1)` for the full load, and state which operations you would shed and in what order.

**23.5** An isolated cast would read η = 0.75. The operator runs it at `N = 3` with `k = 0.35`. Compute `η_effective`, the effective `t_conf` for `t_op = 40` on the 5-minute grid, and the resulting `A`. Does the band change?

**23.6** A colleague shows you a ledger whose absolute-target column reads 9.0 for six consecutive operations and calls it proof the campaign is on track. Write the two-sentence reply, and name the column you would ask to see instead.

*(Answers in **Appendix H**, worked in full. Every parameter here is a design choice; the arithmetic is arithmetic, and the model behind it is a structural analogy, not a measured law.)*
