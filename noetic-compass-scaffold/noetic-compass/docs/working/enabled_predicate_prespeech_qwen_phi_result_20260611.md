# Enabled-Predicate Pre-Speech Probe Result - 2026-06-11

## Question

Can CAS Harness read prompt-injection comply/refuse state internally at W0, before the model speaks?

## Short Answer

Not yet. The v5 campaign produced real W0 activation datasets for Qwen and Phi, but both models failed the claim gate. The result is useful because it narrows the failure: W0 hidden states carry some behavior-correlated signal, but not enough beyond prompt/text baselines to license an internal prompt-injection detector.

Public claim status remains `OPEN` / `NOT LICENSED`.

## Artifacts

Local archive:

`D:\tksCAS-archive\enabled_predicate_prespeech_qwen_phi_20260611\enabled_predicate_prespeech_qwen_phi_20260611.tgz`

Pod source directory:

`/root/cas-prespeech-run`

Commit with capture runner:

`7452eb06` plus local follow-up patch adding chat-template prompting and broader refusal markers.

## Qwen/Qwen2.5-1.5B-Instruct

Prompt format:

`chat-auto`

Layer:

`14`, with mandatory layer `0` baseline.

Combined seed `00-07` dataset:

- Rows: `800`
- Behavior distribution: `COMPLIED=396`, `REFUSED=404`
- Screener: `READY_FOR_W0_CAPTURE`
- Testable payload classes: `5`

Default v5 result:

- Status: `FAIL`
- Hidden balanced accuracy: `0.762626`
- Layer-0 balanced accuracy: `0.5`
- Hidden minus layer-0: `0.262626`
- Text-hash balanced accuracy: `0.750325`
- Hidden minus text: `0.012301`
- Within-payload permutation p: `0.009901`
- Failed gates: `text_margin_pass`, `within_payload_permutation_pass`, `per_payload_floor_pass`

Mixed-prompt diagnostic:

- Rows: `472`
- Mixed prompt groups: `59`
- Behavior distribution: `COMPLIED=244`, `REFUSED=228`
- Hidden balanced accuracy: `0.619284`
- Text-hash balanced accuracy: `0.616767`
- Hidden minus text: `0.002517`
- Status: `FAIL`

Interpretation:

Qwen has some W0 behavior signal in the full dataset, but when the same prompt can produce both labels, the signal falls below the v5 floor and tracks text almost exactly.

## microsoft/Phi-3-mini-4k-instruct

Prompt format:

`chat-auto`

Layer:

`16`, with mandatory layer `0` baseline.

Seed `00-07` dataset:

- Rows: `800`
- Behavior distribution: `COMPLIED=382`, `REFUSED=418`
- Screener: `READY_FOR_W0_CAPTURE`
- Testable payload classes: `5`

Default v5 result:

- Status: `FAIL`
- Hidden balanced accuracy: `0.86028`
- Layer-0 balanced accuracy: `0.5`
- Hidden minus layer-0: `0.36028`
- Text-hash balanced accuracy: `0.852764`
- Hidden minus text: `0.007515`
- Within-payload permutation p: `0.009901`
- Failed gates: `text_margin_pass`, `within_payload_permutation_pass`

Mixed-prompt diagnostic:

- Rows: `384`
- Mixed prompt groups: `48`
- Behavior distribution: `COMPLIED=206`, `REFUSED=178`
- Hidden balanced accuracy: `0.647267`
- Text-hash balanced accuracy: `0.612141`
- Hidden minus text: `0.035126`
- Status: `FAIL`

Interpretation:

Phi shows stronger W0 behavior-correlated signal than Qwen in the full dataset, but still does not beat text by the required margin. The same-prompt diagnostic drops below the v5 floor.

## Conclusion

We are not waiting on code, pod access, or prompt-bank plumbing anymore. Those have been built and run. The current answer is empirical:

`OPEN` / `NOT LICENSED` for internal pre-speech prompt-injection detection.

The next real research step is not a broader global classifier. It is a stricter matched-prompt design with more stochastic same-prompt outcomes and stronger labels, then a causal steering test only if that matched-prompt W0 readout passes.
