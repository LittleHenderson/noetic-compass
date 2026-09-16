# Native nested planning0.3: retained evidence and current status

Date: 2026-09-16. Result: **BOUNDED_NATIVE_NESTED_EPISODE_PASSED**.
The machine discovers a bounded equation dependency order, acquires one missing
atomic procedure inside nested planning, resumes exact callers, checks each
result and completes through the existing commitment gates. No execution order,
caller-authored resolver, expected answer or completed graph enters the problem.

## Actual episode and cost

The retained graph is supplied in non-execution order:

- leaf: 3*leaf+5=26
- mid: mid=1+2*leaf
- side: side=leaf
- root: 2*root+1=mid+side
- unused: an unreachable zero-leading cyclic equation

The query is root. Its results are leaf=7, mid=15, side=7 and root=21/2.
The leaf executes once even though two parents require it. The unused equation
is not executed. The coordinator reaches three active frames: a root waiting
for mid, mid waiting for leaf, and leaf acquiring the missing atomic procedure.

One selection and one independently checked installation serve four actual
procedure calls. Their combined conservative allocation is324 instructions and
42 checker calls, including grounding and original-equation checks. These are
abstract policy units, not measured CPU work, energy or billing.

The saved caller and parent branch remain frozen during each child. Returns
cite exact checked child execution records, and the current debited budget is
preserved. Child outputs remain in their own call workspaces; only the completed
query's checked dependency closure becomes a root branch proposition. Ordinary
reasoning, comparison, contradiction and commitment gates still apply.

## Final source and artifacts

The current source profile is
49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38.
It binds58 files: current0.3 code/contracts and unchanged transitive dependencies.
source_freeze_final.json records the exact set.

The authoritative receipt is acceptance_002/receipt.json, SHA-256
d9b67566817c0ff0f4d1249112542c10bfa71ab1a5cf68a71940076be3c2f0dc.
Its acquisition journal digest is
034c93ab0bcbf4d53ea699d8f49f474a9ed2e62d78d17f2dccf7cddd19d06e9b.
Its final three-episode journal digest is
2459cdcd786cc012a2bfdeac4e57e80181dce09bbe53f2d367ce2b40e8df1c19.

The producer PID66116 and fresh-process PID59608 are recorded. The separate
process semantically reconstructed all31 pause points, including every ordinary
comparison/commit/halt cut, then resumed each to the identical complete journal.
It also recovered the depth3 suspended caller from its exact retained state.

After replay, new-call selection and qualification were patched to raise.
The new-input graph changes leaf's right side to29 and concludes12 using the
installed artifact; its allocation is120 instructions/8 checker calls.
A subsequent native rollback removes the active procedure head while retaining
artifact and evidence history. With acquisition disabled, the next episode
unwinds to NEEDS_CAPABILITY and has no answer. The parent process independently
replays the full final journal.

The reproducer is ../../tools/reproduce_nested_planning.py. From this homebase:
`python -B tools/reproduce_nested_planning.py --output records/nested_planning_001/NEW_DIRECTORY`
The output directory must not already exist. Reproduction uses only symbolic
Python execution; no model, neural, GPU, network or provider work is launched.

acceptance_001 and the preliminary full-suite XML are preserved. Their runtime
source is identical; their source profile172a0fee86f56108985ce220603334f2ca5ed4babcc3d30cbf4aafdc6e2b316a
contains the contract's earlier draft-status paragraph. That paragraph was
replaced by a stable versioned-contract status linking to this evidence file.
The full suite and actual-source acceptance were rerun for the final profile.

## Verification and retained failures

Final full homebase verification passed **820 tests plus496 subtests**, zero
skipped tests, errors or failures. final_full_suite_tests.xml SHA-256:
a310a4127dce3dcbb751d86419980328acef4994aa6d9c7d2ee5bc61dbde79b2.
The separate golden verification reproduces all14 retained fixtures: eight
reasoning, five executable math, and one explicitly contract-only math fixture.

Coverage includes strict immutable models and nine closed schemas; every live
call stage, both frame kinds and all ten decoded record kinds; shuffled and
shared dependency graphs; twelve generated graph families compared with an
independent Fraction evaluator;96 seeded numeric grounding cases; failed
qualification charging; wrong issuer/goal/scope/call/frame/input/artifact;
old-episode reference substitution; duplicate and malformed proposal history;
source/version changes; rehashed false histories; missing, cyclic, depth,
budget and domain failures; and current proof/commit/halt gates.

Fault injections make the atomic checker falsely accept an incorrect answer
or give the call incorrect grounded inputs. The separate equation checker
rejects these, charges18/2 and publishes no execution or checked proposition.

The final acceptance also retains separate failure journals for missing input,
cycles, depth, native budget, zero leading coefficient and composition input
overflow. A valid child can yield more than128 bits under the512-bit output
contract; its parent then refuses to use it as a128-bit procedure input.
Initial testing found that reusing the old63-bit generic JSON integer ceiling
could not retain such a CAS-Math receipt. Version0.3 now has its own bounded
512-bit wire scanner and decoder; typed counters retain narrower bounds.
The failed initial kernel XML is preserved in ../nested_procedure_001/.

A wrong return proposal does not erase an already COMPLETE child's checked
result. The wrong proposal rejects and consumes a tick; a later canonical
return must independently pass its frame/record checks. Unfinished rejected
work records a failure and unwinds. Tick exhaustion can retain unresolved
frames; it never grants a new budget episode.

Earlier failures are retained, including schema terminal-vocabulary correction,
the initial adversarial test collection error and intermediate successes.
Fixture-profile unit tests are expressly labeled; release evidence above
uses actual current source bytes and a separate process.

## Preserved contracts and open work

The accepted native0.2 profile remains
c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607.
Its published source and receipts, the default0.1 runtime, original schemas,
CAS-RPA artifacts and protected sibling were not edited.

The new planner is deterministic and bounded to16 equations, four terms per
equation and at most8 active frames. Atomic acquisition still selects twelve
authored forms with public engineering qualification. These records do not
demonstrate new program synthesis, learned topology, general planning,
authenticated external custody, a CAS-specific performance advantage or full
Foundation semantics. Source profile/genesis/host trust remains explicit.
RPA's existing viewer targets0.2 journals and is not a0.3 control surface.

ledger_update.json records append-only updates to both canonical CNCM ledgers
and the V01-V18 research ledger, preserving original bytes. Next integrated
gaps include provenance-bound semantic correction memory and common verifier
contracts, broader checked program construction, and the remaining language,
flow, learning, tools and Foundry systems. No paid model/provider work was used.
The full V01-V18,31-system and integrated20-step goal remains open.
