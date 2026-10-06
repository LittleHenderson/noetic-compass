# Qubits in the CAS PCBA: what the state space already is, and what a CJT forbids

**Date:** 2026-08-27
**Status:** exploratory design note. No implementation, no commitment.
**Sources:** `CAS_PCBA_Engineer.docx`, `RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf`,
`CAS_Ohm_Quantification_Guide.pdf`, CLAUDE.md Corrections 2 and 4

---

## 1. The observation that reframes the question

CAS does not need a quantum state space added. **It already specifies one and then
restricts it.**

CLAUDE.md Correction 4 mandates:

> Target space is `S°_I = Δ39° = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }`
> Fisher-Rao metric. Geodesic distance `d(p,q) = 2·arccos(Σ√(pk·qk))`

Take the amplitude map `ψ = (√p₁, …, √p₄₀)`. Then `Σψₖ² = 1` — the state is a
**unit vector in a 40-dimensional real space**. And the mandated distance is
exactly twice the angle between two such vectors.

Now the quantum side. For two density matrices that commute — i.e. diagonal in
the same basis, with eigenvalues `p` and `q` — the Uhlmann fidelity is
`√F = Σ√(pₖqₖ)` and the **Bures angle** is `arccos(Σ√(pₖqₖ))`.

Verified numerically on a worked example:

```
fidelity            0.964240
Fisher-Rao d        0.536474   (CAS Correction 4)
2 x sphere angle    0.536474
2 x Bures angle     0.536474   (quantum, diagonal rho)
```

All three coincide, identically, by construction rather than by coincidence.

> **The CAS state space is the real, non-negative, phase-free slice of a
> 40-dimensional quantum state space, carrying the quantum metric.**

So "introduce qubits" is not *adding* machinery. It is **removing three
restrictions CAS already imposes**:

| Restriction | Lifting it admits |
|---|---|
| amplitudes are real | relative **phase** between cognitive states |
| amplitudes are non-negative | **destructive interference** between paths |
| the state is a point on the simplex (diagonal `ρ`) | **coherence** — off-diagonal terms |

Scale, for orientation: 40 states is `log₂ 40 ≈ 5.32` qubits. Domain (4) ⊗
Register (4) is **exactly 4 qubits**; Noetic (10) and Drive (7) are not powers of
two and would need padding or a qudit treatment.

## 2. What lifting each restriction actually buys

### 2.1 Coherent ambivalence — the Ambivalence Analyzer is the test case

From the PCBA Engineer document, the classical treatment of a genuinely
conflicted stimulus:

```
gate dissonance: XOR< attract, averse >;        // fires → genuine conflict
schmitt stabilize: SchmittTrigger< input=stimulus,
    on_threshold=0.7, off_threshold=0.3,
    high_state=attract, low_state=averse >;      // the 0.3–0.7 band is dead
```

The board **detects** ambivalence, then **forces a binary commitment** and
declares the middle band dead. That is a deliberate engineering choice — it buys
stability against chatter, which Chapter 6 argues for well.

But it throws away a distinction that has structure. Compare:

- **Mixture** `ρ = ½|attract⟩⟨attract| + ½|averse⟩⟨averse|` — "it is one of the
  two and I do not know which." A coin already flipped, face down.
- **Superposition** `|ψ⟩ = (|attract⟩ + e^{iφ}|averse⟩)/√2` — "it is genuinely
  both, in a definite relative phase." A coin still spinning.

These are **different objects with identical statistics in the ^2/^3 basis** and
*different* statistics in any rotated basis. Classical CAS cannot represent the
difference: on the simplex both are the point `(0.5, 0.5)`.

This is not decorative. It is an empirically decidable question about the thing
CAS exists to model: **is human ambivalence a mixture or a superposition?** The
classical board answers by assumption — it is a mixture, and the dead band means
we refuse to look. The quantum extension makes it a measurement.

### 2.2 Involution pairs as non-commuting observables

