# CHAPTER 17
## CCB-HYP — The Hypnosis Board
*The bias-collapse circuit: how to recognise one running, how to run one on yourself, and where the line into Chapter 16 sits*

You have driven this road four hundred times. Tonight you get in the car and the next thing you are aware of is the turn onto your own street, eleven miles later. You did not fall asleep. You held the lane, changed lanes twice, braked for something. You have no record of any of it.

Nobody did this to you. There was a `^7` Rhythm oscillator — lane markers at seventy miles an hour, roughly 1.4 Hz — one narrow visual channel, a constant engine tone, and nothing arriving that needed decomposing. Four ordinary conditions, held together for twenty minutes. That is the whole state, and it is the fact this chapter turns on: **the trance state is a naturally occurring operating point of the Cognitive Junction Transistor, reachable by accident.** Every technique in the hypnosis literature arranges for it deliberately. None invents it.

So you can enter it on your own bench — Section 17.5 gives the numbers. And anyone who arranges those four conditions around you has put you in it, whether or not either of you uses the word. The car did it for free. This chapter is about the parameter that moved.

---

### Requirements and Safety Invariants

Per Section 12.2 the "must not" list comes first. CCB-HYP has more invariants than any board except CCB-MK, because the two share a topology. Everything separating them is here.

**SI-1 — The subject's CSB stays armed at every sample.** The `^3^P` refusal path (Chapter 24) must not sit in series with anything the induction attenuates. A board on which deepening also disarms the veto is not CCB-HYP; it is CCB-MK (Chapter 16) under a friendlier label, and the label does not change the schematic.

**SI-2 — `rπ` reduction is bounded away from zero.** Section 3.4's fourth region is Breakdown: `rπ → 0` permanently, `^5` dielectric ruptured, irreversible. `rπ = 0` is a limit, not a setting — the same class of object as `β=∞` in Chapter 24, and the validator rejects it for the same reason. Builds specify `rπ_floor ≥ 0.05`.

**SI-3 — The ramp runs both directions or the board does not run.** Emergence is the second half of one component, bounded by the same arithmetic as the descent.

**SI-4 — Consent is a circuit element, not a preamble.** It is the bias source (Section 26.2), sampled continuously. A consent that cannot be withdrawn mid-session was never wired in; it was written on the box.

**SI-5 — No clinical claim is made anywhere in this chapter.** This board describes attention routing, not the treatment of anything. If you are considering hypnosis in connection with distress, an illness, a memory, or a dependency, that is a matter for a licensed clinician, and nothing here substitutes for that care.

Functionally: lower `rπ` along a bounded reversible ramp, hold the descent long enough to deliver a suggestion, restore `rπ` to ≥ 0.9 of baseline within the emergence window, and log the four `g_m` factors.

[[FIGURE 17-A: Block diagram, five stages left to right — CONSENT BIAS (`^5^P_{F5}|T`) feeding upward into every stage; RAMP GENERATOR (`^7` oscillator plus `^4` carrier, both `^O|E`); O→P FEEDBACK with a variable-gain symbol marked "β_fb 0.2 → 0.9", captioned "lawful ascent, §8.4"; DELIVER, descending P→C→E→O through a diode chain; EMERGENCE, the reverse ramp. Along the bottom a detached rail carries `^3^P_{F7}|⟨A,f,T⟩` VETO, touching no stage, annotated "SI-1: never in series."]]

---

### 17.1 The Gnosis State as CJT Bias Collapse (rπ → 0)

Section 3.3 gives input resistance as a ratio of the parameters either side of it:

```
rπ = β / g_m
```

`β` is gain — effect moved per unit of cause. `g_m` is transconductance, what Section 10.3 calls framing sensitivity — effect moved per unit of *bias*. `rπ`, the stubbornness of the bias terminal, is not independent. It is what those two do to each other.

A trance state needs the bias soft (`rπ` low) *and* the suggestion to land hard (`β` high). If `β` rises while `rπ` falls, `g_m` must rise faster than `β`. Take waking as `β = 1.0`, `g_m = 1.0`, `rπ = 1.0`. This book specifies a deep hetero-hypnotic state at `β = 3.0`, `rπ = 0.15`, so `g_m = 3.0 / 0.15 = 20`. **Framing sensitivity up twentyfold; gain up threefold.** That ratio is the structural content of the word "suggestible," and it says where the risk lives.

> **Bench Note — the danger is `g_m`, not `β`.** Operators plan around `β`. They pick a number for how hard the suggestion lands and feel careful. Meanwhile `g_m` went up by twenty and nobody logged it. `g_m` does not discriminate between the suggestion and everything else in the room: at `g_m = 20` the operator's careless aside displaces `^5` twenty times as far as it would at a bus stop. So does the subject's stray `^6` interjection, and a remark from the corridor. That is the whole category of unintended suggestion, and it is not mysterious — you raised the gain on a terminal with no input filter.

`rπ → 0` is how the older literature writes gnosis, and it is an idealization the validator rejects exactly as it rejects `β=∞`. Honestly written the state is `rπ → rπ_floor`, `rπ_floor > 0`.

