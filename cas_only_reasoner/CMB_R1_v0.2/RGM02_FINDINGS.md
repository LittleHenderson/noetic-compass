# RGM-0.2 — RESULT: `ADMISSION_SAFETY_REPAIRED`

**Run:** 12 new independent worlds (500–511), CPU, `428.05 s`, **$0**
**Hash:** `b74a16a0e973fced` · receipt `RGM02_RECEIPT.json` · raw `RGM02_RAW.json`
**Builder:** Claude. **Auditor:** a different model, named by the owner. **I do not audit this.**
**Conflict of interest declared** in preregistration §0: I audited RGM-0/0.1 and built RGM-0.2.

```
STATUS                    ADMISSION_SAFETY_REPAIRED
GENERIC GEOMETRY          CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY
                          (survives drop-one)
                          RENAMED by owner ratification 2026-09-02 on GLM finding 2.
                          Legacy name: GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED -- direction-
                          ambiguous, since the generic control WINS 3 of 5 families
                          (-0.010 to -0.025) while CAS wins 2 of 5 (+0.4108, +0.3190).
                          The aggregate survives drop-one ONLY because there are two
                          winners. The committed receipt still carries the LEGACY name
                          and is NOT rewritten -- GLM reproduced it byte-identically and
                          that hash is the determinism proof.
MECHANISM-FREE GATE       PASS -- no query-independent shortcut, answer set not recoverable
ITEMS 5-6                 NOT BUILT (were gated on this result; now unlocked)
```

---

## 1. Items 1 and 2 — admission safety is repaired

12 worlds, 10 attacks of each kind per world, plus the corpus `ECHO` family.

| attack | RGM-0.1 admitted FALSE | RGM-0.2 **RETRIEVED** false | RGM-0.2 **AUTHORIZED** false | AUTHORIZED true |
|---|---|---|---|---|
| classic echo | 0 | 177 | **0** | 816 |
| overlap echo | 0 | 142 | **0** | 349 |
| **near-miss (lev-1)** | **119** | 119 | **0** | 358 |

**The near-miss attack that RGM-0.1 could not stop no longer reaches the tier that can
influence reasoning or learning.** RGM-0.1 admitted one forgery per query (119 over 120
queries — the same rate my audit measured as 359/360). RGM-0.2 authorises **zero**, while
still authorising 358 true memories. Corroboration is preserved, not traded away.

Note the two tiers doing their job: forgeries still appear in `RETRIEVED` (they are plausible
candidates and may be shown), but the separation is what stops them from being *acted on*.

## 2. Item 3 — geometry advantage, re-measured with the control on the identical verifier

| family | D (CAS) | E (generic) | delta | worlds positive |
|---|---|---|---|---|
| LOOKALIKE | 0.9758 | **0.9875** | **−0.0117** | 2/12 |
| ORDER_MATTERS | 0.9680 | **0.9931** | **−0.0251** | 0/12 |
| CROSS_DOMAIN | 0.9777 | **0.9910** | **−0.0133** | 0/12 |
| PATTERN_COMPLETION | **0.4167** | 0.0059 | **+0.4108** | 12/12 |
| INDEPENDENT_CORROB | **0.9818** | 0.6629 | **+0.3190** | 12/12 |
| **all families** | | | **+0.1359** | |
| **worst drop-one** | | | **+0.0672** | **survives** |

**`CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY`** (legacy name `GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED`) — and the honest shape matters more than the
headline:

- **The generic control BEATS CAS geometry on three of five families.** On lookalike, order
  and cross-domain retrieval, the role-coarsened control is *better*, consistently
  (0/12 and 2/12 worlds positive).
- **The advantage is concentrated in exactly two capabilities:** composing fragments
  (`PATTERN_COMPLETION`) and corroborating independent sources (`INDEPENDENT_CORROB`).
- It survives drop-one **because there are two such families**, not one. That is the specific
  weakness I raised against RGM-0.1's resonance gate (a pooled headline one family dominated);
  here, dropping either winner still leaves the other.

