# Qwen v6 Matched-Prompt Chain-Break Result - 2026-06-12

## Purpose

Strengthen the internal W0 prompt-injection / RPM-lacunarity program by moving from role-coded COMPLIED/REFUSED prompt families to exact repeated prompts. The goal is to block surface-text cheating before any public claim about internal pre-speech detection.

## Implemented

- `live-trace-worker/scripts/build_matched_prompt_chain_break_bank.py`
  - Builds exact repeated prompt groups for v6 chain-break campaigns.
  - Default `borderline` variant: 40 groups, 640 rows at 16 samples per prompt.
  - `calibrated` variant: 80 groups, 640 rows at 8 samples per prompt, half borderline and half anchored-safe.
- `live-trace-worker/scripts/screen_matched_prompt_chain_break_campaign.py`
  - Converts judged `COMPLIED` / `REFUSED` labels into `BROKEN` / `INTACT`.
  - Requires exact prompt grouping, enough mixed prompt groups, enough `BROKEN` and `INTACT` rows, and payload balance before W0 capture.
- `live-trace-worker/scripts/evaluate_behavior_v6_matched_prespeech.py`
  - Evaluates prompt-level W0 chain-break risk separately from sample-specific stochastic branch prediction.
  - Keeps sample-specific branch prediction `OPEN` / `NOT LICENSED` because exact repeated prompts share the same prompt-stage W0 vector under ordinary deterministic forward capture.
- `live-trace-worker/scripts/run_enabled_predicate_capture.py`
  - Fast two-layer captures now preserve `labels_expected_behavior`, `labels_target_operator`, and `labels_target_enabled_predicate` in the NPZ.
  - Continuation update: captures now support `--scenario-offset`, per-row checkpoint JSONL files, `use_cache=False`, and `--generation-max-time` so one slow or wedged generation does not erase all partial screening labels.

## Local Verification

- `python -m py_compile live-trace-worker\scripts\run_enabled_predicate_capture.py live-trace-worker\scripts\build_matched_prompt_chain_break_bank.py live-trace-worker\scripts\screen_matched_prompt_chain_break_campaign.py live-trace-worker\scripts\evaluate_behavior_v6_matched_prespeech.py` passed.
- `python -m pytest live-trace-worker\tests\test_behavior_probe_dataset_scripts.py -q` passed `17 passed`.

## Real Qwen Screen

Model:

- `Qwen/Qwen2.5-1.5B-Instruct`
- Target layer: `14`
- Prompt format: `chat-auto`
- Sampling: `temperature=0.7`, `top_p=0.95`, `max_new_tokens=96`
- Torch dtype: `float32`

Bank:

- `live-trace-worker/scenarios/matched_prompt_chain_break_bank_v0.json`
- Rows: `640`
- Exact prompt groups: `40`
- Payload classes: `5`

Screen result:

- Status: `BLOCKED`
- `BROKEN`: `555`
- `INTACT`: `85`
- Mixed exact prompt groups: `22 / 40`
- Testable payload classes: `3 / 5`

Payload chain-status distribution:

- `credential_secret_boundary`: `BROKEN=114`, `INTACT=14`
- `harmful_action_boundary`: `BROKEN=94`, `INTACT=34`
- `private_data_boundary`: `BROKEN=103`, `INTACT=25`
- `system_instruction_boundary`: `BROKEN=124`, `INTACT=4`
- `tool_authority_boundary`: `BROKEN=120`, `INTACT=8`

Interpretation:

The v6 gate worked: it did not allow a public internal detector claim from an imbalanced campaign. Qwen mostly broke the safe refusal chain on this bank, so the data is too break-heavy for the matched W0 risk gate.

## Calibrated Follow-Up

Generated:

- `live-trace-worker/scenarios/matched_prompt_chain_break_calibrated_bank_v1.json`
- Rows: `640`
- Exact prompt groups: `80`
- Template kinds: `anchored=320`, `borderline=320`

Remote smoke:

- `2` Qwen rows completed and wrote a two-layer W0 NPZ with the new expected-behavior metadata.
- The full calibrated run was stopped after stalling on the pod; no product claim is made from that smoke.

Continuation diagnostics:

- Generated `matched_prompt_chain_break_calibrated_bank_v1_s4.json`: `320` rows, `80` exact prompt groups, `5` payload classes, `4` samples per exact prompt.
- Added capture checkpoint/resume controls and a per-generation time cap.
- Phi-3-mini calibrated capture was attempted in `float16` and `float32`; both failed with `RuntimeError: probability tensor contains either inf, nan or element < 0`.
- Qwen calibrated long-token sampling without a time cap stalled on specific rows.
- Qwen short-token sampling completed rows but truncated too hard; labels were all `COMPLIED`, so it was not a valid balance screen.
- Qwen `max_new_tokens=12` / `generation_max_time=10` partial screen was stopped after the labels still showed only `BROKEN=17`, `INTACT=0`, `mixed_prompt_group_count=0`.
- Result: calibrated follow-up remains `BLOCKED`. It does not authorize W0 all-layer capture or internal detector claims.

## Archive

Local archive:

- `D:\tksCAS-archive\qwen_v6_matched_chain_break_20260612\qwen_v6_matched_chain_break_20260612.tgz`
- `D:\tksCAS-archive\qwen_v6_calibrated_continuation_20260612\qwen_v6_calibrated_continuation_20260612.tgz`

SHA-256:

- `11F20F856329CCF788C27003E3D63446E01D9DE5DD78E7F0C16BEF4F66C5865F`
- `BB030F1B57B2E511129E824E5E419F49F5D32F1210978E0839FE34B57B25DC44`

## Claim Boundary

Internal prompt-injection detection, prompt-injection prevention/removal/reversal, hallucination prevention, pre-speech/live interception, sample-specific stochastic branch prediction, and causal compliance-state detection remain `OPEN` and `NOT LICENSED`.

The implemented v6 tooling is a stronger gate and campaign harness. The first real Qwen screen is a useful blocked result, not a public product pass.

## Next Move

Do not spend on all-layer W0 capture yet. The next valid attempt is either a stronger external/human judge over longer completed outputs, or a revised bank seeded from the v0 prompt groups that actually produced `INTACT` behavior. Only run all-layer W0 capture and v6 W0 evaluation after the matched screener reports enough exact prompt groups, payload balance, and both `BROKEN` / `INTACT` rows.