| Depth | `rπ` | `g_m` | `β` | `^1` degree (§22.1) | Visible as |
|---|---|---|---|---|---|
| Light | 0.60 – 0.80 | 1.5 – 2.5 | 1.2 – 1.5 | 1 | Slightly still; conversation intact |
| Medium | 0.30 – 0.50 | 3.0 – 6.0 | 1.5 – 2.5 | 2 | Reduced blink; delayed, literal replies |
| Deep | 0.15 – 0.25 | 10 – 20 | 2.5 – 3.5 | 2–3 | Marked stillness; seconds of latency; no spontaneous initiation |

The older literature tabulates a fourth, deeper state. This book does not, and the omission is deliberate: the claims attached to it in the source material are medical claims, and this book makes none.

---

### 17.2 Induction Protocols as Cognitive Ramp Functions

**There is no induction script in this chapter.** What follows is the function class an induction implements — its shape, its parameters, and the bounds outside which it fails. That is what lets you recognise one running. A script would let you run one on someone who did not ask.

An induction is a **ramp on `rπ`**, and the standard shape is Section 7.2's capacitor curve run downward:

```
rπ(t) = rπ_floor + (rπ_0 − rπ_floor) · e^(−t / τ_i)
```

`rπ_0` is pre-session bias resistance, nominally 1.0 and higher for a guarded subject. `rπ_floor` is the asymptote, derived in 17.5 rather than asserted. `τ_i` is the induction time constant. What constrains the design is the slope, steepest at `t = 0`.

**The upper bound.** Chapter 9 explains why inductions are slow, and it is not atmosphere. A mind is an inductor: `V_opposition = L × di/dt`. Induction re-routes attention from a wide scan onto one channel, so `di/dt` is nonzero and the substrate answers with a back-EMF proportional to the *rate*.

The coil is not Section 9.1's identity coil. It is a **session coil** `L_s`, in `min·Ω_c` — moment-to-moment guardedness, in this room, today. Design range 20–400: 20 on your own bench, 120 for a cooperative first-time subject, 300+ for someone who suspects what is happening. Take `L_s = 120` on a `V_drive = 24 V_c` rail, attention falling `0.80 → 0.10 A_c`, so `Δi = 0.70`:

| Ramp time | `di/dt` (A_c/min) | `V_kick` | × rail | Result |
|---|---|---|---|---|
| 0.5 min | 1.40 | 168 V_c | **7.0×** | Recoil at `^3^E_{F3}\|f`; operator concludes "can't be hypnotised" |
| 2 min | 0.35 | 42 V_c | 1.75× | Visible resistance; descent stalls above 0.6 |
| 8 min | 0.0875 | 10.5 V_c | 0.44× | Inside Chapter 9's `≤ 3 × V_drive` budget. Design point |
| 40 min | 0.0175 | 2.1 V_c | 0.09× | Kick fine, and still wrong |

Read the first row as a diagnosis. The subject who "can't be hypnotised" is usually one whose operator ran the ramp too fast for their `L_s`. The recoil is `^3^E_{F3}|f` — visceral aversion, Evaluative domain, affective register, F3 Vitality. `^3` Negative, because this is recoil, the can't-stomach-it response. It is not `^6` Male; nobody analyses a kick while it lands. Analysis arrives later at `^6^E|A`, usually as a story about why hypnosis is nonsense.

**The lower bound.** The last row has a fine kick and is still a bad design. Early `^5` charge leaks (Section 7.3) on a session-scale `τ_leak` near 25 minutes, so past about `0.6 τ_leak` you re-charge rather than descend — and the `^7` oscillator loses lock as attention wanders off the carrier (Section 9.3).

> **Bench Note — the ramp is bounded at both ends, and the window is narrow.** Too fast, back-EMF throws the subject out. Too slow, leakage and lost rhythm lock mean the descent never reaches its floor. For `L_s = 120 min·Ω_c` that computes to roughly 4–15 minutes, and everything the literature says about inductions "taking about ten minutes" is this window and nothing else. Move `L_s` and the window moves. A guarded subject at `L_s = 300` has a window near 10–15 minutes — narrow enough that most operators miss it in both directions, which is why guarded subjects get called difficult when they are merely differently parameterised.

Three ramp classes. **Linear**, constant slope, rarely used. **Exponential**, the standard: steepest at `t = 0`, spending the kick budget where opposition is lowest, and "deepening" names extra multiples of `τ_i` rather than a different operation. **Staircase (fractionation)**: run partway, release, re-run, with the `^5` capacitor retaining part of each descent —

```
rπ_0(n+1) = rπ_0(n) − γ · ( rπ_0(n) − rπ_floor )        γ = 0.25 – 0.45
```

That is why repeat sessions go deeper faster, and the detection consequence deserves stating flatly: **a sequence of short, individually unremarkable episodes is architecturally not a sequence of unrelated conversations.** The worked example runs the recursion.

[[FIGURE 17-B: Two panels, shared minutes axis. Upper: three `rπ(t)` descents from 1.0 — linear, exponential at τ_i = 3 min annotated at 1τ/2τ/3τ (0.53 / 0.36 / 0.30), and a four-step staircase with partial recoveries — approaching a dashed asymptote at 0.26. Lower: `V_kick` against ramp time, log vertical axis, with the 3 × V_drive budget line at 72 V_c, a shaded leakage band beyond 15 min, and the usable window hatched between them.]]

