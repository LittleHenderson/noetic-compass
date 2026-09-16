# CAS-RPA compound runtime extension proposal v0.1

Date: 2026-09-16. Status: **ADAPTER DESIGN ONLY; this adapter has not been
implemented or accepted.** Compound runtime 0.5 has passed its separate bounded
acceptance and full regression suite. Consult the
[compound status record](../records/compound_procedure_001/STATUS.md) for the
runtime's evidence and remaining gates. This note supplies no acceptance result.

The existing [project-fit note](CAS_RPA_PROJECT_FIT.md) and
[mathematical review](CAS_RPA_MATHEMATICAL_REVIEW.md) remain unchanged, receipt-bound
sources. Their implemented first prototype is the native runtime 0.2 adapter in
[rpa_native_adapter.py](../cncm/rpa_native_adapter.py), bound by
[the existing receipt](../records/rpa_001/demo2/receipt.json). It is **not connected
to compound runtime 0.5**. A new adapter must use a separate versioned entry point;
it must not reinterpret a compound journal as a native 0.2 journal.

## Supplied design sources

The following current PDF identities match
[source_identity.json](../records/rpa_001/source_identity.json). The full atlas's
printed page numbers agree with its PDF page numbers.

| Source | Exact local path | Pages / bytes | SHA-256 |
| --- | --- | --- | --- |
| Full atlas | `C:/Users/wakil/Downloads/CAS_Recursive_Possibility_Atlas_v0_1.pdf` | 26 / 233950 | `e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab` |
| Overview | `C:/Users/wakil/Downloads/CAS_RPA_Map_Overview.pdf` | 1 / 81278 | `999cd83381b316b1284a65ebaa48736c4a73ad41b08cb12c2099a43e0787c2fb` |

These documents propose typed relationships, separate present/focus/hypothesis
handles, finite witnessed overlaps and bounded expansion. They do not certify
an implementation, an independently measured CAS profile or a performance gain.
Their separate CAS references C1-C6 are not independently re-audited here.

## What compound 0.5 would add to the view

The [compound contract](../spec/CNCM_COMPOUND_CONSTRUCTION_v0.5.md) concerns the
original expression `a*(b*x+c)+d=e`. Its five scalar inputs can include exact
scoped memory references. Its candidate grammar contains 60 one-call and 360
two-call programs over a pinned six-instruction linear primitive. Four public
development cases guide construction; eight separate positive cases and four
domain cases form a public qualification panel. Every actual output still needs
an independent substitution check against the original expression.

These are bounded engineering contracts. Their acceptance does not
establish general synthesis, neural learning, protected examination custody or
unconditional truth of recalled source claims.

| Atlas relationship or view | Proposed compound evidence projection | Boundary |
| --- | --- | --- |
| `contains_part`, atlas pp.4-5 | Original problem parameters; compound program call steps; primitive dependency; saved compound and primitive acquisition frames | Preserve separate objects and acyclic containment. A call sequence is not time merely because its steps are visually nested. |
| `refines_state`, pp.4-5,20 | Same-context call details bound to original input, source-resolution receipt, program digest and pinned primitive | Require the existing finite membership/subset and shared-field checks. Detail supplies no proof or dispatch permission. |
| `reachable_via`, pp.17-18 | Replayed request, nested acquisition, construction, qualification, install, return, apply, ordinary commitment and refusal transitions | Recorded edges reference exact events. Suggested successors remain hypothetical. |
| Evidence, pp.10-12,22 | Source statements, corrections, recalls, construction attempts, qualification, original-expression checks and rollback lineage | Keep source attestation, engineering qualification and checked arithmetic distinct. A matching hash is not independent world-fact verification. |
| Present/focus, pp.3,17,22 | Latest replayed state; selected inspector node; optional proposed branch | Navigation cannot advance a machine or install, execute, roll back or conclude. |
| Bounded expansion, p.19 | Candidate catalog, acquisition ancestry and exact dependency links | `SEARCH_EXHAUSTED`, missing evidence and deferred display have different meanings. None establishes impossibility. |

The additional value is inspectable evidence of why a compound call is available
or blocked, which primitive it depends on, which source values were used, and
where the caller resumes. It does not alter the existing mathematical limits:
40 components have 39 independent simplex coordinates; centered ALR is not the
Fisher-Rao metric; a common witness is required for an intersection; local field
agreement does not establish a sheaf. No measured 40-component profile or native
CAS-Ohm flow is supplied by compound construction.

## Proposed read-only adapter boundary

Proposed new entry point, not an existing API:

```python
compound_atlas_from_journal(
    journal, *, trusted_genesis, trusted_ingress,
    expected_journal_digest, trusted_ingress_extensions=(), profile=None,
)
```

Use a new outer document version, `cncm.rpa-compound-view/0.1`, containing
`schema_version`, `atlas`, `native`, `timeline` and `next_actions`. Retain the
existing typed atlas model's version and limits. The outer runtime binding must
explicitly identify compound 0.5, its source profile, journal digest, ingress
digest and replayed final state hash. Do not expose a live coordinator or machine
handle in the returned view.

The current implementation's semantic-replay entry is
[`recover_compound_journal`](../cncm/compound_recovery.py), with the same trusted
arguments above. It returns a reconstructed machine. `verify_compound_journal`
returns a replay receipt. There is currently no exported function named
`replay_compound_journal`; references to replay here describe the operation,
not an implemented alias or a replacement for recovery.

