# v1e Phase 1B Shadow Eval — Promotion-Gate Analysis

- suite size: 42 records (35 fractal + 7 negative)
- configs: ['A_control', 'B_smoke', 'C_eos_bias', 'D_first_n', 'E_both']

Per-config aggregate (over the 35 fractal records):

| config | sequence_match | cardinality_match | constrained_selected | hard_notation | jargon | truncated |
|---|---:|---:|---:|---:|---:|---:|
| A_control | 0/35 | 7/35 | 0/35 | 0 | 0 | 0 |
| B_smoke | 0/35 | 7/35 | 0/35 | 0 | 0 | 0 |
| C_eos_bias | 0/35 | 7/35 | 0/35 | 0 | 0 | 0 |
| D_first_n | 0/35 | 3/35 | 20/35 | 0 | 0 | 0 |
| E_both | 0/35 | 3/35 | 20/35 | 0 | 0 | 0 |

## Non-fractal drift (negative controls — must byte-match A)

| record_id | subcategory | B_smoke=A? | C_eos=A? | D_firstn=A? | E_both=A? |
|---|---|---|---|---|---|
| v1e_eval_negative_state_literal | state_literal | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_binary_composition | binary_composition | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_cross_register_omega | cross_register_omega | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_recipe | recipe | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_meta_logic_relation | meta_logic_relation | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_rpm_chain | rpm_chain | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_rpm | rpm | ✓ | ✓ | ✓ | ✓ |

## Record 14 prose-quality watch (k=2 `Φ<3:7>`)

Per the audit: 'Record 14 does not lose prose quality.' Below is the final_text + verifier for Record 14 under each config.

- **A_control**: seq_match=False found=[4, 2, 8, 7] text='Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory.'
- **B_smoke**: seq_match=False found=[4, 2, 8, 7] text='Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory.'
- **C_eos_bias**: seq_match=False found=[4, 2, 8, 7] text='Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory.'
- **D_first_n**: seq_match=False found=[7, 7, 4] text=' aversen into a groove led to becoming aware, which then became practice makes perfect, and finally struck a chord.'
- **E_both**: seq_match=False found=[7, 7, 4] text=' aversen into a groove led to becoming aware, which then became practice makes perfect, and finally struck a chord.'

## Lever-individual safety (each lever vs B_smoke)

- **C_eos_bias** vs B_smoke: seq Δ=+0, card Δ=+0, selected_constrained Δ=+0, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **D_first_n** vs B_smoke: seq Δ=+0, card Δ=-4, selected_constrained Δ=+20, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **E_both** vs B_smoke: seq Δ=+0, card Δ=-4, selected_constrained Δ=+20, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0

## Promotion-gate verdict

| config | verdict | notes |
|---|---|---|
| B_smoke | REVIEW | 0 sequence_match delta |
| C_eos_bias | REVIEW | 0 sequence_match delta |
| D_first_n | REVIEW | 0 sequence_match delta |
| E_both | REVIEW | 0 sequence_match delta |

**Note:** "PASS" is a HEURISTIC label, not a hard promotion gate. Per audit 2026-05-10, α/β/γ paths surface to user with empirical data; promotion is a USER decision.