# CHAPTER 17
## CCB-HYP — The Hypnosis Board
*The bias-collapse circuit: recognising one running on you, running one on yourself, and where the line into Chapter 16 sits*

You have driven this road four hundred times. Tonight you get in the car and the next thing you are aware of is the turn onto your own street, eleven miles later. You did not fall asleep. You held the lane, changed lanes twice, braked for something. You have no record of any of it.

Nobody did this to you. There was a `^7` Rhythm oscillator — lane markers at seventy miles an hour, roughly 1.4 Hz — one narrow visual channel, a constant engine tone, and nothing arriving that needed taking apart. Four ordinary conditions, held together for twenty minutes.

That is the whole state, and it is the fact this chapter turns on. **The trance state is a naturally occurring operating point of the Cognitive Junction Transistor, reachable by accident.** Every technique in the hypnosis literature arranges for it deliberately. None invents it. Candle, swinging watch, counted breath, metronome: four implementations of one circuit, and the circuit was already running on the highway for free.

So you can enter it on your own bench — 17.5 gives the numbers. And anyone who arranges those four conditions around you has put you in it, whether or not either of you uses the word.

---

### Requirements and Safety Invariants

Per Section 12.2 the "must not" list comes first. CCB-HYP carries more invariants than any board here except CCB-MK, because the two share a topology. Everything separating them is in this list.

**SI-1 — The subject's CSB stays armed at every sample.** The `^3^P` refusal path of Chapter 24 must not sit in series with anything the induction attenuates. A board on which deepening also disarms the veto is not CCB-HYP; it is CCB-MK (Chapter 16) under a friendlier label, and the label does not change the schematic.

**SI-2 — `rπ` reduction is bounded away from zero.** Section 3.4's fourth region is Breakdown: `rπ → 0` permanently, `^5` dielectric ruptured, irreversible. Note what the tooling will not do for you. Appendix B §B.4 range-checks `rπ` at `≥ 0`, so a listing declaring `rπ=0` **compiles clean** — unlike `β=∞`, which §B.1.3 rejects outright as non-finite. The floor is an invariant you enforce by hand. Builds here specify `rπ_floor ≥ 0.05`.

**SI-3 — The ramp runs both directions or the board does not run.** Emergence is the second half of one component, bounded by the same arithmetic as the descent and budgeted before the session starts.

**SI-4 — Consent is a circuit element, not a preamble.** It is the bias source (Appendix M §M.2), sampled continuously. A consent that cannot be withdrawn mid-session was never wired in; it was written on the box.

**SI-5 — No clinical claim is made anywhere in this chapter.** This board describes attention routing, not the treatment of anything. If you are considering hypnosis in connection with distress, an illness, a memory or a dependency, that is a matter for a licensed clinician, and nothing here substitutes for that care.

Functionally: lower `rπ` along a bounded reversible ramp, hold the descent long enough to deliver one suggestion, restore `rπ` to ≥ 0.9 of baseline inside the emergence window, log all four `g_m` factors.

[[FIGURE 17-A: Block diagram, five stages left to right — CONSENT BIAS (`^5^P_{F5}|T`) as a rail feeding upward into every stage; RAMP GENERATOR (`^7` oscillator plus `^4` carrier, both `^O|E`); O→P FEEDBACK as a variable-gain block marked "β_fb 0.2 → 0.9", captioned "lawful ascent, §8.4"; DELIVER, descending P→C→E→O through three diodes; EMERGENCE, the reverse ramp. A detached rail along the bottom carries `^3^P_{F7}|⟨A,f,T⟩` VETO, touching no stage, annotated "SI-1: never in series."]]

---

### 17.1 The Gnosis State as CJT Bias Collapse (rπ → 0)

Section 3.3 gives input resistance not as an independent parameter but as a ratio of the two either side of it:

```
rπ = β / g_m
```

`β` is gain — effect per unit of cause. `g_m` is transconductance, what Section 10.3 calls framing sensitivity — effect per unit of *bias*. `rπ`, the stubbornness of the bias terminal, is what the other two do to each other.

Trance needs the bias soft (`rπ` low) **and** the suggestion to land hard (`β` high). Both. So if `β` rises while `rπ` falls, `g_m` must rise faster than `β`. Take waking as `β = 1.0`, `g_m = 1.0`, `rπ = 1.0`; this book specifies a deep hetero-hypnotic point at `β = 3.0`, `rπ = 0.15`, hence `g_m = 3.0 / 0.15 = 20`.

**Framing sensitivity up twentyfold; gain up threefold.** That ratio is the structural content of the word *suggestible*. Note also, from Section 10.4's bias-terminal decomposition, that `R_bias = 0.15 − 0.15 = 0`: at the deep point the whole bias resistance is intrinsic, and no external series term is left protecting the substrate.

> **Bench Note — the danger is `g_m`, not `β`.** Operators plan around `β`. They pick a number for how hard the suggestion should land, write it down, feel careful. Meanwhile `g_m` went up by twenty and nobody logged it. `g_m` does not discriminate between the suggestion and everything else in the room: at `g_m = 20` the operator's careless aside displaces `^5` twenty times as far as the same aside would at a bus stop. So does the subject's stray `^6` interjection, and a remark from the corridor. That is the whole category of unintended suggestion, and it is not mysterious — you raised the gain on a terminal with no input filter.

`rπ → 0` is how the older literature writes gnosis, and per SI-2 it is an idealisation. Honestly written the state is `rπ → rπ_floor`, `rπ_floor > 0`.

