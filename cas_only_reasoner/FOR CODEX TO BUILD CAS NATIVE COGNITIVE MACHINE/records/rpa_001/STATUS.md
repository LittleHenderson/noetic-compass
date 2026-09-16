# CAS-RPA bounded adoption: evidence and status

Date: 2026-09-16. Result: a real native episode can be inspected through the
atlas's typed relationships and two equivalent-data layouts. This is a bounded
read-only prototype, not general planning or full CNCM acceptance.

## Source review and implementation

Both original PDFs were read in full, with visual inspection of the overview
and the full atlas's overlap/interface plates. Their exact identities are in
source_identity.json. Project mapping and the first prototype are specified in
../../docs/CAS_RPA_PROJECT_FIT.md. The mathematical review, with page references
and primary sources, is ../../docs/CAS_RPA_MATHEMATICAL_REVIEW.md.

The implemented model distinguishes contains_part, refines_state, reachable_via,
overlaps_with and references_same_idea. It checks contexts, record versions,
shared-field consistency, containment cycles and finite common witnesses.
Bounded expansion counts the root and retains deferred work. Actual state,
focus and hypothetical branches remain separate.

The native adapter first reconstructs the journal through native semantic
replay against a caller-trusted genesis, source profile and external digest.
It then projects the actual saved caller, input, procedure, budget, evidence,
transitions and proposed next actions. The adapter and viewer cannot write to
the native machine. Proposal hints only report necessary conditions and do not
grant execution permission.

## Final retained prototype

The authoritative current export is demo2/receipt.json, SHA-256
dcd8e3c99fdf0edd45f0e6ea56a6d9336fabac9761ac3056d29b223bf6339f62.
It pins seven source files and eleven generated artifacts. The three examples:

| Export | Actual state | Nodes / links | Bounded expansion |
| --- | --- | --- | --- |
| missing_procedure | RUNNING; caller suspended, procedure absent | 10 / 9 | 8 visited, 0 deferred |
| checked_solution | CONCLUDED; checked output7 | 29 / 28 | 12 visited, 2 deferred |
| recovery_and_rollback | NEEDS_CAPABILITY after reuse, rollback and refused next call | 47 / 46 | 12 visited, 6 deferred |

The missing-procedure prefix was reproduced and its two transitions compared
exactly with the retained native acquisition journal. The completion and
rollback views use acceptance_002 directly. The installed program's acquisition,
independent qualification, exact caller return, result7, fresh-process reuse
on new inputs (-3/2) and later rollback/refusal are runtime records, not
illustrated or hypothetical outcomes.

The native source profile remains
c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607.
The final native journal remains
25780013e6834fb00aff49849d531c4793ff21a035cacaaf89a70baf85a4bfc1.
Those native sources and acceptance evidence were published previously in
8b64cac8e2762333ff16f72e261475dc408ca665.

The earlier demo/ directory is preserved as a prior visual revision. It has
its own source-bound receipt and must not be described as the final renderer.

## Verification

The final complete homebase run passed **571 tests plus462 subtests**, with
zero skipped tests. final_full_suite_tests.xml records all1033 cases and no
failure/error. Its SHA-256 is
4a1ed956ff02330c6bf2fce6287de259c79fce03ee7deee185aed7cf5e2fe3bc.

The new tests cover typed relationships and exact finite overlap, equal-budget
ordinary graph walks, cycles, incompatible refinements, malformed records,
input limits, source/replay failures, exact native evidence, charged failures,
partially accepted batches, rollback, unresolved return frames and focus
isolation. Browser tests use actual local Chrome with Node and cover both
layouts, filter/focus controls, immutable embedded evidence, hostile strings,
proposal-only controls, readable labels and mobile bounds.

Final direct browser QA against all three demo2 HTML paths is retained in
viewer_browser_qa/browser_receipt_final2_review.json, with final2_review_*.png
screenshots. All three report correct titles, centered focus, approximately
16px rendered label height, matching node/link sets, no browser exceptions
and no external page requests. The missing-procedure final screenshot was
also visually inspected by the parent agent.

That QA receipt's browser_test_sha256 describes the test file before a later
teardown-only correction. The product renderer, exported HTML and CDP assertion
script did not change. The first final suite's only failure was a Windows
temporary-profile file still held by Chrome; it is preserved in
full_suite_browser_cleanup_failure.xml. The test now requests graceful closure
of its owned browser and waits, with a fallback limited to its owned process
tree. The final full suite above uses that corrected test and passed.
The earlier overlong shared-call-ID failure and intermediate successful XML
records are also retained, without being substituted for final acceptance.

## Delivery and claim boundary

package_delivery.py copied the three standalone HTML files and two reports
byte-for-byte into the outer homebase's output/rpa_001 directory. Their receipt
is delivery_receipt.json. The HTML opens locally and makes no page network
requests. Publication means a source/evidence checkpoint; it is not a deployed
service or a CI success claim.

ledger_update.json records identical append-only updates to both canonical
CNCM requirement ledgers, preserving all prior bytes. CAS Harness and its
production tracker are outside this change.

No native40-coordinate profile is measured here. DF/F/TF namespaces are not
cast or silently equated. The centered ALR inverse,39-dimensional simplex,
common-intersection requirement, Fisher-Rao distinction and finite expansion
convention are documented; no geometry is used to authorize transitions.
The evidence does not establish a full nerve, sheaf, complete42-role
implementation, improved reasoning/learning or superiority to an ordinary
graph. Held-out equal-information/equal-budget benefit studies remain open.

No paid model/provider work was used. This advances bounded inspection and
diagnosis portions of V08/V10/V13 and systems8/9/24/27/31. The full V01-V18,
31-system and integrated20-step vision remains open.
