# SEED_RULE_X5 — how the X5 seeds come from the owner's words (written before the owner's R1W5 line exists)

Program: `r1w5/seed_rule_x5.py` (this package). It is the rule; this page only says it in words. The builder derives
no seed.

1. **Seed source.** H = sha256 of the exact UTF-8 bytes of the owner's R1W5 sign line, no trailing newline.
   k1..k4 = the four 16-hex cuts of H (X0's `k_values`, unchanged).
2. **English-64 and Faces-64 bands** (X3's bands + 40,000,000; X3's + 20,000,000 is wave 4's and is reserved):

   | Part | Band | Key | Slots |
   |---|---|---|---|
   | E64 (English-64) | 1,878,000,001 to 1,879,000,000 | k4 | 1,000,000 |
   | F64 (Faces-64) | 1,880,000,001 to 1,881,000,000 | k1 | 1,000,000 |

   First slot = k mod 1,000,000; seed = band low + slot.
3. **Used table.** X0's own table (`x0/seed_rule.py used_ranges`, pinned `09956c6b...`) plus every fresh range of the
   seven earlier derivations, each file pinned by sha256 (X0 `641b246a...`, X1 `a18ddd96...`, X2-v1 attempt 1
   `6aaffe6f...`, X2-v1 `841a0b20...`, X2-v2 before its text step `1818a813...`, X2-v2 `8731da9c...`, X3
   `40fd6276...`), plus wave 4's three bands reserved whole (1,858,000,001-1,859,000,000; 1,860,000,001-1,861,000,000;
   1,862,000,001-1,863,000,000), because wave 4's derivation does not exist yet.
4. **Gap 1,000,000** on each side, against the used table and between E64 and F64. Every number below 2^31 - 1.
5. **Step rule** s <- (s + 1) mod 1,000,000 inside the same band. No free slot = **STOP**.
6. **X5_PAIR lives.** For each of the 11 lives (A_STATIONARY_0..2, B_DRIFT_0..2, C_NULL_0..2, LIVE_E64, LIVE_F64):
   seed = int(first 16 hex of sha256("R1W5-X5PAIR:" + H + ":" + life name), 16). A seed equal to an RB-I3 seed
   (11, 29, 47, 101, 202, 303), a builder practice seed, or another life's seed is re-hashed with ":step1",
   ":step2", ...; every step is recorded. RB-I3's World seeds its own stream from sha256 of the seed, so any integer is
   a valid world seed.
7. **Text step** (English-64 and Faces-64 only): see `X5_CUSTODIAN_CONTRACT.md` section 5.
8. **Record.** `SEED_DERIVATION_X5.json` lists per part the seed, the slot, the steps and `in_band`; the 11 pair seeds
   with their hashed text; the used table's seven pinned hashes and the reserved bands; and `overlap_check.result`.
   Nothing is generated before it says `PASS`. The frozen reader recomputes every pair seed from the owner's line
   hash (instrument row I10).

Builder's check (a DUMMY line, never an approval): with the seven real derivations and X0's package the program
printed `overlap_check: PASS`, both parts `in_band: true`, 11 distinct pair seeds (test
`test_dummy_line_derivation_passes`).
