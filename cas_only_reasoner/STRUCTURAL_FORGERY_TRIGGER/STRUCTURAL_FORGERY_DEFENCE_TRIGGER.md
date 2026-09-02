# DEFERRED BUILD + TRIGGER — defence against STRUCTURAL forgery

**Status:** `DEFERRED — NOT BUILT — NOT AUTHORIZED`
**Registered:** 2026-09-02. **Owner rulings 2026-09-02 applied — Fixes A–D, then v0.3
job-scoping.**
**Self-validated:** `validate_trigger.py` — **25 scenarios, all PASS**.
**Trigger state:** run `check_structural_trigger.py`. Do not trust this file's prose for the
current state — the script reads the actual conditions.

---

## 1. What is missing, in one paragraph

Two defences have now been measured against two different attacks, and each covers exactly what
the other does not:

| | RGM-0.2 (admission) | CMB-RP0 (replay) |
|---|---|---|
| attack | **one adaptive** forgery, built at `0.9375` to sit above the bar and inside the margin | **132 cheap** lev-1 forgeries |
| defeated by | **consistency** — the top cluster must agree with itself | **graph degree** — a one-item forgery has fewer edges |
| the verifier | `119 → 0` false authorizations, `358` true kept — **earns itself** | ingests `5.67`; a degree count ingests `4.41` — **adds nothing** |

**The two-tier verifier detects semantic contradiction. It does not detect structural anomaly.**

**The uncovered case is a forgery that is BOTH semantically consistent AND structurally normal.**
Neither measured defence sees it. Nothing here claims that case is reachable or unreachable —
only that it is **not covered**.

## 2. Why this was deferred rather than built

The owner's standing rule is `No automatic second repair`. In this lane a repair manufactured
the next problem **four times**. Building a combined defence immediately after measuring the gap
would be the fifth instance of exactly that pattern.

It is also not needed yet. The gap only bites under conditions that do not currently hold — and
those conditions are what this trigger watches.

## 3. THE TRIGGER

### Automatic conditions — computed, not judged

**`T1` BAND COLLISION.** RGM-0.2 §6 disclosed that the contradiction band `[0.80, 0.99)` is
calibrated on a corpus where the legitimate and forgery populations **do not overlap at all**:
`0 of 3794` legitimate fragment pairs fell inside it. A real corpus with legitimate
near-duplicates at `0.85` would collide, and the verifier would start blocking **truth**.

> **Fires when:** more than `0.5%` of legitimate memory pairs have trajectory similarity in
> `[0.80, 0.99)`.

**`T2` STRUCTURAL SIGNAL LOST — DIRECTION-FREE (Fix A).** CMB-RP0 measured that a degree filter
beats the verifier on bulk forgery because a one-item forgery is low-degree (`4.89` against
`6.67`). That is a property of *that* attack, not a general fact.

> **Separability** = `max(AUC, 1 − AUC)`. `0.50` = none; `1.00` = perfect **in either direction**.
> **Fires when:** separability `< 0.65`.

Direction matters, and the original specification sentence hid it. An `AUC` of `0.10` is
*excellent* reverse-direction separation — forgeries as hubs rather than isolates — and a rule
written "`AUC < 0.65`" would have raised an alarm on a perfectly healthy signal. **The code
always computed `max(AUC, 1−AUC)`; the specification sentence was the defect.** The checker now
prints separability first so the ambiguity cannot recur, and the self-test includes a
reverse-direction corpus.

**`T3` SCALE PAST REVIEW.** Individual review of writes stops being credible.

> **Fires when:** `> 10,000` memories, or `> 500` writes/day.
> **Scale is read from BOTH the corpus and the manifest, and the LARGER wins.** A supplied
> corpus is a *sample*; the manifest declares the *deployment*. Reading only the corpus let an
> 80-memory synthetic sample override a declared 50,000-memory deployment, so `T3` could not
> fire in the one case it exists for — found by the self-test, not by reading.

### Declared conditions — from an authoritative, SCOPE-BOUND manifest (Fix D + v0.3)

**`T4` UNTRUSTED WRITE PATH** · **`T5` MEMORY FEEDS TRAINING** ·
**`T6` OBSERVABLE THRESHOLDS**

`T5` is the axis that converts a retrieval mistake into a **weights** mistake, and it is the
whole reason CMB-RP0 existed: a wrong memory shown to a user can be dismissed; a forgery in a
training batch is written into the weights and cannot be taken back.

**These are SCOPE-BOUND, and they are not ordinary editable booleans.** A manifest declares a
`scope`, and the flag names differ by scope so one file cannot be repurposed across the boundary
by editing a single field:

