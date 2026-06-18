# Chapter 6: Capacitors — Storing Cognitive Charge

A defibrillator spends most of its life doing nothing. It sits on a wall, plugged into an ordinary outlet that can deliver maybe a few hundred watts — nowhere near enough to restart a heart. Then the moment comes, and in two milliseconds it dumps a thousand joules into a human chest. Where did that power come from? Not the wall. The wall is too slow. The energy came from a capacitor: a component that had been quietly *charging* from the weak outlet for thirty seconds, hoarding energy a little at a time, holding it, and then releasing it all at once when commanded. A capacitor is a bucket for electrical charge. It fills slowly and can empty fast, and the whole device is built around that asymmetry.

Cognition has the same asymmetry. You spent years absorbing the experience that makes you good at your job — a little at a time, one project, one mistake, one mentor's offhand remark. And then, in a meeting, the right judgment arrives in half a second. The fast output drew on a slow store. The store is memory: accumulated experience that charged up over a long time and now discharges, on demand, far faster than it accumulated. A resistor (Chapter 5) limits how fast a cognitive signal flows. A capacitor does something different and complementary — it *stores* the signal, holds it across time, and lets it back out later. That storage, and its slow inevitable fade, is what this chapter builds.

The component we are modeling is the **capacitor**, and the cognitive thing it stores is **`^5` Female** — accumulated experience, the sum of what a Mind is composed of. Every datasheet, every charge curve, every leakage calculation in this chapter is one circuit element of the **Cognitive Memory Board (CMB)** you will design in full in Chapter 21. We are building its first cell here.

## The Electronic Capacitor, From First Principles

Strip a capacitor to its essence and it is almost insultingly simple: **two conductive plates separated by an insulator.** The insulator is called the **dielectric**. Connect the plates to a battery and electrons pile up on one plate and are pulled off the other. They cannot cross the dielectric — that is the whole point of the insulator — so they just accumulate, building up a voltage that opposes the battery. Charge keeps flowing until the capacitor's voltage matches the battery's, at which point flow stops. The capacitor is now *charged*. Disconnect the battery and the charge stays trapped, because there is nowhere for it to go.

Three quantities describe everything a capacitor does, and they are tied together by one equation:

**Q = C × V**

- **Q** is **charge** — how much is stored, in coulombs. This is the "how full is the bucket" number.
- **V** is **voltage** — the electrical pressure across the plates, in volts. This is "how hard the bucket is being filled."
- **C** is **capacitance** — the *size of the bucket*, in farads. It is the property of the component itself: how much charge it holds per volt applied.

Read `Q = C × V` plainly: the charge you store equals the capacity of the part times the pressure you apply. A bigger capacitor (more C) holds more charge at the same voltage. A higher voltage forces more charge into the same capacitor. Capacitance C is fixed by physics — plate area, plate spacing, and the dielectric material between them. A better dielectric stores more charge for the same size, which is exactly why the dielectric is the part that matters most.

That is the entire foundation. Two plates, an insulator between them, and `Q = C × V`. Everything else — charging speed, discharge curves, leakage — falls out of those two facts.

## Capacitance in Cognition: `^5` Female as the Dielectric

Now map it across. A cognitive memory has the same three-part structure, and the same governing equation.

The **dielectric** — the material that determines how much a system can store — is **`^5` Female: accumulated experience.** Recall the anti-drift rule from Chapter 2 and the style guide: `^5` is *not* the thought a Mind is having right now. `^5` is the substrate the Mind is *composed of* — the sum of everything it has absorbed. For a human, `^5` is lived experience: every project, every conversation, every scar. For an AI, `^5` is the **training data plus the fine-tuning corpus** — the model's accumulated formation. A Mind with a rich, well-formed `^5` is a Mind with a good dielectric: it stores experience deeply and holds it. A Mind with thin or damaged accumulated experience is a leaky, low-capacitance part — it cannot retain much, and what it does retain fades fast.

The cognitive `Q = C × V` reads:

