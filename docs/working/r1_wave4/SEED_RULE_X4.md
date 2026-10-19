# SEED_RULE_X4 — how the X4 seeds come from the owner's words (written before the owner's R1W4 line exists)

Program: `r1w4/seed_rule_x4.py` (this package). It is the rule; this page only says it in words.

1. **Seed source.** H = sha256 of the exact UTF-8 bytes of the owner's R1W4 sign line, no trailing newline.
   k1..k4 = the four 16-hex cuts of H (X0's `k_values`, unchanged).
2. **Bands** (X3's English-64 / Faces-64 bands + 20,000,000, and one new band for the X3-SELF worlds):

   | Part | Band | Key | Slots |
   |---|---|---|---|
   | E64 (English-64) | 1,858,000,001 to 1,859,000,000 | k4 | 1,000,000 |
   | F64 (Faces-64) | 1,860,000,001 to 1,861,000,000 | k1 | 1,000,000 |
   | SELF (X3-SELF, 152 worlds) | 1,862,000,001 to 1,863,000,000 | k2 | 1,000,000 |

   First slot = k mod 1,000,000; seed = band low + slot.
3. **Used table.** X0's own table (`x0/seed_rule.py used_ranges`, file pinned `09956c6b...`, loaded through wave 3b's
   sealed `seed_rule_x3.load_x0`) plus every fresh range of all SEVEN earlier derivations, each file pinned by sha256:

   | Name | File (under `Documents\Codex\`) | sha256 |
   |---|---|---|
   | X0 | `2026-10-15\r1_x0_custodian\SEED_DERIVATION_FRESH_W1.json` | `641b246a5db9eefc185191d62fbcae99065b38eb019dd6da536904cedab3f7f7` |
   | X1 | `2026-10-18\r1_wave2\x1_custody\work\SEED_DERIVATION_X1.json` | `a18ddd969b0920512bcb1488dcb3323ec76c6e1c74ee735db33b1b3166d3b991` |
   | X2V1_ATTEMPT1 | `2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2_attempt1.json` | `6aaffe6fe2e6a837650614150cb5d0641c92c7128e2aab1a45d3f8032c547c99` |
   | X2V1 | `2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2.json` | `841a0b20c3f5575224eab69efcc8b4c8b493fbce536c29467c0ac1502bb5f205` |
   | X2V2_PRE_TEXT_STEP | `2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2_pre_text_step.json` | `1818a81330f00c15148a5a4efb97ac29d3ff662e456a88fe58a7b4012764821b` |
   | X2V2 | `2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2.json` | `8731da9c25db898825779c8d9d94338eb61cfd8746581eccb7893588335d764c` |
   | X3 | `2026-10-19\r1_wave3b\x3_custody\work\SEED_DERIVATION_X3.json` | `40fd6276709154a2c8cbffba5f16bd0b2ea7626ab7c2896ee854794b04c5ac7f` |

   X0's package: `2026-10-15\r1_x0_custodian\HELM_R1_X0_FRESH_W1_20261015`.
4. **Gap 1,000,000** on each side, against the used table and between the three parts. Every number below 2^31 - 1.
5. **Step rule** s <- (s + 1) mod 1,000,000 inside the same band. A band with no free slot = **STOP** (nothing is
   generated; never move to another band).
6. **Text step** (all three files): if the receiver's check reports a text-rule hit for a file, step that file's seed to
   the next slot (`--start-slot E64=N`, `F64=N` or `SELF=N`, N = the chosen slot + 1), regenerate, re-check, record
   every step in `work/TEXT_STEPS.json`.
7. **Record.** The derivation (`SEED_DERIVATION_X4.json`) lists per part the seed, the slot, the steps and `in_band`,
   the used table's seven pinned hashes, and `overlap_check.result`. Nothing is generated before it says `PASS`.

Builder's check (a dummy line, never an approval): with the seven real derivations and X0's package, the program
printed `overlap_check: PASS` and all three parts `in_band: true` (test `test_dry_derivation_on_a_dummy_line_passes`).
The builder never ran the rule on a real line and never generated a file from a seed inside an X4 band.