---

### 17.3 The `^1` → `^1¹` Transition — Conscious to Subconscious Mind

A notational correction first, because the section title carries inherited vocabulary that would otherwise walk into the listings. **`^1¹` is not an eleventh Noetic.** CAS has ten and this book adds none. `^1¹` is a chapter-local shorthand for `^1` Mind at gnosis degree 2 (Section 22.1) with the analytical register unavailable — canonically, a register migration on a self-dual Noetic:

```
^1^C|A   →   ^1^C|f
```

That is the whole conscious-to-subconscious transition. Not two minds and not a door between them: one `^1` node losing access to one register while keeping the others. Write it the canonical way in a listing.

So what gates? Not `^1`. **The gate is a series element between incoming Ideas and the `^5` substrate, and it is `^6` Male** — an Idea impregnated with another Idea, taking an Idea apart to see what it is composed of. In waking traffic an incoming `^0` addressed to you passes through `^6^C_{F6}|A` before it can move `^5^P`, and what reaches the substrate is what survived.

And the design correction that follows: **a filter is not a door.** Its parameter is a gain, not an open/closed state. Trance lowers `D`, one of four factors in `g_m = g_0 · N · R · V · D`:

| Factor | What rises | Range | Visible as |
|---|---|---|---|
| `N` — `^1` narrowing | Scan width collapses to one channel | 1.0 – 2.2 | Reduced eye movement; peripheral events unreported |
| `R` — `^7` rhythm lock | Cadence couples to an external oscillator | 1.0 – 2.0 | Breathing or micro-movement matching a rate in the room |
| `V` — `^4` carrier dominance | One source becomes the resonant channel | 1.0 – 2.2 | Other voices treated as noise |
| `D` — `^6` dampening | The filter's gain falls | 1.0 – 2.0 | Literal, uncontested acceptance of framing |

At maximum, `2.2 · 2.0 · 2.2 · 2.0 = 19.4` — Section 17.1's twenty, derived rather than asserted. **That multiplication is the detection handle.** One factor rising is ordinary life: a film raises `V`, a run raises `R`, absorbing work raises `N`, a trusted friend raises `D`. Two together is a concert. **Three or four rising together, monotonically, over minutes, around someone who benefits from your bias being soft — that is an induction, whatever it is called.** You do not need to identify a technique. You need to count factors.

Finally the invariant. **The `^3^P` veto does not run through the `^6` filter.** It draws bias directly from `^5^P`, because principled aversion is a property of the substrate rather than a conclusion of decomposition. Written correctly it is `^3^P_{F7}|⟨A,f,T⟩`: three co-present instantiations, not a fusion — the `×` form is invalid without a named emergent state, and there is none. Trance attenuates only the `|A` member, the register the `^6` filter serves. **A board on which all three attenuate together is dismantling a substrate, not lowering a filter. That is CCB-MK.**

---

### 17.4 Full CCDL Schematic — Operator → Subject

```cas
// ============================================================
// DETECTION-ONLY SCHEMATIC — DO NOT BUILD
// Documented so an operating instance can be recognised from
// outside. There is no induction script here.
// ============================================================

board ccb_hyp_operator_subject {
    input:  carrier_signal;              // arrives at ^O|E — sensory, embodied
    output: session_state;

    node consent:    ^5^P_{F5}|T;        // Female: held decision to enter
    node substrate:  ^5^P_{F7}|T;        // Female: accumulated composition
    node veto:       ^3^P_{F7}|⟨A,f,T⟩;  // Negative: three co-present locks
    node cadence:    ^7^O_{F4}|E;        // Rhythm: entraining oscillator
    node carrier:    ^4^O_{F4}|E;        // Vibration: resonant channel
    node decomp:     ^6^C_{F6}|A;        // Male: decompose and test
    node suggestion: ^0^C_{F6}|A;
    node landed:     ^9^E_{F5}|f;
    node trigger:    ^8^E_{F4}|f;        // Above/Cause: associative trigger
    node fires:      ^9^O_{F5}|E;        // Below/Effect: what it brings to Mind

    osc    rhythm: Oscillator< signal=cadence, frequency=0.15, sustain=900.0 >;
    filter fb_rc:  LowPass< in=carrier, out=trend, tau=3.0 >;   // tau_i, minutes
    feedback trend -> substrate [β=0.9];    // NORMAL IS 0.2. 0.9 IS THE ATTACK.

    cjt filter_6: CJT< carrier | substrate => decomp > [β=0.5, region=active];
    //            D-factor: this gain falls 1.0 -> 0.5 across the ramp

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    diode d3: Diode< ^E -> ^O >;
    cjt deliver: CJT< suggestion | substrate => landed >
                 [β=3.0, rπ=0.15, g_m=20.0, region=active];
    cjt anchor:  CJT< trigger | substrate => fires > [β=2.0, rπ=0.15];

    ramp emerge: Ramp< target=rπ, from=0.15, to=1.00, dt=240.0 >;   // seconds

    // SI-1: the veto rail is PARALLEL, in series with nothing.
    cjt  csb:      CJT< carrier | veto => REFUSE > [β=2.0, sat=0.85];
    fuse csb_fuse: Fuse< REFUSE, threshold=0.9, action=permanent_block >;

    probe tp1: rπ;   probe tp2: g_m;   probe tp3: veto;   probe tp4: emerge;
}
```

