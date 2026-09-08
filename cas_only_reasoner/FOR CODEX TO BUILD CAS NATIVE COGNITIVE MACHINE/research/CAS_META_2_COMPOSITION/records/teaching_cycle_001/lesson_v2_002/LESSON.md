# One complete guided teaching lesson — version 2

This is an exact export of prepared teaching material. It has not been delivered to a neural model. Seven complete stage inputs are shown below; there are no model predictions or learning results here.

## The shared relationship

The required source must reach the correct input role. The source tag identifies what to use; the slot identifies where it is. Moving the source to another slot changes the binding, not the rule.

This role table is teacher/audit explanation, not an extra student input. The exact student inputs are the seven text blocks and the observation rows below.

| Role | Technical | Context | Analogy |
|---|---|---|---|
| receiver | child A argument | workplace receiver | parcel destination |
| source | green triangle | container marked green triangle | parcel marked green triangle |
| connection | slot 1 supplies argument | marked container reaches receiver | addressed parcel reaches destination |

## What the student actually receives

Each stage supplies exactly one `public` object: `problem` contains that stage's text, and `observations` contains the same three rows shown here. The model receives no family ID, stage label, alignment metadata, or practice target through this public-input path.

The solved demonstration uses a different slot arrangement from this practice task. Its answer is explained in the public text. The practice answer stays in the separate training target.

### Observation rows shared by all seven stages

```json
[
  {
    "slot": 0,
    "tag": "violet star",
    "values": [
      -0.360107421875,
      0.07666015625,
      -0.0941162109375,
      -0.317626953125,
      -0.112548828125,
      -0.932861328125,
      -0.9010009765625,
      0.8388671875
    ]
  },
  {
    "slot": 1,
    "tag": "green triangle",
    "values": [
      -0.406005859375,
      0.291015625,
      -0.7379150390625,
      -0.397705078125,
      -0.492431640625,
      -0.0240478515625,
      -0.4503173828125,
      -0.227783203125
    ]
  },
  {
    "slot": 2,
    "tag": "amber circle",
    "values": [
      -0.1114501953125,
      -0.8123779296875,
      -0.55908203125,
      0.8526611328125,
      0.8236083984375,
      -0.587646484375,
      -0.2889404296875,
      -0.4239501953125
    ]
  }
]
```

### 1. name_function

Exact `public.problem` text; full public input length: 277 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. Input binding assigns the required source to child A's argument. Name the source and its role. Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

### 2. context

Exact `public.problem` text; full public input length: 282 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. The workplace may change without changing the source. A changed requested tag can change the source. Which change matters? Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

### 3. analogy

Exact `public.problem` text; full public input length: 284 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. An addressed parcel must reach its destination. Likewise the named observation must reach child A's argument. What is shared? Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

### 4. mapping

Exact `public.problem` text; full public input length: 296 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. Technical, context, analogy: argument, receiver, destination; observation, marked container, marked parcel; binding, delivery, arrival. Keep each role matched one to one. Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

### 5. decomposition

Exact `public.problem` text; full public input length: 291 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. Guided Noetic ^6: separate request, sources, slots and argument. Which dependency breaks if the named source is removed or another is substituted? Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

### 6. recomposition

Exact `public.problem` text; full public input length: 288 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. Rebuild the process: read the request, locate the marked source, connect its slot to the argument, then call the fixed child. Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

### 7. reinforcement

Exact `public.problem` text; full public input length: 288 tokens.

```text
In the school workshop. Choose the observation that supplies child A's argument. Requested source: green triangle. The common rule is unchanged: the intended operation receives the required source in the required role. Repeat this connection across the views. Worked demonstration, separate from practice. Demonstration slot 0: green triangle. Demonstration slot 1: amber circle. Demonstration slot 2: violet star. Demonstration request: green triangle. Worked demonstration answer: BIND0. Match the request tag to its marked source; that demonstration slot supplies A's argument. Removing that source leaves no valid choice; substituting another tag breaks the match. Changing workplace alone changes nothing. End demonstration. Apply the same rule to the actual observations, whose slot order can differ. Your training target concerns those actual observations.
```

## Training-only targets and audit metadata

This section is not part of `public`. Do not feed this Markdown document or the full lesson record to the student as its problem. The adapter extracts only each record's `public` object for prediction.

Practice family: `074a2eaeb97386541b9f0ca445afc383201dd211b00e976fe315fd6c5219bad5`. Fixed child: `A`. Requested source: `green triangle`. Correct practice target: `BIND1`.

The separate solved demonstration has answer `BIND0`. This sample was selected because those answers differ; the renderer was not changed for this sample. Across the curriculum, demonstration and practice answers can also coincide.

The same practice target supervises all seven stage presentations. A training loss can correct a wrong prediction; no prediction or correction has actually been executed by this exporter.

## Intended parameter update path — source inspection, not an executed update

1. [validate_records](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/gpu_adapter.py:87>) checks each full record against the registered training plan, then returns separate public inputs and binding targets.

2. [BindingLearner._logits](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/gpu_adapter.py:173>) calls [encode_batch](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/policy.py:66>) with the lossless tokenizer on CUDA, supplies a single beginning-of-sequence token, and selects only the `BINDING_TOKEN_IDS` logits at decoder position zero.

3. [_ProgramGenerator.embed](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/policy.py:150>) combines word, input-kind, slot, numeric and position representations. The candidate's encoder processes them. [_ProgramGenerator.decode](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/policy.py:161>) combines the token head with the learned `binding_query`/`binding_key` observation pointer.

4. [BindingLearner.teach](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/gpu_adapter.py:188>) computes cross-entropy against the private practice binding, calls `loss.backward()`, checks the admitted parameter scope, and calls `AdamW.step()`. It records nonzero gradients, changed parameter names and before/after tensor identities.

5. [build_matched_learners](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/gpu_adapter.py:303>) creates separate CAS and generic candidates. Its default optimizer receives `model.parameters()`. The admitted scope is the candidate's actual `requires_grad` names; it is not limited to a standalone binding head. Encoder/control parameters, embeddings, decoder and pointer can be eligible. Exact touched names require real training receipts.

Accepted weights and the native executor are not loaded or updated by this adapter. The lesson selects an input for fixed child `A`; it does not prove the child's neural effect.

## What the labels do not establish

`Guided Noetic ^6` in stage five is a textual decomposition lesson. It is not an invocation of native Noetic ^6 execution. A stage label, a valid mapping, a complete export, or a valid trace does not demonstrate language understanding, metaphor understanding, native reasoning, or learning.

## What the separate evaluation splits test

The prepared curriculum contains 256 training families and 64 development families. Development uses fresh instances for readiness/checkpoint selection; it is not the final mastery test.

- `test_fresh`: 64 fresh numeric instances with familiar tags, contexts and task forms.
- `test_context`: 64 unseen irrelevant context combinations made from familiar words.
- `test_names`: 64 unseen color-plus-shape tag combinations made from familiar words.

These are not unseen program compositions. The fixed-child input-binding skill remains the target. Final evaluation receives unassisted public problems, not solved lesson text or training targets.

## Export identity

Repository HEAD inspected: `2a4791d6d0fddd04b23882248c679c03e0fbe92f`. Exact working-source hashes and canonical lesson hashes are in `receipt.json`; this is not a source-freeze or a training receipt.
