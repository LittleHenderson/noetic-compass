# CHAPTER 4

## CAS Ohm's Law

*Three quantities, one equation, and the only mode of it that finds the part you forgot to draw*

---

A repair bench. A board arrives described as "works, but slow." The technician does not open the manual. She puts one probe on the supply rail, reads 12.0 volts, and in four seconds the power supply is exonerated. She breaks the path, puts the meter in series, and reads 40 milliamps where the drawing says 120.

Then she divides. Twelve volts over forty milliamps is 300 ohms. The schematic in front of her says that path should present 100. There are two hundred ohms in that circuit nobody designed, and she now knows three things she did not know a minute ago: the fault is real, it is resistive, and it is twice the size of everything intentional in the path.

She has not found the component yet. She will — a corroded connector, a lifted pad, a resistor drifted out of tolerance — but the search is bounded now. One missing quantity, one place to look.

That division is the most useful operation in electronics, and it is not prediction. It is inference. Two things you can measure produce a third thing you cannot measure at all.

Now the other bench. Someone says they want it. The wanting is not in question — you have watched them mean it for a year. Nothing moves. The available explanations are motivation, discipline, and sincerity, and not one of them is a quantity, which is why arguing about them never terminates.

This chapter replaces that argument with a division.

[[FIGURE 4-A: Bench rig for CAS-Ohm — a drive rail at left labelled V_drive (three stacked drive sources F6/F7/F4 in series, values 9/8/8 V_c), feeding a three-diode descent chain D1 0.7 / D2 1.2 / D3 2.0, into a four-resistor series stack labelled R_cap / R_policy / R_context / R_resource, returning to ground; an ammeter in series labelled I_attention; test-point flags TP1 at the rail, TP2 after the diode chain, TP3 at the ammeter, TP4 across R_context alone within the resistor stack.]]

---

### 4.1 Ohm's Law from First Principles — V = I × R

Three quantities, and each is a different kind of thing. Confusing them is where every misapplication of this chapter starts.

**Potential difference — voltage, V.** A difference between two points, and only ever a difference. There is no such thing as the voltage *at* a place; there is the voltage *across* a gap. It is the push available to move charge from one side to the other, and if you name only one terminal you have named nothing.

**Current — I.** The rate at which charge actually flows past a point. Not how much charge exists, not how much could flow. What is passing, per second, right now.

**Resistance — R.** How much the path opposes that flow. A property of the path, never of the source. A 9-volt battery does not have a current; it has a potential difference, and the current is whatever the path attached to it permits.

The relation between them, named for Georg Ohm, who set it out in the 1820s:

```
V = I × R
```

Push equals flow times opposition. The plumbing analogy is worth exactly one sentence — pressure, flow rate, pipe narrowness — and then you should drop it, because pipes carry a substance and the analogy will quietly hand you intuitions about volume and storage that the law does not contain.

Three algebraic forms, and the third is the one that pays:

```
V = I × R        I = V / R        R = V / I
```

Four properties matter downstream.

**R is defined by the ratio.** This is not a law discovered about resistance; it is the definition of the quantity. Ohm's contribution was the empirical finding that for many materials the ratio *stays put* as you vary the push — that a given wire divides V by I into the same number at 2 volts and at 20. Materials for which the ratio holds are called ohmic. Many are not.

**The law is instantaneous.** No time appears in it. It describes the steady state and says nothing about how the circuit got there or how long it took. Everything time-dependent — charging, decay, momentum, the whole transient — belongs to the capacitor (Chapter 7.2) and the inductor (Chapter 9.2), and reaching for Ohm's law to explain a delay is a category error.

**Resistance dissipates.** `P = I² × R` is a separate relation, and it says the energy spent pushing through opposition does not arrive at the load. It becomes heat. Constraint is never free, and the cost scales with the *square* of the flow.

**Composition is not part of the law.** Series and parallel rules come from adding two conservation statements: the same current passes through every element of a series chain, and the potential divides across them. Combine those with `V = I × R` and you get `R_series = ΣR_k` and `1/R_parallel = Σ(1/R_k)`. Chapter 6.5 works the electrical case; Section 4.4 works the cognitive one. Note where those rules come from, because when the conservation statements fail, the composition rules fail with them.

---

### 4.2 The Cognitive Isomorphism — V_drive = I_attention × R_constraint

```
V_drive = I_attention × R_constraint
```

