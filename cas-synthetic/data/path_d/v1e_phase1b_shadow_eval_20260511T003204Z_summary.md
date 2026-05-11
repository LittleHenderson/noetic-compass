# v1e Phase 1B Shadow Eval — Promotion-Gate Analysis

- suite size: 42 records (35 fractal + 7 negative)
- configs: ['A_control', 'G_baseline', 'H1_eos5', 'H2_eos8', 'H3_eos10', 'H4_length_cap']

Per-config aggregate (over the 35 fractal records):

| config | sequence_match | cardinality_match | constrained_selected | hard_notation | jargon | truncated |
|---|---:|---:|---:|---:|---:|---:|
| A_control | 0/35 | 7/35 | 0/35 | 0 | 0 | 0 |
| G_baseline | 0/35 | 0/35 | 33/35 | 0 | 0 | 0 |
| H1_eos5 | 0/35 | 0/35 | 33/35 | 0 | 0 | 0 |
| H2_eos8 | 1/35 | 1/35 | 33/35 | 0 | 0 | 0 |
| H3_eos10 | 5/35 | 5/35 | 33/35 | 0 | 0 | 0 |
| H4_length_cap | 0/35 | 0/35 | 33/35 | 0 | 0 | 19 |

## Non-fractal drift (negative controls — must byte-match A)

| record_id | subcategory | G_baseline=A? | H1_eos5=A? | H2_eos8=A? | H3_eos10=A? | H4_length_cap=A? |
|---|---|--- | --- | --- | --- | ---|
| v1e_eval_negative_state_literal | state_literal | ✓ | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_binary_composition | binary_composition | ✓ | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_cross_register_omega | cross_register_omega | ✓ | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_recipe | recipe | ✓ | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_meta_logic_relation | meta_logic_relation | ✓ | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_rpm_chain | rpm_chain | ✓ | ✓ | ✓ | ✓ | ✓ |
| v1e_eval_negative_rpm | rpm | ✓ | ✓ | ✓ | ✓ | ✓ |

## Record 14 prose-quality watch (k=2 `Φ<3:7>`)

Per the audit: 'Record 14 does not lose prose quality.' Below is the final_text + verifier for Record 14 under each config.

- **A_control**: seq_match=False found=[4, 2, 8, 7] text='Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory.'
- **G_baseline**: seq_match=False found=[3, 7, 4, 7] text=' averse in muscle memory led to something that struck a chord, which then became muscle memory again.'
- **H1_eos5**: seq_match=False found=[3, 7, 4, 7] text=' averse in muscle memory led to something that struck a chord, which then became muscle memory again.'
- **H2_eos8**: seq_match=False found=[3, 7, 4, 7] text=' averse in muscle memory led to something that struck a chord, which then became muscle memory again.'
- **H3_eos10**: seq_match=True found=[3, 7] text=' averse in muscle memory '
- **H4_length_cap**: seq_match=False found=[3, 7, 4] text=' averse in muscle memory led to something that struck a chord, which then became'

## Lever-individual safety (each non-control vs A_control)

- **G_baseline** vs A_control: seq Δ=+0, card Δ=-7, selected_constrained Δ=+33, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **H1_eos5** vs A_control: seq Δ=+0, card Δ=-7, selected_constrained Δ=+33, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **H2_eos8** vs A_control: seq Δ=+1, card Δ=-6, selected_constrained Δ=+33, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **H3_eos10** vs A_control: seq Δ=+5, card Δ=-2, selected_constrained Δ=+33, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+0
- **H4_length_cap** vs A_control: seq Δ=+0, card Δ=-7, selected_constrained Δ=+33, hard_notation Δ=+0, jargon Δ=+0, truncated Δ=+19

## Promotion-gate verdict

| config | verdict | notes |
|---|---|---|
| G_baseline | REVIEW | 0 sequence_match delta |
| H1_eos5 | REVIEW | 0 sequence_match delta |
| H2_eos8 | PASS | +1 sequence_match lift |
| H3_eos10 | PASS | +5 sequence_match lift |
| H4_length_cap | REVIEW | 0 sequence_match delta, ⚠ +19 truncation regression |

**Note:** "PASS" is a HEURISTIC label, not a hard promotion gate. Per audit 2026-05-10, α/β/γ paths surface to user with empirical data; promotion is a USER decision.