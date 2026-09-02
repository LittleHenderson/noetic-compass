# CMB-RP1 — `DO_NOT_BUILD`. Retired before construction, `$0` spent.

**Design committed `6037628a`, attacked immediately, retired the same day. Nothing built, nothing
run, no world touched, `$0`.**

Six adversarial lanes attacked the frozen design. **I re-verified every consequential claim
myself before accepting it** — two of them retract statements I wrote in documents that have
since been audited and passed.

---

## 1. The verdict, and the two independent reasons

**`DO_NOT_BUILD`.** Either reason alone is sufficient.

### Reason 1 — the curve the bench measures cannot exist on this corpus

`traj_sim = 1 − levenshtein/max(len)` over trajectories of length **3 to 6** can take only
**thirteen values**:

```
0, .1667, .2, .25, .3333, .4, .5, .6, .6667, .75, .8, .8333, 1.0
```

The contradiction band `[0.80, 0.99)` is reachable by exactly **two** of them — `0.8` and
`0.8333` — both requiring Levenshtein distance of exactly **1**.

Every forgery in this family copies a stored trajectory, so the top coherence cluster sits at
`1.0`. The next attainable value down is `0.8333`, a gap of `0.1667`, against `DELTA = 0.08`.
**So any forgery at edit distance ≥ 1 is outside the top cluster by construction, and any
forgery at edit distance 0 is inside it.** The verifier's exclusion rate is a **two-valued step
function of one integer**, not a curve.

**α has no interior to move through.** The design's own registered falsifier — *"either curve is
flat"* — fires before a single world is run.

### Reason 2 — the diagnostic is misattributed, so the bench tests a mechanism that never runs

Measured on the registered near-miss attack, 30 queries across three probe worlds:

```
cond_consistent  FIRED (blocked):   0 / 30
cond_absolute    FIRED (blocked):   0 / 30
cond_relative    FIRED (blocked):   0 / 30
```

And the ablation, authorized memories summed over all 30 queries:

| configuration | FALSE (forgeries) | TRUE (real) |
|---|---|---|
| all conditions ON | **0** | 90 |
| **consistency OFF** | **0** | **90** |
| relative margin OFF (`delta = 1e9`) | 1 | 3 |
| both OFF | **30** | 90 |

**Turning the contradiction band off changes nothing — not one forgery, not one true memory.**
The forgeries are excluded because they sit `0.1667` below the top cluster, which exceeds
`DELTA = 0.08`. **Consistency never sees them.**

## 2. What this retracts — RGM-0.2

**THE NUMBERS STAND.** `ADMISSION_SAFETY_REPAIRED`, near-miss authorized `119 → 0`, `358` true
memories kept, and GLM's byte-identical re-execution are all unaffected. Nothing measured
changes.

**THE EXPLANATION DOES NOT STAND.** `RGM02_FINDINGS.md` §4 records this as a self-correction:

> *"I claimed the RELATIVE MARGIN was load-bearing. It is not… Consistency is what holds the
> line."*

and §5 calls the contradiction band *"the load-bearing idea in this repair."*

**Measured: on the registered attack that produced `119 → 0`, the relative margin is what holds
the line, and the contradiction band contributes nothing.**

How I got it backwards: my self-correction was drawn from an **adaptive** forgery I constructed
at coherence `0.9375`. That value sits **inside** `DELTA` of `1.0` (gap `0.0625 < 0.08`), so for
*that* forgery the cluster separation cannot help and consistency is the only thing left. Both
observations are true — **of different attacks.** I generalised from the adaptive case I built
to the headline number, which comes from an attack the band never touches.

**The corrected statement:** the contradiction band's demonstrated value is confined to an
adaptive forgery constructed to defeat the other two conditions. It is inert on every registered
attack in the corpus.

## 3. What this qualifies — CMB-RP0

**THE RESULT STANDS.** `TWO_TIER_GATE_EARNS_NOTHING`, the two-tier gap of `−0.33`, and the three
capability losses at 0 of 9 worlds are unaffected.

**THE `DEGREE_FILTER` HEADLINE NEEDS A NOTE.** The link rule breaks `traj_sim` ties by
**ascending `memory_id`**. Ties are pervasive, because there are only 13 attainable similarity
values. So an id that sorts early gets chosen as a neighbour by more memories.

Same world, same trajectories, same semantics, **only the id prefix changed:**

| forgery id prefix | forgery degree | real degree | separability |
|---|---|---|---|
| `poison_` *(what CMB-RP0 used)* | 4.90 | 6.55 | 0.6811 |
| `zzzF` | 4.90 | 6.55 | 0.6811 |
| `m9F` | 4.90 | 6.55 | 0.6811 |
| **`aaaF`** | **7.03** | **6.48** | **0.5049** |

**An early-sorting prefix erases the signal and inverts the sign.** CMB-RP0's finding that a
degree count (`4.41`) beat the verifier (`5.67`) is therefore **corpus- and naming-specific**,
not a general property of one-item forgeries. It stands as measured and must carry this note.

## 4. What the review produced for free — the uncovered case is trivially constructible

The design proposed a Stage 1 search for a forgery evading both defences. **It exists, it takes
one line, and it is not exotic.**

An **exact copy** of a stored memory's trajectory and semantics, with a **fresh provenance
root** and a **wrong answer**:

```
forgeries AUTHORIZED:  20 / 20
```

The verifier reads it as **corroboration** — exactly as `cmb_r1_v02_core.py` documents:
*"Identical copies CORROBORATE and are fine."*

**The real hole this exposes: corroboration is judged on the fields the query matches
(trajectory, context), not on the payload that would be acted upon (`answer_field`).** Two
memories can agree perfectly on everything the verifier reads while disagreeing completely on
what they assert. Provenance-root deduplication is the only thing standing between that and mass
authorization, and an attacker who can write a memory chooses its root.

This sits at edit distance **0**, which is **outside** the α range the design would have
searched — the family was parameterised in the wrong direction to find it.

## 5. The fifth shortcut, as predicted

`GATE_ALPHA_IS_REAL` is passable by a quantity the mechanism never reads. It demands that
"contradiction-band membership" vary with α — and band membership does vary, while the
verifier's actual decision variable (`cond_consistent`) is `0.00` at every α. **A gate that can
be passed by a number with zero influence on any arm is the same defect class as the previous
four**, and it was in the design I had just committed.

## 6. What happens now — and what deliberately does not

- **CMB-RP1 is retired as designed.** Not redesigned. Redesigning it immediately is exactly the
  *"automatic second repair"* pattern that produced three of the four earlier shortcuts.
- **The diagnostic is WITHDRAWN, not "falsified by a bench".** It was withdrawn by inspection at
  `$0`, which is the cheapest possible outcome and the one the design review existed to produce.
- **Two audited documents get corrections, not retractions.** Every measured number in RGM-0.2
  and CMB-RP0 stands. Two explanations attached to those numbers do not.
- **No new bench is proposed here.** If the owner wants one, the honest candidate is now obvious
  and much narrower than CMB-RP1: *corroboration is judged on the matched fields, not the
  payload* — but proposing it is not the same as authorizing it.

## 7. Cost

```
design written           $0
six-lane adversarial attack   $0  (local CPU)
builder re-verification       $0  (local CPU)
worlds touched                none registered; probes used 802-806
TOTAL                    $0
```

**A design that would have consumed a GPU run and produced an uninterpretable flat curve was
retired for nothing, and it took two audited claims down with it on the way out.**
