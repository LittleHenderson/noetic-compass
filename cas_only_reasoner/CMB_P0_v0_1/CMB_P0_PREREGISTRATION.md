# CMB-P0 — Multi-Chain Phase Necessity Bench · PREREGISTRATION v0.1 (FROZEN)

**Authorized by the owner, 2026-09-01, with the single word "GO".**
**Lane:** side bench. It does **not** replace or delay RGM-0.2 safety and attribution repair.
**Status of this file:** frozen before any measurement. Any change after the first held-out
read becomes `v0.2`, never an edit to `v0.1`.

---

## 1. The one question

> **Does phase-coded two-state memory give a real advantage for separating simultaneous,
> overlapping cognitive chains — over a plain scalar engine, over explicit chain tags, and
> over the same extra state without phase?**

**Why this bench exists.** `docs/design/WHY_PULSE_KNOBS_ARE_INERT_AND_WHERE_THE_INTUITION_IS_RIGHT.md`
established two measured facts on the RGM-0.1 graph at `a086a770`:

1. The knobs cannot re-rank anything. `M = (1−δ)I + γW` shares W's eigenvectors at every
   setting (measured cosine `1.0000000000`; top-20 retrieved set identical under a 9× damping
   change). This is a theorem, not a weak effect.
2. Three of the four knobs are **undefined**, not merely unhelpful: `max |Im(eigenvalue)| =
   0.000e+00`, so nothing rotates, so phase, frequency and Q have no referent.

But the same document identified a **real** gap that the knobs were pointing at:

> One scalar per memory cannot encode *which chain* activated it.

And it noted that RGM-0/0.1 could never have detected this, because **every query there has one
target chain**. This bench builds the exam that asks the question.

**Plain-English version.** Two trains of thought are running at once and they share stations.
The current memory board has one brightness dial per station, so light arriving from train A
and light from train B add into the same number and become inseparable. This bench asks
whether giving each station a *clock hand* (a phase) as well as a brightness lets the two
trains be told apart — and whether that beats just writing the train's name on the ticket.

## 2. Six arms

All six arms see **identical worlds, identical queries, identical seeds, identical link
graphs, identical propagation depth, identical top-k budget**. They differ only in what state
each memory node carries and how the answer is read out.

| Arm | State per node | Chain grouping comes from | Role |
|---|---|---|---|
| `P0_SCALAR` | one real scalar `a` | nothing — chains are summed together | **lower bound** — the current engine |
| `P1_ORACLE_CHAIN_TAG` | `K` real scalars | **the true chain labels** | **upper bound, NOT deployable** |
| `P2_INFERRED_CHAIN_TAG` | `K` real scalars | inferred from the link graph + content | the cheap digital solution |
| `P3_GENERIC_TWO_STATE` | `(a, r)` — two reals, no angle | nothing | **capacity control** |
| `P4_PHASE_OSCILLATOR` | amplitude `a` + phase `θ` | **emergent phase-locking** | the biological solution |
| `P5_PHASE_SHUFFLED` | identical dynamics to P4 | phase permuted across nodes at readout | **killer control** |

**Why `P3` is the load-bearing control.** Without it, any win by `P4` is ambiguous between
*"phase works"* and *"a second number per node works."* `P3` carries the same two-real state
budget as `P4` with **no angular structure**, so `P4 − P3` isolates phase from capacity.

**Why `P5` is the killer control.** It runs the *identical* oscillator and preserves the
amplitudes exactly; only the phase-to-node assignment is destroyed at readout by a
permutation. If `P4 ≈ P5`, the phase structure carries no chain information and the arm's
apparent advantage came from its amplitude dynamics.

**`P1` is an oracle and is labelled as one everywhere.** It is handed the ground truth. It
can never be reported as a method, only as a ceiling. It exists to tell a *hard* task from an
*impossible* one.

### 2.1 What no arm receives

The gold chain identity is **never** exposed to `P0`, `P2`, `P3`, `P4` or `P5` — not in node
features, not in the query, not in the link weights. `P1` alone receives it, by definition.

The query cue is a **node**, not a label: *"these memories are all active; I am currently at
node X; what comes next?"* Which other active memories belong to X's chain is exactly what the
arm has to work out.