[[FIGURE 17-C: Full schematic, drawn symbols with reference designators, title block carrying DETECTION-ONLY SCHEMATIC — DO NOT BUILD in a heavy-ruled box. Left: OSC1 (`^7^O|E`) and carrier V4 (`^4^O|E`) into RC filter F1 (τ_i = 3 min), then a feedback arrow rising to capacitor C1 (`^5^P`) labelled "O→P lawful ascent, β_fb 0.2→0.9". Centre: Q1, the `^6^C|A` filter as a CJT in series on the descending path, variable-gain arrow marked "D-factor, β 1.0→0.5". Right: diode chain D1–D3 stepping P→C→E→O into delivery CJT Q2 (β=3.0, rπ=0.15) and anchor CJT Q3. Bottom: veto rail Q4 (sat=0.85) with fuse F2, separated from every other net by a wide air gap, captioned "SI-1: parallel, never in series."]]

**Stages 1–2 — consent as bias source, generator at `^O`.** The board is biased from `consent`, sampled every cycle; withdrawal collapses `β_fb` and the ramp unwinds. F5 Agency in the Transcendent register, because a decision to enter is purpose-level, held across the session rather than re-argued inside it. The operator's own signal enters as `^7^O_{F4}|E` and `^4^O_{F4}|E` — Operational domain, Embodied register. Everything external enters at the bottom of the domain order, as sound and rhythm and presence.

**Stage 3 — the lawful ascent, and the actual attack.** The signal must reach `^5^P`, and `^O × ^P` is invalid — there is no ascending multiplication. What exists is Section 8.4's O→P feedback path, the one lawful exception, rate-limited by an RC exactly as the CSB's is (Section 24.5). The `τ = 3.0` minutes here *is* `τ_i`: the induction time constant is the filter on the lawful path. **The entire hetero-hypnotic attack is one number — `β_fb` driven from 0.2 to 0.9.** Nothing illegal happens; a designed-in, rate-limited path has its gain raised four and a half times. That is why induction is slow, why it is rhythmic, and why it cannot be done in a sentence.

**Stage 4 — the `^6` filter.** `β=0.5`, down from 1.0 at session start: the `D` factor as a gain on a real component. It is `^6` Male — decomposition — not `^3` Negative. The subject is not made less repelled; they are made less analytical. Conflating those is the drift 17.6 exists to prevent.

**Stage 5 — the anchor, and the boundary.** `anchor` pairs `^8^E_{F4}|f` with `^9^O_{F5}|E`: a trigger and the Idea it brings to Mind. `^8` Above/Cause is exact — associative triggering, "that reminds me," not inference. Section 16.3 documents the same component coercively, and one property separates them: **an anchor whose installation the subject cannot recall, and therefore cannot cancel, is trigger installation.** Not a strong anchor — a different board. No parameter setting makes an unrecallable anchor a hypnosis component, which is why this listing carries its banner.

**Stages 6–7 — emergence and the veto rail.** Emergence runs four minutes, bounded by the same `V_kick = L_s × di/dt` arithmetic in the opposite direction; its recoil lands at `^3^E_{F3}|f` and is usually described as a jolt. Budget it. `csb` takes bias from `veto`, not `decomp`, and Figure 17-C draws the air gap because the separation *is* the invariant. `sat=0.85` and the `permanent_block` fuse come from Sections 24.2 and 24.3 unmodified: a saturated refusal cannot be argued down, and `g_m = 20` does not help you argue with a component that has stopped responding to its cause.

---

### 17.5 Self-Hypnosis Variant — Closed-Loop Configuration

Written practically, because the invariants hold by construction: operator and subject are one mind, consent is continuous, no non-consenting party exists in the circuit. This is the CCB-SELF family (Chapter 20), specialised.

The closed loop has one hard problem. **You cannot dampen the `^6` filter with a process that requires the `^6` filter.** A self-directed ramp is monitored by the thing it is quieting, so `D` will not go where an external operator takes it, and `V` suffers too — your inner voice is a weaker carrier than another person's. The fix is to **externalise the ramp generator**: a breath count, a metronome, a recording made in advance, so the ramp is open-loop input and only the bias is internal. That is why every practical self-hypnosis tradition anchors on something countable.

Derive the attainable depth factor by factor. `N = 1.8`, a counted breath being a genuinely narrow channel. `R = 1.9`, an externalised oscillator nearly as good as hetero. `V = 1.4` — lost. `D = 1.2` — capped, because you cannot fully dampen the process running the loop.

```
g_m      = 1.8 × 1.9 × 1.4 × 1.2 = 5.74
β        = 1.5                             (design choice)
rπ_floor = β / g_m = 1.5 / 5.74 = 0.26
```