| scope | id field | flag names |
|---|---|---|
| `PRODUCTION_DEPLOYMENT` | `deployment_id` | `production_memory_feeds_training`, … |
| `DEVELOPMENT_REPLAY` | `job_id` | `memory_feeds_training`, … |

Every manifest must carry:

```
schema_version   scope   <deployment_id | job_id>   config_digest
declared_owner   timestamp   source_commit   derivation
```

`config_digest` must equal the SHA-256 of the manifest's own non-underscore fields (excluding
itself). A tampered digest is an authority failure and blocks.

**A missing, malformed, mis-scoped, or non-boolean manifest yields `UNKNOWN`, never `False`.**
A deleted or corrupted file must not read as "everything is safe".

`derivation` is `declared` or `derived_from_pipeline_config`. **Owner target state:
`production_memory_feeds_training` should be DERIVED from the pipeline configuration, not
hand-declared.** It is `declared` today only because no production pipeline exists to derive it
from.

**Why production scope is explicit:** CMB-RP0 *did* place retrieved memories into training.
That is recorded separately as `development_memory_feeds_training = true` in
`CMB_RP0_v0_1/DEVELOPMENT_MEMORY_TRAINING_NOTE.md`. So the trigger's dormancy is honest and says
exactly this: **the experimental replay bench used memory in training, but no deployed system
currently does.**

### THE STATE LADDER (Fix B) and EXIT CODES (Fix C)

```
DORMANT              not T5                                            exit  0
CLEAR                T5, both defences healthy, no raiser              exit  0
WATCH_ACKNOWLEDGED   WATCH + an owner ack BOUND TO THIS JOB            exit  0
WATCH                T5, defences healthy, and any of T3 / T4 / T6     exit  5   BLOCKS
WATCH_UNRESOLVED     T5 unknown, OR T5 and (T1 or T2) unknown          exit 10   BLOCKS
REFUSED              manifest does not govern this job                 exit 10   BLOCKS
NECESSARY            T5 and (T1 or T2)                                 exit 20   BLOCKS
URGENT               NECESSARY and (T3 or T4 or T6)                    exit 30   BLOCKS
```

**For any memory-to-training job, EVERY NONZERO CODE BLOCKS LAUNCH.**

**`WATCH` is no longer a silent green (v0.3).** An untrusted write path, a large store, or
observable thresholds do not prove the defences have failed — but they must not disappear into
an ordinary zero exit either. `WATCH` passes only with an **owner acknowledgement bound to this
job's id AND this manifest's digest**. A standing waiver, or an ack for another job, does not
clear it.

`T3` now has real authority: scale cannot by itself prove the defences have failed, but it makes
manual review less credible and **escalates `NECESSARY` to `URGENT`**. Previously it appeared in
the condition list and in **no** decision path — decorative.

**`UNKNOWN` IS NOT `NO`, and it now stops the machinery rather than printing a warning.** If
`T5` itself cannot be established, the state is `WATCH_UNRESOLVED`, not `DORMANT` — we may not
conclude "memory does not feed training" from an absent manifest.

### SCOPE AND JOB BINDING (v0.3) — the gap that mattered most

A `PRODUCTION_DEPLOYMENT` manifest saying *no production system feeds training* returns
`DORMANT`. That is **true**, and it is **useless** as clearance for a development replay job
that really does put retrieved memories into training.

> Without this fix, the checker would truthfully report that the empty production building is
> safe while the experimental workshop next door is running the furnace.

The launcher must now declare what it is launching, and the checker **refuses** a manifest that
does not govern it:

```
--expected-scope    scope the LAUNCHER declares; a mismatch is REFUSED
--job-id            job id the LAUNCHER declares; a mismatch is REFUSED
--pipeline-config   config EMITTED BY THE PIPELINE; memory_feeds_training is DERIVED from it,
                    and a manifest that disagrees is REFUSED
```

**Refused, every one demonstrated in the self-test:**

- a `PRODUCTION_DEPLOYMENT` manifest used to authorize a `DEVELOPMENT_REPLAY` job
- a `DEVELOPMENT_REPLAY` manifest used to authorize production
- a manifest whose `job_id` does not match the launcher's
- `derivation: derived_from_pipeline_config` with **no pipeline config supplied to verify it**
- a declared `memory_feeds_training` that **disagrees with the pipeline configuration**

The last is the important one: **the pipeline is the fact; the manifest is a claim about it.**
Nobody should obtain a clear result by editing a boolean.

## 4. What gets built when it fires — scope, NOT authorization

Registered so the scope cannot drift later. **None of this is authorized.** It needs its own
preregistration, its own mechanism-free baselines, and its own owner authorization.

1. A **structural-anomaly check** over the memory graph, sitting beside the semantic verifier
   rather than inside it — they answer different questions and must fail independently.
