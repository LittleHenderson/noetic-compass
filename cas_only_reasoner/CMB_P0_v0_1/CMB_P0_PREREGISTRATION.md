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

- **No experimental workload on the owner's local CPU.** Enforced by policy and by the
  `require_cuda()` fail-closed check, which aborts before any tensor is allocated.

  > **CORRECTION (A2, pre-launch).** This clause originally read *"Enforced twice: by
  > policy, and by fact — local torch is `2.11.0+cpu`, so no CUDA path exists on this
  > machine at all."* **That was false.** The default interpreter is `2.11.0+cpu`, but
  > `~/venvs/cas-gpu` carries `2.11.0+cu128` with `torch.cuda.is_available() == True` on an
  > RTX 4070 — which is the lane A1.6 itself used for the crash test. A frozen governing
  > document must not tell the owner a guardrail exists when it does not. The local CUDA
  > lane is permitted for smoke/dev under the standing law and is restricted to
  > non-claim-bearing runs; it records no measurement.
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

---

# AMENDMENT A1 — dev-world parameter freeze (2026-09-01, BEFORE any held-out read)

This amendment is made under §3.1, which reserves parameter selection to the **dev** worlds
and requires the freeze to be written down **before** the held-out worlds are read. **No
held-out world (6–25) has been read at the time of writing.** All evidence below comes from
dev worlds 0–5 and from closed-form mathematics. Recorded here rather than silently applied.

## A1.1 Two-state parameters — frozen by mathematics, not by fitting

The originally drafted `b=0.80, eps=0.25` makes the block operator **unstable**: sweeping
`mu(W)` over `[-1,1]` (which covers *every* graph this bench can build, since `W = D⁻¹A` is
similar to a symmetric normalised matrix) gives `rho = 1.0488`. The state grows without
bound, and `Q` is undefined because the dominant mode's decay rate is negative.

Frozen instead: **`b = 0.60, eps = 0.70`** → `rho = 0.8832`, stability margin `0.1168`,
`Q = 2.239`, period `11.29` waves, all `2N` modes complex.

This freeze is **graph-independent** — it is derived from the closed-form spectrum over the
whole admissible range of `mu`, not fitted to any world's results. `delta` and `gamma` are
**not** touched; they stay at the RGM engine's values so the comparison against the current
engine remains honest.

## A1.2 `PHASE_SUBSTEPS` frozen at a CONVERGED value — and why that choice is adverse to P4

The phase system needs enough iterations to lock. Measured on dev worlds 0–5, `k = 2,3,4`:

| phase updates per wave | within-chain order | cross-chain separation (rad) | P4 top-1 |
|---|---|---|---|
| 1 | 0.6418 | 1.0795 | 0.567 |
| **4** | 0.9418 | 0.4537 | **0.755** ← best for P4 |
| 10 | 0.9995 | 0.0618 | 0.710 |
| 25 (20 waves) | 1.0000 | 0.0000 | 0.470 |

**Frozen at `PHASE_SUBSTEPS = 10`** (converged), *not* at 4 (where P4 scores highest).

The reason matters more than the number. At 4 substeps the system is in an **unconverged
transient**: chains have partly locked (0.94) and have not yet merged (0.45 rad apart). Its
apparent advantage depends on stopping at exactly the right moment. **A stopping time is not
a mechanism.** Freezing there would be choosing the setting that flatters the hypothesis —
the same class of error as the structure-channel calibration caught in Tier C C1, and it is
not being repeated.

## A1.3 What the converged regime shows — and the interpretation guard it forces

At convergence the chains lock **internally** (order → 1.0000) but they all lock to the
**same phase** (cross-chain separation → 0.0000). This is not a tuning failure; it is the
fixed point. **Uniform positive coupling on a connected graph has one stable attractor:
global synchrony.** The link graph is connected — cross-chain links and background edges see
to that — so distinct per-chain phase groups are not a stable configuration.