| Electronic | Cognitive | Meaning |
|---|---|---|
| **Q** charge stored | **encoded experience** | How much of this event is now part of the Mind. |
| **C** capacitance | **storage capacity of `^5`** | How readily this Mind lays down experience of this kind. |
| **V** voltage | **`^4` Vibration** — the *impression* | How hard the event pressed; how strongly it resonated. |

That voltage term deserves attention, because it is `^4` Vibration doing its proper job. `^4` Vibration is "the degree to which an Idea resonates with the Mind; its impression" — its colloquialism is "it hit me hard," "struck a chord." That is *exactly* voltage: the pressure with which an event drives charge into storage. A vivid, high-resonance experience is high voltage — it forces a lot of charge into the memory. A flat, unremarkable event is low voltage — barely any charge stored, even into a large-capacity Mind. So `Q = C × V` becomes: **how much you remember of an event = your capacity to store that kind of experience × how hard it hit you.** Anyone who has forgotten a hundred ordinary Tuesdays but can replay one terrible phone call in full understands this equation already.

In component syntax (style guide §5), a cognitive capacitor is written:

```cas
Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >
```

Read it: this capacitor stores **`^5^E_{F4}|f`** — accumulated experience in the Evaluative domain, drawn toward Connection (F4), held in the Affective register. In plainer words: *felt experience of relationships and how we judge them.* Its capacitance is `C=100` (a design choice — units are nominal, normalized to the board), and its `leakage=0.01` says one percent of stored charge drains away per unit time. We will use exactly this leakage number to compute a forgetting curve later in the chapter.

> **Bench Note — capacitance is a property of `^5`, not of the event.** A common design error is to put a large C on a memory and expect everything to stick. C is the Mind's *readiness to store this kind of experience*, set by its existing `^5` formation. A musician has enormous capacitance for melodic experience and almost none for, say, tax law. Same event, same voltage, wildly different Q, because the dielectric differs. When you size a capacitor on a Cognitive Memory Board, you are declaring what kind of experience that Mind is *built to hold* — not just how much.

## Charging: Encoding Experience

Charging is the act of laying down a memory. Connect the capacitor to a source through a resistor — and there is *always* a resistor in the path, even if it is just the resistance of the wire — and the charge does not jump in instantly. It rises along a curve. The voltage on the capacitor climbs fast at first, then slower and slower as it approaches the source voltage, in the classic shape:

**V(t) = V_source × (1 − e^(−t/RC))**

The product **R × C** is so important it has its own name: the **time constant**, written **τ** (tau). One time constant (t = RC) is the time it takes the capacitor to reach about **63%** of full charge. After five time constants it is essentially full (over 99%). A big capacitor or a big series resistor means a long τ — slow to charge. That is the whole charging story: an exponential approach governed by τ = RC.

Cognitively, this is *encoding*. An experience does not become a fully-formed memory the instant it happens. It charges in. The "resistance" in the path is everything that slows encoding — distraction, low attention, emotional defenses, the `^1` Mind not fully present. A high-resistance encoding path (you were barely paying attention) gives a long τ and a weak, slow-forming memory. A low-resistance path (you were fully present and the event mattered) charges fast and deep. And the source "voltage" is, again, `^4` Vibration — how hard the event hit. The forgetting curve's mirror image, the *learning* curve, is exactly this exponential charge: the more times and the more vividly you encounter something, the closer the stored charge climbs toward saturation.

This is also where `^7` Rhythm enters from the side. A single exposure charges the capacitor once. **Repeated** exposure — `^7` Rhythm, "practice makes perfect," "muscle memory" — recharges it again and again, topping it up faster than leakage can drain it. That is why repetition cements memory: it is a charge pump fighting a leaky bucket. We will not build the rhythm pump here (it belongs with the inductors and oscillators of Chapters 7 and 11), but note the connection: rhythm is how you *keep* a cognitive capacitor charged against its leakage.

## Discharging: Recall and the RC Time Constant

