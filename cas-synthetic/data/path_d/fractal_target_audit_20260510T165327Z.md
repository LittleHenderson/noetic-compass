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
- Strict sequence match (target preserves exact k-order/count): **70 (28.1%)**
- Cardinality match only (right count, wrong order): 73 (29.3%)
- Cardinality drift (wrong count): 106 (42.6%)
- Mojibake-corrupted source CAS: 0

## By k-length bucket

| k | Rows | Sequence match | Cardinality match |
|---:|---:|---:|---:|
| 2 | 62 | 22 (35.5%) | 36 (58.1%) |
| 3 | 54 | 25 (46.3%) | 34 (63.0%) |
| 4 | 73 | 17 (23.3%) | 44 (60.3%) |
| 5 | 13 | 5 (38.5%) | 11 (84.6%) |
| 6 | 17 | 0 (0.0%) | 8 (47.1%) |
| 7 | 13 | 1 (7.7%) | 4 (30.8%) |
| 8 | 17 | 0 (0.0%) | 6 (35.3%) |

## By notation

- `Φ<…>` : 128 rows
- `Phi<…>` : 121 rows

## By split

- train: 226 rows
- val: 13 rows
- test: 10 rows

## Sample of worst offenders (manual review)

**id**: `v1mix_cas_to_english_003806` (train)

- source: `Φ<1:7>`
- expected k: [1, 7]
- found k: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- target text: A sequence that starts with an idea on the mind, then moves through paying attention, drawn to something, an aversion, struck a chord, shaped by experience, breaking it down, muscle memory, triggered a memory, and finally something that jus

**id**: `v1mix_cas_to_english_002596` (train)

- source: `Φ<7:1:3:8:4:1:0:8>`
- expected k: [7, 1, 3, 8, 4, 1, 0, 8]
- found k: [0, 1, 1, 3, 8, 4, 3, 7]
- target text: An idea on the mind led to paying attention, then paying attention again, which became pushed away from something, then triggered a memory led to another trigger, which struck a chord, and finally an aversion emerged, with muscle memory in 

**id**: `v1mix_cas_to_english_003658` (train)

- source: `Φ<5:4:9:0:7:6:5:6>`
- expected k: [5, 4, 9, 0, 7, 6, 5, 6]
- found k: [0, 9, 5, 4, 9, 5, 6, 6]
- target text: A thought popped into mind, shaped by one's experiences, struck a chord, then popped into mind again, shaped who you are, practice made it perfect, breaking it down, and breaking it down once more.

**id**: `v1mix_cas_to_english_001075` (train)

- source: `Φ<5:7:0:1:1:2:4>`
- expected k: [5, 7, 0, 1, 1, 2, 4]
- found k: [0, 1, 1, 2, 4, 5, 7]
- target text: A thought led to paying attention, then paying attention again, which became drawn to something, struck a chord, shaped by experience, and finally turned into muscle memory.

**id**: `v1mix_cas_to_english_000469` (train)

- source: `Phi<5:2:6:7:1:0:5:6>`
- expected k: [5, 2, 6, 7, 1, 0, 5, 6]
- found k: [0, 1, 2, 6, 5, 7, 5, 6]
- target text: An idea led to paying attention, which became drawn to it, then breaking it down, shaped by experience, practice makes perfect, shaped by experience again, and breaking it down once more.

**id**: `v1mix_cas_to_english_003266` (train)

- source: `Phi<1:9:9:9:9:1:9:3>`
- expected k: [1, 9, 9, 9, 9, 1, 9, 3]
- found k: [0, 1, 2, 3, 4, 5, 6, 7, 9, 1, 9, 9, 9, 9]
- target text: An idea on the mind led to paying attention, then drawn to something, which became an aversion, that struck a chord, shaped who one is, breaking it down, muscle memory took over, and finally something just clicked, then paying attention aga

**id**: `v1mix_cas_to_english_002612` (train)

- source: `Phi<6:3:3:8:0:0>`
- expected k: [6, 3, 3, 8, 0, 0]
- found k: [0, 6, 0, 3, 3, 3]
- target text: A thought that led to unpacking an idea, then rubs the wrong way, which pushed away again, and that triggered something, leading to another thought, and finally an aversion.

**id**: `v1mix_cas_to_english_003407` (train)

- source: `Φ<7:8:2:3:4:0>`
- expected k: [7, 8, 2, 3, 4, 0]
- found k: [0, 2, 3, 4, 7, 8]
- target text: An idea led to becoming aware, which became drawn to it, in turn pushed away, then struck a chord, which became muscle memory, and finally triggered a memory.