The consequence is exact and was then confirmed in code: when every phase is equal,
`cos(Δθ) = 1`, and **`P4_PHASE_OSCILLATOR` reduces precisely to `P0_SCALAR`**. Measured on
dev world 0, top-1 is identical for the two arms at every `K` (1.00 / 0.50 / 0.73 / 0.25),
while their raw scores still differ (`max|diff| = 0.34`), so this is a genuine degeneracy and
not a code fault.

Therefore the run emits a mandatory **interpretation guard**, `PHASE_DEGENERATE_TO_SCALAR`:

> In the globally synchronised regime, `P4 > P5` shows **only** that *random* phases are
> worse than *uniform* phases. It is **not** evidence of chain binding and must not be
> reported as such.

Without this guard, `P4` beating its own shuffled control would look like a phase result
while the phase channel was carrying no chain information at all. This is the
aggregate-hides-the-mechanism failure in a new costume, and naming it in advance is the only
defence.

## A1.4 What would be needed — named, and deliberately NOT built

Separating chains by phase requires something that keeps locked groups apart: **cross-chain
inhibition (negative coupling)**, or **frequency heterogeneity** across chains. Neither is
added:

- A free frequency control is **forbidden** by the owner's constraint ("Frequency is fixed by
  the registered operator").
- Negative coupling is a **new mechanism**, not a parameter. Adding it would be me
  authorizing a replacement hypothesis mid-experiment, which is exactly what the research
  governance rule forbids.

So it is **reported as the missing ingredient, not built**. Whether to open that lane is the
owner's decision, not mine.

## A1.5 Operational note (no scientific content)

The instance role `cas-aws-gpu-standby-v1-us-west-2` grants S3 access under **one** prefix,
`bridge-control-20260822/*`. Staging and receipt upload use `bridge-control-20260822/cmb_p0/`
accordingly. Verified by a live round-trip before launch, not assumed. No IAM policy was
changed — that is the owner's to change, not mine.

## A1.6 Pre-launch verification performed at $0

- Shape/import smoke test (tiny CPU worlds, scratchpad only, repo guard untouched): PASS.
- GPU crash test at full registered size on the local RTX 4070 (smoke/dev, permitted by the
  standing law; **no measurement recorded**, the claim-bearing run is AWS): PASS — all six
  arms, `k = 1..4`, peak VRAM 31 MB, repeat-run determinism `True`, and every flagged CUDA
  risk cleared (`eigvalsh` float64, `complex128`, CUDA generators, `torch.mode`).
- S3 permission round-trip under the authorized prefix: PASS.

**No held-out world was read during any of the above.**

---

# AMENDMENT A2 — the bench was STOPPED PRE-LAUNCH by its own review (2026-09-01)

**No held-out world (6–25) has been read. No money has been spent. Nothing below is a
result.** Three independent adversarial reviewers were run against harness v0.1 before any
launch. They found defects that would have made the run either meaningless or actively
misleading. **The run was stopped and the harness rebuilt as v0.2.** This amendment records
what was wrong, what was measured, and what was changed — in full, because a defect that is
quietly fixed is indistinguishable from a defect that was never found.

## A2.1 The three disqualifying defects — each CONFIRMED BY MEASUREMENT, not by argument

**C1 — the bench did not test chain separation at all.** In v0.1 the cued node had a private
weight-1.0 edge to its own completion, and no other non-seed candidate came close. So the
gold answer was recoverable by a single edge weight, with no propagation, no chains and no
phase. Measured on dev worlds:

```
argmax over non-seed j of A[cue, j] == gold :  1152/1152 = 1.0000
A[cue, gold] >= 1.0                         :  1152/1152 = 1.0000
```

Every arm was really being scored on *"how faithfully does my readout preserve one-hop cue
adjacency"*. A phase win would have been licensed as *"separated simultaneous chains"* while
the mechanism read one edge.

*Repair:* every cue now links to **every** completion at the same weight, so one-hop
adjacency is uninformative by construction; a completion is tied to its own chain only
through that chain's earlier nodes. Re-measured: **at chance** (0.4870 / 0.3255 / 0.2266 vs
chance 0.5 / 0.3333 / 0.25).

