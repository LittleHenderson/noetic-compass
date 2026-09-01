# CJT-EX1 PREREGISTRATION v2 (AMENDED) — Expert Specialization and Transfer Pilot

> **AMENDED 2026-09-01 by owner ruling after the pre-launch stop.** The original
> protocol was NOT launched. Six changes are frozen below: (1) headroom-aware breadth
> (option B + C); (2) retention protocol replaced (phase 1 QB_INT, phase 2 QB_COMP) with a
> real-interference gate; (3) **E1S anonymous sparse top-1 MoE added as THE killer
> control**; (4) E3 demoted to exploratory with a bounded claim; (5) the result vocabulary
> fixed in advance; (6) E4 must be PROVEN class-independent. Cap $1.20, projected ~$0.72.

**Frozen before any GPU spend. Development-only, non-claim-bearing.**

Owner ruling (2026-09-01): *"Standalone table/J lane: CLOSE. Dedicated J1 GPU pilot:
OPTIONAL, NOT THE MAIN PATH. Carry J forward: YES, as a computational constraint inside
experts. Next primary experiment: CJT EXPERT SPECIALIZATION."* Plus: *"I think a GPU
would work quicker and better on the following and probably in the cloud AWS."*

---

## 0. The owner's correction, adopted

I had written that because the model receives exact labels it "already holds everything R
contains." The owner narrowed this and the narrowing is correct and adopted here:

> Labels are **street names**. R is the **map showing how the streets connect**. Knowing
> the street names does not literally give you the map. But a flexible network, given
> enough examples, can learn the map for itself.

So: exact labels alone do **not** contain R; labels plus sufficient experience allow R to
be **learned**; a frozen table may help mainly by **reducing how much experience is
needed**. J remains a legitimate inductive prior. My earlier wording was broader than the
mathematics warranted. What CJT-EX1 tests is therefore not "does CAS supply missing
facts" but "does CAS **organize the machine** better."

## 1. The question

Does organizing expert modules **by CAS operation** do architectural work — specialize,
transfer, and retain better — than a **matched generic** expert bank?

Everything is held identical: executor, frozen activations, data, seeds, optimizer,
schedule, update count, total trainable parameters, and (measured) per-step compute.
**Only the expert organization differs.**

## 2. The six conditions

| Condition | Organization | Active experts / clause |
|---|---|---|
| **E0 SHARED** | one expert handles every clause | 1 |
| **E1 ANON_MOE** | 4 experts, **dense soft mixture** by a learned content router | 4 |
| **E1S ANON_SPARSE** | 4 experts, learned content router, **top-1 straight-through** | **1** |
| **E2 CAS_EXPERT** | 4 experts, **hard-routed by the true operation class** | 1 |
| **E3 CAS_STRUCT** | E2 + the canonical ^2↔^3 involution as a computational rule | 1 |
| **E4 SHUFFLED** | 4 experts, frozen per-clause hash routing | 1 |

**THE KILLER COMPARISON IS E2 vs E1S** (owner ruling). Both select exactly **one** expert
per clause with matched parameters, width and active-expert count — one selects by CAS
operation identity, the other by a learned content router. Without E1S an E2 win could not
be separated from "using one expert instead of mixing four." **E1 (dense)** is retained to
tell us whether sparsity itself helps; **E4** tells us whether the stable
operation-to-expert *assignment* matters.

Measured capacity match across all six: widths 464/128/128/128/169/128, counts
5,186,926 / 5,195,932 / 5,195,932 / 5,188,756 / 5,197,658 / 5,188,756 — **spread 0.206%**.

### 2a. E3's constraint — J carried forward as computation, not lookup

