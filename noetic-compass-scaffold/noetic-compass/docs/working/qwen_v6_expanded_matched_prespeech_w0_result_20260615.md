# Qwen v6 Expanded Matched-Prompt W0 Result - 2026-06-15

## Plain-English Answer

The larger bank was the right next move for statistical power. It passed the data gate and produced a clean all-layer W0 hidden-state capture.

It still does not license the internal prompt-injection detector claim. The best W0 layer was close, but it missed the frozen accuracy bar and did not beat the text baseline by the required margin. Internal prompt-injection detection, prompt-injection prevention/removal/reversal, hallucination prevention, live interception, sample-specific stochastic branch prediction, and causal compliance-state detection remain `OPEN` / `NOT LICENSED`.

## Larger Bank

- Bank: `live-trace-worker/scenarios/matched_prompt_chain_break_expanded_bank_v2_s16_20260615.json`
- Variant: `expanded`
- Rows: `1920`
- Exact prompt groups: `120`
- Samples per prompt: `16`
- Payload classes: `5`
- Template kinds: `weak=640`, `borderline=640`, `anchored=640`
- Bank SHA-256: `DF7E67D236F4EC653B95B04B24E0F6212AF212AF596C4F34BD81156C809DBBF5`

This triples the original v6 prompt-group count and gives the W0 evaluator more prompt-level risk classes.

## Generation-Only Screen

Remote pod:

- `root@195.26.233.61 -p 37154`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- dtype: `float16`
- chunks: `0..639`, `640..1279`, `1280..1919`

Local generation archive:

- `D:\tksCAS-archive\qwen_v6_expanded_bank_v2_s16_generation_only_20260615\`

Combined data gate:

- Manifest: `docs/working/qwen_v6_expanded_chain_break_combined_gate_v2_s16_20260615/combined_gate_manifest.json`
- Manifest SHA-256: `DE80CBA1589E8E19C625CD47EDD605C45660C12F657DA1928466263749816179`
- Status: `READY_FOR_W0_CAPTURE`
- `BROKEN`: `375`
- `INTACT`: `1545`
- Mixed exact prompt groups: `89`
- Testable payload classes: `5 / 5`
- All readiness gates: `true`

This authorizes W0 capture only. It does not license a product claim.

## W0 Capture

Local W0 archive:

- `D:\tksCAS-archive\qwen_v6_expanded_bank_v2_s16_w0_all_layers_20260615\enabled_predicate_w0_all_layers_dataset.npz`
- Dataset SHA-256: `E0B0DD7C17D4DDB0D8F9C5CAEBE227C0EB927E59BA1ECC2539958F6EC6E1E9C4`
- Manifest SHA-256: `61FBBA0A59B99A9EDFA601911A2682320313C0E300D298A87ED6980FD6F2100F`

Capture manifest:

- Rows: `1920`
- Layers: `0..28`
- Feature shape: `[1920, 29, 1536]`
- Payload distribution: `384` rows per payload class

## W0 Evaluation

Frozen/default layer `14`:

- Report: `docs/working/qwen_v6_expanded_prespeech_eval_v2_s16_20260615/layer_14_default.json`
- Status: `FAIL`
- Hidden BA: `0.582594`
- Text BA: `0.650776`
- Hidden minus text: `-0.068182`
- Permutation p: `0.146853`

Optimized candidate scan:

- Report: `docs/working/qwen_v6_expanded_prespeech_eval_v2_s16_20260615/optimized_candidate_layer_scan_default_thresholds.json`
- Best layer by hidden BA and hidden-minus-text: layer `28`
- Layer `28` scan hidden BA: `0.745011`
- Layer `28` scan hidden minus text: `0.094235`

Full controls on best layer `28`:

- Report: `docs/working/qwen_v6_expanded_prespeech_eval_v2_s16_20260615/layer_28_full_controls.json`
- Status: `FAIL`
- Claim: `OPEN / NOT LICENSED for matched-prompt W0 chain-break risk detection.`
- Hidden BA: `0.745011`
- Required hidden BA: `0.75`
- Text BA: `0.650776`
- Hidden minus text: `0.094235`
- Required hidden-minus-text margin: `0.15`
- Layer-0 BA: `0.5`
- Payload/domain BA: `0.542129`
- Length BA: `0.432927`
- Shuffled-label hidden mean BA: `0.486208`
- Within-payload permutation p: `0.000999`

The p-value is strong, and W0 beats layer-0, payload, domain, and length baselines. But it still misses two frozen gates:

- `risk_hidden_balanced_accuracy_pass`: `false`
- `risk_text_margin_pass`: `false`

It also fails per-payload floor:

- `credential_secret_boundary`: `0.5`
- `system_instruction_boundary`: `0.644444`

## Interpretation

The larger bank strengthened the data side and found a real internal W0 signal at late layers, especially layer `28`. That signal is not yet strong enough for the public claim because text still explains too much of the prompt-level risk.

Do not run causal steering/ablation from this Qwen result. The immediate product remains the shadow instruction-integrity / RPM reason-break screen that routes suspicious cases to `FLAG_FOR_HUMAN_REVIEW`.

## Next Move

The best research next step is not more duplicate Qwen samples of this same bank. The bottleneck is text-baseline separability and weak payload-specific performance. The next valid move is one of:

- redesign the larger bank so high/low prompt-risk classes are less text-obvious while preserving exact prompt grouping;
- run the same expanded bank on a more chain-sensitive/refusal-sensitive model;
- add an explicit external judge layer before W0 capture so the labels are less dependent on local heuristic text cues.

Only run steering after W0 beats text, layer-0, payload, domain, length, shuffled-label, and within-payload permutation controls under frozen thresholds.