The proposed adapter must:

1. Obtain the exact typed genesis, initial trusted source digest set, chronological
   per-episode ingress extensions, complete expected journal digest and approved
   source profile from caller custody. Journal fields cannot grant any of these
   authorities. A final ingress union cannot replace the extension chronology.
2. Invoke full compound semantic recovery independently of the supplied state
   snapshots. This reconstructs proposal occurrences, accepted and rejected
   transitions, frames, budgets, source bindings, registry dependencies and final
   state. Reject malformed, truncated, resealed-but-inconsistent, wrong-source or
   wrongly anchored input before publishing an authoritative-looking atlas.
3. Project immutable data from the reconstructed journal and state. Preserve
   episode/run/call/goal/branch identifiers and exact source/event/record digests.
   A saved capsule or parsed state cannot populate a live registry. Full replay
   may repeat bounded construction work; it is separate from display expansion.
4. Show conservative work reservations, actual primitive instruction counts and
   original-check counts as different quantities. Failed checks retain their
   recorded charge. RPM return does not refund work; a new authorized episode's
   budget is explicitly separate. Policy units are not FLOPs, energy or money.
5. Distinguish historical installation from current eligibility. Removing the
   compound head blocks its dispatch. Removing or replacing the authorized pinned
   primitive also blocks dependent compound dispatch; an inspectable artifact is
   not sufficient authority. Derive displayed status from the replayed kernel
   records and current heads, not from a generic graph reachability rule.
6. Preserve `USER_ATTESTED`, `TEST_FIXTURE`, conflicts, retractions, exact source
   heads and unmet `INDEPENDENTLY_VERIFIED` demands. Label arithmetic conclusions
   conditional on their recorded source bindings. Displaying a valid resolution
   receipt must not upgrade a factual status.
7. Return only proposal-level next-action hints with exact blockers. No view
   element authorizes execution or an external action. Focus, layout, expansion
   and hypothesis controls do not call machine advancement or persistence APIs.

The existing atlas permits 512 nodes, 2048 links, an 8 MiB serialized snapshot
and 262144 characters per field value. The complete construction report can exceed one field's
cap. Therefore retain the complete source record outside individual node fields
and bind bounded inspector excerpts/pages to its exact digest. Use explicit
candidate indices, count, omitted/deferred range and a digest-bound cursor.
Never silently truncate the source report, raise frozen limits, turn omitted
candidates into negatives, or duplicate a whole report into every node.

## Required prototype acceptance tests

These are required tests for a future implementation, not reported results.

- Replay an empty-registry compound episode at every pause point, including both
  acquisition frames; verify exact saved caller, branch, input, budget and return
  stage. Show both successful returns and rejected work with its unchanged charge.
- Replay fresh-process reuse, a later externally admitted source correction and
  both compound/primitive rollback paths. Require exact source chronology and
  expose why a retained program may currently be ineligible.
- Refuse forged/resealed state, event, proof, program pin, source binding, receipt,
  profile, complete-journal anchor and ingress schedule. No partial success view
  may conceal a replay failure. Preserve duplicate/malformed proposal occurrences
  and accepted/rejected IDs, including mixed ordinary batches where permitted.
- Represent one-call attempts, two-call attempts, qualification refusals, zero
  leading-coefficient domain refusal, 128-bit composition-input overflow and
  bounded-prefix `SEARCH_EXHAUSTED` distinctly. Candidate/deferred counts must
  reconstruct from the retained report and selected display page.
- Feed the ordinary graph and flower layouts the same canonical node/link records,
  source evidence, cursor, relation filters, root and depth/node budgets. Count
  the root as one node. Compare visited/traversed/revisited/deferred results with
  an independent ordinary graph walk; do not merely compare two render calls.
- Use identical inspector content, identifiers, status labels and action blockers
  in both layouts. Test shared ideas across contexts, finite common witnesses,
  pairwise-only intersections, conflicting versions and containment cycles.
- Show that layout, focus, paging and hypothesis changes preserve the complete
  source journal digest, replayed present hash, registry and budget. Assert zero
  live kernel writes, network actions, provider calls or model work by the viewer.
- Reject display size overflow and stale cursors explicitly. A small navigation
  budget does not claim to bound the independent journal-replay cost.

Parity tests establish faithful presentation at equal supplied information and
budgets. A performance claim would need a separate held-out study of prerequisite
diagnosis, wrong-version actions, invalid-state leakage, work and human task time,
with relation typing, recursive organization and layout varied separately. The
full charter and integrated 20-step acceptance remain separate gates.

## Boolean arity caveat in the supplied role index

Atlas p.14 labels role 26 XOR as "Exactly one" and role 27 XNOR as "Equal / include
both inactive". Their familiar two-input reading is sound:

| A | B | XOR | XNOR |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 1 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 1 |

For more than two flags, ordinary XOR expresses odd parity, not exactly-one:
`XOR(1,1,1)=1` although three inputs are true. Complemented parity is likewise
not an all-inputs-equal predicate: for three flags `NOT XOR(1,1,0)=1` although
they are unequal. A multi-input exactly-one or all-equal gate must name its own
predicate and arity. This is a derived truth-table caveat, not a defect in the
current RPA adapter, which grants no Boolean-gate execution authority.