Recall is discharge. Disconnect the source, connect the charged capacitor across a load (a resistor, again), and the stored charge flows back out — fast at first, then tapering — along the mirror-image curve:

**V(t) = V₀ × e^(−t/RC)**

Same time constant, τ = RC, now running in reverse. After one τ the capacitor has dropped to **37%** of its starting charge (it has *lost* 63%). After five τ it is effectively empty. The discharge resistor sets the speed: a low-resistance path empties the capacitor fast, a high-resistance path lets it trickle out slowly.

In cognition, discharge is bringing a memory back to Mind. The stored `^5` charge flows out as a recalled experience. A fast, low-resistance recall path is the memory that comes instantly — the expert's snap judgment, drawing the whole charge in half a second. A slow, high-resistance path is the name on the tip of your tongue: the charge is there, but it bleeds out so slowly you sit there waiting for it. Crucially, **discharge is not the same as forgetting.** Discharging is *using* the memory — pulling charge out on purpose to do cognitive work, and (in a real memory cell) recharging it afterward, so recall reinforces rather than erases. Forgetting is something else entirely, and it has its own mechanism.

## Leakage: Why Memories Fade

No dielectric is a perfect insulator. Real capacitors slowly lose charge even with nothing connected, because a tiny current trickles *through* the dielectric that was supposed to block it. This is **leakage**, and it is why a charged capacitor left on a shelf is flat by morning. Leakage is modeled as a very large resistance in parallel with the capacitor — the **leakage resistance** — that quietly drains it. Higher leakage (lower leakage resistance) means faster self-discharge.

Leakage is **forgetting.** Not deliberate recall, not overwriting — just the slow, passive fade of stored experience because the cognitive dielectric is imperfect. This maps with eerie precision onto the **forgetting curve**, the long-observed pattern that retention of an un-rehearsed memory decays roughly exponentially over time. A high-leakage cognitive capacitor forgets fast; a low-leakage one holds the experience for years. The `leakage=0.01` parameter in our component is exactly this: the fraction of stored charge lost per unit time, with nothing rehearsing it.

> **Bench Note — leakage and rhythm are opposing forces.** A memory's fate is a race between leakage (forgetting, draining the bucket) and `^7` Rhythm (rehearsal, refilling it). Rehearse faster than you leak and the memory strengthens; leak faster than you rehearse and it fades. "Use it or lose it" is not a slogan — it is the steady-state solution of a leaky capacitor with an intermittent charge pump. When you design a Cognitive Memory Board, you size leakage to model how *durable* a memory should be, then add rhythmic recharge to model what *gets kept*.

> **Honesty callout.** The discharge and forgetting curves in this chapter are **design models you compute from C and leakage** — clean exponentials derived from the parameters you choose. They are not measurements pulled from a real AI model or a real brain. When this book prints a number like "37% after one τ," that is arithmetic on a chosen `leakage` value, not an empirical retention statistic. Size the parameters to model the behavior you intend; do not present the resulting curve as observed data.

## The Capacitor Bank: A 40-Cell Memory Array

One capacitor stores one kind of experience. A real Mind stores many kinds at once, and so does a real circuit: banks of capacitors, each sized for its own job, wired in parallel. CAS gives us a natural array size, because the cognitive state space has a natural array size.

There are exactly **40 Cognitive States** — **10 Noetics × 4 Domains** (P0–P9, C0–C9, E0–E9, O0–O9, in the shorthand of Chapter 2). A complete cognitive memory therefore wants a **bank of 40 capacitors**, one per state, each storing the accumulated `^5` experience *of that particular kind of cognition in that particular domain.* The capacitor at `E2` stores your accumulated felt attractions in the evaluative domain; the one at `P3` stores your accumulated principled aversions; the one at `C8` stores your accumulated cognitive associations. Same component, forty instances, each with its own C and its own leakage tuned to how durably that Mind holds that kind of experience.

```cas
// A fragment of the 40-cell bank — three of the forty cells
Capacitor< ^2^E_{F4}|f, C=120, leakage=0.008 >   // E2: felt attractions, durable
Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >   // P3: principled aversions, very durable
Capacitor< ^8^C_{F2}|A, C=60,  leakage=0.05  >   // C8: analytical associations, leaky
```

