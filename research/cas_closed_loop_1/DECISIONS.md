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

# Lease `CAS-CORRECTION-20260927-01` decisions (Claude, 2026-09-27)

- Lease accepted on PR #245 (comment 5853300431) before any edit. Writable scope as offered, with two carve-outs
  recorded there: `SOURCE_BINDINGS.json` is not edited because its content digest is the `source_manifest_digest`
  in the retained evidence bundle's admission (`8a049806…`), so a byte change would fail `retained_replay`; the lane
  `CHANGELOG.md` is outside the lease, so lane change entries live here.
- R1. `test_native_step_adapter.py` now imports `TerminalStatus` at module level. The three amended regression
  cases that raised `NameError` at `aa600668` execute. Both the failing head runs and the patched scratch run are
  preserved under `claude_lead_20260927/run_*`.
- R6. Attacker model resolved against the specification: `HARNESS_SPEC.md` excludes hook changes; the adapter's own
  in-scope test patches `CompoundMachine._execute` in memory, so that class is inside the guarantee. A second entry
  on a thread started inside the window, with no hook change, is the same class and was neither counted nor refused
  (corrected probe: two direct entries, receipt says one). The meter is now installed on threads started inside the
  window, refuses a foreign-thread entry at its call event, invalidates the window on any foreign-thread activity,
  and checks after the call that the hook is intact. Residual, stated: a thread that existed before the window is
  not covered; Python 3.12's `threading.setprofile_all_threads` could cover it and was not used, to keep 3.11 and
  3.12 behavior identical. No isolation-against-arbitrary-Python claim is made. Regression case added in the same
  file, so the collected count of the four frozen files is no longer 61; the freeze must be re-cut at the corrected
  commit with the count the source actually collects.
- Local pytest runs on Python 3.11 are engineering checks before each push. Acceptance remains the AWS worker
  sequence on a re-cut freeze, run by Codex under an owner decision.
