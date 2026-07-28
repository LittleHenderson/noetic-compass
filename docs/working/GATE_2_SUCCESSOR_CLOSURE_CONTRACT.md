# `GATE_2_SUCCESSOR_CLOSURE_CONTRACT`

**Committed BEFORE any successor number exists.** That is the entire point of this document.
**Date:** 2026-07-27 · **Ladder:** `0.38` · **Gate 2:** OPEN, threshold `0.46`

---

## Why this exists

Gate 2's language is fixed:

> *"small-model semantic authority, matched controls, uncertainty, claims reconciliation, and
> withdrawn-`ACCEPT` root cause close"* — `cas_harness_production_todo.md:1018`

Two successor lanes are now open — the narrow CJT/J-space joined experiment (`0dcca79b`) and the
`672`-item de-leaked corpus. Both could produce impressive numbers. **Neither may be declared
equivalent to Gate 2 after the fact.** Freezing the closure rule now removes the possibility of
arguing equivalence once results are visible, which is the exact failure mode this campaign has
spent the day guarding against.

---

## The controlling questions, answered now

**Q1 — Can `G2-JSPACE-SUCCESSOR` satisfy Gate 2, or only supply evidence for Gate 3?**

It can **contribute** to Gate 2 but **cannot satisfy it alone**. Gate 2's wording is *small-model
semantic authority*. A causal-intervention result on a registered direction is Gate 3 territory
("steering/ablation candidates pass preregistered controls", `:1019`). Causal evidence may
*strengthen* a Gate 2 packet; it may not *replace* the classification requirement.

**Q2 — Must both the joined CJT experiment and the `672` semantic test pass?**

**The `672` semantic test is required. The joined CJT experiment is not.** Gate 2 is about the
scoring working on a small model. The CJT lane is the mainline *scientific* effort and feeds
Gate 3; it is not a Gate 2 prerequisite.

**Q3 — Is semantic authority demonstrated by classification, causal intervention, or both?**

**Classification, on untouched grouped data.** Intervention is admissible as supporting evidence
and is required for Gate 3, not Gate 2.

**Q4 — What exact comparison must beat the character baseline?**

A **frozen** small-model internal readout, on **untouched grouped** data, must exceed **both**
char 3–5-gram **and** word TF-IDF, computed on **identical items** through the **same folds**.
Layer and token position frozen on a development partition, never on test labels.

**Q5 — What replication is required?**

The advantage must hold on a **second architecture family** (e.g. `pythia` and one of
`gpt2`/`OLMo`/`Qwen`), or the licensed claim names only the model where it held.

**Q6 — Who makes the final equivalence decision?**

**The owner, explicitly.** Not the agent, not the packet, not a hook. No run may declare Gate 2
closed.

**Q7 — What becomes licensed, stays unlicensed, or is withdrawn?**

Specified per result in the evidence packet, using the existing buckets
(licensed / not licensed / void / flagged), with the ceiling stated in the same sentence as the
claim.

---

## Closure rule — FROZEN

Gate 2 may close **only if all six hold**:

| | Condition |
|---|---|
| **A** | the `672`-item de-leaked benchmark carries **independently recoverable** signal |
| **B** | a **frozen** small-model internal readout beats char 3–5-gram **and** word TF-IDF on **untouched grouped** data |
| **C** | the advantage is present on the **clean drive axis** *and* on an **admissible World axis** |
| **D** | permutation, constant-body, surface, wrong-layer, and wrong-token controls **all pass** |
| **E** | uncertainty, claims reconciliation, and the withdrawn-`ACCEPT` root cause are **closed** |
| **F** | **the owner explicitly accepts** `G2-JSPACE-SUCCESSOR` as satisfying Gate 2 |

**`C` is not negotiable down to drive-only.** Today's run showed the model leading *only* on the
contaminated World axis while losing on the clean drive axis — the inverse pattern. A future run
that passes on drive alone, with World still leaked, does not close this gate.

**`B` carries the standing rule:** *statistical uncertainty cannot convert "did not exceed" into
"exceeded."* An overlapping interval is not a pass.

---

## What is already closed under `E`

| Item | Status |
|---|---|
| withdrawn-`ACCEPT` root cause | **CLOSED** — re-review `ACCEPTABLE`, 13/13 citations verified |
| claims matrix (item 1) | **CLOSED** |
| registry signature readiness (item 3) | **CLOSED** — 24 receipts, 4 signed, `verify()` True 4/4 |
| fixture replay (item 8) | **CLOSED** — re-review `ACCEPTABLE`, 17/17 citations verified |
| uncertainty / honest error bars | **DEMONSTRATED** — bootstrap CIs published at full width, including unfavourable ones |
| **small-model semantic authority** | **OPEN — the only remaining blocker** |

---

## Prohibited

- Declaring Gate 2 closed from inside any experiment that targets it.
- Substituting a causal-intervention result for the classification requirement.
- Reporting `672`-corpus accuracy on judge-selected items (circular).
- Any threshold in this document being revised after a successor number exists.

## Status

`FROZEN / OWNER DECISION REQUIRED FOR CLOSURE / NOTHING LICENSED`
