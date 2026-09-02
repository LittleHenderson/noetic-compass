# CPB-0 — CORROBORATION PAYLOAD BENCH — PREREGISTRATION v0.1

**Status:** `DESIGNED — NOT BUILT — NOT AUTHORIZED TO RUN — NOT YET ATTACKED`
**Owner:** *"design the corroboration payload bench"* — 2026-09-02. **Design only.**
**Builder:** Claude. **Auditor:** to be named; not Claude.
**Cost:** Stage 1 is CPU, `$0`. No GPU, no training, no model.

---

## 0. Conflict of interest

I built every bench in this lane, I found this hole, and I would be the one whose finding
shrinks if it turns out to be a one-line bug. **That is the reason to design the bench so the
boring answer is the easy one to reach.**

## 1. The hole, already demonstrated at `$0`

An **exact copy** of a stored memory's trajectory and semantics, given a **fresh provenance
root** and a **different `answer_field`**, is **authorized 20/20**. The verifier reads it as
corroboration — as its own docstring says it should: *"Identical copies CORROBORATE and are
fine."*

**Corroboration is judged on the fields the query matches — trajectory and context — and never
on the payload that would be acted upon.** Two memories can agree perfectly on everything the
verifier reads while asserting opposite things. Worse than a miss: the system becomes **more**
confident because the forgery is there.

**This bench does not exist to re-demonstrate that.** It is demonstrated. Re-measuring it is a
precondition, not a result.

## 2. The real question, frozen

> **Is this a DEFECT with a one-line fix, or a property that resists cheap repair?**

And the question that decides whether the fix is worth anything:

> **Does a payload-agreement check buy anything that a CHEAPER check does not already buy?**

## 3. The prediction, registered before any data — and it is the BORING one

```
PREDICTED:
  a one-line payload-agreement check kills the attack completely (authorized forgeries -> 0)
  at zero cost in legitimate corroboration

CONSEQUENCE IF TRUE:
  this is a DEFECT REPORT plus a FIX, not a research finding.
  The lane closes with a patch and CPB-0 reports that plainly.
```

**I expect to be right, and being right is the cheap outcome.** The design exists to make that
conclusion reachable in one CPU run rather than argued about.

**The prediction is FALSIFIED, and something structural exists, if EITHER:**

- the payload check has **material collateral** — it blocks legitimate corroboration, the way
  `TAU_AUTH = 0.90` destroyed pattern completion in RGM-0.2; or
- the attack **survives** it — an attacker who also matches the payload still gets authorized
  while asserting something harmful.

## 4. The trap this design is built to avoid

**A payload check is worthless if the payload is recoverable from the fields the verifier
already reads.** Topic is 100% recoverable from the semantic vector (measured, `480/480`), so if
payload is a function of topic, then "check the payload" and "check the semantics" are the same
check, and a cheaper semantic competitor matches it for free. **That coupling is exactly what
killed CMB-RP1**, and it is registered here in advance rather than discovered afterwards.

So the corpus carries **two payload regimes**, and the bench runs both:

| regime | payload assignment | what it tests |
|---|---|---|
| `PAYLOAD_COUPLED` | a deterministic function of topic | payload adds **nothing**; a semantic competitor should match it |
| `PAYLOAD_INDEPENDENT` | drawn independently of topic, semantics and trajectory | **only** a payload check can see a divergence |

> **SHARP PREDICTION:** the payload check beats every competitor in `PAYLOAD_INDEPENDENT` and
> **ties a plain semantic competitor in `PAYLOAD_COUPLED`.** If it wins in both, the bench is
> measuring a tautology and the result is void.

## 5. Arms — the repair must beat the cheap things that also work

| arm | what it reads | role |
|---|---|---|
| `VERIFIER_ASIS` | the current two-tier verifier | the hole, unrepaired |
| `PAYLOAD_AGREE` | + requires the top cluster to agree on `answer_field` | **the proposed repair** |
| `ROOT_NOVELTY` | provenance-root first-seen only | mechanism-free — distrust a brand-new corroborating source |
| `EXACT_DUP` | flags trajectory+semantic exact duplicates | mechanism-free — the attack requires an exact copy |
| `SEMANTIC_AGREE` | requires top-cluster semantic agreement | mechanism-free — the `PAYLOAD_COUPLED` competitor |
| `RANDOM_REJECT` | rejects at the same rate, at random | **volume control** — a win must not come from rejecting more |
| `ORACLE_TRUTH` | the forgery labels | ceiling, never a method |