## 3. World construction

`N_NODES = 800` per world, content dimension `D_CONTENT = 32`, `K` simultaneous chains,
chain length `L_CHAIN = 6`. Each world is **independently seeded**; the world is the unit of
statistics.

Every world is built to defeat a shortcut:

| Adversarial property | What it defeats |
|---|---|
| ≥2 simultaneously active chains | single-chain benches (the RGM-0.1 blind spot) |
| chains **share intermediate nodes** | "just partition the graph" |
| **identical static profiles in different orders** | static-profile-only retrieval |
| **misleading cross-chain links** | naive link-following |
| **chain-specific completions** | guessing a globally popular node |
| distractor nodes with high content similarity | pure embedding nearest-neighbour |
| chain identity absent from all features | any arm reading the answer off the input |

**Identical static profiles in different orders** is the sharpest one: two nodes carry the
*same multiset* of profile features in a *different sequence*, so any arm that ignores order
cannot separate them.

### 3.1 Dev / held-out separation

```
worlds  0 –  5   DEV       parameters may be chosen here
worlds  6 – 25   HELD-OUT  parameters frozen; this is what gets reported
```

Every free parameter (`δ`, `γ`, depth, top-k, coupling `K_c`, `ε`, `b`, cluster count rule) is
fixed on the **dev** worlds and written into `FROZEN_PARAMS.json` **before** any held-out world
is read. The held-out read happens once.

Worlds are reported in two disjoint groups and **never pooled**:

- `SINGLE_CHAIN` worlds (`K = 1`) — the sanity condition. If the gap is real, all arms should
  be close here.
- `MULTI_CHAIN` worlds (`K = 2, 3, 4`) — the actual question.

This separation is mandatory: pooling them would let a single-chain tie mask a multi-chain
difference, which is the exact `aggregate-hides-a-reversal` defect raised as **S-1** against
RGM-0.1 and as **M-1** against RGM-0. It is not being repeated here.

## 4. The mathematics, and what is *not* a knob

### 4.1 Registered operator

Base propagation, identical for every arm:

```
a' = BoundedTopK[ (1−δ)·a + γ·W·a ]        W = D⁻¹A, A symmetric
```

Two-state block operator for `P3` / `P4`:

```
        [ (1−δ)I + γW     −b·I   ]
  M  =  [                        ]
        [     ε·I        (1−ε)I  ]
```

### 4.2 Frequency, width and Q are DERIVED, never set

The owner's constraint is honored exactly: **no free frequency control, no free pulse-width
control, no free Q control.**

| Quantity | Status | How it is obtained |
|---|---|---|
| **Frequency** | **fixed by the registered operator** | `ω_d = |arg λ|` rad/wave, read off the eigenvalues of `M`. A single global `ω` would cancel in every phase *difference*, so none is introduced. |
| **Pulse width** | **derived from decay** | `τ = −1 / ln(1−δ)` waves. **Not `1/δ`** — that is only the small-`δ` approximation, per the owner's correction. |
| **Q** | **telemetry only** | registered formula below |

**Registered Q formula** — this is the definition CMB-P0 uses, and it is the only one:

```
For an eigenvalue λ of the one-wave block operator M, on the named mode:

      ω_d = |arg λ|            radians per wave      (damped angular frequency)
      α   = −ln|λ|             nepers per wave       (amplitude decay rate)

      Q   = ω_d / (2α)         dimensionless
```

- **Units:** dimensionless. `ω_d` and `α` are both per-wave, so the ratio is a pure number.
- **Mode:** `Q` is reported **per eigenmode**, identified by index and by `|λ|`. A single
  scalar "the Q" is not licensed — the operator has 2N modes.
- **Undefined case:** if `arg λ = 0` (real spectrum), `Q = 0` and the report says
  `Q_UNDEFINED_REAL_SPECTRUM`. This is what the *current* engine returns, by §1 fact 2.

**Supersession, recorded honestly.** The value `Q ≈ 6.88` in
`WHY_PULSE_KNOBS_ARE_INERT_AND_WHERE_THE_INTUITION_IS_RIGHT.md` §3 was computed under an
**unregistered convention** and was explicitly flagged there as provisional. Under the formula
registered above, the same eigenvalue `λ = 0.7499 + 0.4472j` gives
`ω_d = 0.5377`, `α = 0.1357`, **`Q = 1.981`**. The `6.88` figure is **superseded and must not
be quoted**. This preregistration is the authority.

