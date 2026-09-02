# Why frequency, phase, width and Q are inert — and where the intuition is right

**Author:** Claude, 2026-09-01 · measured on the RGM-0.1 graph at commit `a086a770` · $0 CPU
**Question (owner):** *"See why frequency, phase, width, Q and the others don't work the way
we need them to, because my intuition is telling me there's something there."*

**Short answer:** the knobs are not weak on this substrate — three of the four are
**mathematically undefined** on it, and the fourth is a renaming of a knob that provably
cannot matter. But the intuition is pointing at a real gap, and I can now name it precisely.

---

## 1. The knobs cannot matter — this is a theorem, not an observation

The engine is `a' = BoundedTopK[(1−δ)a + γWa]`, i.e. repeated application of

```
M = (1−δ)·I + γ·W
```

If `Wv = λv`, then `Mv = ((1−δ) + γλ)·v`. **The eigenvectors of M are exactly the
eigenvectors of W, for every δ and every γ.** Damping and coupling move eigen*values*; they
never move eigen*vectors*.

Since repeated application drives `a` toward the dominant eigenvector, δ and γ can change how
*fast* activation settles — never *where* it settles.

**Measured on the real graph (1600 nodes, 10,352 edges):**

| Setting | \|cos(top eigenvector, W's top eigenvector)\| | Top-20 retrieved set vs baseline |
|---|---|---|
| δ=0.3, γ=0.5 (default) | 1.0000000000 | — |
| δ=0.0 (no damping) | 1.0000000000 | **20/20 identical** |
| δ=0.3, γ=1.0 (double coupling) | 1.0000000000 | **20/20 identical** |
| δ=0.9, γ=0.1 (extreme) | 1.0000000000 | **20/20 identical** |

A 9× change in damping and a 5× change in coupling return **the same twenty memories**.
GLM's ablation result (all four within 0.001 of D) was not a weak effect — it was inevitable.

## 2. Frequency, phase and Q are *undefined* here, not merely unhelpful

Oscillation is **rotation in state space**, and rotation requires **complex eigenvalues**.

The link graph is built by symmetrizing the link *set*, so `W = D⁻¹A` with `A` symmetric.
That is similar to `D^(−1/2) A D^(−1/2)`, which is symmetric — therefore **W has a purely
real spectrum**, and adding `(1−δ)I` only shifts it along the real line.

**Measured:** `max |Im(eigenvalue)| = 0.000e+00` at every parameter setting tested.

Consequences, in plain terms:

- **Phase** is the angle of a rotating quantity. Nothing rotates. There is no angle to set.
- **Frequency** is the rate of that rotation. The rate is zero by construction.
- **Q** is the sharpness of a resonant peak. A real spectrum has no peak, so Q has no
  referent — which is why treating it as a *derived diagnostic* was right.
- **Pulse width** is the one that *is* defined: activation decays as `(1−δ)^t`, so width
  **is** `1/δ`. It is a reparameterization of damping — and §1 shows damping cannot re-rank.

This is why the earlier ruling ("add no knobs") was correct, but for a stronger reason than
"no benchmark needs them yet." You cannot tune the phase of something that never turns.

## 3. What would make them well-defined — measured

Add **one** second state variable per memory (activation + a recovery/adaptation term), the
minimal oscillator:

```
[ a' ]   [ (1−δ)I + γW    −b·I   ] [ a ]
[ r' ] = [    ε·I        (1−ε)I  ] [ r ]
```

**Measured on the same graph** (δ=0.3, γ=0.5, b=0.8, ε=0.25):

- **3200 of 3200 eigenvalues become complex**
- example eigenvalue `0.7499 + 0.4472j` → rotation of **0.5377 rad per wave**
- → a genuine **period of 11.68 waves** — a frequency now exists
- → `|λ| = 0.8731` → **Q ≈ 6.88**, now derivable rather than invented

So the knobs are not wrong. **The substrate is wrong for them.** Complex spectrum arrives
with any one of: a second state variable, signed (inhibitory) coupling, or delayed feedback.
The current engine has none of the three.

## 4. Where the intuition is right

There is a real expressive gap, and it is not about dynamics — it is about **capacity**:

> **One scalar per memory cannot encode *which chain* activated it.**

When two chains are active at once, activation arriving from chain A and from chain B is
summed into the same number and becomes inseparable. The verifier then cannot tell which
retrieved memory belongs to which line of reasoning. That is a genuine limitation of the
current design, and it is exactly the problem that phase-coding (binding-by-synchrony) solves
in biological systems: give each chain a different phase and they stay separable while
sharing the same units.

**So the intuition is pointing at something real.** The instinct that "there's something
there" is tracking a true missing capability.

## 5. The honest caution: phase may be the wrong solution to the right problem

Biology uses phase because a neuron cannot carry a label. **Software can.** The same chain
separation is obtainable by carrying a small **chain-id vector** instead of a scalar —
exact, cheaper, no oscillation, no new parameters, and no risk of interference between
nearby frequencies.

Mapping each proposed knob to its cheaper digital equivalent:

| Knob | What it buys | Cheaper equivalent in software |
|---|---|---|
| Phase | keeps simultaneous chains separable | an explicit chain-id tag |
| Frequency | differing refresh/priority rates | a priority queue |
| Pulse width | how long activation persists | a TTL counter |
| Q | selectivity of what stays active | a threshold |

**The one thing a label does not give you** — and the only candidate I cannot dismiss — is
**emergent sequential competition**. With inhibition plus recovery, winner-take-all
*sequences* arise from the coupling structure rather than being scheduled. Whether that is
useful for memory retrieval is a genuinely open empirical question, and it is the strongest
remaining case for an oscillatory substrate.

## 6. Why the current benchmark could never have shown any of this

Every query in RGM-0/0.1 has **one** target chain. No family requires two chains to be held
apart. So even a perfectly working phase mechanism would have measured zero — the exam never
asks the question.

This is the same structural finding as the J-necessity result: *the instrument cannot test
what the task never demands.* "Inert on this benchmark" is therefore **not** evidence about
oscillation in general. It is evidence about this benchmark.

## 7. The decisive test, if the owner wants the intuition settled ($0 CPU)

**Multi-chain interference benchmark.** Construct queries where two chains are simultaneously
active over overlapping memories, and the correct answer requires knowing which memory
belongs to which chain. Three arms, matched budget:

1. **scalar activation** — the current engine (predicted to fail: no capacity to separate)
2. **scalar + explicit chain-id tag** — the cheap digital solution
3. **2-variable oscillator with phase** — the biological solution

- If **(2) ties or beats (3)** → phase is retired for good, on evidence, and the capability is
  delivered by a tag.
- If **(3) beats (2)** → the intuition is vindicated *with a mechanism*, and a pulse property
  has earned entry under the existing pulse-extension law.
- If **(1) already succeeds** → there was no gap, and the whole line closes.

This is the only experiment I would run on this question, and it is cheap. It tests the
capability, not the vocabulary.

---

## Bottom line

The knobs are inert because the operator shares W's eigenvectors at every setting (measured:
cosine 1.0000000000, top-20 identical under a 9× damping change), and three of the four are
undefined because the spectrum is exactly real (measured: max imaginary part 0.000e+00).

