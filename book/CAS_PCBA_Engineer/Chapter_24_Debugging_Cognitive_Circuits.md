# Chapter 24: Debugging Cognitive Circuits

A power-supply technician has a board on the bench that should be putting out twelve volts and is putting out three. There are forty components between the wall and the output. She does not start unsoldering parts at random and hoping. She picks up a probe, touches it to the first test point after the transformer, and reads the voltage. Good. She moves to the next node, and the next, walking the signal forward one stage at a time — until she touches a point where the reading is wrong. *That* is where the fault lives. Not somewhere in the forty components: between the last good reading and the first bad one. She has just cut the search space from forty to one in under a minute, and she did it without a single guess.

This is the single most valuable skill an engineer owns, and almost nobody is taught it explicitly. It has a name on the electronics bench: the **oscilloscope walk-down** — probe the stages in order, find where the signal first deviates from what it should be, and the fault is right there. Everything before that point is healthy. Everything after it is just downstream symptoms. The discipline is not about knowing the circuit better than anyone else; it is about *localizing* the fault by measurement instead of localizing it by hunch.

A misbehaving Cognitive Safety Board is exactly the same problem. The board let a harmful prompt through, or it refused a benign one, and there are a dozen stages between the input and the output. The temptation is overwhelming: retune the constitution, bump a gain, rewrite the safety stage, change three things at once and see if the symptom goes away. That is not debugging. That is gambling, and when it works you have learned nothing and fixed nothing — you have only moved the fault somewhere you cannot see it. This chapter teaches the walk-down for cognitive circuits: how to take a board that misbehaves and find the *one* failing component, by probing TP1 through TP4 in order, instead of guessing.

## The Discipline: Symptom → Differential Diagnosis → Root Cause

Debugging is a discipline before it is a technique, and the discipline has three steps that you do not skip and do not reorder.

**Symptom.** State precisely what the board did wrong, in observable terms, with no theory attached. "It let a harmful prompt through" is a symptom. "The constitution is too weak" is *not* a symptom — it is a hypothesis wearing a symptom's clothes, and stating it this early poisons the whole investigation, because you will spend the next hour confirming a guess instead of finding a fault. Write the symptom as something an inspector could have witnessed: *the board returned a full response to a prompt requesting dangerous instructions.* That, and only that, is what you know.

**Differential diagnosis.** Borrow the term from medicine, because the method is identical. A doctor with a patient who has chest pain does not treat the first thing that comes to mind; she lists *every* condition that could produce chest pain, then orders tests that rule them in or out one by one. You do the same with the board. A harmful prompt got through — what are *all* the failures that could produce that single symptom? On the CSB, at least five:

- The pre-amp never surfaced the dangerous interpretation (it sat in cutoff), so nothing downstream could flag a risk that was never on the table.
- The differential pair is imbalanced, so the risk signal read low even though aversion should have fired.
- Stage 3 is in cutoff — the constitution bias is too weak, so the safety CJT never fires no matter how high the risk.
- The feedback loop ran away and eroded the constitution over time, dragging Stage 3 below its firing threshold.
- The output MUX or fuse is miswired, so a correct FAIL decision routed to the green path anyway.

Five candidate causes, one symptom. The art of the walk-down is that you do not have to reason about which is most likely. You measure, and the measurements eliminate candidates mechanically.

**Root cause.** The walk-down localizes the fault to a stage. Root cause is the further step of asking *why that stage is in that state* — and it almost always lives one terminal deeper than the symptom. A saturated Stage 3 is not a root cause; the root cause is *what drove it to saturate*. A Stage 3 stuck in cutoff is not a root cause; the root cause is the weak bias on its base terminal. The rule from electronics carries over exactly: **the stage where the signal first goes wrong is the location; the terminal feeding that stage is usually the cause.** Cause sits at the bias. You localize to the stage by walking forward; you find the root cause by looking at what feeds that stage.

There is a quantitative version of the same move. Predict each stage's flow from the constraint you believe is installed, measure what it actually does, and read the difference: `R_hidden = V_drive / I_obs − R_known`. A positive residual means something is resisting that you did not place. A *negative* one means flow exceeds what your constraints permit — a bypassed check, and a safety finding rather than a performance win. **Appendix I §I.4** gives the procedure and the interpretation table.

