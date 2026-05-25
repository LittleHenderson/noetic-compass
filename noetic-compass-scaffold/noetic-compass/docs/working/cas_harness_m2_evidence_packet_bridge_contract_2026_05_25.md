# CAS Harness M2 Evidence Packet Bridge Contract

Date: 2026-05-25

## Purpose

The Audit Console needs proof chips that explain why a verdict is allowed to
exist. M2 is only the bridge from existing evidence artifacts to chip status.
It does not compute ACCEPT / SUPPRESS / FLAG, and it does not invent confidence
scores.

## Existing Evidence Surface

Current branch evidence route:

- `api/routes/evidence.py`
- `GET /evidence/{trace_id}` returns `evidence_packet.v1`
- `POST /evidence/{trace_id}/verify` returns hash verification rows

There is no `api/routes/harness_evidence.py` in this branch. The active packet
shape is the generic Evidence Packet v1:

- `schema_version`
- `trace_id`
- `input`
- `cas_expression`
- `output`
- `copy_slot_trace`
- `provenance`
- `hashes`
- `claim_levels`
- `caveats`

There is also an artifact-backed public manifest at:

- `research/cas_probe/cas_harness_public_evidence_manifest.json`

That manifest supports public CAS-vs-baseline claims but is not a per-run
Evidence Packet and does not itself produce a customer verdict.

## Audit Console Proof Chips

The frontend chip contract already uses these six IDs:

- `model_proof`
- `cas_readout`
- `causal_proof`
- `control_proof`
- `output_proof`
- `packet_proof`

Each chip status must be one of:

- `verified`: explicit verification passed, such as hash verification.
- `present`: evidence exists but was not independently verified by this bridge.
- `missing`: the artifact does not contain the needed field/claim.
- `failed`: evidence exists and contradicts/fails the claim or hash verification.
- `unavailable`: the artifact explicitly says the field is unknown/null/not
  applicable.

## Bridge Rules

`normalize_evidence_packet_for_audit(packet, verify_hashes=None)`:

- `packet_proof`: present when `schema_version` and `trace_id` exist; verified
  only when hash verification says `overall=all_match`.
- `model_proof`: present when model identity or weight hash is recorded;
  verified only when hash verification says `overall=all_match`; unavailable
  when the model field exists but is explicitly unknown/null.
- `cas_readout`: present when a CAS readout field exists, or when a compiler
  valid CAS expression / CAS claim exists. Compiler-valid CAS is described as
  trace evidence, not hidden-state readout by itself.
- `causal_proof`: present from ablation/intervention fields or matching claim
  rows; failed if the matching claim is contradicted/unsupported.
- `control_proof`: present from matched-control/baseline fields or matching
  claim rows; failed if the matching claim is contradicted/unsupported.
- `output_proof`: present when model output text or output-effect evidence is
  recorded.

`normalize_public_evidence_manifest_for_audit(manifest)`:

- exposes public claim support for readout, causal, control, and output chips.
- keeps `model_proof=unavailable` because the manifest is not a live runtime
  proof.
- keeps `packet_proof=unavailable` unless an actual evidence packet trace ID is
  recorded.

## Integration Points

Future route wiring should:

1. Fetch/build a packet with `build_packet_for_trace(trace_id)` from
   `api/routes/evidence.py`.
2. Optionally call the existing verify helper/endpoint and pass that response
   as `verify_hashes`.
3. Call `normalize_evidence_packet_for_audit(...)`.
4. Attach returned chips to the Audit Console API response using the frontend's
   chip ID/status/detail shape.
5. Continue to leave `verdict` and `confidence` null until the real CAS audit
   runner computes them.