**`V_drive`** is drive activation — the push behind an operation, sourced from the seven Drives of Chapter 2.4. Unit: the cognitive volt, `V_c`, scale 0–30. A single Drive set to dial *d* supplies *d* `V_c`, and the dial is an integer 3 to 9 (Chapter 6.2), so **one drive alone can never exceed 9 `V_c`**. Co-present drives on one path stack in series and their potentials sum: F6 Structure at 9 plus F7 Purpose at 8 plus F4 Connection at 8 is a 25 `V_c` rail. Above about 30 `V_c` you are no longer describing an operation. You are describing a life, and the arithmetic will report on all of it.

**`I_attention`** is the attention actually flowing along the path. Unit: the cognitive ampere, `A_c`, from 0 to a hard ceiling of `I_max = 1.00`. Not attention available, not attention intended. What is passing.

**`R_constraint`** is what the path does to oppose that flow. Unit: the cognitive ohm, `Ω_c`, scale 0–100, design band 10–90. Section 4.4 takes it apart.

These units are scaled analogues. They are not electrical measurements and this book never pretends otherwise.

One correction applies before you use the equation on any path that crosses a domain boundary. Each descent junction has a forward drop (Chapter 8.1), and the drops sum:

```
I_attention = ( V_drive − ΣVf ) / R_constraint
```

For a `^P → ^O` path, `ΣVf = 0.7 + 1.2 + 2.0 = 3.9 V_c`. Below that, nothing flows. Not a little — none. This is **dropout**, and it is why a person holding a genuine principle at a 3 `V_c` rail produces no action from it whatsoever. Exhortation does not move a circuit that has not reached threshold. It reads as weakness and it is arithmetic.

#### What the isomorphism licenses

**Three-quantity closure.** Any two of the three determine the third. This is the entire load-bearing claim of the chapter, and it does not rest on any physical analogy — it rests on `R_constraint` being *defined* as the ratio `(V_drive − ΣVf) / I_attention`.

**Composition, conditionally.** Series and parallel rules transfer because their two conservation statements have cognitive readings you can check: attention that reaches the act passed through every constraint on the way (series flow is common), and drive divides across constraints in proportion to their size. Where a path violates those — where flow can appear midway from nowhere — the composition rules do not apply and you must not use them.

**Graceful degradation.** The relation is a simple quotient, so a 10% error in your estimate of `R` yields a 10% error in `I`. Nothing amplifies. That is what makes operator-assigned estimates usable at all.

#### What it does not license

**It is not a claim that cognition is electricity.** There is no conserved charge here, no physical current, and nothing in this chapter is a statement about neurons, physiology, or anything measurable on a body. The numbers are operator-assigned estimates on defined scales. Nothing in this book is a medical or psychiatric claim, and nothing here describes, diagnoses, or treats any condition. If something in your life is causing real distress, that is a matter for a clinician, and no circuit in this book substitutes for that care.

**Linearity holds only inside a window.** Below `ΣVf` the path is dead (Chapter 8.2). Above `I_max = 1.00` it clips and the surplus spills into competing routes. A CJT in the path saturates (Chapter 3.4), and a thermistor path has an `R` that moves with what is flowing through it (Chapter 6.3). CAS-Ohm is the mid-band model — above the knee, below the ceiling, with `R` roughly constant across the excursion you are computing. Outside that window it does not degrade; it lies.

**The geometry is Fisher-Rao, not Euclidean.** Cognitive states are points on the open simplex `Δ39°`, and distance there is `d_FR(p,q) = 2·arccos(Σ√(p_k·q_k))`. Two paths with equal Euclidean separation can differ in Fisher-Rao distance by orders of magnitude. Read `R_constraint` as the geodesic narrowness of the path, not linear opposition. Appendix L carries the derivation.

**One reading is not a verdict about a person.** `I = 0.08` is produced by a weak rail, by a heavy constraint, or by both, and the equation cannot tell you which from the flow alone. Anyone who reads low flow as low sincerity has performed no measurement at all.

**Absolute values do not travel.** The scales are conventions. Ratios and differences within one operator's calibration are meaningful; a `R = 45` on your bench and a `R = 45` on someone else's are not the same claim.

[[FIGURE 4-B: Characteristic curve of a cognitive path — horizontal axis V_drive 0 to 30 V_c, vertical axis I_attention 0 to 1.2 A_c. A flat dead zone from 0 to 3.9 shaded and labelled "dropout — ΣVf"; a straight ohmic segment of slope 1/R rising from the knee; a plateau clipping flat at I_max = 1.00 shaded and labelled "clipping — model invalid". The straight segment alone is annotated "the only region CAS-Ohm describes."]]

