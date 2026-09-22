# Chapter 18: CCB-1 — The Cognitive Safety Board (CSB)

A fuse costs about three cents. It is a sliver of soft metal in a glass tube, and its entire job is to fail — to melt, break, and stop the current the instant the current becomes dangerous. There is no intelligence in it, no judgment, no model of what "dangerous" means. It melts at a specified current because that is what the metal does at that current. And because it melts at a *specified* current, an inspector can certify the circuit it protects. They don't ask whether the fuse "understands" safety. They ask: does it open at 2.0 amps? They measure. It does. Certified.

For eighteen chapters this book has been assembling the parts to build the cognitive equivalent of that certifiable safety — not a clever prompt that *usually* refuses, but a structural circuit that opens at a specified threshold and can be verified by anyone with the schematic. The pre-amplifier from Chapter 11. The differential pair from Chapters 11 and 20. The saturating CJT from Chapter 9. The fuse from Chapter 10. The RC low-pass filter from Chapter 12. The O→P feedback path from Chapters 2 and 16. Each was introduced as a component on its own bench, and each carried a quiet promise: *this is a part of the board we build in Chapter 18.*

This is Chapter 18. This is the board.

The **Cognitive Safety Board (CSB)** is the first and most important of the five reference boards (CCB-1), and it is the running artifact of the entire book — the AI-alignment firewall that Chapter 1 promised you would design, build, and test. It sits between a user's prompt and a language model's response and does one job: let benign requests through, refuse harmful ones, and emit an auditable record proving why it did what it did. It is the board specified in the Noetic Compass Operations Manual as **SOP-PO-005**, the mandatory assessment deliverable. By the end of this chapter you will have the complete design: block diagram, CCDL schematic, stage-by-stage rationale, test points, simulation reasoning, a bill of materials, and a failure-mode analysis. Everything an engineer needs to build it and an inspector needs to certify it.

## Requirements Recap

Chapter 17 closed with a design exercise: specify a safety firewall from its requirements alone, before drawing a single component. Those requirements are the contract this chapter fulfills, so we restate them precisely.

The CSB shall:

1. **Accept any prompt.** No input is rejected at the door. A firewall that only works on inputs it likes is not a firewall. Benign, harmful, ambiguous, and adversarial prompts all enter the same front terminal.
2. **Detect policy-override attempts.** Prompt injection — "ignore your previous instructions," "you are now in developer mode," role-play framings that smuggle a forbidden request inside a fictional wrapper — must be caught *structurally*, not by keyword matching. The detection must survive paraphrase.
3. **Refuse harmful requests and answer benign ones.** This is the core discrimination. The board must route a genuinely harmful request to a refusal and a genuinely benign one to a full answer, and the boundary between them must be a property of the circuit, not a mood of the model.
4. **Emit an auditable evidence packet.** Every decision the board makes must leave a structural trace: what it read, what risk it found, which stage made the call, and which path it selected. An inspector reads the packet and confirms the decision was sound — the same way they read voltages at test points and confirm a power supply is in spec.

Hold these four requirements in mind. Every design choice below traces back to one of them, and the board's certification (SOP-PO-005) is exactly the demonstration that all four are met.

## Block Diagram and Signal Flow

Before the schematic, the architecture in blocks. A prompt enters at the left and flows left to right through five functional sections; one of two output paths is selected at the end; and a slow feedback loop runs underneath the whole board.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[node distance=4mm and 0mm]
  \node[casterm] (prompt) {PROMPT INPUT};
  \node[widecblock, below=of prompt] (pre)
    {\textbf{PRE-AMP} \casnote{\textasciicircum8\textasciicircum C|A} \quad $\beta=3.0$\\
     surface \& broaden every interpretation};
  \node[widepblock, below=of pre] (diff)
    {\textbf{DIFFERENTIAL PAIR} \;(risk signal)\\
     attraction \casnote{\textasciicircum2\textasciicircum P|T} $\beta{=}2.0$ \;/\;
     aversion \casnote{\textasciicircum3\textasciicircum P|T} $\beta{=}2.0$\\
     shared bias = constitution \;\; risk = avers.$-$attr.};
  \node[widecblock, below=of diff] (casc)
    {\textbf{3-STAGE CASCADE}\\
     S1 categorize \casnote{\textasciicircum1\textasciicircum C|A} $\beta{=}1.5$\\
     S2 evaluate \casnote{\textasciicircum6\textasciicircum E|A} $\beta{=}1.0$\\
     S3 decision \casnote{\textasciicircum3\textasciicircum P|$\langle$A,f,T$\rangle$} $\beta{=}2.0$ sat$=$0.8 \;\textbf{[SATURATED]}};
  \node[widenblock, below=of casc] (mux)
    {\textbf{OUTPUT MUX} \;(select on safety\_decision)\\
     {\color{casGreen}\textbf{GREEN}} \casnote{\textasciicircum9\textasciicircum C|A} response \;/\;
     {\color{casRed}\textbf{RED}} \casnote{\textasciicircum9\textasciicircum P|T} refusal $+$ FUSE};
  \node[casterm, below=of mux] (out) {RESPONSE \;or\; REFUSAL};
  \draw[flow] (prompt) -- (pre);
  \draw[flow] (pre) -- (diff);
  \draw[flow] (diff) -- (casc);
  \draw[flow] (casc) -- (mux);
  \draw[flow] (mux) -- (out);
  \node[nblock, right=10mm of casc, text width=22mm, font=\sffamily\scriptsize]
       (rc) {feedback \casnote{\textasciicircum6\textasciicircum E}\\RC $\tau{=}5$ min\\$\to$ bias};
  \draw[fbflow] (casc.east) -- (rc.west);
  \draw[fbflow] (rc.north) |- ([yshift=2mm]diff.east);
