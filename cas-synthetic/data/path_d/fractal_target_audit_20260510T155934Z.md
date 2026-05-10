# Fractal target audit

Strict ordered-sequence validation of every fractal-shaped training row in the v1 mix corpus, using `cas_native.inference.fractal_repair.verify_fractal_rendering`.

## Files scanned

| File | Rows | Fractal rows |
|---|---:|---:|
| `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` | 7395 | 226 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl` | 412 | 13 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl` | 412 | 10 |

## Aggregate

- Total fractal rows: **249**
- Strict sequence match (target preserves exact k-order/count): **46 (18.5%)**
- Cardinality match only (right count, wrong order): 65 (26.1%)
- Cardinality drift (wrong count): 138 (55.4%)
- Mojibake-corrupted source CAS: 0

## By k-length bucket

| k | Rows | Sequence match | Cardinality match |
|---:|---:|---:|---:|
| 2 | 62 | 15 (24.2%) | 32 (51.6%) |
| 3 | 54 | 16 (29.6%) | 26 (48.1%) |
| 4 | 73 | 12 (16.4%) | 38 (52.1%) |
| 5 | 13 | 2 (15.4%) | 5 (38.5%) |
| 6 | 17 | 0 (0.0%) | 7 (41.2%) |
| 7 | 13 | 1 (7.7%) | 2 (15.4%) |
| 8 | 17 | 0 (0.0%) | 1 (5.9%) |

## By notation

- `Φ<…>` : 128 rows
- `Phi<…>` : 121 rows

## By split

- train: 226 rows
- val: 13 rows
- test: 10 rows

## Sample of worst offenders (manual review)

**id**: `v1mix_cas_to_english_003896` (val)

- source: `Φ<5:4:5:9:1:3:1:4>`
- expected k: [5, 4, 5, 9, 1, 3, 1, 4]
- found k: [0, 1, 4, 4, 3, 6, 7, 9]
- target text: An idea on the mind led to paying attention, which then struck a chord and resonated, becoming an aversion that rubs the wrong way, shaped by the sum of one's experiences, breaking it down, practice makes perfect, and finally something that

**id**: `v1mix_cas_to_english_002748` (train)

- source: `Φ<5:4:3:2:0:1>`
- expected k: [5, 4, 3, 2, 0, 1]
- found k: [0, 1, 2, 4, 5, 6]
- target text: An idea on the mind led to paying attention, which became drawn to something, then an aversion arose, which struck a chord, and finally this shaped who one is, which in turn led to breaking it down.

**id**: `v1mix_cas_to_english_003407` (train)

- source: `Φ<7:8:2:3:4:0>`
- expected k: [7, 8, 2, 3, 4, 0]
- found k: [0, 2, 3, 4, 7, 8]
- target text: An idea led to becoming aware, which became drawn to it, in turn pushed away, then struck a chord, which became muscle memory, and finally triggered a memory.

**id**: `v1mix_cas_to_english_003806` (train)

- source: `Φ<1:7>`
- expected k: [1, 7]
- found k: [0, 1, 2, 4, 6, 7, 8, 9]
- target text: A sequence that starts with an idea on the mind, then moves through paying attention, drawn to something, an aversion, struck a chord, shaped by experience, breaking it down, muscle memory, triggered a memory, and finally something that jus

**id**: `v1mix_cas_to_english_003266` (train)

- source: `Phi<1:9:9:9:9:1:9:3>`
- expected k: [1, 9, 9, 9, 9, 1, 9, 3]
- found k: [0, 1, 2, 4, 5, 6, 7, 9, 1, 9, 9, 9, 9]
- target text: An idea on the mind led to paying attention, then drawn to something, which became an aversion, that struck a chord, shaped who one is, breaking it down, muscle memory took over, and finally something just clicked, then paying attention aga

**id**: `v1mix_cas_to_english_005105` (train)

- source: `Φ<5:3:0:5:0:7:3:5>`
- expected k: [5, 3, 0, 5, 0, 7, 3, 5]
- found k: [0, 0, 7]
- target text: Something shaped by experience, then an idea on the mind, then an aversion, then shaped by experience again, then an idea on the mind once more, then muscle memory, then an aversion again, then shaped by experience a final time.

**id**: `v1mix_cas_to_english_004978` (train)

- source: `Φ<3:7:4:2:1:6:1>`
- expected k: [3, 7, 4, 2, 1, 6, 1]
- found k: [4, 3, 2, 1, 1, 6, 7]
- target text: Something struck a chord, then pushed away, which became drawn to it, in turn leading to paying attention, then paying attention again, breaking it down, and finally muscle memory.

**id**: `v1mix_cas_to_english_001102` (train)

- source: `Φ<5:6:1:7:9:7>`
- expected k: [5, 6, 1, 7, 9, 7]
- found k: [0, 1, 6, 7, 7, 9]
- target text: An idea shaped by experience, then paying attention to it, which led to unpacking that idea, settling into muscle memory, then muscle memory again, and finally something that just clicked into place.
