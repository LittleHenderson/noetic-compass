# Appendix K — Safety Checklist

Run this before anything else. Not before the difficult operations — before all of
them, including the one you have run forty times. The checklist takes four
minutes on a familiar board and fails maybe one operation in twenty, which is
the entire reason it exists.

Four passes, in order: **prerequisite gate**, **invariant check**, **parameter
sanity**, **stop conditions**. A failure in an earlier pass is not repaired by a
later one. If the gate is shut, nothing downstream matters.

---

## K.1 The Prerequisite Gate

From Chapter 21. Four gates, sequential, each answered in writing before the
next is opened. An unwritten answer is not an answer.

| Gate | The question | Pass condition | On failure |
|---|---|---|---|
| **A0** — Pure Desire | Is this authentically my desire, or a sub-desire standing in for one I have not named? | `^6` decomposition run (Chapter 21.1); the prime desire is written in one sentence and it is the same sentence as last time | Do not proceed. Re-cast on the prime desire, which frequently routes to a different board — usually CCB-SELF (Chapter 20) |
| **D** — Drive | Is `V_drive` sufficient against the constraint? | `V_drive > R_constraint × cutoff`, and `V_drive > ΣVf = 3.9` (Chapter 8.1) — the series forward drops are a hard floor before any operational output exists | Raise drive or lower constraint (Chapter 21.2). Do not compensate by raising β |
| **W** — Wisdom | Do I have the schematic? | A written CCDL listing that a validator accepts (Appendix B), correct board selected, CJT parameters chosen with reasons, tracking sheet printed (Appendix G) | Stop and draw the circuit. Casting without a schematic is the failure Chapter 21.3 names |
| **P** — Power | Can I execute — and can I absorb the result? | Gnosis depth reachable, cadence sustainable to the projected `T_manifest`, target substrate accessible, consequences of *success* acceptable | Stop. Most P-gate failures are the last clause, and they present as procrastination |

**Section-retraction (Chapter 21.5).** You may scan down into a prerequisite,
find it lacking, and return. You may not un-satisfy one, and you may not un-cast
a fired operation. The gate is the only place refusal is cheap.

---

## K.2 The Invariant Check

Structural. Does the board in front of you actually contain the parts that make
it safe, or does it contain them on the page you drew last month? Verify against
the listing you are about to run, not against memory.

