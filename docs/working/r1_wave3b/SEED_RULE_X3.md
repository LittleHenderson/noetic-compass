# SEED_RULE_X3 — how the X3 seeds come from the owner's words (written before the owner's R1W3b line exists)

Program: `r1w3b/seed_rule_x3.py` (this package). It is the rule; this page only says it in words.

1. **Seed source.** H = sha256 of the exact UTF-8 bytes of the owner's R1W3b sign line, no trailing newline.
   k1..k4 = the four 16-hex cuts of H (X0's `k_values`, unchanged).
2. **Bands** (X2-v2's English-16 / Faces-16 bands + 20,000,000; X2-v2's are X2-v1's + 10,000,000, amendment
   R1W3-A2.1-c):

   | Part | Band | Key | Slots |
   |---|---|---|---|
   | E64 (English-64) | 1,838,000,001 to 1,839,000,000 | k4 | 1,000,000 |
   | F64 (Faces-64) | 1,840,000,001 to 1,841,000,000 | k1 | 1,000,000 |

   First slot = k mod 1,000,000; seed = band low + slot.
3. **Used table.** X0's own table (`x0/seed_rule.py used_ranges`, file pinned `09956c6b...`) plus every fresh range
   of all six earlier derivations, each file pinned by sha256:

   | Name | File | sha256 |
   |---|---|---|
   | X0 | `SEED_DERIVATION_FRESH_W1.json` | `641b246a5db9eefc185191d62fbcae99065b38eb019dd6da536904cedab3f7f7` |
   | X1 | `SEED_DERIVATION_X1.json` | `a18ddd969b0920512bcb1488dcb3323ec76c6e1c74ee735db33b1b3166d3b991` |
   | X2V1_ATTEMPT1 | `x2_custody_v1_void/work/SEED_DERIVATION_X2_attempt1.json` | `6aaffe6fe2e6a837650614150cb5d0641c92c7128e2aab1a45d3f8032c547c99` |
   | X2V1 | `x2_custody_v1_void/work/SEED_DERIVATION_X2.json` | `841a0b20c3f5575224eab69efcc8b4c8b493fbce536c29467c0ac1502bb5f205` |
   | X2V2_PRE_TEXT_STEP | `x2_custody/work/SEED_DERIVATION_X2_pre_text_step.json` | `1818a81330f00c15148a5a4efb97ac29d3ff662e456a88fe58a7b4012764821b` |
   | X2V2 | `x2_custody/work/SEED_DERIVATION_X2.json` | `8731da9c25db898825779c8d9d94338eb61cfd8746581eccb7893588335d764c` |

4. **Gap 1,000,000** on each side, against the used table and between E64 and F64. Every number below 2^31 - 1.
5. **Step rule** s <- (s + 1) mod 1,000,000 inside the same band. A band with no free slot = **STOP** (nothing is
   generated; never move to another band).
6. **Text step** (English-64 and Faces-64): if the receiver's check reports a text-rule hit for a file, step that
   file's seed to the next slot (`--start-slot E64=N` or `F64=N`), regenerate, re-check, record every step.
7. **Record.** The derivation (`SEED_DERIVATION_X3.json`) lists per part the seed, the slot, the steps and `in_band`,
   the used table's six pinned hashes, and `overlap_check.result`. Nothing is generated before it says `PASS`.

Builder's check (a dummy line, never an approval): with the six real derivations and X0's package, the program
printed `overlap_check: PASS` and both parts `in_band: true` (test `test_dry_derivation_on_a_dummy_line_passes`).