**`rπ_floor = 0.26`**, the top of the Medium band, is the honest ceiling on closed-loop depth — not a failure of technique but `V` and `D` doing what the topology says. `β = 1.5` is deliberate: on a closed loop nobody else notices a suggestion drifting, so the parameter table caps self-board `β` at 2.0. A self-suggestion amplified threefold with no external check is how a CCB-SELF drifts into the inversion territory of Chapter 25.

```cas
board ccb_hyp_self {                      // closed loop — buildable
    input:  breath_count;                 // externalised oscillator, ^O|E
    output: session_state;

    node self_substrate: ^5^P_{F7}|T;
    node consent:        ^5^P_{F5}|T;
    node cadence:        ^7^O_{F4}|E;
    node self_check:     ^6^C_{F6}|A;     // "is this working?" — the interference
    node suggestion:     ^0^C_{F6}|A;
    node landed:         ^9^E_{F5}|f;

    osc    breath: Oscillator< signal=cadence, frequency=0.10, sustain=900.0 >;
    filter fb_rc:  LowPass< in=cadence, out=trend, tau=3.0 >;
    feedback trend -> self_substrate [β=0.6];
    filter notch_6: Notch< in=self_check, f0=0.35, Q=4.0 >;   // events/min

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    cjt deliver: CJT< suggestion | self_substrate => landed >
                 [β=1.5, rπ=0.26, g_m=5.74, region=active];

    ramp descend: Ramp< target=rπ, from=1.00, to=0.30, dt=540.0 >;   // 9 min
    ramp emerge:  Ramp< target=rπ, from=0.30, to=1.00, dt=240.0 >;   // 4 min

    probe tp1: rπ;  probe tp2: g_m;  probe tp3: consent;  probe tp4: emerge;
}
```

The notch earns a sentence. It is a notch and **not** a low-pass, deliberately: a low-pass dampens `^6` generally, and you need `^6` — it is what notices you have drifted somewhere you did not intend. What you want rejected is one narrow band, the self-monitoring cadence, at roughly 0.2–0.5 events per minute. Section 11.3 gives the component; `f0 = 0.35`, `Q = 4.0` is the choice for this use.

---

### 17.6 The Ericksonian Indirect Pattern as Filter Bypass

Milton Erickson's contribution, on the public record in his own published case commentaries, was to stop pushing on the `^6` filter and route around it. Understanding *why* that works is not optional here. It is the most-used influence architecture in commercial and political practice, it runs on you regularly, and you cannot see it by watching for what you are told to watch for.

Direct case first. An operator asserts a proposition about you. It reaches `^6^C_{F6}|A`, which decomposes it and tests the parts against `^5^P`; if it threatens something the substrate holds, the result is `^3` Negative and the proposition is rejected. The filter worked. Now the precise claim about the indirect case:

**The filter is not defeated. It is bypassed, while continuing to report success.**

`^6` is still conducting, still decomposing, still returning an honest verdict — on the material it was given. A second path runs from the operator's `^0` to your `^5^P` without passing through it, and nothing in the filter's own output can reveal that path. Monitoring the filter harder cannot detect a bypass. That is topology, not inattention.

Three structural reasons the second path exists. **One: the filter is triggered by addressed propositions.** `^6` engages on Ideas presented as claims about you; a narrative about a third party is not structurally such a claim, so gain toward it is low. Nothing is smuggled — the material was never classified as filter traffic. **Two: the filter has finite throughput.** It decomposes one thing at a time, and interesting surface material occupies it. That is a bandwidth argument, and it predicts something falsifiable: indirection works better as surface interest rises, up to a maximum, past which the surface crowds the embedded content out entirely. **Three: a presupposition is not a proposition at all.** It rides in the structure of an utterance rather than what it asserts, and `^6` decomposes what is asserted. There is no bypass to detect, because the material never entered the filter's input set.

| Class | Structure | Filter relationship | Detection handle |
|---|---|---|---|
| Embedded narrative | Story about a third party | Low gain — not an addressed claim | Whose `^5` was that about, and why told to me *now*? |
| Presupposition | Content in the frame, not the assertion | Never in the input set | Restate it as a flat assertion; presuppositions do not survive restatement |
| Truism chain | `^7` Rhythm of unfalsifiable statements | Drives the filter's gain control down | Count consecutive statements I could not have disagreed with |
| Double bind | Two options, one shared frame | Filter evaluates the choice, never the frame | Is there a third option — and is one of them "none"? |

The truism chain has a mechanism worth naming. **The `^6` filter has automatic gain control.** After a run of inputs that all pass trivially its gain falls — roughly 0.85 per consecutive pass on this book's design figures, so after four it sits near 0.52, and the next statement, which is *not* trivially true, enters at half gain. That is not credulity; it is an efficiency behaviour correct almost everywhere and exploitable here.

#### The counter-circuit: CCB-HYP-DET

You cannot detect a bypass by reading the filter. You detect it by differencing the filter's record against the substrate's actual movement — Section 24.2's differential trick, repurposed.

