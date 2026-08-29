# THE CNCM MATHEMATICS LEARNING LEDGER

## 1. What the machine can COMPUTE right now

**Promoted skills: 24** of 24 in the MATH-L0..L10 ladder (store revision 24)

| skill | level | kind | taught by | evidence |
|---|---|---|---|---|
| addition | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | 2af5a78b89889aaf |
| algebra_distribute | MATH-L4 | rewrite_rule | qwen.qwen3-32b-v1:0 | 00bf0a7d14d103d7 |
| axiom_commutativity | MATH-L9 | rewrite_rule | qwen.qwen3-32b-v1:0 | 864687de31146a6b |
| axiom_square_expand | MATH-L9 | rewrite_rule | qwen.qwen3-32b-v1:0 | 3fe126354c8c7f22 |
| conjecture_discovery | MATH-L10 | discovery | qwen.qwen3-32b-v1:0 | d119957e5cbcdba9 |
| coordinate_slope | MATH-L5 | computation | qwen.qwen3-32b-v1:0 | 77d323efad956ed3 |
| counting_order | MATH-L1 | computation | qwen.qwen3-32b-v1:0 | d517779fdffb74ee |
| derivatives_polynomial | MATH-L7 | computation | qwen.qwen3-32b-v1:0 | 08f7356a03d4e8c3 |
| division | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | dd7fb19bec5c5060 |
| formal_proofs | MATH-L9 | proof_search | qwen.qwen3-32b-v1:0 | fb2e6e821408b282 |
| fractions | MATH-L3 | computation | qwen.qwen3-32b-v1:0 | 9560d76f9680d46b |
| functions_evaluation | MATH-L5 | computation | qwen.qwen3-32b-v1:0 | 375d7d5e18772a2c |
| geometry_points | MATH-L6 | computation | qwen.qwen3-32b-v1:0 | 80b313fefeff8b49 |
| geometry_shapes | MATH-L6 | computation | qwen.qwen3-32b-v1:0 | e9b3a3710f7b9a1a |
| integer_comparison | MATH-L1 | computation | qwen.qwen3-32b-v1:0 | 1457bcd5e798436f |
| integrals_polynomial | MATH-L7 | computation | qwen.qwen3-32b-v1:0 | 3f2e8c024430173e |
| linear_equations | MATH-L4 | equation_solving | qwen.qwen3-32b-v1:0 | 512689db40e60f45 |
| matrices_2x2 | MATH-L8 | computation | qwen.qwen3-32b-v1:0 | 0f360eb4f0a88930 |
| multiplication | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | 17ecf2fdbb51cf1e |
| probability_finite | MATH-L8 | computation | qwen.qwen3-32b-v1:0 | f6e8e3f14fc566e2 |
| quantity_grounding | MATH-L0 | grounding | qwen.qwen3-32b-v1:0 | 62d8d8da005f3e41 |
| sequences | MATH-L7 | computation | qwen.qwen3-32b-v1:0 | e4d5bb1a2ef27d9d |
| statistics_basic | MATH-L8 | computation | qwen.qwen3-32b-v1:0 | 1c1ec0f8e9657372 |
| subtraction | MATH-L2 | computation | qwen.qwen3-32b-v1:0 | fca715f2380a77c9 |

## 2. LIVE check (run at ledger generation - fresh store load, unseen exercises)

- addition: `6 add 12` -> PASS (answer 18)
- algebra_distribute: `7 * (x + 3)` -> PASS (answer ((7 * x) + (7 * 3)))
- axiom_commutativity: `x + y` -> PASS (answer (y + x))
- axiom_square_expand: `(x + 1)^2` -> PASS (answer (x^2 + (2 * x * 1) + 1^2))
- conjecture_discovery: `discovery_round` -> PASS (answer discovery_verified)
- coordinate_slope: `slope` -> PASS (answer 1)
- counting_order: `successor` -> PASS (answer 6)
- derivatives_polynomial: `6 * x^3 + 9 * x^2 + 9 * x` -> PASS (answer (9 + (18 * x) + (18 * x^2)))
- division: `4 div 1` -> PASS (answer 4)
- formal_proofs: `prove` -> PASS (answer proved)
- fractions: `2/3 add 3/5` -> PASS (answer 19/15)
- functions_evaluation: `func_eval` -> PASS (answer 18)
- geometry_points: `midpoint` -> PASS (answer 5/2,-1)
- geometry_shapes: `['-3', '3'] tri_area ['-1', '3']` -> PASS (answer 2)
- integer_comparison: `-3 compare -1` -> PASS (answer less)
- integrals_polynomial: `4 * x + 5` -> PASS (answer -1)
- linear_equations: `4 * (z + 1) = 36` -> PASS (answer 8)
- matrices_2x2: `mat_det` -> PASS (answer 18)
- multiplication: `5 mul 3` -> PASS (answer 15)
- probability_finite: `prob` -> PASS (answer 1)
- quantity_grounding: `scene_count` -> PASS (answer 1)
- sequences: `seq_term` -> PASS (answer 41)
- statistics_basic: `stat_mean` -> PASS (answer 0)
- subtraction: `7 sub 6` -> PASS (answer 1)

**Capability honesty (empty store):** asked 3+4, an unschooled student answers `CANNOT_MISSING_SKILL` - the exact engine exists, but the STUDENT may only use promoted skills.

## 3. The paper trail

- Sealed lesson artifacts: 24
  - addition: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - algebra_distribute: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - axiom_commutativity: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - axiom_square_expand: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - conjecture_discovery: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - coordinate_slope: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - counting_order: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - derivatives_polynomial: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - division: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - formal_proofs: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - fractions: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - functions_evaluation: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - geometry_points: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - geometry_shapes: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - integer_comparison: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - integrals_polynomial: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - linear_equations: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - matrices_2x2: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - multiplication: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - probability_finite: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - quantity_grounding: QUARANTINED_ALREADY_PROMOTED
  - sequences: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - statistics_basic: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active
  - subtraction: PROMOTED | CAS-Ohm P_cap 0.0 -> 1.0, flow cutoff -> active

Every promotion carries the checker-source digest, provenance, a rollback pointer, and its sealed twelve-step evidence. The protected battery seed never appears in any teacher channel. Nothing enters this ledger by assertion.
