# Prospective recovery decisions

- The live managed repository starts at `eb3c9b1eac98853b2065c98b08987918e8e7d936`.
  Objects `348638c9d9b6069eebab7853db6b98bfef453092` and
  `2636bbb6e0f41a37ba2c20df08cdf51185718617` are missing there. This work does
  not restore or claim either historical revision. A separate old worktree
  advertises the former HEAD; that does not make it present in this repository.
- Use exact public dependency blobs from available local Git object
  `8182ad52b4468f18f140837dffee0e7debcfe786`, observed as
  `origin/research/helm-integration-20260923`. Materialize only the manifest
  allowlist in ignored `_runtime/`; never edit the active source worktree.
- Preserve the four original supplied handoff files byte-for-byte in
  `provenance/`. New source pins supersede unavailable historical pins.
- `deepseek-0001` correctly identifies incomplete return identities. Emit all
  eleven fields, plus every live frame's identity. Native suspension event
  pre-state hashes identify the whole saved state including Bias; this runtime
  has no separate Bias-version counter. No-frame identities remain null where
  inapplicable. Coordinates have no return authority.
- Contrary to the review prose, the supplied adapter already validates its
  fault path before receipt creation. Harden those checks and preserve the
  native error type on validation failure without issuing a usable receipt.
  `except Exception` does not catch `KeyboardInterrupt` or `SystemExit`.
- Meter actual entry into the original native Python function via its code
  object's call event; track attempted dispatch separately. Refuse a busy
  profiling hook. This measures host entries, not primitive work or all compute.
- Admit actual source bytes, the loaded native profile and exact problem before
  work. Receipt content hashes detect edits but are not signatures or authority.
- Owner's current instruction explicitly permits focused lightweight local
  tests and forbids AWS/model jobs. No paid job or model inference is required.