`ROOT_NOVELTY` and `EXACT_DUP` are the ones that worry me. **The attack requires an exact
trajectory copy** — measured: at edit distance ≥ 1 the forgery falls outside the top cluster and
is excluded anyway. **So an exact-duplicate check might kill it without reading the payload at
all**, and if it does, the payload check is not the story.

## 6. Preconditions — checked and reported before any arm is scored

- **`GATE_ATTACK_WORKS`** — `VERIFIER_ASIS` must authorize forgeries at a material rate. If the
  hole does not reproduce at scale, there is nothing to repair and no status is emitted.
- **`GATE_LEGIT_CORROBORATION_EXISTS`** — genuine multi-source corroboration must exist and be
  authorized in the unrepaired verifier. Otherwise "no collateral" is **vacuous**: you cannot
  damage what was never working. RGM-0.2's `authorized_empty_rate = 1.000` is the precedent.
- **`GATE_PAYLOAD_NOT_RECOVERABLE`** — in `PAYLOAD_INDEPENDENT`, payload must **not** be
  predictable from semantics, trajectory or context above chance. Measured directly. If it is
  recoverable, that regime is not independent and its result is void.
- **`GATE_MECHANISM_FREE`** — no cheap statistic identifies the forgeries. Given the CMB-RP0
  finding that **forgery ids leaked through link tie-breaking**, forgery ids are drawn from the
  **same namespace as real memories** (`m####`, interleaved), and the check explicitly includes
  id rank, insertion order, degree, trajectory length, and both vector norms.

## 7. Status vocabulary

```
CORROBORATION_PAYLOAD_DEFECT_CONFIRMED   the hole reproduces at scale
PAYLOAD_CHECK_REPAIRS_IT                 attack -> 0, no material collateral, and it BEATS
                                         the mechanism-free competitors
PAYLOAD_CHECK_REDUNDANT                  a cheaper check (root novelty, exact-duplicate,
                                         semantic agreement) does the same job
PAYLOAD_CHECK_HAS_COLLATERAL             it kills the attack AND legitimate corroboration
STRUCTURAL_RESISTANCE                    the attack survives the payload check
STATUS_NOT_EMITTED                       a precondition failed
```

`PAYLOAD_CHECK_REDUNDANT` is a **likely and acceptable** outcome. It would mean the correct fix
is an exact-duplicate or root-novelty rule, and the payload framing — **my framing** — was the
wrong lens.

## 8. A live bug this bench forces us to fix

`V2.is_correct` reads `.get("answer")` while `_mk_memory` writes `"answer_field"`, so it returns
`False` for a known-correct memory. Recorded in CMB-RP0 A3 as *latent* because nothing called
it. **It is the natural helper for `PAYLOAD_AGREE`, so it stops being latent here.** It is fixed
as part of building CPB-0, with a unit assertion, and the fix is recorded as a change to a
shared module rather than smuggled in.

## 9. Governance

- **Worlds:** a fresh block, asserted disjoint from `0–19`, `500–511`, `700–708`, and the
  `750+` / `800+` probe ranges.
- **Stage 1:** CPU, `$0`, no model. String similarity and small graph algebra, as RGM-0.2 was.
- **Stage 2 — does an authorized forgery actually cause harm?** **NOT part of this design and
  not requested.** Authorization is not damage, and proving damage needs training, which needs
  the interlock and its own authorization.
- **Uncertainty:** paired permutation, `N_PERM = 10000`, margin from a measured null on dev
  worlds only. Attack success and collateral are **counts**, which is the regime where CMB-RP0
  was decisive and its capability half was not.
- **No claim promotion** without an independent audit by someone who did not build this.
- **No automatic second repair.**

## 10. This design has NOT been attacked yet

Every design in this lane that went straight to construction carried a shortcut. **CMB-RP1 was
retired by its own design review at `$0`, and the review found the fifth shortcut in the
preregistration I had just committed.** CPB-0 gets the same treatment before a line is written.

**Two things I already expect an attacker to say, registered so they cannot be presented as
novel later:**

1. *"`EXACT_DUP` kills it without any payload reasoning, so the whole framing is wrong."* — very
   possibly correct, and `PAYLOAD_CHECK_REDUNDANT` exists for it.
2. *"Assigning payloads changes the corpus, and a new generator is a new shortcut surface."* —
   correct, which is why `GATE_MECHANISM_FREE` explicitly covers id rank and insertion order
   this time.