**C2 — the 64 queries per world were only `k` distinct queries.** v0.1 seeded every chain in
every query, so the only thing that varied was the cue, and two queries with the same target
were byte-identical. Measured: **2/64, 3/64, 4/64 distinct**. Deterministic arms could take
only `k+1` accuracy values per world, the smallest possible disagreement was 0.17–0.48, and
`MARGIN = 0.02` therefore screened out nothing.

*Repair:* each world now builds a **pool** of `k + 4` chains, and each query activates a
random subset of size `k` and cues one of them. Re-measured: **26/64, 51/64, 54/64 distinct**.

**C3 — pooling K=2, 3 and 4 reproduced this project's own most-criticised defect.** v0.1
pooled all multi-chain worlds into one bag of 60 and required 70% positive — which tolerates
**18 negative worlds**. A per-K rule tolerates only 6 per stratum. So phase could lose at
K=4 — the hardest setting, and the entire point of a bench about simultaneous-chain capacity
— and still be reported as a win. This is exactly the aggregate-hides-a-reversal failure
raised as **M-1** against RGM-0 and **S-1** against RGM-0.1, and §3.1 of this very document
promises it "is not being repeated here". It was being repeated, one level down.

*Repair:* every comparison and both gates are now evaluated **per K**, and a win must hold
**independently at K=2, K=3 and K=4**.

## A2.2 Other confirmed defects, all repaired

