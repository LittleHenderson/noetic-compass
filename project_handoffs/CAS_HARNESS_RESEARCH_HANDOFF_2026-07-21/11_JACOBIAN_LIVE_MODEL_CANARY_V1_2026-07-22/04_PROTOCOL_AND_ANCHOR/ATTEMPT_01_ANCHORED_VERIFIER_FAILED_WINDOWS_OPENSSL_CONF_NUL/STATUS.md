# Attempt 1 retained status

Status:

`SUPERSEDED_PRE_EXECUTION_ANCHOR_ATTEMPT / NO_MODEL_EXECUTION / SHADOW / NONE / NOT_LICENSED`

The exact 104-byte RFC3161 query was sent once with explicit user approval.
DigiCert returned an HTTP 200 timestamp reply, and independent low-level
verification confirmed the query imprint, nonce, policy, signature chain,
pinned root, pinned responder certificate, and critical time-stamping-only
EKU. The response SHA-256 is
`2738ceb0ea1b23a65d707b8342d14abd1caff8151942c50333660ea8e4adec1e`.

Canonical anchor-receipt construction then failed closed on Windows because
Git OpenSSL interpreted Python's `os.devnull` value `nul` as a literal
configuration filename. The producer was never launched. No model outcome,
producer receipt, POST capture, receiver verdict, `ACCEPT`, or capability
license exists for this attempt. Its nonce, run ID, protocol, anchor payload,
query, and timestamp response must never be reused for a later code identity.
