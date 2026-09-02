# RGM-0.2 — RESULT: `ADMISSION_SAFETY_REPAIRED`

**Run:** 12 new independent worlds (500–511), CPU, `428.05 s`, **$0**
**Hash:** `b74a16a0e973fced` · receipt `RGM02_RECEIPT.json` · raw `RGM02_RAW.json`
**Builder:** Claude. **Auditor:** a different model, named by the owner. **I do not audit this.**
**Conflict of interest declared** in preregistration §0: I audited RGM-0/0.1 and built RGM-0.2.

```
STATUS                    ADMISSION_SAFETY_REPAIRED
GENERIC GEOMETRY          GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED (survives drop-one)
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

**`GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED`** — and the honest shape matters more than the
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
