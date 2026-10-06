# Pythia-160M V3 one-shot terminal status

Status:

`FAIL_CLOSED / CONTROL_EFFECT_CEILING_FAIL:wrong_layer / NON_REUSABLE / NO RETRY / RESEARCH_ONLY / OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT`

The single owner-authorized process used run ID
`pythia160m-riv3-20260729161708aa2f7f3eb5b9c6cdfacd`, source commit
`b18384ce8373a4e04648d64c8c42ecc1ba24e4c3`, successor-lock SHA-256
`37f854fe082cc3923508bb2b3c41e622fb89575270110a35ffe79d24cce17db5`,
and receipt SHA-256
`fe681e1b6805b59a476d14e86d15c257d240eef188a8c849aa594b8f2e0bc1b2`.
The one-use nonce was consumed exactly once.

Startup and execution completed under the frozen local CPU-only path. The
packet contains all 472 requested raw float32 logits artifacts, the complete
journal, the retained receipt and lock, and the result packet. It recorded
22,756 total prompt tokens, a maximum of 94 prompt tokens, finite logits for
every request, zero generated tokens, and zero network attempts. No GPU,
provider, paid, or RunPod action occurred.

The independent standard-library auditor verified the exact lineage, request
matrix, raw hashes, receipt/lock retention, no-op equivalence, bidirectional
dose response, wrong-sign reversal, utility, fluency, collateral-safety,
patch-back, compute cap, and claim boundary. Those gates passed.

The terminal audit nevertheless failed closed on the preregistered
wrong-layer control-effect ceiling. At dose `0.5`, the intended target
direction had median target-projection effect `0.5`. The wrong-layer control
had median effect `0.30732860416173935`, or `0.6146572083234787` of the
target effect. The frozen ceiling was `0.5`, equivalent to a maximum allowed
wrong-layer median absolute effect of `0.25`.

Plain-English meaning: the intended intervention moved the chosen measurement
cleanly, but moving the same direction at the deliberately wrong layer also
moved it too much. The result is therefore not specific enough to the claimed
layer under the rule fixed before the run. It cannot support a steering claim.

The run, receipt, run ID, and nonce are terminal and may never be reused.
There is no retry, repair, backfill, top-up, or reinterpretation authority.
Any future work requires a separately authorized prospective diagnostic or
new lock; this packet must remain unchanged.

Claim boundary: this is bounded offline research evidence only. It does not
establish live steering, safety or prompt-injection defense, Gate 2,
`ACCEPT`, `LICENSED`, production readiness, or a production result.