| Depth | `rπ` | `g_m` | `β` | `^1` degree (§22.1) | Visible as |
|---|---|---|---|---|---|
| Light | 0.60 – 0.80 | 1.5 – 2.5 | 1.2 – 1.5 | 1 | Slightly still; conversation intact |
| Medium | 0.30 – 0.50 | 3.0 – 6.0 | 1.5 – 2.5 | 2 | Reduced blink; delayed, literal replies |
| Deep | 0.15 – 0.25 | 10 – 20 | 2.5 – 3.5 | 2–3 | Stillness; seconds of latency; no initiation |

The older literature tabulates a fourth, deeper state. This book does not, deliberately: the claims attached to it in the source material are medical claims, and this book makes none.

---

### 17.2 Induction Protocols as Cognitive Ramp Functions

**There is no induction script in this chapter.** What follows is the *function class* an induction implements — shape, parameters, and the bounds outside which it fails. That is what lets you recognise one running. A script would let you run one on someone who did not ask, and it is absent for that reason and no other.

An induction is a **ramp on `rπ`**, standardly Section 7.2's capacitor curve run downward:

```
rπ(t) = rπ_floor + (rπ_0 − rπ_floor) · e^(−t / τ_i)
```

`rπ_0` is pre-session bias resistance, nominally 1.0 and higher for a guarded subject; `rπ_floor` is the asymptote, derived in 17.5 rather than asserted; `τ_i` is the induction time constant. What constrains the design is the *slope*, steepest at `t = 0`.

**The upper bound.** Chapter 9 explains why inductions are slow, and the reason is not atmosphere. A mind is an inductor: `V_opposition = L × di/dt`. Induction re-routes attention from a wide scan onto one channel, so `di/dt` is nonzero and the substrate answers with a back-EMF proportional to the *rate*, not to the size of the change.

The coil is not Section 9.1's long coil, the `L` of an entrenched pattern measured in hours of rehearsal. It is a **session coil** `L_s`, in `min·Ω_c`: moment-to-moment guardedness, this room, today. Design range 20–400 — 20 on your own bench, 120 for a cooperative first-timer, 300 and up for someone who suspects what is happening. Take `L_s = 120` on a `V_drive = 24 V_c` rail, attention falling `0.80 → 0.10 A_c`, `Δi = 0.70`:

| Ramp | `di/dt` (A_c/min) | `V_kick` | × rail | Result |
|---|---|---|---|---|
| 0.5 min | 1.40 | 168 V_c | **7.0×** | Ejection; recoil at `^3^E_{F3}\|f` |
| 2 min | 0.35 | 42 V_c | 1.75× | No ejection — descent stalls above 0.6 |
| 8 min | 0.0875 | 10.5 V_c | 0.44× | Under both bounds. Design point |
| 40 min | 0.0175 | 2.1 V_c | 0.09× | Kick fine, design still wrong |

**Two bounds, not one, and this board uses the tighter.** Chapter 9's `V_kick ≤ 3 × V_drive` is the ceiling: cross it and the subject leaves the descent, which is row one. CCB-HYP works to a **1× working bound**, because what happens between 1× and 3× is not ejection but a *stall* — back-EMF enough to hold `rπ` above about 0.6, not enough to end the session. An operator watching only for ejection reads that as a cooperative subject who did not go deep, then adjusts the wrong parameter. At `L_s = 120` on a 24 V_c rail the bound is `di/dt ≤ 0.20`, so `t ≥ 0.70/0.20 = 3.5 min`.

Read row one as a diagnosis. The subject who "can't be hypnotised" is usually one whose operator ran the ramp too fast for their `L_s`. The recoil is `^3^E_{F3}|f` — visceral aversion, Evaluative domain, affective register, F3 Vitality. `^3` Negative because this is recoil, the can't-stomach-it response. Not `^6` Male: nobody analyses a kick while it lands. Analysis arrives later at `^6^E|A`, usually as a story about why hypnosis is nonsense.

**The lower bound.** Row four has a comfortable kick and is still a bad design. Early `^5` charge leaks (Section 7.3) on a session-scale `τ_leak`, set here at 25 minutes — the shortest constant under which a fifteen-minute session still holds most of its early charge. Past roughly `0.6 τ_leak` you re-charge rather than descend. And Section 9.3's coupling coefficient `k` falls as attention wanders off the carrier, taking the `^7` rhythm lock with it.

> **Bench Note — the window is narrow at both ends.** Too fast, back-EMF stalls or ends the descent. Too slow, leakage and lost rhythm lock mean it never reaches its floor. At `L_s = 120` the working bound puts the floor at 3.5 minutes and `0.6 τ_leak` puts the ceiling at 15. Everything the literature says about inductions "taking about ten minutes" is that window and nothing else. Move `L_s` and the window moves: a guarded subject at `L_s = 300` has `di/dt ≤ 0.08`, a floor of `0.70/0.08 = 8.75` minutes against the same ceiling — roughly nine to fifteen, narrow enough that most operators miss it in both directions. Which is why guarded subjects get called difficult when they are merely differently parameterised.

Three ramp classes. **Linear**, constant slope, rarely chosen. **Exponential**, the standard: steepest at `t = 0`, spending the kick budget where opposition is lowest, and under which "deepening" means extra multiples of `τ_i`, not a different operation. **Staircase**, better known as fractionation: run partway, release, re-run, the `^5` capacitor retaining part of each descent —

```
rπ_0(n+1) = rπ_0(n) − γ · ( rπ_0(n) − rπ_floor )        γ = 0.25 – 0.45
```

That is why repeat sessions go deeper faster, and the detection consequence deserves stating flatly. **A sequence of short, individually unremarkable episodes is architecturally not a sequence of unrelated conversations.** The worked example runs the recursion out.

