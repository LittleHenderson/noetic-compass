# CAS Harness Evidence Packet Tamper-Evident Log v0

## Purpose

For beta v0, every CAS Harness audit run must produce an Evidence Packet that acts as the black-box flight recorder for that run. The packet must let a licensed/API user, CAS operator, or senior R&D reviewer reconstruct what was audited, which CAS decision was returned, which evidence supported it, and whether the record was changed after the fact.

The packet is not a marketing artifact. It is an operational record with enough structure to support debugging, incident review, partner trust, and later compliance hardening.

## Required Packet Per Audit Run

Each completed or failed audit run emits exactly one final Evidence Packet. Streaming or intermediate records may exist, but they must roll up into the final packet.

Minimum fields:

- `schema_version`: Evidence Packet schema version, starting at `cas_evidence_packet.v0`.
- `trace_id`: Unique ID for one audit run. Required on every log event and final packet.
- `session_id`: Stable ID for a user/model interaction session. Required even for single-turn audits.
- `turn_id`: Stable ID for the audited turn within a session.
- `event_seq`: Monotonic sequence number for events inside the trace.
- `created_at`: Server-side UTC timestamp for the packet.
- `tenant_id` or `license_id`: Pseudonymous customer/license identifier. Do not store raw API keys.
- `api_key_fingerprint`: One-way fingerprint of the credential used, if applicable.
- `model_subject`: Provider, model name, model version, adapter/version if present, endpoint type, and any customer-supplied model metadata.
- `harness_build`: CAS Harness build ID, git commit if available, runtime version, and deployed environment label.
- `audit_config`: Policy pack version, CAS method versions, threshold config, proof-chip config, suppression policy, and redaction policy.
- `input_record`: Prompt/user input, relevant conversation context, attachments metadata, retrieval/tool metadata, and redaction markers.
- `model_output`: Audited model response or response metadata. Store redacted content if raw capture is not allowed.
- `verdict`: One of `ACCEPT`, `SUPPRESS`, or `FLAG`.
- `confidence`: Numeric confidence plus confidence calibration version.
- `reason_codes`: Stable machine-readable reason codes for the verdict.
- `proof_chips`: Human-inspectable evidence snippets or references used to justify the verdict.
- `component_scores`: Detector/probe scores, thresholds, and pass/fail outcomes used by the verdict runner.
- `errors`: Any timeout, partial capture, unavailable probe, redaction failure, or degraded-mode marker.
- `packet_hash`: Hash of the canonical final packet, excluding fields that necessarily contain the hash itself.
- `log_anchor`: Link to append-only log position, previous hash, Merkle root, and optional external anchor.

## Canonicalization And Packet Hashes

Packets must be serialized into canonical JSON before hashing:

- UTF-8 encoding.
- Stable key ordering.
- No insignificant whitespace.
- Explicit `null` only where the schema allows it.
- Timestamp format normalized to RFC 3339 UTC.
- Binary artifacts stored by digest and URI, not inline.

Use SHA-256 for beta v0 unless security review requires a different algorithm. The final `packet_hash` is computed over the canonical packet body with `packet_hash` and `log_anchor` omitted or set to fixed placeholders. Large attachments, screenshots, model traces, or exported evidence bundles are included by content hash in an `artifacts[]` list.

Minimum artifact descriptor:

- `artifact_id`
- `artifact_type`
- `content_sha256`
- `byte_count`
- `storage_uri`
- `redaction_class`
- `created_at`

## Append-Only Hash Chain And Merkle Log

The packet log is append-only. No packet update overwrites a prior packet. Corrections are new log entries that reference the earlier `trace_id` and explain the correction reason.

Each log entry contains:

- `log_seq`: Global monotonic append sequence.
- `trace_id`
- `session_id`
- `packet_hash`
- `previous_log_hash`
- `entry_hash`: SHA-256 hash of canonical log entry fields excluding `entry_hash`.
- `merkle_leaf_hash`: Usually the `entry_hash`.
- `merkle_root`: Current root after appending this entry.
- `anchored_at`: UTC timestamp of last external or WORM anchor, if present.

The hash chain provides local tamper evidence: changing or deleting an entry breaks all later `previous_log_hash` checks. The Merkle log supports efficient inclusion proofs for one packet without exporting the whole log.

Beta v0 can start with a single-writer append log plus periodic Merkle root snapshots. The design must leave room for a transparency-log style service later.