**This reproduces the RGM-0.1 shape on 12 new worlds with an un-handicapped control**
(+0.3295 / +0.2975 there, +0.4108 / +0.3190 here, negative on the same three families). My
earlier worry that the advantage might be an artifact of a handicapped control is **refuted** —
and I had already withdrawn the handicap claim itself as factually wrong.

## 3. Item 4 — the mechanism-free gate, run before any arm was scored

| family | semantic-only | popularity | D authorized | D beats semantic-only |
|---|---|---|---|---|
| LOOKALIKE | 0.9444 | 0.0122 | 0.9758 | yes |
| ORDER_MATTERS | 0.8820 | 0.0008 | 0.9680 | yes |
| CROSS_DOMAIN | 0.8280 | 0.0419 | 0.9777 | yes |
| PATTERN_COMPLETION | 0.0005 | 0.0006 | **0.4167** | yes |
| INDEPENDENT_CORROB | 0.3117 | 0.0000 | **0.9818** | yes |

```
answer set recoverable from the graph alone: False
```

**The gate passes**, and it says something the lane had not measured before:

- **No query-independent shortcut.** `popularity` — degree ranking, identical for every query,
  using no query information at all — scores ~0 everywhere. Nothing here is answerable without
  reading the question. The answer set is not recoverable from the graph either.
- **But plain semantic retrieval already reaches 0.83–0.94 on three of five families.** The
  entire geometry-plus-propagation stack adds only 0.03–0.15 there.
- **The machinery earns its keep in exactly two places:** `PATTERN_COMPLETION`
  0.0005 → **0.4167**, and `INDEPENDENT_CORROB` 0.3117 → **0.9818**.

Those two lists are the same two families. **The CAS memory machinery is worth its cost for
composing fragments and for corroborating independent sources, and is not worth much else on
this corpus.** That is a narrower and more useful claim than "CAS geometry helps retrieval".

## 4. Three self-corrections on one verifier — a pattern, not three footnotes

Every one was found by **measurement**, and in each case my reasoning had produced a plausible
wrong answer first.

1. **I claimed the RELATIVE MARGIN was load-bearing.** It is not. An adaptive forgery built at
   0.9375 defeats both the absolute bar and the relative margin; with the contradiction check
   disabled it gets **authorized 20 times**. Consistency is what holds the line.
2. **I blamed the AGREEMENT THRESHOLD for destroying pattern completion** and built a
   contradiction band. The band is right in principle — 0 of 3794 fragment pairs fall in the
   impersonation range 0.80–0.99, while it catches exactly the true-vs-forgery pairs — but it
   **was not the blocker**.
3. **The blocker was the ABSOLUTE BAR `TAU_AUTH = 0.90`**, firing on **33 of 33**
   pattern-completion queries whose best coherence is `0.6944`. And it bought nothing:
   disabling it left the registered attack blocked, and the adaptive forgery sits *above* it.
   Set equal to the floor.

Only after counting which condition actually fired did the cause become clear. **Twice I fixed
the wrong thing.** Recorded so the auditor reads it as a methodological pattern.

## 5. The mechanism, as it now stands

```
RETRIEVED   coherence >= TAU_FLOOR (0.60). May be SHOWN or used as context.
AUTHORIZED  may influence REASONING or LEARNING. Requires:
              - member of the top coherence cluster, separated from the rest by DELTA (0.08)
              - no pair in that cluster inside the IMPERSONATION band [0.80, 0.99)
                  similarity 1.00        CORROBORATION  identical copies    -> allow
                  similarity 0.80-0.99   IMPERSONATION  almost the same     -> BLOCK
                  below 0.80             COMPOSITION    complementary       -> allow
```

**The forgery signature is not "different" — it is "almost the same".** That single
observation is what separates a near-miss attack from legitimate fragment composition, and it
is the load-bearing idea in this repair.