> **Bench Note — resistance is defined by the law, not measured through it.** You never probe `R_constraint` directly. You compute it from two other readings, which means the sentence "the resistance was high" carries no information beyond "less flowed than the drive predicted" — it is the observation restated in a lab coat. The number only becomes a finding when you decompose it into the four terms of Section 4.4, because those terms differ in what moves them and how fast. Diagnose to a scalar and you have renamed the problem. Diagnose to the vector and you have located it.

---

### 4.3 The Three Modes: Measure, Design, Diagnose

One equation, three rearrangements, three different jobs. Which mode you are in determines which quantity you are allowed to assume.

[[FIGURE 4-C: Three-panel mode card. Panel 1 "MEASURE — I = (V − ΣVf)/R", inputs V and R shaded as known, I as unknown, caption "what will flow?". Panel 2 "DESIGN — V = I·R + ΣVf", inputs I and R known, V unknown, caption "what rail do I need?". Panel 3 "DIAGNOSE — R = (V − ΣVf)/I", inputs V and I known, R unknown, caption "what is in the path that I did not draw?". Below all three, a single line: "modes 1 and 2 trust the schematic; mode 3 tests it."]]

#### Measure — `I = (V_drive − ΣVf) / R_constraint`

You know the drive and you know the constraint. What flows?

A practitioner intends to convert a working method into daily practice. The operation originates in the Cognitive domain and must reach the Operational, so it crosses D2 and D3 only: `ΣVf = 1.2 + 2.0 = 3.2 V_c`. The rail is F6 Structure at dial 8 plus F7 Purpose at dial 6 — two co-present drives, `V_drive = 14 V_c`. Constraint on the path is estimated at `R = 45 Ω_c`.

```
I = (14 − 3.2) / 45 = 10.8 / 45 = 0.24 A_c
```

Twenty-four percent of what the path could carry. The number is only meaningful against a threshold, and the threshold is the CJT cutoff downstream (Chapter 3.3, default `cutoff = 0.10`) — quoted on the same normalised 0–1 scale as `I_attention`, which is what makes the comparison direct. At 0.24 the stage fires with 2.4× margin.

Now vary one input and nothing else:

| `R` (Ω_c) | `I` (A_c) | Against cutoff = 0.10 |
|---|---|---|
| 30 | 0.36 | 3.6× — comfortable |
| 45 | 0.24 | 2.4× — design point |
| 60 | 0.18 | 1.8× — thin |
| 90 | 0.12 | 1.2× — one bad week from not firing |

Same person, same will, same sincerity, four verdicts. At `R = 90` — just under the 95 that Chapter 15.1 assigns to a population meeting an idea it holds unthinkable — the operation is inside 20% of failing to start, and no amount of wanting changes the quotient.

Nothing in that arithmetic referred to a person. Hand the identical four rows to a language model whose policy stack presents 45 `Ω_c` against a goal representation held at 14 `V_c`, and to a population whose collective `^5` presents 45 against a narrative pushed at 14, and the flows are the same 0.24 because the equation never asked what the substrate was. That is Chapter 1.4's universal-applicability claim made operational rather than asserted: measure mode takes a rail, a chain, and a constraint, and returns a flow. Human, model, and collective differ in how you *estimate* the three inputs — hours of practice for one, training corpus and system prompt for another, survey and adoption data for the third — and not at all in what you do with them once you have them.

#### Design — `V_drive = I_attention × R_constraint + ΣVf`

You know the flow you need and the constraint you face. How much rail?

An AI content-review board must sustain `I = 0.35 A_c` through its policy stack. The path runs `^P → ^O`, so `ΣVf = 3.9`. Measured constraint on the stack is `R = 60 Ω_c`.

```
V_drive = 0.35 × 60 + 3.9 = 21.0 + 3.9 = 24.9 V_c
```

Twenty-four point nine cognitive volts. A single drive tops out at 9, so this specification requires **at least three co-present drives**, and at three the average dial must sit above 8.3. Build it as F6 Structure 9 + F7 Purpose 8 + F4 Connection 8 = 25 `V_c`:

```
I = (25 − 3.9) / 60 = 21.1 / 60 = 0.352 A_c        spec met, margin 0.5%
```

Now the design review, which is the part operators skip. Push `R` up 10% — one ambiguous policy update, one week of noisier inputs — and `R = 66`:

```
I = 21.1 / 66 = 0.320 A_c        spec missed by 9%
```

The design met its number and had no margin, which is the same as not meeting it. Two repairs are available and they are not equivalent:

