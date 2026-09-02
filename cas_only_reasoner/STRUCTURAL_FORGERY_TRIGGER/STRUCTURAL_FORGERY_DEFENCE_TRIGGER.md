# DEFERRED BUILD + TRIGGER — defence against STRUCTURAL forgery

**Status:** `DEFERRED — NOT BUILT — NOT AUTHORIZED`
**Registered:** 2026-09-02. **Owner rulings 2026-09-02 applied — Fixes A–D, then v0.3
job-scoping.**
**Self-validated:** `validate_trigger.py` — **25 scenarios, all PASS**.
**Externally validated:** `run_external_fixtures.py` — **75 spec-only fixtures from 8 independent authors who never read the implementation**; 64 match, 11
diverge, every divergence triaged in §8.
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

### THE INTERLOCK IS NOW BUILT — `replay_training_gate.py`

The five steps above are no longer a procedure a launcher is asked to follow correctly. They are
a module it calls:

```python
from replay_training_gate import require_clearance, bind_into_receipt, TrainingBlocked

clearance = require_clearance(               # steps 1-4; raises TrainingBlocked on any block
    job_id="CMB-RP1",
    pipeline_config=<the config YOUR PIPELINE EMITTED>,
    corpus_path=<the memory snapshot being replayed>,
    declared_owner=..., source_commit=..., timestamp=...)
... load the model, train ...
receipt = bind_into_receipt(receipt, clearance)      # step 5; refuses without a real clearance
```

**The launcher never writes a manifest.** It hands over the config its pipeline emitted, and the
manifest is *derived* from it — so there is no hand-editable boolean anywhere on the path. The
pipeline is the fact; the claim is now generated from the fact rather than asserted beside it.

`validate_gate.py` proves the wiring, and its load-bearing assertion is not "an exception was
raised" but **"the trainer function never executed"**:

```
memory feeds training, NO corpus     WATCH_UNRESOLVED  10   trainer ran: False
band collision                       NECESSARY         20   trainer ran: False
degree signal gone                   NECESSARY         20   trainer ran: False
scale + fired defence                URGENT            30   trainer ran: False
scale raised, no acknowledgement     WATCH              5   trainer ran: False
healthy corpus, training on          CLEAR              0   trainer ran: True, receipt bound
pipeline says training OFF           DORMANT            0   trainer ran: True
WATCH + ack bound to this job        WATCH_ACKNOWLEDGED 0   trainer ran: True
WATCH + ack for a DIFFERENT job      WATCH              5   trainer ran: False
```

**THE LIMIT, STATED PLAINLY.** This defends against **mistake**, not against a launcher that
deliberately lies about itself. `bind_into_receipt` re-reads the trigger's own receipt file and
checks state, digest and exit code against the clearance handed to it — so a forged clearance
must also forge that file, and both cases are tested — but **a launcher that controls its own
source can always skip the call entirely. You cannot stop code from lying about whether it ran a
check.**

What it does buy: the correct path is the easy path; a run receipt without a clearance is
*visibly incomplete* and an auditor can grep for it; and every blocking state provably stops the
trainer. The residual assurance is **procedural, not technical** — the receipt must carry the
clearance, and an auditor must check it.

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

---

## 8. CONFORMANCE CONTRACT — written because eight independent readers disagreed with the code

GLM audit finding 1 on `2625337f`: *"The suite is the checker validating itself… add an external
negative corpus — fixtures generated by someone other than the checker's author — so the
validator cannot share a blind spot with the code it tests."*

Eight parties read **this document only**, never the implementation or the existing suite, and
each **predicted** a state and exit code before anything ran. 75 fixtures. **64 matched, 11
diverged.** Every divergence below is a place where an honest reader of the specification would
have built something different from what the code does. Each is now resolved **in the
specification**, so the ambiguity cannot be inherited by a future launcher.

### 8.1 One real defect, found and fixed

**An exit code outside the frozen ladder.** Fixture `SB06` passed an unrecognised
`--expected-scope` value. `argparse` rejected it and exited **`2`** — a code the frozen contract
does not define, in the same commit whose spec-sheet row says a launcher *"must not be able to
reinterpret an exit code"*.

**Fixed:** every invocation error — unknown scope value, unknown flag, malformed arguments —
now returns **`REFUSED` / exit `10`**. `exit 2` is no longer reachable. A caller switching on the
documented codes can no longer meet an undocumented one.

### 8.2 `T1` similarity was undefined — three divergences, one root cause

Fixtures `t3_escalates_necessary_to_urgent`, `t1_fired_but_t2_unknown` and
`valid_ack_must_not_clear_necessary_or_urgent` all built pairs they believed were inside the
band, and all measured **0 in-band pairs**. Their authors assumed **cosine similarity** on
trajectory vectors. The implementation uses **edit distance**. The spec said only *"trajectory
similarity"*.

**This is the finding an author-written suite structurally cannot produce**, because the author
would have used the same metric in the fixtures as in the code.

> **NORMATIVE:** `T1` similarity is
> `1 − levenshtein(a, b) / max(len(a), len(b))`, over the raw `trajectory` sequences.
> Identical sequences score `1.0` and are therefore **outside** the band, whose upper end
> `0.99` is exclusive.

**THE METRIC AND ITS THRESHOLDS ARE ONE CALIBRATION PACKAGE (owner ruling 2026-09-02).**

Edit distance is not an arbitrary pick among reasonable similarity measures. **Every threshold
in this trigger was calibrated with it**, on populations measured with it:

