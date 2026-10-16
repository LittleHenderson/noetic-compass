# R1-RT: the collision that decides the design, found by the council

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** a finding, not a design and not a
claim. Nothing here was run, nothing was changed in any package, and no money was spent.

## The finding, in one paragraph

HELM's runtime and the recipe brain are built to refuse each other. The runtime imports torch at
module level and its brain-validity checks are tensor operations. The recipe brain installs an
import blocker at package import that **refuses torch and numpy in its own process**, and **raises
if torch is already loaded**. So R1-RT is not blocked by a missing adapter. It is blocked by an
architectural decision that has not been taken: *which of the two guarantees is given up, or how
are the two kept in separate processes.*

## The two sides, measured

**The runtime wants a torch module.** All four lines are read, not paraphrased:

| Where | What it says |
|---|---|
| `cas_cjt/runtime.py:9-10` | `import torch` / `from torch import Tensor` — module level, **not** guarded |
| `cas_cjt/runtime.py:529` | `expected = operation.state_dict()` |
| `cas_cjt/runtime.py:548` | `operation.load_state_dict(retained, strict=True)` |
| `cas_cjt/runtime.py:1013` | `not torch.equal(...)` |

17 of the runtime's 34 Python files import torch. There is no `try`/`except ImportError` around
any of them; the one `except ImportError` in the whole runtime is in `contracts.py:98` and is
about a test extra, not torch.

**The recipe brain refuses torch on purpose, and says so three times.** `rb/__init__.py` installs
the blocker before any other `rb` module runs:

```python
from . import no_torch as _no_torch
_no_torch.install()
```

`rb/no_torch.py` inserts a meta-path finder that raises on any import of `torch` or `numpy`, and
its `install()` refuses to continue if either is **already loaded**:

> `RB1G: {loaded} already imported before the blocker; the RB process must not hold torch`

That is an `INSTRUMENT ERROR` by the package's own words, not a failure. It is required by the
package's preregistration (`PREREGISTRATION_RB1G2.md` section 3, step B) and it is why wave 1's
recipe arms ran in a process that never held torch.

**So the two cannot simply share a process.** If the recipe brain is imported first, torch cannot
be imported afterwards and the runtime cannot work. If the runtime is imported first, the recipe
brain refuses to install its blocker and the package raises. Both orders fail, and each fails for
a reason the other side wrote down on purpose.

## The three honest ways out, and what each costs

| # | Shape | What it preserves | What it gives up | Status |
|---|---|---|---|---|
| 1 | **Separate processes**: the recipe brain answers in its own clean process; the runtime talks to it across a boundary | both guarantees intact — no torch in the recipe process, no recipe code in the runtime's module graph | a process boundary, its protocol, its failure modes, and the claim "hosted in the runtime" becomes "reached by the runtime" — which must be stated in those words | undesigned |
| 2 | **Drop the blocker**: let the recipe brain's process hold torch | the simplest plumbing; one process | a guarantee the package was built to enforce, in a package whose preregistration requires it. This is a package edit, so it needs a new seal and a new owner line | undocumented, and forbidden by the current package |
| 3 | **A fake torch**: give the runtime a torch-shaped stand-in that its brain checks accept | one process; the recipe brain keeps its own process clean only if the stand-in is loaded after it | the runtime's `state_dict`/`torch.equal` checks would be satisfied by a stub, so they would stop being real checks — the exact substitution this project has been bitten by | not proposed by anyone; named here so it is refused explicitly |

Option 3 is written down so that it is on the record as **refused**, not as an available shortcut.

## What the other seats measured that bears on the choice

- **The runtime already implements GB3's task.** `source_r6/native_task.py:18` carries the same
  task id as GB3's `TASK_CONTRACT.md`, the same eight answers in the same order, the same
  `[1,8,64]` channel map, and `native_learning.py` already runs it through
  `runtime._prepare_inference`. So the *task shape* half of the bridge is not new work.
- **No new operation identity can exist.** `state.py` holds exactly `^6 ^2 ^3 ^8` and
  `make_operation_contract` raises for anything else; `network_coordinator.py:905-913` rejects any
  contract not equal to the frozen one. An adapter must present the recipe brain as one of those
  four, not as a new kind of thing.
- **The brain is invoked from one line inside the runtime.** `runtime.py:1006`
  (`proposal = self.network.forward_node(`) plus one more in `teaching_learning.py:392` — two call
  sites in 22,856 lines. And the words `brain` and `recipe` appear **zero** times in those 22,856
  lines.
- **The store is real and the restart claim is untested.** `persistence.py` is 4,325 lines of
  SQLite with WAL and `BEGIN IMMEDIATE`, and `source_r6/tests/` has **no repair-frame test at
  all** (`historical_passes_do_not_validate_r6`).
- **The nested repair every document calls a stand-in.** Six separate documents record it as "a
  built-in analog, **not HELM's repair**", and `HELM_MANIFEST.md:23` has the runtime's own repair
  switch `resume_restores_carrier` **off by default**. GB3's real repair frame is mechanically
  clean 4 of 4 and **destroys 3 of the 4 answers that were right without it** (`repair_correct: 1`,
  `repair_returned: 4`, `repair_total: 4`).
- **A defect in this council's own reading, found by seat CO-0 and now fixed.** The gate reading
  looked for the owner's half by searching the plan folder for the string `R1-RT`. It found four
  documents that merely *mention* R1-RT, and because `WAVES.md` itself contains that string and
  sits in the same folder, **a different filesystem walk order would have flipped the gate to
  satisfied with no byte changing.** It now requires an admission phrase; it reports five mentions
  and no approval, and it returns `None`, which blocks.

## What this means for the two clean paths

Both still stand, and the collision does not change either:

1. **Design first, gate second.** The council produces the R1-RT design — including which of the
   three shapes above is chosen and why — with its acceptance test frozen before any code. The
   owner then gives or withholds the word.
2. **Gate first, design second.** The owner says yes now; the design is still required before any
   run, because no run may start without a frozen acceptance test.

But the collision adds a third item that neither path can skip: **the shape choice is an
architectural decision, and the council must not take it by itself.** Option 2 edits a frozen
package. Option 1 changes what "hosted in the runtime" means. Option 3 is refused. That decision
belongs to the owner, on the council's recommendation.

## What is deliberately not in this document

- No design, no marks, no run plan. `RT_SPECIFIED` is the condition the council exists to move, and
  moving it by fiat is the substitution this project keeps getting bitten by.
- No claim that the recipe brain can satisfy the runtime's tensor contract. Nobody has measured
  that, including this turn.
- No cost figure for option 1. The seats measured the pieces (the runtime is 22,856 lines and
  1,163,249 bytes; the recipe brain package is 111 files and 3,247,222 bytes; one restart unit
  already measured at 0.37 s), but an inter-process boundary has not been priced.