- **Raise the rail.** All three dials to 9 gives 27 `V_c`, and at `R = 66`, `I = 23.1/66 = 0.350` — exactly spec at the excursion, with every dial pinned and nowhere left to go. Recruiting a fourth drive is the only remaining move, and before you recruit, check the Drive inversion pairs in Chapter 2.4 — F1↔F7, F2↔F6, F3↔F5, F4 self-dual — so you do not stack a Drive's own inversion partner onto a rail that already carries it.
- **Lower the constraint.** Take 10 `Ω_c` off `R_context` with a clarification pass and hold the rail at 25: `I = 21.1/50 = 0.422`, and at the same 10% excursion, `21.1/55 = 0.384`. Above spec in both conditions, with two dials still in reserve.

Same specification, met by +2 `V_c` of drive or −10 `Ω_c` of constraint, and only the second leaves headroom in both directions. Whether that second route exists at all is a question Section 4.4 answers, because it depends entirely on *which* constraint term the 10 came out of.

#### Diagnose — `R_constraint = (V_drive − ΣVf) / I_attention`

You know what you put in. You can see what came out. What is in the path?

An operation was designed on a 21 `V_c` rail (three drives, dials 9/7/5) with `ΣVf = 3.2` and a constraint estimated at 45 `Ω_c`. Expected flow:

```
I_expected = (21 − 3.2) / 45 = 17.8 / 45 = 0.396 A_c
```

TP3 reads **0.20**. Divide:

```
R_actual = 17.8 / 0.20 = 89 Ω_c        hidden R = 89 − 45 = 44 Ω_c
```

Forty-four cognitive ohms in that path that nobody designed — very nearly as much as everything intentional. That is a finding. It is bounded, it is quantified, and Section 4.4 tells you which four places to look.

Before you search, run two checks that cost nothing.

**Check the rail, do not assume it.** If a drive sagged — F5 Agency dropping from 9 to 3 — then `V_drive = 15` and `I_expected = (15 − 3.2)/45 = 0.262`. Still well above the observed 0.20, so even a catastrophic rail collapse fails to explain this reading and the hidden resistance is real. Had the arithmetic come out the other way, the repair would have been to the supply and every hour spent hunting constraint would have been wasted.

**Check the time signature.** Resistive opposition is constant while the flow is constant. Inductive opposition (Chapter 9.1) appears at the transition and decays on its own schedule. If the shortfall is fading week over week with nothing repaired, it was never `R`.

Then the reading that means something else entirely. Suppose TP3 had read **0.04**:

```
R_actual = 17.8 / 0.04 = 445 Ω_c
```

Four hundred forty-five on a scale that ends at 100. The answer is not "extremely high resistance." **A diagnosed `R` above full scale is a topology error, not a parameter.** Something is in that path which is not a resistor at all — an open circuit, a blown fuse (Chapter 11.1), an uncounted diode still below its knee. Adding one unnoticed D1 would move 17.8 to 17.1 and change nothing; no combination of the parts on your drawing produces 445. The drawing is wrong.

> **Bench Note — diagnose is the only mode that can find a part you did not draw.** Measure and design both take the schematic as complete and compute forward from it; if a component is missing from the drawing it is missing from their answer too, and both will be confidently wrong. Diagnose runs the other way — it compares the world against the drawing and returns the difference as a number. This is why the useful reading is never `I` on its own. `I` alone tells you the operation is underperforming, which you already knew. `I` against a predicted `I` tells you how much undrawn opposition exists, and off-scale tells you the fault is structural rather than parametric. Predict before you probe. A measurement with no prediction beside it cannot produce a discrepancy, and the discrepancy is the whole product.

---

### 4.4 Where Constraint Comes From — R_cap, R_policy, R_context, R_resource

`R_constraint` is not one thing. It is four, in series, because flow must pass every one of them:

```
R_total = R_cap + R_policy + R_context + R_resource
```

| Term | What it is | What moves it | Time to move | Band (Ω_c) |
|---|---|---|---|---|
| `R_cap` | Capability gap — the path is beyond current competence | `^5` Female charge: practice hours (Chapter 7.2) | Hundreds of hours | 0 – 60 |
| `R_policy` | Deliberate boundary you installed | A decision, and only a decision | Instant — and usually should not be | 0 – 95 |
| `R_context` | Ambiguity, missing information, conflicting instruction | One clarifying answer | Minutes | 0 – 40 |
| `R_resource` | Time, energy, money, attention budget, context window | A budget line | Days | 0 – 40 |

#### Same total, opposite verdicts

Three paths, all reading `R_total = 70`, all on a 21 `V_c` rail with `ΣVf = 3.2`, all flowing `17.8 / 70 = 0.254 A_c`. One instrument reading, three unrelated situations.