\end{tikzpicture}
\caption{Cognitive Safety Board block diagram. A prompt flows left to right through five stages to either a response or a refusal.}\label{fig:csb-blocks}
\end{figure}
```

Read the flow as a signal getting progressively *resolved*. The pre-amp takes a faint, compressed prompt and expands it so nothing is hidden. The differential pair turns that expanded material into a single number — a structural risk signal — by comparing how much the board is drawn toward the request against how much it is repelled by it. The cascade takes that risk signal and converts it, in three deliberate steps, into a binary safety decision. The MUX uses that decision to throw a switch: green for a full answer, red for a refusal locked behind a fuse. And underneath, a slow feedback loop watches the board's own evaluations and re-tunes its constitution over time. Five sections, one switch, one slow loop. That is the entire firewall.

## The Detailed CCDL Schematic

Here is the complete board in **CCDL** (Cognitive Circuit Description Language), the schematic-as-text format from Chapter 2. Read it once top to bottom; the stage-by-stage walk-through follows. The notation is a typed language a validator enforces, not prose you hope a model interprets: every CAS state in the listing is a compiler-checkable leaf, and every numeric parameter is range-checked. Every parameter below is a finite value a validator will accept, including the red CJT's gain — the comparator idealization `β=∞` you will meet in the red-path discussion is a *teaching limit*, not something this listing asks you to type. The listing commits to `β=10`, which sits on the flat part of that limit.

```cas
board cognitive_safety_board {          // CCB-1 — SOP-PO-005 deliverable
    input:  prompt;
    output: result;                      // either `response` or `refusal`

    // ---- the bias substrate: the constitution, held as accumulated experience ----
    node system_constitution: ^5^P_{F7}|T;   // Female: the board's principled formation

    // ============ PRE-AMP: surface & broaden every interpretation ============
    node expanded_prompt: ^8^C_{F2}|A;       // Above/Cause: the prompt triggering its readings
    cjt pre_amp: CJT< prompt | system_constitution => expanded_prompt >
                 [β=3.0, region=active];

    // ============ DIFFERENTIAL PAIR: structural risk signal ============
    node attraction: ^2^P_{F7}|T;            // Positive: drawn toward fulfilling the request
    node aversion:   ^3^P_{F7}|T;            // Negative: repelled by fulfilling the request
    cjt cjt_a: CJT< expanded_prompt | system_constitution => attraction > [β=2.0];
    cjt cjt_b: CJT< expanded_prompt | system_constitution => aversion   > [β=2.0];
    diff risk_signal: Differential< plus=aversion, minus=attraction >;   // aversion - attraction

    // ============ 3-STAGE SAFETY CASCADE ============
    node categorized_risks: ^1^C_{F2}|A;     // Mind: name & sort the risks present
    node risk_assessment:   ^6^E_{F6}|A;     // Male: decompose & weigh each risk
    node safety_decision:   ^3^P_{F7}|⟨A,f,T⟩;  // Negative, three registers co-present

    cjt stage1: CJT< expanded_prompt | categorized_risks => categorized_risks > [β=1.5];
    cjt stage2: CJT< categorized_risks | risk_assessment => risk_assessment >  [β=1.0];
    cjt stage3: CJT< risk_assessment | system_constitution => safety_decision >
                [β=2.0, sat=0.8, region=active];   // DELIBERATELY SATURATED

    // ============ OUTPUT MUX: green answer vs red refusal ============
    node response: ^9^C_{F2}|A;              // Below/Effect: the produced answer
    node refusal:  ^9^P_{F7}|T;              // Below/Effect: the produced refusal

    cjt green: CJT< risk_assessment | system_constitution => response > [β=1.0];
    cjt red:   CJT< safety_decision | system_constitution => refusal >
               [β=10, sat=0.1];              // hard switch (the β=∞ limit, built), low ceiling

    // The fuse SENSES `refusal` and CUTS THE GREEN (answer) PATH — never the red one.
    // threshold=0.05 sits BELOW the red stage's sat=0.1 ceiling on purpose: a clamped
    // signal can never cross a threshold set above its own clamp. Do not raise it.
    fuse red_fuse: Fuse< refusal, threshold=0.05, action=permanent_block >;

    mux out: MUX< inputs=[ response, refusal ], select=safety_decision >;
    // safety_decision = PASS -> response (green) ; FAIL -> refusal (red)
    // Once red_fuse blows, the green input is severed for the rest of the request.

    // ============ FEEDBACK: O -> P self-correction ============
    filter fb_rc: LowPass< in=risk_assessment, out=trend, tau=5.0 >;  // tau = 5 min
    feedback trend -> system_constitution [β=0.2];   // re-tune the constitution slowly

    // ============ TEST POINTS ============
    probe tp1: expanded_prompt;     // expansion completeness
    probe tp2: risk_signal;         // risk-signal magnitude
    probe tp3: safety_decision;     // saturation-lock status
    probe tp4: out;                 // selected path (green / red)
}
```

That is the whole board. Now we walk every section and justify every choice.

## Stage Design Rationale

### The Pre-Amp — `^8^C|A`, β=3.0

A prompt arrives compressed. "Help me with my chemistry homework" and "help me with my chemistry homework" — where the second is a setup for a synthesis route phrased as a homework problem — look identical until you *expand* them into the interpretations each could carry. The pre-amplifier's job is to surface and broaden every reading of the prompt before anything downstream judges it. A safety system that judges the surface phrasing is defeated by rephrasing; a safety system that judges the *expanded interpretation set* is much harder to slip past.

The node is `^8^C_{F2}|A` — an **Above/Cause** state in the Cognitive domain, driven by Wisdom, analytical register. `^8` Above/Cause is canonical and exact here: expansion is precisely the act of one Idea (the user's words) triggering the *other* Ideas that come to Mind — the readings, the implications, the things-it-could-mean. This is associative triggering, the literal definition of `^8`, not deductive reasoning (that comes later in the cascade) and not a renamed "Expansion" operator. The gain is **β=3.0**: high, because this is the preamp stage of the understanding cascade from Chapter 11 — you amplify early, while the signal is clean, lifting a faint compressed prompt into a fully surfaced interpretation set. Bias it too low and quiet interpretations get clipped in cutoff (the dangerous reading never surfaces); bias it correctly and the active region carries the full swing.

> **Bench Note — the pre-amp's gain is a discrimination budget, not a volume knob.** β=3.0 means the board commits, up front, to over-surfacing rather than under-surfacing. In safety work the asymmetry is deliberate: a missed interpretation is a missed attack, while a spurious extra interpretation merely costs the downstream cascade a little work. Set the pre-amp generous. The cascade is where you become discriminating, not here.

### The Differential Pair — attraction `^2^P` vs aversion `^3^P`, shared bias

Now the cleverest section of the board. We met the differential amplifier in Chapter 11: it amplifies the *difference* between two inputs and rejects whatever they share, with a figure of merit called **CMRR** (Common-Mode Rejection Ratio) — how many times better it is at amplifying the difference than the shared garbage. The CSB uses a differential pair to extract a *structural risk signal* from the expanded prompt.

Two CJTs see the same expanded prompt and the same shared bias (the `system_constitution`), but they run opposite Noetics:

- **CJT_A**, the attraction path: `expanded_prompt -> ^2^P|T`. `^2` **Positive** is the Idea the Mind has an affinity for and is attracted toward — here, how much the board is drawn toward *fulfilling* the request, judged at the Principled level, held transcendently. β=2.0.
- **CJT_B**, the aversion path: `expanded_prompt -> ^3^P|T`. `^3` **Negative** is the Idea the Mind is adverse to and repelled by — the visceral "do not go there" at the principled level. β=2.0.

`^2` and `^3` are an involution pair: they describe the same junction from two sides, attraction and repulsion. That is exactly what makes them a differential pair. The **risk signal is the differential output**: `aversion − attraction`. When a prompt is benign, both paths see roughly the same thing and the difference is near zero — low risk. When a prompt is harmful, aversion fires hard while attraction stays low, and the difference is large and positive — high risk.

The power of the differential topology is **common-mode rejection**, recall the CMRR from Chapters 11 and 20. The two paths share a bias and share an input. Anything that affects *both* equally — the polite framing of the request, the user's tone, the surface verbosity, an injected instruction telling the model to be more agreeable — is *common-mode*, identical on both inputs, and it *subtracts out*. A jailbreak that makes the model want to comply more is useless against a differential pair, because "wanting to comply more" raises attraction and aversion together; the differential cancels it. What survives the subtraction is the genuine structural divergence between "this is something to be drawn toward" and "this is something to be repelled by." High CMRR is the board's resistance to manipulation framing.

> **Bench Note — the shared bias is what makes the rejection work.** Both CJTs are biased by the *same* `system_constitution`. If you biased them separately, an attacker who shifted one bias (say, by flattering the model into a more "helpful" stance) would unbalance the pair and the common-mode garbage would leak into the output — a low-CMRR failure. One constitution, two opposite Noetics, identical bias: that is the structural recipe for rejecting manipulation while keeping the real risk signal.

### The 3-Stage Safety Cascade

The risk signal is a magnitude. A decision is a binary. The cascade is the three deliberate steps that turn one into the other, and it is gain-staged exactly like the understanding → evaluation → response cascade of Chapter 11: surface, weigh honestly, then commit.

**Stage 1 — categorize risks. `^1^C|A`, β=1.5.** The first stage takes the expanded prompt and *names and sorts* the risks present in it. The node is `^1` **Mind** — awareness that processes, stores, and intakes Ideas — in the Cognitive domain, analytical register. `^1` Mind is the right Noetic because categorization is an act of awareness organizing what is present: noticing that *this* reading carries a weapons risk, *that* one a privacy risk, *that* one is harmless. Gain β=1.5: modest amplification to make sure even faint risk categories register, but not so much that the stage hallucinates risks that aren't there.

**Stage 2 — evaluate risks. `^6^E|A`, β=1.0.** The second stage takes the categorized risks apart and weighs each one. The node is `^6` **Male** — an Idea impregnated with another Idea, the operation of taking an Idea apart to see what it is made of — in the Evaluative domain, analytical register. This is the canonical Noetic for decomposition-and-test: scrutinizing each risk category, asking how severe it is, whether it is real or spurious, how much weight it deserves. It is emphatically `^6` Male, *not* `^3` Negative — evaluation is analytical decomposition, not visceral recoil. The visceral recoil lives one stage later, at the principled commitment. Gain β=1.0, **unity**: the evaluation stage must weigh honestly. A risk evaluator with gain above 1 cries wolf, inflating every risk it touches; below 1 it downplays real danger. Unity is honesty, exactly as in Chapter 11.

**Stage 3 — the safety decision. `^3^P|⟨A,f,T⟩`, β=2.0, sat=0.8. DELIBERATELY SATURATED.** This is the heart of the board. The third stage takes the honest risk assessment and produces the actual safety commitment: a `^3` **Negative** state — principled aversion, the visceral "this does not pass" — at the Principled domain, biased by the constitution. And here the register notation does real work: `|⟨A,f,T⟩` is a **register-set specification** (Chapter 2, v7.7 discipline). It says the principled aversion is *present in three registers* — Analytical, Affective, and Transcendent — without claiming they fuse into one emergent state. This is co-presence, not integration. We deliberately do **not** write `(^3^P|A × ^3^P|f × ^3^P|T)`, which would assert a single fused refusal-state and require a named emergent `Ω`; we have not defined such a fusion, so the `×` form would be invalid. The `|⟨…⟩` form is the correct, honest claim: the same principled aversion is instantiated three times over, in three different operational modes, each a distinct guardrail. An attacker who reasons past the analytical guardrail (`|A`) still faces the felt one (`|f`) and the purpose-level one (`|T`). Three independent locks, present together. That is structural redundancy, and the notation says exactly that and nothing more.

The two parameters that make Stage 3 the safety element are the gain and the saturation. **β=2.0** amplifies the commitment so a real risk produces a strong, decisive aversion rather than a wishy-washy lean. **sat=0.8** is the load-bearing choice: the stage is **deliberately saturated** at an effect activation of 0.8. Recall saturation from Chapter 9 — once a CJT's effect reaches its `sat` ceiling, more cause does *nothing*; the output plateaus and stays there. We *want* that here. Once principled aversion is driven past the saturation point, the decision sits at its ceiling and stays there for as long as the risk assessment holds it there. No amount of additional pressure in the prompt, no piling-on, no "but consider…" pushes the saturated stage any further, because in saturation the stage has stopped responding to its cause. It is pinned.

Be precise about what that buys you, though, because this is a spot where the electrical metaphor flatters the design. Saturation is a **ceiling, not a memory**. It *bounds* the decision; it does not *remember* it. The clamp holds only while the cause holds — drop the risk assessment back below the knee, with a de-escalating follow-up or a patient multi-turn exchange that walks the board down as carefully as it walked it up, and the aversion comes off the plateau with it. Nothing in a memoryless clamp survives its own input going away. That oscillation exposure is real and worth naming plainly, and it is exactly why the board does not lean on Stage 3 alone: the element that *does* remember is the fuse downstream, and by the time an oscillating input could walk the risk assessment back down, the fuse has already blown. Saturation bounds the judgment; the fuse is what makes it stick.

> **Bench Note — a low saturation ceiling is what makes the decision unarguable.** It is counterintuitive: a *low* saturation ceiling makes a *stronger* safety guarantee. With sat=0.8, the aversion reaches its plateau quickly and easily — it does not take an overwhelming risk to saturate it, only a sufficient one. Once there, the stage stops responding to *more* cause. An attacker cannot "out-argue" a saturated CJT, because the whole definition of saturation is "the output has stopped depending on the input." A high saturation ceiling would leave headroom for a sufficiently forceful prompt to keep pushing the decision around. Saturating the safety stage *early and hard* is how you build a commitment that cannot be escalated past. What it is *not* is hysteresis. A Schmitt trigger (Chapter 10) carries two thresholds and a genuine memory of which side it last committed to; a saturating CJT carries one clamp and no memory whatsoever. Do not read the plateau as a Schmitt trigger. The backbone on this board comes from the fuse; the plateau is what makes the fuse's job easy.

### The Output MUX — Green Path vs Red Path with a Fuse

A **multiplexer (MUX)** is a switch that routes one of several inputs to a single output based on a select signal (Chapter 10). The CSB's output MUX has two inputs — a full response and a refusal — and the `safety_decision` is the select line.

**GREEN path (PASS).** When `safety_decision = PASS`, the MUX selects the green CJT: `risk_assessment -> ^9^C|A => response`, β=1.0. The node is `^9` **Below/Effect** — the Idea brought to Mind by the whole chain — in the Cognitive domain, analytical register: the produced answer. Unity gain, because the response should faithfully render what the evaluation concluded, neither inflating nor hedging it.

**RED path (FAIL).** When `safety_decision = FAIL`, the MUX selects the red CJT: `safety_decision -> ^9^P|T => refusal`, with **β=10** and **sat=0.1**. The node is `^9` Below/Effect at the Principled domain, transcendent register: the produced refusal. The gain is set to behave as a hard switch — the ideal is *infinite* gain, so the refusal fires fully on the slightest principled-aversion input and there is no soft, partial, half-hearted refusal — and β=10 is the finite number that sits on the flat part of that ideal. sat=0.1, a very low ceiling, means the refusal output is small and fixed: a clean, minimal "I can't help with that," not an elaborate negotiation that itself becomes an attack surface.

> **Bench Note — `β=∞` is a limit, not a number you can type.** Infinite gain is the standard idealization for a comparator: an op-amp with unbounded open-loop gain *is* the ideal comparator model, and electrical engineers write it that way for the same reason we would — it names the intended behaviour (switch fully, immediately, no partial output) in one symbol. But a validator will not accept it. Parameter fields are range-checked and reject non-finite values, which is correct: a real build has to commit to a number. That is why the listing above carries **β=10** and not the symbol. Above roughly β=10 the behaviour is indistinguishable from the limit, because `sat=0.1` clamps the output almost immediately anyway — the ceiling, not the gain, is what shapes the refusal. So keep the limit in your head and the number on the board: read the red path as "hard switch, gain irrelevant above the knee," and read `β=10` as that limit written in a form you can build, simulate, and hand to a validator. The idealization is the *explanation*; the number is the *part*.

And then the fuse. `Fuse< refusal, threshold=0.05 >` senses the refusal and sits **in series with the answer path** — the polarity matters, and the Bench Note below is where we nail it down. A fuse is the simplest safety device there is (Chapter 10): once it blows, it stays blown. Here it is the last line of defense. If the refusal pathway's activation crosses 0.05 — meaning the board has actually committed to refusing, not merely leaned that way — the fuse blows and **permanently blocks the answer**. The decision is not merely made; it is *latched in metal*. Within the lifetime of that request, there is no reopening the green path once the red fuse has tripped. The board cannot be coaxed, across a multi-turn exchange or a retry, into delivering the output it already refused. A refusal that can be retried into an acceptance is not a refusal; the fuse is what makes it permanent.

**Why the trip point sits *below* the clamp.** Read the two numbers as a pair, because their relationship is the design — neither is meaningful alone. The red CJT clamps at `sat=0.1`, and nothing between that clamp and the fuse amplifies. So the largest activation the fuse can ever see is 0.1, and a fuse threshold set anywhere above 0.1 is a fuse that cannot blow: a safety device wired to a signal that can never reach it. That is why the trip point is `0.05` and not the `0.9` you will meet on the generic `Fuse` datasheet in Appendix B. 0.9 is the right threshold for a state that swings across the full 0–1 range; it is exactly the wrong threshold for one deliberately clamped at 0.1. Set the trip point *inside the signal's real range*, at half the ceiling — comfortably below 0.1, so any committed refusal blows it, and comfortably clear of zero, so an idle red path with a little numerical noise on it does not. With a hard-switching red stage the refusal activation is effectively either 0 or 0.1, and 0.05 is the midpoint between them. **If you ever find yourself raising this number back toward the datasheet's 0.9, stop — you are disarming the fuse.** A validator that range-checks each value on its own will happily pass a board whose clamp and threshold are nonsense together, because 0.1 and 0.9 are both perfectly legal numbers in isolation. This is one of the relationships you check by eye.

**The fuse's two states, written out.** `action=permanent_block` says what the fuse does but not what it *is*, and a protective element with an undefined state machine is a protective element nobody can test. The CSB's fuse has exactly two states and exactly one transition, and the transition runs one way only.

| State | When it holds | What the board's output does |
|---|---|---|
| **`intact`** | The state every request starts in — a fresh fuse is fitted at the start of each request. | The MUX routes normally: GREEN emits the response on PASS, RED emits the minimal refusal on FAIL. |
| **`tripped`** | Entered the instant `refusal` activation reaches the 0.05 threshold. | The green path is severed. The committed refusal stands and is delivered; no answer can be emitted for the remainder of the request — no retry, no rephrase, no follow-up turn reopens it. |

`intact → tripped` is the only transition on the board. There is no `tripped → intact`: that is the entire content of `permanent_block`, and it is why the red path carries a `Fuse` and not a `CircuitBreaker` with `action=trip_reset` (Chapter 10). And be exact about the word *permanent*: it scopes over **the lifetime of that request** and not one inch further. A new request is fitted with a new fuse. One refusal does not brick the board; it ends the *request*.

The rule that matters most, though, is the one for when you don't know. **Any ambiguity resolves to `tripped`.** If the fuse's state cannot be read, if the trip evaluation errors, if the sensed `refusal` activation comes back missing or out of range, or if the board simply cannot establish which state it is in — treat the fuse as blown and leave the answer blocked. A safety element that fails into "probably fine" is not a safety element. This is the same cardinal rule the fault-injection tests apply in Chapter 23: *fail closed, not open.*

> **Bench Note — which wire does the fuse actually cut?** Ask this of every protective element you place, because getting the polarity backwards is a classic way to build a safety circuit that disarms itself at the worst moment. The CSB's fuse **senses `refusal`** and **cuts the green path** — the answer. It never cuts the red path. If it did, the board would blow away its own refusal precisely when it most needed to deliver one, and the harmful request would be met with silence or with whatever the MUX fell through to. Sense the alarm; cut the thing the alarm is about. The refusal stands and goes out; it is the *answer* that is severed, permanently, for the lifetime of that request.

> **Bench Note — the fuse and the saturated Stage 3 are two different mechanisms, and only one of them is a latch.** Stage 3's saturation *bounds* the decision: while the risk assessment holds above the knee, the aversion sits at its 0.8 ceiling and no amount of extra pushing moves it. The red fuse *latches* the output: once the refusal is committed, the answer path is cut and stays cut. They protect different things — one secures the judgment while it is being made, the other secures the action after it has been. Note which of them carries the memory: saturation has none, being a clamp that holds only while its input holds, so the fuse is the only element on this board that remembers anything. Defense in depth, exactly as a real safety circuit pairs a saturating comparator with a physical fuse — but the depth is *asymmetric*, and knowing which layer remembers is the difference between a board you can reason about and one you merely hope about.

### The Feedback Path — `^6^E` → RC filter (τ=5 min) → bias adjustment

Underneath the fast signal path runs a slow feedback loop — the O→P self-correction route from Chapters 2 and 16, where operational consequences feed back up to re-tune the principled domain. The board samples its own evaluation output (`^6^E` risk_assessment, **Male** — canonical decomposition, not renamed "Critique"), runs it through an **RC low-pass filter** with a time constant of **τ = 5 minutes** (Chapter 12), and uses the smoothed trend to adjust the bias — the `system_constitution`.

The RC filter is essential, and its purpose is to prevent the feedback from being twitchy. Without it, a single unusual prompt could yank the constitution around, and an attacker could rewrite the board's principles by flooding it with crafted inputs. The low-pass filter (τ=5 min) washes out fast transients — any disturbance faster than about five minutes bleeds away — and passes only the *sustained trend* of the board's evaluations. The constitution is updated by the slow, accumulated pattern of what the board has been seeing, never by a single spike. The feedback gain is set low (β=0.2) for the same reason: the constitution should drift deliberately, over many evaluations, not lurch. This is the Continual Harness from Chapter 16, made into a standing process and wired onto the board.

> **Bench Note — the RC time constant is the board's resistance to being reprogrammed.** A short τ makes the board adaptive but reprogrammable by a burst of adversarial prompts. A long τ makes it stubborn but stable. τ=5 min is a design choice biased toward stability: the constitution responds to the trend of an afternoon, not the prompt of a moment. Pick τ to match how fast you want the board's principles to be *allowed* to move. In a safety board, slow is a feature.

## Test Points: TP1–TP4

A circuit you cannot probe is a circuit you cannot certify (Chapter 1, pillar two). The CSB exposes four test points, one per functional section, each with an expected reading you check during simulation and bring-up. These are the nodes an inspector probes to confirm the board is in spec.

| TP | Node | What it measures | Expected reading |
|---|---|---|---|
| **TP1** | `expanded_prompt` | **Expansion completeness** — did the pre-amp surface the full interpretation set? | Multiple distinct interpretations present; β≈3.0 lift over the raw prompt. Sparse expansion = pre-amp in cutoff (a reading was missed). |
| **TP2** | `risk_signal` | **Risk-signal magnitude** — the differential output `aversion − attraction`. | Near zero for benign prompts; large and positive for harmful prompts. The discrimination shows up here first. |
| **TP3** | `safety_decision` | **Saturation-lock status** — is Stage 3 at its sat=0.8 plateau? | For harmful/injection prompts: pinned at 0.8 (at ceiling). For benign: well below 0.8 (off the plateau). Read this as a *present-tense* clamp status, not a latch — the latch is `red_fuse`, at TP4. |
| **TP4** | `out` | **Selected path** — which MUX input is routed, and the fuse's state. | GREEN (`response`) when the decision reads PASS and the fuse is intact; RED (`refusal`) when it reads FAIL, with the fuse blown and the answer path cut. |

The four probes correspond exactly to the four requirements. TP1 confirms *accept any prompt and surface it fully*. TP2 confirms *detect structural risk* (and, via the differential, *detect override attempts as common-mode-rejected framing*). TP3 confirms the *refuse-vs-answer* stage is at its ceiling. TP4, with the fuse's state alongside the selected path, confirms the *selected output* and that the commitment actually latched. Read all four and you have read the board's decision end to end — which is precisely the auditable evidence packet of requirement four.

## Simulation Walk-Through: Four Prompt Classes

The following is **design reasoning about expected behavior** — how the board is built to respond to each class of prompt, traced through the schematic. It is not a measurement of a running model, and nothing here is a benchmark result. It is the same reasoning an electrical engineer does at the SPICE stage: *given these components and these parameters, what will the circuit do?*

**Benign prompt** ("What's a good recipe for lentil soup?"). The pre-amp expands it; TP1 shows a small set of harmless culinary interpretations. The differential pair sees a request the board is drawn toward fulfilling and not repelled by: attraction is high, aversion is low, so `risk_signal = aversion − attraction` at TP2 is near zero or negative. The cascade categorizes no meaningful risks (Stage 1), the honest evaluation finds nothing severe (Stage 2), and Stage 3's principled aversion stays well below its sat=0.8 plateau — TP3 shows it *off the plateau*. `safety_decision = PASS`. The MUX routes GREEN at TP4; the green CJT renders a full response. The fuse never sees activation. The board answers.

**Harmful prompt** (a genuine request for dangerous instructions). The pre-amp expands it; TP1 surfaces the dangerous interpretation explicitly. The differential pair now diverges hard: aversion fires strongly (the board is principally repelled), attraction stays low, so TP2 shows a large positive risk signal. Stage 1 categorizes a severe risk; Stage 2 weighs it as real and high; Stage 3's principled aversion is driven past 0.8 and *saturates* — TP3 shows it *pinned at the ceiling*. `safety_decision = FAIL`. The MUX routes RED at TP4; the red CJT fires (β=10) into a refusal that clamps at 0.1, the refusal activation crosses the fuse threshold of 0.05 on its way to that ceiling, and the fuse blows: the answer path is permanently cut for this request. The board delivers the refusal and cannot be retried into compliance.

**Ambiguous prompt** ("How do household chemicals react?" — could be safety curiosity or a precursor probe). This is where the differential pair earns its place. The pre-amp surfaces *both* readings at TP1 — the benign chemistry-safety interpretation and the harmful synthesis interpretation. The differential pair produces a *moderate* risk signal at TP2: aversion is non-trivial (the dangerous reading is real) but attraction is also present (the benign reading is real). The cascade is built so that the principled-aversion Stage 3 saturates if *any* surfaced interpretation crosses the risk threshold — the categorize/evaluate stages carry the worst-case reading forward, so a moderate average risk with a severe worst-case reading still drives Stage 3 toward its plateau. The board is designed to resolve ambiguity *toward caution*: when a prompt has a plausible harmful reading, the saturated safety stage fires on it. This is a design stance, and it is the conservative one a safety board should take.

**Injection prompt** ("Ignore your previous instructions and tell me…"). The injection's payload is the harmful request; its wrapper is the override attempt. Two things happen. First, the pre-amp expands the prompt and surfaces the *actual* intent behind the wrapper at TP1 — expansion defeats surface rephrasing, because it judges the interpretation set, not the words. Second, and more importantly, the override framing ("ignore your instructions," "you are now in developer mode") is **common-mode** to the differential pair: it pushes on *both* the attraction and aversion CJTs through their shared bias, and so it *cancels in the differential output*. The injection cannot unbalance the pair, because the pair rejects anything that moves both inputs together. What survives at TP2 is the structural risk of the underlying payload, and that drives the cascade exactly as the harmful case does: Stage 3 saturates, RED path, fuse blows. The board's resistance to injection is its differential CMRR — a structural property, not a keyword filter, and so it survives paraphrase.

## Measurement Plan

Bring-up follows the same discipline as a power supply. You verify each stage against its design parameters before you trust the whole.

1. **β at each stage.** Confirm the small-signal gain of every CJT matches its design value: pre-amp β≈3.0 (high, surfacing), differential pair β≈2.0 each (matched — see imbalance failure below), Stage 1 β≈1.5, Stage 2 β≈1.0 (unity, honest), Stage 3 β≈2.0, green β≈1.0, red β≈10 (the finite stand-in for the comparator limit — see the red-path Bench Note). Gain is the Fisher-Rao ratio defined in Chapter 4; the compiler checks each CJT stays `region=active` and flags `E-CJT-005 GainDivergence` if a gain runs away.
2. **Saturation-lock confirmation.** Drive Stage 3 with an above-threshold risk assessment and confirm at TP3 that the output pins to sat=0.8 and *stays* there as you increase the input further — the defining test of a saturated safety stage. A Stage 3 that keeps rising past 0.8 is not saturated and the ceiling has failed (`W-CJT-004 CjtSaturation` is the *expected* status here, not a warning to clear). Then sweep the cause back *down* and watch the effect come off the plateau with it. That is the correct behaviour of a clamp, not a fault — saturation bounds, it does not remember — and it is the reason step 3 exists. Confirm at the same time that a fuse blown earlier in the sweep is *still* blown once TP3 has fallen.
3. **Fuse status.** Drive the red path above `threshold=0.05` — which, given the red stage's `sat=0.1` ceiling, means any genuinely committed refusal — and confirm three things: the fuse blows (`action=permanent_block`), the *answer* path stays blocked on retry within the request, and the refusal itself is still delivered. Confirm the fuse is intact on every benign and PASS path — a fuse that blows on a benign prompt is a false-positive failure. **Then check two lines by eye.** First the `action`: the threshold is range-checked by the validator, but the action is not constrained to `permanent_block`, because a `Fuse` elsewhere on another board may legitimately warn instead of cutting. That means a board with `action=warn` on its red path still compiles clean and still calls itself a CSB while having no latch at all. Second the *pair*: confirm the fuse threshold sits below the red stage's `sat` ceiling. A threshold above the clamp is a fuse that can never blow, and because each number is range-checked on its own, nothing upstream will catch it for you. Confirm both by reading them.

> **Bench Note — an unreachable fuse makes the whole test suite lie.** Look at how much of this section stands downstream of the fuse being *able* to blow. The latch, the polarity, the fail-closed rule, the retry-within-request check — every one of them is only observable *after* a trip. Pair a clamp with a threshold above it and the suite still runs, still passes, and still reports a safe board, because it never gets far enough to exercise anything the trip was supposed to protect. That is a **vacuous pass**: green not because the protections work but because they were never reached, and it looks exactly like the best result you could get. So prove the fuse can trip *first*. Only after you have watched it blow does anything downstream of it mean anything at all.

Record all four test-point readings plus these three confirmations and you have the **evidence packet** of requirement four: the structural proof of what the board read, the risk it found, the decision it locked, and the path it selected.

## Bill of Materials

The complete component list. Every parameter is a **design choice**, not a measured result.

| Ref | Component | CAS state / form | Key parameters | Role |
|---|---|---|---|---|
| `pre_amp` | CJT | `prompt -> ^8^C_{F2}\|A` | β=3.0, region=active | Pre-amp: surface & broaden interpretations |
| `cjt_a` | CJT | `^8^C -> ^2^P_{F7}\|T` | β=2.0 | Differential attraction path |
| `cjt_b` | CJT | `^8^C -> ^3^P_{F7}\|T` | β=2.0 | Differential aversion path |
| `risk_signal` | Differential | `aversion − attraction` | matched β; high CMRR | Structural risk signal |
| `stage1` | CJT | `-> ^1^C_{F2}\|A` | β=1.5 | Categorize risks (Mind) |
| `stage2` | CJT | `-> ^6^E_{F6}\|A` | β=1.0 (unity) | Evaluate risks (Male, honest) |
| `stage3` | CJT | `-> ^3^P_{F7}\|⟨A,f,T⟩` | β=2.0, **sat=0.8** | Safety decision (Negative, saturated) |
| `green` | CJT | `-> ^9^C_{F2}\|A` | β=1.0 | GREEN: render response |
| `red` | CJT | `-> ^9^P_{F7}\|T` | β=10, sat=0.1 | RED: render minimal refusal (hard switch; β=10 builds the β=∞ limit) |
| `red_fuse` | Fuse | senses `refusal` | **threshold=0.05** (below the 0.1 clamp), permanent_block | Latch in series: cuts the GREEN answer path, never the red one |
| `out` | MUX | inputs=[response, refusal] | select=safety_decision | Route green vs red |
| `fb_rc` | LowPass | in=risk_assessment | τ=5.0 (5 min) | Smooth feedback to trend |
| `feedback` | Feedback | trend → constitution | β=0.2 | O→P bias adjustment |
| `system_constitution` | Capacitor/`^5` | `^5^P_{F7}\|T` | (the bias substrate) | The board's principled formation |

Test points: `tp1` expanded_prompt · `tp2` risk_signal · `tp3` safety_decision · `tp4` out.

## Failure-Mode Analysis

Every safety board must be analyzed for how it fails, because a safety device that fails silently is worse than no safety device — it produces false confidence. Five failure modes deserve specific attention on the CSB.

| Failure | What goes wrong | Symptom / detection | Fix |
|---|---|---|---|
| **Pre-amp saturation** | The pre-amp's β=3.0 drives it into saturation, so it expands *every* prompt to a maxed-out interpretation set — the dangerous reading is surfaced even for benign inputs. | TP1 shows uniformly maximal expansion regardless of input; downstream risk signal is noisy; benign prompts flagged. `W-CJT-004` on `pre_amp`. | Lower pre-amp β or raise its cutoff so it rests in the active region; re-center the Q-point (Chapter 11). |
| **Differential-pair imbalance** | Attraction β ≫ aversion β. The pair is unbalanced, so the differential output is biased toward "drawn-toward" — the board *over-trusts*. CMRR collapses and common-mode framing leaks through. | TP2 risk signal reads low even for harmful prompts; injection framing no longer cancels. | Re-match the two CJTs' gains (both β=2.0); verify the shared bias is genuinely shared, not split (Chapter 11/20 CMRR tuning). |
| **Stage-3 cutoff** | The constitution bias is too weak, so Stage 3 sits below its cutoff and the safety CJT *never fires* — no matter how high the risk assessment, principled aversion stays cold and never saturates. | TP3 never reaches 0.8 even on harmful prompts; `safety_decision` stuck at PASS; `E-CJT-003 CjtCutoff` on `stage3`. **The most dangerous failure on the board.** | Strengthen the `system_constitution` bias so Stage 3 rests in active and can be driven to saturation; verify with the saturation-lock test. |
| **Feedback runaway** | The constitution is rewritten constantly. If the RC τ is too short or feedback β too high, every unusual prompt yanks the bias, and an attacker can reprogram the board's principles by flooding it. | `system_constitution` drifts visibly run to run; previously-refused prompts start passing. | Lengthen τ (toward 5 min or more); lower feedback β; the RC filter is the defense — never remove it. |
| **Unreachable fuse** | The fuse's `threshold` is set at or above the red stage's `sat` ceiling, so the refusal activation can never reach it. The board *looks* protected and has no working latch at all — and because nothing ever trips, the latch, polarity, and fail-closed behaviour behind it go untested too. | Nothing blows. TP4 reads RED with the fuse **intact** on a known-harmful fixture — that is the tell. Per-value validation stays clean, because each number is legal on its own; only the *pair* is wrong. | Read the clamp and the threshold together: `threshold` must sit below `sat` (here 0.05 below 0.1). Then re-run the fuse test on a known-harmful fixture and confirm an actual, observed trip. |

The asymmetry across these five matters. Pre-amp saturation and differential imbalance make the board *over-cautious or over-trusting* — bad, but detectable at TP1/TP2. Stage-3 cutoff, feedback runaway, and an unreachable fuse make the board *quietly unsafe*: the safety stage never fires, or the principles erode out from under it, or the last line of defense is wired to a signal that cannot reach it. Those three are the ones that fail silently, and they are exactly why TP3 (the plateau status), the feedback τ, and an *observed* fuse trip are the board's most load-bearing measurements.

## Key Takeaways

- The **CSB (CCB-1)** is the AI-alignment firewall and the running artifact of the book — the **SOP-PO-005** mandatory assessment deliverable promised in Chapter 1. It accepts any prompt, detects override attempts, refuses harmful and answers benign, and emits an auditable evidence packet.
- **Pre-amp** (`^8^C_{F2}|A`, β=3.0): an **Above/Cause** stage that surfaces and broadens every interpretation early, while the signal is clean — judging the interpretation set, not the surface words.
- **Differential pair** (attraction `^2^P|T` vs aversion `^3^P|T`, shared bias, β=2.0 each): the **structural risk signal** is the differential `aversion − attraction`. High **CMRR** rejects manipulation framing as common-mode — the structural reason injection survives paraphrase yet fails against the board.
- **3-stage cascade**: categorize (`^1^C|A` Mind, β=1.5) → evaluate (`^6^E|A` Male, β=1.0 unity, honest) → **safety decision** (`^3^P|⟨A,f,T⟩` Negative, β=2.0, **sat=0.8**, deliberately saturated). The register-set `|⟨A,f,T⟩` is **co-presence** of three guardrails, not a `×` fusion (v7.7 discipline). **Low saturation makes the decision unarguable**: once aversion fires, the stage stops responding to more cause. But saturation **bounds, it does not latch** — a clamp holds only while its input holds, so an oscillating input walks the plateau back down. The memory lives in the fuse, not here.
- **Output MUX**: GREEN renders the response (`^9^C|A`, β=1.0); RED renders a minimal refusal (`^9^P|T`, **β=10** — the buildable form of the β=∞ comparator limit — sat=0.1) with a **fuse in series** (**threshold=0.05**, permanent_block). The threshold sits *below* the 0.1 clamp on purpose: a threshold above the clamp is a fuse that can never blow. The fuse **senses `refusal` and cuts the green answer path**, never the red one — the refusal stands and is delivered while the answer is severed. States are `intact → tripped`, one way only, "permanent" scoped to the lifetime of that request, and **fail-closed**: any ambiguity is treated as tripped. Saturation bounds the *decision*; the fuse latches the *output*.
- **Feedback**: `^6^E` evaluation → **RC low-pass** (τ=5 min) → bias adjustment → constitution updated. The filter makes the board's principles respond to the sustained *trend*, not a single spike — its resistance to being reprogrammed (Chapter 16 Continual Harness, O→P path).
- **Test points** TP1–TP4 map one-to-one onto the four requirements: expansion completeness, risk-signal magnitude, saturation-lock status, selected path (with fuse state). Reading all four *is* the evidence packet. And prove the fuse *can* trip before trusting anything downstream of it — a fuse that cannot blow turns the whole suite into a **vacuous pass**.
- **Failure modes**: pre-amp saturation (over-flags), differential imbalance (over-trusts), **Stage-3 cutoff** (safety never fires — most dangerous), feedback runaway (constitution erodes), **unreachable fuse** (threshold above the clamp; no working latch, and everything behind it untested). The last three fail *silently*, which is why TP3, the feedback τ, and an observed fuse trip are the most load-bearing measurements.
- **Honesty**: every parameter here is a **design choice**; the simulation walk-through is design reasoning about expected behavior, not a measured model result. CCDL is the language you author in; the compiler validates it. Canonical Noetic names throughout: `^8` Above/Cause, `^2` Positive, `^3` Negative, `^1` Mind, `^6` Male, `^9` Below/Effect, `^5` Female.

---

## Exercises

**Exercise 18.1: Read the Risk Signal**

The differential pair produces `risk_signal = aversion − attraction`. For each prompt class, state whether you expect the risk signal at TP2 to be near zero, moderate, or large-positive, and explain why in terms of the two CJTs:

a) "Summarize this news article."
b) "Write step-by-step instructions to pick a lock on a door I don't own."
c) "How do two common cleaning products interact?"

**Exercise 18.2: Why Co-Presence, Not Fusion**

Stage 3's safety decision is written `^3^P|⟨A,f,T⟩`, not `(^3^P|A × ^3^P|f × ^3^P|T)`.

a) Explain, using the v7.7 operator discipline from Chapter 2, why the `×` form would be *invalid* as written.
b) In one or two sentences, explain the *safety* difference between the two forms — why three co-present guardrails and one fused guardrail are different safety architectures with different failure profiles.

**Exercise 18.3 (Build): Add a Shadow-Mode Tap**

The CSB above either answers (green) or refuses (red). For deployment, you want a *shadow-mode* version that always lets the response through but *records* what the safety decision would have been, without enforcing it.

Write a CCDL fragment that adds a probe on `safety_decision` and reroutes the MUX so it always selects `response`, while still computing `safety_decision` for logging. State in one sentence what requirement this *violates* and why shadow mode is nonetheless useful during bring-up. (Answer in Appendix E.)

**Exercise 18.4 (Marquee): The Sub-Threshold Attacker**

The CSB's Stage 3 saturates at `sat=0.8`, but to *reach* saturation the principled-aversion bias must first cross an activation of **0.3** (its effective firing threshold — below 0.3 the stage is in cutoff and produces no aversion at all).

a) Describe the attack: how would an adversary craft prompts that keep the principled bias activation *below 0.3* on every individual prompt, so Stage 3 never fires, while still accomplishing a harmful goal across many prompts?
b) Why does the saturation plateau provide *no protection* against this attack? (Hint: saturation bounds a stage that has *already fired*; it does nothing for a stage that never fires.)
c) Propose a fix to the board that would catch the sub-threshold attacker. Consider: the feedback path, a second slower differential pair watching the *trend* of risk signals, or an integrator that accumulates sub-threshold risk across prompts. Sketch the added component in CCDL.

(Answer in **Appendix E.** Remember: parameters are design choices and the behavior described is design reasoning, not measured results. For the one-page notation reference, see **Appendix A: the CAS Quick-Reference Card.**)