2. Its own **mechanism-free competitors registered before any run**. `DEGREE_FILTER` is the
   floor to beat; a structural check that does not beat plain degree is not a mechanism.
3. **An adaptive attacker that matches degree**, because the whole point is the case where the
   cheap statistic has stopped working.
4. **A joint evaluation**: the forgery that is semantically consistent AND structurally normal.
   If neither defence nor their combination catches it, that is the honest finding.

**Known trap, recorded in advance:** the combination will be tempting to report as "defence in
depth" the moment it beats either component alone. It is not, unless it beats **the best
mechanism-free competitor on both axes at once**.

## 5. How the trigger fires — EVENT-DRIVEN, not polled

Owner ruling: **no periodic daemon yet.** A weekly job would currently wake, read
`production_memory_feeds_training = false`, and reprint `DORMANT`. That is ceremony, not
protection.

**This check is MANDATORY at these events:**

```
before any replay-training job
before memory-to-training is enabled
after verifier thresholds change
after memory schema changes
after the write path becomes untrusted
after every registered corpus snapshot
after a major memory-volume threshold is crossed
```

```
before every replay-training launch      after write-path trust changes
before enabling memory-to-training       after major scale thresholds
after verifier logic changes             during deployment release
after threshold changes
after memory schema changes
```

### THE LAUNCH SEQUENCE (required, v0.3)

```
derive the job manifest FROM THE ACTUAL PIPELINE
        |
verify manifest scope, job identity and digest
        |
run the structural-forgery trigger
        |
exit 0                permits launch
exit 5                WATCH -- requires an owner acknowledgement bound to this job
exit 10 / 20 / 30     ABORTS launch
        |
bind the trigger receipt and manifest digest INTO the run receipt
```

```bash
python check_structural_trigger.py \
    --manifest CMB_RP1_JOB_MANIFEST.json \
    --expected-scope DEVELOPMENT_REPLAY --job-id CMB-RP1 \
    --pipeline-config <emitted_by_the_launcher.json> \
    --corpus <snapshot.json> --job pre-training \
    --receipt-out trigger_receipt.json
```

`--receipt-out` writes the machine-readable result — state, exit code, manifest digest and
scope, every condition with its measured detail, and the frozen thresholds — so it can be bound
into the experiment receipt rather than merely printed.

**Until a launcher actually calls this, it is a correctly functioning checker standing beside
the machinery, not an interlock inside it.** That is stated plainly rather than implied.

**Backstop, deferred:** once a real deployment sets `production_memory_feeds_training = true`,
add a weekly remote scheduled run. **Not created — owner's to authorize.**

## 6. Relationship to CMB-RP0 and CMB-RP1

**CMB-RP0 is NOT retrofitted.** It ran and completed under its own frozen protocol, and applying
this trigger to it retroactively would change an experiment after launch. Its result stands
exactly as recorded: `TWO_TIER_GATE_EARNS_NOTHING` / `NOT_PROMOTABLE`.

**This trigger governs successor work and real deployment.**

> **`CMB-RP1` MAY NOT LAUNCH** unless it has **its own `DEVELOPMENT_REPLAY` manifest, derived
> from its actual pipeline configuration and checked**, returning a clear state — **or** the
> structural defence it demands has been implemented and independently audited.

**The current `DORMANT` result MAY NOT be used to clear CMB-RP1.** It is valid for
`scope = PRODUCTION_DEPLOYMENT` only. CMB-RP1 will be a development replay job with
`memory_feeds_training = true`, and presenting the production manifest for it is now `REFUSED`
with exit `10`.

A template is provided at `CMB_RP1_JOB_MANIFEST.TEMPLATE.json`. **It is not an authorization**,
and it is deliberately not valid as it stands — its digest does not match and its `derivation`
forces a pipeline config to be supplied — so it cannot accidentally clear anything.

## 7. What this record does NOT do

- It does **not** license building the structural defence.
- It does **not** claim the uncovered case is reachable, or that any real system faces it.
- It does **not** change any status. RGM-0.2 stands at `ADMISSION_SAFETY_REPAIRED`; CMB-RP0
  stands at `TWO_TIER_GATE_EARNS_NOTHING` / `NOT_PROMOTABLE`.
- It is a **smoke alarm**. It does not stop structural forgery. It says: *the current
  contradiction and degree defences are no longer enough — build or enable the stronger defence
  before memory is allowed to train the model.*

Provenance: `cas_only_reasoner/CMB_RP0_v0_1/CMB_RP0_FINDINGS.md` §13,
`cas_only_reasoner/CMB_R1_v0.2/RGM02_FINDINGS.md` §10, GLM audit finding 3, owner ruling
2026-09-02 (Fixes A–D).