CAS declares three involution pairs: `CO-2↔CO-3`, `CO-5↔CO-6`, `CO-8↔CO-9`.
Classically these are complementary — attraction and aversion trade off along one
axis.

Model them instead as **non-commuting observables** (the `σz`/`σx` relationship)
and two things follow that classical CAS cannot produce:

1. **An uncertainty relation.** Sharp attraction implies aversion is not merely
   low but *undefined*. That is a stronger and more falsifiable claim than
   "0.7 / 0.3".
2. **Order effects.** Measuring `^2` then `^3` gives different joint statistics
   from `^3` then `^2`. Classical probability forbids this — `P(A∧B)` is
   order-independent. Quantum probability requires it when the observables do not
   commute.

Question-order effects are **documented in human psychology** and are the
strongest existing motivation for Hilbert-space models of cognition
(Busemeyer & Bruza; Pothos; Khrennikov; Aerts). CAS's involution pairs are a
natural candidate for the non-commuting structure those models posit.

The **breakdown region** also becomes natural rather than exceptional. The PCBA
document describes it as the output flipping to its involution pair — "`^2`
Positive snaps to `^3` Negative, fascination to revulsion." That is a basis flip.
Under the classical model it is a pathology to be flagged (`E-CJT-005`); under the
quantum model it is a Pauli-X, and the interesting question becomes what drives
the rotation.

### 2.3 Interference between reasoning paths

Two `^8 → ^9` paths arriving at the same conclusion can, with opposite phase,
**cancel**. Classically, two supporting paths can only ever add. A mechanism for
"the more angles I consider, the *less* settled I become" exists in the quantum
model and does not exist classically without ad-hoc machinery.

## 3. Where it breaks — and this is the hard part

### 3.1 The CJT cannot be a quantum gate. This is a theorem, not an obstacle.

Quantum gates are **unitary**: reversible and norm-preserving. The CJT is neither.

- **β > 1 is amplification.** The no-cloning theorem forbids amplifying an unknown
  quantum state. There is no coherent transistor. Quantum amplifiers exist but
  necessarily inject noise — that is the Caves bound, not an engineering gap.
- **Saturation clips.** A hard ceiling at 0.85 is non-linear; unitaries are linear.
- **Breakdown flips the output.** Discontinuous.

So a CJT is not a gate. It is a **measurement followed by classical
amplification** — and measurement destroys coherence.

**The consequence is severe and should not be softened:** a board with a CJT in
every stage has *no coherence left to exploit*. The first transistor collapses the
state. Every downstream stage operates on classical probabilities. The quantum
structure would be real for exactly one hop and then gone.

### 3.2 RPM's section-retraction is irreversible by design

Correction 2 is explicit: `εI ∘ ηI = idI` but `ηI ∘ εI ≠ id`, satisfaction is
cached, the chain is one-directional. Unitary evolution is reversible. **The RPM
gate is therefore a projective measurement, not a gate** — the same collapse
problem, in the part of the architecture that carries the most weight.

### 3.3 The Schmitt trigger is deliberately dissipative

Hysteresis *is* memory of the trigger's own past state. That is a classical,
irreversible, path-dependent feature. It is doing real work (Chapter 6's
anti-chatter argument is sound) and it is fundamentally incompatible with
coherent evolution.

## 4. The only architecture that survives all three

You cannot make the board quantum. You can make **one region** quantum:

| Region | Character | Contents |
|---|---|---|
| **Coherent** | unitary, reversible, no gain | state preparation and evolution *between* decisions — Noetic rotations, Domain⊗Register phase relations |
| **Classical** | measurement, irreversible | every CJT, every logic gate, the Schmitt trigger, the RPM gate, the Output Gate |

This is **coherent core with classical readout** — how every real quantum device
is actually built. Mapped onto the Wrap Pipeline: the Input Analyzer prepares a
state, the reasoning region evolves it, and **every gate is a measurement**.