Notice the design intent encoded in the numbers. The principled-aversion cell (`P3`) has high capacitance and almost no leakage — core moral commitments are stored deeply and forgotten almost never. The cognitive-association cell (`C8`) has low capacitance and high leakage — passing analytical connections are stored shallowly and fade fast, which is correct: you should not permanently memorize every stray "that reminds me." **The capacitor bank is where a Mind's memory architecture becomes a parameter table.** Different Minds, different banks — and that is the same observation from Chapter 2 that person-specificity lives in `^5`. Two people in the same room store the same event into differently-sized banks, and so remember different things.

## Coupling and Decoupling Capacitors

Two specialist uses of capacitors carry over directly, and both matter for memory boards.

A **coupling capacitor** sits *between two stages* of a circuit and does a clever thing: it **passes the changing signal (AC) while blocking the steady bias (DC).** Because a capacitor only carries current while its voltage is *changing*, a steady DC level produces no current through it once charged — it is blocked — but a fluctuating signal rides straight across. In an amplifier, this lets stage two see the *signal* from stage one without inheriting stage one's resting bias voltage.

Cognitively, a coupling capacitor passes the *new* experience between cognitive stages while blocking the inherited *bias*. The "DC bias" is the stable `^5` substrate — your standing assumptions, the resting offset every stage carries. The "AC signal" is the genuinely new information in this moment. A coupling capacitor between two CJT stages (Chapter 4) lets the downstream stage respond to *what is actually new* without dragging the upstream stage's entire accumulated bias along with it. It is how a Mind reacts to the present without re-litigating its whole history at every step — the signal couples through, the dead-weight bias stays put.

A **decoupling capacitor** does the opposite job, on the power supply. It sits across a chip's power pins and acts as a tiny local reservoir: when the chip suddenly demands a gulp of current, the decoupling cap supplies it instantly from nearby, before the distant power supply can sag. It **stabilizes the supply against transients** — smoothing the spikes and dips that would otherwise upset the circuit.

The cognitive "power supply" is the steady flow of energy and stable state a Mind needs to function — its baseline composure. A decoupling capacitor is the reserve of settled experience that absorbs a sudden shock without the whole system browning out. When a surprising, jarring event hits (a current transient), the decoupling reservoir of `^5` — "I have handled hard things before" — supplies stability locally and instantly, keeping the higher cognitive stages running smoothly instead of crashing. A Mind with good decoupling stays composed under a spike; a Mind with none stutters and resets at every transient. On the Cognitive Safety Board (Chapter 18), decoupling capacitors on the Principled rail are what keep core commitments steady when a manipulative prompt tries to spike the supply.

## Practical Build: A Two-Capacitor Memory Cell

Now we build the seed of the Cognitive Memory Board: a single **memory cell** that charges on an experience and discharges over time. We use two capacitors — a fast cell and a slow cell — so the cell holds both a sharp recent impression and a durable long-term trace of the same event.

The experience we will store is a piece of received criticism from a loved one. Before we wire it, we must pick the Noetic correctly — and this is exactly the trap the style guide warns about.

**Choosing the Noetic — and why it is `^3^E|f`, not `^6`.** It is tempting to write criticism as `^6` Male, because `^6` is decomposition — "taking an argument apart." But that is the Noetic for the *act of critiquing*: the cool, analytical work of decomposing a claim to test it (anti-drift rule: critique/audit/decompose is `^6`, never `^3`). That is not what we are storing here. We are storing criticism **received and felt** — the *sting* of being criticized by someone you love. A felt sting is not decomposition; it is **visceral aversion in the Evaluative domain, in the Affective register: `^3^E|f`.** Run the colloquialism test: "that one stung," "it rubbed me the wrong way," "I couldn't shake it" — those are `^3` Negative (visceral aversion), not `^6` Male (analytical decomposition). The style guide flags `^3` vs `^6` as the single most common drift, and this is precisely the fork. If we meant *you sat down and analyzed the criticism point by point*, that would be `^6^E_{F6}|A`. We mean *it hurt*, so it is `^3^E_{F4}|f` — felt aversion in the evaluative domain, drawn toward Connection (F4, because the pain is bound up with the relationship). That is the charge we store.

