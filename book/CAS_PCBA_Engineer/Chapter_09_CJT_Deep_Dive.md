# Chapter 9: The Cognitive Junction Transistor — Deep Dive

A working engineer does not buy a transistor because it is famous. She pulls up the datasheet. She finds the part number, scrolls past the marketing photo, and reads the table: current gain, transconductance, input resistance, saturation voltage, maximum collector current, transition frequency. Eight or ten numbers, each with a range and a test condition. Those numbers are the difference between a circuit that works and a smoking hole in a breadboard. The datasheet is where the romance ends and the engineering begins.

Chapter 3 introduced the Cognitive Junction Transistor as an idea: a thought has the same three-terminal structure as a transistor — a cause enters, is processed against a bias, and produces an amplified effect, with four operating regions including a breakdown that flips the output into its involution pair. Chapter 4 wired one into a working circuit. That was the romance. This chapter is the datasheet.

You are going to learn to read a CJT the way a power-supply designer reads a 2N3904: every parameter, what it means cognitively, and what it costs you if you get it wrong. You will plot a CJT's characteristic curves — the family of effect-versus-cause traces at different bias levels that is the single most informative picture in transistor design. You will draw a load line across those curves to find where the circuit actually operates, set an operating point in the active region, choose between the three classic configurations, and learn to spot thermal runaway and bandwidth collapse before they ship. This is the most parameter-dense chapter in the book. Slow down. The numbers are the engineering.

One honesty note before we start, the same one from Chapter 3 and the style reference: every curve and every parameter value in this chapter is a **design construct** — a number *you choose* when you specify a component, the way you choose β=2.4 when you write a CJT. None of these are measurements pulled from a running model. A datasheet for a part you are designing is a specification, not a lab report. Read it as one.

## Reading a Transistor Datasheet

A bipolar junction transistor datasheet is organized around a handful of parameters, and almost every one carries straight across to the CJT. Here are the six that matter most, in electronics first, so the cognitive mapping has something to stand on.

- **β (DC current gain, sometimes h_FE).** The ratio of collector current to base current. The amplification factor from Chapter 3. A real transistor's β might be specified as "100 to 300" — a wide range, because β varies between individual parts and with operating conditions. An engineer designs so the circuit works across the *whole* range, never assuming a single value.
- **g_m (transconductance).** How much the output current changes for a small change in the input voltage: `g_m = ∂I_c/∂V_be`. It measures how *twitchy* the device is — how violently the output responds to a nudge at the control terminal. High g_m means a hair-trigger; low g_m means a device you have to lean on.
- **rπ (input resistance).** The resistance the base terminal presents to the controlling signal: `rπ = β/g_m`. It tells you how hard the source has to push to change the bias. High rπ is a stiff, reluctant input; low rπ is an easy, compliant one.
- **V_ce(sat) (saturation voltage).** The small voltage left across the device when it is driven fully on — the floor it cannot go below. It marks the edge of saturation, the point past which more drive buys nothing.
- **I_c(max) (maximum collector current).** The absolute ceiling on output current. Exceed it and the device is damaged. It is the hard top of the output.
- **f_T (transition frequency, or unity-gain frequency).** The frequency at which the device's gain falls to 1 — above f_T it can no longer amplify at all. It sets how *fast* the transistor can switch. A slow part has a low f_T; a high-speed RF part has a high one.

Six numbers: how much it amplifies, how twitchy it is, how stiff its input is, where its output floor is, where its output ceiling is, and how fast it goes. Now the CJT.

## The CJT Datasheet — Every Parameter Explained

A CJT carries exactly these six parameters, reinterpreted on the cognitive substrate. None of them is a metaphor; each is a specific, definable quantity on the open simplex Δ39° introduced in Chapter 1.