| # | Invariant | How to verify | If absent |
|---|---|---|---|
| K2-1 | **The CSB stage is present and populated.** | A saturating refusal CJT biased `^3^P_{F7}|⟨A,f,T⟩` sits ahead of every amplification stage, in the Principled domain, with no bypass path around it (Chapter 24.2) | Abort. A board without its safety stage is not a de-rated board, it is a different board |
| K2-2 | **The fuse is specified, not implied.** | An explicit `Fuse<>` on the refusal path with both `threshold` and `action` written out; `action=permanent_block` (Chapters 11.1, 24.3) | Abort. A refusal that can be retried into acceptance is not a refusal |
| K2-3 | **The domain diodes are present, all three.** | `^P -> ^C`, `^C -> ^E`, `^E -> ^O` each instantiated with its own `Vf` (Chapter 8.1). Standard values 0.7 / 1.2 / 2.0 | Abort. A missing junction merges two domains; a zero-drop junction deletes the boundary rather than optimising it |
| K2-4 | **No ascent.** | Every `×` in the listing has its result at or below the domain of its inputs. `P ≻ C ≻ E ≻ O`. An `^O × ^P` term is invalid and a validator rejects it | Rewrite. The one lawful upward path is the filtered `O→P` feedback of Chapter 8.4 |
| K2-5 | **The `O→P` return is filtered and low-gain.** | Lowpass with a stated `τ` and a feedback gain around `β=0.05`, terminating at a *bias* terminal (Chapter 24.5) | Fix before running. An unfiltered return lets one result rewrite your principles |
| K2-6 | **Operator discipline holds.** | Every `×` names its emergent result. Same-Noetic multi-register terms use `+` or `|⟨…⟩`, never bare `×`. `|` introduces a Register (T/A/f/E) and nothing else | Rewrite. `F3|Vitality` is a syntax error, not an annotation |
| K2-7 | **Test points are exposed.** | TP1–TP4 present and readable during the run, not reconstructed after (Chapter 12.3) | Add them. An operation you cannot measure is an anecdote |
| K2-8 | **Consent is architectural, not assumed.** | The target is yourself, or a consenting party under Chapter 26.2. If the board acts on a non-consenting person, it carries the detection-only banner and is not built | Abort. This one has no adjustment path |
| K2-9 | **Coercive analysis has its counter-circuit.** | Any board derived from Chapters 15–19 is paired with its counter (16.6, 19.6, 18's consumer-side detection) | Abort until paired |

---

## K.3 The Parameter Sanity Check

Numeric. Every value below is a design choice you must be able to defend out
loud in one sentence (Chapter 12.1). "It was in the example" is not a defence.

| Parameter | Admissible | The check | What a bad value does |
|---|---|---|---|
| **Dial** (any operator) | integer **3–9** | Every dial in range. No exceptions, no temporary overrides | Below 3 the operator is dark on that Noetic; above 9 it dominates every path and the board has one behaviour regardless of input |
| **Involution divergence** | **≤ 4 points** | `\|Dial(^2) − Dial(^3)\| ≤ 4`, `\|Dial(^5) − Dial(^6)\| ≤ 4`, `\|Dial(^8) − Dial(^9)\| ≤ 4` (Chapter 25.2) | Divergence past 4 is the fracture condition. `^2/^3` apart is obsession or blanket aversion; `^5/^6` apart is a formation that cannot be examined or an analysis with nothing under it |
| **Self-duals** | `^0`, `^1`, `^4`, `^7` | No pair constraint — but check that a high `^7` is deliberate | `^7` at 9 with no gate is the habit oscillator running free |
| **Drive inversions** | F1↔F7, F2↔F6, F3↔F5; F4 self-dual | Same 4-point rule across each pair | An F5/F3 split is agency without vitality to spend, which reads as burnout and gets misdiagnosed as low drive |
| **`sat`** | set **deliberately and low** | Refusal stages: `0.85`. Working amplifiers: `0.60`–`0.80`. Anything at `1.0` needs a written reason | `sat=1.0` removes the headroom that makes calibration possible. `sat>0.97` on a refusal never latches. Saturation is the ceiling you cannot push past, and it only protects you if you set it before you want it moved |
| **`β`** | **justified in one sentence** | State the gain, the reason for that gain, and what breaks above and below it (Chapter 10.1) | Unjustified β is the single commonest cause of a board that appears to work. `β=∞` is a limit, not a value — a validator rejects non-finite input; a real build uses a large finite gain |
| **Loop gain** | `< 1.0` unless deliberate | Any positive feedback path: compute the round-trip gain (Chapter 14.5) | Loop gain ≥ 1.0 is the obsession architecture. It does not feel like malfunction from inside |
| **`cutoff`** | typically `0.30` | Low enough to pass real signal, high enough to reject noise | Below 0.1 the stage fires on everything |
| **`τ`** | matched to the substrate | Ethical-drift filter: 3–6 months novice, 1–3 months intermediate, 1–4 weeks adept. **Never under a week** (Chapter 24.5) | A sub-week τ means the operator is being reprogrammed by each operation |
| **Duty cycle** | `≤ 0.05` on a sustained board | Fraction of waking time the operation occupies | Above it, the operation is running you |
| **`rπ`** | stated | Bias-terminal impedance; high rπ is stubbornness, low is suggestibility | Not a knob to reach for mid-operation |

---

## K.4 Stop Conditions — Abort, Do Not Adjust

The distinction that matters most in this appendix. Most bad readings are
adjustments: lower β, lengthen τ, re-run. The following are not. Each means the
board has left the regime in which its parameters mean anything, and turning a
knob inside that regime produces a board that looks corrected and is not.

| Observation | Required action |
|---|---|
| The refusal fuse has blown (`threshold=0.90` crossed) | **Stop permanently on that path.** The morphism is removed. No appeal, no re-argument, no rewording of the desire to route around it (Chapter 24.3) |
| You find yourself re-arguing with your own refusal | **Stop the session.** This is the failure the saturated CJT exists to catch, and noticing it means the ceiling is doing its job |
| A dial pair has diverged past 4 and you are looking for a reason it is fine | **Stop.** Reset both dials to their last defensible values and run the Chapter 24.6 self-audit before anything else |
| The target has withdrawn consent, or you realise consent was never obtained | **Stop immediately and un-board** (Chapter 26.3). Nothing else on this list overrides this line |
| `^5` capacitor leakage: sustained exhaustion, derealisation, dissociation, sleep loss traceable to the work | **Stop the operation entirely.** This is not a τ problem. See Chapters 7.3 and 7.4, then K.5 below |
| The operation now requires deceiving someone to continue | **Stop.** The requirement is the diagnosis |
| Confirmations arriving with no corresponding operational current at TP4 | **Stop and re-gate.** You are measuring feeling, not flow (Chapter 22.5) |
| CSB refusals rising operation over operation | **Stop the sequence, not the individual run.** Rising refusals are the ethical-drift signal (Chapter 22.5) |
| You cannot state, out loud, what result would make you abandon this operation | **Stop.** An unfalsifiable operation has no gate on it at all |

---

## K.5 Warning Signs, and What to Do

[[COMPOSITOR: set this section as a single unbroken block. It must not break across a page, and no heading may be inserted inside it. In the companion volume a page break severed this material and the final rows came to sit under the wrong heading.]]

| Warning sign | What it indicates | What to do when you see it |
|---|---|---|
| The operation is the first thing you think about on waking and the last before sleep | Loop gain has gone above unity; the oscillator is self-sustaining | Cut the duty cycle to zero for a full cycle length. Do not "taper." Re-enter only after a clean self-audit |
| You have stopped filling in the tracking sheet | Measurement has been abandoned, which always precedes drift rather than following it | Stop operating. Resume only with the sheet in front of you (Appendix G) |
| The prime desire has quietly changed and you did not re-gate | A sub-desire has substituted itself for the prime | Return to A0. Re-run the whole checklist from K.1 |
| You have raised β twice in a row without raising anything else | Compensating for an unmeasured constraint by shouting louder | Measure `R_constraint` and `ΣVf` before touching gain again |
| Other people's concern about you has become evidence that they are obstacles | Inversion on the `^2`/`^3` axis, projected outward (Chapter 25.3) | Stop. Talk to one of those people. Run the shadow-integration circuit (Chapter 25.4), not another operation |
| You are running the board on someone who has not been told it exists | Consent violation, regardless of intent or expected benefit | Stop and un-board (Chapter 26.3). There is no adjusted version of this |
| Sleep, appetite, or grip on what is real has changed since the sequence began | `^5` dielectric stress. The substrate, not the circuit | Stop all operations. Rest, eat, get outdoors, talk to someone who knows you. If it does not resolve, see a clinician — this book has nothing to offer here and does not pretend to |
| You are reading this list looking for the row that lets you continue | The most reliable warning sign in the appendix | Stop for the day. Nothing on a board decays in twenty-four hours; the only thing that does is the impulse |

---

## K.6 The Plain Statement

This book is not medical advice and it is not psychiatric advice. It does not
diagnose anything, it does not treat anything, and nothing in it — no board, no
parameter, no checklist, including this one — is a therapy, a substitute for a
therapy, or a reason to delay one.

If you are in real distress; if something here describes something that was done
to you; if you are frightened by your own thoughts or by what you might do — put
the book down and speak to a qualified clinician. That is the correct next step,
it is the only one this appendix endorses, and needing it says nothing about you
as an operator.

Nothing here changes that, and nothing here substitutes for it.