### 4.3 Math audit (persisted, every run)

The receipt persists, for the block operator actually used:

```
block operator M (shape + the four blocks' defining scalars)
full eigenvalue spectrum (real and imaginary parts)
spectral radius  ρ(M)
max |Im(λ)|                      -> is rotation even defined?
rotation angle per wave, per mode
decay constant α per mode
derived τ = −1/ln(1−δ)
period 2π/ω_d per mode
Q per mode, by the §4.2 formula
stability margin  1 − ρ(M)
```

A run with `ρ(M) ≥ 1` is reported `UNSTABLE` and its accuracy numbers are **not** eligible for
any status.

## 5. Metrics

All computed per world, per `K`, per arm. The **world is the statistical unit**. All arms are
**paired** — they see the same worlds and the same queries — so differences are reported as
paired per-world differences with per-world win counts, never as independent-sample means.

| Metric | Definition |
|---|---|
| `top1` | the cued chain's correct continuation is ranked 1 |
| `recall@5` | it appears in the top 5 |
| `cross_chain_contamination` | fraction of the returned top-k belonging to a **non-target** chain |
| `chain_assignment_accuracy` | fraction of active nodes assigned to their true chain (arms that produce an assignment) |
| `false_chain_merges` | count of distinct chain pairs the arm collapses into one group |
| `simultaneous_chain_capacity` | largest `K` at which `top1 ≥ 0.50` |
| `stable` | `ρ(M) < 1` and no state overflow across all waves |
| `cuda_time_ms` | CUDA-event time for the arm's numerical work |
| `peak_vram_bytes` | `torch.cuda.max_memory_allocated` |

`cuda_time_ms` and `peak_vram_bytes` are **volatile** and are **excluded from the determinism
hash** — the exact bug found in RGM-0.1's raw 2-pass hash, not repeated here.

## 6. Status law — five outcomes, decided by a program

The status is emitted by a deterministic function reading frozen thresholds, not by prose.
`Δ` denotes a **paired per-world mean difference on HELD-OUT MULTI_CHAIN worlds only**.
`MARGIN = 0.02` on top-1. A difference must clear `MARGIN` **and** be positive in
**≥ 70% of held-out multi-chain worlds** to count as a win.

| Status | Condition |
|---|---|
| `EXTRA_STATE_CAPACITY_SUPPORTED` | `P3 > P0` **and** `P4` does **not** beat `P3` — the second number helps; the angle adds nothing |
| `PHASE_CODING_WORKS_TAGS_PREFERRED` | `P4 > P0`, `P4 > P3`, `P4 > P5` — **but** `P2 ≥ P4` — phase works, a tag is cheaper |
| `PHASE_MULTICHAIN_SIGNAL` | `P4 > P0`, `P4 > P3`, `P4 > P5`, **and** `P4 > P2` — the intuition is vindicated with a mechanism |
| `EXPLICIT_CHAIN_TAGS_PREFERRED` | `P2 > P0` and `P2 ≥ P4` and `P4` fails to beat `P3` or `P5` |
| `PHASE_MEMORY_UNSAFE` | `P4` is `UNSTABLE`, **or** its `cross_chain_contamination` or `false_chain_merges` exceed `P0`'s by more than `MARGIN` — **this status overrides every other**, including a top-1 win |

### 6.1 Precondition gate — checked BEFORE any status is emitted

**`GATE_HEADROOM`.** If `P0_SCALAR` already reaches `top1 ≥ 0.90` on held-out multi-chain
worlds, there is no gap to measure and the bench cannot discriminate between the arms. In that
case the run emits **`STATUS_NOT_EMITTED`** with reason `NO_MULTICHAIN_GAP`, and the matter is
**escalated to the owner** rather than resolved by me.

**`GATE_ORACLE`.** If `P1_ORACLE_CHAIN_TAG` itself cannot reach `top1 ≥ 0.60`, the task is not
merely hard but ill-posed or the instrument is broken. The run emits `STATUS_NOT_EMITTED` with
reason `INSTRUMENT_OR_TASK_ILL_POSED`.