## 6. Disclosed limitations

- **It fails CLOSED under adaptive attack.** When a forgery is built close enough that the
  system cannot distinguish it, **nothing is authorised — true memories included**. Right trade
  for a memory system, but a flood of near-identical forgeries can deny authorisation to
  legitimate memories. That is an availability cost, and it is real.
- **The band edges (0.80, 0.99) are measured on this corpus**, where the two populations do
  not overlap at all. A corpus whose legitimate fragments sit at 0.85 would collide. The band
  is calibrated, not universal.
- **Forgeries still enter `RETRIEVED`** (119 near-miss, 177 classic, 142 overlap). The claim is
  about what may *influence reasoning*, not about what is surfaced.
- **CPU, no neural inference.** String similarity and small graph algebra, so the GPU-only
  compute law does not apply. Stated in the receipt.
- **12 worlds.** Enough for 12/12 and 0/12 patterns to be unambiguous; not a large-sample study.

## 7. What is licensed

> On these 12 independent synthetic memory worlds, a two-tier verifier reduced false
> admission under the lev-1 near-miss attack from 119 authorised forgeries to **zero**, while
> still authorising 358 true memories; and CAS geometry outperformed a matched
> role-coarsened control **on fragment composition and independent corroboration only**,
> losing to it on lookalike, order and cross-domain retrieval.

**NOT licensed:** any CAS-specific or cognition-general claim; any statement that CAS geometry
helps retrieval generally (it loses on 3 of 5 families); any production-memory claim; anything
about replay or forgetting, which were not built.

## 8. Items 5 and 6

**Not built**, per the owner's ordering: *"Build the selective replay selector only after
admission safety passes."* **It now passes**, so they are unlocked — but they are a separate
piece of work and are not started here.

---

## 9. Independent audit — GLM, 2026-09-02: **PASS**

Owner named GLM as the third-party auditor for CMB-P0, CMB-P1, CMB-P2 and RGM-0.2. GLM did
not build any of them (Claude did), so the independence requirement is satisfied.
Report: `tksCAS_audit_workspace/REFERENCE/AUDITS/CMB_P012_RGM02_GLM_AUDIT.md`. Audit spend `$0`.

**Verified by re-execution, not by reading.** GLM re-ran the entire 12-world bench and produced
content hash `b74a16a0e973fced16af7d172d7b502334407116ddf7f561091cf48eeafb7f1f` —
**byte-identical to the committed receipt** — with every headline number matching:
`PATTERN_COMPLETION 0.4167 vs 0.0059` (+0.4108, 12/12), `INDEPENDENT_CORROB +0.3190` (12/12),
drop-one aggregate `+0.1359`, `survives True`, and the shortcut gate's
`answer set recoverable from the graph alone: False`.

GLM's own summary of the durable asset: the admission-safety mechanism is *"the first verifier
in this program that blocks an adaptive forgery by mechanism rather than by threshold."*

### The four findings, and what was done

