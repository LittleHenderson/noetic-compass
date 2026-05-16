# Stage 6.3 - Full Role-Bound Activation Capture

**Status:** ACTIVATIONS CAPTURED LOCALLY. No probe training and no
mechanistic claim is made by this artifact.

## Purpose

Stage 6.2 locked the full 3,000-row role-bound fixture. Stage 6.3 captures
Pythia-160M hidden states for that fixture using the focus-token extraction
helper pinned in Stage 6.1A.

This stage answers only a plumbing question:

> Can the full locked fixture be passed through Pythia and produce stable
> focus-token, final-token, and mean-pooled activation tensors?

It does not answer whether those activations contain role-bound CAS semantics.
That is the Stage 6.4 probe/evaluation question.

## Command

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\capture_stage6_role_bound_activations.py --input stage6_role_bound_full_20260516.jsonl --out-activations stage6_role_bound_full_activations_20260516.npz --out-manifest stage6_role_bound_full_activations_manifest_20260516.json --device cpu
```

## Runtime

| Item | Value |
|---|---:|
| Device | CPU |
| Rows | 3,000 |
| Elapsed | 271.05 seconds |
| Effective rate | about 11.1 rows/second |

The run used local cached Pythia files. No model download was needed.

## Model Provenance

| Field | Value |
|---|---|
| Model | `EleutherAI/pythia-160m` |
| Revision | `50f5173d932e8e61f858120bcb800b97af589f46` |
| Transformers | `5.8.1` |
| Torch | `2.11.0+cpu` |
| NumPy | `2.3.5` |

The loader reported `embed_out.weight` as an unexpected key. This is the same
informational warning seen in earlier Pythia captures: `GPTNeoXModel` is used
for hidden states and does not need the language-model output head.

## Input Provenance

Input file:

```text
stage6_role_bound_full_20260516.jsonl
```

Input SHA-256:

```text
450086d137396cd9906f8458ab37ead041ead1842fbfa866d47326befd155710
```

This matches the Stage 6.2 locked fixture manifest.

## Output Artifact

Local binary artifact:

```text
stage6_role_bound_full_activations_20260516.npz
```

Output SHA-256:

```text
6641e28519eefeadc66d053c4996075d640401f6f650ef14b80435ccd57206f2
```

File size:

```text
217,947,380 bytes
```

Because this file is larger than GitHub's hard 100 MB per-file limit, the
binary is intentionally not committed. The manifest and this report are
committed, and the artifact can be regenerated with the command above.

## Tensor Shapes

| Array | Shape | dtype |
|---|---|---|
| `X_focus` | `(3000, 13, 768)` | `float32` |
| `X_final` | `(3000, 13, 768)` | `float32` |
| `X_mean` | `(3000, 13, 768)` | `float32` |
| `y` | `(3000,)` | `int64` |
| `sample_ids` | `(3000,)` | `<U75` |
| `focus_token_indices` | `(3000,)` | `int64` |
| `final_token_indices` | `(3000,)` | `int64` |

Class distribution in `y`:

```text
^0 300
^1 300
^2 300
^3 300
^4 300
^5 300
^6 300
^7 300
^8 300
^9 300
```

Focus-token indices range from `16` to `41`. Final-token indices range from
`17` to `42`.

## Boundary

Allowed claim:

> The full Stage 6 role-bound fixture was successfully encoded through
> Pythia-160M, producing focus-token, final-token, and mean-pooled hidden-state
> tensors with the expected shape and class balance.

Not allowed:

- Pythia encodes CAS.
- CAS semantics are proven in the host model.
- The black box issue is solved.
- Glass House AI is validated.

## Next Step

Stage 6.4 should train and evaluate role-bound probes from this activation
artifact. The evaluation must compare against text baselines and metadata
baselines, and it must use the locked test split from Stage 6.2.
