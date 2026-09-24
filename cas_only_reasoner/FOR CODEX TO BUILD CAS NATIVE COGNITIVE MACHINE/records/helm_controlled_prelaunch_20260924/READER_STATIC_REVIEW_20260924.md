# Independent public static reader review — 2026-09-24

**Disposition: CHANGES_REQUIRED before P1b.** The central reproduction predicate is source-conformant. This review does not establish AWS acceptance, production reproduction, technical admission, or launch approval. Claude remains the AWS runner.

## Exact scope and source

- Builder branch: `claude/helm-unchanged-repro-20260924`, reviewed at `d5414964314475e2b13a49595fd54a3d7fee017c`.
- Prospective policy: `codex/helm-controlled-prelaunch-20260924` at `f287f96582eaf03670be93bb0728b1ca09d0ff2e`, `records/helm_controlled_prelaunch_20260924/REPRODUCTION_POLICY.md` and `.json`.
- Source line references below are relative to `records/typed_pointer_001/admission_unchanged_repro_001/` at the exact builder commit above.
- Policy markdown and JSON are byte-identical to those pinned at `bc46b36e60d904248fee03e5d7212f0eb5886c38`: SHA-256 `92a69981e4960d5ad30b9be127d8f9879c18f59cf5a40a55299ea5d679ac770e` and `13eee0490ce568cd7d012989c5a3bf59af0abb3c3e650370a0af2f8351cc9259` respectively.
- The shipped `EXECUTION_ADMISSION.json` says `NOT_READY`; all six prerequisite statuses are `NOT_RUN`.
- The builder verification at `REVIEW.md:688-694` says `APPROVE_READER_CONFORMANCE`, adds four MINOR findings and three NOTES (seven entries total), and explicitly requires source fixes before P1b.

## Source-conformant core

- `read_reproduction.py:123-137`: valid evidence AND learned-state equality AND output equality are required. File and continuation identity never decide the verdict. Invalid evidence cannot authorize fallback.
- `recompute_reproduction_evidence.py:385-399`, `repro_common.py:299-340`, `read_reproduction.py:635-642`: exact logical tensor value bytes, dtype, shape and layout are compared; encoder state and predictive configuration are included. Optimizer/RNG/cursor/counters are reported separately.
- `repro_common.py:593-613`, `read_reproduction.py:610-652`: all 564 pinned records and their order are required. Answers, decisions and grader fields are compared per record; failure to reproduce the reference panel invalidates evidence.
- `read_reproduction.py:192-224`, `252-291`, `367-411`, `564-608`: job identity, inventory-to-record hashes, all three checkpoint records, admitted sources, committed metadata, training package and machine are bound and checked.
- `repro_common.py:1072-1088`, `1091-1156`: prerequisite receipts must exist as committed anchored blobs, match their stated hashes and pass content-specific checks. Owner authority is separate from technical admission.
- `recompute_reproduction_evidence.py:662-670`: changed-buffer acceptance is explicitly `VACUOUS`, conditional on the restored reference having no buffers. It is not a real changed-buffer experiment. Accepting that substitute remains a prospective policy decision.

## Additional findings from this review

### P2 — Validate the complete exception message before truncation

`recompute_reproduction_evidence.py:174-175` truncates `str(error)` to 300 characters before checking the historical refusal-code rule. For example, a plain `ValueError` containing `"POINTER_" + "A"*292 + "\nCUDA fault"` becomes `REFUSED`, although its complete message fails the rule. Against an answered reference, this can become a valid output mismatch instead of `ADMISSION_INVALID_STOP`.

Validate the complete message first; truncate only its stored display. The verification's whole-message claim at `REVIEW.md:743-746` is stronger than the code. This finding is derived from source inspection, not an executed probe.

### P2 — Merge edits evade the one-version history check

`read_reproduction.py:324-326` excludes merge commits with `--no-merges` while counting changes to frozen records, evidence and `result.json` (`:332-334`). A merge resolution can change these files while leaving exactly one counted non-merge version. The endpoint comparison at `:318-320` protects only `EXECUTION_ADMISSION.json`.

Include relevant merge changes or compare immutable pinned blobs. Otherwise the claimed protection against rewriting evidence/results after freeze is incomplete. This is a static Git-history analysis; no mutation experiment was run.

## Confirmed remaining implementation gaps

1. **Missing owner-record object becomes a study verdict.** `read_reproduction.py:739-765` prechecks the reference commit but not all pinned owner-record commits before admission evaluation. A local fetch gap can become a recorded `ADMISSION_INVALID_STOP`. Add a named recoverable tool stop before reading.
2. **Spend sources and freshness are unchecked.** `repro_common.py:973-994` checks source path/hash syntax and timestamp shape but does not open sources or establish freshness. `prepare_unchanged_repro.py:516-517` explicitly leaves later spending and the $30 stop unchecked. Bind and validate record-derived costs under Codex's per-slot policy.
3. **Review does not resolve its commit or bind the writer.** `repro_common.py:997-1021` accepts a syntactically valid 40-hex reviewed commit; it does not resolve that commit or cover `prepare_unchanged_repro.py`. Verify anchored source blobs and separately bind the writer.
4. **Full environment lock is not compared against runtime.** `repro_common.py:938-947` checks the lock file hash and a status string but does not parse the lock. Python, cuDNN, driver and kernel are only recorded/presence-checked (`:290`, `:558-561`). A frozen lock alone will not enforce its values. The numerical subset currently requires RTX PRO 4500, not T4 (`:277-290`).
5. **Per-case acceptance claims are trusted.** `repro_common.py:893-920` requires all eleven named cases and `pass: true`, but does not compare each expected/observed verdict against a registered case table. Add this cheap independent check.

Hash direction, final freeze sequencing, exception/refusal policy, starting-state classification, root binding and changed-buffer vacuity are decisions for Codex's prospective policy response. Source changes above change the reader digest; complete and review them before paying for P1b.

## Open-question wording that the response must cover

`REVIEW.md:637-653` asks R3-A through R3-I: packet contents/hash direction; historical-coded ValueError versus infrastructure fault; buffer vacuity; starting-state identity as invalid training mismatch; reviewed re-pin; spend author/sources/freshness; receipt ancestry in the fetched branch tip; review verdict and reviewer identity limitations; dependency-lock content format. R3-G explicitly says to read only pushed commits of the branch. R3-H acknowledges that a different runner string does not prove reviewer identity. R3-I assigns lock content format to Codex.

`REVIEW.md:869-872` adds V4-A: final launch-request/manifest hashes already flow into admission/frozen records, so the opposite hash direction creates a cycle; the current writer also needs `launch_enabled` before generating frozen records. Parent review owns the resolution.

## Checks actually performed and exposure

Read only the assigned public review/report, reader/comparator/common/writer sources, pins/admission JSON and the two exact prospective policy files via read-only Git access in the audit clone, with explicit refs and `core.longpaths=true`. Compared policy bytes using SHA-256. Read project instructions and repository status before creating this scratch artifact. No protected answers, sealed content, Q3 material or archives were opened. No project code, tests, model, build or AWS job was executed. Existing claimed test/AWS results were not independently rerun. No tracked file was edited or staged; only this untracked scratch report was created.