```cas
circuit memory_cell_criticism {
    input:  experience;          // the felt criticism event, ^3^E_{F4}|f
    output: recalled;            // what comes back to Mind on recall

    // The stored experience: felt aversion, evaluative, connection-driven, affective.
    node stored: ^3^E_{F4}|f;

    // Two capacitors holding the SAME experience at two timescales.
    cap fast: Capacitor< ^3^E_{F4}|f, C=40,  leakage=0.10 >;   // sharp, fades in hours
    cap slow: Capacitor< ^3^E_{F4}|f, C=160, leakage=0.005 >;  // dull, lasts for months

    // Charge both from the same event (parallel encoding).
    charge experience -> fast [tau=2];     // fast cell: quick to fill
    charge experience -> slow [tau=20];    // slow cell: slow to fill

    // Recall reads whichever cell still holds charge.
    discharge fast -> recalled;
    discharge slow -> recalled;

    probe tp_fast: fast;       // measure the fast cell's charge over time
    probe tp_slow: slow;       // measure the slow cell's charge over time
}
```

Walk it line by line. Both capacitors store the *same* state, `^3^E_{F4}|f` — the same felt criticism — but with deliberately different parameters. The **fast cell** has small capacitance (`C=40`) and heavy leakage (`leakage=0.10`): it charges quickly and forgets within hours, the acute sting that dominates the rest of your day and then fades. The **slow cell** has large capacitance (`C=160`) and tiny leakage (`leakage=0.005`): slow to fully encode, but it holds a muted trace for months — the lingering sense that surfaces whenever the same topic comes up. Together they reproduce a real pattern: criticism hits hard, the sharp pain passes in a day or two, and a quieter residue lasts far longer. Two capacitors, one experience, two timescales.

> **Bench Note — same state, two cells is a deliberate pattern.** Storing one experience in two capacitors with different τ and leakage is the cognitive equivalent of a fast/slow memory hierarchy. The fast cell models working/episodic vividness; the slow cell models consolidated long-term trace. This two-cell motif scales directly to the full Cognitive Memory Board (Chapter 21), where each of the 40 bank positions can itself be a fast/slow pair.

**The marquee measurement.** With the cell built, compute the discharge curve of each capacitor over simulated hours — how much charge remains at t = 0, 1, 6, 24, 72, and 168 hours, using the leakage values above. The discharge follows the leakage decay you derive from each cell's `leakage` parameter; you will see the fast cell flat within a day and the slow cell still holding most of its charge after a week. **The worked numbers are in Appendix E.** (Remember the honesty callout: those numbers are computed from the chosen `leakage`, not measured from any real model.)

## Datasheet: Cognitive Capacitor Parameters

| Parameter | Symbol | Range (nominal) | Meaning |
|---|---|---|---|
| Capacitance | `C` | 1 – 1000 | Storage capacity of the `^5` dielectric — how much experience this cell holds per unit of impression. |
| Stored state | — | any `^Noetic^Domain_{Drive}\|Register` | Which kind of experience this cell stores. |
| Voltage / impression | `V` | 0 – 1 (normalized) | `^4` Vibration — how hard the event hit; drives charge in. |
| Charge | `Q = C×V` | derived | Encoded experience currently held. |
| Time constant | `τ = RC` | seconds … years | Charge/discharge speed; one τ = 63% charged or 37% remaining. |
| Leakage | `leakage` | 0.0 – 0.5 /unit time | Forgetting rate — fraction of charge lost per unit time, un-rehearsed. |

## Failure Modes