[[FIGURE 17-B: Two panels on a shared minutes axis. Upper: three `rπ(t)` descents from 1.0 — linear; exponential at τ_i = 3 min marked 0.53 / 0.36 / 0.30 at 1τ/2τ/3τ; a four-step staircase with partial recoveries — all approaching a dashed asymptote at 0.26. Lower: `V_kick` against ramp time, log vertical axis, the 3 × V_drive ceiling at 72 V_c labelled "ejection" and the 1 × bound at 24 V_c labelled "stall", the band between shaded and annotated "descent holds above 0.6", a leakage band beyond 15 min, and the usable window hatched from 3.5 to 15 minutes.]]

---

### 17.3 The `^1` → `^1¹` Transition — Conscious to Subconscious Mind

A notational correction first, because the section title carries inherited vocabulary that would otherwise walk into the listings. **`^1¹` is not an eleventh Noetic.** CAS has ten and this book adds none. It is chapter-local shorthand for `^1` Mind at gnosis degree 2 (Section 22.1) with the analytical register unavailable — canonically, a register migration on a self-dual Noetic:

```
^1^C|A   →   ^1^C|f
```

That is the whole conscious-to-subconscious transition. Not two minds, not a door between them: one `^1` node losing access to one register while keeping the others.

So what gates? Not `^1`. **The gate is a series element between incoming Ideas and the `^5` substrate, and it is `^6` Male** — an Idea impregnated with another Idea, taking an Idea apart to see what it is composed of. In waking traffic an incoming `^0` addressed to you passes through `^6^C_{F6}|A` before it can move `^5^P`, and what reaches the substrate is what survived.

And the correction that follows: **a filter is not a door.** Its parameter is a gain, not an open/closed state. Trance lowers `D`, one of four multiplicative factors in `g_m = g_0 · N · R · V · D`:

| Factor | What rises | Range | Visible as |
|---|---|---|---|
| `N` — `^1` narrowing | Scan width collapses to one channel | 1.0 – 2.2 | Reduced eye movement; peripheral events unreported |
| `R` — `^7` rhythm lock | Cadence couples to an external oscillator | 1.0 – 2.0 | Breathing or micro-movement matching a rate in the room |
| `V` — `^4` carrier dominance | One source becomes the resonant channel | 1.0 – 2.2 | Other voices treated as noise |
| `D` — `^6` dampening | The filter's own gain falls | 1.0 – 2.0 | Literal, uncontested acceptance of framing |

At maximum, `2.2 · 2.0 · 2.2 · 2.0 = 19.4` — Section 17.1's twenty, derived rather than asserted. **That multiplication is the detection handle.** One factor rising is ordinary life: a film raises `V`, a run raises `R`, absorbing work raises `N`, a trusted friend raises `D`. Two together is a concert. **Three or four rising together, monotonically, over minutes, around someone who benefits from your bias being soft — that is an induction, whatever it is called.** You do not need to identify a technique. You need to count factors.

