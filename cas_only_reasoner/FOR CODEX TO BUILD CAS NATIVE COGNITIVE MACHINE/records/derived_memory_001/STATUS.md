# Derived-result memory checkpoint

Status: BOUNDED_RUNTIME_ACCEPTANCE_PASS / FULL_REGRESSION_PASS.

This checkpoint integrates checked mathematical results with native memory,
RPM and compound execution under a new0.6 contract. The required behavior and
contract and limits are in spec/CNCM_DERIVED_MEMORY_v0.6.md.

Completed: implementation, independent adversarial review, closed wire schemas,
and 107 freshly repeated focused tests with unchanged runtime/test sources.
The final revised helper passed all ten expected scenario outcomes and all 141
recovery cuts. The preliminary helper and its weaker binding/reporting boundaries
remain retained separately; they do not substitute for the final recipe.

The revised recipe separately blocks disabled generation and acquisition,
asserts exact stale refusal, pins helper/test/runtime bytes before and after,
binds child inputs to a parent-held manifest SHA, and records both process import
inventories. Every saved prefix reconstructs and resumes in one fresh child
process, not a separate process per cut. Final acceptance binds 117 declared
inputs, 25 artifacts, and 45 parent plus 45 child source imports.

Final runtime profile SHA-256:
1c1427a6b6b63424df578b437a73866823fe6ab21107916aebc62ba33f82bf64.
Final acceptance_001/receipt.json SHA-256:
434ccb827b675509c46047e54b94731768600595cf0a94303880c258e07f657c.

Full symbolic regression passed 1,581 tests and 656 subtests in 1,164.32 seconds,
with zero failures, errors or skips and all declared inputs unchanged. The JUnit
combined count is 2,237. final_suite_001/receipt.json SHA-256:
5d20dc801485f79800df4cf2c718294c0dd73ebb0ddc77fe939d072d2139c958.
All failed development, draft-helper and browser probes remain retained.

The preservation baseline binds 126 accepted sources, all four earlier runtime
profiles and 367 recurrence/handoff evidence files. No local neural or provider
run was used. See docs/CNCM_DERIVED_MEMORY_IMPLEMENTATION_v0.6.md and the separate
docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md.

The complete charter and earlier negative neural results remain unchanged.
