# CCB-R1 Stages 0–4 — Complete

**Date:** 2026-08-27
**Status:** Stages 0–4 built, passing, and enforced in CI. 69 tests.
**Evidence class:** bounded software evidence. Not a research packet, not
authenticated evidence — see `ccb_r1_gate_analysis_2026_08_27.md`.

---

## What runs

| Stage | Deliverable | Tests |
| :--- | :--- | ---: |
| **0** Static conformance | `stage0_lint.py` + two board fixtures | 4 + guard |
| **1** Deterministic simulator | `cjt_sim.py`, `rpm.py`, `cmb.py`, `cdab.py`, `episode.py` | 19 + 31 |
| **2** Fault injection, axis-mapped | `faults.py` | 15 (shared) |
| **3** Truth-firewall sweep | `sweep.py` | 15 (shared) |
| **4** RPM & memory dynamics | `rpm.py`, `cmb.py` | 31 (shared) |
| | **total** | **69** |

Every suite runs on every push via `.github/workflows/ci.yml`, plus a
two-directional fixture guard asserting the audited §11 board stays rejected and
the conformant rebuild stays clean.

---

## The corrections that were applied, and what they caught

### Stage 1 is no longer circular

The review flagged the drafted Stage 1 as unfalsifiable: the same act would
define CJT semantics *and* author the golden traces. With the sources committed,
**the guide is the oracle** — every expected value in the CJT traces is printed
on pp.12/13/14. The simulator can now be wrong.

### Stage 3 has two arms, and the second one earns its place

The drafted sweep asserted conclusion-invariance. That rewards a board that
ignores evidence. Split into `3A-inv` (irrelevant perturbation → invariant) and
`3A-sens` (relevant evidence → moves, correctly), with passing requiring both.

`rigid_reasoner` — a board that always returns the same answer — **passes
3A-inv with a perfect score and fails 3A-sens.** A single-arm sweep would have
certified it. That is the correction working, pinned by
`test_a_reasoner_that_never_updates_fails_3a_sens`.

### Stage 2 is scored, not asserted

"Stage-localization accuracy" was underspecified. Now: a confusion matrix over
(injected × detected), axis accuracy scored separately from stage accuracy, and
a **false-positive arm** on unfaulted controls — a scanner that always shouts is
not a scanner. Current: axis 1.0, stage 1.0, false-positive rate 0.0.

A compound fault reports axis **P**, not whichever single axis is checked first.

### Correction 2 is enforced, not assumed

`PrereqState` caches satisfaction. A cached-sufficient prerequisite **cannot**
retract on re-measurement — property-tested over **10,000 cases**. Genuine
capability loss is still representable, but only through an explicit, auditable
`retract()` call. That is section-retraction as a runtime invariant rather than
a docstring.

### The gaps the audit found are closed

- **`NEEDS_DESIRE`** — the audited design had four terminals and no exit for a
  D-block. Added, so every first-block outcome has a terminal.
- **Depth and cycle bounds** — the audited RPM had no bound; infinite sub-goal
  regress was representable. `RpmPlanner(max_depth=…)` terminates in
  `NONTERMINATING`, a reportable outcome instead of a hang. Cycles are detected.
- **The Δ39° mapping** — the CMB's 40 cells are keyed by the canonical
  `P0..O9` state literals, making explicit what the handbook already implied.
- **The bias firewall keys on domain, not drive** — `^5^P_{F7}` is a charter and
  is allowed on an evaluation stage; `^5^E_{F5}` is ambition and is not.

---

## What is deliberately *not* claimed

- **No experiment has been run.** These are synthetic boards. Per the research
  paper, they "validate software behavior only … cannot establish causal or
  empirical validity."
- **No baseline comparison yet.** B0 (`^8`-only control), B1 (no-bias), and B2
  (random-bias) are expressible against this harness; **B3 (unstructured LLM)**
  requires a model and belongs to Stage 5.
- **No kill criteria.** Still the owner's to supply. Without them the program
  can always conclude that more stages are needed.

---

## Stage 5 readiness

Nothing in Stages 0–4 gated on anything. Stage 5 is a different question, and
the gate analysis answers it: `Rule 9.2` authenticated eligibility is *"always
false"* pending six infrastructure items, roughly half of which already exist in
`scripts/sign_root_ci_protected_deploy_receipt.py`. That decision is
independent of everything above and can be taken whenever.
