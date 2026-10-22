# Return address -- the way back through the RPM, one exact level at a time

Step 3 of THE BUILD (build restart plan item 3: *"Wire the return address. Every open thread bound
to an exact Atlas address; no root shortcut; a stale return refused."*).

Built 2026-10-24 in `C:\Users\wakil\Documents\Codex\2026-10-16\return_address\`, as a NEW standalone
package. Standard library only, plus a read-only copy of the real atlas model. No torch. No numpy.
No network. No AWS. No spend. Nothing outside this folder was modified.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. NO CIRCUIT USES THIS YET.
```

## First, the plain truth: there is no engine here

**This build has no live engine. No recursion is running.** Nothing in this folder dispatches a
child, blocks a node, cycles a Desire loop, or measures anything. There is no brain, no model, no
training, no scoring.

What it does is implement and test the **rules** for how a sub that went down comes back up: what
exactly an open thread is bound to, who receives a checked result, what a caller owes before its own
result may travel further, what may not wake a caller, and what a dirty child does to the chain
above it. Every "call", "suspend", "return" and "child" in the tests is a record this build made,
with values the test wrote by hand.

So: the rules are implemented and tested. A circuit has not used them. Nothing has returned.

## The owner's sentence this build is built from

> "Also, as the sub recurses throughout the RPM system through the Atlas, or the RPA, the coordinate
> system, or system of coordinates, could be used to establish its way back through the RPM, through
> the recursive prerequisite system, back to the original CJT."
> — [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 7, dated 2026-09-24]

The addendum's implementation decision beside it: bind the existing RPM continuation to an exact RPA
address and an explicit return chain. *"The address answers where; the saved continuation answers
which caller and what unfinished work resumes."* [line 8]

## The five rules, and where each one lives in code

| rule (owner's addendum + canon) | where it is enforced | what refuses when it is broken |
|---|---|---|
| 1. Every open thread is bound to an exact address: episode, branch, saved snapshot, Bias version, call occurrence. Never "near the last place", never "closest match". | `address.ReturnAddress`, `stack.ReturnStack._lookup` | `MISSING_FIELD`, `INEXACT_ADDRESS`, `CALL_ID_MISMATCH`, `NO_SUCH_THREAD` |
| 2. A checked child result returns to its immediate waiting caller, which finishes its own remaining work before returning further. No skipping levels. | `stack.Resumption.return_further`, `stack.ReturnStack.no_root_shortcut` | `REMAINING_WORK_UNFINISHED`, `NO_WAITING_CALLER`, `CALLER_NOT_WAITING` |
| 3. Keep a root reference for observation, but no root shortcut for returning. | `address.ObservationReference`, `address.to_root` | `NO_ROOT_SHORTCUT`, `NOT_A_RETURN_PATH`, `ALREADY_AT_ROOT`, `ROOT_NOT_RESOLVABLE` |
| 4. A return must carry a strictly newer Bias; a stale, cancelled or duplicate finish may not wake an unrelated caller. | `stack.ReturnStack.resume` | `BIAS_EQUAL_NOT_NEWER`, `BIAS_OLDER_THAN_SUSPENDED`, `THREAD_CANCELLED`, `THREAD_ALREADY_FINISHED` |
| 5. A dirty child invalidates the whole ancestor chain (Theorem 27.3). | `dirty.mark_dirty`, `dirty.invalidate_ancestors` | `THREAD_INVALIDATED`, `ANCESTOR_INVALIDATED`, `ANCESTOR_CHAIN_BROKEN` |
| 6. On return the child glues back onto its parent, and the real model decides that. | `atlas_binding.glue_back` -- it only reports; `stack.resume(..., glue=...)` only refuses | `GLUE_BACK_REFUSED_BY_REAL_MODEL`, `GLUE_VERDICT_NOT_FROM_REAL_MODEL`, `REAL_MODEL_REFUSAL` |

Canon, quoted for rule 5 — *"[Theorem 27.3] For any recursive depth n, the Section-Retraction identity
epsilon^(n) o eta^(n) = id^(n) must hold independently"* and *"If a child chain at any level uses a
'dirty' resolution (e.g., a Power bypass), the retraction morphism fails, the block propagates back
up the stack, and the entire parent chain is invalidated."*
[Chapter_27_RPM_Structure.md, lines 61 and 63]

## `address.py` -- the exact address, and the root reference

**Does:**

- `ReturnAddress(episode=..., branch=..., snapshot_digest=..., bias_version=..., call_id=...,
  parent_call_id=...)`. Six fields, every one required and typed. A field that is not supplied is
  refused (`MISSING_FIELD`) and named in the refusal. There is no default, no `None` standing in for
  "unknown", and no placeholder. The only `None` the address accepts is `parent_call_id` on the root
  call, and it has to be written out.
- `is_exact(other)` compares **every** field. A partial match is not a match: `require_exact` raises
  `INEXACT_ADDRESS` and names the fields that differ, and `differing_fields`/`exactness_report` say
  the same thing without raising.
- `child_of(parent_address, call_id)` gives a child its own **call occurrence**, because "a module's
  identity alone is not a call identity: one CJT can be invoked more than once" [addendum, line 12].
  It inherits the parent's episode, and the parent's branch, snapshot and Bias unless the caller
  states its own. It refuses a child that reuses its parent's occurrence id (`DUPLICATE_CALL_ID`).
- `to_root(address, stack=None)` returns an `ObservationReference`: the root handle kept "for the
  original goal/CJT throughout" [line 9]. With no stack it answers only when the address **is** the
  root, and otherwise refuses `ROOT_NOT_RESOLVABLE` rather than guess.

**Does not:**

- It does not decide where anything is. Values come from the caller; nothing here walks an atlas or
  infers a branch.
- It does not hold threads, suspensions or repairs. That is `stack.py`.
- It does not use profile coordinates, flower distance, zoom or layout to locate a caller. There is
  no such field and no such function, by construction.
- It does not treat an address as permission: "The exact address is a lookup key, not authority by
  itself" [addendum, line 25]. The checks that decide are in `stack.py`.
- It does not compute a digest. `snapshot_digest` is a sha256 the atlas model computed over a saved
  snapshot; this module checks the shape and copies the value.

## `stack.py` -- the return stack, and the caller's own work

**Does:**

- `suspend(address, bias_version, payload, remaining_work=...)` puts a caller on the stack. It
  refuses a Bias version that disagrees with the address (`BIAS_ADDRESS_MISMATCH`), a second
  suspension of the same address (`THREAD_ALREADY_SUSPENDED`), one occurrence id used at two
  different places (`CALL_ID_REUSED`), and a missing payload or work list.
- `resume(address, returned_bias_version, payload, glue=None)` is the return. It refuses, in this
  order, with one word each: `NOT_A_RETURN_PATH`, then `NO_SUCH_THREAD` / `CALL_ID_MISMATCH` /
  `INEXACT_ADDRESS`, then `THREAD_CANCELLED`, `THREAD_ALREADY_FINISHED`, `THREAD_INVALIDATED` /
  `ANCESTOR_INVALIDATED`, `MISSING_PAYLOAD`, `BIAS_EQUAL_NOT_NEWER`, `BIAS_OLDER_THAN_SUSPENDED`,
  and finally the two glue refusals. A refused return does **not** consume the token.
- `no_root_shortcut(address)` returns the **immediate waiting caller's address**, and refuses a jump
  to the root (`NO_ROOT_SHORTCUT`), a return from the root itself (`ALREADY_AT_ROOT`), a caller that
  is not on the stack (`NO_WAITING_CALLER`), and a caller that is there but not waiting
  (`CALLER_NOT_WAITING`).
- `remaining_work(address)` reports what the caller still owes. `Resumption.return_further()` refuses
  `REMAINING_WORK_UNFINISHED` until every step is done, so "the caller completes its own remaining
  work before its result returns further" is enforced rather than described.
- `cancel(address, reason)` and `finish(address)` complete the state machine. Finished is finished:
  there is no un-resume, and a finished thread cannot be cancelled.
- `receipt()` is the ordered log of call and return edges plus state events, each with its relation
  type (`CALL` / `RETURN`), its source event, and leaf values only.

**Does not:**

- It does not decide that a result is good. It checks that the return is the right return to the
  right caller, not that the result is correct.
- It does not glue anything back. When a verdict is supplied it must be the real model's record from
  `atlas_binding.glue_back`; otherwise `GLUE_VERDICT_NOT_FROM_REAL_MODEL`.
- It does not decide a Bias. It enforces that what comes back is strictly newer than what left.
- It does not search by proximity. There is no nearest, closest, latest or same-name lookup in the
  file, and a failed match reports what is actually there instead.
- It does not restore, rewind or refund. Returning is forward progress: completed work stays charged.
- It does not persist or journal. The addendum points at the runtime's existing transaction path for
  that [line 28]; this build is in memory and writes nothing.
- It does not run a coordinator or a scheduler. Nothing here decides when to call `resume`.

## `dirty.py` -- the dirty child invalidates the chain above it

**Does:**

- `mark_dirty(stack, call_id, reason)` records that one call occurrence resolved dirty, with the
  reason named by the caller. (The owner's brief writes `mark_dirty(call_id, reason)`; the marking
  needs somewhere to be recorded, so it lives on the stack: `stack.mark_dirty(call_id, reason)` is
  that same call with the store named by the object instead of the first argument.)
- `invalidate_ancestors(stack, call_id)` walks the parent links from that child to the root and marks
  **every** ancestor invalid, and reports them in order: the child, the ancestors nearest first, the
  root, the ones that were already invalid, the siblings left valid, and everything else untouched.
- It refuses a chain that does not reach the root (`ANCESTOR_CHAIN_BROKEN`) rather than quietly
  stopping at the last recorded thread.

**Does not:**

- It does not decide that anything is dirty. Canon gives one example ("a Power bypass") and no
  classifier, so the reason is always the caller's word, never this module's judgement.
- It does not revalidate, repair or restore. There is no un-dirty operation and no retry.
- It does not invalidate siblings. Canon names "the entire parent chain", which is the ancestor line,
  and this build follows the same reading `dwp_engine/retraction.py` records for the same gap. A note
  worth stating plainly: a sibling of a dirty child keeps its own record clean, but its **parent**
  is now invalid, so nothing above that sibling may return either. The test says both things.

## `atlas_binding.py` -- the minimal bridge to the real atlas model

**Does:**

- Re-hashes the six real-model files in `real_atlas/` on import and on demand, refusing if a byte
  moved.
- `snapshot_digest_of(snapshot)` reads the real `AtlasSnapshot.snapshot_digest`, and
  `require_snapshot(address, snapshot)` refuses `SNAPSHOT_MISMATCH` when an address names a different
  saved snapshot. That is what makes "which saved snapshot" checkable instead of decorative.
- `glue_back(nodes, witness_id=None)` calls the real `compatibility()` **and** the real
  `certify_overlap()` and reports both answers. `GlueBack.ok` is those two joined with `and`, the
  only thing this build adds.

**Does not:**

- It does not build, extend or re-implement an atlas. No node class, link class, kind vocabulary or
  digest scheme exists in this folder.
- It does not decide glue-back. No field comparison, no overlap test, no witness rule.
- It does not promote or rename a node's status, and writes nothing back into a snapshot.

## `test_all.py` -- 27 cases, no pytest

Run it with:

```
python -B test_all.py
```

It prints one PASS or FAIL line per case plus a total. Every rule in the table above has a case, and
the brief's twelve required cases are all present and named in the file header. It also covers the
three cases the addendum asks for beside the brief: two nested levels returning to the exact waiting
occurrences in dependency order (line 40, AT15/AT20), two callers with identical fields receiving
only their own results (line 41, AT15/AT25/AT26), and stale/cancelled/duplicate completions not
resuming an unrelated caller (line 42, AT16/AT17/AT19).

## The real atlas copy, and how it got here

`real_atlas/` holds six files copied **byte for byte** from
`C:\Users\wakil\Documents\Codex\2026-10-16\continuity_build_v3\real_atlas\`, which is itself a
byte-for-byte copy of branch `codex/helm-rpa-recorded-run-20260922` at commit
`eb9985566bd11a89f485d627186ef0efa7177f02`. `real_atlas/PROVENANCE.md` is carried unchanged and
records that first hop (it therefore mentions the sibling package's function name, which is correct
for the copy it documents). `ATLAS_COPY.md` beside this file records the second hop. The test
`the_copied_real_model_still_hashes_as_recorded` re-hashes all six and checks them against the
recorded values **and** against the files they came from.

Measured sha256 of the model: `rpa_model.py` =
`323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01`.

## Every question the sources do not settle

These are the points where the addendum, the canon and the brief leave a real choice open. Each one
is marked at the place in the code where the choice is made, in the form
`# UNDECIDED IN SOURCES: <question>`, and each one is listed here verbatim. A test fails if the two
lists drift in either direction.

- UNDECIDED IN SOURCES: does a child inherit the parent's snapshot digest or take its own -- the addendum binds the suspended caller's address to a snapshot (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:22) and says an updated live observation is a new source-bound view (line 36), and settles neither for a child.
- UNDECIDED IN SOURCES: must a return address carry the recursion depth n -- Theorem 27.3 is stated depth-wise (Chapter_27_RPM_Structure.md:61) and the addendum's field list (lines 19-24) names no depth, so no depth field is carried here.
- UNDECIDED IN SOURCES: must a child thread stay on its parent's branch, or may a child open a new branch -- the addendum lists the caller's current branch (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:19) and never says whether a child inherits it, so child_of inherits the parent's branch unless the caller states a different one.
- UNDECIDED IN SOURCES: must the root observation reference be held for the whole episode or may it be dropped once the chain is entered -- the addendum says to retain a root reference to the original goal/CJT throughout (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:9) without saying when it may be released, so this build never releases it and never reads it as a return path.
- UNDECIDED IN SOURCES: must a returned Bias be newer by exactly one version or merely greater -- the addendum says a legitimate repair may change Bias (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:30) and the owning brief says strictly newer, and neither fixes the step size, so any strictly greater version is accepted here.
- UNDECIDED IN SOURCES: may a caller invalidated by a dirty child be resumed at all, or must it be revalidated from the root first -- the addendum names a stale or canceled outcome and an explicit revalidation (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:32) but never names an ancestor invalidated by a dirty child (Chapter_27_RPM_Structure.md:63), so this build refuses the return with ANCESTOR_INVALIDATED and performs no revalidation of its own.
- UNDECIDED IN SOURCES: may a resume proceed with no glue-back verdict when no atlas nodes are supplied -- the addendum requires the child's result and its expected parent to be verified (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:29) and the owning brief makes glue-back the real model's decision, but the resume signature carries no nodes, so glue is an optional real-model verdict and its absence is recorded as no verdict rather than as success.
- UNDECIDED IN SOURCES: must one accepted result wake only one waiting caller, or may it notify several compatible callers -- the addendum allows one qualified result to notify multiple compatible waiting callers and also defers general fan-out beyond the first nested demo (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:33), so this build is one thread per call occurrence and does not fan out.
- UNDECIDED IN SOURCES: what a caller's remaining work IS and how a step counts as done -- the addendum says the caller completes its own remaining work before its result returns further (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:9) and names no work items and no completion procedure, so the steps are named by the caller and marked done in the order they were given.
- UNDECIDED IN SOURCES: is a duplicate finish refused because the return token was consumed or because the thread is finished -- the addendum forbids a second committed resume (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:29) and names neither mechanism, so this build models one finish per call occurrence and reports both cases with THREAD_ALREADY_FINISHED.
- UNDECIDED IN SOURCES: is a thread marked dirty by canon's rule, a dirty resolution, the same marking as a thread invalidated by a dirty child -- canon uses invalidated for the parents and dirty for the child's own resolution (Chapter_27_RPM_Structure.md:63) and does not say the two words name one state, so this build keeps them as two flags (dirty for the resolution, invalid for the propagated chain).
- UNDECIDED IN SOURCES: are the same-level siblings of a dirty child also invalidated -- canon names "the entire parent chain" only (Chapter_27_RPM_Structure.md:63) and says nothing about a coproduct's clean parts, so this build invalidates the ancestor line only and leaves siblings valid, the same reading dwp_engine/retraction.py records for the same gap.
- UNDECIDED IN SOURCES: may this build's caller choose the glue-back witness instead of taking the real model's own default -- the real certify_overlap picks the minimum common member when no witness is named and the addendum says nothing about who chooses (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:29-30), so a witness is passed through when the caller names one and the real model's default is used when it does not.

## What this cannot claim

The strongest thing this cannot claim: **that a thought ever came back.** No circuit uses this yet.

More precisely, this build cannot claim any of the following, and does not:

1. **That anything recursed, suspended or returned.** There is no engine, so there was nothing to
   suspend and nothing to resume. The rules are implemented; their use is not.
2. **That it joins the recursion engine or the atlas loop.** It imports neither `dwp_engine` nor
   `continuity_build_v3`; there is no wiring, no adapter and no caller. The address carries no
   recursion depth, because the sources do not say it must (see the undecided list).
3. **That a return address helps a running system.** Nothing here measures accuracy, latency, cost,
   or whether a coordinate-based return is better than a remembered one. The addendum itself says
   the design consequence is *not* established as improving learned accuracy [line 48].
4. **That glue-back is proved.** `GlueBack` reports the real model's shared-field consistency and
   common-witness certificate. That is not a sheaf gluing proof, and the record says so in its own
   `boundary` field.
5. **That a dirty chain is repaired.** This build marks and refuses. It does not revalidate, retry,
   or restart anything from the root.
6. **That any of this is persisted.** It is in memory. A crash loses the stack, and the addendum's
   restart-around-suspension case (AT10/AT21/AT22) is not addressed here.

## What is settled in this build, and in what sense

- The mechanism is implemented and tested: 27 cases, standard library only, under a second.
- Every refusal is a distinct typed word, and every refusal in this README is a word the code
  actually raises.
- The atlas copy is real, is hashed, and is byte-identical to where it came from.
- The claim ceiling above is repeated at the top and bottom of every file in the folder.
