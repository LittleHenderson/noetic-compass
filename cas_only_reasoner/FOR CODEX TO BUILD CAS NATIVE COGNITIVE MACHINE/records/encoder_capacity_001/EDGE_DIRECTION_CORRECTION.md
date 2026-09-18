# EDGE_DIRECTION_CORRECTION — a directed edge was being read as undirected, and every `edge_account` number from round 27 to round 31 carried it

**Round 32. Self-correction #12. Own analysis, not the harness.**
**$0.00. Pure Python. No torch, no GPU, no model, no training, no new run.**

Artifacts: `probe_edge_reachability.py`, `edge_reachability.txt` (the diagnosis);
`measure_bits_read.py` / `bits_read.txt` and `measure_field_bottleneck.py` / `field_bottleneck.txt`
(re-run with the fix).

---

## 1. How it surfaced

Round 31's field decomposition asked what each field of a many-decision answer is worth, by giving
that field the true symbol and re-assembling through the project's own `slots.assemble_answer`. For
`role_set` and `parts` the substitution reached **100.0000%**, so the machinery is sound.

For `edge_account` it reported **0.0000%**.

`edge_account` has exactly **one** field, so that arm hands the answer over outright. A kind that
scores 0.0000% when it is *given* the answer is not a hard kind — it is an **unreachable** one. That
is an impossibility, so it was chased.

## 2. The cause

`measure_bits_read.py` and its descendants built the true symbol for each edge slot like this:

```python
present = {tuple(sorted((row["source"], row["target"]))) for row in value["edges"]}
key     = tuple(sorted((slot["coordinates"][0], slot["coordinates"][1])))
return "PRESENT" if key in present else "ABSENT"
```

**Sorting the pair makes it undirected.** `checker._edges` is
`frozenset((edge["source"], edge["target"]))` — an **ordered** pair — and `assemble_answer` emits
`slot["coordinates"]` as `[source, target]`, in that order. Sorting collapsed the two directions
onto one key, so `(n0, n1)` and `(n1, n0)` were both marked PRESENT.

The diagnosis, printed by `probe_edge_reachability.py` against a world with **4** declared edges:

```
true PRESENT slots: 8 of 16   (truth has 4 edges)
assembled == admissible_answers[0] ?  False
   as SETS equal? False
   only in assembled: [(n1, n0), (n2, n1), (n2, n3), (n3, n0)]
   only in truth    : []
```

**Exactly double, and every extra entry is its partner's reversal.** Not a near miss — a systematic
factor of two on the edge count.

## 3. The fix, and its verification

```python
present = {(row["source"], row["target"]) for row in value["edges"]}
key     = (slot["coordinates"][0], slot["coordinates"][1])
```

Re-run of the same probe:

```
true PRESENT slots: 4 of 16   (truth has 4 edges)
assembled == admissible_answers[0] ?  True
true PRESENT slots: 2 of 9    (truth has 2 edges)
assembled == admissible_answers[0] ?  True
```

The truth is reachable, and Round 31's `edge_account` arm now reads **100.0000%** under the
substitution, like `role_set` and `parts`.

## 4. Scope

**`edge_account` only.** The other three binary kinds key on a **single** coordinate
(`parts`, `role_set`, and the `context` participants), where sorting cannot conflate anything.
`measure_slot_evidence.py` and `measure_read_path_projection.py` never computed a true symbol and are
unaffected.

Affected and re-run: `measure_bits_read.py`, `measure_field_bottleneck.py`, `measure_binding_ceiling.py`,
`measure_fitted_readout_score.py`, `measure_binding_variants.py`. All five patched in place so their
artifacts are reproducible.

## 5. What changed — the corrected numbers

### The machine's per-bit reading of `edge_account`, six runs

| | with the bug (rounds 27–31) | **corrected** |
|---|---|---|
| per-bit accuracy | 52.3810% – 53.5471% | **62.7794% – 67.3469%** |
| truth PRESENT rate | 40.4276% | **20.2138%** |
| chance (p²+(1−p)²) | 51.8326% | **67.7444%** |
| best constant | 59.5724% | **79.7862%** |
| machine − best constant | −6.0253 to −7.1914 | **−12.4393 to −17.0068** |
| exact answers | 0.0000%, all six | 0.0000%, all six |

