# Independent re-run of the input-defect measurement — 2026-09-19

**Why this file exists.** The recorded negative result of commit `857af081` could not be re-checked from the repository,
because the 53 MB cache every analysis script reads (`build2.pkl`) was never committed. The measurement doc says so itself
(`INPUT_DEFECT_MEASUREMENT.md` line 4: "the 53 MB `build2.pkl` cache was not kept"). A claim that cannot be re-checked is a
weak asset. This file records an independent end-to-end re-run and its exact outcome.

**What was run.** The four committed scripts, in order, unmodified, on the same frozen course, from
`records/typed_pointer_001/pre_design/measurements/input_defect/`:

```
python -B build2.py
python -B analyze2.py
python -B analyze2b.py
python -B check_alias_hits.py
```

Python 3.14.0, pure standard library plus the project's pure modules. No torch, no GPU, no network, $0.

**Outcome: the recorded result REPRODUCES.**

| Script | Comparison | Result |
|---|---|---|
| `build2.py` | gate digests, record counts, slot count, row count | **EXACT MATCH** |
| `analyze2.py` → stdout | line-by-line after stripping each line's trailing wall-clock seconds | **IDENTICAL** |
| `analyze2.py` → `analyze2_summary.json` | canonical JSON (sorted keys, compact separators) | **IDENTICAL** (5,424 canonical characters both runs) |
| `analyze2b.py` → stdout | line-by-line after stripping trailing wall-clock seconds | **IDENTICAL** |
| `check_alias_hits.py` → stdout | byte-for-byte | **IDENTICAL** |

**The exact gate line, re-derived:**

```
GATE True projection ('4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9', 3829) readout ('14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667', 90)
```

Both digests equal the published constants in `INPUT_DEFECT_MEASUREMENT.md` line 19-20. Slot count 2,598 and distinct row
count 2,442 also match. Split 127 / 358 / 79 (held / trained / excluded) matches.

**The one honest difference.** The committed `.txt` files are not byte-identical to the re-run because each progress line ends
with elapsed wall-clock seconds, which cannot repeat. Committed `build2_out.txt` records `load s 95.1 … done s 556.1`; this
re-run measured `load s 164.4 … done s 903.2`. Committed `analyze2_summary.json` differs in byte layout only; every key,
array and value is equal after canonicalisation. **No measured number changed.**

**Consequence for the claim.** The negative result stands as recorded:

- 🟥 REAL (negative, measured): for the four per-bit kinds — parts, context, role_set, edge_account — a cross-world linear
  probe fitted on practised worlds scores no better than the held majority on never-practised worlds, and inside a
  random-query null (P from 0.1633 to 0.9833). Held accuracy parts 58.3333 / context 60.2941 / role_set 83.3333 /
  edge_account 73.8971 against majorities 52.7778 / 75.0000 / 83.3333 / 80.1471.
- The published 96.3758 % (context) was exact-name recall: seen names 96.8627–100.0000, unseen names 50.0000.

**Claim-state correction (this re-run, not a new measurement).** Two statements must be kept apart, and the handoff prose
of `857af081` ran them together:

- MEASURED: no transfer to held worlds **for the four per-bit kinds probed**, and any never-seen slot name gets chance,
  whether it sits in a new world or a practised one. The measurement doc states this correctly.
- INFERRED, **not** measured: "impossible for ANY learner, ALL kinds". `INPUT_DEFECT_MEASUREMENT.md` line 168 already marks
  this INFERRED. The four choice kinds (`definition`, `analogy`, `correspondence`, `reach`) were never probed. The handoff
  §3, the memory note and `MACHINE_STATE_001/STATUS.md` should say MEASURED for the four per-bit kinds and INFERRED for the
  general claim. The spec-sheet row at `docs/CAS_HARNESS_SPEC_SHEET.md:1375` is already worded correctly and needs no change.

**Rebuild cost recorded here for the next agent:** 903.2 s for `build2.py` on this machine, 2026-09-19.
