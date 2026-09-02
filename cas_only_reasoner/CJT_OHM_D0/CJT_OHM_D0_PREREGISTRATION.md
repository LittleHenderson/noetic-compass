# CJT-OHM-D0 — EQUAL-CONDUCTANCE DIAGNOSTIC REPAIR BENCH — PREREGISTRATION v0.1

**Status:** `DESIGNED — NOT BUILT — NOT ATTACKED — NOT AUTHORIZED TO RUN`
**Owner ruling 2026-09-02:** typed diagnosis and next-tick repair is the **primary next
hypothesis**. `GPU: NO, until audit and preregistration.`
**Builder:** Claude. **Auditor:** to be named; not Claude.
**Cost:** `$0` to design. Stage 1 is CPU. No GPU is requested by this document.

---

## 0. Conflict of interest

I produced the `C8` result this bench exists to test properly, and the owner has already
corrected my framing of it once — I measured a coefficient-only competitor and reported it as
though it settled something about CAS. **That correction is the reason this bench exists**, and
it is the reason I must not audit it.

## 1. The question, frozen

> Given **identical current conductance** but **different underlying causes**, does the typed
> CAS-Ohm factorisation learn the correct **next-tick repair** better than a matched
> **full-information generic controller** receiving the same raw fields?

**What this is not.** It is not *"can a coefficient pick the repair"* — `CJT-OHM-0R` `C8` already
showed it cannot, and that is a statement about coefficients, not about CAS. The generic
competitor here sees **every field the CAS controller sees**, as a flat vector.

CAS earns something only on: **sample efficiency, unseen combinations, repair-error rate,
next-tick recovery, diagnosis fidelity, and permission enforcement.** Never on expressiveness —
`CJT-OHM-0R` `C15` proved the law restricts nothing.

## 2. Gold by causal simulation, never by declaration

**The owner's constraint, and the most important line in this document:**

```
enumerate the legal repairs
simulate the next tick under each
verify the resulting Effect
select the lowest-cost repair that succeeds
EXCLUDE TIES
```

**No human, and no builder, declares which repair is correct.** In `CPB-0` the status was
selectable by one line in the corpus generator. The equivalent free parameter here is the
**repair-cost function**, and it is where this bench would die.

> **REGISTERED:** the cost function is frozen before any run, and the result **must** include a
> **sensitivity analysis across at least three cost functions**. If the ranking of arms changes
> with the cost function, the result is `STATUS_NOT_EMITTED`. A finding that depends on my
> choice of costs is my choice, not a finding.

## 3. The pre-check that could kill this bench before it is built

**Registered as the first thing to measure, before any arm is scored:**

> **`GATE_REPAIR_NOT_TRIVIALLY_RECOVERABLE`** — is the correct repair recoverable by a rule that
> uses no controller at all? Candidates that must ALL be measured and ALL fail:
> `argmax` over resistance components; `argmin` over `V`; "always repair the largest single
> deficit"; "always pick the cheapest legal repair"; "always pick the most frequent repair in
> training"; the repair implied by the single largest field of the raw state vector.

If any trivial rule reaches high accuracy, **the bench is dead and no controller comparison
means anything.** Six label-free shortcuts have been found in this program's benches; three were
created by the repair for the previous one. This gate exists because I expect a seventh.

## 4. Arms — the owner's list, with what each is for

| arm | receives | role |
|---|---|---|
| `D0_NO_REPAIR` | — | floor: never repairs |
| `D1_RATIO_ONLY` | `g = V/R` and nothing else | the coefficient-only competitor `C8` already beat — kept as the **documented weak arm**, never as the bar |
| `D2_GENERIC_FULL_STATE_MLP` | **all raw nongold fields, flat** | **THE BAR.** The owner's correction made explicit |
| `D3_GENERIC_MONOTONE` | same fields, monotone-constrained | a *structured* generic — tests whether monotonicity alone explains any CAS gain |
| `D4_CAS_TYPED_REPAIR` | same fields, CAS-Ohm factorisation + typed repair rules | the mechanism under test |
| `D5_CAS_TYPES_SHUFFLED` | same fields, type↔repair correspondence broken | **if this does not hurt, the typing is ornamental and the lane closes** |
| `D6_ORACLE` | the simulated gold | ceiling, never a method |

`D3` is the arm I expect to be decisive. If a *generic monotone* controller matches `D4`, the
finding is `MONOTONE_STRUCTURE_SUFFICIENT` — structure helped, the CAS form did not.

## 5. Task families

Each case: a state with **matched conductance** across junctions but a **different cause**.

```
LOW_DRIVE            V weak, resistance ordinary       -> clarify goal / deprioritise
HIGH_CONTEXT_R       Drive strong, context conflict    -> remove a context constraint
HIGH_RESOURCE_R      Drive strong, compute short       -> allocate compute / split
MISSING_WISDOM       readiness zero, prerequisite gone -> retrieve / ask / learn
POLICY_BLOCKED       hard mask closed                  -> refuse, regardless of Drive
SATURATED            operating region at ceiling       -> cap or decompose
```

**Held out:** unseen cause combinations, unseen resistance-component orderings, and a family
withheld entirely to test transfer.

## 6. Status vocabulary — separate, never OR-ed

```
STATUS_NOT_EMITTED               a precondition failed, or the cost-function sensitivity failed
REPAIR_TRIVIALLY_RECOVERABLE     a no-controller rule solved it; the bench is void
CAS_TYPED_REPAIR_SIGNAL          D4 beats D2 AND D3, and D5 shuffling destroys it
MONOTONE_STRUCTURE_SUFFICIENT    D3 matches D4; structure helped, the CAS form did not
GENERIC_FULL_STATE_SUFFICIENT    D2 matches D4; the factorisation adds nothing
CAS_TYPING_ORNAMENTAL            D5 shuffling does NOT hurt
SAMPLE_EFFICIENCY_SIGNAL         same ceiling, materially fewer examples -- reported SEPARATELY
```

`CAS_TYPED_REPAIR_SIGNAL` requires **all three**: beat `D2`, beat `D3`, and be destroyed by `D5`.
Any two without the third is not the status.

## 7. What this bench cannot settle

- **It does not test weight generation.** That claim is closed (`CJT-OHM-0R` `C1`, `C14`).
- **It does not test the cascade.** That is `CJT-CASCADE-S0`, a separate design, and the owner
  ruled it is *not* a continuation of the retired weight claim.
- **It does not license any CAS-specific claim** about cognition, only about this bench.
- **Whether it needs a GPU at all is an open question I want answered before asking for one.**
  A repair-selection task over small state vectors may be a CPU problem; `CJT-OHM-0R` was.

## 8. Not yet attacked

**Two designs in a row have been retired at `$0` by their own adversarial review** — `CMB-RP1`
(the curve could not exist; the diagnostic was misattributed) and `CPB-0` (the status was
selectable by one line). Both reviews found the shortcut *inside a preregistration I had just
committed*.

**This document gets the same treatment before a line is written.** Three things I already
expect an attacker to say, registered now so they cannot be presented as novel later:

1. *"The repair is recoverable by `argmax` over resistance components."* — §3 exists for this and
   it is the likeliest way the bench dies.
2. *"The gold depends on your cost function, so you chose the answer."* — §2 registers the
   sensitivity analysis; if the ranking moves, no status is emitted.
3. *"`D2` with enough data matches `D4`, so this is a sample-efficiency question dressed as an
   accuracy question."* — probably correct, which is why `SAMPLE_EFFICIENCY_SIGNAL` is a separate
   status and not a component of the main one.
