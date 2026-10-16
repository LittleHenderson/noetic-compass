# R1-RT design, appendix J: a hosted brain survives a restart, and the fourth edit it cost

**Date:** 2026-10-16
**Status:** the restart half of R1-RT's target sentence is now **measured and working**. A runtime
created with the client writes a real SQLite store, closes, reopens from that store, and answers
again — with the answer coming from the recipe brain across the process boundary.

## 1. It did not work, and it was measured failing first

Appendix I proved the answers but wrote nothing, so the restart half was untouched. There was a
specific reason to expect trouble, and it was found by **reading** the patch: `create()` was the only
place the patch registered an extension operation. `open()` builds its own network and contracts and
took no extension operations at all.

The prediction was that a reopened runtime would fail on the empty operation slot. **The prediction was
wrong in its detail and right about the cause.** What actually happened, recorded verbatim:

```
phase 1 create : OK
phase 1 tick   : FIRST_UNSUPPORTED_LEG_1    (rule says FIRST_UNSUPPORTED_LEG_1   ) OK
the store is on disk: ...\hosted.sqlite3 (266240 bytes)
phase 2 open   : FAILED
  CheckpointError: checkpoint keys do not match the Neural CJT module
```

Not the allowlist error. A **checkpoint key mismatch**, which fires earlier: the checkpoint was
written with the client's parameter in the module tree, and the reopened network had no such
parameter, so the two key sets differ. The registration therefore has to happen **before**
`load_module_checkpoint`, not after it.

## 2. The fourth edit

One more edit, and it mirrors the one `create()` already needed: `open()` gains the same
`extension_operations` parameter and registers them immediately after it builds its network, ahead of
the checkpoint load. **Twelve edits in total** across four files, prepared by
`prepare_client_patch.py`, all **34 of 34** modules compiling.

| # | file | what it does |
|---|---|---|
| 1-8 | `neural.py`, `network.py`, `runtime.py` | route D: the task's content reaches the operation |
| 9 | `state.py` | one entry in the frozen operation table |
| 10-11 | `runtime.py` | `create()` takes and registers an extension operation |
| **12** | **`runtime.py`** | **`open()` takes and registers one too, before its checkpoint is compared** |

So the client costs **four** edits beyond route D, not the one route D assumed and not the three
appendix G reported. Each was forced by a measured refusal, and this one by a measured failure.

## 3. The restart, working

```
phase 1 create : OK
phase 1 tick   : FIRST_UNSUPPORTED_LEG_1    (rule says FIRST_UNSUPPORTED_LEG_1   ) OK
the store is on disk: ...\hosted.sqlite3 (266240 bytes)
phase 2 open   : OK
phase 2 tick   : ALL_LEGS_PRESENT           (rule says ALL_LEGS_PRESENT          ) OK
VERDICT : A HOSTED BRAIN SURVIVES A RESTART THROUGH THE STORE
```

Two things make this worth more than a single success:

- **The two ticks are different cases with different answers.** A runtime returning a cached or
  default value could not pass both.
- **The store is real**: 266,240 bytes of SQLite written by the runtime itself, closed, and reopened
  from disk. The brain worker never held torch through either phase.

Reproduce with:
```
python -B probe_hosted_restart.py <patched-parent> <base-tree> <gb-root> <v3-package-root>
```

## 4. What this does NOT establish

1. **Still not a result on the exam.** Two hand-written cases. No teaching, no mark, and nothing here
   touches wave 1's reading.
2. **The decoder is still the design's, not the task's.** A version-2 contract and its exact semantic
   lineage are still needed before a run can claim the task.
3. **No nested repair.** That is the remaining half of the target sentence and it is untouched.
4. **It ran on copies.** The frozen source is unchanged at 0 of 34, 0 of 29 and 0 of 11.
5. **The envelope is still not re-costed.**

## 5. Where R1-RT stands

| part | state |
|---|---|
| the input rule | falsified as frozen; replaced by the spare-constant encoding, proved on 323,851 cases |
| the output rule | frozen in appendix B |
| the patch | built, tested, measured on the real path |
| the client operation | built, measured; four edits beyond route D |
| the process boundary | built, measured; 0.061 ms per tick median; never held torch |
| the brain answering a runtime tick | **done**, appendix I, 3 of 3 |
| **surviving a restart through the store** | **done here** |
| a real nested repair | **not done** |
| the version-2 decoder and its lineage | **not done** |
| the re-costed envelope | **not done** |
| the owner's line for a paid run | **not given, and not yet asked for** |

Two of the target sentence's three parts are now working. The third is the nested repair.