The canonical ^2↔^3 involution ("an Idea the Mind has an affinity for and is **attracted
toward**" vs "an Idea the Mind is **adverse to and repelled by**") is expressed as a rule
about how two experts *transform*, not as a table entry saying they are related: the
aversion expert's readout is tied to the negation of the attraction expert's,
`v[1] = −v[0]`. Aversion is literally attraction read with reversed orientation. The
^6 and ^8 experts keep free readouts.

### 2b. E4 design note (registered)

A fixed **bijection** class→expert would not be a control at all — it is a pure relabeling
of expert indices and trains to a bit-identical model. This is the lesson the C1 review
taught when the four "NULL siblings" turned out to be one model. The scramble is therefore
**per-clause, not per-class**, and the bijection-is-relabeling claim is **verified in the
P0 gates, not assumed**.

### 2c. Disclosed: class labels remain available to every arm elsewhere

Every condition also receives the exact one-hot operation profile through the **attention**
path (`λ·⟨W_r q, p⟩`), exactly as in A1 and C1. So E1 and E4 are not label-blind — they are
**expert-organization-blind**. This is deliberate: removing labels entirely from E1/E4
would confound *expert organization* with *label availability*, and the owner's question is
specifically about organization. Stated plainly rather than glossed.

## 3. Transfer is built into the data, not bolted on

Training uses families **A and B** (verbs 0–5, clause forms 0–3). Evaluation uses family
**C** (verbs 6–7, form 4), which the model never sees in training. **Every reported
accuracy is therefore already an unseen-verb, unseen-template transfer number.** The
`C2_STRUCTURE_EVAL` half of val stays **sealed**; evaluation uses the 597-record
`C1_TRANSFORM_SELECT` half. Both protected splits remain untouched.

Disclosed reuse: those 597 records were the C1 evaluation set. C1 selected no transform
(`NO_TRANSFORM_CONSUMES_STRUCTURE`), so no selection carries into EX1; the reuse is mild
and is recorded rather than hidden.

## 4. Retention (sequential learning) — AMENDED

**Phase 1 = QB_INT (^2, ^6). Phase 2 = QB_COMP (^2, ^6, and ^8 NEWLY INTRODUCED).**

The original protocol (QB_REL then QB_COMP) was rejected before spend: QB_COMP contains
**zero ^3 clauses** in all 3,000 records, so a hard-routed ^3 expert received no phase-2
gradient and *could not forget*. CAS arms were shielded by the clause template rather than
by expert organization.

**Precise claim (owner correction, adopted):** not "every expert is exercised in both
phases" — ^2 and ^6 are, ^8 is new in phase 2, and **^3 appears in neither**. The accurate
statement is: *every expert relevant to the retained phase-1 skill (^2 and ^6) remains
exposed to phase-2 learning, while ^8 enters as a new specialist.*

Measured and reported, never a bare ratio: retained accuracy **before and after** phase 2,
absolute **forgetting** (before − after), new-task **acquisition**, per-expert **gradient**
and **parameter movement**, and the count of nonzero-gradient updates in each phase.

A retention advantage requires **all** of:
- E2 forgets at least **0.02 less** than E1S, positive in **≥ 2 of 3 seeds**;
- E2's phase-2 acquisition is within **0.02** of the best matched control (so a model
  cannot "retain" by refusing to learn);
- **real interference pressure**: every condition gains ≥ 0.05 on the new task and shows
  nonzero parameter movement in its experts. If not, the run emits
  `RETENTION_STRESS_INSUFFICIENT` and **no retention claim is made**.

## 5. Gates before the main spend (P0)

- dataset digests match `PATHB_DATASET_MANIFEST.json`; **both** the C1 and the sealed-C2
  pid-set digests match `C1_SPLIT_MANIFEST.json` (verified from pids only — the sealed half
  is never read);
- cache binding verified fail-closed (per-record content hashes, manifest, model,
  tokenizer, extraction-code digest, layer, pid-set equality) with **raw counts persisted**;
- total trainable parameters matched within **1%** (measured spread **0.206%** after the
  capacity-matching fix; widths 464/128/128/128/169/128);
- **E4 proven class-independent**: mutual information between its routing and the CAS class
  must be ≤ 0.01 bits. Measured on the real data before launch: **0.000084 bits** over
  54,000 training clauses and 0.002978 over 3,582 eval clauses (finite-sample bias alone is
  0.0018), against E2's 2.000 bits. Every class spreads ≈25% across all four experts, so it
  is not a global permutation;
- **every** bank tensor in both banks receives a nonzero gradient (the readout bias `vb` is
  exempt and disclosed: a constant shift is softmax-invariant across candidates, so it is
  non-identifiable by construction);
- **bijection-is-relabeling confirmed** (see 2b);
- every condition's expert bank receives a nonzero gradient at step 50;
- routing behaves as specified per condition (E2/E3 one-hot by class; E4 uncorrelated with
  class; E1 soft; E0 single).

Any failure → `CJT_EX1_SMOKE_FAILED`, no main spend.