```
contradiction band            0.80 to 0.99
legitimate collateral          0 of 3794     (no legitimate pair falls in the band)
forgery pairs                 54 of 108
```

Swapping in cosine similarity would leave `0.80` and `0.99` as **ungrounded numbers** — the same
digits measuring a different quantity, against populations nobody has re-measured.

> **NORMATIVE:** Any future change to `T1`'s similarity metric is a **RECALIBRATION EVENT**
> requiring new population measurements. **Thresholds may NEVER be carried across metrics
> unchanged.** It is not a spelling correction and it is not code cleanup — it is a new
> measurement event, and it needs an owner ruling and a dated spec-sheet row like any other.

### 8.3 The acknowledgement format was undefined — the only path from blocking to exit 0

Fixture `watch_ack_bound_to_job_and_digest` supplied a perfectly reasonable ack and was refused.
Its author invented `{job_id, config_digest, acknowledged_by, timestamp}`; the implementation
requires `acknowledges` and `manifest_digest`. Their note is the correct criticism:

> *"WATCH_ACKNOWLEDGED is the only path from a blocking state to exit 0, and it is the least
> specified thing in the document."*

> **NORMATIVE — acknowledgement file, passed with `--watch-ack`:**
> ```json
> {
>   "acknowledges": "WATCH",
>   "job_id": "<or deployment_id, matching the manifest's scope>",
>   "manifest_digest": "<the manifest's config_digest, exactly>",
>   "acknowledged_by": "<a person>"
> }
> ```
> All four are required. `acknowledges` must be the literal `"WATCH"`. An ack is valid **only**
> for the state `WATCH`: it can never clear `NECESSARY`, `URGENT`, `WATCH_UNRESOLVED` or
> `REFUSED`. Both of those non-clearing cases are covered by passing fixtures.

### 8.4 Ladder resolution order — stated, because the rows are not mutually exclusive

An author observed that `T5` true with `T1` fired and `T2` unknown satisfies **both**
`WATCH_UNRESOLVED` and `NECESSARY`, and the document never said which wins.

> **NORMATIVE, evaluated in this order:**
> 1. **`REFUSED` is a precondition gate, not a ladder row.** If the manifest does not govern
>    this job, nothing in it is read and no condition is evaluated.
> 2. `T5` unknown → `WATCH_UNRESOLVED`. We may not conclude *memory does not feed training*.
> 3. `T5` false → `DORMANT`, regardless of any other fired condition. The trigger is
>    training-scoped by design.
> 4. **A FIRED defence beats an UNKNOWN one** → `NECESSARY`, escalating to `URGENT`.
> 5. Only then, an unknown defence → `WATCH_UNRESOLVED`.
> 6. Only then, a raiser → `WATCH`.

### 8.5 State names at the same exit code — resolved for the receipt's sake

Four divergences (`SB06`, and the three malformed-`--pipeline-config` cases) agreed on **exit
`10`** and disagreed only on the state string. The exit was never at risk; the receipt's wording
was.

> **NORMATIVE:** an unrecognised scope, and a `--pipeline-config` whose
> `memory_feeds_training` is absent, null, or not a boolean, are **`REFUSED`** — the manifest's
> claim of derivation cannot be verified, so it does not govern the job. `REFUSED` is for *this
> manifest cannot speak here*; `WATCH_UNRESOLVED` is for *a fact could not be established*.

### 8.6 Empty evidence is UNKNOWN, not clear

`t1_every_group_has_exactly_one_member` produces **no legitimate pairs at all**. Its author
predicted `CLEAR` — nothing in band, so nothing fires. The implementation returns `UNKNOWN`.

> **NORMATIVE:** a corpus that yields **no evaluable pairs** for `T1`, or **no `is_forgery`
> labels** for `T2`, is `UNKNOWN`, not clear. Zero measurements is not a measurement of zero.
> Consistent with `UNKNOWN IS NOT "NO"`.

### 8.7 Also normative, from the authors' notes

- **`T1` denominator:** pairs **within** a `legitimate_group`. Memories with no group, and any
  `is_forgery` memory, are excluded.
- **Pipeline config shape:** a JSON object with a boolean `memory_feeds_training` at top level,
  **emitted by the pipeline**, never hand-written. The same key in both scopes.
- **Scale keys:** `n_memories` **or** `memory_count` are both read, plus `writes_per_day`; the
  corpus and the manifest are both read and **the larger wins**.
- **`derivation: "declared"` is legal in `DEVELOPMENT_REPLAY`.** Only an unverifiable
  `derived_from_pipeline_config` claim is refused.
- **`T6` observable thresholds** means: a party who can write memories can learn the verifier's
  numeric thresholds — by documentation, by observing accept/reject boundaries, or by reading
  the code — making an adaptive forgery cheap rather than expensive.

### 8.8 Three fixture errors, recorded rather than hidden

Not every divergence was the code's fault, and saying so is part of the record:
`t2_boundary_exact_065_forward` predicted a fire at **exactly** `0.65` when the spec says
`< 0.65` (its author's own reverse-direction twin predicted correctly);
`dormancy_dominates_fired_t1_t3_t4_t6` carried a prediction contradicting its own rationale,
**which its author disclosed unprompted before submitting**; and the three `T1` cases in §8.2
mispredicted for the metric reason, which is the spec's fault, not theirs.

### 8.9 Standing rule

**`run_external_fixtures.py` runs alongside `validate_trigger.py`.** The author's suite proves
the code does what its author meant. The external suite proves the code does what *the
specification says*. **A future change must keep both green**, and a new divergence is a finding
in one or the other — never something to reconcile by editing the prediction to match the code.
