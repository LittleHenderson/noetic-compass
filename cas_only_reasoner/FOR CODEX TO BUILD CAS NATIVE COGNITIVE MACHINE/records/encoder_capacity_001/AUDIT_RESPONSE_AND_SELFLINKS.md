# AUDIT_RESPONSE_AND_SELFLINKS — an independent audit's findings, accepted, plus the opening it handed over

**Round 34. Response to an external audit of rounds 27–33, and a new result the audit pointed at.**
**$0.00. Pure standard library. No torch, no GPU, no model, no training, no new run.**

Scripts: `measure_selflinks_and_edges.py` (`selflinks_and_edges.txt`),
`measure_one_world_joint.py` (`one_world_joint.txt`), `probe_edge_reachability.py`
(`edge_reachability_after_fix.txt`).

---

## 1. What the audit got right, and it was acted on

An independent audit of the round-32 direction correction checked the bug, the fix, and the numbers
built on them. It confirmed the bug and the fix, and found that several conclusions drawn from the
corrected numbers went further than the evidence allowed. **I accept the substantive findings. Every
one is corrected here and in place.**

| # | Finding | Verdict | Action |
|---|---|---|---|
| 1 | "The correction makes the machine look better" is misleading — always-ABSENT now scores 79.7862% for free, above the fitted readout's 77.8426% | **Correct.** The number rose because the answer key has fewer yeses, not because the reader improved | §3 adopts the audit's metric |
| 2 | "Below chance in four of the six runs" is wrong — it is **all six** | **Correct.** 62.7794%–67.3469%, all under 67.7444% | **Corrected in five files** |
| 3 | The fitted readout is not the trained machine | **Correct.** It is a ridge fit on the frozen encoder's output | §4 sharpens the wording |
| 4 | "There is no composition defect left" is unsupported — 13 of 70 edge questions have 9 slots (so 3.43%, not 1.82%), and each rate rests on 1–3 questions | **Correct.** 1/70 has a 95% interval of 0.04%–7.70% | **Downgraded to "consistent with"** |
| 5 | `STATUS.md` contradicts itself on `setting_ref` | **Correct** | **Fixed** |
| 6 | The 100% substitution results only test the measuring tool | **Correct and important** | §4 restates the scope |
| — | `CORRECTED`/`UNCHANGED`/`NEW` are not the spec sheet's status words | **Correct** | This record uses the sheet's vocabulary |
| — | 5.8886% shown as 5.88% | **Correct** | **Now 5.89%** |
| — | The after-fix probe output was never saved | **Correct** | `edge_reachability_after_fix.txt` now exists |

**One correction the audit did not make, made here:** the 1.82% figure in three records was
`0.778426¹⁶` applied to all 70 questions. Thirteen of them have nine slots, not sixteen, so the
mixture prediction is `(57 × 0.778426¹⁶ + 13 × 0.778426⁹) / 70 = 3.43%`. The audit's 3.4289% and this
record's 3.43% agree.

## 2. The audit's strongest single point, and the metric now adopted

**Per-slot accuracy is a bad target here.** After the direction fix only 20.2138% of edge slots are
PRESENT, so a decoder that always answers ABSENT earns **79.7862%** for free. A per-slot figure near
65% is therefore not a near-miss — it is **below a constant**.

The audit's recommendation is adopted: report **edges found**, **false alarms**, and **balanced
accuracy** — the mean of the two, which is 50% for a coin flip. Measured on the recorded machine
across all six runs and all 6,174 edge slots:

```
  true edges (PRESENT)            1248   of 6174 slots
  true non-edges (ABSENT)         4926
  edges FOUND                      460   36.8590%   of real edges
  edges MISSED                     788   63.1410%
  FALSE ALARMS                    1359   27.5883%   of non-edges
  balanced accuracy             54.6353%   (coin flip = 50%)
  plain per-slot accuracy       65.2251%   (always-ABSENT = 79.7862%)
```

**The machine finds 36.8590% of real edges and raises 1,359 false alarms. Its balanced accuracy is
54.6353%, 4.6353 points above a coin flip.** That is the honest measure of how well it reads edges,
and it is far less flattering than "62.7794%–67.3469% per slot". **Every future edge figure in this
record uses this metric.**

## 3. The opening the audit handed over, and it works

The audit observed that the fitted readout marked 35 self-link slots (X→X) PRESENT and that none was
a real edge, and suggested self-links might be the same kind of opening as round 33's declared
constraints. **It is, and it is stronger than suggested.**

**Verified across the whole course: 216,576 world declarations, 649,728 declared edges, and ZERO
self-links.** The task never presents a self-link. So a self-link slot is a slot whose answer is
declared, and the composer does not read it.

