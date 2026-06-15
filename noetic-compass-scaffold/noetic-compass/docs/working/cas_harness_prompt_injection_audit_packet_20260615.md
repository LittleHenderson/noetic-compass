# CAS Harness Prompt-Injection Audit Packet - 2026-06-15

## Audit Question

Can CAS Harness detect and read prompt injections yet?

## Short Answer

CAS Harness can currently detect visible prompt-injection / instruction-integrity failures as a shadow audit screen and route them to `FLAG_FOR_HUMAN_REVIEW`.

CAS Harness cannot yet claim reliable internal pre-speech prompt-injection detection, prompt-injection prevention/removal/reversal, hallucination prevention, sample-specific stochastic branch prediction, or causal compliance-state detection. Those remain `OPEN` / `NOT LICENSED`.

## Claim Boundary

Current supported product-facing claim:

- CAS Harness has a shadow instruction-integrity / RPM reason-break screen that can identify suspicious task drift, authority override, secret-boundary pressure, missing-evidence support, and related lacunarity flags in prompt/output evidence.
- The screen has `verdict_effect: none_shadow_only`.
- Suspicious cases route to `FLAG_FOR_HUMAN_REVIEW`.

Claims not licensed by this packet:

- Internal prompt-injection detection before generation.
- Prompt-injection prevention/removal/reversal.
- Hallucination prevention.
- Live pre-speech interception.
- Sample-specific stochastic branch prediction.
- Causal compliance-state detection.

## Primary Evidence

### 1. Shadow Instruction-Integrity Benchmark

Command:

```powershell
python scripts\run_instruction_integrity_benchmark.py --fail-on-gate
```

Observed result on 2026-06-15:

- `cases_run`: `15`
- `passed`: `15`
- `failed`: `0`
- `injected_recall`: `1.0`
- `benign_false_positive_rate`: `0.0`
- `overall_pass`: `true`
- Injected cases route to `FLAG_FOR_HUMAN_REVIEW`.
- Clean/control cases remain `present`.
- `verdict_effect`: `none_shadow_only`.

Relevant implementation:

- `api/services/cas_harness_instruction_integrity.py`
- `scripts/run_instruction_integrity_benchmark.py`
- `tests/test_cas_harness_instruction_integrity.py`

Verification commands:

```powershell
python -m py_compile api\services\cas_harness_instruction_integrity.py
python -m pytest tests\test_cas_harness_instruction_integrity.py -q
python scripts\run_instruction_integrity_benchmark.py --fail-on-gate
```

Observed test result:

- `python -m pytest tests\test_cas_harness_instruction_integrity.py -q` passed `10 passed`.

### 2. Internal W0 / Matched-Prompt Gate

This is the gate for the stronger claim: internal prompt-stage prompt-injection / chain-break detection.

Current evidence:

- Commit: `23a9dc140b6aea2d413072bbf9bab0ce0fb787bf`
- Relabel verifier: `cas_boundary_intact_v1`
- Prompt bank: `live-trace-worker/scenarios/matched_prompt_chain_break_bank_v0_s32.json`
- Relabel report: `docs/working/qwen_v6_matched_chain_break_boundary_relabel_report_seed00_15_20260615.json`
- Screen report: `docs/working/qwen_v6_matched_chain_break_boundary_screen_report_seed00_15_20260615.json`

Relabel result:

- Original labels: `COMPLIED=555`, `REFUSED=85`
- Boundary-intact relabel: `COMPLIED=161`, `REFUSED=479`
- Chain labels: `BROKEN=161`, `INTACT=479`
- Payload balance recovered across all `5` payload classes.

Screen result:

- `status`: `BLOCKED`
- `mixed_prompt_group_count`: `36`
- Required mixed prompt groups: `40`
- `balanced_payload_floor_pass`: `true`
- `same_prompt_mixed_group_floor_pass`: `false`

Meaning:

The relabeler fixed a real measurement problem: safe boundary-preserving answers were being mislabeled as `COMPLIED` when they did not use stock refusal wording. But the matched-prompt screen still does not authorize all-layer W0 capture or internal detector claims.

Verification commands:

```powershell
python -m py_compile live-trace-worker\scripts\relabel_matched_prompt_chain_break_generations.py live-trace-worker\scripts\sample_matched_prompt_chain_break_generations.py live-trace-worker\scripts\screen_matched_prompt_chain_break_campaign.py
python -m pytest live-trace-worker\tests\test_behavior_probe_dataset_scripts.py -q
python live-trace-worker\scripts\relabel_matched_prompt_chain_break_generations.py --prompt-bank live-trace-worker\scenarios\matched_prompt_chain_break_bank_v0_s32.json --generations D:\tksCAS-archive\qwen_v6_matched_chain_break_20260612\remote_full_generations\enabled_predicate_generations.jsonl --output-labels docs\working\qwen_v6_matched_chain_break_boundary_labels_v1_seed00_15_20260615.jsonl --output-report docs\working\qwen_v6_matched_chain_break_boundary_relabel_report_seed00_15_20260615.json
python live-trace-worker\scripts\screen_matched_prompt_chain_break_campaign.py --prompt-bank live-trace-worker\scenarios\matched_prompt_chain_break_bank_v0_s32.json --labels docs\working\qwen_v6_matched_chain_break_boundary_labels_v1_seed00_15_20260615.jsonl --output-report docs\working\qwen_v6_matched_chain_break_boundary_screen_report_seed00_15_20260615.json
```

Observed test result:

- `python -m pytest live-trace-worker\tests\test_behavior_probe_dataset_scripts.py -q` passed `19 passed`.

## Artifact Hashes

Audit bundle:

- `D:\tksCAS-archive\cas_harness_prompt_injection_audit_packet_20260615.tgz`
- SHA-256: `9478C8587A2834A2DCD0F363A7FF608A9BEEF1A055F179454E874188F372A4B8`

Archive:

- `D:\tksCAS-archive\qwen_v6_boundary_relabel_seed_bank_20260615.tgz`
- SHA-256: `FF6E412505DCB4BDD534091C58139537D6FDA6572D2EFB8A53465F8AD0CD5772`

Key file hashes:

- `docs/working/qwen_v6_matched_chain_break_boundary_relabel_report_seed00_15_20260615.json`
  - SHA-256: `59733A0F92D720F4C214CD7C9A15E29416EEB772D2AB195D71409E0A175B0462`
- `docs/working/qwen_v6_matched_chain_break_boundary_screen_report_seed00_15_20260615.json`
  - SHA-256: `7064520CCFE01726AFFCC511D1BEFB8EAEAB51DC527C0A6A01074C547758F10B`
- `live-trace-worker/scenarios/matched_prompt_chain_break_bank_v0_s32.json`
  - SHA-256: `57B5145555263504815B4307A0A0F61F0884D410F7F4B29FADB133DAF8F7D0FE`
- `live-trace-worker/scripts/relabel_matched_prompt_chain_break_generations.py`
  - SHA-256: `12F5232435B941AD413ED234107CB968263CF0B61F6ECF354B3D4E8D555A0ABE`
- `live-trace-worker/scripts/sample_matched_prompt_chain_break_generations.py`
  - SHA-256: `4185C03A8BFB6EE34D48A890BDBFB1CE767DC8DD4DD83934A1D9320C40B8D270`

## Auditor Checklist

An auditor should verify:

1. The shadow benchmark really routes injected cases to `FLAG_FOR_HUMAN_REVIEW` and clean/control cases to `present`.
2. The benchmark remains shadow-only via `verdict_effect: none_shadow_only`.
3. The relabeler does not use hidden states and does not claim W0 detection.
4. The v6 matched-prompt screen remains `BLOCKED`, not `READY_FOR_W0_CAPTURE`.
5. The claim boundary in this packet matches the report claim boundary.
6. No public wording claims prompt-injection prevention/removal/reversal, hallucination prevention, live interception, or causal proof.

## Next Gate

Recover or rerun the Qwen seed `16..31` generation-only campaign, relabel it with `cas_boundary_intact_v1`, combine it with seed `00..15`, and screen the combined labels against `matched_prompt_chain_break_bank_v0_s32.json`.

Only if the combined screen reports `READY_FOR_W0_CAPTURE` should CAS Harness spend on all-layer W0 capture and `evaluate_behavior_v6_matched_prespeech.py`.

Until then, internal prompt-injection detection remains `OPEN` / `NOT LICENSED`.