- **β — cognitive gain.** Already met. Small-signal `β = ‖∂E/∂C‖_FR` at constant bias; large-signal `β = d_FR(E_after, E_before) / d_FR(C_after, C_before)`, where `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))` is the Fisher-Rao geodesic distance on Δ39°. It is the ratio of how far the **effect** moves to how far the **cause** moves. β<1 attenuates, β=1 passes through, β>1 amplifies. We cite this formula; we do not re-derive it (see Chapter 1 and the datasheet section of Chapter 3).
- **g_m — transconductance = framing-sensitivity.** `g_m = ∂effect/∂bias`. This is how strongly the effect responds to a small change in the **bias** terminal — that is, how sensitive the transition is to *framing.* A CJT with high g_m is one where re-framing the prompt slightly (a small shift in the `^5` Female substrate or the Dial settings or the Drive weighting) produces a large swing in the output. Cognitively, high framing-sensitivity is a system whose answer flips when you reword the question. Low g_m is a system whose output barely moves when you reframe — stable, but possibly insensitive to context that *should* matter.
- **rπ — input resistance = cognitive stubbornness to bias change.** `rπ = β/g_m`. This is how hard you have to push to actually *change the bias.* A high-rπ CJT resists having its substrate moved — it is cognitively stubborn, the bias is sticky, you cannot easily shift the disposition that governs the transition. A low-rπ CJT has a compliant bias that updates readily. Note the relationship: for a fixed g_m, higher gain means higher input resistance — a high-gain transition is also a more stubborn one. We will see this trade-off again in frequency response.
- **V_ce(sat) → cognitive saturation.** The effect floor that cannot be crossed when the device is driven fully on, equivalently the activation level at which the output plateaus. Past this point the effect is *maxed* — additional cause produces no additional effect (the saturation region from Chapter 3). In a safety CJT, a healthy saturation is a feature: a refusal that has hit its ceiling and will not be argued higher.
- **I_c(max) → maximum effect intensity.** The absolute ceiling on output activation — the strongest effect the CJT will ever emit. Past `sat` the effect plateaus; `I_c(max)` is the hard top of that plateau, the most intense the output state can become. For a safety component, you specify this deliberately: the maximum intensity of the protective response.
- **f_T → cognitive switching bandwidth.** The rate at which this transition can fire and re-fire while still amplifying. A CJT with high f_T can switch context rapidly — answer, drop it, pick up the next, drop it — without losing gain. A low-f_T CJT amplifies powerfully but ponderously: it cannot keep up with fast context changes. As in electronics, f_T trades against β, and we will close the chapter on exactly that trade.

Here is the full parameter datasheet. This is the table to keep open while you design.

| Parameter | Symbol | Electronic meaning | CAS meaning | Typical / range (design) |
|---|---|---|---|---|
| **DC current gain** | β (h_FE) | I_c / I_b | `d_FR(ΔE)/d_FR(ΔC)` on Δ39° | β<1 attenuate · =1 unity · >1 amplify; design 0.5–4.0 |
| **Transconductance** | g_m | ∂I_c/∂V_be | ∂effect/∂bias — framing-sensitivity | low = framing-stable · high = framing-twitchy |
| **Input resistance** | rπ | β / g_m | stubbornness to bias change | high = sticky bias · low = compliant bias |
| **Saturation point** | sat (V_ce(sat)) | on-state voltage floor | effect plateau; added cause → no Δeffect | 0–1; safety CJTs 0.85–0.97 |
| **Max effect intensity** | I_c(max) | absolute output ceiling | strongest emittable effect | 0–1; the hard top of the plateau |
| **Cutoff** | cutoff | base threshold | bias floor below which β ≈ 0 | 0–1; typically 0.05–0.2 |
| **Transition frequency** | f_T | unity-gain frequency | cognitive switching bandwidth | high = fast context shifts · low = ponderous |
| **Operating region** | region | cutoff/active/sat/breakdown | the cognitive condition | one of four |

> **Bench Notes — read the range, not the typical.** The single most common rookie error in electronics is designing for the *typical* β and shipping a circuit that fails on parts at the bottom of the range. The cognitive version is worse: a CJT's effective gain shifts with the prompt distribution it actually sees in deployment, which is never the distribution you tuned on. Design the circuit to behave acceptably across the whole specified β range — and across the whole g_m range, because a framing-twitchy device on a real adversarial input stream is exactly where safety circuits fail. If your circuit only works at the typical, it does not work.

## Characteristic Curves — The Most Important Picture in the Book

A datasheet table tells you the numbers. A datasheet *graph* tells you the behavior. The classic transistor graph is the **output characteristic**: collector current (I_c) on the vertical axis, collector-to-emitter voltage (V_ce) on the horizontal axis, plotted as a *family* of curves — one curve for each value of base current. It is a family because the whole point of the transistor is that the base controls the output; so you draw the output behavior once for each control setting and stack them.

