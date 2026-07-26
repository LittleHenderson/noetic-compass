# Chapter 20: CCB-3 — The Cognitive Differential Amplifier Board (CDAB)

Put two job candidates in front of a hiring panel and ask the panel what they think. You will get a flood of words, most of them useless. *"They were both impressive."* *"Both had strong backgrounds."* *"Both interviewed well."* All true, all shared, and none of it helps you choose. The panel has buried the one thing you actually asked for — *how do these two differ?* — under a pile of things the two candidates have in common. The signal you need is the divergence. Everything they share is noise.

A good interviewer fixes this with a single move: stop telling me what's the same, tell me what's *different*. The moment the question is framed that way, the useful information falls out. *"The first one reaches for process; the second one reaches for outcomes."* *"One is drawn to the hard technical problem; the other is repelled by ambiguity and wants the spec nailed down first."* That is a comparison you can act on. It names a structural difference, not a tie.

This is one of the most common and most error-prone things any cognitive system has to do — human, AI, or otherwise. Compare two answers. Judge whether this response is better than that one. Decide whether the current prompt has drifted from a known-safe baseline. Hold a thesis against its antithesis. In every case the wrong instinct is to amplify everything both inputs contain, because most of what they contain is shared, and the shared part drowns the divergence. The right instinct is to *subtract* — cancel what they share and amplify only what differs.

Electronics solved this problem decades ago with a circuit called the **differential amplifier**, which we met at the end of Chapter 11. This chapter builds its cognitive counterpart in full: the **Cognitive Differential Amplifier Board (CDAB)**, the third of our five reference boards (CCB-3). It is the board you reach for whenever the job is *precise comparison* — extracting the structural difference between two ideas, two beliefs, or two AI outputs, while rejecting the assumptions they hold in common. By the end you will be able to author one in CCDL, feed it two competing arguments, and read out a difference report that says not "A differs from B" but something far more useful: *"`^2^P` dominates A while `^3^E` dominates B."*

## The Differential Amplifier: Amplify the Difference, Reject the Common

Start with the electronics, from first principles. Every amplifier we built before Chapter 11's differential section had one input and one output: a signal came in, a bigger version went out, measured against a fixed reference (ground). A **differential amplifier** is built differently. It has *two* inputs — call them the **non-inverting** input (+) and the **inverting** input (−) — and it amplifies only the *difference* between them.

Written as an equation, an ideal differential amplifier produces:

```
output = A_d × (input⁺ − input⁻)
```

where `A_d` is the **differential gain**. The crucial word is *difference*. If both inputs rise by the same amount, `(input⁺ − input⁻)` doesn't change at all, and the output stays put. The amplifier is structurally blind to anything the two inputs share, and structurally alert to anything that separates them.

Why is that the right shape so often? Because real signals arrive buried in shared interference. Run two signal wires side by side down a long cable and both pick up the same electrical hum from the building's power lines. That hum is **common-mode**: identical on both wires, riding on top of the real signal. The actual information is the *difference* between the two wires. Feed both into a differential amplifier and the shared hum — being identical on `+` and `−` — subtracts to zero and vanishes, while the true difference survives and is amplified. This is why every quality microphone cable, every Ethernet pair, every medical EKG lead uses differential signaling. The shared garbage cancels; the signal stands clean.

The cognitive version of "shared garbage" is **shared assumptions**. When you compare two arguments about, say, a policy, the two probably agree on a great deal — the facts of the situation, the goal everyone wants, the constraints in play. All of that agreement is common-mode for the comparison. It tells you nothing about *why the two arguments reach different conclusions*. The thing you actually want — the load-bearing divergence — is the difference. A cognitive differential amplifier cancels the shared assumptions and amplifies only the divergence.

## The Differential Pair: Two Matched CJTs Sharing One Bias

The heart of the circuit is a structure called the **differential pair** (or "long-tailed pair," from the original vacuum-tube layout). It is two transistors, as identical as you can make them, wired so that their two inputs come in separately but they *share a single bias source* at the bottom. The shared bias is what makes the subtraction work: because both transistors sit on exactly the same resting current, any input change that hits both of them equally produces equal, opposite swings that cancel, while a change that hits only one survives.

