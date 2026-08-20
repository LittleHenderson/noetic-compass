# Future evidence packet requirements

This directory intentionally contains no run output. A real WELD-v3 evidence
packet must live outside the frozen preregistration bundle and contain, at
minimum:

1. `freeze_receipt.json`, externally anchored before any actor output;
2. the five frozen public inputs whose hashes match that receipt;
3. the pre-freeze external commitment receipt whose hash is frozen, including
   the asserted OS-CSPRNG source and at least 32-byte salt/key sizes;
4. a `PRODUCTION_RUST` binding with parsed Cargo identities, a bound JSON
   version claim, external build provenance, and successful freeze/pre/post
   attestations;
5. an external sandbox/custody receipt proving plaintext truth and HMAC key
   were unavailable on the actor host during Phase A;
6. `actor_receipt.json` with one successful invocation and one schema-valid
   output per public case, unique case working directories, and the exact
   common pipeline trace;
7. an externally anchored `actor_receipt_seal.json` binding the exact receipt
   identity and recording `NOT_RELEASED` before truth/key release;
8. the post-seal custodian release receipt, released high-entropy HMAC key, and
   truth object whose HMAC equals the frozen commitment;
9. `adjudication.json` showing target verdict, control verdict, information
   match, pair verdict, and overall verdict;
10. a byte inventory and independent replay from the frozen inputs;
11. for model-facing execution, separately bound J1, J2, model, tokenizer, and
   Stage-5 artifacts plus provider receipts and leakage checks.

Mock receipts are evidence only for protocol mechanics. They must carry
`MOCK_PROTOCOL_TEST_ONLY` and cannot be promoted to CAS validation evidence.
This revision has no trusted external-anchor signature verifier and therefore
blocks `PRODUCTION_RUST` adjudication unconditionally; assembling the listed
files does not remove that code-level block.