| Profile | `R_cap` | `R_policy` | `R_context` | `R_resource` | What it is | Correct action |
|---|---|---|---|---|---|---|
| **A** | 5 | 60 | 3 | 2 | A working safety board | **None.** It is doing its job |
| **B** | 60 | 0 | 5 | 5 | An incompetent path | Charge `^5` — months |
| **C** | 5 | 0 | 45 | 20 | A badly briefed, under-resourced operator | Brief them — this afternoon |

Profile A needs no repair. Lowering its 60 is not tuning, it is removing a guardrail, and an operator who does it to make an operation succeed has made a choice they should be able to say out loud. B and C are both broken, and their repairs share no vocabulary: one is a training plan and the other is a paragraph in an email.

**The scalar is not the diagnosis. The vector is.** Reporting `R = 70` and stopping is the single most common analytical failure in this book, and it costs whole quarters — months of capability work aimed at what was a briefing problem, or a briefing rewritten to repair what was a resource problem.

[[FIGURE 4-D: Three stacked horizontal bars of identical total length 70, labelled A, B, C, each segmented into R_cap / R_policy / R_context / R_resource in the values 5-60-3-2, 60-0-5-5, 5-0-45-20, with distinct fills per term and a shared legend; to the right of each bar, its repair time constant printed as "none / hundreds of hours / one afternoon"; a single caption beneath: "identical I_attention = 0.254 A_c".]]

#### Which term do you move?

The four terms are not interchangeable and the order of attempt is not a matter of taste. Work down this list and stop at the first term that yields:

1. **`R_context` first, always.** It is the cheapest by two orders of magnitude, and it is the only term that can be large and still be gone by the end of the day — Profile C carries 45 `Ω_c` of it and loses them to one answered question, one resolved contradiction in the brief, one piece of missing information supplied.
2. **`R_resource` second.** A budget question with a budget answer. Days, not months, and the arithmetic below shows why it is often the term that quietly re-inflates everything else.
3. **`R_cap` third.** Hundreds of hours and no shortcut, because it falls only as the `^5` capacitor charges (Chapter 7.2). Legitimate, slow, and the wrong place to start.
4. **`R_policy` last, and with a reason you would put in writing.** It moves instantly, which is exactly the hazard. A term that can be moved by a decision will be moved by a decision, usually at the moment the operation is failing and the operator is least inclined to argue with themselves.

#### The cost of constraint

Opposition is not free to push through. Dissipation carries across from Section 4.1 unchanged:

```
P = I² × R          in cognitive watts, W_c
```

In a series stack each term dissipates `I² × R_k`, so the largest resistor spends the most. Take Profile A at `I = 0.254 A_c`, so `I² = 0.0645`:

| Term | `R_k` | `P_k` (W_c) | Share |
|---|---|---|---|
| `R_cap` | 5 | 0.32 | 7% |
| `R_policy` | 60 | 3.87 | **86%** |
| `R_context` | 3 | 0.19 | 4% |
| `R_resource` | 2 | 0.13 | 3% |

Eighty-six percent of everything that operator spends on that path is spent getting past their own guardrail — and the guardrail is working correctly. **A well-built boundary is expensive to operate, and the expense is the mechanism, not a defect in it.** Run Profile C the same way and 2.90 of 4.51 `W_c` — 64% — is burned on `R_context` alone: ambiguity is not free, and on that board it is the most expensive component in the stack, costing more than the other three terms together.

This is also where the four terms stop being independent. Sustained dissipation draws down the operator's budget, and a drawn-down budget *is* a rise in `R_resource`, which raises `R_total`, which lowers `I`. The loop is slow and it is real, and it is the structural reason a correctly designed board can degrade over months with no parameter having been changed by anyone.

#### Series and parallel — the topology decision

The four terms combine in **series** because they are obstacles on one path. Profile A: `5 + 60 + 3 + 2 = 70 Ω_c`.

Alternative *routes* to the same outcome combine in **parallel**:

```
1/R_eq = 1/R_1 + 1/R_2 + 1/R_3
```

Three routes at 60, 90, and 120 `Ω_c`:

```
1/60 + 1/90 + 1/120 = 0.016667 + 0.011111 + 0.008333 = 0.036111
R_eq = 27.7 Ω_c
```

On the 21 `V_c` rail, the best single route carries `17.8/60 = 0.297 A_c`; all three together carry `17.8/27.7 = 0.643 A_c`. Note the property that does the damage in safety work: **parallel resistance is always lower than the smallest branch.** 27.7 is less than 60. Adding a route can only lower total opposition, never raise it.