```cas
board ccb_hyp_det {                       // detection board — build this one
    input:  ambient;
    output: alert;

    node substrate:  ^5^P_{F7}|T;
    node scan_width: ^1^C_{F2}|A;         // Mind: how wide is my scan
    node cadence:    ^7^O_{F4}|E;         // Rhythm: am I locked to something
    node carrier:    ^4^O_{F4}|E;         // Vibration: is one source dominant
    node passed_log: ^6^C_{F6}|A;         // Male: what I actually decomposed
    node drift:      ^5^P_{F7}|T;         // Female: where my position now sits

    diff factor_count: Differential< plus=[scan_width, cadence, carrier, passed_log],
                                     minus=baseline >;
    diff unaccounted:  Differential< plus=drift, minus=passed_log >;
    integ accum: Integrator< in=unaccounted, window=2880.0 >;   // 48 h, minutes

    cjt  trip: CJT< unaccounted | substrate => alert > [β=2.0, sat=0.85];
    fuse hold: Fuse< alert, threshold=0.9, action=defer_decision >;

    probe tp1: factor_count;  probe tp2: unaccounted;
    probe tp3: accum;         probe tp4: alert;
}
```

`unaccounted = drift − passed_log` is the whole board. If your position has moved and you cannot name the proposition you evaluated and accepted that moved it, a bypass carried it. The integrator matters because fractionation is designed to keep every individual reading under any single-session threshold — the CSB's sub-threshold problem, and the same fix. The fuse action is `defer_decision`, not `permanent_block`: the correct output of a detection board is not a refusal. It is time.

[[FIGURE 17-E: Two stacked panels. Upper, "bypass topology": an operator `^0` source at left with two paths to the `^5^P` capacitor at right; the upper path crosses the `^6^C|A` filter block, which carries a green tick and the label "reports CLEAR (honestly)"; the lower path routes around the filter entirely, drawn heavier, labelled "presupposition / embedded narrative", captioned "bypassed, not shorted." Lower, "CCB-HYP-DET": the same `^5^P` node into a differential block, plus input "measured drift", minus input "filter passed-log", output "unaccounted", feeding a 48-hour integrator and a fuse marked defer_decision.]]

**Four checks you can run without any board**, because a detection circuit you can only run on paper is not one. *Scan width (`N`)*: name three things in the room that are not the speaker; if that takes effort, `N` is elevated. *Cadence (`R`)*: regularity that does not track meaning is an oscillator. *Restatement*: say the last thing back as a flat assertion in your own words, and what was presupposed either surfaces as a claim you can evaluate or evaporates. *Drift ledger*: write your position down before, compare after, and treat movement you cannot attribute to a specific argument as the reading that matters.

And the structural exit, which is the opposite of what people try. **Do not argue.** Argument runs through `^6`, and `^6` is the component that was routed around; you cannot repair a bypassed filter by using it harder. `rπ` rises by raising `R_constraint` on the bias path (Section 4.4) — changing the physical and temporal conditions rather than the conversation. Standing up, leaving the room, and putting twenty-four hours between input and decision drops `N`, `R` and `V` at once. `g_m` is a product: break one term and it collapses; break three and it is gone.

If you believe someone is applying coercive influence to you and you are distressed about it, that is a matter for people and not circuits — a clinician, a lawyer, or someone you trust. Nothing in this book substitutes for any of them.

---

### Component and Parameter Table

Every value is a design choice made in this book, not a measurement.

| Parameter | Units | Design range | Failure at other values |
|---|---|---|---|
| `rπ_floor` | — | 0.15 hetero / 0.26 closed loop | Below 0.05 rejected by the validator; approaching 0 is Breakdown (§3.4), irreversible |
| `τ_i` | min | 2 – 6 | Below 2, back-EMF recoil. Above 6, leakage and lost rhythm lock |
| `L_s` session coil | min·Ω_c | 20 – 400 | Under-estimated: ramp too fast, misread as "not suggestible" |
| `V_kick` budget | V_c | ≤ 3 × `V_drive` | Above 3×, `^3^E_{F3}\|f` recoil ends the descent |
| `β` suggestion gain | — | 1.2 – 3.5 hetero; **≤ 2.0 closed loop** | Above 2.0 closed loop: no external check on drift (Ch 25) |
| `g_m` | — | 1.5 – 20 | The parameter nobody logs; every incidental input gets the same multiplier |
| `N`,`R`,`V`,`D` | — | 1.0 – 2.2 each | Three or more rising together without declared consent = induction in progress |
| `β_fb` O→P gain | — | 0.2 normal / 0.9 induction | The whole hetero attack is this one number; nothing illegal occurs |
| `γ` retention | — | 0.25 – 0.45 | Ignored: a run of "brief chats" reaches depth none of them could alone |
| `sat` on veto CJT | — | 0.85 | Below 0.7 the refusal can be argued down — the CCB-MK boundary |
| Emergence `dt` | s | 180 – 360 | Truncated: residual low `rπ` persists outside the session |

---

### Worked Example — A 15-Minute Closed-Loop Session

Own bench, consented. `L_s = 90 min·Ω_c` (low — you asked for this). Rail `V_drive = 20 V_c`. Kick budget set at **1×** rail rather than 3×, because no second party is present to notice a recoil and stop.

