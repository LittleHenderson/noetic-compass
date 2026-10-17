# repair_performer — the thing that opens a repair child

**Claim ceiling:** `MECHANISM ONLY. THE FAILURE IS PLANTED, NOT DETECTED. THE GLUE IS MODELLED, NOT CANON. NO REAL FAILURE HAS YET STARTED A REPAIR.`

That sentence is the honest summary. Read the whole file before quoting a number out of it.

## Why this exists

Every artifact built before this one could recurse, and none of them ever did. LM-T6's
`CASCADE_1` passes at depths 0, 1, 2 and 3 with **0** fails, and `CASCADE_3` is **512 of 512**
right at depths 3 and 4. Codex's audit found `dwp_engine_v2` "builds nested chains when given
scripted blockades". The recursion engine was never the problem.

The council's own arithmetic named the cost:

```
gate 1, child opened 1, child run 0, glued 0, return 1
Y_T = min(1, 1, 0, 0, 1) = 0        eta = 0/0 -> UNDEFINED, not a low score
```

`child_run` and `glued` were both zero because **nothing was wired to the verdict the gate was
already producing**. `the_loop_v3/loop.py` said so itself at lines 84-85:

> *"It does NOT open a sub-goal, perform a repair, or flatten a horizon chain. A REPAIR verdict
> names the sub-goal; a REFUSE verdict names the flatten plan; **nothing here acts on either**."*

This module is that actor, and nothing more.

## What it does

Six steps, in `THE_TRIGGER_SPEC_20261017.md`'s order:

1. **DETECT** — ask the gate. Already built. The gate decides; this module never opines.
2. **NAME** — `GateVerdict.sub_goal` and `GateVerdict.gap` come off the verdict directly.
3. **OPEN** — the functor is picked by `RpmCause.blocked_node` (`"D"`, `"W"`, `"P"`). The child's
   depth is checked with the real `depth.check_depth` **before** it is opened.
4. **RUN** — `real_fit_child` runs rb_c4's own route fitter through `faculties_v2/real_fit.py`.
5. **GLUE AND RE-CHECK** — the child's output realises the prerequisite, the Bias goes strictly
   newer, and **the parent's own gate is asked again**.
6. **RECORD** — every attempt appends to a ledger. A refused child is still a recorded line.

`repaired` means **the parent's own gate passed afterwards**. It does not mean the child
succeeded. Those are different claims and only the second one counts.

## What was measured

From `ACTOR_RESULT.txt`, which this package reproduces on every run:

```
parent gate        -> REPAIR  (gap "the stock of the ingredient", sub_goal RPM(...)@1)
depth check        -> OK at child depth 1
child RUN          -> start_kept 1, fallback fired, 64 rows, held-out 32/32
parent gate after  -> PROCEED / NOTHING_BLOCKED   (Bias 1 -> 2)
outcome            -> REPAIRED
```

**`child_run` moved 0 → 1. `glued` moved 0 → 1.** `Y_T` is defined now instead of undefined.

## Two findings the run produced that reading could not

- **The glue must change the CAUSE, not the request.** Removing the gap from
  `request.prerequisites` changes nothing the gate looks at; the parent still answered `REPAIR`.
- **Clearing `unsatisfied` alone is not enough.** The code then reads
  `BLOCK_NEEDS_A_CHILD_CHAIN`, because `blocked_node` is still set. A successful child realises
  the prerequisite, so the node that was blocked by its absence is no longer blocked. Both fields
  move together. `the_second_glue_field_is_load_bearing` fails if anyone deletes the second one.

## What this does NOT prove

- **The failure is planted.** `demonstration()` constructs an `RpmCause`. It does not detect a
  failure inside a running loop. Spec §4 item 7 is **not met**.
- **The glue is modelled.** A successful child is modelled as realising its prerequisite. A
  production glue inserts the child's actual result.
- **The Atlas return address (step 2) is not wired.** The child returns to a gate, not an address.
- **No language crosses this.** Nothing here says the brain understands anything.
- **The Unity Eye and ASOM are absent by design.** Neither may appear in the decision path, and
  a test enforces it.

## Run it

```
C:\Python314\python.exe -X utf8 -B test_all.py     # the suite
C:\Python314\python.exe -X utf8 -B actor.py        # the demonstration
```

It needs the sibling packages `the_loop_v3`, `dwp_engine_v2`, `return_address` and
`faculties_v2`, which are found relative to this folder. The real fitter additionally needs
rb_c4 and its `lsr_*` dependencies, which live outside this repository; without them the child
reports `real_fit did not import` and the run disengages rather than pretending.