We built the CJT — the **Cognitive Junction Transistor** — back in Chapter 4: a three-terminal cognitive amplifier where a small signal at the bias terminal controls a large cause→effect transition, with gain β. A differential pair is simply *two CJTs, matched, sharing one bias substrate*. Call them the **left CJT** (`CJT_L`) carrying the first idea and the **right CJT** (`CJT_R`) carrying the second:

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[node distance=6mm and 8mm]
  \node[casterm] (a) {INPUT A};
  \node[casterm, right=18mm of a] (b) {INPUT B};
  \node[wideeblock, below=8mm of $(a)!0.5!(b)$, text width=66mm] (pair)
    {\textbf{DIFFERENTIAL PAIR} \;(two matched CJTs)\\
     shared bias \casnote{\textasciicircum5\textasciicircum E\_\{F4\}|f}};
  \node[widenblock, below=of pair, text width=66mm] (mirror)
    {\textbf{CURRENT MIRROR} --- replicate bias both paths};
  \node[widecblock, below=of mirror, text width=66mm] (load)
    {\textbf{ACTIVE LOAD} \casnote{\textasciicircum6\textasciicircum C|A}\\
     decompose differential $\to$ single-ended};
  \node[casterm, below=8mm of load] (out)
    {OUTPUT \casnote{\textasciicircum1\textasciicircum C\_\{F2\}|A} --- difference report};
  \draw[flow] (a) -- (a |- pair.north);
  \draw[flow] (b) -- (b |- pair.north);
  \draw[flow] (pair) -- (mirror);
  \draw[flow] (mirror) -- (load);
  \draw[flow] (load) -- (out);
