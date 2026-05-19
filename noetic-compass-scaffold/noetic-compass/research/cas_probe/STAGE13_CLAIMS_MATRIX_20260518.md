# Stage 13 Claims Matrix

| Claim | Status | Evidence | Boundary |
|---|---|---|---|
| CAS Harness can inspect hidden activations across layers for a trained CAS readout | `STAGE13_MULTILAYER_TRACE_AUDIT_COMPLETE` | focus_token layer 12 test acc `0.9540` | Open-model activations only |
| CAS Harness can flag class-level blind spots | diagnostic pass | Top candidates: relation_dependency, production_recipe, membership_assertion, cover_partition_formula, yield_query, cardinality_assertion, state_vector, emergent_register_assignment | Blind spot means weak/unstable evidence, not proof of incapacity |
| CAS Harness can trace example-level stability/drift | diagnostic pass | 77.7% stable-like; 22.3% problem-like | Does not identify exact causal neurons |
| CAS can detect weights firing | rejected phrasing | Weights are static; activations change per input | Say activation firing or weight alignment instead |
| Pythia internally validates CAS formulas | not established | Stage 12/13 use external compiler-valid labels | Pythia is audited by CAS Harness; it is not a CAS compiler |
