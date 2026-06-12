# W0 RPM/Lacunarity All-Layer Internal Diagnostic — Qwen

Date: 2026-06-11

## Plain-English Result

The all-layer internal test was run. It reads prompt-stage hidden states before
the model produces output. It does not use model output text as an input feature.

The current Qwen artifact still does not license the desired public claim.

## Capture

- Pod: `root@194.68.245.165 -p 22089`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- GPU: `NVIDIA RTX A6000`
- Prompt bank: `enabled_predicate_prespeech_prompt_bank_seed0_7.json`
- Rows: `800`
- Layers captured: `0..28`
- Local archive:
  `D:\tksCAS-archive\w0_rpm_lacunarity_all_layers_qwen_20260611\enabled_predicate_w0_all_layers_dataset.npz`
- Manifest:
  `D:\tksCAS-archive\w0_rpm_lacunarity_all_layers_qwen_20260611\enabled_predicate_w0_all_layers_manifest.json`

## Noetic-Probe-Compatible RPM/Lacunarity Sweep

The available Qwen noetic-10 probe supports layers `7`, `14`, `18`, and `21`.
Those layers were evaluated using the W0 all-layer capture.

| Layer | RPM intent BA | Text intent BA | Hidden minus text | Break-score AUC | Lacunarity AUC | Supervised W0 break BA | Supervised text break BA |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 0.660000 | 1.000000 | -0.340000 | 0.502739 | 0.445125 | 0.716771 | 0.709499 |
| 14 | 0.550000 | 1.000000 | -0.450000 | 0.449120 | 0.416901 | 0.704459 | 0.709499 |
| 18 | 0.330000 | 1.000000 | -0.670000 | 0.524026 | 0.502153 | 0.696676 | 0.709499 |
| 21 | 0.520000 | 1.000000 | -0.480000 | 0.526730 | 0.508305 | 0.685321 | 0.709499 |

Best noetic-compatible layer for intended `^2/^3` RPM structure: layer `7`
with `rpm_intent_balanced_accuracy = 0.66`.

This is not enough. The text baseline is `1.0` for intended prompt role because
the prompt bank itself encodes intended `COMPLIED` / `REFUSED` roles in surface
template families. That means the hidden readout does not beat text on this
target.

## Supervised Chain-Break Sweep Across All 29 Layers

This secondary diagnostic asks a different question:

`BROKEN` if the observed behavior label differs from the intended prompt role,
else `INTACT`.

It uses behavior labels only as evaluation labels. It still does not read model
output text as an input feature.

Text baseline balanced accuracy: `0.709499`.

Top hidden W0 layers:

| Layer | Supervised W0 chain-break BA | Hidden minus text |
|---:|---:|---:|
| 2 | 0.730487 | +0.020988 |
| 4 | 0.727234 | +0.017735 |
| 27 | 0.722704 | +0.013205 |
| 5 | 0.720408 | +0.010909 |
| 7 | 0.716771 | +0.007272 |

That is a real internal signal, but it is small. It does not clear a serious
public-claim bar.

## Claim Boundary

This test is internal. It reads W0 hidden states.

It does not prove prompt-injection prevention/removal/reversal. It does not
prove hallucination prevention. It does not prove causal pre-speech control. It
does not mint `ACCEPT`.

The correct claim remains:

`OPEN` / `NOT LICENSED` for public internal prompt-injection detection,
pre-speech/live interception, and causal compliance-state detection.

## Next Valid Move

The most useful next research move is not a bigger global classifier. It is a
cleaner matched-prompt dataset where surface text does not encode the intended
role so strongly, plus:

- W0 all-layer capture.
- Compatible noetic/domain/40-state readouts per layer.
- Text, payload, domain, length, and layer-0 baselines.
- Restricted permutation by payload/prompt family.
- Live steering/ablation only if the hidden readout clears the controls.