| Defect | What was wrong | Repair |
|---|---|---|
| Channel budget | tag arms kept 48 survivors **per channel** (up to 4× P0's budget) and renormalised per channel | one shared budget and one shared normalisation across channels |
| `P5` reference phase | the permutation was applied *before* the cue's phase was read, so the control's reference belonged to a **random node** — it destroyed its own baseline instead of isolating chain structure | reference is read from the **unpermuted** field |
| `bounded_topk` sign | discarded slots were filled with `0.0`, so when kept values went negative — exactly what P3's inhibition produces — the discarded zeros outranked every kept node | select by **magnitude**, keep the sign |
| Tie handling | strict `>` scored every node tied with gold as *worse* than gold, handing free top-1 to whichever arm zeroed more nodes | ties counted **pessimistically** |
| Degeneracy guard | `PHASE_DEGENERATE_TO_SCALAR` was written into the receipt and then **ignored** by the status decision — "PASS with caveats" implemented in Python | the guard now **blocks** the five-outcome law |
| Safety units | `false_chain_merges` is an integer count but was compared against `MARGIN = 0.02`, an accuracy fraction; one extra merge in two worlds would have fired the override that "overrides every other outcome" | `MERGE_MARGIN = 0.50` in merge units; `CONTAM_MARGIN = 0.05` |
| Safety fail-open | a missing safety metric evaluated to "safe" | missing metric now emits `STATUS_NOT_EMITTED` |
| §6 clauses missing | the `P2 ≥ P4` conditions in §6 were absent from the code, so a status could assert a preference the data contradicted | both clauses implemented |
| Host-CPU arm logic | P2's decisive clustering ran in a host Python loop — an arm's core numerics on CPU, while the receipt reported `cuda:0` | average-linkage rewritten **on device** |
| Circular clustering | phase grouping cut sorted gaps with no wrap-around, splitting any chain synchronised near ±π | circular-mean assignment, computed for **P4 and P5 alike** |
| Dead adversarial props | `profiles` was built and never read, so "identical static profiles in different orders" defended against an attack nobody mounted | `B_STATIC` diagnostic now mounts it (measured **0.000** — defeated as designed) |
| Missing metrics | `simultaneous_chain_capacity`, per-arm CUDA time and VRAM were registered in §5 and never computed | all computed |
| Crash = total loss | the receipt was written only at the very end | partial receipt written on exception |
| Determinism | hash covered only three fields; no `use_deterministic_algorithms`, no `CUBLAS_WORKSPACE_CONFIG` (a regression against this repo's own standard) | hash widened; both flags set |
| Launcher | no check that torch installed or that CUDA was present; relative staging paths; no recovery if the receipt never arrived | fail-loud torch check, absolute paths with **sha256 of staged bytes**, console-output fallback |

## A2.3 A seventh arm was ADDED — and it can only make a phase claim harder

`P4` is exactly `P0` multiplied by a non-negative mask. Nothing in the registered six arms
separated *"phase works"* from *"any second cue-seeded channel sharpens the ranking"* — and
two estimators of the same signal, multiplied together, rank it better than either alone,
with no chain information involved anywhere.

**`P6_SCALAR_TWO_CHANNEL`** is that missing control: `a × clamp(b, 0)`, where `b` is a plain
scalar field seeded at the cue, in the identical product form, carrying **no angle**. `P4`
must now beat `P6` as well.

> **Flagged for owner ratification.** The owner registered **six** arms. This is a seventh,
> added by me. It is a *control*, so it can only weaken a phase claim, never strengthen one
> — the conservative direction. The owner may strike it.

## A2.4 Control arms were tuned UP, and that direction is deliberate

Two control arms were broken rather than merely inert, and a broken control silently
guarantees a phase win:

- **P3 scored top-1 `0.000` at every K** at the drafted `b=0.60, eps=0.70`. Not inert —
  *below chance*, while P0 scored 0.297. The oscillation scrambled retrieval outright.
- A cue-similarity gate on `r` was tried and **rejected**: `r` is an adaptation magnitude,
  not an identity code, and since the cue is strongly seeded while the gold deliberately is
  not, the gate scored the gold at `0.0000` in every query.

Swept on dev and re-frozen at **`b=0.30, eps=0.50`** (`rho = 0.8660`, stable, still
oscillatory), where P3 scores 0.482 / 0.331 / 0.227 — properly matched to P0's
0.495 / 0.333 / 0.263. P2's clustering reach depth was likewise swept and frozen at **2**
(purity 0.787).

**Both changes strengthen arms that COMPETE with the phase hypothesis.** Strengthening a
competitor makes a phase win harder, never easier. Tuning `P4` up would have been the biased
direction and was not done — `KC_PHASE` remains at its drafted value and was not swept.

## A2.5 Dev gate pre-check — PASSED before any spend

Run on dev worlds 0–5 only, on the local RTX 4070 smoke lane. **No measurement recorded;
held-out worlds 6–25 were not read.**

```
  K       P0     P1     P2     P3     P4     P5     P6   B_STATIC
  1    0.922  0.922  0.531  0.883  0.917  0.409  0.297    0.000
  2    0.495  0.909  0.312  0.482  0.565  0.305  0.234    0.000
  3    0.333  0.781  0.240  0.331  0.391  0.268  0.349    0.000
  4    0.263  0.693  0.219  0.227  0.284  0.216  0.201    0.000

  K=2: HEADROOM P0=0.495 < 0.90 PASS   ORACLE P1=0.909 >= 0.60 PASS
  K=3: HEADROOM P0=0.333 < 0.90 PASS   ORACLE P1=0.781 >= 0.60 PASS
  K=4: HEADROOM P0=0.263 < 0.90 PASS   ORACLE P1=0.693 >= 0.60 PASS
```

The task is solvable with perfect tags (P1) and sits near chance-among-completions without
them (P0), so the bench discriminates. The outcome is genuinely open: P4's dev edge over P0
is +0.070 / +0.058 / **+0.021** at K=2/3/4, and the K=4 figure sits barely above
`MARGIN = 0.02`, so the per-K requirement is a real test rather than a formality.

## A2.6 What is still owed to the owner

1. **Ratification of `P6`** (A2.3) — a seventh arm I added.
2. **A ruling on §6's merge comparator.** §6 says merges must exceed **`P0`'s**. `P0`
   produces no chain assignment at all, so that comparison is *unimplementable as written*.
   The code compares against `P2`. This is a genuine deviation from a frozen clause, and it
   is named here rather than buried.
3. The standing items from earlier lanes: the `E1S` ruling on CJT-EX1, the resonance
   relabel, and naming a cross-model auditor for RGM-0.1.

**Status: the harness is v0.2, the dev gates pass, and no held-out world has been read.**
