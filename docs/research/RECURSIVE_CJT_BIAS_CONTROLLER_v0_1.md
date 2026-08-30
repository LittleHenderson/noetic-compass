# Recursive CJT Bias Controller v0.1

## RPM-Gated, ASOM-Regulated, CAS-Ohm-Routed Simplex Transformation

Status: **DESIGN SPECIFICATION — PROPOSED_UNTESTED.** Documentation only. No model, no
GPU, no run, no claim promotion. This document supersedes the *architectural scope* of
`ATTENTION_CAS_OHM_COUPLING_RND_v1.md` (now designated **Static Coupling Baseline v1**);
it does not erase it. The static report remains the clean control this recursive design
must beat.

The owner's design rule that creates this document: **every CJT Bias is itself a
prerequisite-bearing structure.** The Bias is not a neural bias term `b`, not a static
vector, not fixed weights. It is a recursive stateful subcircuit — a control room, not a
knob. One precision holds throughout: **RPM does not produce ASOM. They are two different
systems attached to the same Bias.** RPM asks "what does this Bias require before it can
operate correctly?" ASOM asks "what operating condition is this Bias currently in?"

The central object changes from `E = T(C; B)` to:

```
(E_t, B_{t+1}) = J(C_t, B_t)
```

A CJT produces an Effect AND updates its own Bias state — because it learned, saturated,
failed, acquired a prerequisite, or received feedback. That makes a CJT a recurrent,
stateful, gated expert — closer to a small cognitive board than to one neuron.

---

## 1. Static baseline inherited

Everything verified in Static Coupling Baseline v1 carries forward unchanged:

- The mixture math (`q = αᵀP`, flow marginals, cone decomposition `d = m·π`, kernel
  propagation `p_E = p_C·K_B`, factorized product over flat Δ¹¹¹⁹) is computed-correct.
- `F = I·α·p` is rank-1 bookkeeping, not measurement, until an independent joint-flow
  quantity is specified.
- The hull-reachability test is usable only as ε-projection distance with a *declared*
  Idea segmentation; the raw in-hull test is near-vacuous for generic targets.
- Prior art stands: `q = αᵀP` is published (MIL 2018, pointer-generator 2017, Concept
  Transformer 2022); simplex-semantics typing is CoDA scale-class doctrine; selective
  plasticity mechanisms are EWC/SI/PackNet/SupSup; the partly-novel pieces are the typed
  three-factor coupling, reachability-as-control-signal, and the Fisher-Rao structural key.
- The three broken imports are repaired here rather than repeated: `I_total` (Ch. 7),
  the 28-cell naming (recorded as a versioned translation, with the REAL hazard being
  Drives×Domains vs Drives×Registers), and the control battery (Ch. 12, 14).

**Owner calibrations recorded (2026-08-30):** (a) the `I_total := 1` decision governs the
static dense-forward-pass experiment ONLY — total flow re-enters when adaptive
computation gives it a measured referent (Ch. 7); (b) the construction-gold restriction
on `p_i` binds the first claim-bearing experiment, not all future ones — an
activation-decoded `p_i` may be used later ONLY after beating surface, matched-semantic,
shuffled, and random controls; (c) the Worlds↔Registers correspondence is a declared,
frozen translation key, held as a versioned mapping rather than an asserted ontological
identity; (d) the 15-agent R&D process is internal review — model agreement changes
audit priority only and creates no authority.

What changes in this document: the Baseline treated Bias as static. Here the Bias
carries readiness, operating condition, memory, and repair machinery, and the
architecture becomes adaptive — which is precisely what re-opens the questions the
static experiment could not ask.

---

## 2. Bias state schema

For CJT `j` at time `t`:

```
B_{j,t} = ( S_j, M_{j,t}, R_{j,t}, Z_{j,t}, Θ_j, G_{j,t} )
```

