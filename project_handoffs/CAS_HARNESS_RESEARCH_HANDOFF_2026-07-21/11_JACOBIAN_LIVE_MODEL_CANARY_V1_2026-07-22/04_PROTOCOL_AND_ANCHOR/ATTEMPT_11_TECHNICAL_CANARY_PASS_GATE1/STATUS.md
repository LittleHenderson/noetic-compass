# Attempt 11 — RECEIVER-CONFIRMED TECHNICAL CANARY PASS. Gate 1 (0.38) earned.

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT / PRODUCER_TECHNICAL_CANARY_PASS_CANDIDATE / RECEIVER_TECHNICAL_CANARY_PASS_OPERATOR_ATTESTED_PENDING_EXTERNAL_REPRODUCTION / MATHEMATICAL_CONSISTENCY_VERIFIED / RFC3161_ANCHOR_VERIFIED / GATE_1_EARNED_0.38 / SHADOW / NONE / NOT_LICENSED`

## What happened

Attempt 11 (commit `04cd32e7d7bb78832b12a9a746b338b24605839c` — the receiver
GPU-ruler fix on top of the Attempt 10 VJP fix) ran the complete fresh
create-once ceremony and, for the first time in the project's history, BOTH
halves of the canary passed:

- **Producer:** `TECHNICAL_CANARY_PASS_CANDIDATE_PENDING_INDEPENDENT_VERIFICATION`,
  `failed_gates []`, `1248/1248` autograd contract, `213` artifacts,
  execution receipt `96c300fe8381c579533b6f06b578d8510d9ad7a6165131a8018895de9b3d3bf6`.
- **Independent receiver** (torch-free, pinned `/usr/bin/python3.11` + numpy
  1.26.3; re-derives everything from raw artifacts):
  `receiver_status = TECHNICAL_CANARY_PASS_OPERATOR_ATTESTED_PENDING_EXTERNAL_REPRODUCTION`,
  `mathematical_consistency_verified = true`,
  `rfc3161_protocol_anchor_verified = true`,
  `operator_execution_evidence_cross_bound = true`,
  receiver receipt `8744172d7e7418e5c0d97773c95fa683e0bdf3aa1b379139e222bd1e63f67622`.

Identity and anchor:
- Run `jlcv1-rfc3161-2f7f8aa400618cb9692e22a5910d810a38be9f8a4dbaa3eaf1a4f5c327daeed0`
  (fresh nonce `c92af757…`); official dir `cas-jlcv1-official-04cd32e7-2f7f8aa4`
  on pod `zp2s9pscgncn0b` (A40 `GPU-b7638993…`, host identity `d88f4a80…`
  continuous since Attempt 8).
- Real DigiCert RFC3161 anchor: tsq `84c26022…` (105 bytes), tsr `88141b37…`
  (6034 bytes), TSA time `Jul 24 19:27:53 2026 GMT`, status
  `QUERY_NONCE_IMPRINT_POLICY_SIGNATURE_CHAIN_RESPONDER_AND_TRUST_ROOT_VERIFIED`.
- Protocol `051f614c…`; launch config `c2d3cdb6…`; PRE reverify
  `CURRENT_RUNTIME_FILES_MATCH_CAPTURE` (17,007 files / 5.09 GB, main `717d5a15…`);
  POST captured; post-run capture `1b187165…`.

## What earned the pass (the three fixes, in order)

1. **Attempt 9 → functional gate** (owner-directed): `GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT`
   `1e-4 → 5e-4` from the measured forward-vs-reverse floor.
2. **Attempt 10 → local VJP gate** (owner-approved diff): the local VJP scalar
   bilinear metric was ill-conditioned (divided by a random near-zero
   projection); replaced with the well-conditioned adjoint VECTOR check
   (`M^T v` vs the true reverse-mode vector), both local limits `1e-3` from the
   measured `5.35e-4` estimator floor; strictness proven against a 0.5%
   corrupted matrix (`5.1e-3`, fails loudly).
3. **Attempt 11 → receiver GPU ruler** (owner-directed "make the receiver's
   ruler match the producer's ruler"): the receiver compared its NVML-derived
   environment GPU identity against the producer's torch-derived identity with
   exact equality, which can never hold (uuid prefix + CUDA-visible vs board
   total). The receiver now converts its NVML reading to the producer's torch
   representation: uuid exact after stripping the deterministic `GPU-` prefix,
   and CUDA-visible total required `<=` NVML board total.

## Honest boundaries (from the receiver receipt itself)

- `claim_status = NOT_LICENSED`, `execution_mode = SHADOW`, `verdict_influence = NONE`.
- `cryptographic_model_origin_proven = false`; `external_reproduction_verified = false`;
  `provider_state_cryptographically_authenticated = false`. RFC3161 proves the
  protocol payload existed at the timestamp; environment/execution captures are
  operator-retained evidence.
- The pass grants NO semantic, prompt-injection, output-control, universality,
  300B, CJT, RPM, J-Space, or CAS-Ohm license (receipt `technical_only_notice`).

## Score

- **Gate 1 earned: `0.38`** — "a passing technical canary on real weights,
  producer + independent receiver."
- Gate 2 (`0.46`) remains OPEN: small-model semantic authority with matched
  comparisons and honest error bars is separate follow-on work that can now
  begin on this foundation.

Evidence in `evidence/`: producer receipt `96c300fe` + marker, receiver receipt
`8744172d`, anchor receipt `2cd54236`, post-run capture, launch records,
wrapper stdout, PRE reverify.