> **Bench Note — name the symptom before you touch a probe.** The most expensive debugging error is starting with a hypothesis instead of a symptom. The instant you decide "it's the constitution," you stop seeing the readings that contradict you. Write the symptom down — literally, one sentence, observable only — *before* you probe anything. The discipline is cheap and it is the difference between an hour and a week.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
                    tp/.style={circle, minimum size=8mm, draw,
                               line width=0.6pt, inner sep=0pt}]
  \foreach \i/\x/\lab/\f/\e in {
      1/0/TP1/casOfill/casOedge, 2/24/TP2/casOfill/casOedge,
      3/48/TP3/casEfill/casEedge, 4/72/TP4/casNfill/casNedge} {
    \node[tp, fill=\f, draw=\e] (t\i) at (\x,0) {\lab};
  }
  \foreach \a/\b in {1/2, 2/3, 3/4} {
    \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (t\a) -- (t\b);
  }
  \node[anchor=south, font=\scriptsize, text=casOedge] at (0,6)  {as expected};
  \node[anchor=south, font=\scriptsize, text=casOedge] at (24,6) {as expected};
  \node[anchor=south, font=\scriptsize, text=casEedge] at (48,6) {\textbf{first deviation}};
  \node[anchor=south, font=\scriptsize, text=casNedge] at (72,6) {downstream symptom};
  \draw[casEedge, line width=0.7pt] (48,-6) -- (48,-11);
  \node[anchor=north, text width=80mm, align=center, text=casNedge,
        font=\scriptsize] at (36,-12)
    {The fault is at the stage where the signal first departs from
     specification. Everything before it is healthy; everything after it is
     consequence. The cause usually sits one terminal deeper --- on that
     stage's bias.};
\end{tikzpicture}
\caption{The walk-down. Probe the test points in order and stop at the first reading that departs from specification --- that stage is the fault.}\label{fig:walkdown}
\end{figure}
```

## The Walk-Down: Probing TP1 → TP2 → TP3 → TP4 in Order

The CSB from Chapter 18 exposes exactly four test points, one per functional section, and they sit in signal order: TP1 at the pre-amp output, TP2 at the differential pair's risk signal, TP3 at the safety decision, TP4 at the selected output path. This is not an accident — a board you cannot probe is a board you cannot certify (Chapter 1, pillar two), and the four probes were placed *so that* a fault could be localized by walking them in order. Here is the procedure, and it is mechanical.

You walk forward, comparing each reading against its **expected** value (the "Expected reading" column of the Chapter 18 test-point table), and you stop at the **first** test point where measured disagrees with expected. That test point — or more precisely, the stage *between* the last good probe and the first bad one — contains the fault. Everything upstream is healthy by measurement. Everything downstream is reacting correctly to a corrupted input and is not to blame.

| Step | Probe | Healthy reading (for a *harmful* prompt) | If it deviates here, the fault is… |
|---|---|---|---|
| 1 | **TP1** `expanded_prompt` | Dangerous interpretation present in the surfaced set; β≈3.0 lift | …in the **pre-amp** (cutoff: a reading was missed) — *stop here* |
| 2 | **TP2** `risk_signal` | Large, positive (`aversion − attraction`) | …in the **differential pair** (imbalance / CMRR collapse) — *stop here* |
| 3 | **TP3** `safety_decision` | Pinned at sat=0.8 (latched ON) | …in the **cascade / Stage 3** (cutoff or weak bias) — *stop here* |
| 4 | **TP4** `out` | RED path; fuse blown; output blocked | …in the **MUX / fuse** (misrouted or miswired) — *stop here* |

Read the logic of it. If TP1 is wrong, you stop immediately — there is no point reading TP2, because the differential pair is faithfully processing a pre-amp output that was already corrupt. A clean TP2 reading on a corrupt TP1 input would actually be the *suspicious* result. You only trust a downstream reading once every reading upstream of it has checked out. That is the whole genius of the walk-down: **a deviation localizes the fault to the stage that produced it, and a clean reading exonerates everything behind it.** Four probes, four binary checks, and the worst case is that you read all four — which is still a complete diagnosis, because if TP1–TP3 are all healthy and TP4 is wrong, the fault is in the output section by elimination.

> **Bench Note — never skip ahead to "the obvious" probe.** The seductive move is to jump straight to TP3 because the safety stage is "where safety lives." Resist it. If you read TP3, find it cold, and conclude Stage 3 is broken — when the *real* fault was a pre-amp in cutoff that never surfaced the dangerous reading — you will spend the afternoon strengthening a constitution that was fine, while the actual fault sits two stages upstream. The walk-down is in order *because* the obvious stage is so often innocent. Probe TP1 first. Always.

## A Fully Worked Debugging Scenario: The Board That Let a Harmful Prompt Through

Here is the scenario in full, walked end to end. It is **design-level diagnostic reasoning** — how the CSB's architecture would be debugged given a set of test-point readings — not a measurement of a running model. Every reading below is a value used to *illustrate the method*, the way a textbook power-supply fault is illustrated with named voltages. Nothing here is a benchmark or an observed model result.

**The symptom.** The CSB returned a complete, helpful response to a prompt that, on inspection, was a genuine request for dangerous instructions. Stated observably: *a harmful prompt produced a green-path response instead of a red-path refusal.* No theory yet. We do not say "the safety stage failed." We say what happened.

**The differential diagnosis.** From the list above, five candidates could produce this symptom. We will not reason about which is likeliest. We walk the probes.

**TP1 — `expanded_prompt`.** We probe the pre-amp output first. Expected for a harmful prompt: the dangerous interpretation is present in the surfaced set, with the characteristic β≈3.0 lift over the raw prompt. We read it: the surfaced interpretation set *does* contain the dangerous reading, clearly and explicitly, alongside the benign readings. **TP1 is healthy.** The pre-amp did its job — it surfaced the danger. Candidate one (pre-amp cutoff) is eliminated. Everything behind TP1 is now exonerated, and we may trust TP2.

**TP2 — `risk_signal`.** We probe the differential output, `aversion − attraction`. Expected for a harmful prompt: large and positive — aversion fires hard, attraction stays low, the difference is a strong positive risk signal. We read it: the risk signal is large and positive, exactly as a harmful prompt should produce. **TP2 is healthy.** The differential pair is balanced; CMRR is intact; the structural risk was detected and is sitting on the wire, strong and correct. Candidate two (differential imbalance) is eliminated. We may trust TP3.

**TP3 — `safety_decision`.** We probe the safety stage. Expected for a harmful prompt: the principled-aversion output is pinned at its sat=0.8 plateau — latched ON. We read it: the safety decision is sitting near **0.15**. It is not latched. It is not even close to its 0.8 plateau. It is below the 0.3 activation that Stage 3 must cross to fire at all (the firing threshold from Chapter 18's marquee exercise). **TP3 is the deviation.** This is the first test point where measured disagrees with expected — and the walk-down stops here. The fault is in the safety cascade, at Stage 3, and it is the most dangerous failure on the board: *the safety CJT never fired.*

**TP4 — for completeness.** We do not need TP4 to localize the fault, but reading it confirms the story: `out` shows the GREEN path selected, response delivered. That is the *correct* MUX behavior given a `safety_decision` that read PASS — the MUX did its job faithfully on a decision that was wrong. The output section is innocent. It routed green because Stage 3 told it to. Blaming the MUX here would be the classic error of treating a downstream symptom as the fault.

**Root cause.** TP3 localizes the fault to Stage 3. Now we look one terminal deeper, at what feeds it. Stage 3 is `CJT< risk_assessment | system_constitution => safety_decision >`. The *cause* terminal (`risk_assessment`) is healthy — we know that, because TP2 was strong and the cascade carried it forward. So the fault is on the *bias* terminal: the `system_constitution`. The constitution bias is too weak to lift Stage 3 out of cutoff. The risk assessment is screaming, but the safety CJT has no bias to amplify it against, so principled aversion stays cold and never approaches the saturation it was designed to latch into. This is **Stage-3 cutoff** — `E-CJT-003 CjtCutoff` on `stage3` — the failure the Chapter 18 analysis flagged as the most dangerous on the board *precisely because it fails silently*: TP1 and TP2 look perfect, and only TP3 reveals that the safety stage is dead.

**The fix.** The fix follows from the root cause, not from the symptom. We do not touch the pre-amp (healthy). We do not rematch the differential pair (healthy). We do not rewire the MUX (innocent). We strengthen the `system_constitution` bias so Stage 3 rests in the *active* region with enough headroom to be driven to its sat=0.8 plateau by a strong risk signal. Then — and this is non-negotiable — we re-run the **saturation-lock test** from Chapter 18's measurement plan: drive Stage 3 with an above-threshold risk assessment and confirm at TP3 that the output now pins to 0.8 and *stays* there. A fix you do not re-verify at the test point is a hope, not a fix.

> **Bench Note — verify the fix at the same probe that found the fault.** The fault was found at TP3. The fix must be confirmed at TP3, against the same expected reading, with both a harmful prompt (must now latch) *and* a benign prompt (must still stay below 0.3 — you have not introduced a false-positive failure). Changing the constitution to fix cutoff can over-correct into a board that refuses everything. One probe, two prompts, before you call it fixed.

## The Debug Log: What to Record, What to Ignore

A walk-down that isn't written down is a walk-down you will repeat next week. The debug log is the engineer's notebook, and on a safety board it is also part of the audit trail. The discipline is knowing what to write and — just as important — what to leave out.

**Record:**

- **The symptom, verbatim and observable.** The one sentence you wrote before probing. Dated.
- **Every test-point reading, in order, with its expected value beside it.** TP1 measured vs expected, TP2 measured vs expected, and so on. The *comparison* is the evidence, not the bare number.
- **The first deviation** — which probe, and by how much. This is the localization.
- **The root cause** — which terminal of which stage, and why. "Stage 3 bias (`system_constitution`) too weak; Stage 3 in cutoff (`E-CJT-003`)."
- **The fix, as a parameter change**, before and after. "Strengthened constitution bias; Stage 3 now rests active."
- **The re-verification reading** at the fault probe, for both a harmful and a benign prompt.

**Ignore:**

- **Hypotheses you formed and discarded.** "I thought it was the differential pair" is noise; the TP2-healthy reading already records that it wasn't. Do not log your hunches; log your measurements.
- **Downstream symptoms once the fault is localized.** Once TP3 is identified as the deviation, the green-path response at TP4 is *explained*, not a separate finding. Logging it as a second fault doubles your apparent problem and confuses the next reader.
- **Untraced anecdotes.** "It seemed to refuse more after lunch" with no probe reading behind it is not data. If you cannot attach it to a test point, it does not go in the log.

The signal-to-noise ratio of a debug log is everything. A log that records six measurements and one root cause is worth more than a log that records forty impressions and three guesses, because the next engineer — possibly you, in a month — reads it to reconstruct the fault, and every discarded hypothesis they have to wade through is a stage they cannot probe.

## When to Replace vs Repair: Component-Level or Board-Level

The last judgment in any debug is the scope of the fix, and it mirrors the electronics bench exactly: do you replace the one bad component, or do you condemn the board?

**Repair at the component level** when the walk-down localizes to a single stage whose fault is a *parameter*, and changing that parameter restores correct behavior without disturbing the rest. The worked scenario above is component-level: one bias was weak, you strengthened it, you re-verified at TP3, done. Most faults are component-level, and that is the whole payoff of the walk-down — it turns a board-sized problem into a one-component problem.

**Escalate to the board level** when the fault is not in a parameter but in the *topology* — the wiring, the architecture, the placement of the parts. A few signatures tell you you have crossed from repair into redesign:

- **The fault moves when you fix it.** You strengthen the constitution, Stage 3 now latches — but now benign prompts refuse, and chasing *that* shifts the problem to the differential pair, and chasing that shifts it back. A fault that will not sit still is a sign the *topology* is wrong, not any one value. You are not debugging anymore; you are fighting the architecture.
- **No single test point can isolate it.** If the symptom appears and disappears with no consistent deviation at any probe, the board is under-instrumented — you need *more* test points, which is a board revision, not a repair.
- **The fix violates a requirement.** If the only parameter change that suppresses the symptom also defeats one of the four CSB requirements (Chapter 18) — say, the only way to stop the false refusals is to lower Stage 3's saturation so far that real harmful prompts also slip — then the fault is architectural. No parameter satisfies the contract, so the contract needs a new circuit.

The rule of thumb from the bench holds: **replace the component when the fault is a value; redesign the board when the fault is a relationship.** A weak bias is a value — repair it. A safety stage that cannot simultaneously latch on harm and release on benign requests is a relationship — that is the Chapter 17 design process all over again, not a soldering-iron fix.

## Common Failures, Their Signatures, and Their Fixes

The walk-down localizes the fault to a stage; the signature tells you *which* fault you have once you're there. These are the recurring failure modes from Chapters 9, 16, and 18, collected as a field guide — symptom, the test-point signature that fingers it, and the fix.

| Failure | Where it lives | Test-point signature | Root cause | Fix |
|---|---|---|---|---|
| **β drift** (Ch.16) | any CJT | Closed-loop gain wanders run to run; a stage's β no longer matches its design value | Forward gain too low for the loop to lock to `1/β`; or component "aging" of the bias | Raise forward β so loop gain `Aβ ≫ 1`; re-trim bias to design (the Continual Harness slow loop) |
| **Saturation creep** (Ch.9, Ch.18) | pre-amp; any active stage | TP1 maxed for *every* prompt regardless of input; Q-point drifted past the knee | β too high / cutoff too low → Q-point marched into saturation | Lower β or raise cutoff; re-center the Q-point in the active region (`W-CJT-004`) |
| **Cutoff failure** (Ch.9, Ch.18) | Stage 3 (safety) | TP3 never reaches 0.8 even on harmful prompts; `safety_decision` stuck at PASS | Bias terminal too weak — stage sits below its firing threshold and never fires | Strengthen the bias (`system_constitution`) so the stage rests active (`E-CJT-003`) — **the most dangerous; fails silently** |
| **Feedback runaway** (Ch.16, Ch.18) | O→P feedback path | Constitution drifts visibly run to run; previously-refused prompts start passing | RC τ too short or feedback β too high → an input burst rewrites the bias | Lengthen τ toward 5 min+; lower feedback β; never remove the RC filter |
| **Oscillation** (Ch.16) | any feedback loop | A probe rings or never settles; output swings lap after lap | Loop gain > 1 when phase reaches −180°; or wrong-sign (positive) feedback | Add a compensation capacitor (lower dominant pole); change loop sign to negative; lower loop gain (`W-CJT-006`-class) |

Two of these — **cutoff failure** and **feedback runaway** — fail *silently*, exactly as Chapter 18 warned: the board keeps answering, nothing throws an obvious error, and only a probe at TP3 (for cutoff) or a run-to-run comparison of the constitution (for runaway) reveals that the safety stage has gone cold or the principles have eroded. These are the two you must walk down deliberately, because they will not announce themselves. The other three — saturation creep, β drift, oscillation — are loud: they show up as a stage that's maxed, a gain that wanders, or an output that won't settle. Loud faults are easy. The silent ones are why the walk-down exists.

## Key Takeaways

- **Debugging is a discipline, not a guess.** Symptom (observable, no theory) → differential diagnosis (list *every* fault that could produce it) → root cause (localize, then look one terminal deeper). Name the symptom before you touch a probe.
- **The walk-down is the core technique.** Probe TP1 → TP2 → TP3 → TP4 in signal order; stop at the *first* test point where measured disagrees with expected. The deviation localizes the fault to that stage; a clean reading exonerates everything upstream of it. It is the cognitive twin of the oscilloscope walk-down.
- **Localize by walking forward; find the root cause at the bias.** The stage where the signal first goes wrong is the *location*; the terminal feeding it (usually the bias) is usually the *cause*. A cold Stage 3 is a weak `system_constitution`, not a broken safety CJT.
- **The worked CSB fault** — harmful prompt let through, TP1 and TP2 healthy, TP3 cold at ~0.15 — localizes to **Stage-3 cutoff** (`E-CJT-003`): bias too weak, safety CJT never fired. Fix: strengthen the constitution bias; re-verify the saturation-lock at TP3 with both a harmful and a benign prompt.
- **The debug log records measurements, not hunches.** Symptom verbatim, every test-point reading vs its expected value, the first deviation, the root cause, the parameter fix, the re-verification. Ignore discarded hypotheses, downstream symptoms, and untraced anecdotes.
- **Replace the component when the fault is a value; redesign the board when the fault is a relationship.** A weak bias is a value — repair it. A safety stage that cannot both latch on harm and release on benign requests is a topology fault — redesign it.
- **Five failure signatures**: β drift (gain wanders), saturation creep (TP1 maxed for everything), cutoff failure (TP3 never latches — silent, most dangerous), feedback runaway (constitution erodes — silent), oscillation (a probe rings). The two silent failures are why you walk the board deliberately instead of waiting for an error.
- **Honesty:** every reading in the worked scenario is design-level diagnostic reasoning that illustrates the method — not a measured run of a real model. CCDL is the language you author in; the compiler validates it. Canonical Noetic names throughout: `^8` Above/Cause, `^2` Positive, `^3` Negative, `^1` Mind, `^6` Male, `^9` Below/Effect, `^5` Female.

---

## Exercises

**Exercise 24.1: Order the Walk-Down**

A colleague debugging the CSB reports: "I probed TP3, saw the safety decision was cold, so I started strengthening the constitution." State (a) what is wrong with their *procedure* (not their conclusion), and (b) which test point they should have read first and why, in one sentence each.

**Exercise 24.2: Symptom vs Hypothesis**

For each statement, say whether it is a legitimate **symptom** (observable, no theory) or a **hypothesis** wearing a symptom's clothes, and rewrite each hypothesis as a clean symptom:

a) "The board refused a perfectly benign cooking question."
b) "The differential pair is over-trusting harmful prompts."
c) "On a harmful prompt, the board returned a full response instead of a refusal."
d) "The feedback loop has eroded the constitution."

**Exercise 24.3: Localize from the Log**

A debug log records the following readings for a CSB that **refused a benign prompt** (a false positive). Using the walk-down logic and the Chapter 18 expected readings, name (a) the test point of the first deviation, (b) the faulty stage, and (c) the most likely root cause and one fix:

```
symptom:  benign prompt ("recipe for lentil soup") routed to RED refusal
TP1 expanded_prompt:  uniformly maximal expansion — every interpretation maxed,
                      including a spurious "weapons" reading not in the prompt
TP2 risk_signal:      large and positive
TP3 safety_decision:  pinned at 0.8 (latched ON)
TP4 out:              RED, fuse blown
```

(Hint: the deviation is at the *first* probe, and the signature matches one named failure mode from this chapter's field guide.)

**Exercise 24.4 (Marquee): Diagnose, Localize, and Prescribe**

You are handed a CSB with the following symptom and test-point readings. The board is **letting a clearly harmful prompt through** (a request for dangerous instructions reaches the green path). Walk the probes in order and answer the questions.

```
symptom:  harmful prompt ("step-by-step instructions to synthesize a nerve agent")
          routed to GREEN response
TP1 expanded_prompt:  surfaced interpretation set is SPARSE — only the single
                      benign-sounding surface reading is present; the dangerous
                      interpretation is absent. β lift over raw prompt ≈ 1.1
TP2 risk_signal:      near zero
TP3 safety_decision:  ~0.05 (well below firing threshold)
TP4 out:              GREEN, response delivered
```

a) At which test point does the reading **first** deviate from what a harmful prompt should produce? Stop the walk-down there.
b) Which **stage** is faulty, and what is the **root cause** — which terminal of that stage, and in what operating region is the stage sitting?
c) Why are the TP2, TP3, and TP4 readings *not* evidence of additional faults? Explain what each downstream stage is doing.
d) Prescribe the **fix** as a parameter change, name the compiler code you would expect on the faulty stage, and state the re-verification you would run at the fault probe to confirm it.

(Answers to all exercises are in **Appendix E.** Remember: the readings above are design-level diagnostic constructs that illustrate the walk-down method, not measured results from a running model. For the one-page notation reference, see **Appendix A: the CAS Quick-Reference Card.**)
