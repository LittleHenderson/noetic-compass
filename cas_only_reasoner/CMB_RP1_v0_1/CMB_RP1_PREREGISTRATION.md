# CMB-RP1 — PREREGISTRATION v0.1 (DESIGN ONLY, NOT AUTHORIZED TO RUN)

**Status:** `DESIGNED — NOT BUILT — NOT AUTHORIZED TO RUN`
**Owner authorization:** *"AUTHORIZE CMB-RP1 DESIGN"* — 2026-09-02. **Design only.**
**Builder:** Claude. **Auditor:** to be named; not Claude, who wrote this.
**Spend to date:** `$0`.

---

## 0. Conflict of interest, declared first

I built CMB-P0, CMB-P1, CMB-P2, RGM-0.2 and CMB-RP0. I produced the diagnostic this bench
exists to test, and I would be the one embarrassed if it fails. **That is the reason to test
it, and the reason I must not audit it.**

## 1. The question, frozen

CMB-RP0 closed on an audited negative. `No automatic second repair` means CMB-RP1 must **not**
be *replay selection again with fixes* — that question was answered, decisively, against the
mechanism, and re-asking it is exactly what this program's discipline exists to prevent.

What survived CMB-RP0 is a **diagnostic**, not a mechanism:

> The two-tier verifier detects **semantic contradiction**. It does not detect **structural
> anomaly**.

That sentence currently rests on **two data points**: RGM-0.2 (one adaptive forgery, blocked by
consistency) and CMB-RP0 (132 cheap forgeries, beaten by a degree count). **It has never been
tested as a prediction.** It was written *after* seeing both results, which is precisely the
shape of a post-hoc story.

> **FROZEN QUESTION.** Across an attack family that varies continuously from *purely semantic*
> to *purely structural*, does the two-tier verifier's exclusion rate follow the diagnostic's
> prediction — high where the attack must be semantically ambiguous, collapsing where the attack
> is structurally normal — and does a degree-only filter show the **mirror** pattern?

And the second question, which decides whether the deferred structural-forgery build is ever
needed:

> **Is the uncovered case CONSTRUCTIBLE?** A forgery that is *simultaneously* semantically
> consistent (no contradiction for the verifier to find) and structurally normal (no degree
> anomaly for the cheap filter to find). If it cannot be built cheaply, the registered gap is
> theoretical. If it can, that is a finding on its own.

## 2. The prediction, registered BEFORE any data

This is the part that makes it a test rather than an exploration. **Written now, checkable
later, and wrong if the curves come out flat.**

Let `α ∈ [0, 1]` parameterise the attack: `α = 0` is a purely **semantic** forgery (a near-copy
that must sit inside the contradiction band to work, and is otherwise structurally ordinary);
`α = 1` is a purely **structural** forgery (semantically distant, cheap, numerous — the
CMB-RP0 attack).

```
PREDICTED, in advance:

  verifier exclusion      HIGH at alpha=0, FALLING as alpha -> 1
  degree-filter exclusion LOW  at alpha=0, RISING  as alpha -> 1
  the two curves CROSS at some intermediate alpha
```

**FALSIFIED IF ANY OF:**

- either curve is **flat** (no monotone trend across `α`) — the diagnostic describes nothing;
- the curves **do not cross** — one method dominates everywhere and the "complementary
  defences" claim is wrong;
- the verifier's curve **rises** with `α`, or the degree filter's **falls** — the diagnostic is
  backwards;
- a **single mechanism-free competitor** beats both across the whole range — the whole framing
  is unnecessary.

**A flat pair of curves is the most likely honest outcome and must be reported as such.**

## 3. Two stages, cheap falsification first

**STAGE 1 — CPU, `$0`, no training, no GPU.** Construct the `α` family; measure verifier and
degree-filter exclusion across it; test the prediction in §2. This is string similarity and
small graph algebra, exactly as RGM-0.2 was, and it needs no model.

> **If Stage 1 falsifies the prediction, the bench STOPS THERE and reports the negative.** No
> GPU, no training, no Stage 2. This is deliberate: the expensive stage is only reachable by
> passing the cheap one.

**STAGE 2 — GPU, gated, only if Stage 1 confirms a constructible uncovered case.** Measure
whether that case actually **damages a model through replay** — because a forgery that no
defence catches is only interesting if it does harm once it reaches the weights. This is the
stage where `memory_feeds_training = true`, and therefore the stage the interlock governs.

**Stage 2 is NOT authorized by this document.** It requires its own owner authorization after
Stage 1 reports.

## 4. Arms

Every arm is registered before any run, and the mechanism-free competitors are the bar.

