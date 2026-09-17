# Frozen-encoder capacity: why six of eight question kinds never learn

Status: **MEASURED — $0, standard library only, no model, GPU, checkpoint or provider used.**

Result: `result.json`. Reproduce with
`python -B verify_encoder_capacity.py --json result.json`.

## What was asked

Every completed experiment in this project shows the same pattern: of the eight
question kinds, only `correspondence` and `reach` ever move off chance, while
`context`, `definition` and `edge_account` stay at exactly 0 in every run, on
every seed, in both teaching arms. The matched study repeated this pattern
independently. This record asks whether the frozen encoder can even carry the
information those questions need.

## Method and its validity

The frozen token projection and the frozen symbol readout are built by one pure
function in `cas_meta2/typed_teaching/binding.py`:

```
bits = int.from_bytes(sha256(canonical([ROW_ALGORITHM, seed, d_model, domain]))
                      .digest()[:8], "little")
row  = struct.pack("<64f", *(0.125 if (bits >> i) & 1 else -0.125 for i in range(64)))
```

That reproduces both matrices **byte for byte**. Both were validated against the
SHA-256 the GPU worker recorded for the real bytes:

| matrix | bytes | reconstructed SHA-256 | recorded | exact |
| --- | ---: | --- | --- | --- |
| readout (90 symbols) | 23040 | `14da2c58…0ac667` | `14da2c58…0ac667` | **yes** |
| projection (3829 tokens) | 980224 | `4481b1d2…9fefdd9` | `4481b1d2…9fefdd9` | **yes** |

The digest match is what licenses everything below: these are the exact rows the
learner computed with, not a model of them.

## Finding 1 — the readout is NOT the bottleneck

A hypothesis worth testing was that the 65 world rows are too alike for a
64-dimensional readout to separate, which would cap `world_id` permanently.

False. The rows are a well-spread random frame:

- 90 symbol rows, mean `|cos|` **0.098408**, max `|cos|` **0.468750**
- 65 world rows, mean `|cos|` **0.101412**, max `|cos|` **0.468750**
- **0 duplicate rows**; the projection also has **0 duplicates across 3829 tokens**

An ideal hidden state set to a world's own row yields a worst-case runner-up
logit of 0.469 against a self-logit of 1.0. That is a usable margin. The readout
is fine.

## Finding 2 — the token projection is NOT the bottleneck either

3829 vocabulary entries map to 3829 distinct unit rows. No collisions. The
`collision_free_claim: false` in the binding profile is accurate but the measured
collision count is zero.

## Finding 3 — the packet mean destroys question-level signal

This is the finding. The stated rule is
`packet = unit_l2( sum(unit token rows) )`.

Two questions about the same world share all but a few token rows. Measured
angle between two such packets, over the frame lengths this course actually uses:

| packet rows | differing rows k | cos(A,B) | 1−cos | ‖A−B‖ |
| ---: | ---: | ---: | ---: | ---: |
| 794 | 1 | 0.998893 | 0.001107 | 0.046732 |
| 794 | 4 | 0.995499 | 0.004501 | 0.094128 |
| 794 | 16 | 0.982086 | 0.017914 | 0.187986 |
| 4096 | 16 | 0.997814 | 0.002186 | 0.065655 |
| 27718 | 4 | 0.999978 | 0.000022 | 0.006545 |
| 27718 | 16 | 0.999912 | 0.000088 | 0.013234 |

At the course's own maximum frame length (27,818 tokens, recorded in the worker
evidence), the entire query field can differ and the packet still moves by
`1−cos = 8.8e-05`.

Now compare that against the readout's own cross-talk between unrelated symbols:
mean `|cos| = 0.098408`.

**The signal distinguishing two questions at full frame length is about 1,100×
smaller than the interference between two unrelated answer symbols.** Even at the
shortest frames measured (794 rows, the development panel), 16 differing rows give
`1−cos = 0.0179` — still 5.5× below the readout's noise floor.