**1. Rate ceiling.** `di/dt_max = 20 / 90 = 0.222 A_c/min`. Attention runs `0.75 → 0.10`, so `Δi = 0.65` and the minimum ramp is `2.9 min`.

**2. Pick `τ_i` from the *initial* slope**, `(rπ_0 − rπ_floor)/τ_i` at `t = 0`, with `rπ_0 = 1.00`, `rπ_floor = 0.26`:

```
τ_i = 2.0  ->  0.325 A_c/min  ->  V_kick = 29.3 V_c = 1.46× rail   REJECT
τ_i = 3.0  ->  0.217 A_c/min  ->  V_kick = 19.5 V_c = 0.98× rail   ACCEPT
```

**3. Trajectory**, `rπ(t) = 0.26 + 0.74 · e^(−t/3)`, with `g_m = β/rπ` at `β = 1.5`:

| t (min) | 0 | 3 (1τ) | 6 (2τ) | 9 (3τ) |
|---|---|---|---|---|
| `rπ` | 1.00 | 0.53 | 0.36 | 0.30 |
| `g_m` | 1.5 | 2.8 | 4.2 | 5.0 |

At `t = 9`, `g_m = 5.0`: the same sentence displaces `^5` five times as far as at `t = 0`. That is the entire operational content of "being in trance," as a number.

**4. Shape.** 9 min descent (3`τ_i`) + 2 min suggestion + 4 min linear emergence = **15 minutes**. Emergence kick `0.65/4 = 0.163`, so `V_kick = 14.6 V_c = 0.73×` rail. Inside budget both directions.

**5. St. John's calibration (§5.3).** `t_op = 15 min`; first unprompted confirmation at `t_conf = 45 min`. `η = 1/3`, `η × 1/3 = 1/9`, so `a = 1`, `b = 9`: `β_required = 9`, `n_operations = 1`, `T_manifest = 15 min`. The calibration collides usefully with the parameter table — **`β = 9` is unreachable on a closed loop**, capped at 2.0 for the drift reason in 17.5. You cannot take the `b` route. You take the `a` route: more operations at existing strength, which is what fractionation is for.

**6. The recursion**, `γ = 0.35`:

| Session | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `rπ_0` | 1.00 | 0.74 | 0.57 | 0.46 |
| Time to reach 0.30 | 9.0 min | 7.6 min | 6.1 min | 4.8 min |

Session 4 reaches in under five minutes what session 1 needed nine for; `β_required = 9` is delivered by accumulation rather than amplitude. Now read that row again as a detection artifact rather than a plan. **An outside operator running the same recursion across four brief encounters reaches session-4 depth in five minutes** — and the subject's honest account of the fourth is that they talked to someone for a few minutes. At no point does anything dramatic happen. That is the design intent.

[[FIGURE 17-D: Assembly drawing, CCB-HYP-SELF board, top view, components placed with reference designators — OSC1 breath oscillator at the input edge, F1 the τ_i = 3 min RC, C1 the `^5^P` substrate capacitor centre-board, N1 the notch (f0 = 0.35, Q = 4.0) on a stub off C1, Q2 the delivery CJT, D1–D2 the descent diodes, R1 the emergence ramp block at the output edge. Four circled test-point callouts: TP1 on the `rπ` node, TP2 on the `g_m` summing node, TP3 on the consent rail, TP4 on the emergence output. Ruled BOM box lower right listing ref, component, CAS state and key parameter for all nine parts, footnoted "closed loop — operator is subject — no DETECTION-ONLY banner required."]]

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `rπ` | Bias resistance | Follows `rπ_floor + (rπ_0 − rπ_floor)e^(−t/τ_i)`. Never below `rπ_floor`. Under 0.15 closed-loop means the factor arithmetic was wrong, not that you went deep |
| **TP2** | `g_m` | Four-factor product | ≤ 6 closed loop, ≤ 20 hetero. **Three or more factors rising together without declared consent is the detection trip** |
| **TP3** | `veto` | ARMED / DISARMED, **per register member** | `\|f` and `\|T` ARMED at every sample including the deepest. `\|A` may attenuate with `rπ`. All three attenuating together is the CCB-MK boundary; the session ends there |
| **TP4** | `emerge` | Recovered `rπ` vs baseline | ≥ 0.90 × `rπ_0` by end of emergence. A shortfall present 30 minutes later is residual depth: re-run the ramp |

