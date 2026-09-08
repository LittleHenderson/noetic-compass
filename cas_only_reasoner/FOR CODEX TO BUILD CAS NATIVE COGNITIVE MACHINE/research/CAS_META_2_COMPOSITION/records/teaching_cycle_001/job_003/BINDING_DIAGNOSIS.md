# Job003 binding diagnosis — observed behavior and one testable mechanism

Recorded 2026-09-08. This is a read-only source/development diagnosis, not causal proof, a model change, or a new training result. The accepted core, original run, source bundle and teaching allocation are unchanged. No final evaluation-private data, tensor checkpoint payloads, neural/NumPy/SQLite imports, GPU execution or provider calls were used for this diagnosis.

## Exact evidence

Job: `cas-meta2-teaching-20260908052915-8b5df59c`.

Local evidence root:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/job_003`

Files below are relative to that exact root; the archive member names retain their original names.

| Evidence | SHA-256 |
|---|---|
| `launch/result.json` | `c12347f65d38dc883221b9f9ddb48099574c851acc858d6d6444a0eaa2295b76` |
| `launch/partial_collected/complete.json` | `72e855be29eef920df8cf4089b6f81347a9b709a952e7f6d9aff44208e7d97a7` |
| Result archive, key `results/artifacts.zip`, 69,240,408 bytes | `73a1e22bdf011380527d78fd72f2a343bfffa1d302eedffc57b0f5417aa361e9` |
| `evaluation_001/extracted/train/campaign_summary.json` | `26b23bb5f23ca875375797db155e8520b947bf0b4eada71e596a9ec7493e195f` |
| `evaluation_001/extracted/input/source.zip` | `494f44d467a85e2edd54b568cf4b0822db6e25355003a8a6ae8c7d4c09dd8cec` |
| Source ZIP `manifest.json` | `975296defc543e234d4bd09fcf9e46a25dc42792e4cf6aed5ad35332de3167a9` |
| Frozen source map; source commit `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e` | `60340b5865c674cc5558a27da6524928ec0db7042163b1ef031591ad7794555e` |
| Frozen material receipt | `32cfb9183d389a880df49bf35dbda518cfcf277ddaf704d42abb169f9704a256` |
| Training cases | `0ff9a38451aac68ec59fbc49b84cadc3cb6ccb318b4459738fb85c95f0e5c496` |
| Development cases | `45682abc65433707099691c3e849536c06a47c12604022ff97527922e886b667` |
| Source ZIP `wheels/casformer_reference-0.1.0-py3-none-any.whl` | `0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee` |

The gradient/loss inspection checked all 1,587 committed intent/result pairs. For each arm, it checked the latest receipt's raw hash against the summary, the latest metadata's raw hash against that receipt, all committed event raw hashes against metadata history, and each result's intent hash. It did not load `candidate.pt`. The latest receipt identities were:

| Arm | Transaction | Receipt SHA-256 |
|---|---:|---|
| CAS aligned | 9 | `3d06586b6ff761e836f9d53b929fc3998842e007c7dbf51028d76be1e9751c0f` |
| CAS ordinary | 8 | `b17128e411e770e6434bb142797bb7f6c66aa3054fe0b4abfae8ef047c14efbd` |
| Generic aligned | 8 | `b821f6ade330de852bdb048b7a178dad8533029e61b74a3b3ac1e71433473041` |
| Generic ordinary | 8 | `7f8d920e216906c0fecc3a5e583ed23b3b4f9413fcd2a9571330e0fc9e58e40c` |

Events are under `evaluation_001/extracted/train/campaign/<arm>/events/step-XXXXXXXX.{intent,result}.json`. Receipt/metadata files are under the same arm's `journal/txn-XXXXXXXX/` directory.

## Observed symptoms

All four arms completed seven of sixteen allocated epochs. CAS aligned also completed nineteen updates into epoch eight. The wall-time stop was `TEACHING_INCOMPLETE`, not completion of the curriculum. Every arm remained on full teaching assistance. There is no final held-out score or native task-execution result here.

| Candidate | Updates | Epoch 7 mean training cross-entropy | Development e4 / e5 / e6 / e7 |
|---|---:|---:|---|
| CAS aligned | 411 | 1.1056417823 | 21/64, 21/64, 21/64, 21/64 |
| CAS ordinary | 392 | 1.0975690910 | 21/64, 20/64, 21/64, 21/64 |
| Generic aligned | 392 | 0.2944724139 | 21/64, 24/64, 49/64, 42/64 |
| Generic ordinary | 392 | 0.3194685714 | 21/64, 27/64, 32/64, 46/64 |

For three equally likely choices, uniform predictions have cross-entropy `log(3) = 1.0986122887`. CAS is therefore not fitting the guided training targets well either. The bare-development wording shift cannot be the whole explanation. These are observed epoch means, not an independent training-set correctness evaluation. CAS aligned's last partial-epoch loss was 1.0511263609; that partial checkpoint had no development evaluation. Untrained development was not measured, and epochs 1–3 attempted zero development cases.

CAS often picked a single slot: aligned e4 picked slot 1 for all 64 cases, e5/e6 picked slot 2 for all 64, and e7 picked slot 2 for 55 and slot 0 for nine. Ordinary e7 picked slot 2 for all 64. Development targets are balanced at 22/21/21; training targets are 86/85/85. This is not a one-class curriculum.

All 87 named trainable CAS parameter tensors had at least one nonzero gradient on every committed update. Binding-query/key, word embedding, control-adapter and most other tensors changed bytes every update. The two gate `raw_span` tensors changed less often: aligned 64/411 and 41/411; ordinary 38/392 each. Nonzero gradients and byte changes establish active update paths, not useful gradient magnitudes or causation. The receipts contain no gradient norms, measured gate distributions or pointer/base-logit decomposition.

## Static source facts

These line references refer to the exact source ZIP above, not a later working-tree revision.

- `cas_meta2/features_v2.py:132`: tokenization retains problem/tag text, whitespace and punctuation, explicit observation slot identity, and a numeric-values token. Byte fallback avoids an unknown-token collapse; overlength inputs fail rather than truncate.
- `cas_meta2/policy.py:150`: embedding combines word, kind, slot, numeric and position information. `:161` pools each observation's encoded tokens and adds a differentiable slot-pointer score to the three binding-token logits. No static tag erasure, label swap or disconnected pointer was found.
- `cas_meta2/teaching_cycle/gpu_adapter.py:173`: both teaching and prediction use the same BOS-to-three-binding-logits path. Teaching uses cross-entropy; prediction uses argmax. All dropout is zero. `:303` initializes matched candidates with AdamW learning rate **0.003**; `worker.py:135` uses that default.
- `cas_meta2/teaching_cycle/runner.py:292`: development presents bare `make_public(case)`, without teaching text. Training used full guided views. The pure train-only tokenizer reconstruction produced digest `d4a219e9a91516f6174e103533bd4266ab7880692a77d601634c4f018bc8bec4`, vocabulary 427, fitted public views 11,008. Tokenizer fitting is not supervised teaching.
- Exact full-guidance input lengths are 277–296 tokens for aligned and 285 for ordinary. All 64 development inputs are **54 tokens**. Faded/none views exist, but none were delivered in this partial run. Worked-demo answers refer to separately permuted demonstration slots and are not always the actual practice answer.
- `cas_meta2/policy.py:192` initializes saturation as `2.0 * max_length`, with maximum length 512: initial saturation **1024**. The saturation parameter remains trainable; its learned value was not read.
- Inside the pinned reference wheel, `casformer/core.py:663` sums positive per-edge current over all valid keys. This sum is separate from normalized semantic attention. `:930` adds bias/diagnostic terms, and `:933–935` applies a smoothstep gate. `:1017–1019` multiplies the attention effect by that gate inside a tanh difference. The control adapter starts Drive near 1 and summed resistance near 1.1, with learned deviations (`casformer/controls.py`).

## Testable mechanism, not a concluded cause

The code makes gate strength depend on input length. Ignoring initial random deviations, learned changes and bias/diagnostic terms, the nominal calculation is:

`u = ((token_count / 1.1) - 0.01) / (1024 - 0.01); gate = u*u*(3 - 2*u)`.

That gives about 0.15965 at 285 tokens and 0.006672 at 54 tokens, roughly a 24-fold difference. These numbers are an analytic illustration, **not measured GPU gates**. Learned controls may compensate. Tanh bias may further alter sensitivity. The shared decoder also retains ordinary cross-attention, so this gate mechanism alone does not prove that CAS cannot learn the task.

The smallest distinguishing AWS check would restore saved candidates without changing weights, compare the same problems with full teaching text and bare text, and record current/gate/region/attention-effect size plus the base-token and slot-pointer logits. Change only the requested tag, then permute observation slots, and check whether scores follow the correct source. Use matched generic candidates for the same checks. Any backward-only gradient-norm probe would be separate and explicitly recorded; no optimizer update is needed for the first check.

No such GPU diagnosis was executed here. Do not convert this hypothesis into a source change, a lower teaching threshold, an extra paid job, a held-out improvement claim or a redesign of the accepted core.
