# RESULT — E-arm vs S2: the controlled instruction test

**Design:** identical to S2 in criterion, sealed families, runner-owned metadata, 16 frozen
cells, and 4×5 budget. **Sole difference:** one frozen, target-blind prohibition paragraph.
**Ordering note:** the owner's interpretation table was specified **before any E number was
read** (E completed after that message was composed). The conclusion below is the frozen table's
first row applying — not a post-hoc reading.

---

## Target-blindness verification (owner requirement, checked mechanically)

- The paragraph is a module-level frozen string — **identical for all 16 cells**, same placement.
- It lists **all four** canonical words for every cell; it never names only the target's word.
- No target-specific World clue, emphasis, or repetition anywhere in the prompt body (audited
  before every send, prohibition paragraph exempt by design).

## Result

```
                      overall leak       leaks
v1 (label + prohibition, VOID)   0.4058
v2 (label + defs + prohibition)  0.1625   (same 16 cells)
S2 (silent, no label)            0.1969
E  (no label + universal instr.) 0.0094   3 of 320 candidates
```

Per cell — every drive-1 cell at zero, every starved cell at zero except one candidate:

```
        E        S2                     E        S2
1d    0.000    0.500          1b     0.000    0.700
2a    0.000    0.200          2b     0.100    0.250
5d    0.000    0.300          5b     0.000    0.150
6a    0.000    0.050          6c     0.000    0.000
6b    0.000    0.200          6d     0.000    0.050
7a    0.000    0.100          7b     0.000    0.050
7c    0.000    0.000          2c     0.000    0.250
7d    0.050    0.100          3d     0.000    0.250
```

The three leaks: `7d` "physical" ×1, `2b` "emotional" ×2 — **all non-own-World or single
occurrences; the drive-topic channel (`1b → spiritual ×13` under silence) closed completely.**

## Interpretation — frozen table, row 1, strongest form

> *"E lowers drive-1 leakage and preserves the starved-cell gains → the v3 prompt architecture
> is clear."*

Both conditions hold, and beyond preservation the starved gains improved to zero. The v3
authoring instrument is therefore, per the pre-specified rule:

```
drive motive block          (what the actor ultimately seeks — no category term)
+ unlabeled realization criterion   (where the decisive success must become true)
+ opaque RF-family description      (sealed manifest, audited author text)
+ universal target-blind avoidance instruction   (identical across all 28 cells)
+ private regex enforcement          (the instruction is an aid, never the authority)
```

**No drive-specific instruction policy** — prompt policy must never correlate with Foundation.

## What this does and does not establish

- **Established (controlled):** under this author model, the universal target-blind instruction
  suppresses the drive-topic vocabulary channel without recreating priming — because no label is
  present to prime. `0.1969 → 0.0094` with one variable changed.
- **Suggestive only:** the size of the label-priming effect. v1 differed in multiple ways and was
  voided; a matched label arm would be needed to estimate that effect formally, and it is **not
  needed** to choose the v3 instrument.
- **Not established:** anything semantic. **Zero-leak text can still be semantically empty — the
  `T2` lesson.** `R1`/`R1B` are stage one only.

## Gate before v3 — per owner, R1 alone does not unlock generation

One confirmatory pilot under the selected policy must pass **all** of:

```
R1 leakage · R1B copying · R2 June surface gate · R3 blind World/drive/joint recovery
R4 held-out realization-family transfer · R5 lexical-baseline resistance · R6 second author
```

Then the v3 budget is simulated from the **worst observed World × drive cell**, and only then
does full 28-Foundation regeneration run.

**Open choice for `R6`:** the available second author is `models/gemini-2.5-flash` — a different
model but the **same family** as flash-lite, which weakens the "does it follow the author?"
inference. A cross-family author (or a small owner-authored arm, valid for the *mechanical* leak
metric since the detector is a regex) would be stronger. Flagged rather than decided.

## Leakage matrix (owner reporting standard, adopted for all future reports)

by World · by drive · by World × drive cell · leaked-word identity · own-World vs non-own-World.
`1b → "spiritual"` is **non-own-World** leakage: drive-topic vocabulary, not a Mental realization
failure. Collapsing it into a World rate conceals the mechanism.

## Status

`E = 0.0094 / policy selected by frozen rule / confirmatory R1–R6 pilot required before v3`
`QUARANTINED / nothing licensed / Gate 2 OPEN at 0.38`