The intuition is nonetheless tracking a real gap — **simultaneous chains cannot be held apart
by one scalar** — and one extra state variable makes the full oscillatory vocabulary
well-defined (measured: period 11.68 waves, Q ≈ 6.88). Whether that vocabulary is the *right*
way to close the gap, or whether an explicit tag closes it more cheaply, is settled by one
benchmark that does not yet exist.


---

## CLOSING NOTE (2026-09-02) — what the three benches this document launched actually settled

This document proposed the multi-chain interference benchmark in §7. It was built three times
(CMB-P0, CMB-P1, CMB-P2) and the owner closed the lane on 2026-09-02.

**§4's claim — that one scalar per memory cannot encode which chain activated it — was never
tested.** All three benches were solvable *without* separating chains: CMB-P0's gold was
findable from one edge weight, then from content, and CMB-P2's from two-hop graph mass, where a
phase-free rule beat an oracle handed the true labels (0.8255/0.8568 vs 0.7682/0.6797). Each
shortcut was created by the repair for the previous one.

So the capacity gap named in §4 remains **an open question, neither confirmed nor refuted**.
What §1 and §2 established — that the knobs cannot re-rank on the RGM-0.1 engine, and that
phase, frequency and Q are undefined on a real spectrum — still stands; those were measured
directly on that engine and do not depend on the benchmark.

**§7's three-arm design was insufficient.** It called for scalar / tag / oscillator. It should
have required a mechanism-free baseline at every depth the mechanism can see — content,
one-hop, two-hop, topology, candidate identity — measured before any arm and re-measured after
every world repair. That is now the registered return condition for any future phase work.

Full record: `cas_only_reasoner/CMB_P2_v0_1/PHASE_LANE_CLOSURE.md`.
