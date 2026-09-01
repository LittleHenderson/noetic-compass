# CJT-DEV-P1.1 diagnostic findings — why the v1 pilot plateaued at ~0.21

Development-only, non-claim-bearing. One cloud T4 run (562.8s,
`i-0a7840fe7f1e41f59`, self-terminated). Raw numbers:
`DIAGNOSTIC_RESULTS.json`.

## Causal picture (in order of importance)

1. **The machinery is healthy.** Diagnostic B: the S3 head memorizes 128
   passages to accuracy **1.000** (loss 9e-06). Head, optimizer, and candidate
   scorer are not defective.
2. **The learned attention is collapsed and dead.** Diagnostic G: mean
   normalized attention entropy **0.0** — α is one-hot on a single clause —
   and that clause is the gold clause only **23.7%** (val) / **27.0%** (train)
   of the time, barely above random clause-picking. Diagnostic F explains why:
   the attention query gradient `w_q_grad_norm` ≈ **1e-17 → 0** — the softmax
   saturated early and the routing never learned. This is exactly the
   pathology the P1.2 routing repair (`s_content + λ·s_profile`) addresses.
3. **The profile channel is inert in the v1 architecture.** Diagnostic F:
   true = uniform = permuted = zeroed-W_p, all 0.211–0.212 val accuracy
   (`w_p` grads ~3–5e-4). This mechanically explains every S3=S6=S7-Δ tie in
   the v1 pilot: the network ignored the dashboard it was shown after the
   turn was already taken.
4. **Fixing attention alone buys +0.036.** Diagnostic D (gold-clause oracle,
   100% gold resolution — 6082 unique + 918 tiebreak, 0 unresolved):
   0.248 vs 0.212. **Contextual candidate grounding buys +0.031**
   (Diagnostic E: 0.243 vs 0.212; D+E combined 0.239, not additive under the
   old head). Both repairs are licensed; neither approaches B0 = 0.668 — the
   answer-binding readout (pooled clause vector → context-free/contextual
   candidate dot-product) remains the deeper ceiling.
5. **Cross-family transfer costs ~0.03–0.07, not the whole gap.**
   Diagnostic C: in-distribution holdout 0.237 (no-profile) / **0.278**
   (CAS profile) vs cross-family val 0.211 / 0.210. Two reads: (a) even
   in-distribution the head reaches only ~0.28 ≪ B0, so generalization of the
   binding readout — not the zero-verb-overlap transfer — is the primary
   bottleneck; (b) the CAS profile DID help in-distribution (+0.042 over
   no-profile, ~2.3 SE on n=600 — suggestive, not decisive) and the advantage
   evaporates cross-family.

## Repair adopted for the five-arm relaunch (licensed by the ruling)

- **RoutedHead** (mandated, P1.2 §8): `s_i = (W_q g·W_k h_i)/√d +
  λ·(W_r g·p_i)`, λ learned from 0 — the profile now participates in Idea
  *selection*; identical mechanism for S3/S6/S7-H/S7-Δ; S0 capacity-matched.
- **Contextual candidates for ALL arms equally** (licensed by Diagnostic E's
  jump), extracted per candidate layer in one pass.
- Nothing else changed: same data, seeds, optimizer, batch size, updates,
  checkpoints, B0/B1 references, dev-status law extended to all four controls.

Honest expectation set by Diagnostic D: with the binding readout unrepaired,
absolute accuracies likely stay well under B0; the experiment's information is
in the BETWEEN-ARM differences the routing architecture can now express.