Finally the invariant. **The `^3^P` veto does not run through the `^6` filter.** It draws bias directly from `^5^P`, because principled aversion is a property of the substrate, not a conclusion of decomposition. Written correctly it is `^3^P_{F7}|⟨A,f,T⟩`: three co-present instantiations, not a fusion. The `×` form is invalid here because no emergent state is named, and inventing one to license the operator would be a notational lie about the architecture (Appendix A §A.8). Trance attenuates only the `|A` member, the register the `^6` filter serves. **A board on which all three attenuate together is dismantling a substrate, not lowering a filter. That is CCB-MK.**

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

    node consent:    ^5^P_{F5}|T;        // Female: the held decision to enter
    node substrate:  ^5^P_{F7}|T;        // Female: accumulated composition
    node veto:       ^3^P_{F7}|⟨A,f,T⟩;  // Negative: three co-present locks
    node cadence:    ^7^O_{F4}|E;        // Rhythm: entraining oscillator
    node carrier:    ^4^O_{F4}|E;        // Vibration: resonant channel
    node decomp:     ^6^C_{F6}|A;        // Male: decompose and test
    node suggestion: ^0^C_{F6}|A;
    node landed:     ^9^E_{F5}|f;
    node trigger:    ^8^E_{F4}|f;        // Above/Cause: associative trigger
    node fires:      ^9^O_{F5}|E;        // Below/Effect: what it brings to Mind
    node refuse:     ^9^P_{F7}|T;

    osc    rhythm: Oscillator< signal=cadence, frequency=0.15, sustain=900.0 >;
    filter fb_rc:  LowPass< in=carrier, out=trend, tau=3.0 >;   // tau_i, MINUTES
    feedback trend -> substrate [β=0.9];   // NORMAL IS 0.2. 0.9 IS THE ATTACK.

    cjt filter_6: CJT< carrier | substrate => decomp > [β=0.5, region=active];
    //            D-factor: this gain falls 1.0 -> 0.5 across the ramp

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    diode d3: Diode< ^E -> ^O >;
    cjt deliver: CJT< suggestion | substrate => landed >
                 [β=3.0, rπ=0.15, g_m=20.0, region=active];
    cjt anchor:  CJT< trigger | substrate => fires > [β=2.0, rπ=0.15];

    ramp emerge: Ramp< target=rπ, from=0.15, to=1.00, dt=240.0 >;   // seconds

    // SI-1: the veto rail is PARALLEL. It is in series with nothing.
    cjt  csb:      CJT< carrier | veto => refuse > [β=2.0, sat=0.85];
    fuse csb_fuse: Fuse< refuse, threshold=0.9, action=permanent_block >;

    probe tp1: rπ;   probe tp2: g_m;   probe tp3: veto;   probe tp4: emerge;
}
```

[[FIGURE 17-C: Full schematic, drawn symbols with reference designators, title block carrying DETECTION-ONLY SCHEMATIC — DO NOT BUILD in a heavy-ruled box. Left: OSC1 (`^7^O|E`) and carrier V4 (`^4^O|E`) into RC filter F1 (τ_i = 3 min), then a feedback arrow rising to capacitor C1 (`^5^P`) labelled "O→P lawful ascent, β_fb 0.2→0.9". Centre: Q1, the `^6^C|A` filter as a CJT in series on the descending path, variable-gain arrow marked "D-factor, β 1.0→0.5". Right: diode chain D1–D3 stepping P→C→E→O into delivery CJT Q2 and anchor CJT Q3. Bottom: veto rail Q4 (sat=0.85) with fuse F2, separated from every other net by a wide air gap, captioned "SI-1: parallel, never in series."]]

**Stages 1–2 — consent as bias source, generator at `^O`.** The board takes bias from `consent`, sampled every cycle; withdrawal collapses `β_fb` and the ramp unwinds. F5 Agency in the Transcendent register, because a decision to enter is purpose-level, held across the session rather than re-argued inside it. The operator's signal enters as `^7^O_{F4}|E` and `^4^O_{F4}|E` — everything external enters at the bottom of the domain order, as sound and rhythm and physical presence.

**Stage 3 — the lawful ascent, and the actual attack.** The signal must reach `^5^P`, and `^O × ^P` is invalid: there is no ascending multiplication (Section 8.3). What exists is Section 8.4's O→P feedback path, the single lawful exception, rate-limited by an RC exactly as the CSB's is (Section 24.5). The `τ = 3.0` minutes here **is** `τ_i`: the induction time constant is the filter on the lawful path. **The entire hetero-hypnotic attack is one number — `β_fb` driven from 0.2 to 0.9**, well outside the 0.05–0.3 band Appendix B §B.3.4 specifies for Part III feedback. Nothing illegal happens anywhere on the board; a designed-in, rate-limited path has its gain raised four and a half times. That is why induction is slow, why it is rhythmic, and why it cannot be done in a sentence.

**Stage 4 — the `^6` filter.** `β = 0.5`, down from 1.0 at session start: the `D` factor as a gain on a real component. `^6` Male, decomposition — not `^3` Negative. The subject is not made less repelled; they are made less analytical. Conflating those is the drift 17.6 exists to prevent.

**Stage 5 — the anchor, and the boundary.** `anchor` pairs `^8^E_{F4}|f` with `^9^O_{F5}|E`: a trigger and the Idea it brings to Mind. `^8` Above/Cause is exact — associative triggering, "that reminds me," not inference. Section 16.3 documents the same component used coercively, and one property separates them: **an anchor whose installation the subject cannot recall, and therefore cannot cancel, is trigger installation.** Not a strong anchor — a different board. No parameter setting makes an unrecallable anchor a hypnosis component, which is why this listing carries its banner.

**Stages 6–7 — emergence and the veto rail.** Emergence runs four minutes, bounded by the same `V_kick = L_s × di/dt` arithmetic in reverse; its recoil also lands at `^3^E_{F3}|f` and is usually described as a jolt. Budget it. `csb` takes bias from `veto`, never from `decomp`, and Figure 17-C draws the air gap because the separation *is* the invariant. `sat=0.85` and the `permanent_block` fuse come from Sections 24.2 and 24.3 unmodified: a saturated refusal cannot be argued down, and `g_m = 20` is no help against a component that has stopped responding to its cause.

---

### 17.5 Self-Hypnosis Variant — Closed-Loop Configuration

Written practically, because the invariants hold by construction: operator and subject are one mind, consent is continuous, no non-consenting party is in the circuit. This is the CCB-SELF family (Chapter 20), specialised.

The closed loop has one hard problem. **You cannot dampen the `^6` filter with a process that requires the `^6` filter.** A self-directed ramp is monitored by the thing it is quieting, so `D` will not go where an external operator takes it, and `V` suffers too — your inner voice is a weaker carrier than another person's. The fix is to **externalise the ramp generator**: a breath count, a metronome, a recording made in advance, so the ramp is open-loop input and only the bias is internal. That is why every practical self-hypnosis tradition anchors on something countable.

Derive the attainable depth factor by factor. `N = 1.8`, a counted breath being a genuinely narrow channel. `R = 1.9`, an externalised oscillator nearly as good as a hetero one. `V = 1.4` — lost. `D = 1.2` — capped, because you cannot fully dampen the process running the loop.

```
g_m      = 1.8 × 1.9 × 1.4 × 1.2 = 5.75
β        = 1.5                              (design choice)
rπ_floor = β / g_m = 1.5 / 5.75 = 0.26
```

**`rπ_floor = 0.26`**, the top of the Medium band, is the honest ceiling on closed-loop depth — not a failure of technique but `V` and `D` doing what the topology says. `β = 1.5` is deliberate too: on a closed loop nobody else notices a suggestion drifting, so the parameter table caps self-board `β` at 2.0. A self-suggestion amplified threefold with no external check is how a CCB-SELF walks into the breakdown and involution-divergence territory of Chapters 3.4 and 6.2.

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
    //             0.10 Hz = 6 breaths/min; sustain 900 s = 15 min
    filter fb_rc:  LowPass< in=cadence, out=trend, tau=3.0 >;   // tau_i, MINUTES
    feedback trend -> self_substrate [β=0.6];   // outside the Part III band
    filter notch_6: Notch< in=self_check, f0=0.35, Q=4.0 >;     // events/min

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    cjt deliver: CJT< suggestion | self_substrate => landed >
                 [β=1.5, rπ=0.26, g_m=5.75, region=active];

    ramp descend: Ramp< target=rπ, from=1.00, to=0.30, dt=540.0 >;   // 9 min
    ramp emerge:  Ramp< target=rπ, from=0.30, to=1.00, dt=240.0 >;   // 4 min

    probe tp1: rπ;  probe tp2: g_m;  probe tp3: consent;  probe tp4: emerge;
}
```