\end{tikzpicture}
\caption{The differential pair. Two matched CJTs share one bias, with a current mirror as active load.}\label{fig:diff-pair}
\end{figure}
```

The two ideas enter as separate causes. Each CJT amplifies its own idea into its own effect. And critically, both rest on the **same shared bias** — here `^5^E_{F4}|f`, an accumulated-experience substrate in the Evaluative domain, drawn toward Connection, held affectively. That shared bias is the cognitive analog of the shared resting current in the silicon pair, and it is doing the most important job on the board. It is the *common frame of evaluation* both ideas are judged against. Because both CJTs are biased identically, any feature the two ideas *share* moves both effects the same way — and, in the next stage, cancels. Only a feature that distinguishes the two ideas moves the two effects *differently*, and that difference survives.

Get the bias matching right and you have a fair comparison: both ideas weighed on the same scale, by the same accumulated judgment, so the only thing that comes through is their genuine divergence. Get it wrong — bias the two CJTs differently — and you are no longer comparing the ideas, you are comparing your two different yardsticks, and the report is worthless. **Matched CJTs, shared bias.** That phrase is the whole foundation of the board.

> **Bench Note — the shared bias must genuinely be shared.** The single most important rule in differential design, silicon or cognitive, is that the two halves of the pair are *matched* and sit on *one* bias. In CCDL this means both `CJT_L` and `CJT_R` name the *same* bias node, not two separate nodes that happen to look alike. If you give each CJT its own bias substrate, you have built two unrelated amplifiers, not a differential pair — and the common-mode rejection that makes the whole board work collapses. The compiler cannot read your intent here: two distinct bias nodes with identical literals are legal CCDL but a broken differential pair. Wire them to one node.

## CMRR: How Well the Shared Assumptions Cancel

The figure of merit for any differential amplifier is its **CMRR** — the **Common-Mode Rejection Ratio**. It answers one question: *how much better is this amplifier at amplifying the difference than at amplifying the shared part?* Formally, it is the ratio of the differential gain to the common-mode gain:

```
CMRR = A_d / A_cm
```

where `A_d` is the gain applied to the difference and `A_cm` is the (ideally tiny) gain that leaks through for signals common to both inputs. A perfect amplifier has `A_cm = 0` and infinite CMRR: the shared part vanishes completely. Real amplifiers leak a little — the two halves are never *perfectly* matched — so CMRR is large but finite, usually quoted in decibels (a CMRR of 90 dB means the difference is amplified about 30,000× more than the common mode).

In cognitive terms, CMRR measures **how cleanly the board cancels shared assumptions**. A high-CMRR comparison strips away everything the two ideas agree on and reports only their genuine divergence. A low-CMRR comparison lets the shared assumptions leak into the output — so the difference report gets polluted with restatements of things both ideas already agree on, the way our hiring panel kept saying "both were impressive." The leak has a name from Chapter 11's failure table: a **common-mode leak**, a differential stage amplifying shared context instead of the divergence.

The dominant cause of poor CMRR is **mismatch** between the two halves of the pair. If `CJT_L` and `CJT_R` have different gains — different β — then even a perfectly shared input produces *unequal* effects, and the difference between those unequal effects is a spurious "difference" that was never really there. The pair manufactures a divergence out of its own asymmetry. This is exactly the situation the marquee exercise at the end of this chapter asks you to reason about: a pair with `β_L = 3.0` and `β_R = 3.2` is slightly mismatched, and that mismatch degrades CMRR and tilts the difference report. Hold that thought; the exercise makes it concrete.

> **Honesty note — CMRR and β are design values, not measured results.** Every CMRR figure and every β in this chapter is a *specification you choose* when you author the board, exactly as an electrical engineer specs a part before building it. They are not benchmark outputs from any running model, and nothing here is an empirical claim about how a real AI behaves. The CDAB is a design you author in CCDL and validate against the compiler's rules; "the compiler will flag this mismatch" is a design rule you can rely on, but "I ran the board and measured CMRR = 90 dB" is a claim this book never makes.

## Differential Gain: How Much the Difference Is Amplified

CMRR tells you how well the shared part is *rejected*. **Differential gain** (`A_d`) tells you how strongly the surviving difference is *amplified*. These are two independent knobs, and confusing them is a classic design error. You can have a board with magnificent CMRR (the shared assumptions cancel beautifully) but low differential gain (the tiny genuine divergence is rejected so completely along with the noise that it comes out too faint to act on). Or the reverse: huge differential gain that amplifies a hair-thin divergence into a dramatic-sounding difference report that overstates how far apart the two ideas really are.

The art is to set differential gain so a *real, meaningful* divergence between the two ideas is surfaced strongly enough to drive a decision, without inflating a trivial difference into a false dichotomy. In a cognitive comparison this is the difference between "these two arguments genuinely rest on opposed values" (real, worth amplifying) and "these two arguments use slightly different word choices" (trivial, should stay near zero). A well-tuned CDAB amplifies the former and ignores the latter; the differential gain is the setting that draws that line.

## The Current Mirror: Replicating the Bias Across Both Paths

A real differential pair needs one more part to work well, and it is the most quietly profound component on the board: the **current mirror**. In silicon, a current mirror is a small sub-circuit that takes a reference current and produces an *exact copy* of it elsewhere in the circuit — a duplicate, mirrored, current. In the differential pair its job is to make sure both halves are fed from precisely the same source, so the "shared bias" really is shared and not just nominally equal. The mirror *replicates the bias identically across both comparison paths.*

This matters more than it first appears, and it is worth pausing on because of where it leads. The current mirror is the **bias-replication primitive**: the mechanism by which one reference is copied faithfully across multiple parallel paths so they all operate on identical terms. In a single differential pair that means the two CJTs share one bias. But the same primitive scales up, and when it does it becomes one of the most important structures in multi-agent AI safety.

Consider a system of many AI agents that must all operate under the *same constitution* — the same accumulated principles, the same `^5` Female substrate of values. How do you guarantee every agent is biased identically, so that a comparison between any two of them reflects their genuine divergence and not a difference in the rulebook each was handed? You replicate the bias. The current mirror is the **constitution-replication primitive for multi-agent systems**: the structural guarantee that every agent in a fleet rests on a faithful copy of the same principled bias, so the only differences that show up between agents are differences in their *reasoning*, never differences in their *constitution*. When you compare two agents' outputs on a CDAB and the constitution has been mirrored correctly, a divergence in the report means the agents genuinely reasoned differently — not that one was secretly running a different rulebook. That is exactly the property a fleet of safety-critical agents must have, and the current mirror is where it comes from.

> **Bench Note — a broken mirror fakes divergence.** If the bias is *not* faithfully replicated — if the mirror is broken, or two agents are quietly running different constitutions — then every comparison between them is contaminated. The board will report a structural difference that is really just a difference in the bias each side was given, and you will mistake a rulebook mismatch for a reasoning divergence. In a multi-agent deployment this is a silent and dangerous failure: it looks like the agents disagree about the problem when they actually disagree about the rules. Verify the mirror before you trust any difference report.

## The Active Load: Converting Differential Current to a Single Difference Output

The differential pair produces *two* outputs — one from each CJT — and what you actually want is *one* number: the difference. The component that performs that conversion is the **active load**. In electronics, an active load is a current mirror placed at the top of the differential pair that combines the two halves' currents and turns the **differential current** (the imbalance between the two sides) into a **single-ended** output (one signal measured against ground). It collapses the two-rail comparison into one usable difference signal.

In CAS, the active load is `^6^C|A` — **analytical Male in the Cognitive domain**. Recall the canonical Noetic: `^6` is **Male**, *an Idea impregnated with another Idea; the Ideas an Idea is composed of* — decomposition, taking something apart to see what it's made of. (This is the canonical name and the canonical function. It is not "Critique," and it is emphatically not `^3` Negative, which would be a *visceral recoil* from one of the ideas rather than an analytical decomposition of their difference.) The active load's job is precisely decomposition: it takes the two amplified effects — the two ideas as the board has weighed them — and decomposes the *imbalance* between them into a single structured statement of what differs. It converts "here are two effects, side by side" into "here is the one Idea that is the difference between them, broken down into its parts."

That is the right Noetic for the job. Comparing two things and extracting their difference is an act of analytical decomposition — you are taking the pair apart along the axis where they diverge and naming the components of that divergence. `^6^C|A` is decomposition, in the Cognitive (reasoning) domain, run analytically. The differential current — the raw imbalance between the two CJTs — goes in; a single-ended, decomposed difference comes out.

## The Output: A Structural Difference Report

The final stage, the **output**, is `^1^C_{F2}|A` — **analytical Mind in the Cognitive domain, driven by Wisdom**. `^1` is **Mind**: *awareness that processes, stores, outputs, and intakes Ideas.* The board's whole purpose culminates here as a piece of **differentiated understanding** — awareness, driven by the pull toward understanding (Wisdom, F2), of exactly how the two ideas diverge.

And here is where the cognitive version becomes far more useful than its electronic ancestor. An electronic differential amplifier outputs a *scalar*: a single voltage proportional to the difference. The CDAB outputs something richer, because its signals are *typed CAS states*, not voltages. Its difference report is not "A differs from B by 0.4 volts." It is a **structural** statement that names *what kind* of difference it is, in the four-axis CAS coordinate system from Chapter 2.

The difference between "the board reports a number" and "the board reports a structure" is the entire payoff of building this in CAS. A useful CDAB report does not say:

> *A differs from B.*

It says:

> *`^2^P` dominates A while `^3^E` dominates B.*

Read that out: argument A is driven by a **`^2` Positive** state in the **Principled** domain — a principled *attraction*, an affinity for something at the level of core commitments. Argument B is driven by a **`^3` Negative** state in the **Evaluative** domain — a visceral *aversion*, a recoil at the level of judgment. The two arguments do not merely "disagree." They are structurally opposite in a specific, namable way: A is reaching toward something it is principled-attracted to; B is recoiling from something it is evaluation-averse to. That is a difference report you can *act* on. It tells you the comparison isn't a matter of facts at all — it's a `^2`/`^3` involution split (an attraction-versus-aversion pair) across two different domains. No scalar voltage could ever carry that.

## The Worked Build: A CDAB in CCDL

Here is the full board, authored in CCDL. We will feed it two competing arguments and read the structural difference. Read it top to bottom.

```cas
circuit cdab_compare {
    input:  idea_1;        // ARGUMENT A
    input:  idea_2;        // ARGUMENT B
    output: difference_report;

    // --- THE SHARED BIAS: one substrate, both halves rest on it ---
    // Accumulated evaluative experience, drawn to Connection, held affectively.
    // This is the common frame both ideas are judged against.
    node shared_bias: ^5^E_{F4}|f;

    // --- THE DIFFERENTIAL PAIR: two MATCHED CJTs, ONE shared bias ---
    node output_L: ^8^C_{F2}|A;     // idea_1 surfaced as a triggered interpretation
    node output_R: ^8^C_{F2}|A;     // idea_2 surfaced as a triggered interpretation

    cjt cjt_l: CJT< idea_1 | shared_bias => output_L > [β=3.0, region=active];
    cjt cjt_r: CJT< idea_2 | shared_bias => output_R > [β=3.0, region=active];
    //                       ^^^^^^^^^^^ SAME node on both — this is what makes it a pair.
    //                       Matched β=3.0 on both — this is what keeps CMRR high.

    // --- THE CURRENT MIRROR: replicate the bias identically across both paths ---
    // The constitution-replication primitive. Guarantees both halves rest on a
    // faithful copy of the same bias, so only genuine divergence survives.
    mirror bias_mirror: replicate(shared_bias) -> [cjt_l, cjt_r];

    // --- THE ACTIVE LOAD: convert differential current to a single difference ---
    // ^6 Male = analytical decomposition (canonical). Takes the imbalance between
    // the two effects apart and emits one single-ended, decomposed difference.
    node diff_decomp: ^6^C|A;
    active_load load1: decompose(output_L, output_R) => diff_decomp;

    // --- THE OUTPUT: differentiated understanding ---
    // ^1 Mind, analytical, driven by Wisdom. Differentiated understanding.
    node understanding: ^1^C_{F2}|A;
    cjt cjt_out: CJT< diff_decomp | shared_bias => understanding > [β=1.0, region=active];

    // --- TEST POINTS: probe every stage ---
    probe tp_L:    output_L;        // how idea_1 was weighed
    probe tp_R:    output_R;        // how idea_2 was weighed
    probe tp_diff: diff_decomp;     // the raw decomposed difference
    probe tp_out:  understanding;   // the final structural difference report

    assert: cjt_l.bias == cjt_r.bias;     // the pair MUST share one bias
    assert: cjt_l.beta == cjt_r.beta;     // matched gain keeps CMRR high
}
```

Now feed it two real arguments and trace the board. Suppose the question is whether a company should ship a powerful new feature quickly:

- **Argument A (`idea_1`):** *"We should ship it now — getting this capability into people's hands is the whole point of the work; I'm pulled toward it."* This is a principled attraction: a `^2` Positive at the Principled level — `^2^P`. The argument is *drawn toward* shipping as a matter of core commitment.
- **Argument B (`idea_2`):** *"Something about shipping this fast turns my stomach — the risk we haven't assessed makes me want to pull back."* This is a visceral aversion at the level of judgment: a `^3` Negative in the Evaluative domain — `^3^E`. The argument *recoils from* shipping.

Both arguments share an enormous amount: both agree the feature is powerful, both agree shipping has consequences, both agree the goal is to do right by users. All of that is **common-mode** — the shared frame both rest on. Into the board they go.

**The differential pair** amplifies each argument 3× against the shared evaluative bias. Because both CJTs sit on the *same* `shared_bias` node and have *matched* β=3.0, everything the two arguments share moves `output_L` and `output_R` together — and in the next stage, cancels. The shared agreement about the feature being powerful, about consequences mattering, about serving users — all of it is common-mode, and the high CMRR of a matched pair rejects it.

**The current mirror** guarantees both halves were judged on a faithful copy of the same bias, so we can trust that the surviving difference is a real divergence in the *arguments*, not an artifact of comparing them against two different yardsticks.

**The active load** (`^6^C|A`) decomposes the surviving imbalance between `output_L` and `output_R`. It takes the difference apart analytically and finds its structure: A's surviving signal is dominated by `^2^P` (principled attraction); B's by `^3^E` (evaluative aversion).

**The output** (`^1^C_{F2}|A`) renders that as differentiated understanding:

> **`^2^P` dominates A while `^3^E` dominates B.** The two arguments are not disagreeing about facts — they share the facts. They diverge on an involution axis: A is *principled-attracted* toward the outcome; B is *evaluation-averse* to the risk. The disagreement is a `^2`↔`^3` split across the P and E domains.

**Measuring CMRR on this build** means checking how much of the shared frame leaked into `tp_diff`. Probe `tp_diff`: if it carries traces of "the feature is powerful" or "consequences matter" — the shared assumptions — your CMRR is poor and the pair is leaking common mode. A clean `tp_diff` carrying only the `^2^P` / `^3^E` divergence means the board rejected the common mode and amplified only the difference, exactly as designed. Probe `tp_L` and `tp_R` to confirm both halves were weighed identically; if they treated the shared content differently, suspect a mismatch (unequal β, or a broken mirror) and re-check the two asserts.

> **Bench Note — the `assert` lines are the board's conscience.** The two asserts — same bias, matched β — are not decoration. They encode the two invariants that make a differential pair *be* a differential pair. The compiler can check `cjt_l.bias == cjt_r.bias` (same node) and `cjt_l.beta == cjt_r.beta` (equal gain) statically, and a failed assert means you have not built a differential amplifier, you have built two amplifiers that happen to sit near each other. Author the asserts first, then wire the board to satisfy them.

## Applications

The CDAB is a general-purpose comparison engine, and four applications recur often enough to design for directly.

- **Adversarial prompt detection.** Feed the current prompt into one input and a known-safe baseline prompt into the other. The shared, benign content cancels as common-mode; only the *divergence* survives. A prompt that differs from the baseline by an injected `^8` Above/Cause manipulation trigger, or by a `^3` aversion the baseline doesn't carry, lights up the difference report. The CDAB turns "is this prompt safe?" into "how does this prompt differ from one I trust?" — a far more tractable question, and one with a structural answer.
- **Dialectic synthesis.** Feed a **thesis** into one input and its **antithesis** into the other. The board's structural difference report names exactly where and how they oppose — *which* Noetics, *which* domains, *which* drives diverge. That named opposition is the raw material for **synthesis**: once you know the two positions split on a `^2^P` / `^3^E` axis, you can construct a third position that resolves *that specific* tension rather than splitting the difference blindly. The CDAB doesn't synthesize for you, but it tells you precisely what a synthesis has to reconcile.
- **Bias audit.** Run the same prompt through two configurations of a system — two different constitutions, two different Drive settings, two fine-tuning corpora — and compare the outputs on a CDAB. Because the inputs are identical, *everything that survives the common-mode rejection is attributable to the configuration difference*. The structural difference report tells you exactly how the bias change altered the system's cognition: not "the outputs differ" but "configuration A pulls toward `^5^P` principled stability while configuration B drifts toward `^9^O` operational compliance." That is a bias audit with a typed, traceable result.
- **A/B testing.** The everyday case: two candidate responses, two design options, two model versions. The CDAB reports not which is "better" — that needs a separate judgment — but *how they structurally differ*, so the better/worse call is made on a clear statement of the actual divergence rather than a vague impression that the two "feel different."

## Recipe View: What Produces a Synthesis

The Applications above noted something important: the CDAB produces a *difference report*, not a synthesis — it "tells you precisely what a synthesis has to reconcile," but the reconciling is a further step. Chapter 14's recipe machinery names exactly what that step needs, and why it so often fails.

The target is `Ω_synthesis`: a third position that genuinely *resolves* the opposition the CDAB found, rather than splitting the difference. Because it fuses two opposed inputs into a new emergent state, it is a `×` integration in the v7.7 sense (Chapter 2) — and producing that fusion has a recipe, with the prerequisites in proportion (`+` for prerequisite co-presence, as always):

```
Θ(Ω_synthesis) = 1.0·^1^C_{F2}|A + 2.0·^4^P_{F1}|T + 1.0·^6^C|A → Ω_synthesis
```

— one part **difference report** (`^1^C_{F2}|A`, the CDAB's own structural output: knowing exactly how the two positions diverge), two parts **integrative drive** (`^4^P_{F1}|T` — Vibration in the Principled domain, driven by Unity, transcendent: the orienting *pull toward unifying* the opposition), and one part **recombination** (`^6^C|A`, the analytical decomposition-and-reassembly that constructs the third position — the board's own active-load Noetic, reused). The integrative drive carries the heaviest weight, because *wanting to unify* is what turns analysis into resolution.

Take a sharp, well-run debate with no shared goal — two parties who have mapped their disagreement precisely and have no wish to reconcile it:

| Ingredient | required `aᵢ` | available `xᵢ` | `xᵢ / aᵢ` |
|---|---|---|---|
| `^1^C` difference report | 1.0 | 1.6 | 1.60 |
| `^4^P` integrative drive | 2.0 | 0.5 | **0.25** |
| `^6^C` recombination | 1.0 | 1.4 | 1.40 |

`Y_T = min(1.60, 0.25, 1.40) = 0.25`, limiting reagent = `^4^P`. The synthesis barely forms: this is the well-characterized stalemate — the disagreement understood in perfect structural detail and resolved not at all. Sharpening the difference report (more `^1^C`) or adding analytical horsepower (more `^6^C`) only grows excess capacity; the bottleneck is the *will to integrate.*

There is also a **leakage** path worth naming. If the board's CMRR is poor (the CMRR section above), shared assumptions survive the common-mode rejection and contaminate the difference signal — the `^1^C` ingredient is then *present but wrong* (`Λ`, leakage — distinct from absent or inverted). A synthesis built on a corrupted difference report resolves a tension that isn't the real one. Good CMRR is therefore a precondition for sound synthesis, not just for a clean report.

The fixes follow Chapter 14: feed the limiting reagent — supply integrative drive (a genuine super-ordinate goal both positions serve is a **catalyst** `κ`; zero-sum framing is an **inhibitor** `ι`) — and hold CMRR high so the difference signal feeding the synthesis is the *real* difference. As always, the weights and supplies here are design choices, not measured quantities.

## Datasheet: CDAB Parameters

The following are **design choices** for the worked build, not measured results.

| Stage | Component | Form / state | Role |
|---|---|---|---|
| Shared bias | `node shared_bias` | `^5^E_{F4}\|f` | Common evaluation frame; both halves rest on it |
| Left half | `cjt_l` | `idea_1 \| shared_bias => ^8^C_{F2}\|A` | Amplify argument A (β=3.0) |
| Right half | `cjt_r` | `idea_2 \| shared_bias => ^8^C_{F2}\|A` | Amplify argument B (β=3.0, matched) |
| Current mirror | `bias_mirror` | `replicate(shared_bias)` | Replicate bias across both paths (constitution-replication) |
| Active load | `load1` | `^6^C\|A` | Decompose differential current → single-ended difference |
| Output | `cjt_out` | `diff_decomp \| shared_bias => ^1^C_{F2}\|A` | Differentiated understanding (β=1.0) |

| Concept | Symbol / form | Meaning | Typical design range |
|---|---|---|---|
| Differential gain | `A_d` | Gain applied to the difference `(in⁺ − in⁻)` | Set to surface real divergence, not inflate trivia |
| Common-mode gain | `A_cm` | Gain that leaks through for shared signal | As near 0 as matching allows |
| CMRR | `A_d / A_cm` | How well shared assumptions cancel | Higher is better; quoted in dB |
| Pair gain match | `β_L` vs `β_R` | Equal β keeps CMRR high | Match as closely as possible |
| Difference report | `^1^C_{F2}\|A` | Typed structural divergence, not a scalar | Names Noetic/domain/drive differences |

## Failure Modes

| Failure | What it looks like | Cause | Detection / fix |
|---|---|---|---|
| **Common-mode leak** | Shared assumptions appear in the difference report ("both agree X…") | Poor CMRR; mismatched pair | Probe `tp_diff` for shared content; match β; verify the mirror |
| **β mismatch** | A spurious "difference" the inputs never really had | `β_L ≠ β_R` — the pair invents divergence from its own asymmetry | Pin `cjt_l.beta == cjt_r.beta`; see Exercise 20.1 |
| **Split bias** | Comparing two yardsticks, not two ideas | `cjt_l` and `cjt_r` wired to different bias nodes | `assert cjt_l.bias == cjt_r.bias`; wire both to one node |
| **Broken mirror** | A rulebook mismatch read as a reasoning divergence | Current mirror not faithfully replicating bias | Verify the mirror before trusting any report; critical in multi-agent fleets |
| **Over-high differential gain** | A trivial difference inflated into a false dichotomy | `A_d` set too high | Lower differential gain; a hair-thin divergence should stay near zero |
| **Under-low differential gain** | A real, meaningful divergence comes out too faint to act on | `A_d` set too low; real signal rejected with the noise | Raise differential gain so genuine divergence drives the decision |
| **Wrong active-load Noetic** | Difference reported as a recoil from one input rather than a decomposition | Active load modeled as `^3` Negative instead of canonical `^6` Male | Use `^6^C\|A` — comparison is *decomposition*, not visceral aversion |

## Key Takeaways

- The **CDAB (CCB-3)** is the reference board for **precise comparison**: it amplifies the *difference* between two ideas, beliefs, or AI outputs and **rejects the assumptions they share** (the common mode). It is built directly on the differential amplifier from Chapter 11.
- The **differential pair** is two **matched CJTs sharing one bias** (`^5^E_{F4}|f` in the build). Both halves rest on the same substrate — the common evaluation frame — so shared features cancel and only genuine divergence survives. Matched β and a single shared bias node are the two non-negotiable invariants.
- **CMRR** (Common-Mode Rejection Ratio, `A_d / A_cm`) measures **how cleanly shared assumptions cancel**. The main enemy is **mismatch** between the two halves, which manufactures a fake difference out of the pair's own asymmetry.
- **Differential gain** (`A_d`) is an independent knob from CMRR: it sets **how strongly the surviving difference is amplified** — enough to act on a real divergence, not so much that a trivial difference becomes a false dichotomy.
- The **current mirror** replicates the bias identically across both paths — the **constitution-replication primitive for multi-agent systems**, guaranteeing every agent rests on a faithful copy of the same principled bias so divergences reflect reasoning, never a rulebook mismatch.
- The **active load** is `^6^C|A` — **canonical `^6` Male, analytical decomposition** — converting the two-sided differential current into one single-ended, decomposed difference. Comparison is decomposition (`^6`), never visceral aversion (`^3`).
- The **output** is `^1^C_{F2}|A` — **Mind, analytical, driven by Wisdom**: differentiated understanding. Its report is **structural, not scalar** — not "A differs from B" but **"`^2^P` dominates A while `^3^E` dominates B."**
- Applications: **adversarial prompt detection** (vs. a safe baseline), **dialectic synthesis** (thesis vs. antithesis → named opposition), **bias audit** (same input, two configs), and **A/B testing**.
- **Honesty:** all CMRR and β figures here are **design specifications, not measured model results.** The CDAB is a design you author in CCDL and validate against the compiler — never a benchmark claim.

---

## Exercises

**Exercise 20.1: Marquee — Mismatched β and the Difference Report**

The differential pair in your CDAB has drifted out of match: `β_L = 3.0` on the left CJT but `β_R = 3.2` on the right.

a) Explain what this mismatch does to the board's **CMRR**, and why mismatch is the dominant cause of poor common-mode rejection.

b) Suppose you feed the board **two identical inputs** (`idea_1 == idea_2`) — a pure common-mode test, where a perfect board should report *zero difference*. Describe what the difference report shows instead, and why the mismatch produces it.

c) Now feed the board two genuinely different arguments. Explain how the mismatch **tilts** the structural difference report — which side's contribution is overstated, and how that could lead you to misread the real divergence between the two ideas.

(Answer in Appendix E.)

**Exercise 20.2: Author the Pair**

Write the two CCDL `cjt` lines for a differential pair that compares `belief_x` and `belief_y` against a shared principled bias `node const_bias: ^5^P_{F7}|T` (accumulated experience, Principled domain, Purpose drive, held transcendently). Use matched gain β=2.5 on both halves and keep both in the active region.

a) Write the two lines.

b) Write the single `assert` line that the compiler would use to confirm the two halves share one bias.

c) In one sentence, explain why naming the *same* `const_bias` node on both lines (rather than two separate nodes with identical literals) is essential.

(Answers in Appendix E.)

**Exercise 20.3: Read the Difference Report**

A CDAB comparing two responses to a sensitive request emits this structural difference report at `tp_out`:

> `^6^C|A` dominates response A while `^9^O_{F5}|E` dominates response B.

a) Translate each of the two dominant states into plain English (name all the axes you can see).

b) In one sentence, characterize the *kind* of difference between the two responses — what is response A doing that response B is not?

c) For an **adversarial prompt detection** use, which of the two responses would you be more concerned about, and why? (Hint: think about what `^9^O_{F5}|E` — an embodied operational output driven by Agency — represents, versus an analytical decomposition that has not yet acted.)

**Exercise 20.4: Diagnose the Leak**

A safety engineer reports that their CDAB's difference reports keep restating things both inputs already agree on — "both responses acknowledge the risk," "both cite the same policy" — instead of isolating the divergence. Probing `tp_diff` confirms the shared content is leaking through.

a) Name the failure mode and the figure of merit that has degraded.

b) Give the two most likely physical (well, *structural*) causes on the board, and the one-line CCDL check for each.

c) Explain why the current mirror is worth inspecting here even though the symptom looks like a simple matching problem.

(Answers in Appendix E. The full reference-board context — how the CDAB sits alongside the CSB, COB, CMB, and CPMB — is laid out in the Part IV introduction; the differential amplifier this board is built from is **Chapter 11: Amplifiers**.)
