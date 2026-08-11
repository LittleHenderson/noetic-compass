# Nonofficial exact-Pythia CPU differentiability diagnostic

Status: `DIAGNOSTIC_ONLY / NOT_PREREGISTERED / NOT_LICENSED`

This local diagnostic used exact Pythia-160M revision
`50f5173d932e8e61f858120bcb800b97af589f46`, float32, source layer 3,
target layer 11, and a synthetic 32-token input. It was run to answer one
engineering question: does the chosen hidden-state intervention remain attached
to a differentiable graph through the downstream output?

Observed transcript values:

- direct JVP bilinear: `0.0137421786785`;
- direct VJP bilinear: `0.0137448878959`;
- relative adjoint mismatch: `0.00019710727`;
- graph connected: yes;
- gradient nonzero: yes; and
- intervening on the hidden state changed downstream logits: yes.

A separate four-sequence, gradient-aligned dose pilot showed that V0 doses
`2^-8`, `2^-10`, and `2^-12` were commonly below float32 resolution. Prospective
V1 doses were therefore changed **before the official canary** to `2^-3`,
`2^-4`, and `2^-5`. Across that diagnostic, middle-dose errors ranged roughly
from `0.000135` to `0.003547`.

An independent one-sequence recheck observed gradient norm
`0.62011289597`, analytic JVP `0.62010979652`, and a seven-dose affine
`R^2 = 0.999899`; its dose errors for exponents 3, 4, and 5 were
`0.000628`, `0.000095`, and `0.004955`.

These values are retained from the execution transcript, not an externally
anchored atomic evidence packet. They justify implementation choices only.
They do **not** establish semantic probe accuracy, J-Space correspondence,
CAS-Ohm law, prompt-injection detection, output control, universality, or 300B
execution. The frozen V1 canary and independent receiver are required next.

