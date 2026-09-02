# DEFERRED BUILD + TRIGGER — defence against STRUCTURAL forgery

**Status:** `DEFERRED — NOT BUILT — NOT AUTHORIZED`
**Registered:** 2026-09-02, on owner instruction, after the CMB-RP0 lane closed.
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
Neither measured defence sees it. Nothing in this program has tested that case, and nothing here
claims it is reachable or unreachable — only that it is **not covered**.

## 2. Why this was deferred rather than built

The owner's standing rule is `No automatic second repair`. In this lane a repair manufactured
the next problem **four times**. Building a combined defence immediately after measuring the gap
would be the fifth instance of exactly that pattern.

It is also not needed yet. The gap only bites under conditions that do not currently hold — and
those conditions are what this trigger watches.

## 3. THE TRIGGER

### Automatic conditions — computed from a corpus, not judged

**`T1` BAND COLLISION.** RGM-0.2 §6 disclosed that the contradiction band `[0.80, 0.99)` is
calibrated on a corpus where the legitimate and forgery populations **do not overlap at all**:
`0 of 3794` legitimate fragment pairs fell inside it. A real corpus with legitimate
near-duplicates at `0.85` would collide, and the verifier would start blocking **truth**.

> **Fires when:** more than `0.5%` of legitimate memory pairs have trajectory similarity in
> `[0.80, 0.99)`.

**`T2` STRUCTURAL SIGNAL LOST.** CMB-RP0 measured that a degree filter beats the verifier on
bulk forgery because a one-item forgery is low-degree (`4.89` against `6.67`). That cheap
defence is a property of *this* attack, not a general fact. An attacker who matches degree, or
bulk forgeries that accumulate links over time, erases it — and **the verifier does not cover
what the degree filter was covering.**

> **Fires when:** a single-threshold degree classifier separates known forgeries from real
> memories at `AUC < 0.65`.

**`T3` SCALE PAST REVIEW.** Individual review of writes stops being possible.

> **Fires when:** the store exceeds `10,000` memories, or `500` writes/day. (Owner-adjustable.)

### Declared conditions — facts about deployment, owner-set

**`T4` UNTRUSTED WRITE PATH.** Any memory write that is not first-party and reviewed —
external ingestion, multiple users, or agent-authored memories.

**`T5` MEMORY FEEDS TRAINING.** Memory contents enter fine-tuning or replay rather than only
display. **This is the axis that converts a retrieval mistake into a weights mistake**, and it
is the entire reason CMB-RP0 was built: a wrong memory shown to a user can be dismissed; a
forgery in a training batch is written into the weights and cannot be taken back.

**`T6` OBSERVABLE THRESHOLDS.** A party who can write memories can observe or infer the
verifier's thresholds — which is what makes the adaptive attack cheap rather than expensive.

### FIRING RULE

```
NECESSARY   T5 AND (T1 OR T2)
              memory feeds training, AND one of the two defences has lost its footing

URGENT      NECESSARY AND (T4 OR T6)
              ... and there is an actual adversary write-path

WATCH       any single condition met, firing rule not yet satisfied

DORMANT     nothing met
```

**Unknown is not "no".** Any condition the checker cannot evaluate is reported `UNKNOWN`, and an
`UNKNOWN` on `T1` or `T2` while `T5` holds escalates to `WATCH_UNRESOLVED`, which requires a
human decision rather than passing silently. This program has been burned by silent passes.

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
   If neither defence nor their combination catches it, that is the honest finding, and it must
   be reportable as such.

**Known trap, recorded in advance:** the combination will be tempting to report as "defence in
depth" the moment it beats either component alone. It is not, unless it beats **the best
mechanism-free competitor on both axes at once** — the standing rule that a win by mechanism M
is uninterpretable until it beats the cheapest method without M.

## 5. How the trigger actually fires

Honest about the mechanism, because a note nobody reads is not a trigger:

1. **`docs/CAS_HARNESS_SPEC_SHEET.md` carries a row pointing here.** `CLAUDE.md` mandates
   reading that sheet **before any CAS Harness work**, so any agent starting harness work meets
   this record.
2. **`check_structural_trigger.py` evaluates the conditions.** Run it against a corpus and a
   declared-flags file; it prints the state and exits non-zero on `NECESSARY` or `URGENT` so it
   can gate a pipeline.
3. **It is a checkpoint, not a daemon.** Nothing here polls. If the owner wants a periodic
   check, that is a scheduled task and is the owner's to authorize — it has not been created.

## 6. What this record does NOT do

- It does **not** license building the structural defence.
- It does **not** claim the uncovered case is reachable, or that any real system faces it.
- It does **not** change any status. RGM-0.2 stands at `ADMISSION_SAFETY_REPAIRED`; CMB-RP0
  stands at `TWO_TIER_GATE_EARNS_NOTHING` / `NOT_PROMOTABLE`.

Provenance: `cas_only_reasoner/CMB_RP0_v0_1/CMB_RP0_FINDINGS.md` §13,
`cas_only_reasoner/CMB_R1_v0.2/RGM02_FINDINGS.md` §10, GLM audit finding 3.