| Term | Meaning |
|---|---|
| `S_j` | Stable substrate: learned parameters, long-term formation (the ^5-analog: what this Bias is composed of) |
| `M_{j,t}` | Local memory and recent history (inputs, Effects, verifier outcomes) |
| `R_{j,t}` | RPM state: raw `D_j, W_j, P_j`, prerequisite tree, open/suspended subgoals, return addresses |
| `Z_{j,t}` | Operating record: `region_state` (cutoff / active / saturation / breakdown / non-ohmic / unstable / unassessed) AND `semantic_outcome` (intended / opposite / off-axis / unassessed) — two axes, never one letter (Ch. 5) |
| `Θ_j` | Transformation parameters (the kernel `K_B`, adapters, gain `β_j`) |
| `G_{j,t}` | Governance: hard permissions, resource ceilings, quarantine flags, authority gates |

**Typed product, not simplex soup.** The Bias is a product of typed spaces:

- `p^{ND} ∈ Δ³⁹°` — Noetic×Domain composition (COMPOSITION semantics), OPEN simplex:
  all `p_k > 0`, validated strictly, with a frozen ε-floor — per CLAUDE.md Correction 4
  and the Baseline's FR-vertex caveat (gradients blow up at near-one-hot profiles).
- `a^{ASOM} ∈ Δ³` — ONLY as a POSTERIOR belief over the four regions when the region is
  uncertain; never as a claim the stage is literally 65% active.
- `b^{RPM} ∈ Δ^{m-1}` — ALLOCATION across the `m` open RPM branches.
- `D, W, P` — independent raw scalars. NEVER one simplex (all three can be high at
  once); only the *deficit* vector normalizes for bottleneck attribution.
- Drive: `magnitude × Δ⁶` cone. CAS-Sem content: a graph. RPM dependencies: a graph and
  a stack. Compute: an absolute magnitude. Authority: hard typed permissions. Semantic
  outcome: a separate verified status.

Every simplex-valued field carries its `simplex_semantics` tag
(ALLOCATION / COMPOSITION / POSTERIOR / RECIPE / SELECTION_PROBABILITY), per the CoDA
scale-class discipline adopted in the Baseline.

This Bias can answer: *Am I relevant to this Cause? Do I know how to transform it? Do I
have capacity? Am I in the correct operating region? Did my last Effect verify? Should I
execute, recurse, split, ask, learn, stop, or roll back?*

---

## 3. RPM readiness semantics

Each Bias keeps `D_j, W_j, P_j` as independently assessable raw values (per the CAS-Ohm
guide: the Ohm relation is a prediction and consistency test, NOT a replacement for the
three RPM assessments).

Hard readiness gate:

```
ρ_j = 1[ D_j ≥ τ_D  AND  W_j ≥ τ_W  AND  P_j ≥ τ_P ]
```

