# SEED_RULE_XREAL — how the X-REAL seeds come from the owner's words (written before the owner's line exists)

Program: `xreal/seed_rule_xreal.py` (this package). It is the rule; this page only says it in words.

1. **Seed source (A-XR-18).** The owner pre-approved X-REAL with a line that names no package hash ("I PRE-APPROVE
   BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.").
   The seed text is that verbatim line + ":" + the full sha256 (64 lower-case hex) of the FINAL sealed X-REAL zip;
   H = sha256 of the seed text's UTF-8 bytes (no trailing newline). k1..k4 = the four 16-hex cuts of H (X0's `k_values`, X0's `seed_rule.py` pinned `09956c6b...`, unchanged).
2. **Bands** (each 1,000,000 wide, all above X5's E64 1,878,000,001-1,879,000,000 and F64 1,880,000,001-1,881,000,000,
   and X4's 1,858-1,863 million):

   | Part | What it seeds | Band | Key |
   |---|---|---|---|
   | XS | Part S sample | 1,898,000,001 to 1,899,000,000 | k4 |
   | XA | Part R-ASIS sample (and its B pairing) | 1,900,000,001 to 1,901,000,000 | k1 |
   | XB | Part R-REBOUND sample (and its B pairing) | 1,902,000,001 to 1,903,000,000 | k2 |
   | XF | Part F world choice and every fault choice (file, line, offset, code page) | 1,904,000,001 to 1,905,000,000 | k3 |

   First slot = k mod 1,000,000; seed = band low + slot.
3. **Used table.** X0's own table plus every fresh range of the nine earlier derivations, each file pinned by sha256:
   X0 `641b246a...`, X1 `a18ddd96...`, X2V1_ATTEMPT1 `6aaffe6f...`, X2V1 `841a0b20...`, X2V2_PRE_TEXT_STEP `1818a813...`,
   X2V2 `8731da9c...`, X3 `40fd6276...`, X4 `77efc1ac...`, X5 `100354cf...` (full hashes in `xreal/common_xr.py`).
4. **Gap 1,000,000** on each side, against the used table and between the four X-REAL seeds (the R1W2-A1 lesson).
   Every number below 2^31 - 1.
5. **Step rule** s <- (s + 1) mod 1,000,000 inside the same band. A band with no free slot = **STOP** (exit 4,
   `XREAL_BLOCKED_SEED.json`; nothing is sampled; never move to another band) (R1W3-A1 / R1W3-A2.1-c practice).
6. **No text step.** Unlike X1-X5 there is no generator to re-seed: items are replaced one by one by hash rank
   (`rank = sha256("XREAL:" + part + ":" + seed + ":" + item id)`), each skip recorded with its reason from the closed
   list {PERSONAL_DATA, FORBIDDEN_TEXT, PRACTICE, NO_PAIR, DUPLICATE_TEXT}.
7. **Record.** `SEED_DERIVATION_XREAL.json` lists per part the seed, the slot, the steps and `in_band`, the used table's
   nine pinned hashes, and `overlap_check.result`. Nothing is sampled before it says `PASS`.

Builder's check (dummy inputs, never an approval): `tests_xreal.test_units_xr.TestSeedRule` derives four in-band,
distinct seeds and proves a fully used band STOPs; the laptop check with the nine real derivation files on a dummy line
is recorded in `TEST_COUNTS_XREAL.json` (`overlap_check: PASS`, no sample drawn).