The mechanism is ordinary dilution. The differing rows contribute `O(sqrt(k))` to
a sum whose norm is `O(sqrt(n))`, so the discriminating component is
`O(sqrt(k/n))` of the packet. The measured `‖A−B‖` column tracks `sqrt(k/n)`
closely across the whole table. The packet is a mean, and the mean is dominated by
the bulk of the frame rather than by the query.

### The course's own counts corroborate the dilution

The frozen course record states, in `records/typed_course_001/checks_002/public_course.json`:

```
"materialized_input_bytes_max": 225368,
"source_bank_bytes": 219105,
```

The shared bank of 64 worlds is **219,105 of the 225,368 bytes** — **97.2%** — of
every packet. The question itself is the remaining 2.8%. Every packet carries the
whole bank, so the token rows that distinguish one question from another are a few
percent of the input by construction, before any pooling.

The same record also states `"unique_public_packets": 564` alongside
`"unique_query_families": 24`. The course is 564 presentations over **24 query
families**; this is the project's own count and matches the independently measured
finding that the 564 rows carry only 244 distinct expected answers (24 for each of
analogy, context, definition, edge_account, parts and correspondence; 36 for
role_set; 64 for reach).

## What this explains, and what it predicts

Consistent with every completed run:

- Answers fixed by the **query's own scope** — carried by the separate, short slot
  query vector `(unit packet + unit slot query)/sqrt(2)` rather than by the packet
  — can be learned. These are `correspondence` (which candidate) and `reach`
  (which reach rule).
- Answers requiring **content retrieval from the frame** — the focus world's own
  declarations, participants and edges, which occupy roughly a 1/64 slice of a
  mean-pooled vector — cannot be. These are `context`, `definition`,
  `edge_account`, and weakly `parts` and `role_set`.
- `world_id` sat at normalized loss ≈ 0.47 at update 0 and never moved across 160
  updates. That is the signature of a bulk statistic being read out, not of the
  query being read out. The model captured the frame's gross bias and had no
  gradient path to the focus.
- No number of seeds and no amount of training can repair this, because the
  information is destroyed before the trainable block sees it. This is consistent
  with the matched study failing to find an advantage and with the earlier
  per-field loss record showing six of eleven fields never leaving chance.

Predictions this record makes, each testable on the existing artifacts:

1. Loss on `setting_ref`, `function_ref`, `kind_ref` will not improve if frames are
   shortened, because the same world content is present in every packet either way
   — unless the frame is shortened by *removing the other 63 worlds*, which is a
   different change.
2. Making the packet a **mean over a much smaller slice** (only the focus world's
   own declarations and relations) should move those fields off chance. That is
   the cheapest decisive experiment available.
3. Replacing mean-pooling with a **content-addressed read** — attention or a
   keyed lookup over token rows instead of a sum — should also work, and is the
   architecturally interesting fix.

## Limits of this record

- The measurement uses **random token rows** for the bulk, not the real frames.
  Real frames repeat tokens (the 64-world bank, repeated declarations, worked
  supports), which can only *amplify* a differing token's contribution if that
  token is repeated. The numbers above are therefore a first-order model, and the
  real dilution should be treated as of the same order, not as an exact figure for
  any specific packet.
- The frame-length values (794, 4096, 27718) are taken from recorded worker
  evidence (maximum frame text 54,830 bytes; maximum complete input 27,818
  tokens), not re-derived by tokenizing the course here.
- No claim is made about the trainable block. This record shows the encoder cannot
  deliver the signal; it does not show the block could not use it if delivered.
- The split of the eight kinds into "scope-fixed" and "content-retrieval" is a
  reading of the evidence offered here as a hypothesis, not a measurement.

## Evidence

| artifact | SHA-256 |
| --- | --- |
| frozen readout (recorded by the GPU worker) | `14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667` |
| frozen projection (recorded by the GPU worker) | `4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9` |
| `result.json` | see file |

Source of the row algorithm:
`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/binding.py` lines 198–216.
Source of the recurrence:
`research/CAS_META_2_COMPOSITION/cas_meta2/recurrent_cjt/recurrence.py` lines 182–215.

This record makes no learning, capability or readiness claim. It is a measurement
of a frozen encoder, performed on saved public data with no neural execution.