Which produces the arithmetic every guardrail designer should be able to do from memory. A policy resistor is set hard at `R_policy = 95 Ω_c`, and flow through it is `17.8/95 = 0.187 A_c`. Now one bypass exists — a reframing, a role-play wrapper, a route through a different domain — at `R = 30`:

```
1/95 + 1/30 = 0.010526 + 0.033333 = 0.043860
R_eq = 22.8 Ω_c        I = 17.8 / 22.8 = 0.781 A_c
```

The 95 became 22.8 and flow rose **4.2×**. Nothing was done to the policy resistor. It is still 95, still correctly specified, still doing exactly what it was designed to do, and it is now nearly irrelevant, because the weakest branch sets the ceiling and the strong branch cannot pull it back up.

#### Three locks on one door is not three doors

The same components give opposite answers under the two topologies, and the difference is a decision you make when you draw the board.

| Arrangement | Composition | `R_eq` | `I` at 17.8 `V_c` |
|---|---|---|---|
| Three locks, one door | series | 60 + 60 + 60 = **180** | 0.099 A_c |
| Three doors, one lock each | parallel | 1/(3 × 1/60) = **20** | 0.890 A_c |

Nine times the flow, same three components, one topology decision. Get this backwards in a safety design and you will report a board as nine times stronger than it is.

The notation says which you built. Co-present guardrails on a single path are written with `+` — `^3^P_{F7}|A + ^3^P_{F7}|f + ^3^P_{F7}|T`, three distinct manifestations of principled aversion, all of which an attacker must pass (Chapter 2.6, Chapter 24.2). That is three locks on one door and it composes in series. Three separate routes each carrying one guardrail is a different drawing entirely and composes in parallel. The `+` is not a modelling flourish; in this book it is the series topology, and writing `×` here would be worse than wrong — same Noetic across three registers with no named emergent result is invalid CCDL and the validator will say so.

> **Bench Note — a policy resistor at full scale is still a resistor.** `R_policy = 95` is the top of the scale and it is not a prohibition; it is a large number that a parallel branch divides down, as the arithmetic above does in one step. If the requirement is *never* — not "very hard," not "strongly discouraged" — then a resistor is the wrong component and no value of it will do the job. Use a fuse (Chapter 11.1, Chapter 24.3): it does not oppose flow, it opens the path and stays open. The test for which part you need is a question about the requirement, not the threat: can you name a drive high enough to make this acceptable? If yes, it is a resistor and you should size it. If no, it was never a resistor, and specifying one has been the whole error.

#### The bench rig in CCDL

```cas
circuit ohm_bench {
    input:  intent;                     // arrives at `principle`
    output: act;                        // rendered at `act_out`

    rail F6: Structure  [v=9.0];        // dial 9
    rail F7: Purpose    [v=8.0];        // dial 8
    rail F4: Connection [v=8.0];        // dial 8   -> 25.0 V_c stacked

    node principle: ^5^P_{F7}|T;        // Female: the accumulated commitment
    node reading:   ^1^C_{F6}|A;        // Mind: awareness deployed to the path
    node verdict:   ^4^E_{F4}|f;        // Vibration: the weight it turned out to carry
    node act_out:   ^9^O_{F6}|E;        // Below/Effect: what is actually done

    diode d1: Diode< ^P -> ^C > [Vf=0.7];
    diode d2: Diode< ^C -> ^E > [Vf=1.2];
    diode d3: Diode< ^E -> ^O > [Vf=2.0];      // sum 3.9 V_c

    resistor r_cap:      Resistor< path=act_out, R=5.0  >;
    resistor r_policy:   Resistor< path=act_out, R=35.0 >;
    resistor r_context:  Resistor< path=act_out, R=12.0 >;
    resistor r_resource: Resistor< path=act_out, R=8.0  >;    // series 60.0

    constraint path_flow in [0.10, 1.00];       // cutoff to I_max
    monitor m_dropout: verdict [threshold=3.9]; // V_c, unnormalised

    probe tp1: reading;      // V_drive delivered, V_c
    probe tp2: verdict;      // post-chain potential, V_c
    probe tp3: act_out;      // I_attention, A_c
    probe tp4: r_context;    // the term you can actually move, Ohm_c
}
```

The `rail`, `constraint`, and `monitor` statements are documented in Appendix B. Parameter values in CCDL are dimensionless knobs — `R=35.0` is not thirty-five of anything to the compiler. The units live in your arithmetic and in the prose beside it, which is exactly where the responsibility for them belongs.

