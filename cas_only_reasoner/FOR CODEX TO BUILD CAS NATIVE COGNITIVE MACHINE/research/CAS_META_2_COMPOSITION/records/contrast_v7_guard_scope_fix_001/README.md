# Scoped bridge-test import guard

The focused correction passed. The new bridge test now blocks neural/provider
imports only during its own imports and test methods, and restores both
`sys.meta_path` and `sys.path` on normal or exceptional exit.

Only `tests/test_contrast_v7_bridge.py` was changed for this correction.
No canonical validator, source loader, old fixture, model, executor, or retained
proof runner was changed.

## Reproduced defect

The frozen clean audit at `80e44f20a3f2c66a62754212729ce6e11ff9c8fe`
is retained in `records/clean_source_prototype_v7_001/`.
Its full suite had three failures: the bridge test's module-global import hook
blocked the later pure `botocore.exceptions` tests. All 556 checked source/input
bytes and all 316 protected files were unchanged.

Failed clean-audit receipt SHA-256:
`dec93b989ee66c6e4c79476dcc06631d14df947ed5c77aef5b2ab109e103d9d1`.

## Focused rerun

The command actually run was:

```powershell
& 'C:/Python314/python.exe' -B 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_v7_guard_scope_fix_001/run.py' --stage focused
```

Working directory was `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`.

Result: **15 test functions and 15 subtests passed**, exit 0, pytest time
**1.12 seconds**. The JUnit count is 30 because it includes subtests.
The selection contains all 12 bridge methods plus the three exact formerly
failing exception-import cases, run afterward in the same process.

The existing bridge purity test now explicitly checks normal cleanup,
exception cleanup, blocked neural/provider imports inside the scope, and a
fresh re-import of its own collection code with no import-hook or path leak.
The method count remains 12, preserving the unchanged portable proof runner's
declared test count.

The exact selected IDs, commands, source hashes, outputs, and JUnit are retained
under `focused/`. The watched source files stayed unchanged during the run.

- Corrected bridge test SHA-256:
  `827248b956b85024fd94c789df4ba092152922f32492d34b125dcdd916779adb`.
- Focused receipt SHA-256:
  `acf19d1b9d2577186a3a019dd899be6cc4d221b9cbf7ae7db58ea48fd65e8047`.

This used the existing Python 3.14 environment. No provider, model, GPU, budget
reservation, current v6 data, or registered dataset was used.

## Full-suite follow-up

The root agent deferred a full active-worktree run because other authorized
source changes are still being prepared. After committing the selected recovery
and guard-fix files, the full guarded validator and portable v7 proof must run
in a new clean detached checkout pinned to that exact commit. No full-suite
pass is claimed for this correction yet. The failed frozen run remains
unchanged evidence.