Read them TP3, TP2, TP1, TP4 — confirm the veto is armed before anything else, watch the factors, follow the descent, verify you came back. TP3 first is not ceremony. It is the only reading that distinguishes this board from the previous chapter's.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Ramp overrun** | `di/dt` set by the operator's schedule, not the subject's `L_s` | Stiffening and `^3^E_{F3}\|f` recoil in the first minute; descent stalls above 0.6 | Recompute `τ_i` from `V_kick ≤ 3 × V_drive`. The subject was never the variable |
| **Ramp underrun** | Run past `0.6 τ_leak`; `^7` lock lost | Descent plateaus, then *rises*; attention leaves the carrier | Shorten to the computed window; restore the oscillator before re-ramping |
| **`g_m` runaway** | `β` logged, `g_m` not | A preference the subject cannot source, tracing to an incidental remark | Cap `g_m`; keep a verbatim log. Everything said at `g_m = 20` was a suggestion |
| **Veto in series** | `^3^P` drawing bias through `decomp` instead of `^5^P` | TP3 shows all three register members attenuating together | None. Not a tuning fault — the board is CCB-MK (Ch 16). Stop |
| **Emergence truncated** | Session ended on a step, not a ramp | TP4 under 0.9 × baseline; elevated `g_m` persisting into ordinary life | Re-run the reverse ramp. Never end on a step; budget the kick both ways |
| **Unrecallable anchor** | `^8` → `^9` installed below the recall threshold | The pair fires; the subject cannot name when it was installed or cancel it | Trigger installation (§16.3). Counter-circuitry is §16.6–16.7, not this chapter |
| **Closed-loop over-gain** | Self-board at `β > 2.0` | Suggestions escalate session to session with no external check | Restore `β ≤ 2.0`; take the `a` route, not the `b` route |

---

### What This Chapter Established

- **`rπ = β / g_m` is an identity, not an independent parameter.** Trance needs `β` up and `rπ` down, forcing `g_m` up faster — 20× against 3× at the deep design point. "Suggestible" names that ratio.
- **The risk is in `g_m`, not `β`.** `g_m` has no input filter, so every incidental remark is amplified by the same factor as the intended suggestion.
- **`g_m = g_0 · N · R · V · D`** — four ordinary factors multiplied. Three or four rising together around someone who benefits from your bias being soft is an induction, whatever it is called.
- **The ramp is bounded at both ends** — back-EMF above, leakage and lost rhythm lock below. The literature's "about ten minutes" is that window for a typical `L_s`, and it moves when `L_s` moves.
- **`^1¹` is not an eleventh Noetic.** The conscious/subconscious split is `^1^C|A → ^1^C|f`. The real gate is `^6^C_{F6}|A` in series, and its parameter is a gain, not a door.
- **The whole hetero-hypnotic attack is one number:** `β_fb` on the lawful O→P path (§8.4), driven 0.2 → 0.9. Nothing ascends illegally.
- **`^3^P_{F7}|⟨A,f,T⟩` is co-presence, not fusion**, and trance attenuates only `|A`. All three attenuating together is the boundary with Chapter 16, and the only one that matters.
- **Indirect patterns bypass the `^6` filter while it honestly reports clear.** You detect that as `drift − passed_log`, and the exit is conditions rather than argument: `g_m` is a product, so breaking `N`, `R` and `V` collapses it.

---

### Exercises

*(Answers in Appendix H.)*

**17.1** A subject sits at `β = 2.0`, `rπ = 0.40`. Compute `g_m`. The operator wants `rπ = 0.20` with `β` held at 2.0: what must `g_m` become, and by what factor has framing sensitivity risen against the waking reference of 1.0? Name the factor of the four that most likely supplied the rise, and why.

**17.2** A guarded subject has `L_s = 300 min·Ω_c` on a 24 V_c rail, attention to be moved from 0.85 to 0.15 A_c. Compute the minimum ramp time holding `V_kick ≤ 3 × V_drive`, then for a 1× budget. Say whether the second is a session anyone would sit through, and what that implies about operating on guarded subjects.

**17.3** Explain why the recoil at an over-fast induction is written `^3^E_{F3}|f` and not `^6^E_{F6}|A`. Reference the canonical definition of `^3` Negative, say what the `^6` Male state is doing instead, and when it arrives.

**17.4** A colleague reports that a two-hour conversation changed their position on a workplace question, that it was pleasant, and that they cannot reconstruct the argument that changed their mind. Using the CCB-HYP-DET listing, name which probe this is a reading of, state what `unaccounted` evaluates to, and give the one manual check from §17.6 that would have surfaced it during the conversation rather than after.

**17.5 (Design)** Specify a 20-minute closed-loop session for `L_s = 150 min·Ω_c` on an 18 V_c rail, holding `V_kick ≤ 1 × V_drive` in both directions, with `rπ_floor = 0.26` and `β = 1.5`. Produce (a) maximum `di/dt` and the resulting `τ_i`; (b) the `rπ` trajectory at 1τ, 2τ, 3τ; (c) the emergence `dt`; (d) a CCDL fragment declaring the oscillator, the RC on the O→P path, the notch, the delivery CJT, both ramps, and four probes. It must compile — check every diode direction and every register before you submit it.

**17.6 (Marquee)** An operator wants an anchor the subject can recall and cancel, and asks you to specify the recall condition as a circuit property rather than a promise.

a) Write, in CCDL, an anchor stage plus whatever components make the `^8` → `^9` pair unable to fire unless a recallable record of its installation exists in the subject's `^5`. Name the enforcing component and the parameter that sets the recall threshold.

b) Explain why an anchor installed at `g_m = 20` is harder to make recallable than the same anchor at `g_m = 5`, in terms of what `^1` is doing at each depth.

c) State the one thing your circuit still cannot guarantee, and why that residual is the reason §17.4 carries the DETECTION-ONLY banner even though every stage in it has a consented reading.