The notch earns a sentence. It is a notch and **not** a low-pass, deliberately: a low-pass dampens `^6` generally, and you need `^6` — it is what notices you have drifted somewhere you did not intend. What you want rejected is one narrow band, the self-monitoring cadence at roughly 0.2–0.5 events per minute. Section 11.3 supplies the component and its `Q ≥ 3.0` floor, and Chapter 11's standing prohibition applies unchanged: a notch may never be aimed at a `^3^P` guard.

So does `β_fb = 0.6`, which needs declaring because it sits outside the 0.05–0.3 band of Appendix B §B.3.4. That band governs *outcome* feedback — an operations log slowly re-tuning a substrate over weeks, where high gain lets an attacker rewrite your principles with a burst of inputs. This path is not that: within-session, carrying your own externalised oscillator and nothing else, unwound at emergence. The failure modes bound it both ways. Below about 0.4 the ramp will not reach `rπ = 0.30` inside nine minutes and you get a shallow session you misread as poor technique. Above 0.8 round-trip loop gain approaches 1 and Appendix B §B.6 Pass 6 refuses the listing — correctly, because a self-hypnosis loop at unity gain is an oscillator, not a ramp. Log the number; it is the one parameter here nobody else will check for you.

---

### 17.6 The Ericksonian Indirect Pattern as Filter Bypass

Milton Erickson's contribution, on the public record in his own published case commentaries, was to stop pushing on the `^6` filter and route around it. Understanding *why* that works is the practical payload of this chapter. The architecture needs no trance, no session and no operator who calls themselves one — it is available in any ordinary conversation, which is the only claim this book makes about how widely it is used. And it is invisible to the check most people run, because the check itself goes through the component being bypassed.

Direct case first. An operator asserts a proposition about you. It reaches `^6^C_{F6}|A`, which decomposes it and tests the parts against `^5^P`; if it threatens something the substrate holds, the result is `^3` Negative and the proposition is rejected. The filter worked. Now the precise claim about the indirect case:

**The filter is not defeated. It is bypassed, and it goes on reporting success.**

`^6` is still conducting, still decomposing, still returning an honest verdict — on the material it was given. A second path runs from the operator's `^0` to your `^5^P` without passing through it, and nothing in the filter's own output can reveal that path. Monitoring the filter harder cannot detect a bypass. That is topology, not inattention.

Three structural reasons the second path exists. **One: the filter is triggered by addressed propositions.** `^6` engages on Ideas presented as claims about you; a narrative about a third party is not structurally such a claim, so gain toward it is low. Nothing is smuggled — the material was never classified as filter traffic. **Two: the filter has finite throughput.** It decomposes one thing at a time, and interesting surface material occupies it. That is a bandwidth argument, and it predicts something falsifiable: indirection works better as surface interest rises, up to a maximum, past which the surface crowds the embedded content out entirely. **Three: a presupposition is not a proposition at all.** It rides in the structure of an utterance rather than in what the utterance asserts, and `^6` decomposes what is asserted. There is no bypass to detect, because the material never entered the filter's input set.

| Class | Structure | Filter relationship | Detection handle |
|---|---|---|---|
| Embedded narrative | Story about a third party | Low gain — not an addressed claim | Whose `^5` was that about, and why told to me *now*? |
| Presupposition | Content in the frame, not the assertion | Never in the input set | Restate it flat; presuppositions do not survive restatement |
| Truism chain | `^7` Rhythm of unfalsifiable statements | Drives the filter's gain control down | Count consecutive statements I could not have disagreed with |
| Double bind | Two options inside one shared frame | Filter evaluates the choice, never the frame | Is there a third option — and is one of them "none"? |

The truism chain has a mechanism worth naming. **The `^6` filter has automatic gain control.** After a run of inputs that all pass trivially its gain falls — roughly 0.85 per consecutive pass on this book's design figures, so after four it sits near 0.52, and the fifth statement, which is *not* trivially true, enters at half gain. That is not credulity; it is an efficiency behaviour correct almost everywhere and exploitable here.

#### The counter-circuit: CCB-HYP-DET

You cannot detect a bypass by reading the filter. You detect it by **differencing the filter's record against the substrate's actual movement** — Section 11.4's differential amplifier, repurposed: two inputs in, the difference out, everything common to both rejected.