**The machine looks better in absolute terms and worse against its baselines.** It reads at
62.7794%–67.3469% where chance is 67.7444% — **below chance in all six runs** — and
12.4393–17.0068 points below the trivial constant. The round-27 conclusion (that this kind is not
reading its bits) is unchanged in direction and **stronger in degree**.

The corrected bits-correct histogram, 420 questions:

```
edge_account   (420 questions, slot counts {9: 13, 16: 57})
    40% correct     3    0.71%
    50% correct    52   12.38%
    60% correct   168   40.00%
    70% correct    79   18.81%
    80% correct   103   24.52%
    90% correct    15    3.57%
   -- never 0%, never 100%
```

It still never once gets a 16-slot question fully right in 420 questions.

### The fitted readout, per field

| kind | field | slots | per-slot, with the bug | **corrected** |
|---|---|---|---|---|
| `edge_account` | `edge` | 1029 | 59.9611% | **77.8426%** |

and the substitution arms, corrected:

| kind | arm | accuracy |
|---|---|---|
| `edge_account` | fitted | 1.4286% |
| `edge_account` | **fitted + `edge` truth** | **100.0000%** |
| `role_set` | fitted + `role` truth | 100.0000% |
| `parts` | fitted + `node` truth | 100.0000% |
| `context` | fitted + `participant` truth | 75.7143% |
| `context` | fitted + `setting_ref` truth | 4.2857% (**+0.0000**) |
| `definition` | fitted | **48.5714%** |

`parts` and `context` move slightly because the fit is shared across kinds and `edge_account`'s
labels are inputs to it: `parts` 15.0943% → 3.7736%, `context` 4.2857% → 4.2857% (unchanged per field,
its participant per-slot accuracy 55.0562% → 52.8090%). Those shifts are consequences of the shared
fit, not independent measurements.

## 6. The method lesson, which is worth more than the bug cost

**The 229/229 validation did not catch this, and it could not have.** That check compared the
machine's **submitted answer** to the answer the project's checker derives from the public snapshot,
and it passed six-for-six, twice. It validated the **truth derivation** — correctly.

It never touched `true_symbol`, the mapping from that truth to per-slot labels. **A validation that
confirms your oracle does not validate the layer you build on top of it.** The layer that was wrong
was one step above the layer that was checked, and the check was silent about it by construction.

What caught it was not a validation at all: it was an arm that produced an **impossible** result.
0.0000% when given the answer is not a low score, it is a contradiction, and contradictions are
cheaper detectors than validations.

**Both lessons are now standing practice in this record:** validate the layer you actually use, and
treat an impossible reading as a bug report about your own instrument before treating it as a finding
about the machine.

## 7. Claim status

- **REAL, verified:** the diagnosis and the fix. `probe_edge_reachability.py` prints the doubled
  count, the reversal set, and — after the fix — `True` against the admissible answer, for two
  questions.
- **REAL:** every corrected figure in §5, from re-run artifacts.
- **CORRECTED:** the `edge_account` rows of `BITS_READ_RESULT.md`, `BINDING_VARIANTS_RESULT.md` and
  `FITTED_READOUT_RESULT.md`, and Limits 2 and 4 of `MACHINE_STATE_001/STATUS.md`. Each carries a
  pointer to this record.
- **UNCHANGED:** everything about `parts`, `role_set`, `context` and `definition`, except where a
  shared fit makes their numbers move, which §5 states.
- **NEW, and the strongest statement in this record:** giving any single-field kind its one true
  field yields **100.0000%**. The answer assembly is correct, the task is reachable, and the entire
  deficit is per-slot readout accuracy. Exact-answer accuracy is per-slot accuracy raised to the slot
  count — `edge_account` 0.778426¹⁶ = 3.43% against 1.4286% measured; `role_set` 0.694444⁶ = 11.22%
  against 8.3333%; `context` 0.528090⁴ × 0.757143 = 5.89% against 4.2857%. **There is no composition
  defect left to explain.**