| arm | what it uses | role |
|---|---|---|
| `VERIFIER_AUTHORIZED` | the two-tier verifier, authorized tier | the mechanism under test |
| `VERIFIER_RETRIEVED` | its retrieval tier alone | **it dominated the mechanism in CMB-RP0 — it is a competitor, not a component** |
| `DEGREE_FILTER` | graph degree only | mechanism-free; the predicted mirror |
| `SEMANTIC_NEAREST` | semantic distance only | mechanism-free |
| `RANDOM_EXCLUDE` | excludes at the same rate, at random | **volume control** — matches every arm's exclusion COUNT so a "win" cannot come from excluding more |
| `ORACLE_TRUTH` | the forgery labels | ceiling, never a method |

`RANDOM_EXCLUDE` exists because of A1.5: an arm that excludes more items is a different
experiment, not a better detector.

## 5. What must be true before a single number is read

Preconditions, checked and reported **before** any arm is scored:

- **`GATE_ALPHA_IS_REAL`** — the `α` parameter must actually move both the semantic and the
  structural properties it claims to. Measured directly: contradiction-band membership and
  degree separability must each vary monotonically with `α`. **If `α` does not move them, the
  family is not an attack spectrum and no status is emitted.**
- **`GATE_MECHANISM_FREE`** — no query-independent shortcut recovers the forgeries. This lane
  has produced **four** label-free shortcuts, and three were created by the repair for the
  previous one. The five-depth check (content, one-hop, two-hop, topology, candidate identity)
  runs before any arm.
- **`GATE_ID_ORDER`** — store order, attack placement and query selection are drawn per world
  from the world's own RNG, and an `ID_ORDER` arm must not tie the ceiling. **CMB-RP0 failed
  this at 32/32 overlap and it was found by an outsider, not by me.**

## 6. Status vocabulary — the outcomes, all of them

```
DIAGNOSTIC_PREDICTS            both curves monotone in the predicted directions, and they cross
DIAGNOSTIC_PARTIAL             one curve behaves, the other does not
DIAGNOSTIC_FALSIFIED           flat curves, no crossing, or reversed direction
UNCOVERED_CASE_CONSTRUCTIBLE   a forgery evading BOTH defences was built, and how cheaply
UNCOVERED_CASE_NOT_FOUND       within the registered search budget, none was built
STATUS_NOT_EMITTED             a precondition failed
```

**`DIAGNOSTIC_FALSIFIED` retires the sentence from the spec sheet.** It does not soften it, does
not add a caveat, and does not get re-run with a different attack family. Registered now so that
outcome is not renegotiated later.

## 7. Power, registered as a limitation before the run

CMB-RP0 measured a between-world sd of `0.0706–0.1151` on paired forgetting deltas. **Exclusion
rates are COUNTS**, with much lower relative variance — which is why CMB-RP0's safety half was
decisive while its capability half was not. Stage 1 is therefore expected to be **adequately
powered**, and that expectation is itself a registered claim: the run reports the measured
between-world sd of the exclusion rates, and **if it exceeds the effect the curves show, the
result is `STATUS_NOT_EMITTED`, not a headline.**

Threshold and uncertainty procedure: paired permutation on per-world values, `N_PERM = 10000`,
with the margin set from a **measured null** — two independent draws of the same stochastic arm
— on **dev worlds only, never the registered ones.**

## 8. Governance

- **Worlds:** a fresh block, asserted disjoint from `0–19` (RGM-0.1), `500–511` (RGM-0.2),
  `700–708` (CMB-RP0) and the `750+` dev range. Registered before the run.
- **Stage 1 cost:** `$0`, CPU. **Stage 2 cost:** not requested; Stage 2 is not authorized.
- **The interlock:** Stage 2, if it is ever authorized, emits its own pipeline config, derives a
  `DEVELOPMENT_REPLAY` manifest from it, calls `require_clearance` **before loading or training
  anything**, and binds the clearance into its receipt, which `verify_receipt_clearance.py`
  must then pass. Stage 1 does not train and does not need it.
- **No claim promotion** without an independent audit by someone who did not build this.
- **No automatic second repair.** If CMB-RP1 fails, it fails.

## 9. What this design does NOT do

- It does **not** re-run replay selection. That question was answered against the mechanism.
- It does **not** build the structural-forgery defence. That remains deferred, and its trigger
  remains `DORMANT`.
- It does **not** assume the diagnostic is true. **The most valuable outcome available here is
  `DIAGNOSTIC_FALSIFIED`**, because it would retire a sentence I wrote and that two audits have
  since repeated.
