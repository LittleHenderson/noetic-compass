# STRUCTURAL_CONSTANTS_RESULT — the "declared by absence" class is exactly eight cells, and it is now exhausted

**Round 35. Systematising the opening an independent audit found by luck.**
**$0.00. Pure standard library. No torch, no GPU, no model, no training, no new run.**

Script: `measure_structural_constants.py`. Raw output: `structural_constants.txt`.

---

## 1. What was generalised

The round-34 audit observed that the fitted readout marks self-link slots (X→X) PRESENT and that none
is a real edge. Verified against the whole course that turned out to be **structural** — zero
self-links in 649,728 declared edges — and forcing self-link slots ABSENT moved `edge_account` from
0.0000% to 4.2857%.

**That was one instance of a general class: a slot whose symbol is the same in every world needs no
reader at all.** This round finds every such cell **by construction** rather than by luck, over all 64
worlds in the bank, and then measures what hard-coding them is worth on the recorded scores.

Cells are keyed structurally, not by question or by world: the kind, the field, and the slot's
coordinates reduced to node **positions within their own world**. A cell is a structural constant when
**every one of the 64 worlds** gives it the same symbol.

## 2. The scan — eight cells, and nothing else

```
  CONSTANT          ('edge_account', 'edge', (0, 0))  ->  ABSENT   (4480 observations)
  CONSTANT          ('edge_account', 'edge', (1, 1))  ->  ABSENT   (4480 observations)
  CONSTANT          ('edge_account', 'edge', (2, 2))  ->  ABSENT   (4480 observations)
  CONSTANT          ('edge_account', 'edge', (3, 3))  ->  ABSENT   (2964 observations)
  CONSTANT                 ('parts', 'node', (0, 0))  ->  ABSENT    (960 observations)
  CONSTANT                 ('parts', 'node', (1, 1))  ->  ABSENT   (1472 observations)
  CONSTANT                 ('parts', 'node', (2, 2))  ->  ABSENT    (640 observations)
  CONSTANT                 ('parts', 'node', (3, 3))  ->  ABSENT    (260 observations)

cells scanned: 36   constant: 8   mixed: 28
```

**Every constant is a self-link or a self-part, and every one is ABSENT.** `parts`' four are the slot
for the supplied `whole` itself — a node is never a direct part of itself, for the same reason a node
has no edge to itself.

**`context` has no structural constants at all.** Its participant cells are genuinely mixed across the
64 worlds, so that kind gets nothing from this avenue. That is an honest negative and it is the useful
half of the result: **the class is bounded, and it is now exhausted.**

## 3. What hard-coding them is worth

Recorded scores, six runs, truth-free:

| kind | q | independent | constants applied | hard-coded | lift |
|---|---|---|---|---|---|
| `edge_account` | 420 | 0.0000% | 1602 | **4.2857%** | **+4.2857%** |
| `parts` | 318 | 29.2453% | 318 | **31.7610%** | **+2.5157%** |
| `context` | 420 | 0.0000% | 0 | 0.0000% | **+0.0000%** |

**`edge_account`'s +4.2857% reproduces round 34's ad-hoc self-link result exactly.** The systematic
scan was built independently of that test and lands on the same figure from the same 18 of 420
questions — **an unplanned cross-check that both measurements pass.**

## 4. Reconstructing the `parts` estimate, and why it is not an addition

Round 34's truth-free total counted `parts` at **+23.83** questions per run from the declared
cardinality constraint. This round measures `parts` at **+2.5157%** from the self-part constant — but
that is measured against the **independent** baseline of 29.2453%, and the cardinality decoder already
reaches 74.2138% on the same kind.

**The two fixes overlap: a top-k selection over the non-self slots will usually not choose the self
slot anyway. Their combination is unmeasured, and this record does not add them.**

**So the truth-free total is unchanged at +36.83 questions per run:**

| kind | mechanism | counted |
|---|---|---|
| `parts` | declared out-edge count of `whole` | **+23.83** of 53 |
| `definition` | `FOCUS_WORLD_DECLARATION_IDENTITY` | **+7.17** of 70 |
| `edge_account` | self-links are never PRESENT | **+3.00** of 70 |
| `context` | one-world joint decode | **+2.83** of 70 |
| | | **+36.83 per run of 564** |

Mean **195.5/564 = 34.66% → 232.3/564 = 41.19%**.

## 5. What this round is actually worth

**It closes an avenue rather than opening one, and that is the value.** After the audit's lead there
was an obvious temptation: hunt for more free constants. This round answers that question definitively
— **there are exactly eight, they are all self-link or self-part, and four of the six kinds have none
at all.** No further free wins exist in this class, and no more time needs spending looking for them.

It also produced one number worth keeping: **`parts` gains +2.5157% from a constant that requires no
reader**, which matters only if the cardinality constraint is ever dropped.

**And it is a second instance of the round-34 lesson working as intended:** an observation made by luck
in one kind (self-links in `edge_account`) was turned into a construction, run over the whole bank, and
**bounded** — including the negative that `context` has nothing of this kind.

## 6. Claim status

- **REAL:** §2's scan. Eight constant cells over 36, keyed structurally, verified across all 64 worlds
  of the bank. `context` has none.
- **REAL:** §3's decoder table, six runs, truth-free.
- **REAL:** the cross-check. `edge_account`'s +4.2857% is reproduced by two independently built
  measurements.
- **NOT LICENSED:** adding §3's `parts` gain to round 33's cardinality gain. They overlap and the
  combination is unmeasured.
- **NOT LICENSED:** that a run realises any of it. All decoders ran offline against recorded scores;
  `score_decisions` is untouched.
- **OPEN, and now the largest single item:** `parts`' cardinality decoder reaches 74.2138% while
  `context`'s best truth-free decoder reaches 4.0476% and `edge_account`'s reaches 4.2857%. The gap
  between them is the same gap round 27 measured — `parts` reads its bits at 70.5314%–73.9130% against
  a 51.2707% chance rate, and the other two do not. **The constraint layer is now as good as the
  readout underneath it, and the readout is the binding constraint.**
