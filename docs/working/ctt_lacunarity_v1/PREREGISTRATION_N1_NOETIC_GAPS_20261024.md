# N1 predeclaration — Noetic exposure versus error across the eighteen checkpoints (2026-10-24)

Status: **exploratory, but frozen before any result is computed.** It is deliberately NOT part of the checkpoint or
generation decisions already reported. Nothing here can change those outcomes.

## 1. The question

Between step 1,000 and step 6,000, held-out next-token error rises while generated replies improve. Where does the
rise live? Two competing explanations, stated before measurement:

- **H-overfit:** error rises in Noetic cells with **high** training exposure — repeated examples are being
  over-learned at the expense of the rest.
- **H-neglect:** error is high and stays high in cells with **low** exposure — those capabilities were never taught.

A third outcome is allowed and must be reported: neither pattern holds, and error rises uniformly across cells.

## 2. Data and unit

- Rows: `cas_val.jsonl`, the CAS validation set (gold CAS targets, so teacher-forced error is computable).
- Address per row: the set of Noetic tokens `^0`…`^9` that appear in the row's gold target. A row can carry more than
  one Noetic and is counted in each.
- Exposure per cell: the number of training rows (`cas_keep.jsonl`) whose gold target contains that Noetic.
- Error per cell at a checkpoint: mean per-token negative log-likelihood over every validation row whose address
  contains that cell.
- Checkpoints: the 18 already on disk (3 seeds × steps 1,000…6,000).

## 3. What is measured

1. Exposure vector `E` over the ten Noetics; its CAS state lacunarity `Λ(E) = Var/Mean²`.
2. Error vector `Err_t` over the ten Noetics at every checkpoint; `Λ(Err_t)`.
3. Change in error per cell between step 1,000 and step 6,000, per seed.
4. The relation between exposure and error change: rank correlation, and a comparison of high-exposure versus
   low-exposure cells split at the median exposure.

## 4. What would count as evidence for each hypothesis

- **H-overfit supported** if the high-exposure half's mean error rises more than the low-exposure half's in at least
  2 of 3 seeds.
- **H-neglect supported** if low-exposure cells carry higher error at both checkpoints in at least 2 of 3 seeds.
- Otherwise: neither, and that is the recorded result.

These are descriptive comparisons, not significance tests. With ten cells and three seeds, a rank correlation is
reported as a number, never as proof.

## 5. Limits, stated now

- Noetic labels come from the gold CAS targets, not from the model's internals. A row's address is where the data
  says it belongs, not where the model put it.
- Exposure counts rows, not repetitions; the fixed data order means every cell is seen many times.
- The analysis cannot show causation. It can only show whether the error rise is concentrated in a kind of cell.
- Diagnostic only, local GPU, not claim-bearing.

## 6. Output

One report: exposure table, per-cell error at step 1,000 and 6,000 for each seed, the change table, and the verdict
on H-overfit / H-neglect / neither — whichever the numbers give.
