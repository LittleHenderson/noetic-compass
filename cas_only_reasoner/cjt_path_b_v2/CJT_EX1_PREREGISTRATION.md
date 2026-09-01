# CJT-EX1 PREREGISTRATION — Expert Specialization and Transfer Pilot

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

## 2. The five conditions

| Condition | Organization |
|---|---|
| **E0 SHARED** | one expert handles every clause |
| **E1 ANON_MOE** | 4 experts, **soft-routed by a learned router** over clause content; no CAS identities |
| **E2 CAS_EXPERT** | 4 experts, **hard-routed by the true operation class** (^2/^3/^6/^8 → expert 0/1/2/3) |
| **E3 CAS_STRUCT** | E2 **plus a registered computational constraint** encoding the canonical ^2↔^3 involution |
| **E4 SHUFFLED** | 4 experts, hard-routed by a **frozen per-clause hash** carrying no operation information |

**The killer comparison is E2 vs E1** — same expert count, same parameters, same router
inputs; one routes by CAS operation identity, one learns its own routing. **E4** then asks
whether any E2 advantage is about CAS identity or merely about having four experts.

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

## 4. Retention (sequential learning)

Phase 1: train on **QB_REL only** for 500 updates. Phase 2: train on **QB_COMP only** for
500 updates, carrying the same optimizer (AdamW moments persist — the realistic continual
setting) while each phase gets its own warmup+cosine schedule. Measure how much QB_REL
survives.

Verified before launch: the schedule restarts cleanly across phases — both phases warm up
to an identical 1e-3 peak and decay to 1.09e-08, with `initial_lr` preserved. No
compounding or collapse.

Hypothesis under test: operation-routed experts interfere less, because a newly exercised
operation (^8, entering with QB_COMP) lands on a **different expert** than the ones QB_REL
trained (^3 and ^2).

Both statistics are reported: the **retention ratio** (a₂/a₁) and **absolute forgetting**
(a₁−a₂). Registered caveat: a ratio flatters a condition that learned less in phase 1 and
therefore had less to lose, so the phase-1 level is reported alongside it.

## 5. Gates before the main spend (P0)

- dataset digests match `PATHB_DATASET_MANIFEST.json`; **both** the C1 and the sealed-C2
  pid-set digests match `C1_SPLIT_MANIFEST.json` (verified from pids only — the sealed half
  is never read);
- cache binding verified fail-closed (per-record content hashes, manifest, model,
  tokenizer, extraction-code digest, layer, pid-set equality) with **raw counts persisted**;
- total trainable parameters matched within **1%** (measured spread 0.974%: E0 5,138,194 /
  E1 5,141,644 / E2 5,188,756 / E3 5,188,500 / E4 5,188,756 at hidden widths
  458/126/128/128/128);
- **bijection-is-relabeling confirmed** (see 2b);
- every condition's expert bank receives a nonzero gradient at step 50;
- routing behaves as specified per condition (E2/E3 one-hot by class; E4 uncorrelated with
  class; E1 soft; E0 single).

Any failure → `CJT_EX1_SMOKE_FAILED`, no main spend.

## 6. The seven registered success conditions (owner's list, all must hold)

1. **E2 − E1 ≥ 0.02** (CAS experts beat the anonymous matched MoE) — the killer comparison
2. advantage on **unseen verbs and templates** — true by construction (§3)
3. advantage spans **≥ 2 operation families**
4. **E2 − E4 ≥ 0.02** (shuffling removes the advantage)
5. **E3 − E2 ≥ 0.02** (removing the registered relationship damages transfer)
6. **E2 retention ratio > E1 retention ratio** (better retention under sequential learning)
7. matched parameters, compute, seeds

Status: `CJT_EX1_EXPERT_SPECIALIZATION_DEV_SIGNAL` if **all seven** hold, else
`NO_CJT_EXPERT_SPECIALIZATION_SIGNAL`.

**Registered stringency disclosure:** this is a seven-way conjunction, and with 597
evaluation records a margin's standard error is ≈ 0.029, so the 0.02 thresholds sit *below*
one standard error. These are decision thresholds, not significance claims. Per-seed
margins, seed sign-consistency, and the approximate standard error are reported alongside
every decision quantity so the reader can see how thin any margin is. This is stated in
advance so no post-hoc reinterpretation is possible in either direction.

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