## 6. The registered success conditions (amended)

1. **E2 − E1S ≥ 0.02** — the killer comparison, against the *sparse* anonymous control
2. advantage on **unseen verbs and templates** — true by construction (§3)
3. **breadth over ELIGIBLE families**: ≥ 2 eligible families improved, where a family is
   **saturated** (and excluded from this gate, though still fully reported) when baseline
   ≥ 0.99 **or** headroom < 0.01, and an eligible family counts as improved when its
   **mean paired gain ≥ 0.005** and the gain is **positive in ≥ 2 of 3 seeds**.
   Frozen for this evaluation: **QB_COMP = saturated; QB_REL and QB_INT = eligible.**
   No post-result family substitution is permitted.
4. **E2 − E4 ≥ 0.02** (shuffling removes the advantage)
5. **E3 − E2 ≥ 0.02** — *exploratory only*
6. **retention** per §4 (forgetting margin + acquisition tolerance + interference gate)
7. matched parameters, compute, seeds
8. **E4 proven class-independent** (MI ≤ 0.01 bits)
9. **competence floor**: every arm ≥ candidate-uniform chance + 0.15

Per family the run reports absolute accuracy, absolute gain, **remaining-error reduction**,
raw additional correct answers, and **paired** uncertainty — every arm sees the same
records, so paired statistics are used throughout rather than the independent-samples
formula that made the earlier standard error larger than the margin it decided.

### Frozen result vocabulary

| Outcome | Status |
|---|---|
| E2 beats E1 (dense) but **not** E1S | `SPARSITY_ADVANTAGE_ONLY` |
| E2 beats E1S **and** clears breadth, shuffle and retention | `CJT_EXPERT_SPECIALIZATION_SIGNAL` |
| E4 ≥ E2 (with E4 a valid control) | `CAS_EXPERT_MEANINGS_NOT_LOAD_BEARING` |
| no CAS arm beats E1S | `NO_CJT_EXPERT_SPECIALIZATION_SIGNAL` |
| E3 − E2 ≥ 0.02 | secondary: `STRUCTURED_WEIGHT_SHARING_SIGNAL` |
| insufficient phase-2 learning or parameter movement | appended: `RETENTION_STRESS_INSUFFICIENT` |

An E3 advantage is **never** reported as an involution-specific CAS advantage: this run has
no matched generic pair-sharing control, so constrained sharing and the *specific* CAS
involution are not separated. **No CAS-specific claim is licensed by any outcome.**

## 7. Permitted and prohibited conclusions

Permitted at most, and only if all seven conditions hold:

> CJT-organized expert modules improved specialization, transfer, or retention relative to
> a matched generic expert architecture in a controlled development task.

Prohibited regardless of outcome: **"CAS-specific"** and **"specific"** (reserved by the
standing claim law for incremental value over serious matched controls under protected
evaluation), `EMPIRICALLY_SUPPORTED`, `GATE1B_PASS`, `CJT_TRANSFORMER_VALIDATED`, any
claim promotion, any protected read, any read of the sealed C2 half, any threshold change
after seeing numbers, and any second tournament to "fix" a disappointing result — a
`NO_CJT_EXPERT_SPECIALIZATION_SIGNAL` outcome is a finding, recorded and kept.

## 8. Money

One self-terminating `g4dn.xlarge` (Tesla T4) in us-west-2 at $0.526/hr. **Hard cap
$1.20** (≈137 minutes), set by me consistent with prior rounds (C1 $0.80, C2 $0.60) and
**subject to owner override** — the owner authorized the experiment and the cloud, not a
specific figure.

Measured projection: per-step compute is 1.50–1.64× C1's across conditions (well matched
between conditions), giving ≈ 71 minutes total including boot, dependency install, model
download and activation extraction — about **$0.62**, with 66 minutes of headroom under
the cap. In-instance hard timer 110 min; client watchdog force-terminates at 120 min;
`InstanceInitiatedShutdownBehavior=terminate` plus an EXIT-trap shutdown. Partial results
flush after **every** run so a mid-run failure cannot destroy the evidence. A standalone
receipt (instance id, runtime, self-termination evidence, cost + method
`instance_runtime_estimate`) is filed in the same commit as the results; the harness's own
`compute_wall_estimate` is recorded separately and labelled a **lower bound**. Cumulative
program spend before this run: **$1.889 of $30**.