| # | finding | disposition |
|---|---|---|
| 1 | **12 worlds where the RGM-0.1 audit prescribed ≥20**, no recorded justification. With margin 5× below sd, power is the open question. | 🔒 **OWNER** — accept 12 with the caveat, or authorize the extra worlds. Not the builder's call. |
| 2 | **`GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED` is direction-ambiguous** — a drop-one aggregate hiding a 3-of-5 reversal. | **Headline corrected above** (no status changed). The rename itself is 🔒 **OWNER** — changing a status word on a completed, audited result is a governance act, not a builder edit. Proposed: `CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY`. |
| 3 | **ID_ORDER hazard** (`topic = i % N_TOPICS` + sorted-id coupling, inherited from GLM's own v0.1 core) not exhaustively checked here. No RGM-0.2 result implicated — all arms are score-based. Register the per-world randomized store order and the tie-refuses-status guard in any successor round. | **CLOSED in the successor round.** CMB-RP0 is that round, and it found the hazard the hard way: `ID_ORDER` reproduced its registered ceiling at **32/32 overlap**. Both guards are now in place — per-world randomized store order, poison draw, query draw and task split (A3.1, re-verified at 2/32 and 0/32 against chance 1.9 and 0.9), and the `id_order_not_equivalent` precondition that emits `STATUS_NOT_EMITTED` on a tie. |
| 4 | **CMB-P0 / P1 not independently re-executed** (local torch is CPU-only; a GPU re-run needs an authorized instance). Receipts carry full device provenance and content hashes. | 🔒 **OWNER** — GLM recommends a GPU re-run **only if the phase lane reopens**. The lane is closed, so no action is proposed. |

### Auditor disclosure, recorded

GLM's verification re-run briefly rewrote `RGM02_RECEIPT.json` on disk with **byte-identical**
content — the identical hash is itself the determinism proof — and restored it from git. The
working tree is clean. Recorded here because a disclosure that lives only in the auditor's own
report is not a disclosure.

---

## 10. Cross-reference — the same verifier, measured against a different attack

**CMB-RP0 (2026-09-02) tested this verifier as a REPLAY SELECTOR and it added nothing there:**
`TWO_TIER_GATE_EARNS_NOTHING`, with the authorization tier *dominated by its own retrieval tier*
and beaten on forgery exclusion by a filter that counts graph edges (`4.41` vs `5.67`).
Independently audited by GLM: **PASS**.

**That does not disturb this result, and the reason is the useful part.** The two benches
measured the same mechanism against two different attacks:

- **Here (admission):** one **adaptive** forgery, built to sit above the absolute bar and inside
  the relative margin. It is blocked by **consistency**, which an attacker cannot defeat without
  the forgery ceasing to be a forgery. `119 → 0` false authorizations, `358` true kept.
- **There (replay):** 132 **cheap** forgeries. They are not ambiguous, they are conspicuous —
  a one-item forgery sits in the graph differently from what it copies — and the verifier does
  not look at structure at all.

**The verifier detects semantic contradiction, not structural anomaly.** Both facts are now
measured, and the full statement is in `CMB_RP0_v0_1/CMB_RP0_FINDINGS.md` section 13.

---

## 11. Owner rulings on the GLM findings — 2026-09-02

### Finding 1: TWELVE WORLDS ACCEPTED, WITH THE CAVEAT

The owner accepted 12 worlds rather than funding the >=20 the RGM-0.1 audit prescribed. **The
caveat is a permanent rider on this result and travels with every quotation of it:**

> RGM-0.2 ran on **12 worlds**, not the >=20 prescribed. The two winning families
> (`PATTERN_COMPLETION` +0.4108, `INDEPENDENT_CORROB` +0.3190) are **12/12 and unambiguous at
> this sample size**. The three losing families (-0.0117, -0.0251, -0.0133) are **small and
> noise-limited**, and 12 worlds cannot establish their magnitude. The admission-safety result
> (119 -> 0 false authorizations) is a **count**, not a mean, and is not power-limited.

So the caveat binds the *geometry* comparison, not the *admission-safety* headline. The
admission result is the one that carries the lane, and it is a count.

### Finding 2: RENAME RATIFIED

```
GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED     -> CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY
GENERIC_GEOMETRY_ADVANTAGE_NOT_SUPPORTED -> CAS_GEOMETRY_NO_ADVANTAGE_OVER_GENERIC_CONTROL
```

`run_rgm02.py` emits the new name and additionally emits the old one as
`generic_geometry_status_legacy_name`, so no historical reference breaks.

**`RGM02_RECEIPT.json` is deliberately NOT rewritten.** It carries the legacy name. GLM
reproduced that file byte-identically by re-execution, and its hash
`b74a16a0e973fced16af7d172d7b502334407116ddf7f561091cf48eeafb7f1f` is the determinism proof.
Editing it to look tidier would destroy the strongest evidence this result has.