The design rule that falls out: **coherence is a budget spent at the first
measurement.** If a board wants to exploit interference, the interference has to
happen *before* any CJT, and there can be only one collapse per coherent segment.

## 5. What this does not buy — stated plainly

**No computational speedup. None.** A 40-dimensional state is a 40×40 complex
matrix. Exact simulation is microseconds on a laptop. There is no regime, no
input size, and no algorithm here where quantum hardware helps. Grover and Shor
are irrelevant at this scale — they are asymptotic results and this problem has
no asymptote.

**No quantum computer is required, or useful.** Quantum *probability* is a
mathematical framework that runs perfectly well on classical hardware. The entire
quantum-cognition literature does exactly this.

**Conflating those two destroys the work.** "Quantum cognitive architecture" reads
as crankery to any reviewer unless it is stated in the first sentence that this
means **quantum probability theory, not quantum hardware**. That sentence is the
difference between a defensible contribution and an unpublishable one.

## 6. Two things to settle before anyone writes code

### 6.1 Patent posture — this is genuinely new

Every clarification so far has been carefully framed as *specification of existing
primitives*: v7.5 Registers, v7.6 production semantics, v7.7 operator discipline —
all argued as "no new primitives" to protect USPTO #64/037,173.

**Complex amplitudes, non-commuting observables and density matrices are new
primitives.** This is not a v7.8 clarification. It is a different mathematical
object with a strictly larger state space. Attorney input belongs *before* any
public disclosure, not after.

### 6.2 The falsifiability trap — the same one the board arm fell into

A quantum model has **strictly more free parameters** than its classical
restriction: the phases. More parameters fit better. A "quantum CAS vs classical
CAS" comparison on fit quality is **rigged** — quantum wins automatically and the
result means nothing.

This is exactly the defect that made the standalone board arm useless: a test
whose outcome is fixed before it runs
(`ccb_r1_stage5_construct_validity_2026_08_27.md`).

The test has to be a **qualitative prediction classical probability forbids**, not
a better fit:

- **order effects** — `P(^2 then ^3) ≠ P(^3 then ^2)`
- **violations of the law of total probability**
- **interference terms** in a double-conditioning design

Those are the right tests precisely because they are not about fit. A classical
model does not fit them badly; it **cannot produce them at all**.

## 7. The cheapest first experiment

Take the Ambivalence Analyzer's own stimulus — an ambiguous request that fires
both `^2` and `^3` at roughly 0.5. Run two conditions:

- **A:** ask attraction first, then aversion
- **B:** ask aversion first, then attraction

Classical CAS: the joint statistics must be identical. Order cannot matter.
Quantum CAS: they differ, by an amount set by how far the involution pair is from
commuting.

**Measure the order effect.**

- Zero, stably, across items → the involution pairs commute, and quantum structure
  buys nothing here. A clean negative result, cheaply obtained.
- Non-zero and stable → you have a phenomenon classical CAS **structurally cannot
  accommodate**, and the case for the extension is empirical rather than
  aesthetic.

This is a **prompt-order manipulation on the harness that already exists**. It
needs the paired statistics already built (`stats.py`), the existing item
generators, and no new mathematics *to run* — only to explain the result if it
comes back non-zero.

That ordering matters: it tests whether the extension is needed **before** anyone
pays for building it.

## 8. Honest summary

The strongest argument is not that quantum bits would make CAS more powerful.
It is that **CAS's own Correction 4 already commits to the quantum metric on a
quantum state space, with the phases set to zero** — and nobody has checked
whether that restriction is doing damage.

The strongest argument *against* is that the CJT, the RPM gate and the Schmitt
trigger are all irreversible by design and by necessity, so coherence cannot
survive more than one hop through the board as it stands.

Both can be true. The reconciliation is a coherent state-preparation region ahead
of a classical decision region — and the question of whether that region earns its
place is decided by the order-effect experiment in §7, not by argument.