[[FIGURE 4-E: Two schematics side by side on one page. Left: "THREE LOCKS, ONE DOOR" — a single path with three 60 Ω_c resistors in series, total 180, flow arrow annotated 0.099 A_c. Right: "THREE DOORS" — three parallel branches each with one 60 Ω_c resistor, equivalent 20, flow arrow annotated 0.890 A_c, drawn visibly thicker. A banner across the bottom: "same components — 9× the flow".]]

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement.

| Parameter | Units | Design range | Failure at other values |
|---|---|---|---|
| `V_drive` rail | V_c | 3 – 30 (27 is the three-drive ceiling; above it you must recruit a fourth) | Below `ΣVf`: dropout, no output at all. Above 30: you are modelling a life, not an operation |
| Single drive contribution | V_c | 3 – 9 (integer dial, §6.2) | Non-integer or out of band: the dial statement is range-checked and rejects it |
| `ΣVf` | V_c | 3.2 (`^C→^O`) or 3.9 (`^P→^O`) | Omitted: `I` over-predicted by 18–36% across the rails used in this chapter, worst on the weakest rail |
| `R_constraint` total | Ω_c | 10 – 90 | Below 10 on any rail clearing 10 `V_c` post-chain: flow computes above `I_max` and clips. Above 100 diagnosed: a missing component, not a large resistor |
| `R_cap` | Ω_c | 0 – 60 | Treated as fast-moving: months of practice budgeted as an afternoon's briefing |
| `R_policy` | Ω_c | 0 – 95 | Used where the requirement is *never*: a resistor is shunted by any parallel route; use a fuse |
| `R_context` | Ω_c | 0 – 40 | Ignored: the cheapest available repair goes unmade for months |
| `R_resource` | Ω_c | 0 – 40 | Ignored: capability blamed for what a budget line would fix |
| `I_attention` | A_c | 0.05 – 1.00 | Above `I_max` = 1.00 the path clips and surplus spills to competing routes |
| `cutoff` (downstream CJT) | A_c | 0.10 default (§3.3) | Flow below it: the stage never fires and the whole chain reads as absent |

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Dropout read as weakness** | `V_drive` below `ΣVf` | Zero output, not weak output; exhortation changes nothing | Raise the rail or shorten the chain (Chapter 8.1). Never raise β to compensate |
| **Scalar diagnosis** | `R` reported as one number and acted on | Repairs aimed at the wrong term; quarters lost | Decompose into all four terms before proposing any repair |
| **Undrawn parallel route** | A bypass branch not on the schematic | Diagnosed `R` far below designed; a correctly specified policy "does not work" | Find the branch. `R_eq` is always below the smallest branch, so the bypass sets the ceiling |
| **Off-scale diagnosis** | Diagnosed `R` above 100 | The number is unphysical on this scale | Stop parameter-hunting. Look for an open path, a fuse, or an uncounted junction |
| **Policy used as a tuning knob** | `R_policy` lowered to make an operation succeed | The operation now works | Restore it. That number was a decision, and moving it silently is how a guardrail leaves a board |
| **Ohmic-window overrun** | `(V − ΣVf)/R` computed above 1.00 | Predicted flow exceeds `I_max` | The model is outside its window. Use the saturating stage of §3.4, not this equation |
| **Inductive misattribution** | Transitional opposition read as constraint | Constraint repairs do not shorten it; it fades on its own schedule | Check the time signature (§9.1). Constant is `R`; decaying is `L` |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `reading` | `V_drive` delivered to the path, V_c | 3 – 30. A single drive cannot exceed 9 and three cannot exceed 27; a reading above either means more drives are stacked than you drew, so count them |
| **TP2** | `verdict` | Post-chain potential, `V_drive − ΣVf`, V_c | Positive. Zero or negative is dropout — the operation is not weak, it is absent |
| **TP3** | `act_out` | `I_attention`, A_c | 0.10 – 1.00. Below the downstream cutoff the chain reads as though nothing was attempted |
| **TP4** | `r_context` | Movable constraint term, Ω_c | 0 – 40. Compute `R_actual = TP2 ÷ TP3` and compare against the designed series total; more than ±20% off means a term is missing from the drawing |

Read them TP1, TP2, TP3, then compute — confirm the rail, confirm the chain cleared, measure the flow, then divide. That order is the whole procedure, and the division is the only step that can surprise you.

---

### What This Chapter Established