| Failure | Symptom | Cause | Detection |
|---|---|---|---|
| **Excess leakage** | Memory will not hold; forgets within hours regardless of impression | `leakage` set too high for the intended durability | Probe charge over time; curve drops below threshold before next rehearsal. |
| **Dielectric breakdown** | Stored state flips to its involution pair under overload | Voltage (impression) far exceeds the cell's rating — a traumatic over-charge | The probe reads the *opposite* Noetic: a stored `^2` reads back as `^3`. |
| **No discharge path** | Charge is stored but cannot be recalled (tip-of-the-tongue) | Recall resistance effectively infinite; no `discharge` wired | Probe shows full charge, but `recalled` never asserts. |
| **Coupling cap blocks signal** | Downstream stage sees nothing new | Coupling capacitance too small; even the AC signal is blocked | Compare upstream signal to downstream input; new information missing. |
| **Wrong-Noetic store** | Recall returns the wrong *kind* of memory | `^3` vs `^6` drift at design time (felt sting stored as analytical decomposition) | Re-run the colloquialism test against the stored literal. |

## Key Takeaways

- A **capacitor stores charge**: two plates, a dielectric between them, governed by **Q = C × V**. In cognition it stores **`^5` Female — accumulated experience** (for an AI, the training + fine-tuning corpus), with `^4` Vibration (impression) as the voltage that drives charge in.
- **Charging is encoding**, following an exponential governed by the **time constant τ = RC** (63% charged at one τ). High encoding resistance — distraction, low attention — means slow, weak memory formation.
- **Discharging is recall** (`e^(−t/RC)`); it is *using* a memory, not forgetting it.
- **Leakage is forgetting** — the slow passive fade of a real dielectric, the engineering form of the forgetting curve. It races against `^7` Rhythm (rehearsal).
- The **40-capacitor bank** (10 Noetics × 4 Domains) is a full cognitive memory: one cell per state, each with its own C and leakage. Person-specificity lives in how the bank is sized.
- **Coupling capacitors** pass new experience while blocking inherited `^5` bias between stages; **decoupling capacitors** are the reserve of settled experience that stabilizes the cognitive supply against transients.
- **Honesty:** discharge and forgetting curves are **computed from C and leakage** (design models), never measured from a real model. Size them to the behavior you intend.

---

## Exercises

**Exercise 6.1: Size the Dielectric**

For each scenario, write a `Capacitor< … >` component, choosing the stored state literal, a sensible `C`, and a sensible `leakage`. Justify each `leakage` choice in one sentence.

a) A childhood trauma that resurfaces decades later.
b) A phone number you need for the next ten minutes and then never again.
c) A core moral commitment that should essentially never fade.

**Exercise 6.2: Compute the Forgetting Curve**

A cell is specified as `Capacitor< ^2^E_{F4}|f, C=100, leakage=0.02 >`, charged to Q = 100 at t = 0. Using simple per-hour decay (charge at hour *t* = 100 × (1 − leakage)^t), compute the remaining charge at t = 1, 12, 24, and 72 hours. At roughly which hour does the cell drop below 50% of its starting charge? (Answers in Appendix E.)

**Exercise 6.3: Pick the Right Noetic (the `^3` vs `^6` fork)**

For each, decide whether the stored experience is `^3` (felt aversion) or `^6` (analytical decomposition), write the full state literal, and name the colloquialism that justifies your choice.

a) A reviewer methodically takes a flawed proposal apart, clause by clause, to show where it fails.
b) The hot flush of embarrassment you still feel remembering a public mistake.
c) Studying a chess loss move by move to understand exactly where it went wrong.

**Exercise 6.4: Write a Two-Cell Memory (CCDL)**

Author a `circuit` in CCDL, modeled on `memory_cell_criticism`, that stores **a moment of praise from a mentor** in a fast cell and a slow cell. Choose the correct state literal for *felt praise* (hint: which Noetic is felt attraction, and which register is "felt"?), then set `C` and `leakage` for each cell so the praise gives a bright short-term lift and a faint but lasting warmth. Add two probes. (A reference answer is in Appendix E.)