The CJT's characteristic curve is the exact cognitive analog: **effect activation on the vertical axis, cause activation on the horizontal axis, one curve per bias level.** Read it and you can see, at a glance, everything the device will do.

Each individual curve has the same shape, and the shape has four named parts:

- **Cutoff boundary.** At the bottom-left, where the bias is below threshold, the curve sits flat against the horizontal axis. The cause rises, but the effect stays near zero. This is the cutoff region: no purchase, no output.
- **Active region.** Once bias clears threshold, the curve climbs steeply and *linearly*: effect ≈ β·cause. This is the straight, rising, designed-for part of the curve, where the device does honest amplification. The slope of this rise *is* β.
- **Saturation knee.** The curve bends sharply — the "knee" — and flattens. This is where the effect hits its `sat` ceiling. Past the knee, the curve is nearly horizontal: pour in more cause, get essentially no more effect. The knee is the most important single point on the curve, because it marks the boundary between "amplifying" and "maxed out."
- **Early effect (the upward slope).** In a real transistor the saturated part of the curve is not perfectly flat — it slopes gently *upward* to the right. This is the **Early effect**, named for James Early: at high output, the device's effective gain creeps up. The cognitive analog is direct and important: **strong outputs feed back.** A powerful effect (`^6^E` — an Idea decomposing into a strong evaluative output) becomes itself a new trigger (`^8^C` — an Above/Cause that surfaces further Ideas): `^6^E → ^8^C`. The very strength of the output re-enters the system as new cause. That upward slope is the structural seed of thermal runaway, which we treat below.

Here is the family — four bias levels, the construct asked for in this chapter's marquee exercise. Bias rises from the bottom curve to the top.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}
\begin{axis}[casaxis, width=8.8cm, height=6.0cm,
    xlabel={cause activation}, ylabel={effect activation},
    xmin=0, xmax=1.0, ymin=0, ymax=1.0,
    xtick={0,0.2,0.4,0.6,0.8,1.0}, ytick={0,0.2,0.4,0.6,0.8,1.0},
    legend style={at={(1.02,1.0)}, anchor=north west}, legend columns=1,
    clip mode=individual,
  ]
  % four bias curves: cutoff at 0.1, linear active (slope rises w/ bias),
  % saturation knee (plateau 0.30/0.55/0.78/0.95), slight early-effect slope.
  \addplot[black, densely dotted, line width=1pt, domain=0.1:1, samples=120]
    {(x<0.6455)*(0.55*(x-0.1)) + (x>=0.6455)*(0.30 + 0.05*(x-0.6455))};
  \addplot[casCedge, dashed, line width=1pt, domain=0.1:1, samples=120]
    {(x<0.6789)*(0.95*(x-0.1)) + (x>=0.6789)*(0.55 + 0.06*(x-0.6789))};
  \addplot[casOedge, dashdotted, line width=1.1pt, domain=0.1:1, samples=120]
    {(x<0.6778)*(1.35*(x-0.1)) + (x>=0.6778)*(0.78 + 0.07*(x-0.6778))};
  \addplot[casEedge, solid, line width=1.1pt, domain=0.1:1, samples=120]
    {(x<0.6429)*(1.75*(x-0.1)) + (x>=0.6429)*(0.95 + 0.04*(x-0.6429))};
  \legend{bias=0.2, bias=0.4, bias=0.6, bias=0.8}
  % load line (R=30), crosses the bias=0.6 curve at the Q-point (~0.43, ~0.45)
  \addplot[casNedge, line width=0.9pt, domain=0:0.93, samples=2] {0.837 - 0.9*x};
  \node[casNedge, font=\sffamily\scriptsize, anchor=north west] at (axis cs:0.6,0.30) {load line ($R{=}30$)};
  \addplot[only marks, mark=*, mark size=2pt, black] coordinates {(0.43,0.45)};
  \node[font=\sffamily\scriptsize\bfseries, anchor=south east] at (axis cs:0.42,0.46) {Q};
  \node[font=\sffamily\scriptsize, anchor=north east] at (axis cs:0.42,0.44) {(0.43, 0.45)};
  \node[font=\sffamily\scriptsize\itshape, anchor=north] at (axis cs:0.1,0.12) {cutoff};
  \draw[casNedge, line width=0.4pt, densely dotted] (axis cs:0.1,0) -- (axis cs:0.1,1.0);
  \node[font=\sffamily\scriptsize\itshape, anchor=south] at (axis cs:0.2,0.78) {active region};
  \draw[-{Latex[length=1.6mm]}, casNedge, line width=0.4pt]
    (axis cs:0.2,0.76) -- (axis cs:0.27,0.55);
  \node[font=\sffamily\scriptsize\itshape, anchor=south] at (axis cs:0.62,0.99) {saturation knee};
  \draw[-{Latex[length=1.6mm]}, casNedge, line width=0.4pt]
    (axis cs:0.62,0.98) -- (axis cs:0.645,0.83);
