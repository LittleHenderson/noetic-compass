# THE CNCM MATHEMATICS LEARNING LEDGER

## 1. What the machine can COMPUTE right now

**Promoted skills: 10** of 10 in the MATH-L0..L4 ladder (store revision 10)

| skill | level | kind | taught by | evidence |
|---|---|---|---|---|
| addition | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | 2af5a78b89889aaf |
| algebra_distribute | MATH-L4 | rewrite_rule | qwen.qwen3-32b-v1:0 | 00bf0a7d14d103d7 |
| counting_order | MATH-L1 | computation | qwen.qwen3-32b-v1:0 | d517779fdffb74ee |
| division | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | dd7fb19bec5c5060 |
| fractions | MATH-L3 | computation | qwen.qwen3-32b-v1:0 | 9560d76f9680d46b |
| integer_comparison | MATH-L1 | computation | qwen.qwen3-32b-v1:0 | 1457bcd5e798436f |
| linear_equations | MATH-L4 | equation_solving | qwen.qwen3-32b-v1:0 | 512689db40e60f45 |
| multiplication | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | 17ecf2fdbb51cf1e |
| quantity_grounding | MATH-L0 | grounding | qwen.qwen3-32b-v1:0 | 62d8d8da005f3e41 |
| subtraction | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | fca715f2380a77c9 |

## 2. LIVE check (run at ledger generation - fresh store load, unseen exercises)

- addition: `6 add 12` -> PASS (answer 18)
- algebra_distribute: `7 * (x + 3)` -> PASS (answer ((7 * x) + (7 * 3)))
- counting_order: `successor` -> PASS (answer 6)
- division: `4 div 1` -> PASS (answer 4)
- fractions: `2/3 add 3/5` -> PASS (answer 19/15)
- integer_comparison: `-3 compare -1` -> PASS (answer less)
- linear_equations: `4 * (z + 1) = 36` -> PASS (answer 8)
- multiplication: `5 mul 3` -> PASS (answer 15)
- quantity_grounding: `scene_count` -> PASS (answer 1)
- subtraction: `7 sub 6` -> PASS (answer 1)

**Capability honesty (empty store):** asked 3+4, an unschooled student answers `CANNOT_MISSING_SKILL` - the exact engine exists, but the STUDENT may only use promoted skills.

## 3. The paper trail

- Sealed lesson artifacts: 10
  - addition: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - algebra_distribute: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - counting_order: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - division: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - fractions: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - integer_comparison: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - linear_equations: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - multiplication: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - quantity_grounding: QUARANTINED_ALREADY_PROMOTED
  - subtraction: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active

Every promotion carries the checker-source digest, provenance, a rollback pointer, and its sealed twelve-step evidence. The protected battery seed never appears in any teacher channel. Nothing enters this ledger by assertion.