Smooth surrogate for differentiable training:
`ρ̃_j = σ((D_j−τ_D)/T)·σ((W_j−τ_W)/T)·σ((P_j−τ_P)/T)` — but the runtime MUST always
preserve the typed reason, e.g. `FIRST_BLOCK = WISDOM`. A scalar readiness score without
the cause of failure surrenders the CLAIMED interpretability benefit (itself untested;
it is what Ch. 13's ablation signatures test).

When `ρ_j = 0`, RPM opens the typed subgoal for the FIRST unmet prerequisite:

- Desire insufficient → the transformation is not relevant enough to pursue; deprioritize.
- Wisdom insufficient → retrieve, ask, use a tool, or learn — then re-measure.
- Power insufficient → allocate capacity, split the task, acquire a procedure, or route
  to a more capable expert.

**Section-retraction discipline (Correction 2 of the master charter):** prerequisite
satisfaction is ONE-DIRECTIONAL. A satisfied prerequisite is cached with its evidence and
timestamp; re-verification happens on explicit invalidation events (verifier rejection,
distribution-shift flag, governance change), never assumed reversible for free.

RPM here is also the **biasing circuit** in the electronic sense (Ch. 6): its job, when a
CJT is needed, is to move that CJT's operating point into the middle of its active region
by repairing whichever prerequisite pins it in cutoff or saturation.

---

## 4. ASOM operating-state semantics

The four CJT operating regions (cutoff / active / saturation / breakdown) are the
source-defined objects, from the CAS PCBA book. **ASOM itself is the Ohm guide's
session-derived mnemonic overlay onto those regions** — retained per the CAS-Ohm paper's
Conflict 3.5 disposition "only as a mnemonic overlay ... never as an identity theorem":

| ASOM | Region | Runtime meaning |
|---|---|---|
| S — Starved | Cutoff | Insufficient activation, knowledge, capacity, or relevant substrate |
| A — Aligned | Active | Proportional operation within the useful range |
| O — Oversaturated | Saturation | More Cause or flow yields little additional Effect |
| M — Misaligned | Breakdown / inversion | Wrong direction, wrong Effect type, structural failure |

ASOM is the readable dashboard. The underlying record is two-dimensional (Ch. 5). When
the region itself is uncertain, `a^{ASOM} ∈ Δ³` stores a POSTERIOR belief over regions —
an observer-uncertainty object, not a composition claim.

**Q-point.** The CAS PCBA source's characteristic-curve/load-line picture is adopted as
the operating model: the Bias configuration selects the characteristic curve; CAS-Ohm's
constraints contribute the load line; ASOM names the region containing the intersection
(the Q-point); RPM changes missing prerequisites so the Q-point MOVES; the verifier
decides whether the Effect at that Q-point is semantically correct. Worked examples:
Wisdom too low → Q-point in cutoff → RPM retrieves the missing method → Q-point enters
active. Too many premises → Q-point near saturation → RPM splits the argument into
subproblems routed to child CJTs, Effects recombined after verification.

---

## 5. The two-axis record: operating region vs semantic outcome

Frozen rule, inherited verbatim from the CAS-Ohm paper's requirement that dose-response
region and semantic outcome stay independent:

```
region_state       ∈ {cutoff, active, saturation, breakdown, non-ohmic, unstable, unassessed}
semantic_outcome   ∈ {intended, opposite, off-axis, unassessed}
```

An active response may still be wrong. A flat response may be cutoff, saturation, a wrong
direction, or a measurement failure. **A numerical region NEVER mechanically determines
that the semantic Effect is correct** — only the verifier writes `semantic_outcome`, and
the guide's design rule stands: a correct flow reading with a wrong effect points toward
bias, gain, saturation, or breakdown, not a simple resistance problem.

---

## 6. CAS-Ohm route score

Resistance decomposes into typed components:

```
R_j = R_{W,j} + R_{P,j} + R_{policy,j} + R_{context,j} + R_{resource,j}
```

(`R_W` = lack of applicable knowledge; `R_P` = lack of capability; the rest are external
constraints.) `V_j` = the goal/Foundation pressure supporting route `j`.

The route score:

```
s_j = m_j · ρ_j · ψ(Z_j) · (V_j / R_j)
```

- `m_j` — HARD permission mask. Absolute prohibitions are masks, never merely large
  resistances (a large `R` can be outvoted by a large `V`; a mask cannot).
- `ρ_j` — RPM readiness gate (Ch. 3).
- `ψ(Z_j)` — operating-region controller:

```
ψ(Z_j) = 0                (Starved / cutoff)
       = 1                (Active)
       = cap or split     (Oversaturated)
       = 0 + quarantine   (Breakdown / misaligned)
```

**The softmax boundary (inherited skeptical rule):** for `V, R > 0`,
`g_j = softmax_j(log V_j − log R_j)` — an Ohmic router is exactly a softmax router whose
logit decomposes into push-minus-opposition. Because `cV/cR = V/R`, the pair `(V, R)` is
unidentifiable up to scale. Therefore CAS-Ohm earns interpretability credit ONLY under
these conditions, all required:

1. `V_j` comes from an independently defined Drive/goal state (not a free learned logit);
2. `R_j` components come from separately measured capacity, resource, context, or policy
   constraints, each with its own record;
3. `β_j` remains a separate gain quantity (never folded into `V/R`);
4. absolute prohibitions are masks, not resistances;
5. the router beats the control battery — plain-softmax routing (arm B, falsifier
   `E ≤ B`, Ch. 14) AND the matched generic hierarchical controller (arm H, Ch. 12) —
   otherwise it is a renamed softmax and must be reported as such.

---

## 7. Simplex normalization and the absolute compute budget

Relative routing:

```
g_j = s_j / Σ_ℓ s_ℓ          (the operation-routing ALLOCATION simplex)
```

**Total flow — the corrected treatment.** The Baseline proved `I_total` is a decorative
dial in a fixed dense forward pass (every simplex-level quantity invariant to it). That
verdict is kept for the static experiment (`I_total := 1`) and REVERSED for this
architecture, where computation actually varies. Define the measured budget:

```
B_t = actual available compute, in declared units:
      CJT execution ticks | active experts | branch evaluations | generated tokens |
      retrieval operations | tool calls | forward/backward FLOPs | wall-clock ms
B_{j,t} = B_t · g_{j,t}      (the measurable allocation to CJT j)
```

Rules: (a) the unit is DECLARED and fixed per experiment; (b) `B_t` is observed, never
free; (c) for a dense Transformer `B_t` is constant and the coordinate degenerates —
which is exactly why the static baseline sets it to 1; (d) CAS-Ohm receives credit only
if its predicted allocation improves efficiency or fault diagnosis against matched
controllers (Ch. 12). The CAS-Ohm paper's own boundary stands: its equation is a
profile-specific response proposal, not physical law, not a validated attention measure.

---

## 8. Bias update law

Execution:

```
(E_{j,t}, B_{j,t+1}) = J(C_{j,t}, B_{j,t})
```

History dependence, in the mathematical (memristive-like) sense only — no physical
memristor claim:

```
x_{j,t+1} = F_j(x_{j,t}, C_t, E_t, verifier result)
R_{j,t}   = G_j(x_{j,t})
```

The history variable `x_t` is not a mysterious hidden scalar; it has typed internal
structure: RPM acquisitions, ASOM trajectory, memory state, prior verifier outcomes,
consolidation history. The CAS-Ohm paper marks stateful/hysteresis behavior as an open,
unvalidated research boundary — this chapter gives that boundary a concrete candidate
structure and nothing more.

What may update `B`: the CJT's own execution outcome, the verifier's decision, RPM
acquisitions, ASOM transitions, consolidation events, governance changes. What may NOT:
a model's proposal about another CJT's state (no authority), any write that bypasses the
governance gates in `G_{j,t}`.

---

## 9. Verification, rollback, and consolidation

After each Effect, the verifier (behavioral, external to the CJT) writes
`semantic_outcome` and triggers exactly one of:

```
commit | rollback | recurse | split | consolidate | reopen
```

**Typed abstention:** when blocked, the system reports the typed reason
(`FIRST_BLOCK = WISDOM`, `REGION = saturation`, `MASKED = policy`), not a generic
failure. The full failure ladder is DESIGNED to become distinguishable: wrong Idea chosen
/ right Idea wrong operation / right operation missing knowledge / knowledge present
missing capacity / adequate flow misaligned Bias / aligned Bias saturated transformation
/ everything right but the Effect false. Ordinary output checking sees only the last
line. Whether the typed reports actually localize faults is exactly the Ch. 13
double-dissociation test — and the advantage is REFUTED if ablations produce
undifferentiated error patterns.

**Selective-plasticity law (the most important learning application):**

| Bias state | Learning response |
|---|---|
| Starved | Do NOT merely raise the learning rate. Identify the missing Wisdom, Power, data, or capacity and open that subgoal. |
| Aligned | Reduce unnecessary updates; consolidate; softly protect the useful subspace. |
| Oversaturated | Cap updates, reduce gain, split the skill, or spawn another expert. |
| Misaligned | Roll back, quarantine, change the transformation, or reopen the Bias for structural repair. |

Training-time flow gets its OWN profile, separate from inference flow:
`Δθ_k = −η · g_k^{learn} · ∇L` with `g^{learn} = V^{learn}/R^{learn}` and a consolidation
form `R_k^{learn} = R_0 + λΩ_k` (`Ω_k` = estimated importance to a mastered capability —
the EWC-family mechanism, CAS-typed). Inference `V,R` and learning `V,R` are different
records; assuming they coincide is forbidden. Known structural threat carried from the
Baseline: superposition — parameter groups serve many regions at once, so disjoint
dampable region↔parameter maps may not exist; this is a falsifiable assumption of arm F,
not a premise.

---

## 10. Recursion limits and cycle detection

If every Bias has an RPM and every RPM subgoal uses CJTs whose Biases have RPMs, the
architecture can recurse forever ("computational ivy"). Mandatory base cases:

```
maximum RPM depth            | maximum branch count      | maximum compute budget B_t
return addresses             | memoized prerequisite results (with invalidation events)
shared prerequisite graph    | typed cycle detection (same subgoal signature on the stack)
hard halting conditions      | primitive Bias leaves that do not recurse further
```

**Granularity rule:** RPM/ASOM live at the level of CJT experts, Noetic operator modules,
boards, reasoning stages, retrieval paths, and tool paths — NEVER individual scalar
weights. And per the CAS-Ohm guide's aggregate warning: a healthy parent aggregate can
hide a starved child and an overloaded child — parent summaries must not erase child
probes; the trace keeps per-child records.

---

## 11. Fast loop vs slow repair loop

**Fast loop (every token / reasoning step):** read content → apply cached readiness →
route among ready CJTs → execute sparse transformations → produce candidate Effect.

**Slow loop (event-triggered only):** full RPM scan → open subgoals → update ASOM state →
retrieve missing knowledge → change plasticity → consolidate or reopen Biases → update
long-term memory.

Slow-loop wake conditions (frozen list): a readiness threshold fails; the verifier
rejects an Effect; the residual exceeds tolerance; saturation is detected; the goal
changes; a new skill is being learned. The full RPM does NOT run per token.

---

## 12. Matched adaptive-MoE baseline (the killer control)

The design's value claim is comparative, and the comparison that matters is arm **H**:

> a matched generic hierarchical controller — same parameter count, same sparse expert
> bank, same adaptive-compute machinery (learned gating, learned readiness scalar,
> learned region regulator), but NO CAS ontology: no typed D/W/P, no ASOM names, no
> Noetic labels, no V/R decomposition.

If the full CAS controller (arm F) does not beat H, the honest conclusion is that
hierarchical adaptive control helps and the CAS ontology is decoration. Cheaper killers
also included: anonymous MoE (arm A), and — carried from the Baseline's critique — hash
routing, which has matched learned routing in published settings and must therefore
appear as a sub-baseline of A.

---

## 13. Ablation signatures (pre-registered double dissociations)

Each component must produce its OWN failure fingerprint when removed. Predictions frozen
before any run:

```
Remove RPM        → prerequisite failures and forced answers INCREASE;
                    typed-abstention rate collapses to zero.
Remove ASOM       → saturation events, runaway updates, and collateral damage INCREASE;
                    accuracy on easy items unchanged.
Remove CAS-Ohm    → allocation efficiency worsens (compute per solved item rises);
                    semantic verification outcomes UNCHANGED.
Shuffle CAS labels→ operation-level transfer to unseen compositions DETERIORATES;
                    within-template accuracy may survive (the shortcut signature).
Swap in generic H → if all metrics stay equal, CAS-specific value is NOT established.
```

If two different ablations produce the same undifferentiated error pattern, the
fault-localization advantage is REFUTED for those components.

---

## 14. Hard falsifiers and the arm table

| Arm | Architecture |
|---|---|
| A | Matched ordinary mixture-of-experts (incl. hash-routing sub-baseline) |
| B | CJT experts with CAS labels, ordinary softmax routing |
| C | B + RPM readiness |
| D | B + ASOM regulation |
| E | B + CAS-Ohm routing |
| F | Full CJT + RPM + ASOM + CAS-Ohm |
| G | F with shuffled CAS meanings |
| H | Matched generic hierarchical controller, no CAS ontology |
| I | F with a random-matched state stream: every `p^{ND}` replaced by a frozen draw from a Dirichlet fit to the real profile population (matched entropy/sparsity), identical architecture and parameters |
| J | F with the simplex stream disconnected: every `p^{ND}` frozen to uniform `1/40`, so the pathway and its parameters exist and train but carry zero item-specific information (the matched-capacity control) |

**Letter map warning:** these arm letters do NOT correspond to the Static Coupling
Baseline's A–G letters (there, F was random-matched and G was matched-capacity). Any
cross-document comparison must name the document with the letter.

Frozen falsifiers (each failure = REFUTED for its claim, emitted by the deterministic
promotion program, never by prose):

```
B ≤ A                       → CAS expert meanings add no demonstrated value.
E ≤ B                       → CAS-Ohm routing adds no demonstrated value.
G ≥ F                       → CAS label semantics are not load-bearing.
F ≤ H                       → the win is generic hierarchical control, not CAS.
I ≥ F                       → the benefit is the extra state stream, not CAS structure.
J ≥ F                       → the simplex is decorative (pure capacity effect).
template-only gains         → no structural generalization shown.
controller overhead > compute saved → no efficiency claim allowed.
```

Metrics (frozen list): task accuracy; examples-to-threshold; old-skill retention; compute
used; branch count; unnecessary expert activations; correct abstention; successful
prerequisite recovery; collateral damage; routing balance; latency; GPU memory; causal
ablation effects. ≥10 seeds; group bootstrap; effect sizes + CIs.

**"Idea" — the operational definition for the first experiment (frozen):** one
independently represented and verifiable CAS-Sem proposition, event, or RPM subgoal —
never arbitrary token boundaries. **Attention aggregation:** one declared aggregation
procedure over `α_{ℓ,h,i,j}` is selected and frozen before any run, and compared against
alternatives as a robustness appendix, because no single universal α exists.

---

## 15. GPU execution plan

Per the standing compute law — nothing here runs until an owner-signed phase record
exists:

- Every neural script fails closed (`GPU_REQUIRED`); local RTX 4070 = smoke/shape-debug
  only; ALL claim-bearing runs on AWS (SageMaker Training or EC2 GPU, frozen container,
  receipts, cost ceiling, auto-terminate).
- Stage 1 (static preliminaries) reuses the Baseline's cached-activation economics
  (frozen `Qwen2.5-0.5B-Instruct`, heads-only training, ~tens of dollars).
- Stage 2 (adaptive arms C–H) CANNOT fully cache activations — adaptive computation
  changes the forward pass — so the budget is larger: adapter-level training (LoRA-class
  inserts, base frozen) on one A10G/A100; a pilot sizing run precedes the frozen sweep;
  expected bracket low hundreds of A10G-hours, exact ceiling frozen at sign-off.
- Datasets: construction-gold CAS traces per `CAS_TRACE_GOLD_SPEC_v1.md`
  (CONSTRUCTION_CANDIDATE → owner-gated promotion; no model votes; independent
  preservation checker; ^8 = Idea-triggers-Idea). Model outputs never create ground truth.
- Cached tensors hashed and S3-stored; every job writes the full receipt (instance, GPU,
  versions, digests, seed, wall-clock, peak memory, exit status, cost).

---

## 16. Claim boundary

- Status of EVERYTHING in this document: **PROPOSED_UNTESTED.** No advantage listed here
  is a capability. The spec-sheet rule applies: no status upgrade without an artifact
  path; negative results are never deleted.
- Claim mapping: decodability questions = Claim A; "CAS-specific" language = Claim B and
  requires beating BOTH the matched-semantic control and arm H (generic controller), not
  merely shuffled/random arms; intervention utility = Claim C; learning/retention
  benefits (Ch. 9's plasticity law) = Claim D.
- Settled negatives that constrain implementation: Claim A (weights natively CAS) is
  DEAD — in claim-bearing runs `p_i` comes from construction-gold traces, and any future
  activation-decoded `p_i` must first beat surface + matched-semantic + shuffled + random
  controls with the full leakage discipline.
- Label authority: per the Phase 0C backbone — models propose, a deterministic program
  issues candidates, only the owner-gated promotion path creates claim-bearing labels;
  model consensus changes audit priority only.
- Governance: owner-signed phase gates; deterministic claim promotion (raw result +
  frozen threshold + controls + hard gates → status); a failed hard gate is REFUTED,
  never "pass with caveats"; Claude is NOT the research governor.
- Honest possibility stated up front: this architecture may prove slower, overengineered,
  or no better than a matched adaptive mixture-of-experts. That outcome would be a
  RESULT, recorded, not a failure to be rescued.

---

### The one-line summary

> **CAS-Ohm sets the flow, ASOM reads the operating point, RPM repairs the Bias, and the
> CJT performs the transformation — and none of it earns a claim until it beats a
> matched generic controller under frozen falsifiers.**