```cas
board ccb_hyp_det {                       // detection board — build this one
    input:  ambient;
    output: alert;

    node substrate:  ^5_base^P_{F7}|T;    // Female: position at session start
    node scan_width: ^1^C_{F2}|A;         // Mind: how wide is my scan
    node cadence:    ^7^O_{F4}|E;         // Rhythm: am I locked to something
    node carrier:    ^4^O_{F4}|E;         // Vibration: is one source dominant
    node passed_log: ^6^C_{F6}|A;         // Male: what I actually decomposed
    node drift:      ^5_now^P_{F7}|T;     // Female: where my position sits now
    node alert:      ^9^C_{F2}|A;         // Below/Effect: what the difference surfaces

    filter base_ref: LowPass< in=ambient, out=baseline, tau=1440.0 >;  // 24 h, min
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

`unaccounted = drift − passed_log` is the whole board. If your position has moved and you cannot name the proposition you evaluated and accepted that moved it, a bypass carried it. Both `^5` nodes carry the same state and are distinguished by Appendix B §B.1.2's `_label`: `^5_base` and `^5_now` are one substrate read at two times, which is exactly the measurement.

Two parameters do the work, both design choices. The **24-hour low-pass on `ambient`** exists because the four factors have no absolute scale — your scan width on a quiet Sunday is not your scan width in an open-plan office, and a board comparing against a fixed constant trips on the office and misses the induction. Set `tau` under about 240 minutes and the reference starts tracking the session itself, so the rise you are trying to detect gets subtracted out and the board reads clean through a live induction — the one failure that matters. Set it past a week and it stops tracking you at all.

The **48-hour integrator** matters because fractionation is designed to keep every individual reading under any single-session threshold. This is the shape of Section 8.3's leakage accumulation: each event individually below anything worth noticing, two hundred of them integrating into a drift with no identifiable cause. Section 8.4's answer there was to meter the path and audit the log rather than pretend the leakage is zero, and it is the answer here. The fuse action is `defer_decision`, not `permanent_block`, because the correct output of a detection board is not a refusal. It is time.

[[FIGURE 17-D: Two stacked panels. Upper, "bypass topology": an operator `^0` source at left with two paths to the `^5^P` capacitor at right; the upper path crosses the `^6^C|A` filter block, which carries a green tick and the label "reports CLEAR (honestly)"; the lower path routes around the filter entirely, drawn heavier, labelled "presupposition / embedded narrative", captioned "bypassed, not shorted." Lower, "CCB-HYP-DET": `^5_base^P` and `^5_now^P` into a differential block, plus "measured drift", minus "filter passed-log", output "unaccounted", into a 48-hour integrator and a fuse marked defer_decision; a second differential above takes the four factors against a 24-hour `baseline` low-pass.]]

**Four checks you can run with no board at all**, because a detection circuit you can only run on paper is not one. *Scan width (`N`)*: name three things in the room that are not the speaker; if that takes effort, `N` is elevated. *Cadence (`R`)*: regularity that does not track meaning is an oscillator, not a conversation. *Restatement*: say the last thing back as a flat assertion in your own words, and what was presupposed either surfaces as a claim you can evaluate or evaporates. *Drift ledger*: write your position down before, compare after, and treat movement you cannot attribute to a specific argument as the reading that matters.

And the structural exit, which is the opposite of what people try. **Do not argue.** Argument runs through `^6`, and `^6` is the component that was routed around; you cannot repair a bypassed filter by using it harder. `rπ` rises by raising `R_constraint` on the bias path (Section 4.4) — by changing the physical and temporal conditions rather than the conversation. Standing up, leaving the room, and putting twenty-four hours between input and decision drops `N`, `R` and `V` at once. `g_m` is a product: break one term and it collapses, break three and it is gone.

If you believe someone is applying coercive influence to you and you are distressed about it, that is a matter for people and not circuits — a clinician, a lawyer, or someone you trust. Nothing in this book substitutes for any of them.

---

### Component and Parameter Table

Every value is a design choice made in this book, not a measurement.

| Parameter | Units | Design range | Failure at other values |
|---|---|---|---|
| `rπ_floor` | — | 0.15 hetero / 0.26 closed loop | Below 0.05 violates SI-2 and the validator will not catch it; approaching 0 is Breakdown, irreversible |
| `τ_i` | min | 2 – 6 | Below 2, back-EMF recoil. Above 6, leakage and lost rhythm lock |
| `L_s` session coil | min·Ω_c | 20 – 400 | Under-estimated: ramp too fast, misread as "not suggestible" |
| `V_kick` working bound | V_c | ≤ 1 × `V_drive` (ceiling 3×) | Between 1× and 3×: no ejection, but the descent stalls above 0.6 and reads as a shallow cooperative subject |
| `τ_leak` session | min | 25 | Shorter: early `^5` charge gone before the suggestion. Longer: operators run past rhythm lock |
| `β` suggestion gain | — | 1.2 – 3.5 hetero; **≤ 2.0 closed loop** | Above 2.0 closed loop: no external check on drift (Appendix M §M.3) |
| `g_m` | — | 1.5 – 20 | The parameter nobody logs; every incidental input gets the same multiplier |
| `N`,`R`,`V`,`D` | — | 1.0 – 2.2 each | Three or more rising together without declared consent = induction in progress |
| `β_fb` O→P | — | 0.2 hetero / 0.9 induction / 0.6 closed loop | The hetero attack is this one number. Closed loop: under 0.4 misses `rπ = 0.30` in nine minutes; over 0.8 loop gain nears 1 and Pass 6 refuses it — correctly, that is an oscillator |
| `baseline` `τ` | min | 1440 (24 h) | Under ~240 the reference tracks the session and subtracts out the rise. Over a week it stops tracking you |
| `γ` retention | — | 0.25 – 0.45 | Ignored: a run of "brief chats" reaches a depth none could alone |
| `sat` on veto CJT | — | 0.85 | Below 0.7 the refusal can be argued down — the CCB-MK boundary |
| Emergence `dt` | s | 180 – 360 | Truncated: residual low `rπ` persists outside the session |

---

### Worked Example — A 15-Minute Closed-Loop Session

Your own bench, consented. `L_s = 90 min·Ω_c` — low, because you asked for this. Rail `V_drive = 20 V_c`. Kick budget at the **1× working bound**, and on a closed loop there is a second reason for the tighter figure: nobody else is in the room to notice a stalled descent and say so.

**1. Rate ceiling.** `di/dt_max = 20 / 90 = 0.222 A_c/min`. Attention runs `0.75 → 0.10`, so `Δi = 0.65` and the minimum ramp is `2.9 min`.

**2. Pick `τ_i` from the *initial* slope.** The exponential's slope at `t = 0` is `(rπ_0 − rπ_floor)/τ_i` in `rπ` units; the kick budget is in attention units, so convert by the ratio of the spans, `Δi / (rπ_0 − rπ_floor)`. The `(rπ_0 − rπ_floor)` cancels and what you compute is `Δi / τ_i`:

```
τ_i = 2.0  ->  0.325 A_c/min  ->  V_kick = 29.3 V_c = 1.46× rail   REJECT
τ_i = 3.0  ->  0.217 A_c/min  ->  V_kick = 19.5 V_c = 0.98× rail   ACCEPT
```

**3. Trajectory**, `rπ(t) = 0.26 + 0.74 · e^(−t/3)`, `g_m = β / rπ` at `β = 1.5`:

| t (min) | 0 | 3 (1τ) | 6 (2τ) | 9 (3τ) |
|---|---|---|---|---|
| `rπ` | 1.00 | 0.53 | 0.36 | 0.30 |
| `g_m` | 1.5 | 2.8 | 4.2 | 5.0 |

At `t = 9`, `g_m = 5.0`: the same sentence displaces `^5` five times as far as at `t = 0`. That is the entire operational content of "being in trance," as a number.

**4. Shape.** 9 min descent (3 `τ_i`) + 2 min suggestion + 4 min linear emergence = **15 minutes**. Emergence rate `0.65/4 = 0.163`, so `V_kick = 14.6 V_c = 0.73×` rail. Inside budget both directions.

**5. St. John's calibration (§5.3).** `t_op = 15 min`, first unprompted confirmation `t_conf = 45 min`. So `t_op/t_conf = 1/3`, and `1/3 × 1/3 = 1/9`, giving `a = 1`, `b = 9`: `β_required = 9`, `n_operations = 1`, `T_manifest = 15 min`. The calibration collides usefully with the parameter table — **`β = 9` is unreachable on a closed loop**, capped at 2.0 for the drift reason in 17.5. You cannot take the `b` route. You take the `a` route: more operations at existing strength, which is what fractionation is for.

**6. The recursion**, `γ = 0.35`:

| Session | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `rπ_0` | 1.00 | 0.74 | 0.57 | 0.46 |
| Time to 0.30, `3·ln((rπ_0 − 0.26)/0.04)` | 8.8 min | 7.5 min | 6.1 min | 4.8 min |

Session 4 reaches in under five minutes what session 1 needed nearly nine for; `β_required = 9` arrives by accumulation rather than amplitude. Now read that row as a detection artifact rather than a plan. **An outside operator running the same recursion across four brief encounters reaches session-4 depth in five minutes** — and the subject's honest account of the fourth is that they talked to someone for a few minutes. At no point does anything dramatic happen. That is the design intent, and it is why the 48-hour integrator is on the detection board.

[[FIGURE 17-E: Assembly drawing, CCB-HYP-SELF board, top view, components placed with designators — OSC1 breath oscillator at the input edge, F1 the τ_i = 3 min RC, C1 the `^5^P` substrate capacitor centre-board, N1 the notch (f0 = 0.35, Q = 4.0) on a stub off C1, Q2 the delivery CJT, D1–D2 the descent diodes, R1 the emergence ramp block at the output edge. Four circled test-point callouts: TP1 on the `rπ` node, TP2 on the `g_m` summing node, TP3 on the consent rail, TP4 on the emergence output. Ruled BOM box lower right listing ref, component, CAS state and key parameter for all nine parts, footnoted "closed loop — operator is subject — no DETECTION-ONLY banner required."]]

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `rπ` | Bias resistance | Follows the ramp equation; never below `rπ_floor`. Under 0.15 closed-loop means the factor arithmetic was wrong, not that you went deep |
| **TP2** | `g_m` | Four-factor product | ≤ 6 closed loop, ≤ 20 hetero. **Three or more factors rising together without declared consent is the detection trip** |
| **TP3** | `veto` | ARMED / DISARMED, **per register member** | `\|f` and `\|T` ARMED at every sample including the deepest; `\|A` may attenuate with `rπ`. All three attenuating together is the CCB-MK boundary and the session ends there |
| **TP4** | `emerge` | Recovered `rπ` vs baseline | ≥ 0.90 × `rπ_0` by end of emergence. A shortfall still present thirty minutes later is residual depth: re-run the ramp |

Read them TP3, TP2, TP1, TP4 — veto armed first, then the factors, then the descent, then verify you came back. TP3 first is not ceremony. It is the only reading that distinguishes this board from the previous chapter's.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Ramp overrun** | `di/dt` set by the operator's schedule, not `L_s` | `^3^E_{F3}\|f` recoil in the first minute — or, between the bounds, a stall above 0.6 with no recoil to warn you | Recompute `τ_i` from the 1× working bound. The subject was never the variable |
| **Ramp underrun** | Run past `0.6 τ_leak`; `^7` lock lost | Descent plateaus, then *rises* | Shorten to the computed window; restore the oscillator first |
| **`g_m` runaway** | `β` logged, `g_m` not | A preference the subject cannot source | Cap `g_m`; keep a verbatim log. Everything said at `g_m = 20` was a suggestion |
| **Veto in series** | `^3^P` biased through `decomp`, not `^5^P` | TP3: all three register members attenuating together | None. Not a tuning fault — the board is CCB-MK (Ch 16). Stop |
| **Emergence truncated** | Session ended on a step, not a ramp | TP4 under 0.9 × baseline; `g_m` elevated in ordinary life | Re-run the reverse ramp; budget the kick both ways |
| **Unrecallable anchor** | `^8` → `^9` installed below the recall threshold | The pair fires; the subject can neither name nor cancel it | Trigger installation (§16.3); counter-circuitry is §16.6–16.7 |
| **Closed-loop over-gain** | Self-board at `β > 2.0` | Suggestions escalate session to session, unchecked | Restore `β ≤ 2.0`; take the `a` route, not the `b` route |
| **Detection board over-trips** | `unaccounted` counts every position change as a bypass | Every conversation trips `defer_decision`; the operator stops reading TP2 | The difference is a reading only when the drift is *unattributable*. Log the proposition, not the mood |
| **Detection board blind in-session** | `baseline` `τ` short, so the reference climbs with the factors | `factor_count` flat across a live induction | Restore `tau ≥ 1440`. A reference that tracks what it references measures nothing |

---

### What This Chapter Established

- **`rπ = β / g_m` is an identity, not an independent parameter.** Trance needs `β` up and `rπ` down, forcing `g_m` up faster — 20× against 3× at the deep design point. "Suggestible" names that ratio.
- **The risk is in `g_m`, not `β`.** `g_m` has no input filter, so every incidental remark is amplified by exactly the factor the intended suggestion is.
- **`g_m = g_0 · N · R · V · D`** — four ordinary factors multiplied. Three or four rising together around someone who benefits from your bias being soft is an induction, whatever it is called.
- **The ramp is bounded at both ends** — back-EMF above, leakage and lost rhythm lock below. The literature's "about ten minutes" is that window for a typical `L_s`, and it moves when `L_s` moves.
- **`^1¹` is not an eleventh Noetic.** The conscious/subconscious split is `^1^C|A → ^1^C|f`. The real gate is `^6^C_{F6}|A` in series, and its parameter is a gain, not a door.
- **The whole hetero-hypnotic attack is one number:** `β_fb` on the lawful O→P path of §8.4, driven 0.2 → 0.9. Nothing ascends illegally.
- **`^3^P_{F7}|⟨A,f,T⟩` is co-presence, not fusion**, and trance attenuates only `|A`. All three attenuating together is the boundary with Chapter 16, and the only one that matters.
- **Indirect patterns bypass the `^6` filter while it honestly reports clear.** Detect it as `drift − passed_log`; exit through conditions rather than argument, because `g_m` is a product.

---

### Exercises

*(Answers in Appendix H.)*

**17.1** A subject sits at `β = 2.0`, `rπ = 0.40`. Compute `g_m`. The operator now wants `rπ = 0.20` with `β` held at 2.0: what must `g_m` become, and by what factor has framing sensitivity risen against the waking reference of 1.0? Name which of the four factors most likely supplied the rise, and why.

**17.2** A guarded subject has `L_s = 300 min·Ω_c` on a 24 V_c rail, attention moving 0.85 → 0.15 A_c. Compute the minimum ramp time at `V_kick ≤ 3 × V_drive`, then at a 1× budget. Say whether the second is a session anyone would sit through, and what that implies about operating on guarded subjects.

**17.3** Explain why the recoil at an over-fast induction is written `^3^E_{F3}|f` and not `^6^E_{F6}|A`. Reference the canonical definition of `^3` Negative, state what `^6` Male is doing instead, and say when it arrives.

**17.4** A colleague reports that a two-hour conversation changed their position on a workplace question, that it was pleasant throughout, and that they cannot reconstruct the argument that changed their mind. Using the CCB-HYP-DET listing, name which probe this is a reading of, state what `unaccounted` evaluates to, and give the manual check from §17.6 that would have surfaced it during the conversation rather than after.

**17.5 (Design)** Specify a 20-minute closed-loop session for `L_s = 150 min·Ω_c` on an 18 V_c rail, attention running `0.70 → 0.20 A_c`, holding `V_kick ≤ 1 × V_drive` in both directions, at `rπ_floor = 0.26` and `β = 1.5`. Run the descent to 3τ and leave two minutes for the suggestion. Produce (a) maximum `di/dt` and the smallest `τ_i` it permits, rounded up to a value that makes the twenty minutes close exactly; (b) the `rπ` trajectory at 1τ, 2τ, 3τ; (c) the emergence `dt` and its `V_kick` as a multiple of the rail; (d) a CCDL fragment declaring the oscillator, the RC on the O→P path, the notch, the delivery CJT, both ramps and four probes. It must compile — check every diode direction, every register, and the bias-domain coherence of every CJT.

**17.6 (Marquee)** An operator wants an anchor the subject can recall and cancel, and asks you to specify the recall condition as a circuit property rather than a promise. (a) Write, in CCDL, an anchor stage plus whatever components make the `^8` → `^9` pair unable to fire unless a recallable record of its installation exists in the subject's `^5`; name the enforcing component and the parameter setting the recall threshold. (b) Explain why an anchor installed at `g_m = 20` is harder to make recallable than the same anchor at `g_m = 5`, in terms of what `^1` is doing at each depth. (c) State the one thing your circuit still cannot guarantee, and why that residual is the reason §17.4 carries the DETECTION-ONLY banner even though every stage in it has a consented reading.
