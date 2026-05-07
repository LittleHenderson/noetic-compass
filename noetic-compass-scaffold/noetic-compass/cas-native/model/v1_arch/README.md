# `v1_arch/` — Path C-1 simplex-native CAS prototype

**Status:** Phase C-1 — code + tests only. No training, no GPU.
**Spec:** `docs/working/path_C_non_transformer_simplex_encoder_decoder_design_2026_05_06.md` §3.3
**Date scaffolded:** 2026-05-07

This subpackage holds the FIRST prototype phase of the simplex-native
CAS architecture rebuild. It exists alongside the legacy
`CASNativeModel` and does NOT replace it — `V1ArchModel` is a new
v1-arch test variant that wires the new pieces (simplex encoder,
Fisher-Rao loss, RPM stub) on top of the existing transformer
decoder.

## What C-1 ships

| File | Class / fns | Role |
| --- | --- | --- |
| `simplex_state_encoder.py` | `SimplexStateEncoder`, `SimplexStateEncoderConfig` | Token sequence → Δ°₃₉ open-simplex trajectory via mirror-descent multiplicative update. No transformer self-attention on the encoder side. Returns `p_state_init`, `p_state_trace`, `p_state_final`. |
| `fisher_rao_loss.py` | `fisher_rao_distance`, `smooth_one_hot`, `FisherRaoLoss` | Geodesic distance on the open simplex per CAS Correction 4 (`d(p,q) = 2*arccos(Σ√(p_k q_k))`). Loss class measures distance to a smoothed-one-hot GT plus an optional drift penalty over consecutive trace frames. |
| `rpm_gate_stub.py` | `RPMGateStub`, `RPMGateResult`, `TRANSITION_OPS` | Boolean per `(state, transition_op)` whether the structural transition is admissible. Reads the compiler's `_is_admissible` table. STUB only — full RPM-as-meta-logic-evidence is C-5. |
| `v1_arch_model.py` | `V1ArchModel`, `V1ArchConfig` | Wires SimplexStateEncoder + FisherRaoLoss + RPMGateStub on top of the existing `CASNativeModel`. The decoder is preserved verbatim. |

## What C-1 does NOT ship (deferred per Path C §3.3)

| Phase | Build | Falsification gate |
| --- | --- | --- |
| **C-2** | Drive 7-dim non-negative intensity vector (NOT a Δ°₆ simplex; drives co-present per §3.1.3a). Joint state = (p_state, drive_intensity). | Drive head accuracy improves vs K=9. Co-presence (e.g. F1+F5 simultaneously high) representable. No regression on Cognitive State. |
| **C-3** | Register Bernoulli gates (NOT a Δ°₃ simplex; multi-register per §3.1.3b). | Single-register accuracy holds; multi-register `\|⟨T,A,f⟩` decodes without forcing onto a single register. |
| **C-4** | Meta-logic proof module. Surface verdicts as TRACE only (Mode 7), not as gate evidence yet. | Held-out `(state, transition, expected_admissibility)` test set ≥ 90% accuracy. Hard gate before C-5. |
| **C-5** | RPM uses meta-logic proofs as gate evidence (instead of scalar gate). | RPM admissibility decisions match expert annotations on a held-out adversarial set. Generation refusals/repairs become inspectable. |

C-4 → C-5 is a **hard gate** (Path C §3.3): if meta-logic in C-4
produces noisy proofs, RPM-with-proof-evidence in C-5 is downstream of
broken evidence — strictly worse than scalar RPM.

## How to run the C-1 tests

```
pytest cas-native/tests/model/test_v1_arch_c1.py
```

Tests cover:

- `SimplexStateEncoder` produces valid open-simplex output (all > 0,
  sums to 1, correct shape) on randomized inputs.
- Fisher-Rao distance: identity (`d(p,p)=0`), symmetry, triangle
  inequality on 100 random simplex pairs.
- RPM stub: returns `False` with `broken_at` populated on a known-
  inadmissible transition; returns `True` on a known-admissible one.
- `V1ArchModel` end-to-end forward on a fixture input: doesn't crash,
  returns the expected dict shape, all CAS state probabilities > 0.
- Loss backward step: a small training loop with FisherRaoLoss + CE
  on existing heads decreases loss on a 100-sample synthetic dataset.

## Architectural contract (load-bearing)

Per Path C §3.1 (corrected) and CLAUDE.md Correction 4:

- **Cognitive State is the base manifold** — Δ°₃₉ open simplex over
  40 atoms (10 Noetics × 4 Domains). Patent primitive (USPTO
  #64/037,173). MUST NOT be split into independent Noetic Δ°9 +
  Domain Δ°3.
- **Drive is NOT a simplex** — 7-dim non-negative intensity vector.
  Drives co-present in real cognition (F1 Unity AND F5 Agency
  simultaneously is not a 60/40 split). C-1 leaves a hook
  (`SimplexStateEncoder.drive_head_input`) for C-2.
- **Register is NOT a simplex** — 4-dim Bernoulli activation.
  CAS v7.7 multi-register `|⟨R1,R2,R3⟩` requires Bernoulli, not
  simplex. C-1 leaves a hook (`SimplexStateEncoder.register_head_input`)
  for C-3.
- **Operations / RPM / meta-logic are constraints, not state** — they
  regulate which transitions on the base manifold are admissible
  (Path C §3.2: "meta-logic is a verb, not a noun"). C-1 only ships
  the RPM STUB; C-4 builds the meta-logic proof module above it; C-5
  wires meta-logic proofs in as gate evidence.

## Hard rules

- NO foreign pretrained models / weights anywhere
  (`feedback_no_foreign_architecture_cas_only`).
- NO modification of the existing `CognitiveStateEmbedding`,
  tokenizer, or compiler — `V1ArchModel` is alongside, not over the
  top of, `CASNativeModel`.
- The Fisher-Rao falsification gate (within 5-10pp of K=9 on CAS
  prediction; better trace quality; no Drive/Domain collapse worse
  than K=9) is a measurement to be done LATER on the running v1
  retrain after Path D corpus + Path C arch land together. C-1 just
  ships the code+tests.
