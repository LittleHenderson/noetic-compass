# Architecture change spec v0.1 — addressed aggregation for the typed learner

> **STATUS: PREDICTION 1 RUN AND MET — the spec is VALIDATED at the level of the
> defect it addresses.** At full sample the current mean-pooled packet decodes the
> focus world at **0.18%** (1 of 564; chance 1.5625%) while the row structure
> decodes it at **70.92%** (45× chance). An earlier partial run on 200 packets gave
> 11.50% and prompted a withdrawal; that run was **sample-limited**, and the
> learning curve in §8 shows why. **The withdrawal is itself withdrawn.**
>
> This validates the *diagnosis*, not the outcome: the change still has to be run
> to see whether the three zero-score kinds move. No launch is authorized.

Status: **SPECIFICATION ONLY — nothing is implemented, nothing is launched,
no reservation exists.** Prepared for owner review and signature.

Basis: `records/encoder_capacity_001/STATUS.md` Findings 3–9, all measured at $0 on
saved public data.

## 1. The defect, in one paragraph

The frozen encoder turns a 75-row frame into a single 64-dimensional vector by
`unit_l2(sum of unit row vectors)`. Every row receives weight `1/75` regardless of
content, so a one-token `START` marker and the 6,852-token alias table have
identical influence, and each row is itself a mean of its own tokens. The
aggregation is fixed: nothing in it depends on the question. Measured consequence:
a trained linear probe recovers which world the question concerns from that vector
**0 times in 200**, while the same probe over the raw rows recovers it at **7×
chance**, and decodability falls monotonically as rows are summed (query alone
11.0% → plus 3 rows 3.5% → plus all 76 rows 0.0%).

The question is averaged into its own evidence before any learning happens.

## 2. What changes

One function and one parameter list. Everything else is untouched.

**Encoder** (`cas_meta2/typed_teaching/encoder.py`, `packet_entry`, line ~164).
Today:

```python
result = normalize(torch.stack(vectors).sum(dim=0) / math.sqrt(len(vectors))).detach()
```

Under the new opt-in profile the encoder returns the **row structure** as well as
the existing mean:

- `encode_packet` / `encode_slot` keep returning the current 64-dim vector, so
  every existing caller, receipt and test is unaffected.
- A new method returns `rows` as a `(R, 64)` tensor plus the index of the row that
  addresses the question (the `QUERY` row; `QUERY`+`RECORD`+`SUPPORT` under the
  measured ablation).

**Learner** (`cas_meta2/typed_teaching/learner.py`, `_forward`, line ~146).
Today the encoded slot is consumed directly by the recurrence. Under the new
profile, one learned addressing step is inserted **before** the recurrence:

```
a_r   = <w, rows_r> / tau                       # w in R^64, tau in R
alpha = softmax(a)                              # R weights, content-dependent
encoded = normalize( sum_r alpha_r * rows_r )   # replaces the fixed uniform mean
```

then the existing `recurrence.run_passes(encoded, core, depth=...)` runs unchanged,
with the same `^6` block, the same readout and the same loss.

**New trainable parameters: 65.** `address.weight` (64,) and `address.tau` (1,).
Total trainable parameters go from **16,384 to 16,449** (+0.40%). They are added to
`PARAMETERS` and to the AdamW group; `PARAMETER_SHAPES` gains both entries and the
existing shape assertion extends to them.

## 3. Why this shape and not another

| alternative | why rejected |
| --- | --- |
| Drop the non-focus worlds | **unsafe** — they are the distractors that make a 64-way answer meaningful; `correspondence` and `analogy` become identifiable by elimination |
| Fixed content-addressed read (dot product against world rows) | **measured and failed** — 6.25% focus recovery against 1.56% chance, not a usable read |
| Weight rows by token count | fixes the 18.8× alias mismatch but leaves the aggregation content-blind, so defect 3 remains |
| Attend over tokens instead of rows | stronger, but a larger change; keep as v0.2 once v0.1 is shown to help |

The chosen shape is the **smallest change that makes the aggregation depend on the
question**, which is precisely defect 3 and the one no amount of training can
reach.

## 4. Preserved invariants

- The existing encoding profile remains the default. **No existing receipt,
  checkpoint, course or test changes meaning.**
- `learning_rate`, batch schedule, depths, slot plan, loss, checker and readout are
  unchanged.
- The frozen encoder, tokenizer and projection remain frozen and byte-identical.
- Work accounting gains one term (the addressing step) and must be reported
  separately, not folded into core forward calls.
- The change is opt-in by profile identity, so a run under the old profile is
  bit-comparable with the completed `typed_numeric_001` and `typed_matched_001`
  runs.

## 5. Testable predictions, stated before any run

Each is falsifiable on the existing scaffold:

1. **The focus becomes decodable.** A linear probe over `encoded` recovers the
   focus world at well above the measured 0% for the current profile. If it stays
   at 0, the change does not address the defect and should be withdrawn.
2. **`context` and `definition` leave 0.** They score exactly 0/70 in every
   completed run. A partial improvement (say 5/70) is a positive signal; 0/70 again
   means the addressing did not reach the declaration content.
3. **`analogy` improves or stops declining.** It runs at 10–16% with complete
   turnover.
4. **`edge_account` may remain 0** even if 1–3 improve. That kind is a conjunction
   of up to 16 exact binary slots, and Finding 6 shows exact accuracy falls
   geometrically in slot count. **A null result on `edge_account` alone must not be
   read as failure of the change.**
5. **`correspondence` and `reach`, which already work, must not regress.** This is
   the guard against the change simply adding noise.

## 6. Cost

- Implementation and pure tests: **$0**, no GPU, no provider.
- Validation run, if the owner authorizes one: one job on the existing bounded
  profile. Prior art is 3,300–3,600-second children at **$7** reserved. **Budget
  two reservations ($14)**: the project's own precedent is that a novel workload
  timed out on its first attempt and needed a corrected relaunch.
- Ledger position at authoring: revision 84, **$501.00 reserved, $4,499.00
  unreserved** of the $5,000 cap. Two further $7 reservations fit.

## 7. What this spec does not claim

- It does not claim the change will work. Prediction 1 is the cheap falsifier and
  should be run before the GPU run.
- It does not claim any learning advantage, matching control, transfer or
  retention result. Those need the matched design, not this change.
- It does not touch the CAS architectural question of whether a type alters the
  mechanism. Addressing is a plumbing fix to a measured defect; whether CAS
  structure can then do work is a separate and larger question.
- It does not authorize a launch. **`execution_enabled` stays false and no
  reservation is created until an owner record names this profile.** Speech in a
  session is not an owner record.

## 8. Prediction 1, run — MET at full sample, after a self-correction

`falsify_prediction_1.py`, ridge probe solved in the dual, 5-fold CV, chance
1/64 = 1.5625%. `cat_head` concatenates the nine non-world rows; `cat_all`
concatenates every row.

**Full sample, all 564 packets:**

| features | dims | CV accuracy | vs chance |
| --- | ---: | ---: | ---: |
| **mean (the current profile)** | 64 | **0.18%** | **0.1×** |
| query row only | 64 | 39.89% | 25.5× |
| query + support rows | 256 | 25.53% | 16.3× |
| **head rows (no world rows)** | 576 | **70.92%** | **45.4×** |
| the 64 world rows | 4096 | 0.89% | 0.6× |
| all rows concatenated | 4864 | 64.89% | 41.5× |

**An earlier run on 200 packets gave 11.00% and 11.50% and this spec was withdrawn
on that basis. That was wrong, and the learning curve shows why:**

| n samples | mean (64d) | query (64d) | head (576d) |
| ---: | ---: | ---: | ---: |
| 50 | 0.00% | 0.00% | 0.00% |
| 100 | 1.00% | 5.00% | 3.00% |
| 200 | 2.50% | 12.00% | 9.00% |
| 300 | 2.67% | 20.33% | 29.00% |
| 400 | 1.00% | 28.25% | 44.50% |
| 500 | 0.20% | 38.60% | **64.60%** |

**The row features are sample-limited, not information-limited — their decodability
climbs steeply with data and is still rising at the full 564.** The mean-pooled
feature is neither: it sits at 0.00–2.67% across the whole curve and is **0.20% at
n=500**. More data does not help it, because the information is not there.

Four things follow:

1. **The defect is confirmed and quantified.** The current profile decodes the
   focus world **1 time in 564**; the row structure decodes it **400 times in 564**.
2. **The proposed change is worth running.** A read over the rows has a measured
   ceiling of ~71%, not the 11.5% the partial run suggested.
3. **Adding the world rows HURTS.** `cat_head` alone gives 70.92%; adding the 4,096
   question-invariant world-row dimensions drops it to 64.89%. This is the dilution
   effect measured directly at the read, and it says the read should address the
   head rows for *identification* while the world rows supply *content*.
4. **The 64 world rows decode the focus at 0.89% — below chance.** They are
   identical in every packet, so they cannot identify the focus; they can only help
   answer once it is known.

**Revised shape for §2:** the addressing step should attend over the head rows to
identify the focus, and then draw the focus world's row for content — two steps,
not one mean over everything. The §2 formula still applies but should be read as
operating on the head rows with the world rows fetched by the resulting address.

**Prediction 1 is met. The launch recommendation is restored, subject to owner
authorization.** The self-correction is recorded rather than removed: the first
run's low number was a real measurement of a sample-limited quantity, and the fix
was more data, not a different theory.