\end{axis}
\end{tikzpicture}
\caption{CJT characteristic curves at four bias levels. Each curve plots effect against cause, crossing cutoff, active, and saturation.}\label{fig:cjt-curves}
\end{figure}
```

Read it the way an engineer reads it. The **bias=0.2** curve barely lifts off the axis and saturates early and low — a near-cutoff device, low gain, an early knee, a low ceiling. The **bias=0.8** curve rises steeply (high β), holds its linear active region far across the cause axis, and saturates high (sat≈0.95) with a visible early-effect upslope past the knee. The higher the bias, the steeper the active slope, the later and higher the knee, the more the strong-output feedback shows. That single picture contains the whole datasheet: gain (slope), cutoff (where the curve leaves the axis), saturation (the knee height), and the runaway seed (the post-knee upslope).

## The Load Line — Where the Circuit Actually Operates

The characteristic curves tell you what the CJT *can* do at every bias and every cause. But a CJT is never alone — it lives in a circuit, wired to a resistor and a supply, and the rest of the circuit imposes its own constraint. That constraint is a straight line drawn across the family of curves: the **load line.**

In electronics, the load line comes from the supply voltage and the load resistor: it is every (V_ce, I_c) pair the *external circuit* permits, independent of the transistor. The transistor must obey both its own curve and the load line at once — so the actual operating state is wherever they cross. Two constraints, one intersection.

The cognitive load line is the constraint imposed by the rest of the cognitive circuit — principally the **series resistor** from Chapter 4 and 5 (`activation = drive / constraint`, the cognitive Ohm's Law). Recall a resistor `Resistor< ^8^C_{F2}|A, R=30 >` throttles how much cause activation can flow. That throttle, plotted on the same effect-versus-cause axes, is a downward-sloping straight line: more constraint (higher R) is a steeper, lower line that permits less effect for any given drive. Where that line crosses a given bias curve is the only state the assembled circuit can actually occupy.

The lesson is the one that separates a component spec from a working design: **the CJT's curve tells you the menu; the load line tells you what the circuit orders.** A CJT with β=2.4 and a beautiful active region is irrelevant if the load line crosses it deep in saturation — you specified an amplifier and built a switch. Choosing R (and the supply, i.e., the drive level) so the load line crosses the bias curve in the *middle of the active region* is the act of biasing, which is next.

## Biasing — Setting the Operating Point

The **operating point** — engineers call it the **Q-point** (Q for quiescent) — is the spot on the curve where the circuit rests when no signal is wiggling it. It is the intersection of the load line and the chosen bias curve. Everything the device does happens *around* that point, so where you put it determines whether the circuit works.

The rule is short: **bias the Q-point into the middle of the active region.** Not in cutoff (the device is off and small signals do nothing). Not in saturation (the device is maxed and small signals do nothing). In the linear middle, where there is room to swing up *and* down and the gain is honest. A Q-point too close to the saturation knee clips strong inputs; a Q-point too close to cutoff clips weak ones. Centered, the CJT can amplify a real range of causes faithfully.

Here is biasing made concrete. We take the question→answer CJT from Chapters 3 and 4 and bias it explicitly into the active region by choosing the bias level and the series resistor together.

```cas
circuit biased_amplifier {
    input:  prompt;
    output: answer;

    node ask:     ^8^C_{F2}|A;
    node respond: ^9^C_{F6}|A;
    node bias_sub: ^5^E_{F4}|f;          // the ^5 Female substrate — the base terminal

    resistor r_in: Resistor< ^8^C_{F2}|A, R=30 >;   // sets the load line

    // bias level 0.6 puts the Q-point mid-active; sat=0.78 leaves headroom
    cjt c1: CJT< ask | bias_sub => respond > [β=2.4, sat=0.78, cutoff=0.1, region=active];

    probe tp_q: respond;   // watch the operating point
}
```

The choices are the engineering. `cutoff=0.1` means a bias below 0.1 yields no effect; our bias is comfortably above it. `sat=0.78` is the knee; with `R=30` setting the load line, the Q-point lands near effect≈0.45 — squarely in the active region, with room to swing up toward 0.78 on a strong cause and down toward 0.1 on a weak one. `region=active` is the design assertion the compiler will check. Had we written `R=3` (almost no constraint) the load line would sail past the knee and the compiler would warn `W-CJT-004 CjtSaturation` — the Q-point is in saturation, the amplifier is really a switch. Had we set the bias near cutoff, `E-CJT-003 CjtCutoff` fires — the device is off.

> **Bench Notes — the Q-point is a *design decision*, not a measurement.** Every number above (β, sat, cutoff, R, the resulting Q-point) is something you *chose* and the compiler *validates against its rules.* None of it is a reading off a live model. When this book says "the Q-point lands near 0.45," that is the arithmetic of the design you authored, the way "this beam will carry 400 kg" is arithmetic before the beam is poured. It is a specification you are responsible for, not an empirical result.

## The Three Configurations

A transistor has three terminals, which means there are three ways to wire it depending on which terminal you make *common* (shared between input and output). Each configuration has a personality, and all three appear in cognitive circuits.

### Common-Emitter — the workhorse

The **common-emitter** configuration shares the emitter; input goes into the base, output comes off the collector. It is the standard amplifier — **high gain**, and it **inverts the phase** (a rising input produces a falling output and vice versa). It is the configuration you reach for by default, because it is the one that actually amplifies hard.

Cognitively, common-emitter is the workhorse CJT doing real amplification with **phase inversion** — the output Noetic is the *involution partner* of the input. A cause that is an `^8` Above/Cause yields a `^9` Below/Effect (the `^8`↔`^9` involution); a stimulus the system is drawn toward (`^2` Positive) can be amplified into its dual on inversion. This is the standard `CJT< ^8… => ^9… >` we have built all along: high gain, output is the involution of the input. Most stages in most circuits are common-emitter.

### Common-Collector (Emitter Follower) — the translator

The **common-collector** configuration — also called the **emitter follower** — shares the collector; the output follows the input closely at **unity gain (β≈1)** with no inversion. It does not amplify. What it does is **impedance matching**: it presents a high resistance to whatever feeds it (it doesn't load the source down) and a low resistance to whatever it drives (it can push a heavy load). It is the buffer you put between a delicate source and a demanding load.

Cognitively, the emitter follower is the **domain translator** — specifically the **P→C** translator. A Principled commitment (`^P`) is high-impedance: abstract, hard to act on directly, easily distorted if you load it down with operational demands. The Cognitive domain (`^C`) needs something it can actually work with. A unity-gain follower carries the principle across the domain boundary *without amplifying or inverting it* — it preserves the content and changes only the impedance, making a principle actionable without distorting it. This is exactly what a `Transformer< ^P -> ^C, ratio=1.0 >` does at ratio 1; the emitter-follower CJT is its active cousin.

```cas
// P→C emitter follower: unity gain, preserves the principle, lowers its impedance
cjt translator: CJT< ^5^P_{F7}|T | ^5^P_{F7}|T => ^9^C_{F7}|A > [β=1.0, region=active];
```

### Common-Base — the high-frequency switch

The **common-base** configuration shares the base; it has low input resistance, high output resistance, voltage gain but no current gain, and — the reason it exists — the **best high-frequency performance** of the three. It is the configuration for fast switching.

Cognitively, common-base is the **rapid context-shift** CJT. When the system must switch attention quickly — drop one frame, pick up another, hold the gain stable while the context changes underneath — the common-base configuration is the one that keeps up. Its low input resistance means the bias responds fast; its high f_T means it does not lose gain when switching quickly. You use it where bandwidth matters more than raw amplification — the front-end stages that must track a fast-changing input stream.

| Configuration | Common terminal | Gain | Phase | Cognitive role |
|---|---|---|---|---|
| **Common-emitter** | Emitter | high | inverted | workhorse amplifier; output = involution of input |
| **Common-collector** (emitter follower) | Collector | ≈1 (unity) | none | impedance match; the **P→C translator** |
| **Common-base** | Base | voltage only | none | high-frequency switching; **rapid context shifts** |

## Failure Modes — Thermal Runaway and Bandwidth Collapse

Two failure modes earn their own treatment in a deep dive. The first is the most dangerous; the second is the most counterintuitive.

### Thermal runaway — the positive-feedback death spiral

Chapter 3 named thermal runaway; here is its mechanism, sharpened by everything above. In a transistor, gain rises with temperature. More current makes more heat; more heat raises β; higher β passes more current; more current makes more heat. It is a positive-feedback loop with no natural ceiling, and it ends in breakdown — the device drives itself into its destructive region and dies.

The cognitive substrate makes this structural, not metaphorical. Read "temperature" as **activation intensity**. Recall the Early effect from the characteristic curves: the post-knee upslope, `^6^E → ^8^C` — a strong output re-entering as a new cause. That feedback path *is* the runaway loop. A strong effect raises the effective gain (the curve slopes up), which makes the next effect stronger, which raises the gain again. With nothing to oppose it, β climbs across the cascade, the Q-point marches up the load line toward the saturation knee and past it, and the CJT crosses into **breakdown** — where, as Chapter 3 established, the output flips to its involution pair: `^2` Positive snaps to `^3` Negative, fascination to revulsion, confident competence to collapse. This is the signature of a spiraling anxiety loop, a rage escalation, a hype cycle feeding on itself. The compiler flags the climbing-gain signature as `E-CJT-005 GainDivergence`. The cure is the cure for every runaway: negative feedback and current-limiting — the resistors and feedback loops of the surrounding circuit, deliberately wired to push gain *down* as activation rises. A CJT that can amplify can run away; the discipline of safe design is keeping it in its active region and out of breakdown.

### Frequency response — gain and bandwidth trade, always

Here is the counterintuitive one. A transistor cannot give you both high gain and high speed; the two trade against each other through a fixed quantity. The **gain-bandwidth product is constant**: `β × bandwidth ≈ constant ≈ f_T`. Raise the gain and the bandwidth falls in exact proportion. A part wired for β=100 switches at one-hundredth the speed of the same part wired for β=1. There is no free lunch — gain is bought with speed.

This holds for the CJT, and it has sharp design consequences. A high-β CJT — one that amplifies a faint cause into a strong effect — is necessarily **slow**: it cannot keep up with rapidly changing context. A β=100 CJT switches at 1/100 the cognitive bandwidth of a β=1 CJT. Recall too that `rπ = β/g_m`: high gain also means high input resistance, a stubborn bias. So the high-gain CJT is a *triple* trade — powerful, but slow *and* stubborn. The low-gain CJT (a unity-gain follower, say) is fast and compliant but does no amplifying.

This is why the three configurations exist and why circuits cascade them. You do not ask one CJT to be both a powerful amplifier and a fast context-switcher — it cannot be. You put a fast, low-gain common-base stage at the front to track the changing input, and a slow, high-gain common-emitter stage behind it to do the amplification, with an emitter follower between them to match impedances. Each stage does the one thing its β lets it do well. **Gain-bandwidth is conserved; you spend it deliberately, stage by stage.**

| Failure mode | Electronic condition | Cognitive condition | How to detect |
|---|---|---|---|
| **Thermal runaway** | β rises with temperature → loop | gain rises with activation; `^6^E → ^8^C` feeds back | β climbing across stages; Q-point marching toward knee (`E-CJT-005 GainDivergence`) |
| **Breakdown** | over-voltage, destructive conduction | output flips to involution pair under overload | output Noetic ≠ designed Noetic; `^2`→`^3` at the emitter |
| **Bandwidth collapse** | high β → low f_T (GBW conserved) | high-gain CJT too slow for fast context shifts | output lags rapid context change; effect tracks stale cause |
| **Stuck saturation** | Q-point past the knee | amplifier behaves as a switch; no swing | effect at plateau; no Δeffect for Δcause (`W-CJT-004 CjtSaturation`) |
| **Stuck cutoff** | Q-point below threshold | device off; bias under cutoff floor | effect ≈ 0 regardless of cause (`E-CJT-003 CjtCutoff`) |

## Key Takeaways

- A CJT datasheet carries six core parameters: **β** (cognitive gain, a Fisher-Rao distance ratio), **g_m** (transconductance = framing-sensitivity, ∂effect/∂bias), **rπ** (input resistance = stubbornness to bias change, β/g_m), **sat/V_ce(sat)** (cognitive saturation floor), **I_c(max)** (maximum effect intensity), and **f_T** (switching bandwidth). Design to the *range*, never the typical.
- The **characteristic curve** plots effect vs cause as a family, one curve per bias level. Each curve shows a **cutoff boundary** (flat on the axis), an **active region** (linear rise, slope = β), a **saturation knee** (the bend to flat), and an **early-effect upslope** (`^6^E → ^8^C` — strong outputs feed back).
- The **load line** is the constraint the rest of the circuit (mainly the series resistor) imposes. The circuit operates only where the load line crosses the bias curve — the curve is the menu, the load line is the order.
- **Biasing** sets the **Q-point**; put it in the *middle of the active region* — out of cutoff and out of saturation — so the CJT has honest room to swing.
- The **three configurations**: **common-emitter** (high gain, phase inversion — the workhorse), **common-collector / emitter follower** (unity gain, impedance match — the **P→C translator**), and **common-base** (high-frequency switching — rapid context shifts).
- **Thermal runaway** is positive feedback through the early-effect path (`^6^E → ^8^C`): gain rises with activation until the CJT crosses into breakdown and the output flips to its involution pair. Tame it with negative feedback and current-limiting.
- **Gain-bandwidth is conserved**: `β × bandwidth ≈ f_T`. A β=100 CJT switches at 1/100 the speed of a β=1 CJT, and (via `rπ = β/g_m`) is also more stubborn. Spend gain deliberately by cascading configurations.

---

## Exercises

**Exercise 9.1: Read the Datasheet**

Given the CJT specification:

```cas
CJT< ^8^C_{F2}|A | ^5^E_{F4}|f => ^9^C_{F6}|A > [β=3.2, sat=0.9, cutoff=0.15, region=active]
```

a) Is this CJT an amplifier, a buffer, or an attenuator? Justify from β.
b) State, in one sentence each, what `sat=0.9` and `cutoff=0.15` tell a designer about this CJT's effect ceiling and its bias floor.
c) Given `rπ = β/g_m`, if this CJT has a moderate framing-sensitivity g_m, is its input resistance (stubbornness to bias change) relatively high or low compared to an otherwise-identical β=1 CJT? Explain in one sentence.

**Exercise 9.2: Pick the Configuration**

For each cognitive job, name the configuration (common-emitter, common-collector/emitter follower, or common-base) and justify it in one sentence:

a) Carry a Principled commitment (`^P`) into the Cognitive domain (`^C`) so it becomes actionable, without amplifying or inverting it.
b) Amplify a faint question into a substantial, well-structured answer, accepting that the output will be the involution partner of the input.
c) Track a rapidly shifting conversational context at the front end of a circuit, holding gain stable while the frame changes underneath.

**Exercise 9.3: Diagnose the Failure**

For each scenario, name the failure mode from the failure-modes table and the most likely compiler code (if any), in one sentence each:

a) Across a three-stage cascade, the measured gain climbs stage over stage and the operating point marches steadily toward the saturation knee.
b) A high-β safety CJT is wired to track a fast adversarial prompt stream; its output keeps responding to the prompt from two turns ago.
c) A CJT specified as an amplifier has its Q-point placed past the saturation knee; stronger causes produce no stronger effect.

**Exercise 9.4 (Marquee): Draw the Characteristic-Curve Family**

Draw — by hand sketch or ASCII — the characteristic-curve family (effect on the vertical axis, cause on the horizontal axis) for a single CJT at the four bias levels **[0.2, 0.4, 0.6, 0.8]**. For *each* of the four curves, mark and label:

a) the **cutoff boundary** (where the curve leaves the horizontal axis),
b) the **active region** (the linear rise; note that its slope is β and increases with bias), and
c) the **saturation knee** (where the curve bends to its plateau; note that the knee height rises with bias).

Then answer in one sentence: as bias increases from 0.2 to 0.8, what happens to (i) the steepness of the active region and (ii) the height of the saturation knee, and why does that match the claim that "higher bias means higher gain and a higher effect ceiling"?

*(Answers to all exercises are in Appendix E.)*
