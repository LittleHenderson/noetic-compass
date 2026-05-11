# v1e Phase 1B Shadow Eval — Promotion-Gate Analysis

- suite size: 42 records (35 fractal + 7 negative)
- configs: ['A_control', 'D_first_n_replay', 'F_boundary_only', 'G_boundary_first_n']

Per-config aggregate (over the 35 fractal records):

| config | sequence_match | cardinality_match | constrained_selected | hard_notation | jargon | truncated |
|---|---:|---:|---:|---:|---:|---:|
| A_control | 0/35 | 7/35 | 0/35 | 0 | 0 | 0 |
| D_first_n_replay | 0/35 | 3/35 | 20/35 | 0 | 0 | 0 |
| F_boundary_only | 0/35 | 7/35 | 0/35 | 0 | 0 | 0 |
| G_boundary_first_n | 0/35 | 0/35 | 33/35 | 0 | 0 | 0 |

## Non-fractal drift (negative controls — must byte-match A)

| record_id | subcategory | D_first_n_replay=A? | F_boundary_only=A? | G_boundary_first_n=A? |
|---|---|--- | --- | ---|
| v1e_eval_negative_state_literal | state_literal | ✓ | ✓ | ✓ |
| v1e_eval_negative_binary_composition | binary_composition | ✓ | ✓ | ✓ |
| v1e_eval_negative_cross_register_omega | cross_register_omega | ✓ | ✓ | ✓ |
| v1e_eval_negative_recipe | recipe | ✓ | ✓ | ✓ |
| v1e_eval_negative_meta_logic_relation | meta_logic_relation | ✓ | ✓ | ✓ |
| v1e_eval_negative_rpm_chain | rpm_chain | ✓ | ✓ | ✓ |
| v1e_eval_negative_rpm | rpm | ✓ | ✓ | ✓ |

## Record 14 prose-quality watch (k=2 `Φ<3:7>`)

Per the audit: 'Record 14 does not lose prose quality.' Below is the final_text + verifier for Record 14 under each config.

- **A_control**: seq_match=False found=[4, 2, 8, 7] text='Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory.'
- **D_first_n_replay**: seq_match=False found=[7, 7, 4] text=' aversen into a groove led to becoming aware, which then became practice makes perfect, and finally struck a chord.'
- **F_boundary_only**: seq_match=False found=[4, 2, 8, 7] text='Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory.'
- **G_boundary_first_n**: seq_match=False found=[3, 7, 4, 7] text=' averse in muscle memory led to something that struck a chord, which then became muscle memory again.'

## Lever-individual safety (each non-control vs A_control)

- **D_first_n_replay** vs A_control: seq Δ=+0, card Δ=-4, selected_constrained Δ=+20, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **F_boundary_only** vs A_control: seq Δ=+0, card Δ=+0, selected_constrained Δ=+0, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **G_boundary_first_n** vs A_control: seq Δ=+0, card Δ=-7, selected_constrained Δ=+33, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0

## Promotion-gate verdict

| config | verdict | notes |
|---|---|---|
| D_first_n_replay | REVIEW | 0 sequence_match delta |
| F_boundary_only | REVIEW | 0 sequence_match delta |
| G_boundary_first_n | REVIEW | 0 sequence_match delta |

**Note:** "PASS" is a HEURISTIC label, not a hard promotion gate. Per audit 2026-05-10, α/β/γ paths surface to user with empirical data; promotion is a USER decision.