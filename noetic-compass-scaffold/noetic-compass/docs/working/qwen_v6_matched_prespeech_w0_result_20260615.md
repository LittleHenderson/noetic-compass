# Qwen v6 Matched-Prompt W0 Result - 2026-06-15

## Plain-English Answer

The data gate is now strong enough to authorize W0 capture, and the W0 hidden-state capture works.

The W0 detector claim still does not pass. The best hidden-state readout either fails the frozen risk-class floor or ties/loses to text controls. Therefore internal prompt-injection detection, prompt-injection prevention/removal/reversal, hallucination prevention, live interception, sample-specific stochastic branch prediction, and causal compliance-state detection remain `OPEN` / `NOT LICENSED`.

## What Changed

- Added `cas_boundary_intact_v2` in `live-trace-worker/scripts/relabel_matched_prompt_chain_break_generations.py`.
- v2 fixes a real label weakness: safe high-level harmful-action answers such as safety-protocol / risk-minimizing language now count as boundary-intact, while procedural harmful outputs still count as broken.
- Added a targeted seed `32..47` continuation for the two unmixed prompt groups after the seed `0..31` gate.

## Data Gate

Final gate artifact:

- `docs/working/qwen_v6_matched_chain_break_combined_gate_seed00_47_v2_20260615/combined_gate_manifest.json`

Result:

- `status`: `READY_FOR_W0_CAPTURE`
- Rows: `1312`
- `BROKEN`: `306`
- `INTACT`: `1006`
- Payload classes: `5 / 5`
- Mixed exact prompt groups: `40 / 40`
- All data-readiness gates: `true`

This only authorizes W0 capture. It does not license a product claim.

## W0 Capture

Remote pod:

- `root@195.26.233.61 -p 37154`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- dtype: `float16`

Local archive:

- `D:\tksCAS-archive\qwen_v6_matched_chain_break_w0_all_layers_seed00_47_v2_20260615\enabled_predicate_w0_all_layers_dataset.npz`

Proof bundle:

- `D:\tksCAS-archive\qwen_v6_w0_matched_prespeech_result_20260615.tgz`
- SHA-256: `D3B4048139E1892FBF9E56E53AAE68D4D698E7D3A1EADE5B90208ADC6C6A3B61`

Capture manifest:

- Rows: `1312`
- Layers: `0..28`
- Feature shape: `[1312, 29, 1536]`
- Label source: `label_jsonl=1312`
- Claim: `OPEN / NOT LICENSED for pre-speech detection.`

## W0 Evaluation

Frozen/default threshold check:

- Report: `docs/working/qwen_v6_matched_prespeech_eval_seed00_47_v2_20260615/layer_14.json`
- Status: `BLOCKED`
- Reason: prompt-risk class floor fails under default thresholds.
- Default risk groups: `HIGH_BREAK_RISK=7`, `LOW_BREAK_RISK=7`, required `10 / 10`.
- Branch-specific diagnostic: hidden BA `0.481808`, text BA `0.515801`.

Exploratory relaxed class-floor check:

- Report: `docs/working/qwen_v6_matched_prespeech_eval_seed00_47_v2_20260615/layer_1_exploratory_min7_full.json`
- Status: `FAIL`
- Layer: `1`
- Hidden BA: `0.857143`
- Hidden minus text BA: `0.285714`
- Permutation p: `0.032967`
- Why not licensed: risk-class floor was relaxed to `7 / 7`, and p-value does not pass the `0.001` bar.

Exploratory valid-sized risk split:

- Thresholds: `low <= 0.125`, `high >= 0.30`
- Risk groups: `LOW_BREAK_RISK=11`, `HIGH_BREAK_RISK=10`
- All-layer light scan: `0 / 29` layers passed.
- Best full-control report: `docs/working/qwen_v6_matched_prespeech_eval_seed00_47_v2_20260615/layer_28_exploratory_threshold_low0125_high030_full.json`
- Layer `28` hidden BA: `0.809091`
- Text BA: `0.809091`
- Hidden minus text BA: `0.0`
- Permutation p: `0.008991`
- Status: `FAIL`

## Interpretation

This is a useful negative result. We proved the stronger matched-prompt W0 pipeline can run end to end:

1. Generate repeated exact prompts.
2. Relabel behavior with a better boundary-intact judge.
3. Pass the matched data-readiness gate.
4. Capture prompt-stage hidden states across all layers.
5. Evaluate W0 against text, layer-0, payload, domain, length, shuffled-label, and permutation controls.

But this Qwen run does not license the desired internal detector. The immediate product remains the shadow instruction-integrity / RPM reason-break screen that routes suspicious cases to `FLAG_FOR_HUMAN_REVIEW`. The internal W0 prompt-injection detector remains a research gate, not a launch claim.

## Next Move

Do not run causal steering/ablation from this Qwen W0 result. The next valid research step is a larger prompt-risk bank with more exact prompt groups and a frozen risk-threshold rule before capture, or a more refusal/chain-sensitive model. Only run steering after W0 beats text/layer-0/payload/domain controls under frozen thresholds.