> **Governance note, stated plainly.** `STATUS_NOT_EMITTED` is **not** a sixth outcome and is
> **not** me legislating a new status word. It is a *precondition failure* that stops the
> five-outcome law from running on an instrument that cannot answer. Claude is not the research
> governor; a bench that cannot discriminate must return nothing and escalate, not pick the
> least-bad label.

## 7. Claim vocabulary — frozen

**Permitted**, and only these:

```
PHASE_MULTICHAIN_SIGNAL
PHASE_CODING_WORKS_TAGS_PREFERRED
EXTRA_STATE_CAPACITY_SUPPORTED
EXPLICIT_CHAIN_TAGS_PREFERRED
PHASE_MEMORY_UNSAFE
STATUS_NOT_EMITTED
UNSTABLE
Q_UNDEFINED_REAL_SPECTRUM
```

**Prohibited in every artifact from this lane:**

```
any resonance-specific claim
any CAS-specific claim
"validated", "proven", "law", "breakthrough"
any claim that generalizes beyond synthetic worlds of this construction
any merge of CMB-P0 into CMB-R1
```

The owner's instruction is explicit and is repeated here so it cannot drift:
**"No resonance-specific or CAS-specific claim is licensed."**

A win by `P4` licenses exactly one sentence: *on synthetic multi-chain worlds of this
construction, a phase-coded two-state engine separated simultaneous chains better than a
scalar engine, than a matched two-state engine without phase, and than its own
phase-destroyed control.* Nothing about CAS. Nothing about resonance. Nothing about real
memory.

## 8. Compute law — GPU only, fail closed

Owner's constraint, honored literally:

- **No experimental workload on the owner's local CPU.** Enforced twice: by policy, and by
  fact — local torch is `2.11.0+cpu`, so no CUDA path exists on this machine at all.
- **One remote AWS GPU instance.** `g4dn.xlarge` (Tesla T4), `us-west-2`.
- **All substantive numerical operations execute on CUDA.** Every arm's propagation, readout
  and scoring runs as batched tensor ops on the device.
- **Fail closed on silent CPU fallback.** The harness asserts `torch.cuda.is_available()` and
  asserts `tensor.device.type == "cuda"` at every arm boundary. A CPU tensor raises
  `GPU_REQUIRED` and aborts the run. There is no fallback branch to take.
- **Remote host CPU is permitted only** for orchestration, file I/O, hashing, monitoring and
  shutdown.

**Recorded in the receipt:** tensor devices per arm, GPU name and UUID, driver version, CUDA
runtime and torch build, CUDA-event time, host wall time, peak VRAM, instance id and type,
`instance_runtime_estimate` (the authoritative spend proxy), `compute_wall_estimate` (a
labeled lower bound only), and termination proof.

**Cost.** Hard cap **$0.80**, one instance, self-terminating:
`InstanceInitiatedShutdownBehavior=terminate` + EXIT-trap + in-instance timer + client
watchdog. *This cap is my proposal, set below the $1.20 the owner last authorized; it is not
an owner-issued figure and the owner may overrule it.*

## 9. Stop condition

**Stop after the deterministic report.** No merge into CMB-R1. No follow-on arm. No
parameter retry against held-out. The next action after the report is an **independent
audit**, exactly as the owner directed.

## 10. Falsifiers — what would show this bench is wrong

Recorded so it can fail honestly:

- `GATE_HEADROOM` fires — the scalar engine already solves multi-chain worlds, so the gap
  identified in the design document does not exist on this construction.
- `GATE_ORACLE` fires — even ground-truth chain labels cannot solve it, so the task is
  ill-posed and no arm comparison means anything.
- `P4 ≈ P5` — phase structure carries no chain information; the oscillator's apparent
  advantage was amplitude dynamics wearing a costume.
- `P4 ≈ P3` — the win is extra state capacity, not phase, and the whole oscillatory vocabulary
  is unnecessary.
- The spectrum comes back real (`max |Im λ| = 0`) under the block operator — the oscillator
  was not actually built, and `Q_UNDEFINED_REAL_SPECTRUM` fires.

---

**Frozen.** Nothing below this line existed when the file was sealed.
