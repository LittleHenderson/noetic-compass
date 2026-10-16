# R1-RT design, appendix I: the brain answered a real runtime tick

**Date:** 2026-10-16
**Status:** the two halves proved separately have been **joined and run**. One
`runtime._prepare_inference` call now produces a tensor whose decoded symbol is the recipe brain's
answer, read back through **the runtime's own decoder**.

## 1. What was joined

Appendix G proved the runtime accepts and calls a client operation and hands it the task's content.
Appendix H proved the brain answers over a process boundary and has never held torch. Neither of them
had the brain behind the client. This does.

The client is a conduit. It reads the case the runtime handed it, sends the question across the
boundary, and writes the returned answer into the tensor by appendix B's frozen rule. It holds no
learned parameters and decides nothing.

## 2. What the run produced

Three ticks, with different cases so that a constant answer could not pass. The symbol below is what
**the runtime's own decoder** reported, not what the probe inspected:

| tick | the case | the rule's answer | the runtime reported | |
|---|---|---|---|---|
| 1 | the second leg is missing | `FIRST_UNSUPPORTED_LEG_1` | `FIRST_UNSUPPORTED_LEG_1` | OK |
| 2 | every leg present | `ALL_LEGS_PRESENT` | `ALL_LEGS_PRESENT` | OK |
| 3 | the third leg is missing | `FIRST_UNSUPPORTED_LEG_2` | `FIRST_UNSUPPORTED_LEG_2` | OK |

**3 of 3.** The answers were not constant — three distinct symbols — so a client returning a fixed
value cannot pass this check.

What crossed the boundary, recorded so the two sides can be compared line for line:

```
route [0, 1, 2]      edges [[0, 1]]              -> FIRST_UNSUPPORTED_LEG_1
route [0, 1, 2]      edges [[0, 1], [1, 2]]      -> ALL_LEGS_PRESENT
route [3, 4, 5, 6]   edges [[3, 4], [4, 5]]      -> FIRST_UNSUPPORTED_LEG_2
```

## 3. The readings

| reading | result |
|---|---|
| a client ran on the runtime's own path | **YES** |
| it asked the brain across the boundary | **YES** |
| the runtime's **own** decoder agreed with the rule | **3 of 3** |
| the answers were not constant | **YES**, 3 distinct |
| the runtime's answer **is** the brain's answer | **YES** |
| the bank was left empty afterwards | **YES** |
| the brain worker never held torch | **YES** (its own report) |
| peak memory | **221.6 MiB** of the 300 MiB laptop rule |

Reproduce with:
```
python -B probe_hosted_brain.py <patched-parent> <base-tree> <gb-root> <v3-package-root>
```

## 4. What this does NOT establish

This is the single most important section of this appendix, because the result above is easy to read
wider than it is.

1. **It is not a result on the exam.** Three ticks on cases written by hand prove the mechanism. They
   are not the task's 288 cases, there is no teaching, and no mark is claimed. Nothing here upgrades or
   touches wave 1's reading.
2. **The decoder is the design's, not the task's.** The runtime's decoder contract here is the
   design's own version 1. `native_task.task_decoder_contracts` pins `operation_id == "^6"` and
   refuses anything else, so the task's own contract could not be used. A run that claims the task
   must supply a version-2 contract **and** its exact semantic lineage, which `_semantic_lineage`
   validates field by field. That is not done.
3. **No durability, no restart, no repair.** Nothing was written to the store, so the restart and
   nested-repair halves of R1-RT are untouched. They are what the target sentence actually asks for
   beyond the answers.
4. **It ran on copies.** Three edits sit in a copy of the runtime under `_client_patch`. The frozen
   source is unchanged: **0 of 34** files in the R6 tree, **0 of 29** in the vendored GB3 tree, **0 of
   11** in `rb`.
5. **The envelope is not re-costed.** Appendix H gives the per-tick boundary cost (0.061 ms median),
   but a hosted tick also pays the runtime's own overhead, which this probe does not separate out.

## 5. What the join cost, and what it did not

The join itself needed no new edits. The three edits from appendix G were enough, and the client
slotted into the operation position the runtime was already calling. Two things did have to be got
right, and both are recorded because they are the same two traps as before:

- **The client holds no reference to another `nn.Module`.** `ask` and `read_case` are plain callables
  set from outside, so the only thing the client contributes to the module tree is its own parameter.
  Holding the operation bank would have made `state_dict()` walk bank to client to bank and recurse.
- **The boundary is closed in a `finally`.** A worker left running after a failed tick would hold a
  file handle and a process, and the failure would look like a leak rather than a result.

## 6. Where R1-RT now stands

| part | state |
|---|---|
| the input rule | falsified as frozen, replaced by the spare-constant encoding, proved on 323,851 cases against the live oracle |
| the output rule | frozen in appendix B |
| the patch that lets the operation see the question | built, tested, measured on the real path |
| the client operation | built, measured; three edits to a copy |
| the process boundary | built, measured; 0.061 ms per tick median; the worker never held torch |
| **the brain answering a runtime tick** | **done here, 3 of 3** |
| the exam, the restart, the nested repair | **not done** |
| the version-2 decoder and its lineage | **not done** |
| the re-costed envelope | **not done** |
| the owner's line for a paid run | **not given, and not yet asked for** |

The mechanism is finished. What remains is running it on the task the target names, and that is where
cost and the owner's line both come back in.