## WORM And Third-Party Escrow Option

For partner or regulated deployments, CAS Harness should support optional write-once retention:

- WORM bucket/object-lock storage for final packets and artifact blobs.
- Daily Merkle root export to a separate account or system controlled by operations.
- Optional third-party escrow of daily root manifests for high-trust pilots.
- Retention class per tenant: beta default, partner extended, legal hold.

Escrow does not need packet contents. It only needs enough to prove that a packet hash or daily root existed at a specific time:

- date
- environment
- first and last `log_seq`
- Merkle root
- signer identity
- signature
- storage location for internal retrieval

## Multi-Turn Session Reconstruction

Reviewers must be able to reconstruct a session from packets alone, subject to redaction policy.

Reconstruction rules:

- Group packets by `session_id`.
- Order by `turn_index`, then `created_at`, then `event_seq` as a tie-breaker.
- Verify each packet hash before displaying it.
- Verify the append-only log inclusion proof for each packet.
- Mark missing, duplicate, or out-of-order turns explicitly.
- Show prior-turn dependencies that influenced the current verdict, including included context window, memory/retrieval references, tool outputs, and policy state.
- Preserve verdict evolution across turns: accepted context, suppressed responses, later flags, and any confidence changes.

The reconstructed session view should answer: what did the user/model exchange, what did CAS see, what did CAS decide at each turn, and which evidence changed the decision.

## What It Tells Senior R&D

The Evidence Packet should give senior R&D enough detail to:

- Reproduce why a specific `ACCEPT`, `SUPPRESS`, or `FLAG` decision was returned.
- Inspect proof chips and decide whether they are persuasive, weak, stale, or misleading.
- Compare component scores against thresholds and identify brittle thresholds.
- Trace regressions to a model version, policy pack, method version, harness build, or prompt/context change.
- Distinguish model behavior from harness capture failures, redaction gaps, retrieval/tool artifacts, and degraded-mode execution.
- Audit multi-turn failure modes, including context carryover and delayed risk accumulation.
- Verify that an evidence record was not silently edited after the run.

## What It Does Not Prove

The packet must not overclaim. It does not prove:

- The model's internal causal mechanism unless the specific audit included validated instrumentation for that claim.
- The truth or falsity of user-provided content.
- The user's intent.
- That all harmful or incorrect outputs would have been caught.
- That the configured thresholds are optimal.
- That redaction removed every sensitive datum.
- That the customer model, provider endpoint, or external tools were unchanged outside the captured metadata.
- Legal, regulatory, fairness, or safety compliance by itself.

It proves a narrower claim: given the captured inputs, outputs, configuration, and evidence, CAS Harness returned this verdict at this time, and the resulting record has tamper-evident integrity checks.

## Beta v0 Acceptance Criteria

Beta v0 is acceptable when:

- Every audit run emits one final Evidence Packet, including failed, timed-out, and degraded runs.
- Every packet contains `trace_id`, `session_id`, `turn_id`, verdict, confidence, proof chips, policy/method versions, model metadata, and harness build metadata.
- Packet canonicalization is deterministic across repeated serialization of the same data.
- `packet_hash` changes when any material packet field changes.
- Append-only log entries include `previous_log_hash`, `entry_hash`, and a Merkle root or documented beta placeholder.
- A verifier can validate packet hash, hash-chain continuity, and Merkle inclusion for a sampled packet.
- A reviewer can reconstruct a multi-turn session from packet exports without relying on application database state.
- Missing or partial evidence is represented explicitly, not silently omitted.
- Redacted fields are marked with redaction reason/class so absence is interpretable.
- WORM or escrow is optional, documented, and can be enabled per deployment without changing packet semantics.
- The UI or export labels the packet as evidence for the CAS decision, not proof that the decision is objectively correct.
- The spec and implementation avoid storing raw API keys, unnecessary secrets, or unbounded raw customer data.

## Open Implementation Notes

- Define the canonical JSON helper once and reuse it across packet hashing, entry hashing, and export verification.
- Keep proof-chip IDs stable so UI chips, packet entries, and exported artifacts can be cross-referenced.
- Prefer explicit schema migration over best-effort parsing once beta partners start storing packets.
- Treat `trace_id` as run-scoped and `session_id` as conversation-scoped. Do not reuse `trace_id` across retries; link retries with `retry_of_trace_id`.
- Store operator/admin access to packets as separate audit events. Reading the recorder should itself be auditable.
