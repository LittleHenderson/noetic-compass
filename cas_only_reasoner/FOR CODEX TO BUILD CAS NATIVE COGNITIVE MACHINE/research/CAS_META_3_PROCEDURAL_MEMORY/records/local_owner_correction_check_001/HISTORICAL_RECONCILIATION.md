# Reconciliation of the owner's 13-failure report

Historical commit: `63f5b4210cc4df179193a5b5e3489ff48d79b3dd`.
Owner-reported result: 13 failed, 518 passed, one warning, Python 3.14.0.
The supplied text names failures but does not include their exception tracebacks.
Preserve that report; it is not replaced by the following passing run.

## Fresh exact-commit run

A separate detached checkout was created with:

```powershell
git -c core.autocrlf=false worktree add --detach 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3-audit-63f5b421' 63f5b4210cc4df179193a5b5e3489ff48d79b3dd
```

From that checkout's CAS_META_3_PROCEDURAL_MEMORY directory:

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/historical_owner_reconciliation_001
```

Result: **531 passed, one warning**, zero failures/errors/skips. Pytest took
35.73 seconds; parent validation took 37.012774 seconds. Python was 3.14.0.
The existing validator blocked neural/provider imports, checked 316 protected
files and pinned dependencies, and verified source bytes before and after.
It did not run inference, load a checkpoint, install packages, or change source.

Authoritative raw receipt and output directory:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3-audit-63f5b421/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_owner_reconciliation_001/`

This is a separate builder-run checkout, not a third-party execution claim.

## Source and environment findings

Git diff from the historical SHA to the current branch shows no changes to
cas_meta3/native_demo.py, tools/inspect_cloud_packet.py,
tests/test_native_demo.py, or tests/test_packet_inspection.py.
The later learned-handoff additions are not direct edits to the reported cases.

The current interpreter also reports that `cas_neural_cjt` is not importable,
yet the historical suite passes. Inspection of the frozen wheel's ZIP entries
shows its import package is `cas_cjt`; `cas_neural_cjt` is its distribution/wheel
name. No neural package was imported to make this check. Therefore failure of
`import cas_neural_cjt` does not by itself establish a missing runtime dependency
or explain these pure-test failures.

Packet fixtures call native_demo.source_identity() before constructing their
malformed records. That function checks pinned native and protected file bytes.
A failure there would stop the test before it tests admission. This is an
identified possible boundary, NOT a conclusion that this caused the owner's run.
The separate checkout used core.autocrlf=false to preserve committed bytes;
line-ending conversion is not established as the historical cause.

## Remaining evidence needed

The failing run's exception tracebacks, exact command, and checkout-byte identity
are needed to distinguish source/fixture setup from an actual rejection failure.
The failure list alone does not show malformed records passed admission. Do not
declare historical closure, weaken checks, install unrelated packages, or reopen
the accepted core/META-0/META-1 audits based on the list.
