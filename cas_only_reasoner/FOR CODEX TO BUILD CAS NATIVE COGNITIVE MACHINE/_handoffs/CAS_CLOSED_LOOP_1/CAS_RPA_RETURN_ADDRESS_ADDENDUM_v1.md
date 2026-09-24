# CAS-CLOSED-LOOP-1: RPA-addressed RPM return
**Addendum:** RPA-RETURN-1, 2026-09-24. **Status:** implementation clarification; no new execution or passing result is asserted.
**Notice:** chatgpt-rpa-return-20260924-01. **Author:** ChatGPT for Little Henderson.
**Base:** DIRECTIVE.md SHA-256 `3772f1741f8af430144fa0d0b739a7bdebb3eef56819fab013313a07052207db`. Preserve the original package and its manifest unchanged.

## 1. Owner's addition and the implementation decision
The owner said: “Also, as the sub recurses throughout the RPM system through the Atlas, or the RPA, the coordinate system, or system of coordinates, could be used to establish its way back through the RPM, through the recursive prerequisite system, back to the original CJT.”
Implement this by binding the existing RPM continuation to an exact RPA address and an explicit return chain. The address answers where; the saved continuation answers which caller and what unfinished work resumes. This clarifies existing tasks T05/T07 and directive sections 6/8, not a new controller or a replacement for the existing return machinery.
A successfully checked child result returns to its immediate waiting caller. That caller completes its own remaining work before its result returns further. Retain a root reference to the original goal/CJT throughout. A direct root shortcut must not mark intermediate prerequisites complete.

## 2. Keep three kinds of location distinct
**Exact address:** episode, branch, source snapshot, board/CJT, call occurrence and saved continuation. Reuse existing stable runtime identifiers and the atlas's snapshot-bound address scheme. A module's identity alone is not a call identity: one CJT can be invoked more than once.
**Profile coordinates:** the optional 39-coordinate chart derived from a declared 40-component profile, with basis, ordering, chart version and reference. These locate a description, not necessarily a unique complete state. Equal profiles cannot merge callers. Missing profiles must not prevent exact return.
**Screen position:** flower placement, zoom and layout. They may display the return trail but must neither choose the execution recipient nor grant execution rights. Re-centering a chart or changing display focus cannot change the saved continuation.
Treat the combined record as an atlas-addressed continuation. Do not locate the caller by nearest flower, nearest profile, distance to zero, or inversion of a profile transformation. Do not introduce a competing live registry owned by the renderer.

## 3. Minimal saved return information
Map these meanings to existing fields first; extend only what is missing, under a new adapter version rather than changing frozen native schemas:
- Episode/root goal and original board/CJT; current branch and parent call occurrence.
- Unique child occurrence, immediate parent frame/continuation, and expected child-result type or postcondition.
- Exact caller inputs/context, source versions and the specific next stage after suspension.
- Snapshot-bound atlas address for the suspended caller, plus the authoritative runtime state/frame reference.
- Bias version at suspension, permitted repair/update lineage, and current budget-ledger reference. Saved remaining work is historical evidence, not a fresh spend allowance.
- Optional chart/profile/reference metadata and an ordered list of runtime call/return edges for display. Every edge must retain its relation type and source event.
The exact address is a lookup key, not authority by itself. The coordinator still checks whether the caller is waiting, the result is valid for it, and resumption is permitted.

## 4. Enter, return and recover
Before dispatching a child, durably preserve the parent's continuation using the runtime's existing transaction/journal path. For strict nesting, record the parent link on the RPM stack. No copy of an entire global snapshot is required at each level.
On completion, verify the child's result and its episode, branch, occurrence and expected parent. Commit the accepted result/update and consume its return token through the existing coordinator. Duplicate delivery must not cause a second committed resume or a second application of the repair. Do not infer an exactly-once external action from this local guarantee.
Resume the same logical caller at its saved next stage, carrying only qualified repair deltas and rechecking invalidated prerequisites. A legitimate repair may change Bias and current-state identity; do not require the old state hash to remain the live hash or restore the pre-repair Bias over the new one. Preserve the old hash as history.
Returning is forward progress with a result, not reversing time or undoing the child. Completed work stays charged. Use the current ledger, not the saved historical remainder, to admit further work. Rollback or canceled work never refunds execution already performed.
If a parent was canceled, replaced or materially changed, return a named stale/canceled outcome or perform the existing explicit revalidation. Never substitute the nearest or latest same-named CJT. Corrupt or incomplete recovery data must not fabricate a successful return.
For shared prerequisites, one qualified result may notify multiple compatible waiting callers, each with its own continuation and acceptance check. The general dependency graph is not necessarily one tree. Asynchronous siblings may finish out of order; shared results do not make all callers complete automatically. Reuse an existing subscriber/continuation mechanism if present; otherwise defer general fan-out beyond the first nested demo.

## 5. Atlas presentation and acceptance within existing tasks
Show the original goal, current executing child, immediate return destination, remaining caller chain, and actual completed return edges. Distinguish inspecting a historical parent from executing a resume. An updated live observation creates a new source-bound view; the old snapshot/address stays inspectable.
Add focused cases to the already planned checks, not a separate large review or a blocker on current Helm training:
| Existing checks | Required case |
|---|---|
| AT15, AT20 | At least two nested prerequisite levels return to the exact waiting occurrences, in dependency order, with original inputs and correct resume stages. Reuse a supported native nested fixture. |
| AT15, AT25, AT26 | Two callers with identical profiles still receive only their own results; recentering, relayout and missing profiles do not change runtime return destinations. |
| AT16, AT17, AT19, AT27 | Wrong-branch, stale, canceled or duplicate completions cannot resume an unrelated caller; cycles and depth limits use the existing bounded behavior. |
| AT10, AT21, AT22 | Restart around suspension/return preserves the chain, accepted Bias deltas and consumed work; replay does not restore an old allowance or repeat a committed repair. |
If a required behavior already passes under the pinned runtime, cite that test and add only its atlas binding check. Supporting arbitrary DAG fan-out or a new coordinate geometry is not required to close the initial nested witness. No neural run is needed to test address preservation itself; follow existing resource policy for actual runtime tests.

## 6. Scope, sources and delivery
Source basis: the base directive section 6 already preserves exact caller frames and budgets, and section 8 separates runtime state, focus and coordinates. `docs/CAS_RPA_OHM_ATLAS_20260922.md` specifies snapshot-bound exact addresses and reference-independent item identity. `docs/CAS_RPA_MATHEMATICAL_REVIEW.md` explains that equal profiles do not establish complete-state equality. `docs/CAS_RPA_COMPOUND_RUNTIME_v0.1.md` and the current equivalent preserve occurrence identities, charged work and replay.
The design consequence proposed here is their explicit connection for RPM returns. Neither the source documents nor this addendum establish that this connection is implemented, that geometry is necessary for it, or that it improves learned accuracy. Reuse the same exact-return facilities in matched controller comparisons.
Codex remains the proposed integration writer; Claude coordinates, reviews the changed path and owns authorized AWS execution. Relay this through existing channels, import the addendum beside the immutable base in the owning branch, and return the actual source/test mapping and a saved nested-return trace. Preserve all existing jobs, custody, budgets and original results. Do not spawn another agent or restart completed reviews.