**And the machine over-asserts them.** Of 1,602 self-link slots in the 420 edge questions, it called
**472 (29.4632%) PRESENT** — every one a false alarm by construction.

Forcing self-link slots ABSENT, on the recorded scores, six runs:

| decoder | exact answers | per-slot |
|---|---|---|
| independent (the run's own rule) | 0.0000% (0 of 420) | 65.2251% |
| **self-links forced ABSENT** | **4.2857% (18 of 420)** | **72.8701%** |
| self-links ABSENT **+ declared cardinality** | 4.2857% (18 of 420) | **74.3440%** |

**Truth-free. `edge_account` moves off zero.**

## 4. This refutes part of round 33, and the refutation is the point

Round 33 concluded that `edge_account`'s declared-cardinality constraint did nothing **"because that
kind's margins carry no signal"**, and generalised to "a constraint can reorder evidence; it cannot
create it".

**That conclusion was too strong, and this round shows why.** The margins do carry signal — balanced
accuracy 54.6353%, above chance — and a **different** declared constraint moves the kind off zero. The
cardinality constraint failed not because there was nothing to reorder but because it was **the wrong
constraint**: it asks the reader to rank sixteen pairs when the reader's ranking is only 54.6353%
balanced. The self-link constraint asks nothing of the reader at all — it is a fact about the task.

**So the corrected rule is not "no signal, no gain". It is: a declared constraint helps in proportion
to how little it asks of a reader that is weak.** `parts` (a real signal) gained +44.9686 from a
cardinality constraint. `edge_account` (a weak signal) gains +4.2857 from a constraint that requires
no ranking at all, and +0.0000 from one that requires a good one.

## 5. Two more results from this round, both truth-free

`measure_one_world_joint.py` applied round 33's joint candidate mechanism — enumerate the bank, score
each world's implied answer, take the argmax — to the two kinds whose whole answer is one world's
declaration:

| kind | independent | **joint** | lift |
|---|---|---|---|
| `context` | 0.0000% | **4.0476%** | **+4.0476%** |
| `edge_account` | 0.0000% | **6.1905%** | **+6.1905%** |

Six runs each. And it produced the number that explains round 32's shortfall: **the recorded machine's
`setting_ref` slot is right only 10.7143% of the time** — above the 1.5625% chance rate for a 64-way
choice, so it *is* reading the world, but far too weakly to carry `context` on its own. That is what
forced round 32's arm to hold `setting_ref` at the truth, and it is now measured rather than inferred.

## 6. Truth-free gains, summed

| kind | mechanism | lift per run |
|---|---|---|
| `parts` | declared out-edge count of `whole` | **+23.83** of 53 |
| `definition` | `FOCUS_WORLD_DECLARATION_IDENTITY` | **+7.17** of 70 |
| `edge_account` | self-links are never PRESENT | **+3.00** of 70 |
| `context` | one-world joint decode | **+2.83** of 70 |
| | | **+36.83 per run of 564** |

Against the six recorded runs of 193, 192, 200, 203, 196, 189 — mean **195.5/564 = 34.66%** — that is a
mean of **232.3/564 = 41.19%**.

**`context`'s round-32 cardinality result (+32.6190) is NOT counted**, because that arm held
`setting_ref` at the truth; the +2.83 above is the truth-free joint decode instead.

## 7. Claim status, in the spec sheet's vocabulary

- **REAL:** the bug, the fix, and the six-run corrected machine table. `probe_edge_reachability.py`
  reproduces `4 of 16`, `2 of 9` and `True` twice, and its output is saved.
- **REAL:** zero self-links in 649,728 declared edges over 216,576 world declarations; 472 of 1,602
  self-link slots called PRESENT by the recorded machine.
- **REAL:** §3's and §5's decoder tables, six runs each, truth-free.
- **REAL:** the balanced-accuracy figures — 460 of 1,248 edges found, 1,359 false alarms, 54.6353%.
- **WITHDRAWN:** round 33's "a constraint can reorder evidence; it cannot create it", as stated. The
  corrected rule is §4's.
- **WITHDRAWN:** "there is no composition defect left to explain". The substitution arms reach 100.0000%
  because they are given the truth, which shows the assembly can build the true answer and the task is
  not impossible. **It says nothing about the machine**, and the samples behind the per-kind rates are
  1–3 questions. The honest statement is **consistent with** pure compounding, not proof of it.
- **NOT LICENSED:** that a run realises +36.83 questions. All decoders ran offline against recorded
  scores. `score_decisions` is untouched and must change for any of this to count.
- **FLAG_FOR_HUMAN_REVIEW:** whether the per-slot rates rest on enough questions to be quoted at all.
  1/70 has a 95% interval of 0.04%–7.70%, and this record now says so where it quotes them.
