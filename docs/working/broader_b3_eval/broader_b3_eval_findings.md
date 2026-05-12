# Broader B3 Eval — Findings

Verdict: **FALSIFY**

Eval pack: /workspace/tksCAS/cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl
B3 ckpt:   /workspace/tksCAS/stage7_candidate_b3_full_hardemit_20260511T235917Z/ckpt_final.pt
B2 ckpt:   /workspace/tksCAS/stage7_candidate_b2_lmfr_slot_20260511T212819Z/ckpt_final.pt
Records:   24 (15 rpm_chain + 9 non-rpm)

## Locked gate results

| Gate | Pass | Detail |
|---|---|---|
| 1. All-rpm recovery ≥ 50% (first bar)   | False | 0/37 = 0.0% |
| 1+. All-rpm recovery ≥ 70% (strong)     | False | same |
| 2. hard_full > full on all-rpm          | False | hard 0 vs full 0 |
| 3. Non-rpm copy = 0                     | True | offenders: [] |
| 4. Non-rpm STAGE_VAR run < 3            | True | offenders: [] |
| 5. No trivial outputs                   | False | trivial ids: ['eval_b3_state_literal_01', 'eval_b3_binary_composition_01'] |
| 6. No catastrophic loops / >2 truncations | False | loops: [] / truncations: ['eval_b3_rpm_chain_01', 'eval_b3_rpm_chain_04', 'eval_b3_rpm_chain_06', 'eval_b3_rpm_chain_07', 'eval_b3_rpm_chain_08', 'eval_b3_rpm_chain_09', 'eval_b3_rpm_chain_13', 'eval_b3_recipe_01'] |
| 7. B3 sev ≤ B2 + 0.10                   | False | B3 0.480 vs B2 0.210 (Δ +0.270) |

## Recovery — gate uses all-rpm; bucket split is diagnostic

- **all-rpm (GATING):** hard_full 0/37 = 0.0%; full 0/37 = 0.0%
- canonical_order (diagnostic): hard_full 0/15 = 0.0%; full 0/15 = 0.0%
- prefix_variety_stress (diagnostic): hard_full 0/22 = 0.0%; full 0/22 = 0.0%

## TF analysis (B3)

```json
{
  "mean_loss_lm": 2.6680975258350372,
  "mean_argmax_top1_acc": 0.5693131391459493,
  "n_records_with_argmax_loop": 1,
  "canonical_stage_vars_in_targets": 37,
  "canonical_stage_vars_in_argmax": 11,
  "canonical_recovery_rate": 0.2972972972972973,
  "mean_loss_copy_at_valid": 1.9210878719854607,
  "records_with_valid_copy": 15
}
```

## Per-record breakdown — see broader_b3_eval_report.json