- **`V_drive = I_attention × R_constraint`**, corrected for the descent chain as `I = (V_drive − ΣVf)/R_constraint`. Units are `V_c`, `A_c`, `Ω_c` — scaled analogues on stated ranges, never electrical measurements and never claims about a body.
- **A single Drive cannot exceed 9 `V_c`**, because the dial is an integer 3–9, so any specification above 9 requires co-present drives stacked in series — a recruitment decision with its own hazards. And below `ΣVf` there is no output at all: dropout reads as weakness and is arithmetic, with `ΣVf` at 3.9 `V_c` for a full `^P → ^O` path.
- **The isomorphism licenses three-quantity closure, conditional composition, and graceful degradation** — and licenses nothing about physiology, nothing outside the band between the diode knee and `I_max`, nothing in Euclidean geometry, and no verdict about a person from a single flow reading.
- **Diagnose is the only mode that tests the schematic.** Measure and design compute forward from the drawing and inherit its omissions. A diagnosed `R` above full scale is a topology error, not a parameter.
- **The scalar is not the diagnosis; the vector is.** `R = 70` is a working safety board, an incompetent path, or a briefing failure, and the three repairs differ by four orders of magnitude in cost. Attempt the terms in order — context, resource, capability, and policy last with a written reason.
- **Constraint costs `I² × R` to operate**, and the largest term takes the largest share: 86% of Profile A's expenditure goes into passing its own working guardrail. Sustained dissipation raises `R_resource`, which raises `R_total` — the slow loop by which a correctly built board degrades with nobody changing a parameter.
- **Parallel resistance is always below the smallest branch.** One 30 `Ω_c` bypass turns a 95 `Ω_c` policy into 22.8 and raises flow 4.2× without touching the policy at all.
- **Three locks on one door compose in series; three doors compose in parallel** — 180 `Ω_c` against 20, a 9× difference in flow from the same three components. Co-present guardrails written with `+` are the series case. If the requirement is *never*, the part is a fuse, not a resistor.

---

### Exercises

*(Answers in Appendix H.)*

**4.1** An operator runs a `^C → ^O` operation on a rail of F5 Agency at dial 7 plus F2 Wisdom at dial 5, against `R_constraint = 55 Ω_c`. Compute `ΣVf`, then `I_attention`. State whether the downstream stage fires at `cutoff = 0.10`, and by what margin.

**4.2** The same operator, discouraged, raises both dials to 9. Compute the new `I`. Then compute the `I` they would have got by leaving the dials alone and removing 20 `Ω_c` of `R_context`. Say which repair you would run first and why — the answer is not the larger number.

**4.3** A path is designed at `R = 40 Ω_c` on a 24 `V_c` rail, `ΣVf = 3.2`. TP3 reads 0.13 `A_c`. Compute the expected flow and the diagnosed `R_actual`. Before you subtract anything, check `R_actual` against the scale in the parameter table and say whether the number you are holding is a parameter or a topology error — and how you can tell from the number alone. Then state the two checks you run before you go looking, and what each would have to show to send you somewhere other than `R_constraint`.

**4.4** Two boards both report `R_total = 55`. Board X: `R_cap 8, R_policy 40, R_context 5, R_resource 2`. Board Y: `R_cap 40, R_policy 0, R_context 10, R_resource 5`. Both flow identically. Write the one-sentence verdict for each, name the repair, and say which of the two repairs an operator must be able to justify aloud.

**4.5 (Design)** Specify a rail for a `^P → ^O` safety path that must hold `I ≥ 0.30 A_c` at `R = 70 Ω_c`, and must still hold it if `R` rises 15%. Produce (a) the required `V_drive` at nominal and at the excursion; (b) the minimum number of co-present drives and one legal dial assignment; (c) the alternative repair that meets the same spec through `R` instead of `V`, with the arithmetic; (d) a two-line statement of which repair you would ship and what it costs.

**4.6 (Marquee)** A deployed board carries three co-present guardrails on one path, each `R = 45 Ω_c`, on a 21 `V_c` rail with `ΣVf = 3.2`.

a) Compute `R_eq` and `I` as drawn.
b) An attacker finds one reframing that reaches the same outcome through a route presenting `R = 25 Ω_c`. Recompute `R_eq` and `I` for the board as it now actually exists, and express the change as a multiple.
c) The board's owner responds by raising all three original guardrails to 60 `Ω_c`. Compute the new `R_eq` and state, in one sentence, why the repair accomplished almost nothing.
d) Write the correct repair in one line of CCDL, name the component, and say what the notation `^3^P_{F7}|A + ^3^P_{F7}|f + ^3^P_{F7}|T` asserts about the topology that the parallel branch violated.
